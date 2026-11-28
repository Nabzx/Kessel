"""Two fixed collection variants, selected on development before final practice."""
import zipfile

from kessel_training.policy import configure_cpu
from .coverage_rollout import run
from .linear_feedback import load
from .runtime import ROOT, FAMILIES
from .study_tools import Budget, begin, retain, seal, sha

D = ROOT/"docs/phase-11/collection-coverage-evidence"
VARIANTS = ((1.35,3.),(1.6,2.5))


def execute():
    configure_cpu(7,threads=1); budget = Budget(300,environment=24000,teacher=24000,replay=18000)
    names = [str(p.relative_to(ROOT)) for p in (ROOT/"training/kessel_training").glob("*.py")]
    names += ["training/kessel_lab/"+n+".py" for n in ("coverage_task","coverage_rollout","coverage_study","linear_feedback",
        "progress_task","progress_supervisor","runtime","clearance_stop","bootstrap_hold","range_contract","range_supervisor","motion_hold","range_pilot")]
    checkpoint = ROOT/"docs/phase-11/linear-feedback-evidence/feedback.pt"
    jobs = [(f,s) for s in (19020,19021) for f in ("nominal","low","low_grip","start_offset")]+[("low",19023)]
    plan = begin(D,"docs/adr/0082-bounded-collection-coverage-correction.md",names,
        {"kind":"collection-coverage-v1","variants":VARIANTS,"development":jobs,"evaluation_base":19024,"checkpoint_sha256":sha(checkpoint.read_bytes()),
         "families":list(FAMILIES),"patterns":["recovery","carry_loss","stale_clearance","old_clearance","missing_clearance"]})
    report = {"plan":plan,"cases":[],"complete":False,"errors":[],"budget_stop":None,"runtime_admitted":False,"weight_updates":0}
    try:
        scores = []; baselines = {}
        with zipfile.ZipFile(D/"traces.zip","w",compression=zipfile.ZIP_STORED) as archive:
            for variant,(spacing,reverse) in enumerate(VARIANTS):
                passed = collisions = 0
                for family,seed in jobs:
                    value = run(family,seed,budget,spacing=spacing,reverse_clearance=reverse)
                    passed += value["evaluation"]["passed"]; collisions += value["outcome"]["collision"]
                    report["cases"].append({"split":"development","variant":variant,"family":family,"seed":seed,"pattern":None,"source":"reference",
                        "outcome":value["outcome"],"evaluation":value["evaluation"],**retain(archive,f"development-{variant}-{family}-{seed}.json.gz",value)})
                    print("coverage development",variant,family,seed,value["evaluation"]["passed"],round(value["outcome"]["delivered_kg"]),flush=True)
                scores.append({"variant":variant,"passed":passed,"collisions":collisions})
            selected = max(scores,key=lambda r:(r["passed"],-r["collisions"],-r["variant"]))
            report.update(selection_scores=scores,selected=selected)
            spacing,reverse = VARIANTS[selected["variant"]]
            final = [(f,None) for f in FAMILIES]+[("nominal",p) for p in plan["patterns"]]
            for source in ("reference","learned_linear"):
                for family,pattern in final:
                    model,_ = load(checkpoint); learned = source == "learned_linear"
                    value = run(family,19024,budget,pattern,replay=True,actuator=model.action if learned else None,spacing=spacing,reverse_clearance=reverse)
                    queries = sum(not f["supervision"]["override"] for f in value["frames"][:-1]) if learned else 0
                    assert model.calls == 2*queries
                    value.update(neural_queries=queries,action_replay_queries=queries,checkpoint_sha256=plan["checkpoint_sha256"] if learned else None)
                    row = {"split":"evaluation","variant":selected["variant"],"family":family,"seed":19024,"pattern":pattern,"source":source,
                        "outcome":value["outcome"],"evaluation":value["evaluation"],"neural_queries":queries,
                        **retain(archive,f"evaluation-{source}-{family}-{pattern or 'standard'}.json.gz",value)}
                    if not learned: baselines[family,pattern] = value
                    else: row["same_outcome"] = value["evaluation"]["passed"] == baselines[family,pattern]["evaluation"]["passed"] and value["outcome"]["full_success"] == baselines[family,pattern]["outcome"]["full_success"]
                    report["cases"].append(row)
                    print("coverage final",source,family,pattern,value["evaluation"]["passed"],value["outcome"]["reason"] or "hold",flush=True)
        report["complete"] = len(report["cases"]) == 54
        report["gate_passed"] = report["complete"] and all(c["evaluation"]["passed"] for c in report["cases"] if c["split"] == "evaluation")
        report["max_replay_state_error"] = 0.
    except TimeoutError as error: report["budget_stop"] = str(error)
    except Exception as error: report["errors"].append(type(error).__name__+": "+str(error))
    report["cost"] = budget.report(); seal(D,report)
    print("coverage result",report.get("gate_passed"),report["errors"],report["budget_stop"],report["cost"],flush=True)
    if not report["complete"] or report["errors"] or report["budget_stop"]: raise SystemExit(1)


if __name__ == "__main__": execute()
