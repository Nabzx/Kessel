#!/usr/bin/env python3
"""Seal retained continuation artefacts and the source files that define their roles."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
folders=('docs/phase-11/shift-evidence','docs/phase-11/working-policy-model-evidence',
         'docs/phase-11/continuation-evidence','docs/phase-11/live-demo','training/kessel_lab','training/tests_lab')
suffixes={'.py','.json','.zip','.svg','.jpg','.jsonl','.html','.css','.js','.md','.cjs','.txt'}
paths={p for name in folders for p in (ROOT/name).rglob('*') if p.is_file() and p.suffix in suffixes and '__pycache__' not in p.parts}
for name in ('docs/adr/0062-interactive-synthetic-runtime.md','docs/phase-11/shift-study.md',
             'docs/phase-11/world-model-shift-protocol.md','docs/phase-11/working-policy-models.md',
             'docs/phase-11/runtime-and-observations.md','docs/phase-11/continuation-review.md',
             'scripts/verify-shift-evidence.py','scripts/research/seal-shift-evidence.py',
             'scripts/research/verify-shift-actions.py','scripts/research/evaluate-working-policy-models.py',
             'scripts/research/verify-live-demo.cjs','scripts/research/probe-observation-recorder.py',
             'scripts/research/audit-simulator-extensions.py','scripts/research/plot-shift-scorecard.py',
             'scripts/research/review-full-experience.cjs','scripts/research/profile-presentation.cjs',
             'scripts/research/verify-offline-presentation.cjs','scripts/research/verify-visibility-resize.cjs',
             'js/experience.js','index.html'):
    paths.add(ROOT/name)
output=ROOT/'docs/phase-11/shift-evidence/files.json';paths.discard(output)
manifest={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}
output.write_text(json.dumps(manifest,indent=2)+'\n');print('Sealed',len(manifest),'source and evidence files')
