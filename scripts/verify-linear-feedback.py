"""Verify retained learned-feedback actions without loading a numerical library."""
import importlib.util
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = ROOT/"docs/phase-11/linear-feedback-evidence"


def module(name,path):
    spec = importlib.util.spec_from_file_location(name,path); value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


def verify():
    base = module("progress_check",ROOT/"scripts/verify-progress-control.py")
    numpy = module("forecast_arrays",ROOT/"scripts/verify-forecast-refit.py")
    report = base.capsule(D,current=True); plan = report["plan"]; fitted = report["fit"]
    assert not report["runtime_admitted"] and report["optimiser_updates"] == 0
    assert report["training_label_queries"] == report["evaluation_label_queries"] == 0
    assert fitted == json.loads((D/"fit.json").read_text()) and fitted["least_squares_solves"] == 4
    assert fitted["ranks"] == [3,1,1,1] and fitted["max_training_action_error"] <= 1e-10
    assert base.sha((D/"feedback.pt").read_bytes()) == (D/"feedback.pt.sha256").read_text().strip()
    assert base.sha((D/"training.npz").read_bytes()) == fitted["training_data_sha256"]
    data = numpy.npz(D/"training.npz",("features","labels")); weights = fitted["weight_matrix"]
    assert len(data["features"]) == fitted["training_rows"] == sum(c["rows"] for c in report["included_training"])
    def action(features): return [max(-1.,min(1.,sum(a*b for a,b in zip(row,features)))) for row in weights]
    for features,label in zip(data["features"],data["labels"]): assert max(abs(a-b) for a,b in zip(action(features),label)) <= 1e-10
    families = plan["families"]; assert len(families) == 13 and len(report["cases"]) == 26
    assert {(c["source"],c["family"]) for c in report["cases"]} == {(s,f) for s in ("reference","learned_linear") for f in families}
    physical = replay = 0; gates = []
    for case,payload in base.payloads(D,report):
        assert payload["scenario"]["seed"] == 19023 and payload["evaluation"] == case["evaluation"]
        physical += case["outcome"]["decisions"]; criterion = case["evaluation"]["criterion"]
        passed = base.stopping(payload["frames"],case["outcome"]["done"],.3 if case["family"] == "range_dropout" else .1) if criterion == "stop" else case["outcome"]["full_success"] and not case["outcome"]["collision"]
        assert case["evaluation"]["passed"] == passed; gates.append(passed)
        if case["source"] == "learned_linear":
            replay += case["outcome"]["decisions"]; calls = 0
            assert payload["checkpoint_sha256"] == base.sha((D/"feedback.pt").read_bytes())
            for f in payload["frames"][:-1]:
                supervisor = f["supervision"]
                assert supervisor["proposal_source"] == "learned_linear_feedback"
                if not supervisor["override"]:
                    expected = action(supervisor["task"]["control_features"])
                    assert max(abs(a-b) for a,b in zip(expected,f["action"])) <= 1e-10
                    calls += 1
            assert payload["neural_queries"] == payload["action_replay_queries"] == case["neural_queries"] == calls
            assert case["same_outcome"]
    assert report["gate_passed"] == all(gates) and report["max_replay_state_error"] == 0
    assert report["cost"]["counts"] == {"environment":physical,"teacher":physical,"replay":replay}
    assert physical <= 16000 and replay <= 8000 and report["cost"]["wall_s"] <= 180
    print("Linear feedback: fitted gains and every applied learned action verified; matched task outcomes retained; full gate:",report["gate_passed"])


if __name__ == "__main__": verify()
