"""Short learned branches with independent uncertainty and physical guards."""

import numpy as np
import torch

from .kinematics import footprints
from .wm_state import INDEX, PILE_START, PILE_END, model_observation, violations


def admissibility(current, predicted, rewards):
    """Report raw failures; do not repair learned predictions by clipping."""
    raw = violations(predicted)
    reasons = {k: v for k, v in raw.items() if k != "mass_error_kg"}
    reasons["mass_balance"] = np.abs(raw["mass_error_kg"]) > 1.0
    reasons["nonmonotone_material"] = ((predicted[:, 8:10]-current[:, 8:10]) < -1e-4).any(axis=1)
    reasons["pile_creation"] = ((predicted[:, PILE_START:PILE_END]-current[:, PILE_START:PILE_END]) > 1e-5).any(axis=1)
    delivered = np.maximum(predicted[:, 8]-current[:, 8], 0)
    reasons["unearned_reward"] = (rewards > delivered/3500+1e-4) | (rewards < -6)
    reasons["non_finite_reward"] = ~np.isfinite(rewards)
    dt = current[:, INDEX["decision_s"]]
    reasons["excess_motion"] = np.linalg.norm(predicted[:, :2]-current[:, :2], axis=1) > 2*dt+0.02
    reasons["backwards_clock"] = predicted[:, 10] < current[:, 10]-1e-6
    reasons["negative_counters"] = (predicted[:, [10, 11, 12, 13]] < -1e-6).any(axis=1)
    corners = footprints(predicted[:, :3], predicted[:, 4:7])
    reasons["wall_clearance"] = ((corners[..., 0] < -11) | (corners[..., 0] > 18)
        | (np.abs(corners[..., 1]) > predicted[:, INDEX["half_width_m"], None, None])).any(axis=(1, 2))
    old_corners = footprints(current[:, :3], current[:, 4:7])
    low = np.minimum(old_corners.min(axis=2), corners.min(axis=2))
    high = np.maximum(old_corners.max(axis=2), corners.max(axis=2))
    overlap = ((low[..., 0] <= predicted[:, INDEX["obstacle_x_max_m"], None])
        & (high[..., 0] >= predicted[:, INDEX["obstacle_x_min_m"], None])
        & (low[..., 1] <= predicted[:, INDEX["obstacle_y_max_m"], None])
        & (high[..., 1] >= predicted[:, INDEX["obstacle_y_min_m"], None])).any(axis=1)
    reasons["obstacle_clearance"] = (predicted[:, INDEX["obstacle_present"]] > 0.5) & overlap
    reasons["roof_clearance"] = np.maximum(1.9, 0.95+2*np.sin(predicted[:, 5])) > predicted[:, INDEX["ceiling_m"]]+1e-3
    def mouth(state):
        yaw = state[:, 2];front_yaw = yaw+state[:, 4]
        return state[:, :2]+1.8*np.stack((np.cos(yaw), np.sin(yaw)), axis=1)+(1.6+1.2*np.cos(state[:, 5]))[:, None]*np.stack((np.cos(front_yaw), np.sin(front_yaw)), axis=1)
    old_mouth, new_mouth = mouth(current), mouth(predicted)
    gx, gy = np.meshgrid((np.arange(8)+0.5)*0.5, (np.arange(8)+0.5)*0.5, indexing="ij")
    centres = np.stack((gx.ravel(), gy.ravel()), axis=1)[None, ...]+current[:, None, [INDEX["pile_origin_x_m"], INDEX["pile_origin_y_m"]]]
    local_masks = []
    for state, position in ((current, old_mouth), (predicted, new_mouth)):
        yaw = state[:, 2]+state[:, 4];difference = centres-position[:, None, :]
        along = difference[..., 0]*np.cos(yaw[:, None])+difference[..., 1]*np.sin(yaw[:, None])
        across = -difference[..., 0]*np.sin(yaw[:, None])+difference[..., 1]*np.cos(yaw[:, None])
        local_masks.append((np.abs(along) <= 0.75) & (np.abs(across) <= 0.9))
    removed = (current[:, PILE_START:PILE_END]-predicted[:, PILE_START:PILE_END])*0.25*current[:, INDEX["density_kg_m3"], None]
    reasons["remote_extraction"] = ((removed > 0.1) & ~(local_masks[0] | local_masks[1])).any(axis=1)
    return ~np.logical_or.reduce(list(reasons.values())), reasons


