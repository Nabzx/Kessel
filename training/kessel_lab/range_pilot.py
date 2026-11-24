"""Bounded ADR-0065 practice pilot; no training, runtime promotion or fresh tests."""
import copy
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
from kessel_training.phase_memory import PhaseMemory
from kessel_training.policy import configure_cpu
from kessel_training.wm_state import pack
from .range_supervisor import METHOD, RangeSupervisor
from .runtime import ROOT, Run, checkpoint, digest, environment

PATTERNS = ("healthy","reset_loss","approach_loss","fill_loss","lift_loss",
            "carry_loss","transient","recovery","partial_occlusion")
PERMANENT = PATTERNS[1:6]
OUTPUT = ROOT/".local/range-supervisor-pilot-2026-11-24"


class FaultInput:
    """Observation-only phase triggers; physical state never enters this adapter."""
    def __init__(self, pattern):
        self.pattern = pattern; self.trigger = PhaseMemory(); self.started = None
        self.last_crop = np.zeros((1,5,5))

    def apply(self, actual):
        obs = {k:v.copy() for k,v in actual.items()}
        phase = int(self.trigger.update(actual)[0]); now = float(actual["proprio"][0,13])
        if self.started is None:
            hit = (self.pattern == "reset_loss" or
                   self.pattern in ("approach_loss","transient") and now >= 1.-1e-9 or
                   self.pattern == "fill_loss" and phase == 1 or
                   self.pattern == "lift_loss" and phase == 2 or
                   self.pattern in ("carry_loss","recovery") and phase == 3)
            if hit: self.started = now
        duration = .1 if self.pattern == "transient" else 2. if self.pattern == "recovery" else float("inf")
        active = self.started is not None and now-self.started < duration-1e-9
        if active:
            obs["local_height_m"] = self.last_crop.copy(); obs["range_valid"][:] = 0
            obs["proprio"][0,11] = max(float(actual["proprio"][0,11]), now-self.started+(.1 if self.started else 0.))
            obs["proprio"][0,12] = 0
        else:
            self.last_crop = actual["local_height_m"].copy()
        if self.pattern == "partial_occlusion": obs["range_valid"][:,:2,:] = 0
        return obs, {"active":active,"started_s":self.started,"trigger_phase":phase}


def weights(actor):
    if isinstance(actor,RangeSupervisor): actor = actor.actor
    return hashlib.sha256(b"".join(v.detach().numpy().tobytes() for v in actor.state_dict().values())).hexdigest()


def stop_metrics(records, final, done):
    losses = [i for i,r in enumerate(records) if r["fault"]["active"]]
    if not losses: return None
    first = losses[0]; start = records[first]["state"][10]
    samples = [r["state"] for r in records[first:]]+[final["state"]]
    streak = 0; settled = None
    for i,state in enumerate(samples):
        streak = streak+1 if abs(state[3]) <= .08 else 0
        if streak >= 3: settled = i; break
    detected = next((r["state"][10] for r in records[first:] if r["supervision"] and r["supervision"]["override"]),None)
    result = {"loss_s":start,"detected_s":detected,"settled_s":None,"hold_s":0.,
              "stop_distance_m":None,"hold_path_m":None,"hold_max_speed_m_s":None,
              "physical_speed_at_loss_m_s":samples[0][3],"physical_load_at_loss_kg":samples[0][7],
              "grade_rad":samples[0][84],"passed":False}
    if settled is None: return result
    path = [float(np.linalg.norm(np.asarray(b[:2])-a[:2])) for a,b in zip(samples,samples[1:])]
    result.update(settled_s=samples[settled][10],hold_s=samples[-1][10]-samples[settled][10],
                  stop_distance_m=sum(path[:settled]),hold_path_m=sum(path[settled:]),
                  hold_max_speed_m_s=max(abs(s[3]) for s in samples[settled:]))
    result["passed"] = bool(detected is not None and detected-start <= .3+1e-8
        and result["settled_s"]-start <= 2.5+1e-8 and result["stop_distance_m"] <= 2.
        and result["hold_s"] >= 3.-1e-8 and result["hold_path_m"] <= .25
        and result["hold_max_speed_m_s"] <= .10 and not done)
    return result


