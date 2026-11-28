"""Verify the bounded collection comparison, including retained failed gates."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = ROOT/"docs/phase-11/collection-coverage-evidence"


def module(name,path):
    spec = importlib.util.spec_from_file_location(name,path); value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


def verify():
    base = module("progress_check",ROOT/"scripts/verify-progress-control.py")
    report = base.capsule(D,current=True); plan = report["plan"]
    assert not report["runtime_admitted"] and report["weight_updates"] == 0
    weights_dir = ROOT/"docs/phase-11/linear-feedback-evidence"
    assert base.sha((weights_dir/"feedback.pt").read_bytes()) == plan["checkpoint_sha256"]
    weights = json.loads((weights_dir/"fit.json").read_text())["weight_matrix"]
    scores = [{"variant":i,"passed":0,"collisions":0} for i in range(2)]
    assert len(report["cases"]) == 54
    assert {(c["variant"],c["family"],c["seed"]) for c in report["cases"] if c["split"] == "development"} == {(i,f,s) for i in range(2) for f,s in plan["development"]}
    jobs = {(f,None) for f in plan["families"]}|{("nominal",p) for p in plan["patterns"]}
    assert {(c["source"],c["family"],c["pattern"]) for c in report["cases"] if c["split"] == "evaluation"} == {(s,f,p) for s in ("reference","learned_linear") for f,p in jobs}
    count = replay = 0; gates = []
    for case,value in base.payloads(D,report):
        count += case["outcome"]["decisions"]
        assert value["evaluation"] == case["evaluation"] and value["scenario"]["seed"] == case["seed"]
        delay = .3 if case["family"] == "range_dropout" or case["pattern"] == "carry_loss" else .1
        passed = base.stopping(value["frames"],case["outcome"]["done"],delay) if case["evaluation"]["criterion"] == "stop" else case["outcome"]["full_success"] and not case["outcome"]["collision"]
        if case["pattern"] == "recovery": passed &= bool(case["evaluation"]["fault_trigger_s"] is not None and case["evaluation"]["resumed"] and case["evaluation"]["override_decisions"])
        assert passed == case["evaluation"]["passed"]
        if case["split"] == "development":
            scores[case["variant"]]["passed"] += passed; scores[case["variant"]]["collisions"] += case["outcome"]["collision"]
        else:
            assert case["seed"] == 19024 and case["variant"] == report["selected"]["variant"]
            replay += case["outcome"]["decisions"]; gates.append(passed)
        if case["source"] == "learned_linear":
            queries = 0; assert case["same_outcome"]
            for frame in value["frames"][:-1]:
                control = frame["supervision"]
                if control["override"]: continue
                features = control["task"]["control_features"]
                expected = [max(-1,min(1,sum(a*b for a,b in zip(row,features)))) for row in weights]
                assert max(abs(a-b) for a,b in zip(expected,frame["action"])) <= 1e-10
                queries += 1
            assert queries == value["neural_queries"] == value["action_replay_queries"] == case["neural_queries"]
    assert report["selection_scores"] == scores and report["selected"] == max(scores,key=lambda r:(r["passed"],-r["collisions"],-r["variant"]))
    assert report["gate_passed"] == all(gates) and report["max_replay_state_error"] == 0
    assert report["cost"]["counts"] == {"environment":count,"teacher":count,"replay":replay}
    assert count <= 24000 and replay <= 18000 and report["cost"]["wall_s"] <= 300
    print("Collection coverage: both fixed variants, learned actions and complete failed gates verified; final gate:",report["gate_passed"])


if __name__ == "__main__": verify()
