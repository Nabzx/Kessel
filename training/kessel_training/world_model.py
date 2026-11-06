"""Bootstrapped residual dynamics, separate from the reference simulator."""

import copy
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from . import checkpoints
from .evaluate import source_identity
from .policy import configure_cpu
from .wm_data import Normaliser
from .wm_state import EVENT_NAMES, INDEX, PILE_END, STATE_SIZE, STATE_VERSION, TARGET_FLOORS, decode, delta_target


@dataclass(frozen=True)
class ModelConfig:
    members: int = 3
    hidden: int = 128
    epochs: int = 30
    batch_size: int = 256
    learning_rate: float = 0.001
    seeds: tuple = (101, 211, 307)

    def __post_init__(self):
        for value in (self.members, self.hidden, self.epochs, self.batch_size):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError("model dimensions and iteration counts must be positive integers")
        if self.members > 5 or self.hidden > 256 or self.epochs > 200 or self.batch_size > 4096:
            raise ValueError("model configuration exceeds prototype bounds")
        if len(self.seeds) != self.members or len(set(self.seeds)) != len(self.seeds):
            raise ValueError("independent member seeds are required")
        if not np.isfinite(self.learning_rate) or not 0 < self.learning_rate <= 0.01:
            raise ValueError("invalid model learning rate")


class DynamicsMLP(nn.Module):
    def __init__(self, hidden=128):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(STATE_SIZE+4, hidden), nn.SiLU(),
            nn.Linear(hidden, hidden), nn.SiLU(), nn.Linear(hidden, PILE_END+1+len(EVENT_NAMES)))
        nn.init.normal_(self.net[-1].weight, mean=0, std=0.01)
        nn.init.zeros_(self.net[-1].bias)

    def forward(self, x):
        y = self.net(x)
        return y[:, :PILE_END+1], y[:, PILE_END+1:]


class DynamicsEnsemble(nn.Module):
    def __init__(self, config, input_normaliser, target_normaliser):
        super().__init__()
        self.config = config
        self.models = nn.ModuleList()
        for seed in config.seeds:
            configure_cpu(seed)
            self.models.append(DynamicsMLP(config.hidden))
        for prefix, normal in (("input", input_normaliser), ("target", target_normaliser)):
            self.register_buffer(prefix+"_mean", torch.as_tensor(normal.mean, dtype=torch.float64))
            self.register_buffer(prefix+"_scale", torch.as_tensor(normal.scale, dtype=torch.float64))
            self.register_buffer(prefix+"_constant", torch.as_tensor(normal.constant))

    def features(self, states, actions):
        x = torch.as_tensor(np.column_stack((states, actions)), dtype=torch.float64)
        if x.ndim != 2 or x.shape[1] != STATE_SIZE+4 or not torch.isfinite(x).all():
            raise ValueError("model inputs must be finite state/action rows")
        z = (x-self.input_mean)/self.input_scale
        return z.clamp(-10, 10).float(), z.abs().amax(dim=1)

    @torch.no_grad()
    def predict(self, states, actions):
        x, envelope = self.features(states, actions)
        normal, logits = zip(*(model(x) for model in self.models))
        normal = torch.stack(normal).double()
        changes = normal*self.target_scale+self.target_mean
        mean = changes.mean(dim=0).numpy()
        disagreement = torch.sqrt(normal.var(dim=0, unbiased=False).mean(dim=-1)).numpy()
        next_state = decode(np.asarray(states), mean)
        return {"next_state": next_state, "reward": mean[:, -1],
                "events": torch.stack(logits).sigmoid().mean(dim=0).numpy(),
                "disagreement": disagreement, "input_envelope": envelope.numpy(),
                "member_changes": changes.numpy(), "normalised_changes": normal.numpy()}


