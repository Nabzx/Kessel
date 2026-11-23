#!/usr/bin/env python3
"""Analyse retained cases only, without physics execution, training or teachers."""
from collections import Counter
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "training"))
try:
    os.nice(10)
    priority_adjusted = True
except PermissionError:
    priority_adjusted = False
import numpy as np
import torch
from kessel_lab.receiver_diagnostic import mouth_error, receiver_x, recover_proprio, static_force
from kessel_lab.runtime import checkpoint
from kessel_training.phase_memory import features
from kessel_training.policy import configure_cpu

configure_cpu(7, threads=1)
started = time.monotonic()
source = ROOT / "docs/phase-11/shift-evidence"
report = json.loads((source / "report.json").read_text())
rows = []
counterfactual_queries = 0
with zipfile.ZipFile(source / "traces.zip") as z:
    for case in report["cases"]:
        if case["family"] not in ("nominal", "receiver_far"):
            continue
        raw = z.read(case["trace"])
        if hashlib.sha256(raw).hexdigest() != case["sha256"]:
            raise ValueError("retained trace changed")
        episode = json.loads(gzip.decompress(raw))
        frames = episode["frames"][:-1]
        final = frames[-1]
        p = final["observation"]["proprio"]
        row = {"family": case["family"], "source": case["source"], "seed": case["seed"],
               "trace_sha256": case["sha256"], "reason": case["reason"],
               "phase_counts": dict(Counter(f["phase"] for f in frames)),
               "delivered_kg": case["delivered_kg"], "terminal_x_m": p[0],
               "terminal_speed_m_s": p[4], "terminal_load_kg": p[8],
               "mouth_error_m": mouth_error(p), "observed_receiver_x_m": receiver_x(p),
               "drive_command": final["action"][0], "force": static_force(final["state"], final["action"][0])}
        if case["source"] != "reference" and case["family"] == "receiver_far":
            actor, _ = checkpoint(case["source"])
            obs = {k: np.asarray([v]) for k, v in final["observation"].items()}
            phase = torch.tensor([final["phase"]])
            outputs = []
            # Deliberate input interventions, not newly simulated or held-out episodes.
            for dx in (-2., 0., 2.):
                altered = {k: v.copy() for k, v in obs.items()}
                altered["proprio"][0, 0] += dx
                with torch.no_grad():
                    action = actor(features(altered), phase)[0].tolist()
                outputs.append({"odometry_delta_x_m": dx, "drive_command": action[0]})
                counterfactual_queries += 1
            row["fixed_goal_input_interventions"] = outputs
        rows.append(row)
        if time.monotonic() - started > 45:
            raise TimeoutError("offline diagnosis exceeded 45 seconds")

training = []
train_archive = ROOT / "docs/phase-11/phase-memory-evidence/artifacts.zip"
with zipfile.ZipFile(train_archive) as z:
    names = [n for n in z.namelist() if n.endswith(".json.gz") and
             not n.startswith(("validation", "final"))]
    for name in names:
        episode = json.loads(gzip.decompress(z.read(name)))
        for d in episode["data"]:
            if d["phase"] == 3:
                p = recover_proprio(d["features"])
                training.append([p[0], p[9], receiver_x(p)])
        if time.monotonic() - started > 45:
            raise TimeoutError("offline diagnosis exceeded 45 seconds")
a = np.asarray(training)
result = {"kind": "receiver-retained-diagnosis-v1", "role": "diagnosis of already consumed cases; no qualification",
          "retained_cases": len(rows), "cases": rows, "training_acquisition_episodes": len(names),
          "training_carry_rows": len(a), "training_odometry_x_range_m": [float(a[:, 0].min()), float(a[:, 0].max())],
          "training_receiver_x_range_m": [float(a[:, 2].min()), float(a[:, 2].max())],
          "training_x_receiver_forward_correlation": float(np.corrcoef(a[:, :2].T)[0, 1]),
          "counterfactual_policy_queries": counterfactual_queries,
          "new_environment_decisions": 0, "teacher_queries": 0, "optimiser_updates": 0,
          "cpu_threads": 1, "process_nice_increment": 10 if priority_adjusted else 0, "wall_s": time.monotonic() - started}
output = ROOT / "docs/phase-11/receiver-evidence/diagnosis.json"
if output.exists():
    raise FileExistsError(output)
output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
print(json.dumps({k: v for k, v in result.items() if k != "cases"}, indent=2))
print("First farther-receiver interventions:",
      next(r["fixed_goal_input_interventions"] for r in rows if "fixed_goal_input_interventions" in r))
