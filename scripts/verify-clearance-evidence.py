"""Offline clearance-pilot verification. No policy imports or simulator queries."""
import gzip
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
D = ROOT/"docs/phase-11/clearance-latched-evidence"


def sha(raw): return hashlib.sha256(raw).hexdigest()


def verify():
    manifest = json.loads((D/"files.json").read_text())
    assert set(manifest) == {str((D/n).relative_to(ROOT)) for n in ("plan.json","report.json","source.zip","traces.zip")}
    for name,digest in manifest.items(): assert sha((ROOT/name).read_bytes()) == digest,name
    report = json.loads((D/"report.json").read_text()); plan = report["plan"]
    assert plan == json.loads((D/"plan.json").read_text())
    assert report["complete"] and not report["errors"] and report["budget_stop"] is None
    assert not report["runtime_admitted"] and not report["fresh_qualification"]
    assert report["teacher_queries"] == report["optimiser_updates"] == 0
    assert report["max_replay_state_error"] == 0 and report["max_mass_residual_kg"] < 1e-7
    assert plan["cpu_threads"] == 1 and report["cost"]["wall_s"] <= report["cost"]["wall_cap_s"] == 119
    assert report["cost"]["limits"] == {"evaluation":6200,"replay":6200}
    aborted = json.loads((ROOT/plan["preceding_abort"]).read_text())
    assert not aborted["complete"] and aborted["cost"]["counts"] == {"evaluation":1,"replay":0}
    preceding = json.loads((ROOT/plan["preceding_pilot"]).read_text())
    assert preceding["complete"] and not preceding["pilot_passed"]
    assert preceding["cost"]["counts"] == {"evaluation":5706,"replay":5706}
    assert aborted["cost"]["wall_s"]+preceding["cost"]["wall_s"]+report["cost"]["wall_s"] <= 180
    with zipfile.ZipFile(D/"source.zip") as archive:
        assert set(archive.namelist()) == set(plan["files"])
        for name,digest in plan["files"].items(): assert sha(archive.read(name)) == sha((ROOT/name).read_bytes()) == digest,name
    spec = importlib.util.spec_from_file_location("hold_evidence",ROOT/"scripts/verify-bootstrap-hold.py")
    holds = importlib.util.module_from_spec(spec); spec.loader.exec_module(holds)
    expected = {(seed,policy,kind) for seed in (19000,19001) for policy in (7,19,41)
                for kind in ("healthy","blocked","forward_loaded","reverse_loaded","stale")}
    assert len(report["cases"]) == 30
    assert {(c["seed"],int(c["source"].rsplit("-",1)[1]),c["kind"]) for c in report["cases"]} == expected
    with zipfile.ZipFile(D/"traces.zip") as archive:
        assert set(archive.namelist()) == {c["trace"] for c in report["cases"]}
        for case in report["cases"]:
            raw = archive.read(case["trace"]); assert sha(raw) == case["sha256"]
            trace = json.loads(gzip.decompress(raw)); frames = trace["frames"]; outcome = case["outcome"]
            assert trace["outcome"] == outcome and trace["checkpoint_sha256"] == case["checkpoint_sha256"]
            assert not trace["applied_machine_commands"] and len(frames) == outcome["decisions"]+1
            assert frames[0]["state"][7] == (2500 if case["kind"].endswith("loaded") else 0)
            for i,frame in enumerate(frames):
                s = frame["state"]; assert len(s) == 102 and all(math.isfinite(v) for v in s)
                assert abs(sum(s[15:79])*.25*s[81]+sum(s[7:10])-s[82]) < 1e-7
                if i == len(frames)-1: continue
                assert frame["next_state"] == frames[i+1]["state"]
                assert frame["supervision"] == frame["clearance"]["supervision"]
                assert frame["action"] == frame["supervision"]["applied_action"]
                assert all(abs(v) <= 1 and math.isfinite(v) for v in frame["action"])
                channel = frame["clearance"]["clearance"]; packet = frame["clearance"]["packet"]
                assert packet["version"] == "synthetic-envelope-clearance-1" and len(packet["distance_m"]) == 4
                assert all(0 <= v <= 12 for v in packet["distance_m"])
                assert math.isclose(channel["threshold_m"],.6+.2*abs(frame["observation"]["proprio"][4])+frame["observation"]["proprio"][4]**2/1.2,abs_tol=1e-12)
                assert frame["fault"]["active"] == (not channel["usable"])
                if not channel["usable"]:
                    assert frame["supervision"]["override"] and frame["action"][1:] == [0,0,0]
                    assert frame["clearance"]["range_health"]["usable"]
                    assert frame["clearance"]["proposal_input"] == "clearance_handoff_mask"
                if case["kind"] == "stale": assert channel["reason"] == "stale_or_future_clearance"
            if case["kind"] == "healthy":
                passed = outcome["full_success"] and outcome["healthy_exact"]
                if outcome["healthy_exact"]: assert all(not f["supervision"]["override"] for f in frames[:-1])
                else: assert not passed and any(f["supervision"]["override"] for f in frames[:-1])
            else:
                passed = holds.stop_pass(frames,outcome["done"]) and not outcome["collision"]
                assert not outcome["full_success"]
            assert outcome["passed"] == passed
    count = sum(c["outcome"]["decisions"] for c in report["cases"])
    assert report["cost"]["counts"] == {"evaluation":count,"replay":count} and count+5707 <= 12000
    assert report["pilot_passed"] == all(c["outcome"]["passed"] for c in report["cases"])
    print("Clearance evidence: 30 complete practice cases, exact replay, explicit stop/delivery outcomes; pilot passed:",report["pilot_passed"])


if __name__ == "__main__": verify()
