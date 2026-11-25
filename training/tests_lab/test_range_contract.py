import copy
import unittest
import numpy as np
import torch
from kessel_lab.range_contract import canonicalize, CompleteRangeSupervisor
from kessel_training.phase_memory import PhaseActor


def observation(t=0.):
    p = np.zeros((1,15)); p[0,3] = 1; p[0,12] = 1; p[0,13] = t
    return {"proprio":p,"local_height_m":np.zeros((1,5,5)),"range_valid":np.ones((1,5,5))}


class CompleteRangeContractTests(unittest.TestCase):
    def test_invalid_height_values_cannot_leak_into_canonical_neural_inputs(self):
        obs = observation(); obs["local_height_m"][:] = .7; obs["range_valid"][0,0,0] = 0
        saved = copy.deepcopy(obs); encoded,health = canonicalize(obs)
        self.assertEqual(encoded["local_height_m"][0,0,0],0)
        self.assertFalse(health["usable"])
        self.assertEqual(health["kind"],"fresh_partial")
        for k in obs: np.testing.assert_array_equal(obs[k],saved[k])
        obs["proprio"][0,12] = 0
        stale,health = canonicalize(obs)
        self.assertEqual(stale["range_valid"].sum(),0)
        self.assertEqual(stale["local_height_m"].sum(),0)
        self.assertEqual(health["kind"],"stale")

    def test_empty_complete_crop_remains_healthy_and_actions_are_unchanged(self):
        torch.set_num_threads(1)
        actor = PhaseActor(True).eval(); original = copy.deepcopy(actor)
        s = CompleteRangeSupervisor(actor)
        for i in range(4):
            obs = observation(i*.1)
            np.testing.assert_array_equal(s.act(obs),original.act(obs))
            self.assertFalse(s.last["override"])

    def test_one_missing_cell_stops_immediately_and_recovery_needs_stable_inputs(self):
        s = CompleteRangeSupervisor(PhaseActor(True).eval())
        s.act(observation())
        bad = observation(.1); bad["range_valid"][0,4,4] = 0
        s.act(bad); self.assertTrue(s.last["override"])
        s.act(observation(.2)); s.act(observation(.3)); self.assertTrue(s.last["override"])
        s.act(observation(.4)); self.assertFalse(s.last["override"])
        self.assertAlmostEqual(s.last["paused_s"],.3)

    def test_negative_heights_and_unusable_speed_are_errors_not_stops(self):
        bad = observation(); bad["local_height_m"][0,0,0] = -.1
        with self.assertRaises(ValueError): canonicalize(bad)
        bad = observation(); bad["proprio"][0,4] = np.nan
        with self.assertRaises(ValueError): canonicalize(bad)


if __name__ == "__main__":
    unittest.main()
