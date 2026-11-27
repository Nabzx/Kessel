"""Complete episode split checks for the working-policy refit."""
import importlib.util

import numpy as np

from .runtime import ROOT


def validate_splits(splits):
    expected = {"train":{19010,19011},"validation":{19012},"evaluation":{19013}}
    if set(splits) != set(expected): raise ValueError("all three declared splits required")
    identities = set()
    for split,episodes in splits.items():
        for episode in episodes:
            scenario = episode["scenario"]; key = (scenario["seed"],scenario["family"])
            if scenario["seed"] not in expected[split] or key in identities: raise ValueError("episode/base split overlap")
            identities.add(key); frames = episode["frames"]; decisions = episode["outcome"]["decisions"]
            if len(frames) != decisions+1 or not 1 <= decisions <= 600: raise ValueError("incomplete episode")
            if frames[0]["state"][7] != 0: raise ValueError("working-policy episodes require empty starts")
            for current,following in zip(frames,frames[1:]):
                if current["next_state"] != following["state"]: raise ValueError("non-contiguous physical transition")
                if current["observation"]["proprio"][13] != current["t_s"]: raise ValueError("input clock differs")


def arrays(episodes):
    # Reuse the frozen measurement/label extraction, never its collection runner.
    path = ROOT/"scripts/research/evaluate-working-policy-models.py"
    spec = importlib.util.spec_from_file_location("working_forecast_data",path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    data,meta = module.data(episodes)
    data["event_targets"] = np.column_stack((data["events"],np.array([
        i == e["stop"]-1 and e["reason"] == "stuck"
        for e in meta for i in range(e["start"],e["stop"])])))
    data["event_targets"] = data["event_targets"].astype(float)
    return data,meta
