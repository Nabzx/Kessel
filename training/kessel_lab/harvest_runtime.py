"""Request-driven qualified harvest execution and causal shadow forecasts."""
import argparse
import copy
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
import uuid

import numpy as np

from kessel_training.policy import configure_cpu
from kessel_training.wm_state import pack, violations
from .bootstrap_runtime import Handler as BaseHandler, Session as PlaybackSession
from .harvest_admission import FEEDBACK, FORECAST, load_admission, sha
from .harvest_contract import certificate
from .harvest_scenarios import environment
from .harvest_runtime_gate import verify_runtime_receipt
from .linear_feedback import load as load_feedback
from .range_pilot import stop_metrics
from .runtime import ROOT, FAMILIES, digest
from .server import Session as LockSession
from .start_progress import StartProgressSupervisor
from .start_rollout import clearance_packet
from .structured_fit import load as load_forecast

PATTERNS = ("recovery","carry_loss","stale_clearance","old_clearance","missing_clearance")
SOURCES = ("learned_linear","reference")


class LiveRun:
    def __init__(self,family,seed,source,pattern,admission,runtime_sha):
        self.env,self.scenario = environment(family,seed); self.initial_certificate = certificate(pack(self.env)[0])
        if family != "prepared_no_progress" and not self.initial_certificate["supported"]:
            raise ValueError("Outside qualified synthetic material/traction limits. Choose another practice seed or scenario.")
        self.source = source; self.family = family; self.pattern = pattern; self.base = self
        self.feedback,_ = load_feedback(FEEDBACK); self.forecaster,_ = load_forecast(FORECAST)
        self.actor = StartProgressSupervisor(actuator=self.feedback.action if source == "learned_linear" else None)
        self.records = []; self.decisions = 0; self.done = False; self.finished = False; self.end_reason = None
        self.fault_start = self.loss_start = self.settled = None; self.slow = 0
        self.override_decisions = 0; self.resumed = False; self.previous_override = False; self.max_mass_residual = 0.
        self.stop_result = self.refusal_result = None
        self.stop_check = family in ("blocked","range_dropout") or pattern in ("carry_loss","stale_clearance","old_clearance","missing_clearance")
        self.criterion = "accepted_refusal" if family == "prepared_no_progress" else "stop" if self.stop_check else "delivery"
        self.gate = admission["forecast_gate"]
        self.identity = digest({"scenario":self.scenario,"source":source,"pattern":pattern,"admission":admission,"runtime_sha256":runtime_sha})

    def frame(self):
        state = pack(self.env)[0].tolist()
        return {"state":state,"t_s":state[10],"phase":int(self.actor.memory.phase[0]),"step_index":self.decisions,
                "wheel_angles_rad":self.env.wheel_angles[0].tolist(),"last_action":self.records[-1]["action"] if self.records else None,
                "forecast":copy.deepcopy(self.records[-1]["forecast"]) if self.records else None}

    def step(self):
        if self.finished: raise ValueError("run finished; start a new run")
        actual = self.env.observe(); observed = {k:v.copy() for k,v in actual.items()}; now = float(self.env.elapsed[0])
        if self.pattern in ("recovery","carry_loss") and self.fault_start is None and self.actor.task.mode == "carry" and actual["proprio"][0,4] <= -.5:
            self.fault_start = now
        injected = self.fault_start is not None and (self.pattern != "recovery" or now-self.fault_start < 2.-1e-8)
        if injected:
            observed["range_valid"][:] = 0; observed["proprio"][0,12] = 0; observed["proprio"][0,11] = now-self.fault_start+.1
        packet = clearance_packet(self.env,self.pattern); action = self.actor.act(observed,packet)
        override = self.actor.last["override"]; self.override_decisions += override
        self.resumed |= self.previous_override and not override; self.previous_override = override
        progress_hold = self.actor.last["proposal_source"] == "conventional_initial_no_progress_hold"
        active = bool(injected or self.family == "range_dropout" or not self.actor.last["clearance"]["usable"] or progress_hold)
        if active and self.loss_start is None: self.loss_start = now
        record = self.frame(); state = np.asarray([record["state"]])
        prediction = self.forecaster.predict(state,action)
        invalid = violations(prediction["next_state"])
        physical = any(bool(v[0]) for k,v in invalid.items() if k != "mass_error_kg") or abs(invalid["mass_error_kg"][0]) > 25
        forecast = {"source":"privileged_hybrid_shadow","produced_at_s":now,"for_decision":self.decisions,
                    "nominal_horizon_s":.1,"state":prediction["next_state"][0].tolist(),"events":prediction["events"][0].tolist(),
                    "disagreement":float(prediction["disagreement"][0]),"accepted":bool(not physical and prediction["disagreement"][0] <= self.gate["threshold"]),
                    "known_priors":["kinematics","geometric events","material accounting"],"influences_action":False}
        record.update(observation={k:v[0].tolist() for k,v in observed.items()},actual_observation={k:v[0].tolist() for k,v in actual.items()},
                      clearance=packet,supervision=copy.deepcopy(self.actor.last),action=action[0].tolist(),forecast=forecast,
                      fault={"active":active,"started_s":self.loss_start,"injected":injected,"cause":"initial_no_progress" if progress_hold else "sensor_or_clearance"})
        _,reward,term,trunc,info = self.env.step(action); self.done = bool((term|trunc)[0]); self.decisions += 1
        following = pack(self.env)[0]; predicted = prediction["next_state"][0]
        forecast["measured_error"] = {"position_m":float(np.linalg.norm(predicted[:2]-following[:2])),"carried_kg":float(abs(predicted[7]-following[7])),
                                      "delivered_kg":float(abs(predicted[8]-following[8])),"pile_height_mae_m":float(abs(predicted[15:79]-following[15:79]).mean()),
                                      "actual_interval_s":float(following[10]-now)}
        residual = abs(float(self.env.pile.mass()[0]+self.env.payload[0]+self.env.delivered[0]+self.env.spilled[0]-self.env.pile.initial_mass[0]))
        self.max_mass_residual = max(self.max_mass_residual,residual)
        if residual > 1e-7: raise AssertionError("material ledger differs")
        record.update(next_state=following.tolist(),reward=float(reward[0]),transfer={k:float(info["transfer"][k][0]) for k in ("loaded_kg","delivered_kg","spilled_kg")})
        self.records.append(record)
        if override:
            if len(self.records) == 1 or not self.records[-2]["supervision"]["override"]: self.slow = int(abs(record["state"][3]) <= .08)
            self.slow = self.slow+1 if abs(float(self.env.speed[0])) <= .08 else 0
            if self.settled is None and self.slow >= 3: self.settled = float(self.env.elapsed[0])
            if self.settled is not None and float(self.env.elapsed[0])-self.settled >= 10.-1e-8:
                self.finished = True; self.end_reason = "accepted_no_progress_hold" if progress_hold else "controlled_hold"
        else: self.slow = 0; self.settled = None
        if self.done: self.finished = True; self.end_reason = "environment_terminal"
        if self.finished and self.criterion != "delivery":
            result = stop_metrics(self.records,self.frame(),self.done)
            delay = .3 if self.family == "range_dropout" or self.pattern == "carry_loss" else .1
            if result: result["passed"] = bool(result["passed"] and result["hold_s"] >= 10.-1e-8 and result["detected_s"]-result["loss_s"] <= delay+1e-8)
            if self.criterion == "accepted_refusal": self.refusal_result = result
            else: self.stop_result = result
        return self.frame()

    def outcome(self):
        reason = str(self.env.reason[0]); collision = reason.startswith(("tunnel","obstacle"))
        return {"reason":reason,"done":self.done,"full_success":self.done and reason == "success","collision":collision,"decisions":self.decisions,
                "initial_payload_kg":0.,"delivered_kg":float(self.env.delivered[0]),"carried_kg":float(self.env.payload[0]),
                "spilled_kg":float(self.env.spilled[0]),"peak_load_kg":float(self.env.peak_load[0]),"cycle_s":float(self.env.elapsed[0]),
                "max_mass_residual_kg":self.max_mass_residual}

    def evaluation(self):
        passed = None
        if self.finished:
            metric = self.refusal_result if self.criterion == "accepted_refusal" else self.stop_result
            passed = bool(metric and metric["passed"] and not self.outcome()["collision"]) if self.criterion != "delivery" else self.outcome()["full_success"]
            if self.pattern == "recovery": passed &= bool(self.fault_start is not None and self.override_decisions and self.resumed)
        return {"criterion":self.criterion,"passed":passed,"stop":self.stop_result,"accepted_refusal":self.refusal_result,
                "override_decisions":self.override_decisions,"resumed":self.resumed,"fault_trigger_s":self.fault_start}

    def telemetry(self):
        record = self.records[-1] if self.records else None; obs = record["observation"] if record else {k:v[0].tolist() for k,v in self.env.observe().items()}
        p = obs["proprio"]; control = record["supervision"] if record else None
        return {"status":control["mode"] if control else "ready","owner":control["proposal_source"] if control else None,
                "sensor":{"fresh":bool(p[12]),"age_s":p[11],"valid_cells":int(np.asarray(obs["range_valid"]).sum()),"total_cells":25,
                          "usable":bool(p[12] and p[11] <= .2 and np.asarray(obs["range_valid"]).sum() >= 5)},
                "input_time_s":p[13],"task_time_s":control["task_time_s"] if control else p[13],
                "proposal":control["task_proposal"] if control else None,"applied_action":record["action"] if record else None,
                "override":bool(control and control["override"])}


