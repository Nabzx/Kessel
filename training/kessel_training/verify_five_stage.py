"""Reference-only feasibility and independent action replay on consumed validation scenes."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np

from .contracts import canonical_json
from .controller import ReferenceController
from .evaluate import source_identity
from .five_stage import CONTRACT, STAGES, FiveStageEnv
from .reference_audit import pack
from .scenarios import family

SEEDS = tuple(range(108000, 108016))
PHASES = dict(fill=1, retract=2, carry=3, tip=4, complete=0)


def environment(stage, seed):
    return FiveStageEnv(1, seed=seed, scene=family('standard')[0], stage=stage)


def replay(stage, seed, records, expected=None):
    env = environment(stage, seed)
    maximum = 0.
    for index, row in enumerate(records):
        if (env.terminated | env.truncated).any():
            raise AssertionError('trace continues after terminal')
        maximum = max(maximum, float(np.abs(pack(env)[0]-row['state']).max()))
        _, reward, _, _, info = env.step(np.asarray([row['action']]))
        maximum = max(maximum, float(np.abs(pack(env)[0]-row['next_state']).max()),
                      abs(float(reward[0])-row['reward']))
    if maximum != 0 or not (env.terminated | env.truncated).all():
        raise AssertionError('action replay differs or trace incomplete')
    if expected is not None:
        actual = {'stage_success': bool(info['metrics']['stage_success'][0]),
                  'full_success': bool(info['metrics']['full_success'][0]),
                  'reason': str(env.reason[0]), 'delivered_kg': float(env.delivered[0]),
                  'retained_kg': float(env.payload[0]), 'cycle_s': float(env.elapsed[0])}
        if any(expected[key] != value for key, value in actual.items()):
            raise AssertionError('reported outcome differs from replay')
    return maximum


def collect(stage, seed):
    env = environment(stage, seed)
    controller = ReferenceController(1)
    controller.phase[:] = PHASES[stage]
    initial = pack(env)[0].tolist()
    records, residual = [], 0.
    while True:
        state = pack(env)[0].tolist()
        action = controller.act(env.observe())
        _, reward, term, trunc, info = env.step(action)
        residual = max(residual, float(np.abs(env.pile.mass()+env.payload+env.delivered+
                                             env.spilled-env.pile.initial_mass).max()))
        records.append({'state': state, 'action': action[0].tolist(),
                        'next_state': pack(env)[0].tolist(), 'reward': float(reward[0])})
        if (term | trunc).any():
            break
    if residual > 1e-7:
        raise AssertionError('ledger failed')
    summary = {'stage': stage, 'seed': seed, 'split': 'consumed_validation',
        'controller': 'stage_initialised_reference', 'learned_policy': False,
        'prepared_start': stage != 'complete', 'initial_payload_kg': initial[7],
        'initial_state_sha256': hashlib.sha256(canonical_json(initial).encode()).hexdigest(),
        'stage_success': bool(info['metrics']['stage_success'][0]),
        'full_success': bool(info['metrics']['full_success'][0]), 'reason': str(env.reason[0]),
        'steps': len(records), 'cycle_s': float(env.elapsed[0]),
        'delivered_kg': float(env.delivered[0]), 'retained_kg': float(env.payload[0]),
        'max_mass_residual_kg': residual, 'replay_max_error': replay(stage, seed, records)}
    return summary, records


def run(output):
    source = source_identity()
    if source['training_dirty']:
        raise ValueError('commit training source before retaining results')
    output.mkdir(parents=True, exist_ok=False)
    cases, traces = [], []
    for stage in STAGES:
        for seed in SEEDS:
            summary, records = collect(stage, seed)
            cases.append(summary)
            traces.append({'stage': stage, 'seed': seed, 'records': records})
        print(stage, sum(c['stage_success'] for c in cases if c['stage'] == stage), '/16', flush=True)
    trace_path = output/'traces.json.gz'
    # Fixed gzip metadata for repeatable archival bytes.
    trace_path.write_bytes(gzip.compress(canonical_json(traces).encode(), mtime=0))
    report = {'contract': CONTRACT, 'source': source, 'controller': ReferenceController(1).settings(),
        'purpose': 'reference feasibility only; no learned training or final-test evaluation',
        'cases': cases, 'reference_decisions': sum(c['steps'] for c in cases),
        'replay_decisions': sum(c['steps'] for c in cases),
        'traces_sha256': hashlib.sha256(trace_path.read_bytes()).hexdigest()}
    (output/'report.json').write_text(json.dumps(report, indent=2)+'\n')


def verify(output):
    report = json.loads((output/'report.json').read_text())
    if source_identity()['package_sha256'] != report['source']['package_sha256']:
        raise ValueError('replay requires the recorded source package')
    trace_bytes = (output/'traces.json.gz').read_bytes()
    if hashlib.sha256(trace_bytes).hexdigest() != report['traces_sha256']:
        raise ValueError('trace hash differs')
    traces = json.loads(gzip.decompress(trace_bytes))
    if len(report['cases']) != 80:
        raise ValueError('case count differs')
    if [(t['stage'], t['seed']) for t in traces] != [(s, n) for s in STAGES for n in SEEDS]:
        raise ValueError('stage/scene coverage differs')
    for row, case in zip(traces, report['cases'], strict=True):
        if len(row['records']) != case['steps']:
            raise ValueError('decision count differs')
        replay(row['stage'], row['seed'], row['records'], case)
    print('Verified all 80 reference traces with zero state/reward error')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    (verify if args.verify else run)(args.output)


if __name__ == '__main__':
    main()
