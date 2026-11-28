import hashlib
import json
import unittest
from unittest.mock import patch

import numpy as np

from kessel_lab.harvest_contract import certificate
from kessel_lab.harvest_scenarios import environment
from kessel_lab.runtime import ROOT
from kessel_lab.structured_fit import load
from kessel_training.environment import LoaderEnv
from kessel_training.wm_state import pack

D = ROOT/"docs/phase-11/harvest-qualification-evidence"


class HarvestQualificationTests(unittest.TestCase):
    def test_screened_initial_states_reconstruct_without_physics_queries(self):
        report = json.loads((D/"reservation.json").read_text())
        with patch.object(LoaderEnv,"step",side_effect=AssertionError("transition during screening")):
            for family,seeds in report["selected_by_family"].items():
                for seed in seeds:
                    env,_ = environment(family,seed); state = pack(env)[0]
                    row, = [r for r in report["identities"] if r["seed"] == seed and r["family"] == family]
                    self.assertEqual(hashlib.sha256(state.astype("<f4").tobytes()).hexdigest(),row["fingerprints"]["state<f4"])
                    actual = certificate(state); expected = row["certificate"]
                    self.assertEqual(actual["supported"],expected["supported"])
                    self.assertEqual(actual["reasons"],expected["reasons"])
                    for key in ("available_above_blade_kg","empty_forward_margin_n"):
                        self.assertAlmostEqual(actual[key],expected[key],places=7)

    def test_saved_fresh_predictions_replay_without_simulator_oracle(self):
        model,_ = load(ROOT/"docs/phase-11/structured-dynamics-evidence/structured.pt")
        with np.load(D/"fresh/forecast-data.npz",allow_pickle=False) as data:
            ids = np.linspace(0,len(data["state"])-1,32,dtype=int)
            with patch.object(LoaderEnv,"step",side_effect=AssertionError("oracle prediction")):
                actual = model.predict(data["state"][ids],data["action"][ids])
        with np.load(D/"fresh/forecast-predictions.npz",allow_pickle=False) as expected:
            for field in ("next_state","reward","events","disagreement"):
                np.testing.assert_allclose(actual[field],expected[field][ids],rtol=1e-5,atol=1e-5)

    def test_refusal_window_is_not_an_environment_terminal_or_delivery(self):
        report = json.loads((D/"fresh/report.json").read_text())
        self.assertFalse(report["original_full_gate"])
        with np.load(D/"fresh/forecast-data.npz",allow_pickle=False) as data:
            episodes = [e for e in report["forecast"]["episodes"] if e["family"] == "prepared_no_progress"]
            self.assertEqual(len(episodes),8)
            for episode in episodes:
                self.assertFalse(episode["done"])
                np.testing.assert_array_equal(data["events"][episode["start"]:episode["stop"],:2],False)
                np.testing.assert_array_equal(data["next_state"][episode["start"]:episode["stop"],8],0.)


if __name__ == "__main__": unittest.main()
