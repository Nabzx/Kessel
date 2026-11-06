"""Prepare cleared aerial ground maps. Usage: python script.py <source directory>."""
import hashlib
import json
from pathlib import Path
import sys
from PIL import Image
root = Path(__file__).resolve().parents[1]
records = []
for channel in ['diff', 'nor_gl', 'rough']:
    source = Path(sys.argv[1]) / f'aerial_grass_rock_{channel}_1k.jpg'
    image = Image.open(source).convert('RGB')
    if channel != 'diff':
        image = image.resize((512, 512), Image.Resampling.LANCZOS)
    if channel == 'rough':
        image = image.convert('L')
    target = root / f'assets/materials/aerial_grass_rock_{channel}.webp'
    image.save(target, format='WEBP', quality=86, lossless=channel != 'diff', method=6)
    records.append(dict(path=str(target.relative_to(root)), sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
        bytes=target.stat().st_size, source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        source_bytes=source.stat().st_size, source_url=f'https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/aerial_grass_rock/{source.name}',
        channel=channel, colour_space='srgb' if channel == 'diff' else 'linear', width=image.width,height=image.height,
        licence='CC0-1.0', repeat_m=15))
(root / 'assets/materials/surface-manifest.json').write_text(json.dumps(dict(source='https://polyhaven.com/a/aerial_grass_rock',
    credit='Aerial Grass Rock by Rob Tuytel, Poly Haven', licence='CC0-1.0', generator='Pillow 13.0.0; scripts/prepare-surface-materials.py', maps=records),indent=2)+'\n')
