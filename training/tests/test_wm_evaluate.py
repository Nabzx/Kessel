import numpy as np

from kessel_training.environment import LoaderEnv
from kessel_training.wm_evaluate import errors, event_scores, metrics, simple_prediction
from kessel_training.wm_state import pack


def test_prediction_errors_use_real_reference_pairs_and_expose_impossible_material():
    env = LoaderEnv(2);state = pack(env)
    data = {"next_state": state, "reward": np.zeros(2), "events": np.zeros((2, 4), dtype=bool), "regime": np.array([0, 2])}
    prediction = {"next_state": state.copy(), "reward": np.zeros(2), "events": np.zeros((2, 4))}
    assert metrics(prediction, data)["position_mae_m"] == 0
    prediction["next_state"][0, 0] += 0.2
    prediction["next_state"][0, 7] = 4000
    report = metrics(prediction, data)
    assert report["position_mae_m"] == 0.1
    assert report["raw_violations"]["capacity_excess"] == 1
    assert report["mass_balance_max_kg"] > 3999
    assert errors(prediction, state, np.zeros(2), data["events"])["high_error"][0]


def test_simple_baseline_does_not_copy_future_material_or_unknown_events():
    state = pack(LoaderEnv(1));prediction = simple_prediction(state, np.array([[1., 0, 0, 0]]), "kinematic")
    assert prediction["next_state"][0, 0] > state[0, 0]
    assert prediction["next_state"][0, 7] == 0
    scores = event_scores(np.zeros(3), np.array([False, True, False]))
    assert scores["false_negatives"] == 1 and scores["precision_at_half"] is None
