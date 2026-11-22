"""Shared execution for frozen-policy stress tests and the localhost viewer."""
from dataclasses import asdict, replace
import hashlib
import io
import json
from pathlib import Path
import zipfile

import numpy as np
import torch
from kessel_training.contracts import canonical_json
from kessel_training.controller import ReferenceController
from kessel_training.environment import LoaderEnv, SceneConfig
from kessel_training.phase_memory import PhaseActor
from kessel_training.reference_audit import initial_status
from kessel_training.wm_state import pack

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT/'docs/phase-11/phase-memory-evidence'
FAMILIES = ('nominal', 'low', 'ridge', 'rubble', 'steep', 'receiver_far',
            'receiver_left', 'start_offset', 'low_grip', 'high_resistance',
            'range_dropout', 'range_impaired', 'blocked')
SOURCES = ('phase_memory-7', 'phase_memory-19', 'phase_memory-41', 'reference')


def digest(value):
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def checkpoint(source):
    if source not in SOURCES or source == 'reference':
        raise ValueError('unknown learned source')
    selected = json.loads((EVIDENCE/'selection.json').read_text())[source]
    with zipfile.ZipFile(EVIDENCE/'artifacts.zip') as archive:
        data = archive.read(selected['path'])
    if hashlib.sha256(data).hexdigest() != selected['sha256']:
        raise ValueError('checkpoint hash differs')
    state = torch.load(io.BytesIO(data), map_location='cpu', weights_only=True)
    actor = PhaseActor(True); actor.load_state_dict(state['actor']); actor.eval()
    return actor, selected['sha256']


def environment(family, seed):
    if family not in FAMILIES or isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 209999:
        raise ValueError('unsupported scenario or seed')
    scene = SceneConfig(randomise=True)
    if family in ('low', 'ridge', 'rubble', 'steep'):
        scene = replace(scene, pile_family=family)
    if family == 'low_grip': scene = replace(scene, friction=.12, grade_rad=.04)
    if family == 'high_resistance': scene = replace(scene, pile_resistance_n_m=36000.)
    if family == 'range_dropout': scene = replace(scene, dropout=1.)
    if family == 'range_impaired': scene = replace(scene, sensor_noise=1., dropout=.25, occlusion=.2)
    if family == 'blocked': scene = replace(scene, obstacles=((6., 6.1, -4.2, 4.2),))
    env = LoaderEnv(1, seed=seed, scene=scene)
    if family == 'receiver_far': env.receiver[0, 0] -= 2.
    if family == 'receiver_left': env.receiver[0, 1] += 1.
    if family == 'start_offset': env.pose[0, 1] += .6; env.pose[0, 2] += .08
    if family in ('receiver_far', 'receiver_left', 'start_offset'):
        env.initial_pose[0] = env.pose[0]
        env._update_observations(np.array([True]), reset=True)
    if not initial_status(env)[0]['valid']:
        raise ValueError('invalid initial geometry')
    identity = {'family': family, 'seed': seed, 'scene': asdict(scene),
                'initial_state_sha256': hashlib.sha256(pack(env).astype('<f8').tobytes()).hexdigest()}
    return env, identity


class Run:
    def __init__(self, family, seed, source):
        if source not in SOURCES: raise ValueError('unsupported source')
        self.env, self.scenario = environment(family, seed)
        self.source = source
        self.actor, self.checkpoint_sha256 = (ReferenceController(1), None) if source == 'reference' else checkpoint(source)
        self.identity = digest({'scenario': self.scenario, 'source': source, 'checkpoint': self.checkpoint_sha256})
        self.done = False; self.decisions = 0; self.max_mass_residual = 0.
        self.inference_us = []; self.records = []

    def frame(self):
        return {'t_s': float(self.env.elapsed[0]), 'state': pack(self.env)[0].tolist(),
                'phase': int(self.actor.phase[0] if self.source == 'reference' else self.actor.memory.phase[0]),
                'wheel_angles_rad': self.env.wheel_angles[0].tolist()}

    def step(self):
        import time
        if self.done: raise ValueError('episode is terminal; reset to start a new run')
        obs = self.env.observe(); start = time.perf_counter_ns()
        action = self.actor.act(obs)
        self.inference_us.append((time.perf_counter_ns()-start)/1000)
        before = self.frame(); before['action'] = action[0].tolist()
        before['observation'] = {k: v[0].tolist() for k, v in obs.items()}
        _, reward, term, trunc, info = self.env.step(action)
        self.decisions += 1; self.done = bool((term | trunc)[0])
        residual = abs(float((self.env.pile.mass()+self.env.payload+self.env.delivered+self.env.spilled-self.env.pile.initial_mass)[0]))
        self.max_mass_residual = max(self.max_mass_residual, residual)
        if residual > 1e-7: raise AssertionError('material ledger diverged')
        before.update(next_state=pack(self.env)[0].tolist(), reward=float(reward[0]),
                      transfer={k: float(info['transfer'][k][0]) for k in ('loaded_kg', 'delivered_kg', 'spilled_kg')})
        self.records.append(before)
        return self.frame()

    def outcome(self):
        reason = str(self.env.reason[0])
        return {'reason': reason, 'done': self.done, 'full_success': self.done and reason == 'success',
                'collision': reason in ('tunnel_wall', 'tunnel_roof') or reason.startswith('obstacle'),
                'initial_payload_kg': 0., 'delivered_kg': float(self.env.delivered[0]),
                'carried_kg': float(self.env.payload[0]), 'peak_load_kg': float(self.env.peak_load[0]),
                'spilled_kg': float(self.env.spilled[0]), 'cycle_s': float(self.env.elapsed[0]),
                'decisions': self.decisions, 'max_mass_residual_kg': self.max_mass_residual}
