"""Prepare small local PBR maps from the retained, cleared look-development maps.

Run with Pillow 13.0.0. No source download or runtime image processing.
"""
from pathlib import Path
import hashlib
import json
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'docs/phase-11/lookdev/assets'
OUT = ROOT / 'assets/materials'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    OUT.mkdir(exist_ok=True)
    records = []
    for name in ['rock_face_03', 'dark_rock_02']:
        for channel in ['diff', 'nor_gl', 'rough', 'ao']:
            source = SOURCE / f'{name}_{channel}_1k.jpg'
            if not source.exists():
                source = SOURCE / f'{name}_{channel.upper()}_1k.jpg'
            image = Image.open(source).convert('RGB')
            if channel == 'nor_gl':
                image = image.resize((512,512), Image.Resampling.LANCZOS)
            if channel in ['rough', 'ao']:
                image = image.convert('L').resize((512, 512), Image.Resampling.LANCZOS)
            dest = OUT / f'{name}_{channel}.webp'
            # Avoid lossy tangent-normal block artefacts. Scalar maps are linear.
            image.save(dest, format='WEBP', lossless=channel != 'diff', quality=86, method=6)
            records.append(dict(path=str(dest.relative_to(ROOT)), sha256=sha(dest), bytes=dest.stat().st_size,
                                source=str(source.relative_to(ROOT)), source_sha256=sha(source),
                                source_bytes=source.stat().st_size, channel=channel,
                                colour_space='srgb' if channel == 'diff' else 'linear', width=image.width,
                                height=image.height, licence='CC0-1.0', source_url=f'https://polyhaven.com/a/{name}',
                                repeat_m=2.7 if name == 'rock_face_03' else 2.0))
    (OUT / 'manifest.json').write_text(json.dumps(dict(generator='Pillow 13.0.0; scripts/prepare-visual-materials.py',
        notes='Rock Face 03 by Dario Barresi / Rico Cilliers. Dark Rock 02 by Amal Kumar. JPEG source maps are retained in lookdev.',
        maps=records), indent=2) + '\n')
    print(json.dumps({'source_bytes':sum(r['source_bytes'] for r in records),
                      'webp_bytes':sum(r['bytes'] for r in records)}))

if __name__ == '__main__':
    main()
