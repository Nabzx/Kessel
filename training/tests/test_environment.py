from dataclasses import replace

import numpy as np
import pytest

from kessel_training.contracts import LoaderConfig
from kessel_training.dynamics import clearance, release_material, traction
from kessel_training.environment import LoaderEnv, SceneConfig
from kessel_training.kinematics import components


def assert_observations_equal(a, b):
    for key in a:
        np.testing.assert_array_equal(a[key], b[key])


@pytest.mark.parametrize("size", [0, -1, True, 1.5])
def test_invalid_batch_size(size):
    with pytest.raises(ValueError):
        LoaderEnv(size)


def test_action_trace_repeats_after_seeded_reset_and_outputs_are_copies():
    env = LoaderEnv(3, seed=91)
    actions = np.random.default_rng(9).uniform(-0.3, 0.3, (20, 3, 4))
    first = [env.step(a) for a in actions]
    env.reset(seed=91)
    second = [env.step(a) for a in actions]
    for a, b in zip(first, second):
        assert_observations_equal(a[0], b[0])
        np.testing.assert_array_equal(a[1], b[1])
        np.testing.assert_array_equal(a[4]["pose"], b[4]["pose"])
    obs, info = env.observe(), env.diagnostics()
    obs["proprio"][:] = 999
    info["geometry"]["front"][:] = 999
    info["pile_height_m"][:] = 999
    assert (env.observe()["proprio"] != 999).all()
    assert env.pile.height.max() < 999
    assert env.diagnostics()["geometry"]["front"].max() < 999


def test_partial_reset_does_not_change_other_stream_or_sensor_rng():
    scene = SceneConfig(sensor_noise=1, dropout=0.3, randomise=True)
    a, b = LoaderEnv(2, seed=7, scene=scene), LoaderEnv(2, seed=7, scene=scene)
    a.reset(mask=np.array([True, False]))
    before = a.observe()
    a.reset(mask=np.array([True, False]))
    for k in before:
        np.testing.assert_array_equal(before[k][1], a.observe()[k][1])
    for _ in range(5):
        oa = a.step(np.zeros((2, 4)))[0]
        ob = b.step(np.zeros((2, 4)))[0]
        for k in oa:
            np.testing.assert_array_equal(oa[k][1], ob[k][1])


def test_scalar_matches_batch_with_the_same_stream_id():
    batch = LoaderEnv(4, seed=29, scene=SceneConfig(randomise=True, sensor_noise=1))
    scalar = LoaderEnv(1, seed=29, stream_ids=[2], scene=batch.scene)
    rng = np.random.default_rng(1)
    for _ in range(35):
        a = rng.uniform(-0.4, 0.4, (4, 4))
        bo, br, bt, bx, bi = batch.step(a)
        so, sr, st, sx, si = scalar.step(a[2:3])
        for k in bo:
            np.testing.assert_allclose(bo[k][2:3], so[k], rtol=0, atol=1e-12)
        for k in ("pose", "joints", "pile_height_m", "wheel_angle_rad"):
            np.testing.assert_allclose(bi[k][2:3], si[k], rtol=0, atol=1e-12)
        np.testing.assert_allclose(br[2:3], sr, rtol=0, atol=1e-12)
        np.testing.assert_array_equal(bt[2:3], st)
        np.testing.assert_array_equal(bx[2:3], sx)


def test_time_limit_is_truncation_and_requires_explicit_reset():
    env = LoaderEnv(2, scene=SceneConfig(max_steps=1))
    obs, reward, terminated, truncated, info = env.step(np.zeros((2, 4)))
    assert not terminated.any() and truncated.all()
    assert (info["metrics"]["reason"] == "time_limit").all()
    assert reward.shape == (2,) and obs["proprio"].shape == (2, 15)
    with pytest.raises(RuntimeError, match="reset"):
        env.step(np.zeros((2, 4)))
    env.reset(mask=np.array([True, False]))
    with pytest.raises(RuntimeError):
        env.step(np.zeros((2, 4)))
    env.reset(mask=np.array([False, True]))
    env.step(np.zeros((2, 4)))


def test_invalid_inputs_do_not_mutate_state():
    env = LoaderEnv(1)
    before = env.diagnostics()
    for action in ([[np.nan, 0, 0, 0]], [[2, 0, 0, 0]], [0, 0, 0, 0]):
        with pytest.raises(ValueError):
            env.step(action)
        np.testing.assert_array_equal(env.pose, before["pose"])
    for mask in ([1], [True, False], True):
        with pytest.raises(ValueError):
            env.reset(mask=mask)
    with pytest.raises(ValueError):
        LoaderEnv(2, stream_ids=[1, 1])
    with pytest.raises(ValueError):
        LoaderEnv(seed=-1)


