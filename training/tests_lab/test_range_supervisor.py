import copy
import unittest
from unittest.mock import patch

import numpy as np
import torch
from kessel_lab.range_supervisor import RangeSupervisor
from kessel_training.phase_memory import PhaseActor


def observation(t=0., speed=0., healthy=True):
    p = np.zeros((1,15)); p[0,3] = 1.; p[0,4] = speed
    p[0,11] = 0 if healthy else 1.; p[0,12] = healthy; p[0,13] = t
    return {"proprio":p,"local_height_m":np.zeros((1,5,5)),
            "range_valid":np.full((1,5,5),float(healthy))}


class RangeSupervisorTests(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1)
        self.actor = PhaseActor(True).eval()

    def test_healthy_actions_and_phase_are_exact_and_inputs_are_unchanged(self):
        original = copy.deepcopy(self.actor); wrapped = RangeSupervisor(self.actor)
        with patch("kessel_training.controller.ReferenceController.act",side_effect=AssertionError("teacher")):
            for i in range(6):
                obs = observation(i*.1); snapshot = copy.deepcopy(obs)
                if i >= 2: obs["local_height_m"][:] = .5; snapshot = copy.deepcopy(obs)
                np.testing.assert_array_equal(wrapped.act(obs),original.act(obs))
                np.testing.assert_array_equal(wrapped.memory.phase,original.memory.phase)
                self.assertFalse(wrapped.last["override"])
                for k in obs: np.testing.assert_array_equal(obs[k],snapshot[k])

    def test_uninitialised_range_overrides_both_directions_and_holds_joints(self):
        for speed in (-.8,.8):
            s = RangeSupervisor(copy.deepcopy(self.actor))
            action = s.act(observation(speed=speed,healthy=False))
            self.assertTrue(s.last["override"])
            self.assertLess(action[0,0]*speed,0)
            np.testing.assert_array_equal(action[0,1:],np.zeros(3))
            self.assertEqual(s.last["reason"],"range_uninitialised")

    def test_grace_distinguishes_transient_loss_and_persistent_poor_coverage(self):
        s = RangeSupervisor(self.actor)
        s.act(observation())
        s.act(observation(.1,healthy=False)); self.assertFalse(s.last["override"])
        s.act(observation(.2)); self.assertFalse(s.last["override"])
        for t in (.3,.4,.5):
            obs = observation(t); obs["range_valid"][:] = 0
            obs["range_valid"][0,0,0] = 1  # Fresh but below the declared coverage threshold.
            s.act(obs)
        self.assertTrue(s.last["override"])

    def test_recovery_preserves_phase_and_pauses_fill_timeout(self):
        s = RangeSupervisor(self.actor)
        s.memory.phase[0] = 1; s.memory.fill_start[0] = 0
        s.act(observation())
        for i in range(1,251): s.act(observation(i*.1,healthy=False))
        for i in (251,252):
            s.act(observation(i*.1)); self.assertTrue(s.last["override"])
        s.act(observation(25.3))
        self.assertFalse(s.last["override"])
        self.assertEqual(s.memory.phase[0],1)
        self.assertLess(s.last["task_elapsed_s"],1.)
        self.assertGreater(s.last["paused_s"],24.)

    def test_unusable_proprioception_and_clock_gaps_are_rejected(self):
        s = RangeSupervisor(self.actor)
        bad = observation(); bad["proprio"][0,4] = np.nan
        with self.assertRaises(ValueError): s.act(bad)
        s.act(observation())
        with self.assertRaises(ValueError): s.act(observation(.5))


if __name__ == "__main__":
    unittest.main()
