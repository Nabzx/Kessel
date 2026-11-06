import json

import numpy as np
import pytest

from kessel_training.wm_experiment import DEFAULT_PLAN, collection_budgets, policy_configuration


def test_world_model_comparison_charges_offline_data_and_matches_total_real_budget():
    plan = json.loads(DEFAULT_PLAN.read_text())
    for assisted in (False, True):
        config = policy_configuration(plan, 7, assisted)
        real = config.num_envs*config.rollout_steps*config.updates
        assert real+(10240 if assisted else 0) == 40960
        assert not config.curriculum and not config.shaping
    assert plan["splits"]["train"]+plan["splits"]["validation"] == plan["assisted_offline_training_validation_samples"]
    assert collection_budgets(8192, plan["source_fractions"]) == {"reference": 4096, "random": 2048, "policy": 2048}
    with pytest.raises(ValueError):
        collection_budgets(3, plan["source_fractions"])
