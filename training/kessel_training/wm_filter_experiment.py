"""Predeclared bounded-filter follow-up, retaining the raw study and controls."""

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import torch

from . import checkpoints
from .constrained_model import ConstrainedModel, FilterConfig
from .contracts import canonical_json
from .evaluate import source_identity
from .evaluation import evaluate_controller, load_policy
from .imagination import imagine, observation_from_flat
from .model_assisted import ModelAssistedTrainer
from .study import export_policy, final_checkpoint
from .wm_data import assert_disjoint, collect_split, load_partition, save_partition
from .wm_evaluate import calibrate, gate_report, metrics, open_loop, simple_prediction
from .wm_experiment import collection_budgets, policy_configuration, write
from .wm_export import export_examples, verify_residuals
from .wm_plots import figures
from .world_model import load_model

DEFAULT_PLAN = Path(__file__).parent.parent/"experiments/world-model-filter-study-v1.json"


def run(source, output, plan_path=DEFAULT_PLAN):
    source, root = Path(source), Path(output)
    plan = json.loads(Path(plan_path).read_text());base_plan = json.loads((source/"plan.json").read_text())
    config = FilterConfig(**plan["filter"])
    if plan["additional_on_policy_samples_per_seed"] != base_plan["assisted_on_policy_samples"] or plan["offline_samples_charged_per_seed"] != base_plan["assisted_offline_training_validation_samples"]:
        raise ValueError("follow-up and original comparison budgets differ")
    identity = source_identity()
    if identity["training_dirty"]:raise ValueError("commit training source before the study")
    root.mkdir(parents=True, exist_ok=False);started = time.perf_counter()
    write(root/"plan.json", plan)
    model_path = source/"models/ensemble.pt";model, model_identity = load_model(model_path)
    filtered = ConstrainedModel(model, config)
    write(root/"manifest.json", {"source": identity, "plan_sha256": hashlib.sha256(canonical_json(plan).encode()).hexdigest(),
        "started_at_utc": datetime.now(timezone.utc).isoformat(), "model_identity": model_identity,
        "filter_sha256": config.digest(), "base_study_manifest": json.loads((source/"manifest.json").read_text())})
    train, train_manifest = load_partition(source/"datasets", "train")
    validation, vm = load_partition(source/"datasets", "validation")
    gate_start = time.perf_counter();gate = calibrate(filtered, validation, vm["episodes"])
    gate_cost = time.perf_counter()-gate_start;write(root/"gate.json", gate)
    # This is the only selection. Held-out outcomes below cannot change limits or gate.
    arrays, episodes = collect_split("test", collection_budgets(plan["fresh_test_rows"], base_plan["source_fractions"]),
        seed_offset=plan["fresh_test_seed_offset"], source_stride=plan["fresh_test_source_stride"])
    partitions = {"test": arrays};manifests = {"test": save_partition(root/"datasets", "test", arrays, episodes)}
    for index, name in enumerate(base_plan["ood_families"]):
        arrays, episodes = collect_split("test", collection_budgets(plan["fresh_ood_rows_per_family"], base_plan["source_fractions"]),
            ood=name, seed_offset=plan["fresh_ood_seed_offset"]+index*plan["fresh_ood_family_stride"], source_stride=plan["fresh_ood_source_stride"])
        partitions[name] = arrays;manifests[name] = save_partition(root/"datasets", name, arrays, episodes)
    assert_disjoint([(train, train_manifest["episodes"]), (validation, vm["episodes"]),
        *[(partitions[k], m["episodes"]) for k, m in manifests.items()]])
    # The inspected first test/OOD corpus is also excluded from fresh partitions.
    old_manifests = json.loads((source/"datasets.json").read_text())["manifests"]
    old_seeds = {e["seed"] for m in old_manifests.values() for e in m["episodes"]}
    old_piles = {e["initial_pile_sha256"] for m in old_manifests.values() for e in m["episodes"]}
    for m in manifests.values():
        if any(e["seed"] in old_seeds or e["initial_pile_sha256"] in old_piles for e in m["episodes"]):
            raise ValueError("fresh held-out data overlaps the first study")
    write(root/"datasets.json", {"manifests": manifests, "immutable_training_sha256": train_manifest["logical_sha256"],
        "immutable_validation_sha256": vm["logical_sha256"], "fresh_and_disjoint_from_first_study": True})
    partitions["validation"] = validation;manifests["validation"] = vm
    diagnostic, _ = load_policy(source/"policies/model_free-7.pt")
    reports, drift, exports = {}, {}, {}
    export_identity = {**model_identity, "predictor_kind": "neural_with_explicit_bounded_filter", "filter": asdict(config), "filter_sha256": config.digest()}
    for name, data in partitions.items():
        pred = filtered.predict(data["state"], data["action"])
        ids = np.linspace(0, len(data["reward"])-1, 128, dtype=int)
        _, _, branches = imagine(filtered, diagnostic, data["state"][ids], diagnostic.encode(observation_from_flat(data["observation"][ids])),
            gate, torch.Generator(device="cpu").manual_seed(7301))
        branches["usage"] = "diagnostic only; no optimisation or held-out feedback"
        reports[name] = {"prediction_metrics": {
            "raw_ensemble": metrics(model.predict(data["state"], data["action"]), data),
            "bounded_hybrid": metrics(pred, data),
            "kinematic": metrics(simple_prediction(data["state"], data["action"], "kinematic"), data)},
            "uncertainty_audit": gate_report(filtered, data, gate), "imagined_branch_audit": branches,
            "filter": {"rejected_rows": int(pred["filter_rejected"].sum()),
                "correction_maxima": {k: float(v.max()) for k, v in pred["filter_correction"].items()},
                "correction_means": {k: float(v.mean()) for k, v in pred["filter_correction"].items()}}}
        drift[name] = open_loop(filtered, data, manifests[name]["episodes"])
        if name in ("test", "contact_start", "blocked"):
            exports[name] = export_examples(filtered, export_identity, data, manifests[name]);verify_residuals(exports[name])
    write(root/"prediction-metrics.json", reports);write(root/"drift.json", drift);write(root/"predictions.json", exports)
    figures(root/"figures", filtered, validation, partitions["test"], gate, {k: drift[k] for k in ("test", "high_resistance", "unusual_pile")})
    runs, comparisons, curves = [], [], []
    payload = checkpoints.load(model_path);model_hash = checkpoints.sha256(model_path)
    original_costs = json.loads((source/"completed.json").read_text())["shared_pretraining_costs"]
    for seed in plan["additional_policy_seeds"]:
        train_config = policy_configuration(base_plan, seed, True)
        setup_start = time.perf_counter();trainer = ModelAssistedTrainer(train_config, payload, model_hash, gate, plan["filter"])
        setup_s = time.perf_counter()-setup_start
        report = trainer.run(root/"policy-runs"/f"bounded_assisted_critic-{seed}")
        path = root/"policies"/f"bounded_assisted_critic-{seed}.pt"
        export_policy(final_checkpoint(report)["path"], path)
        runs.append({"method": "bounded_assisted_critic", "seed": seed, "configuration": asdict(train_config),
            "configuration_sha256": train_config.digest(), "source": report["source"], "counters": report["counters"],
            "stop_reason": report["stop_reason"], "policy_reference_steps": report["counters"]["environment_steps"],
            "offline_reference_steps_charged": plan["offline_samples_charged_per_seed"],
            "total_reference_steps_charged": report["counters"]["environment_steps"]+plan["offline_samples_charged_per_seed"],
            "policy_training_wall_s": report["training_wall_s"], "policy_setup_wall_s": setup_s,
            "shared_pretraining_costs": {**original_costs, "filtered_gate_calibration_s": gate_cost},
            "learning_curve": report["learning_curve"], "episodes": report["episodes"]})
        for ckpt in report["checkpoints"]:
            charged = ckpt["rollout"]*train_config.num_envs*train_config.rollout_steps+plan["offline_samples_charged_per_seed"]
            if charged not in (20480, 30720, 40960):continue
            if any(r["seed"] == seed and r["charged_reference_steps"] == charged for r in curves):continue
            p, ident = load_policy(ckpt["path"])
            curves.append({"method": "bounded_assisted_critic", "seed": seed, "charged_reference_steps": charged,
                "evaluation": evaluate_controller(p, split="validation", count=4, identity=ident)})
        print(json.dumps({"event": "bounded_policy", "seed": seed, "counters": report["counters"]}), flush=True)
    for method in ("model_free", "model_assisted_critic", "bounded_assisted_critic"):
        for seed in base_plan["policy_seeds"]:
            path = (root if method == "bounded_assisted_critic" else source)/"policies"/f"{method}-{seed}.pt"
            policy, ident = load_policy(path)
            for name in base_plan["policy_evaluation_families"]:
                comparisons.append({"method": method, "seed": seed, "evaluation": evaluate_controller(policy, split="test", count=4,
                    family_name=name, identity=ident, seed_offset=plan["fresh_policy_test_seed_offset"])})
    for name in base_plan["policy_evaluation_families"]:
        comparisons.append({"method": "reference", "seed": None, "evaluation": evaluate_controller(kind="reference", split="test", count=4,
            family_name=name, seed_offset=plan["fresh_policy_test_seed_offset"])})
    write(root/"policy-comparison.json", {"runs": runs, "matched_budget_validation": curves, "test_comparisons": comparisons,
        "control_costs_and_weights": "unchanged first-study final policies; original full costs retained there",
        "comparison_scope": "equal total reference budgets, shared offline corpus charged per assisted arm; not an isolated auxiliary-loss ablation"})
    write(root/"completed.json", {"source_mode": "recorded_synthetic", "source": identity, "model_refits": 0,
        "additional_dataset_reference_transitions": sum(len(partitions[k]["reward"]) for k in partitions if k != "validation"),
        "additional_policy_reference_transitions": sum(r["policy_reference_steps"] for r in runs),
        "accepted_imagined_transitions": sum(r["counters"]["imagined_transitions"] for r in runs),
        "auxiliary_critic_updates": sum(r["counters"]["auxiliary_updates"] for r in runs),
        "experiment_wall_s": time.perf_counter()-started, "filtered_gate_calibration_s": gate_cost})
    print(json.dumps({"event": "complete", "output": str(root)}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True);parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    args = parser.parse_args();run(args.source, args.output, args.plan)


if __name__ == "__main__":main()
