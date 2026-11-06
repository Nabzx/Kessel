"""Versioned privileged dynamics state, separate from the 65 policy features."""

import numpy as np

from .contracts import LoaderConfig

DYNAMIC_NAMES = ("x_m", "y_m", "yaw_rad", "speed_m_s", "articulation_rad", "boom_rad", "bucket_rad",
                 "carried_kg", "delivered_kg", "spilled_kg", "elapsed_s", "stuck_time_s",
                 "effort_proxy_j", "slip_s", "slip_ratio")
PILE_START = len(DYNAMIC_NAMES)
PILE_END = PILE_START+64
CONTEXT_NAMES = ("pile_origin_x_m", "pile_origin_y_m", "density_kg_m3", "initial_mass_kg",
    "friction", "grade_rad", "pile_resistance_n_m", "half_width_m", "ceiling_m",
    "receiver_x_m", "receiver_y_m", "receiver_half_x_m", "receiver_half_y_m",
    "max_steps", "step_index", "success_kg", "stuck_limit_s", "decision_s",
    "obstacle_x_min_m", "obstacle_x_max_m", "obstacle_y_min_m", "obstacle_y_max_m", "obstacle_present")
STATE_NAMES = (*DYNAMIC_NAMES, *(f"pile_{i}_{j}_m" for i in range(8) for j in range(8)), *CONTEXT_NAMES)
INDEX = {name: i for i, name in enumerate(STATE_NAMES)}
STATE_SIZE = len(STATE_NAMES)
STATE_VERSION = "loader-dynamics-1"
EVENT_NAMES = ("terminated", "truncated", "contact", "collision")
TARGET_FLOORS = np.array([0.005, 0.005, 0.005, 0.01, 0.002, 0.002, 0.002, 1, 1, 1,
                          0.001, 0.02, 1, 0.001, 0.01]+[1e-5]*64+[0.001], dtype=float)


def pack(env):
    if env.loader.digest() != LoaderConfig().digest() or len(env.scene.obstacles) > 1:
        raise ValueError("world-model schema supports the default loader and at most one obstacle")
    n = env.num_envs
    obstacle = (*env.scene.obstacles[0], 1) if env.scene.obstacles else (0, 0, 0, 0, 0)
    result = np.column_stack((env.pose, env.speed, env.joints, env.payload, env.delivered, env.spilled,
        env.elapsed, env.stuck_time, env.effort, env.slip_s, env.last_slip,
        env.pile.height.reshape(n, -1), env.pile.origin, env.pile.density, env.pile.initial_mass,
        env.friction, env.grade, env.resistance, env.half_width, np.full(n, env.scene.ceiling_m),
        env.receiver, np.tile(env.receiver_half, (n, 1)), np.full(n, env.scene.max_steps), env.steps,
        np.full(n, env.scene.success_kg), np.full(n, env.scene.stuck_s), np.full(n, env.loader.decision_s),
        np.tile(obstacle, (n, 1))))
    if result.shape != (n, STATE_SIZE) or not np.isfinite(result).all():
        raise ValueError("invalid world-model state")
    return result


def delta_target(states, next_states, rewards):
    delta = np.asarray(next_states[:, :PILE_END]-states[:, :PILE_END], dtype=np.float64)
    delta[:, 2] = (delta[:, 2]+np.pi) % (2*np.pi)-np.pi
    return np.column_stack((delta, rewards))


def decode(states, changes):
    result = np.asarray(states, dtype=np.float64).copy()
    result[:, :PILE_END] += changes[:, :PILE_END]
    result[:, 2] = (result[:, 2]+np.pi) % (2*np.pi)-np.pi
    result[:, INDEX["step_index"]] += 1
    return result


def violations(states):
    s = np.asarray(states)
    mass = s[:, PILE_START:PILE_END].sum(axis=1)*0.25*s[:, INDEX["density_kg_m3"]]+s[:, 7:10].sum(axis=1)
    return {"non_finite": ~np.isfinite(s).all(axis=1),
        "negative_pile": (s[:, PILE_START:PILE_END] < -1e-6).any(axis=1),
        "negative_material": (s[:, 7:10] < -1e-6).any(axis=1),
        "capacity_excess": s[:, 7] > 3500+1e-3,
        "joint_bounds": (np.abs(s[:, 4]) > 0.6+1e-3) | (s[:, 5] < -0.1-1e-3) | (s[:, 5] > 1.1+1e-3)
                         | (s[:, 6] < -0.7-1e-3) | (s[:, 6] > 1.0+1e-3),
        "speed_bounds": (s[:, 3] < -1.5-1e-3) | (s[:, 3] > 2+1e-3),
        "mass_error_kg": mass-s[:, INDEX["initial_mass_kg"]]}


def model_observation(states):
    """Idealised local projection for short critic targets, not learned sensing."""
    s = np.asarray(states, dtype=float)
    n = len(s);yaw = s[:, 2];front_yaw = yaw+s[:, 4]
    rear = np.stack((np.cos(yaw), np.sin(yaw)), axis=1)
    front = np.stack((np.cos(front_yaw), np.sin(front_yaw)), axis=1)
    left = np.stack((-front[:, 1], front[:, 0]), axis=1)
    mouth = s[:, :2]+1.8*rear+(1.6+1.2*np.cos(s[:, 5]))[:, None]*front
    a, b = np.meshgrid(np.arange(-1, 4)*0.75, np.arange(-2, 3)*0.75, indexing="ij")
    points = mouth[:, None, None, :]+a[None, ..., None]*front[:, None, None, :]+b[None, ..., None]*left[:, None, None, :]
    origin = s[:, [INDEX["pile_origin_x_m"], INDEX["pile_origin_y_m"]]]
    local = np.floor((points-origin[:, None, None, :])/0.5).astype(int)
    valid = ((local >= 0) & (local < 8)).all(axis=-1)
    pile = s[:, PILE_START:PILE_END].reshape(n, 8, 8)
    crop = pile[np.arange(n)[:, None, None], np.clip(local[..., 0], 0, 7), np.clip(local[..., 1], 0, 7)]
    displacement = s[:, [INDEX["receiver_x_m"], INDEX["receiver_y_m"]]]-s[:, :2]
    p = np.column_stack((s[:, :2], np.sin(yaw), np.cos(yaw), s[:, 3:8],
        np.sum(displacement*rear, axis=1), np.sum(displacement*np.stack((-rear[:, 1], rear[:, 0]), axis=1), axis=1),
        np.zeros(n), np.ones(n), s[:, 10], s[:, 14]))
    return {"proprio": p, "local_height_m": np.where(valid, crop, 0), "range_valid": np.ones((n, 5, 5))}
