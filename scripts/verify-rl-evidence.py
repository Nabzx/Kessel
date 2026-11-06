#!/usr/bin/env python3
"""Check packaged study accounting, source identity and executable-policy hashes."""

import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]/"docs/phase-11/rl-evidence"


def read(path):
    text = gzip.decompress(path.read_bytes()).decode() if path.suffix == ".gz" else path.read_text()
    return json.loads(text, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"non-finite JSON: {value}")))


def verify(root=ROOT):
    root = root.resolve()
    index = read(root/"files.json")
    for entry in index["files"]:
        path = (root/entry["path"]).resolve()
        if not path.is_relative_to(root):
            raise ValueError("evidence path escapes its directory")
        if path.stat().st_size != entry["bytes"] or hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            raise ValueError(f"evidence hash differs: {entry['path']}")
    manifest, plan, completed = (read(root/name) for name in ("manifest.json", "plan.json", "completed.json"))
    canonical = json.dumps(plan, sort_keys=True, separators=(",", ":"), allow_nan=False)
    if hashlib.sha256(canonical.encode()).hexdigest() != manifest["plan_sha256"]:
        raise ValueError("study plan hash differs")
    runs = read(root/"runs.json")
    if len(runs) != completed["training_runs"] or len(runs) != plan["maximum_training_runs"]:
        raise ValueError("study run count differs")
    source = manifest["source"]["package_sha256"]
    for run in runs:
        if run["source"]["package_sha256"] != source or run["source"]["training_dirty"]:
            raise ValueError("mixed or uncommitted training sources")
        canonical = json.dumps(run["configuration"], sort_keys=True, separators=(",", ":"), allow_nan=False)
        if hashlib.sha256(canonical.encode()).hexdigest() != run["configuration_sha256"]:
            raise ValueError("training configuration hash differs")
    for key in ("environment_steps", "completed_episodes", "optimiser_updates", "subtask_successes"):
        if sum(r["counters"][key] for r in runs) != completed[key]:
            raise ValueError(f"study count differs: {key}")
    curves = read(root/"learning-curves.json.gz")
    episodes = read(root/"training-episodes.json.gz")
    for run in runs:
        rows = curves[run["name"]]
        if len(rows) != run["counters"]["rollouts"] or len(episodes[run["name"]]) != run["counters"]["completed_episodes"]:
            raise ValueError("incomplete learning curves or episode outcomes")
        if rows[-1]["environment_steps"] != run["counters"]["environment_steps"]:
            raise ValueError("last learning-curve count differs")
    policy_hashes = {hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/"policies").glob("*.pt")}
    comparisons = read(root/"comparison.json")["records"]
    robustness = read(root/"robustness.json")["records"]
    scene_ids = {}
    for report in comparisons+robustness:
        if report["summary"]["episodes"] != len(report["cases"]):
            raise ValueError("evaluation case count differs")
        if report["controller_kind"] != "reference" and report["identity"]["checkpoint_sha256"] not in policy_hashes:
            raise ValueError("evaluation has no retained executable policy")
        if report["source"]["package_sha256"] != source:
            raise ValueError("evaluation source differs")
        key = (report["split"], report["family"], report["perturbation"])
        ids = [c["scenario_sha256"] for c in report["cases"]]
        if key in scene_ids and scene_ids[key] != ids:
            raise ValueError("controllers were evaluated on different scenes")
        scene_ids[key] = ids
    replay = read(root/"checkpoint-replay.json.gz")
    for item in replay["replays"]:
        if item["evaluation"]["identity"]["checkpoint_sha256"] not in policy_hashes:
            raise ValueError("replay has no retained executed checkpoint")
        for trace in item["traces"].values():
            if len(trace["frames"]) != trace["case"]["steps"] or trace["final_record"]["action"] is not None:
                raise ValueError("replay boundary differs")
            if any(len(frame["action"]) != 4 or max(map(abs, frame["action"])) > 1 for frame in trace["frames"]):
                raise ValueError("replay actions violate the contract")
    return {"training_runs": len(runs), "comparison_reports": len(comparisons),
            "robustness_reports": len(robustness), "retained_policies": len(policy_hashes),
            "replay_milestones": len(replay["replays"]), "files": len(index["files"])}


if __name__ == "__main__":
    print(json.dumps(verify()))
