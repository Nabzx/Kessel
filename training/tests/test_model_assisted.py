import copy

import numpy as np
import pytest
import torch

from kessel_training.model_assisted import auxiliary_value_step
from kessel_training.policy import ActorCritic, configure_cpu
from kessel_training.environment import LoaderEnv


def test_model_value_auxiliary_changes_only_critic_not_actor_or_sampling_state():
    g = configure_cpu(7);policy = ActorCritic(32)
    optimiser = torch.optim.Adam(policy.parameters(), lr=0.001)
    features = policy.encode(LoaderEnv(4).observe())
    actor = copy.deepcopy(policy.actor.state_dict());critic = copy.deepcopy(policy.critic.state_dict())
    rng = g.get_state().clone();log_std = policy.log_std.detach().clone()
    report = auxiliary_value_step(policy, optimiser, features, torch.ones(4))
    assert report["loss"] > 0
    for k, value in policy.actor.state_dict().items():
        torch.testing.assert_close(value, actor[k], rtol=0, atol=0)
    torch.testing.assert_close(policy.log_std, log_std, rtol=0, atol=0)
    torch.testing.assert_close(g.get_state(), rng, rtol=0, atol=0)
    assert any(not torch.equal(value, critic[k]) for k, value in policy.critic.state_dict().items())


def test_nonfinite_imagined_target_is_rejected_before_value_update():
    configure_cpu(3);policy = ActorCritic();optimiser = torch.optim.Adam(policy.parameters())
    features = policy.encode(LoaderEnv().observe())
    with pytest.raises(ValueError):
        auxiliary_value_step(policy, optimiser, features, torch.tensor([float("nan")]))
