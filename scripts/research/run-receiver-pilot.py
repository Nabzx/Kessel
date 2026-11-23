#!/usr/bin/env python3
"""A sixty-second, one-thread training-partition pilot; no training or admission."""
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "training"))
import numpy as np
import torch
from kessel_lab.runtime import Run, digest
from kessel_lab.receiver_frame import METHOD, ReceiverFrameActor
from kessel_training.controller import ReferenceController
from kessel_training.policy import configure_cpu


def weights(actor):
    if isinstance(actor, ReceiverFrameActor):
        actor = actor.actor
    return hashlib.sha256(b"".join(v.detach().numpy().tobytes() for v in actor.state_dict().values())).hexdigest()


def execute():
    output = ROOT / ".local/receiver-pilot-2026-11-23"
    if not output.resolve().is_relative_to(ROOT):
        raise ValueError("pilot output must stay in the repo")
    output.mkdir(parents=True, exist_ok=False)
    configure_cpu(7, threads=1)
    jobs = [{"method":method, "source":"phase_memory-"+str(seed), "family":family, "seed":19000}
            for method in ("original", METHOD) for seed in (7,19,41)
            for family in ("nominal", "receiver_far")]
    jobs += [{"method":"reference","source":"reference","family":f,"seed":19000}
             for f in ("nominal","receiver_far")]
    source_files = ["training/kessel_lab/runtime.py","training/kessel_lab/receiver_frame.py",
                    "training/kessel_training/phase_memory.py","scripts/research/run-receiver-pilot.py",
                    "docs/adr/0063-receiver-frame-pilot.md"]
    source = {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in source_files}
    plan = {"protocol":"ADR-0063","source_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
            "files":source,"cases":jobs,"cpu_threads":1,"wall_cap_s":60,"decision_cap":8400,
            "teacher_training_queries":0,"optimiser_updates":0,"held_out_cases":0,
            "software":{"torch":str(torch.__version__),"numpy":np.__version__}}
    (output/"plan.json").write_text(json.dumps(plan,indent=2)+"\n")
    started=time.monotonic();rows=[];decisions=0;reference_queries=0;active=None
    original=ReferenceController.act
    def guard(self, observation):
        nonlocal reference_queries
        if active!="reference":
            raise AssertionError("reference controller called for a learned pilot")
        reference_queries+=1
        return original(self,observation)
    ReferenceController.act=guard
    capped=False
    try:
        with zipfile.ZipFile(output/"traces.zip","w",compression=zipfile.ZIP_STORED) as archive:
            for i,job in enumerate(jobs):
                if time.monotonic()-started>=60:
                    capped=True;break
                active=job["source"];run=Run(job["family"],job["seed"],job["source"])
                if job["method"]==METHOD:
                    run.actor=ReceiverFrameActor(run.actor)
                before=weights(run.actor) if active!="reference" else None
                while not run.done:
                    if time.monotonic()-started>=60 or decisions>=8400:
                        capped=True;break
                    run.step();decisions+=1
                    if decisions%50==0:time.sleep(.002)
                after=weights(run.actor) if active!="reference" else None
                if before!=after:raise AssertionError("weights changed during pilot")
                identity=digest({"job":job,"run":run.identity,"method_sources":source})
                payload={"job":job,"identity":identity,"scenario":run.scenario,
                         "checkpoint_sha256":run.checkpoint_sha256,"outcome":run.outcome(),
                         "weights_before":before,"weights_after":after,
                         "frames":run.records+[run.frame()]}
                raw=gzip.compress(json.dumps(payload,separators=(",",":"),allow_nan=False).encode(),mtime=0)
                name=str(i).zfill(2)+".json.gz";archive.writestr(name,raw)
                row={**job,"identity":identity,"checkpoint_sha256":run.checkpoint_sha256,
                     "trace":name,"sha256":hashlib.sha256(raw).hexdigest(),
                     "weights_unchanged":before==after,**run.outcome()}
                rows.append(row)
                print(job["method"],job["source"],job["family"],row["reason"] or "budget_cap",
                      round(row["delivered_kg"],1),flush=True)
                if capped:break
    finally:
        ReferenceController.act=original
    adapted=[r for r in rows if r["method"]==METHOD]
    complete=not capped and len(rows)==14 and all(r["done"] for r in rows)
    result={"kind":"receiver-training-pilot-v1","plan":plan,"cases":rows,
            "complete":complete,"advance_hypothesis":complete and len(adapted)==6 and
             all(r["full_success"] and not r["collision"] for r in adapted),
            "environment_decisions":decisions,"reference_controller_queries":reference_queries,
            "teacher_training_queries":0,"optimiser_updates":0,"held_out_cases":0,
            "active_wall_s":time.monotonic()-started,
            "trace_archive_sha256":hashlib.sha256((output/"traces.zip").read_bytes()).hexdigest(),
            "admission":"not admitted; training-partition pilot only"}
    (output/"report.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print("Complete:",complete,"advance:",result["advance_hypothesis"],"decisions:",decisions,flush=True)


if __name__=="__main__":
    execute()
