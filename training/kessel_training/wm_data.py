"""Episode-isolated simulator transition corpora with deterministic archives."""

from dataclasses import dataclass, replace
import hashlib
import io
import json
from pathlib import Path
import zipfile

import numpy as np
import torch

from .contracts import canonical_json
from .controller import ReferenceController
from .environment import LoaderEnv
from .evaluation import load_policy
from .evaluate import source_identity
from .kinematics import components
from .scenarios import family, scenario_seed
from .wm_state import EVENT_NAMES, STATE_NAMES, STATE_VERSION, pack

POLICIES = Path(__file__).resolve().parents[2]/"docs/phase-11/rl-evidence/policies"
SOURCE_IDS = {"reference": 0, "random": 1, "policy": 2}


def flat_observation(observation):
    return np.concatenate((observation["proprio"], observation["local_height_m"].reshape(-1, 25),
                           observation["range_valid"].reshape(-1, 25)), axis=1)


def logical_hash(arrays, episodes):
    h = hashlib.sha256(canonical_json(episodes).encode())
    for name, array in sorted(arrays.items()):
        h.update(name.encode());h.update(array.dtype.str.encode());h.update(str(array.shape).encode());h.update(array.tobytes())
    return h.hexdigest()


def write_archive(path, arrays):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, array in sorted(arrays.items()):
            stream = io.BytesIO();np.lib.format.write_array(stream, array, allow_pickle=False)
            info = zipfile.ZipInfo(name+".npy", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, stream.getvalue())


def ood_scene(name):
    scene, _ = family("standard")
    if name == "high_resistance":
        return replace(scene, pile_resistance_n_m=72000), None
    if name == "low_grip":
        return replace(scene, friction=0.08, grade_rad=0.15), None
    if name == "sensing_failure":
        return replace(scene, sensor_noise=3, dropout=0.8, occlusion=0.7, load_bias_fraction=0.25), None
    if name == "unusual_pile":
        return scene, "reshape"
    if name == "contact_start":
        return scene, "contact"
    if name == "blocked":
        return replace(scene, obstacles=((6., 8., -5., 5.),)), None
    raise ValueError("unknown world-model OOD family")


@torch.no_grad()
def collect_split(split, budgets, *, ood=None, seed_offset=0):
    if set(budgets) != set(SOURCE_IDS) or any(not isinstance(n, int) or isinstance(n, bool) or n < 1 for n in budgets.values()):
        raise ValueError("positive reference/random/policy collection budgets are required")
    policies = [load_policy(POLICIES/f"policy-{s}.pt") for s in (7, 19, 43)]
    columns = {k: [] for k in ("state", "action", "next_state", "observation", "next_observation", "reward",
        "events", "reward_terms", "episode_id", "step", "physical_dt_s", "regime")}
    episodes = []
    for source, budget in budgets.items():
        collected = 0;number = 0
        while collected < budget:
            seed = scenario_seed(split, seed_offset+SOURCE_IDS[source]*1000+number)
            family_name = "blocked" if number % 4 == 3 else "standard"
            scene, setup = ood_scene(ood) if ood else (family(family_name)[0], None)
            env = LoaderEnv(1, seed=seed, scene=scene)
            if setup == "reshape":
                shape = np.ones((8, 8));shape[::2] = 0.1;shape[:, 3:5] *= 3
                env.pile.height[0] *= shape
                env.pile.height[0] *= env.pile.initial_mass[0]/env.pile.mass()[0]
            if setup == "contact":
                env.pose[0, 0] = env.pile.origin[0, 0]-3.8
                env.joints[0] = (0, -0.1, -0.3)
            if setup:
                env.initial_pose[:] = env.pose
                env.initial_pile_hashes[0] = hashlib.sha256(env.pile.height[0].astype("<f8").tobytes()).hexdigest()
                env._update_observations(np.ones(1, dtype=bool), reset=True)
                env._assert_finite()
            controller = ReferenceController(1)
            policy, identity = policies[number % len(policies)]
            rng = np.random.default_rng(np.random.SeedSequence([seed, SOURCE_IDS[source], 944]))
            first = len(columns["reward"]);episode_id = len(episodes)
            episode = {"id": episode_id, "split": split, "seed": seed, "stream_id": 0,
                "family": ood or family_name, "source_kind": source,
                "controller_identity": identity if source == "policy" else controller.settings() if source == "reference" else {"seed": seed, "kind": "uniform_bounded"},
                "initial_pile_sha256": env.initial_pile_hashes[0], "scenario_sha256": env.scenario_identity()[0],
                "prepared_start": setup, "start": first}
            for step in range(scene.max_steps):
                observation = env.observe();state = pack(env)[0]
                if source == "reference":
                    action = controller.act(observation)
                elif source == "random":
                    action = rng.uniform(-1, 1, (1, 4))
                else:
                    action = policy.sample(policy.encode(observation), deterministic=True)["action"].numpy()
                geometry = components(env.pose, env.joints)
                contact = bool(env.pile.sample(geometry["mouth"])[0] > geometry["bucket_height"][0])
                next_obs, reward, term, trunc, info = env.step(action)
                collision = bool(info["metrics"]["collision_time_s"][0] >= 0)
                transfer = sum(float(info["transfer"][k][0]) for k in ("loaded_kg", "delivered_kg", "spilled_kg"))
                regime = 3 if collision or env.reason[0] == "stuck" else 2 if transfer > 1e-6 else 1 if contact else 0
                row = {"state": state, "action": action[0], "next_state": pack(env)[0],
                    "observation": flat_observation(observation)[0], "next_observation": flat_observation(next_obs)[0],
                    "reward": float(reward[0]), "events": [term[0], trunc[0], contact or transfer > 1e-6, collision],
                    "reward_terms": [float(info["reward_terms"][k][0]) for k in ("delivered_kg", "spilled_kg", "elapsed_s", "effort_proxy_j", "collision_count", "slip_s")],
                    "episode_id": episode_id, "step": step, "physical_dt_s": float(env.elapsed[0]-state[10]), "regime": regime}
                for key, value in row.items():
                    columns[key].append(value)
                collected += 1
                if (term | trunc).any() or collected == budget:
                    break
            episode.update(stop=len(columns["reward"]), terminated=bool(term[0]), truncated=bool(trunc[0]),
                           collection_boundary=bool(not (term | trunc).any()), outcome=str(env.reason[0]) or "collection_budget")
            episodes.append(episode);number += 1
    arrays = {k: np.asarray(v, dtype=bool if k == "events" else np.int64 if k in ("episode_id", "step", "regime") else np.float64)
              for k, v in columns.items()}
    validate(arrays, episodes)
    return arrays, episodes


