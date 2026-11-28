"""Verify causal shadow forecasts and complete frozen-control equivalence receipts."""
import gzip
import importlib.util
import json
import math
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
D = ROOT/"docs/phase-11/harvest-live-evidence"


def verify():
    spec = importlib.util.spec_from_file_location("progress_check",ROOT/"scripts/verify-progress-control.py")
    base = importlib.util.module_from_spec(spec); spec.loader.exec_module(base)
    report = base.capsule(D,current=True); plan = report["plan"]
    assert plan["browsers_started"] == plan["sockets_bound"] == 0 and not report["machine_commands"]
    assert len(report["cases"]) == len(plan["jobs"]) == 38
    assert {(c["source"],c["family"],c["pattern"]) for c in report["cases"]} == {tuple(j) for j in plan["jobs"]}
    decisions = 0
    with zipfile.ZipFile(D/"traces.zip") as archive:
        assert set(archive.namelist()) == {c["trace"] for c in report["cases"]}
        for case in report["cases"]:
            raw = archive.read(case["trace"]); assert base.sha(raw) == case["sha256"]
            value = json.loads(gzip.decompress(raw)); frames = value["frames"]
            assert case["evaluation"]["passed"] and case["equivalent_to_frozen_control"] and not value["applied_machine_commands"]
            assert case["outcome"] == value["outcome"] and len(frames) == case["decisions"]+1
            decisions += case["decisions"]
            if case["evaluation"]["criterion"] == "accepted_refusal":
                assert not case["outcome"]["full_success"] and case["outcome"]["delivered_kg"] == 0
            for current,following in zip(frames,frames[1:]):
                assert current["next_state"] == following["state"]
                forecast = current["forecast"]; assert forecast["source"] == "privileged_hybrid_shadow" and not forecast["influences_action"]
                assert forecast["produced_at_s"] == current["t_s"] and forecast["for_decision"] == current["step_index"]
                pred = forecast["state"]; actual = current["next_state"]; error = forecast["measured_error"]
                expected = {"position_m":math.dist(pred[:2],actual[:2]),"carried_kg":abs(pred[7]-actual[7]),
                            "delivered_kg":abs(pred[8]-actual[8]),"pile_height_mae_m":sum(abs(a-b) for a,b in zip(pred[15:79],actual[15:79]))/64,
                            "actual_interval_s":actual[10]-current["t_s"]}
                for key,number in expected.items(): assert math.isclose(error[key],number,abs_tol=1e-9,rel_tol=1e-8)
    assert report["cost"]["counts"] == {"environment":2*decisions,"teacher":decisions,"replay":0}
    assert 2*decisions <= 30000 and report["cost"]["wall_s"] <= 360
    assert report["max_state_error"] == report["max_action_error"] == report["max_observation_error"] == 0
    print("Harvest live: 38 complete in-process runs match frozen control; causal forecast errors verified; no socket/browser")


if __name__ == "__main__": verify()
