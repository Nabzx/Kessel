"""Portable source/derivative integrity and finite, physically coherent film motion."""
import hashlib,json,math,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];m=json.loads((ROOT/'assets/film/manifest.json').read_text())
for a in m['assets']+m['sources']:
 p=ROOT/a['path'];assert p.stat().st_size==a['bytes'];assert hashlib.sha256(p.read_bytes()).hexdigest()==a['sha256'],p
# Read the actual MP4 movie clock, independent of the declared manifest.
blob=(ROOT/'assets/film/surface.mp4').read_bytes()
def boxes(start,end):
 while start+8<=end:
  size,kind=struct.unpack_from('>I4s',blob,start);header=8
  if size==1:size=struct.unpack_from('>Q',blob,start+8)[0];header=16
  if size==0:size=end-start
  assert size>=header and start+size<=end,'Invalid MP4 box'
  yield kind,start+header,start+size
  start+=size
moov=next((a,b) for kind,a,b in boxes(0,len(blob)) if kind==b'moov')
a,b=next((a,b) for kind,a,b in boxes(*moov) if kind==b'mvhd')
version=blob[a]
if version==0:scale,duration=struct.unpack_from('>II',blob,a+12)
else:scale=struct.unpack_from('>I',blob,a+20)[0];duration=struct.unpack_from('>Q',blob,a+24)[0]
assert abs(duration/scale-m['encoding']['duration_s'])<.05,'Encoded duration disagrees with the source clock'
assert m['encoding']['duration_s']==16 and m['encoding']['output_fps']==24
assert m['assets'][0]['bytes']<4_000_000
trace=json.loads((ROOT/'data/surface-haul.json').read_text());audit=json.loads((ROOT/'assets/film/scene-audit.json').read_text())
assert trace['loop'] is False and m['motion']['loop'] is False and audit['rotation_mode']=='XYZ'
assert len(audit['samples'])==len(trace['rows'])
for row,pose in zip(trace['rows'],audit['samples']):
 assert pose['heading_dot']>.99999
 assert all(abs(y-trace['ground_y_m'])<.00001 for y in pose['tyre_bottoms'])
 assert abs(pose['forward'][0]-math.sin(row[4]))<1e-6 and abs(pose['forward'][1]+math.cos(row[4]))<1e-6
assert trace['rows'][0][5]==0 and trace['rows'][-1][5]==0
assert trace['rows'][-1][4]-trace['rows'][0][4]>1.5,'Truck must actually turn'
assert trace['rows'][-1][13]>26,'Haul makes useful progress'
assert (ROOT/'tools/blender/references/surface/makehuman-base.obj').read_text().find('explicitly released as CC0')>=0
print('PASS: packed Blender source, CC0 provenance, bounded local film, finite haul, evaluated orientation and tyre contact')
