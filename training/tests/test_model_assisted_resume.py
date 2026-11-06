import numpy as np
import pytest
import torch

from kessel_training import checkpoints
from kessel_training.model_assisted import ModelAssistedTrainer
from kessel_training.train import TrainConfig, Trainer
from kessel_training.wm_data import Normaliser
from kessel_training.wm_state import PILE_END, STATE_SIZE, STATE_VERSION
from kessel_training.world_model import DynamicsEnsemble, ModelConfig


@pytest.mark.parametrize("filter_config", [None, {}])
def test_model_assisted_resume_keeps_gate_rng_and_rejected_samples_separate(tmp_path, filter_config):
    config = ModelConfig(members=1, hidden=8, epochs=1, seeds=(11,))
    nx = Normaliser(np.zeros(STATE_SIZE+4), np.ones(STATE_SIZE+4), np.zeros(STATE_SIZE+4, dtype=bool))
    ny = Normaliser(np.zeros(PILE_END+1), np.ones(PILE_END+1), np.zeros(PILE_END+1, dtype=bool))
    model = DynamicsEnsemble(config, nx, ny)
    payload = {"model_version": STATE_VERSION, "artefact_kind": "dynamics-ensemble",
               "configuration": {"members": 1, "hidden": 8, "epochs": 1, "seeds": (11,)}, "weights": model.state_dict()}
    training = TrainConfig(num_envs=2, hidden=16, rollout_steps=4, updates=8)
    gate = {"threshold": None, "supported_horizon": 0}
    a = ModelAssistedTrainer(training, payload, "fixture-model", gate, filter_config)
    for _ in range(8):a.iterate()
    b = ModelAssistedTrainer(training, payload, "fixture-model", gate, filter_config)
    for _ in range(4):b.iterate()
    path = tmp_path/"assisted.pt";checkpoints.save(path, b.state())
    with pytest.raises(ValueError, match="matching model-assisted"):
        Trainer.resume(path)
    b = ModelAssistedTrainer.resume(path)
    for _ in range(4):b.iterate()
    for key, value in a.policy.state_dict().items():
        torch.testing.assert_close(value, b.policy.state_dict()[key], rtol=0, atol=0)
    assert b.filter_config == filter_config
    assert a.counters == b.counters
    assert a.counters["imagined_transitions"] == 0 and a.counters["rejected_branches"] > 0
    assert a.counters["auxiliary_updates"] == 0
    control = Trainer(training)
    for _ in range(8):control.iterate()
    for key, value in a.policy.state_dict().items():
        torch.testing.assert_close(value, control.policy.state_dict()[key], rtol=0, atol=0)
