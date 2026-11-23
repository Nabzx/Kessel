"""Frozen, bounded receiver-frame qualification. No training or teacher fallback."""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import time
import zipfile

import numpy as np
import torch
from kessel_training.controller import ReferenceController
from kessel_training.evaluate import source_identity
from kessel_training.policy import configure_cpu
from kessel_training.wm_state import pack
from .runtime import ROOT, Run, checkpoint, digest, environment
from .receiver_frame import METHOD, ReceiverFrameActor

SEEDS = tuple(range(205800,205808))
FAMILIES = ("nominal","receiver_far")
OUTPUT = ROOT / ".local/receiver-qualification-2026-11-23"
EVIDENCE = ROOT / "docs/phase-11/receiver-evidence"
WALL_CAP = 420
DECISION_CAP = 67200
REPLAY_CAP = 28800


def admitted(cases, complete):
    return bool(complete and all(
        len(rows := [r for r in cases if r["method"]==METHOD and
                     r["source"]=="phase_memory-"+str(seed) and r["family"]==family])==8
        and sum(r["full_success"] for r in rows)>=7
        and not any(r["collision"] for r in rows)
        for seed in (7,19,41) for family in FAMILIES))


def weights(actor):
    if isinstance(actor,ReceiverFrameActor):actor=actor.actor
    return hashlib.sha256(b"".join(v.detach().numpy().tobytes() for v in actor.state_dict().values())).hexdigest()


