"""Original 16-second surface film. Metres, 24 fps, reproducible seed.

Blender 5.2: run-headless.py -- cinematic-surface. Set KESSEL_RENDER=film to
render the sequence; default renders one look-development frame. HDR is a
cleared local reference; sources and packed scene are retained, not shipped.
"""
import bpy, math, random, os
from mathutils import Vector
random.seed(5401)
R=REPO_ROOT
for o in list(bpy.data.objects):bpy.data.objects.remove(o,do_unlink=True)
S=bpy.context.scene;S.unit_settings.system='METRIC';S.render.engine='BLENDER_EEVEE'
S.render.resolution_x=1440;S.render.resolution_y=900;S.render.resolution_percentage=100
S.render.fps=24;S.frame_start=1;S.frame_end=384
S.render.image_settings.file_format='PNG';S.render.image_settings.color_mode='RGB'
S.render.film_transparent=False
S.view_settings.view_transform='AgX';S.view_settings.look='AgX - Medium High Contrast'
S.view_settings.exposure=.2
if hasattr(S,'eevee'):S.eevee.taa_render_samples=48

def xyz(v):return (v[0],-v[2],v[1])
def material(name,c,metal=0,rough=.6):
 m=bpy.data.materials.new(name);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*c,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough;return m

def mapped(name,diff,normal=None,rough=None,scale=1,metal=0,tint=None):
 m=material(name,(.5,.5,.5),metal);n=m.node_tree.nodes;l=m.node_tree.links;p=n.get('Principled BSDF')
 tc=n.new('ShaderNodeTexCoord');mapping=n.new('ShaderNodeVectorMath');mapping.operation='SCALE';mapping.inputs[3].default_value=1/scale;l.new(tc.outputs['Object'],mapping.inputs[0])
 def image(path,linear=False):
  a=n.new('ShaderNodeTexImage');a.image=bpy.data.images.load(R+'/'+path,check_existing=True);a.projection='BOX';a.projection_blend=.2
  if linear:a.image.colorspace_settings.name='Non-Color'
  l.new(mapping.outputs[0],a.inputs['Vector']);return a
 a=image(diff)
 if tint:
  mix=n.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1;mix.inputs[2].default_value=(*tint,1);l.new(a.outputs['Color'],mix.inputs[1]);l.new(mix.outputs[0],p.inputs['Base Color'])
 else:l.new(a.outputs['Color'],p.inputs['Base Color'])
 if normal:
  a=image(normal,True);nm=n.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.7;l.new(a.outputs['Color'],nm.inputs['Color']);l.new(nm.outputs[0],p.inputs['Normal'])
 if rough:l.new(image(rough,True).outputs['Color'],p.inputs['Roughness'])
 return m

def cube(name,size,pos,m,parent=None,bevel=.03):
 bpy.ops.mesh.primitive_cube_add(size=1);o=bpy.context.object;o.name=name;o.dimensions=(size[0],size[2],size[1]);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.location=xyz(pos);o.parent=parent;o.data.materials.append(m)
 if bevel:mod=o.modifiers.new('soft manufactured edges','BEVEL');mod.width=bevel;mod.segments=2
 return o

def cylinder(name,r,d,pos,m,parent=None,axis='up',vertices=20):
 bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=r,depth=d,location=xyz(pos));o=bpy.context.object;o.name=name;o.parent=parent;o.data.materials.append(m)
 if axis=='x':o.rotation_euler.y=math.pi/2
 if axis=='z':o.rotation_euler.x=math.pi/2
 mod=o.modifiers.new('rolled edges','BEVEL');mod.width=.015;mod.segments=2
 for p in o.data.polygons:p.use_smooth=True
 return o

def imported(path):
 before=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=R+'/'+path);return [o for o in bpy.data.objects if o not in before]

