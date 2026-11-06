"""Explicit known-physics filter; raw neural accuracy remains separate."""

from dataclasses import asdict, dataclass
import hashlib

import numpy as np

from .contracts import canonical_json
from .wm_state import INDEX, PILE_START, PILE_END


@dataclass(frozen=True)
class FilterConfig:
    max_joint_correction_rad: float = 0.01
    max_cell_height_correction_m: float = 0.002
    max_material_correction_kg: float = 25.0
    max_pile_correction_kg: float = 25.0
    max_clock_correction_s: float = 0.02
    max_effort_correction_j: float = 100.0
    max_reward_correction: float = 0.05
    max_speed_correction_m_s: float = 0.01
    max_slip_correction: float = 0.02
    max_slip_time_correction_s: float = 0.02

    def __post_init__(self):
        if any(not np.isfinite(v) or v <= 0 for v in asdict(self).values()):
            raise ValueError("filter limits must be finite and positive")

    def digest(self):
        return hashlib.sha256(canonical_json(asdict(self)).encode()).hexdigest()


def mouth(state):
    yaw = state[:, 2];front = yaw+state[:, 4]
    return state[:, :2]+1.8*np.stack((np.cos(yaw), np.sin(yaw)), axis=1)+(1.6+1.2*np.cos(state[:, 5]))[:, None]*np.stack((np.cos(front), np.sin(front)), axis=1)


def filter_prediction(current, prediction, config=None):
    cfg = config or FilterConfig();raw = prediction["next_state"];out = raw.copy()
    for i, low, high in ((3, -1.5, 2), (4, -0.6, 0.6), (5, -0.1, 1.1), (6, -0.7, 1.0), (14, 0, 1)):
        out[:, i] = np.clip(out[:, i], low, high)
    dt = current[:, INDEX["decision_s"]]
    out[:, 10] = np.clip(out[:, 10], current[:, 10], current[:, 10]+dt)
    out[:, 11] = np.clip(out[:, 11], 0, current[:, 11]+dt)
    out[:, 12:14] = np.maximum(out[:, 12:14], current[:, 12:14])
    old_mouth, new_mouth = mouth(current), mouth(out)
    gx, gy = np.meshgrid((np.arange(8)+0.5)*0.5, (np.arange(8)+0.5)*0.5, indexing="ij")
    centres = np.stack((gx.ravel(), gy.ravel()), axis=1)[None, ...]+current[:, None, [INDEX["pile_origin_x_m"], INDEX["pile_origin_y_m"]]]
    masks = []
    for state, point in ((current, old_mouth), (out, new_mouth)):
        difference = centres-point[:, None, :];yaw = state[:, 2]+state[:, 4]
        along = difference[..., 0]*np.cos(yaw[:, None])+difference[..., 1]*np.sin(yaw[:, None])
        across = -difference[..., 0]*np.sin(yaw[:, None])+difference[..., 1]*np.cos(yaw[:, None])
        masks.append((np.abs(along) <= 0.75) & (np.abs(across) <= 0.9))
    floor = np.minimum(0.35+2*np.sin(current[:, 5]), 0.35+2*np.sin(out[:, 5]))
    available = np.minimum(np.maximum(current[:, PILE_START:PILE_END]-floor[:, None], 0), 0.7)
    removal = np.minimum(np.maximum(current[:, PILE_START:PILE_END]-raw[:, PILE_START:PILE_END], 0), available)*(masks[0] | masks[1])
    mass_per_height = 0.25*current[:, INDEX["density_kg_m3"]]
    gain = removal.sum(axis=1)*mass_per_height
    room = np.minimum(np.maximum(3500-current[:, 7], 0), 1200*dt)
    ratio = np.minimum(1, room/np.maximum(gain, 1e-12))
    removal *= ratio[:, None];gain *= ratio
    out[:, PILE_START:PILE_END] = current[:, PILE_START:PILE_END]-removal
    delivery = np.maximum(raw[:, 8]-current[:, 8], 0)
    spill = np.maximum(raw[:, 9]-current[:, 9], 0)
    receiver = current[:, [INDEX["receiver_x_m"], INDEX["receiver_y_m"]]]
    receiver_half = current[:, [INDEX["receiver_half_x_m"], INDEX["receiver_half_y_m"]]]
    delivery *= (np.abs(new_mouth-receiver) <= receiver_half).all(axis=1)
    tipping = np.clip((-np.minimum(current[:, 6], out[:, 6])-0.2)/0.5, 0, 1)
    budget = (current[:, 7]+gain)*np.minimum(1, 3*dt*tipping)
    ratio = np.minimum(1, budget/np.maximum(delivery+spill, 1e-12))
    delivery *= ratio;spill *= ratio
    out[:, 7] = current[:, 7]+gain-delivery-spill
    out[:, 8] = current[:, 8]+delivery;out[:, 9] = current[:, 9]+spill
    credit_limit = (delivery-spill)/3500-0.002*(out[:, 10]-current[:, 10])-3e-8*(out[:, 12]-current[:, 12])-0.02*(out[:, 13]-current[:, 13])
    reward = np.minimum(prediction["reward"], credit_limit)
    correction = {"joint_rad": np.max(np.abs(out[:, 4:7]-raw[:, 4:7]), axis=1),
        "cell_height_m": np.max(np.abs(out[:, PILE_START:PILE_END]-raw[:, PILE_START:PILE_END]), axis=1),
        "material_kg": np.max(np.abs(out[:, 7:10]-raw[:, 7:10]), axis=1),
        "pile_kg": np.sum(np.abs(out[:, PILE_START:PILE_END]-raw[:, PILE_START:PILE_END]), axis=1)*mass_per_height,
        "clock_s": np.max(np.abs(out[:, 10:12]-raw[:, 10:12]), axis=1),
        "effort_j": np.abs(out[:, 12]-raw[:, 12]), "reward": np.abs(reward-prediction["reward"]),
        "speed_m_s": np.abs(out[:, 3]-raw[:, 3]), "slip_ratio": np.abs(out[:, 14]-raw[:, 14]),
        "slip_s": np.abs(out[:, 13]-raw[:, 13])}
    limits = (cfg.max_joint_correction_rad, cfg.max_cell_height_correction_m, cfg.max_material_correction_kg,
              cfg.max_pile_correction_kg, cfg.max_clock_correction_s, cfg.max_effort_correction_j, cfg.max_reward_correction, cfg.max_speed_correction_m_s, cfg.max_slip_correction, cfg.max_slip_time_correction_s)
    too_large = np.logical_or.reduce([value > limit for value, limit in zip(correction.values(), limits)])
    result = {**prediction, "next_state": out, "reward": reward,
              "raw_next_state": raw, "raw_reward": prediction["reward"],
              "filter_correction": correction, "filter_rejected": too_large,
              "predictor_kind": "neural_with_explicit_bounded_filter"}
    return result


class ConstrainedModel:
    def __init__(self, model, config=None):
        self.model = model;self.config = config or FilterConfig()

    def predict(self, states, actions):
        return filter_prediction(states, self.model.predict(states, actions), self.config)