def execute():
    reservation=EVIDENCE/"reservation.json"
    cert=json.loads(reservation.read_text())
    if cert.get("verified") is not True or cert.get("seeds")!=list(SEEDS):
        raise ValueError("verified matching fresh-case reservation required")
    if not OUTPUT.resolve().is_relative_to(ROOT):raise ValueError("output escaped the repo")
    OUTPUT.mkdir(parents=True,exist_ok=False)
    configure_cpu(7,threads=1)
    jobs=[]
    for family in FAMILIES:
        for seed in SEEDS:
            jobs.extend({"family":family,"seed":seed,"source":"phase_memory-"+str(policy),"method":method}
                        for policy in (7,19,41) for method in ("original",METHOD))
            jobs.append({"family":family,"seed":seed,"source":"reference","method":"reference"})
    tracked=["training/kessel_lab/runtime.py","training/kessel_lab/receiver_frame.py",
             "training/kessel_lab/receiver_qualification.py","docs/adr/0064-receiver-frame-qualification.md",
             "docs/phase-11/phase-memory-evidence/selection.json"]
    files={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in tracked}
    plan={"kind":"receiver-frame-qualification-v1","cases":jobs,"source":source_identity(),
          "files":files,"reservation_sha256":hashlib.sha256(reservation.read_bytes()).hexdigest(),
          "wall_cap_s":WALL_CAP,"evaluation_decision_cap":DECISION_CAP,
          "adapted_physics_replay_cap":REPLAY_CAP,"cpu_threads":1,
          "software":{"torch":str(torch.__version__),"numpy":np.__version__},
          "optimiser_updates":0,"teacher_training_queries":0,"selection":"fixed ADR-0061 checkpoints; no test selection"}
    (OUTPUT/"plan.json").write_text(json.dumps(plan,indent=2)+"\n")
    # Archive exact numerical source before any policy query.
    with zipfile.ZipFile(OUTPUT/"source.zip","w",compression=zipfile.ZIP_DEFLATED) as z:
        for folder in ("training/kessel_training","training/kessel_lab"):
            for p in sorted((ROOT/folder).glob("*.py")):z.writestr(p.relative_to(ROOT).as_posix(),p.read_bytes())
        for name in ("training/pyproject.toml","training/uv.lock",*tracked[3:]):
            z.writestr(name,(ROOT/name).read_bytes())
    started=time.monotonic();rows=[];decisions=0;reference_queries=0;active=None;budget_stop=None
    maximum_state=0.;maximum_action=0.;physics_replay=0;action_replay=0;replayed_cases=0;action_cases=0
    original=ReferenceController.act
    def guard(self,obs):
        nonlocal reference_queries
        if active!="reference":raise AssertionError("reference action requested by a learned method")
        reference_queries+=1
        return original(self,obs)
    def within_budget():
        return time.monotonic()-started<WALL_CAP
    ReferenceController.act=guard
    try:
        with zipfile.ZipFile(OUTPUT/"traces.zip","w",compression=zipfile.ZIP_STORED) as z:
            for index,job in enumerate(jobs):
                if not within_budget():budget_stop="wall cap before case";break
                active=job["source"];run=Run(job["family"],job["seed"],job["source"])
                if job["method"]==METHOD:run.actor=ReceiverFrameActor(run.actor)
                before=weights(run.actor) if active!="reference" else None
                while not run.done:
                    if not within_budget() or decisions>=DECISION_CAP:
                        budget_stop="evaluation cap";break
                    run.step();decisions+=1
                    if decisions%50==0:time.sleep(.002)
                if active!="reference" and weights(run.actor)!=before:raise AssertionError("weights changed")
                identity=digest({"job":job,"base":run.identity,"sources":files})
                payload={"job":job,"identity":identity,"scenario":run.scenario,
                         "checkpoint_sha256":run.checkpoint_sha256,"outcome":run.outcome(),
                         "frames":run.records+[run.frame()]}
                raw=gzip.compress(json.dumps(payload,separators=(",",":"),allow_nan=False).encode(),mtime=0)
                path=str(index).zfill(3)+".json.gz";z.writestr(path,raw)
                rows.append({**job,"identity":identity,"scenario":run.scenario,
                             "checkpoint_sha256":run.checkpoint_sha256,"weights_unchanged":True,
                             "trace":path,"sha256":hashlib.sha256(raw).hexdigest(),**run.outcome()})
                if z.fp.tell()>32*1024*1024:budget_stop="archive cap"
                if budget_stop:break
                if index%7==6:
                    print("Evaluated",job["family"],job["seed"],len(rows),"/112",flush=True)
        # Freeze evaluated outcomes before independent replay; no reselection.
        evaluated={"cases":rows,"environment_decisions":decisions,"budget_stop":budget_stop}
        (OUTPUT/"evaluation.json").write_text(json.dumps(evaluated,indent=2)+"\n")
        if not budget_stop and len(rows)==112:
            active="independent_replay"
            with zipfile.ZipFile(OUTPUT/"traces.zip") as z:
                for case in rows:
                    if case["source"]=="reference":continue
                    if not within_budget():budget_stop="replay wall cap";break
                    raw=z.read(case["trace"])
                    if hashlib.sha256(raw).hexdigest()!=case["sha256"]:raise ValueError("trace hash differs")
                    data=json.loads(gzip.decompress(raw))
                    actor,sha=checkpoint(case["source"])
                    if sha!=case["checkpoint_sha256"]:raise ValueError("checkpoint identity differs")
                    if case["method"]==METHOD:
                        actor=ReceiverFrameActor(actor)
                        replay,_=environment(case["family"],case["seed"])
                    else:replay=None
                    for frame in data["frames"][:-1]:
                        if not within_budget():budget_stop="replay wall cap";break
                        obs={k:np.asarray([v]) for k,v in frame["observation"].items()}
                        action=actor.act(obs)[0];action_replay+=1
                        maximum_action=max(maximum_action,float(np.abs(action-frame["action"]).max()))
                        if int(actor.memory.phase[0])!=frame["phase"]:raise AssertionError("phase replay differs")
                        if replay is not None:
                            if physics_replay>=REPLAY_CAP:budget_stop="physics replay cap";break
                            maximum_state=max(maximum_state,float(np.abs(pack(replay)[0]-frame["state"]).max()))
                            replay.step([frame["action"]]);physics_replay+=1
                            maximum_state=max(maximum_state,float(np.abs(pack(replay)[0]-frame["next_state"]).max()))
                    if budget_stop:break
                    action_cases+=1
                    if replay is not None:
                        if str(replay.reason[0])!=case["reason"]:raise AssertionError("replayed outcome differs")
                        replayed_cases+=1
    finally:
        ReferenceController.act=original
    if maximum_state!=0 or maximum_action!=0:raise AssertionError("nonzero independent replay error")
    if any(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=sha for name,sha in files.items()):
        raise ValueError("source changed during frozen evaluation")
    complete=(not budget_stop and len(rows)==112 and all(r["done"] for r in rows) and
              replayed_cases==48 and action_cases==96)
    summaries=[]
    for family in FAMILIES:
        for method in ("original",METHOD,"reference"):
            sources=("reference",) if method=="reference" else tuple("phase_memory-"+str(s) for s in (7,19,41))
            for source in sources:
                selected=[r for r in rows if (r["family"],r["method"],r["source"])==(family,method,source)]
                summaries.append({"family":family,"method":method,"source":source,"cases":len(selected),
                                  "successes":sum(r["full_success"] for r in selected),
                                  "collisions":sum(r["collision"] for r in selected),
                                  "reasons":dict(Counter(r["reason"] for r in selected))})
    result={"kind":"receiver-frame-qualification-v1","plan":plan,"cases":rows,"summaries":summaries,
            "complete":complete,"budget_stop":budget_stop,"admitted":admitted(rows,complete),
            "evaluation_decisions":decisions,"reference_controller_queries":reference_queries,
            "adapted_physical_replay_cases":replayed_cases,"physics_replay_decisions":physics_replay,
            "learned_action_replay_cases":action_cases,"action_replay_queries":action_replay,
            "max_state_error":maximum_state,"max_action_error":maximum_action,
            "teacher_training_queries":0,"optimiser_updates":0,"active_wall_s":time.monotonic()-started,
            "trace_archive_sha256":hashlib.sha256((OUTPUT/"traces.zip").read_bytes()).hexdigest(),
            "source_archive_sha256":hashlib.sha256((OUTPUT/"source.zip").read_bytes()).hexdigest()}
    (OUTPUT/"report.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print("Qualification complete:",complete,"admitted:",result["admitted"],"budget:",budget_stop,flush=True)


if __name__=="__main__":
    execute()
