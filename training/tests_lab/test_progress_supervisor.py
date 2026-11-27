import unittest

from kessel_lab.clearance_stop import synthetic_clearance
from kessel_lab.progress_supervisor import ClearanceMonitor, ProgressSupervisor
from kessel_lab.runtime import checkpoint, environment
from kessel_lab.ordered_clearance import OrderedClearanceStop


class ProgressSupervisorTests(unittest.TestCase):
    def test_previously_intercepted_healthy_case_delivers_with_the_guard_active(self):
        from kessel_lab.progress_rollout import run
        from kessel_lab.study_tools import Budget
        result = run("nominal",19001,Budget(20,environment=600,teacher=600,replay=600),replay=True)
        self.assertTrue(result["evaluation"]["passed"])
        self.assertTrue(result["outcome"]["full_success"])
        self.assertGreaterEqual(result["outcome"]["delivered_kg"],2000)
        self.assertFalse(result["outcome"]["collision"])

    def test_monitor_matches_ordered_contract_and_old_input_cannot_clear_a_latch(self):
        env,_ = environment("nominal",19020); packet = synthetic_clearance(env)
        monitor = ClearanceMonitor(); old = OrderedClearanceStop(checkpoint("phase_memory-7")[0])
        for captured,gap in ((0,1.2),(.1,1.2),(.05,10),(.2,10)):
            value = {**packet,"capture_s":captured,"distance_m":[gap,10,3,3]}
            self.assertEqual(monitor.update(value,max(.1,captured),.8),old.channel_health(value,max(.1,captured),.8))

    def test_fresh_but_empty_crops_do_not_extend_grace_indefinitely(self):
        env,_ = environment("nominal",19020); obs = env.observe(); packet = synthetic_clearance(env); actor = ProgressSupervisor()
        actor.act(obs,packet)
        obs["range_valid"][:] = 0
        for step in range(1,5):
            now = step*.1; obs["proprio"][0,13] = now
            actor.act(obs,{**packet,"capture_s":now})
        self.assertTrue(actor.overridden)
        self.assertIsNone(actor.last["conventional_proposal"])
        self.assertNotIn("neural_proposal",actor.last)


if __name__ == "__main__": unittest.main()
