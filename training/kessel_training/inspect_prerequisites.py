"""Audit retained teacher coverage and stage prerequisites, without task training."""

import argparse
from dataclasses import asdict, replace
import gzip
import json
from pathlib import Path
import time

import numpy as np
import torch

from .contracts import ACTION_NAMES, LoaderConfig
from .controller import ReferenceController
from .core_smoke import smoke
from .curriculum import STAGES, TrainingEnv
from .diagnose_readiness import digest
from .environment import LoaderEnv, SceneConfig, PROPRIO_NAMES
from .evaluate import source_identity
from .followup_study import load_policy, raw_observation, teacher_pairs
from .reference_audit import initial_status, pack
from .scenarios import family


def stage_environment(stage, seed):
    if stage not in STAGES:
        raise ValueError('unknown curriculum stage')
    scene = family('standard')[0]
    if stage == 'complete':
        return LoaderEnv(1, seed=seed, scene=scene)
    env = TrainingEnv(1, seed=seed, scene=scene, curriculum=True, shaping=False)
    env.stage_index = STAGES.index(stage)
    env.base.scene = env._scene()
    env.reset(seed=seed)
    return env


def stage_probe(stage, seed, policy=None):
    env = stage_environment(stage, seed)
    if not initial_status(env)[0]['valid']:
        raise ValueError('invalid prepared stage start')
    controller = ReferenceController(1)
    # Prepared stages require matching controller state, not an approach restart.
    controller.phase[:] = {'fill': 1, 'retract': 2, 'carry': 3, 'complete': 0}[stage]
    initial_payload = float(env.payload[0])
    trace = []
    max_mass_residual = 0.0
    while True:
        observation = env.observe()
        if policy is None:
            action = controller.act(observation)
        else:
            with torch.no_grad():
                action = policy.sample(policy.encode(observation), deterministic=True)['action'].numpy()
        row = {'t_s': float(env.elapsed[0]), 'state': pack(env)[0].tolist(), 'action': action[0].tolist()}
        _, reward, term, trunc, info = env.step(action)
        row.update(next_state=pack(env)[0].tolist(), reward=float(reward[0]),
                   transfer={k: float(info['transfer'][k][0]) for k in ('loaded_kg', 'delivered_kg', 'spilled_kg')})
        trace.append(row)
        mass = env.pile.mass() + env.payload + env.delivered + env.spilled
        max_mass_residual = max(max_mass_residual, float(np.abs(mass - env.pile.initial_mass).max()))
        if (term | trunc).any():
            break
    if max_mass_residual > 1e-7:
        raise AssertionError('prepared stage material accounting failed')
    return {'stage': stage, 'seed': seed, 'split': 'validation',
            'controller': 'learned_policy' if policy is not None else 'stage_initialised_reference',
            'initial_payload_kg': initial_payload, 'prepared_start': stage != 'complete',
            'reason': str(env.reason[0]), 'steps': len(trace), 'cycle_s': float(env.elapsed[0]),
            'stage_success': str(env.reason[0]) in ('stage_success', 'success'),
            'full_success': str(env.reason[0]) == 'success' and initial_payload == 0 and stage == 'complete',
            'peak_load_kg': float(env.peak_load[0]), 'delivered_kg': float(env.delivered[0]),
            'max_mass_residual_kg': max_mass_residual, 'records': trace}


def observation_aliases():
    base = SceneConfig()
    variants = {'baseline': base, 'narrower_corridor': replace(base, half_width_m=3.8),
                'blocked_route': replace(base, obstacles=((6.0, 6.1, -4.2, 4.2),))}
    reference = LoaderEnv(1, seed=7, scene=base).observe()
    rows = []
    for name, scene in variants.items():
        env = LoaderEnv(1, seed=7, scene=scene)
        rows.append({'variant': name, 'scene': asdict(scene), 'initial_valid': initial_status(env)[0]['valid'],
                     'same_initial_observation': all(np.array_equal(reference[k], env.observe()[k]) for k in reference),
                     'scenario_sha256': env.scenario_identity()[0]})
    return rows


def teacher_metrics(policy, data):
    with torch.no_grad():
        prediction = policy.sample(policy.encode(raw_observation(data['observation'])), deterministic=True)['action'].numpy()
    squared = (prediction - data['action'])**2
    return {'training_pair_action_mse': float(squared.mean()),
            'per_action_mse': squared.mean(axis=0).tolist(),
            'per_phase': [{'phase': phase, 'rows': int((data['phase'] == phase).sum()),
                           'action_mse': float(squared[data['phase'] == phase].mean())}
                          for phase in range(5) if (data['phase'] == phase).any()]}


