import unittest
import numpy as np

from kessel_lab.robust_reference_fix import DampedTaskReference
from kessel_lab.robust_task import TaskReference
from kessel_training.contracts import LoaderConfig
from kessel_training.kinematics import advance


class DampedReferenceTests(unittest.TestCase):
    def test_offset_forward_motion_converges_without_articulation_saturation(self):
        def motion(actor):
            pose = np.array([[0.,.6,.08]]); joints = np.zeros((1,3)); speed = np.array([.8]); wheels = np.zeros((1,4))
            for i in range(120):
                p = np.zeros((1,15)); p[0,:2] = pose[0,:2]; p[0,2:4] = (np.sin(pose[0,2]),np.cos(pose[0,2])); p[0,4] = .8
                p[0,5:8] = joints[0]; p[0,12] = 1; p[0,13] = i*.1
                obs = {"proprio":p,"local_height_m":np.zeros((1,5,5)),"range_valid":np.ones((1,5,5))}
                action = actor.act(obs); action[0,2:] = 0
                advance(pose,speed,joints,wheels,action,np.zeros(1),LoaderConfig(),.1)
            return pose,joints
        fixed,angles = motion(DampedTaskReference(12.)); rejected,rejected_angles = motion(TaskReference(12.))
        self.assertLess(abs(fixed[0,1]),.6); self.assertLess(abs(angles[0,0]),.2)
        self.assertGreater(abs(rejected_angles[0,0]),.5)


if __name__ == "__main__": unittest.main()
