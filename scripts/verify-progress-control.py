"""Verify adaptive practice provenance and frozen conventional task/stop results."""
import gzip
import hashlib
import json
import math
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/"docs/phase-11/progress-development-evidence"
D = ROOT/"docs/phase-11/progress-validation-evidence"


def sha(raw): return hashlib.sha256(raw).hexdigest()


def capsule(directory,current=False):
    manifest = json.loads((directory/"files.json").read_text())
    for name,digest in manifest.items(): assert sha((ROOT/name).read_bytes()) == digest,name
    report = json.loads((directory/"report.json").read_text()); plan = report["plan"]
    assert plan == json.loads((directory/"plan.json").read_text()) and report["complete"]
    assert not report["errors"] and report["budget_stop"] is None and plan["cpu_threads"] == 1
    with zipfile.ZipFile(directory/"source.zip") as archive:
        assert set(archive.namelist()) == set(plan["files"])
        for name,digest in plan["files"].items():
            assert sha(archive.read(name)) == digest
            if current: assert sha((ROOT/name).read_bytes()) == digest,name
    return report


def payloads(directory,report):
    with zipfile.ZipFile(directory/"traces.zip") as archive:
        assert set(archive.namelist()) == {c["trace"] for c in report["cases"]}
        for c in report["cases"]:
            raw = archive.read(c["trace"]); assert sha(raw) == c["sha256"]
            value = json.loads(gzip.decompress(raw)); outcome = value["outcome"]; frames = value["frames"]
            assert outcome == c["outcome"] and len(frames) == outcome["decisions"]+1
            assert frames[0]["state"][7] == outcome["initial_payload_kg"] == 0 and not value["applied_machine_commands"]
            assert outcome["full_success"] == (outcome["reason"] == "success")
            if outcome["full_success"]: assert outcome["delivered_kg"] >= 2000 and not outcome["collision"]
            for i,f in enumerate(frames):
                s = f["state"]; assert len(s) == 102 and all(math.isfinite(v) for v in s)
                assert abs(sum(s[15:79])*.25*s[81]+sum(s[7:10])-s[82]) < 1e-7
                if i == len(frames)-1: continue
                assert f["next_state"] == frames[i+1]["state"] and len(f["action"]) == 4
                assert all(math.isfinite(v) and abs(v) <= 1 for v in f["action"])
                assert f["observation"]["proprio"][13] == f["t_s"] == s[10]
            yield c,value


def stopping(frames,done,delay):
    first = next((i for i,f in enumerate(frames[:-1]) if f["fault"]["active"]),None)
    if first is None: return False
    samples = [f["state"] for f in frames[first:]]
    settled = next((i for i in range(2,len(samples)) if all(abs(s[3]) <= .08 for s in samples[i-2:i+1])),None)
    detected = next((f["t_s"] for f in frames[first:-1] if f["supervision"]["override"]),None)
    if settled is None or detected is None: return False
    path = [math.dist(a[:2],b[:2]) for a,b in zip(samples,samples[1:])]
    return bool(detected-samples[0][10] <= delay+1e-8 and samples[settled][10]-samples[0][10] <= 2.5+1e-8
        and sum(path[:settled]) <= 2 and samples[-1][10]-samples[settled][10] >= 10.-1e-8
        and sum(path[settled:]) <= .25 and max(abs(s[3]) for s in samples[settled:]) <= .1 and not done)


def verify():
    decisions = 0; wall = 0.; scores = []
    for revision in range(1,9):
        directory = BASE/f"revision-{revision}"; report = capsule(directory)
        assert report["plan"]["preceding_decisions"] == decisions
        assert math.isclose(report["plan"]["preceding_wall_s"],wall,abs_tol=1e-9)
        count = passed = collisions = 0
        for c,value in payloads(directory,report):
            assert c["seed"] in (19020,19021); count += c["outcome"]["decisions"]
            if "evaluation" in value: passed += value["evaluation"]["passed"]
            else: passed += c["outcome"]["full_success"]
            collisions += c["outcome"]["collision"]
        assert report["cost"]["counts"] == {"environment":count,"teacher":count}
        decisions += count; wall += report["cost"]["wall_s"]
        assert decisions <= 40000 and wall <= 300
        if revision in (7,8): scores.append({"revision":revision,"gain":report["plan"]["lateral_gain"],"passed":passed,"collisions":collisions})
    report = capsule(D,current=True); plan = report["plan"]
    selected = max(scores,key=lambda s:(s["passed"],-s["collisions"],s["gain"]))
    assert plan["selected"] == selected and plan["selection_scores"] == scores and plan["seed"] == 19022
    assert len(report["cases"]) == len(plan["jobs"]) == 18
    assert {(c["family"],c["pattern"]) for c in report["cases"]} == {(f,p) for f,p in plan["jobs"]}
    count = 0; gates = []
    for case,value in payloads(D,report):
        assert value["source"] == "conventional_progress_task" and value["neural_queries"] == 0
        count += case["outcome"]["decisions"]; evaluation = value["evaluation"]
        assert evaluation == case["evaluation"]
        if evaluation["criterion"] == "stop":
            passed = stopping(value["frames"],case["outcome"]["done"],.3 if case["pattern"] == "carry_loss" or case["family"] == "range_dropout" else .1)
            assert not case["outcome"]["full_success"]
        else:
            passed = case["outcome"]["full_success"] and not case["outcome"]["collision"]
            if case["pattern"] == "recovery": passed &= bool(evaluation["fault_trigger_s"] is not None and evaluation["override_decisions"] and evaluation["resumed"])
        assert evaluation["passed"] == passed; gates.append(passed)
    assert report["gate_passed"] == all(gates) and not report["runtime_admitted"]
    assert report["cost"]["counts"] == {"environment":count,"teacher":count,"replay":count} and count <= 12000
    assert report["cost"]["wall_s"] <= 180 and report["max_replay_state_error"] == 0
    print("Progress controller: 128 retained practice cases and 18 frozen delivery/stop/recovery checks verified; gate:",report["gate_passed"])


if __name__ == "__main__": verify()
