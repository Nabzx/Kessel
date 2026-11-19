import copy
import json

import numpy as np
import pytest
import torch

from kessel_training import full_cycle as fc
from kessel_training import checkpoints
from kessel_training.wm_state import pack


@pytest.fixture
def clean(monkeypatch):
    identity = fc.source_identity()
    monkeypatch.setattr(fc, 'source_identity', lambda: dict(identity, training_dirty=False))


def case(stage, seed, success=False):
    return dict(stage=stage, seed=seed, steps=1, reason='success' if success else 'timeout',
                cycle_s=1., stage_success=success, full_success=success and stage == 'complete',
                delivered_kg=2000 if success else 0)


def quick(monkeypatch):
    monkeypatch.setattr(fc, 'probe', lambda policy, stage, seed: case(stage, seed))


def test_resume_reproduces_updates_and_pending_validation(tmp_path, monkeypatch, clean):
    quick(monkeypatch)
    cfg = fc.Config(max_rollouts=2)
    a = fc.CycleRun(tmp_path/'a', cfg, 'test')
    a.train()
    b = fc.CycleRun(tmp_path/'b', cfg, 'test'); b.open_log()
    b.tick()
    for _ in range(7):
        b.tick()
    b.commit('interrupt')
    b = fc.CycleRun.resume(tmp_path/'b'); b.train()
    for name, value in a.policy.state_dict().items():
        torch.testing.assert_close(value, b.policy.state_dict()[name], rtol=0, atol=0)
    np.testing.assert_array_equal(pack(a.env), pack(b.env))
    assert a.counters == b.counters
    assert a.candidates == b.candidates
    assert a.phase == b.phase == 'frozen'


def test_resume_from_last_validation_case_does_not_requery(tmp_path, monkeypatch, clean):
    quick(monkeypatch)
    run = fc.CycleRun(tmp_path, fc.Config(max_rollouts=1), 'test'); run.open_log(); run.tick()
    p = run.pending
    p['cases'] = [case('complete', n) for n in fc.VALIDATION]
    run.counters['validation_decisions'] = 16
    run.commit('last_case')
    run = fc.CycleRun.resume(tmp_path)
    monkeypatch.setattr(fc, 'probe', lambda *_: pytest.fail('requeried validation'))
    run.tick()
    assert len(run.candidates) == 1 and run.phase == 'train'


def test_plain_reward_equals_raw_and_selection_prefers_earlier_tie(tmp_path):
    run = fc.CycleRun(tmp_path, fc.Config(), 'test')
    _, reward, _, _, info = run.env.step(np.zeros((4, 4)))
    np.testing.assert_array_equal(reward, info['training_reward']['raw_delivery_reward'])
    assert run.env.stage == 'complete' and not run.env.shaping
    assert fc.full_score([case('fill', 7, True)])[0] == 0
    assert fc.full_score([case('complete', 7, True)])[0] == 1


def test_gate_preserves_policy_and_optimiser_and_resets_environment(tmp_path):
    run = fc.CycleRun(tmp_path, fc.Config(method='curriculum'), 'test'); run.open_log()
    run.iterate()
    weights = copy.deepcopy(run.policy.state_dict())
    optimiser = copy.deepcopy(run.algorithm.optimiser.state_dict())
    run.env.history = [True]*32
    run.counters['stage_rollouts'] = 16
    batch = dict(policy_sha256=fc.policy_identity(run.policy),
                 cases=[case('fill', n, True) for n in fc.VALIDATION])
    run.apply_gate(batch)
    assert run.env.stage == 'retract' and run.env.history == []
    assert run.counters['stage_rollouts'] == 0
    assert not run.env.steps.any()
    for name, value in weights.items():
        torch.testing.assert_close(value, run.policy.state_dict()[name], rtol=0, atol=0)
    for key, value in optimiser['state'].items():
        for name, item in value.items():
            torch.testing.assert_close(item, run.algorithm.optimiser.state_dict()['state'][key][name], rtol=0, atol=0)


def test_gate_provenance_and_prior_retention_fail_closed(tmp_path):
    run = fc.CycleRun(tmp_path, fc.Config(method='curriculum'), 'test'); run.open_log()
    run.env.set_stage('retract'); run.env.history = [True]*32
    run.counters['stage_rollouts'] = 16
    batch = dict(policy_sha256=fc.policy_identity(run.policy), cases=[case(s, n, s == 'retract') for s in ('fill', 'retract') for n in fc.VALIDATION])
    run.apply_gate(batch)
    assert run.env.stage == 'retract' and 'prior_retention' in run.gates[-1]['reasons']
    batch['policy_sha256'] = 'wrong'
    with pytest.raises(ValueError, match='different policy'):
        run.apply_gate(batch)
    batch['policy_sha256'] = fc.policy_identity(run.policy)
    batch['cases'].pop()
    with pytest.raises(ValueError, match='provenance'):
        run.apply_gate(batch)


def test_stage_failure_stops_and_cap_preserves_test_allowance(tmp_path, monkeypatch, clean):
    quick(monkeypatch)
    run = fc.CycleRun(tmp_path/'stage', fc.Config(method='curriculum', stage_rollouts=1), 'test')
    run.train()
    assert run.status == 'stage_gate_failed' and run.counters['training_decisions'] == 256
    run = fc.CycleRun(tmp_path/'cap', fc.Config(max_rollouts=4, max_wall_s=10, test_reserve_s=3), 'test')
    monkeypatch.setattr(run, 'wall', lambda: run.counters['rollouts']*7.)
    run.train()
    assert run.status == 'training_wall_cap' and run.counters['rollouts'] == 1
    assert len(run.candidates) == 1  # Partial final validation cannot select.


def test_evaluation_preserves_training_rng_and_environment(tmp_path):
    run = fc.CycleRun(tmp_path, fc.Config(), 'test')
    state = pack(run.env).copy(); rng = run.generator.get_state().clone()
    fc.probe(run.policy, 'fill', 108000)
    np.testing.assert_array_equal(pack(run.env), state)
    torch.testing.assert_close(run.generator.get_state(), rng, rtol=0, atol=0)


def test_checkpoint_log_mismatch_rejected(tmp_path, clean):
    run = fc.CycleRun(tmp_path, fc.Config(), 'test'); run.open_log(); run.commit('initial')
    run.log.append('uncommitted', {'counters': dict(run.counters, rollouts=1)})
    with pytest.raises(ValueError, match='counters differ'):
        fc.CycleRun.resume(tmp_path)
