import numpy as np
import pytest
import torch

from kessel_training.environment import LoaderEnv
from kessel_training.policy import ActorCritic, configure_cpu, squashed_log_prob


def test_policy_actions_and_density_match_pytorch_transform():
    mean = torch.tensor([[0.1, -0.2, 0.3, 0.4]], dtype=torch.float64)
    log_std = torch.full_like(mean, -0.4)
    latent = torch.tensor([[0.2, -0.6, 1.2, -2.1]], dtype=torch.float64)
    transformed = torch.distributions.TransformedDistribution(
        torch.distributions.Normal(mean, log_std.exp()),
        [torch.distributions.TanhTransform(cache_size=1)])
    expected = transformed.log_prob(latent.tanh()).sum(-1)
    torch.testing.assert_close(squashed_log_prob(mean, log_std, latent), expected, rtol=0, atol=1e-12)
    extreme = torch.tensor([[-30., -10., 10., 30.]])
    assert torch.isfinite(squashed_log_prob(torch.zeros_like(extreme), torch.zeros_like(extreme), extreme)).all()


def test_sampled_actions_and_recomputed_likelihoods_are_identical_and_bounded():
    generator = configure_cpu(7)
    policy = ActorCritic()
    features = policy.encode(LoaderEnv(16).observe())
    sample = policy.sample(features, generator=generator)
    log_prob, _, _ = policy.evaluate(features, sample["latent"], generator=generator)
    torch.testing.assert_close(sample["action"], sample["latent"].tanh(), rtol=0, atol=0)
    torch.testing.assert_close(sample["log_prob"], log_prob, rtol=0, atol=0)
    assert (sample["action"].abs() <= 1).all()
    assert sample["action"].shape == (16, 4) and sample["value"].shape == (16,)
    assert policy.description()["parameters"] == 17097
    assert all(p.device.type == "cpu" for p in policy.parameters())


def test_initialisation_sampling_and_deterministic_evaluation_repeat():
    g1 = configure_cpu(11); a = ActorCritic()
    features = a.encode(LoaderEnv(2).observe())
    first = a.sample(features, generator=g1)
    g2 = configure_cpu(11); b = ActorCritic()
    second = b.sample(features, generator=g2)
    for k in first:
        torch.testing.assert_close(first[k], second[k], rtol=0, atol=0)
    before = g2.get_state().clone()
    deterministic = b.sample(features, generator=g2, deterministic=True)
    torch.testing.assert_close(before, g2.get_state())
    torch.testing.assert_close(deterministic["action"], b.actor(features).tanh())


def test_observation_normalisation_rejects_privileged_or_nonfinite_input():
    configure_cpu(0); policy = ActorCritic(); obs = LoaderEnv().observe()
    assert policy.encode(obs).shape == (1, 65)
    assert "proprio_scale" in policy.state_dict()
    assert "height_scale" in policy.state_dict()
    obs["privileged_pile"] = np.zeros((1, 8, 8))
    with pytest.raises(ValueError, match="local"):
        policy.encode(obs)
    del obs["privileged_pile"]
    obs["proprio"][0, 0] = np.nan
    with pytest.raises(ValueError, match="finite"):
        policy.encode(obs)
