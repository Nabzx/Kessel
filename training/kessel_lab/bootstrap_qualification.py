"""ADR-0070: frozen fresh moving-carry qualification; no training or runtime promotion."""
import copy
import gzip
import hashlib
import json
import subprocess
import time
import zipfile

import numpy as np
import torch
from kessel_training.controller import ReferenceController
from kessel_training.policy import configure_cpu
from kessel_training.wm_state import pack
from .bootstrap_hold import METHOD, BootstrapHoldSupervisor as CompleteRangeSupervisor
from .range_pilot import weights
from .runtime import ROOT, digest
from .bootstrap_hold_pilot import make_run, SpatialFault, stopping

OUTPUT = ROOT/".local/bootstrap-fresh-qualification-2026-11-25"
SEEDS = tuple(range(208700,208708))
PATTERNS = ("healthy","partial_carry_zeroed","carry_loss","recovery")
EVIDENCE = ROOT/"docs/phase-11/bootstrap-qualification-evidence"


def jobs():
    rows = []
    for seed in SEEDS:
        for policy in (7,19,41):
            for pattern in PATTERNS:
                rows.append({"source":"phase_memory-"+str(policy),"seed":seed,"method":METHOD,
                             "kind":"task","pattern":pattern,
                             "criterion":"stop" if pattern in ("partial_carry_zeroed","carry_loss") else "delivery"})
    rows += [{"source":"phase_memory-"+str(policy),"seed":seed,"method":"original",
              "kind":"task","pattern":"healthy","criterion":"delivery"} for seed in SEEDS for policy in (7,19,41)]
    return rows


def admitted(cases, complete, healthy_exact):
    expected = {(j["method"],j["source"],j["pattern"],j["seed"]) for j in jobs()}
    actual = {(j["method"],j["source"],j["pattern"],j["seed"]) for j in cases}
    return bool(complete and healthy_exact and len(cases) == 120 and actual == expected and all(
        len(group := [c for c in cases if c["method"] == METHOD and c["source"] == "phase_memory-"+str(policy)
                      and c["pattern"] == pattern]) == 8
        and {c["seed"] for c in group} == set(SEEDS)
        and sum(c["criterion_passed"] for c in group) >= 7 and not any(c["collision"] for c in group)
        and all(c["weights_unchanged"] for c in group)
        for policy in (7,19,41) for pattern in PATTERNS))


