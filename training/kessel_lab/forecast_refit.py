"""ADR-0075 training-only working-policy refit and unchanged forecast gates."""
import gzip
import json
import zipfile

import numpy as np
import torch

from kessel_training.constrained_model import ConstrainedModel
from kessel_training.followup_models import ObservationModel, fit_observable
from kessel_training import checkpoints
from kessel_training.policy import configure_cpu
from kessel_training.wm_data import logical_hash, write_archive
from kessel_training.wm_evaluate import calibrate, errors, gate_report, metrics, open_loop, simple_prediction
from kessel_training import wm_evaluate
from kessel_training.wm_state import violations
from kessel_training.world_model import ModelConfig, fit, load_model, save_model
from .forecast_dataset import arrays, validate_splits
from .runtime import ROOT, FAMILIES, Run
from .study_tools import Budget, begin, retain, seal, sha, write

D = ROOT/"docs/phase-11/working-policy-refit-evidence"
PREVIOUS = ROOT/"docs/phase-11/robustness-repair-evidence"


class Baseline:
    def __init__(self,name): self.name = name
    def predict(self,state,action): return simple_prediction(state,action,self.name)


def bounded_calibration(method,data,episodes):
    original = wm_evaluate.open_loop
    def bounded(*args,**kwargs):
        kwargs["max_windows"] = 128
        return original(*args,**kwargs)
    wm_evaluate.open_loop = bounded
    try: return calibrate(method,data,episodes)
    finally: wm_evaluate.open_loop = original


def operational_gate(model,data,gate):
    result = gate_report(model,data,gate); prediction = model.predict(data["state"],data["action"])
    selected = np.zeros(len(data["state"]),dtype=bool) if gate["threshold"] is None else prediction["disagreement"] <= gate["threshold"]
    invalid = violations(prediction["next_state"])
    physical = np.logical_or.reduce([value for key,value in invalid.items() if key != "mass_error_kg"])
    physical |= abs(invalid["mass_error_kg"]) > 25
    rejected = prediction.get("filter_rejected",np.zeros(len(selected),dtype=bool))
    accepted = selected & ~physical & ~rejected
    high_error = errors(prediction,data["next_state"],data["reward"],data["events"])["high_error"]
    return {"forecast_gate":result,"physically_invalid_rows":int(physical.sum()),"filter_rejected_rows":int(rejected.sum()),
            "operational_accepted":int(accepted.sum()),"operational_missed_high_error":int((accepted&high_error).sum()),
            "operational_high_error_fraction":float(high_error[accepted].mean()) if accepted.any() else None}


