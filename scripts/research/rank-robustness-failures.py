#!/usr/bin/env python3
"""Rank consumed stress traces without importing or executing any controller."""
from collections import Counter
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import time
import zipfile

ROOT = Path(__file__).resolve().parents[2]
E = ROOT / "docs/phase-11/shift-evidence"
D = ROOT / "docs/phase-11/failure-ranking-evidence"
ORDER = ("range_dropout", "blocked", "start_offset", "low", "range_impaired",
         "steep", "ridge", "low_grip", "high_resistance", "rubble")
STAGES = ("approach", "fill", "lift", "carry", "tip")
SOURCE_NAMES = ("controller", "environment", "phase_memory", "wm_state")
MAX_TRACE_BYTES = 32 * 1024**2


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def mean(values):
    return sum(values) / len(values) if values else None


def metrics(case, trace):
    frames = trace["frames"][:-1]
    final = trace["frames"][-1]
    if len(frames) != case["decisions"] or not frames:
        raise ValueError("decision coverage differs")
    if trace["identity"] != case["identity"] or trace["scenario"] != case["scenario"]:
        raise ValueError("trace identity differs")
    if trace["source"] != case["source"] or trace["checkpoint_sha256"] != case["checkpoint_sha256"]:
        raise ValueError("controller identity differs")
    if trace["outcome"] != {k: case[k] for k in trace["outcome"]}:
        raise ValueError("trace outcome differs")
    phase_counts = Counter(); entries = {}; valid_fractions = []; ages = []
    invalid = nonneutral = moving = longest = streak = fresh = cues = 0
    invalid_distance = approach_pickup = 0.; first_pickup = None
    transfers = Counter(); max_mass = 0.; path = 0.
    for index, frame in enumerate(frames):
        state = frame["state"]; nxt = frame["next_state"]
        if nxt != trace["frames"][index+1]["state"]:
            raise ValueError("broken state continuity")
        if len(state) != 102 or not all(math.isfinite(x) for x in state):
            raise ValueError("invalid state")
        phase = frame["phase"]
        if phase not in range(5): raise ValueError("unknown phase")
        phase_counts[STAGES[phase]] += 1
        entries.setdefault(STAGES[phase], frame["t_s"])
        obs = frame["observation"]; p = obs["proprio"]
        if set(obs) != {"proprio", "local_height_m", "range_valid"} or len(p) != 15:
            raise ValueError("observation contract differs")
        valid = [v for row in obs["range_valid"] for v in row]
        height = [v for row in obs["local_height_m"] for v in row]
        if len(valid) != 25 or len(height) != 25 or any(v not in (0, 1) for v in valid):
            raise ValueError("invalid range shape or mask")
        valid_fractions.append(sum(valid)/25); ages.append(p[11]); fresh += bool(p[12])
        cues += max(h*v for h,v in zip(height, valid)) > .1
        distance = math.hypot(nxt[0]-state[0], nxt[1]-state[1]); path += distance
        if not any(valid):
            invalid += 1; streak += 1; longest = max(longest, streak)
            nonneutral += abs(frame["action"][0]) > .05
            moving += abs(state[3]) > .08
            invalid_distance += distance
        else:
            streak = 0
        for key, value in frame["transfer"].items(): transfers[key] += value
        loaded = frame["transfer"]["loaded_kg"]
        if loaded > 1e-7 and first_pickup is None: first_pickup = frame["t_s"]
        if phase == 0: approach_pickup += loaded
        max_mass = max(max_mass, abs(sum(state[15:79])*.25*state[81]+sum(state[7:10])-state[82]))
    last = frames[-1]; p = last["observation"]["proprio"]
    tail = [f for f in frames[-50:] if f["phase"] == 3]
    s = final["state"]
    max_mass = max(max_mass, abs(sum(s[15:79])*.25*s[81]+sum(s[7:10])-s[82]))
    if max_mass > 1e-7 or abs(transfers["delivered_kg"]-case["delivered_kg"]) > 1e-7:
        raise ValueError("material ledger differs")
    if abs(transfers["spilled_kg"]-case["spilled_kg"]) > 1e-7:
        raise ValueError("spillage ledger differs")
    peak = max(f["state"][7] for f in trace["frames"])
    # Kernel peaks include physical substeps between the recorded decisions.
    if peak > case["peak_load_kg"]+1e-7:
        raise ValueError("sampled payload exceeds recorded physical peak")
    if frames[0]["state"][7] != 0 or abs(transfers["loaded_kg"]-sum(s[7:10])) > 1e-7:
        raise ValueError("empty-start acquisition ledger differs")
    return {"family": case["family"], "source": case["source"], "seed": case["seed"],
            "identity": case["identity"], "trace": case["trace"], "sha256": case["sha256"],
            **{k:case[k] for k in ("reason", "full_success", "collision", "decisions",
                                  "delivered_kg", "carried_kg", "peak_load_kg", "spilled_kg")},
            "terminal_stage": STAGES[final["phase"]], "phase_decisions": dict(phase_counts),
            "first_phase_entry_s": entries, "initial_available_mass_kg": frames[0]["state"][82],
            "transfer_totals_kg": dict(transfers), "first_pickup_s": first_pickup,
            "pickup_while_approach_kg": approach_pickup,
            "final_state": {"x_m":s[0], "y_m":s[1], "yaw_rad":s[2], "speed_m_s":s[3],
                            "stuck_time_s":s[11], "slip_s":s[13], "slip_ratio":s[14]},
            "last_input": {"x_m":p[0], "speed_m_s":p[4], "load_kg":p[8],
                           "receiver_mouth_error_m":p[9]-(1.8+(1.6+1.2*math.cos(p[6]))*math.cos(p[5])),
                           "drive_command":last["action"][0]},
            "tail_carry_decisions":len(tail),
            "tail_carry_mean_abs_speed_m_s":mean([abs(f["state"][3]) for f in tail]),
            "tail_carry_mean_drive_command":mean([f["action"][0] for f in tail]),
            "path_length_m":path, "range": {
                "mean_valid_fraction":mean(valid_fractions), "fresh_decisions":fresh,
                "max_age_s":max(ages), "observed_height_cue_decisions":cues,
                "completely_invalid_decisions":invalid, "longest_invalid_decisions":longest,
                "nonneutral_drive_when_invalid_decisions":nonneutral,
                "moving_when_invalid_decisions":moving, "distance_when_invalid_m":invalid_distance},
            "max_mass_residual_kg":max_mass}


