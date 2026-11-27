"""Verify all retained rehearsal/validation/evaluation cases without inference."""
from collections import Counter
import gzip
import hashlib
import json
import math
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
D = ROOT/"docs/phase-11/robustness-repair-evidence"


def sha(raw): return hashlib.sha256(raw).hexdigest()


def verify():
    manifest = json.loads((D/"files.json").read_text())
    for name,digest in manifest.items(): assert sha((ROOT/name).read_bytes()) == digest,name
    report = json.loads((D/"report.json").read_text()); plan = report["plan"]
    assert plan == json.loads((D/"plan.json").read_text())
    assert report["complete"] and not report["errors"] and report["budget_stop"] is None
    assert plan["role"] == "consumed practice study; no fresh qualification" and not report["runtime_admitted"]
    assert plan["cpu_threads"] == 1 and report["cost"]["wall_s"] <= report["cost"]["wall_cap_s"] == 600
    limits = {"environment":100000,"teacher":30000,"updates":3000,"replay":25000}
    assert report["cost"]["limits"] == limits
    assert all(report["cost"]["counts"][k] <= v for k,v in limits.items())
    with zipfile.ZipFile(D/"source.zip") as archive:
        assert set(archive.namelist()) == set(plan["files"])
        for name,digest in plan["files"].items(): assert sha(archive.read(name)) == sha((ROOT/name).read_bytes()) == digest,name
    families = plan["families"]; assert len(families) == 13 and len(set(families)) == 13
    expected = {("rehearsal",f"task_reference-{t}",f,s) for t in (6,12) for f in families for s in (19010,19011)}
    expected |= {("validation",f"candidate-{p}-smooth-{s}",f,19012) for p in (7,19,41) for s in (0,1) for f in families}
    expected |= {("evaluation",f"{m}-{p}",f,19013) for p in (7,19,41) for m in ("original","candidate") for f in families}
    cases = report["cases"]
    assert len(cases) == 208 and {(c["stage"],c["source"],c["family"],c["seed"]) for c in cases} == expected
    with zipfile.ZipFile(D/"traces.zip") as archive:
        assert set(archive.namelist()) == {c["trace"] for c in cases}
        for case in cases:
            raw = archive.read(case["trace"]); assert sha(raw) == case["sha256"]
            trace = json.loads(gzip.decompress(raw)); outcome = trace["outcome"]; frames = trace["frames"]
            assert outcome == case["outcome"] and not trace["applied_machine_commands"]
            assert trace["scenario"]["seed"] == case["seed"] and trace["scenario"]["family"] == case["family"]
            assert len(frames) == outcome["decisions"]+1 and 1 <= outcome["decisions"] <= 600
            assert outcome["initial_payload_kg"] == frames[0]["state"][7] == 0
            assert outcome["full_success"] == (outcome["reason"] == "success")
            assert outcome["collision"] == outcome["reason"].startswith(("tunnel","obstacle"))
            assert outcome["max_mass_residual_kg"] < 1e-7
            if outcome["full_success"]: assert outcome["delivered_kg"] >= 2000 and not outcome["collision"]
            assert frames[-1]["state"][8] == outcome["delivered_kg"] and frames[-1]["state"][10] == outcome["cycle_s"]
            for i,frame in enumerate(frames):
                s = frame["state"]; assert len(s) == 102 and all(math.isfinite(v) for v in s)
                assert 0 <= frame["phase"] <= 4
                assert abs(sum(s[15:79])*.25*s[81]+sum(s[7:10])-s[82]) < 1e-7
                if i == len(frames)-1: continue
                assert frame["next_state"] == frames[i+1]["state"]
                assert frame["observation"]["proprio"][13] == frame["t_s"] == s[10]
                assert len(frame["action"]) == 4 and all(math.isfinite(v) and abs(v) <= 1 for v in frame["action"])
                if case["source"].startswith("candidate"):
                    sup = frame["supervision"]
                    assert len(sup["model_input_features"]) == 65 and all(math.isfinite(v) for v in sup["model_input_features"])
                    assert frame["action"] == sup["applied_action"]
                    if sup["override"]: assert frame["action"][1:] == [0,0,0]
                    else: assert frame["action"] == sup["neural_proposal"]
    counts = report["cost"]["counts"]
    assert counts["environment"] == sum(c["outcome"]["decisions"] for c in cases)
    assert counts["teacher"] == sum(c["outcome"]["decisions"] for c in cases if c["stage"] == "rehearsal")
    assert counts["replay"] == sum(c["outcome"]["decisions"] for c in cases if c["stage"] == "evaluation" and c["source"].startswith("candidate"))
    assert counts["updates"] == sum(m["updates"] for m in report["models"]) == 3000
    scores = {t:sum(c["outcome"]["full_success"] for c in cases if c["stage"] == "rehearsal" and c["source"] == f"task_reference-{t}") for t in (6,12)}
    timeout = max((6,12),key=lambda t:(scores[t],t)); assert timeout == report["selected_fill_timeout_s"]
    assert report["training_rows"] == sum(c["outcome"]["decisions"] for c in cases if c["stage"] == "rehearsal" and c["source"] == f"task_reference-{timeout}")
    selection = json.loads((ROOT/"docs/phase-11/phase-memory-evidence/selection.json").read_text())
    for model in report["models"]:
        assert model["updates"] == 1000 and sha((D/model["path"]).read_bytes()) == model["sha256"]
        assert model["initial_checkpoint_sha256"] == selection[f"phase_memory-{model['seed']}"]["sha256"]
        assert model["training_rows_sha256"] == report["training_rows_sha256"]
        scores = {}
        for smooth in (False,True):
            rows = [c for c in cases if c["stage"] == "validation" and c["source"] == f"candidate-{model['seed']}-smooth-{int(smooth)}"]
            scores[smooth] = (sum(c["outcome"]["full_success"] for c in rows),-sum(c["outcome"]["collision"] for c in rows),not smooth)
        assert report["selected_smoothing"][str(model["seed"])] == max((False,True),key=lambda s:scores[s])
    for summary in report["summary"]:
        for method in ("original","candidate"):
            rows = [c for c in cases if c["stage"] == "evaluation" and c["family"] == summary["family"] and c["source"].startswith(method)]
            assert summary[method] == {"successes":sum(c["outcome"]["full_success"] for c in rows),
                "collisions":sum(c["outcome"]["collision"] for c in rows),"reasons":dict(Counter(c["outcome"]["reason"] for c in rows))}
    assert report["max_replay_state_error"] == 0
    assert (D/"traces.zip").stat().st_size <= plan["trace_cap_bytes"] == 64*1024**2
    print("Robustness repair: 208 complete practice cases, three trained candidates, validation-only selection and all negative outcomes verified")


if __name__ == "__main__": verify()
