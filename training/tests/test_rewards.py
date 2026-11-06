import numpy as np
import pytest

from kessel_training.environment import LoaderEnv, SceneConfig
from kessel_training.rewards import RewardConfig, UNITS, calculate


def test_idle_empty_driving_and_collision_have_no_positive_reward():
    idle, driving = LoaderEnv(), LoaderEnv()
    ri = idle.step([[0, 0, 0, 0]])[1]
    _, rd, _, _, info = driving.step([[1, 0, 0, 0]])
    assert rd[0] < ri[0] < 0
    assert info["reward_description"]["version"] == "delivery-v1"
    assert info["reward_description"]["units"] == UNITS
    np.testing.assert_allclose(sum(info["reward_description"]["weighted"].values()), rd)
    collision = LoaderEnv(scene=SceneConfig(obstacles=((5.3, 5.4, -2, 2),)))
    for _ in range(40):
        _, reward, term, _, _ = collision.step([[1, 0, 0, 0]])
        if term[0]:
            break
    assert term[0] and reward[0] < -5


def test_partial_delivery_is_credited_once_and_carried_load_is_not_rewarded():
    env = LoaderEnv()
    gain, _ = env.pile.extract(np.array([[9., 0.]]), np.array([[1., 0.]]),
                               np.zeros(1), np.array([500.]), np.ones(1))
    env.payload += gain
    env.pose[0, 0] = -6.1
    # Holding a bucket earns no material reward.
    _, held, _, _, held_info = env.step([[0, 0, 0, 0]])
    assert held[0] < 0 and held_info["reward_terms"]["delivered_kg"][0] == 0
    env.joints[0, 2] = -0.7
    credited = 0
    for _ in range(100):
        _, _, _, _, info = env.step([[0, 0, 0, 0]])
        credited += info["reward_terms"]["delivered_kg"][0]
    assert credited == pytest.approx(500, abs=1e-7)
    assert env.delivered[0] == pytest.approx(500, abs=1e-7)
    assert env.payload[0] < 1e-7


def test_slip_has_an_explicit_cost_and_reward_config_is_hashed():
    terms = {k: np.zeros(2) for k in UNITS}
    terms["slip_s"][1] = 1
    total, description = calculate(terms)
    np.testing.assert_allclose(total, [0, -0.02])
    assert len(description["config_sha256"]) == 64
    with pytest.raises(ValueError):
        RewardConfig(mass_scale_kg=0)
    terms["delivered_kg"][0] = float("inf")
    with pytest.raises(ValueError):
        calculate(terms)
