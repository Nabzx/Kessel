"""Train/evaluate observation-only forecasts on hashed recorded sensor streams."""
import gzip
import json
import zipfile

import numpy as np

from kessel_training.policy import configure_cpu
from kessel_training.wm_data import write_archive, logical_hash
from .runtime import ROOT
from .sensor_model import fit, load, save, observations
from .sensor_records import from_episode, parse, pairs
from .study_tools import Budget, begin, seal, sha, write

D = ROOT/"docs/phase-11/sensor-forecast-v2-evidence"


def measurements(data,prediction):
    y = data["next_observation"]; p = prediction["observation"]
    mask = y[:,40:65]; count = mask.sum(axis=1)
    height = (abs(p[:,15:40]-y[:,15:40])*mask).sum(axis=1)/np.maximum(count,1)
    position = np.linalg.norm(p[:,:2]-y[:,:2],axis=1); speed = abs(p[:,4]-y[:,4]); load_error = abs(p[:,8]-y[:,8])
    high = (position > .05)|(speed > .05)|(load_error > 50)|(height > .05)
    return {"high":high,"position":position,"speed":speed,"carried":load_error,"height":height,"height_valid":count > 0,
            "validity_brier":((p[:,40:65]-mask)**2).mean(axis=1),"freshness_brier":(p[:,12]-y[:,12])**2}


def metric(data,prediction,indices=None):
    errors = measurements(data,prediction); selected = np.ones(len(data["action"]),dtype=bool) if indices is None else indices
    rows = int(selected.sum()); result = {"rows":rows}
    for name in ("position","speed","carried","height","validity_brier","freshness_brier","high"):
        eligible = selected & errors["height_valid"] if name == "height" else selected
        result[name+"_mean"] = float(errors[name][eligible].mean()) if eligible.any() else None
    result["target_valid_height_rows"] = int((selected & errors["height_valid"]).sum())
    return result


def predict(model,data):
    # Bound inference memory independently of archive size.
    values = {name:[] for name in ("observation","disagreement","input_usable")}
    for start in range(0,len(data["action"]),512):
        part = {k:v[start:start+512] for k,v in data.items()}
        result = model.predict(observations(part["observation"]),part["action"],observations(part["previous_observation"]),part["previous_action"],part["history_present"])
        for name in values: values[name].append(result[name])
    return {name:np.concatenate(parts) for name,parts in values.items()}


