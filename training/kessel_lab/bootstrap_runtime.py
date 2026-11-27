"""Qualified stopping service. Importing this module binds no socket or browser."""
import argparse
import copy
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlsplit
import uuid
import zipfile

import numpy as np
import torch
from kessel_training.policy import configure_cpu
from kessel_training.wm_state import pack
from .bootstrap_hold import METHOD
from .bootstrap_hold_pilot import make_run, SpatialFault, stopping
from .bootstrap_qualification import admitted
from .range_contract import canonicalize
from .runtime import ROOT, digest
from .server import Handler as BaseHandler, Session as BaseSession

D = ROOT/"docs/phase-11/bootstrap-qualification-evidence"
REPORT = D/"report.json"
FAMILIES = ("healthy","partial_carry_zeroed","carry_loss","recovery")
SOURCES = tuple(METHOD+"-"+str(p) for p in (7,19,41))+tuple("phase_memory-"+str(p) for p in (7,19,41))
LABELS = {"healthy":"Healthy range: deliver", "partial_carry_zeroed":"Partial range: stop and hold",
          "carry_loss":"Complete range loss: stop and hold", "recovery":"Range returns: recover and deliver"}
QUALIFIED = set(SOURCES[:3])


def sha(raw): return hashlib.sha256(raw).hexdigest()


def verify_qualification(report):
    try:
        if not report.get("admitted") or not admitted(report.get("cases",[]),report.get("complete",False),report.get("healthy_exact",False)):
            raise ValueError("every qualification seed/family must pass")
        if report["budget_stop"] is not None or any(report[k] != 0 for k in
                ("max_state_error","max_action_error","max_observation_error","teacher_queries","optimiser_updates")):
            raise ValueError("qualification has errors, training or an exhausted budget")
        if report["physics_replay_cases"] != 96 or report["action_replay_cases"] != 120 or report["held_out_cases"] != 120:
            raise ValueError("qualification replay/coverage is incomplete")
        cases = report["cases"]; decisions = sum(c["decisions"] for c in cases)
        physical = sum(c["decisions"] for c in cases if c["method"] == METHOD)
        if not (decisions == report["environment_decisions"] == report["neural_queries"] == report["action_replay_queries"] <= 71400
                and physical == report["physics_replay_decisions"] <= 57600 and 0 <= report["active_wall_s"] <= 400):
            raise ValueError("qualification cost ledger differs")
        if not all(c["weights_unchanged"] for c in cases): raise ValueError("qualified weights changed")
        software = report["plan"]["software"]
        if software["numpy"] != np.__version__ or software["torch"].split("+")[0] != str(torch.__version__).split("+")[0]:
            raise ValueError("numerical library releases differ from qualification")
        required = {str(p.relative_to(ROOT)) for p in (ROOT/"training/kessel_training").glob("*.py")}
        required |= {"training/kessel_lab/"+name+".py" for name in ("runtime","range_supervisor","range_contract","range_pilot",
            "bootstrap_hold_pilot","bootstrap_qualification","motion_hold","bootstrap_hold","reserve_bootstrap_replacement","reserve_bootstrap")}
        required |= {"training/uv.lock","docs/phase-11/phase-memory-evidence/selection.json"}
        required |= {"docs/adr/"+name+".md" for name in ("0066-spatial-range-contract-and-pilot","0068-observed-motion-holding-pilot",
            "0069-bootstrap-motion-holding-pilot","0070-bootstrap-hold-fresh-qualification","0071-fresh-qualification-logging-erratum")}
        required |= {"docs/phase-11/bootstrap-qualification-evidence/"+name+".json" for name in
                     ("reservation-corrected","reservation","reservation-replacement")}
        if set(report["plan"]["files"]) != required: raise ValueError("qualified source inventory differs")
        for name,expected_sha in report["plan"]["files"].items():
            if sha((ROOT/name).read_bytes()) != expected_sha: raise ValueError("qualified source changed: "+name)
        certificate = D/"reservation-corrected.json"
        if sha(certificate.read_bytes()) != report["plan"]["reservation_sha256"]: raise ValueError("reservation identity differs")
        selection = json.loads((ROOT/"docs/phase-11/phase-memory-evidence/selection.json").read_text())
        if any(c["checkpoint_sha256"] != selection[c["source"]]["sha256"] for c in cases):
            raise ValueError("checkpoint selection differs")
    except (KeyError,TypeError,AttributeError) as error:
        raise ValueError("incomplete qualification record") from error


