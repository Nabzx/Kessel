import unittest
import numpy as np

from kessel_lab.progress_task import ProgressTask
from kessel_lab.runtime import environment


class ProgressTaskTests(unittest.TestCase):
    def test_retained_payload_does_not_start_a_cut_before_contact(self):
        env,_ = environment("nominal",19020); obs = env.observe()
        obs["proprio"][0,8] = 1500; obs["local_height_m"][:] = 0
        actor = ProgressTask(); actor.collection_pass = 1
        actor.act(obs)
        self.assertEqual(actor.mode,"approach")
        self.assertIsNone(actor.cut_start)

    def test_measured_load_ends_fill_without_waiting_for_a_timer(self):
        env,_ = environment("nominal",19020); obs = env.observe(); actor = ProgressTask()
        obs["local_height_m"][:,:2,:] = .3; obs["proprio"][0,8] = 2300
        action = actor.act(obs)
        self.assertEqual(actor.mode,"lift")
        self.assertGreater(action[0,2],0)
        self.assertTrue(np.isfinite(action).all())


if __name__ == "__main__": unittest.main()
