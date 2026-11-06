"""Execute retained neural weights against actual recorded prediction/reference pairs."""

import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import torch

from kessel_training.constrained_model import ConstrainedModel, FilterConfig
from kessel_training.policy import configure_cpu
from kessel_training.wm_export import verify_residuals
from kessel_training.world_model import load_model

ROOT = Path(__file__).resolve().parents[2]


def read(path):
    return json.loads(gzip.decompress(path.read_bytes()))


@torch.no_grad()
def test_retained_model_weights_reproduce_raw_and_explicitly_filtered_forecasts():
    configure_cpu(71)
    raw_root = ROOT/"docs/phase-11/world-model-evidence"
    model, identity = load_model(raw_root/"models/ensemble.pt")
    replayed = 0
    for folder, filtered in (("world-model-evidence", False), ("world-model-filter-evidence", True)):
        bundles = read(ROOT/"docs/phase-11"/folder/"predictions.json.gz")
        for bundle in bundles.values():
            assert bundle["model_identity"]["model_sha256"] == identity["model_sha256"]
            predictor = ConstrainedModel(model, FilterConfig(**bundle["model_identity"]["filter"])) if filtered else model
            assert verify_residuals(bundle) > 0
            for example in bundle["examples"]:
                current = np.asarray([example["initial_state"]]);reward = 0.0;stopped = False
                records = {r["horizon_decisions"]: r for r in example["predictions"]}
                for step, action in enumerate(example["actions"], 1):
                    if stopped:break
                    prediction = predictor.predict(current, np.asarray([action]))
                    current = prediction["next_state"];reward += float(prediction["reward"][0])
                    if step in records:
                        row=records[step];assert row["prediction"] is not None
                        np.testing.assert_allclose(current[0], row["prediction"]["state"], rtol=2e-5, atol=5e-4)
                        np.testing.assert_allclose(prediction["events"][0], row["prediction"]["event_probabilities"], rtol=2e-5, atol=5e-5)
                        assert abs(reward-row["prediction"]["cumulative_reward"]) < 5e-4
                        if filtered:
                            np.testing.assert_allclose(prediction["raw_next_state"][0], row["bounded_filter"]["raw_next_state"], rtol=2e-5, atol=5e-4)
                            assert bool(prediction["filter_rejected"][0]) == row["bounded_filter"]["rejected"]
                        replayed += 1
                    stopped = prediction["events"][0, :2].max() >= 0.5
    assert replayed >= 60


def test_packaged_world_model_evidence_preserves_budgets_splits_and_checksums():
    path=ROOT/"scripts/verify-world-model-evidence.py"
    spec=importlib.util.spec_from_file_location("verify_world_model_evidence",path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    assert module.verify() == {"files":48,"policy_training_runs":9}
