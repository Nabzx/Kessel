#!/usr/bin/env python3
"""Independently execute selected validation policies and every retained final trace."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'training'))
import numpy as np
import torch
from kessel_training import checkpoints
from kessel_training.evaluate import source_identity
from kessel_training.full_cycle import probe, policy_identity, full_score
from kessel_training.five_stage import FiveStageEnv
from kessel_training.policy import ActorCritic, configure_cpu
from kessel_training.scenarios import family
from kessel_training.wm_state import pack


def execute(evidence, output, names=None):
    report = json.loads((evidence/'report.json').read_text())
    if source_identity()['package_sha256'] != report['plan']['source']['package_sha256']:
        raise ValueError('independent execution requires archived exact training source')
    configure_cpu(7)
    temporary = tempfile.TemporaryDirectory()
    try:
        if (evidence/'artifacts.zip').exists():
            runs = Path(temporary.name)
            with zipfile.ZipFile(evidence/'artifacts.zip') as archive:
                for name in archive.namelist():
                    if PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts:
                        raise ValueError('unsafe archive path')
                archive.extractall(runs)
        else:
            runs = evidence
        results, maximum_state, maximum_action, maximum_reward = [], 0., 0., 0.
        validation_decisions, trace_decisions = 0, 0
        for run in report['runs']:
            name = f'{run["configuration"]["method"]}-{run["configuration"]["seed"]}'
            if names is not None and name not in names:
                continue
            directory = runs/name
            selected = run['selected']
            if selected != report['selection'][name]:
                raise AssertionError('selection changed')
            path = directory/selected['path']
            if checkpoints.sha256(path) != selected['sha256']:
                raise AssertionError('selected checkpoint hash differs')
            state = checkpoints.load(path)
            if state['software'] != {'torch': str(torch.__version__), 'numpy': np.__version__}:
                raise ValueError('numerical library versions differ')
            actor = ActorCritic(64); actor.load_state_dict(state['actor_critic'])
            if policy_identity(actor) != selected['policy_sha256']:
                raise AssertionError('selected policy identity differs')
            for expected in selected['validation']:
                actual = probe(actor, 'complete', expected['seed'])
                for key in ('reason', 'steps', 'cycle_s', 'full_success', 'delivered_kg', 'initial_state_sha256'):
                    if actual[key] != expected[key]:
                        raise AssertionError('selected validation differs: '+key)
                validation_decisions += actual['steps']
            for case in run['tests']:
                trace_path = directory/case['trace']
                if checkpoints.sha256(trace_path) != case['trace_sha256']:
                    raise AssertionError('trace hash differs')
                trace = json.loads(gzip.decompress(trace_path.read_bytes()))
                env = FiveStageEnv(1, seed=case['seed'], scene=family('standard')[0], stage='complete', shaping=False)
                initial = hashlib.sha256(pack(env)[0].astype('<f8').tobytes()).hexdigest()
                if initial != case['initial_state_sha256']:
                    raise AssertionError('test initial identity differs')
                for row in trace['records']:
                    maximum_state = max(maximum_state, float(np.abs(pack(env)[0]-row['state']).max()))
                    with torch.no_grad():
                        action = actor.sample(actor.encode(env.observe()), deterministic=True)['action'].numpy()[0]
                    maximum_action = max(maximum_action, float(np.abs(action-row['action']).max()))
                    _, reward, _, _, info = env.step(np.asarray([row['action']]))
                    maximum_state = max(maximum_state, float(np.abs(pack(env)[0]-row['next_state']).max()))
                    maximum_reward = max(maximum_reward, abs(float(reward[0])-row['raw_reward']))
                    trace_decisions += 1
                if len(trace['records']) != case['steps'] or not (env.terminated | env.truncated).all():
                    raise AssertionError('trace is incomplete')
                if str(env.reason[0]) != case['reason'] or float(env.delivered[0]) != case['delivered_kg'] or bool(info['metrics']['full_success'][0]) != case['full_success']:
                    raise AssertionError('test outcome differs')
            results.append({'run': name, 'selected_validation_cases': len(selected['validation']),
                            'held_out_traces': len(run['tests']), 'test_score': full_score(run['tests'])})
            print('Replayed', name, flush=True)
        if max(maximum_state, maximum_action, maximum_reward) != 0:
            raise AssertionError('independent state/action/reward error is nonzero')
        result = {'kind': 'full-cycle-independent-replay-v1', 'source': report['plan']['source'],
            'runs': results, 'validation_decisions': validation_decisions, 'trace_decisions': trace_decisions,
            'max_state_error': maximum_state, 'max_action_error': maximum_action, 'max_raw_reward_error': maximum_reward}
        output.write_text(json.dumps(result, indent=2)+'\n')
        return result
    finally:
        temporary.cleanup()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--runs', nargs='+')
    args = parser.parse_args()
    execute(args.evidence, args.output, args.runs)
