import json

import pytest
import torch

from kessel_training import checkpoints
from kessel_training.evaluation import load_policy
from kessel_training.study import DEFAULT_PLAN, configuration, export_policy, milestones, rank_candidates
from kessel_training.train import Trainer, TrainConfig, preset_config


def test_search_and_ablations_share_sample_budgets_and_use_training_seeds():
    plan = json.loads(DEFAULT_PLAN.read_text())
    assert len(plan["candidates"])*len(plan["training_seeds"])+len(plan["training_seeds"])*(1+len(plan["ablations"])) == plan["maximum_training_runs"]
    cap = len(plan["training_seeds"])*(len(plan["candidates"])*plan["search_wall_s_per_run"]
        + plan["full_wall_s_per_run"] + len(plan["ablations"])*plan["search_wall_s_per_run"])
    assert cap == plan["maximum_training_loop_seconds"]
    for candidate in plan["candidates"]:
        c = configuration(candidate, 7, plan["search_samples_per_run"], 30)
        assert c.num_envs*c.rollout_steps*c.updates == 40960
        assert c.curriculum and c.shaping and c.randomise_training
        ablation = configuration(candidate, 7, 40960, 30, "no_curriculum")
        assert not ablation.curriculum and ablation.shaping


def test_selection_does_not_use_test_metrics_or_training_reward():
    rows = []
    for name, size, fill in (("large", 64, 0.2), ("small", 32, 0.2), ("filling", 64, 0.4)):
        rows.append({"candidate": {"id": name, "hidden": size}, "validation_success_rate": 0,
                     "validation_delivered_kg": 0, "validation_fill_ratio": fill, "validation_collisions": 0})
    assert [r["candidate"]["id"] for r in rank_candidates(rows)] == ["filling", "small", "large"]


def test_replay_milestones_follow_actual_progress_and_stable_ties():
    report = {"checkpoints": [{"rollout": r} for r in (0, 2, 4, 6)]}
    assert [c["rollout"] for _, c in milestones(report)] == [0, 2, 6]


def test_compact_export_executes_the_same_policy_weights(tmp_path):
    trainer = Trainer(TrainConfig(num_envs=1, rollout_steps=2, updates=1))
    trainer.iterate()
    source, target = tmp_path/"source.pt", tmp_path/"policy.pt"
    checkpoints.save(source, trainer.state())
    export_policy(source, target)
    policy, identity = load_policy(target)
    for k, v in trainer.policy.state_dict().items():
        torch.testing.assert_close(v, policy.state_dict()[k], rtol=0, atol=0)
    assert identity["source_checkpoint_sha256"] == checkpoints.sha256(source)
    assert identity["checkpoint_sha256"] == checkpoints.sha256(target)


def test_measured_presets_keep_the_selected_network_and_bounded_work():
    quick, full = preset_config("quick"), preset_config("full")
    assert (quick.hidden, quick.num_envs, quick.rollout_steps) == (32, 16, 32)
    assert quick.updates*quick.num_envs*quick.rollout_steps == 40960
    assert full.updates*full.num_envs*full.rollout_steps == 262144
    assert quick.max_wall_s == 30 and full.max_wall_s == 120
    assert quick.curriculum and full.curriculum
