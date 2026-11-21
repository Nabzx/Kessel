"""Independently verify retained readiness identities, ledgers and trace hashes."""

import gzip
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    repo = Path(__file__).resolve().parents[1]
    root = repo / 'docs/phase-11/readiness-evidence'
    files = json.loads((root / 'files.json').read_text())
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    assert actual == set(files) | {'files.json'}, 'unlisted or missing evidence'
    for relative, expected in files.items():
        path = root / relative
        assert path.resolve().is_relative_to(root.resolve()), 'invalid manifest path'
        assert sha(path) == expected, f'changed evidence: {relative}'
    report = json.loads((root / 'report.json').read_text())
    assert report['schema'] == 'learning-readiness-v1'
    assert not report['source']['training_dirty']
    assert report['protocol']['training_updates'] == 0
    original = repo / 'docs/phase-11/policy-followup-evidence'
    assert sha(original / 'report.json') == report['retained_report_sha256']
    previous = json.loads((original / 'report.json').read_text())
    expected_pairs = {(run['method'], trace['seed']) for run in previous['runs']
                      if run['seed'] == report['protocol']['learned_training_seed']
                      for trace in run['traces']}
    assert {(r['method'], r['seed']) for r in report['learned']} == expected_pairs
    assert len(report['learned']) == len(expected_pairs)
    for case in report['learned']:
        run = next(r for r in previous['runs'] if r['method'] == case['method'] and r['seed'] == case['training_seed'])
        trace = next(t for t in run['traces'] if t['seed'] == case['seed'])
        assert sha(original / case['checkpoint']) == case['checkpoint_sha256'] == run['selected']['sha256']
        assert sha(original / trace['path']) == case['trace_sha256'] == trace['sha256']
        assert case['retained_max_state_error'] <= 1e-7
        assert case['retained_max_action_error'] <= 1e-7
        assert case['steps'] == trace['steps'] and case['reason'] == trace['reason']
    for case in report['learned'] + report['reference'] + report['idle'] + report['controller_sensitivity']:
        assert case['initial_payload_kg'] == 0
        assert case['max_mass_residual_kg'] <= 1e-7
        assert case['max_reward_decomposition_error'] <= 1e-12
        assert abs(sum(case['weighted_reward_totals'].values()) - case['undiscounted_return']) < 1e-9
        if case['reason'] == 'success':
            assert case['delivered_kg'] >= case['scene']['success_kg']
    audit_path = root / report['reference_audit']['path']
    assert sha(audit_path) == report['reference_audit']['sha256']
    audit = json.loads(audit_path.read_text())
    assert len(audit['reference_cases']) == report['reference_audit']['cases']
    for case in audit['reference_cases']:
        path = root / 'reference-audit' / f'{case["scene"]["pile_family"]}-{case["seed"]}.json.gz'
        trace = json.loads(gzip.decompress(path.read_bytes()))
        encoded = json.dumps([r['next_state'] for r in trace['records']], sort_keys=True,
                             separators=(',', ':'), allow_nan=False).encode()
        assert hashlib.sha256(encoded).hexdigest() == case['state_sha256'] == trace['state_sha256']
        assert trace['outcome'] == case['outcome']
        assert abs(trace['delivered_kg'] - case['delivered_kg']) < 1e-9
        assert trace['independent_max_state_error'] <= 1e-9
        assert max(abs(r['mass_residual_kg']) for r in trace['records']) <= 1e-7
    print(f'Readiness evidence verified: {len(expected_pairs)} learned replays and {len(audit["reference_cases"])} reference traces')


if __name__ == '__main__':
    verify()
