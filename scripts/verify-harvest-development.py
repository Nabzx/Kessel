"""Verify every adaptive harvest attempt without relabelling failed deliveries."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = ROOT/"docs/phase-11/harvest-development-evidence"


def verify():
    spec = importlib.util.spec_from_file_location("progress_check",ROOT/"scripts/verify-progress-control.py")
    base = importlib.util.module_from_spec(spec); spec.loader.exec_module(base)
    physical = replay = 0; wall = 0.; cases = 0
    directories = sorted(D.glob("revision-*"),key=lambda p:int(p.name.split("-")[-1]))
    assert [int(p.name.split("-")[-1]) for p in directories] == list(range(1,len(directories)+1)) and len(directories) <= 8
    for directory in directories:
        report = base.capsule(directory); plan = report["plan"]
        assert plan["preceding_decisions"] == physical and plan["preceding_replay"] == replay
        assert abs(plan["preceding_wall_s"]-wall) < 1e-8 and not report["runtime_admitted"]
        assert {(c["family"],c["seed"]) for c in report["cases"]} == {tuple(j) for j in plan["jobs"]}
        count = 0; gates = []
        for case,value in base.payloads(directory,report):
            assert case["evaluation"] == value["evaluation"] and value["neural_queries"] == 0
            count += case["outcome"]["decisions"]; cases += 1
            if case["evaluation"]["criterion"] == "stop":
                passed = base.stopping(value["frames"],case["outcome"]["done"],.3 if case["family"] == "range_dropout" else .1)
            else: passed = case["outcome"]["full_success"] and not case["outcome"]["collision"]
            assert passed == case["evaluation"]["passed"]; gates.append(passed)
        assert report["gate_passed"] == all(gates)
        assert report["cost"]["counts"] == {"environment":count,"teacher":count,"replay":count}
        physical += count; replay += count; wall += report["cost"]["wall_s"]
        assert physical <= 40000 and replay <= 40000 and wall <= 600
    last = base.capsule(directories[-1],current=True)
    for family,seed in (("low",19023),("low_grip",19021)):
        case, = [c for c in last["cases"] if c["family"] == family and c["seed"] == seed]
        assert case["outcome"]["full_success"] and case["outcome"]["delivered_kg"] >= 2000 and case["outcome"]["cycle_s"] <= 60
    print("Harvest development:",cases,"complete cases, repaired low-pile and recoverable low-grip deliveries; failed gates preserved")


if __name__ == "__main__": verify()
