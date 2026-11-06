"""Objective subtask gates and explicitly prepared synthetic reset conditions."""

from dataclasses import asdict, replace
import hashlib

import numpy as np

from .contracts import canonical_json
from .environment import LoaderEnv, SceneConfig
from .kinematics import components

STAGES = ("fill", "retract", "carry", "complete")
RANDOMISATION = {
    "pile_front_m": [7.5, 8.5], "pile_lateral_offset_m": [-0.25, 0.25],
    "pile_mass_kg": [9000, 14000], "density_kg_m3": [1600, 2100],
    "friction_multiplier": [0.7, 1.2], "resistance_multiplier": [0.7, 1.3],
    "grade_offset_rad": [-0.06, 0.06], "half_width_multiplier": [0.9, 1.1],
    "sensor_noise_scale": 1.0, "frame_dropout": 0.1, "cell_occlusion": 0.1,
    "load_bias_fraction": [-0.05, 0.05],
}


class TrainingEnv:
    def __init__(self, num_envs, *, seed, scene, curriculum=True, shaping=True, gamma=0.995):
        self.curriculum = curriculum
        self.shaping = shaping
        self.gamma = gamma
        self.original_scene = scene
        self.stage_index = 0 if curriculum else 3
        self.history = []
        self.transitions = []
        self.base = LoaderEnv(num_envs, seed=seed, scene=self._scene())
        self.initial_rear_x = np.zeros(num_envs)
        self._prepare(np.ones(num_envs, dtype=bool))

    def __getattr__(self, name):
        return getattr(self.base, name)

    @property
    def stage(self):
        return STAGES[self.stage_index]

    def _scene(self):
        horizon = (200, 200, 400, 600)[self.stage_index]
        return replace(self.original_scene, max_steps=min(self.original_scene.max_steps, horizon))

    def _prepare(self, mask):
        b = self.base
        if self.stage != "complete":
            for i in np.flatnonzero(mask):
                if self.stage in ("fill", "retract"):
                    b.pose[i, 0] = b.pile.origin[i, 0]-3.8
                    b.joints[i] = (0, -0.1, -0.3)
                else:
                    b.pose[i, 0] = 2.0
                    b.joints[i] = (0, 0.35, 0.9)
                initial_load = {"fill": 0.0, "retract": 1500.0, "carry": 2200.0}[self.stage]
                if initial_load:
                    b.pile.height[i] *= (b.pile.mass()[i]-initial_load)/b.pile.mass()[i]
                    b.payload[i] = initial_load
                    b.peak_load[i] = initial_load
                b.initial_pose[i] = b.pose[i]
                b.initial_pile_hashes[i] = hashlib.sha256(b.pile.height[i].astype("<f8").tobytes()).hexdigest()
            b._assert_finite()
            b._update_observations(mask, reset=True)
        self.initial_rear_x[mask] = b.pose[mask, 0]

    def reset(self, *, seed=None, mask=None):
        selected = np.ones(self.num_envs, dtype=bool) if mask is None else np.asarray(mask)
        self.base.reset(seed=seed, mask=selected)
        self._prepare(selected)
        return self.observe(), self.diagnostics()

    def observe(self):
        return self.base.observe()

    def potential(self):
        b = self.base
        mouth = components(b.pose, b.joints)["mouth"]
        receiver_distance = np.linalg.norm(mouth-b.receiver, axis=1)
        if self.stage == "fill":
            return np.clip(b.payload/1000, 0, 1.5)
        if self.stage == "retract":
            return (np.clip((self.initial_rear_x-b.pose[:, 0])/1.0, 0, 1)
                    + np.clip(b.joints[:, 1]/0.2, 0, 1)*0.4)
        if self.stage == "carry":
            return 1-np.clip(receiver_distance/14, 0, 1)
        pile_target = b.pile.origin+np.array([1.0, 2.0])
        approach = 1-np.clip(np.linalg.norm(mouth-pile_target, axis=1)/10, 0, 1)
        carrying = b.payload >= 1000
        return np.where(carrying, 0.8+0.6*(1-np.clip(receiver_distance/14, 0, 1)),
                        0.3*approach+0.6*np.clip(b.payload/2000, 0, 1))

    def step(self, actions):
        before = self.potential()
        observation, raw_reward, term, trunc, info = self.base.step(actions)
        b = self.base
        if self.stage == "fill":
            achieved = b.payload >= 1000
        elif self.stage == "retract":
            achieved = ((b.pose[:, 0] <= self.initial_rear_x-1) & (b.joints[:, 1] >= 0.2)
                        & (b.joints[:, 2] >= 0.4) & (b.payload >= 1200))
        elif self.stage == "carry":
            mouth = components(b.pose, b.joints)["mouth"]
            achieved = ((np.abs(mouth-b.receiver) <= np.array([1.4, 1.8])).all(axis=1)
                        & (np.abs(b.speed) < 0.2) & (b.payload >= 1800))
        else:
            achieved = b.reason == "success"
        subtask_success = achieved & ~term & (self.stage != "complete")
        b.terminated[subtask_success] = True
        b.truncated[subtask_success] = False
        b.reason[subtask_success] = "stage_success"
        term, trunc = b.terminated.copy(), b.truncated.copy()
        shaping = self.gamma*np.where(term, 0, self.potential())-before if self.shaping else np.zeros(self.num_envs)
        bonus = subtask_success.astype(float)
        info["metrics"].update(reason=b.reason.copy(), stage=np.full(self.num_envs, self.stage),
                               stage_success=subtask_success | (b.reason == "success"), full_success=(b.reason == "success"))
        info["training_reward"] = {"version": "potential-v1", "stage": self.stage,
            "raw_delivery_reward": raw_reward.copy(), "potential_difference": shaping,
            "subtask_bonus": bonus, "gamma": self.gamma}
        return observation, raw_reward+shaping+bonus, term, trunc, info

    def consider_advancement(self, episodes, rollout):
        if not self.curriculum or self.stage == "complete":
            return None
        self.history.extend(bool(e.get("stage_success", False)) for e in episodes if e.get("stage") == self.stage)
        self.history = self.history[-32:]
        if len(self.history) < 32 or sum(self.history)/32 < 0.7:
            return None
        old = self.stage
        self.stage_index += 1
        event = {"rollout": rollout, "from": old, "to": self.stage,
                 "window_episodes": 32, "successes": sum(self.history),
                 "discarded_partial_slots": int((~(self.terminated | self.truncated)).sum()),
                 "reward_version": "potential-v1" if self.shaping else "delivery-v1+subtask"}
        self.transitions.append(event)
        self.history = []
        self.base.scene = self._scene()
        self.reset()
        return event

    def diagnostics(self):
        info = self.base.diagnostics()
        info["training_stage"] = self.stage
        return info

    def checkpoint_state(self):
        from .checkpoints import environment_state
        return {"base": environment_state(self.base), "initial_rear_x": self.initial_rear_x.tolist(),
                "stage_index": self.stage_index, "history": self.history, "transitions": self.transitions,
                "original_scene": asdict(self.original_scene), "curriculum": self.curriculum,
                "shaping": self.shaping, "gamma": self.gamma}

    def restore_checkpoint_state(self, state):
        from .checkpoints import restore_environment
        if (state["curriculum"], state["shaping"], state["gamma"]) != (self.curriculum, self.shaping, self.gamma):
            raise ValueError("checkpoint curriculum settings differ")
        if canonical_json(state["original_scene"]) != canonical_json(asdict(self.original_scene)):
            raise ValueError("checkpoint randomisation settings differ")
        self.stage_index = state["stage_index"]
        self.base.scene = self._scene()
        restore_environment(self.base, state["base"])
        self.initial_rear_x = np.asarray(state["initial_rear_x"], dtype=float)
        self.history, self.transitions = state["history"], state["transitions"]
