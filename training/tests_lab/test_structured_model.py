from unittest.mock import patch
import unittest

import numpy as np

from kessel_lab.runtime import environment
from kessel_lab.structured_model import StructuredModel, cell_features, decode, local_features
from kessel_training.environment import LoaderEnv
from kessel_training.wm_state import INDEX, TARGET_FLOORS, pack, violations


class StructuredModelTests(unittest.TestCase):
    def test_prediction_needs_no_simulator_transition_and_preserves_raw_validity(self):
        env,_ = environment("nominal",19020); state = pack(env); model = StructuredModel(TARGET_FLOORS)
        with patch.object(LoaderEnv,"step",side_effect=AssertionError("oracle transition")):
            output = model.predict(state,np.array([[.5,.2,.1,.2]]))["next_state"]
        checked = violations(output)
        self.assertLess(abs(checked["mass_error_kg"][0]),1e-7)
        self.assertFalse(any(v.any() for k,v in checked.items() if k != "mass_error_kg"))
        self.assertEqual(output[0,INDEX["step_index"]],1)
        self.assertEqual(output[0,INDEX["success_kg"]],state[0,INDEX["success_kg"]])
        self.assertEqual(local_features(state,np.zeros((1,4))).shape,(1,25))
        self.assertEqual(cell_features(state,np.zeros((1,4))).shape,(1,64,12))

    def test_known_release_prior_conserves_loaded_material(self):
        env,_ = environment("nominal",19020); env.pile.height[0] *= (env.pile.mass()[0]-2500)/env.pile.mass()[0]
        env.payload[0] = 2500; env.joints[0] = (0,.35,-.7)
        state = pack(env); output,_,_ = decode(state,np.zeros((1,4)),np.zeros(1),np.ones((1,64)))
        self.assertLess(abs(violations(output)["mass_error_kg"][0]),1e-7)
        self.assertLess(output[0,7],2500)
        self.assertAlmostEqual(output[0,7:10].sum(),2500)


if __name__ == "__main__": unittest.main()
