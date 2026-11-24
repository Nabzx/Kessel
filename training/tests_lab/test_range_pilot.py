import copy
import unittest
import numpy as np
from kessel_lab.range_pilot import FaultInput, stop_metrics


class FaultAndStopMetricTests(unittest.TestCase):
    def test_stale_crop_and_observation_phase_trigger_do_not_modify_the_source(self):
        p = np.zeros((1,15)); p[0,3] = 1; p[0,12] = 1
        actual = {"proprio":p,"local_height_m":np.full((1,5,5),.5),"range_valid":np.ones((1,5,5))}
        before = copy.deepcopy(actual)
        observed, fault = FaultInput("fill_loss").apply(actual)
        self.assertTrue(fault["active"])
        self.assertEqual(fault["trigger_phase"],1)
        self.assertEqual(observed["range_valid"].sum(),0)
        for key in actual: np.testing.assert_array_equal(actual[key],before[key])

    def test_a_later_rollaway_or_termination_cannot_pass_as_a_held_stop(self):
        samples = []
        for i in range(33):
            state = [0.]*102; state[10] = i*.1; samples.append(state)
        records = [{"state":s,"fault":{"active":True},"supervision":{"override":True}} for s in samples[:-1]]
        final = {"state":samples[-1]}
        self.assertTrue(stop_metrics(records,final,False)["passed"])
        self.assertFalse(stop_metrics(records,final,True)["passed"])
        samples[10][3] = .2
        self.assertFalse(stop_metrics(records,final,False)["passed"])
        samples[10][3] = 0; samples[-1][0] = .3
        self.assertFalse(stop_metrics(records,final,False)["passed"])


if __name__ == "__main__":
    unittest.main()