def validate(arrays, episodes):
    n = len(arrays["reward"])
    if n < 1 or any(len(v) != n or not np.isfinite(v).all() for v in arrays.values()):
        raise ValueError("non-finite, empty or misaligned transition arrays")
    if arrays["state"].shape != (n, len(STATE_NAMES)) or arrays["next_state"].shape != arrays["state"].shape or arrays["action"].shape != (n, 4):
        raise ValueError("transition shapes differ from the world-state schema")
    if (np.abs(arrays["action"]) > 1).any() or (arrays["events"][:, 0] & arrays["events"][:, 1]).any():
        raise ValueError("invalid actions or episode events")
    cursor = 0
    for i, episode in enumerate(episodes):
        if episode["start"] != cursor or episode["stop"] <= cursor:
            raise ValueError("episode slices are not contiguous")
        indices = slice(cursor, episode["stop"])
        if not (arrays["episode_id"][indices] == i).all():
            raise ValueError("episode identities differ")
        if arrays["events"][cursor:episode["stop"]-1, :2].any():
            raise ValueError("transitions continue across a terminal/reset boundary")
        cursor = episode["stop"]
    if cursor != n:
        raise ValueError("episode metadata does not cover the corpus")


def assert_disjoint(partitions):
    seen_seeds, seen_piles = set(), set()
    for _, episodes in partitions:
        seeds = {e["seed"] for e in episodes};piles = {e["initial_pile_sha256"] for e in episodes}
        if seeds & seen_seeds or piles & seen_piles:
            raise ValueError("episode seed or generated pile leaked across splits")
        seen_seeds |= seeds;seen_piles |= piles


def save_partition(directory, name, arrays, episodes):
    directory = Path(directory);directory.mkdir(parents=True, exist_ok=True)
    archive = directory/f"{name}.npz"
    if archive.exists():
        raise FileExistsError(archive)
    write_archive(archive, arrays)
    manifest = {"schema_version": "1.0", "state_version": STATE_VERSION, "source_mode": "recorded_synthetic",
        "name": name, "source": source_identity(), "state_names": STATE_NAMES, "event_names": EVENT_NAMES,
        "regimes": {"0": "empty_motion", "1": "contact_without_transfer", "2": "material_transfer", "3": "collision_or_stuck"},
        "transitions": len(arrays["reward"]), "episodes": episodes,
        "logical_sha256": logical_hash(arrays, episodes), "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "regime_counts": {str(i): int((arrays["regime"] == i).sum()) for i in range(4)},
        "event_counts": {key: int(arrays["events"][:, i].sum()) for i, key in enumerate(EVENT_NAMES)}}
    archive.with_suffix(".json").write_text(json.dumps(manifest, indent=2, allow_nan=False)+"\n")
    return manifest


def load_partition(directory, name):
    directory = Path(directory);manifest = json.loads((directory/f"{name}.json").read_text());path = directory/f"{name}.npz"
    if hashlib.sha256(path.read_bytes()).hexdigest() != manifest["archive_sha256"]:
        raise ValueError("transition archive hash differs")
    with np.load(path, allow_pickle=False) as archive:
        arrays = {k: archive[k] for k in archive.files}
    validate(arrays, manifest["episodes"])
    if logical_hash(arrays, manifest["episodes"]) != manifest["logical_sha256"]:
        raise ValueError("transition logical content differs")
    return arrays, manifest


@dataclass
class Normaliser:
    mean: np.ndarray
    scale: np.ndarray
    constant: np.ndarray

    @classmethod
    def fit(cls, values, floors=None):
        values = np.asarray(values, dtype=np.float64)
        if values.ndim != 2 or len(values) < 2 or not np.isfinite(values).all():
            raise ValueError("normaliser needs finite training rows")
        std = values.std(axis=0);constant = std < 1e-12
        scale = np.where(constant, 1.0, std) if floors is None else np.maximum(std, floors)
        if not np.isfinite(scale).all() or (scale <= 0).any():
            raise ValueError("normaliser scales must be positive")
        return cls(values.mean(axis=0), scale, constant)

    def transform(self, values):
        result = (values-self.mean)/self.scale
        if not np.isfinite(result).all():
            raise ValueError("non-finite normalised values")
        return result

    def inverse(self, values):
        result = values*self.scale+self.mean
        if not np.isfinite(result).all():
            raise ValueError("non-finite inverse values")
        return result
