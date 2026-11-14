"""Execute retained pilot checkpoints and independently replay held-out actions."""

import argparse
import json
from pathlib import Path
import sys
import tempfile
import zipfile
import gzip

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / 'training'))

import numpy as np
import torch
from kessel_training import checkpoints
from kessel_training.evaluate import source_identity
from kessel_training.inspect_prerequisites import stage_environment, stage_probe
from kessel_training.policy import ActorCritic, configure_cpu
from kessel_training.wm_state import pack


def run(folder):
    folder = Path(folder)
    report = json.loads((folder / 'report.json').read_text())
    if source_identity()['package_sha256'] != report['plan']['source']['package_sha256']:
        raise ValueError('restore the recorded source package before executing checkpoints')
    configure_cpu(0)
    decisions = 0
    maximum_state = maximum_action = 0.0
    with tempfile.TemporaryDirectory(prefix='kessel-pilot-replay-') as temporary:
        extracted = Path(temporary)
        with zipfile.ZipFile(folder / 'artifacts.zip') as archive:
            for name in archive.namelist():
                target = extracted / name
                if not target.resolve().is_relative_to(extracted.resolve()):
                    raise ValueError('invalid archive path')
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(name))
        for run in report['runs']:
            key = f'{run["configuration"]["setting"]}-{run["configuration"]["seed"]}'
            path = extracted / key / run['selected']['path']
            if checkpoints.sha256(path) != run['selected']['sha256']:
                raise ValueError('selected checkpoint hash differs')
            state = checkpoints.load(path)
            if state['software'] != {'torch': str(torch.__version__), 'numpy': np.__version__}:
                raise ValueError('restore the pinned numerical library versions before replay')
            policy = ActorCritic(64)
            policy.load_state_dict(state['actor_critic'])
            policy.eval()
            for expected in run['selected']['validation']:
                actual = stage_probe('retract', expected['seed'], policy)
                decisions += actual['steps']
                assert actual['reason'] == expected['reason'] and actual['steps'] == expected['steps']
                assert (actual['reason'] == 'stage_success') == expected['stage_success']
                for metric in ('delivered_kg', 'peak_load_kg', 'cycle_s'):
                    assert abs(actual[metric] - expected[metric]) < 1e-7
            matched = next((t for t in report['tests'] if t['seed'] == run['configuration']['seed'] and t['setting'] == run['configuration']['setting']), None)
            if matched is None:
                continue
            for case in matched['cases']:
                trace_path = extracted / key / case['trace']
                assert checkpoints.sha256(trace_path) == case['trace_sha256']
                trace = json.loads(gzip.decompress(trace_path.read_bytes()))
                assert trace['split'] == 'test' and trace['initial_payload_kg'] == 1500
                env = stage_environment('retract', case['seed'])
                for row in trace['records']:
                    maximum_state = max(maximum_state, float(np.abs(pack(env)[0] - row['state']).max()))
                    with torch.no_grad():
                        action = policy.sample(policy.encode(env.observe()), deterministic=True)['action'].numpy()
                    maximum_action = max(maximum_action, float(np.abs(action[0] - row['action']).max()))
                    env.step(np.asarray([row['action']]))
                    maximum_state = max(maximum_state, float(np.abs(pack(env)[0] - row['next_state']).max()))
                    decisions += 1
                assert str(env.reason[0]) == case['reason']
                assert (str(env.reason[0]) == 'stage_success') == case['stage_success']
    if maximum_state > 1e-7 or maximum_action > 1e-7:
        raise AssertionError('independent checkpoint/action replay changed')
    return {'schema': 'pilot-independent-replay-v1', 'checkpoint_validation_cases': sum(len(r['selected']['validation']) for r in report['runs']),
            'heldout_traces': sum(len(t['cases']) for t in report['tests']), 'diagnostic_reference_decisions': decisions,
            'maximum_state_error': maximum_state, 'maximum_action_error': maximum_action,
            'scope': 'Post-study verification only; no training, selection change or new proficiency estimate.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder', type=Path, default=root / 'docs/phase-11/retraction-pilot-evidence')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('choose a new verification output')
    result = run(args.folder)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
