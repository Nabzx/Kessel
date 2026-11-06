"""Bounded, resumable CPU policy experiments on the synthetic loader."""

import argparse
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import signal
import time

import numpy as np
import torch

from . import checkpoints
from .contracts import canonical_json
from .environment import LoaderEnv, SceneConfig
from .evaluate import source_identity
from .policy import ActorCritic, configure_cpu
from .ppo import PPO, PPOConfig, collect


@dataclass(frozen=True)
class TrainConfig:
    seed: int = 7
    num_envs: int = 32
    hidden: int = 64
    rollout_steps: int = 20
    updates: int = 40
    max_wall_s: float = 30.0
    checkpoint_every: int = 10
    threads: int = 1
    scene: SceneConfig = field(default_factory=SceneConfig)
    ppo: PPOConfig = field(default_factory=PPOConfig)

    def __post_init__(self):
        ranges = {"seed": (0, 99999), "num_envs": (1, 64), "hidden": (8, 256),
                  "rollout_steps": (1, 128), "updates": (1, 10000),
                  "checkpoint_every": (1, 10000), "threads": (1, 8)}
        for name, (low, high) in ranges.items():
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
                raise ValueError(f"invalid training setting {name}")
        if not np.isfinite(self.max_wall_s) or not 0 < self.max_wall_s <= 3600:
            raise ValueError("max_wall_s must be in (0,3600]")

    def digest(self):
        return hashlib.sha256(canonical_json(asdict(self)).encode()).hexdigest()


def config_from_dict(value):
    value = dict(value)
    value["scene"] = SceneConfig(**value.get("scene", {}))
    value["ppo"] = PPOConfig(**value.get("ppo", {}))
    return TrainConfig(**value)


