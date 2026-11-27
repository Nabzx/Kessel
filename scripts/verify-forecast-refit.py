"""Recompute retained forecast errors and acceptance counts with the standard library."""
import ast
import gzip
import hashlib
import json
import math
from pathlib import Path
import struct
import zipfile

ROOT = Path(__file__).resolve().parents[1]
D = ROOT/"docs/phase-11/working-policy-refit-evidence"


def sha(raw): return hashlib.sha256(raw).hexdigest()


def npz(path,names):
    result = {}
    with zipfile.ZipFile(path) as archive:
        for name in names:
            raw = archive.read(name+".npy"); assert raw[:6] == b"\x93NUMPY"
            major = raw[6]; width = 2 if major == 1 else 4; start = 8+width
            size = int.from_bytes(raw[8:start],"little"); header = ast.literal_eval(raw[start:start+size].decode().strip())
            assert not header["fortran_order"] and len(header["shape"]) in (1,2)
            code = {"<f8":"d","<f4":"f","<i8":"q","<i4":"i","|b1":"?"}[header["descr"]]
            values = [v[0] for v in struct.iter_unpack("<"+code,raw[start+size:])]
            assert len(values) == math.prod(header["shape"])
            if len(header["shape"]) == 2:
                columns = header["shape"][1]; values = [values[i:i+columns] for i in range(0,len(values),columns)]
            result[name] = values
    return result


def errors(data,prediction):
    high = []; positions = []; carried = []; piles = []; rewards = []; masses = []; invalid = []
    for s,t,r,y in zip(prediction["next_state"],data["next_state"],prediction["reward"],data["reward"]):
        position = math.hypot(s[0]-t[0],s[1]-t[1]); mass = abs(s[7]-t[7]); pile = sum(abs(a-b) for a,b in zip(s[15:79],t[15:79]))/64
        reward = abs(r-y); ledger = sum(s[15:79])*.25*s[81]+sum(s[7:10])-s[82]
        physical = any(v < -1e-6 for v in s[7:10]+s[15:79]) or s[7] > 3500.001
        physical |= abs(s[4]) > .601 or not -.101 <= s[5] <= 1.101 or not -.701 <= s[6] <= 1.001 or not -1.501 <= s[3] <= 2.001
        physical |= abs(ledger) > 25 or not all(math.isfinite(v) for v in s)
        positions.append(position); carried.append(mass); piles.append(pile); rewards.append(reward); masses.append(abs(ledger)); invalid.append(physical)
    for i in range(len(positions)):
        wrong = (prediction["events"][i][0] >= .5) != bool(data["events"][i][0])
        high.append(positions[i] > .05 or carried[i] > 50 or piles[i] > .01 or rewards[i] > .05 or wrong)
    return {"high":high,"position":positions,"carried":carried,"pile":piles,"reward":rewards,"ledger":masses,"invalid":invalid}


def mean(values): return sum(values)/len(values)
def close(a,b): assert math.isclose(a,b,rel_tol=1e-7,abs_tol=1e-8),(a,b)


