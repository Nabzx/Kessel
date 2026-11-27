"""Complete conventional task/stop traces, including actual sensor faults."""
import copy

import numpy as np

from kessel_training.wm_state import pack
from .clearance_stop import synthetic_clearance
from .progress_supervisor import ProgressSupervisor
from .range_pilot import stop_metrics
from .runtime import environment


def frame(env,actor):
    return {"t_s":float(env.elapsed[0]),"state":pack(env)[0].tolist(),"phase":int(actor.memory.phase[0]),
            "wheel_angles_rad":env.wheel_angles[0].tolist()}


def run(family,seed,budget,pattern=None,replay=False):
    env,scenario = environment(family,seed); actor = ProgressSupervisor(); records = []
    fault_start = None; loss_start = None; settled = None; slow = 0; done = False; override_count = 0; resumed = False; previous_override = False
    stop_check = family in ("blocked","range_dropout") or pattern == "carry_loss"
    end = None; mass_error = 0.
    while not done:
        budget.charge("environment"); budget.charge("teacher")
        actual = env.observe(); observed = {k:v.copy() for k,v in actual.items()}; now = float(env.elapsed[0])
        if pattern and fault_start is None and actor.task.mode == "carry" and actual["proprio"][0,4] <= -.5: fault_start = now
        injected = fault_start is not None and (pattern != "recovery" or now-fault_start < 2.-1e-8)
        if injected:
            observed["range_valid"][:] = 0; observed["proprio"][0,12] = 0; observed["proprio"][0,11] = now-fault_start+.1
        packet = synthetic_clearance(env); action = actor.act(observed,packet)
        overridden = actor.last["override"]; override_count += overridden
        resumed |= previous_override and not overridden; previous_override = overridden
        active = bool(injected or family == "range_dropout" or not actor.last["clearance"]["usable"])
        if active and loss_start is None: loss_start = now
        before = frame(env,actor)
        before.update(observation={k:v[0].tolist() for k,v in observed.items()},actual_observation={k:v[0].tolist() for k,v in actual.items()},
                      clearance=packet,supervision=copy.deepcopy(actor.last),fault={"active":active,"started_s":loss_start,"injected":injected},action=action[0].tolist())
        _,reward,term,trunc,info = env.step(action); done = bool((term|trunc)[0])
        before.update(next_state=pack(env)[0].tolist(),reward=float(reward[0]),transfer={k:float(info["transfer"][k][0]) for k in ("loaded_kg","delivered_kg","spilled_kg")})
        records.append(before)
        mass_error = max(mass_error,abs(float(env.pile.mass()[0]+env.payload[0]+env.delivered[0]+env.spilled[0]-env.pile.initial_mass[0])))
        if mass_error > 1e-7: raise AssertionError("material ledger differs")
        if overridden:
            if len(records) == 1 or not records[-2]["supervision"]["override"]: slow = int(abs(before["state"][3]) <= .08)
            slow = slow+1 if abs(float(env.speed[0])) <= .08 else 0
            if settled is None and slow >= 3: settled = float(env.elapsed[0])
            if settled is not None and float(env.elapsed[0])-settled >= 10.-1e-8:
                end = "hold_window"; break
        else: slow = 0; settled = None
    final = frame(env,actor); final["observation"] = {k:v[0].tolist() for k,v in env.observe().items()}
    reason = str(env.reason[0]); collision = reason.startswith(("tunnel","obstacle"))
    stopping = stop_metrics(records,final,done) if stop_check else None
    if stopping:
        detection = .3 if family == "range_dropout" or pattern == "carry_loss" else .1
        stopping["passed"] = bool(stopping["passed"] and stopping["hold_s"] >= 10.-1e-8 and stopping["detected_s"]-stopping["loss_s"] <= detection+1e-8)
    passed = bool(stopping and stopping["passed"] and not collision) if stop_check else bool(done and reason == "success" and not collision)
    if pattern == "recovery": passed &= bool(fault_start is not None and override_count and resumed)
    outcome = {"reason":reason,"done":done,"end_reason":end or "environment_terminal","collision":collision,"full_success":done and reason == "success",
        "decisions":len(records),"initial_payload_kg":0.,"delivered_kg":float(env.delivered[0]),"carried_kg":float(env.payload[0]),
        "peak_load_kg":float(env.peak_load[0]),"spilled_kg":float(env.spilled[0]),"cycle_s":float(env.elapsed[0]),"max_mass_residual_kg":mass_error}
    evaluation = {"criterion":"stop" if stop_check else "delivery","passed":passed,"stop":stopping,"override_decisions":override_count,
                  "resumed":resumed,"fault_trigger_s":fault_start}
    if replay:
        independent,_ = environment(family,seed); controller = ProgressSupervisor()
        for record in records:
            budget.charge("replay")
            assert synthetic_clearance(independent) == record["clearance"]
            assert {k:v[0].tolist() for k,v in independent.observe().items()} == record["actual_observation"]
            obs = {k:np.asarray([v]) for k,v in record["observation"].items()}
            assert controller.act(obs,record["clearance"])[0].tolist() == record["action"]
            assert controller.last == record["supervision"]
            independent.step([record["action"]]); assert pack(independent)[0].tolist() == record["next_state"]
    return {"source":"conventional_progress_task","scenario":scenario,"pattern":pattern,"outcome":outcome,"evaluation":evaluation,
            "frames":records+[final],"applied_machine_commands":False,"neural_queries":0}
