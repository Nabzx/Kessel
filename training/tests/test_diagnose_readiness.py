import pytest

from kessel_training.diagnose_readiness import rollout
from kessel_training.environment import LoaderEnv, SceneConfig
from kessel_training.reference_audit import pack


def test_idle_diagnostic_reconstructs_reward_and_conserves_material():
    result = rollout(100000, SceneConfig(max_steps=3), idle=True)
    assert result['reason'] == 'time_limit'
    assert result['delivered_kg'] == 0
    assert result['undiscounted_return'] == pytest.approx(-0.0006)
    assert sum(result['weighted_reward_totals'].values()) == pytest.approx(result['undiscounted_return'])
    assert result['max_mass_residual_kg'] < 1e-7


def test_diagnostic_rejects_changed_retained_outcome():
    scene = SceneConfig(max_steps=1)
    env = LoaderEnv(1, seed=100000, scene=scene)
    before = pack(env)[0].tolist()
    env.step([[0, 0, 0, 0]])
    expected = {'steps': 1, 'reason': 'success', 'records': [
        {'state': before, 'action': [0, 0, 0, 0]}, {'state': pack(env)[0].tolist()}]}
    with pytest.raises(AssertionError, match='outcome'):
        rollout(100000, scene, idle=True, expected=expected)


def test_diagnostic_rejects_changed_retained_state():
    scene = SceneConfig(max_steps=1)
    env = LoaderEnv(1, seed=100000, scene=scene)
    before = pack(env)[0].tolist()
    env.step([[0, 0, 0, 0]])
    after = pack(env)[0].tolist()
    after[0] += 0.1
    expected = {'steps': 1, 'reason': 'time_limit', 'records': [
        {'state': before, 'action': [0, 0, 0, 0]}, {'state': after}]}
    with pytest.raises(AssertionError, match='reproduce'):
        rollout(100000, scene, idle=True, expected=expected)
