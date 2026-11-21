#!/usr/bin/env python3
"""Verify retained five-stage reference evidence using only the standard library."""
import gzip
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT/'docs/phase-11/five-stage-evidence'
STAGES = ('fill', 'retract', 'carry', 'tip', 'complete')


def verify():
    manifest = json.loads((EVIDENCE/'files.json').read_text())
    for name, digest in manifest.items():
        assert hashlib.sha256((EVIDENCE/name).read_bytes()).hexdigest() == digest, name
    report = json.loads((EVIDENCE/'report.json').read_text())
    assert report['contract'] == 'five-stage-potential-v2'
    assert report['source']['training_dirty'] is False
    trace_data = (EVIDENCE/'traces.json.gz').read_bytes()
    assert hashlib.sha256(trace_data).hexdigest() == report['traces_sha256']
    traces = json.loads(gzip.decompress(trace_data))
    pairs = [(s, n) for s in STAGES for n in range(108000, 108016)]
    assert [(c['stage'], c['seed']) for c in report['cases']] == pairs
    assert [(c['stage'], c['seed']) for c in traces] == pairs
    decisions = 0
    for case, trace in zip(report['cases'], traces, strict=True):
        assert case['controller'] == 'stage_initialised_reference'
        assert case['learned_policy'] is False and case['split'] == 'consumed_validation'
        stage = case['stage']
        assert case['initial_payload_kg'] == (2200 if stage in ('retract', 'carry', 'tip') else 0)
        assert case['stage_success'] and case['full_success'] == (stage == 'complete')
        assert case['reason'] == ('success' if stage in ('tip', 'complete') else 'stage_success')
        assert case['replay_max_error'] == 0 and case['max_mass_residual_kg'] < 1e-7
        rows = trace['records']
        assert len(rows) == case['steps'] and rows
        assert hashlib.sha256(json.dumps(rows[0]['state'], sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest() == case['initial_state_sha256']
        for prior, following in zip(rows, rows[1:]):
            assert prior['next_state'] == following['state']
        if stage in ('tip', 'complete'):
            assert case['delivered_kg'] >= 2000
        if stage in ('retract', 'carry'):
            assert case['retained_kg'] >= 2100
        decisions += len(rows)
    assert report['reference_decisions'] == report['replay_decisions'] == decisions
    with zipfile.ZipFile(EVIDENCE/'source.zip') as archive:
        digest = hashlib.sha256()
        for name in sorted(n for n in archive.namelist() if n.startswith('kessel_training/') and n.endswith('.py')):
            digest.update(Path(name).name.encode())
            digest.update(archive.read(name))
        assert digest.hexdigest() == report['source']['package_sha256']
    print(f'Five-stage evidence verified: 80 reference successes, {decisions} decisions plus replay; no learned result')


if __name__ == '__main__':
    verify()
