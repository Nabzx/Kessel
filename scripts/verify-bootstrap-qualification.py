"""Verify fresh stopping qualification, audit provenance and exact replay."""
import gzip
import hashlib
import json
import math
from pathlib import Path
import struct
import zipfile

ROOT = Path(__file__).resolve().parents[1]
D = ROOT/"docs/phase-11/bootstrap-qualification-evidence"
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
    assert len(report["cases"]) == len(plan["cases"]) == 120
    cert = json.loads((D/"reservation-corrected.json").read_text())
    assert cert["verified"] and not cert["hits"] and not cert["errors"]
    assert cert["seeds"] == list(range(208701,208709)) and cert["new_policy_queries"] == 0
    assert cert["excluded_consumed_bases"] == [208700]
    audits = []
    for row in cert["audits"]:
        path = (ROOT/row["path"]).resolve(); assert path.is_relative_to(ROOT)
        raw = path.read_bytes(); assert sha(raw) == row["sha256"]
        audit = json.loads(raw); audits.append(audit)
        assert audit["verified"] and not audit["hits"] and not audit["errors"] and audit["new_policy_queries"] == 0
        assert audit["audit_wall_s"] <= audit["audit_cap_s"] == 180
        assert audit["worker_wall_s"] <= audit["worker_cap_s"] == 175 and audit["cpu_threads"] == 1
        assert len(audit["inventory"]) >= 7000
        assert any(v["format"] == ".zip" and any(p.startswith("git:") for p in v["locations"]) for v in audit["inventory"].values())
    assert audits[0]["seeds"] == list(range(208700,208708)) and audits[1]["seeds"] == [208708]
    assert cert["identities"] == [r for r in audits[0]["identities"] if r["seed"] != 208700]+audits[1]["identities"]
    assert sha((D/"reservation-corrected.json").read_bytes()) == plan["reservation_sha256"]
    aborted = D/"aborted-attempt"; abort = json.loads((aborted/"abort.json").read_text())
    assert abort["consumed_bases"] == [208700] and abort["retained_case_traces"] == 0
    assert abort["environment_decisions_upper_bound"] == abort["neural_queries_upper_bound"] == 600
    assert abort["physics_replay_decisions"] == abort["action_replay_queries"] == 0
    for name,digest in abort["archives"].items(): assert sha((aborted/name).read_bytes()) == digest
    with zipfile.ZipFile(aborted/"traces.zip") as z: assert not z.namelist()
    with zipfile.ZipFile(aborted/"source.zip") as z:
        for name in ("runtime.py","range_supervisor.py","range_contract.py","range_pilot.py","bootstrap_hold_pilot.py","bootstrap_hold.py","motion_hold.py"):
            path = "training/kessel_lab/"+name
            assert z.read(path) == (ROOT/path).read_bytes(), "control changed after abort: "+name
        for path in z.namelist():
            if path.startswith("training/kessel_training/") and path.endswith(".py"):
                assert z.read(path) == (ROOT/path).read_bytes(), "kernel changed after abort: "+path
    for name,digest in cert["audit_files"].items(): assert sha((ROOT/name).read_bytes()) == digest,name
    expected = {(METHOD,"phase_memory-"+str(p),pattern,seed) for p in (7,19,41) for seed in cert["seeds"]
                for pattern in ("healthy","partial_carry_zeroed","carry_loss","recovery")}
    expected |= {("original","phase_memory-"+str(p),"healthy",seed) for p in (7,19,41) for seed in cert["seeds"]}
    assert {(c["method"],c["source"],c["pattern"],c["seed"]) for c in report["cases"]} == expected
    identities = {c["seed"]:c["scenario"] for c in cert["identities"]}
    assert report["active_wall_s"] <= plan["wall_cap_s"] == 400 and plan["cpu_threads"] == 1
    assert report["environment_decisions"] == report["neural_queries"] <= plan["evaluation_cap"] == 71400
    assert report["environment_decisions"]+abort["environment_decisions_upper_bound"] <= 72000
    assert report["physics_replay_decisions"] <= plan["physics_replay_cap"] == 57600
    assert report["action_replay_queries"] <= plan["action_replay_cap"] == 72000
    assert report["physics_replay_cases"] == 96 and report["action_replay_cases"] == 120
    assert report["max_state_error"] == report["max_action_error"] == report["max_observation_error"] == 0
    assert report["teacher_queries"] == report["optimiser_updates"] == 0
    assert report["held_out_cases"] == 120
    assert sha((D/"traces.zip").read_bytes()) == report["trace_archive_sha256"]
    assert (D/"traces.zip").stat().st_size <= plan["trace_archive_cap"] == 32*1024**2
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
            assert trace["scenario"] == identities[c["seed"]] and c["kind"] == "task"
            assert c["identity"] == trace["identity"] and c["identity"] not in unique; unique.add(c["identity"])
            assert trace["checkpoint_sha256"] == c["checkpoint_sha256"] == selection[c["source"]]["sha256"]
            assert trace["weights_before"] == trace["weights_after"] and c["weights_unchanged"]
            assert trace["outcome"] == {k:c[k] for k in trace["outcome"]}
            assert len(frames) == c["decisions"]+1 and c["decisions"] <= 600
            assert frames[0]["state"][7] == c["initial_payload_kg"] == 0
            assert sha(struct.pack("<102d",*frames[0]["state"])) == identities[c["seed"]]["initial_state_sha256"]
            assert frames[-1]["state"][7:10] == [c["carried_kg"],c["delivered_kg"],c["spilled_kg"]]
            assert c["full_success"] == (c["done"] and c["reason"] == "success")
            if c["full_success"]: assert c["delivered_kg"] >= 2000 and not c["collision"]
            for key in ("delivered_kg","spilled_kg"):
                assert abs(sum(f["transfer"][key] for f in frames[:-1])-c[key]) < 1e-7
            assert abs(sum(f["transfer"]["loaded_kg"] for f in frames[:-1])-sum(frames[-1]["state"][7:10])) < 1e-7
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
            if c["pattern"] == "healthy": healthy[c["source"],c["seed"],c["method"]] = frames
    exact = True
    for source in ("phase_memory-7","phase_memory-19","phase_memory-41"):
        for seed in cert["seeds"]:
            a,b = healthy[source,seed,METHOD],healthy[source,seed,"original"]
            exact &= len(a) == len(b) and all(x["state"] == y["state"] and x["phase"] == y["phase"] and x.get("action") == y.get("action") for x,y in zip(a,b))
    assert report["healthy_exact"] == exact
    assert decisions == report["environment_decisions"] == report["action_replay_queries"]
    assert physics == report["physics_replay_decisions"]
    passed = bool(exact and all(
        len(group := [c for c in report["cases"] if c["method"] == METHOD and c["source"] == "phase_memory-"+str(p) and c["pattern"] == pattern]) == 8
        and sum(c["criterion_passed"] for c in group) >= 7 and not any(c["collision"] for c in group)
        for p in (7,19,41) for pattern in ("healthy","partial_carry_zeroed","carry_loss","recovery")))
    assert report["admitted"] == passed
    for name,digest in json.loads((D/"files.json").read_text()).items():
        p = (ROOT/name).resolve(); assert p.is_relative_to(ROOT)
        assert sha(p.read_bytes()) == digest,name
    print("PASS: fresh audit, 120 outcomes, per-seed stopping/recovery gates and exact replay")


if __name__ == "__main__": verify()
