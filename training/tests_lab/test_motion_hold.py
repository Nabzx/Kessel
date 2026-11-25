import copy
import json
import unittest
from unittest.mock import patch
import numpy as np
import torch
from kessel_lab.motion_hold import MotionHoldSupervisor, response
from kessel_training.phase_memory import PhaseActor


def observation(t=0.,speed=0.,healthy=False):
    p = np.zeros((1,15)); p[0,3] = 1; p[0,4] = speed; p[0,8] = 2500
    p[0,12] = healthy; p[0,13] = t
    return {"proprio":p,"local_height_m":np.zeros((1,5,5)),"range_valid":np.full((1,5,5),float(healthy))}


class ObservedMotionTests(unittest.TestCase):
    def setUp(self): torch.set_num_threads(1)

    def test_known_observed_residual_is_recovered_without_hidden_inputs(self):
        s = MotionHoldSupervisor(PhaseActor(True).eval())
        first = s.act(observation(speed=.2))[0,0]
        acceleration = response(.2,2500)*first-.3-.1962
        self.assertLess(abs(acceleration),1.4)
        s.act(observation(.1,.2+.1*acceleration))
        self.assertTrue(s.last["observer"]["accepted"])
        self.assertAlmostEqual(s.last["observer"]["disturbance_m_s2"],.3)
        json.dumps(s.last)

    def test_clipped_acceleration_and_rest_are_not_identifiable_force_samples(self):
        s = MotionHoldSupervisor(PhaseActor(True).eval())
        s.act(observation(speed=.8)); s.act(observation(.1,.65))
        self.assertFalse(s.last["observer"]["accepted"])
        self.assertEqual(s.last["observer"]["reason"],"acceleration_limit")
        s = MotionHoldSupervisor(PhaseActor(True).eval())
        s.act(observation()); s.act(observation(.1))
        self.assertEqual(s.last["observer"]["reason"],"low_speed")
        self.assertEqual(s.last["observer"]["disturbance_m_s2"],0)

    def test_healthy_actions_remain_exact_and_teacher_is_never_called(self):
        actor = PhaseActor(True).eval(); original = copy.deepcopy(actor); s = MotionHoldSupervisor(actor)
        with patch("kessel_training.controller.ReferenceController.act",side_effect=AssertionError("teacher")):
            for i in range(4):
                obs = observation(i*.1,healthy=True)
                np.testing.assert_array_equal(s.act(obs),original.act(obs)); json.dumps(s.last)
        bad = observation(); bad["grade"] = np.zeros(1)
        with self.assertRaises(ValueError): s.act(bad)


if __name__ == "__main__": unittest.main()
