"""Complete in-process control equivalence for the experimental sensor wrapper."""
import zipfile

from kessel_training.policy import configure_cpu
from .harvest_runtime import LiveRun
from .sensor_runtime import Session
from .runtime import ROOT, FAMILIES
from .study_tools import Budget, begin, retain, seal

D = ROOT/"docs/phase-11/sensor-live-evidence"


def charge(budget,key):
    if sum(budget.counts.values()) >= 30000: raise TimeoutError("combined_physical_cap")
    budget.charge(key)


def execute():
    configure_cpu(7,threads=1); budget = Budget(360,environment=30000,replay=30000)
    names = ("sensor_runtime","sensor_runtime_gate","sensor_runtime_check","sensor_model","sensor_records","harvest_runtime","harvest_runtime_gate","harvest_admission","bootstrap_runtime","server")
    paths = ["training/kessel_lab/"+n+".py" for n in names]+["scripts/verify-sensor-forecast.py"]
    jobs = [(s,f,None) for s in ("reference","learned_linear") for f in (*FAMILIES,"prepared_no_progress")]
    jobs += [(s,"nominal",p) for s in ("reference","learned_linear") for p in ("recovery","carry_loss","stale_clearance","old_clearance","missing_clearance")]
    plan = begin(D,"docs/adr/0090-experimental-sensor-live-inspection.md",paths,{"kind":"sensor-live-control-equivalence-v1","jobs":jobs,"seed":19020,"browsers_started":0,"sockets_bound":0})
    r = {"plan":plan,"cases":[],"complete":False,"errors":[],"budget_stop":None,"machine_commands":False,"model_assisted_actions":0,"sensor_model_gate_passed":False}
    try:
        session = Session(verification=True)
        with zipfile.ZipFile(D/"traces.zip","w",compression=zipfile.ZIP_STORED) as archive:
            for i,(source,family,pattern) in enumerate(jobs):
                session.reset({"family":family,"seed":19020,"source":source,"pattern":pattern})
                while not session.run.finished:
                    charge(budget,"environment"); session.step({"run_id":session.run_id,"after":session.run.decisions})
                reference = LiveRun(family,19020,source,pattern,session.admission,"frozen_control_comparison")
                live = session.export_trace(); frames = live["frames"]
                for f in frames[:-1]:
                    charge(budget,"replay"); reference.step(); g = reference.records[-1]
                    for key in ("state","next_state","action","observation","actual_observation","supervision","fault","transfer","reward"):
                        assert f[key] == g[key],key
                    forecast = f["forecast"]
                    assert not forecast["influences_action"] and not forecast["privileged_inputs"] and not forecast["accepted"]
                    assert forecast["produced_at_s"] == f["t_s"]
                assert reference.finished and reference.outcome() == live["outcome"] and reference.evaluation() == live["scenario_evaluation"]
                assert live["scenario_evaluation"]["passed"]
                r["cases"].append({"source":source,"family":family,"pattern":pattern,"decisions":session.run.decisions,
                    "evaluation":live["scenario_evaluation"],"outcome":live["outcome"],"equivalent_to_frozen_control":True,**retain(archive,f"{i:02}.json.gz",live)})
                print("sensor live equivalence",source,family,pattern,session.run.decisions,flush=True)
        r["complete"] = len(r["cases"]) == 38
        if sum(p.stat().st_size for p in D.rglob("*") if p.is_file()) > 64*1024**2: raise TimeoutError("artifact_cap")
    except TimeoutError as error: r["budget_stop"] = str(error)
    except Exception as error: r["errors"].append(type(error).__name__+": "+str(error))
    r["cost"] = budget.report(); seal(D,r); print("sensor live",r["complete"],r["errors"],r["cost"],flush=True)
    if not r["complete"] or r["errors"] or r["budget_stop"]: raise SystemExit(1)


if __name__ == "__main__": execute()
