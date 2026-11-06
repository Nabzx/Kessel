"""Versioned CPU checkpoints, including simulator and random-generator state."""

import copy
from dataclasses import asdict
import hashlib
import os
from pathlib import Path
import random
import tempfile

import numpy as np
import torch

from .contracts import canonical_json

VERSION = "1.0"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def array_state(array):
    if array.dtype.kind in "US":
        return {"text": array.tolist(), "dtype": array.dtype.str, "shape": list(array.shape)}
    return torch.from_numpy(array.copy())


def array_value(value):
    if isinstance(value, torch.Tensor):
        return value.cpu().numpy().copy()
    return np.asarray(value["text"], dtype=value["dtype"]).reshape(value["shape"])


def environment_state(env):
    """Capture all runtime arrays, including observation caches; never resample."""
    return {"arrays": {k: array_state(v) for k, v in vars(env).items() if isinstance(v, np.ndarray)},
        "pile": {k: array_state(v) if isinstance(v, np.ndarray) else v for k, v in vars(env.pile).items()},
        "initial_pile_hashes": list(env.initial_pile_hashes),
        "sensor_rng": [copy.deepcopy(r.bit_generator.state) for r in env.sensor_rng],
        "loader": asdict(env.loader), "scene": asdict(env.scene), "reward": asdict(env.reward_config)}


def restore_environment(env, state):
    for name in ("loader", "scene"):
        if canonical_json(asdict(getattr(env, name))) != canonical_json(state[name]):
            raise ValueError(f"checkpoint {name} configuration differs")
    if canonical_json(asdict(env.reward_config)) != canonical_json(state["reward"]):
        raise ValueError("checkpoint reward configuration differs")
    expected = {k for k, v in vars(env).items() if isinstance(v, np.ndarray)}
    if expected != set(state["arrays"]):
        raise ValueError("checkpoint runtime layout differs")
    arrays = {k: array_value(v) for k, v in state["arrays"].items()}
    for k, value in arrays.items():
        original = getattr(env, k)
        if value.shape != original.shape or value.dtype != original.dtype:
            raise ValueError(f"checkpoint array differs: {k}")
    for k, value in arrays.items():
        setattr(env, k, value)
    for k, value in state["pile"].items():
        setattr(env.pile, k, array_value(value) if isinstance(value, (dict, torch.Tensor)) else value)
    env.initial_pile_hashes = list(state["initial_pile_hashes"])
    if len(state["sensor_rng"]) != env.num_envs:
        raise ValueError("checkpoint sensor batch differs")
    for rng, value in zip(env.sensor_rng, state["sensor_rng"]):
        rng.bit_generator.state = copy.deepcopy(value)
    env._assert_finite()


def random_state(generator):
    numpy_state = np.random.get_state()
    return {"sampling": generator.get_state(), "torch": torch.get_rng_state(),
            "python": random.getstate(), "numpy": {"algorithm": numpy_state[0],
            "keys": numpy_state[1].tolist(), "position": numpy_state[2],
            "has_gaussian": numpy_state[3], "cached_gaussian": numpy_state[4]}}


def restore_random_state(generator, state):
    generator.set_state(state["sampling"])
    torch.set_rng_state(state["torch"])
    random.setstate(state["python"])
    n = state["numpy"]
    np.random.set_state((n["algorithm"], np.asarray(n["keys"], dtype=np.uint32),
                         n["position"], n["has_gaussian"], n["cached_gaussian"]))


def save(path, state):
    path = Path(path)
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".checkpoint-", delete=False) as stream:
            temporary = Path(stream.name)
            torch.save({"checkpoint_version": VERSION, **state}, stream)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
        digest = sha256(path)
        path.with_suffix(path.suffix+".sha256").write_text(digest+"\n")
        return digest
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def load(path):
    path = Path(path)
    expected = path.with_suffix(path.suffix+".sha256").read_text().strip()
    if sha256(path) != expected:
        raise ValueError("checkpoint hash mismatch")
    state = torch.load(path, map_location="cpu", weights_only=True)
    if state.get("checkpoint_version") != VERSION:
        raise ValueError("unsupported checkpoint version")
    return state
