"""Explicit reward/environment exploit fixtures, separate from policy evaluation."""

import numpy as np
import torch

from .environment import LoaderEnv, SceneConfig
from .evaluate import source_identity
from .ppo import advantages


def reward_probe(env, action, steps):
    total, terms = 0.0, None
    for _ in range(steps):
        _, reward, term, trunc, info = env.step([action])
        total += float(reward[0])
        terms = {k: float(v[0]) for k, v in info["reward_terms"].items()}
        if (term | trunc).any():
            break
    return {"reward_total": total, "delivered_kg": float(env.delivered[0]),
            "spilled_kg": float(env.spilled[0]), "reason": str(env.reason[0]),
            "last_reward_terms": terms, "mass_error_kg": float(
                env.pile.mass()[0]+env.payload[0]+env.delivered[0]+env.spilled[0]-env.pile.initial_mass[0])}


def run_suite():
    cases = {}
    cases["idle"] = reward_probe(LoaderEnv(), [0, 0, 0, 0], 30)
    cases["empty_reverse"] = reward_probe(LoaderEnv(), [-0.3, 0, 0, 0], 30)
    env = LoaderEnv(scene=SceneConfig(obstacles=((5.3, 5.4, -2, 2),)))
    cases["wall_push"] = reward_probe(env, [1, 0, 0, 0], 40)
    try:
        env.step([[1, 0, 0, 0]])
        rejected = False
    except RuntimeError:
        rejected = True
    cases["wall_push"]["repeated_step_rejected"] = rejected
    env = LoaderEnv(scene=SceneConfig(friction=0.0001, stuck_s=0.2, max_steps=4))
    env.joints[0, 1] = env.loader.boom_max_rad
    cases["saturated_joint_stuck"] = reward_probe(env, [1, 0, 1, 0], 3)
    env = LoaderEnv()
    gain, _ = env.pile.extract(np.array([[9., 0.]]), np.array([[1., 0.]]), np.zeros(1), np.array([500.]), np.ones(1))
    env.payload += gain
    env.joints[0, 2] = -0.7
    cases["out_of_zone_tipping"] = reward_probe(env, [0, 0, 0, 0], 100)
    assert env.spilled[0] > 499.99 and env.delivered[0] == 0
    env.reset(seed=0)
    cases["reset_cannot_carry_delivery_credit"] = reward_probe(env, [0, 0, 0, 0], 1)
    r = torch.zeros((2, 1));v = torch.zeros((2, 1));nv = torch.tensor([[2.], [99.]])
    term = torch.zeros((2, 1), dtype=torch.bool);trunc = torch.tensor([[True], [False]])
    a, _ = advantages(r, v, nv, term, trunc, 0.9, 1)
    cases["truncation_no_reset_leak"] = {"first_advantage": float(a[0, 0]), "expected": 1.8}
    phi = np.array([1., 2., 1., 0.]); gamma = 0.995
    discounted = sum(gamma**i*(gamma*phi[i+1]-phi[i]) for i in range(3))
    cases["potential_cycle_no_farming"] = {"discounted_shaping": float(discounted), "expected": -1.0}
    for name in ("idle", "empty_reverse", "wall_push", "saturated_joint_stuck", "out_of_zone_tipping", "reset_cannot_carry_delivery_credit"):
        assert cases[name]["reward_total"] <= 0 and cases[name]["delivered_kg"] == 0
        assert abs(cases[name]["mass_error_kg"]) < 1e-7
    assert rejected and cases["saturated_joint_stuck"]["reason"] == "stuck"
    assert abs(cases["truncation_no_reset_leak"]["first_advantage"]-1.8) < 1e-6
    assert abs(discounted+1) < 1e-12
    return {"source_mode": "recorded_synthetic", "purpose": "Adversarial analytic fixtures, not learned-policy trajectories",
            "source": source_identity(), "passed": True, "cases": cases,
            "corrected_defect": "ADR-0039: saturated actuator requests no longer suppress stuck detection"}
