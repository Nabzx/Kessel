import numpy as np
import torch

from kessel_training.wm_data import collect_split, logical_hash
from kessel_training.world_model import ModelConfig, fit, load_model, save_model


def test_model_training_round_trip_and_train_only_statistics(tmp_path):
    train, episodes = collect_split("train", {"reference": 10, "random": 6, "policy": 6})
    validation, _ = collect_split("validation", {"reference": 6, "random": 3, "policy": 3})
    manifest = {"episodes": episodes, "logical_sha256": logical_hash(train, episodes)}
    model, report = fit(train, validation, manifest, ModelConfig(members=2, hidden=16, epochs=2, seeds=(11, 19), batch_size=16))
    np.testing.assert_allclose(report["normalisers"]["input_mean"], np.column_stack((train["state"], train["action"])).mean(0))
    assert len(report["episode_bootstraps"]) == 2 and len(report["history"]) == 3
    assert report["history"][1]["current_validation"] != report["history"][0]["current_validation"]
    before = model.predict(validation["state"], validation["action"])
    path = tmp_path/"model.pt";save_model(path, model, report)
    restored, identity = load_model(path)
    after = restored.predict(validation["state"], validation["action"])
    for key in before:
        np.testing.assert_array_equal(before[key], after[key])
    assert len(identity["model_sha256"]) == 64
    assert before["events"].shape == (12, 4)
    assert np.isfinite(before["reward"]).all()
    assert ((before["events"] >= 0) & (before["events"] <= 1)).all()
