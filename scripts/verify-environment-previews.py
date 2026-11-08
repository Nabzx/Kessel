"""Verify source notices, local photo derivatives and authored preview contracts."""
from pathlib import Path
import hashlib
import json
ROOT=Path(__file__).resolve().parents[1]

def verify():
    manifest=json.loads((ROOT/'assets/environments/manifest.json').read_text())
    data=json.loads((ROOT/'data/experience.json').read_text())
    records={item['id']:item for item in manifest['images']}
    assert set(records)=={e['id'] for e in data['environments']}
    for environment in data['environments']:
        item=records[environment['id']];file=ROOT/item['path']
        assert file.stat().st_size==item['bytes']
        assert hashlib.sha256(file.read_bytes()).hexdigest()==item['sha256']
        assert item['dimensions']==[768,432] and item['colour_space']=='srgb'
        assert item['credit'] and item['notice'] and item['source_sha256'] and item['source_bytes']>0
        assert item['page'].startswith('https://') and item['url'].startswith('https://')
        assert item['representative'] and environment['preview']['representative']
        assert environment['preview']['path']==item['path'] and environment['preview']['alt']
    assert 'not Rutongo' in records['underground']['subject']
    assert sum(r['bytes'] for r in records.values())==manifest['total_bytes']<350_000
    home=data['visuals']['home']
    assert 0<home['station_span']<1.5 and 2.38<home['night_radius']<home['cloud_radius']<home['atmosphere_radius']
    assert len(home['star_sizes'])==3 and all(0<s<.1 for s in home['star_sizes'])
    print('PASS: five credited reference photographs, hashes, colour space, byte budget and home layer bounds')
if __name__=='__main__':verify()
