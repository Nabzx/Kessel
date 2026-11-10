"""Correct rigid rotation modes and retain an evaluated directed-haul audit."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
R=Path(REPO_ROOT)
bpy.ops.wm.open_mainfile(filepath=str(R/'tools/blender/source/cinematic-surface.blend'))
S=bpy.context.scene;D=json.loads((R/'data/surface-haul.json').read_text());truck=bpy.data.objects['hauler'];wheels=[o for o in truck.children if o.type=='EMPTY' and o.name.startswith('Wheel_')]
print('PREVIOUS_TRUCK_ROTATION_MODE',truck.rotation_mode,flush=True)
for o in [truck]+wheels:o.animation_data_clear();o.rotation_mode='XYZ';o.rotation_euler=(0,0,0)
for row in D['rows']:
 t,x,y,z,h,v,k,sl,sr,*_=row;frame=round(t*24)+1
 truck.location=(x,-z,y);truck.rotation_euler.z=h
 truck.keyframe_insert(data_path='location',frame=frame);truck.keyframe_insert(data_path='rotation_euler',frame=frame)
 for w in wheels:
  left=w.location.x<0;front=w.location.y<0;j=(2 if front else 0)+(0 if left else 1)
  w.rotation_euler.x=row[9+j];w.rotation_euler.z=(sl if left else sr) if front else 0
  w.keyframe_insert(data_path='rotation_euler',frame=frame)
for o in [truck]+wheels:
 for layer in o.animation_data.action.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for fc in bag.fcurves:
     for point in fc.keyframe_points:point.interpolation='LINEAR'
# Keep the excavation's internal faces dark, rather than exposing a bright rock
# wall through the opening. This is authored lining, not a survey.
dark=bpy.data.materials.new('Unlit adit lining');dark.use_nodes=True;p=dark.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(.007,.009,.008,1);p.inputs['Roughness'].default_value=1
for o in bpy.data.objects:
 if o.type=='MESH' and ('excavated' in o.data.name.lower() or 'portalhill' in o.name.lower()):
  idx=len(o.data.materials);o.data.materials.append(dark)
  for face in o.data.polygons:
   c=o.matrix_world@face.center
   if abs(c.x)<4.4 and 82<c.y<116 and -.2<c.z<7.7:face.material_index=idx
S.frame_start=1;S.frame_end=384;S.render.fps=24
# Audit Blender's evaluated transforms, not just the requested Euler values.
audit=[]
for row in D['rows']:
 S.frame_set(round(row[0]*24)+1);bpy.context.view_layer.update();forward=truck.matrix_world.to_3x3()@Vector((0,-1,0));expected=Vector((math.sin(row[4]),-math.cos(row[4]),0))
 dot=forward.normalized().dot(expected);assert dot>.999999,(row[0],dot)
 bottoms=[w.matrix_world.translation.z-D['wheel_radius_m'] for w in wheels]
 assert all(abs(h-D['ground_y_m'])<.00001 for h in bottoms),(row[0],bottoms)
 audit.append({'t':row[0],'position':list(truck.matrix_world.translation),'forward':list(forward),'heading_dot':dot,'tyre_bottoms':bottoms})
S.frame_set(1);bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(R/'tools/blender/source/cinematic-surface.blend'),compress=True)
(R/'assets/film/scene-audit.json').write_text(json.dumps({'source':'Evaluated Blender 5.2 rigid transforms','rotation_mode':truck.rotation_mode,'trajectory':'data/surface-haul.json','samples':audit},separators=(',',':'))+'\n')
S.render.resolution_percentage=90;S.eevee.taa_render_samples=16
folder=Path('/private/tmp/kessel-directed-haul');folder.mkdir(exist_ok=True)
for i,frame in enumerate(range(1,385,2)):
 S.frame_set(frame);S.render.filepath=str(folder/f'{i:04}.png');bpy.ops.render.render(write_still=True)
 print('DIRECTED_HAUL_FRAME',i,flush=True)
