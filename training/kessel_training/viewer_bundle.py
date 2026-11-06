"""Validate browser experiment records without importing numerical/training libraries."""

import hashlib
import json
import math

VERSION="1.0"
UNITS={"position":"m","angle":"rad","mass":"kg","time":"s","action":"normalised [-1,1]","reward":"dimensionless","disagreement":"dimensionless, not probability"}


def require(condition, message):
    if not condition:raise ValueError(message)


def finite(value):
    if isinstance(value,dict):
        for v in value.values():finite(v)
    elif isinstance(value,list):
        for v in value:finite(v)
    elif isinstance(value,(int,float)):
        require(math.isfinite(value),"non-finite bundle value")


def sha(value):
    return isinstance(value,str) and len(value)==64 and all(c in "0123456789abcdef" for c in value)


def validate(bundle):
    finite(bundle)
    require(bundle.get("schema_version")==VERSION and bundle.get("source_mode")=="recorded_synthetic","unsupported recorded bundle")
    require(bundle.get("units")==UNITS,"bundle units differ")
    run=bundle["run"];require(sha(run["configuration_sha256"]) and sha(run["source"]["package_sha256"]) and run["source"]["training_dirty"] is False,"unverified training identity")
    require(bundle["export_source"]["training_dirty"] is False,"uncommitted export source")
    curve=bundle["learning_curve"];previous=0
    for row in curve:
        require(row["environment_steps"]>previous,"training curve is not monotone")
        previous=row["environment_steps"]
    require(previous==run["counters"]["environment_steps"],"training counters do not reconcile")
    require(len(bundle["state_names"])==102 and len(bundle["action_names"])==4,"state/action schema differs")
    require(sha(bundle["world_model"]["model_sha256"]),"model hash missing")
    require(bundle["world_model"]["kind"]=="raw_neural_ensemble","unidentified model correction")
    require(len(bundle["episodes"])==3,"initial/intermediate/final episodes required")
    for ep in bundle["episodes"]:
        require(sha(ep["policy"]["checkpoint_sha256"]) and sha(ep["policy"]["source_checkpoint_sha256"]),"executed checkpoint identity missing")
        records=ep["records"];require(len(records)>=2 and ep["terminated"] != ep["truncated"],"episode boundary missing")
        require(records[0]["t_s"]==0 and records[-1]["action"] is None,"episode endpoints differ")
        require(ep["steps"]==len(records)-1,"episode decision count differs")
        previous=-1
        for i,row in enumerate(records):
            require(row["t_s"]>previous and len(row["state"])==102 and len(row["observation"])==65 and len(row["wheel_angles_rad"])==4,"record shape/time differs")
            require(abs(row["t_s"]-row["state"][10])<1e-9,"state and record timestamps differ")
            previous=row["t_s"]
            if i<len(records)-1:
                action=row["action"];require(isinstance(action,list) and len(action)==4 and all(-1<=v<=1 for v in action),"invalid recorded action")
                require(row["reward"] is not None and set(row["reward_terms"])=={"delivered_kg","spilled_kg","elapsed_s","effort_proxy_j","collision_count","slip_s"},"reward decomposition missing")
            else:require(row["reward"] is None,"terminal record has invented next reward")
            for p in row["predictions"]:
                h=p["horizon_decisions"];require(h in (1,2,4,8),"unknown prediction horizon")
                target=i+h
                if p["prediction"] is None:
                    require(p["missing_reason"] is not None and p["residual"] is None,"invented missing prediction")
                    continue
                require(target<len(records) and p["reference_index"]==target,"forecast crosses episode")
                require(abs(p["target_t_s"]-records[target]["t_s"])<1e-9,"forecast timestamp differs")
                state=p["prediction"];reference=records[target]["state"]
                require(len(state)==102 and len(p["members_xy_m"])==3 and all(len(v)==2 for v in p["members_xy_m"]),"forecast shape differs")
                position=math.hypot(state[0]-reference[0],state[1]-reference[1])
                require(abs(position-p["residual"]["position_m"])<1e-9,"invented position residual")
                require(abs(state[7]-reference[7]-p["residual"]["carried_kg"])<1e-9,"invented mass residual")
                reward=sum(records[j]["reward"] for j in range(i,target))
                require(abs(p["cumulative_reward"]-reward-p["residual"]["reward"])<1e-9,"invented reward residual")
    return {"episodes":len(bundle["episodes"]),"decisions":sum(e["steps"] for e in bundle["episodes"]),"predictions":sum(sum(p["prediction"] is not None for p in r["predictions"]) for e in bundle["episodes"] for r in e["records"])}