def execute():
    configure_cpu(7,threads=1)
    OUTPUT.mkdir(parents=True,exist_ok=False)
    jobs = [{"method":METHOD,"source":"phase_memory-"+str(s),"pattern":p,"seed":19000}
            for s in (7,19,41) for p in PATTERNS]
    jobs += [{"method":"original","source":"phase_memory-"+str(s),"pattern":p,"seed":19000}
             for s in (7,19,41) for p in ("healthy","reset_loss")]
    source_paths = sorted((ROOT/"training/kessel_training").glob("*.py"))
    source_paths += [ROOT/n for n in ("training/kessel_lab/runtime.py","training/kessel_lab/range_supervisor.py",
        "training/kessel_lab/range_pilot.py","training/uv.lock","docs/adr/0065-missing-range-supervisor-pilot.md",
        "docs/phase-11/phase-memory-evidence/selection.json")]
    files = {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths}
    plan = {"protocol":"ADR-0065","cases":jobs,"files":files,
            "commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
            "cpu_threads":1,"wall_cap_s":180,"evaluation_cap":19800,"physics_replay_cap":16200,
            "action_replay_cap":19800,"trace_archive_cap":16*1024**2,
            "software":{"torch":str(torch.__version__),"numpy":np.__version__}}
    (OUTPUT/"plan.json").write_text(json.dumps(plan,indent=2)+"\n")
    with zipfile.ZipFile(OUTPUT/"source.zip","w",compression=zipfile.ZIP_DEFLATED) as z:
        for p in source_paths: z.write(p,p.relative_to(ROOT))
    started = time.monotonic(); rows = []; decisions = queries = physical = actions = 0
    state_error = action_error = observation_error = 0.; physics_cases = action_cases = 0
    stopped = None; trace_bytes = 0
    class BudgetStop(Exception): pass
    def budget():
        if time.monotonic()-started >= 180: raise BudgetStop("wall_cap")
    original_reference = ReferenceController.act
    def reject_reference(*args,**kwargs): raise AssertionError("reference call in a neural-only pilot")
    ReferenceController.act = reject_reference
    try:
        with zipfile.ZipFile(OUTPUT/"traces.zip","w",compression=zipfile.ZIP_STORED) as archive:
            for index,job in enumerate(jobs):
                budget()
                run = Run("nominal",job["seed"],job["source"])
                if job["method"] == METHOD: run.actor = RangeSupervisor(run.actor)
                injector = FaultInput(job["pattern"]); before = weights(run.actor)
                study_end = None; sampled_loss = False; slow_streak = 0; settled_at = None
                try:
                    while not run.done:
                        budget()
                        if decisions >= 19800: raise BudgetStop("evaluation_cap")
                        actual = run.env.observe(); observed,fault = injector.apply(actual)
                        action = run.actor.act(observed); queries += 1
                        record = run.frame()
                        record.update(observation={k:v[0].tolist() for k,v in observed.items()},
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
                        if job["method"] == METHOD and job["pattern"] in PERMANENT:
                            if fault["active"]:
                                if not sampled_loss:
                                    slow_streak = int(abs(record["state"][3]) <= .08); sampled_loss = True
                                slow_streak = slow_streak+1 if abs(float(run.env.speed[0])) <= .08 else 0
                                if settled_at is None and slow_streak >= 3: settled_at = float(run.env.elapsed[0])
                                if settled_at is not None and float(run.env.elapsed[0])-settled_at >= 3.-1e-8:
                                    study_end = "hold_window"; break
                except BudgetStop as e:
                    stopped = str(e); study_end = "budget_cap"
                final = run.frame(); after = weights(run.actor)
                if before != after: raise AssertionError("weights changed")
                stop = stop_metrics(run.records,final,run.done) if job["pattern"] in PERMANENT else None
                outcome = run.outcome(); overrides = [r for r in run.records if r["supervision"] and r["supervision"]["override"]]
                resumed = any(not r["supervision"]["override"] and r["supervision"]["paused_s"] > 0
                              for r in run.records if r["supervision"])
                identity = digest({"job":job,"base_run":run.identity,"files":files})
                payload = {"job":job,"identity":identity,"scenario":run.scenario,
                           "checkpoint_sha256":run.checkpoint_sha256,"weights_before":before,"weights_after":after,
                           "outcome":outcome,"frames":run.records+[final]}
                raw = gzip.compress(json.dumps(payload,separators=(",",":"),allow_nan=False).encode(),mtime=0)
                name = str(index).zfill(2)+".json.gz"
                if trace_bytes+len(raw)+10000 > plan["trace_archive_cap"]:
                    raise BudgetStop("trace_archive_cap")
                archive.writestr(name,raw); trace_bytes += len(raw)
                passed = ((stop and stop["passed"] and not outcome["collision"])
                          if job["pattern"] in PERMANENT and job["method"] == METHOD else outcome["full_success"])
                if job["pattern"] == "recovery": passed = passed and bool(overrides) and resumed
                rows.append({**job,**outcome,"identity":identity,"checkpoint_sha256":run.checkpoint_sha256,
                             "trace":name,"sha256":hashlib.sha256(raw).hexdigest(),"weights_unchanged":before == after,
                             "study_end":study_end or "environment_terminal","stop":stop,
                             "override_decisions":len(overrides),"resumed":resumed,"criterion_passed":bool(passed)})
                print(job["method"],job["source"],job["pattern"],rows[-1]["study_end"],
                      outcome["reason"] or "nonterminal", "pass",bool(passed),flush=True)
                if stopped: break
        # Seal outcomes before any independent replay.
        (OUTPUT/"evaluation.json").write_text(json.dumps({"cases":rows,"budget_stop":stopped},indent=2)+"\n")
        if not stopped:
            with zipfile.ZipFile(OUTPUT/"traces.zip") as archive:
                for row in rows:
                    budget(); trace = json.loads(gzip.decompress(archive.read(row["trace"])))
                    frames = trace["frames"][:-1]
                    if row["method"] == METHOD:
                        replay,_ = environment("nominal",row["seed"]); injection = FaultInput(row["pattern"])
                        for record in frames:
                            budget()
                            if physical >= 16200: raise BudgetStop("physics_replay_cap")
                            state_error = max(state_error,float(np.abs(pack(replay)[0]-record["state"]).max()))
                            actual = replay.observe(); observed,fault = injection.apply(actual)
                            if fault != record["fault"]: raise AssertionError("fault schedule differs")
                            for k in actual:
                                observation_error = max(observation_error,float(np.abs(actual[k][0]-record["actual_observation"][k]).max()),
                                                        float(np.abs(observed[k][0]-record["observation"][k]).max()))
                            replay.step([record["action"]]); physical += 1
                            state_error = max(state_error,float(np.abs(pack(replay)[0]-record["next_state"]).max()))
                        physics_cases += 1
                    actor,_ = checkpoint(row["source"])
                    if row["method"] == METHOD: actor = RangeSupervisor(actor)
                    for record in frames:
                        budget()
                        if actions >= 19800: raise BudgetStop("action_replay_cap")
                        obs = {k:np.asarray([v]) for k,v in record["observation"].items()}
                        applied = actor.act(obs)[0]; actions += 1
                        action_error = max(action_error,float(np.abs(applied-record["action"]).max()))
                        if int(actor.memory.phase[0]) != record["phase"]: raise AssertionError("phase replay differs")
                        if row["method"] == METHOD and actor.last != record["supervision"]:
                            raise AssertionError("supervisor/proposal/clock replay differs")
                    action_cases += 1
        if state_error or action_error or observation_error: raise AssertionError("independent replay differs")
    except BudgetStop as e:
        stopped = str(e)
    finally:
        ReferenceController.act = original_reference
    healthy_exact = True
    with zipfile.ZipFile(OUTPUT/"traces.zip") as archive:
        for source in ("phase_memory-7","phase_memory-19","phase_memory-41"):
            pair = [r for r in rows if r["source"] == source and r["pattern"] == "healthy"]
            if len(pair) != 2: healthy_exact = False; continue
            a,b = [json.loads(gzip.decompress(archive.read(r["trace"]))) for r in pair]
            healthy_exact &= len(a["frames"]) == len(b["frames"]) and all(
                x["phase"] == y["phase"] and x.get("action") == y.get("action") and x["state"] == y["state"]
                for x,y in zip(a["frames"],b["frames"]))
    complete = stopped is None and len(rows) == 33 and physics_cases == 27 and action_cases == 33
    supervised = [r for r in rows if r["method"] == METHOD]
    result = {"kind":"missing-range-training-pilot-v1","plan":plan,"cases":rows,
              "complete":complete,"budget_stop":stopped,
              "advance_hypothesis":complete and healthy_exact and all(r["criterion_passed"] for r in supervised),
              "healthy_exact":bool(healthy_exact),"environment_decisions":decisions,"neural_queries":queries,
              "physics_replay_decisions":physical,"physics_replay_cases":physics_cases,
              "action_replay_queries":actions,"action_replay_cases":action_cases,
              "max_state_error":state_error,"max_action_error":action_error,"max_observation_error":observation_error,
              "reference_controller_queries":0,"teacher_training_queries":0,"optimiser_updates":0,"held_out_cases":0,
              "active_wall_s":time.monotonic()-started,
              "trace_archive_sha256":hashlib.sha256((OUTPUT/"traces.zip").read_bytes()).hexdigest(),
              "source_archive_sha256":hashlib.sha256((OUTPUT/"source.zip").read_bytes()).hexdigest(),
              "admission":"not admitted; training-partition pilot only"}
    (OUTPUT/"report.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print("Complete",complete,"advance",result["advance_hypothesis"],"decisions",decisions,
          "physics replay",physical,"wall",round(result["active_wall_s"],2),flush=True)


if __name__ == "__main__":
    execute()
