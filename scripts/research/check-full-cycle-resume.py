#!/usr/bin/env python3
"""Check that resuming a completed study adds no decisions or changes to selection/tests."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def check(study, evidence):
    before = json.loads((study/'report.json').read_text())
    selection_hash = hashlib.sha256((study/'selection.json').read_bytes()).hexdigest()
    process = subprocess.run([sys.executable, '-m', 'kessel_training.full_cycle', '--output', str(study.resolve()),
        '--reservation', str((evidence/'reservation.json').resolve()), '--resume'],
        cwd=ROOT/'training', text=True, capture_output=True, check=True)
    after = json.loads((study/'report.json').read_text())
    result = {'kind': 'completed-full-cycle-resume-v1',
        'selection_unchanged': before['selection'] == after['selection'] and
            selection_hash == hashlib.sha256((study/'selection.json').read_bytes()).hexdigest(),
        'test_outcomes_unchanged': [r['tests'] for r in before['runs']] == [r['tests'] for r in after['runs']],
        'counter_deltas': [{k: new['counters'][k]-old['counters'][k] for k in old['counters']}
                           for old, new in zip(before['runs'], after['runs'], strict=True)],
        'stdout': process.stdout}
    if not result['selection_unchanged'] or not result['test_outcomes_unchanged'] or any(any(row.values()) for row in result['counter_deltas']):
        raise AssertionError('completed study changed on resume')
    (evidence/'resume-check.json').write_text(json.dumps(result, indent=2)+'\n')
    print('Completed-study resume: zero decision deltas, selection and tests unchanged')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--study', type=Path, required=True)
    p.add_argument('--evidence', type=Path, required=True)
    a = p.parse_args(); check(a.study, a.evidence)
