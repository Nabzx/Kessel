"""Charged adaptive practice only; all attempts are append-only and retained."""
import argparse
import json
import time
import zipfile

import numpy as np

from kessel_training.contracts import LoaderConfig
from kessel_training.policy import configure_cpu
from .progress_task import ProgressTask
from .robustness_study import rollout
from .runtime import ROOT, environment
from .study_tools import Budget, begin, retain, seal, write

BASE = ROOT/"docs/phase-11/progress-development-evidence"


def execute(label,families,supervised=False,lateral_gain=.15):
    configure_cpu(7,threads=1)
    prior = [json.loads(p.read_text()) for p in BASE.glob("*/report.json")]
    used = sum(r["cost"]["counts"]["environment"] for r in prior); elapsed = sum(r["cost"]["wall_s"] for r in prior)
    if len(prior) >= 8: raise ValueError("eight-revision corrected practice cap")
    budget = Budget(max(0.,300-elapsed),environment=40000-used,teacher=40000-used)
    names = ["training/kessel_lab/"+n+".py" for n in ("progress_task","progress_development","runtime","robustness_study","range_supervisor")]
    if supervised: names += ["training/kessel_lab/"+n+".py" for n in ("progress_rollout","progress_supervisor","clearance_stop","bootstrap_hold","range_contract","motion_hold","range_pilot")]
    names += [str(p.relative_to(ROOT)) for p in (ROOT/"training/kessel_training").glob("*.py")]
    names += ["docs/adr/0079-lateral-feedback-stability-correction.md"]
    directory = BASE/label
    plan = begin(directory,"docs/adr/0078-progress-driven-task-and-clearance-compatibility.md",names,
                 {"kind":"adaptive-progress-practice-v1","bases":[19020,19021],"families":families,"preceding_decisions":used,"preceding_wall_s":elapsed,"supervised":supervised,"lateral_gain":lateral_gain})
    report = {"plan":plan,"cases":[],"complete":False,"errors":[],"budget_stop":None}
    try:
        with zipfile.ZipFile(directory/"traces.zip","w",compression=zipfile.ZIP_STORED) as archive:
            for seed in (19020,19021):
                for family in families:
                    env,_ = environment(family,seed)
                    bottom = .35+2*np.sin(LoaderConfig().boom_min_rad)
                    upper = float(np.maximum(env.pile.height[0]-bottom,0).sum()*.25*env.pile.density[0])
                    if supervised:
                        from .progress_rollout import run
                        payload = run(family,seed,budget,lateral_gain=lateral_gain)
                    else: payload = rollout(family,seed,ProgressTask(),budget,teacher=True)
                    row = {"seed":seed,"family":family,"recoverable_material_upper_bound_kg":upper,"outcome":payload["outcome"],
                           **retain(archive,f"{seed}-{family}.json.gz",payload)}
                    report["cases"].append(row)
                    print(label,seed,family,payload["outcome"]["reason"],round(payload["outcome"]["delivered_kg"]),"upper bound",round(upper),flush=True)
        report["complete"] = len(report["cases"]) == 2*len(families)
    except TimeoutError as error: report["budget_stop"] = str(error)
    except Exception as error: report["errors"].append(type(error).__name__+": "+str(error))
    report["cost"] = budget.report(); seal(directory,report)
    print("practice",label,report["cost"],report["errors"],flush=True)
    if report["errors"] or report["budget_stop"] or not report["complete"]: raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--label",required=True)
    parser.add_argument("--families",nargs="+",default=["nominal","low","steep","start_offset"])
    parser.add_argument("--supervised",action="store_true")
    parser.add_argument("--lateral-gain",type=float,default=.15,choices=(.15,.1))
    args = parser.parse_args(); execute(args.label,args.families,args.supervised,args.lateral_gain)
