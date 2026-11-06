"""Complete-task comparisons with checkpoint execution and fixed scene identities."""

import argparse
from dataclasses import asdict, replace
import json
import math
from pathlib import Path
import time

import numpy as np
import torch

from . import checkpoints
from .controller import ReferenceController
from .environment import LoaderEnv
from .evaluate import source_identity
from .kinematics import components
from .policy import ActorCritic, configure_cpu
from .scenarios import family, scenario_seed


def load_policy(path):
    state = checkpoints.load(path)
    configure_cpu(state["configuration"]["seed"], state["configuration"]["threads"])
    policy = ActorCritic(state["configuration"]["hidden"])
    policy.load_state_dict(state["actor_critic"], strict=True)
    if not all(torch.isfinite(p).all() for p in policy.parameters()):
        raise ValueError("checkpoint policy has non-finite parameters")
    policy.eval()
    return policy, {"checkpoint_sha256": checkpoints.sha256(path), "training_source": state["source"],
                    "trainer_kind": state.get("trainer_kind", "model-free"),
                    "source_checkpoint_sha256": state.get("source_checkpoint_sha256", checkpoints.sha256(path)),
                    "training_configuration_sha256": state["configuration_sha256"],
                    "training_seed": state["configuration"]["seed"], "training_counters": state["counters"]}


def wilson(successes, count):
    if count < 1:
        raise ValueError("success interval needs at least one case")
    z = 1.959963984540054
    p = successes/count; denominator = 1+z*z/count
    centre = (p+z*z/(2*count))/denominator
    radius = z*math.sqrt(p*(1-p)/count+z*z/(4*count*count))/denominator
    return [max(0, centre-radius), min(1, centre+radius)]


def summary(cases):
    successes = sum(c["reason"] == "success" for c in cases)
    result = {"episodes": len(cases), "successes": successes, "success_rate": successes/len(cases),
              "success_wilson_95": wilson(successes, len(cases)),
              "outcomes": {reason: sum(c["reason"] == reason for c in cases) for reason in sorted({c["reason"] for c in cases})}}
    for key in ("delivered_kg", "fill_ratio", "cycle_s", "spilled_kg", "effort_proxy_j", "slip_s", "collision_count"):
        values = np.array([c[key] for c in cases], dtype=float)
        result[key] = {"mean": float(values.mean()), "std": float(values.std(ddof=1)) if len(values) > 1 else 0.0,
                       "min": float(values.min()), "max": float(values.max())}
    return result


def perturbation_spec(name):
    base, _ = family("standard")
    specs = {
        "grip_moderate": (replace(base, friction=0.12, grade_rad=0.1), None, "grip/grade", 1),
        "grip_severe": (replace(base, friction=0.06, grade_rad=0.16), None, "grip/grade", 2),
        "sensing_moderate": (replace(base, sensor_noise=2, dropout=0.4, occlusion=0.4, load_bias_fraction=0.15), None, "sensing", 1),
        "sensing_severe": (replace(base, sensor_noise=3, dropout=0.8, occlusion=0.7, load_bias_fraction=0.25), None, "sensing", 2),
        "narrow_moderate": (replace(base, half_width_m=2.0), None, "geometry", 1),
        "narrow_severe": (replace(base, half_width_m=1.2), None, "geometry", 2),
        "pile_offset": (base, (0.0, 0.8), "pile_position", 1),
        "pile_far": (base, (1.5, 0.0), "pile_position", 2),
        "large_obstacle": (replace(base, obstacles=((6., 8., -5., 5.),)), None, "obstacle", 2),
    }
    if name not in specs:
        raise ValueError("unknown robustness perturbation")
    scene, shift, group, severity = specs[name]
    return scene, shift, {"distribution": "out_of_training_distribution", "group": group, "severity": severity}


