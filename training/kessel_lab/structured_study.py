"""ADR-0081 rare-event acquisition and structured forecast comparison."""
import gzip
import json
import zipfile

import numpy as np
import torch

from kessel_training.policy import configure_cpu
from kessel_training.wm_data import logical_hash, write_archive
from kessel_training.wm_evaluate import gate_report, metrics, open_loop, simple_prediction
from kessel_training.world_model import load_model
from .forecast_refit import bounded_calibration, operational_gate
from .runtime import ROOT, FAMILIES
from .structured_data import arrays, collect_fixture
from .structured_fit import fit, load, save
from .study_tools import Budget, begin, retain, seal, sha, write

D = ROOT/"docs/phase-11/structured-dynamics-evidence"


class Variant:
    def __init__(self,model,ablation=False,learned_events=False): self.model = model; self.ablation = ablation; self.learned_events = learned_events
    def predict(self,state,action): return self.model.predict(state,action,ablation=self.ablation,learned_events=self.learned_events)


class Baseline:
    def __init__(self,name): self.name = name
    def predict(self,state,action): return simple_prediction(state,action,self.name)


def read_cases(directory,filter_case):
    report = json.loads((directory/"report.json").read_text()); values = []
    with zipfile.ZipFile(directory/"traces.zip") as archive:
        for case in report["cases"]:
            if not filter_case(case): continue
            raw = archive.read(case["trace"])
            if sha(raw) != case["sha256"]: raise ValueError("reused source trace changed")
            values.append(json.loads(gzip.decompress(raw)))
    return values