def run(output, evidence):
    output, evidence = Path(output), Path(evidence)
    if output.exists():
        raise FileExistsError('choose a new output directory')
    source = source_identity()
    if source['training_dirty']:
        raise ValueError('commit training code before retaining diagnostic evidence')
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    output.mkdir(parents=True)
    started = time.perf_counter()
    old = json.loads((evidence / 'report.json').read_text())
    if digest(evidence / 'teacher.npz') != old['teacher_sha256']:
        raise AssertionError('teacher archive hash changed')
    with np.load(evidence / 'teacher.npz', allow_pickle=False) as archive:
        data = {k: archive[k].copy() for k in archive.files}
    regenerated, episodes = teacher_pairs(len(data['phase']))
    if episodes != old['teacher_episodes'] or any(not np.array_equal(data[k], regenerated[k]) for k in data):
        raise AssertionError('teacher generation changed')
    coverage = {'rows': len(data['phase']), 'episodes': episodes,
                'phase_counts': np.bincount(data['phase'], minlength=5).tolist(),
                'observation_min': data['observation'].min(axis=0).tolist(),
                'observation_max': data['observation'].max(axis=0).tolist(),
                'action_min': data['action'].min(axis=0).tolist(),
                'action_max': data['action'].max(axis=0).tolist(),
                'unique_teacher_reference_decisions': len(data['phase']),
                'reconstruction_diagnostic_decisions': len(data['phase'])}
    comparisons = []
    for row in old['runs']:
        if row['method'] != 'bc_ppo':
            continue
        for candidate in row['candidates']:
            if candidate['label'] not in ('warm-start', 'final'):
                continue
            path = evidence / candidate['path']
            if digest(path) != candidate['sha256']:
                raise AssertionError('candidate checkpoint hash changed')
            policy, _ = load_policy(path)
            comparison = {'training_seed': row['seed'], 'candidate': candidate['label'],
                          'checkpoint': candidate['path'], 'checkpoint_sha256': candidate['sha256'],
                          'retained_complete_validation': candidate['validation'], **teacher_metrics(policy, data)}
            if row['seed'] == min(r['seed'] for r in old['runs']):
                comparison['stage_probes'] = []
                for stage in STAGES:
                    for seed in (100000, 100001):
                        probe = stage_probe(stage, seed, policy)
                        filename = f'bc-{row["seed"]}-{candidate["label"]}-{stage}-{seed}.json.gz'
                        (output / filename).write_bytes(gzip.compress(json.dumps(probe, separators=(',', ':'), allow_nan=False).encode(), mtime=0))
                        comparison['stage_probes'].append({k: v for k, v in probe.items() if k != 'records'} | {'trace': filename})
            comparisons.append(comparison)
        print('teacher comparison', row['seed'], 'verified', flush=True)
    references = [stage_probe(stage, seed) for stage in STAGES for seed in (100000, 100001)]
    for probe in references:
        filename = f'reference-{probe["stage"]}-{probe["seed"]}.json.gz'
        (output / filename).write_bytes(gzip.compress(json.dumps(probe, separators=(',', ':'), allow_nan=False).encode(), mtime=0))
        probe.pop('records')
        probe['trace'] = filename
    # These are execution/throughput checks, not task-proficiency experiments.
    timings = [smoke(seed=seed, num_envs=4, rollout_steps=64, updates=4) for seed in (7, 19, 41)]
    report = {'schema': 'learning-prerequisites-v1', 'source_mode': 'recorded_synthetic', 'source': source,
              'original_report_sha256': digest(evidence / 'report.json'), 'teacher_sha256': old['teacher_sha256'],
              'protocol': {'evaluation_seeds': [100000, 100001], 'stage_probe_training_seed': 7,
                           'candidate_labels': ['warm-start', 'final'], 'stages': list(STAGES),
                           'task_training_updates': 0, 'timing_smoke_rollouts': 12,
                           'timing_smoke_reference_decisions': 3072,
                           'scope': 'reused validation scenes and training pairs; no new held-out proficiency result'},
              'teacher_coverage': coverage, 'candidate_comparisons': comparisons, 'reference_stage_probes': references,
              'observation_contract': {'proprio_names': list(PROPRIO_NAMES), 'height_shape': [5, 5],
                                       'validity_shape': [5, 5], 'total_features': 65,
                                       'action_names': list(ACTION_NAMES), 'loader': asdict(LoaderConfig()),
                                       'initial_scene_aliases': observation_aliases()},
              'curriculum': [{'seed': r['seed'], 'transitions': [c['transition'] | {'rollout': c['rollout']} for c in r['curve'] if c['transition']],
                              'last_gate': r['gates'][-1], 'retention': r['retention'], 'training_counters': r['counters']}
                             for r in old['runs'] if r['method'] == 'bridged_curriculum'],
              'cpu_execution_smokes': timings, 'wall_s': time.perf_counter() - started,
              'limits': 'Small synthetic diagnostics. Teacher MSE is in-distribution training fit, not task success. '
                        'Prepared stage success is not an empty-start full cycle. Timing weights are discarded; '
                        'throughput cannot predict the interaction budget needed for learning.'}
    (output / 'report.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    files = {p.name: digest(p) for p in sorted(output.iterdir()) if p.is_file()}
    (output / 'files.json').write_text(json.dumps(files, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, default=Path('../docs/phase-11/policy-followup-evidence'))
    args = parser.parse_args()
    result = run(args.output, args.evidence)
    print(json.dumps({'output': str(args.output), 'wall_s': result['wall_s']}))
