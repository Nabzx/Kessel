"""Bounded replay, reward and reference diagnostics. Does not train policies."""

import argparse
from collections import Counter
from dataclasses import asdict
import gzip
import hashlib
import json
from pathlib import Path
import platform
import time

import numpy as np
import torch

from .controller import ControllerConfig, ReferenceController
from .environment import LoaderEnv
from .evaluate import source_identity
from .followup_policy import HistoryEnv
from .followup_study import load_policy
from .reference_audit import initial_status, pack, run as reference_audit
from .scenarios import family


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rollout(seed, scene, policy=None, history=False, expected=None, idle=False, controller_config=None):
    """Execute actual actions and independently account for every reward term."""
    base = LoaderEnv(1, seed=seed, scene=scene)
    env = HistoryEnv(base) if history else base
    if not initial_status(base)[0]['valid']:
        raise ValueError('diagnostic requires a valid start')
    controller = ReferenceController(1, controller_config)
    initial_hash = base.scenario_identity()[0]
    totals = Counter()
    action_square = np.zeros(4)
    max_state_error = max_action_error = max_mass_error = max_reward_error = 0.0
    peak_load = 0.0
    steps = 0
    reward_total = 0.0
    first_load_s = None
    while True:
        observation = env.observe()
        if idle:
            action = np.zeros((1, 4))
        elif policy is None:
            action = controller.act(observation)
        else:
            with torch.no_grad():
                action = policy.sample(policy.encode(observation), deterministic=True)['action'].numpy()
        if expected is not None:
            if steps >= len(expected['records']) - 1:
                raise AssertionError('current rollout exceeds retained trace')
            row = expected['records'][steps]
            max_state_error = max(max_state_error, float(np.abs(pack(base)[0] - row['state']).max()))
            max_action_error = max(max_action_error, float(np.abs(action[0] - row['action']).max()))
        _, reward, term, trunc, info = env.step(action)
        weighted = info['reward_description']['weighted']
        for name, value in weighted.items():
            totals[name] += float(value[0])
        reward_total += float(reward[0])
        max_reward_error = max(max_reward_error, abs(sum(float(v[0]) for v in weighted.values()) - float(reward[0])))
        ledger = base.pile.mass() + base.payload + base.delivered + base.spilled
        max_mass_error = max(max_mass_error, float(np.abs(ledger - base.pile.initial_mass).max()))
        peak_load = max(peak_load, float(base.payload[0]))
        if first_load_s is None and info['transfer']['loaded_kg'][0] > 0:
            first_load_s = float(base.elapsed[0])
        action_square += np.asarray(action[0], dtype=float)**2
        steps += 1
        if (term | trunc).any():
            break
    if expected is not None:
        max_state_error = max(max_state_error, float(np.abs(pack(base)[0] - expected['records'][-1]['state']).max()))
        if steps != expected['steps'] or str(base.reason[0]) != expected['reason']:
            raise AssertionError('retained outcome or step count changed')
        if max_state_error > 1e-7 or max_action_error > 1e-7:
            raise AssertionError('checkpoint inference does not reproduce retained trace')
    if max_mass_error > 1e-7 or max_reward_error > 1e-12:
        raise AssertionError('mass or reward accounting failed')
    return {
        'seed': seed, 'scenario_sha256': initial_hash, 'scene': asdict(scene),
        'controller': 'idle' if idle else ('learned_policy' if policy is not None else 'observation_only_reference'),
        'reference_settings': controller.settings() if policy is None and not idle else None,
        'steps': steps, 'reason': str(base.reason[0]), 'elapsed_s': float(base.elapsed[0]),
        'initial_payload_kg': 0.0, 'delivered_kg': float(base.delivered[0]),
        'spilled_kg': float(base.spilled[0]), 'peak_load_kg': peak_load,
        'first_load_s': first_load_s, 'final_pose': base.pose[0].tolist(),
        'action_rms': np.sqrt(action_square / steps).tolist(),
        'undiscounted_return': reward_total, 'weighted_reward_totals': dict(totals),
        'max_mass_residual_kg': max_mass_error, 'max_reward_decomposition_error': max_reward_error,
        'retained_max_state_error': max_state_error if expected is not None else None,
        'retained_max_action_error': max_action_error if expected is not None else None,
    }


