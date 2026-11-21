"""Bounded sensor, recorded-result and metadata audit for the remaining demo research."""

import argparse
from dataclasses import asdict
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np

from .environment import LoaderEnv, SceneConfig
from .evaluate import source_identity
from .followup_data import SensorEnv, SensorProfile, observation_inventory
from .wm_state import pack


def sensor_probe(profile, connected):
    base = LoaderEnv(2, seed=100000, scene=SceneConfig(randomise=True))
    base.pose[:, 0] = base.pile.origin[:, 0] - 4.2
    base.joints[:, 1] = -0.1
    base.initial_pose[:] = base.pose
    base._update_observations(np.ones(2, dtype=bool), reset=True)
    env = SensorEnv(base, SensorProfile(**profile, communications_available=connected))
    states, valid, age = [], [], []
    observations = []
    for _ in range(32):
        obs, _, terminated, truncated, _ = env.step(np.tile([.2, 0, 0, .2], (2, 1)))
        if (terminated | truncated).any():
            raise AssertionError('fixed sensor diagnostic ended early')
        states.append(pack(env).copy())
        observations.append(np.concatenate([v.ravel() for v in obs.values()]))
        valid.append(int(obs['range_valid'].sum()))
        age.append(float(obs['proprio'][:, 11].max()))
    return {'profile': asdict(env.profile), 'decisions': 64, 'valid_samples': sum(valid),
            'possible_samples': 1600, 'max_age_s': max(age)}, np.asarray(states), np.asarray(observations)


def scan_seed_references(root):
    references, errors, files = {}, [], []
    def walk(value, path):
        if isinstance(value, dict):
            for key, item in value.items():
                if key in ('seed', 'training_seed') and isinstance(item, int):
                    references.setdefault(item, set()).add(path)
                elif key in ('seeds', 'evaluation_seeds', 'scene_seeds') and isinstance(item, list):
                    for seed in item:
                        if isinstance(seed, int):
                            references.setdefault(seed, set()).add(path)
                elif isinstance(item, dict) or (isinstance(item, list) and item and isinstance(item[0], dict)):
                    walk(item, path)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    walk(item, path)
    for directory in ('data', 'docs/phase-11', 'training/experiments', 'training/runs'):
        for path in sorted((root / directory).rglob('*')):
            if not path.is_file() or not (path.name.endswith('.json') or path.name.endswith('.json.gz')):
                continue
            relative = path.relative_to(root).as_posix()
            try:
                raw = gzip.decompress(path.read_bytes()) if path.name.endswith('.gz') else path.read_bytes()
                walk(json.loads(raw), relative)
                files.append(relative)
            except (ValueError, OSError) as error:
                errors.append({'path': relative, 'error': str(error)})
    candidates = {}
    for name, first, last in [('validation', 108000, 108015), ('pilot_test', 208900, 208915), ('final_test', 209900, 209931)]:
        hits = {str(seed): sorted(references[seed]) for seed in range(first, last + 1) if seed in references}
        candidates[name] = {'first': first, 'last': last, 'explicit_reference_hits': hits,
                            'reservation_verified': False}
    return {'files_scanned': len(files), 'distinct_seed_values': len(references), 'errors': errors,
            'candidates': candidates,
            'coverage': 'Explicit JSON/JSON.gz metadata fields in listed directories, including local raw diagnostic runs.',
            'exclusions': ['NPZ arrays', 'PT checkpoints', 'JSONL streams', 'deleted Git history',
                           'implicit generator offsets and schedules', 'external or unretained runs'],
            'conclusion': 'No metadata hit is not proof of an untouched scenario. Complete the excluded-source audit before reservation.'}


def audit(root):
    root = Path(root)
    source = source_identity()
    if source['training_dirty']:
        raise ValueError('commit diagnostic code before recording evidence')
    sensors = []
    clean, physics, _ = sensor_probe({}, False)
    for name, profile in [('clean', {}), ('delay', {'range_latency_steps': 2}),
                          ('impaired', {'range_latency_steps': 2, 'dropout': .25, 'occlusion': .15, 'range_noise_m': .01}),
                          ('dropout', {'dropout': 1.0})]:
        offline, states, observed = sensor_probe(profile, False)
        online, connected_states, connected_observed = sensor_probe(profile, True)
        offline.update(name=name, physics_max_error_vs_clean=float(np.abs(states - physics).max()),
                       communications_physics_max_error=float(np.abs(states - connected_states).max()),
                       communications_observation_max_error=float(np.abs(observed - connected_observed).max()))
        if any(offline[k] > 1e-12 for k in ('physics_max_error_vs_clean', 'communications_physics_max_error', 'communications_observation_max_error')):
            raise AssertionError('sensor/communications wrapper changed fixed-action physics')
        sensors.append(offline)
    scorecards = []
    for filename in ('reference', 'curriculum', 'loader'):
        path = root / f'data/experiments/{filename}-v1.json'
        bundle = json.loads(path.read_text())
        cases = [{'name': e['name'], 'outcome': e['outcome'], 'initial_payload_kg': e['records'][0]['state'][7],
                  'delivered_kg': e['metrics']['delivered_kg'], 'steps': e['steps'],
                  'complete_empty_start_success': e['outcome'] == 'success' and e['records'][0]['state'][7] == 0}
                 for e in bundle['episodes']]
        scorecards.append({'run_id': bundle['run_id'], 'bundle_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                          'agent': 'reference_controller' if (bundle.get('agent') or {}).get('kind') == 'reference_controller' else 'learned_policy',
                          'cases': cases, 'selection': bundle['presentation'].get('selection'),
                          'limits': 'Selected exported episodes, not an aggregate proficiency or generalisation benchmark.'})
    model_path = root / 'docs/phase-11/world-followup-evidence/report.json'
    wm = json.loads(model_path.read_text())
    models = {name: {k: m['raw']['one_step']['natural'][k] for k in ('position_mae_m', 'mass_balance_mae_kg', 'reward_mae')}
              | {'supported_horizon': m['raw']['calibration']['supported_horizon']} for name, m in wm['models'].items()}
    return {'schema': 'demo-frontier-audit-v1', 'source': source,
            'sensor_protocol': {'slots': 2, 'steps': 32, 'fixed_action': [.2, 0, 0, .2],
                                'executed_reference_decisions': 576,
                                'scope': 'Nine fixed-action diagnostic rollouts, no closed-loop policy robustness or real sensor validation.'},
            'sensors': sensors, 'observability': observation_inventory(),
            'seed_inventory': scan_seed_references(root), 'scorecards': scorecards,
            'world_model_report_sha256': hashlib.sha256(model_path.read_bytes()).hexdigest(),
            'world_models': models,
            'event_failures': {name: {k: event[k] for k in ('actual', 'false_positive', 'false_negative', 'precision', 'recall')}
                               for name, event in wm['events']['test'].items() if name != 'stop_tradeoff'},
            'assistance': {'full_cycle_successes': sum(case['full_success'] for t in wm['assistance']['treatments'] for case in t['test']),
                           'critic_updates': sum(record['critic_update'] is not None for t in wm['assistance']['treatments'] for record in t['auxiliary_records']),
                           'imagined_transitions': sum(record['branches']['imagined_transitions'] for t in wm['assistance']['treatments'] for record in t['auxiliary_records'])}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('choose a new output file')
    result = audit(Path(__file__).resolve().parents[2])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'output': str(args.output), 'sensors': len(result['sensors']),
                      'metadata_files': result['seed_inventory']['files_scanned']}))
