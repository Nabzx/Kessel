"""Validate immutable photographic backgrounds and the new orbital asset contract."""
import hashlib,json,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def verify():
 data=json.loads((ROOT/'data/experience.json').read_text());manifest=json.loads((ROOT/'assets/environments/backgrounds.json').read_text())
 assert [e['id'] for e in data['environments']]==['underground','glacier','desert','space','deep-sea']
 assert len(manifest['images'])==5
 for row in manifest['images']:
  path=ROOT/row['path'];blob=path.read_bytes()
  assert blob[:4]==b'RIFF' and blob[8:12]==b'WEBP'
  assert len(blob)==row['bytes'] and hashlib.sha256(blob).hexdigest()==row['sha256']
  assert 1400<=row['dimensions'][0]<=2048 and abs(row['dimensions'][0]/row['dimensions'][1]-16/9)<.003
  assert row['dimensions'][0]<=row['source_dimensions'][0] and row['dimensions'][1]<=row['source_dimensions'][1]
  assert row['source_sha256'] and row['source_url'].startswith('https://') and row['credit'] and row['notice']
  assert row['colour_space']=='srgb' and row['representative'] and row['bytes']<2_500_000
  environment=next(e for e in data['environments'] if e['id']==row['id']);assert environment['background_image']['path']==row['path']
 assert sum(r['bytes'] for r in manifest['images'])==manifest['total_bytes']<1_500_000
 assert 'not Rutongo' in next(r for r in manifest['images'] if r['id']=='underground')['subject']
 assets=json.loads((ROOT/'assets/authored/manifest.json').read_text())['assets'];sat={r['path']:r for r in assets if 'satellite' in r['path']}
 hi=sat[data['visuals']['home']['satellite_model']];low=sat[data['visuals']['home']['satellite_overview']]
 assert low['triangles']<hi['triangles']<35000 and hi['bytes']<3_000_000
 html=(ROOT/'index.html').read_text();assert 'class="permanent-caption"' not in html
 assert 'scenario-note">Illustrative operating scenario' in html and 'id="sources-open"' in html
 for path in ['assets/brand/kessel-orbital.svg','assets/brand/kessel-instrument.svg']:assert '<path ' in (ROOT/path).read_text()
 print('PASS: Underground-first order, five cleared full-screen photos, exact hashes, genuine spacecraft LOD and contextual source controls')
if __name__=='__main__':verify()
