"""Deterministic observation-only reference. No privileged pile access."""

from dataclasses import asdict, dataclass

import numpy as np


@dataclass(frozen=True)
class ControllerConfig:
    approach_m_s: float = 0.9
    fill_m_s: float = 0.45
    reverse_m_s: float = 0.8
    target_load_kg: float = 2450.0
    carry_boom_rad: float = 0.35
    fill_timeout_s: float = 22.0


class ReferenceController:
    def __init__(self, num_envs, config=None):
        self.config = config or ControllerConfig()
        self.phase = np.zeros(num_envs, dtype=int)
        self.fill_start = np.zeros(num_envs)

    def reset(self, mask):
        self.phase[mask] = 0
        self.fill_start[mask] = 0

    def settings(self):
        return asdict(self.config)

    def act(self, observation):
        p = observation["proprio"]
        if p.shape != (len(self.phase), 15):
            raise ValueError("controller expects the loader observation contract")
        speed, articulation, boom, curl, load = (p[:, i] for i in (4, 5, 6, 7, 8))
        elapsed = p[:, 13]
        visible_height = observation["local_height_m"] * observation["range_valid"]
        contact = visible_height.max(axis=(1, 2)) > 0.1
        entered = (self.phase == 0) & contact
        self.fill_start[entered] = elapsed[entered]
        self.phase[entered] = 1
        filled = ((load >= self.config.target_load_kg)
                  | (elapsed-self.fill_start >= self.config.fill_timeout_s))
        self.phase[(self.phase == 1) & filled] = 2
        lifted = (boom >= self.config.carry_boom_rad-0.02) & (curl >= 0.6)
        self.phase[(self.phase == 2) & lifted] = 3
        # Receiver displacement is relative to the rear axle in the observed
        # chassis frame. Derive mouth offset from the same joint geometry.
        reach = 1.8 + (1.6+1.2*np.cos(boom))*np.cos(articulation)
        mouth_error = p[:, 9]-reach
        near = (np.abs(mouth_error) < 0.5) & (np.abs(speed) < 0.08)
        self.phase[(self.phase == 3) & near] = 4
        target_speed = np.zeros(len(p))
        target_speed[self.phase == 0] = self.config.approach_m_s
        target_speed[self.phase == 1] = self.config.fill_m_s
        hauling = self.phase == 3
        target_speed[hauling] = np.clip(mouth_error[hauling]*0.65,
                                              -self.config.reverse_m_s, 0.3)
        acceleration = np.clip(1.8*(target_speed-speed)+np.sign(target_speed)*0.12, -1, 1)
        heading = np.arctan2(p[:, 2], p[:, 3])
        target_articulation = np.clip(-0.8*heading-0.15*p[:, 1], -0.2, 0.2)
        # Correct steering sign when reversing, while keeping both axles aligned.
        target_articulation = np.where(hauling, -target_articulation, target_articulation)
        steering = np.clip((target_articulation-articulation)*2, -1, 1)
        target_boom = np.where(self.phase < 2, -0.1, self.config.carry_boom_rad)
        target_curl = np.where(self.phase == 0, -0.1, 0.95)
        target_curl[self.phase == 4] = -0.7
        return np.stack((acceleration, steering, np.clip((target_boom-boom)*4, -1, 1),
                         np.clip((target_curl-curl)*4, -1, 1)), axis=1)
