import unittest
import numpy as np
from pathlib import Path
import json

from kessel_lab.linear_feedback import fit, load
from kessel_lab.runtime import ROOT


class LinearFeedbackTests(unittest.TestCase):
    def test_fit_recovers_independent_feedback_labels_and_preserves_saturation(self):
        rng = np.random.default_rng(42); x = rng.normal(size=(1000,6)); weights = np.zeros((4,6))
        weights[0,:3] = (.9,.3,-.2); weights[1,3] = 1.7; weights[2,4] = 3.2; weights[3,5] = 2.4
        y = np.clip(x@weights.T,-1,1); model,report = fit(x,y)
        np.testing.assert_allclose(model.action(x),y,atol=1e-12,rtol=1e-12)
        self.assertEqual(report["ranks"],[3,1,1,1])
        with self.assertRaises(ValueError): model.action([[float("nan")]*6])
    def test_constant_labels_cannot_hide_an_underdetermined_fit(self):
        with self.assertRaises(ValueError): fit(np.ones((20,6)),np.zeros((20,4)))
    def test_retained_weights_match_fit_metadata_and_training_actions(self):
        directory = ROOT/"docs/phase-11/linear-feedback-evidence"
        if not (directory/"feedback.pt").exists(): self.skipTest("retained fit not present")
        model,metadata = load(directory/"feedback.pt")
        np.testing.assert_array_equal(model.network.weight.detach().numpy(),metadata["weight_matrix"])
        with np.load(directory/"training.npz") as data:
            np.testing.assert_allclose(model.action(data["features"]),data["labels"],atol=1e-10,rtol=0)


if __name__ == "__main__": unittest.main()
