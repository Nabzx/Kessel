"""Isolated sensor-only inspection; failed predictor gates never change control."""
import argparse
import copy
from http.server import ThreadingHTTPServer
from urllib.parse import urlsplit
import uuid

import numpy as np

from kessel_training.wm_state import pack
from .harvest_runtime import LiveRun as BaseRun, Session as BaseSession, Handler as BaseHandler, PATTERNS, SOURCES
from .harvest_runtime_gate import verify_runtime_receipt
from .range_pilot import stop_metrics
from .runtime import ROOT, FAMILIES, digest
from .start_rollout import clearance_packet
from .sensor_model import load, flatten
from .sensor_runtime_gate import MODEL, load_sensor_receipt, verify_sensor_runtime, runtime_hash


class SensorRun(BaseRun):
    def __init__(self,family,seed,source,pattern,admission,runtime_sha,sensor_receipt):
        super().__init__(family,seed,source,pattern,admission,runtime_sha)
        self.forecaster,_ = load(MODEL); self.sensor_receipt = sensor_receipt
        self.previous_observation = self.previous_action = None
        self.identity = digest({"base":self.identity,"sensor_receipt":sensor_receipt})

    def sensor_snapshot(self):
        actual = self.env.observe(); observed = {k:v.copy() for k,v in actual.items()}; now = float(self.env.elapsed[0])
        start = self.fault_start
        if self.pattern in ("recovery","carry_loss") and start is None and self.actor.task.mode == "carry" and actual["proprio"][0,4] <= -.5:
            start = now
        injected = start is not None and (self.pattern != "recovery" or now-start < 2.-1e-8)
        if injected:
            observed["range_valid"][:] = 0; observed["proprio"][0,12] = 0; observed["proprio"][0,11] = now-start+.1
        return actual,observed,now,start,injected

    def frame(self):
        frame = super().frame()
        frame["observation"] = {k:v[0].tolist() for k,v in self.sensor_snapshot()[1].items()}
        return frame

    def step(self):
        if self.finished: raise ValueError("run finished; start a new run")
        actual,observed,now,fault_start,injected = self.sensor_snapshot()
        self.fault_start = fault_start
        packet = clearance_packet(self.env,self.pattern); action = self.actor.act(observed,packet)
        override = self.actor.last["override"]; self.override_decisions += override
        self.resumed |= self.previous_override and not override; self.previous_override = override
        progress_hold = self.actor.last["proposal_source"] == "conventional_initial_no_progress_hold"
        active = bool(injected or self.family == "range_dropout" or not self.actor.last["clearance"]["usable"] or progress_hold)
        if active and self.loss_start is None: self.loss_start = now
        record = self.frame()
        prediction = self.forecaster.predict(observed,action,self.previous_observation,self.previous_action)
        q = prediction["observation"][0]
        input_usable = bool(prediction["input_usable"][0])
        accepted = bool(self.sensor_receipt["gate_passed"] and self.family in self.sensor_receipt["supported_families"] and input_usable and prediction["disagreement"][0] <= self.sensor_receipt["threshold"])
        forecast = {"source":"sensor_observation_residual_ensemble","produced_at_s":now,"for_decision":self.decisions,
                    "nominal_horizon_s":.1,"observation":{"proprio":q[:15].tolist(),"local_height_m":q[15:40].reshape(5,5).tolist(),"range_valid_probability":q[40:65].reshape(5,5).tolist()},
                    "render_pose":[float(q[0]),float(q[1]),float(np.arctan2(q[2],q[3])),*q[4:8].tolist()],
                    "disagreement":float(prediction["disagreement"][0]),"accepted":accepted,"input_usable":input_usable,
                    "model_gate_passed":self.sensor_receipt["gate_passed"],"experimental":not accepted,"privileged_inputs":False,
                    "previous_input_time_s":None if self.previous_observation is None else float(self.previous_observation["proprio"][0,13]),
                    "known_priors":prediction["known_priors"],"influences_action":False}
        self.previous_observation = {k:v.copy() for k,v in observed.items()}; self.previous_action = action.copy()
        record.update(observation={k:v[0].tolist() for k,v in observed.items()},actual_observation={k:v[0].tolist() for k,v in actual.items()},
                      clearance=packet,supervision=copy.deepcopy(self.actor.last),action=action[0].tolist(),forecast=forecast,
                      fault={"active":active,"started_s":self.loss_start,"injected":injected,"cause":"initial_no_progress" if progress_hold else "sensor_or_clearance"})
        _,reward,term,trunc,info = self.env.step(action); self.done = bool((term|trunc)[0]); self.decisions += 1
        following = pack(self.env)[0]
        _,received,next_time,_,_ = self.sensor_snapshot(); target = flatten(received)[0]
        interval = next_time-now; mask = target[40:65]; valid = int(mask.sum())
        forecast["actual_interval_s"] = interval
        forecast["measured_error"] = None if abs(interval-.1) > 1e-7 else {
            "position_m":float(np.linalg.norm(q[:2]-target[:2])),"carried_kg":float(abs(q[8]-target[8])),
            "speed_m_s":float(abs(q[4]-target[4])),"valid_height_mae_m":float((abs(q[15:40]-target[15:40])*mask).sum()/valid) if valid else None,
            "target_valid_cells":valid,"validity_brier":float(((q[40:65]-mask)**2).mean())}
        forecast["comparison_scope"] = "next_received_numeric_observation" if forecast["measured_error"] is not None else "partial_interval_outside_sensor_horizon"
        record["next_observation"] = {k:v[0].tolist() for k,v in received.items()}
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


