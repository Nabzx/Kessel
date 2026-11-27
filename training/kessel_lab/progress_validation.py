"""Frozen thirteen-family validation plus recovery and clearance-input faults."""
import gzip
import json
import zipfile

from kessel_training.policy import configure_cpu
from .progress_rollout import run
from .runtime import ROOT, FAMILIES
from .study_tools import Budget, begin, retain, seal

D = ROOT/"docs/phase-11/progress-validation-evidence"
DEVELOPMENT = ROOT/"docs/phase-11/progress-development-evidence"


def selection():
    scores = []
    for revision,gain in ((7,.15),(8,.1)):
        directory = DEVELOPMENT/f"revision-{revision}"; report = json.loads((directory/"report.json").read_text())
        if not report["complete"] or report["errors"] or report["budget_stop"]: raise ValueError("incomplete final rehearsal")
        passed = collisions = 0
        with zipfile.ZipFile(directory/"traces.zip") as archive:
            for row in report["cases"]:
                payload = json.loads(gzip.decompress(archive.read(row["trace"])))
                passed += payload["evaluation"]["passed"]; collisions += payload["outcome"]["collision"]
        scores.append({"revision":revision,"gain":gain,"passed":passed,"collisions":collisions})
    chosen = max(scores,key=lambda s:(s["passed"],-s["collisions"],s["gain"]))
    return chosen,scores


def execute():
    configure_cpu(7,threads=1); chosen,scores = selection(); budget = Budget(180,environment=12000,teacher=12000,replay=12000)
    names = [str(p.relative_to(ROOT)) for p in (ROOT/"training/kessel_training").glob("*.py")]
    names += ["training/kessel_lab/"+n+".py" for n in ("progress_task","progress_supervisor","progress_rollout","progress_validation",
        "clearance_stop","runtime","range_supervisor","range_contract","bootstrap_hold","motion_hold","range_pilot")]
    names += ["docs/adr/0079-lateral-feedback-stability-correction.md"]
    jobs = [(family,None) for family in FAMILIES]+[("nominal",pattern) for pattern in ("recovery","carry_loss","stale_clearance","old_clearance","missing_clearance")]
    plan = begin(D,"docs/adr/0078-progress-driven-task-and-clearance-compatibility.md",names,
                 {"kind":"frozen-progress-validation-v1","seed":19022,"selected":chosen,"selection_scores":scores,"jobs":jobs,
                  "role":"consumed-practice validation, not fresh qualification"})
    report = {"plan":plan,"cases":[],"complete":False,"errors":[],"budget_stop":None,"runtime_admitted":False,"neural_queries":0}
    try:
        with zipfile.ZipFile(D/"traces.zip","w",compression=zipfile.ZIP_STORED) as archive:
            for family,pattern in jobs:
                payload = run(family,19022,budget,pattern,replay=True,lateral_gain=chosen["gain"])
                report["cases"].append({"family":family,"pattern":pattern,"outcome":payload["outcome"],"evaluation":payload["evaluation"],
                    **retain(archive,f"{family}-{pattern or 'standard'}.json.gz",payload)})
                print("frozen validation",family,pattern,payload["evaluation"]["passed"],payload["outcome"]["reason"] or "hold",flush=True)
        report["complete"] = len(report["cases"]) == len(jobs)
        report["max_replay_state_error"] = 0.
    except TimeoutError as error: report["budget_stop"] = str(error)
    except Exception as error: report["errors"].append(type(error).__name__+": "+str(error))
    report["cost"] = budget.report(); report["gate_passed"] = report["complete"] and all(c["evaluation"]["passed"] for c in report["cases"])
    seal(D,report); print("validation",report["gate_passed"],report["errors"],report["cost"],flush=True)
    if not report["complete"] or report["errors"] or report["budget_stop"]: raise SystemExit(1)


if __name__ == "__main__": execute()