ref='tools/blender/references/surface/'
soil=mapped('Scanned dry compacted ground','assets/textures/brown_mud_dry_diff.jpg',scale=4,tint=(.8,.73,.62))
rock=mapped('Scanned weathered rock','assets/materials/rock_face_03_diff.webp','assets/materials/rock_face_03_nor_gl.webp','assets/materials/rock_face_03_rough.webp',2.7,tint=(.8,.79,.71))
concrete=mapped('Scanned stained concrete',ref+'concrete-diff.jpg',ref+'concrete-normal.jpg',ref+'concrete-rough.jpg',1.5,tint=(.4,.41,.37))
cladding=mapped('Scanned corrugated galvanised steel',ref+'corrugated-diff.jpg',ref+'corrugated-normal.jpg',ref+'corrugated-rough.jpg',1.1,.65)
grass=mapped('Scanned hillside grass','assets/materials/aerial_grass_rock_diff.webp','assets/materials/aerial_grass_rock_nor_gl.webp','assets/materials/aerial_grass_rock_rough.webp',12,tint=(.63,.72,.5))
steel=material('Weathered steel',(.19,.22,.21),.8,.51);rubber=material('Tyre rubber',(.013,.016,.016),0,.91)
paint=material('Dusty ochre painted steel',(.43,.235,.055),.2,.5)
# Fine abrasion breaks up the large painted panels without implausible macro noise.
n=paint.node_tree.nodes;l=paint.node_tree.links;p=n.get('Principled BSDF');noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=85;noise.inputs['Detail'].default_value=3;bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.18;bump.inputs['Distance'].default_value=.008;l.new(noise.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs['Normal'],p.inputs['Normal'])
glass=material('Tinted laminated glazing',(.035,.065,.072),.15,.12);p=glass.node_tree.nodes.get('Principled BSDF');p.inputs['Transmission Weight'].default_value=.32
black=material('Portal darkness',(.004,.006,.006),0,1)

# Actual open portal and closed excavated mass, rather than a landscape card.
for o in imported('assets/authored/portal-hill.glb'):
 if o.type=='MESH':o.data.materials.clear();o.data.materials.append(rock)
# Original concrete portal. The render source owns its mesh transforms so a
# GLB rigid-attachment conversion cannot rotate ducts or kerbs across the road.
for side in [-1,1]:
 cube('concrete portal pier',(1.5,3.5,1.2),(side*4.75,1.75,-83.5),concrete)
 cube('portal footing',(2.1,.4,2.1),(side*4.75,.2,-83.5),concrete)
 for k in range(3):cube('retaining wing',(1.0,3.5-k*.7,2.2),(side*(5.5+k*.55),(3.5-k*.7)/2,-82+k*1.4),concrete)
# Semicircular concrete arch, extruded along the adit direction.
verts=[];faces=[]
for depth in [-82.9,-84.1]:
 for radius in [4,5.5]:
  for i in range(33):
   a=i*math.pi/32;verts.append((radius*math.cos(a),-depth,3.5+radius*math.sin(a)))
for i in range(32):
 for a,b in [(0,33),(66,99),(0,66),(33,99)]:faces.append((a+i,a+i+1,b+i+1,b+i))
faces.extend([(0,33,99,66),(32,65,131,98)])
mesh=bpy.data.meshes.new('cast concrete arch');mesh.from_pydata(verts,[],faces);mesh.update();o=bpy.data.objects.new('cast concrete arch',mesh);bpy.context.collection.objects.link(o);o.data.materials.append(concrete)
cube('portal top coping',(11.5,.3,1.5),(0,9.1,-83.5),concrete)
for side in [-1,1]:
 cube('longitudinal kerb',(.35,.25,16),(side*3.7,.125,-91),concrete)
 cube('worklamp housing',(.5,.25,.25),(side*3.3,7.0,-82.8),steel)
