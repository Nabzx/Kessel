import copy
from dataclasses import replace
import unittest

import numpy as np

from kessel_lab.clearance_stop import ClearanceStop, LatchedClearanceStop, health, synthetic_clearance
from kessel_lab.runtime import checkpoint, environment
from kessel_training.environment import LoaderEnv, SceneConfig


class ClearanceTests(unittest.TestCase):
    def test_stopping_does_not_reduce_the_release_clearance(self):
        env,_ = environment("nominal",19000); packet = synthetic_clearance(env)
        wrapper = LatchedClearanceStop(checkpoint("phase_memory-7")[0])
        blocked = {**packet,"distance_m":[1.2,10,3,3]}
        self.assertFalse(wrapper.channel_health(blocked,0,.8)["usable"])
        self.assertFalse(wrapper.channel_health(blocked,0,0)["usable"])
        cleared = {**blocked,"distance_m":[3,10,3,3]}
        self.assertTrue(wrapper.channel_health(cleared,0,0)["usable"])
    def test_packet_detects_boxes_but_does_not_mistake_the_pile_for_an_obstacle(self):
        env,_ = environment("nominal",19000)
        packet = synthetic_clearance(env)
        self.assertTrue(health(packet,0,0)["usable"])
        env.scene = replace(env.scene,obstacles=((6.,6.1,-4.2,4.2),))
        self.assertLess(synthetic_clearance(env)["distance_m"][0],1.)
        self.assertFalse(health(synthetic_clearance(env),0,.8)["usable"])

    def test_bad_channels_fail_closed_without_inventing_range_cells(self):
        env,_ = environment("nominal",19000); packet = synthetic_clearance(env)
        for changed in (None,{**packet,"capture_s":1.},{**packet,"capture_s":-.3},
                        {**packet,"distance_m":[float("nan")]*4},{**packet,"valid":"true"},
                        {**packet,"version":"unknown"},{**packet,"distance_m":[1,2]}):
            self.assertFalse(health(changed,0,0)["usable"])

    def test_clear_channel_preserves_neural_actions_and_missing_channel_holds_phase(self):
        env,_ = environment("nominal",19000); original,_ = checkpoint("phase_memory-7")
        actor,_ = checkpoint("phase_memory-7"); wrapper = ClearanceStop(actor)
        obs = env.observe(); before = copy.deepcopy(obs)
        np.testing.assert_array_equal(wrapper.act(obs,synthetic_clearance(env)),original.act(obs))
        for name in obs: np.testing.assert_array_equal(obs[name],before[name])
        env.step([[0,0,0,0]]); phase = wrapper.memory.phase.copy()
        action = wrapper.act(env.observe(),None)
        np.testing.assert_array_equal(wrapper.memory.phase,phase)
        self.assertTrue(wrapper.last["supervision"]["override"])
        self.assertEqual(action[0,1:].tolist(),[0.,0.,0.])
        self.assertTrue(wrapper.last["range_health"]["usable"])


if __name__ == "__main__": unittest.main()
