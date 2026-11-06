#!/usr/bin/env python3
"""Verify CPU export provenance, identities and identical-scene comparisons."""

import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def read(path):return json.loads(path.read_text(),parse_constant=lambda v:(_ for _ in ()).throw(ValueError(v)))


def verify(root=ROOT/"docs/phase-11/offline-policy-evidence"):
    root=root.resolve();index=read(root/"files.json")
    actual={p.name for p in root.iterdir() if p.is_file() and p.name!="files.json"}
    if actual!={f["path"] for f in index["files"]}:raise ValueError("offline inventory differs")
    for f in index["files"]:
        path=(root/f["path"]).resolve()
        if not path.is_relative_to(root) or path.stat().st_size!=f["bytes"] or hashlib.sha256(path.read_bytes()).hexdigest()!=f["sha256"]:raise ValueError("offline file checksum differs")
    manifest=read(root/"manifest.json");plan=read(root/"plan.json");comparison=read(root/"comparison.json")
    canonical=json.dumps(plan,sort_keys=True,separators=(",",":"),allow_nan=False)
    if hashlib.sha256(canonical.encode()).hexdigest()!=manifest["plan_sha256"]:raise ValueError("inference protocol differs")
    if manifest["source"]["training_dirty"] or manifest["runtime"]["ORT_DISABLE_TELEMETRY"]!="1":raise ValueError("uncommitted or network-enabled runtime")
    teacher=ROOT/plan["teacher"]
    if hashlib.sha256(teacher.read_bytes()).hexdigest()!=manifest["teacher"]["checkpoint_sha256"]:raise ValueError("teacher weights differ")
    if {v["variant"] for v in comparison["variants"]}!=set(plan["variants"]) or comparison["unsupported"]:raise ValueError("missing supported comparisons")
    known_hashes={hashlib.sha256(p.read_bytes()).hexdigest() for p in root.glob("*.onnx")}|{manifest["teacher"]["checkpoint_sha256"]}
    scenes={}
    for item in comparison["evaluations"]:
        e=item["evaluation"];key=e["family"];ids=[c["scenario_sha256"] for c in e["cases"]]
        if key in scenes and scenes[key]!=ids:raise ValueError("offline variants saw different scenes")
        scenes[key]=ids
        if e["identity"]["checkpoint_sha256"] not in known_hashes:raise ValueError("evaluation weights missing")
        if [c["seed"] for c in e["cases"]]!=list(range(206600,206604)):raise ValueError("fresh evaluation seeds differ")
    history=read(root/"distillation.json")
    if history["optimiser_updates"]!=plan["student_epochs"]*(plan["training_observations"]//plan["student_batch"]):raise ValueError("student update accounting differs")
    selected=min(history["history"],key=lambda r:r["current_validation_action_mse"])
    if selected["epoch"]!=history["selected_epoch"]:raise ValueError("student selection differs")
    return {"variants":len(comparison["variants"]),"evaluations":len(comparison["evaluations"]),"files":len(index["files"])}


if __name__=="__main__":print(json.dumps(verify()))