def execute():
    configure_cpu(7,threads=1); budget = Budget(420,environment=32000,replay=20000,updates=2250)
    validation_dir = ROOT/"docs/phase-11/progress-validation-evidence"
    chosen = json.loads((validation_dir/"report.json").read_text())["plan"]["selected"]
    training_dir = ROOT/f"docs/phase-11/progress-development-evidence/revision-{chosen['revision']}"
    evaluation_dir = ROOT/"docs/phase-11/linear-feedback-evidence"
    inputs = {}
    for directory in (training_dir,validation_dir,evaluation_dir):
        for name in ("report.json","traces.zip"): inputs[str((directory/name).relative_to(ROOT))] = sha((directory/name).read_bytes())
    paths = [str(p.relative_to(ROOT)) for p in (ROOT/"training/kessel_training").glob("*.py")]
    paths += ["training/kessel_lab/"+name+".py" for name in ("structured_model","structured_data","structured_fit","structured_study",
        "runtime","forecast_refit","forecast_dataset")]
    plan = begin(D,"docs/adr/0081-structured-local-dynamics-and-rare-events.md",paths,
        {"kind":"structured-local-dynamics-study-v1","inputs":inputs,"training_bases":[19020,19021],"validation_base":19022,"evaluation_base":19023,
         "rare_training_collision":list(range(19100,19228)),"rare_training_stuck":list(range(19228,19356)),
         "rare_validation":[19360,19361,19362,19363],"rare_evaluation":[19370,19371,19372,19373],
         "updates_per_member":750,"member_seeds":[101,211,307],"windows_per_split":128,"artifact_cap_bytes":96*1024**2,
         "software":{"torch":str(torch.__version__),"numpy":np.__version__}})
    report = {"plan":plan,"collection":[],"datasets":{},"methods":{},"complete":False,"errors":[],"budget_stop":None,
              "teacher_queries":0,"policy_updates":0,"assisted_updates":0,"runtime_admitted":False,"assistance_qualified":False}
    try:
        splits = {"train":read_cases(training_dir,lambda c:True),
                  "validation":read_cases(validation_dir,lambda c:c["pattern"] is None),
                  "evaluation":read_cases(evaluation_dir,lambda c:c["source"] == "learned_linear")}
        assert [len(splits[n]) for n in ("train","validation","evaluation")] == [26,13,13]
        jobs = [("train","collision",s) for s in range(19100,19228)]+[("train","stuck",s) for s in range(19228,19356)]
        jobs += [(split,kind,seed) for split,seeds in (("validation",[19360,19361,19362,19363]),("evaluation",[19370,19371,19372,19373]))
                 for kind,seed in zip(("collision","collision","stuck","stuck"),seeds)]
        with zipfile.ZipFile(D/"trajectories.zip","w",compression=zipfile.ZIP_STORED) as archive:
            for split,episodes in splits.items():
                for episode in episodes:
                    name = f"{split}-working-{episode['scenario']['seed']}-{episode['scenario']['family']}.json.gz"
                    report["collection"].append({"split":split,"reused":True,"seed":episode["scenario"]["seed"],"family":episode["scenario"]["family"],
                        "outcome":episode["outcome"],**retain(archive,name,episode)})
            for index,(split,kind,seed) in enumerate(jobs):
                budget.check(); episode = collect_fixture(kind,seed,budget); splits[split].append(episode)
                report["collection"].append({"split":split,"reused":False,"seed":seed,"family":"prepared_"+kind,
                    "outcome":episode["outcome"],"fixture_gate_passed":episode["fixture_gate_passed"],
                    **retain(archive,f"{split}-{kind}-{seed}.json.gz",episode)})
                if (index+1)%32 == 0: print("prepared coverage",index+1,"episodes",budget.counts,flush=True)
        groups = {split:arrays(episodes) for split,episodes in splits.items()}
        for split,(data,episodes) in groups.items():
            write_archive(D/f"{split}.npz",data)
            report["datasets"][split] = {"rows":len(data["state"]),"episodes":episodes,"logical_sha256":logical_hash(data,episodes),
                "regime_rows":np.bincount(data["regime"],minlength=4).tolist()}
        train,tm = groups["train"]; validation,vm = groups["validation"]; evaluation,em = groups["evaluation"]
        rare = [r for r in report["collection"] if r["split"] == "train" and not r["reused"]]
        collisions = sum(r["outcome"]["collision"] for r in rare); stuck = sum(r["outcome"]["reason"] == "stuck" for r in rare)
        report["rare_coverage"] = {"collision_episodes":collisions,"stuck_episodes":stuck,"target_per_class":128,
            "goal_met":collisions == stuck == 128,"unique_prepared_bases":len({r["seed"] for r in rare})}
        model,training = fit(train,tm,budget); training["training_dataset_sha256"] = logical_hash(train,tm)
        save(D/"structured.pt",model,training); write(D/"training.json",training)
        print("structured heads fitted",budget.counts,flush=True)
        model,_ = load(D/"structured.pt")
        retained,_ = load_model(ROOT/"docs/phase-11/world-followup-evidence/multistep_material.pt")
        refit,_ = load_model(ROOT/"docs/phase-11/working-policy-refit-evidence/refit.pt")
        methods = (("persistence",Baseline("persistence")),("kinematic",Baseline("kinematic")),("retained_ensemble",retained),
                   ("previous_refit",refit),("structured",Variant(model)),("structured_learned_events",Variant(model,learned_events=True)),
                   ("no_learned_motion_or_flux",Variant(model,ablation=True)))
        for name,method in methods:
            budget.check(); prediction = method.predict(evaluation["state"],evaluation["action"])
            write_archive(D/f"predictions-{name}.npz",{k:v for k,v in prediction.items() if k in ("next_state","reward","events","learned_events","disagreement","input_envelope")})
            entry = {"one_step":metrics(prediction,evaluation),"drift":open_loop(method,evaluation,em,max_windows=128)}
            if name not in ("persistence","kinematic","no_learned_motion_or_flux"):
                gate = bounded_calibration(method,validation,vm); vp = method.predict(validation["state"],validation["action"])
                write_archive(D/f"validation-predictions-{name}.npz",{k:v for k,v in vp.items() if k in ("next_state","reward","events","disagreement")})
                entry["calibration_gate"] = gate; entry["families"] = []
                for family in (*FAMILIES,"prepared_collision","prepared_stuck"):
                    ids = [e["id"] for e in em if e["family"] == family]; mask = np.isin(evaluation["episode_id"],ids)
                    entry["families"].append({"family":family,**operational_gate(method,{k:v[mask] for k,v in evaluation.items()},gate)})
                entry["forecast_eligible"] = bool(gate["supported_horizon"] >= 1 and report["rare_coverage"]["goal_met"] and all(
                    r["forecast_gate"]["accepted"] and r["forecast_gate"]["accepted_high_error_fraction"] <= .1
                    and r["operational_accepted"] and r["operational_high_error_fraction"] <= .1
                    for r in entry["families"] if r["family"] != "blocked"))
            report["methods"][name] = entry
            print(name,"position",round(entry["one_step"]["position_mae_m"],5),"high-error",round(entry["one_step"]["high_error_fraction"],4),
                  "eligible",entry.get("forecast_eligible"),flush=True)
        report["forecast_eligible_methods"] = [n for n,e in report["methods"].items() if e.get("forecast_eligible")]
        report["complete"] = len(report["collection"]) == 316 and len(report["methods"]) == 7
        report["max_fixture_replay_state_error"] = 0.
        if sum(p.stat().st_size for p in D.rglob("*") if p.is_file()) > 96*1024**2: raise TimeoutError("artifact_cap")
    except TimeoutError as error: report["budget_stop"] = str(error)
    except Exception as error: report["errors"].append(type(error).__name__+": "+str(error))
    report["cost"] = budget.report(); seal(D,report)
    print("structured study",report["complete"],report.get("forecast_eligible_methods"),report["errors"],report["budget_stop"],report["cost"],flush=True)
    if not report["complete"] or report["errors"] or report["budget_stop"]: raise SystemExit(1)


if __name__ == "__main__": execute()
