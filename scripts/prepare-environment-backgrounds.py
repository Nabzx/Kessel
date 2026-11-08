"""Deterministic crops of the cleared source photographs for immersive selection.

Usage: isolated Pillow Python scripts/prepare-environment-backgrounds.py <source-dir>
No image synthesis, outbound requests or replacement of the original previews.
"""
from pathlib import Path
import hashlib,json,sys
from PIL import Image,ImageOps
ROOT=Path(__file__).resolve().parents[1]

def prepare(source):
 manifest=json.loads((ROOT/'assets/environments/manifest.json').read_text());rows=[]
 for item in manifest['images']:
  original=source/(item['source'] if item['id']!='underground' else 'mine-hires.tif')
  photo=ImageOps.exif_transpose(Image.open(original)).convert('RGB');dimensions=list(photo.size)
  width=min(2048,photo.width);size=(width,round(width*9/16));focal=(.5,.34) if item['id']=='underground' else tuple(item['focal'])
  crop=ImageOps.fit(photo,size,method=Image.Resampling.LANCZOS,centering=focal)
  relative='assets/environments/'+item['id']+'-scene.webp';target=ROOT/relative;crop.save(target,'WEBP',quality=88,method=6)
  rows.append({**{k:item[k] for k in ('id','page','credit','subject','notice','representative')},'source_url':item['url'] if item['id']!='underground' else item['page']+'#hlHighResDownload','source_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),'source_bytes':original.stat().st_size,'source_dimensions':dimensions,'path':relative,'dimensions':list(crop.size),'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'colour_space':'srgb','operation':'EXIF orientation; 16:9 crop at declared focal point; Lanczos downsample; WebP quality 88; no synthesis or upscaling','focal':list(focal)})
 (ROOT/'assets/environments/backgrounds.json').write_text(json.dumps({'schema':'immersive-backgrounds-v1','date':'2026-11-08','images':rows,'total_bytes':sum(r['bytes'] for r in rows)},indent=2)+'\n')
 print([(r['id'],r['dimensions'],r['bytes']) for r in rows])
if __name__=='__main__':prepare(Path(sys.argv[1]))
