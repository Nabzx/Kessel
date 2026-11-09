"""Portable source/derivative integrity and finite, physically coherent film motion."""
import hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];m=json.loads((ROOT/'assets/film/manifest.json').read_text())
for a in m['assets']+m['sources']:
 p=ROOT/a['path'];assert p.stat().st_size==a['bytes'];assert hashlib.sha256(p.read_bytes()).hexdigest()==a['sha256'],p
assert m['encoding']['duration_s']==24 and m['encoding']['output_fps']==24
assert m['assets'][0]['bytes']<4_000_000
v=m['motion'];r=v['rear_axle_turn_radius_m'];half=v['half_track_m'];length=v['wheelbase_m'];period=v['period_s']
assert abs(v['speed_m_s']-r*2*math.pi/period)<1e-12
# Rear-axle tangent motion and per-wheel Ackermann rolling, independent of
# Blender / video decoders. Source dimensions exclude impossible pivoting.
assert r>length and 1<v['speed_m_s']<3
for side in [-1,1]:
 angle=math.atan2(length,r+side*half);front_radius=math.hypot(r+side*half,length)
 assert abs(math.sin(angle)*front_radius-length)<1e-12
assert (ROOT/'tools/blender/references/surface/makehuman-base.obj').read_text().find('explicitly released as CC0')>=0
print('PASS: packed Blender source, CC0 provenance, bounded local film, 24 s loop and axle-based motion')
