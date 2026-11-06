"""Measure real loader stepping separately from controller work and export."""

import argparse
import json
from pathlib import Path
import platform
import resource
import time

import numpy as np

from .controller import ReferenceController
from .environment import LoaderEnv
from .evaluate import source_identity


def control_trace():
    env, controller = LoaderEnv(1, seed=0), ReferenceController(1)
    trace = []
    for _ in range(600):
        action = controller.act(env.observe())
        trace.append(action[0])
        _, _, terminated, truncated, _ = env.step(action)
        if (terminated | truncated).any():
            break
    return np.asarray(trace)


def profile(sizes=(1, 16, 32, 64), steps=400, repeats=3):
    preparation = time.perf_counter()
    trace = control_trace()
    preparation_s = time.perf_counter()-preparation
    rows = []
    for size in sizes:
        trials = []
        for repeat in range(repeats):
            env = LoaderEnv(size, seed=repeat)
            actions = np.tile(trace[:, None, :], (1, size, 1))
            # Warm up allocations and native NumPy paths before timed stepping.
            for _ in range(5):
                env.step(actions[0])
            env.reset(seed=repeat)
            step_s, reset_s, completed, successes = 0.0, 0.0, 0, 0
            for index in range(steps):
                started = time.perf_counter()
                _, _, terminated, truncated, info = env.step(actions[index % len(trace)])
                step_s += time.perf_counter()-started
                done = terminated | truncated
                completed += int(done.sum())
                successes += int((info["metrics"]["reason"] == "success").sum())
                if done.any():
                    started = time.perf_counter()
                    env.reset(mask=done)
                    reset_s += time.perf_counter()-started
            trials.append({"step_s": step_s, "reset_s": reset_s,
                "environment_steps": size*steps, "completed_episodes": completed,
                "successes": successes, "environment_steps_s": size*steps/step_s})
        rows.append({"num_envs": size, "trials": trials,
                     "median_environment_steps_s": float(np.median([r["environment_steps_s"] for r in trials]))})
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak_mib = peak/(1024**2 if platform.system() == "Darwin" else 1024)
    return {"schema_version": "1.0", "source_mode": "recorded_synthetic",
            "calibrated": False, "source": source_identity(),
            "hardware": {"system": platform.system(), "machine": platform.machine(),
                         "python": platform.python_version(), "numpy": np.__version__},
            "steps_per_trial": steps, "repeats": repeats, "rows": rows,
            "control_trace_preparation_s": preparation_s, "peak_process_mib": peak_mib,
            "policy_inference_s": 0, "optimiser_updates": 0,
            "method": "Precomputed conventional-control actions; step timer includes observations, validation and diagnostics. Resets, control preparation and JSON serialisation excluded. Episode outcomes are workload diagnostics, not controller evaluation."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", type=int, default=400)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.steps <= 10000 or not 1 <= args.repeats <= 10:
        parser.error("steps/repeats exceed bounded profiling limits")
    if args.output.exists():
        parser.error("output exists; choose a new path")
    report = profile(steps=args.steps, repeats=args.repeats)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False)+"\n")
    print(json.dumps({"output": str(args.output), "rows": [
        {k: r[k] for k in ("num_envs", "median_environment_steps_s")} for r in report["rows"]]}))


if __name__ == "__main__":
    main()
