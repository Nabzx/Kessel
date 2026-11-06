import numpy as np
import pytest

from kessel_training.environment import LoaderEnv
from kessel_training.wm_data import Normaliser, assert_disjoint, collect_split, logical_hash, load_partition, save_partition
from kessel_training.wm_state import STATE_SIZE, decode, delta_target, model_observation, pack, violations


def test_world_state_and_idealised_local_projection_match_reference_sensors():
    env = LoaderEnv(3, seed=4)
    for _ in range(3):
        state = pack(env)
        assert state.shape == (3, STATE_SIZE) and STATE_SIZE == 102
        observed, projected = env.observe(), model_observation(state)
        for k in observed:
            np.testing.assert_allclose(observed[k], projected[k], atol=1e-12)
        assert np.abs(violations(state)["mass_error_kg"]).max() < 1e-7
        env.step(np.tile([0.3, 0.1, -0.2, 0.1], (3, 1)))


def test_circular_delta_and_static_context_round_trip():
    env = LoaderEnv(1);a = pack(env);b = a.copy();a[0, 2] = np.pi-0.01;b[0, 2] = -np.pi+0.01
    b[0, -9] += 1
    target = delta_target(a, b, np.zeros(1))
    assert target[0, 2] == pytest.approx(0.02)
    out = decode(a, target)
    assert out[0, 2] == pytest.approx(b[0, 2])


def test_corpus_is_deterministic_and_archives_are_byte_identical(tmp_path):
    budgets = {"reference": 4, "random": 3, "policy": 3}
    a, ea = collect_split("train", budgets)
    b, eb = collect_split("train", budgets)
    assert logical_hash(a, ea) == logical_hash(b, eb)
    one, two = tmp_path/"one", tmp_path/"two"
    ma = save_partition(one, "train", a, ea);mb = save_partition(two, "train", b, eb)
    assert ma["archive_sha256"] == mb["archive_sha256"]
    loaded, _ = load_partition(one, "train")
    np.testing.assert_array_equal(loaded["next_state"], a["next_state"])
    assert all(e["collection_boundary"] for e in ea)
    assert not a["events"][:, :2].any()


def test_split_guard_rejects_same_generated_pile_or_episode_seed():
    first = ({}, [{"seed": 1, "initial_pile_sha256": "a"}])
    for second in (({}, [{"seed": 1, "initial_pile_sha256": "b"}]), ({}, [{"seed": 2, "initial_pile_sha256": "a"}])):
        with pytest.raises(ValueError, match="leaked"):
            assert_disjoint([first, second])


def test_train_only_normalisation_handles_constant_features_and_invalid_rows():
    train = np.array([[1., 5.], [3., 5.]])
    normal = Normaliser.fit(train)
    np.testing.assert_allclose(normal.inverse(normal.transform(train)), train, atol=1e-12)
    assert normal.constant.tolist() == [False, True]
    assert normal.transform(np.array([[100., 5.]]))[0, 0] == 98
    np.testing.assert_array_equal(normal.mean, [2, 5])
    with pytest.raises(ValueError):
        Normaliser.fit(np.array([[np.nan, 0], [1, 2]]))
