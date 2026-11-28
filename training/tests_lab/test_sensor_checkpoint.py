"""Saved inference must reproduce retained predictions without a simulator oracle."""
import json
import unittest
from unittest.mock import patch

import numpy as np

from kessel_training.policy import configure_cpu
from kessel_lab.runtime import ROOT
from kessel_lab.sensor_model import load, observations


class SensorCheckpointTests(unittest.TestCase):
    def test_saved_checkpoint_replays_recorded_predictions_without_physics(self):
        configure_cpu(7,threads=1)
        directory = ROOT/"docs/phase-11/sensor-forecast-v2-evidence"
        model,meta = load(directory/"sensor.pt")
        self.assertEqual(meta,json.loads((directory/"training.json").read_text()))
        for split in ("validation","evaluation"):
            with np.load(directory/f"{split}.npz",allow_pickle=False) as data, np.load(directory/f"{split}-predictions.npz",allow_pickle=False) as saved:
                # Span the complete cohort, including later stop/fault recordings.
                ids = np.unique(np.linspace(0,len(data["action"])-1,256).astype(int))
                with patch("kessel_training.environment.LoaderEnv.step",side_effect=AssertionError("physics oracle")), patch("kessel_training.wm_state.pack",side_effect=AssertionError("state oracle")):
                    prediction = model.predict(observations(data["observation"][ids]),data["action"][ids],
                        observations(data["previous_observation"][ids]),data["previous_action"][ids],data["history_present"][ids])
                for key in ("observation","disagreement","input_usable"):
                    np.testing.assert_allclose(prediction[key],saved[key][ids],rtol=1e-5,atol=1e-5)
                self.assertFalse(prediction["privileged_inputs"])
