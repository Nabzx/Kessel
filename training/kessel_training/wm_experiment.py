"""Predeclared world-model data, error, uncertainty and critic-assistance study."""

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
from .contracts import canonical_json
from .environment import SceneConfig
from .evaluation import evaluate_controller, load_policy
from .evaluate import source_identity
from .imagination import imagine, observation_from_flat
from .model_assisted import ModelAssistedTrainer
from .policy import configure_cpu
from .study import export_policy, final_checkpoint
from .train import Trainer, TrainConfig
from .wm_data import collect_split, assert_disjoint, save_partition, load_partition
from .wm_evaluate import calibrate, gate_report, metrics, open_loop, simple_prediction
from .wm_export import export_examples, verify_residuals
from .wm_plots import figures
from .world_model import ModelConfig, fit, load_model, save_model

DEFAULT_PLAN = Path(__file__).parent.parent/"experiments/world-model-study-v1.json"


def write(path, value):
    path = Path(path)
    if path.exists():raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+"\n")


def collection_budgets(total, fractions):
    budgets = {name: int(total*fraction) for name, fraction in fractions.items()}
    if sum(budgets.values()) != total or min(budgets.values()) < 1:
        raise ValueError("collection fractions do not yield the declared transition budget")
    return budgets


def policy_configuration(plan, seed, assisted):
    rows = plan["assisted_on_policy_samples"] if assisted else plan["model_free_on_policy_samples"]
    batch = plan["policy_environments"]*plan["policy_rollout"]
    if rows % batch or (rows+(plan["assisted_offline_training_validation_samples"] if assisted else 0)) != plan["total_reference_sample_budget_per_policy"]:
        raise ValueError("model-assisted and model-free reference budgets differ")
    return TrainConfig(seed=seed, hidden=plan["policy_hidden"], num_envs=plan["policy_environments"],
        rollout_steps=plan["policy_rollout"], updates=rows//batch, checkpoint_every=20,
        max_wall_s=plan["policy_wall_cap_s"], scene=SceneConfig(randomise=True))


def compare_policies(root, plan, model_path, gate, shared_costs):
    model_payload = checkpoints.load(model_path);model_hash = checkpoints.sha256(model_path)
    records, learning_curves, comparisons = [], [], []
    for assisted in (False, True):
        method = "model_assisted_critic" if assisted else "model_free"
        for seed in plan["policy_seeds"]:
            config = policy_configuration(plan, seed, assisted)
            setup_started = time.perf_counter()
            trainer = ModelAssistedTrainer(config, model_payload, model_hash, gate) if assisted else Trainer(config)
            setup_s = time.perf_counter()-setup_started
            report = trainer.run(root/"policy-runs"/f"{method}-{seed}")
            final = final_checkpoint(report)
            exported = root/"policies"/f"{method}-{seed}.pt";export_policy(final["path"], exported)
            policy, identity = load_policy(exported)
            offline = plan["assisted_offline_training_validation_samples"] if assisted else 0
            record = {"method": method, "seed": seed, "configuration": asdict(config),
                "configuration_sha256": config.digest(), "source": report["source"],
                "counters": report["counters"], "stop_reason": report["stop_reason"],
                "policy_reference_steps": report["counters"]["environment_steps"], "offline_reference_steps_charged": offline,
                "total_reference_steps_charged": report["counters"]["environment_steps"]+offline,
                "policy_training_wall_s": report["training_wall_s"],
                "policy_setup_wall_s": setup_s,
                "standalone_training_wall_s": setup_s+report["training_wall_s"]+(sum(shared_costs.values()) if assisted else 0),
                "shared_pretraining_costs": shared_costs if assisted else {},
                "policy_identity": identity, "learning_curve": report["learning_curve"], "episodes": report["episodes"]}
            records.append(record)
            # Complete-task validation curves at matched total real-sample costs.
            for ckpt in report["checkpoints"]:
                charged = ckpt["rollout"]*config.num_envs*config.rollout_steps+offline
                if charged not in (10240, 20480, 30720, 40960):continue
                if any(r["method"] == method and r["seed"] == seed and r["charged_reference_steps"] == charged for r in learning_curves):continue
                p, ident = load_policy(ckpt["path"])
                result = evaluate_controller(p, split="validation", count=plan["policy_evaluation_cases"], identity=ident)
                learning_curves.append({"method": method, "seed": seed, "charged_reference_steps": charged, "evaluation": result})
            # No policy/model/gate changes follow held-out evaluation.
            for family in plan["policy_evaluation_families"]:
                result = evaluate_controller(policy, split="test", count=plan["policy_evaluation_cases"], family_name=family, identity=identity)
                comparisons.append({"method": method, "seed": seed, "evaluation": result})
            print(json.dumps({"event": "policy_comparison", "method": method, "seed": seed,
                "real_policy_steps": record["policy_reference_steps"], "total_real_steps_charged": record["total_reference_steps_charged"],
                "imagined_steps": report["counters"]["imagined_transitions"], "auxiliary_updates": report["counters"].get("auxiliary_updates", 0),
                "policy_wall_s": report["training_wall_s"]}), flush=True)
    for family in plan["policy_evaluation_families"]:
        comparisons.append({"method": "reference", "seed": None,
            "evaluation": evaluate_controller(kind="reference", split="test", count=plan["policy_evaluation_cases"], family_name=family)})
    return {"runs": records, "matched_budget_validation": learning_curves, "test_comparisons": comparisons,
        "comparison_scope": "equal standalone total reference samples; offline corpus charged to assisted arm, fewer on-policy interactions; not an isolated auxiliary-loss ablation",
        "shared_cost_note": "Offline corpus/model/gate costs are charged per standalone assisted run and also reported as one-time shared costs; the actual corpus was collected once."}


