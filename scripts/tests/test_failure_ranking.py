"""Check distinctions that matter when interpreting retained failure traces."""
import copy
import importlib.util
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1]/"research/rank-robustness-failures.py"
SPEC = importlib.util.spec_from_file_location("failure_ranking", SOURCE)
RANKING = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RANKING)


def fixture():
    state = [0.]*102
    state[15] = 400.; state[81] = 1.; state[82] = 100.
    nxt = state.copy(); nxt[15] = 360.; nxt[7] = 10.; nxt[10] = .1
    obs = {"proprio":[0.]*15, "local_height_m":[[.5]*5 for _ in range(5)],
           "range_valid":[[0.]*5 for _ in range(5)]}
    frame = {"state":state, "next_state":nxt, "phase":0, "t_s":0.,
             "observation":obs, "action":[.5,0,0,0],
             "transfer":{"loaded_kg":10., "delivered_kg":0., "spilled_kg":0.}}
    case = {"family":"range_dropout", "source":"phase_memory-7", "seed":1,
            "identity":"fixture", "scenario":{}, "checkpoint_sha256":"fixture",
            "trace":"fixture", "sha256":"fixture", "reason":"time_limit",
            "full_success":False, "collision":False, "decisions":1,
            "delivered_kg":0., "carried_kg":10., "peak_load_kg":12., "spilled_kg":0.}
    trace = {k:case[k] for k in ("identity","scenario","source","checkpoint_sha256")}
    trace.update(outcome={"reason":"time_limit"}, frames=[frame, {"state":nxt,"phase":0}])
    return case, trace


class RetainedInterpretationTests(unittest.TestCase):
    def test_pickup_does_not_imply_observed_contact_or_phase_progress(self):
        case, trace = fixture()
        row = RANKING.metrics(case, trace)
        self.assertEqual(row["pickup_while_approach_kg"], 10)
        self.assertEqual(row["terminal_stage"], "approach")
        self.assertEqual(row["range"]["observed_height_cue_decisions"], 0)
        # The kernel can record a higher peak between decision samples.
        self.assertEqual(row["peak_load_kg"], 12)

    def test_drive_command_does_not_prove_motion_or_a_safe_stop(self):
        case, trace = fixture()
        row = RANKING.metrics(case, trace)
        self.assertEqual(row["range"]["nonneutral_drive_when_invalid_decisions"], 1)
        self.assertEqual(row["range"]["distance_when_invalid_m"], 0)
        self.assertEqual(row["range"]["moving_when_invalid_decisions"], 0)
        self.assertNotIn("safe_stop", row)

    def test_broken_continuity_and_material_ledger_are_rejected(self):
        case, trace = fixture()
        bad = copy.deepcopy(trace)
        bad["frames"][-1]["state"] = list(bad["frames"][-1]["state"])
        bad["frames"][-1]["state"][0] += 1
        with self.assertRaisesRegex(ValueError, "continuity"):
            RANKING.metrics(case, bad)
        bad = copy.deepcopy(trace); bad["frames"][0]["transfer"]["loaded_kg"] = 9
        with self.assertRaisesRegex(ValueError, "acquisition ledger"):
            RANKING.metrics(case, bad)


if __name__ == "__main__":
    unittest.main()
