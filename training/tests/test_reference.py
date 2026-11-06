from dataclasses import replace

import numpy as np
import pytest

from kessel_training.controller import ReferenceController
from kessel_training.environment import LoaderEnv, SceneConfig
from kessel_training.scenarios import SPLITS, family, scenario_seed


def test_reference_completes_scoop_haul_delivery_and_records_nonzero_transfer():
    env = LoaderEnv(1, seed=0, scene=family("standard")[0])
    controller = ReferenceController(1)
    loaded = 0
    initial = env.scenario_identity()
    for _ in range(env.scene.max_steps):
        observation = env.observe()
        action = controller.act(observation)
        _, _, terminated, truncated, info = env.step(action)
        loaded += info["transfer"]["loaded_kg"][0]
        if (terminated | truncated).any():
            break
    assert info["metrics"]["reason"][0] == "success"
    assert loaded > env.scene.success_kg
    assert env.delivered[0] >= env.scene.success_kg
    assert env.effort[0] > 0 and env.elapsed[0] > 0
    assert env.spilled[0] == 0
    assert env.scenario_identity() == initial


def test_reference_keeps_a_blocked_failure_instead_of_restarting():
    env = LoaderEnv(1, seed=0, scene=family("blocked")[0])
    controller = ReferenceController(1)
    for _ in range(50):
        _, _, term, trunc, info = env.step(controller.act(env.observe()))
        if (term | trunc).any():
            break
    assert info["metrics"]["reason"][0] == "obstacle_0"
    assert env.delivered[0] == 0
    assert env.episode_index[0] == 0


def test_stuck_is_termination_and_can_be_distinguished_from_a_time_limit():
    env = LoaderEnv(1, scene=SceneConfig(friction=0.0001, stuck_s=0.2, max_steps=2))
    env.step([[1, 0, 0, 0]])
    _, _, term, trunc, info = env.step([[1, 0, 0, 0]])
    assert term[0] and not trunc[0]
    assert info["metrics"]["reason"][0] == "stuck"


def test_seed_partitions_do_not_overlap_or_silently_wrap():
    assert scenario_seed("train", 0) == 0
    assert scenario_seed("validation", 0) == 100000
    assert scenario_seed("test", 0) == 200000
    intervals = sorted(SPLITS.values())
    assert all(a[1] < b[0] for a, b in zip(intervals, intervals[1:]))
    for split in SPLITS:
        with pytest.raises(ValueError):
            scenario_seed(split, -1)
        with pytest.raises(ValueError):
            scenario_seed(split, 100000)
    with pytest.raises(ValueError):
        family("invented")


def test_family_is_repeatable_and_failure_case_is_explicit():
    standard, status = family("standard")
    assert status == "feasible_reference"
    for seed in range(8):
        a, b = LoaderEnv(1, seed=seed, scene=standard), LoaderEnv(1, seed=seed, scene=standard)
        assert a.scenario_identity() == b.scenario_identity()
        assert a.half_width[0] > a.loader.width_m
        assert a.pile.origin[0, 0]+4 < 18
        assert a.pile.initial_mass[0] > a.scene.success_kg
    assert family("blocked")[1] == "expected_failure"


def test_dropouts_do_not_change_scenario_or_dynamics_when_actions_are_fixed():
    a = LoaderEnv(2, seed=8, scene=SceneConfig(randomise=True))
    b = LoaderEnv(2, seed=8, scene=SceneConfig(randomise=True, sensor_noise=2, dropout=0.9))
    np.testing.assert_array_equal(a.pile.height, b.pile.height)
    for _ in range(20):
        a.step(np.tile([0.2, 0, -0.1, 0], (2, 1)))
        b.step(np.tile([0.2, 0, -0.1, 0], (2, 1)))
    np.testing.assert_array_equal(a.pose, b.pose)


def test_pile_contact_cannot_fill_a_stationary_bucket_without_a_scoop_action():
    env = LoaderEnv(1)
    env.pose[0, 0] = 4.4
    for _ in range(10):
        env.step([[0, 0, 0, 0]])
    assert env.payload[0] == 0


def test_roof_clearance_and_reverse_wall_limits_use_the_bucket_and_body():
    env = LoaderEnv(1, scene=SceneConfig(ceiling_m=1.9))
    for _ in range(100):
        _, _, term, _, info = env.step([[0, 0, 1, 0]])
        if term[0]:
            break
    assert info["metrics"]["reason"][0] == "tunnel_roof"
    env = LoaderEnv(1)
    for _ in range(100):
        _, _, term, _, info = env.step([[-1, 0, 0, 0]])
        if term[0]:
            break
    assert info["metrics"]["reason"][0] == "tunnel_wall"
    assert env.pose[0, 0] > -9.1
