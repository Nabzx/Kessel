import copy
import json
import unittest
import numpy as np
import torch
from kessel_lab.bootstrap_hold import BootstrapHoldSupervisor
from kessel_lab.motion_hold import response
from kessel_training.phase_memory import PhaseActor


def obs(t=0.,speed=0.,healthy=False):
    p = np.zeros((1,15)); p[0,3] = 1; p[0,4] = speed; p[0,8] = 2500
    p[0,12] = healthy; p[0,13] = t
    return {"proprio":p,"local_height_m":np.zeros((1,5,5)),"range_valid":np.full((1,5,5),float(healthy))}


class BootstrapHoldingTests(unittest.TestCase):
    def setUp(self): torch.set_num_threads(1)

    def test_first_command_is_identifiable_and_holding_clears_integral_bias(self):
        s = BootstrapHoldSupervisor(PhaseActor(True).eval())
        first = s.act(obs(speed=.8))[0,0]; self.assertEqual(first,-.25)
        acceleration = response(.8,2500)*first-.3-.1962
        s.act(obs(.1,.8+.1*acceleration))
        self.assertTrue(s.last["observer"]["estimate_valid"])
        self.assertAlmostEqual(s.last["observer"]["disturbance_m_s2"],.3)
        s.act(obs(.2,.07))
        self.assertTrue(s.last["observer"]["integral_cleared"])
        self.assertEqual(s.last["integral"],0)
        json.dumps(s.last)

    def test_reversals_and_static_samples_do_not_invent_force_estimates(self):
        s = BootstrapHoldSupervisor(PhaseActor(True).eval())
        s.act(obs(speed=.04)); s.act(obs(.1,-.04))
        self.assertFalse(s.last["observer"]["accepted"])
        self.assertEqual(s.last["observer"]["reason"],"speed_transition")
        s = BootstrapHoldSupervisor(PhaseActor(True).eval()); s.act(obs())
        self.assertFalse(s.last["observer"]["probe_applied"])
        self.assertFalse(s.last["observer"]["estimate_valid"])

    def test_healthy_neural_actions_are_exact_and_journal_is_serialisable(self):
        actor = PhaseActor(True).eval(); original = copy.deepcopy(actor); s = BootstrapHoldSupervisor(actor)
        for i in range(4):
            observation = obs(i*.1,healthy=True)
            np.testing.assert_array_equal(s.act(observation),original.act(observation)); json.dumps(s.last)


if __name__ == "__main__": unittest.main()
