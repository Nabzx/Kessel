import unittest
from unittest.mock import patch
import numpy as np
import torch

from kessel_lab.receiver_frame import ReceiverFrameActor, encode
from kessel_training.phase_memory import PhaseActor


def observation():
    p = np.zeros((1, 15))
    p[0, 0] = -6.; p[0, 3] = 1.; p[0, 9] = 2.5
    return {"proprio": p, "local_height_m": np.zeros((1, 5, 5)),
            "range_valid": np.ones((1, 5, 5))}


class ReceiverFrameTests(unittest.TestCase):
    def test_encode_changes_only_carry_x_and_does_not_mutate_inputs(self):
        obs = observation();before = {k:v.copy() for k,v in obs.items()}
        for phase in range(3):
            np.testing.assert_array_equal(encode(obs, [phase])["proprio"], obs["proprio"])
        actual = encode(obs, [3])
        self.assertEqual(actual["proprio"][0, 0], -4.)
        np.testing.assert_array_equal(actual["proprio"][:, 1:], obs["proprio"][:, 1:])
        for key in obs:
            np.testing.assert_array_equal(obs[key], before[key])
        with self.assertRaises(ValueError):encode(obs, [5])

    def test_carry_frame_is_invariant_to_absolute_x_with_same_relative_goal(self):
        first = observation();second = observation();second["proprio"][0, 0] += 2.
        np.testing.assert_array_equal(encode(first, [3])["proprio"], encode(second, [3])["proprio"])

    def test_phase_uses_original_goal_and_never_calls_teacher(self):
        torch.set_num_threads(1)
        raw = PhaseActor(True);actor = ReceiverFrameActor(raw)
        before = {k:v.clone() for k,v in raw.state_dict().items()}
        obs = observation();actor.memory.phase[0] = 3
        with patch("kessel_training.controller.ReferenceController.act", side_effect=AssertionError("teacher")):
            action = actor.act(obs)
        self.assertEqual(actor.memory.phase[0], 3)  # Original receiver is still too far.
        self.assertEqual(action.shape, (1, 4))
        self.assertTrue(np.isfinite(action).all())
        for key,value in before.items():
            torch.testing.assert_close(raw.state_dict()[key], value, rtol=0, atol=0)
        actor.reset()
        self.assertEqual(actor.memory.phase[0], 0)


if __name__ == "__main__":
    unittest.main()
