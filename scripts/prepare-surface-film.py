"""Encode the original local Blender frame sequence and freeze provenance."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def row(p):return {'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':digest(p)}
p=argparse.ArgumentParser();p.add_argument('--frames',type=Path,default=Path('/private/tmp/kessel-directed-haul'));p.add_argument('--poster',type=Path,default=Path('/private/tmp/kessel-directed-haul/0000.png'));p.add_argument('--manifest-only',action='store_true');args=p.parse_args()
out=ROOT/'assets/film';out.mkdir(exist_ok=True)
trajectory=json.loads((ROOT/'data/surface-haul.json').read_text());duration=trajectory['duration_s']
if not args.manifest_only:
 subprocess.run(['ffmpeg','-y','-framerate','12','-i',str(args.frames/'%04d.png'),'-vf',f'tpad=stop_mode=clone:stop_duration=0.3,minterpolate=fps=24:mi_mode=blend,trim=duration={duration}','-an','-c:v','libx264','-preset','medium','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(out/'surface-encoding.mp4')],check=True)
 subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(out/'surface-encoding.mp4'),'-f','null','-'],check=True)
 (out/'surface-encoding.mp4').replace(out/'surface.mp4')
 subprocess.run(['cwebp','-q','94','-m','6',str(args.poster),'-o',str(out/'surface-poster.webp')],check=True)
sources=[ROOT/'tools/blender/source/cinematic-surface.blend',ROOT/'tools/blender/cinematic-surface.py',ROOT/'tools/blender/render-surface.py',ROOT/'tools/blender/surface-haul.py',ROOT/'data/surface-haul.json',ROOT/'assets/film/scene-audit.json']+sorted((ROOT/'tools/blender/references/surface').glob('*'))
manifest={'source':'Original authored Blender surface. Representative terrain, not a survey or real mine footage.','blender':'5.2.3 LTS','assets':[row(out/n) for n in ['surface.mp4','surface-poster.webp']],'sources':[row(s) for s in sources if s.is_file()],'encoding':{'render_fps':12,'output_fps':24,'duration_s':duration,'width':1296,'height':810,'codec':'H.264','operation':'Alternate source frames, linear frame blending to 24 fps, CRF 20, yuv420p, faststart'},'motion':{'trajectory':'data/surface-haul.json','audit':'assets/film/scene-audit.json','loop':False,'rotation_mode':'XYZ','route':'Finite yard haul with one smooth ninety-degree bend and a stationary endpoint','max_speed_m_s':trajectory['max_speed_m_s'],'acceleration_m_s2':trajectory['acceleration_m_s2'],'ground_y_m':trajectory['ground_y_m'],'front_steering':'Ackermann; signed travel per wheel','dust':'No engine smoke or dust plume in the film. Real-time fallback uses the same retained motion.'},'licences':['Original Kessel geometry: repository LICENSE','MakeHuman core base: CC0-1.0','Poly Haven scans and representative HDR sky: CC0-1.0'],'rights':'tools/blender/references/surface/README.md; existing assets/materials and assets/textures manifests'}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Surface film provenance frozen')