def verify():
    manifest = json.loads((D/"files.json").read_text())
    for name,digest in manifest.items(): assert sha((ROOT/name).read_bytes()) == digest,name
    assert sum((ROOT/name).stat().st_size for name in manifest) < 64*1024**2
    report = json.loads((D/"report.json").read_text()); plan = report["plan"]
    assert plan == json.loads((D/"plan.json").read_text()) and report["complete"]
    assert not report["errors"] and report["budget_stop"] is None
    assert not report["runtime_admitted"] and not report["assistance_qualified"]
    assert report["teacher_queries"] == report["policy_updates"] == report["assisted_updates"] == 0
    assert plan["cpu_threads"] == 1 and report["cost"]["wall_s"] <= report["cost"]["wall_cap_s"] == 300
    assert report["cost"]["limits"] == {"environment":31200,"updates":6000}
    assert report["cost"]["counts"]["environment"] <= 31200 and report["cost"]["counts"]["updates"] <= 6000
    with zipfile.ZipFile(D/"source.zip") as archive:
        assert set(archive.namelist()) == set(plan["files"])
        for name,digest in plan["files"].items(): assert sha(archive.read(name)) == sha((ROOT/name).read_bytes()) == digest,name
    expected = {(split,seed,family) for split,seeds in (("train",[19010,19011]),("validation",[19012]),("evaluation",[19013])) for seed in seeds for family in plan["families"]}
    assert len(report["collection"]) == 52 and {(c["split"],c["seed"],c["family"]) for c in report["collection"]} == expected
    with zipfile.ZipFile(D/"trajectories.zip") as archive:
        assert set(archive.namelist()) == {c["trace"] for c in report["collection"]}
        for c in report["collection"]:
            raw = archive.read(c["trace"]); assert sha(raw) == c["sha256"]
            trace = json.loads(gzip.decompress(raw)); frames = trace["frames"]
            assert trace["outcome"] == c["outcome"] and len(frames) == c["outcome"]["decisions"]+1
            assert frames[0]["state"][7] == 0 and not trace["applied_machine_commands"]
            for current,following in zip(frames,frames[1:]): assert current["next_state"] == following["state"]
    assert report["cost"]["counts"]["environment"] == sum(c["outcome"]["decisions"] for c in report["collection"] if not c["reused"])
    data = npz(D/"evaluation.npz",("state","next_state","reward","events","episode_id"))
    validation = npz(D/"validation.npz",("state","next_state","reward","events","episode_id"))
    assert len(data["state"]) == report["datasets"]["evaluation"]["rows"]
    eligible_methods = []
    for name,entry in report["methods"].items():
        fields = ["next_state","reward","events","disagreement"]
        if name == "refit_bounded_filter": fields.append("filter_rejected")
        predicted = npz(D/f"predictions-{name}.npz",fields); measured = errors(data,predicted); metric = entry["one_step"]
        assert metric["rows"] == len(data["state"])
        for key,values in (("position_mae_m",measured["position"]),("pile_height_mae_m",measured["pile"]),
                           ("reward_mae",measured["reward"]),("high_error_fraction",measured["high"]),("mass_balance_mae_kg",measured["ledger"])):
            close(metric[key],mean(values))
        for column,event in enumerate(("terminated","truncated","contact","collision")):
            probability = [r[column] for r in predicted["events"]]; labels = [r[column] for r in data["events"]]
            close(metric["events"][event]["brier"],mean([(p-y)**2 for p,y in zip(probability,labels)]))
            assert metric["events"][event]["false_positives"] == sum(p >= .5 and not y for p,y in zip(probability,labels))
            assert metric["events"][event]["false_negatives"] == sum(p < .5 and y for p,y in zip(probability,labels))
        if "calibration_gate" not in entry: continue
        gate = entry["calibration_gate"]; val_predicted = npz(D/f"validation-predictions-{name}.npz",fields)
        val_error = errors(validation,val_predicted); scores = sorted(val_predicted["disagreement"])
        for trade in gate["tradeoffs"]:
            index = (len(scores)-1)*trade["percentile"]/100; lower = int(index); upper = math.ceil(index)
            close(trade["threshold"],scores[lower]+(scores[upper]-scores[lower])*(index-lower))
            accepted = [i for i,s in enumerate(val_predicted["disagreement"]) if s <= trade["threshold"]]
            assert len(accepted) == trade["accepted"]; close(trade["accepted_high_error_fraction"],mean([val_error["high"][i] for i in accepted]))
        eligible = [r for r in gate["tradeoffs"] if r["accepted"] >= 20 and r["accepted_high_error_fraction"] <= .1]
        selected = max(eligible,key=lambda r:r["coverage"]) if eligible else None
        assert gate["threshold"] == (selected["threshold"] if selected else None)
        family_gate = True
        for family in entry["families"]:
            episodes = [e for e in report["datasets"]["evaluation"]["episodes"] if e["family"] == family["family"]]
            ids = {e["id"] for e in episodes}; indices = [i for i,e in enumerate(data["episode_id"]) if e in ids]
            accepted = [i for i in indices if gate["threshold"] is not None and predicted["disagreement"][i] <= gate["threshold"]]
            raw = family["forecast_gate"]; assert raw["accepted"] == len(accepted)
            assert raw["missed_high_error_cases"] == sum(measured["high"][i] for i in accepted)
            operational = [i for i in accepted if not measured["invalid"][i] and not predicted.get("filter_rejected",[False]*len(data["state"]))[i]]
            assert family["operational_accepted"] == len(operational)
            assert family["operational_missed_high_error"] == sum(measured["high"][i] for i in operational)
            if family["family"] != "blocked":
                family_gate &= bool(accepted and mean([measured["high"][i] for i in accepted]) <= .1 and operational and mean([measured["high"][i] for i in operational]) <= .1)
        qualifies = bool(gate["supported_horizon"] >= 1 and family_gate)
        assert entry["forecast_eligible"] == qualifies
        if qualifies: eligible_methods.append(name)
    assert sorted(report["forecast_eligible_methods"]) == sorted(eligible_methods)
    state_training = json.loads((D/"state-training.json").read_text())
    assert state_training["normalisers_fitted_on"] == "training_only" and len(state_training["episode_bootstraps"]) == 3
    assert state_training["training_dataset_sha256"] == report["datasets"]["train"]["logical_sha256"]
    assert state_training["configuration"]["epochs"] == 30 and state_training["configuration"]["hidden"] == 64
    assert report["rare_failure_training_goal"]["target_per_class"] == 128 and not report["rare_failure_training_goal"]["met"]
    print("Forecast refit: 52 isolated practice episodes; raw errors, validation-only calibration and all-family eligibility recomputed; eligible:",eligible_methods)


if __name__ == "__main__": verify()
