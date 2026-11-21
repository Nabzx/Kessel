import numpy as np
import pytest

from kessel_training import checkpoints
from kessel_training.controller import ReferenceController
from kessel_training.curriculum import TrainingEnv
from kessel_training.environment import SceneConfig
from kessel_training.five_stage import FiveStageEnv, STAGES, advancement_gate
from kessel_training.kinematics import components


def make(stage='fill', n=2, **kwargs):
    return FiveStageEnv(n, seed=108000, scene=SceneConfig(randomise=True), stage=stage, **kwargs)


@pytest.mark.parametrize('stage', STAGES)
def test_prepared_ledger_and_tip_alignment(stage):
    env = make(stage)
    expected = 2200 if stage in ('retract', 'carry', 'tip') else 0
    np.testing.assert_array_equal(env.payload, expected)
    np.testing.assert_allclose(env.pile.mass()+env.payload, env.pile.initial_mass, atol=1e-7, rtol=0)
    assert not env.terminated.any() and not env.truncated.any()
    assert (env.delivered == 0).all() and (env.spilled == 0).all()
    if stage == 'tip':
        np.testing.assert_allclose(components(env.pose, env.joints)['mouth'], env.receiver, atol=1e-14)
        np.testing.assert_array_equal(env.joints[:, 1:], [[.35, .9]]*2)
        assert (env.potential() == 0).all()


def test_fill_2200_gate_and_retract_retention_are_not_legacy_thresholds():
    env = make()
    env.payload[:] = [2199, 2200]
    np.testing.assert_array_equal(env.achieved(), [False, True])
    env = make('retract')
    env.pose[:, 0] -= 1.01
    env.joints[:, 1:] = [.21, .41]
    env.payload[:] = [2099, 2100]
    np.testing.assert_array_equal(env.achieved(), [False, True])


def test_carry_requires_payload_stop_and_receiver_approach():
    env = make('tip', n=3)
    env.set_stage('carry', seed=108000)
    env.pose[:, :2] += env.receiver-components(env.pose, env.joints)['mouth']
    env.payload[:] = [2100, 2099, 2200]
    env.speed[:] = [0, 0, .2]
    np.testing.assert_array_equal(env.achieved(), [True, False, False])


def test_tip_delivery_is_not_full_success_and_terminal_steps_give_no_credit():
    env = make('tip', n=1)
    controller = ReferenceController(1)
    controller.phase[:] = 4
    for _ in range(200):
        _, _, term, trunc, info = env.step(controller.act(env.observe()))
        if (term | trunc).any():
            break
    assert info['metrics']['stage_success'][0]
    assert not info['metrics']['full_success'][0]
    assert env.delivered[0] >= 2000
    with pytest.raises(RuntimeError, match='reset finished'):
        env.step(np.zeros((1, 4)))


def test_collision_precedes_gate_and_invalid_start_fails_before_action():
    with pytest.raises(ValueError, match='clearance'):
        FiveStageEnv(1, seed=7, scene=SceneConfig(obstacles=((-10, 18, -4, 4),)), stage='tip')
    env = make(n=1)
    # A physically impossible gate fixture must still lose to collision.
    env.pile.height *= (env.pile.mass()[0]-2200)/env.pile.mass()[0]
    env.payload[:] = 2200
    env.pose[:, 1] = 20
    _, _, _, _, info = env.step(np.zeros((1, 4)))
    assert env.reason[0] == 'tunnel_wall'
    assert not info['metrics']['stage_success'][0]


def test_masked_reset_and_stage_transition_keep_other_slots_and_clear_history():
    env = make('retract')
    env.step(np.array([[-1, 0, 1, 1]]*2))
    before = env.pose[1].copy()
    env.reset(mask=np.array([True, False]))
    after = env.pose[1]
    np.testing.assert_array_equal(before, after)
    env.history = [True]*32
    env.set_stage('tip', seed=108000)
    assert env.history == [] and env.stage == 'tip'
    assert not env.steps.any()
    with pytest.raises(RuntimeError, match='retention'):
        env.consider_advancement([], 1)


@pytest.mark.parametrize('stage', STAGES)
def test_checkpoint_roundtrip_and_cross_contract_rejection(stage):
    a = make(stage)
    a.step(np.array([[-.2, .1, .1, .1]]*2))
    state = checkpoints.environment_state(a)
    b = make()
    checkpoints.restore_environment(b, state)
    for _ in range(3):
        aa = a.step(np.zeros((2, 4))); bb = b.step(np.zeros((2, 4)))
        for key in aa[0]:
            np.testing.assert_array_equal(aa[0][key], bb[0][key])
        np.testing.assert_array_equal(aa[1], bb[1])
        np.testing.assert_array_equal(a.pile.height, b.pile.height)
    legacy = TrainingEnv(2, seed=108000, scene=SceneConfig(randomise=True))
    with pytest.raises(ValueError, match='wrapper'):
        checkpoints.restore_environment(legacy, state)
    with pytest.raises(ValueError, match='wrapper'):
        checkpoints.restore_environment(b, checkpoints.environment_state(legacy))


def test_advancement_requires_current_validation_and_all_prior_retention():
    vals = {s: [True]*16 for s in STAGES[:4]}
    assert advancement_gate('tip', [True]*23+[False]*9, vals, 4096)['advance']
    vals['fill'] = [True]*11+[False]*5
    result = advancement_gate('tip', [True]*32, vals, 4096)
    assert result['reasons'] == ['prior_retention']
    vals['fill'] = [True]*12+[False]*4
    assert advancement_gate('tip', [True]*32, vals, 4096)['advance']
    vals['tip'] = [True]*13+[False]*3
    assert 'current_validation' in advancement_gate('tip', [True]*32, vals, 4096)['reasons']
    for decisions in (0, 4095, 32769):
        assert not advancement_gate('tip', [True]*32, vals, decisions)['advance']
    assert not advancement_gate('tip', [True]*22+[False]*10, vals, 4096)['advance']
    with pytest.raises(ValueError):
        advancement_gate('tip', [True]*32, {'tip': [True]*16}, 4096)
    with pytest.raises(ValueError):
        advancement_gate('fill', [True]*32, {'fill': [1]*16}, 4096)
