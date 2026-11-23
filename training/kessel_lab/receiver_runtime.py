"""Optional qualified receiver-frame service. Importing it starts no process or browser."""
import argparse
import hashlib
from http.server import ThreadingHTTPServer
import json
from urllib.parse import urlsplit

from kessel_training.evaluate import source_identity
from kessel_training.policy import configure_cpu
from .receiver_frame import METHOD, ReceiverFrameActor
from .receiver_qualification import SEEDS, admitted
from .runtime import ROOT, digest
from .server import Handler as BaseHandler, Session as BaseSession

REPORT = ROOT / "docs/phase-11/receiver-evidence/qualification.json"
SOURCES = tuple(METHOD+"-"+str(seed) for seed in (7,19,41)) + ("reference",)
FAMILIES = ("nominal","receiver_far")


def verify_qualification(report):
    if not report.get("admitted") or not admitted(report.get("cases",[]),report.get("complete",False)):
        raise ValueError("receiver-frame method has not passed every seed/family gate")
    expected={(family,seed,source,method) for family in FAMILIES for seed in SEEDS
              for source,method in [*(("phase_memory-"+str(s),m) for s in (7,19,41)
                                      for m in ("original",METHOD)),("reference","reference")]}
    actual={(c["family"],c["seed"],c["source"],c["method"]) for c in report["cases"]}
    if actual!=expected or len(report["cases"])!=112:raise ValueError("qualification coverage differs")
    if report["adapted_physical_replay_cases"]!=48 or report["learned_action_replay_cases"]!=96:
        raise ValueError("independent replay is incomplete")
    if report["max_state_error"] or report["max_action_error"] or report["budget_stop"]:
        raise ValueError("qualification verification failed")
    if report["teacher_training_queries"] or report["optimiser_updates"]:
        raise ValueError("unexpected training during qualification")
    if report["plan"]["source"]["package_sha256"]!=source_identity()["package_sha256"]:
        raise ValueError("reference source changed since qualification")
    if not 0<=report["evaluation_decisions"]<=67200 or not 0<=report["physics_replay_decisions"]<=28800:
        raise ValueError("qualification decision budget differs")
    if not 0<=report["active_wall_s"]<=420:
        raise ValueError("qualification execution budget differs")
    required={"training/kessel_lab/runtime.py","training/kessel_lab/receiver_frame.py",
              "training/kessel_lab/receiver_qualification.py","docs/adr/0064-receiver-frame-qualification.md",
              "docs/phase-11/phase-memory-evidence/selection.json"}
    if set(report["plan"]["files"])!=required:
        raise ValueError("qualification source inventory differs")
    for name,sha in report["plan"]["files"].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=sha:
            raise ValueError("qualified source changed: "+name)


class Session(BaseSession):
    def __init__(self):
        raw=REPORT.read_bytes()
        self.qualification=json.loads(raw)
        verify_qualification(self.qualification)
        trace=ROOT/"docs/phase-11/receiver-evidence/qualification-traces.zip"
        if hashlib.sha256(trace.read_bytes()).hexdigest()!=self.qualification["trace_archive_sha256"]:
            raise ValueError("qualification traces changed")
        self.qualification_sha256=hashlib.sha256(raw).hexdigest()
        self.adapter_sha256=self.qualification["plan"]["files"]["training/kessel_lab/receiver_frame.py"]
        super().__init__()

    def reset(self,body):
        source=body.get("source")
        if source not in SOURCES or body.get("family") not in FAMILIES:
            raise ValueError("receiver runtime supports qualified nominal/far families and explicit sources only")
        if source=="reference":return super().reset(body)
        base={**body,"source":"phase_memory-"+source.rsplit("-",1)[1]}
        super().reset(base)  # Retains practice-seed and input validation.
        self.run.actor=ReceiverFrameActor(self.run.actor)
        self.run.source=source
        self.run.identity=digest({"base_run":self.run.identity,"method":METHOD,
                                  "adapter_sha256":self.adapter_sha256,
                                  "qualification_sha256":self.qualification_sha256})
        return self.response([self.run.frame()])

    def response(self,frames):
        result=super().response(frames)
        result.update(qualification_sha256=self.qualification_sha256,
                      adapter_sha256=self.adapter_sha256 if self.run.source!="reference" else None)
        if self.run.source!="reference":
            result["control_description"]="Neural controls with rule-based phase memory and receiver-frame inputs. Qualified only for nominal/far synthetic cases"
        return result


class Handler(BaseHandler):
    def do_GET(self):
        if not self.valid_host():return self.json(403,{"error":"loopback host required"})
        path=urlsplit(self.path).path
        if path=="/api/info":
            return self.json(200,{"families":FAMILIES,"sources":SOURCES,"seed_min":19000,
                                  "seed_max":19999,"mode":"live_synthetic"})
        if path=="/api/export":
            with self.server.session.lock:
                session=self.server.session;run=session.run
                if run is None:return self.json(409,{"error":"start a run first"})
                value=session.response(run.records+[run.frame()])
                value.update(applied_machine_commands=False)
                return self.json(200,value)
        return super().do_GET()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--port",type=int,default=8094);args=p.parse_args()
    configure_cpu(7,threads=1)
    session=Session()  # Fails before binding if the evidence does not qualify.
    server=ThreadingHTTPServer(("127.0.0.1",args.port),Handler);server.session=session
    print("Receiver-frame simulator: http://127.0.0.1:"+str(args.port)+"/docs/phase-11/live-demo/",flush=True)
    server.serve_forever()


if __name__=="__main__":
    main()
