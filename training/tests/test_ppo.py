import copy

import pytest
import torch

from kessel_training.environment import LoaderEnv, SceneConfig
from kessel_training.policy import ActorCritic, configure_cpu
from kessel_training.ppo import PPO, PPOConfig, advantages, collect


def test_gae_matches_hand_calculated_nonterminal_returns():
    r = torch.tensor([[1.], [2.]], dtype=torch.float64)
    v = torch.tensor([[0.5], [0.6]], dtype=torch.float64)
    nv = torch.tensor([[0.6], [0.7]], dtype=torch.float64)
    boundary = torch.zeros((2, 1), dtype=torch.bool)
    a, returns = advantages(r, v, nv, boundary, boundary, 0.9, 1.0)
    torch.testing.assert_close(a, torch.tensor([[2.867], [2.03]], dtype=torch.float64), rtol=0, atol=1e-12)
    torch.testing.assert_close(returns, torch.tensor([[3.367], [2.63]], dtype=torch.float64), rtol=0, atol=1e-12)


@pytest.mark.parametrize("truncation,expected", [(False, 2.3), (True, 7.97)])
def test_gae_bootstraps_truncation_but_never_crosses_a_reset(truncation, expected):
    r = torch.tensor([[1.], [2.], [100.]], dtype=torch.float64)
    v = torch.tensor([[0.5], [0.6], [10.]], dtype=torch.float64)
    nv = torch.tensor([[0.6], [7.], [11.]], dtype=torch.float64)
    term = torch.tensor([[False], [not truncation], [False]])
    trunc = torch.tensor([[False], [truncation], [False]])
    a, _ = advantages(r, v, nv, term, trunc, 0.9, 1)
    assert a[0, 0] == pytest.approx(expected, abs=1e-12)
    assert a[2, 0] == pytest.approx(99.9, abs=1e-12)


def test_collector_captures_final_value_before_time_limit_reset():
    g = configure_cpu(4); policy = ActorCritic()
    policy.value = lambda features: features[:, 13]
    env = LoaderEnv(1, scene=SceneConfig(max_steps=1))
    rollout = collect(env, policy, 3, g)
    assert rollout.truncated.all() and not rollout.terminated.any()
    torch.testing.assert_close(rollout.values, torch.zeros((3, 1)))
    torch.testing.assert_close(rollout.next_values, torch.full((3, 1), 0.1/60))
    assert len(rollout.episodes) == 3 and env.episode_index[0] == 3


def test_real_ppo_update_changes_weights_and_records_finite_diagnostics():
    g = configure_cpu(19); policy = ActorCritic(); env = LoaderEnv(4)
    rollout = collect(env, policy, 12, g)
    before = copy.deepcopy(policy.state_dict())
    stats = PPO(policy).update(rollout, g)
    assert stats["minibatch_updates"] > 0 and stats["samples_used"] >= 48
    assert any(not torch.equal(v, before[k]) for k, v in policy.state_dict().items())
    for key in ("policy_loss", "value_loss", "entropy_mc", "approximate_kl", "clip_fraction", "gradient_norm_before_clip"):
        assert torch.isfinite(torch.tensor(stats[key]))
    assert all(torch.isfinite(p).all() for p in policy.parameters())
    assert stats["gradient_norm_after_clip"] <= 0.500001


def test_invalid_update_restores_parameters_optimiser_and_rng():
    g = configure_cpu(9); policy = ActorCritic(); algorithm = PPO(policy)
    rollout = collect(LoaderEnv(2), policy, 4, g)
    before = copy.deepcopy(policy.state_dict()); rng = g.get_state().clone()
    rollout.rewards[0, 0] = float("nan")
    with pytest.raises(FloatingPointError):
        algorithm.update(rollout, g)
    for key, value in policy.state_dict().items():
        torch.testing.assert_close(value, before[key], rtol=0, atol=0)
    torch.testing.assert_close(g.get_state(), rng)
    assert not algorithm.optimiser.state


def test_kl_guard_stops_before_an_unrelated_likelihood_update():
    g = configure_cpu(2); policy = ActorCritic()
    rollout = collect(LoaderEnv(2), policy, 4, g)
    rollout.log_prob += 4
    before = copy.deepcopy(policy.state_dict())
    stats = PPO(policy).update(rollout, g)
    assert stats["kl_stopped"] and stats["minibatch_updates"] == 0
    assert stats["kl_at_stop"] > PPOConfig().target_kl
    for key, value in policy.state_dict().items():
        torch.testing.assert_close(value, before[key], rtol=0, atol=0)


def test_discount_and_boundary_validation():
    with pytest.raises(ValueError):
        PPOConfig(gamma=1.1)
    with pytest.raises(ValueError):
        PPOConfig(minibatch=0)
    r = torch.ones((2, 1)); boundary = torch.ones((2, 1), dtype=torch.bool)
    with pytest.raises(ValueError):
        advantages(r, r, r, boundary, boundary, 0.99, 0.95)


def test_failure_after_an_optimiser_step_rolls_back_the_entire_update():
    g = configure_cpu(3); policy = ActorCritic(); algorithm = PPO(policy)
    rollout = collect(LoaderEnv(2), policy, 4, g)
    before = copy.deepcopy(policy.state_dict()); rng = g.get_state().clone()
    original_step = algorithm.optimiser.step

    def interrupted_step():
        original_step()
        raise FloatingPointError("injected failure after parameter mutation")

    algorithm.optimiser.step = interrupted_step
    with pytest.raises(FloatingPointError, match="injected"):
        algorithm.update(rollout, g)
    for key, value in policy.state_dict().items():
        torch.testing.assert_close(value, before[key], rtol=0, atol=0)
    assert not algorithm.optimiser.state
    torch.testing.assert_close(g.get_state(), rng)
