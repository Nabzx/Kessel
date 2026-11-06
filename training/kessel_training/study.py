"""Execute the predeclared bounded model-free study, including unsuccessful runs."""

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np

from . import checkpoints
from .adversarial import run_suite
from .contracts import canonical_json
from .evaluation import evaluate_controller, load_policy
from .evaluate import source_identity
from .ppo import PPOConfig
from .train import TrainConfig, Trainer

DEFAULT_PLAN = Path(__file__).parent.parent/"experiments/rl-study-v1.json"


def write_json(path, data):
    path = Path(path)
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False)+"\n")


def configuration(candidate, seed, samples, wall_s, ablation=None):
    per_rollout = candidate["num_envs"]*candidate["rollout_steps"]
    if samples % per_rollout:
        raise ValueError("study sample target must be divisible by the rollout batch")
    updates = samples//per_rollout
    return TrainConfig(seed=seed, num_envs=candidate["num_envs"], hidden=candidate["hidden"],
        rollout_steps=candidate["rollout_steps"], updates=updates, max_wall_s=wall_s,
        checkpoint_every=max(1, updates//4), curriculum=ablation != "no_curriculum",
        shaping=ablation != "no_shaping", randomise_training=True,
        ppo=PPOConfig(learning_rate=candidate["learning_rate"]))


def final_checkpoint(report):
    maximum = max(c["rollout"] for c in report["checkpoints"])
    return next(c for c in reversed(report["checkpoints"]) if c["rollout"] == maximum)


def rank_candidates(rows):
    return sorted(rows, key=lambda r: (-r["validation_success_rate"], -r["validation_delivered_kg"],
        -r["validation_fill_ratio"], r["validation_collisions"], r["candidate"]["hidden"], r["candidate"]["id"]))


def milestones(report):
    earliest = min(report["checkpoints"], key=lambda c: c["rollout"])
    latest = final_checkpoint(report)
    middle = min(report["checkpoints"], key=lambda c: (abs(c["rollout"]-latest["rollout"]/2), c["rollout"]))
    return [("initial", earliest), ("intermediate", middle), ("final", latest)]


def training_run(root, candidate, seed, config, name, count):
    run_dir = root/"runs"/name
    if run_dir.exists():
        raise FileExistsError("study run exists; do not silently replace or omit it")
    report = Trainer(config).run(run_dir)
    checkpoint = final_checkpoint(report)
    policy, identity = load_policy(checkpoint["path"])
    validation = evaluate_controller(policy, split="validation", count=count, identity=identity)
    write_json(run_dir/"validation.json", validation)
    record = {"name": name, "candidate": candidate, "seed": seed, "configuration_sha256": config.digest(),
        "counters": report["counters"], "training_wall_s": report["training_wall_s"],
        "stop_reason": report["stop_reason"], "curriculum_transitions": report["curriculum_transitions"],
        "last_training_stage": report["learning_curve"][-1]["training_stage"] if report["learning_curve"] else "none",
        "final_checkpoint": checkpoint, "validation": validation["summary"]}
    print(json.dumps({"event": "training_run", "name": name, "steps": report["counters"]["environment_steps"],
        "episodes": report["counters"]["completed_episodes"], "subtask_successes": report["counters"]["subtask_successes"],
        "stage": record["last_training_stage"], "validation_success": validation["summary"]["successes"],
        "validation_fill": validation["summary"]["fill_ratio"]["mean"], "wall_s": report["training_wall_s"]}), flush=True)
    return record


def search(root, plan):
    records, rows = [], []
    count = plan["evaluation_cases_per_family"]
    for candidate in plan["candidates"]:
        current = []
        for seed in plan["training_seeds"]:
            config = configuration(candidate, seed, plan["search_samples_per_run"], plan["search_wall_s_per_run"])
            result = training_run(root, candidate, seed, config, f"search-{candidate['id']}-{seed}", count)
            current.append(result);records.append(result)
        rows.append({"candidate": candidate,
            "validation_success_rate": float(np.mean([r["validation"]["success_rate"] for r in current])),
            "validation_delivered_kg": float(np.mean([r["validation"]["delivered_kg"]["mean"] for r in current])),
            "validation_fill_ratio": float(np.mean([r["validation"]["fill_ratio"]["mean"] for r in current])),
            "validation_collisions": float(np.mean([r["validation"]["collision_count"]["mean"] for r in current])),
            "median_training_wall_s": float(np.median([r["training_wall_s"] for r in current])),
            "success_spread_across_training_seeds": [r["validation"]["success_rate"] for r in current]})
    ranked = rank_candidates(rows)
    result = {"selection_rule": plan["selection"], "selected": ranked[0]["candidate"],
              "ranking": ranked, "runs": records, "test_used_for_selection": False}
    write_json(root/"selection.json", result)
    return result


def full_and_ablations(root, plan, selected):
    results = {"full": [], "ablations": []}
    for seed in plan["training_seeds"]:
        config = configuration(selected, seed, plan["full_samples_per_run"], plan["full_wall_s_per_run"])
        results["full"].append(training_run(root, selected, seed, config, f"full-{seed}", plan["evaluation_cases_per_family"]))
    for ablation in plan["ablations"]:
        for seed in plan["training_seeds"]:
            config = configuration(selected, seed, plan["search_samples_per_run"], plan["search_wall_s_per_run"], ablation)
            results["ablations"].append(training_run(root, selected, seed, config, f"{ablation}-{seed}", plan["evaluation_cases_per_family"]))
    write_json(root/"full-and-ablations.json", results)
    return results


def export_policy(source, target):
    state = checkpoints.load(source)
    keys = ("configuration", "configuration_sha256", "source", "actor_critic", "counters", "software")
    exported = {k: state[k] for k in keys}
    exported.update(artefact_kind="policy-only", source_checkpoint_sha256=checkpoints.sha256(source))
    return checkpoints.save(target, exported)


def evaluations(root, plan, selected, training):
    records, robustness, replay = [], [], []
    count = plan["evaluation_cases_per_family"]
    # Selection has already been committed to an immutable report. No training follows these tests.
    for name in plan["test_families"]:
        records.append(evaluate_controller(kind="reference", split="test", count=count, family_name=name))
    for result in training["full"]:
        seed = result["seed"]
        report = json.loads((root/"runs"/f"full-{seed}"/"run.json").read_text())
        earliest = min(report["checkpoints"], key=lambda c: c["rollout"])
        latest = final_checkpoint(report)
        for label, ckpt in (("untrained", earliest), ("policy", latest)):
            exported = root/"policies"/f"{label}-{seed}.pt"
            export_policy(ckpt["path"], exported)
            policy, identity = load_policy(exported)
            for name in plan["test_families"]:
                records.append(evaluate_controller(policy, kind=label, split="test", count=count, family_name=name, identity=identity))
            if label == "policy":
                for perturbation in plan["robustness"]:
                    robustness.append(evaluate_controller(policy, split="test", count=count, perturbation=perturbation, identity=identity))
        if seed == plan["replay_seed"]:
            for label, ckpt in milestones(report):
                exported = root/"policies"/f"replay-{label}-{seed}.pt"
                export_policy(ckpt["path"], exported)
                policy, identity = load_policy(exported)
                episode = evaluate_controller(policy, split="validation", count=count, identity=identity, record=True)
                traces = episode.pop("representative_traces")
                replay.append({"label": label, "rollout": ckpt["rollout"], "evaluation": episode,
                               "traces": traces, "selection_rule": plan["replay_selection"]})
        print(json.dumps({"event": "evaluated", "training_seed": seed, "test_families": len(plan["test_families"]),
                          "robustness_families": len(plan["robustness"])}), flush=True)
    write_json(root/"comparison.json", {"records": records,
        "uncertainty_note": "Wilson intervals are per fixed policy on four independent scene streams. Across-training-seed spread is descriptive; repeated scenes are not additional independent reliability samples."})
    write_json(root/"robustness.json", {"records": robustness, "selection_frozen_before_test": True})
    with gzip.GzipFile(filename=str(root/"checkpoint-replay.json.gz"), mode="wb", mtime=0) as stream:
        stream.write(canonical_json({"source_mode": "recorded_synthetic", "replays": replay}).encode())
    write_json(root/"replay-summary.json", [{"label": r["label"], "rollout": r["rollout"],
        "identity": r["evaluation"]["identity"], "summary": r["evaluation"]["summary"],
        "selected_outcomes": list(r["traces"]), "selection_rule": r["selection_rule"]} for r in replay])
    write_json(root/"adversarial.json", run_suite())
    return records


def run(plan_path, output):
    plan = json.loads(Path(plan_path).read_text())
    source = source_identity()
    if source["training_dirty"]:
        raise ValueError("freeze and commit training sources before the study")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    write_json(output/"plan.json", plan)
    write_json(output/"manifest.json", {"source": source, "plan_sha256": hashlib.sha256(canonical_json(plan).encode()).hexdigest(),
        "started_at_utc": datetime.now(timezone.utc).isoformat(), "maximum_training_runs": plan["maximum_training_runs"],
        "maximum_training_loop_seconds": plan["maximum_training_loop_seconds"]})
    selection = search(output, plan)
    full = full_and_ablations(output, plan, selection["selected"])
    evaluations(output, plan, selection["selected"], full)
    total = selection["runs"]+full["full"]+full["ablations"]
    write_json(output/"completed.json", {"source_mode": "recorded_synthetic", "selected": selection["selected"],
        "training_runs": len(total), "environment_steps": sum(r["counters"]["environment_steps"] for r in total),
        "completed_episodes": sum(r["counters"]["completed_episodes"] for r in total),
        "full_task_training_successes": sum(r["counters"]["successes"] for r in total),
        "subtask_successes": sum(r["counters"]["subtask_successes"] for r in total),
        "training_wall_s": sum(r["training_wall_s"] for r in total),
        "optimiser_updates": sum(r["counters"]["optimiser_updates"] for r in total)})
    print(json.dumps({"event": "complete", "output": str(output)}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.plan, args.output)


if __name__ == "__main__":
    main()
