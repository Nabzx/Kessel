import math
import unittest

from kessel_lab.receiver_diagnostic import mouth_error, receiver_x, static_force


class ReceiverDiagnosticTests(unittest.TestCase):
    def test_receiver_position_uses_relative_goal_and_heading(self):
        p = [0.] * 15
        p[0] = 1.; p[3] = 1.; p[9] = -2.5
        self.assertAlmostEqual(receiver_x(p), -1.5)
        p[2] = 1.; p[3] = 0.; p[9] = 0.; p[10] = 2.5
        self.assertAlmostEqual(receiver_x(p), -1.5)

    def test_goal_error_accounts_for_bucket_reach(self):
        p = [0.] * 15
        p[6] = .35
        p[9] = 1.8 + 1.6 + 1.2 * math.cos(.35) - 2.
        self.assertAlmostEqual(mouth_error(p), -2.)

    def test_small_reverse_command_can_be_held_by_grade_and_rolling(self):
        s = [0.] * 102
        s[7] = 2600.; s[83] = .6; s[84] = -.046
        weak = static_force(s, -.31)
        strong = static_force(s, -1.)
        self.assertTrue(weak["stationary"])
        self.assertTrue(weak["within_rolling_resistance"])
        self.assertFalse(strong["within_rolling_resistance"])


if __name__ == "__main__":
    unittest.main()