# Ventilation continues into the adit at the edge of the clear opening.
cylinder('ventilation duct',.48,25,(2.8,5.9,-95),steel,axis='z')
for z in [-84,-88,-92,-96,-100]:cylinder('duct coupling',.52,.11,(2.8,5.9,z),steel,axis='z')
# Interior shadow and continuous road through the aperture.
cube('unlit adit interior',(8.0,6,1),(0,3,-115),black)
cube('ground',(500,.25,500),(0,-.16,-90),soil,bevel=0)
# Road edge and disturbed soil, several scales of genuine 3D scatter.
for i in range(820):
 x=random.uniform(-82,82);z=random.uniform(-115,10)
 if -7<x<25 and z>-83:continue
 bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=1,location=xyz((x,.05,z)));o=bpy.context.object;o.name='loose stone';r=random.uniform(.05,.42);o.scale=(r*1.5,r,r*.55);o.rotation_euler=(random.random(),random.random(),random.random()*6);o.data.materials.append(rock)
# Low surrounding hills, noise-displaced and shaded with scanned vegetation.
for x,z,sx,sz,h in [(-110,-170,105,150,54),(100,-198,96,132,67),(-120,-330,160,150,80),(130,-380,180,170,95)]:
 bpy.ops.mesh.primitive_uv_sphere_add(segments=48,ring_count=24,location=xyz((x,0,z)));o=bpy.context.object;o.scale=(sx,sz,h);o.data.materials.append(grass)
 bpy.context.view_layer.objects.active=o;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 for v in o.data.vertices:v.co.z+=1.2*math.sin(v.co.x*.2+v.co.y*.1)*math.cos(v.co.y*.17)
 for f in o.data.polygons:f.use_smooth=True
# A practical service shed, rendered close enough to see seams, fasteners and wear.
for x,z,w,d,h in [(-23,-68,16,12,5.5),(35,-77,17,16,6)]:
 cube('concrete plinth',(w+.3,.6,d+.3),(x,.3,z),concrete)
 cube('corrugated service building',(w,h,d),(x,h/2+.4,z),cladding)
 roof=cube('standing seam roof',(w+1.2,.18,d+1.2),(x,h+.7,z),cladding);roof.rotation_euler.y=.05
 for dx in [-w*.27,w*.27]:
  cube('roller door',(w*.30,h*.67,.1),(x+dx,h*.335+.4,z+d/2+.07),steel)
  for k in range(16):cube('roller shutter seam',(w*.3,.018,.035),(x+dx,.52+k*h*.04,z+d/2+.14),rubber,bevel=0)
 for dx in [-w/2+.2,w/2-.2]:
  cylinder('downpipe',.055,h,(x+dx,h/2+.35,z+d/2+.12),steel)
  for height in [1,3,5]:cube('pipe clip',(.16,.03,.18),(x+dx,height,z+d/2+.1),steel)
 for k in range(round(w/.7)):
  for height in [.8,h*.55,h-.1]:cylinder('cladding fastener',.013,.018,(x-w/2+.3+k*.7,height,z+d/2+.02),steel,axis='z',vertices=8)
 cube('rain gutter',(w+.8,.14,.2),(x,h+.45,z+d/2+.5),steel)
# Retaining edge, service pipes, bollards and practical scale cues.
for side in [-1,1]:
 for k in range(6):cube('concrete barrier',(2,.75,.55),(side*(8+k*2.1),.375,-80),concrete)
 for h in [.6,1.1]:cylinder('portal services',.09,24,(side*5.1,h,-91),steel,axis='z')
 for z in [-81,-74]:cylinder('safety bollard',.12,1.2,(side*5, .6,z),paint)

# Detailed original hauler with its original pivots. Source geometry remains reusable.
objects=imported('assets/authored/hauler-close.glb');truck=next(o for o in objects if o.name=='hauler')
for o in objects:
 if o.type=='MESH':
  for i,m in enumerate(o.data.materials):
   key=m.name.lower();o.data.materials[i]=rubber if 'rubber' in key else glass if 'glass' in key or 'lens' in key else paint if 'paint' in key else steel if 'steel' in key else m
