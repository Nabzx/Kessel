"""Reconstruct screened scope, task outcomes and frozen fresh forecast gates."""
import importlib.util
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/"docs/phase-11/harvest-qualification-evidence"


def module(name,path):
    spec = importlib.util.spec_from_file_location(name,path); value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


def proof(state):
    available = sum(max(h-(.35+2*math.sin(-.1)),0) for h in state[15:79])*.25*state[81]
    mass = 10500.; grip = state[83]*mass*9.81*math.cos(state[84])
    margin = min(22000.,grip)-mass*9.81*math.sin(state[84])*math.cos(state[2])-.02*mass*9.81*math.cos(state[84])
    return available,margin


def verify():
    base = module("progress_check",ROOT/"scripts/verify-progress-control.py")
    numpy = module("forecast_arrays",ROOT/"scripts/verify-forecast-refit.py")
    reservation = json.loads((BASE/"reservation.json").read_text())
    assert reservation["verified"] and not reservation["hits"] and not reservation["errors"] and reservation["new_policy_queries"] == 0
    assert reservation["seeds"] == list(range(207400,207432)) and reservation["rare_seeds"] == list(range(207450,207466))
    assert reservation["guard_seeds"] == list(range(207470,207478)) and reservation["audit_wall_s"] <= 250
    original = json.loads((BASE/"reservation-attempt-1.json").read_text())
    assert not original["verified"] and not original["hits"] and len(original["errors"]) == 1
    assert reservation["original_certificate_sha256"] == base.sha((BASE/"reservation-attempt-1.json").read_bytes())
    assert reservation["original_errors"] == original["errors"] and reservation["inventory"] == original["inventory"]
    assert reservation["identities"] == original["identities"] and reservation["selected_by_family"] == original["selected_by_family"]
    correction = reservation["correction"]
    assert correction["literal_utf8"] == "data/example.json" and correction["sha256"] == base.sha(b"data/example.json")
    assert correction["location"] == original["errors"][0]["location"] and correction["sha256"] in original["inventory"]
    assert original["worker_wall_s"] <= 235 and reservation["original_parent_wall_s"] <= 240 and correction["wall_s"] <= 10
    assert correction["new_policy_queries"] == correction["new_physics_queries"] == 0
    assert len(reservation["identities"]) == 440 and reservation["inventory"]
    for name,digest in reservation["audit_files"].items(): assert base.sha((ROOT/name).read_bytes()) == digest
    for family,seeds in reservation["selected_by_family"].items():
        rows = [r for r in reservation["identities"] if r["family"] == family]
        assert [r["seed"] for r in rows if r["certificate"]["supported"]][:8] == seeds and len(seeds) == 8
        for row in rows:
            certificate = row["certificate"]
            assert certificate["supported"] == (certificate["available_above_blade_kg"] >= 3200 and certificate["empty_forward_margin_n"] >= 200)
    fit_dir = ROOT/"docs/phase-11/linear-feedback-evidence"
    weights = json.loads((fit_dir/"fit.json").read_text())["weight_matrix"]
    forecast_dir = ROOT/"docs/phase-11/structured-dynamics-evidence"
    for fresh in (False,True):
        directory = BASE/"fresh" if fresh else ROOT/"docs/phase-11/harvest-practice-evidence"
        report = base.capsule(directory,current=True); plan = report["plan"]
        assert not report["runtime_admitted"] and report["weight_updates"] == report["evaluation_label_queries"] == report["forecast_assisted_actions"] == 0
        assert plan["feedback_sha256"] == base.sha((fit_dir/"feedback.pt").read_bytes())
        assert plan["forecast_sha256"] == base.sha((forecast_dir/"structured.pt").read_bytes())
        assert plan["forecast_report_sha256"] == base.sha((forecast_dir/"report.json").read_bytes())
        assert sum(p.stat().st_size for p in directory.rglob("*") if p.is_file()) <= 96*1024**2
        assert {(c["source"],c["family"],c["pattern"],c["seed"],c["split"]) for c in report["cases"]} == {tuple(j) for j in plan["jobs"]}
        assert len(report["cases"]) == (304 if fresh else 42) and len(report["fixtures"]) == (16 if fresh else 0)
        if fresh: assert plan["reservation_sha256"] == base.sha((BASE/"reservation.json").read_bytes())
        physical = planning = 0; passed = []; payload_by_key = {}
        combined = {"cases":report["cases"]+report["fixtures"]}
        for case,value in base.payloads(directory,combined):
            physical += case["outcome"]["decisions"]
            if case in report["fixtures"]:
                assert case["fixture_gate_passed"] and value["fixture_gate_passed"]
                assert (case["outcome"]["collision"] if case["family"] == "prepared_collision" else case["outcome"]["reason"] == "stuck")
                continue
            planning += case["outcome"]["decisions"]; state = value["frames"][0]["state"]
            available,margin = proof(state); certificate = case["certificate"]
            numpy.close(certificate["available_above_blade_kg"],available); numpy.close(certificate["empty_forward_margin_n"],margin)
            assert certificate["supported"] == (available >= 3200 and margin >= 200) and not certificate["controller_input"]
            if fresh and case["split"] != "start_guard_challenge": assert certificate["supported"] and case["seed"] in reservation["selected_by_family"][case["family"]]
            assert case["evaluation"] == value["evaluation"]
            delay = .3 if case["family"] == "range_dropout" or case["pattern"] == "carry_loss" else .1
            criterion = case["evaluation"]["criterion"]
            ok = base.stopping(value["frames"],case["outcome"]["done"],delay) if criterion == "stop" else case["outcome"]["full_success"] and not case["outcome"]["collision"]
            if case["pattern"] == "recovery": ok &= bool(case["evaluation"]["resumed"] and case["evaluation"]["fault_trigger_s"] is not None)
            assert ok == case["evaluation"]["passed"]; passed.append(ok)
            refusal = case["evaluation"]["proposed_refusal"]
            if refusal:
                assert refusal["passed"] == base.stopping(value["frames"],case["outcome"]["done"],.1)
                assert not case["outcome"]["full_success"] and case["outcome"]["delivered_kg"] == 0 and criterion == "delivery" and not ok
                first = next(i for i,f in enumerate(value["frames"][:-1]) if f["supervision"]["proposal_source"] == "conventional_initial_no_progress_hold")
                assert first >= 30
                for f in value["frames"][first: -1]:
                    assert f["fault"]["cause"] == "initial_no_progress" and f["supervision"]["override"]
                    assert f["supervision"]["proposal_source"] == "conventional_initial_no_progress_hold"
            if case["source"] == "learned_linear":
                calls = 0
                for f in value["frames"][:-1]:
                    control = f["supervision"]
                    if control["override"]: continue
                    assert control["proposal_source"] == "learned_linear_feedback"
                    features = control["task"]["control_features"]
                    expected = [max(-1,min(1,sum(a*b for a,b in zip(row,features)))) for row in weights]
                    assert max(abs(a-b) for a,b in zip(expected,f["action"])) <= 1e-10
                    calls += 1
                assert calls == case["neural_queries"] == value["neural_queries"] == value["action_replay_queries"]
            payload_by_key[case["source"],case["family"],case["pattern"],case["seed"]] = value
        assert report["original_full_gate"] == all(passed) and report["max_replay_state_error"] == 0
        assert report["cost"]["counts"] == {"environment":physical,"teacher":planning,"replay":physical}
        cap = 100000 if fresh else 12000
        assert physical <= cap and report["cost"]["wall_s"] <= (900 if fresh else 180)
        for group in report["groups"]:
            cases = [c for c in report["cases"] if c["split"] not in ("known_regression","start_guard_challenge") and (c["source"],c["family"],c["pattern"]) == (group["source"],group["family"],group["pattern"])]
            supported = [c for c in cases if c["certificate"]["supported"] or c["evaluation"]["criterion"] == "stop"]
            assert group["scheduled"] == len(cases) and group["supported"] == len(supported)
            assert group["supported_passed"] == sum(c["evaluation"]["passed"] for c in supported)
            assert group["passed"] == (len(supported) >= (8 if fresh else 0) and all(c["evaluation"]["passed"] for c in supported))
        known = [c for c in report["cases"] if c["split"] == "known_regression" and (c["family"],c["seed"]) != ("low_grip",19024)]
        scope_gate = all(g["passed"] for g in report["groups"]) and all(c["evaluation"]["passed"] for c in known) and not any(c["outcome"]["collision"] for c in report["cases"])
        assert report["supported_envelope_gate"] == scope_gate
        if not fresh: continue
        challenges = [c for c in report["cases"] if c["split"] == "start_guard_challenge"]
        assert report["start_guard_qualified"] == (len(challenges) == 16 and all(c["evaluation"]["proposed_refusal"] and c["evaluation"]["proposed_refusal"]["passed"] for c in challenges))
        data = numpy.npz(directory/"forecast-data.npz",("state","next_state","reward","events","episode_id"))
        prediction = numpy.npz(directory/"forecast-predictions.npz",("next_state","reward","events","disagreement"))
        entry = report["forecast"]; measured = numpy.errors(data,prediction); metric = entry["one_step"]
        assert len(entry["episodes"]) == 128 and len(data["state"]) == entry["rows"] == metric["rows"]
        assert [r["horizon_decisions"] for r in entry["drift"]] == [1,2,4,8] and all(r["rows"] <= 128 for r in entry["drift"])
        for key,values in (("position_mae_m",measured["position"]),("pile_height_mae_m",measured["pile"]),("reward_mae",measured["reward"]),
                           ("mass_balance_mae_kg",measured["ledger"]),("high_error_fraction",measured["high"])): numpy.close(metric[key],numpy.mean(values))
        gate = json.loads((forecast_dir/"report.json").read_text())["methods"]["structured"]["calibration_gate"]
        assert entry["calibration_gate"] == gate and len(entry["families"]) == 16
        qualified = True
        for family in entry["families"]:
            ids = {e["id"] for e in entry["episodes"] if e["family"] == family["family"]}
            indices = [i for i,e in enumerate(data["episode_id"]) if e in ids]
            accepted = [i for i in indices if prediction["disagreement"][i] <= gate["threshold"]]
            operational = [i for i in accepted if not measured["invalid"][i]]
            assert family["forecast_gate"]["accepted"] == len(accepted) and family["operational_accepted"] == len(operational)
            assert family["forecast_gate"]["missed_high_error_cases"] == sum(measured["high"][i] for i in accepted)
            assert family["operational_missed_high_error"] == sum(measured["high"][i] for i in operational)
            if family["family"] != "blocked": qualified &= bool(accepted and operational and numpy.mean([measured["high"][i] for i in accepted]) <= .1 and numpy.mean([measured["high"][i] for i in operational]) <= .1)
        assert entry["gate_passed"] == bool(gate["supported_horizon"] >= 1 and qualified)
    print("Harvest qualification: screened scope, actual actions, separate failed delivery/refusal outcomes and frozen forecast gates verified")


if __name__ == "__main__": verify()
