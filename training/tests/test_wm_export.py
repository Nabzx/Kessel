import copy

import numpy as np
import pytest

from kessel_training.wm_data import collect_split, logical_hash
from kessel_training.wm_export import export_examples, verify_residuals
from kessel_training.wm_state import PILE_END


class IdentityFixture:
    def predict(self, states, actions):
        out = states.copy();out[:, 0] += 0.01
        return {"next_state": out, "reward": np.zeros(len(states)), "events": np.zeros((len(states), 4)),
                "disagreement": np.full(len(states), 0.3)}


def test_prediction_export_keeps_real_pairs_and_missing_horizons():
    arrays, episodes = collect_split("test", {"reference": 3, "random": 2, "policy": 2})
    manifest = {"episodes": episodes, "logical_sha256": logical_hash(arrays, episodes)}
    bundle = export_examples(IdentityFixture(), {"model_sha256": "test-fixture"}, arrays, manifest)
    assert verify_residuals(bundle) > 0
    assert any(row["prediction"] is None for example in bundle["examples"] for row in example["predictions"])
    changed = copy.deepcopy(bundle)
    first = next(row for e in changed["examples"] for row in e["predictions"] if row["residual"] is not None)
    first["residual"]["state"][0] += 1
    with pytest.raises(ValueError, match="residual"):
        verify_residuals(changed)
