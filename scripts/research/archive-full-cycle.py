#!/usr/bin/env python3
"""Freeze the completed six-run study before any idempotence checks alter its logs."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def archive(study, evidence):
    report = json.loads((study/'report.json').read_text())
    if len(report['runs']) != 6 or any(not r['test_complete'] or r['phase'] != 'done' for r in report['runs']):
        raise ValueError('all six final-test sets must be complete')
    for name in ('report.json', 'plan.json', 'selection.json'):
        path = evidence/name
        if path.exists():
            raise FileExistsError(path)
        shutil.copyfile(study/name, path)
    paths = set()
    for run in report['runs']:
        name = f'{run["configuration"]["method"]}-{run["configuration"]["seed"]}'
        paths.add(name+'/events.jsonl')
        for candidate in run['candidates']:
            paths.add(name+'/'+candidate['path']); paths.add(name+'/'+candidate['path']+'.sha256')
        for case in run['tests']:
            paths.add(name+'/'+case['trace'])
        for line in (study/name/'events.jsonl').read_text().splitlines():
            row = json.loads(line)
            if row['kind'] == 'gate':
                checkpoint = f'transaction-{row["sequence"]+1:06}.pt'
                paths.add(name+'/'+checkpoint); paths.add(name+'/'+checkpoint+'.sha256')
    interruption = json.loads(Path('/tmp/kessel-full-cycle-interrupt.json').read_text())
    checkpoint = 'plain-7/'+interruption['pointer']['path']
    paths.add(checkpoint); paths.add(checkpoint+'.sha256')
    with zipfile.ZipFile(evidence/'artifacts.zip', 'x', zipfile.ZIP_DEFLATED) as z:
        for name in sorted(paths):
            z.write(study/name, name)
    with zipfile.ZipFile(evidence/'source.zip', 'x', zipfile.ZIP_DEFLATED) as z:
        for path in sorted((ROOT/'training/kessel_training').glob('*.py')):
            z.write(path, 'kessel_training/'+path.name)
        for name in ('pyproject.toml', 'uv.lock'):
            z.write(ROOT/'training'/name, name)
        for name in ('train-full-cycle-worker.py', 'archive-full-cycle.py', 'check-full-cycle-resume.py', 'replay-full-cycle.py', 'plot-full-cycle.py'):
            z.write(ROOT/'scripts/research'/name, 'research/'+name)
    shutil.copyfile('/tmp/kessel-full-cycle-interrupt.json', evidence/'interruption-check.json')
    shutil.copyfile('/tmp/kessel-full-cycle-hardware.json', evidence/'hardware.json')
    traces = [study/f'{r["configuration"]["method"]}-{r["configuration"]["seed"]}'/c['trace']
              for r in report['runs'] for c in r['tests']]
    consumption = {'kind': 'full-cycle-consumption-v1',
        'validation_role': 'consumed for current/prior-stage gates and full-task selection',
        'final_test_role': 'consumed_once_after_all_six_frozen_selections',
        'final_test_seeds': report['plan']['final_test_seeds'], 'final_policy_cases': len(traces),
        'selection_sha256': hashlib.sha256((study/'selection.json').read_bytes()).hexdigest(),
        'selection_mtime_ns': (study/'selection.json').stat().st_mtime_ns,
        'first_test_trace_mtime_ns': min(p.stat().st_mtime_ns for p in traces)}
    if consumption['selection_mtime_ns'] >= consumption['first_test_trace_mtime_ns']:
        raise AssertionError('selection was not frozen before tests')
    (evidence/'consumption.json').write_text(json.dumps(consumption, indent=2)+'\n')
    print('Archived', len(paths), 'files and all', len(traces), 'final traces')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--study', type=Path, required=True)
    p.add_argument('--evidence', type=Path, required=True)
    a = p.parse_args(); archive(a.study, a.evidence)
