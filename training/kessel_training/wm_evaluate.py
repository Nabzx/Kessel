"""Prediction errors, open-loop drift and validation-only uncertainty gates."""

import numpy as np

from .wm_state import DYNAMIC_NAMES, INDEX, PILE_START, PILE_END, decode, violations


def simple_prediction(states, actions, kind):
    if kind not in ("persistence", "kinematic"):
        raise ValueError("unknown simple prediction baseline")
    out = states.copy();dt = states[:, INDEX["decision_s"]]
    events = np.zeros((len(states), 4))
    if kind == "kinematic":
        speed = np.clip(states[:, 3]+actions[:, 0]*1.5*dt, -1.5, 2)
        out[:, 0] += 0.5*(states[:, 3]+speed)*np.cos(states[:, 2])*dt
        out[:, 1] += 0.5*(states[:, 3]+speed)*np.sin(states[:, 2])*dt
        out[:, 3] = speed
        for i, rate, low, high in ((4, 0.35, -0.6, 0.6), (5, 0.25, -0.1, 1.1), (6, 0.5, -0.7, 1.0)):
            out[:, i] = np.clip(states[:, i]+actions[:, i-3]*rate*dt, low, high)
    out[:, 10] += dt
    out[:, INDEX["step_index"]] += 1
    events[:, 1] = out[:, INDEX["step_index"]] >= out[:, INDEX["max_steps"]]
    return {"next_state": out, "reward": -0.002*dt if kind == "kinematic" else np.zeros(len(states)),
            "events": events, "disagreement": np.zeros(len(states)), "input_envelope": np.zeros(len(states))}


def errors(prediction, targets, rewards, events):
    delta = prediction["next_state"]-targets
    delta[:, 2] = (delta[:, 2]+np.pi) % (2*np.pi)-np.pi
    position = np.linalg.norm(delta[:, :2], axis=1)
    pile = np.abs(delta[:, PILE_START:PILE_END]).mean(axis=1)
    reward = np.abs(prediction["reward"]-rewards)
    terminal_wrong = (prediction["events"][:, 0] >= 0.5) != events[:, 0]
    high_error = (position > 0.05) | (np.abs(delta[:, 7]) > 50) | (pile > 0.01) | (reward > 0.05) | terminal_wrong
    return {"delta": delta, "position_m": position, "pile_mae_m": pile,
            "reward_abs": reward, "high_error": high_error}


def event_scores(probability, labels):
    selected = probability >= 0.5;truth = labels.astype(bool)
    tp = int((selected & truth).sum());fp = int((selected & ~truth).sum());fn = int((~selected & truth).sum())
    return {"positives": int(truth.sum()), "brier": float(np.mean((probability-truth)**2)),
            "precision_at_half": tp/(tp+fp) if tp+fp else None,
            "recall_at_half": tp/(tp+fn) if tp+fn else None,
            "false_positives": fp, "false_negatives": fn}


def metrics(prediction, data):
    e = errors(prediction, data["next_state"], data["reward"], data["events"])
    raw = violations(prediction["next_state"])
    result = {"rows": len(data["reward"]), "position_mae_m": float(e["position_m"].mean()),
        "position_p95_m": float(np.quantile(e["position_m"], 0.95)),
        "state_mae": {name: float(np.abs(e["delta"][:, i]).mean()) for i, name in enumerate(DYNAMIC_NAMES)},
        "pile_height_mae_m": float(e["pile_mae_m"].mean()), "reward_mae": float(e["reward_abs"].mean()),
        "high_error_fraction": float(e["high_error"].mean()),
        "mass_balance_mae_kg": float(np.abs(raw["mass_error_kg"]).mean()),
        "mass_balance_max_kg": float(np.abs(raw["mass_error_kg"]).max()),
        "raw_violations": {k: int(v.sum()) for k, v in raw.items() if k != "mass_error_kg"},
        "events": {name: event_scores(prediction["events"][:, i], data["events"][:, i])
                   for i, name in enumerate(("terminated", "truncated", "contact", "collision"))}}
    result["regimes"] = {}
    for value, name in enumerate(("empty_motion", "contact_without_transfer", "material_transfer", "collision_or_stuck")):
        selected = data["regime"] == value
        if selected.any():
            result["regimes"][name] = {"rows": int(selected.sum()), "position_mae_m": float(e["position_m"][selected].mean()),
                "pile_height_mae_m": float(e["pile_mae_m"][selected].mean()),
                "carried_mass_mae_kg": float(np.abs(e["delta"][selected, 7]).mean()),
                "delivered_mass_mae_kg": float(np.abs(e["delta"][selected, 8]).mean()),
                "spilled_mass_mae_kg": float(np.abs(e["delta"][selected, 9]).mean()),
                "reward_mae": float(e["reward_abs"][selected].mean())}
    return result


