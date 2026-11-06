#!/usr/bin/env python3
"""Package the completed RL study without publishing resumable training state."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    def reject(value):
        raise ValueError(f"non-finite JSON: {value}")
    return json.loads(path.read_text(), parse_constant=reject)


def write(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False)+"\n")


def package(source, output):
    if output.exists():
        raise FileExistsError("choose a new evidence directory")
    completed, manifest = read(source/"completed.json"), read(source/"manifest.json")
    plan = read(source/"plan.json")
    if completed["training_runs"] != plan["maximum_training_runs"]:
        raise ValueError("study does not contain its declared training runs")
    canonical_plan = json.dumps(plan, sort_keys=True, separators=(",", ":"), allow_nan=False)
    if hashlib.sha256(canonical_plan.encode()).hexdigest() != manifest["plan_sha256"]:
        raise ValueError("predeclared study plan hash differs")
    raw_reports = sorted((source/"runs").glob("*/run.json"))
    if len(raw_reports) != completed["training_runs"]:
        raise ValueError("missing training reports")
    runs, curves, episodes = [], {}, {}
    for path in raw_reports:
        run = read(path)
        if run["source"]["package_sha256"] != manifest["source"]["package_sha256"] or run["source"]["training_dirty"]:
            raise ValueError("training sources were not consistently frozen")
        name = path.parent.name
        runs.append({"name": name, "configuration": run["configuration"],
            "configuration_sha256": run["configuration_sha256"], "source": run["source"],
            "network": run["network"], "counters": run["counters"], "training_wall_s": run["training_wall_s"],
            "stop_reason": run["stop_reason"], "randomisation": run["randomisation"],
            "curriculum_transitions": run["curriculum_transitions"],
            "validation": read(path.parent/"validation.json"), "raw_report_sha256": digest(path)})
        curves[name] = [{k: v for k, v in row.items() if k != "minibatches"} for row in run["learning_curve"]]
        episodes[name] = run["episodes"]
    output.mkdir(parents=True)
    names = ("plan.json", "manifest.json", "completed.json", "comparison.json", "robustness.json",
             "adversarial.json", "replay-summary.json", "checkpoint-replay.json.gz")
    for name in names:
        shutil.copyfile(source/name, output/name)
    for name in ("selection.json", "full-and-ablations.json"):
        value = read(source/name)
        # Paths are local acquisition details. Retain checkpoint identity and rollout.
        def scrub(item):
            if isinstance(item, dict):
                return {k: scrub(v) for k, v in item.items() if k != "path"}
            if isinstance(item, list):
                return [scrub(v) for v in item]
            return item
        write(output/name, scrub(value))
    write(output/"runs.json", runs)
    for name, value in (("learning-curves.json.gz", curves), ("training-episodes.json.gz", episodes)):
        with gzip.GzipFile(filename=str(output/name), mode="wb", mtime=0) as stream:
            stream.write(json.dumps(value, separators=(",", ":"), allow_nan=False).encode())
    (output/"policies").mkdir()
    for path in sorted((source/"policies").glob("*.pt")):
        if digest(path) != path.with_suffix(".pt.sha256").read_text().strip():
            raise ValueError("policy artifact hash differs")
        shutil.copyfile(path, output/"policies"/path.name)
        shutil.copyfile(path.with_suffix(".pt.sha256"), output/"policies"/(path.name+".sha256"))
    files = [{"path": str(p.relative_to(output)), "sha256": digest(p), "bytes": p.stat().st_size}
             for p in sorted(output.rglob("*")) if p.is_file()]
    write(output/"files.json", {"source_mode": "recorded_synthetic", "files": files,
          "notes": "Every rollout curve and training episode is retained. Curves omit per-minibatch rows but retain update aggregates. Policies are compact executable exports, not resumable simulator/optimiser archives."})
    return {"files": len(files), "bytes": sum(f["bytes"] for f in files), "training_runs": len(runs)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(package(args.source, args.output)))
