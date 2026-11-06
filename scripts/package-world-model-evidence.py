#!/usr/bin/env python3
"""Retain measured world-model results and executable weights outside the site."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(), parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))


def package(source, output):
    if output.exists():raise FileExistsError(output)
    plan, manifest, completed = (read(source/n) for n in ("plan.json", "manifest.json", "completed.json"))
    canonical = json.dumps(plan, sort_keys=True, separators=(",", ":"), allow_nan=False)
    if hashlib.sha256(canonical.encode()).hexdigest() != manifest["plan_sha256"]:
        raise ValueError("predeclared plan hash differs")
    if completed["source"]["training_dirty"] or completed["source"] != manifest["source"]:
        raise ValueError("study source was not consistently frozen")
    output.mkdir(parents=True)
    raw_inputs = []
    for path in sorted(source.glob("*.json")):
        value = read(path);raw_inputs.append({"path": path.name, "sha256": digest(path)})
        if path.name in ("policy-comparison.json", "predictions.json"):
            with gzip.GzipFile(filename=str(output/(path.name+".gz")), mode="wb", mtime=0) as stream:
                stream.write(json.dumps(value, separators=(",", ":"), allow_nan=False).encode())
        else:shutil.copyfile(path, output/path.name)
    for directory in ("models", "policies"):
        if not (source/directory).exists():continue
        (output/directory).mkdir()
        for path in sorted((source/directory).glob("*.pt")):
            if digest(path) != path.with_suffix(".pt.sha256").read_text().strip():
                raise ValueError("saved model or policy hash differs")
            shutil.copyfile(path, output/directory/path.name)
            shutil.copyfile(path.with_suffix(".pt.sha256"), output/directory/(path.name+".sha256"))
    (output/"figures").mkdir()
    for path in sorted((source/"figures").glob("*.svg")):shutil.copyfile(path, output/"figures"/path.name)
    points=source/"figures/uncertainty-points.json"
    with gzip.GzipFile(filename=str(output/"figures/uncertainty-points.json.gz"), mode="wb", mtime=0) as stream:
        stream.write(points.read_bytes())
    files = [{"path": str(p.relative_to(output)), "sha256": digest(p), "bytes": p.stat().st_size}
             for p in sorted(output.rglob("*")) if p.is_file()]
    (output/"files.json").write_text(json.dumps({"source_mode": "recorded_synthetic", "files": files,
        "raw_report_inputs": raw_inputs,
        "scope": "Every comparison curve, training episode and selected prediction/reference pair retained; executable final weights retained. Full transition archives and resumable optimiser/simulator state stay in ignored runs; deterministic corpus manifests and hashes permit regeneration."}, indent=2)+"\n")
    return {"files": len(files), "bytes": sum(f["bytes"] for f in files), "study_id": plan["study_id"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True);parser.add_argument("--output", type=Path, required=True)
    args=parser.parse_args();print(json.dumps(package(args.source, args.output)))
