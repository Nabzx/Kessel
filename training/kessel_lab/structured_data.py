"""Complete working episodes and distinct prepared failure fixtures for ADR-0081."""
from dataclasses import asdict, replace
import copy
import hashlib

import numpy as np

from kessel_training.environment import LoaderEnv, SceneConfig
from kessel_training.kinematics import components, footprints
from kessel_training.reference_audit import initial_status
from kessel_training.wm_state import pack
from .structured_model import sample_height


def fixture(kind,seed):
    env = LoaderEnv(1,seed=seed,scene=SceneConfig(randomise=True))
    if kind == "collision":
        front = float(footprints(env.pose,env.joints)[0,...,0].max())
        gap = float(np.random.default_rng(seed+617).uniform(.3,1.2))
        env.scene = replace(env.scene,obstacles=((front+gap,front+gap+.1,-4.2,4.2),))
    elif kind == "stuck":
        i,j = np.unravel_index(np.argmax(env.pile.height[0]),(8,8))
        env.pose[0,:2] = env.pile.origin[0]+np.array([(i+.5)*.5-3.4,(j+.5)*.5])
        env.joints[0] = (0,-.1,.95)
        if env.pile.height[0,i,j] <= .5: raise ValueError("stuck fixture lacks a high front cell")
    else: raise ValueError("unknown prepared fixture")
    env.initial_pose[:] = env.pose
    if not initial_status(env)[0]["valid"]: raise ValueError("prepared geometry is invalid")
    env._update_observations(np.array([True]),reset=True)
    return env


def collect_fixture(kind,seed,budget):
    env = fixture(kind,seed); initial = pack(env)[0].tolist(); rows = []
    while True:
        budget.charge("environment"); obs = env.observe(); before = pack(env)[0].tolist(); action = np.array([[1.,0,0,0]])
        _,reward,term,trunc,info = env.step(action)
        rows.append({"t_s":before[10],"state":before,"next_state":pack(env)[0].tolist(),"observation":{k:v[0].tolist() for k,v in obs.items()},
                     "action":action[0].tolist(),"reward":float(reward[0]),"phase":0,
                     "transfer":{k:float(info["transfer"][k][0]) for k in ("loaded_kg","delivered_kg","spilled_kg")}})
        if (term|trunc)[0]: break
    reason = str(env.reason[0]); final = {"state":pack(env)[0].tolist(),"t_s":float(env.elapsed[0]),"phase":0,
                    "observation":{k:v[0].tolist() for k,v in env.observe().items()}}
    expected = reason.startswith("obstacle") if kind == "collision" else reason == "stuck"
    payload = {"scenario":{"seed":seed,"family":"prepared_"+kind,"scene":asdict(env.scene),"prepared_start":True,
        "initial_state_sha256":hashlib.sha256(np.asarray(initial,dtype="<f8").tobytes()).hexdigest(),
        "initial_pile_sha256":env.initial_pile_hashes[0]},"outcome":{"reason":reason,"done":True,"full_success":False,
        "collision":reason.startswith(("tunnel","obstacle")),"decisions":len(rows),"initial_payload_kg":0.},
        "frames":rows+[final],"source":"fixed_action_failure_fixture","applied_machine_commands":False,"fixture_gate_passed":expected}
    replay = fixture(kind,seed)
    for record in rows:
        budget.charge("replay"); replay.step([record["action"]])
        if pack(replay)[0].tolist() != record["next_state"]: raise AssertionError("fixture physics replay differs")
    return payload


def arrays(episodes):
    columns = {k:[] for k in ("state","action","next_state","reward","events","regime","episode_id","step")}
    metadata = []
    for episode in episodes:
        frames = episode["frames"]; outcome = episode["outcome"]; start = len(columns["state"]); index = len(metadata)
        if len(frames) != outcome["decisions"]+1: raise ValueError("incomplete model episode")
        for step,(current,following) in enumerate(zip(frames,frames[1:])):
            if current["next_state"] != following["state"]: raise ValueError("model episode contains a broken transition")
            state = np.asarray(current["state"]); target = np.asarray(current["next_state"])
            done = bool(outcome["done"] and step == len(frames)-2)
            collision = done and bool(outcome["collision"]); stuck = done and outcome["reason"] == "stuck"
            g = components(state[None,:3],state[None,4:7]); transfer = sum(current["transfer"].values())
            contact = bool(sample_height(state[None],g["mouth"])[0] > g["bucket_height"][0] or transfer > 1e-6)
            values = {"state":state,"next_state":target,"action":current["action"],"reward":current["reward"],
                "events":[done and outcome["reason"] != "time_limit",done and outcome["reason"] == "time_limit",contact,collision],
                "regime":3 if collision or stuck else 2 if transfer > 1e-6 else 1 if contact else 0,"episode_id":index,"step":step}
            for key,value in values.items(): columns[key].append(value)
        metadata.append({"id":index,"start":start,"stop":len(columns["state"]),"seed":episode["scenario"]["seed"],
                         "family":episode["scenario"]["family"],"reason":outcome["reason"],"done":outcome["done"],
                         "source":episode.get("source","conventional_progress_task")})
    return {k:np.asarray(v) for k,v in columns.items()},metadata
