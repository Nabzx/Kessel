from dataclasses import replace
from pathlib import Path

from kessel_training.export_viewer import episode, forecasts
from kessel_training.scenarios import family
from kessel_training.world_model import load_model

ROOT=Path(__file__).resolve().parents[2]


def test_executed_policy_export_uses_outgoing_actions_and_independent_exact_replay():
    scene=replace(family("standard")[0],max_steps=2)
    ep=episode(ROOT/"docs/phase-11/rl-evidence/policies/replay-final-7.pt","final",scene,100000)
    assert ep["steps"]==2 and ep["truncated"] and not ep["terminated"]
    assert len(ep["records"])==3 and ep["records"][0]["t_s"]==0
    assert ep["records"][-1]["action"] is None and ep["records"][-1]["reward"] is None
    assert ep["action_replay"]["max_state_absolute_error"]==0
    model,_=load_model(ROOT/"docs/phase-11/world-model-evidence/models/ensemble.pt")
    forecasts(ep,model)
    assert ep["records"][0]["predictions"][0]["reference_index"]==1
    assert ep["records"][0]["predictions"][-1]["missing_reason"]=="reference_episode_ended"
