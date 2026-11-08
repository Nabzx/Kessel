"""Bind displayed export comparisons and photographic sky to cleared sources."""
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[1]
d=json.loads((root/'data/engineering.json').read_text());raw=(root/d['source']).read_bytes();assert hashlib.sha256(raw).hexdigest()==d['sha256']
source=json.loads(raw)
for row in d['variants']:
 ref=next(r for r in source['variants'] if r['variant']==row['variant'])
 assert all(row[k]==ref[k] for k in row)
sky=json.loads((root/'assets/materials/sky-manifest.json').read_text());raw=(root/sky['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==sky['sha256'] and len(raw)==sky['bytes']<2_500_000
assert sky['licence']=='CC0-1.0' and sky['scope']=='Representative sky, not a Rwanda observation'
print('PASS: retained CPU figures and cleared local sky hashes')
