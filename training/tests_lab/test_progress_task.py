import unittest
import numpy as np

from kessel_lab.progress_task import ProgressTask
from kessel_lab.runtime import environment
from kessel_training.contracts import LoaderConfig
from kessel_training.kinematics import advance


class ProgressTaskTests(unittest.TestCase):
    def test_lane_change_converges_at_the_commanded_approach_speed(self):
        actor = ProgressTask(); pose = np.array([[0.,0.,0.]])
        joints = np.zeros((1,3)); speed = np.array([1.2]); wheels = np.zeros((1,4))
        for step in range(200):
            p = np.zeros((1,15)); p[0,:2] = pose[0,:2]
            p[0,2:4] = (np.sin(pose[0,2]),np.cos(pose[0,2])); p[0,4] = speed[0]
            p[0,5:8] = joints[0]; p[0,12:] = (1,step*.1,.5)
            action = actor.act({"proprio":p,"local_height_m":np.zeros((1,5,5)),"range_valid":np.ones((1,5,5))})
            action[0,2:] = 0
            advance(pose,speed,joints,wheels,action,np.zeros(1),LoaderConfig(),.1)
        self.assertLess(abs(pose[0,1]-1.1),.25)
        self.assertLess(abs(pose[0,2]),.15)

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
