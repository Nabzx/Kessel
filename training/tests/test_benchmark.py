import numpy as np
import pytest

from kessel_training.benchmark import LoadingSpike, measure_environment


def test_seeded_workloads_reproduce_state_and_mass_accounting():
    a, b = LoadingSpike(4), LoadingSpike(4)
    rng = np.random.default_rng(9)
    for _ in range(20):
        action = rng.uniform(-1, 1, (4, 4))
        x, ended = a.step(action)
        y, _ = b.step(action)
        np.testing.assert_array_equal(x, y)
        np.testing.assert_allclose(a.state[:, 5:8].sum(axis=1), a.initial_mass)
    assert ended.all()
    with pytest.raises(RuntimeError):
        a.step(action)


def test_reset_does_not_change_unselected_state():
    env = LoadingSpike(2)
    env.step(np.ones((2, 4)))
    previous = env.state[1].copy()
    env.reset([True, False])
    np.testing.assert_array_equal(env.state[1], previous)
    assert env.steps.tolist() == [0, 1]


def test_episode_and_physical_step_counts_are_separate():
    control = measure_environment(2, "control", 45, 42)
    primitive = measure_environment(2, "primitive", 45, 42)
    assert control["environment_steps"] == primitive["environment_steps"] == 90
    assert control["completed_episodes"] == primitive["completed_episodes"] == 4
    assert control["physical_substeps"] == 450
    assert primitive["physical_substeps"] == 4500
    assert primitive["simulated_seconds"] == 10 * control["simulated_seconds"]
    assert control["optimiser_updates"] == 0
