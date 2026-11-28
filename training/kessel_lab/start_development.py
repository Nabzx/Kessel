"""Append-only adaptive rehearsal under the shared ADR-0083 cost ledger."""
import argparse
import json
import zipfile

from kessel_training.policy import configure_cpu
from .start_rollout import run
from .runtime import ROOT, FAMILIES
from .study_tools import Budget, begin, retain, seal

BASE = ROOT/"docs/phase-11/harvest-development-evidence"


def execute(revision,regression=False):
    configure_cpu(7,threads=1); decisions = replay = 0; wall = 0.
    for i in range(1,revision):
        previous = json.loads((BASE/f"revision-{i}/report.json").read_text())
        decisions += previous["cost"]["counts"]["environment"]; replay += previous["cost"]["counts"].get("replay",0)
        wall += previous["cost"]["wall_s"]
    if not 1 <= revision <= 8: raise ValueError("eight-revision cap")
    budget = Budget(600-wall,environment=40000-decisions,teacher=40000-decisions,replay=40000-replay)
    directory = BASE/f"revision-{revision}"
    paths = [str(p.relative_to(ROOT)) for p in (ROOT/"training/kessel_training").glob("*.py")]
    paths += ["training/kessel_lab/"+n+".py" for n in ("harvest_task","harvest_rollout","harvest_development","start_progress","start_rollout","start_development","progress_task","progress_supervisor",
        "runtime","clearance_stop","bootstrap_hold","range_supervisor","range_contract","motion_hold","range_pilot")]
    jobs = [("low",19023),("low_grip",19021),("low_grip",19024),("nominal",19020)]
    if regression: jobs = [(f,s) for s in (19020,19021) for f in FAMILIES]+[("low",19023),("low_grip",19024)]
    plan = begin(directory,"docs/adr/0083-harvest-recovery-and-traction-feasibility.md",paths,
        {"kind":"proposed-start-guard-development-v1","revision":revision,"jobs":jobs,"preceding_decisions":decisions,"preceding_replay":replay,"preceding_wall_s":wall})
    report = {"plan":plan,"cases":[],"complete":False,"errors":[],"budget_stop":None,"runtime_admitted":False}
    try:
        with zipfile.ZipFile(directory/"traces.zip","w",compression=zipfile.ZIP_STORED) as archive:
            for family,seed in jobs:
                value = run(family,seed,budget,replay=True)
                report["cases"].append({"seed":seed,"family":family,"pattern":None,"outcome":value["outcome"],"evaluation":value["evaluation"],
                    **retain(archive,f"{family}-{seed}.json.gz",value)})
                print("harvest",revision,family,seed,value["evaluation"]["passed"],value["outcome"],flush=True)
        report["complete"] = len(report["cases"]) == len(jobs)
    except TimeoutError as error: report["budget_stop"] = str(error)
    except Exception as error: report["errors"].append(type(error).__name__+": "+str(error))
    report["cost"] = budget.report(); report["gate_passed"] = report["complete"] and all(c["evaluation"]["passed"] for c in report["cases"])
    seal(directory,report)
    if not report["complete"] or report["errors"] or report["budget_stop"]: raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--revision",required=True,type=int); parser.add_argument("--regression",action="store_true")
    args = parser.parse_args(); execute(args.revision,args.regression)