class Session(BaseSession):
    def __init__(self,*,verification=False):
        super().__init__(verification=verification)
        self.sensor_receipt = load_sensor_receipt()
        self.sensor_runtime_receipt = None if verification else verify_sensor_runtime()
        self.runtime_sha = runtime_hash()

    def info(self):
        value = super().info()
        value.update(forecast_source="sensor_observation_residual_ensemble",sensor_model_gate_passed=self.sensor_receipt["gate_passed"],
                     sensor_study_sha256=self.sensor_receipt["report_sha256"],sensor_runtime_receipt_sha256=self.sensor_runtime_receipt,
                     forecast_qualification="failed; experimental inspection only")
        return value

    def reset(self,body):
        seed = body.get("seed"); family = body.get("family"); source = body.get("source"); pattern = body.get("pattern")
        if isinstance(seed,bool) or not isinstance(seed,int) or not 19000 <= seed <= 19999: raise ValueError("use a practice seed from 19000 to 19999")
        if family not in (*FAMILIES,"prepared_no_progress") or source not in SOURCES: raise ValueError("choose a supported scenario and controller")
        if pattern is not None and (pattern not in PATTERNS or family != "nominal"): raise ValueError("input/recovery patterns are qualified with nominal scenarios only")
        run = SensorRun(family,seed,source,pattern,self.admission,self.runtime_sha,self.sensor_receipt)
        self.run = run; self.run_id = uuid.uuid4().hex; self.playing = False; self.epoch += 1
        return self.response([run.frame()])

    def response(self,frames):
        value = super().response(frames)
        value.update(method="qualified_control_with_experimental_sensor_forecast",forecast_checkpoint_sha256=self.sensor_receipt["checkpoint_sha256"],
                     sensor_model_gate_passed=self.sensor_receipt["gate_passed"],sensor_study_sha256=self.sensor_receipt["report_sha256"],
                     sensor_runtime_receipt_sha256=self.sensor_runtime_receipt,forecast_qualification="failed; experimental inspection only")
        return value

    def export_trace(self):
        value = super().export_trace(); value["export_kind"] = "executed_experimental_sensor_forecast_trace"
        return value


class Handler(BaseHandler):
    STATIC = {"/docs/phase-11/sensor-demo/","/docs/phase-11/sensor-demo/index.html","/docs/phase-11/sensor-demo/viewer.js",
              "/docs/phase-11/sensor-demo/presentation.mjs","/docs/phase-11/harvest-demo/viewer.css",
              "/docs/phase-11/qualified-demo/viewer.css","/docs/phase-11/qualified-demo/client.mjs","/docs/phase-11/sensor-forecasts.md"}

    def do_GET(self):
        if not self.valid_host(): return self.json(403,{"error":"loopback host required"})
        path = urlsplit(self.path).path
        if path in ("/","/docs/phase-11/harvest-demo/","/docs/phase-11/harvest-demo/index.html","/docs/phase-11/qualified-demo/","/docs/phase-11/qualified-demo/index.html","/docs/phase-11/live-demo/","/docs/phase-11/live-demo/index.html"):
            self.send_response(302); self.send_header("Location","/docs/phase-11/sensor-demo/"); self.send_header("Content-Length","0"); self.end_headers(); return
        if path.startswith("/docs/phase-11/harvest-demo/") and path not in self.STATIC: return self.json(404,{"error":"use /docs/phase-11/sensor-demo/"})
        return super().do_GET()


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--port",type=int,default=8097); args = parser.parse_args()
    session = Session(); server = ThreadingHTTPServer(("127.0.0.1",args.port),Handler); server.session = session
    print(f"Experimental sensor inspection: http://127.0.0.1:{args.port}/docs/phase-11/sensor-demo/",flush=True); server.serve_forever()


if __name__ == "__main__": main()
