"""Render the packed original scene without requiring the connector or HDR path.

Blender --background --factory-startup --python tools/blender/render-surface.py
Source time is 24 fps. Render alternate frames (12 fps) and interpolate the
encoded film to 24 fps. Timing and trajectories remain those in the source.
"""
import bpy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'tools/blender/source/cinematic-surface.blend'))
s=bpy.context.scene;s.render.resolution_percentage=90
if hasattr(s,'eevee'):s.eevee.taa_render_samples=16
folder=Path('/private/tmp/kessel-directed-haul');folder.mkdir(parents=True,exist_ok=True)
for i,frame in enumerate(range(1,round(json.loads((ROOT/'data/surface-haul.json').read_text())['duration_s']*24)+1,2)):
 s.frame_set(frame);s.render.filepath=str(folder/f'{i:04}.png');bpy.ops.render.render(write_still=True)
 print('KESSEL_FILM_FRAME',i,flush=True)