class Trainer:
    def __init__(self, config=None):
        self.config = config or TrainConfig()
        self.generator = configure_cpu(self.config.seed, self.config.threads)
        self.policy = ActorCritic(self.config.hidden)
        self.algorithm = PPO(self.policy, self.config.ppo)
        self.env = LoaderEnv(self.config.num_envs, seed=self.config.seed, scene=self.config.scene)
        self.source = source_identity()
        self.started_at_utc = datetime.now(timezone.utc).isoformat()
        self.counters = {"rollouts": 0, "environment_steps": 0, "agent_decisions": 0,
                         "optimiser_updates": 0, "completed_episodes": 0, "successes": 0,
                         "imagined_transitions": 0, "nominal_simulated_s": 0.0}
        self.curve, self.episodes = [], []
        self.checkpoint_records = []
        self.training_wall_s = 0.0
        self.stop_requested = False

    def iterate(self):
        started = time.perf_counter()
        rollout = collect(self.env, self.policy, self.config.rollout_steps, self.generator)
        collection_s = time.perf_counter()-started
        started = time.perf_counter()
        stats = self.algorithm.update(rollout, self.generator)
        update_s = time.perf_counter()-started
        steps = self.config.num_envs*self.config.rollout_steps
        self.counters["rollouts"] += 1
        self.counters["environment_steps"] += steps
        self.counters["agent_decisions"] += steps
        self.counters["optimiser_updates"] += stats["minibatch_updates"]
        self.counters["completed_episodes"] += len(rollout.episodes)
        self.counters["successes"] += sum(e["reason"] == "success" for e in rollout.episodes)
        self.counters["nominal_simulated_s"] += steps*self.env.loader.decision_s
        self.episodes.extend(rollout.episodes)
        self.curve.append({"rollout": self.counters["rollouts"], "environment_steps": self.counters["environment_steps"],
                           "completed_episodes": self.counters["completed_episodes"],
                           "mean_step_reward": float(rollout.rewards.mean()),
                           "collection_s": collection_s, "update_s": update_s, **stats})
        return self.curve[-1]

    def state(self):
        return {"configuration": asdict(self.config), "configuration_sha256": self.config.digest(),
                "source": self.source, "started_at_utc": self.started_at_utc,
                "actor_critic": self.policy.state_dict(), "optimiser": self.algorithm.optimiser.state_dict(),
                "environment": checkpoints.environment_state(self.env),
                "rng": checkpoints.random_state(self.generator), "counters": self.counters.copy(),
                "learning_curve": self.curve, "episodes": self.episodes,
                "checkpoint_records": list(self.checkpoint_records),
                "training_wall_s": self.training_wall_s,
                "software": {"torch": str(torch.__version__), "numpy": np.__version__}}

    @classmethod
    def resume(cls, path):
        state = checkpoints.load(path)
        config = config_from_dict(state["configuration"])
        if config.digest() != state["configuration_sha256"]:
            raise ValueError("checkpoint configuration hash differs")
        trainer = cls(config)
        if trainer.source["package_sha256"] != state["source"]["package_sha256"]:
            raise ValueError("resume requires the same training source package")
        if str(torch.__version__) != state["software"]["torch"] or np.__version__ != state["software"]["numpy"]:
            raise ValueError("resume requires the recorded numerical library versions")
        trainer.policy.load_state_dict(state["actor_critic"], strict=True)
        trainer.algorithm.optimiser.load_state_dict(state["optimiser"])
        checkpoints.restore_environment(trainer.env, state["environment"])
        checkpoints.restore_random_state(trainer.generator, state["rng"])
        trainer.source, trainer.started_at_utc = state["source"], state["started_at_utc"]
        trainer.counters, trainer.curve, trainer.episodes = state["counters"], state["learning_curve"], state["episodes"]
        trainer.training_wall_s = state["training_wall_s"]
        trainer.checkpoint_records = state.get("checkpoint_records", [])
        current = {"path": str(Path(path).resolve()), "sha256": checkpoints.sha256(path),
                   "rollout": trainer.counters["rollouts"]}
        trainer.checkpoint_records = list({x["path"]: x for x in [*trainer.checkpoint_records, current]}.values())
        return trainer

    def run(self, output, *, until_update=None):
        """Stop on a transaction boundary; wall budget is cumulative on resume."""
        output = Path(output)
        output.mkdir(parents=True, exist_ok=True)
        limit = self.config.updates if until_update is None else min(until_update, self.config.updates)
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < self.counters["rollouts"]:
            raise ValueError("update limit cannot precede the resumed position")
        started = time.perf_counter()
        previous_wall = self.training_wall_s

        def checkpoint(final=False):
            suffix = "-final" if final else ""
            path = output/f"checkpoint-{self.counters['rollouts']:06d}{suffix}.pt"
            if not path.exists():
                digest = checkpoints.save(path, self.state())
            else:
                old = checkpoints.load(path)
                if (old["configuration_sha256"] != self.config.digest() or old["counters"] != self.counters
                        or old["started_at_utc"] != self.started_at_utc):
                    raise FileExistsError("checkpoint path belongs to another run")
                digest = checkpoints.sha256(path)
            self.checkpoint_records.append({"path": str(path.resolve()), "sha256": digest,
                                            "rollout": self.counters["rollouts"]})
            self.checkpoint_records = list({x["path"]: x for x in self.checkpoint_records}.values())

        checkpoint()
        stop_reason = "update_limit"
        while self.counters["rollouts"] < limit:
            self.training_wall_s = previous_wall+time.perf_counter()-started
            if self.stop_requested:
                stop_reason = "requested_stop"
                break
            if self.training_wall_s >= self.config.max_wall_s:
                stop_reason = "wall_budget"
                break
            self.iterate()
            self.training_wall_s = previous_wall+time.perf_counter()-started
            if self.counters["rollouts"] % self.config.checkpoint_every == 0:
                checkpoint()
        self.training_wall_s = previous_wall+time.perf_counter()-started
        checkpoint(final=True)
        report = {"schema_version": "1.0", "source_mode": "recorded_synthetic",
                  "configuration": asdict(self.config), "configuration_sha256": self.config.digest(),
                  "source": self.source, "started_at_utc": self.started_at_utc,
                  "network": self.policy.description(), "counters": self.counters,
                  "training_wall_s": self.training_wall_s, "stop_reason": stop_reason,
                  "checkpoint_overhead_note": "Budget checked between complete rollout/update transactions; initial/final saves add overhead.",
                  "checkpoints": self.checkpoint_records,
                  "learning_curve": self.curve, "episodes": self.episodes}
        (output/"run.json").write_text(json.dumps(report, indent=2, allow_nan=False)+"\n")
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preset", choices=("quick", "full"), default="quick")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--resume", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--until-update", type=int)
    args = parser.parse_args()
    if args.resume and args.config:
        parser.error("resume uses its recorded configuration")
    if args.resume:
        trainer = Trainer.resume(args.resume)
    else:
        if args.output.exists():
            parser.error("choose a new output directory for a fresh run")
        config = config_from_dict(json.loads(args.config.read_text())) if args.config else (
            TrainConfig() if args.preset == "quick" else TrainConfig(num_envs=64, rollout_steps=64, updates=200, max_wall_s=120))
        trainer = Trainer(config)
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: setattr(trainer, "stop_requested", True))
    report = trainer.run(args.output, until_update=args.until_update)
    print(json.dumps({"output": str(args.output), "stop_reason": report["stop_reason"], **report["counters"],
                      "training_wall_s": report["training_wall_s"]}))


if __name__ == "__main__":
    main()
