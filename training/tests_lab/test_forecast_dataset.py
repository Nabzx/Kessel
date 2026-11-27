import copy
import unittest

from kessel_lab.forecast_dataset import validate_splits


def episode(seed):
    state = [0.]*102; next_state = state.copy(); next_state[10] = .1
    return {"scenario":{"seed":seed,"family":"nominal"},"outcome":{"decisions":1},
            "frames":[{"state":state,"next_state":next_state,"t_s":0.,"observation":{"proprio":[0.]*15}},
                      {"state":next_state.copy()}]}


class ForecastDatasetTests(unittest.TestCase):
    def test_episode_isolation_continuity_and_input_clocks(self):
        valid = {"train":[episode(19010),episode(19011)],"validation":[episode(19012)],"evaluation":[episode(19013)]}
        validate_splits(valid)
        for mutate in (lambda s:s["train"].append(episode(19012)),lambda s:s["train"].append(episode(19010)),
                       lambda s:s["evaluation"][0]["frames"][-1]["state"].__setitem__(0,1),
                       lambda s:s["train"][0]["frames"][0]["observation"]["proprio"].__setitem__(13,.1)):
            bad = copy.deepcopy(valid); mutate(bad)
            with self.assertRaises(ValueError): validate_splits(bad)


if __name__ == "__main__": unittest.main()
