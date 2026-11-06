"""Evaluate the fixed observation-only reference and retain success/failure traces."""

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import time

import numpy as np

from .contracts import canonical_json
from .controller import ReferenceController
from .environment import LoaderEnv
from .scenarios import family, scenario_seed


def source_identity():
    root = Path(__file__).parent
    digest = hashlib.sha256()
    for path in sorted(root.glob("*.py")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, cwd=root).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain", "--", "training"], text=True, cwd=root.parent.parent))
    except (OSError, subprocess.CalledProcessError):
        commit, dirty = None, None
    return {"package_sha256": digest.hexdigest(), "git_commit": commit, "training_dirty": dirty}


def evaluate(split="validation", count=4, families=("standard", "low_grip", "occluded", "blocked")):
    start = time.perf_counter()
    records, traces = [], {}
    settings = ReferenceController(1).settings()
    controller_hash = hashlib.sha256(canonical_json(settings).encode()).hexdigest()
    for name in families:
        scene, difficulty = family(name)
        for index in range(count):
            seed = scenario_seed(split, index)
            env = LoaderEnv(1, seed=seed, scene=scene)
            controller = ReferenceController(1)
            identity = env.scenario_identity()[0]
            pile_hash = env.initial_pile_hashes[0]
            trace = []
            while True:
                observation = env.observe()
                action = controller.act(observation)
                _, reward, term, trunc, info = env.step(action)
                trace.append({"time_s": float(env.elapsed[0]), "pose": env.pose[0].tolist(),
                    "joints": env.joints[0].tolist(), "action": action[0].tolist(),
                    "carried_kg": float(env.payload[0]), "delivered_kg": float(env.delivered[0]),
                    "spilled_kg": float(env.spilled[0]), "reward": float(reward[0]),
                    "loaded_kg": float(info["transfer"]["loaded_kg"][0]),
                    "phase": int(controller.phase[0])})
                if (term | trunc).any():
                    break
            metrics = {k: v[0].item() for k, v in info["metrics"].items()}
            record = {"family": name, "difficulty": difficulty, "seed": seed,
                      "stream_id": 0, "scenario_sha256": identity,
                      "scene": asdict(scene), "steps": len(trace),
                      "terminated": bool(term[0]), "truncated": bool(trunc[0]), **metrics}
            records.append(record)
            outcome = "success" if metrics["reason"] == "success" else "failure"
            # First result of each kind, never a hand-selected attractive episode.
            if outcome not in traces:
                traces[outcome] = {"case": record, "frames": trace,
                    "initial_pile_sha256": pile_hash}
    successes = sum(r["reason"] == "success" for r in records)
    return {"schema_version": "1.0", "source_mode": "recorded_synthetic",
            "controller_kind": "conventional_feedback", "calibrated": False,
            "split": split, "source": source_identity(),
            "hardware": {"system": platform.system(), "machine": platform.machine(),
                         "python": platform.python_version(), "numpy": np.__version__},
            "controller": settings, "controller_sha256": controller_hash,
            "counts": {"episodes": len(records), "successes": successes,
                       "environment_steps": sum(r["steps"] for r in records),
                       "policy_updates": 0},
            "wall_s": time.perf_counter()-start, "cases": records,
            "representative_traces": traces}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=("train", "validation", "test"), default="validation")
    parser.add_argument("--count", type=int, default=4)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.count < 1 or args.count > 100:
        parser.error("count must be between 1 and 100 per family")
    if args.output.exists():
        parser.error("output exists; choose a new path")
    report = evaluate(args.split, args.count)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False)+"\n")
    print(json.dumps({"output": str(args.output), **report["counts"], "wall_s": report["wall_s"]}))


if __name__ == "__main__":
    main()
