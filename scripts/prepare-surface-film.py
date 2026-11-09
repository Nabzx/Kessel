"""Encode the original local Blender frame sequence and freeze provenance."""
import argparse,hashlib,json,subprocess
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def row(p):return {'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':digest(p)}
p=argparse.ArgumentParser();p.add_argument('--frames',type=Path,default=Path('/private/tmp/kessel-surface-film/final'));p.add_argument('--poster',type=Path,default=Path('/private/tmp/kessel-surface-look.png'));p.add_argument('--manifest-only',action='store_true');args=p.parse_args()
out=ROOT/'assets/film';out.mkdir(exist_ok=True)
if not args.manifest_only:
 subprocess.run(['ffmpeg','-y','-framerate','12','-i',str(args.frames/'%04d.png'),'-vf','tpad=stop_mode=clone:stop_duration=0.3,minterpolate=fps=24:mi_mode=blend,trim=duration=24','-an','-c:v','libx264','-preset','medium','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(out/'surface.mp4')],check=True)
 Image.open(args.poster).save(out/'surface-poster.webp',quality=94,method=6)
sources=[ROOT/'tools/blender/source/cinematic-surface.blend',ROOT/'tools/blender/cinematic-surface.py',ROOT/'tools/blender/render-surface.py']+sorted((ROOT/'tools/blender/references/surface').glob('*'))
manifest={'source':'Original authored Blender surface. Representative terrain, not a survey or real mine footage.','blender':'5.2.3 LTS','assets':[row(out/n) for n in ['surface.mp4','surface-poster.webp']],'sources':[row(s) for s in sources if s.is_file()],'encoding':{'render_fps':12,'output_fps':24,'duration_s':24,'width':1296,'height':810,'codec':'H.264','operation':'Alternate source frames, linear frame blending to 24 fps, CRF 20, yuv420p, faststart'},'motion':{'rear_axle_circle_centre_m':[10,-53],'rear_axle_turn_radius_m':9,'period_s':24,'wheelbase_m':5.1,'half_track_m':1,'tyre_radius_m':.51,'speed_m_s':9*2*3.141592653589793/24,'front_steering':'Ackermann; per-side radius and tyre travel','dust':'No engine smoke or dust plume in the film. Real-time fallback emits restrained dust at previous rear tyre contacts.'},'licences':['Original Kessel geometry: repository LICENSE','MakeHuman core base: CC0-1.0','Poly Haven scans and representative HDR sky: CC0-1.0'],'rights':'tools/blender/references/surface/README.md; existing assets/materials and assets/textures manifests'}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Surface film provenance frozen')
