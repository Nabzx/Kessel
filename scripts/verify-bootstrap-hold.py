"""Verify bootstrap holding, cold starts, unchanged gates and exact replay."""
import gzip
import hashlib
import json
import math
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
D = ROOT/"docs/phase-11/bootstrap-hold-evidence"
METHOD = "bootstrapped_motion_hold"


def sha(raw): return hashlib.sha256(raw).hexdigest()


def response(speed, load):
    return min(22000.,28000./max(abs(speed),.5))/(10500.+min(3500.,max(0.,load)))


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
    report = json.loads((D/"report.json").read_text()); plan = report["plan"]
    assert json.loads((D/"plan.json").read_text()) == plan
    evaluation = json.loads((D/"evaluation.json").read_text())
    assert evaluation["cases"] == report["cases"] and evaluation["budget_stop"] == report["budget_stop"]
    assert report["complete"] and report["budget_stop"] is None
    assert len(report["cases"]) == len(plan["cases"]) == 57
    prior = json.loads((ROOT/"docs/phase-11/motion-hold-evidence/report.json").read_text())
    paired = [c for c in plan["cases"] if c.get("initial_speed_m_s",1) != 0]
    assert len(paired) == 51
    for old,new in zip(prior["plan"]["cases"],paired):
        expected = {**old,"method":METHOD if old["method"] != "original" else "original"}
        assert expected == new
    cold = [c for c in plan["cases"] if c.get("initial_speed_m_s",1) == 0]
    assert {(c["source"],c["grade_rad"]) for c in cold} == {
        ("phase_memory-"+str(seed),grade) for seed in (7,19,41) for grade in (-.06,.06)}
    assert sum(c["kind"] == "stop_fixture" for c in report["cases"]) == 18
    assert sum(c["criterion"] == "stop" for c in report["cases"]) == 45
    assert report["active_wall_s"] <= plan["wall_cap_s"] == 150 and plan["cpu_threads"] == 1
    assert report["environment_decisions"] == report["neural_queries"] <= plan["evaluation_cap"] == 30000
    assert report["physics_replay_decisions"] <= plan["physics_replay_cap"] == 28800
    assert report["action_replay_queries"] <= plan["action_replay_cap"] == 30600
    assert report["physics_replay_cases"] == 54 and report["action_replay_cases"] == 57
    assert report["max_state_error"] == report["max_action_error"] == report["max_observation_error"] == 0
    assert report["teacher_queries"] == report["optimiser_updates"] == report["held_out_cases"] == 0
    assert report["admission"] == "not admitted; bootstrap holding practice pilot only"
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
            disturbance = 0.; estimate_valid = False
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
                    motion = sup["observer"]; current = obs["proprio"]
                    accepted = probe = cleared = False; acceleration = None; reason = "not_overriding"
                    if sup["override"]:
                        if i == 0 or not frames[i-1]["supervision"]["override"]:
                            disturbance = 0.; estimate_valid = False; reason = "new_override"
                            probe = abs(current[4]) > .03
                        else:
                            previous = frames[i-1]["observation"]["proprio"]
                            acceleration = (current[4]-previous[4])/(current[13]-previous[13])
                            if abs(previous[4]) <= .03 or abs(current[4]) <= .03 or previous[4]*current[4] <= 0:
                                reason = "speed_transition"
                            elif abs(acceleration) >= 1.4: reason = "acceleration_limit"
                            else:
                                residual = response(previous[4],previous[8])*frames[i-1]["action"][0]-acceleration
                                residual -= .1962*(1 if previous[4] > 0 else -1)
                                disturbance = min(.8,max(-.8,residual)); accepted = estimate_valid = True; reason = "accepted"
                    coefficient = response(current[4],current[8])
                    feedforward = disturbance/coefficient if sup["override"] and estimate_valid else 0.
                    cleared = sup["override"] and estimate_valid and abs(current[4]) <= .08
                    assert motion["accepted"] == accepted and motion["reason"] == reason
                    assert motion["estimate_valid"] == estimate_valid and motion["probe_applied"] == probe
                    assert motion["integral_cleared"] == cleared
                    if cleared: assert sup["integral"] == 0
                    assert motion["observed_acceleration_m_s2"] == acceleration
                    assert abs(motion["disturbance_m_s2"]-disturbance) < 1e-12
                    assert abs(motion["response_m_s2_per_command"]-coefficient) < 1e-12
                    assert abs(motion["feedforward_command"]-feedforward) < 1e-12
                    if sup["override"]:
                        expected_drive = min(1.,max(-1.,feedforward-2.*current[4]-sup["integral"]))
                        if probe: expected_drive = -.25*(1 if current[4] > 0 else -1)
                        assert abs(f["action"][0]-expected_drive) < 1e-12
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
    print("PASS: all 57 bootstrap hold cases, cold starts, unchanged gates and exact replay")


if __name__ == "__main__": verify()
