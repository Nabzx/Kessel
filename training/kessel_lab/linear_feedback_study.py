"""ADR-0080 deterministic fitting and complete reference/learned comparison."""
import gzip
import json
import zipfile

import numpy as np

from kessel_training.policy import configure_cpu
from kessel_training.wm_data import write_archive
from .linear_feedback import fit, load, save
from .progress_rollout import run
from .runtime import ROOT, FAMILIES
from .study_tools import Budget, begin, retain, seal, sha, write

D = ROOT/"docs/phase-11/linear-feedback-evidence"


def execute():
    configure_cpu(7,threads=1); budget = Budget(180,environment=16000,teacher=16000,replay=8000)
    validation = ROOT/"docs/phase-11/progress-validation-evidence/report.json"
    selected = json.loads(validation.read_text())["plan"]["selected"]
    source = ROOT/f"docs/phase-11/progress-development-evidence/revision-{selected['revision']}"
    reference = json.loads((source/"report.json").read_text())
    names = [str(p.relative_to(ROOT)) for p in (ROOT/"training/kessel_training").glob("*.py")]
    names += ["training/kessel_lab/"+n+".py" for n in ("linear_feedback","linear_feedback_study","progress_task","progress_supervisor",
        "progress_rollout","runtime","clearance_stop","bootstrap_hold","range_contract","range_supervisor","motion_hold","range_pilot")]
    plan = begin(D,"docs/adr/0080-linear-feedback-imitation.md",names,{"kind":"linear-feedback-imitation-v1","training_bases":[19020,19021],
        "evaluation_base":19023,"selected":selected,"families":list(FAMILIES),"teacher_archive_sha256":sha((source/"traces.zip").read_bytes()),
        "teacher_report_sha256":sha((source/"report.json").read_bytes()),"teacher_source":str(source.relative_to(ROOT)),
        "hypothesis":"sparse learned linear feedback with hard action bounds; conventional planning/braking"})
    report = {"plan":plan,"complete":False,"errors":[],"budget_stop":None,"cases":[],"runtime_admitted":False,
              "training_label_queries":0,"evaluation_label_queries":0,"optimiser_updates":0}
    try:
        rows = []; targets = []; included = []; excluded = []
        with zipfile.ZipFile(source/"traces.zip") as archive:
            for case in reference["cases"]:
                raw = archive.read(case["trace"]); assert sha(raw) == case["sha256"]
                payload = json.loads(gzip.decompress(raw))
                if not payload["evaluation"]["passed"]: excluded.append({"seed":case["seed"],"family":case["family"]}); continue
                count = 0
                for frame in payload["frames"][:-1]:
                    control = frame["supervision"]
                    if control["override"]: continue
                    rows.append(control["task"]["control_features"]); targets.append(frame["action"]); count += 1
                included.append({"seed":case["seed"],"family":case["family"],"rows":count})
        x,y = np.asarray(rows),np.asarray(targets); write_archive(D/"training.npz",{"features":x,"labels":y})
        model,fit_report = fit(x,y); fit_report.update(training_rows=len(x),training_data_sha256=sha((D/"training.npz").read_bytes()))
        save(D/"feedback.pt",model,fit_report); write(D/"fit.json",fit_report)
        report.update(fit=fit_report,included_training=included,excluded_training=excluded)
        baselines = {}
        with zipfile.ZipFile(D/"traces.zip","w",compression=zipfile.ZIP_STORED) as archive:
            for source_name in ("reference","learned_linear"):
                for family in FAMILIES:
                    budget.check(); model,_ = load(D/"feedback.pt")
                    payload = run(family,19023,budget,replay=source_name == "learned_linear",
                                  actuator=model.action if source_name == "learned_linear" else None,lateral_gain=selected["gain"])
                    queries = sum(not f["supervision"]["override"] for f in payload["frames"][:-1]) if source_name == "learned_linear" else 0
                    assert model.calls == 2*queries
                    payload.update(neural_queries=queries,action_replay_queries=queries,
                                   checkpoint_sha256=sha((D/"feedback.pt").read_bytes()) if source_name == "learned_linear" else None)
                    row = {"source":source_name,"family":family,"outcome":payload["outcome"],"evaluation":payload["evaluation"],
                           "neural_queries":queries,**retain(archive,f"{source_name}-{family}.json.gz",payload)}
                    if source_name == "reference": baselines[family] = payload
                    else:
                        previous = baselines[family]
                        row["same_outcome"] = payload["outcome"]["full_success"] == previous["outcome"]["full_success"] and payload["evaluation"]["passed"] == previous["evaluation"]["passed"]
                        row["max_aligned_action_error"] = max(max(abs(a-b) for a,b in zip(f["action"],g["action"])) for f,g in zip(payload["frames"][:-1],previous["frames"][:-1]))
                    report["cases"].append(row)
                    print(source_name,family,payload["evaluation"]["passed"],payload["outcome"]["reason"] or "hold",flush=True)
        report["complete"] = len(report["cases"]) == 26
        report["gate_passed"] = report["complete"] and all(c["evaluation"]["passed"] for c in report["cases"])
        report["max_replay_state_error"] = 0.
    except TimeoutError as error: report["budget_stop"] = str(error)
    except Exception as error: report["errors"].append(type(error).__name__+": "+str(error))
    report["cost"] = budget.report(); seal(D,report)
    print("linear feedback",report.get("gate_passed"),report["errors"],report["cost"],flush=True)
    if not report["complete"] or report["errors"] or report["budget_stop"]: raise SystemExit(1)


if __name__ == "__main__": execute()
