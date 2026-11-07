"""Freeze original DCC source, scripted operations and shipped derivative hashes."""
import hashlib
import json
from pathlib import Path
import struct
ROOT=Path(__file__).resolve().parents[2]

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def prepare():
    rows=[]
    for path in sorted((ROOT/'assets/authored').iterdir()):
        if path.suffix not in ('.glb','.webp'):continue
        source=ROOT/'tools/blender/source'/(path.stem+'.blend' if path.suffix=='.glb' else 'material-calibration.blend')
        row={'path':str(path.relative_to(ROOT)),'bytes':path.stat().st_size,'sha256':digest(path),
             'source':str(source.relative_to(ROOT)),'source_sha256':digest(source),
             'licence':'CC-BY-4.0; mohamed.salaah880; non-destructive rig round trip' if path.stem=='excavator' else 'Original Kessel; repository LICENSE',
             'units':'Original asset units; browser normalises horizontal length to 7 m' if path.stem=='excavator' else 'metres; proposed kit displayed at 10x presentation scale'}
        if path.suffix=='.glb':
            blob=path.read_bytes();size=struct.unpack_from('<I',blob,12)[0];data=json.loads(blob[20:20+size])
            row['triangles']=sum(data['accessors'][p['indices']]['count']//3 for m in data.get('meshes',[]) for p in m['primitives']);row['nodes']=len(data['nodes'])
        else:
            original=ROOT/'tools/blender/bakes'/(path.stem+'.png')
            row.update(original_bake=str(original.relative_to(ROOT)),original_sha256=digest(original),operation='Lossless WebP; exact decoded RGBA pixels',colour_space='linear data; GL tangent normal or AO')
        rows.append(row)
    manifest={'blender':'5.2.3 LTS','blender_build':'e13b728c6880','connector_revision':'2e4b0bc294694b1570d76ed01be657c22e6d02a0','connector_version':'2.2.7','safe_mode':True,'telemetry':False,
        'source_mode':'Original synthetic visual geometry; proposed kit; not calibrated simulator collision geometry or a Rutongo survey.','assets':rows,
        'scripts':[{'path':str(p.relative_to(ROOT)),'sha256':digest(p)} for p in sorted((ROOT/'tools/blender').glob('*.py'))]}
    (ROOT/'assets/authored/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
if __name__=='__main__':prepare()