def fit(train, validation, train_manifest, config=None):
    config = config or ModelConfig()
    started = time.perf_counter()
    inputs = np.column_stack((train["state"], train["action"]))
    target = delta_target(train["state"], train["next_state"], train["reward"])
    xnormal, ynormal = Normaliser.fit(inputs), Normaliser.fit(target, TARGET_FLOORS)
    ensemble = DynamicsEnsemble(config, xnormal, ynormal)
    x = torch.as_tensor(xnormal.transform(inputs), dtype=torch.float32).clamp(-10, 10)
    y = torch.as_tensor(ynormal.transform(target), dtype=torch.float32)
    labels = torch.as_tensor(train["events"], dtype=torch.float32)
    vx = torch.as_tensor(xnormal.transform(np.column_stack((validation["state"], validation["action"]))), dtype=torch.float32).clamp(-10, 10)
    vy = torch.as_tensor(ynormal.transform(delta_target(validation["state"], validation["next_state"], validation["reward"])), dtype=torch.float32)
    vl = torch.as_tensor(validation["events"], dtype=torch.float32)
    positives = labels.sum(dim=0)
    class_weights = ((len(labels)-positives)/positives.clamp_min(1)).clamp(1, 50)
    optimisers = [torch.optim.Adam(m.parameters(), lr=config.learning_rate) for m in ensemble.models]
    bootstraps, identities = [], []
    for seed in config.seeds:
        rng = np.random.default_rng(seed)
        chosen = rng.integers(0, len(train_manifest["episodes"]), size=len(train_manifest["episodes"]))
        indices = np.concatenate([np.arange(train_manifest["episodes"][i]["start"], train_manifest["episodes"][i]["stop"]) for i in chosen])
        bootstraps.append((indices, rng))
        identities.append({"seed": seed, "episode_draws": chosen.tolist(), "indices_sha256": hashlib.sha256(indices.tobytes()).hexdigest(), "rows": len(indices)})

    @torch.no_grad()
    def validation_loss():
        values = [m(vx) for m in ensemble.models]
        prediction = torch.stack([p for p, _ in values]).mean(0)
        event_prob = torch.stack([l.sigmoid() for _, l in values]).mean(0).clamp(1e-6, 1-1e-6)
        return {"normalised_state_mse": float(F.mse_loss(prediction[:, :-1], vy[:, :-1])),
                "normalised_reward_mse": float(F.mse_loss(prediction[:, -1], vy[:, -1])),
                "event_bce": float(F.binary_cross_entropy(event_prob, vl))}

    initial = validation_loss();history = [{"epoch": 0, "train_loss": None, "current_validation": initial}]
    best_loss = float("inf");best_state = None;best_epoch = 0;updates = 0
    for epoch in range(1, config.epochs+1):
        losses = []
        for model, optimiser, (indices, rng) in zip(ensemble.models, optimisers, bootstraps):
            order = indices[rng.permutation(len(indices))]
            for start in range(0, len(order), config.batch_size):
                batch = order[start:start+config.batch_size]
                prediction, logits = model(x[batch])
                loss = (F.mse_loss(prediction[:, :-1], y[batch, :-1])
                        + 0.2*F.mse_loss(prediction[:, -1], y[batch, -1])
                        + 0.1*F.binary_cross_entropy_with_logits(logits, labels[batch], pos_weight=class_weights))
                if not torch.isfinite(loss):
                    raise FloatingPointError("non-finite dynamics loss")
                optimiser.zero_grad(set_to_none=True);loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0, error_if_nonfinite=True)
                optimiser.step();losses.append(float(loss.detach()));updates += 1
        current = validation_loss()
        score = current["normalised_state_mse"]+0.2*current["normalised_reward_mse"]+0.1*current["event_bce"]
        if not np.isfinite(score):
            raise FloatingPointError("non-finite dynamics validation")
        if score < best_loss:
            best_loss = score;best_state = copy.deepcopy(ensemble.state_dict());best_epoch = epoch
        history.append({"epoch": epoch, "train_loss": float(np.mean(losses)), "current_validation": current,
                        "current_validation_score": score, "best_validation_score_so_far": best_loss})
    ensemble.load_state_dict(best_state)
    return ensemble, {"source": source_identity(), "configuration": asdict(config), "state_version": STATE_VERSION,
        "normalisers_fitted_on": "training_only", "training_dataset_sha256": train_manifest["logical_sha256"],
        "normalisers": {"input_mean": xnormal.mean.tolist(), "input_scale": xnormal.scale.tolist(),
                        "input_constant": xnormal.constant.tolist(), "target_mean": ynormal.mean.tolist(),
                        "target_scale": ynormal.scale.tolist(), "target_constant": ynormal.constant.tolist()},
        "class_weights": class_weights.tolist(), "episode_bootstraps": identities,
        "history": history, "selected_epoch": best_epoch, "selection": "lowest raw validation score, first tie",
        "optimiser_updates": updates, "training_wall_s": time.perf_counter()-started,
        "parameters": sum(p.numel() for p in ensemble.parameters())}


def save_model(path, model, report):
    return checkpoints.save(path, {"artefact_kind": "dynamics-ensemble", "model_version": STATE_VERSION,
        "configuration": asdict(model.config), "weights": model.state_dict(), "training": report})


def load_model(path):
    state = checkpoints.load(path)
    return model_from_state(state), {"model_sha256": checkpoints.sha256(path), "training": state["training"]}


def model_from_state(state):
    if state.get("model_version") != STATE_VERSION or state.get("artefact_kind") != "dynamics-ensemble":
        raise ValueError("unsupported dynamics model")
    config = ModelConfig(**state["configuration"])
    weights = state["weights"]
    nx = Normaliser(weights["input_mean"].numpy(), weights["input_scale"].numpy(), weights["input_constant"].numpy())
    ny = Normaliser(weights["target_mean"].numpy(), weights["target_scale"].numpy(), weights["target_constant"].numpy())
    model = DynamicsEnsemble(config, nx, ny);model.load_state_dict(weights, strict=True);model.eval()
    if not all(torch.isfinite(p).all() for p in model.parameters()):
        raise ValueError("non-finite saved dynamics weights")
    return model
