"""Bounded PPO execution check, not a checkpointed learning experiment."""

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import platform
import resource
import time

import torch

from .environment import LoaderEnv
from .evaluate import source_identity
from .policy import ActorCritic, configure_cpu
from .ppo import PPO, collect


def state_hash(policy):
    digest = hashlib.sha256()
    for name, tensor in sorted(policy.state_dict().items()):
        digest.update(name.encode())
        digest.update(tensor.detach().cpu().numpy().tobytes())
    return digest.hexdigest()


def smoke(seed=7, num_envs=32, rollout_steps=20, updates=4):
    if not 1 <= num_envs <= 64 or not 1 <= rollout_steps <= 64 or not 1 <= updates <= 4:
        raise ValueError("core smoke exceeds its bounded workload")
    started = time.perf_counter()
    generator = configure_cpu(seed)
    policy = ActorCritic()
    env = LoaderEnv(num_envs, seed=seed)
    algorithm = PPO(policy)
    before = state_hash(policy)
    records, episodes = [], []
    collection_s, update_s = 0.0, 0.0
    for update in range(updates):
        t = time.perf_counter()
        rollout = collect(env, policy, rollout_steps, generator)
        collection_s += time.perf_counter()-t
        episodes.extend(rollout.episodes)
        t = time.perf_counter()
        stats = algorithm.update(rollout, generator)
        update_s += time.perf_counter()-t
        records.append({"rollout_index": update, **stats})
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return {"schema_version": "1.0", "source_mode": "recorded_synthetic",
        "purpose": "PPO execution check; no task-improvement claim or checkpoint selection",
        "source": source_identity(), "seed": seed, "network": policy.description(),
        "ppo": asdict(algorithm.config), "reward": asdict(env.reward_config),
        "num_envs": num_envs, "rollout_steps": rollout_steps,
        "counts": {"environment_steps": num_envs*rollout_steps*updates,
                   "rollouts": len(records), "minibatch_updates": sum(r["minibatch_updates"] for r in records),
                   "completed_episodes": len(episodes), "successes": sum(e["reason"] == "success" for e in episodes)},
        "timing": {"collection_s": collection_s, "update_s": update_s,
                   "wall_s_excluding_import": time.perf_counter()-started},
        "peak_process_mib": peak/(1024**2 if platform.system() == "Darwin" else 1024),
        "torch_version": torch.__version__, "initial_state_sha256": before,
        "final_state_sha256": state_hash(policy), "updates": records, "episodes": episodes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--num-envs", type=int, default=32)
    parser.add_argument("--rollout-steps", type=int, default=20)
    parser.add_argument("--updates", type=int, default=4)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output exists; choose a new path")
    report = smoke(args.seed, args.num_envs, args.rollout_steps, args.updates)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False)+"\n")
    print(json.dumps({"output": str(args.output), **report["counts"], **report["timing"]}))


if __name__ == "__main__":
    main()
