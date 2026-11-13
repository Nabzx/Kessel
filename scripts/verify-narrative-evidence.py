"""Check narrative research source identities and retained browser evidence."""

import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
study = root / 'docs/phase-11/narrative-study'
manifest = json.loads((study / 'evidence/manifest.json').read_text())
for relative, expected in manifest['files'].items():
    path = root / relative
    assert path.resolve().is_relative_to(root.resolve())
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, f'changed narrative evidence/source: {relative}'
report = json.loads((study / 'evidence/report.json').read_text())
assert report['errors'] == []
assert len(report['profiles']) == 3 and len(report['recovery']) == 2
bundles = {name: json.loads((root / f'data/experiments/{name}-v1.json').read_text()) for name in ('reference', 'curriculum')}
count = 0
for profile in report['profiles']:
    frames = profile['frames']
    if profile['spec']['width'] <= 700:
        assert frames == []  # Narrow navigation check is not desktop framing qualification.
        continue
    assert len(frames) == 5
    for frame in frames:
        bundle = bundles['curriculum' if frame['step'] == 'learn' else 'reference']
        assert frame['source'] == bundle['run_id']
        assert frame['checkedPoses'] == 2 * len(bundle['episodes'][0]['records']) - 1
        safe, projected = frame['fit']['safe'], frame['fit']['projected']
        assert safe['left'] - 1 <= projected['left'] <= projected['right'] <= safe['right'] + 1
        assert safe['top'] - 1 <= projected['top'] <= projected['bottom'] <= safe['bottom'] + 1
        count += frame['checkedPoses']
assert count == 6014
assert all(name in report['baseline'] for name in ('earth', 'environments', 'surface', 'training'))
print(f'Narrative research evidence verified: {count} pose/midpoint checks, three viewport profiles and loading recovery')
