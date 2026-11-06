"""A bounded auxiliary critic objective. Imagined rows never enter PPO ratios."""

import copy
import time

import numpy as np
import torch
from torch.nn import functional as F

from . import checkpoints
from .imagination import imagine
from .ppo import collect
from .train import Trainer, config_from_dict
from .world_model import model_from_state


def auxiliary_value_step(policy, optimiser, features, targets, coefficient=0.1):
    if not 0 < coefficient <= 0.1:
        raise ValueError("auxiliary coefficient exceeds prototype bounds")
    if features.shape[0] != len(targets) or not len(targets) or not torch.isfinite(targets).all():
        raise ValueError("invalid auxiliary value targets")
    before = copy.deepcopy(policy.state_dict());optimiser_before = copy.deepcopy(optimiser.state_dict())
    try:
        optimiser.zero_grad(set_to_none=True)
        loss = coefficient*F.mse_loss(policy.value(features.detach()), targets.detach())
        if not torch.isfinite(loss):
            raise FloatingPointError("non-finite auxiliary critic loss")
        loss.backward()
        norm = torch.nn.utils.clip_grad_norm_(policy.critic.parameters(), 0.5, error_if_nonfinite=True)
        if any(p.grad is not None for p in policy.actor.parameters()) or policy.log_std.grad is not None:
            raise RuntimeError("imagined value loss leaked into actor gradients")
        optimiser.step()
        if not all(torch.isfinite(p).all() for p in policy.parameters()):
            raise FloatingPointError("non-finite auxiliary critic weights")
        return {"loss": float(loss.detach()), "gradient_norm_before_clip": float(norm)}
    except (ValueError, FloatingPointError, RuntimeError):
        policy.load_state_dict(before);optimiser.load_state_dict(optimiser_before)
        optimiser.zero_grad(set_to_none=True)
        raise


class ModelAssistedTrainer(Trainer):
    trainer_kind = "model-assisted-critic-v1"

    def __init__(self, config, model_payload, model_sha256, gate):
        if config.curriculum or config.shaping:
            raise ValueError("world-model comparison uses complete tasks and raw delivery rewards")
        super().__init__(config)
        self.model_payload = model_payload
        self.model = model_from_state(model_payload).requires_grad_(False)
        self.model_sha256, self.gate = model_sha256, gate
        self.auxiliary_rng = np.random.default_rng(config.seed+91000)
        self.branch_generator = torch.Generator(device="cpu").manual_seed(config.seed+12000)
        self.auxiliary_records = []
        self.last_rollout = None
        self.counters.update(auxiliary_updates=0, proposed_model_transitions=0,
                             accepted_branches=0, rejected_branches=0)

    def collect_rollout(self):
        if (self.env.seeds >= 100000).any():
            raise ValueError("held-out seeds cannot anchor model-assisted training")
        self.last_rollout = collect(self.env, self.policy, self.config.rollout_steps, self.generator, record_world_state=True)
        return self.last_rollout

    def iterate(self):
        row = super().iterate()
        if self.counters["rollouts"] % 4:
            return row
        rollout = self.last_rollout
        started = time.perf_counter()
        features = rollout.features.reshape(-1, 65)
        states = rollout.world_states.reshape(-1, rollout.world_states.shape[-1])
        size = len(states)//4
        if not size:
            return row
        ids = self.auxiliary_rng.choice(len(states), size=size, replace=False)
        targets, selected, stats = imagine(self.model, self.policy, states[ids], features[ids], self.gate,
                                          self.branch_generator, horizon=2, gamma=self.config.ppo.gamma)
        update = None
        if selected.any():
            update = auxiliary_value_step(self.policy, self.algorithm.optimiser, features[ids][selected],
                                          torch.as_tensor(targets[selected], dtype=torch.float32))
            self.counters["auxiliary_updates"] += 1
        for key in ("imagined_transitions", "proposed_model_transitions", "accepted_branches", "rejected_branches"):
            self.counters[key] += stats[key]
        record = {"rollout": self.counters["rollouts"], "model_sha256": self.model_sha256,
                  "cadence": 4, "maximum_anchor_ratio": 0.25, "maximum_horizon": 2,
                  "auxiliary_coefficient": 0.1, "model_refits": 0, "branches": stats, "critic_update": update}
        record["auxiliary_wall_s"] = time.perf_counter()-started
        self.auxiliary_records.append(record);row["model_assistance"] = record
        return row

    def state(self):
        state = super().state()
        state["auxiliary"] = {"model_payload": self.model_payload, "model_sha256": self.model_sha256,
            "gate": self.gate, "rng": self.auxiliary_rng.bit_generator.state,
            "branch_generator": self.branch_generator.get_state(), "records": self.auxiliary_records}
        return state

    @classmethod
    def resume(cls, path):
        state = checkpoints.load(path)
        if state.get("trainer_kind") != cls.trainer_kind:
            raise ValueError("not a model-assisted checkpoint")
        extra = state["auxiliary"]
        trainer = cls(config_from_dict(state["configuration"]), extra["model_payload"], extra["model_sha256"], extra["gate"])
        trainer.restore_state(state, path)
        trainer.auxiliary_rng.bit_generator.state = extra["rng"]
        trainer.branch_generator.set_state(extra["branch_generator"])
        trainer.auxiliary_records = extra["records"]
        return trainer