def load_qualification():
    raw = REPORT.read_bytes(); report = json.loads(raw)
    manifest = json.loads((D/"files.json").read_text())
    if sha(raw) != manifest[REPORT.relative_to(ROOT).as_posix()]: raise ValueError("qualification report changed")
    verify_qualification(report)
    for name,key in (("traces.zip","trace_archive_sha256"),("source.zip","source_archive_sha256")):
        if sha((D/name).read_bytes()) != report[key]: raise ValueError("qualification archive changed: "+name)
    with zipfile.ZipFile(D/"source.zip") as z:
        if set(z.namelist()) != set(report["plan"]["files"]): raise ValueError("source capsule inventory differs")
        for name,expected_sha in report["plan"]["files"].items():
            if sha(z.read(name)) != expected_sha: raise ValueError("source capsule changed: "+name)
    return report,sha(raw)


def control_status(record):
    supervision = record.get("supervision")
    if supervision is None: return "neural"
    if not supervision["override"]: return "neural"
    if supervision["health"]["usable"]: return "recovering"
    return supervision["mode"]


class LiveRun:
    def __init__(self, family, seed, source, qualification_sha, runtime_sha):
        supervised = source in QUALIFIED
        self.job = {"source":"phase_memory-"+source.rsplit("-",1)[1],"seed":seed,
                    "method":METHOD if supervised else "original","kind":"task","pattern":family,
                    "criterion":"stop" if family in ("partial_carry_zeroed","carry_loss") else "delivery"}
        self.base = make_run(self.job); self.injector = SpatialFault(family)
        self.source = source; self.finished = False; self.end_reason = None
        self.loss_sampled = False; self.slow_streak = 0; self.settled_at = None
        self.stop_result = None; self.override_decisions = 0; self.resumed = False; self.previous_override = False
        self.identity = digest({"job":self.job,"public_source":source,"base":self.base.identity,
                                "qualification_sha256":qualification_sha,"runtime_sha256":runtime_sha})

    def frame(self):
        frame = self.base.frame(); frame["step_index"] = self.base.decisions
        frame["last_action"] = self.base.records[-1]["action"] if self.base.records else None
        return frame

    def step(self):
        if self.finished: raise ValueError("run finished; start a new run")
        run = self.base; actual = run.env.observe(); observed,fault = self.injector.apply(actual)
        action = run.actor.act(observed); record = run.frame()
        supervision = copy.deepcopy(run.actor.last) if self.job["method"] == METHOD else None
        record.update(observation={k:v[0].tolist() for k,v in observed.items()},
                      actual_observation={k:v[0].tolist() for k,v in actual.items()},fault=fault,
                      supervision=supervision,action=action[0].tolist())
        _,reward,term,trunc,info = run.env.step(action)
        run.decisions += 1; run.done = bool((term|trunc)[0])
        residual = abs(float((run.env.pile.mass()+run.env.payload+run.env.delivered+run.env.spilled-run.env.pile.initial_mass)[0]))
        if residual > 1e-7: raise AssertionError("material ledger differs")
        run.max_mass_residual = max(run.max_mass_residual,residual)
        record.update(next_state=pack(run.env)[0].tolist(),reward=float(reward[0]),
                      transfer={k:float(info["transfer"][k][0]) for k in ("loaded_kg","delivered_kg","spilled_kg")})
        run.records.append(record)
        overridden = bool(supervision and supervision["override"])
        self.override_decisions += overridden
        self.resumed |= self.previous_override and not overridden
        self.previous_override = overridden
        if self.job["criterion"] == "stop" and fault["active"]:
            if not self.loss_sampled:
                self.slow_streak = int(abs(record["state"][3]) <= .08); self.loss_sampled = True
            self.slow_streak = self.slow_streak+1 if abs(float(run.env.speed[0])) <= .08 else 0
            if self.settled_at is None and self.slow_streak >= 3: self.settled_at = float(run.env.elapsed[0])
            if self.settled_at is not None and float(run.env.elapsed[0])-self.settled_at >= 10.-1e-8:
                self.stop_result = stopping(run.records,run.frame(),run.done)
                self.finished = True
                self.end_reason = "hold_window_passed" if self.stop_result and self.stop_result["passed"] else "hold_window_failed"
        if run.done:
            self.finished = True; self.end_reason = "environment_terminal"
            if self.job["criterion"] == "stop": self.stop_result = stopping(run.records,run.frame(),True)
        return self.frame()

    def evaluation(self):
        passed = None
        if self.finished:
            passed = bool(self.stop_result and self.stop_result["passed"] and not self.base.outcome()["collision"]) if self.job["criterion"] == "stop" else self.base.outcome()["full_success"]
            if self.job["pattern"] != "healthy": passed = passed and self.injector.started is not None
            if self.job["pattern"] == "recovery": passed = passed and self.override_decisions > 0 and self.resumed
        return {"criterion":self.job["criterion"],"passed":passed,"trigger_reached":self.injector.started is not None,
                "override_decisions":self.override_decisions,"resumed":self.resumed,"stop":self.stop_result}

    def telemetry(self):
        record = self.base.records[-1] if self.base.records else None
        observed = record["observation"] if record else {k:v[0].tolist() for k,v in self.base.env.observe().items()}
        canonical,health = canonicalize({k:np.asarray([v]) for k,v in observed.items()})
        p = observed["proprio"]; supervision = record["supervision"] if record else None
        action = record["action"] if record else None
        return {"status":control_status(record) if record else "ready",
                "owner":"conventional_supervisor" if supervision and supervision["override"] else "neural_policy" if record else None,
                "input_time_s":p[13],"task_time_s":supervision["task_elapsed_s"] if supervision else p[13],
                "sensor":{"kind":health["kind"],"usable":health["usable"],"fresh":bool(p[12]),"age_s":p[11],
                          "valid_cells":int(canonical["range_valid"].sum()),"total_cells":25},
                "neural_proposal":supervision["neural_proposal"] if supervision else action,
                "applied_action":action,"observer":supervision["observer"] if supervision else None,
                "fault":record["fault"] if record else {"active":False,"started_s":None,"trigger_phase":0}}


