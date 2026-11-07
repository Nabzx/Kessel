"""Clipped PPO with explicit final-state bootstrapping and update diagnostics."""

import copy
from dataclasses import asdict, dataclass, field
import math

import numpy as np
import torch
from torch.nn import functional as F


@dataclass(frozen=True)
class PPOConfig:
    gamma: float = 0.995
    gae_lambda: float = 0.95
    clip: float = 0.2
    value_weight: float = 0.5
    entropy_weight: float = 0.005
    learning_rate: float = 0.0003
    max_grad_norm: float = 0.5
    target_kl: float = 0.03
    epochs: int = 4
    minibatch: int = 128

    def __post_init__(self):
        for name, value in asdict(self).items():
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"invalid PPO setting {name}")
        if not 0 < self.gamma <= 1 or not 0 <= self.gae_lambda <= 1 or not 0 < self.clip < 1:
            raise ValueError("invalid discount, GAE lambda or policy clip")
        if not 0 < self.learning_rate <= 0.1 or self.max_grad_norm <= 0 or self.target_kl <= 0:
            raise ValueError("invalid optimiser or KL setting")
        for value in (self.epochs, self.minibatch):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError("epochs and minibatch must be positive integers")


def advantages(rewards, values, next_values, terminated, truncated, gamma, gae_lambda):
    """Bootstrap a truncation's final state, but stop its recursive trace."""
    if rewards.ndim != 2 or 0 in rewards.shape:
        raise ValueError("GAE expects non-empty (time,environment) arrays")
    if any(v.shape != rewards.shape for v in (values, next_values, terminated, truncated)):
        raise ValueError("GAE arrays must share their shape")
    if terminated.dtype != torch.bool or truncated.dtype != torch.bool:
        raise ValueError("episode boundaries must be boolean")
    if (terminated & truncated).any():
        raise ValueError("termination and truncation are exclusive")
    if not all(torch.isfinite(v).all() for v in (rewards, values, next_values)):
        raise FloatingPointError("non-finite GAE inputs")
    if not rewards.is_floating_point() or values.dtype != rewards.dtype or next_values.dtype != rewards.dtype:
        raise ValueError("GAE values and rewards must share a floating-point dtype")
    result = torch.zeros_like(rewards)
    carry = torch.zeros(rewards.shape[1], dtype=rewards.dtype, device=rewards.device)
    bootstrap = (~terminated).to(rewards.dtype)
    continuation = (~(terminated | truncated)).to(rewards.dtype)
    for t in reversed(range(len(rewards))):
        delta = rewards[t] + gamma*bootstrap[t]*next_values[t] - values[t]
        carry = delta + gamma*gae_lambda*continuation[t]*carry
        result[t] = carry
    return result, result+values


@dataclass
class Rollout:
    features: torch.Tensor
    latent: torch.Tensor
    log_prob: torch.Tensor
    values: torch.Tensor
    next_values: torch.Tensor
    rewards: torch.Tensor
    terminated: torch.Tensor
    truncated: torch.Tensor
    episodes: list
    reward_components: dict = field(default_factory=dict)
    world_states: np.ndarray | None = None


@torch.no_grad()
def collect(env, policy, steps, generator, *, record_world_state=False):
    if isinstance(steps, bool) or not isinstance(steps, int) or steps < 1:
        raise ValueError("rollout steps must be a positive integer")
    finished = env.terminated | env.truncated
    if finished.any():
        env.reset(mask=finished)
    columns = [[] for _ in range(8)]
    episodes = []
    reward_components = {}
    world_states = []
    for _ in range(steps):
        if record_world_state:
            from .wm_state import pack
            world_states.append(pack(env))
        features = policy.encode(env.observe())
        sample = policy.sample(features, generator=generator)
        observation, reward, terminated, truncated, info = env.step(sample["action"].numpy())
        groups = {"raw": info["reward_terms"], "weighted": info["reward_description"]["weighted"]}
        if "training_reward" in info:
            groups["training"] = {k: v for k, v in info["training_reward"].items() if isinstance(v, np.ndarray)}
        for group, components in groups.items():
            for key, values in components.items():
                name = f"{group}.{key}"
                reward_components[name] = reward_components.get(name, 0.0)+float(values.sum())
        # Capture V(final observation) before resetting any batch slot.
        next_value = policy.value(policy.encode(observation))
        row = (features, sample["latent"], sample["log_prob"], sample["value"], next_value,
               torch.as_tensor(reward, dtype=torch.float32),
               torch.as_tensor(terminated), torch.as_tensor(truncated))
        for column, value in zip(columns, row):
            column.append(value.clone())
        done = terminated | truncated
        for i in np.flatnonzero(done):
            episodes.append({k: v[i].item() for k, v in info["metrics"].items()})
        if done.any():
            env.reset(mask=done)
    return Rollout(*(torch.stack(c) for c in columns), episodes=episodes, reward_components=reward_components,
                   world_states=np.stack(world_states) if record_world_state else None)


