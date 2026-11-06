"""Verify local visual derivatives, scale metadata and geometry budgets."""
import hashlib
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]

def verify():
    data = json.loads((ROOT / 'data/experience.json').read_text())
    records = []
    for name in ['manifest.json', 'surface-manifest.json']:
        manifest = json.loads((ROOT / 'assets/materials' / name).read_text())
        for item in manifest['maps']:
            path = ROOT / item['path']
            assert path.stat().st_size == item['bytes'], path
            assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256'], path
            assert item['colour_space'] == ('srgb' if item['channel'] == 'diff' else 'linear')
            assert item['licence'] == 'CC0-1.0' and item['repeat_m'] > 0
            if item.get('source'):
                assert hashlib.sha256((ROOT / item['source']).read_bytes()).hexdigest() == item['source_sha256']
            records.append(item)
    main = [r for r in records if 'rock_face_03' in r['path']]
    assert sum(r['bytes'] for r in main) < data['visuals']['budgets']['main_rock_maps_max_bytes']
    assert data['visuals']['rock']['repeat_m'] == 2.7
    assert data['visuals']['surface']['ground']['repeat_m'] == 15
    orbit = json.loads((ROOT / 'assets/models/iss/manifest.json').read_text())
    binary = (ROOT / orbit['path']).read_bytes()
    assert hashlib.sha256(binary).hexdigest() == orbit['sha256']
    magic, version, length = struct.unpack_from('<4sII', binary)
    assert magic == b'glTF' and version == 2 and length == len(binary)
    size, kind = struct.unpack_from('<I4s', binary, 12)
    assert kind == b'JSON'
    model = json.loads(binary[20:20+size])
    assert not model.get('textures') and not model.get('extensionsRequired')
    triangles = sum(model['accessors'][p['indices']]['count']//3 for mesh in model['meshes'] for p in mesh['primitives'])
    assert triangles == orbit['triangles'] <= data['visuals']['budgets']['orbit_triangles_max']
    assert orbit['bytes'] == len(binary) < 200_000
    assert data['visuals']['orbit']['decorative'] is True
    # Keep the licensed articulated model byte-for-byte intact.
    excavator = ROOT / 'assets/models/excavator/excavator.gltf'
    assert hashlib.sha256(excavator.read_bytes()).hexdigest() == '4e6cd154c3c25f92d2ff9566dc461fd26fd07e0aedec875fbb4df9e2c14ef9f5'
    truck = json.loads((ROOT / data['assets']['truck']).read_text())
    assert truck['forward_axis'] == [0,0,1] and truck['wheels']['radius_m'] > 0
    services = data['visuals']['services']
    for run in services['runs']:
        assert min(run['from'][1],run['to'][1]) - services['vent_radius_m'] > data['mine']['floor_y'] + truck['dimensions_m']['height'] + 1
    assert data['visuals']['dust']['capacity'] <= data['visuals']['budgets']['dust_particles_max']
    print(f'PASS: {len(records)} hashed CC0 maps, {triangles} NASA triangles, intact licensed rig and presentation budgets')

if __name__ == '__main__':
    verify()
