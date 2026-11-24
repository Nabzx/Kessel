"""Verify the bounded missing-range pilot, including failures and nonterminal holds."""
import gzip
import hashlib
import json
import math
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
D = ROOT/"docs/phase-11/range-supervisor-evidence"
METHOD = "missing_range_supervisor"
PERMANENT = {"reset_loss","approach_loss","fill_loss","lift_loss","carry_loss"}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def stopping(frames, done):
    first = next(i for i,f in enumerate(frames[:-1]) if f["fault"]["active"])
    samples = [f["state"] for f in frames[first:]]
    settled = next((i for i in range(2,len(samples)) if all(abs(s[3]) <= .08 for s in samples[i-2:i+1])),None)
    detected = next((f["state"][10] for f in frames[first:-1] if f["supervision"] and f["supervision"]["override"]),None)
    if settled is None: return False
    distances = [math.dist(a[:2],b[:2]) for a,b in zip(samples,samples[1:])]
    return bool(detected is not None and detected-samples[0][10] <= .3+1e-8
                and samples[settled][10]-samples[0][10] <= 2.5+1e-8
                and sum(distances[:settled]) <= 2.
                and samples[-1][10]-samples[settled][10] >= 3.-1e-8
                and sum(distances[settled:]) <= .25
                and max(abs(s[3]) for s in samples[settled:]) <= .1 and not done)


