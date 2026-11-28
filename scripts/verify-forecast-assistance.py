"""Reconstruct the frozen paired comparison without loading numerical libraries."""
import importlib.util
import math
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]
D = ROOT/"docs/phase-11/assistance-comparison-evidence"


def module(name,path):
    spec = importlib.util.spec_from_file_location(name,ROOT/path)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


def physical(s):
    ledger = sum(s[15:79])*.25*s[81]+sum(s[7:10])-s[82]
    return (all(math.isfinite(v) for v in s) and min(s[7:10]+s[15:79]) >= -1e-6
        and s[7] <= 3500.001 and abs(s[4]) <= .601 and -.101 <= s[5] <= 1.101
        and -.701 <= s[6] <= 1.001 and -1.501 <= s[3] <= 2.001 and abs(ledger) <= 25)


def verify():
    base = module("progress_check","scripts/verify-progress-control.py")
    r = base.capsule(D,current=True); p = r["plan"]
    assert not r["runtime_admitted"] and r["teacher_labels"] == r["optimiser_updates"] == 0
    assert len(p["screened"]) == len(r["pairs"]) == 24 and all(c["certificate"]["supported"] for c in p["screened"])
    assert len(r["cases"]) == 48 and r["max_replay_error"] == 0
    expected = {(c["family"],c["seed"],c["pattern"],arm) for c in p["screened"] for arm in p["arms"]}
    assert {(c["family"],c["seed"],c["pattern"],c["arm"]) for c in r["cases"]} == expected
    total = model_rows = changed_total = 0
    for case,value in base.payloads(D,r):
        assert case["evaluation"] == value["evaluation"] and case["evaluation"]["passed"]
        assert not value["applied_action_forecast_influences_action"]
        assert value["candidate_forecasts_influence_actions"] == (case["arm"] == "candidate_refinement")
        rows = cached = changed = 0
        for f in value["frames"][:-1]:
            supervision = f["supervision"]; a = supervision["assistance"]
            assert supervision["applied_action"] == f["action"]
            if supervision["override"]:
                assert a == {"mode":"independent_guard","model_rows":0,"selected":0}
                assert f["action"][1:] == [0,0,0]
                rows += 1; continue
            assert a["mode"] == case["arm"] and a["model_rows"] == 5
            actions = [a["base_proposal"].copy() for _ in range(5)]
            for i,j,delta in ((1,0,.15),(2,0,-.15),(3,3,.15),(4,3,-.15)):
                actions[i][j] = max(-1,min(1,actions[i][j]+delta))
            assert actions == a["candidate_actions"]
            predictions = a["predictions"]; scores = []; accepted = []
            for i,s in enumerate(predictions["next_state"]):
                original = f["state"]
                score = s[7]-original[7]+2*(s[8]-original[8])-5*(s[9]-original[9])-.0001*(s[12]-original[12])
                assert math.isclose(score,a["scores"][i],abs_tol=1e-9)
                scores.append(score)
                accepted.append(physical(s) and predictions["disagreement"][i] <= p["admission"]["forecast_gate"]["threshold"] and predictions["events"][i][3] < .5)
            assert accepted == a["accepted"]
            best = max(range(5),key=lambda i:scores[i] if accepted[i] else -math.inf)
            assert best == a["best"]
            selected = best if case["arm"] == "candidate_refinement" and a["eligible_mode"] and accepted[0] and accepted[best] and scores[best] > scores[0]+5 else 0
            assert a["selected"] == selected and f["action"] == actions[selected]
            assert f["forecast"]["state"] == predictions["next_state"][selected]
            changed += selected != 0; rows += 5; cached += 1
        assert rows == case["model_rows"] == case["replay_model_rows"]
        assert cached == case["cached_applied_predictions"] == case["replay_cached_applied_predictions"]
        assert changed == case["changed_actions"]
        assert case["neural_queries"] == case["replay_neural_queries"] == cached
        total += case["outcome"]["decisions"]; model_rows += 2*rows; changed_total += changed
    reductions = []; no_regression = True
    for pair in r["pairs"]:
        a,b = [next(c for c in r["cases"] if (c["family"],c["seed"],c["pattern"],c["arm"]) == (pair["family"],pair["seed"],pair["pattern"],arm)) for arm in p["arms"]]
        both = a["evaluation"]["criterion"] == "delivery" and a["evaluation"]["passed"] and b["evaluation"]["passed"]
        assert pair["both_deliveries"] == both
        assert pair["baseline_passed"] == a["evaluation"]["passed"] and pair["assisted_passed"] == b["evaluation"]["passed"]
        no_regression &= not pair["baseline_passed"] or pair["assisted_passed"]
        if both:
            reduction = (a["outcome"]["cycle_s"]-b["outcome"]["cycle_s"])/a["outcome"]["cycle_s"]
            assert math.isclose(pair["cycle_reduction_fraction"],reduction,abs_tol=1e-12)
            reductions.append(reduction)
    median = statistics.median(reductions)
    assert r["median_paired_cycle_reduction"] == median and r["no_paired_criterion_regression"] == no_regression
    assert r["benefit_demonstrated"] == (no_regression and not any(c["outcome"]["collision"] for c in r["cases"]) and median >= .1)
    assert r["cost"]["counts"] == {"environment":total,"replay":total,"model_rows":model_rows}
    assert total <= 30000 and model_rows <= 300000 and r["cost"]["wall_s"] <= 600
    print(f"Assistance: 24 exact paired cases, {changed_total} changed actions; median reduction {median:.6%}; benefit {r['benefit_demonstrated']}")


if __name__ == "__main__": verify()