def execute():
    configure_cpu(7,threads=1); budget = Budget(240,updates=2250)
    inputs = (("train",ROOT/"docs/phase-11/harvest-development-evidence/revision-7"),
              ("validation",ROOT/"docs/phase-11/harvest-practice-evidence"),("evaluation",ROOT/"docs/phase-11/harvest-qualification-evidence/fresh"))
    paths = ["docs/adr/0089-sensor-terminal-clock-conversion.md"]+["training/kessel_lab/"+name+".py" for name in ("sensor_records","sensor_model","sensor_study","observations","range_supervisor")]
    plan = begin(D,"docs/adr/0088-recorded-sensor-only-forecast.md",paths,{"kind":"recorded_sensor_forecast_v1","source_archives":{str((d/"traces.zip").relative_to(ROOT)):sha((d/"traces.zip").read_bytes()) for _,d in inputs},
        "training_bases":[19020,19021],"validation_bases":[19025],"evaluation_bases":list(range(207400,207432))+list(range(207470,207478)),"physical_queries":0,
        "source_kind":"recorded_synthetic","field_recordings_supplied":False,"optimiser_updates":2250})
    report = {"plan":plan,"recordings":[],"datasets":{},"complete":False,"errors":[],"budget_stop":None,"runtime_admitted":False,"physical_queries":0,"privileged_inputs":False}
    try:
        splits = {}; identity_seen = set(); base_splits = {}
        with zipfile.ZipFile(D/"recordings.zip","w",compression=zipfile.ZIP_STORED) as output:
            for split,directory in inputs:
                source = json.loads((directory/"report.json").read_text()); collected = []
                with zipfile.ZipFile(directory/"traces.zip") as archive:
                    for case in source["cases"]:
                        if split == "train" and case["seed"] not in (19020,19021): continue
                        if split == "validation" and (case["source"] != "learned_linear" or case["split"] == "known_regression"): continue
                        if split == "evaluation" and case["source"] != "learned_linear": continue
                        raw = archive.read(case["trace"])
                        if sha(raw) != case["sha256"]: raise ValueError("recorded source trace changed")
                        episode = json.loads(gzip.decompress(raw)); base = episode["scenario"]["seed"]
                        if base in base_splits and base_splits[base] != split: raise ValueError("base split leakage")
                        base_splits[base] = split
                        recording = from_episode(episode,archive=str((directory/"traces.zip").relative_to(ROOT)),member=case["trace"],source_sha256=sha(raw))
                        header,rows,stats = parse(recording)
                        if header["recording_id"] in identity_seen: raise ValueError("recording split overlap")
                        identity_seen.add(header["recording_id"]); collected.append((header,rows))
                        name = split+"-"+header["recording_id"]+".jsonl.gz"; output.writestr(name,recording)
                        report["recordings"].append({"split":split,"member":name,"sha256":sha(recording),"header":header,"stats":stats,
                            "omitted_partial_terminal_snapshots":len(episode["frames"])-len(rows)})
                data,metadata,skipped = pairs(collected); splits[split] = (data,metadata)
                if not len(data["action"]): raise ValueError("empty recorded pair split")
                write_archive(D/f"{split}.npz",data)
                report["datasets"][split] = {"rows":len(data["action"]),"episodes":metadata,"skipped_intervals":skipped,"logical_sha256":logical_hash(data,metadata)}
                print("sensor recordings",split,len(collected),"pairs",len(data["action"]),"skipped",skipped,flush=True)
        train,tm = splits["train"]; validation,vm = splits["validation"]; evaluation,em = splits["evaluation"]
        model,training = fit(train,tm,budget); training["training_dataset_sha256"] = logical_hash(train,tm)
        save(D/"sensor.pt",model,training); write(D/"training.json",training)
        model,_ = load(D/"sensor.pt"); vp = predict(model,validation); ep = predict(model,evaluation)
        write_archive(D/"validation-predictions.npz",vp); write_archive(D/"evaluation-predictions.npz",ep)
        errors = measurements(validation,vp); usable = vp["input_usable"]; trades = []
        if usable.any():
            for percentile in (10,25,50,75,90,100):
                threshold = float(np.percentile(vp["disagreement"][usable],percentile)); accepted = usable&(vp["disagreement"] <= threshold)
                trades.append({"percentile":percentile,"threshold":threshold,"accepted":int(accepted.sum()),"coverage":float(accepted.mean()),"high_error_fraction":float(errors["high"][accepted].mean())})
        eligible = [r for r in trades if r["accepted"] >= 100 and r["high_error_fraction"] <= .1]
        chosen = max(eligible,key=lambda r:r["coverage"]) if eligible else None
        threshold = chosen["threshold"] if chosen else None
        accepted = ep["input_usable"]&(ep["disagreement"] <= threshold) if threshold is not None else np.zeros(len(evaluation["action"]),dtype=bool)
        persistence = {"observation":evaluation["observation"].copy()}; persistence["observation"][:,13] += .1
        raw_metric = metric(evaluation,ep); accepted_metric = metric(evaluation,ep,accepted); baseline = metric(evaluation,persistence,accepted)
        benefit = any(accepted_metric[name] is not None and baseline[name] is not None and baseline[name] > 0 and accepted_metric[name] <= .9*baseline[name] for name in ("speed_mean","height_mean"))
        families = []
        for family in sorted({e["family"] for e in em}):
            ids = [e["id"] for e in em if e["family"] == family]; mask = np.isin(evaluation["recording_id"],ids)
            measured = metric(evaluation,ep,mask&accepted)
            families.append({"family":family,"input_usable_rows":int((mask&ep["input_usable"]).sum()),"accepted":measured,
                "supported":bool(measured["rows"] >= 20 and measured["high_mean"] <= .1)})
        finite = bool(np.isfinite(ep["observation"]).all() and (ep["observation"][:,15:40] >= 0).all() and ((ep["observation"][:,40:65] >= 0)&(ep["observation"][:,40:65] <= 1)).all())
        report.update(calibration={"split":"validation","tradeoffs":trades,"threshold":threshold},raw=raw_metric,accepted=accepted_metric,persistence_same_accepted=baseline,
                      beats_persistence=bool(benefit),families=families,finite_nonnegative_probability_bounds=finite,
                      gate_passed=bool(finite and accepted_metric["rows"] >= 100 and accepted_metric["high_mean"] <= .1 and benefit),complete=True)
        if sum(p.stat().st_size for p in D.rglob("*") if p.is_file()) > 64*1024**2: raise TimeoutError("artifact_cap")
    except TimeoutError as error: report["budget_stop"] = str(error)
    except Exception as error: report["errors"].append(type(error).__name__+": "+str(error))
    report["cost"] = budget.report(); seal(D,report); print("sensor result",report["complete"],report.get("gate_passed"),report["errors"],report["budget_stop"],report["cost"],flush=True)
    if not report["complete"] or report["errors"] or report["budget_stop"]: raise SystemExit(1)


if __name__ == "__main__": execute()
