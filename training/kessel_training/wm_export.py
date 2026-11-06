"""Actual saved-model predictions paired with independently recorded references."""

import numpy as np

from .wm_state import DYNAMIC_NAMES, PILE_END, STATE_NAMES, violations


def export_examples(model, identity, arrays, manifest, horizons=(1, 2, 4, 8)):
    chosen = []
    for regime in range(4):
        candidates = np.flatnonzero(arrays["regime"] == regime)
        if len(candidates):chosen.append(int(candidates[0]))
    learned = [e for e in manifest["episodes"] if e["source_kind"] == "policy"]
    if learned:chosen.extend([learned[0]["start"], learned[0]["stop"]-1])
    examples = []
    for index in dict.fromkeys(chosen):
        episode = manifest["episodes"][int(arrays["episode_id"][index])]
        current = arrays["state"][index:index+1].copy()
        predicted_reward = 0.0;reference_reward = 0.0;predicted_stop = False;records = []
        for step in range(1, max(horizons)+1):
            row = index+step-1
            reference_available = row < episode["stop"]
            prediction = None
            if reference_available:
                reference_reward += float(arrays["reward"][row])
                if not predicted_stop:
                    prediction = model.predict(current, arrays["action"][row:row+1])
                    current = prediction["next_state"]
                    predicted_reward += float(prediction["reward"][0])
                    predicted_stop = bool(prediction["events"][0, :2].max() >= 0.5)
            if step not in horizons:
                continue
            record = {"horizon_decisions": step, "nominal_horizon_s": step*0.1,
                      "prediction": None, "reference": None, "residual": None,
                      "missing_reason": "reference_episode_ended" if not reference_available else "model_event_stop" if prediction is None else None}
            if reference_available:
                record["reference"] = {"state": arrays["next_state"][row].tolist(), "cumulative_reward": reference_reward,
                    "elapsed_horizon_s": float(arrays["next_state"][row, 10]-arrays["state"][index, 10])}
            if prediction is not None:
                raw = violations(current)
                residual = current[0, :PILE_END]-arrays["next_state"][row, :PILE_END]
                residual[2] = (residual[2]+np.pi) % (2*np.pi)-np.pi
                record.update(prediction={"state": current[0].tolist(), "cumulative_reward": predicted_reward,
                    "event_probabilities": prediction["events"][0].tolist()},
                    residual={"state": residual.tolist(), "cumulative_reward": predicted_reward-reference_reward},
                    uncertainty={"score": float(prediction["disagreement"][0]),
                        "method": "RMS ensemble std of train-normalised one-step outputs at the final predicted state",
                        "units": "dimensionless score; not calibrated probability or cumulative horizon covariance"})
                record["raw_physical_violations"] = {k: float(v[0]) if k == "mass_error_kg" else bool(v[0]) for k, v in raw.items()}
            records.append(record)
        examples.append({"dataset_row": index, "episode": episode, "regime": int(arrays["regime"][index]),
                         "initial_state": arrays["state"][index].tolist(),
                         "actions": arrays["action"][index:min(index+max(horizons), episode["stop"])].tolist(),
                         "predictions": records})
    return {"schema_version": "1.0", "source_mode": "recorded_synthetic", "model_identity": identity,
            "dataset_logical_sha256": manifest["logical_sha256"], "state_names": STATE_NAMES,
            "residual_state_names": STATE_NAMES[:PILE_END], "dynamic_names": DYNAMIC_NAMES,
            "selection": "first row of each available regime, first learned-policy episode start/end; no best-case selection",
            "reference_source": "independent simulator transitions captured before model training",
            "examples": examples}


def verify_residuals(bundle):
    count = 0
    for example in bundle["examples"]:
        for record in example["predictions"]:
            if record["prediction"] is None:
                if record["residual"] is not None or record["missing_reason"] is None:
                    raise ValueError("missing prediction acquired an invented residual")
                continue
            p = record["prediction"];r = record["reference"]
            if not np.isfinite(p["state"]).all() or not np.isfinite(r["state"]).all() or not np.isfinite([p["cumulative_reward"], r["cumulative_reward"]]).all():
                raise ValueError("non-finite prediction/reference pair")
            residual = np.asarray(p["state"][:PILE_END])-r["state"][:PILE_END]
            residual[2] = (residual[2]+np.pi) % (2*np.pi)-np.pi
            if not np.allclose(residual, record["residual"]["state"], rtol=0, atol=1e-10):
                raise ValueError("prediction/reference residual differs")
            if abs(p["cumulative_reward"]-r["cumulative_reward"]-record["residual"]["cumulative_reward"]) > 1e-10:
                raise ValueError("reward residual differs")
            count += 1
    return count
