import io
import json

import numpy as np
import pytest
import torch

from kessel_training import checkpoints
from kessel_training.policy import ActorCritic, configure_cpu
from kessel_training.retraction_pilot import Config, PilotRun, best_candidate, score
from kessel_training.reserve_scenarios import inspect, sha
from kessel_training.wm_state import pack


def test_default_exploration_preserves_legacy_initialisation_and_actions():
    configure_cpu(7)
    old = ActorCritic(64)
    configure_cpu(7)
    explicit = ActorCritic(64, initial_log_std=[-.5] * 4)
    for name, value in old.state_dict().items():
        torch.testing.assert_close(value, explicit.state_dict()[name], rtol=0, atol=0)
    for setting in ([1, 2], [False, 0, 0, 0], [float('nan')] * 4, [-5] * 4):
        with pytest.raises(ValueError):
            ActorCritic(8, initial_log_std=setting)


def test_steering_ablation_changes_only_exploration_initialisation():
    configure_cpu(7)
    baseline = ActorCritic(64)
    configure_cpu(7)
    steering = ActorCritic(64, initial_log_std=[-.5, -2.5, -.5, -.5])
    for name, value in baseline.state_dict().items():
        if name != 'log_std':
            torch.testing.assert_close(value, steering.state_dict()[name], rtol=0, atol=0)


def test_checkpoint_resume_reproduces_uninterrupted_optimisation(tmp_path, monkeypatch):
    from kessel_training import retraction_pilot as pilot
    identity = pilot.source_identity()
    monkeypatch.setattr(pilot, 'source_identity', lambda: dict(identity, training_dirty=False))
    cfg = Config(rollouts=4)
    continuous = PilotRun(tmp_path / 'continuous', cfg, 'test', [100000])
    for _ in range(4):
        continuous.iterate()
    interrupted = PilotRun(tmp_path / 'interrupted', cfg, 'test', [100000])
    interrupted.open_log()
    for _ in range(2):
        interrupted.iterate()
    interrupted.transaction('rollout', 'boundary')
    resumed = PilotRun.resume(tmp_path / 'interrupted')
    for _ in range(2):
        resumed.iterate()
    for name, value in continuous.policy.state_dict().items():
        torch.testing.assert_close(value, resumed.policy.state_dict()[name], rtol=0, atol=0)
    np.testing.assert_array_equal(pack(continuous.env), pack(resumed.env))
    assert continuous.counters == resumed.counters


def test_validation_is_separate_from_training_state_and_rng(tmp_path):
    run = PilotRun(tmp_path, Config(rollouts=1), 'test', [100000])
    before = pack(run.env).copy()
    rng = run.generator.get_state().clone()
    run.evaluate()
    np.testing.assert_array_equal(pack(run.env), before)
    torch.testing.assert_close(run.generator.get_state(), rng, rtol=0, atol=0)
    assert run.counters['training_decisions'] == 0 and run.counters['validation_decisions'] > 0


def test_selection_ignores_reward_and_keeps_earlier_exact_tie():
    early = {'score': [14, 0, -3.0], 'rollout': 16, 'reward': -1000}
    late = {'score': [14, 0, -3.0], 'rollout': 32, 'reward': 1000}
    failed = {'score': [0, 0, 0], 'rollout': 128, 'reward': 100000}
    assert best_candidate([early, late, failed]) is early


def test_prepared_delivery_cannot_substitute_for_the_retraction_gate():
    assert score([{'reason': 'success', 'stage_success': True, 'cycle_s': 10}])[0] == 0
    assert score([{'reason': 'stage_success', 'stage_success': True, 'cycle_s': 3}])[0] == 1


def test_archive_scan_detects_seed_and_geometry_reuse_without_outcome_inspection():
    assert inspect(b'{"seed":208900,"success":false}', 'case.json', {208900}, set())
    state = np.arange(102, dtype=float)
    stream = io.BytesIO()
    np.savez_compressed(stream, state=state[None])
    assert inspect(stream.getvalue(), 'case.npz', set(), {sha(state[15:79].astype('<f4').tobytes())})
    assert inspect(json.dumps({'state': state.tolist()}).encode(), 'case.json', set(), {sha(state.astype('<f8').tobytes())})


def test_paused_runs_do_not_charge_other_runs_wall_time(tmp_path):
    run = PilotRun(tmp_path, Config(), 'test', [100000])
    run.pause_clock()
    before = run.wall()
    assert run.wall() == before
    run.start_clock()
    assert run.wall() >= before
