"""Execute fixed checkpoints, verify action replay and export genuine static playback."""

import argparse
from dataclasses import asdict
import gzip
import hashlib
import json
from pathlib import Path
import platform
import time

import numpy as np
import torch

from . import checkpoints
from .environment import LoaderEnv
from .evaluation import load_policy
from .evaluate import source_identity
from .rewards import UNITS as REWARD_UNITS
from .scenarios import family
from .viewer_bundle import UNITS, validate
from .wm_data import flat_observation
from .wm_state import pack, STATE_NAMES, violations
from .world_model import load_model

ROOT=Path(__file__).resolve().parents[2]


def row(env):
    return {"t_s":float(env.elapsed[0]),"state":pack(env)[0].tolist(),
        "observation":flat_observation(env.observe())[0].tolist(),"wheel_angles_rad":env.wheel_angles[0].tolist(),
        "action":None,"reward":None,"reward_terms":None,"events":[],"predictions":[]}


@torch.no_grad()
def episode(policy_path,label,scene,seed):
    policy,identity=load_policy(policy_path)
    env=LoaderEnv(1,seed=seed,stream_ids=[0],scene=scene);records=[]
    scenario=env.scenario_identity()[0]
    while True:
        record=row(env);action=policy.sample(policy.encode(env.observe()),deterministic=True)["action"].numpy()
        _,reward,term,trunc,info=env.step(action)
        record.update(action=action[0].tolist(),reward=float(reward[0]),
            reward_terms={k:float(v[0]) for k,v in info["reward_terms"].items()},
            events=[k for k in ("loaded_kg","delivered_kg","spilled_kg") if info["transfer"][k][0]>0])
        if info["metrics"]["collision_time_s"][0]>=0:record["events"].append("collision")
        records.append(record)
        if (term|trunc).any():break
    final=row(env);final["events"]=[str(env.reason[0])];records.append(final)
    metrics={k:v[0].item() for k,v in info["metrics"].items()}
    result={"id":label,"name":{"initial":"Initial","intermediate":"Intermediate","final":"Final"}[label],
        "seed":seed,"stream_id":0,"scene":asdict(scene),"scenario_sha256":scenario,"policy":identity,
        "terminated":bool(term[0]),"truncated":bool(trunc[0]),"outcome":str(env.reason[0]),
        "steps":len(records)-1,"metrics":metrics,"records":records}
    # Execute recorded actions independently; file presence cannot establish provenance.
    replay=LoaderEnv(1,seed=seed,stream_ids=[0],scene=scene)
    max_error=0.0
    for current,next_record in zip(records,records[1:]):
        np.testing.assert_allclose(pack(replay)[0],current["state"],rtol=0,atol=1e-10)
        replay.step(np.asarray([current["action"]]))
        error=float(np.abs(pack(replay)[0]-next_record["state"]).max());max_error=max(error,max_error)
        if error>1e-9:raise ValueError("recorded actions do not reproduce exported reference state")
    result["action_replay"]={"decisions":len(records)-1,"max_state_absolute_error":max_error}
    return result


def forecasts(ep,model):
    records=ep["records"];states=np.asarray([r["state"] for r in records[:-1]])
    actions=np.asarray([r["action"] for r in records[:-1]])
    for index,record in enumerate(records[:-1]):
        horizons=(1,2,4,8) if index%20==0 or record["events"] or index==len(records)-2 else (1,)
        current=states[index:index+1].copy();total=0.0;stop=False
        for h in range(1,max(horizons)+1):
            j=index+h-1
            p=None
            if j<len(records)-1 and not stop:
                before=current.copy();p=model.predict(current,actions[j:j+1]);current=p["next_state"];total+=float(p["reward"][0])
                stop=bool(p["events"][0,:2].max()>=0.5)
            if h not in horizons:continue
            item={"horizon_decisions":h,"nominal_horizon_s":h*0.1,"reference_index":index+h if index+h<len(records) else None,
                "target_t_s":records[index+h]["t_s"] if index+h<len(records) else None,"prediction":None,
                "residual":None,"missing_reason":"reference_episode_ended" if index+h>=len(records) else "model_event_stop" if p is None else None}
            if p is not None:
                reference=np.asarray(records[index+h]["state"]);raw=violations(current)
                members=(before[0,:2]+p["member_changes"][:,0,:2]).tolist()
                item.update(prediction=current[0].tolist(),cumulative_reward=total,
                    event_probabilities=p["events"][0].tolist(),disagreement=float(p["disagreement"][0]),members_xy_m=members,
                    residual={"position_m":float(np.linalg.norm(current[0,:2]-reference[:2])),"carried_kg":float(current[0,7]-reference[7]),
                        "reward":total-sum(records[k]["reward"] for k in range(index,index+h)),"clock_s":float(current[0,10]-reference[10])},
                    violations={k:float(v[0]) if k=="mass_error_kg" else bool(v[0]) for k,v in raw.items()})
            record["predictions"].append(item)


