import unittest

import numpy as np

from kessel_lab.harvest_task import HarvestTask
from kessel_lab.linear_feedback import load
from kessel_lab.runtime import ROOT, environment


class HarvestTaskTests(unittest.TestCase):
    def test_tip_accepts_contained_receiver_position_without_an_uphill_correction(self):
        env,_ = environment("low_grip",19021); obs = env.observe(); p = obs["proprio"][0]
        p[4:9] = (0.,0.,.35,.95,2050.)
        reach = 1.8+1.6+1.2*np.cos(.35); p[9:11] = (reach+.6,.2)
        task = HarvestTask(); task.mode = "carry"; action = task.act(obs)
        self.assertEqual(task.mode,"tip"); self.assertLess(action[0,3],0)
        obs["proprio"][0,10] = 1.5; task = HarvestTask(); task.mode = "carry"; task.act(obs)
        self.assertEqual(task.mode,"carry")

    def test_learned_actuator_is_queried_once_and_supplies_the_actual_command(self):
        env,_ = environment("nominal",19020); model,_ = load(ROOT/"docs/phase-11/linear-feedback-evidence/feedback.pt")
        task = HarvestTask(actuator=model.action); action = task.act(env.observe())
        self.assertEqual(model.calls,1)
        np.testing.assert_array_equal(action[0],task.last["applied_action"])
        self.assertEqual(task.last["proposal_source"],"learned_linear_feedback")


if __name__ == "__main__": unittest.main()