def summary(rows):
    failed = [r for r in rows if not r["full_success"]]
    return {"cases":len(rows), "successes":sum(r["full_success"] for r in rows),
            "collisions":sum(r["collision"] for r in rows),
            "reasons":dict(Counter(r["reason"] for r in rows)),
            "failed_terminal_stages":dict(Counter(r["terminal_stage"] for r in failed)),
            "failed_peak_load_below_target":sum(r["peak_load_kg"] < 2000 for r in failed),
            "failed_carry_with_payload_at_least_target":sum(r["terminal_stage"] == "carry" and r["carried_kg"] >= 2000 for r in failed),
            "failed_with_partial_delivery":sum(r["delivered_kg"] > 0 for r in failed),
            "cases_with_pickup_in_approach":sum(r["pickup_while_approach_kg"] > 1e-7 for r in rows),
            "cases_with_no_height_cue":sum(r["range"]["observed_height_cue_decisions"] == 0 for r in rows),
            "invalid_decisions":sum(r["range"]["completely_invalid_decisions"] for r in rows),
            "nonneutral_drive_when_invalid_decisions":sum(r["range"]["nonneutral_drive_when_invalid_decisions"] for r in rows),
            "distance_when_invalid_m":sum(r["range"]["distance_when_invalid_m"] for r in rows),
            "min_initial_available_mass_kg":min(r["initial_available_mass_kg"] for r in rows)}


