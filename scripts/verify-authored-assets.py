"""Check pinned Blender source/derivative provenance and bounded self-contained GLBs."""
import hashlib
import json
from pathlib import Path
import struct
ROOT=Path(__file__).resolve().parents[1]

def glb(path):
    blob=path.read_bytes();magic,version,total=struct.unpack_from('<III',blob)
    assert magic==0x46546c67 and version==2 and total==len(blob),path
    size,kind=struct.unpack_from('<II',blob,12);assert kind==0x4e4f534a
    data=json.loads(blob[20:20+size]);assert not data.get('extensionsRequired'),path
    assert all(not b.get('uri') for b in data.get('buffers',[])),path
    assert all('bufferView' in i for i in data.get('images',[])),path
    triangles=sum(data['accessors'][p['indices']]['count']//3 for m in data.get('meshes',[]) for p in m['primitives'])
    return data,triangles

def verify():
    manifest=json.loads((ROOT/'assets/authored/manifest.json').read_text())
    assert manifest['connector_revision']=='2e4b0bc294694b1570d76ed01be657c22e6d02a0'
    assert manifest['blender']=='5.2.3 LTS' and manifest['safe_mode'] and not manifest['telemetry']
    counts={}
    for row in manifest['assets']:
        path=ROOT/row['path'];assert path.stat().st_size==row['bytes']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256']
        source=ROOT/row['source'];assert source.exists() and hashlib.sha256(source.read_bytes()).hexdigest()==row['source_sha256']
        if path.suffix=='.glb':
            data,triangles=glb(path);assert triangles==row['triangles'] and triangles<=50000
            assert len(data.get('nodes',[]))<=80 and len(path.read_bytes())<3_000_000
            counts[path.stem]=triangles
    assert counts['hauler-overview']<counts['hauler-close']
    assert counts['observation-satellite-overview']<counts['observation-satellite']
    loader,_=glb(ROOT/'assets/authored/reference-loader.glb')
    names={n.get('name') for n in loader['nodes']}
    assert {'ReferenceLoader','FrontJoint','Boom','Bucket','Wheel_0','Wheel_3'}<=names
    assert loader.get('animations')
    assert all(s.get('interpolation','LINEAR')=='LINEAR' for a in loader['animations'] for s in a['samplers'])
    machine,_=glb(ROOT/'assets/authored/excavator.glb')
    assert len(machine.get('skins',[]))==1 and len(machine['skins'][0]['joints'])==11
    assert {'KesselNode_6','KesselNode_10','KesselNode_5'}<={n.get('name') for n in machine['nodes']}
    for script in manifest['scripts']:
        assert hashlib.sha256((ROOT/script['path']).read_bytes()).hexdigest()==script['sha256']
    print('PASS: bounded GLBs, baked detail, source hashes, licensed rig, pivots and distinct hauler LODs')
if __name__=='__main__':verify()