class PPO:
    def __init__(self, policy, config=None):
        self.policy = policy
        self.config = config or PPOConfig()
        self.optimiser = torch.optim.Adam(policy.parameters(), lr=self.config.learning_rate, eps=1e-5)

    def update(self, rollout, generator):
        snapshot = copy.deepcopy(self.policy.state_dict())
        optimiser_snapshot = copy.deepcopy(self.optimiser.state_dict())
        rng_snapshot = generator.get_state().clone()
        try:
            return self._update(rollout, generator)
        except (ValueError, FloatingPointError, RuntimeError):
            self.policy.load_state_dict(snapshot)
            self.optimiser.load_state_dict(optimiser_snapshot)
            generator.set_state(rng_snapshot)
            self.optimiser.zero_grad(set_to_none=True)
            raise

    def _update(self, rollout, generator):
        cfg = self.config
        advantage, returns = advantages(rollout.rewards, rollout.values, rollout.next_values,
                                       rollout.terminated, rollout.truncated, cfg.gamma, cfg.gae_lambda)
        count = advantage.numel()
        tensors = (rollout.features, rollout.latent, rollout.log_prob, returns, advantage)
        if not all(torch.isfinite(v).all() for v in tensors):
            raise FloatingPointError("non-finite rollout")
        feature_size = self.policy.feature_size
        if rollout.features.shape != (*advantage.shape, feature_size) or rollout.latent.shape != (*advantage.shape, 4):
            raise ValueError("invalid rollout feature/action shape")
        if rollout.log_prob.shape != advantage.shape:
            raise ValueError("invalid rollout likelihood shape")
        features = rollout.features.reshape(count, feature_size).detach()
        latents = rollout.latent.reshape(count, 4).detach()
        old_log = rollout.log_prob.reshape(count).detach()
        targets = returns.reshape(count).detach()
        adv = advantage.reshape(count).detach()
        adv = (adv-adv.mean()) / (adv.std(unbiased=False)+1e-8)
        records, kl_stop, kl_at_stop = [], False, None
        for _ in range(cfg.epochs):
            permutation = torch.randperm(count, generator=generator)
            for start in range(0, count, cfg.minibatch):
                indices = permutation[start:start+cfg.minibatch]
                log_prob, value, entropy = self.policy.evaluate(features[indices], latents[indices], generator=generator)
                log_ratio = log_prob-old_log[indices]
                ratio = log_ratio.exp()
                if not torch.isfinite(ratio).all():
                    raise FloatingPointError("non-finite PPO likelihood ratio")
                approximate_kl = ((ratio-1)-log_ratio).mean()
                if approximate_kl.detach() > cfg.target_kl:
                    kl_stop = True
                    kl_at_stop = float(approximate_kl.detach())
                    break
                policy_loss = torch.maximum(-adv[indices]*ratio,
                    -adv[indices]*ratio.clamp(1-cfg.clip, 1+cfg.clip)).mean()
                value_loss = 0.5*F.mse_loss(value, targets[indices])
                entropy_estimate = entropy.mean()
                loss = policy_loss+cfg.value_weight*value_loss-cfg.entropy_weight*entropy_estimate
                if not torch.isfinite(loss):
                    raise FloatingPointError("non-finite PPO loss")
                self.optimiser.zero_grad(set_to_none=True)
                loss.backward()
                grad_norm = torch.nn.utils.clip_grad_norm_(self.policy.parameters(), cfg.max_grad_norm,
                                                           error_if_nonfinite=True)
                clipped_norm = torch.linalg.vector_norm(torch.stack([
                    torch.linalg.vector_norm(p.grad) for p in self.policy.parameters() if p.grad is not None]))
                self.optimiser.step()
                if not all(torch.isfinite(p).all() for p in self.policy.parameters()):
                    raise FloatingPointError("non-finite updated parameters")
                records.append({"samples": len(indices), "policy_loss": float(policy_loss.detach()),
                    "value_loss": float(value_loss.detach()), "entropy_mc": float(entropy_estimate.detach()),
                    "approximate_kl": float(approximate_kl.detach()),
                    "clip_fraction": float(((ratio-1).abs() > cfg.clip).float().mean().detach()),
                    "gradient_norm_before_clip": float(grad_norm),
                    "gradient_norm_after_clip": float(clipped_norm)})
            if kl_stop:
                break
        total = sum(r["samples"] for r in records)
        keys = ("policy_loss", "value_loss", "entropy_mc", "approximate_kl", "clip_fraction", "gradient_norm_before_clip", "gradient_norm_after_clip")
        return {"minibatch_updates": len(records), "samples_used": total, "kl_stopped": kl_stop, "kl_at_stop": kl_at_stop,
                **{k: sum(r[k]*r["samples"] for r in records)/max(total, 1) for k in keys},
                "minibatches": records}
