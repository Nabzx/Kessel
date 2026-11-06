"""Versioned, unit-labelled incremental rewards. No pickup/carried credit."""

from dataclasses import asdict, dataclass
import hashlib
import math

import numpy as np

from .contracts import canonical_json

UNITS = {"delivered_kg": "kg", "spilled_kg": "kg", "elapsed_s": "s",
         "effort_proxy_j": "J_proxy", "collision_count": "count", "slip_s": "s"}


@dataclass(frozen=True)
class RewardConfig:
    version: str = "delivery-v1"
    mass_scale_kg: float = 3500.0
    delivery: float = 1.0
    spillage: float = 1.0
    time_per_s: float = 0.002
    effort_per_j: float = 3e-8
    collision: float = 5.0
    slip_per_s: float = 0.02

    def __post_init__(self):
        if self.version != "delivery-v1":
            raise ValueError("unknown reward version")
        for name, value in asdict(self).items():
            if name == "version":
                continue
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"invalid reward setting {name}")
        if self.mass_scale_kg <= 0:
            raise ValueError("reward mass scale must be positive")

    def digest(self):
        return hashlib.sha256(canonical_json(asdict(self)).encode()).hexdigest()


def calculate(terms, config=None):
    cfg = config or RewardConfig()
    if set(terms) != set(UNITS):
        raise ValueError("reward terms must match the versioned unit contract")
    arrays = {k: np.asarray(v, dtype=float) for k, v in terms.items()}
    shape = arrays["delivered_kg"].shape
    if len(shape) != 1 or shape[0] < 1 or any(v.shape != shape for v in arrays.values()):
        raise ValueError("reward terms must share a non-empty batch shape")
    if any(not np.isfinite(v).all() or (v < -1e-9).any() for v in arrays.values()):
        raise ValueError("reward terms must be finite non-negative increments")
    weights = {"delivered_kg": cfg.delivery/cfg.mass_scale_kg,
               "spilled_kg": -cfg.spillage/cfg.mass_scale_kg,
               "elapsed_s": -cfg.time_per_s, "effort_proxy_j": -cfg.effort_per_j,
               "collision_count": -cfg.collision, "slip_s": -cfg.slip_per_s}
    weighted = {k: v*weights[k] for k, v in arrays.items()}
    total = sum(weighted.values())
    return total, {"version": cfg.version, "config_sha256": cfg.digest(),
                   "units": UNITS.copy(), "weights": weights, "weighted": weighted}