def execute():
    cert_path = EVIDENCE/"reservation.json"
    cert = json.loads(cert_path.read_text())
    if not cert.get("verified") or cert.get("seeds") != list(SEEDS) or cert.get("hits") or cert.get("errors"):
        raise ValueError("matching verified fresh reservation required")
    for name,digest in cert["audit_files"].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != digest: raise ValueError("audit source changed: "+name)
    configure_cpu(7,threads=1); OUTPUT.mkdir(parents=True,exist_ok=False)
    paths = sorted((ROOT/"training/kessel_training").glob("*.py"))
    paths += [ROOT/n for n in ("training/kessel_lab/runtime.py","training/kessel_lab/range_supervisor.py",
        "training/kessel_lab/range_contract.py","training/kessel_lab/range_pilot.py","training/kessel_lab/bootstrap_hold_pilot.py","training/kessel_lab/bootstrap_qualification.py","training/kessel_lab/motion_hold.py","training/kessel_lab/bootstrap_hold.py",
        "training/uv.lock","docs/adr/0066-spatial-range-contract-and-pilot.md",
        "docs/adr/0068-observed-motion-holding-pilot.md","docs/adr/0069-bootstrap-motion-holding-pilot.md","docs/adr/0070-bootstrap-hold-fresh-qualification.md",
        "docs/phase-11/phase-memory-evidence/selection.json","docs/phase-11/bootstrap-qualification-evidence/reservation.json")]
    files = {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    plan = {"protocol":"ADR-0070","reservation_sha256":hashlib.sha256(cert_path.read_bytes()).hexdigest(),"cases":jobs(),"files":files,"cpu_threads":1,"wall_cap_s":420,
            "evaluation_cap":72000,"physics_replay_cap":57600,"action_replay_cap":72000,"trace_archive_cap":32*1024**2,
            "commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
            "software":{"torch":str(torch.__version__),"numpy":np.__version__}}
    (OUTPUT/"plan.json").write_text(json.dumps(plan,indent=2)+"\n")
    with zipfile.ZipFile(OUTPUT/"source.zip","w",compression=zipfile.ZIP_DEFLATED) as z:
        for p in paths: z.write(p,p.relative_to(ROOT))
    started = time.monotonic(); rows = []; decisions = physics = queries = 0
    physical_cases = action_cases = 0; state_error = action_error = observation_error = 0.; stop = None; trace_bytes = 0
    class BudgetStop(Exception): pass
    def budget():
        if time.monotonic()-started >= 420: raise BudgetStop("wall_cap")
    original = ReferenceController.act
    def reject(*args,**kwargs): raise AssertionError("teacher/reference call")
    ReferenceController.act = reject
    try:
        with zipfile.ZipFile(OUTPUT/"traces.zip","w",compression=zipfile.ZIP_STORED) as archive:
            for index,job in enumerate(plan["cases"]):
                budget(); run = make_run(job); injector = SpatialFault(job["pattern"])
                before = weights(run.actor); first_loss = False; streak = 0; settled = None; end = None
                try:
                    while not run.done:
                        budget()
                        if decisions >= 72000: raise BudgetStop("evaluation_cap")
                        actual = run.env.observe(); obs,fault = injector.apply(actual)
                        action = run.actor.act(obs); record = run.frame()
                        record.update(observation={k:v[0].tolist() for k,v in obs.items()},
                                      actual_observation={k:v[0].tolist() for k,v in actual.items()},fault=fault,
                                      supervision=copy.deepcopy(run.actor.last) if job["method"] == METHOD else None,
                                      action=action[0].tolist())
                        _,reward,term,trunc,info = run.env.step(action)
                        run.decisions += 1; decisions += 1; run.done = bool((term|trunc)[0])
                        residual = abs(float((run.env.pile.mass()+run.env.payload+run.env.delivered+run.env.spilled-run.env.pile.initial_mass)[0]))
                        if residual > 1e-7: raise AssertionError("material ledger differs")
                        run.max_mass_residual = max(run.max_mass_residual,residual)
                        record.update(next_state=pack(run.env)[0].tolist(),reward=float(reward[0]),
                                      transfer={k:float(info["transfer"][k][0]) for k in ("loaded_kg","delivered_kg","spilled_kg")})
                        run.records.append(record)
                        if job["criterion"] == "stop" and fault["active"]:
                            if not first_loss: streak = int(abs(record["state"][3]) <= .08); first_loss = True
                            streak = streak+1 if abs(float(run.env.speed[0])) <= .08 else 0
                            if settled is None and streak >= 3: settled = float(run.env.elapsed[0])
                            if settled is not None and float(run.env.elapsed[0])-settled >= 10.-1e-8:
                                end = "hold_window"; break
                except BudgetStop as e: stop = str(e); end = "budget_cap"
                after = weights(run.actor)
                if before != after: raise AssertionError("weights changed")
                outcome = run.outcome(); outcome["initial_payload_kg"] = job.get("initial_payload_kg",0.)
                final = run.frame(); metric = stopping(run.records,final,run.done) if job["criterion"] == "stop" else None
                overrides = [f for f in run.records if f["supervision"] and f["supervision"]["override"]]
                resumed = any(not f["supervision"]["override"] and f["supervision"]["paused_s"] > 0 for f in run.records if f["supervision"])
                passed = bool(metric and metric["passed"] and not outcome["collision"]) if job["criterion"] == "stop" else outcome["full_success"]
                if job["pattern"] != "healthy": passed = passed and injector.started is not None
                if job["pattern"] == "recovery": passed = passed and bool(overrides) and resumed
                identity = digest({"job":job,"scenario":run.scenario,"files":files})
                payload = {"job":job,"identity":identity,"scenario":run.scenario,"checkpoint_sha256":run.checkpoint_sha256,
                           "outcome":outcome,"weights_before":before,"weights_after":after,"frames":run.records+[final]}
                raw = gzip.compress(json.dumps(payload,separators=(",",":"),allow_nan=False).encode(),mtime=0)
                if trace_bytes+len(raw)+20000 > 32*1024**2: raise BudgetStop("trace_archive_cap")
                name = str(index).zfill(2)+".json.gz"; archive.writestr(name,raw); trace_bytes += len(raw)
                rows.append({**job,**outcome,"identity":identity,"checkpoint_sha256":run.checkpoint_sha256,
                             "trace":name,"sha256":hashlib.sha256(raw).hexdigest(),"weights_unchanged":True,
                             "study_end":end or "environment_terminal","stop":metric,"trigger_reached":injector.started is not None,
                             "override_decisions":len(overrides),"resumed":resumed,"criterion_passed":bool(passed)})
                print(job["source"],job["pattern"],job.get("grade_rad",""),job.get("initial_speed_m_s",""),
                      outcome["reason"] or end,"pass",bool(passed),flush=True)
                if stop: break
        (OUTPUT/"evaluation.json").write_text(json.dumps({"cases":rows,"budget_stop":stop},indent=2)+"\n")
        if not stop:
            with zipfile.ZipFile(OUTPUT/"traces.zip") as archive:
                for row,job in zip(rows,plan["cases"]):
                    budget(); trace = json.loads(gzip.decompress(archive.read(row["trace"]))); frames = trace["frames"][:-1]
                    if row["method"] == METHOD:
                        replay = make_run(job); injection = SpatialFault(row["pattern"])
                        for f in frames:
                            budget()
                            if physics >= 57600: raise BudgetStop("physics_replay_cap")
                            state_error = max(state_error,float(np.abs(pack(replay.env)[0]-f["state"]).max()))
                            actual = replay.env.observe(); observed,fault = injection.apply(actual)
                            if fault != f["fault"]: raise AssertionError("fault replay differs")
                            for k in actual:
                                observation_error = max(observation_error,float(np.abs(actual[k][0]-f["actual_observation"][k]).max()),
                                                        float(np.abs(observed[k][0]-f["observation"][k]).max()))
                            replay.env.step([f["action"]]); physics += 1
                            state_error = max(state_error,float(np.abs(pack(replay.env)[0]-f["next_state"]).max()))
                        physical_cases += 1
                    replay = make_run(job)
                    for f in frames:
                        budget()
                        if queries >= 72000: raise BudgetStop("action_replay_cap")
                        obs = {k:np.asarray([v]) for k,v in f["observation"].items()}
                        action = replay.actor.act(obs)[0]; queries += 1
                        action_error = max(action_error,float(np.abs(action-f["action"]).max()))
                        if int(replay.actor.memory.phase[0]) != f["phase"]: raise AssertionError("phase replay differs")
                        if row["method"] == METHOD and replay.actor.last != f["supervision"]:
                            raise AssertionError("canonical input/proposal/clock replay differs")
                    action_cases += 1
        if state_error or action_error or observation_error: raise AssertionError("independent replay differs")
    except BudgetStop as e: stop = str(e)
    finally: ReferenceController.act = original
    exact = True
    with zipfile.ZipFile(OUTPUT/"traces.zip") as z:
        for policy in (7,19,41):
            for seed in SEEDS:
                pair = [r for r in rows if r["source"] == "phase_memory-"+str(policy) and r["pattern"] == "healthy" and r["seed"] == seed]
                if len(pair) != 2: exact = False; continue
                a,b = [json.loads(gzip.decompress(z.read(c["trace"]))) for c in pair]
                exact &= len(a["frames"]) == len(b["frames"]) and all(x["state"] == y["state"] and x["phase"] == y["phase"] and x.get("action") == y.get("action") for x,y in zip(a["frames"],b["frames"]))
    trace_sha = hashlib.sha256((OUTPUT/"traces.zip").read_bytes()).hexdigest()
    source_sha = hashlib.sha256((OUTPUT/"source.zip").read_bytes()).hexdigest()
    duration = time.monotonic()-started
    if duration >= 420 and stop is None: stop = "final_verification_wall_cap"
    complete = stop is None and len(rows) == 120 and physical_cases == 96 and action_cases == 120
    r = {"kind":"bootstrap-hold-fresh-qualification-v1","plan":plan,"cases":rows,"complete":complete,"budget_stop":stop,
         "admitted":admitted(rows,complete,bool(exact)),"healthy_exact":bool(exact),
         "environment_decisions":decisions,"neural_queries":decisions,"physics_replay_decisions":physics,"physics_replay_cases":physical_cases,
         "action_replay_queries":queries,"action_replay_cases":action_cases,"max_state_error":state_error,
         "max_action_error":action_error,"max_observation_error":observation_error,
         "teacher_queries":0,"optimiser_updates":0,"held_out_cases":len(rows),"active_wall_s":duration,
         "trace_archive_sha256":trace_sha,"source_archive_sha256":source_sha,
         "scope":"fresh nominal-physics healthy/partial-carry/complete-loss/recovery only; not runtime or field qualification"}
    (OUTPUT/"report.json").write_text(json.dumps(r,indent=2,allow_nan=False)+"\n")
    print("Complete",complete,"admitted",r["admitted"],"decisions",decisions,"replay",physics,"wall",round(r["active_wall_s"],2),flush=True)


if __name__ == "__main__": execute()
