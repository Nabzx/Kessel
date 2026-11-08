"""Original observation satellite, metres. Run through the local Blender MCP."""
import bpy,math,random
from mathutils import Vector
random.seed(8311)
for old in list(bpy.data.objects):bpy.data.objects.remove(old,do_unlink=True)
bpy.data.orphans_purge(do_recursive=True)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.render.engine='CYCLES';scene.cycles.samples=24
scene.render.resolution_x=1400;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX'

def material(name,rgb,metal,rough):
 m=bpy.data.materials.new(name);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*rgb,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough;return m
foil=material('gold multilayer insulation',(.43,.25,.065),.82,.37)
frame=material('anodised aluminium',(.29,.32,.34),.85,.3)
white=material('ceramic radiator',(.66,.69,.7),.08,.73)
black=material('graphite baffle',(.008,.012,.017),.05,.64)
cell=material('silicon cells',(.012,.032,.078),.3,.29)
cell2=material('silicon cells alternate',(.018,.043,.097),.3,.34)
wire=material('silver interconnects',(.37,.42,.48),.8,.24)
root=bpy.data.objects.new('ObservationSatellite',None);scene.collection.objects.link(root)

def cube(name,size,loc,mat,bevel=0):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(mat);o.parent=root
 if bevel:
  mod=o.modifiers.new('manufactured edge','BEVEL');mod.width=bevel;mod.segments=2;bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=mod.name)
 return o

def cylinder(name,radius,depth,loc,mat,vertices=16):
 bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=radius,depth=depth,location=loc);o=bpy.context.object;o.name=name;o.data.materials.append(mat);o.parent=root;return o

def rod(a,b,radius,mat):
 a,b=Vector(a),Vector(b);o=cylinder('structural tube',radius,(b-a).length,(a+b)/2,mat,10);o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler();return o

cube('instrument bus',(.95,1.05,1.3),(0,0,0),foil,.045)
# Folded insulation tiles use actual shallow irregular relief, not an unexported noise shader.
for side in (-1,1):
 for i in range(5):
  for j in range(6):
   o=cube('insulation quilt',(.022,.18,.19),(side*.489,(i-2)*.2,(j-2.5)*.21),foil,.012);o.rotation_euler[0]=(random.random()-.5)*.035
 cube('radiator plate',(.75,.026,1.04),(0,side*.54,0),white,.018)
 for k in range(14):cube('radiator channels',(.71,.006,.009),(0,side*.557,-.45+k*.07),frame)
 for x in (-.46,.46):rod((x,side*.51,-.63),(x,side*.51,.63),.018,frame)
 cube('array drive housing',(.25,.3,.27),(side*.62,0,.15),frame,.025)
 rod((side*.5,0,.15),(side*1.15,0,.15),.045,frame)
 for panel in range(3):
  centre=side*(1.72+panel*1.43)
  cube('solar sandwich panel',(1.38,2.32,.026),(centre,0,.15),black,.01)
  for edge in (-1,1):
   cube('solar perimeter rail',(1.4,.025,.055),(centre,edge*1.17,.15),frame)
   cube('solar perimeter rail',(.025,2.34,.055),(centre+edge*.7,0,.15),frame)
  for row in range(12):
   for col in range(7):
    x=centre+(col-3)*.188;y=(row-5.5)*.184
    cube('photovoltaic cell',(.178,.173,.0025),(x,y,.166),cell if (row+col)%3 else cell2)
    for offset in (-.045,.045):cube('cell busbar',(.0016,.168,.001),(x+offset,y,.168),wire)
  rod((centre-.61,-1.1,.1),(centre+.61,1.1,.1),.009,frame)
  rod((centre-.61,1.1,.1),(centre+.61,-1.1,.1),.009,frame)
  for y in (-.7,.7):cylinder('deployment hinge',.045,.11,(centre-side*.69,y,.15),frame,12)
# A recessed optical aperture and its stacked light baffles.
for k in range(5):cylinder('telescope baffle',.23-k*.018,.12,(0,0,-.68-k*.105),black,32)
cylinder('aperture lens',.135,.008,(0,0,-1.16),cell,32)
for x in (-.35,.35):
 for y in (-.4,.4):cylinder('mounting fastener',.025,.02,(x,y,-.662),frame,12)
# Parabolic communications dish and three feed supports.
verts=[(0,0,.72)];faces=[];rings=10;segments=40
for ring in range(1,rings+1):
 r=.39*ring/rings
 for k in range(segments):
  t=k*2*math.pi/segments;verts.append((r*math.cos(t),r*math.sin(t),.72+r*r*.65))
for k in range(segments):faces.append((0,1+k,1+(k+1)%segments))
for ring in range(rings-1):
 for k in range(segments):
  a=1+ring*segments+k;b=1+ring*segments+(k+1)%segments;faces.append((a,b,b+segments,a+segments))
mesh=bpy.data.meshes.new('dish reflector');mesh.from_pydata(verts,[],faces);mesh.materials.append(white);dish=bpy.data.objects.new('parabolic reflector',mesh);scene.collection.objects.link(dish);dish.parent=root
for t in (0,2.094,4.189):rod((.36*math.cos(t),.36*math.sin(t),.8),(0,0,1.11),.009,frame)
cylinder('feed',.025,.07,(0,0,1.12),foil,16)
for side in (-1,1):rod((side*.4,.39,.5),(side*.6,.6,1.5),.009,frame)
# Batch by material for a small number of runtime draws; named root remains intact.
for mat in (foil,frame,white,black,cell,cell2,wire):
 objects=[o for o in root.children if o.type=='MESH' and o.data.materials and o.data.materials[0]==mat]
 if not objects:continue
 bpy.ops.object.select_all(action='DESELECT')
 for o in objects:o.select_set(True)
 bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join();bpy.context.object.name=mat.name
# Export only the authored model. No lights or cameras ship.
bpy.ops.object.select_all(action='DESELECT');root.select_set(True)
for o in root.children:o.select_set(True)
bpy.context.view_layer.objects.active=root
output=REPO_ROOT+'/assets/authored/observation-satellite.glb'
bpy.ops.export_scene.gltf(filepath=output,export_format='GLB',use_selection=True,export_yup=True,export_apply=True,export_animations=False)
bpy.ops.wm.save_as_mainfile(filepath=REPO_ROOT+'/tools/blender/source/observation-satellite.blend',compress=True)
scene.world.color=(.08,.08,.08)
bpy.ops.object.light_add(type='AREA',location=(2,-6,8));light=bpy.context.object;light.data.energy=900;light.data.shape='DISK';light.data.size=5
bpy.ops.object.camera_add(location=(8,-12,10));camera=bpy.context.object;camera.rotation_euler=(Vector((0,0,0))-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.lens=48;scene.camera=camera
scene.render.filepath=REPO_ROOT+'/docs/phase-11/orbital-home-evidence/satellite-source.png';bpy.ops.render.render(write_still=True)
print('ORBITAL_ASSET',output,'triangles',sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in root.children if o.type=='MESH'))
