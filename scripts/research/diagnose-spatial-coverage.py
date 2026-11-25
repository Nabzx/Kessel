#!/usr/bin/env python3
"""255 frozen-phase queries on consumed practice inputs; no physics or training."""
import gzip
import hashlib
import json
from pathlib import Path
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0,str(ROOT/"training"))
import numpy as np
import torch
from kessel_lab.runtime import checkpoint
from kessel_training.controller import ReferenceController
from kessel_training.phase_memory import features
from kessel_training.policy import configure_cpu


def execute():
    configure_cpu(7,threads=1); started = time.monotonic()
    d = ROOT/"docs/phase-11/spatial-range-evidence"; d.mkdir(exist_ok=False)
    old = ROOT/"docs/phase-11/range-supervisor-evidence"
    report = json.loads((old/"report.json").read_text())
    masks = {}
    for name in ("near_rows","far_rows","centre_column","left_column","right_column","centre_3x3","centre_cell","all_cells"):
        mask = np.ones((5,5))
        if name == "near_rows": mask[:2,:] = 0
        if name == "far_rows": mask[2:,:] = 0
        if name == "centre_column": mask[:,2] = 0
        if name == "left_column": mask[:,0] = 0
        if name == "right_column": mask[:,4] = 0
        if name == "centre_3x3": mask[1:4,1:4] = 0
        if name == "centre_cell": mask[2,2] = 0
        if name == "all_cells": mask[:] = 0
        masks[name] = mask
    files = {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
             (old/"report.json",old/"traces.zip",Path(__file__).resolve(),
              ROOT/"docs/adr/0066-spatial-range-contract-and-pilot.md",
              ROOT/"training/kessel_lab/range_contract.py")}
    plan = {"role":"frozen-phase sensitivity on consumed practice traces; no qualification",
            "files":files,"masks":{k:v.tolist() for k,v in masks.items()},"cap_s":45,"query_cap":255,
            "snapshot_rule":"middle decision of each phase in each supervised healthy trace"}
    (d/"diagnostic-plan.json").write_text(json.dumps(plan,indent=2)+"\n")
    rows = []; snapshots = []; queries = 0
    original = ReferenceController.act
    def reject(*args,**kwargs): raise AssertionError("teacher call")
    ReferenceController.act = reject
    try:
        with torch.no_grad(), zipfile.ZipFile(old/"traces.zip") as z:
            for source in ("phase_memory-7","phase_memory-19","phase_memory-41"):
                case = next(c for c in report["cases"] if c["source"] == source and c["pattern"] == "healthy" and c["method"] == "missing_range_supervisor")
                raw = z.read(case["trace"])
                if hashlib.sha256(raw).hexdigest() != case["sha256"]: raise ValueError("input trace hash differs")
                trace = json.loads(gzip.decompress(raw)); actor,checkpoint_sha = checkpoint(source)
                for phase in range(5):
                    candidates = [i for i,f in enumerate(trace["frames"][:-1]) if f["phase"] == phase]
                    index = candidates[len(candidates)//2]; frame = trace["frames"][index]
                    obs = {k:np.asarray([v]) for k,v in frame["observation"].items()}
                    baseline = actor(features(obs),torch.tensor([phase]))[0].numpy(); queries += 1
                    if baseline.tolist() != frame["action"]: raise AssertionError("baseline action differs")
                    snapshots.append({"source":source,"phase":phase,"frame":index,"trace":case["trace"],
                                      "trace_sha256":case["sha256"],"checkpoint_sha256":checkpoint_sha,
                                      "baseline":baseline.tolist(),"observation":frame["observation"]})
                    for name,mask in masks.items():
                        for encoding in ("retained_height","zeroed_height"):
                            if time.monotonic()-started >= 45: raise TimeoutError("45-second diagnostic cap")
                            changed = {k:v.copy() for k,v in obs.items()}; changed["range_valid"] *= mask
                            if encoding == "zeroed_height": changed["local_height_m"] *= mask
                            action = actor(features(changed),torch.tensor([phase]))[0].numpy(); queries += 1
                            rows.append({"source":source,"phase":phase,"region":name,"encoding":encoding,
                                         "action":action.tolist(),"action_delta":(action-baseline).tolist(),
                                         "max_abs_action_delta":float(np.abs(action-baseline).max()),
                                         "height_cue_before":bool((obs["local_height_m"]*obs["range_valid"]).max() > .1),
                                         "height_cue_after":bool((changed["local_height_m"]*changed["range_valid"]).max() > .1)})
    finally: ReferenceController.act = original
    result = {"kind":"spatial-range-practice-diagnostic-v1","plan":plan,"snapshots":snapshots,"interventions":rows,
              "neural_queries":queries,"environment_decisions":0,"teacher_queries":0,"optimiser_updates":0,
              "cpu_threads":1,"wall_s":time.monotonic()-started}
    data = json.dumps(result,indent=2,allow_nan=False)+"\n"
    if queries != 255 or len(data.encode()) > 2*1024**2: raise ValueError("diagnostic coverage/output cap")
    (d/"diagnostic.json").write_text(data)
    print("Completed",queries,"queries in",round(result["wall_s"],2),"seconds; no physics or training")
    for phase in range(5):
        selected = max((r for r in rows if r["phase"] == phase),key=lambda r:r["max_abs_action_delta"])
        print("phase",phase,"largest delta",round(selected["max_abs_action_delta"],3),selected["region"],selected["encoding"],selected["source"])


if __name__ == "__main__": execute()
