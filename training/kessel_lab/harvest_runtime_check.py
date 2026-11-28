"""Bounded in-process equivalence of new live sessions to frozen qualified control."""
import zipfile

from kessel_training.policy import configure_cpu
from .harvest_runtime import Session
from .linear_feedback import load
from .harvest_admission import FEEDBACK
from .runtime import ROOT, FAMILIES
from .start_rollout import run
from .study_tools import Budget, begin, retain, seal

D = ROOT/"docs/phase-11/harvest-live-evidence"


def execute():
    configure_cpu(7,threads=1); budget = Budget(360,environment=30000,teacher=15000,replay=0)
    paths = ["training/kessel_lab/"+name+".py" for name in ("harvest_admission","harvest_runtime","harvest_runtime_gate","harvest_runtime_check","bootstrap_runtime","server")]
    jobs = [(source,f,None) for source in ("reference","learned_linear") for f in (*FAMILIES,"prepared_no_progress")]
    jobs += [(source,"nominal",p) for source in ("reference","learned_linear") for p in ("recovery","carry_loss","stale_clearance","old_clearance","missing_clearance")]
    plan = begin(D,"docs/adr/0086-qualified-harvest-live-integration.md",paths,{"kind":"harvest-live-equivalence-v1","jobs":jobs,"seed":19020,"browsers_started":0,"sockets_bound":0})
    report = {"plan":plan,"cases":[],"complete":False,"errors":[],"budget_stop":None,"machine_commands":False}
    try:
        session = Session(verification=True)
        with zipfile.ZipFile(D/"traces.zip","w",compression=zipfile.ZIP_STORED) as archive:
            for index,(source,family,pattern) in enumerate(jobs):
                session.reset({"family":family,"seed":19020,"source":source,"pattern":pattern})
                while not session.run.finished:
                    budget.charge("environment"); session.step({"run_id":session.run_id,"after":session.run.decisions})
                model,_ = load(FEEDBACK)
                reference = run(family,19020,budget,pattern,actuator=model.action if source == "learned_linear" else None)
                live = session.export_trace(); frames = live["frames"]
                assert len(frames) == len(reference["frames"])
                for f,g in zip(frames,reference["frames"]):
                    assert f["state"] == g["state"]
                    if "action" not in f: continue
                    assert f["action"] == g["action"] and f["observation"] == g["observation"] and f["supervision"] == g["supervision"]
                    assert not f["forecast"]["influences_action"] and f["forecast"]["produced_at_s"] == f["t_s"]
                assert live["outcome"] == reference["outcome"] or all(live["outcome"][k] == reference["outcome"][k] for k in live["outcome"])
                assert live["scenario_evaluation"]["passed"]
                report["cases"].append({"source":source,"family":family,"pattern":pattern,"decisions":session.run.decisions,"evaluation":live["scenario_evaluation"],
                    "outcome":live["outcome"],"equivalent_to_frozen_control":True,**retain(archive,f"{index:02}.json.gz",live)})
                print("live equivalence",source,family,pattern,session.run.decisions,flush=True)
        report["complete"] = len(report["cases"]) == 38
        report["max_state_error"] = report["max_action_error"] = report["max_observation_error"] = 0.
    except TimeoutError as error: report["budget_stop"] = str(error)
    except Exception as error: report["errors"].append(type(error).__name__+": "+str(error))
    report["cost"] = budget.report(); seal(D,report); print("live evidence",report["complete"],report["errors"],report["cost"],flush=True)
    if not report["complete"] or report["errors"] or report["budget_stop"]: raise SystemExit(1)


if __name__ == "__main__": execute()
