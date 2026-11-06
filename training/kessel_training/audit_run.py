"""Reconcile append-only training transactions with final checkpoint counters."""

import argparse
import hashlib
import json
from pathlib import Path

from . import checkpoints
from .telemetry import scan


def audit(directory):
    directory=Path(directory);report=json.loads((directory/"run.json").read_text())
    rows=scan(directory/"events.jsonl");rollouts=[r["payload"] for r in rows if r["kind"]=="rollout"]
    initial=rows[0]["payload"]["counters"];counters=report["counters"];config=report["configuration"]
    if initial["environment_steps"]+len(rollouts)*config["num_envs"]*config["rollout_steps"] != counters["environment_steps"]:
        raise ValueError("transition/rollout accounting differs")
    if initial["optimiser_updates"]+sum(r["metrics"]["minibatch_updates"] for r in rollouts)!=counters["optimiser_updates"]:
        raise ValueError("optimiser accounting differs")
    if report["telemetry"]["final_counters"]!=counters or rows[-1]["payload"]["counters"]!=counters:
        raise ValueError("final log counters differ")
    if hashlib.sha256((directory/"events.jsonl").read_bytes()).hexdigest()!=report["telemetry"]["file_sha256"]:
        raise ValueError("run log hash differs")
    final=next(r for r in reversed(rows) if r["kind"]=="checkpoint")["payload"]
    path=directory/final["file"];state=checkpoints.load(path)
    if checkpoints.sha256(path)!=final["checkpoint_sha256"] or state["counters"]!=counters:
        raise ValueError("final checkpoint counters differ")
    return {"source_mode":"recorded_synthetic","source":report["source"],"rollout_transactions":len(rollouts),
        "counters":counters,"training_wall_s":report["training_wall_s"],"telemetry":report["telemetry"]}


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("directory",type=Path)
    args=parser.parse_args();print(json.dumps(audit(args.directory)))