def export(output,report_path=None):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    source=source_identity()
    if source["training_dirty"]:raise ValueError("commit training source before exporting")
    started=time.perf_counter();evidence=ROOT/"docs/phase-11/rl-evidence"
    study=evidence/"runs.json"
    run=next(r for r in json.loads(study.read_text()) if r["name"]=="full-7")
    run["learning_curve"]=json.loads(gzip.decompress((evidence/"learning-curves.json.gz").read_bytes()))["full-7"]
    scene,_=family("standard")
    model,model_identity=load_model(ROOT/"docs/phase-11/world-model-evidence/models/ensemble.pt")
    episodes=[]
    for label in ("initial","intermediate","final"):
        path=evidence/"policies"/f"replay-{label}-7.pt"
        ep=episode(path,label,scene,100000);forecasts(ep,model);episodes.append(ep)
    curve=[{k:r[k] for k in ("rollout","environment_steps","completed_episodes","mean_step_reward","collection_s","update_s","training_stage","reward_components")}
           for r in run["learning_curve"]]
    bundle={"schema_version":"1.0","source_mode":"recorded_synthetic","run_id":"rl-study-v1-full-7",
        "export_source":source,"units":UNITS,"state_names":STATE_NAMES,
        "action_names":["acceleration","articulation rate","boom rate","bucket rate"],"reward_units":REWARD_UNITS,
        "run":{k:run[k] for k in ("configuration","configuration_sha256","source","network","counters","training_wall_s","stop_reason")},
        "learning_curve":curve,"world_model":{"kind":"raw_neural_ensemble","model_sha256":model_identity["model_sha256"],
            "training_source":model_identity["training"]["source"],"members":3,"uncertainty_method":"RMS ensemble std of normalised outputs; dimensionless, not probability",
            "envelope_method":"Final-step conditional member endpoint spread in metres; not cumulative horizon covariance or calibrated confidence"},
        "presentation":{"replay_seconds":12,"checkpoint_seconds":4,"decimation":"none; every action, contact and terminal boundary retained",
            "limitations":"No complete learned cycle; raw forecasts can violate physics. Mine business figures remain illustrative."},
        "episodes":episodes}
    counts=validate(bundle);raw=json.dumps(bundle,separators=(",",":"),allow_nan=False).encode()
    output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(raw+b"\n")
    index={"schema_version":"1.0","experiments":[{"run_id":bundle["run_id"],"url":str(output.relative_to(ROOT)),
        "sha256":hashlib.sha256(output.read_bytes()).hexdigest(),"bytes":output.stat().st_size,"source_mode":"recorded_synthetic"}]}
    (output.parent/"index.json").write_text(json.dumps(index,indent=2)+"\n")
    report={**counts,"source":source,"export_wall_s":time.perf_counter()-started,"bytes":len(raw)+1,"gzip_bytes":len(gzip.compress(raw,mtime=0)),
        "decimation_max_position_error_m":0,"decimation_max_material_error_kg":0,"dropped_decisions":0,
        "action_replay_max_error":max(e["action_replay"]["max_state_absolute_error"] for e in episodes),
        "platform":platform.platform(),"training_source":run["source"],"run_report_sha256":run["raw_report_sha256"],"retained_runs_sha256":hashlib.sha256(study.read_bytes()).hexdigest()}
    if report_path:Path(report_path).write_text(json.dumps(report,indent=2)+"\n")
    return report


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--output",type=Path,required=True);parser.add_argument("--report",type=Path)
    args=parser.parse_args();print(json.dumps(export(args.output,args.report)))
