import numpy as np
import torch

from kessel_training.environment import LoaderEnv
from kessel_training.imagination import admissibility, imagine
from kessel_training.policy import ActorCritic, configure_cpu
from kessel_training.wm_state import pack
from kessel_training.wm_state import PILE_END, INDEX


class FrozenFixture:
    def __init__(self, *, uncertainty=0, terminal=False):
        self.uncertainty, self.terminal = uncertainty, terminal

    def predict(self, states, actions):
        events = np.zeros((len(states), 4));events[:, 0] = self.terminal
        result = states.copy();result[:, 10] += 0.1
        return {"next_state": result, "reward": np.full(len(states), -0.001),
                "events": events, "disagreement": np.full(len(states), self.uncertainty), "input_envelope": np.zeros(len(states))}


def test_imagination_stops_on_uncertainty_and_terminal_events_without_reference_steps():
    g = configure_cpu(4);policy = ActorCritic();env = LoaderEnv(3)
    states = pack(env);features = policy.encode(env.observe())
    gate = {"threshold": 0.1, "supported_horizon": 2}
    _, accepted, stats = imagine(FrozenFixture(uncertainty=1), policy, states, features, gate, g)
    assert not accepted.any() and stats["imagined_transitions"] == 0
    _, accepted, stats = imagine(FrozenFixture(terminal=True), policy, states, features, gate, g)
    assert accepted.all() and stats["imagined_transitions"] == 3
    assert stats["accepted_horizons"]["1"] == 3
    assert stats["reference_transitions_generated"] == 0
    np.testing.assert_array_equal(env.elapsed, 0)


def test_physical_guards_expose_material_creation_and_reward_exploitation():
    state = pack(LoaderEnv(2));predicted = state.copy()
    predicted[0, 7] = 100
    valid, reasons = admissibility(state, predicted, np.array([0.1, 0.1]))
    assert not valid.any() and reasons["mass_balance"][0]
    assert reasons["unearned_reward"].all()


def test_mass_conservation_alone_cannot_authorise_remote_ore_pickup():
    state = pack(LoaderEnv(1));predicted = state.copy()
    predicted[0, PILE_END-1] -= 1/(0.25*state[0, INDEX["density_kg_m3"]])
    predicted[0, 7] += 1
    valid, reasons = admissibility(state, predicted, np.zeros(1))
    assert reasons["remote_extraction"][0] and not valid[0]
    assert not reasons["mass_balance"][0]
