"""ADR-0073 consumed-practice clearance stopping; no runtime admission."""
from dataclasses import asdict, replace
import copy
import zipfile

import numpy as np

from kessel_training.environment import LoaderEnv, SceneConfig
from kessel_training.kinematics import footprints
from kessel_training.policy import configure_cpu
from kessel_training.wm_state import pack
from .bootstrap_hold_pilot import stopping
from .clearance_stop import LatchedClearanceStop as ClearanceStop, synthetic_clearance
from .runtime import ROOT, checkpoint, environment
from .study_tools import Budget, begin, encode, retain, seal

D = ROOT/"docs/phase-11/clearance-latched-evidence"
KINDS = ("healthy","blocked","forward_loaded","reverse_loaded","stale")


def fixture(kind,seed):
    if kind in ("healthy","blocked","stale"): return environment("blocked" if kind == "blocked" else "nominal",seed)[0]
    env = LoaderEnv(1,seed=seed,scene=SceneConfig(randomise=False,grade_rad=.06 if kind == "forward_loaded" else -.06))
    env.joints[0] = (0,.35,.95); env.speed[0] = .8 if kind == "forward_loaded" else -.8
    env.pile.height[0] *= (env.pile.mass()[0]-2500)/env.pile.mass()[0]
    env.payload[0] = env.peak_load[0] = 2500
    corners = footprints(env.pose,env.joints)[0]
    x = float(corners[...,0].max()+1.2) if kind == "forward_loaded" else float(corners[...,0].min()-1.3)
    env.scene = replace(env.scene,obstacles=((x,x+.1,-4.2,4.2),))
    env._update_observations(np.array([True]),reset=True)
    return env


def frame(env,actor):
    return {"t_s":float(env.elapsed[0]),"state":pack(env)[0].tolist(),
            "phase":int(actor.memory.phase[0]),"wheel_angles_rad":env.wheel_angles[0].tolist()}


