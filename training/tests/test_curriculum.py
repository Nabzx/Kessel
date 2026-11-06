import numpy as np
import pytest
import torch

from kessel_training import checkpoints
from kessel_training.curriculum import TrainingEnv, STAGES
from kessel_training.environment import LoaderEnv, SceneConfig
from kessel_training.train import TrainConfig, Trainer


def make_env():
    return TrainingEnv(4, seed=7, scene=SceneConfig(randomise=True), curriculum=True, shaping=True)


def test_prepared_starts_preserve_mass_and_do_not_claim_a_learned_scoop():
    env = make_env()
    for stage in range(4):
        env.stage_index = stage
        env.base.scene = env._scene()
        env.reset(seed=7)
        env.base._assert_finite()
        assert env.stage == STAGES[stage]
        assert np.isfinite(env.observe()["proprio"]).all()
        if stage in (1, 2):
            assert (env.payload > 0).all()
            assert (env.delivered == 0).all()
        else:
            assert (env.payload == 0).all()


def test_curriculum_requires_a_complete_objective_window_and_never_advances_on_a_clock():
    env = make_env()
    assert env.consider_advancement([], 10000) is None
    success = {"stage": "fill", "stage_success": True}
    failure = {"stage": "fill", "stage_success": False}
    assert env.consider_advancement([success]*22+[failure]*9, 1) is None
    assert env.stage == "fill"
    assert env.consider_advancement([failure], 2) is None
    event = env.consider_advancement([success], 3)
    # Window now still has 22/32 successes: the first old success was removed.
    assert event is None
    env.history = []
    event = env.consider_advancement([success]*23+[failure]*9, 4)
    assert event["successes"] == 23 and env.stage == "retract"
    assert env.transitions[-1]["rollout"] == 4


def test_potential_reward_is_a_discounted_difference_and_not_pickup_credit():
    env = make_env()
    phi = env.potential().copy()
    _, reward, term, _, info = env.step(np.zeros((4, 4)))
    after = np.where(term, 0, env.potential())
    np.testing.assert_allclose(info["training_reward"]["potential_difference"], env.gamma*after-phi)
    np.testing.assert_allclose(reward, info["training_reward"]["raw_delivery_reward"]+env.gamma*after-phi)
    assert (info["reward_terms"]["delivered_kg"] == 0).all()


def test_randomised_payload_estimates_are_seeded_bounded_and_do_not_change_mass():
    scene = SceneConfig(randomise=True, sensor_noise=1, dropout=0.1, load_bias_fraction=0.05)
    a, b = LoaderEnv(16, seed=19, scene=scene), LoaderEnv(16, seed=19, scene=scene)
    np.testing.assert_array_equal(a.load_bias, b.load_bias)
    assert np.abs(a.load_bias).max() <= 175
    assert (a.observe()["proprio"][:, 8] >= 0).all()
    assert (a.observe()["proprio"][:, 8] <= 3500).all()
    assert np.all((a.friction >= 0.42) & (a.friction <= 0.72))
    a._assert_finite()
    with pytest.raises(ValueError):
        SceneConfig(load_bias_fraction=0.5)


def test_curriculum_and_randomisation_resume_exactly(tmp_path):
    config = TrainConfig(num_envs=3, rollout_steps=4, updates=3,
                         curriculum=True, shaping=True, randomise_training=True)
    a = Trainer(config); a.iterate(); a.iterate(); a.iterate()
    b = Trainer(config); b.iterate()
    path = tmp_path/"curriculum.pt";checkpoints.save(path, b.state())
    b = Trainer.resume(path); b.iterate(); b.iterate()
    for k, value in a.policy.state_dict().items():
        torch.testing.assert_close(value, b.policy.state_dict()[k], rtol=0, atol=0)
    np.testing.assert_array_equal(a.env.pose, b.env.pose)
    assert a.env.history == b.env.history and a.counters == b.counters
