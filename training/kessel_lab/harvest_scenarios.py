"""Explicit prepared no-traction fixtures; normal scenario generation is frozen."""
from dataclasses import asdict
import hashlib

from kessel_training.environment import LoaderEnv, SceneConfig
from kessel_training.reference_audit import initial_status
from kessel_training.wm_state import pack
from .runtime import environment as original_environment


def environment(family,seed):
    if family != "prepared_no_progress": return original_environment(family,seed)
    env = LoaderEnv(1,seed=seed,scene=SceneConfig(friction=.085,grade_rad=.1,randomise=False))
    if not initial_status(env)[0]["valid"]: raise ValueError("invalid prepared start")
    return env,{"family":family,"seed":seed,"scene":asdict(env.scene),"prepared_start":True,
                "initial_state_sha256":hashlib.sha256(pack(env).astype("<f8").tobytes()).hexdigest()}
