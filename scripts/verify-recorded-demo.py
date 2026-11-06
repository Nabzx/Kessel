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
    audit=json.loads((ROOT/"docs/phase-11/recorded-telemetry.json").read_text())
    events_path=ROOT/"docs/phase-11/recorded-telemetry-events.jsonl"
    if hashlib.sha256(events_path.read_bytes()).hexdigest()!=audit["telemetry"]["file_sha256"]:raise ValueError("retained transaction stream differs")
    previous=None;events=[]
    for line in events_path.read_text().splitlines():
        row=json.loads(line);digest=row.pop("sha256")
        if row["sequence"]!=len(events) or row["previous_sha256"]!=previous:raise ValueError("transaction chain order differs")
        if hashlib.sha256(json.dumps(row,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()!=digest:raise ValueError("transaction hash differs")
        events.append(row);previous=digest
    if events[-1]["payload"]["counters"]!=audit["counters"] or previous!=audit["telemetry"]["last_event_sha256"]:raise ValueError("transaction summary differs")
    return results


if __name__=="__main__":print(json.dumps(verify()))
