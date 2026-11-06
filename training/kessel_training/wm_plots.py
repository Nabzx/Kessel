"""Standalone measured figures, independent of the investor interface."""

import json
import os
from pathlib import Path
import tempfile

import numpy as np

from .wm_evaluate import errors


def figures(directory, model, validation, test, gate, drift):
    os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir())/"kessel-wm-matplotlib"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    directory = Path(directory);directory.mkdir(parents=True, exist_ok=True)
    points = {}
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), layout="constrained")
    for name, data, colour in (("Validation", validation, "#ac7928"), ("Test", test, "#365f87")):
        prediction = model.predict(data["state"], data["action"])
        error = errors(prediction, data["next_state"], data["reward"], data["events"])
        score = prediction["disagreement"]
        points[name] = {"disagreement": score.tolist(), "position_error_m": error["position_m"].tolist(),
                        "high_error": error["high_error"].tolist()}
        axes[0].scatter(score, error["position_m"], s=9, alpha=0.3, label=name, color=colour, rasterized=True)
    axes[0].set(xlabel="Ensemble disagreement (dimensionless)", ylabel="Reference position error (m)", title="Actual one-step error")
    axes[0].set_yscale("symlog", linthresh=0.001);axes[0].legend()
    rows = gate["tradeoffs"]
    axes[1].plot([r["coverage"] for r in rows], [r["accepted_high_error_fraction"] for r in rows], "o-", color="#365f87")
    axes[1].axhline(0.1, color="#ac7928", linestyle="--", label="Declared 10% limit")
    axes[1].set(xlabel="Validation fraction accepted", ylabel="Accepted high-error fraction", title="Validation gate trade-off", xlim=(0, 1), ylim=(0, 1))
    axes[1].legend()
    fig.savefig(directory/"uncertainty.png", dpi=160);fig.savefig(directory/"uncertainty.svg", metadata={"Date": None});plt.close(fig)
    (directory/"uncertainty-points.json").write_text(json.dumps(points, separators=(",", ":"), allow_nan=False)+"\n")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), layout="constrained")
    for name, rows in drift.items():
        available = [r for r in rows if r["rows"]]
        axes[0].plot([r["nominal_horizon_s"] for r in available], [r["position_mae_m"] for r in available], "o-", label=name)
        axes[1].plot([r["nominal_horizon_s"] for r in available], [r["state_mae"]["carried_kg"] for r in available], "o-", label=name)
    axes[0].set(xlabel="Nominal horizon (s)", ylabel="Position MAE (m)", title="Fixed-action open-loop drift")
    axes[1].set(xlabel="Nominal horizon (s)", ylabel="Carried-mass MAE (kg)", title="Material prediction drift")
    for axis in axes:axis.legend(fontsize=8);axis.grid(alpha=0.2)
    fig.savefig(directory/"drift.png", dpi=160);fig.savefig(directory/"drift.svg", metadata={"Date": None});plt.close(fig)