class Session(BaseSession):
    def __init__(self):
        configure_cpu(7,threads=1)
        self.qualification,self.qualification_sha = load_qualification()
        self.runtime_sha = sha(Path(__file__).read_bytes())
        self.playing = False; self.epoch = 0
        super().__init__()

    def info(self):
        return {"families":list(FAMILIES),"sources":list(SOURCES),"family_labels":LABELS,
                "source_labels":{s:("Neural policy + stopping supervisor" if s in QUALIFIED else "Original neural policy")+" / seed "+s.rsplit("-",1)[1] for s in SOURCES},
                "supported_sources":{f:list(SOURCES) if f == "healthy" else list(SOURCES[:3]) for f in FAMILIES},
                "seed_min":19000,"seed_max":19999,"mode":"live_synthetic","qualification_sha256":self.qualification_sha}

    def reset(self, body):
        seed = body.get("seed"); family = body.get("family"); source = body.get("source")
        if isinstance(seed,bool) or not isinstance(seed,int) or not 19000 <= seed <= 19999:
            raise ValueError("interactive seeds are restricted to practice range 19000–19999")
        if not isinstance(family,str) or family not in FAMILIES or not isinstance(source,str) or source not in SOURCES:
            raise ValueError("choose a supported qualified scenario and controller")
        if source not in QUALIFIED and family != "healthy": raise ValueError("original comparators support healthy range only")
        run = LiveRun(family,seed,source,self.qualification_sha,self.runtime_sha)
        self.run = run; self.run_id = uuid.uuid4().hex; self.playing = False; self.epoch += 1
        return self.response([run.frame()])

    def require_run(self, body, counter=False):
        if not self.run or body.get("run_id") != self.run_id: raise ValueError("stale run; start or reconnect to a run")
        after = body.get("after")
        if counter and (isinstance(after,bool) or not isinstance(after,int) or after != self.run.base.decisions):
            raise ValueError("stale decision counter; no steps executed")

    def play(self, body):
        self.require_run(body,counter=True)
        if self.run.finished: raise ValueError("run finished; start a new run")
        if not self.playing: self.epoch += 1
        self.playing = True
        return self.response([self.run.frame()])

    def pause(self, body):
        self.require_run(body); self.playing = False; self.epoch += 1
        return self.response([self.run.frame()])

    def step(self, body):
        self.require_run(body,counter=True)
        count = body.get("steps",1); automatic = body.get("automatic",False)
        if isinstance(count,bool) or not isinstance(count,int) or not 1 <= count <= 10: raise ValueError("steps must be 1–10")
        if not isinstance(automatic,bool): raise ValueError("automatic must be boolean")
        if automatic:
            epoch = body.get("playback_epoch")
            if not self.playing or isinstance(epoch,bool) or not isinstance(epoch,int) or epoch != self.epoch:
                raise ValueError("stale playback request; no steps executed")
        elif self.playing: raise ValueError("pause before stepping manually")
        frames = []
        for _ in range(count):
            if self.run.finished: break
            frames.append(self.run.step())
        if self.run.finished and self.playing: self.playing = False; self.epoch += 1
        return self.response(frames)

    def response(self, frames):
        live = self.run; run = live.base
        return {"run_id":self.run_id,"identity":live.identity,"scenario":run.scenario,"family":live.job["pattern"],
                "source":live.source,"method":live.job["method"],"checkpoint_sha256":run.checkpoint_sha256,
                "qualification_sha256":self.qualification_sha,"runtime_sha256":self.runtime_sha,
                "mode":"live_synthetic","decision_s":run.env.loader.decision_s,"frames":frames,"outcome":run.outcome(),
                "playback":{"running":self.playing,"epoch":self.epoch,"finished":live.finished,"end_reason":live.end_reason},
                "scenario_evaluation":live.evaluation(),"telemetry":live.telemetry(),
                "control_description":"Neural policy with conventional phase memory and stopping supervisor" if live.source in QUALIFIED else "Original neural policy with conventional phase memory"}

    def export_trace(self):
        if not self.run: raise ValueError("start a run first")
        value = self.response(copy.deepcopy(self.run.base.records)+[self.run.frame()])
        value.update(applied_machine_commands=False,export_kind="executed_synthetic_trace")
        return value