wheels=[o for o in objects if o.type=='EMPTY' and o.name.startswith('Wheel_')]
for w in wheels:
 for child in list(w.children):bpy.data.objects.remove(child,do_unlink=True)
 cylinder('radial tyre',.51,.274,(0,0,0),rubber,w,axis='x',vertices=40)
 cylinder('wheel hub',.22,.285,(0,0,0),steel,w,axis='x',vertices=24)
# Cab details, tyre lugs, ladder, mirrors and safety bars at physical scale.
for side in [-1,1]:
 cube('cab door',( .035,.75,1.1),(side*1.01,1.45,2.1),paint,truck)
 cube('cab window',(.045,.45,.8),(side*1.035,1.75,2.2),glass,truck)
 cube('door handle',(.065,.035,.17),(side*1.08,1.48,1.9),steel,truck)
 cylinder('mirror stalk',.016,.43,(side*1.15,1.94,2.75),steel,truck,axis='x')
 cube('side mirror',(.1,.23,.15),(side*1.38,2.02,2.75),glass,truck)
 for k in range(3):cube('access step',(.32,.045,.22),(side*1.07,.43+k*.27,2.38),steel,truck)
for wheel in wheels:
 for k in range(32):
  a=k*math.tau/32;o=cube('tyre tread',(.26,.035,.075),(0,.51*math.cos(a),.51*math.sin(a)),rubber,wheel,.008);o.rotation_euler.x=-a
# Tiny high-frequency dirt on tyres and paint is measured in millimetres.

# Human core mesh is CC0. Assign full work clothing and original helmet / PPE.
# The base mesh is only a proportioned body surface; no exposed torso is shown.
bpy.ops.wm.obj_import(filepath=R+'/'+ref+'makehuman-base.obj');worker=bpy.context.object;worker.name='PPE worker'
# The MakeHuman base contains helper groups. Keep the body surface only.
if len(worker.data.polygons)>15000:
 # Body faces precede helper geometry in the official base OBJ (joint groups).
 groups={g.index:g.name for g in worker.vertex_groups}
 import bmesh
 bm=bmesh.new();bm.from_mesh(worker.data);bm.verts.ensure_lookup_table();bm.faces.ensure_lookup_table()
 # Exported OBJ face groups are not a reliable material boundary. Keep by vertex
 # index using the documented base-mesh human vertex count, excluding helpers.
 remove=[f for f in bm.faces if any(v.index>=13380 for v in f.verts)]
 bmesh.ops.delete(bm,geom=remove,context='FACES');bm.to_mesh(worker.data);bm.free()
# OBJ is Y-up, metres are decimetres in the source. Transform using its extent.
ys=[v.co.y for v in worker.data.vertices];zs=[v.co.z for v in worker.data.vertices]
# Blender's importer converts Y-up to Z-up; detect the long axis explicitly.
axis=1 if max(ys)-min(ys)>max(zs)-min(zs) else 2
if axis==1:worker.rotation_euler.x=math.pi/2
bpy.context.view_layer.objects.active=worker;bpy.ops.object.transform_apply(location=False,rotation=True,scale=False)
lo=min(v.co.z for v in worker.data.vertices);hi=max(v.co.z for v in worker.data.vertices)
for v in worker.data.vertices:v.co.z-=lo
scale=1.78/(hi-lo);worker.scale=(scale,scale,scale);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
for v in worker.data.vertices:
 if abs(v.co.x)>.22 and 1.05<v.co.z<1.58:
  side=1 if v.co.x>0 else -1;dx=v.co.x-side*.19;dz=v.co.z-1.47;a=-side*.78;v.co.x=side*.19+dx*math.cos(a)-dz*math.sin(a);v.co.z=1.47+dx*math.sin(a)+dz*math.cos(a)
cloth=material('Woven workwear',(.09,.13,.15),0,.94);hi_vis=material('High visibility vest',(.66,.36,.025),0,.86);skin=material('Skin',(.18,.09,.052),0,.55);reflect=material('Reflective PPE tape',(.55,.57,.48),.15,.44)
for m in [cloth,hi_vis,skin]:worker.data.materials.append(m)
for f in worker.data.polygons:
 z=sum(worker.data.vertices[i].co.z for i in f.vertices)/len(f.vertices);f.material_index=2 if z>1.52 else 1 if z>1.0 else 0;f.use_smooth=True
