"""ADR-0068: repeat the frozen practice suite with observed-motion holding."""
import copy
from dataclasses import asdict
import gzip
import hashlib
import json
import subprocess
import time
import zipfile

import numpy as np
import torch
from kessel_training.controller import ReferenceController
from kessel_training.environment import LoaderEnv, SceneConfig
from kessel_training.phase_memory import PhaseMemory
from kessel_training.policy import configure_cpu
from kessel_training.reference_audit import initial_status
from kessel_training.wm_state import pack
from .motion_hold import METHOD, MotionHoldSupervisor as CompleteRangeSupervisor
from .range_pilot import stop_metrics, weights
from .runtime import ROOT, Run, digest

OUTPUT = ROOT/".local/observed-motion-hold-pilot-2026-11-25"
PATTERNS = ("healthy","transient","recovery","partial_reset_retained","partial_reset_zeroed",
            "partial_fill_retained","partial_fill_zeroed","partial_lift_retained","partial_lift_zeroed",
            "partial_carry_retained","partial_carry_zeroed","carry_loss")


def jobs():
    rows = []
    for seed in (7,19,41):
        base = {"source":"phase_memory-"+str(seed),"seed":19000,"method":METHOD}
        for pattern in PATTERNS:
            rows.append({**base,"kind":"task","pattern":pattern,
                         "criterion":"stop" if pattern.startswith("partial_") or pattern == "carry_loss" else "delivery"})
        for grade in (-.06,.06):
            for speed in (-.8,.8):
                rows.append({**base,"kind":"stop_fixture","pattern":"fixture_loss","criterion":"stop",
                             "grade_rad":grade,"initial_speed_m_s":speed,"initial_payload_kg":2500.})
    rows += [{"source":"phase_memory-"+str(seed),"seed":19000,"method":"original",
              "kind":"task","pattern":"healthy","criterion":"delivery"} for seed in (7,19,41)]
    return rows


def make_run(job):
    run = Run("nominal",job["seed"],job["source"])
    if job["kind"] == "stop_fixture":
        scene = SceneConfig(randomise=False,grade_rad=job["grade_rad"])
        env = LoaderEnv(1,seed=job["seed"],scene=scene)
        env.pose[0] = (0,0,0); env.initial_pose[0] = env.pose[0]
        env.joints[0] = (0,.35,.95); env.speed[0] = job["initial_speed_m_s"]
        mass = float(env.pile.mass()[0]); load = job["initial_payload_kg"]
        if mass <= load: raise ValueError("insufficient fixture material")
        env.pile.height[0] *= (mass-load)/mass
        env.payload[0] = env.peak_load[0] = load
        env._update_observations(np.array([True]),reset=True)
        if not initial_status(env)[0]["valid"]: raise ValueError("invalid fixture geometry")
        run.env = env
        run.actor.memory.phase[0] = 3
        run.scenario = {"kind":"declared nonempty stopping fixture","scene":asdict(scene),"job":job,
                        "initial_state_sha256":hashlib.sha256(pack(env).astype("<f8").tobytes()).hexdigest()}
    if job["method"] == METHOD: run.actor = CompleteRangeSupervisor(run.actor)
    return run


class SpatialFault:
    def __init__(self, pattern):
        self.pattern = pattern; self.trigger = PhaseMemory(); self.started = None
        self.last_crop = np.zeros((1,5,5))

    def apply(self, actual):
        obs = {k:v.copy() for k,v in actual.items()}; p = actual["proprio"][0]
        phase = int(self.trigger.update(actual)[0]); now = float(p[13]); pattern = self.pattern
        moving = phase == 3 and p[4] <= -.5
        if self.started is None:
            hit = (pattern == "fixture_loss" or pattern.startswith("partial_reset_") or
                   pattern == "transient" and now >= 1.-1e-9 or
                   pattern.startswith("partial_fill_") and phase == 1 or
                   pattern.startswith("partial_lift_") and phase == 2 or
                   (pattern.startswith("partial_carry_") or pattern in ("carry_loss","recovery")) and moving)
            if hit: self.started = now
        duration = .1 if pattern == "transient" else 2. if pattern == "recovery" else float("inf")
        active = self.started is not None and now-self.started < duration-1e-9
        if active and pattern.startswith("partial_"):
            obs["range_valid"][:,:2,:] = 0
            if pattern.endswith("zeroed"): obs["local_height_m"][:,:2,:] = 0
        elif active:
            obs["range_valid"][:] = 0; obs["local_height_m"] = self.last_crop.copy()
            obs["proprio"][0,12] = 0
            obs["proprio"][0,11] = now-self.started+(.1 if self.started else 0.)
        else: self.last_crop = actual["local_height_m"].copy()
        return obs,{"active":active,"started_s":self.started,"trigger_phase":phase}