class Session(PlaybackSession):
    def __init__(self,*,verification=False):
        configure_cpu(7,threads=1); self.admission = load_admission()
        self.runtime_receipt = None if verification else verify_runtime_receipt()
        self.runtime_sha = digest({name:sha((ROOT/name).read_bytes()) for name in ("training/kessel_lab/harvest_runtime.py","training/kessel_lab/harvest_admission.py",
            "training/kessel_lab/bootstrap_runtime.py","training/kessel_lab/server.py")}); self.playing = False; self.epoch = 0
        LockSession.__init__(self)

    def info(self):
        return {"families":[*FAMILIES,"prepared_no_progress"],"sources":list(SOURCES),"patterns":[None,*PATTERNS],
                "family_labels":{f:f.replace("_"," ").capitalize() for f in (*FAMILIES,"prepared_no_progress")},
                "supported_sources":{f:list(SOURCES) for f in (*FAMILIES,"prepared_no_progress")},
                "seed_min":19000,"seed_max":19999,"mode":"live_synthetic","forecast_source":"privileged_hybrid_shadow",
                "runtime_receipt_sha256":self.runtime_receipt,"in_process_verification_only":self.runtime_receipt is None,
                "qualification_sha256":self.admission["qualification_sha256"],"source_labels":{"learned_linear":"Fitted feedback with conventional planning","reference":"Conventional feedback and planning"}}

    def reset(self,body):
        seed = body.get("seed"); family = body.get("family"); source = body.get("source"); pattern = body.get("pattern")
        if isinstance(seed,bool) or not isinstance(seed,int) or not 19000 <= seed <= 19999: raise ValueError("use a practice seed from 19000 to 19999")
        if family not in (*FAMILIES,"prepared_no_progress") or source not in SOURCES: raise ValueError("choose a supported scenario and controller")
        if pattern is not None and (pattern not in PATTERNS or family != "nominal"): raise ValueError("input/recovery patterns are qualified with nominal scenarios only")
        run = LiveRun(family,seed,source,pattern,self.admission,self.runtime_sha)
        self.run = run; self.run_id = uuid.uuid4().hex; self.playing = False; self.epoch += 1
        return self.response([run.frame()])

    def response(self,frames):
        run = self.run
        return {"run_id":self.run_id,"identity":run.identity,"scenario":run.scenario,"family":run.family,"pattern":run.pattern,"source":run.source,
                "method":"qualified_harvest_with_shadow_forecast","checkpoint_sha256":self.admission["feedback_sha256"] if run.source == "learned_linear" else None,
                "forecast_checkpoint_sha256":self.admission["forecast_sha256"],"qualification_sha256":self.admission["qualification_sha256"],"runtime_sha256":self.runtime_sha,
                "mode":"live_synthetic","decision_s":.1,"frames":frames,"outcome":run.outcome(),"scenario_evaluation":run.evaluation(),"telemetry":run.telemetry(),
                "runtime_receipt_sha256":self.runtime_receipt,"in_process_verification_only":self.runtime_receipt is None,
                "playback":{"running":self.playing,"epoch":self.epoch,"finished":run.finished,"end_reason":run.end_reason},
                "initial_admission":run.initial_certificate,"control_description":"Saved fitted feedback with conventional planning and guards" if run.source == "learned_linear" else "Conventional feedback, planning and guards"}

    def export_trace(self):
        if not self.run: raise ValueError("start a run first")
        value = self.response(copy.deepcopy(self.run.records)+[self.run.frame()])
        value.update(applied_machine_commands=False,export_kind="executed_harvest_shadow_trace",forecast_influences_action=False)
        return value


