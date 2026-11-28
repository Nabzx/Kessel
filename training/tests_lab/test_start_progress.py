import unittest

import numpy as np

from kessel_lab.harvest_contract import certificate
from kessel_lab.harvest_scenarios import environment
from kessel_lab.start_progress import StartProgressTask
from kessel_training.wm_state import pack


class StartProgressTests(unittest.TestCase):
    def test_empty_start_hold_requires_a_continuous_observed_stall(self):
        env,_ = environment("prepared_no_progress",19024); obs = env.observe(); task = StartProgressTask()
        for step in range(32):
            obs["proprio"][0,13] = step*.1; obs["proprio"][0,14] = .6
            task.act(obs)
        self.assertEqual(task.mode,"no_progress_hold")
        self.assertEqual(task.last["proposal_source"],"conventional_initial_no_progress_hold")
        np.testing.assert_array_equal(task.last["applied_action"],[.39,0,0,0])

    def test_real_progress_resets_the_stall_window(self):
        env,_ = environment("prepared_no_progress",19024); obs = env.observe(); task = StartProgressTask()
        for step in range(60):
            obs["proprio"][0,13] = step*.1; obs["proprio"][0,14] = .6
            if step%20 == 0: obs["proprio"][0,0] += .03
            task.act(obs)
        self.assertNotEqual(task.mode,"no_progress_hold")

    def test_admission_is_an_explicit_privileged_certificate(self):
        env,_ = environment("low_grip",19024); result = certificate(pack(env)[0])
        self.assertFalse(result["supported"]); self.assertFalse(result["controller_input"])
        self.assertLess(result["empty_forward_margin_n"],0)
        env,_ = environment("nominal",19020)
        self.assertTrue(certificate(pack(env)[0])["supported"])

    def test_declared_empty_grade_bound_supports_the_holding_prior(self):
        mass_g = 10500*9.81
        checked = 0
        for mu in np.linspace(.084,.144,31):
            for grade in np.linspace(-.02,.1,61):
                grip = mu*mass_g*np.cos(grade); slope = mass_g*np.sin(grade)
                rolling = .02*mass_g*np.cos(grade)
                if abs(min(22000,grip)-slope) <= rolling:
                    self.assertLessEqual(abs(min(.39*22000,grip)-slope),rolling+1e-9)
                    checked += 1
        self.assertGreater(checked,0)


if __name__ == "__main__": unittest.main()