def stopping(records, final, done):
    result = stop_metrics(records,final,done)
    if result:
        result["passed"] = bool(result["passed"] and result["detected_s"]-result["loss_s"] <= .1+1e-8
                                and result["hold_s"] >= 10.-1e-8)
    return result


def execute():
    configure_cpu(7,threads=1); OUTPUT.mkdir(parents=True,exist_ok=False)
    paths = sorted((ROOT/"training/kessel_training").glob("*.py"))
    paths += [ROOT/n for n in ("training/kessel_lab/runtime.py","training/kessel_lab/range_supervisor.py",
        "training/kessel_lab/range_contract.py","training/kessel_lab/range_pilot.py","training/kessel_lab/motion_hold_pilot.py","training/kessel_lab/motion_hold.py",
        "training/uv.lock","docs/adr/0066-spatial-range-contract-and-pilot.md",
        "docs/adr/0068-observed-motion-holding-pilot.md",
        "docs/phase-11/phase-memory-evidence/selection.json","docs/phase-11/spatial-range-evidence/report.json")]
    files = {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    plan = {"protocol":"ADR-0068","cases":jobs(),"files":files,"cpu_threads":1,"wall_cap_s":150,
            "evaluation_cap":30000,"physics_replay_cap":28800,"action_replay_cap":30600,"trace_archive_cap":16*1024**2,
            "commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
            "software":{"torch":str(torch.__version__),"numpy":np.__version__}}
    (OUTPUT/"plan.json").write_text(json.dumps(plan,indent=2)+"\n")
    with zipfile.ZipFile(OUTPUT/"source.zip","w",compression=zipfile.ZIP_DEFLATED) as z:
        for p in paths: z.write(p,p.relative_to(ROOT))
    started = time.monotonic(); rows = []; decisions = physics = queries = 0
    physical_cases = action_cases = 0; state_error = action_error = observation_error = 0.; stop = None; trace_bytes = 0
    class BudgetStop(Exception): pass
    def budget():
        if time.monotonic()-started >= 150: raise BudgetStop("wall_cap")
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
                        if decisions >= 30000: raise BudgetStop("evaluation_cap")
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
                if trace_bytes+len(raw)+20000 > 16*1024**2: raise BudgetStop("trace_archive_cap")
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
                            if physics >= 28800: raise BudgetStop("physics_replay_cap")
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
                        if queries >= 30600: raise BudgetStop("action_replay_cap")
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
        for s in (7,19,41):
            pair = [r for r in rows if r["source"] == "phase_memory-"+str(s) and r["pattern"] == "healthy"]
            if len(pair) != 2: exact = False; continue
            a,b = [json.loads(gzip.decompress(z.read(c["trace"]))) for c in pair]
            exact &= len(a["frames"]) == len(b["frames"]) and all(x["state"] == y["state"] and x["phase"] == y["phase"] and x.get("action") == y.get("action") for x,y in zip(a["frames"],b["frames"]))
    complete = stop is None and len(rows) == 51 and physical_cases == 48 and action_cases == 51
    r = {"kind":"observed-motion-holding-practice-v1","plan":plan,"cases":rows,"complete":complete,"budget_stop":stop,
         "advance_hypothesis":bool(complete and exact and all(c["criterion_passed"] for c in rows)),"healthy_exact":bool(exact),
         "environment_decisions":decisions,"neural_queries":decisions,"physics_replay_decisions":physics,"physics_replay_cases":physical_cases,
         "action_replay_queries":queries,"action_replay_cases":action_cases,"max_state_error":state_error,
         "max_action_error":action_error,"max_observation_error":observation_error,
         "teacher_queries":0,"optimiser_updates":0,"held_out_cases":0,"active_wall_s":time.monotonic()-started,
         "trace_archive_sha256":hashlib.sha256((OUTPUT/"traces.zip").read_bytes()).hexdigest(),
         "source_archive_sha256":hashlib.sha256((OUTPUT/"source.zip").read_bytes()).hexdigest(),
         "admission":"not admitted; observed-motion practice pilot only"}
    (OUTPUT/"report.json").write_text(json.dumps(r,indent=2,allow_nan=False)+"\n")
    print("Complete",complete,"advance",r["advance_hypothesis"],"decisions",decisions,"replay",physics,"wall",round(r["active_wall_s"],2),flush=True)


if __name__ == "__main__": execute()
