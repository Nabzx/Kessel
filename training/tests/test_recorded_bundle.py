"""Re-execute the shipped browser records and saved neural forecasts."""

import copy
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from kessel_training.environment import LoaderEnv, SceneConfig
from kessel_training.evaluation import load_policy
from kessel_training.viewer_bundle import validate
from kessel_training.wm_data import flat_observation
from kessel_training.wm_state import pack
from kessel_training.world_model import load_model

ROOT=Path(__file__).resolve().parents[2]
BUNDLE=ROOT/"data/experiments/loader-v1.json"


def test_shipped_decisions_reproduce_actual_policy_actions_and_reference_states():
    bundle=json.loads(BUNDLE.read_text());assert validate(bundle)=={"episodes":3,"decisions":755,"predictions":916}
    policies={hashlib.sha256(p.read_bytes()).hexdigest():p for p in (ROOT/"docs/phase-11/rl-evidence/policies").glob("*.pt")}
    inferences=0
    for episode in bundle["episodes"]:
        policy,_=load_policy(policies[episode["policy"]["checkpoint_sha256"]])
        env=LoaderEnv(1,seed=episode["seed"],stream_ids=[episode["stream_id"]],scene=SceneConfig(**episode["scene"]))
        for index,row in enumerate(episode["records"]):
            np.testing.assert_allclose(pack(env)[0],row["state"],rtol=1e-9,atol=1e-7)
            if row["action"] is None:continue
            if index<12 or row["events"] or index==episode["steps"]-1:
                actual=policy.sample(policy.encode(env.observe()),deterministic=True)["action"].detach().numpy()[0]
                np.testing.assert_allclose(actual,row["action"],rtol=1e-5,atol=1e-5);inferences+=1
                np.testing.assert_allclose(flat_observation(env.observe())[0],row["observation"],rtol=1e-9,atol=1e-8)
            env.step(np.asarray([row["action"]]))
        assert str(env.reason[0])==episode["outcome"]
    assert inferences>=36


def test_shipped_multistep_forecasts_execute_the_identified_model_and_member_endpoints():
    bundle=json.loads(BUNDLE.read_text());model,identity=load_model(ROOT/"docs/phase-11/world-model-evidence/models/ensemble.pt")
    assert identity["model_sha256"]==bundle["world_model"]["model_sha256"]
    for episode in bundle["episodes"]:
        row=episode["records"][0];current=np.asarray([row["state"]]);stopped=False;reward=0
        records={p["horizon_decisions"]:p for p in row["predictions"]}
        for h in range(1,9):
            if stopped:break
            previous=current.copy();p=model.predict(current,np.asarray([episode["records"][h-1]["action"]]));current=p["next_state"];reward+=p["reward"][0]
            if h in records:
                recorded=records[h]
                np.testing.assert_allclose(current[0],recorded["prediction"],rtol=2e-5,atol=5e-4)
                np.testing.assert_allclose(previous[0,:2]+p["member_changes"][:,0,:2],recorded["members_xy_m"],rtol=2e-5,atol=5e-5)
                assert abs(p["disagreement"][0]-recorded["disagreement"])<1e-4
                assert abs(reward-recorded["cumulative_reward"])<5e-4
            stopped=p["events"][0,:2].max()>=0.5


def test_recorded_schema_rejects_invented_residuals_terminal_actions_and_wrong_source_units():
    original=json.loads(BUNDLE.read_text())
    for mutation in (lambda b:b["units"].update(mass="tonnes"),lambda b:b["run"]["source"].update(training_dirty=True),
                     lambda b:b["episodes"][0]["records"][-1].update(action=[0,0,0,0]),
                     lambda b:b["episodes"][0]["records"][0]["predictions"][0]["residual"].update(position_m=100)):
        bundle=copy.deepcopy(original);mutation(bundle)
        with pytest.raises(ValueError):validate(bundle)
