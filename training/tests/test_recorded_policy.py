"""Execute retained policy weights and compare actual recorded machine actions."""

import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
import torch

from kessel_training.environment import LoaderEnv, SceneConfig
from kessel_training.evaluation import load_policy

EVIDENCE = Path(__file__).resolve().parents[2]/"docs/phase-11/rl-evidence"


@torch.no_grad()
def test_retained_checkpoints_reproduce_recorded_actions_and_physical_motion():
    replay = json.loads(gzip.decompress((EVIDENCE/"checkpoint-replay.json.gz").read_bytes()))
    policies = {hashlib.sha256(p.read_bytes()).hexdigest(): p for p in (EVIDENCE/"policies").glob("*.pt")}
    for item in replay["replays"]:
        report = item["evaluation"]
        policy, identity = load_policy(policies[report["identity"]["checkpoint_sha256"]])
        assert identity["checkpoint_sha256"] == report["identity"]["checkpoint_sha256"]
        for trace in item["traces"].values():
            case = trace["case"]
            env = LoaderEnv(1, seed=case["seed"], stream_ids=[case["stream_id"]], scene=SceneConfig(**report["scene"]))
            for frame in trace["frames"][:12]:
                action = policy.sample(policy.encode(env.observe()), deterministic=True)["action"].numpy()
                np.testing.assert_allclose(action[0], frame["action"], rtol=0, atol=1e-5)
                env.step(action)
                np.testing.assert_allclose(env.pose[0], frame["pose"], rtol=0, atol=1e-5)
                np.testing.assert_allclose(env.joints[0], frame["joints"], rtol=0, atol=1e-5)
