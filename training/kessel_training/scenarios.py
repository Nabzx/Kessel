"""Immutable seed partitions and named synthetic scene families."""

from dataclasses import replace

from .environment import SceneConfig

SPLITS = {"train": (0, 99999), "validation": (100000, 109999), "test": (200000, 209999)}


def scenario_seed(split, index):
    if split not in SPLITS:
        raise ValueError("unknown scenario split")
    first, last = SPLITS[split]
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index <= last-first:
        raise ValueError("scenario index outside its immutable split")
    return first+index


def family(name):
    base = SceneConfig(randomise=True)
    if name == "standard":
        return base, "feasible_reference"
    if name == "low_grip":
        return replace(base, friction=0.12, grade_rad=0.04), "difficult"
    if name == "occluded":
        return replace(base, sensor_noise=1, dropout=0.2, occlusion=0.25), "difficult"
    if name == "blocked":
        return replace(base, obstacles=((6.0, 6.1, -4.2, 4.2),)), "expected_failure"
    raise ValueError("unknown scenario family")