def execute():
    started = time.monotonic()
    output = D / "report.json"
    if output.exists(): raise FileExistsError(output)
    inputs = {str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in
              (E/"report.json", E/"traces.zip", E/"source.zip",
               ROOT/"docs/phase-11/failure-ranking-plan.md", Path(__file__).resolve())}
    report = json.loads((E/"report.json").read_text())
    if inputs[str((E/"traces.zip").relative_to(ROOT))] != report["trace_archive_sha256"]:
        raise ValueError("stress archive hash differs")
    expected = {(f,s,b) for f in report["plan"]["families"] for s in report["plan"]["sources"] for b in report["plan"]["seeds"]}
    if len(report["cases"]) != 416 or {(c["family"],c["source"],c["seed"]) for c in report["cases"]} != expected:
        raise ValueError("incomplete stress catalogue")
    sources = {}
    with zipfile.ZipFile(E/"source.zip") as z:
        for name in SOURCE_NAMES:
            path = "training/kessel_training/"+name+".py"
            sources[path] = sha(z.read(path))
    cases = []
    with zipfile.ZipFile(E/"traces.zip") as z:
        for case in report["cases"]:
            if time.monotonic()-started > 60: raise TimeoutError("60-second analysis cap exceeded")
            if z.getinfo(case["trace"]).file_size > MAX_TRACE_BYTES:
                raise ValueError("compressed trace exceeds cap")
            raw = z.read(case["trace"])
            if sha(raw) != case["sha256"]: raise ValueError("trace digest differs")
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
                payload = stream.read(MAX_TRACE_BYTES+1)
            if len(payload) > MAX_TRACE_BYTES: raise ValueError("decompressed trace exceeds cap")
            cases.append(metrics(case, json.loads(payload)))
    families = []
    for family in report["plan"]["families"]:
        rows = [c for c in cases if c["family"] == family]
        neural = [c for c in rows if c["source"] != "reference"]
        refs = {c["seed"]:c for c in rows if c["source"] == "reference"}
        paired = Counter()
        for c in neural:
            ref = refs[c["seed"]]
            label = ("both_success" if c["full_success"] and ref["full_success"] else
                     "reference_only_success" if ref["full_success"] else
                     "neural_only_success" if c["full_success"] else "both_fail")
            paired[label] += 1
        families.append({"family":family, "rank":ORDER.index(family)+1 if family in ORDER else None,
                         "neural":summary(neural), "reference":summary(list(refs.values())),
                         "by_source":{s:summary([c for c in rows if c["source"] == s]) for s in report["plan"]["sources"]},
                         "paired_neural_reference":dict(paired)})
    duration = time.monotonic()-started
    if duration > 60: raise TimeoutError("60-second analysis cap exceeded")
    result = {"kind":"retained-robustness-failure-ranking-v1", "date":"2026-11-24",
              "role":"diagnosis on consumed original-policy traces; no new qualification",
              "inputs":inputs, "archived_source_sha256":sources, "order":list(ORDER),
              "families":families, "cases":cases, "retained_cases":len(cases),
              "analysed_decisions":sum(c["decisions"] for c in cases),
              "new_policy_queries":0, "teacher_queries":0, "new_environment_decisions":0,
              "optimiser_updates":0, "execution":"serial Python standard library; no numerical libraries",
              "wall_s":duration, "cap_s":60, "max_trace_bytes":MAX_TRACE_BYTES,
              "max_output_bytes":2*1024**2}
    data = json.dumps(result, indent=2, allow_nan=False)+"\n"
    if len(data.encode()) > result["max_output_bytes"]: raise ValueError("output cap exceeded")
    D.mkdir(exist_ok=True)
    with output.open("x") as f: f.write(data)
    print(f"Analysed {len(cases)} retained cases in {duration:.2f}s; no controller or simulator queries")
    for f in sorted((f for f in families if f["rank"]), key=lambda f:f["rank"]):
        print(f["rank"], f["family"], "neural", f["neural"]["successes"], "/24; collisions", f["neural"]["collisions"],
              "; failed stages", f["neural"]["failed_terminal_stages"])


if __name__ == "__main__":
    execute()