def execute():
    configure_cpu(7,threads=1); budget = Budget(300,environment=31200,updates=6000)
    names = [str(p.relative_to(ROOT)) for p in (ROOT/"training/kessel_training").glob("*.py")]
    names += ["training/kessel_lab/"+n+".py" for n in ("forecast_dataset","forecast_refit","runtime")]
    names += ["scripts/research/evaluate-working-policy-models.py"]
    old_path = ROOT/"docs/phase-11/world-followup-evidence/multistep_material.pt"
    if sha(old_path.read_bytes()) != old_path.with_suffix(".pt.sha256").read_text().strip(): raise ValueError("old model hash differs")
    old_obs_path = old_path.with_name("observable.pt")
    if sha(old_obs_path.read_bytes()) != old_obs_path.with_suffix(".pt.sha256").read_text().strip(): raise ValueError("old observable model hash differs")
    prior = json.loads((PREVIOUS/"report.json").read_text())
    plan = begin(D,"docs/adr/0075-working-policy-world-model-refit.md",names,{"kind":"working-policy-refit-practice-v1",
        "training_bases":[19010,19011],"validation_bases":[19012],"evaluation_bases":[19013],"families":list(FAMILIES),
        "source":"phase_memory-7","state_epochs":30,"observable_epochs":20,"hidden":64,"members":3,
        "old_model_sha256":sha(old_path.read_bytes()),"reused_report_sha256":sha((PREVIOUS/"report.json").read_bytes()),
        "old_observable_sha256":sha(old_obs_path.read_bytes()),
        "windows_per_split":128,"windows_per_method_cap":256,
        "role":"consumed practice refit; no fresh qualification","artifact_cap_bytes":64*1024**2})
    report = {"plan":plan,"complete":False,"errors":[],"budget_stop":None,"collection":[],"methods":{},
              "teacher_queries":0,"policy_updates":0,"assisted_updates":0,"assistance_qualified":False,"runtime_admitted":False}
    original_step = torch.optim.Adam.step
    def counted_step(optimiser,*args,**kwargs): budget.charge("updates"); return original_step(optimiser,*args,**kwargs)
    torch.optim.Adam.step = counted_step
    try:
        splits = {"train":[],"validation":[],"evaluation":[]}
        with zipfile.ZipFile(D/"trajectories.zip","w",compression=zipfile.ZIP_STORED) as archive, zipfile.ZipFile(PREVIOUS/"traces.zip") as preceding:
            for split,bases in (("train",[19010,19011]),("validation",[19012]),("evaluation",[19013])):
                for seed in bases:
                    for family in FAMILIES:
                        budget.check(); reused = False
                        matching = next((c for c in prior["cases"] if c["stage"] == "evaluation" and c["source"] == "original-7" and c["family"] == family and c["seed"] == seed),None)
                        if matching:
                            raw = preceding.read(matching["trace"])
                            if sha(raw) != matching["sha256"]: raise ValueError("reused trajectory differs")
                            payload = json.loads(gzip.decompress(raw)); reused = True
                        else:
                            run = Run(family,seed,"phase_memory-7")
                            while not run.done: budget.charge("environment"); run.step()
                            final = run.frame(); final["observation"] = {k:v[0].tolist() for k,v in run.env.observe().items()}
                            payload = {"scenario":run.scenario,"outcome":run.outcome(),"frames":run.records+[final],
                                       "checkpoint_sha256":run.checkpoint_sha256,"applied_machine_commands":False}
                        splits[split].append(payload)
                        report["collection"].append({"split":split,"seed":seed,"family":family,"reused":reused,"outcome":payload["outcome"],
                            **retain(archive,f"{split}-{seed}-{family}.json.gz",payload)})
                print("forecast corpus",split,len(splits[split]),"complete episodes",flush=True)
        validate_splits(splits); converted = {split:arrays(episodes) for split,episodes in splits.items()}
        train,tm = converted["train"]; validation,vm = converted["validation"]; evaluation,em = converted["evaluation"]
        report["datasets"] = {}
        for split,(data,meta) in converted.items():
            write_archive(D/f"{split}.npz",data)
            report["datasets"][split] = {"rows":len(data["state"]),"episodes":meta,"logical_sha256":logical_hash(data,meta),
                "collision_episodes":sum(e["reason"].startswith(("tunnel","obstacle")) for e in meta),"stuck_episodes":sum(e["reason"] == "stuck" for e in meta),
                "regime_rows":np.bincount(data["regime"],minlength=4).tolist()}
        budget.check()
        model,training = fit(train,validation,{"episodes":tm,"logical_sha256":logical_hash(train,tm)},ModelConfig(hidden=64,epochs=30))
        save_model(D/"refit.pt",model,training); write(D/"state-training.json",training)
        print("privileged refit selected epoch",training["selected_epoch"],"updates",training["optimiser_updates"],flush=True)
        usable_train = train["observable_target_present"].astype(bool); usable_val = validation["observable_target_present"].astype(bool)
        observable,observed_training = fit_observable({k:v[usable_train] for k,v in train.items()},{k:v[usable_val] for k,v in validation.items()},epochs=20)
        torch.save({"weights":observable.state_dict(),"training":observed_training},D/"observable.pt")
        write(D/"observable-training.json",observed_training)
        old,_ = load_model(old_path)
        for name,method in (("persistence",Baseline("persistence")),("kinematic",Baseline("kinematic")),
                            ("retained_ensemble",old),("refit_raw",model),("refit_bounded_filter",ConstrainedModel(model))):
            budget.check(); prediction = method.predict(evaluation["state"],evaluation["action"])
            write_archive(D/f"predictions-{name}.npz",{k:v for k,v in prediction.items() if k in
                ("next_state","reward","events","disagreement","input_envelope","filter_rejected")})
            entry = {"one_step":metrics(prediction,evaluation),"drift":open_loop(method,evaluation,em,max_windows=128)}
            if name in ("retained_ensemble","refit_raw","refit_bounded_filter"):
                gate = bounded_calibration(method,validation,vm); entry["calibration_gate"] = gate; entry["families"] = []
                val_prediction = method.predict(validation["state"],validation["action"])
                write_archive(D/f"validation-predictions-{name}.npz",{k:v for k,v in val_prediction.items() if k in
                    ("next_state","reward","events","disagreement","input_envelope","filter_rejected")})
                for family in FAMILIES:
                    ids = [e["id"] for e in em if e["family"] == family]; mask = np.isin(evaluation["episode_id"],ids)
                    part = {k:v[mask] for k,v in evaluation.items()}
                    entry["families"].append({"family":family,**operational_gate(method,part,gate)})
                entry["forecast_eligible"] = bool(gate["supported_horizon"] >= 1 and all(
                    r["forecast_gate"]["accepted"] and r["forecast_gate"]["accepted_high_error_fraction"] <= .1
                    and r["operational_accepted"] and r["operational_high_error_fraction"] <= .1
                    for r in entry["families"] if r["family"] != "blocked"))
            report["methods"][name] = entry
            print("forecast",name,"position",round(entry["one_step"]["position_mae_m"],5),"high-error",round(entry["one_step"]["high_error_fraction"],4),flush=True)
        present = evaluation["observable_target_present"].astype(bool); target = evaluation["next_observation"][present]
        valid = target[:,40:].astype(bool)
        old_weights = checkpoints.load(old_obs_path)["weights"]
        old_observable = ObservationModel(old_weights["input_mean"],old_weights["input_scale"],old_weights["target_mean"],old_weights["target_scale"])
        old_observable.load_state_dict(old_weights); old_observable.eval(); report["observable"] = {}
        for name,method in (("retained",old_observable),("refit",observable)):
            predicted = method.predict(evaluation["observation"][present],evaluation["action"][present])["observation"]
            write_archive(D/f"observable-{name}-predictions.npz",{"observation":predicted})
            report["observable"][name] = {"rows":int(present.sum()),"excluded_terminal_rows":int((~present).sum()),
                "proprio_mae":abs(predicted[:,:15]-target[:,:15]).mean(axis=0).tolist(),
                "valid_range_mae_m":float(abs(predicted[:,15:40]-target[:,15:40])[valid].mean()),
                "range_validity_accuracy":float(((predicted[:,40:] >= .5) == valid).mean()),"hidden_material_prediction":None}
        report["rare_failure_training_goal"] = {"target_per_class":128,"collision":report["datasets"]["train"]["collision_episodes"],
            "stuck":report["datasets"]["train"]["stuck_episodes"],"met":False}
        report["forecast_eligible_methods"] = [n for n,e in report["methods"].items() if e.get("forecast_eligible")]
        report["decision"] = "forecast gate passes only on consumed practice; a separate matched-budget assistance study is required" if report["forecast_eligible_methods"] else "no-go: retain rejected forecast gate; assistance remains disabled"
        report["complete"] = len(report["collection"]) == 52 and len(report["methods"]) == 5
        if sum(p.stat().st_size for p in D.rglob("*") if p.is_file()) > 64*1024**2: raise TimeoutError("artifact_cap")
    except TimeoutError as error: report["budget_stop"] = str(error)
    except Exception as error: report["errors"].append(type(error).__name__+": "+str(error))
    finally: torch.optim.Adam.step = original_step
    report["cost"] = budget.report(); seal(D,report)
    print("forecast complete",report["complete"],report["errors"],report["budget_stop"],report["cost"],flush=True)
    if not report["complete"] or report["errors"] or report["budget_stop"]: raise SystemExit(1)


if __name__ == "__main__": execute()
