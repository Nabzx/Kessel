"""Verify unchanged control receipts and causal experimental sensor measurements."""
import gzip
import importlib.util
import json
import math
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
D = ROOT/"docs/phase-11/sensor-live-evidence"


def verify():
    spec = importlib.util.spec_from_file_location("progress_check",ROOT/"scripts/verify-progress-control.py")
    base = importlib.util.module_from_spec(spec); spec.loader.exec_module(base)
    r = base.capsule(D,current=True); p = r["plan"]
    assert len(r["cases"]) == len(p["jobs"]) == 38 and p["seed"] == 19020
    assert {(c["source"],c["family"],c["pattern"]) for c in r["cases"]} == {tuple(j) for j in p["jobs"]}
    assert p["browsers_started"] == p["sockets_bound"] == r["model_assisted_actions"] == 0
    assert not r["machine_commands"] and not r["sensor_model_gate_passed"]
    decisions = partial = 0
    with zipfile.ZipFile(D/"traces.zip") as archive:
        assert set(archive.namelist()) == {c["trace"] for c in r["cases"]}
        for case in r["cases"]:
            raw = archive.read(case["trace"]); assert base.sha(raw) == case["sha256"]
            value = json.loads(gzip.decompress(raw)); frames = value["frames"]
            assert case["equivalent_to_frozen_control"] and case["evaluation"]["passed"] and len(frames) == case["decisions"]+1
            assert value["outcome"] == case["outcome"] and value["scenario_evaluation"] == case["evaluation"]
            assert not value["sensor_model_gate_passed"] and not value["forecast_influences_action"] and not value["applied_machine_commands"]
            assert value["forecast_qualification"] == "failed; experimental inspection only"
            assert "observation" in frames[-1]
            decisions += case["decisions"]
            for i,(f,g) in enumerate(zip(frames,frames[1:])):
                s = f["state"]; forecast = f["forecast"]; q = forecast["observation"]["proprio"]
                assert abs(sum(s[15:79])*.25*s[81]+sum(s[7:10])-s[82]) < 1e-7
                assert f["next_state"] == g["state"] and f["next_observation"] == g["observation"]
                assert not forecast["accepted"] and forecast["experimental"] and not forecast["privileged_inputs"] and not forecast["influences_action"]
                assert "state" not in forecast and forecast["source"] == "sensor_observation_residual_ensemble"
                assert forecast["produced_at_s"] == f["t_s"] and forecast["for_decision"] == i
                assert forecast["previous_input_time_s"] == (frames[i-1]["observation"]["proprio"][13] if i else None)
                expected_pose = [q[0],q[1],math.atan2(q[2],q[3]),*q[4:8]]
                assert all(math.isclose(a,b,abs_tol=1e-9) for a,b in zip(expected_pose,forecast["render_pose"]))
                observation = f["observation"]; current = observation["proprio"]
                assert forecast["input_usable"] == bool(current[12] == 1 and current[11] <= .2+1e-9 and sum(sum(observation["range_valid"],[])) >= 5)
                target = g["observation"]; y = target["proprio"]; interval = y[13]-current[13]
                assert math.isclose(interval,forecast["actual_interval_s"],abs_tol=1e-9)
                if abs(interval-.1) > 1e-7:
                    partial += 1; assert forecast["measured_error"] is None
                    assert forecast["comparison_scope"] == "partial_interval_outside_sensor_horizon"; continue
                mask = sum(target["range_valid"],[])
                if not (y[12] == 1 and y[11] <= .2+1e-9): mask = [0]*25
                valid = sum(mask); height = sum(forecast["observation"]["local_height_m"],[]); truth = sum(target["local_height_m"],[])
                probability = sum(forecast["observation"]["range_valid_probability"],[])
                expected = {"position_m":math.dist(q[:2],y[:2]),"carried_kg":abs(q[8]-y[8]),"speed_m_s":abs(q[4]-y[4]),
                    "target_valid_cells":valid,"validity_brier":sum((a-b)**2 for a,b in zip(probability,mask))/25,
                    "valid_height_mae_m":sum(abs(a-b)*m for a,b,m in zip(height,truth,mask))/valid if valid else None}
                assert forecast["comparison_scope"] == "next_received_numeric_observation"
                for key,number in expected.items():
                    if number is None: assert forecast["measured_error"][key] is None
                    else: assert math.isclose(number,forecast["measured_error"][key],rel_tol=1e-8,abs_tol=1e-9)
    assert r["cost"]["counts"] == {"environment":decisions,"replay":decisions} and 2*decisions <= 30000
    assert r["cost"]["wall_s"] <= 360
    print(f"Sensor live: 38 complete unchanged-control runs; causal observed errors verified; {partial} partial terminal errors withheld; predictor remains experimental")


if __name__ == "__main__": verify()
