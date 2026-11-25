import unittest
import numpy as np
from kessel_lab.range_contract import canonicalize
from kessel_lab.spatial_range_pilot import SpatialFault, jobs, make_run, stopping
from kessel_training.wm_state import pack


def observation(speed=0.):
    p = np.zeros((1,15)); p[0,3] = 1; p[0,4] = speed; p[0,12] = 1
    return {"proprio":p,"local_height_m":np.full((1,5,5),.5),"range_valid":np.ones((1,5,5))}


class SpatialPilotBoundaryTests(unittest.TestCase):
    def test_native_height_semantics_are_distinct_but_canonical_invalid_inputs_agree(self):
        actual = observation()
        retained,_ = SpatialFault("partial_reset_retained").apply(actual)
        zeroed,_ = SpatialFault("partial_reset_zeroed").apply(actual)
        self.assertGreater(retained["local_height_m"][0,:2,:].sum(),0)
        self.assertEqual(zeroed["local_height_m"][0,:2,:].sum(),0)
        a,_ = canonicalize(retained); b,_ = canonicalize(zeroed)
        for k in a: np.testing.assert_array_equal(a[k],b[k])
        self.assertEqual(actual["range_valid"].sum(),25)
        fault = SpatialFault("carry_loss"); fault.trigger.phase[0] = 3
        self.assertFalse(fault.apply(observation(-.3))[1]["active"])
        self.assertTrue(fault.apply(observation(-.6))[1]["active"])

    def test_nonempty_fixtures_conserve_material_without_changing_the_kernel(self):
        fixtures = [j for j in jobs() if j["kind"] == "stop_fixture"]
        self.assertEqual(len(jobs()),51); self.assertEqual(len(fixtures),12)
        for job in fixtures:
            run = make_run(job); s = pack(run.env)[0]
            self.assertEqual(s[7],2500); self.assertEqual(s[3],job["initial_speed_m_s"])
            self.assertEqual(s[84],job["grade_rad"])
            self.assertAlmostEqual(sum(s[15:79])*.25*s[81]+sum(s[7:10]),s[82])
            self.assertEqual(run.actor.memory.phase[0],3)
            self.assertEqual(run.env.loader.substeps,5)

    def test_ten_second_gate_cannot_accept_the_old_three_second_window(self):
        samples = []
        for i in range(103):
            s = [0.]*102; s[10] = i*.1; samples.append(s)
        records = [{"state":s,"fault":{"active":True},"supervision":{"override":True}} for s in samples[:-1]]
        self.assertFalse(stopping(records[:32],{"state":samples[32]},False)["passed"])
        self.assertTrue(stopping(records,{"state":samples[-1]},False)["passed"])
        samples[-1][3] = .11
        self.assertFalse(stopping(records,{"state":samples[-1]},False)["passed"])


if __name__ == "__main__": unittest.main()
