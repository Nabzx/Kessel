"""Verify the bounded pilot, frozen selection, costs and retained archive identities."""

import hashlib
import json
import statistics
import struct
import zipfile
import gzip
from pathlib import Path

root = Path(__file__).resolve().parents[1]
folder = root / 'docs/phase-11/retraction-pilot-evidence'
manifest = json.loads((folder / 'files.json').read_text())
for name, digest in manifest.items():
    path = folder / name
    assert path.resolve().is_relative_to(folder.resolve())
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, name
report = json.loads((folder / 'report.json').read_text())
plan = report['plan']
assert plan == json.loads((folder / 'plan.json').read_text())
assert not plan['source']['training_dirty'] and len(report['runs']) == 6
reservation = json.loads((folder / 'reservation.json').read_text())
assert reservation['reservation_verified'] and not reservation['hits'] and not reservation['failures']
assert hashlib.sha256((folder / 'reservation.json').read_bytes()).hexdigest() == plan['reservation_sha256']
assert len(reservation['identities']) == 64
reserved = {r['seed']: r for r in reservation['identities']}
final_seeds = {r['seed'] for r in reservation['identities'] if r['split'] == 'final_test'}
assert final_seeds.isdisjoint(plan['validation_seeds'] + plan['pilot_test_seeds'])
with zipfile.ZipFile(folder / 'source.zip') as archive:
    digest = hashlib.sha256()
    for name in sorted(n for n in archive.namelist() if n.startswith('training/kessel_training/') and n.endswith('.py')):
        digest.update(Path(name).name.encode())
        digest.update(archive.read(name))
    assert digest.hexdigest() == plan['source']['package_sha256']
with zipfile.ZipFile(folder / 'artifacts.zip') as archive:
    for run in report['runs']:
        cfg, counters = run['configuration'], run['counters']
        assert cfg['max_wall_s'] == 600 and cfg['test_reserve_s'] == 60
        assert counters['training_decisions'] == counters['rollouts'] * 256 <= 32768
        assert run['status'] == 'completed' and run['wall_s'] <= cfg['max_wall_s']
        assert len(run['curve']) == counters['rollouts']
        assert sum(c['update']['minibatch_updates'] for c in run['curve']) == counters['optimiser_minibatches']
        assert sum(c['steps'] for batch in run['validation_batches'] for c in batch['cases']) == counters['validation_decisions']
        key = f'{cfg["setting"]}-{cfg["seed"]}'
        for candidate in run['candidates']:
            assert candidate['rollout'] % 16 == 0 and len(candidate['validation']) == 16
            assert [c['seed'] for c in candidate['validation']] == plan['validation_seeds']
            assert all(c['split'] == 'validation' and c['initial_payload_kg'] == 1500 and not c['full_success'] for c in candidate['validation'])
            success = [c for c in candidate['validation'] if c['reason'] == 'stage_success']
            collisions = sum(c['reason'] in ('tunnel_wall', 'tunnel_roof') or c['reason'].startswith('obstacle') for c in candidate['validation'])
            score = [len(success), -collisions, -statistics.mean(c['cycle_s'] for c in success) if success else 0.0]
            assert candidate['score'] == score
            assert hashlib.sha256(archive.read(f'{key}/{candidate["path"]}')).hexdigest() == candidate['sha256']
            assert archive.read(f'{key}/{candidate["path"]}.sha256').decode().strip() == candidate['sha256']
        assert [c['rollout'] for c in run['candidates']] == list(range(0, 129, 16))
        chosen = max(run['candidates'], key=lambda c: tuple(c['score']) + (-c['rollout'],))
        assert run['selected'] == chosen
        assert f'{key}/events.jsonl' in archive.namelist()
        previous = None
        events = [json.loads(line) for line in archive.read(f'{key}/events.jsonl').splitlines()]
        for index, event in enumerate(events):
            digest = event.pop('sha256')
            assert event['sequence'] == index and event['previous_sha256'] == previous
            assert hashlib.sha256(json.dumps(event, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest() == digest
            previous = digest
        assert events[-1]['payload']['counters'] == counters
    assert sum(r['counters']['training_decisions'] for r in report['runs']) == 196608
    medians = {setting: statistics.median(r['selected']['score'][0] for r in report['runs'] if r['configuration']['setting'] == setting) for setting in plan['settings']}
    selected = max(plan['settings'], key=lambda name: (medians[name], name == 'baseline'))
    assert report['selection']['setting'] == selected and report['selection']['validation_medians'] == medians
    assert report['selection'] == json.loads((folder / 'selection.json').read_text())
    passed = sum(r['selected']['score'][0] >= 14 for r in report['runs'] if r['configuration']['setting'] == selected) >= 2
    assert report['selection']['gate_passed'] == passed
    assert len(report['tests']) == 3
    for test in report['tests']:
        assert test['setting'] == selected and test['test_complete'] and len(test['cases']) == 16
        run = next(r for r in report['runs'] if r['configuration']['setting'] == selected and r['configuration']['seed'] == test['seed'])
        assert test['checkpoint_sha256'] == run['selected']['sha256']
        assert [c['seed'] for c in test['cases']] == plan['pilot_test_seeds']
        assert sum(c['steps'] for c in test['cases']) == run['counters']['test_decisions']
        for case in test['cases']:
            assert case['split'] == 'test' and case['initial_payload_kg'] == 1500 and not case['full_success']
            assert case['stage_success'] == (case['reason'] == 'stage_success')
            name = f'{selected}-{test["seed"]}/{case["trace"]}'
            assert hashlib.sha256(archive.read(name)).hexdigest() == case['trace_sha256']
            trace = json.loads(gzip.decompress(archive.read(name)))
            initial = struct.pack('<102d', *trace['records'][0]['state'])
            assert hashlib.sha256(initial).hexdigest() == reserved[case['seed']]['starts']['retract']['state_float64_sha256']
assert not report['full_cycle_training_executed']
assert sum(c['steps'] for c in report['shared_reference_validation']) == report['shared_reference_validation_decisions']
assert all(c['reason'] == 'stage_success' for c in report['shared_reference_validation'])
verification = json.loads((folder / 'independent-replay.json').read_text())
assert verification['checkpoint_validation_cases'] == 96 and verification['heldout_traces'] == 48
assert verification['maximum_state_error'] <= 1e-7 and verification['maximum_action_error'] <= 1e-7
resume = json.loads((folder / 'resume-check.json').read_text())
assert resume['training_decision_delta'] == resume['validation_decision_delta'] == resume['test_decision_delta'] == 0
print('Retraction pilot verified: six bounded runs, validation-only frozen selection, 48 held-out cases and independent checkpoint/action replay')