def test_grade_payload_friction_and_resistance_change_acceleration():
    env = LoaderEnv(2)
    args = (env.pose, env.speed, env.joints)
    low, slip, _, _ = traction(*args, np.array([0., 3500.]), np.ones(2), env.pile,
                               np.array([0.02, 0.02]), np.zeros(2), env.resistance, 1.5)
    assert (slip > 0).all() and (low >= 0).all()
    # At power-limited cruising speed, payload and uphill grade reduce progress.
    env.speed[:] = 2
    acceleration, _, _, _ = traction(*args, np.array([0., 3500.]), np.ones(2), env.pile,
                                     env.friction, np.array([0., 0.1]), env.resistance, 1.5)
    assert acceleration[1] < acceleration[0]
    env.pose[:, 0] = 4.5
    env.speed[:] = 0
    blocked, _, _, _ = traction(*args, np.zeros(2), np.ones(2), env.pile,
                                env.friction, env.grade, np.full(2, 1e9), 1.5)
    assert (blocked == 0).all()


def test_release_only_credits_the_receiver_and_empty_release_is_zero():
    delivered, spilled = release_material(np.array([100., 100., 0.]),
        np.full(3, -0.7), np.array([[0., 0.], [10., 0.], [0., 0.]]),
        np.zeros((3, 2)), np.ones(2), 0.1)
    np.testing.assert_allclose(delivered, [30, 0, 0])
    np.testing.assert_allclose(spilled, [0, 30, 0])


def test_swept_clearance_catches_thin_obstacle_and_preserves_clear_reverse():
    old = np.zeros((1, 3)); new = old.copy(); new[0, 0] = 10
    joints = np.zeros((1, 3))
    hit = clearance(old, joints, new, joints, np.array([4.2]), 3.2,
                    ((6., 6.01, -1., 1.),))
    assert hit[0] == "obstacle_0"
    new[0, 0] = -1
    assert clearance(old, joints, new, joints, np.array([4.2]), 3.2, ())[0] == ""
    new[0, 1] = 4.1
    assert clearance(old, joints, new, joints, np.array([4.2]), 3.2, ())[0] == "tunnel_wall"


def test_collision_stops_motion_and_records_time_and_impact_proxy():
    # Thin obstacle lies just ahead of the bucket at rest, not inside it.
    env = LoaderEnv(1, loader=replace(LoaderConfig(), decision_s=2),
                    scene=SceneConfig(obstacles=((5.4, 5.41, -2, 2),)))
    _, _, term, trunc, info = env.step([[1, 0, 0, 0]])
    assert term[0] and not trunc[0]
    assert info["metrics"]["reason"][0] == "obstacle_0"
    assert 0 < info["metrics"]["collision_time_s"][0] < 2
    assert info["metrics"]["impact_speed_m_s"][0] > 0
    assert components(env.pose, env.joints)["mouth"][0, 0] + 0.6 < 5.4
    assert env.speed[0] == 0


def test_random_actions_preserve_material_ledger_and_actuator_bounds():
    env = LoaderEnv(8, seed=44)
    rng = np.random.default_rng(91)
    for _ in range(150):
        _, _, term, trunc, info = env.step(rng.uniform(-1, 1, (8, 4)))
        m = info["metrics"]
        np.testing.assert_allclose(m["pile_kg"]+m["carried_kg"]+m["delivered_kg"]+m["spilled_kg"],
                                   m["initial_kg"], rtol=0, atol=1e-7)
        assert (env.payload >= 0).all() and (env.payload <= env.loader.payload_kg).all()
        assert (np.abs(env.joints[:, 0]) <= env.loader.articulation_rad).all()
        assert (np.abs(env.speed) <= env.loader.forward_m_s).all()
        if (term | trunc).any():
            env.reset(mask=term | trunc)


def test_sensor_dropout_has_age_and_cached_observations_do_not_advance_rng():
    env = LoaderEnv(1, scene=SceneConfig(dropout=1, sensor_noise=1))
    assert not env.observe()["range_valid"].any()
    first = env.observe()
    for _ in range(5):
        assert_observations_equal(first, env.observe())
    obs = env.step([[0, 0, 0, 0]])[0]
    assert obs["proprio"][0, 11] == pytest.approx(0.1)
    assert obs["proprio"][0, 12] == 0
    # A privileged far-away pile cell cannot enter the local sensor crop.
    a, b = LoaderEnv(1, seed=77), LoaderEnv(1, seed=77)
    b.pile.height[0, -1, -1] += 1
    b.pile.initial_mass[:] = b.pile.mass()
    ao = a.step([[0, 0, 0, 0]])[0]
    bo = b.step([[0, 0, 0, 0]])[0]
    assert_observations_equal(ao, bo)
    assert "pile_height_m" not in ao and "future" not in ao
