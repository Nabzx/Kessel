"""Small CPU actor/critic with an explicitly transformed action density."""

import math

import torch
from torch import nn
from torch.nn import functional as F

FEATURES = 65


def configure_cpu(seed=0, threads=1):
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2**63:
        raise ValueError("seed must be a non-negative 63-bit integer")
    if isinstance(threads, bool) or not isinstance(threads, int) or not 1 <= threads <= 8:
        raise ValueError("CPU threads must be between 1 and 8")
    torch.set_num_threads(threads)
    torch.use_deterministic_algorithms(True)
    torch.manual_seed(seed)
    return torch.Generator(device="cpu").manual_seed(seed)


def squashed_log_prob(mean, log_std, latent):
    normal = torch.distributions.Normal(mean, log_std.exp())
    jacobian = 2*(math.log(2)-latent-F.softplus(-2*latent))
    return (normal.log_prob(latent)-jacobian).sum(dim=-1)


def network(hidden, outputs, gain):
    layers = nn.Sequential(nn.Linear(FEATURES, hidden), nn.Tanh(),
                           nn.Linear(hidden, hidden), nn.Tanh(), nn.Linear(hidden, outputs))
    for module in layers:
        if isinstance(module, nn.Linear):
            nn.init.orthogonal_(module.weight, math.sqrt(2))
            nn.init.zeros_(module.bias)
    nn.init.orthogonal_(layers[-1].weight, gain)
    return layers


class ActorCritic(nn.Module):
    feature_size = FEATURES
    def __init__(self, hidden=64, initial_log_std=None):
        super().__init__()
        if isinstance(hidden, bool) or not isinstance(hidden, int) or not 8 <= hidden <= 256:
            raise ValueError("hidden width must be an integer from 8 to 256")
        self.hidden = hidden
        self.actor = network(hidden, 4, 0.01)
        self.critic = network(hidden, 1, 1.0)
        if initial_log_std is None:
            initial_log_std = [-0.5] * 4
        if (not isinstance(initial_log_std, (tuple, list)) or len(initial_log_std) != 4
                or any(isinstance(v, bool) or not isinstance(v, (int, float))
                       or not math.isfinite(v) or not -4 <= v <= 1 for v in initial_log_std)):
            raise ValueError("initial_log_std must contain four finite values in [-4,1]")
        self.log_std = nn.Parameter(torch.tensor(initial_log_std, dtype=torch.float32))
        self.register_buffer("proprio_scale", torch.tensor(
            [12, 4.2, 1, 1, 2, 0.6, 1.1, 1, 3500, 20, 6, 5, 1, 60, 1], dtype=torch.float32))
        self.register_buffer("height_scale", torch.tensor(1.5))

    def encode(self, observation):
        if set(observation) != {"proprio", "local_height_m", "range_valid"}:
            raise ValueError("policy accepts only the local observation fields")
        tensors = {k: torch.as_tensor(v, dtype=torch.float32, device="cpu")
                   for k, v in observation.items()}
        p, height, valid = (tensors[k] for k in ("proprio", "local_height_m", "range_valid"))
        if p.ndim != 2 or p.shape[1] != 15 or p.shape[0] < 1:
            raise ValueError("proprio must have shape (N,15)")
        if height.shape != (len(p), 5, 5) or valid.shape != height.shape:
            raise ValueError("local crop and mask must have shape (N,5,5)")
        if not all(torch.isfinite(v).all() for v in tensors.values()):
            raise ValueError("policy observations must be finite")
        if not ((valid == 0) | (valid == 1)).all():
            raise ValueError("range validity must be binary")
        return torch.cat((p/self.proprio_scale, height.flatten(1)/self.height_scale,
                          valid.flatten(1)), dim=1).clamp(-5, 5)

    def distribution(self, features):
        if features.ndim != 2 or features.shape[1] != self.feature_size or not torch.isfinite(features).all():
            raise ValueError(f"features must be finite (N,{self.feature_size}) values")
        return self.actor(features), self.log_std.clamp(-4, 1).expand(len(features), -1)

    def value(self, features):
        return self.critic(features).squeeze(-1)

    def sample(self, features, *, generator=None, deterministic=False):
        mean, log_std = self.distribution(features)
        if deterministic:
            latent = mean
        else:
            latent = mean+log_std.exp()*torch.randn(mean.shape, generator=generator, device="cpu")
        return {"action": latent.tanh(), "latent": latent,
                "log_prob": squashed_log_prob(mean, log_std, latent),
                "value": self.value(features)}

    def evaluate(self, features, latent, *, generator=None):
        mean, log_std = self.distribution(features)
        if latent.shape != mean.shape or not torch.isfinite(latent).all():
            raise ValueError("action latents must be finite (N,4) values")
        fresh = mean+log_std.exp()*torch.randn(mean.shape, generator=generator, device="cpu")
        return (squashed_log_prob(mean, log_std, latent), self.value(features),
                -squashed_log_prob(mean, log_std, fresh))

    def description(self):
        return {"features": self.feature_size, "hidden": [self.hidden, self.hidden],
                "actions": 4, "parameters": sum(p.numel() for p in self.parameters()),
                "actor_parameters": sum(p.numel() for p in self.actor.parameters())+4,
                "critic_parameters": sum(p.numel() for p in self.critic.parameters()),
                "normalisation": "fixed_physical_scales_v1", "device": "cpu",
                "torch_threads": torch.get_num_threads()}
