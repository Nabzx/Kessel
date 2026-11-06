from dataclasses import replace

import numpy as np
import pytest

from kessel_training import checkpoints
from kessel_training.environment import SceneConfig
from kessel_training.evaluation import evaluate_controller, load_policy, perturbation_spec, wilson
from kessel_training.train import Trainer, TrainConfig


def test_checkpoint_evaluation_uses_same_complete_task_identities_as_reference(tmp_path):
    trainer = Trainer(TrainConfig(num_envs=2, rollout_steps=2, updates=1))
    trainer.iterate()
    path = tmp_path/"policy.pt";checkpoints.save(path, trainer.state())
    policy, identity = load_policy(path)
    scene = SceneConfig(max_steps=3, randomise=True)
    trained = evaluate_controller(policy, count=2, identity=identity, record=True, scene_override=scene)
    reference = evaluate_controller(kind="reference", count=2, scene_override=scene)
    assert [c["scenario_sha256"] for c in trained["cases"]] == [c["scenario_sha256"] for c in reference["cases"]]
    assert identity["checkpoint_sha256"] == checkpoints.sha256(path)
    assert all(c["truncated"] for c in trained["cases"])
    assert trained["summary"]["episodes"] == 2
    first = trained["representative_traces"]["failure"]
    assert first["case"]["case_index"] == 0 and len(first["frames"]) == 3
    assert all(np.abs(f["action"]).max() <= 1 for f in first["frames"])
    assert first["final_record"]["action"] is None


def test_intervals_keep_all_failure_and_all_success_uncertainty_visible():
    assert wilson(0, 4)[1] > 0
    assert wilson(4, 4)[0] < 1
    assert wilson(0, 4)[0] >= 0
    with pytest.raises(ValueError):
        wilson(0, 0)


def test_robustness_severity_is_explicit_and_outside_training_distribution():
    a, _, label_a = perturbation_spec("sensing_moderate")
    b, _, label_b = perturbation_spec("sensing_severe")
    assert a.dropout < b.dropout
    assert label_a["severity"] < label_b["severity"]
    assert label_b["distribution"] == "out_of_training_distribution"
    with pytest.raises(ValueError):
        perturbation_spec("unknown")
