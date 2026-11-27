"""Verify retained live-interface regression evidence without running a model."""
import gzip
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
D = ROOT/"docs/phase-11/qualified-runtime-evidence"
PRACTICE = ROOT/"docs/phase-11/bootstrap-hold-evidence"
METHOD = "bootstrapped_motion_hold"


def sha(raw): return hashlib.sha256(raw).hexdigest()
def encoded(value): return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()


def verify():
    manifest = json.loads((D/"files.json").read_text())
    expected_files = {str((D/name).relative_to(ROOT)) for name in ("plan.json","report.json","recovery-export.json.gz")}
    assert set(manifest) == expected_files
    for name,digest in manifest.items(): assert sha((ROOT/name).read_bytes()) == digest,name
    report = json.loads((D/"report.json").read_text()); plan = report["plan"]
    assert plan == json.loads((D/"plan.json").read_text())
    assert plan["protocol"] == "ADR-0072" and plan["role"] == "consumed practice regression; no new qualification"
    assert report["complete"] and not report["errors"] and report["budget_stop"] is None
    assert plan["seed"] == 19000 and plan["cpu_threads"] == 1
    assert 0 < report["active_wall_s"] <= plan["wall_cap_s"] == 120
    assert report["environment_decisions"] == report["neural_queries"] <= plan["evaluation_cap"] == 9000
    for key in ("teacher_queries","optimiser_updates","held_out_cases","browser_sessions","listening_servers"):
        assert report[key] == 0
    assert report["reset_cleared"] and report["exports_nonmutating"]
    required = {"scripts/research/verify-qualified-runtime.py","docs/adr/0072-qualified-stopping-live-simulator.md",
                "training/kessel_lab/bootstrap_runtime.py","training/tests_lab/test_bootstrap_runtime.py",
                "scripts/tests/qualified-client.test.mjs"}
    required |= {"docs/phase-11/qualified-demo/"+name for name in ("index.html","viewer.css","viewer.js","client.mjs","presentation.mjs")}
    assert set(plan["files"]) == required
    for name,digest in plan["files"].items(): assert sha((ROOT/name).read_bytes()) == digest,"regression source changed: "+name
    qualification = ROOT/"docs/phase-11/bootstrap-qualification-evidence/report.json"
    assert sha(qualification.read_bytes()) == report["qualification_sha256"]
    assert report["runtime_sha256"] == plan["files"]["training/kessel_lab/bootstrap_runtime.py"]
    assert sha((PRACTICE/"traces.zip").read_bytes()) == plan["reference_archive_sha256"]
    assert sha((PRACTICE/"report.json").read_bytes()) == plan["reference_report_sha256"]
    practice = json.loads((PRACTICE/"report.json").read_text())
    families = ["healthy","partial_carry_zeroed","carry_loss","recovery"]
    sources = [METHOD+"-"+str(p) for p in (7,19,41)]+["phase_memory-"+str(p) for p in (7,19,41)]
    assert plan["sources"] == sources and plan["families"] == families
    expected = {(s,f) for s in sources[:3] for f in families}|{(s,"healthy") for s in sources[3:]}
    assert len(report["cases"]) == 15 and {(c["source"],c["family"]) for c in report["cases"]} == expected
    with zipfile.ZipFile(PRACTICE/"traces.zip") as archive:
        for c in report["cases"]:
            method = METHOD if c["source"].startswith(METHOD) else "original"
            source = "phase_memory-"+c["source"].rsplit("-",1)[1]
            reference = next(r for r in practice["cases"] if (r["method"],r["source"],r["pattern"]) == (method,source,c["family"]))
            assert c["seed"] == reference["seed"] == 19000 and c["method"] == method
            assert c["trace"] == reference["trace"] and c["reference_sha256"] == reference["sha256"]
            raw = archive.read(c["trace"]); assert sha(raw) == c["reference_sha256"]
            trace = json.loads(gzip.decompress(raw))
            assert sha(encoded(trace["frames"])) == c["frame_sha256"]
            assert c["exact"] and c["weights_unchanged"]
            assert c["checkpoint_sha256"] == trace["checkpoint_sha256"]
            assert c["outcome"] == trace["outcome"] and c["decisions"] == reference["decisions"]
            evaluation = c["evaluation"]
            assert evaluation == {"criterion":reference["criterion"],"passed":reference["criterion_passed"],
                "trigger_reached":reference["trigger_reached"],"override_decisions":reference["override_decisions"],
                "resumed":reference["resumed"],"stop":reference["stop"]}
            assert evaluation["passed"] and not c["outcome"]["collision"]
            modes = set()
            for frame in trace["frames"][:-1]:
                sup = frame["supervision"]
                modes.add("neural" if not sup or not sup["override"] else "recovering" if sup["health"]["usable"] else sup["mode"])
            assert c["modes"] == sorted(modes)
            if c["family"] in ("carry_loss","partial_carry_zeroed"):
                assert c["end_reason"] == "hold_window_passed" and not c["outcome"]["done"] and not c["outcome"]["full_success"]
                assert {"neural","stopping","holding"} <= modes
            else:
                assert c["end_reason"] == "environment_terminal" and c["outcome"]["full_success"]
            if c["family"] == "recovery": assert {"neural","stopping","holding","recovering"} <= modes
    assert report["environment_decisions"] == sum(c["decisions"] for c in report["cases"])
    raw = (D/"recovery-export.json.gz").read_bytes(); assert sha(raw) == report["retained_export_sha256"]
    export = json.loads(gzip.decompress(raw))
    assert export["export_kind"] == "executed_synthetic_trace" and not export["applied_machine_commands"]
    assert export["source"] == METHOD+"-7" and export["family"] == "recovery"
    assert export["qualification_sha256"] == report["qualification_sha256"] and export["runtime_sha256"] == report["runtime_sha256"]
    assert export["scenario"]["seed"] == 19000 and export["run_id"] and export["identity"]
    assert not export["playback"]["running"] and export["playback"]["finished"]
    case = next(c for c in report["cases"] if c["source"] == export["source"] and c["family"] == "recovery")
    assert export["outcome"] == case["outcome"] and export["scenario_evaluation"] == case["evaluation"]
    assert len(export["frames"]) == export["outcome"]["decisions"]+1
    export["frames"][-1].pop("step_index"); export["frames"][-1].pop("last_action")
    assert sha(encoded(export["frames"])) == case["frame_sha256"]
    print("Qualified runtime: 15 exact practice traces, clear stop/delivery endings and a complete recovery export verified")


if __name__ == "__main__": verify()
