#!/usr/bin/env python3
"""Verify shipped recorded playback against retained policy/model identities."""

import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"training"))
from kessel_training.viewer_bundle import validate


def verify():
    index=json.loads((ROOT/"data/experiments/index.json").read_text())
    if index["schema_version"]!="1.0":raise ValueError("unsupported catalogue")
    results=[]
    hashes={hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/"docs/phase-11/rl-evidence/policies").glob("*.pt")}
    model_hash=hashlib.sha256((ROOT/"docs/phase-11/world-model-evidence/models/ensemble.pt").read_bytes()).hexdigest()
    for entry in index["experiments"]:
        path=(ROOT/entry["url"]).resolve()
        if not path.is_relative_to(ROOT/"data/experiments") or path.suffix!=".json":raise ValueError("invalid bundle path")
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=entry["sha256"] or len(raw)!=entry["bytes"]:raise ValueError("bundle integrity differs")
        bundle=json.loads(raw);counts=validate(bundle)
        if bundle["run_id"]!=entry["run_id"] or bundle["source_mode"]!=entry["source_mode"]:raise ValueError("catalogue source identity differs")
        if bundle["world_model"]["model_sha256"]!=model_hash:raise ValueError("forecast weights not retained")
        for episode in bundle["episodes"]:
            if episode["policy"]["checkpoint_sha256"] not in hashes:raise ValueError("executed policy not retained")
        results.append({"run_id":bundle["run_id"],**counts,"bytes":len(raw)})
    return results


if __name__=="__main__":print(json.dumps(verify()))