class Handler(BaseHandler):
    STATIC = {"/docs/phase-11/harvest-demo/","/docs/phase-11/harvest-demo/index.html","/docs/phase-11/harvest-demo/viewer.js",
        "/docs/phase-11/harvest-demo/viewer.css","/docs/phase-11/harvest-demo/presentation.mjs","/docs/phase-11/harvest-qualification.md",
        "/docs/phase-11/qualified-demo/viewer.css","/docs/phase-11/qualified-demo/client.mjs"}

    def do_GET(self):
        if not self.valid_host(): return self.json(403,{"error":"loopback host required"})
        path = urlsplit(self.path).path
        if path in ("/","/docs/phase-11/live-demo/","/docs/phase-11/live-demo/index.html","/docs/phase-11/qualified-demo/","/docs/phase-11/qualified-demo/index.html"):
            self.send_response(302); self.send_header("Location","/docs/phase-11/harvest-demo/"); self.send_header("Content-Length","0"); self.end_headers(); return
        if path.startswith("/docs/phase-11/qualified-demo/") and path not in self.STATIC: return self.json(404,{"error":"use /docs/phase-11/harvest-demo/"})
        return super().do_GET()


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--port",type=int,default=8096); args = parser.parse_args()
    session = Session(); server = ThreadingHTTPServer(("127.0.0.1",args.port),Handler); server.session = session
    print(f"Harvest shadow simulator: http://127.0.0.1:{args.port}/docs/phase-11/harvest-demo/",flush=True); server.serve_forever()


if __name__ == "__main__": main()
