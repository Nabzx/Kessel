#!/usr/bin/env python3
"""Check bounded full-cycle study evidence without numerical dependencies."""
import gzip
import hashlib
import json
from pathlib import Path
import statistics
import struct
import zipfile

ROOT = Path(__file__).resolve().parents[1]
E = ROOT/'docs/phase-11/full-cycle-evidence'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def collision(c):
    return c['reason'] in ('tunnel_wall', 'tunnel_roof') or c['reason'].startswith('obstacle')


def score(cases):
    good = [c for c in cases if c['full_success'] and c['reason'] == 'success' and c['delivered_kg'] >= 2000]
    return [len(good), -sum(collision(c) for c in cases), -statistics.mean(c['cycle_s'] for c in good) if good else 0.]


def verify():
    manifest = json.loads((E/'files.json').read_text())
    for name, digest in manifest.items():
        assert sha((E/name).read_bytes()) == digest, name
    report = json.loads((E/'report.json').read_text())
    selection = json.loads((E/'selection.json').read_text())
    assert selection == report['selection']
    proof = json.loads((E/'pre-test-freeze.json').read_text())
    assert proof['no_final_test_files'] and proof['frozen_selections'] == selection
    assert all(r['phase'] == 'frozen' and r['counters']['test_decisions'] == 0 for r in proof['runs'].values())
    interruption = json.loads((E/'interruption-check.json').read_text())
    assert interruption['resume_counters_match']
    assert interruption['after_stop']['payload']['counters'] == interruption['resume_event']['payload']['counters']
    assert report['plan']['source']['training_dirty'] is False
    reservation = json.loads((E/'reservation.json').read_text())
    assert reservation['final_test_verified_unused'] and not reservation['disallowed_hits'] and not reservation['errors']
    assert sha((E/'reservation.json').read_bytes()) == report['plan']['reservation_sha256']
    final = list(range(209900, 209932)); validation = list(range(108000, 108016))
    assert report['plan']['final_test_seeds'] == reservation['final_test_seeds'] == final
    assert report['plan']['validation_seeds'] == validation
    identities = {c['seed']: c['starts']['complete']['state_float64_sha256'] for c in reservation['final_initial_identities']}
    runs = report['runs']
    assert [(r['configuration']['method'], r['configuration']['seed']) for r in runs] == [(m, s) for m in ('plain', 'curriculum') for s in (7, 19, 41)]
    with zipfile.ZipFile(E/'artifacts.zip') as archive:
        for run in runs:
            name = f'{run["configuration"]["method"]}-{run["configuration"]["seed"]}'
            c = run['counters']; config = run['configuration']
            assert config['max_rollouts'] == 640 and config['stage_rollouts'] == 128
            assert config['max_wall_s'] == 1200 and config['test_reserve_s'] == 240
            assert c['training_decisions'] == c['rollouts']*256 <= 163840
            assert len(run['curve']) == c['rollouts']
            assert sum(r['update']['minibatch_updates'] for r in run['curve']) == c['optimiser_minibatches']
            assert sum(len(r['episodes']) for r in run['curve']) == c['training_episodes']
            assert c['training_resets'] == 4+c['training_episodes']+4*len(run['transitions'])
            for candidate in run['candidates']:
                assert candidate['score'] == score(candidate['validation'])
                assert [v['seed'] for v in candidate['validation']] == validation
                assert all(v['stage'] == 'complete' and v['initial_payload_kg'] == 0 for v in candidate['validation'])
                assert sha(archive.read(name+'/'+candidate['path'])) == candidate['sha256']
                assert archive.read(name+'/'+candidate['path']+'.sha256').decode().strip() == candidate['sha256']
            chosen = max(run['candidates'], key=lambda v: tuple(v['score']))
            assert chosen == run['selected'] == selection[name]
            assert len({v['training_decisions'] for v in run['candidates']}) == len(run['candidates'])
            assert run['phase'] == 'done' and run['test_complete'] and len(run['tests']) == 32
            assert [t['seed'] for t in run['tests']] == final
            assert c['test_decisions'] == sum(t['steps'] for t in run['tests'])
            admitted = score(run['tests'])[0] >= 28 and sum(collision(t) for t in run['tests']) <= 1
            assert admitted == run['capability_gate_passed']
            previous, rows = None, []
            for line in archive.read(name+'/events.jsonl').splitlines():
                row = json.loads(line); digest = row.pop('sha256')
                assert row['sequence'] == len(rows) and row['previous_sha256'] == previous
                assert sha(canonical(row)) == digest
                previous = digest; rows.append(row)
            assert rows[-1]['payload']['counters'] == c
            assert previous == run['log']['last_event_sha256']
            assert sha(archive.read(name+'/events.jsonl')) == run['log']['file_sha256']
            assert sum(r['payload']['case']['steps'] for r in rows if r['kind'] == 'validation_case' and r['payload']['purpose'] == 'full') == c['validation_decisions']
            assert sum(r['payload']['case']['steps'] for r in rows if r['kind'] == 'validation_case' and r['payload']['purpose'] == 'gate') == c['gate_decisions']
            freeze = next(i for i, r in enumerate(rows) if r['kind'] == 'freeze')
            assert all(i > freeze for i, r in enumerate(rows) if r['kind'] == 'test_case')
            assert all(r['payload']['checkpoint_sha256'] == chosen['sha256'] for r in rows if r['kind'] == 'test_case')
            for test in run['tests']:
                data = archive.read(name+'/'+test['trace'])
                assert sha(data) == test['trace_sha256']
                trace = json.loads(gzip.decompress(data)); records = trace['records']
                assert len(records) == test['steps'] and records
                assert sha(struct.pack('<102d', *records[0]['state'])) == identities[test['seed']] == test['initial_state_sha256']
                assert records[0]['state'][7] == 0 and test['initial_payload_kg'] == 0
                for a, b in zip(records, records[1:]):
                    assert a['next_state'] == b['state']
                assert records[-1]['next_state'][8] == test['delivered_kg']
                assert test['max_mass_residual_kg'] < 1e-7
    for method in ('plain', 'curriculum'):
        assert report['admission_by_method'][method] == all(r['capability_gate_passed'] for r in runs if r['configuration']['method'] == method)
    replay = json.loads((E/'independent-replay.json').read_text())
    assert replay['source'] == report['plan']['source']
    assert [r['run'] for r in replay['runs']] == [f'{m}-{s}' for m in ('plain', 'curriculum') for s in (7, 19, 41)]
    assert len(replay['runs']) == 6
    assert sum(r['selected_validation_cases'] for r in replay['runs']) == 96
    assert sum(r['held_out_traces'] for r in replay['runs']) == 192
    assert replay['max_state_error'] == replay['max_action_error'] == replay['max_raw_reward_error'] == 0
    assert replay['trace_decisions'] == sum(r['counters']['test_decisions'] for r in runs)
    resume = json.loads((E/'resume-check.json').read_text())
    assert resume['selection_unchanged'] and resume['test_outcomes_unchanged']
    assert all(all(v == 0 for v in row.values()) for row in resume['counter_deltas'])
    consumption = json.loads((E/'consumption.json').read_text())
    assert consumption['final_test_role'] == 'consumed_once_after_all_six_frozen_selections'
    assert consumption['selection_mtime_ns'] < consumption['first_test_trace_mtime_ns']
    with zipfile.ZipFile(E/'source.zip') as archive:
        digest = hashlib.sha256()
        for name in sorted(n for n in archive.namelist() if n.startswith('kessel_training/') and n.endswith('.py')):
            digest.update(Path(name).name.encode()); digest.update(archive.read(name))
        assert digest.hexdigest() == report['plan']['source']['package_sha256']
    print('Full-cycle study verified: six bounded runs, frozen selection, 192 final cases and independent replay')


if __name__ == '__main__':
    verify()