def observation_from_flat(flat):
    return {"proprio": flat[:, :15], "local_height_m": flat[:, 15:40].reshape(-1, 5, 5),
            "range_valid": flat[:, 40:].reshape(-1, 5, 5)}


@torch.no_grad()
def imagine(model, policy, states, features, gate, generator, *, horizon=2, gamma=0.995):
    if horizon not in (1, 2):
        raise ValueError("prototype imagination supports at most two steps")
    n = len(states)
    stats = {"anchors": n, "accepted_branches": 0, "rejected_branches": 0,
             "imagined_transitions": 0, "accepted_horizons": {}, "rejections": {},
             "proposed_model_transitions": 0,
             "source_kind": "imagined", "reference_transitions_generated": 0}
    if gate["threshold"] is None or gate["supported_horizon"] == 0:
        stats["rejected_branches"] = n;stats["rejections"]["unsupported_validation_horizon"] = n
        return np.zeros(n), np.zeros(n, dtype=bool), stats
    limit = min(horizon, gate["supported_horizon"])
    active = np.ones(n, dtype=bool);accepted = np.zeros(n, dtype=int)
    current = states.copy();total = np.zeros(n);terminal = np.zeros(n, dtype=bool)
    for t in range(limit):
        ids = np.flatnonzero(active)
        if not len(ids):
            break
        inputs = features[ids] if t == 0 else policy.encode(model_observation(current[ids]))
        action = policy.sample(inputs, generator=generator)["action"].numpy()
        prediction = model.predict(current[ids], action)
        stats["proposed_model_transitions"] += len(ids)
        valid, reasons = admissibility(current[ids], prediction["next_state"], prediction["reward"])
        reasons["non_finite_model_scores"] = (~np.isfinite(prediction["events"]).all(axis=1)
            | ~np.isfinite(prediction["disagreement"]) | ~np.isfinite(prediction["input_envelope"]))
        if "filter_rejected" in prediction:
            reasons["bounded_filter"] = prediction["filter_rejected"]
            valid &= ~reasons["bounded_filter"]
            stats["filtered_proposals"] = stats.get("filtered_proposals", 0)+len(ids)
            stats["predictor_kind"] = prediction["predictor_kind"]
            peaks = stats.setdefault("filter_correction_maxima", {})
            for key, values in prediction["filter_correction"].items():
                peaks[key] = max(peaks.get(key, 0.0), float(np.max(values)))
        reasons["uncertainty"] = prediction["disagreement"] > gate["threshold"]
        reasons["input_envelope"] = prediction["input_envelope"] > 6
        valid &= ~reasons["uncertainty"] & ~reasons["input_envelope"] & ~reasons["non_finite_model_scores"]
        for key, flags in reasons.items():
            stats["rejections"][key] = stats["rejections"].get(key, 0)+int(flags.sum())
        active[ids[~valid]] = False
        keep = ids[valid]
        if not len(keep):
            continue
        total[keep] += gamma**t*prediction["reward"][valid]
        current[keep] = prediction["next_state"][valid]
        accepted[keep] += 1
        terminal[keep] = prediction["events"][valid, 0] >= 0.5
        truncated = prediction["events"][valid, 1] >= 0.5
        active[keep[terminal[keep] | truncated]] = False
        stats["rejections"]["predicted_terminal_stop"] = stats["rejections"].get("predicted_terminal_stop", 0)+int(terminal[keep].sum())
        stats["rejections"]["predicted_truncation_stop"] = stats["rejections"].get("predicted_truncation_stop", 0)+int(truncated.sum())
    selected = accepted > 0
    bootstrap = np.flatnonzero(selected & ~terminal)
    if len(bootstrap):
        value = policy.value(policy.encode(model_observation(current[bootstrap]))).numpy()
        total[bootstrap] += gamma**accepted[bootstrap]*value
    stats["accepted_branches"] = int(selected.sum());stats["rejected_branches"] = int((~selected).sum())
    stats["imagined_transitions"] = int(accepted.sum())
    stats["accepted_horizons"] = {str(h): int((accepted == h).sum()) for h in range(1, limit+1)}
    return total, selected, stats
