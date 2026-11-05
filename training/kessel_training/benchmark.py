"""Disposable CPU feasibility spike, not the task simulator or a trained policy."""

import argparse
from datetime import datetime, timezone
import json
import platform
from pathlib import Path
import resource
import subprocess
import sys
import time

import numpy as np

from .contracts import LoaderConfig, validate_actions


class LoadingSpike:
    """Small, uncalibrated mass-transfer workload with bounded loader controls.

    The primitive mode runs one second of a fixed approach/scoop/retract servo.
    Control mode accepts rates for 0.1 seconds. Neither models granular contact,
    proper vehicle articulation, collisions, perception or learned behaviour.
    """

    def __init__(self, num_envs, mode="control", seed=42, horizon=20):
        validate_actions(np.zeros((num_envs, 4)), num_envs)
        if mode not in {"control", "primitive"} or horizon <= 0:
            raise ValueError("invalid benchmark mode or horizon")
        self.n = num_envs
        self.mode = mode
        self.seed = seed
        self.horizon = horizon
        self.config = LoaderConfig()
        self.substeps = 5 if mode == "control" else 50
        self.dt = self.config.physical_step_s
        self.rng = np.random.default_rng(seed)
        self.state = np.zeros((num_envs, 8), dtype=np.float64)
        self.steps = np.zeros(num_envs, dtype=np.int64)
        self.initial_mass = np.zeros(num_envs)
        self.reset()

    def reset(self, mask=None):
        if mask is None:
            mask = np.ones(self.n, dtype=bool)
        mask = np.asarray(mask, dtype=bool)
        if mask.shape != (self.n,):
            raise ValueError("reset mask has wrong shape")
        self.state[mask] = 0
        self.state[mask, 3] = 0.1
        self.state[mask, 6] = self.rng.uniform(8000, 12000, mask.sum())
        self.initial_mass[mask] = self.state[mask, 6]
        self.steps[mask] = 0
        return self.observe()

    def observe(self):
        # x, velocity, articulation, boom, bucket, carried kg, pile kg, removed kg.
        return self.state / np.array([10, 2, 0.6, 1.1, 1, 3500, 12000, 3500])

    def step(self, actions):
        commands = validate_actions(actions, self.n)
        if (self.steps >= self.horizon).any():
            raise RuntimeError("reset finished benchmark episodes before stepping")
        if self.mode == "primitive":
            # Three authored servos, selected through the first scalar only.
            choice = np.where(commands[:, 0] < -1/3, 0,
                              np.where(commands[:, 0] > 1/3, 2, 1))
            commands = np.array([[1, 0, -0.3, -0.3], [0.6, 0, 0.2, 1],
                                 [-1, 0, 1, 0]], dtype=np.float64)[choice]
        s, c, dt = self.state, self.config, self.dt
        for _ in range(self.substeps):
            s[:, 1] = np.clip(s[:, 1] + commands[:, 0] * c.acceleration_m_s2 * dt,
                              -c.reverse_m_s, c.forward_m_s)
            s[:, 0] += s[:, 1] * dt
            s[:, 2] = np.clip(s[:, 2] + commands[:, 1] * c.articulation_rate_rad_s * dt,
                              -c.articulation_rad, c.articulation_rad)
            s[:, 3] = np.clip(s[:, 3] + commands[:, 2] * c.boom_rate_rad_s * dt,
                              c.boom_min_rad, c.boom_max_rad)
            s[:, 4] = np.clip(s[:, 4] + commands[:, 3] * c.bucket_rate_rad_s * dt,
                              c.bucket_min_rad, c.bucket_max_rad)
            contact = (s[:, 0] >= 2.5) & (s[:, 0] <= 4.5) & (s[:, 3] < 0.4)
            transfer = np.minimum(np.minimum(s[:, 6], c.payload_kg - s[:, 5]),
                                  np.maximum(commands[:, 3], 0) * 5000 * dt * contact)
            s[:, 6] -= transfer
            s[:, 5] += transfer
            # Removed material merges deposit/spillage in this reduced workload.
            unload = np.minimum(s[:, 5], s[:, 5] * 3 * dt * (s[:, 4] < -0.2))
            s[:, 5] -= unload
            s[:, 7] += unload
        self.steps += 1
        return self.observe(), self.steps >= self.horizon


def _peak_rss_mb():
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return rss / (1024**2 if sys.platform == "darwin" else 1024)


def _git_source():
    root = Path(__file__).resolve().parents[2]
    def read(*args):
        result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
        return result.stdout.strip() if result.returncode == 0 else None
    # Only experiment sources affect this workload; unrelated hero CSS is separate.
    return {"commit": read("rev-parse", "HEAD"),
            "training_dirty": bool(read("status", "--porcelain", "--", "training"))}


def _cpu_name():
    if sys.platform == "darwin":
        result = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"],
                                capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    return platform.processor() or "unavailable"


