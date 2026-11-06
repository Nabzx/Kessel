import numpy as np
import pytest
import torch

from kessel_training import checkpoints
from kessel_training.environment import SceneConfig
from kessel_training.train import TrainConfig, Trainer


def test_checkpoint_resume_matches_uninterrupted_policy_environment_and_rng(tmp_path):
    config = TrainConfig(num_envs=3, rollout_steps=4, updates=4,
                         scene=SceneConfig(randomise=True, sensor_noise=1, dropout=0.2))
    uninterrupted = Trainer(config)
    for _ in range(4):
        uninterrupted.iterate()
    interrupted = Trainer(config)
    for _ in range(2):
        interrupted.iterate()
    path = tmp_path/"resume.pt"
    checkpoints.save(path, interrupted.state())
    resumed = Trainer.resume(path)
    for _ in range(2):
        resumed.iterate()
    for key, value in uninterrupted.policy.state_dict().items():
        torch.testing.assert_close(value, resumed.policy.state_dict()[key], rtol=0, atol=0)
    np.testing.assert_array_equal(uninterrupted.env.pose, resumed.env.pose)
    np.testing.assert_array_equal(uninterrupted.env.pile.height, resumed.env.pile.height)
    for key, value in uninterrupted.env.observe().items():
        np.testing.assert_array_equal(value, resumed.env.observe()[key])
    torch.testing.assert_close(uninterrupted.generator.get_state(), resumed.generator.get_state())
    assert uninterrupted.counters == resumed.counters
    assert uninterrupted.curve[-1]["policy_loss"] == resumed.curve[-1]["policy_loss"]


def test_checkpoint_corruption_and_overwrite_are_rejected(tmp_path):
    trainer = Trainer(TrainConfig(num_envs=1, rollout_steps=2, updates=1))
    path = tmp_path/"checkpoint.pt"
    checkpoints.save(path, trainer.state())
    with pytest.raises(FileExistsError):
        checkpoints.save(path, trainer.state())
    path.write_bytes(path.read_bytes()+b"changed")
    with pytest.raises(ValueError, match="hash"):
        checkpoints.load(path)


def test_wall_budget_and_requested_stop_save_recoverable_state(tmp_path):
    trainer = Trainer(TrainConfig(num_envs=1, updates=3, max_wall_s=1e-9))
    report = trainer.run(tmp_path/"budget")
    assert report["stop_reason"] == "wall_budget" and report["counters"]["rollouts"] == 0
    resumed = Trainer.resume(tmp_path/"budget/checkpoint-000000-final.pt")
    assert resumed.counters == trainer.counters
    assert resumed.training_wall_s == trainer.training_wall_s
    trainer = Trainer(TrainConfig(num_envs=1, updates=3))
    trainer.stop_requested = True
    assert trainer.run(tmp_path/"stop")["stop_reason"] == "requested_stop"


@pytest.mark.parametrize("kwargs", [{"num_envs": 0}, {"seed": 100000}, {"updates": -1}, {"max_wall_s": float("nan")}])
def test_training_configuration_bounds(kwargs):
    with pytest.raises(ValueError):
        TrainConfig(**kwargs)


def test_resume_preserves_checkpoint_history_and_continues_cli_boundary(tmp_path):
    config = TrainConfig(num_envs=2, rollout_steps=2, updates=4, checkpoint_every=1)
    trainer = Trainer(config)
    trainer.run(tmp_path, until_update=2)
    resumed = Trainer.resume(tmp_path/"checkpoint-000002-final.pt")
    report = resumed.run(tmp_path)
    assert report["counters"]["rollouts"] == 4
    assert {c["rollout"] for c in report["checkpoints"]} == {0, 1, 2, 3, 4}
    assert report["learning_curve"][0]["rollout"] == 1
