"""Independently check structured-model data, raw errors and forecast gates."""
import gzip
import importlib.util
import json
import math
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
D = ROOT/"docs/phase-11/structured-dynamics-evidence"


def module(name,path):
    spec = importlib.util.spec_from_file_location(name,path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


def verify():
    base = module("progress_check",ROOT/"scripts/verify-progress-control.py")
    arrays = module("forecast_arrays",ROOT/"scripts/verify-forecast-refit.py")
    report = base.capsule(D,current=True); plan = report["plan"]
    assert not report["runtime_admitted"] and not report["assistance_qualified"]
    assert report["teacher_queries"] == report["policy_updates"] == report["assisted_updates"] == 0
    assert sum(p.stat().st_size for p in D.rglob("*") if p.is_file()) <= 96*1024**2
    for name,digest in plan["inputs"].items(): assert base.sha((ROOT/name).read_bytes()) == digest
    assert len(report["collection"]) == 316
    expected = {(split,seed,kind) for split,seeds in (("train",range(19100,19356)),("validation",range(19360,19364)),("evaluation",range(19370,19374)))
                for seed in seeds for kind in ["prepared_collision" if (split == "train" and seed < 19228) or (split != "train" and seed%10 < 2) else "prepared_stuck"]}
    actual = {(c["split"],c["seed"],c["family"]) for c in report["collection"] if not c["reused"]}
    assert actual == expected and len(actual) == 264
    physical = 0; rare = {"prepared_collision":0,"prepared_stuck":0}; identities = set()
    datasets = {split:arrays.npz(D/f"{split}.npz",("state","action","next_state","reward","events","regime","episode_id","step"))
                for split in ("train","validation","evaluation")}
    with zipfile.ZipFile(D/"trajectories.zip") as archive:
        assert set(archive.namelist()) == {c["trace"] for c in report["collection"]}
        for case in report["collection"]:
            raw = archive.read(case["trace"]); assert base.sha(raw) == case["sha256"]
            value = json.loads(gzip.decompress(raw)); frames = value["frames"]; outcome = value["outcome"]
            assert outcome == case["outcome"] and len(frames) == outcome["decisions"]+1 and not value["applied_machine_commands"]
            data = datasets[case["split"]]
            episode, = [e for e in report["datasets"][case["split"]]["episodes"] if e["seed"] == case["seed"] and e["family"] == case["family"]]
            assert episode["stop"]-episode["start"] == outcome["decisions"]
            for step,(current,following) in enumerate(zip(frames,frames[1:])):
                i = episode["start"]+step
                assert current["next_state"] == following["state"] == data["next_state"][i]
                assert current["state"] == data["state"][i] and current["action"] == data["action"][i]
                terminal = outcome["done"] and step == outcome["decisions"]-1
                assert data["events"][i][:2] == [terminal and outcome["reason"] != "time_limit",terminal and outcome["reason"] == "time_limit"]
            if not case["reused"]:
                physical += outcome["decisions"]; assert case["fixture_gate_passed"] and value["fixture_gate_passed"]
                assert outcome["done"] and (outcome["collision"] if case["family"] == "prepared_collision" else outcome["reason"] == "stuck")
                assert value["scenario"]["initial_state_sha256"] not in identities
                identities.add(value["scenario"]["initial_state_sha256"])
                if case["split"] == "train": rare[case["family"]] += 1
    assert rare == {"prepared_collision":128,"prepared_stuck":128} and report["rare_coverage"]["goal_met"]
    assert report["cost"]["counts"] == {"environment":physical,"replay":physical,"updates":2250}
    assert physical <= 20000 and report["cost"]["wall_s"] <= 420
    assert report["max_fixture_replay_state_error"] == 0
    training = json.loads((D/"training.json").read_text())
    assert training["optimiser_updates"] == 2250 and training["training_dataset_sha256"] == report["datasets"]["train"]["logical_sha256"]
    assert [h["seed"] for h in training["bootstrap_histories"]] == [101,211,307]
    assert all(len(h["history"]) == 750 and len(h["episode_draws"]) == 282 for h in training["bootstrap_histories"])
    assert base.sha((D/"structured.pt").read_bytes()) == (D/"structured.pt.sha256").read_text().strip()
    data = datasets["evaluation"]; validation = datasets["validation"]; eligible_methods = []
    assert len(report["methods"]) == 7
    for name,entry in report["methods"].items():
        prediction = arrays.npz(D/f"predictions-{name}.npz",("next_state","reward","events","disagreement"))
        measured = arrays.errors(data,prediction); metric = entry["one_step"]
        assert metric["rows"] == len(data["state"]) and len(entry["drift"]) == 4
        assert all(r["rows"] <= 128 for r in entry["drift"])
        for key,values in (("position_mae_m",measured["position"]),("pile_height_mae_m",measured["pile"]),("reward_mae",measured["reward"]),
                           ("high_error_fraction",measured["high"]),("mass_balance_mae_kg",measured["ledger"])):
            arrays.close(metric[key],arrays.mean(values))
        for column,event in enumerate(("terminated","truncated","contact","collision")):
            pairs = [(p[column],y[column]) for p,y in zip(prediction["events"],data["events"])]
            arrays.close(metric["events"][event]["brier"],arrays.mean([(p-y)**2 for p,y in pairs]))
            assert metric["events"][event]["false_positives"] == sum(p >= .5 and not y for p,y in pairs)
            assert metric["events"][event]["false_negatives"] == sum(p < .5 and y for p,y in pairs)
        if "calibration_gate" not in entry: continue
        gate = entry["calibration_gate"]
        vp = arrays.npz(D/f"validation-predictions-{name}.npz",("next_state","reward","events","disagreement"))
        ve = arrays.errors(validation,vp); scores = sorted(vp["disagreement"])
        for trade in gate["tradeoffs"]:
            index = (len(scores)-1)*trade["percentile"]/100; lo = int(index); hi = math.ceil(index)
            arrays.close(trade["threshold"],scores[lo]+(scores[hi]-scores[lo])*(index-lo))
            accepted = [i for i,s in enumerate(vp["disagreement"]) if s <= trade["threshold"]]
            assert len(accepted) == trade["accepted"]
            arrays.close(trade["accepted_high_error_fraction"],arrays.mean([ve["high"][i] for i in accepted]))
        candidates = [r for r in gate["tradeoffs"] if r["accepted"] >= 20 and r["accepted_high_error_fraction"] <= .1]
        selected = max(candidates,key=lambda r:r["coverage"]) if candidates else None
        assert gate["threshold"] == (selected["threshold"] if selected else None)
        supported = [r["horizon_decisions"] for r in gate["validation_drift"] if r["rows"] >= 20 and r["position_mae_m"] <= .1
                     and r["state_mae"]["carried_kg"] <= 100 and r["pile_height_mae_m"] <= .02 and r["reward_mae"] <= .1]
        assert gate["supported_horizon"] == (min(2,max(supported)) if selected and supported else 0)
        family_gate = True
        assert len(entry["families"]) == 15
        for family in entry["families"]:
            ids = {e["id"] for e in report["datasets"]["evaluation"]["episodes"] if e["family"] == family["family"]}
            indices = [i for i,e in enumerate(data["episode_id"]) if e in ids]
            accepted = [i for i in indices if gate["threshold"] is not None and prediction["disagreement"][i] <= gate["threshold"]]
            operational = [i for i in accepted if not measured["invalid"][i]]
            raw = family["forecast_gate"]
            assert raw["accepted"] == len(accepted) and raw["missed_high_error_cases"] == sum(measured["high"][i] for i in accepted)
            assert family["operational_accepted"] == len(operational) and family["operational_missed_high_error"] == sum(measured["high"][i] for i in operational)
            if family["family"] != "blocked": family_gate &= bool(accepted and operational and arrays.mean([measured["high"][i] for i in accepted]) <= .1 and arrays.mean([measured["high"][i] for i in operational]) <= .1)
        qualifies = bool(gate["supported_horizon"] >= 1 and family_gate and report["rare_coverage"]["goal_met"])
        assert entry["forecast_eligible"] == qualifies
        if qualifies: eligible_methods.append(name)
    assert sorted(eligible_methods) == sorted(report["forecast_eligible_methods"])
    print("Structured dynamics: rare coverage, complete transitions, errors and all-family gates verified; eligible:",eligible_methods)


if __name__ == "__main__": verify()