def measure_environment(num_envs, mode, decisions, seed):
    env = LoadingSpike(num_envs, mode, seed)
    actions = np.random.default_rng(seed + 1).uniform(-1, 1, (32, num_envs, 4))
    completed = 0
    start = time.perf_counter()
    for i in range(decisions):
        _, ended = env.step(actions[i % len(actions)])
        completed += int(ended.sum())
        if ended.any():
            env.reset(ended)
    elapsed = time.perf_counter() - start
    steps = decisions * num_envs
    return {
        "mode": mode, "num_envs": num_envs, "decision_calls": decisions,
        "environment_steps": steps, "agent_decisions": steps,
        "completed_episodes": completed, "optimiser_updates": 0,
        "physical_substeps": steps * env.substeps,
        "simulated_seconds": steps * env.substeps * env.dt,
        "wall_seconds": elapsed, "environment_steps_per_second": steps / elapsed,
        "physical_substeps_per_second": steps * env.substeps / elapsed,
        "process_peak_rss_mb": _peak_rss_mb(),
    }


def measure_optimiser(torch, num_envs, updates, seed):
    torch.manual_seed(seed)
    env = LoadingSpike(num_envs, seed=seed)
    rng = np.random.default_rng(seed + 1)
    xs, ys = [], []
    for _ in range(32):
        obs = env.observe()
        action = rng.uniform(-1, 1, (num_envs, 4))
        next_obs, ended = env.step(action)
        xs.append(np.concatenate((obs, action), axis=1))
        ys.append(next_obs - obs)
        if ended.any():
            env.reset(ended)
    x = torch.tensor(np.concatenate(xs), dtype=torch.float32, device="cpu")
    y = torch.tensor(np.concatenate(ys), dtype=torch.float32, device="cpu")
    # A gradient workload only: no held-out model score or policy-learning claim.
    model = torch.nn.Sequential(torch.nn.Linear(12, 64), torch.nn.Tanh(),
                                torch.nn.Linear(64, 64), torch.nn.Tanh(),
                                torch.nn.Linear(64, 8)).cpu()
    optimiser = torch.optim.Adam(model.parameters(), lr=1e-3)
    batch = min(256, len(x))
    losses = []
    start = time.perf_counter()
    for update in range(updates):
        offset = update * batch % len(x)
        ids = (torch.arange(batch) + offset) % len(x)
        loss = torch.nn.functional.mse_loss(model(x[ids]), y[ids])
        optimiser.zero_grad(set_to_none=True)
        loss.backward()
        optimiser.step()
        losses.append(float(loss.detach()))
    elapsed = time.perf_counter() - start
    if not np.isfinite(losses).all():
        raise RuntimeError("non-finite benchmark gradient workload")
    return {
        "num_envs": num_envs, "dataset_transitions": len(x),
        "batch_size": batch, "optimiser_updates": updates,
        "wall_seconds": elapsed, "updates_per_second": updates / elapsed,
        "initial_mse": losses[0], "final_mse": losses[-1],
        "parameter_count": sum(p.numel() for p in model.parameters()),
        "process_peak_rss_mb": _peak_rss_mb(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--decisions", type=int, default=200)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--updates", type=int, default=40)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    if min(args.decisions, args.repeats, args.updates) <= 0:
        parser.error("decisions, repeats and updates must be positive")
    if args.output.exists():
        parser.error("output already exists; choose a new report path")
    import_start = time.perf_counter()
    import torch
    import_seconds = time.perf_counter() - import_start
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    batches = [1, 16] if args.smoke else [1, 16, 32, 64]
    if args.smoke:
        args.decisions, args.repeats, args.updates = 20, 1, 2
    started = time.perf_counter()
    environment = [measure_environment(n, mode, args.decisions, args.seed + repeat)
                   for mode in ("control", "primitive") for n in batches
                   for repeat in range(args.repeats)]
    optimisation = [measure_optimiser(torch, n, args.updates, args.seed) for n in batches]
    report = {
        "format": "kessel-cpu-spike-v1", "scope": "disposable_feasibility_benchmark",
        "created_at_utc": datetime.now(timezone.utc).isoformat(), "source": _git_source(),
        "hardware": {"cpu": _cpu_name(), "platform": platform.platform(),
                     "machine": platform.machine(), "device": "cpu", "torch_threads": 1},
        "software": {"python": platform.python_version(), "numpy": np.__version__,
                     "torch": torch.__version__},
        "config": {"seed": args.seed, "decisions": args.decisions,
                   "repeats": args.repeats, "updates": args.updates,
                   "config_sha256": LoaderConfig().digest()},
        "torch_import_seconds": import_seconds, "workload_wall_seconds": time.perf_counter() - started,
        "environment": environment, "optimisation": optimisation,
        "limitations": ["Not PPO, policy learning or a validated world model.",
                        "Primitive decisions advance ten times the physical time of control decisions.",
                        "RSS is the cumulative process high-water mark, not per-case allocated memory.",
                        "Mass transfer and one-dimensional travel are uncalibrated; no collision or sensing model."],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(f"Wrote CPU feasibility report to {args.output}")


if __name__ == "__main__":
    main()
