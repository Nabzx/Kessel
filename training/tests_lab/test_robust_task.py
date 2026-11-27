import unittest
import numpy as np

from kessel_lab.robust_task import InputSmoother, RetryMemory, TaskReference
from kessel_lab.runtime import environment


class RobustTaskTests(unittest.TestCase):
    def test_retry_requires_an_empty_tipped_bucket_and_never_resets_physics(self):
        env,_ = environment("nominal",19010); obs = env.observe(); memory = RetryMemory()
        memory.phase[0] = 4; obs["proprio"][0,8] = 100
        for _ in range(4): memory.update(obs)
        self.assertEqual(memory.phase[0],4)
        obs["proprio"][0,8] = 0; obs["local_height_m"][:] = 0
        for _ in range(3): memory.update(obs)
        self.assertEqual(memory.phase[0],0); self.assertEqual(memory.cycles,1)
        self.assertEqual(float(env.elapsed[0]),0)

    def test_smoothing_preserves_current_mask_and_capture_clock(self):
        env,_ = environment("nominal",19010); obs = env.observe(); smooth = InputSmoother(); smooth(obs)
        obs["range_valid"][:,:2,:] = 0; obs["local_height_m"][:,:2,:] = 50; obs["proprio"][0,13] = .1
        result = smooth(obs)
        np.testing.assert_array_equal(result["range_valid"],obs["range_valid"])
        self.assertEqual(result["proprio"][0,13],.1)
        self.assertTrue((result["local_height_m"][:,:2,:] == 0).all())
        self.assertTrue((obs["local_height_m"][:,:2,:] == 50).all())

    def test_missing_range_uses_declared_stop_and_finite_commands(self):
        env,_ = environment("range_dropout",19010); actor = TaskReference(12.)
        action = actor.act(env.observe())
        self.assertEqual(actor.last["owner"],"conventional_stop")
        self.assertTrue(np.isfinite(action).all()); self.assertTrue((abs(action) <= 1).all())


if __name__ == "__main__": unittest.main()
