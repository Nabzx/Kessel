from pathlib import Path
import unittest

import numpy as np

from kessel_lab.forecast_refit import D, operational_gate
from kessel_lab.runtime import environment
from kessel_training.wm_state import pack
from kessel_training.world_model import load_model


class ForecastGateTests(unittest.TestCase):
    def test_low_forecast_error_cannot_admit_impossible_or_filter_rejected_states(self):
        env,_ = environment("nominal",19010); state = pack(env)
        data = {"state":state,"next_state":state.copy(),"action":np.zeros((1,4)),"reward":np.zeros(1),"events":np.zeros((1,4),dtype=bool)}
        gate = {"threshold":1.,"tradeoffs":[{"threshold":1.}]*3}
        class Predictor:
            def __init__(self,negative=False,rejected=False): self.negative = negative; self.rejected = rejected
            def predict(self,state,action):
                following = state.copy()
                if self.negative: following[:,15] = -.0001
                return {"next_state":following,"reward":np.zeros(1),"events":np.zeros((1,4)),"disagreement":np.zeros(1),"filter_rejected":np.array([self.rejected])}
        self.assertEqual(operational_gate(Predictor(),data,gate)["operational_accepted"],1)
        self.assertEqual(operational_gate(Predictor(negative=True),data,gate)["operational_accepted"],0)
        self.assertEqual(operational_gate(Predictor(rejected=True),data,gate)["operational_accepted"],0)


@unittest.skipUnless((D/"refit.pt").exists(),"retained refit not present yet")
class SavedRefitTests(unittest.TestCase):
    def test_saved_weights_reproduce_retained_predictions_and_train_only_normalisers(self):
        model,_ = load_model(D/"refit.pt")
        with np.load(D/"train.npz") as train:
            features = np.column_stack((train["state"],train["action"]))
            np.testing.assert_allclose(model.input_mean.numpy(),features.mean(axis=0),atol=1e-10,rtol=1e-10)
        with np.load(D/"evaluation.npz") as data, np.load(D/"predictions-refit_raw.npz") as retained:
            rows = np.linspace(0,len(data["state"])-1,16,dtype=int)
            actual = model.predict(data["state"][rows],data["action"][rows])
            for name in ("next_state","reward","events","disagreement"):
                np.testing.assert_allclose(actual[name],retained[name][rows],rtol=1e-4,atol=1e-4)


if __name__ == "__main__": unittest.main()
