"""ADR-0076 correction, charged against the remaining robustness budget."""
import json
import zipfile

from kessel_training.policy import configure_cpu
from kessel_training.wm_state import pack
from .robust_reference_fix import DampedTaskReference
from .robustness_study import rollout
from .runtime import ROOT, FAMILIES, environment
from .study_tools import Budget, begin, retain, seal

D = ROOT/"docs/phase-11/damped-reference-evidence"


def execute():
    configure_cpu(7,threads=1); budget = Budget(180,environment=7800,teacher=7800,replay=7800)
    paths = [str(p.relative_to(ROOT)) for p in (ROOT/"training/kessel_training").glob("*.py")]
    paths += ["training/kessel_lab/"+n+".py" for n in ("robust_task","robust_reference_fix","robustness_study","damped_reference_pilot","runtime","range_supervisor")]
    plan = begin(D,"docs/adr/0076-forward-steering-stability-correction.md",paths,{"kind":"damped-reference-correction-v1",
                 "base":19014,"fill_timeout_s":12,"families":list(FAMILIES),"runtime_admitted":False})
    report = {"plan":plan,"cases":[],"complete":False,"errors":[],"budget_stop":None,"optimiser_updates":0,"runtime_admitted":False}
    try:
        with zipfile.ZipFile(D/"traces.zip","w",compression=zipfile.ZIP_STORED) as archive:
            for family in FAMILIES:
                payload = rollout(family,19014,DampedTaskReference(12.),budget,teacher=True)
                replay,_ = environment(family,19014)
                for frame in payload["frames"][:-1]:
                    budget.charge("replay"); replay.step([frame["action"]])
                    assert pack(replay)[0].tolist() == frame["next_state"]
                report["cases"].append({"family":family,"outcome":payload["outcome"],**retain(archive,family+".json.gz",payload)})
                print("damped reference",family,payload["outcome"]["reason"],round(payload["outcome"]["delivered_kg"]),flush=True)
        report["complete"] = len(report["cases"]) == 13
        preceding = json.loads((ROOT/"docs/phase-11/robustness-repair-evidence/report.json").read_text())
        counts = budget.counts; previous = preceding["cost"]["counts"]
        assert counts["environment"]+previous["environment"] <= 100000
        assert counts["teacher"]+previous["teacher"] <= 30000
        assert counts["replay"]+previous["replay"] <= 25000
        assert budget.elapsed+preceding["cost"]["wall_s"] <= 600
        report["max_replay_state_error"] = 0.
    except TimeoutError as error: report["budget_stop"] = str(error)
    except Exception as error: report["errors"].append(type(error).__name__+": "+str(error))
    report["cost"] = budget.report(); seal(D,report)
    print("damped correction",report["complete"],report["errors"],report["cost"],flush=True)
    if not report["complete"] or report["errors"] or report["budget_stop"]: raise SystemExit(1)


if __name__ == "__main__": execute()