def open_loop(model, arrays, episodes, horizons=(1, 2, 4, 8), max_windows=256):
    # Stratify within episodes so material/failure windows are not lost in an
    # arbitrary chronological prefix. This selection does not train the model.
    starts = []
    for episode in episodes:
        available = episode["stop"]-episode["start"]
        starts.extend(range(episode["start"], episode["stop"], max(1, available//12)))
    if len(starts) > max_windows:
        starts = [starts[i] for i in np.linspace(0, len(starts)-1, max_windows, dtype=int)]
    reports = []
    common = [i for i in starts if i+max(horizons) <= episodes[int(arrays["episode_id"][i])]["stop"]]
    for horizon in horizons:
        valid = common
        if not valid:
            reports.append({"horizon_decisions": horizon, "rows": 0, "missing": "no reference window"});continue
        valid = np.asarray(valid)
        current = arrays["state"][valid].copy()
        total_reward = np.zeros(len(valid));prob = np.zeros((len(valid), 4))
        for t in range(horizon):
            prediction = model.predict(current, arrays["action"][valid+t])
            current = prediction["next_state"];total_reward += prediction["reward"]
            prob = 1-(1-prob)*(1-prediction["events"])
        reward = sum(arrays["reward"][valid+t] for t in range(horizon))
        target_events = np.stack([arrays["events"][valid+t] for t in range(horizon)]).any(axis=0)
        target = {"next_state": arrays["next_state"][valid+horizon-1], "reward": reward,
                  "events": target_events, "regime": arrays["regime"][valid]}
        result = metrics({"next_state": current, "reward": total_reward, "events": prob}, target)
        result.update(horizon_decisions=horizon, nominal_horizon_s=horizon*0.1,
                      reference_elapsed_mean_s=float(np.mean(target["next_state"][:, 10]-arrays["state"][valid, 10])),
                      diagnostic_mode="fixed recorded actions; do not stop on predicted events; never cross reference boundaries")
        reports.append(result)
    return reports


def calibrate(model, validation, episodes):
    prediction = model.predict(validation["state"], validation["action"])
    e = errors(prediction, validation["next_state"], validation["reward"], validation["events"])
    score = prediction["disagreement"]
    tradeoffs = []
    for percentile in (10, 25, 50, 75, 90, 100):
        threshold = float(np.percentile(score, percentile));accepted = score <= threshold
        tradeoffs.append({"percentile": percentile, "threshold": threshold, "accepted": int(accepted.sum()),
            "coverage": float(accepted.mean()), "accepted_high_error_fraction": float(e["high_error"][accepted].mean()),
            "missed_high_error_cases": int((accepted & e["high_error"]).sum()),
            "rejected_high_error_cases": int((~accepted & e["high_error"]).sum())})
    eligible = [r for r in tradeoffs if r["accepted"] >= 20 and r["accepted_high_error_fraction"] <= 0.1]
    chosen = max(eligible, key=lambda r: r["coverage"]) if eligible else None
    drift = open_loop(model, validation, episodes, horizons=(1, 2))
    supported = [r["horizon_decisions"] for r in drift if r["rows"] >= 20 and r["position_mae_m"] <= 0.1
                 and r["state_mae"]["carried_kg"] <= 100 and r["pile_height_mae_m"] <= 0.02
                 and r["reward_mae"] <= 0.1]
    correlation = float(np.corrcoef(score, e["position_m"])[0, 1]) if score.std() and e["position_m"].std() else None
    return {"split": "validation", "uncertainty_method": "RMS ensemble standard deviation of train-normalised residual/reward outputs",
            "uncertainty_units": "dimensionless score, not probability", "high_error_rule": "position>0.05m or carried>50kg or pile-MAE>0.01m or reward>0.05 or terminal mismatch",
            "tradeoffs": tradeoffs, "threshold": chosen["threshold"] if chosen else None,
            "supported_horizon": min(2, max(supported)) if chosen and supported else 0,
            "position_error_pearson": correlation, "validation_drift": drift,
            "selection_rule": "highest validation coverage with >=20 accepted rows and <=10% high-error rate; then measured drift limits"}


def gate_report(model, arrays, gate):
    prediction = model.predict(arrays["state"], arrays["action"])
    e = errors(prediction, arrays["next_state"], arrays["reward"], arrays["events"])
    accepted = np.zeros(len(arrays["reward"]), dtype=bool) if gate["threshold"] is None else prediction["disagreement"] <= gate["threshold"]
    diagnostic_threshold = gate["threshold"] if gate["threshold"] is not None else gate["tradeoffs"][2]["threshold"]
    low_score = prediction["disagreement"] <= diagnostic_threshold
    return {"rows": len(accepted), "accepted": int(accepted.sum()), "coverage": float(accepted.mean()),
            "diagnostic_low_score_threshold": diagnostic_threshold,
            "low_score_high_error_cases": int((low_score & e["high_error"]).sum()),
            "missed_high_error_cases": int((accepted & e["high_error"]).sum()),
            "confident_wrong_fraction": float((accepted & e["high_error"]).mean()),
            "rejected_high_error_cases": int((~accepted & e["high_error"]).sum()),
            "accepted_high_error_fraction": float(e["high_error"][accepted].mean()) if accepted.any() else None}