@torch.no_grad()
def evaluate_controller(policy=None, *, kind="policy", split="validation", count=4,
                        family_name="standard", perturbation=None, identity=None, record=False, scene_override=None, seed_offset=0):
    if not isinstance(count, int) or isinstance(count, bool) or not 1 <= count <= 32:
        raise ValueError("evaluation case count must be in [1,32]")
    if kind not in ("policy", "untrained", "reference") or (kind != "reference" and policy is None):
        raise ValueError("evaluation needs a valid controller")
    if not isinstance(seed_offset, int) or isinstance(seed_offset, bool) or seed_offset < 0:
        raise ValueError("evaluation seed offset must be a non-negative integer")
    started = time.perf_counter()
    scene, difficulty = family(family_name)
    shift, distribution = None, {"distribution": "held_out_nominal" if family_name == "standard" else "held_out_perturbed"}
    if perturbation:
        scene, shift, distribution = perturbation_spec(perturbation)
    if scene_override is not None:
        scene = scene_override
    env = LoaderEnv(count, seed=scenario_seed(split, seed_offset), scene=scene)
    for i in range(count):
        mask = np.zeros(count, dtype=bool); mask[i] = True
        env.reset(seed=scenario_seed(split, seed_offset+i), mask=mask)
    if shift:
        env.pile.origin += np.asarray(shift)
        env._update_observations(np.ones(count, dtype=bool), reset=True)
    scene_hashes = env.scenario_identity()
    realised = [{"friction": float(env.friction[i]), "grade_rad": float(env.grade[i]),
                 "resistance_n_m": float(env.resistance[i]), "half_width_m": float(env.half_width[i]),
                 "load_bias_kg": float(env.load_bias[i]), "density_kg_m3": float(env.pile.density[i]),
                 "initial_mass_kg": float(env.pile.initial_mass[i]), "pile_origin_xy_m": env.pile.origin[i].tolist()}
                for i in range(count)]
    initial_piles = env.pile.height.copy()
    initial_origins = env.pile.origin.copy()
    controller = ReferenceController(count) if kind == "reference" else None
    active = np.ones(count, dtype=bool)
    cases = [None]*count
    traces = [[] for _ in range(count)] if record else None
    cumulative_reward = np.zeros(count)
    for step in range(scene.max_steps):
        observation = env.observe()
        action = (controller.act(observation) if controller else
                  policy.sample(policy.encode(observation), deterministic=True)["action"].numpy())
        action[~active] = 0
        _, reward, term, trunc, info = env.step(action)
        cumulative_reward[active] += reward[active]
        if record:
            for i in np.flatnonzero(active):
                traces[i].append({"t_s": float(env.elapsed[i]), "action": action[i].tolist(),
                    "pose": env.pose[i].tolist(), "joints": env.joints[i].tolist(),
                    "wheel_angle_rad": env.wheel_angles[i].tolist(),
                    "carried_kg": float(env.payload[i]), "delivered_kg": float(env.delivered[i]),
                    "spilled_kg": float(env.spilled[i]),
                    "reward_terms": {k: float(v[i]) for k, v in info["reward_terms"].items()},
                    "removed_cell_kg": info["transfer"]["removed_cell_kg"][i].tolist() if info["transfer"]["loaded_kg"][i] else None})
        done = term | trunc
        for i in np.flatnonzero(done & active):
            metrics = {k: v[i].item() for k, v in info["metrics"].items()}
            cases[i] = {"case_index": int(i), "seed": scenario_seed(split, seed_offset+int(i)), "stream_id": int(i),
                "scenario_sha256": scene_hashes[i], "realised": realised[i], "steps": step+1, "terminated": bool(term[i]),
                "truncated": bool(trunc[i]), "raw_reward_total": float(cumulative_reward[i]),
                "collision_count": int(metrics["collision_time_s"] >= 0), **metrics}
            active[i] = False
        if not active.any():
            break
        if done.any():
            env.reset(mask=done)
    if active.any():
        raise RuntimeError("evaluation did not reach its declared episode boundary")
    selected = {}
    if record:
        for i, case in enumerate(cases):
            result = "success" if case["reason"] == "success" else "failure"
            if result not in selected:
                selected[result] = {"case": case, "initial_pile_height_m": initial_piles[i].tolist(),
                    "pile_origin_xy_m": initial_origins[i].tolist(), "frames": traces[i],
                    "final_record": {"t_s": traces[i][-1]["t_s"], "action": None}}
    return {"schema_version": "1.0", "source_mode": "recorded_synthetic", "calibrated": False,
        "controller_kind": kind, "identity": identity, "source": source_identity(),
        "split": split, "family": family_name, "difficulty": difficulty,
        "perturbation": perturbation, "distribution": distribution, "scene": asdict(scene),
        "case_protocol": "One complete episode per seed/index; identical seed and stream id for all controllers. Finished dummy slots are not counted.",
        "summary": summary(cases), "cases": cases, "wall_s": time.perf_counter()-started,
        "representative_traces": selected}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--reference", action="store_true")
    parser.add_argument("--split", choices=("train", "validation", "test"), default="validation")
    parser.add_argument("--count", type=int, default=4)
    parser.add_argument("--family", choices=("standard", "low_grip", "occluded", "blocked"), default="standard")
    parser.add_argument("--record", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if bool(args.checkpoint) == args.reference or args.output.exists():
        parser.error("select exactly one controller and a new output path")
    policy, identity = (None, None) if args.reference else load_policy(args.checkpoint)
    report = evaluate_controller(policy, kind="reference" if args.reference else "policy",
        split=args.split, count=args.count, family_name=args.family, identity=identity, record=args.record)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False)+"\n")
    print(json.dumps({"output": str(args.output), **report["summary"]}))


if __name__ == "__main__":
    main()