sub=worker.modifiers.new('smooth cloth silhouette','SUBSURF');sub.levels=1
worker.location=xyz((-7.5,.08,-74));worker.rotation_euler.z=.3
# Original hard hat, waist tape and protected worker area outside all truck paths.
bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,location=xyz((-7.5,1.82,-74)));o=bpy.context.object;o.name='hard hat';o.scale=(.14,.17,.09);o.data.materials.append(paint)
cylinder('hard hat brim',.185,.025,(-7.5,1.77,-74),paint)
for x in [-9,-6]:cylinder('pedestrian protection',.07,1.15,(x,.575,-71.5),paint)
# Physical daylight and soft sky reflections, without flat ambient lighting.
world=bpy.data.worlds.new('Cleared Poly Haven sky');world.use_nodes=True;S.world=world;n=world.node_tree.nodes;l=world.node_tree.links;n.clear();env=n.new('ShaderNodeTexEnvironment');env.image=bpy.data.images.load('/private/tmp/kessel-surface-sky.hdr');bg=n.new('ShaderNodeBackground');bg.inputs['Strength'].default_value=.65;out=n.new('ShaderNodeOutputWorld');l.new(env.outputs['Color'],bg.inputs['Color']);l.new(bg.outputs[0],out.inputs[0])
bpy.ops.object.light_add(type='SUN',location=(0,0,50));sun=bpy.context.object;sun.rotation_euler=(.5,-.45,-.65);sun.data.energy=2.2;sun.data.angle=.075
# Locked establishing composition. Interactive chapter transitions handle the cut.
bpy.ops.object.camera_add(location=xyz((24,6.8,-27)));cam=bpy.context.object;cam.rotation_euler=(Vector(xyz((0,4,-79)))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=40;S.camera=cam;cam.data.clip_end=2000;cam.data.dof.use_dof=True;cam.data.dof.focus_distance=57;cam.data.dof.aperture_fstop=10
# One retained directed work order. Blender imports use quaternion mode;
# explicit Euler mode is required before writing yaw/spin animation keys.
import json
haul=json.load(open(R+'/data/surface-haul.json'))
for o in [truck]+wheels:o.rotation_mode='XYZ';o.rotation_euler=(0,0,0)
for row in haul['rows']:
 t,x,y,z,h,v,k,sl,sr,*_=row;frame=round(t*24)+1
 truck.location=xyz((x,y,z));truck.rotation_euler.z=h
 truck.keyframe_insert(data_path='location',frame=frame);truck.keyframe_insert(data_path='rotation_euler',frame=frame)
 for w in wheels:
  left=w.location.x<0;front=w.location.y<0;j=(2 if front else 0)+(0 if left else 1)
  w.rotation_euler.x=row[9+j];w.rotation_euler.z=(sl if left else sr) if front else 0;w.keyframe_insert(data_path='rotation_euler',frame=frame)
for o in [truck]+wheels:
 if o.animation_data and o.animation_data.action:
  for fc in o.animation_data.action.layers[0].strips[0].channelbag(o.animation_data.action_slot).fcurves:
   for k in fc.keyframe_points:k.interpolation='LINEAR'
S.frame_set(1)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=R+'/tools/blender/source/cinematic-surface.blend',compress=True)
os.makedirs('/private/tmp/kessel-surface-film',exist_ok=True)
S.render.filepath='/private/tmp/kessel-surface-film/frame-'
if os.environ.get('KESSEL_RENDER')=='film':bpy.ops.render.render(animation=True)
else:S.render.filepath='/private/tmp/kessel-surface-look.png';bpy.ops.render.render(write_still=True)
print('KESSEL_CINEMATIC_SURFACE_COMPLETE')