def verify():
    r = json.loads((D/"report.json").read_text()); plan = r["plan"]
    assert json.loads((D/"plan.json").read_text()) == plan
    evaluation = json.loads((D/"evaluation.json").read_text())
    assert evaluation["cases"] == r["cases"] and evaluation["budget_stop"] == r["budget_stop"]
    assert r["complete"] and r["budget_stop"] is None
    assert len(r["cases"]) == len(plan["cases"]) == 33
    assert [{k:c[k] for k in ("method","source","pattern","seed")} for c in r["cases"]] == plan["cases"]
    expected = {(METHOD,"phase_memory-"+str(s),p,19000) for s in (7,19,41) for p in
                ("healthy","reset_loss","approach_loss","fill_loss","lift_loss","carry_loss","transient","recovery","partial_occlusion")}
    expected |= {("original","phase_memory-"+str(s),p,19000) for s in (7,19,41) for p in ("healthy","reset_loss")}
    assert {(c["method"],c["source"],c["pattern"],c["seed"]) for c in r["cases"]} == expected
    assert r["active_wall_s"] <= plan["wall_cap_s"] == 180 and plan["cpu_threads"] == 1
    assert r["environment_decisions"] == r["neural_queries"] <= plan["evaluation_cap"] == 19800
    assert r["physics_replay_decisions"] <= plan["physics_replay_cap"] == 16200
    assert r["action_replay_queries"] <= plan["action_replay_cap"] == 19800
    assert r["physics_replay_cases"] == 27 and r["action_replay_cases"] == 33
    assert r["max_state_error"] == r["max_action_error"] == r["max_observation_error"] == 0
    assert r["reference_controller_queries"] == r["teacher_training_queries"] == r["optimiser_updates"] == r["held_out_cases"] == 0
    assert r["admission"] == "not admitted; training-partition pilot only"
    assert sha((D/"traces.zip").read_bytes()) == r["trace_archive_sha256"]
    assert (D/"traces.zip").stat().st_size <= plan["trace_archive_cap"] == 16*1024**2
    assert sha((D/"source.zip").read_bytes()) == r["source_archive_sha256"]
    with zipfile.ZipFile(D/"source.zip") as z:
        assert set(z.namelist()) == set(plan["files"])
        for path, digest in plan["files"].items():
            assert sha(z.read(path)) == sha((ROOT/path).read_bytes()) == digest,path
    selection = json.loads((ROOT/"docs/phase-11/phase-memory-evidence/selection.json").read_text())
    decisions = physics = 0; healthy = {}
    with zipfile.ZipFile(D/"traces.zip") as z:
        assert set(z.namelist()) == {c["trace"] for c in r["cases"]}
        for c in r["cases"]:
            raw = z.read(c["trace"]); assert sha(raw) == c["sha256"]
            t = json.loads(gzip.decompress(raw)); frames = t["frames"]
            assert t["job"] == {k:c[k] for k in ("method","source","pattern","seed")}
            assert t["identity"] == c["identity"]
            assert t["checkpoint_sha256"] == c["checkpoint_sha256"] == selection[c["source"]]["sha256"]
            assert c["weights_unchanged"] and t["weights_before"] == t["weights_after"]
            assert t["outcome"] == {k:c[k] for k in t["outcome"]}
            assert len(frames) == c["decisions"]+1 and c["decisions"] <= 600
            assert frames[0]["state"][7] == c["initial_payload_kg"] == 0
            assert frames[-1]["state"][8] == c["delivered_kg"]
            decisions += c["decisions"]
            if c["method"] == METHOD: physics += c["decisions"]
            for i,f in enumerate(frames):
                s = f["state"]; assert len(s) == 102 and all(math.isfinite(v) for v in s)
                assert abs(sum(s[15:79])*.25*s[81]+sum(s[7:10])-s[82]) < 1e-7
                if i == len(frames)-1: continue
                assert f["next_state"] == frames[i+1]["state"]
                assert len(f["action"]) == 4 and all(abs(v) <= 1 and math.isfinite(v) for v in f["action"])
                supervision = f["supervision"]
                if c["method"] == METHOD:
                    assert supervision["method"] == METHOD and supervision["phase"] == f["phase"]
                    assert supervision["applied_action"] == f["action"]
                    assert supervision["real_elapsed_s"] == f["observation"]["proprio"][13]
                    assert abs(supervision["task_elapsed_s"]+supervision["paused_s"]-supervision["real_elapsed_s"]) < 1e-8
                    assert len(supervision["neural_proposal"]) == 4
                    assert all(abs(v) <= 1 and math.isfinite(v) for v in supervision["neural_proposal"])
                    if supervision["override"]:
                        assert f["action"][1:] == [0,0,0]
                        assert supervision["reason"] in ("range_uninitialised","range_timeout")
                    else: assert f["action"] == supervision["neural_proposal"]
                else: assert supervision is None
            if c["method"] == METHOD:
                overrides = sum(f["supervision"]["override"] for f in frames[:-1])
                resumed = any(not f["supervision"]["override"] and f["supervision"]["paused_s"] > 0 for f in frames[:-1])
                assert c["override_decisions"] == overrides and c["resumed"] == resumed
                if c["pattern"] in PERMANENT:
                    passed = stopping(frames,c["done"])
                    assert c["stop"]["passed"] == passed
                    passed = passed and not c["collision"]
                else:
                    passed = c["full_success"]
                    if c["pattern"] == "recovery": passed = passed and overrides > 0 and resumed
                assert c["criterion_passed"] == passed
            if c["pattern"] == "healthy": healthy[c["method"],c["source"]] = frames
    assert decisions == r["environment_decisions"] == r["action_replay_queries"]
    assert physics == r["physics_replay_decisions"]
    healthy_exact = True
    for source in ("phase_memory-7","phase_memory-19","phase_memory-41"):
        a,b = healthy[METHOD,source],healthy["original",source]
        healthy_exact &= len(a) == len(b) and all(x["phase"] == y["phase"] and x.get("action") == y.get("action") and x["state"] == y["state"] for x,y in zip(a,b))
    assert r["healthy_exact"] == healthy_exact
    assert r["advance_hypothesis"] == (healthy_exact and all(c["criterion_passed"] for c in r["cases"] if c["method"] == METHOD))
    for path, digest in json.loads((D/"files.json").read_text()).items():
        p = (ROOT/path).resolve(); assert p.is_relative_to(ROOT)
        assert sha(p.read_bytes()) == digest,path
    print("PASS: all 33 practice cases, explicit overrides, physical hold criteria and retained failures; no admission")


if __name__ == "__main__":
    verify()
