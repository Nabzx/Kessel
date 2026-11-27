import unittest
import numpy as np

from kessel_lab.clearance_stop import LatchedClearanceStop, synthetic_clearance
from kessel_lab.ordered_clearance import METHOD, OrderedClearanceStop
from kessel_lab.runtime import checkpoint, environment


class CaptureOrderTests(unittest.TestCase):
    def test_duplicate_old_and_negative_captures_stop_without_advancing_the_clock(self):
        env,_ = environment("nominal",19000); packet = synthetic_clearance(env)
        wrapper = OrderedClearanceStop(checkpoint("phase_memory-7")[0])
        self.assertFalse(wrapper.channel_health({**packet,"capture_s":-.1},0,0)["usable"])
        self.assertIsNone(wrapper.accepted_capture_s)
        self.assertTrue(wrapper.channel_health({**packet,"capture_s":.1},.1,0)["usable"])
        for captured in (.1,.05):
            status = wrapper.channel_health({**packet,"capture_s":captured},.2,0)
            self.assertFalse(status["usable"]); self.assertEqual(status["reason"],"nonmonotonic_clearance_capture")
            self.assertEqual(wrapper.accepted_capture_s,.1)
        self.assertTrue(wrapper.channel_health({**packet,"capture_s":.2},.2,0)["usable"])

    def test_old_clear_packet_cannot_release_an_obstacle_latch(self):
        env,_ = environment("nominal",19000); packet = synthetic_clearance(env)
        wrapper = OrderedClearanceStop(checkpoint("phase_memory-7")[0])
        blocked = {**packet,"capture_s":.1,"distance_m":[1.2,10,3,3]}
        self.assertFalse(wrapper.channel_health(blocked,.1,.8)["usable"])
        previous = wrapper.release_m
        self.assertFalse(wrapper.channel_health(packet,.2,0)["usable"])
        self.assertEqual(wrapper.release_m,previous)
        self.assertTrue(wrapper.channel_health({**packet,"capture_s":.3},.3,0)["usable"])

    def test_ordered_commands_match_frozen_wrapper_and_duplicate_input_requests_override(self):
        for policy in (7,19,41):
            env,_ = environment("nominal",19000); packet = synthetic_clearance(env); obs = env.observe()
            frozen = LatchedClearanceStop(checkpoint(f"phase_memory-{policy}")[0])
            wrapper = OrderedClearanceStop(checkpoint(f"phase_memory-{policy}")[0])
            np.testing.assert_array_equal(wrapper.act(obs,packet),frozen.act(obs,packet))
            following = {k:v.copy() for k,v in obs.items()}; following["proprio"][0,13] = .1
            action = wrapper.act(following,packet)
            self.assertTrue(wrapper.last["supervision"]["override"])
            self.assertEqual(wrapper.last["method"],METHOD)
            self.assertEqual(wrapper.last["accepted_capture_s"],0.)
            self.assertEqual(action[0,1:].tolist(),[0.,0.,0.])
            for elapsed in (.2,.3,.4):
                following["proprio"][0,13] = elapsed
                wrapper.act(following,{**packet,"capture_s":elapsed})
            self.assertFalse(wrapper.last["supervision"]["override"])


if __name__ == "__main__": unittest.main()