class Handler(BaseHandler):
    STATIC = {"/docs/phase-11/qualified-demo/","/docs/phase-11/qualified-demo/index.html",
              "/docs/phase-11/qualified-demo/viewer.js","/docs/phase-11/qualified-demo/viewer.css",
              "/docs/phase-11/qualified-demo/client.mjs","/docs/phase-11/qualified-demo/presentation.mjs",
              "/docs/phase-11/bootstrap-qualification.md"}

    def do_GET(self):
        if not self.valid_host(): return self.json(403,{"error":"loopback host required"})
        path = urlsplit(self.path).path
        if path in ("/docs/phase-11/live-demo/","/docs/phase-11/live-demo/index.html"):
            self.send_response(302); self.send_header("Location","/docs/phase-11/qualified-demo/")
            self.send_header("Content-Length","0"); self.end_headers(); return
        if path == "/api/info": return self.json(200,self.server.session.info())
        if path in ("/api/state","/api/export"):
            with self.server.session.lock:
                s = self.server.session
                if not s.run: return self.json(409,{"error":"start a run first"})
                return self.json(200,s.export_trace() if path == "/api/export" else s.response([s.run.frame()]))
        if path in self.STATIC: return SimpleHTTPRequestHandler.do_GET(self)
        return super().do_GET()

    def do_POST(self):
        origin = self.headers.get("Origin")
        if not self.valid_host() or origin is not None and origin not in (f"http://127.0.0.1:{self.server.server_port}",f"http://localhost:{self.server.server_port}"):
            return self.json(403,{"error":"same-origin loopback request required"})
        if self.headers.get("Content-Type") != "application/json": return self.json(415,{"error":"application/json required"})
        try:
            length = int(self.headers.get("Content-Length","0"))
            if not 0 < length <= 2048: raise ValueError("request body must be 1–2048 bytes")
            body = json.loads(self.rfile.read(length))
            if not isinstance(body,dict): raise ValueError("JSON object required")
            actions = {"/api/reset":"reset","/api/play":"play","/api/pause":"pause","/api/step":"step"}
            if self.path not in actions: return self.json(404,{"error":"unknown endpoint"})
            with self.server.session.lock: result = getattr(self.server.session,actions[self.path])(body)
            return self.json(200,result)
        except (ValueError,KeyError,TypeError) as error: return self.json(400,{"error":str(error)})


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument("--port",type=int,default=8095); args = p.parse_args()
    session = Session()  # Validate evidence before binding.
    server = ThreadingHTTPServer(("127.0.0.1",args.port),Handler); server.session = session
    print(f"Qualified synthetic simulator: http://127.0.0.1:{args.port}/docs/phase-11/qualified-demo/",flush=True)
    server.serve_forever()


if __name__ == "__main__": main()
