"""Check input sensitivity and all revised practice outcomes without running actors."""
import gzip
import hashlib
import json
import math
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
D = ROOT/"docs/phase-11/spatial-range-evidence"
METHOD = "complete_range_supervisor"


def sha(raw): return hashlib.sha256(raw).hexdigest()


def stop_pass(frames, done):
    first = next((i for i,f in enumerate(frames[:-1]) if f["fault"]["active"]),None)
    if first is None: return False
    samples = [f["state"] for f in frames[first:]]
    settled = next((i for i in range(2,len(samples)) if all(abs(s[3]) <= .08 for s in samples[i-2:i+1])),None)
    detected = next((f["state"][10] for f in frames[first:-1] if f["supervision"] and f["supervision"]["override"]),None)
    if settled is None or detected is None: return False
    distances = [math.dist(a[:2],b[:2]) for a,b in zip(samples,samples[1:])]
    return bool(detected-samples[0][10] <= .1+1e-8 and samples[settled][10]-samples[0][10] <= 2.5+1e-8
                and sum(distances[:settled]) <= 2 and samples[-1][10]-samples[settled][10] >= 10-1e-8
                and sum(distances[settled:]) <= .25 and max(abs(s[3]) for s in samples[settled:]) <= .1 and not done)


def verify():
    diagnostic = json.loads((D/"diagnostic.json").read_text()); dp = diagnostic["plan"]
    assert json.loads((D/"diagnostic-plan.json").read_text()) == dp
    assert diagnostic["neural_queries"] == dp["query_cap"] == 255
    assert diagnostic["environment_decisions"] == diagnostic["teacher_queries"] == diagnostic["optimiser_updates"] == 0
    assert diagnostic["cpu_threads"] == 1 and diagnostic["wall_s"] <= dp["cap_s"] == 45
    assert (D/"diagnostic.json").stat().st_size < 2*1024**2
    with zipfile.ZipFile(D/"diagnostic-source.zip") as snapshot:
        for name,digest in dp["files"].items():
            raw = snapshot.read(name) if name in snapshot.namelist() else (ROOT/name).read_bytes()
            assert sha(raw) == digest,name
    aborted = D/"aborted-attempt"; abort = json.loads((aborted/"abort.json").read_text())
    assert abort["retained_cases"] == abort["physics_replay_decisions"] == abort["action_replay_queries"] == 0
    assert abort["environment_decisions_upper_bound"] == abort["neural_queries_upper_bound"] == 600
    for name,key in (("source.zip","source_archive_sha256"),("plan.json","plan_sha256"),("traces.zip","trace_archive_sha256")):
        assert sha((aborted/name).read_bytes()) == abort[key]
    with zipfile.ZipFile(aborted/"traces.zip") as z: assert not z.namelist()
    with zipfile.ZipFile(aborted/"source.zip") as z:
        before = z.read("training/kessel_lab/range_contract.py").decode()
        corrected = before.replace('"usable":kind == "fresh_complete" and p[11] <= .2+1e-9}',
                                   '"usable":bool(kind == "fresh_complete" and p[11] <= .2+1e-9)}')
        assert corrected == (ROOT/"training/kessel_lab/range_contract.py").read_text()
    assert len(diagnostic["snapshots"]) == 15 and len(diagnostic["interventions"]) == 240
    snapshots = {(s["source"],s["phase"]):s for s in diagnostic["snapshots"]}
    expected = {(s,p,m,e) for s in ("phase_memory-7","phase_memory-19","phase_memory-41")
                for p in range(5) for m in dp["masks"] for e in ("retained_height","zeroed_height")}
    assert len(expected) == 240 and {(r["source"],r["phase"],r["region"],r["encoding"]) for r in diagnostic["interventions"]} == expected
    for r in diagnostic["interventions"]:
        baseline = snapshots[r["source"],r["phase"]]["baseline"]
        assert all(abs((a-b)-delta) < 2e-7 for a,b,delta in zip(r["action"],baseline,r["action_delta"]))
        assert abs(max(abs(v) for v in r["action_delta"])-r["max_abs_action_delta"]) < 1e-7
    report = json.loads((D/"report.json").read_text()); plan = report["plan"]
    assert json.loads((D/"plan.json").read_text()) == plan
    evaluation = json.loads((D/"evaluation.json").read_text())
    assert evaluation["cases"] == report["cases"] and evaluation["budget_stop"] == report["budget_stop"]
    assert report["complete"] and report["budget_stop"] is None
    assert len(report["cases"]) == len(plan["cases"]) == 51
    assert sum(c["kind"] == "stop_fixture" for c in report["cases"]) == 12
    assert sum(c["criterion"] == "stop" for c in report["cases"]) == 39
    assert report["active_wall_s"] <= plan["wall_cap_s"] == 150 and plan["cpu_threads"] == 1
    assert report["environment_decisions"] == report["neural_queries"] <= plan["evaluation_cap"] == 30000
    assert report["environment_decisions"]+abort["environment_decisions_upper_bound"] <= 30600
    assert report["physics_replay_decisions"] <= plan["physics_replay_cap"] == 28800
    assert report["action_replay_queries"] <= plan["action_replay_cap"] == 30600
    assert report["physics_replay_cases"] == 48 and report["action_replay_cases"] == 51
    assert report["max_state_error"] == report["max_action_error"] == report["max_observation_error"] == 0
    assert report["teacher_queries"] == report["optimiser_updates"] == report["held_out_cases"] == 0
    assert report["admission"] == "not admitted; revised practice pilot only"
    assert sha((D/"traces.zip").read_bytes()) == report["trace_archive_sha256"]
    assert (D/"traces.zip").stat().st_size <= plan["trace_archive_cap"] == 16*1024**2
    assert sha((D/"source.zip").read_bytes()) == report["source_archive_sha256"]
    with zipfile.ZipFile(D/"source.zip") as z:
        assert set(z.namelist()) == set(plan["files"])
        for name,digest in plan["files"].items(): assert sha(z.read(name)) == sha((ROOT/name).read_bytes()) == digest,name
    selection = json.loads((ROOT/"docs/phase-11/phase-memory-evidence/selection.json").read_text())
    decisions = physics = 0; healthy = {}; unique = set()
    with zipfile.ZipFile(D/"traces.zip") as z:
        assert set(z.namelist()) == {c["trace"] for c in report["cases"]}
        for c,job in zip(report["cases"],plan["cases"]):
            raw = z.read(c["trace"]); assert sha(raw) == c["sha256"]
            trace = json.loads(gzip.decompress(raw)); frames = trace["frames"]
            assert trace["job"] == job == {k:c[k] for k in job}
            assert c["identity"] == trace["identity"] and c["identity"] not in unique; unique.add(c["identity"])
            assert trace["checkpoint_sha256"] == c["checkpoint_sha256"] == selection[c["source"]]["sha256"]
            assert trace["weights_before"] == trace["weights_after"] and c["weights_unchanged"]
            assert trace["outcome"] == {k:c[k] for k in trace["outcome"]}
            assert len(frames) == c["decisions"]+1 and c["decisions"] <= 600
            assert frames[0]["state"][7] == c["initial_payload_kg"] == (2500 if c["kind"] == "stop_fixture" else 0)
            if c["kind"] == "stop_fixture":
                s = frames[0]["state"]
                assert s[:3] == [0,0,0] and s[3] == c["initial_speed_m_s"] and s[84] == c["grade_rad"]
                assert c["criterion"] == "stop" and not c["full_success"]
            decisions += c["decisions"]
            if c["method"] == METHOD: physics += c["decisions"]
            for i,f in enumerate(frames):
                s = f["state"]; assert len(s) == 102 and all(math.isfinite(v) for v in s)
                assert abs(sum(s[15:79])*.25*s[81]+sum(s[7:10])-s[82]) < 1e-7
                if i == len(frames)-1: continue
                assert f["next_state"] == frames[i+1]["state"]
                assert len(f["action"]) == 4 and all(math.isfinite(v) and abs(v) <= 1 for v in f["action"])
                sup = f["supervision"]
                if c["method"] == METHOD:
                    assert sup["phase"] == f["phase"] and sup["method"] == METHOD
                    obs = f["observation"]; canonical = sup["canonical_observation"]
                    fresh = bool(obs["proprio"][12]); valid = [v for row in obs["range_valid"] for v in row]
                    heights = [v for row in obs["local_height_m"] for v in row]
                    assert [v for row in canonical["range_valid"] for v in row] == (valid if fresh else [0]*25)
                    assert [v for row in canonical["local_height_m"] for v in row] == [h*v if fresh else 0 for h,v in zip(heights,valid)]
                    assert abs(sup["task_elapsed_s"]+sup["paused_s"]-sup["real_elapsed_s"]) < 1e-8
                    assert sup["applied_action"] == f["action"]
                    if sup["override"]: assert f["action"][1:] == [0,0,0]
                    else: assert sup["health"]["usable"] and sup["neural_proposal"] == f["action"]
                else: assert sup is None
            if c["criterion"] == "stop":
                passed = stop_pass(frames,c["done"])
                assert bool(c["stop"] and c["stop"]["passed"]) == passed
                passed = passed and not c["collision"]
            else: passed = c["full_success"]
            if c["pattern"] != "healthy": passed = passed and c["trigger_reached"]
            if c["pattern"] == "recovery": passed = passed and c["override_decisions"] > 0 and c["resumed"]
            assert c["criterion_passed"] == passed
            if c["pattern"] == "healthy": healthy[c["source"],c["method"]] = frames
    exact = True
    for source in ("phase_memory-7","phase_memory-19","phase_memory-41"):
        a,b = healthy[source,METHOD],healthy[source,"original"]
        exact &= len(a) == len(b) and all(x["state"] == y["state"] and x["phase"] == y["phase"] and x.get("action") == y.get("action") for x,y in zip(a,b))
    assert report["healthy_exact"] == exact
    assert decisions == report["environment_decisions"] == report["action_replay_queries"]
    assert physics == report["physics_replay_decisions"]
    assert report["advance_hypothesis"] == (exact and all(c["criterion_passed"] for c in report["cases"]))
    for name,digest in json.loads((D/"files.json").read_text()).items():
        p = (ROOT/name).resolve(); assert p.is_relative_to(ROOT)
        assert sha(p.read_bytes()) == digest,name
    print("PASS: 255 diagnostic queries, all 51 revised practice cases, retained abort, distinct gates and exact replay")


if __name__ == "__main__": verify()
