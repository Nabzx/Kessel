from dataclasses import asdict

import numpy as np
import pytest

from kessel_training.constrained_model import FilterConfig, filter_prediction
from kessel_training.environment import LoaderEnv
from kessel_training.imagination import admissibility, imagine
from kessel_training.policy import ActorCritic, configure_cpu
from kessel_training.wm_state import pack, PILE_START, PILE_END, INDEX


def forecast(state):
    out = state.copy();out[:, 10] += 0.1
    return {"next_state": out, "reward": np.full(len(state), -0.001),
        "events": np.zeros((len(state), 4)), "disagreement": np.zeros(len(state)), "input_envelope": np.zeros(len(state))}


def test_small_filter_repairs_are_explicit_conservative_and_cannot_move_machine():
    state = pack(LoaderEnv(2));raw = forecast(state)
    raw["next_state"][:, PILE_START:PILE_END] -= 0.00001
    raw["next_state"][:, 7] += 0.5
    result = filter_prediction(state, raw)
    assert not result["filter_rejected"].any()
    np.testing.assert_array_equal(result["next_state"][:, :3], raw["next_state"][:, :3])
    np.testing.assert_array_equal(result["raw_next_state"], raw["next_state"])
    mass = result["next_state"][:, PILE_START:PILE_END].sum(axis=1)*0.25*state[:, INDEX["density_kg_m3"]]+result["next_state"][:, 7:10].sum(axis=1)
    np.testing.assert_allclose(mass, state[:, INDEX["initial_mass_kg"]], rtol=0, atol=1e-8)
    assert result["filter_correction"]["pile_kg"].min() > 0
    assert admissibility(state, result["next_state"], result["reward"])[0].all()


def test_large_material_correction_cannot_enter_imagined_targets():
    env = LoaderEnv(1);state = pack(env);g = configure_cpu(4);policy = ActorCritic()
    class Bad:
        def predict(self, states, actions):
            raw = forecast(states);raw["next_state"][:, 7] += 1000
            return filter_prediction(states, raw)
    _, accepted, stats = imagine(Bad(), policy, state, policy.encode(env.observe()), {"threshold": 1, "supported_horizon": 2}, g)
    assert not accepted.any() and stats["rejections"]["bounded_filter"] == 1
    assert stats["imagined_transitions"] == 0
    assert stats["filter_correction_maxima"]["material_kg"] >= 1000


def test_filter_limits_are_finite_and_hash_identified():
    with pytest.raises(ValueError):FilterConfig(max_reward_correction=float("inf"))
    assert FilterConfig().digest() == FilterConfig(**asdict(FilterConfig())).digest()
    assert FilterConfig(max_material_correction_kg=1).digest() != FilterConfig().digest()
