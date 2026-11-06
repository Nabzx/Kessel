"""Units, coordinates and bounded controls from ADR-0033."""

from dataclasses import asdict, dataclass
import hashlib
import json
import math

import numpy as np

SCHEMA_VERSION = "1.0"
ACTION_NAMES = ("acceleration", "articulation_rate", "boom_rate", "bucket_rate")


@dataclass(frozen=True)
class LoaderConfig:
    length_m: float = 7.1
    width_m: float = 1.5
    height_m: float = 1.9
    payload_kg: float = 3500.0
    decision_s: float = 0.1
    substeps: int = 5
    forward_m_s: float = 2.0
    reverse_m_s: float = 1.5
    acceleration_m_s2: float = 1.5
    articulation_rad: float = 0.6
    articulation_rate_rad_s: float = 0.35
    boom_min_rad: float = -0.1
    boom_max_rad: float = 1.1
    boom_rate_rad_s: float = 0.25
    bucket_min_rad: float = -0.7
    bucket_max_rad: float = 1.0
    bucket_rate_rad_s: float = 0.5

    def __post_init__(self):
        for name, value in asdict(self).items():
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
            if not name.endswith(("min_rad", "max_rad")) and value <= 0:
                raise ValueError(f"{name} must be positive")
        if isinstance(self.substeps, bool) or not isinstance(self.substeps, int):
            raise ValueError("substeps must be a positive integer")
        if self.boom_min_rad >= self.boom_max_rad:
            raise ValueError("boom range must be increasing")
        if self.bucket_min_rad >= self.bucket_max_rad:
            raise ValueError("bucket range must be increasing")

    @property
    def physical_step_s(self):
        return self.decision_s / self.substeps

    def digest(self):
        return hashlib.sha256(canonical_json(asdict(self)).encode()).hexdigest()


def canonical_json(value):
    """Reject non-finite JSON and hash configuration independently of key order."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def validate_actions(actions, num_envs):
    """Return float64 commands, rejecting shape changes and invalid controls."""
    if isinstance(num_envs, bool) or not isinstance(num_envs, int) or num_envs <= 0:
        raise ValueError("num_envs must be a positive integer")
    values = np.asarray(actions, dtype=np.float64)
    if values.shape != (num_envs, len(ACTION_NAMES)):
        raise ValueError(f"actions must have shape ({num_envs}, 4)")
    if not np.isfinite(values).all() or (np.abs(values) > 1).any():
        raise ValueError("actions must be finite and within [-1, 1]")
    return values


def physical_to_three(points):
    """Map (..., 3) physical vectors to Three.js without changing handedness."""
    points = np.asarray(points, dtype=np.float64)
    if points.ndim == 0 or points.shape[-1] != 3 or not np.isfinite(points).all():
        raise ValueError("points must be finite (..., 3) vectors")
    return np.stack((points[..., 0], points[..., 2], -points[..., 1]), axis=-1)
