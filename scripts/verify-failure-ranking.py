"""Verify diagnostic provenance and complete paired counts without executing actors."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "docs/phase-11/failure-ranking-evidence"
ORDER = ["range_dropout", "blocked", "start_offset", "low", "range_impaired",
         "steep", "ridge", "low_grip", "high_resistance", "rubble"]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify():
    raw = (D/"report.json").read_bytes(); report = json.loads(raw)
    assert len(raw) <= report["max_output_bytes"] == 2*1024**2
    assert report["wall_s"] <= report["cap_s"] == 60
    assert report["max_trace_bytes"] == 32*1024**2
    assert report["retained_cases"] == len(report["cases"]) == 416
    assert report["order"] == ORDER
    assert report["new_policy_queries"] == report["teacher_queries"] == report["new_environment_decisions"] == report["optimiser_updates"] == 0
    expected_inputs = {"docs/phase-11/shift-evidence/"+n for n in ("report.json","traces.zip","source.zip")}
    expected_inputs |= {"docs/phase-11/failure-ranking-plan.md", "scripts/research/rank-robustness-failures.py"}
    assert set(report["inputs"]) == expected_inputs
    for path, digest in report["inputs"].items():
        assert sha((ROOT/path).read_bytes()) == digest, path
    with zipfile.ZipFile(ROOT/"docs/phase-11/shift-evidence/source.zip") as z:
        assert len(report["archived_source_sha256"]) == 4
        for path, digest in report["archived_source_sha256"].items():
            assert sha(z.read(path)) == sha((ROOT/path).read_bytes()) == digest
    original = json.loads((ROOT/"docs/phase-11/shift-evidence/report.json").read_text())
    old = {c["identity"]:c for c in original["cases"]}
    assert len(old) == len({c["identity"] for c in report["cases"]}) == 416
    for c in report["cases"]:
        for key in ("family","seed","source","identity","trace","sha256","reason","full_success",
                    "collision","decisions","delivered_kg","carried_kg","peak_load_kg","spilled_kg"):
            assert c[key] == old[c["identity"]][key], (c["identity"],key)
        assert sum(c["phase_decisions"].values()) == c["decisions"]
        assert c["terminal_stage"] in c["phase_decisions"]
        assert set(c["first_phase_entry_s"]) == set(c["phase_decisions"])
        assert c["initial_available_mass_kg"] >= 2000
        assert c["max_mass_residual_kg"] < 1e-7
        assert abs(c["transfer_totals_kg"]["loaded_kg"]-sum(c[k] for k in ("carried_kg","delivered_kg","spilled_kg"))) < 1e-7
        r = c["range"]
        assert 0 <= r["nonneutral_drive_when_invalid_decisions"] <= r["completely_invalid_decisions"] <= c["decisions"]
        assert 0 <= r["moving_when_invalid_decisions"] <= r["completely_invalid_decisions"]
        assert 0 <= r["longest_invalid_decisions"] <= r["completely_invalid_decisions"]
        assert 0 <= r["fresh_decisions"] <= c["decisions"]
        assert 0 <= r["mean_valid_fraction"] <= 1
        assert 0 <= r["distance_when_invalid_m"] <= c["path_length_m"]+1e-7
        assert 0 <= c["tail_carry_decisions"] <= 50
    assert report["analysed_decisions"] == sum(c["decisions"] for c in report["cases"]) == original["evaluation_decisions"] == 154244
    assert len(report["families"]) == 13
    assert {f["family"] for f in report["families"]} == set(original["plan"]["families"])
    for f in report["families"]:
        rows = [c for c in report["cases"] if c["family"] == f["family"]]
        neural = [c for c in rows if c["source"] != "reference"]
        refs = {c["seed"]:c for c in rows if c["source"] == "reference"}
        assert len(rows) == 32 and len(neural) == 24 and len(refs) == 8
        assert f["rank"] == (ORDER.index(f["family"])+1 if f["family"] in ORDER else None)
        subsets = [(f["neural"],neural),(f["reference"],list(refs.values()))]
        for source in original["plan"]["sources"]:
            subset = [c for c in rows if c["source"] == source]
            summary = f["by_source"][source]
            prior = next(s for s in original["summaries"] if s["family"] == f["family"] and s["source"] == source)
            assert all(summary[k] == prior[k] for k in ("cases","successes","collisions","reasons"))
            subsets.append((summary,subset))
        for s, subset in subsets:
            failed = [c for c in subset if not c["full_success"]]
            assert s["cases"] == len(subset)
            assert s["successes"] == sum(c["full_success"] for c in subset)
            assert s["collisions"] == sum(c["collision"] for c in subset)
            assert s["reasons"] == dict(Counter(c["reason"] for c in subset))
            assert s["failed_terminal_stages"] == dict(Counter(c["terminal_stage"] for c in failed))
            assert s["failed_peak_load_below_target"] == sum(c["peak_load_kg"] < 2000 for c in failed)
            assert s["failed_carry_with_payload_at_least_target"] == sum(c["terminal_stage"] == "carry" and c["carried_kg"] >= 2000 for c in failed)
            assert s["failed_with_partial_delivery"] == sum(c["delivered_kg"] > 0 for c in failed)
            assert s["cases_with_pickup_in_approach"] == sum(c["pickup_while_approach_kg"] > 1e-7 for c in subset)
            assert s["cases_with_no_height_cue"] == sum(c["range"]["observed_height_cue_decisions"] == 0 for c in subset)
            assert s["invalid_decisions"] == sum(c["range"]["completely_invalid_decisions"] for c in subset)
            assert s["nonneutral_drive_when_invalid_decisions"] == sum(c["range"]["nonneutral_drive_when_invalid_decisions"] for c in subset)
            assert abs(s["distance_when_invalid_m"]-sum(c["range"]["distance_when_invalid_m"] for c in subset)) < 1e-7
            assert s["min_initial_available_mass_kg"] == min(c["initial_available_mass_kg"] for c in subset)
        pairs = Counter()
        for c in neural:
            a,b = c["full_success"], refs[c["seed"]]["full_success"]
            pairs[{(True,True):"both_success",(False,True):"reference_only_success",
                   (True,False):"neural_only_success",(False,False):"both_fail"}[a,b]] += 1
        assert f["paired_neural_reference"] == dict(pairs)
    manifest = json.loads((D/"files.json").read_text())
    for path, digest in manifest.items():
        p = (ROOT/path).resolve(); assert p.is_relative_to(ROOT)
        assert sha(p.read_bytes()) == digest, path
    print("PASS: 416 consumed cases, complete ten-family ranking, paired outcomes and diagnostic provenance")


if __name__ == "__main__":
    verify()