def run(plan_path, output):
    plan = json.loads(Path(plan_path).read_text());root = Path(output)
    source = source_identity()
    if source["training_dirty"]:raise ValueError("commit the training source before the study")
    root.mkdir(parents=True, exist_ok=False)
    write(root/"plan.json", plan)
    write(root/"manifest.json", {"source": source, "plan_sha256": hashlib.sha256(canonical_json(plan).encode()).hexdigest(),
        "started_at_utc": datetime.now(timezone.utc).isoformat(), "hardware": {"device": "cpu", "torch_threads": 1}})
    started = time.perf_counter();partitions = {};manifests = {};collection_costs = {}
    for split, total in plan["splits"].items():
        t = time.perf_counter()
        arrays, episodes = collect_split(split, collection_budgets(total, plan["source_fractions"]))
        partitions[split] = arrays;manifests[split] = save_partition(root/"datasets", split, arrays, episodes)
        collection_costs[split] = time.perf_counter()-t
        print(json.dumps({"event": "collected", "split": split, "rows": total, "regimes": manifests[split]["regime_counts"]}), flush=True)
    for index, name in enumerate(plan["ood_families"]):
        t = time.perf_counter();arrays, episodes = collect_split("test", collection_budgets(plan["ood_transitions_per_family"], plan["source_fractions"]), ood=name, seed_offset=3000+index*100)
        partitions[name] = arrays;manifests[name] = save_partition(root/"datasets", name, arrays, episodes)
        collection_costs[name] = time.perf_counter()-t
    assert_disjoint([(partitions[k], m["episodes"]) for k, m in manifests.items()])
    write(root/"datasets.json", {"manifests": manifests, "collection_wall_s": collection_costs,
        "total_reference_transitions": sum(len(p["reward"]) for p in partitions.values()),
        "split_check": "episode seeds and initial pile hashes disjoint across every partition"})
    models, fits, identities = {}, {}, {}
    for name, seeds in (("single", (plan["single_model_seed"],)), ("ensemble", tuple(plan["ensemble_seeds"]))):
        config = ModelConfig(members=len(seeds), hidden=plan["model_hidden"], epochs=plan["model_epochs"],
            batch_size=plan["model_batch"], learning_rate=plan["model_learning_rate"], seeds=seeds)
        model, report = fit(partitions["train"], partitions["validation"], manifests["train"], config)
        path = root/"models"/(name+".pt");save_model(path, model, report)
        models[name], identities[name] = load_model(path);fits[name] = report
        write(root/(name+"-training.json"), report)
        print(json.dumps({"event": "fitted", "model": name, "selected_epoch": report["selected_epoch"],
                          "wall_s": report["training_wall_s"], "updates": report["optimiser_updates"]}), flush=True)
    model = models["ensemble"]
    t = time.perf_counter();gate = calibrate(model, partitions["validation"], manifests["validation"]["episodes"])
    gate_cost = time.perf_counter()-t;write(root/"gate.json", gate)
    reports = {};drift = {};exports = {}
    diagnostic_policy, _ = load_policy(Path(__file__).resolve().parents[2]/"docs/phase-11/rl-evidence/policies/policy-7.pt")
    for name in ("validation", "test", *plan["ood_families"]):
        arrays = partitions[name];pred = model.predict(arrays["state"], arrays["action"])
        baselines = {key: metrics(simple_prediction(arrays["state"], arrays["action"], key), arrays) for key in ("persistence", "kinematic")}
        baselines.update(single=metrics(models["single"].predict(arrays["state"], arrays["action"]), arrays), ensemble=metrics(pred, arrays))
        ids = np.linspace(0, len(arrays["reward"])-1, min(128, len(arrays["reward"])), dtype=int)
        features = diagnostic_policy.encode(observation_from_flat(arrays["observation"][ids]))
        generator = torch.Generator(device="cpu").manual_seed(7301)
        _, _, branch_stats = imagine(model, diagnostic_policy, arrays["state"][ids], features, gate, generator)
        branch_stats["usage"] = "held-out diagnostic only; no optimisation or data feedback"
        reports[name] = {"prediction_metrics": baselines, "uncertainty_audit": gate_report(model, arrays, gate), "imagined_branch_audit": branch_stats}
        drift[name] = open_loop(model, arrays, manifests[name]["episodes"], tuple(plan["diagnostic_horizons"]))
        if name in ("test", "contact_start", "blocked"):
            exports[name] = export_examples(model, identities["ensemble"], arrays, manifests[name])
            verify_residuals(exports[name])
    write(root/"prediction-metrics.json", reports);write(root/"drift.json", drift);write(root/"predictions.json", exports)
    figures(root/"figures", model, partitions["validation"], partitions["test"], gate,
            {k: drift[k] for k in ("test", "high_resistance", "unusual_pile")})
    print(json.dumps({"event": "calibrated", "threshold": gate["threshold"], "supported_horizon": gate["supported_horizon"]}), flush=True)
    shared_costs = {"training_validation_collection_s": collection_costs["train"]+collection_costs["validation"],
                    "ensemble_training_s": fits["ensemble"]["training_wall_s"], "gate_calibration_s": gate_cost}
    comparison = compare_policies(root, plan, root/"models/ensemble.pt", gate, shared_costs)
    write(root/"policy-comparison.json", comparison)
    write(root/"completed.json", {"source_mode": "recorded_synthetic", "source": source,
        "dataset_reference_transitions": sum(len(p["reward"]) for p in partitions.values()),
        "policy_reference_transitions": sum(r["policy_reference_steps"] for r in comparison["runs"]),
        "accepted_imagined_transitions": sum(r["counters"]["imagined_transitions"] for r in comparison["runs"]),
        "proposed_model_transitions": sum(r["counters"].get("proposed_model_transitions", 0) for r in comparison["runs"]),
        "auxiliary_critic_updates": sum(r["counters"].get("auxiliary_updates", 0) for r in comparison["runs"]),
        "model_optimiser_updates": sum(r["optimiser_updates"] for r in fits.values()),
        "experiment_wall_s": time.perf_counter()-started,
        "shared_pretraining_costs": shared_costs, "collection_costs": collection_costs,
        "training_models_wall_s": sum(r["training_wall_s"] for r in fits.values()),
        "policy_training_wall_s": sum(r["policy_training_wall_s"] for r in comparison["runs"])})
    print(json.dumps({"event": "complete", "output": str(root)}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN);parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args();run(args.plan, args.output)


if __name__ == "__main__":main()