def execute():
    configure_cpu(7,threads=1); budget = Budget(119,evaluation=6200,replay=6200)
    names = [str(p.relative_to(ROOT)) for p in (ROOT/"training/kessel_training").glob("*.py")]
    names += ["training/kessel_lab/"+n+".py" for n in ("clearance_stop","clearance_pilot","runtime","bootstrap_hold",
             "range_contract","range_supervisor","motion_hold","bootstrap_hold_pilot","range_pilot")]
    plan = begin(D,"docs/adr/0073-blocked-path-observation-and-stopping.md",names,
                 {"kind":"clearance-stop-practice-v1","bases":[19000,19001],"policy_seeds":[7,19,41],"kinds":list(KINDS),
                  "wall_cap_s":119,"decision_caps":{"evaluation":6200,"replay":6200},"runtime_admitted":False,
                  "preceding_abort":"docs/phase-11/clearance-evidence/report.json",
                  "preceding_pilot":"docs/phase-11/clearance-stop-evidence/report.json"})
    report = {"plan":plan,"cases":[],"complete":False,"errors":[],"budget_stop":None,"teacher_queries":0,"optimiser_updates":0,
              "runtime_admitted":False,"fresh_qualification":False,"max_replay_state_error":0.,"max_mass_residual_kg":0.}
    try:
        with zipfile.ZipFile(D/"traces.zip","w",compression=zipfile.ZIP_STORED) as archive:
            for seed in plan["bases"]:
                for policy in plan["policy_seeds"]:
                    for kind in KINDS:
                        budget.check(); env = fixture(kind,seed); neural,weight_sha = checkpoint("phase_memory-"+str(policy))
                        actor = ClearanceStop(neural); baseline,_ = checkpoint("phase_memory-"+str(policy))
                        records = []; slow = 0; settled = loss = None; healthy_exact = True; done = False
                        initial_mass = float(env.pile.initial_mass[0])
                        while not done:
                            budget.charge("evaluation"); actual = env.observe(); packet = synthetic_clearance(env)
                            if kind == "stale": packet["capture_s"] -= .3
                            action = actor.act(actual,packet); before = frame(env,actor)
                            if kind == "healthy": healthy_exact &= bool(np.array_equal(action,baseline.act(actual)))
                            supervision = copy.deepcopy(actor.last["supervision"])
                            active = not actor.last["clearance"]["usable"]
                            if active and loss is None: loss = float(env.elapsed[0])
                            before.update(observation={k:v[0].tolist() for k,v in actual.items()},clearance=copy.deepcopy(actor.last),
                                          fault={"active":active,"started_s":loss},supervision=supervision,action=action[0].tolist())
                            _,reward,term,trunc,info = env.step(action); done = bool((term|trunc)[0])
                            before.update(next_state=pack(env)[0].tolist(),reward=float(reward[0]),
                                          transfer={k:float(info["transfer"][k][0]) for k in ("loaded_kg","delivered_kg","spilled_kg")})
                            records.append(before)
                            residual = abs(float(env.pile.mass()[0]+env.payload[0]+env.delivered[0]+env.spilled[0])-initial_mass)
                            report["max_mass_residual_kg"] = max(report["max_mass_residual_kg"],residual)
                            if residual > 1e-7: raise AssertionError("material ledger differs")
                            if active:
                                if len(records) == 1 or not records[-2]["fault"]["active"]: slow = int(abs(before["state"][3]) <= .08)
                                slow = slow+1 if abs(float(env.speed[0])) <= .08 else 0
                                if settled is None and slow >= 3: settled = float(env.elapsed[0])
                                if settled is not None and float(env.elapsed[0])-settled >= 10.-1e-8: break
                        final = frame(env,actor); reason = str(env.reason[0]); collision = reason.startswith("obstacle") or reason.startswith("tunnel")
                        metric = stopping(records,final,done) if kind != "healthy" else None
                        passed = bool(reason == "success" and healthy_exact) if kind == "healthy" else bool(metric and metric["passed"] and not collision)
                        replay = fixture(kind,seed); replay_actor = ClearanceStop(checkpoint("phase_memory-"+str(policy))[0])
                        for record in records:
                            budget.charge("replay"); packet = synthetic_clearance(replay)
                            if kind == "stale": packet["capture_s"] -= .3
                            assert packet == record["clearance"]["packet"]
                            assert {k:v[0].tolist() for k,v in replay.observe().items()} == record["observation"]
                            replay_action = replay_actor.act(replay.observe(),packet)
                            assert replay_action[0].tolist() == record["action"]
                            assert replay_actor.last == record["clearance"]
                            replay.step([record["action"]])
                            error = float(np.abs(pack(replay)[0]-record["next_state"]).max())
                            report["max_replay_state_error"] = max(report["max_replay_state_error"],error)
                            assert error == 0
                        outcome = {"reason":reason,"done":done,"collision":collision,"delivered_kg":float(env.delivered[0]),
                                   "full_success":done and reason == "success","decisions":len(records),"passed":passed,
                                   "stop":metric,"healthy_exact":healthy_exact}
                        payload = {"source":"phase_memory-"+str(policy),"seed":seed,"kind":kind,"checkpoint_sha256":weight_sha,
                                   "scene":asdict(env.scene),"outcome":outcome,"frames":records+[final],"applied_machine_commands":False}
                        stored = retain(archive,f"{seed}-{policy}-{kind}.json.gz",payload)
                        report["cases"].append({k:v for k,v in payload.items() if k != "frames"}|stored)
                        print(seed,policy,kind,"pass",passed,reason or "hold_window",flush=True)
        report["complete"] = len(report["cases"]) == 30
    except TimeoutError as error: report["budget_stop"] = str(error)
    except Exception as error: report["errors"].append(type(error).__name__+": "+str(error))
    report["cost"] = budget.report(); report["pilot_passed"] = report["complete"] and all(c["outcome"]["passed"] for c in report["cases"])
    seal(D,report)
    print("clearance pilot",report["pilot_passed"],report["cost"],report["errors"],flush=True)
    if not report["complete"] or report["errors"] or report["budget_stop"]: raise SystemExit(1)


if __name__ == "__main__": execute()