def run(output, evidence):
    output, evidence = Path(output), Path(evidence)
    if output.exists():
        raise FileExistsError('choose a new output directory')
    source = source_identity()
    if source['training_dirty']:
        raise ValueError('commit training changes before retaining diagnostic evidence')
    torch.set_num_threads(1)
    output.mkdir(parents=True)
    started = time.perf_counter()
    retained = json.loads((evidence / 'report.json').read_text())
    learned = []
    # All declared methods and both retained test scenes, first declared seed.
    # These are reused diagnostic scenes, not a new held-out evaluation set.
    first_seed = min(row['seed'] for row in retained['runs'])
    for row in retained['runs']:
        if row['seed'] != first_seed:
            continue
        checkpoint = evidence / row['selected']['path']
        if digest(checkpoint) != row['selected']['sha256']:
            raise AssertionError('retained checkpoint hash changed')
        policy, identity = load_policy(checkpoint)
        for trace in row['traces']:
            trace_path = evidence / trace['path']
            if digest(trace_path) != trace['sha256']:
                raise AssertionError('retained trace hash changed')
            expected = json.loads(gzip.decompress(trace_path.read_bytes()))
            case = rollout(trace['seed'], family('standard')[0], policy,
                           row['method'] == 'history_ppo', expected)
            case.update(method=row['method'], training_seed=row['seed'],
                        checkpoint=checkpoint.relative_to(evidence).as_posix(),
                        checkpoint_sha256=digest(checkpoint), trace_sha256=digest(trace_path),
                        original_source=identity['source'])
            learned.append(case)
        print(row['method'], 'retained inference verified', flush=True)
    reference = []
    for name in ('standard', 'low_grip', 'occluded', 'blocked'):
        for seed in (200000, 200001):
            reference.append({'family': name, **rollout(seed, family(name)[0])})
    idle = [rollout(seed, family('standard')[0], idle=True) for seed in (200000, 200001)]
    # Isolate control-loop sensitivity without changing the physical time budget.
    sensitivity = []
    for label, scene, config in (
        ('default', family('standard')[0], None),
        ('slower_approach', family('standard')[0], {'approach_m_s': 0.7}),
        ('faster_approach', family('standard')[0], {'approach_m_s': 1.1}),
    ):
        sensitivity.append({'variant': label, **rollout(100000, scene,
                            controller_config=ControllerConfig(**(config or {})))})
    audit = reference_audit(output / 'reference-audit')
    report = {
        'schema': 'learning-readiness-v1', 'source_mode': 'recorded_synthetic',
        'source': source, 'hardware': {'machine': platform.machine(), 'python': platform.python_version(),
                                      'numpy': np.__version__, 'torch': torch.__version__, 'torch_threads': 1},
        'protocol': {'training_updates': 0, 'learned_training_seed': first_seed,
                     'scene_seeds': [200000, 200001], 'methods': [r['method'] for r in retained['runs'] if r['seed'] == first_seed],
                     'selection': 'all methods, first declared training seed, both existing test traces',
                     'scope': 'reused diagnostic scenes, not independent test evidence or a learning improvement'},
        'retained_report_sha256': digest(evidence / 'report.json'),
        'learned': learned, 'reference': reference, 'idle': idle,
        'controller_sensitivity': sensitivity,
        'reference_audit': {'path': 'reference-audit/report.json', 'sha256': digest(output / 'reference-audit/report.json'),
                            'cases': len(audit['reference_cases']),
                            'outcomes': dict(Counter(r['outcome'] for r in audit['reference_cases'])),
                            'integration_comparison_passed': all(r['passed'] for r in audit['integration_comparison'])},
        'curriculum_gates': [{'method': r['method'], 'seed': r['seed'], 'stages': sorted(set(c['stage'] for c in r['curve'])),
                              'last_gate': r['gates'][-1] if r['gates'] else None,
                              'counters': r['counters']} for r in retained['runs']],
        'wall_s': time.perf_counter() - started,
        'limits': 'Uncalibrated cell-centre material contact and conservative swept AABBs. '
                  'No training, new learned proficiency, real sensor validation or deployment evidence.',
    }
    (output / 'report.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, default=Path('../docs/phase-11/policy-followup-evidence'))
    args = parser.parse_args()
    result = run(args.output, args.evidence)
    print(json.dumps({'output': str(args.output), 'learned_cases': len(result['learned']),
                      'reference_cases': len(result['reference']), 'wall_s': result['wall_s']}))
