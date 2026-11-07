"""Original Kessel assets. Executed through MCP safe mode, never by the website.

REPO_ROOT, EXPERIENCE and TRUCK are supplied by client.py from local authored data.
Coordinate helper: Three.js x/right, y/up, z/forward -> Blender x, -y/forward, z/up.
"""
import bpy
import bmesh
import math
import random
from mathutils import Vector

random.seed(20261107)
for old in list(bpy.data.objects):bpy.data.objects.remove(old,do_unlink=True)
bpy.data.orphans_purge(do_recursive=True)
scene=bpy.context.scene
scene.unit_settings.system='METRIC'
scene.unit_settings.scale_length=1
scene.render.engine='CYCLES'
scene.cycles.samples=16
scene.render.resolution_x=1280
scene.render.resolution_y=800
scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX'
scene.render.image_settings.file_format='PNG'
OUTPUT=REPO_ROOT+'/assets/authored/'
SOURCE=REPO_ROOT+'/tools/blender/source/'


def xyz(v):return (v[0],-v[2],v[1])
def material(name,colour,metal=0,rough=.7):
    m=bpy.data.materials.new(name);m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*colour,1)
    p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
    return m
paint=material('Kessel_PaintedSteel',(.52,.285,.07),0,.55)
steel=material('Kessel_BareSteel',(.22,.26,.265),.85,.34)
dark=material('Kessel_Rubber',(.012,.017,.019),0,.94)
glass=material('Kessel_Lens',(.018,.065,.075),0,.16)
rock=material('Kessel_Rock',(.20,.185,.16),0,.96)
pcb=material('Kessel_PCB',(.018,.095,.07),0,.72)
concrete=material('Kessel_Concrete',(.21,.23,.22),0,.92)
section=material('Kessel_Section',(.105,.125,.115),0,.98)
white=material('Kessel_Ceramic',(.68,.7,.63),0,.65)


def empty(name,parent=None,position=(0,0,0)):
    o=bpy.data.objects.new(name,None);scene.collection.objects.link(o);o.parent=parent;o.location=xyz(position);return o

def cube(name,size,pos,mat,parent=None,bevel=.025):
    bpy.ops.mesh.primitive_cube_add(size=1,location=xyz(pos));o=bpy.context.object;o.name=name
    o.dimensions=xyz((size[0],size[1],-size[2]));bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bevel:
        mod=o.modifiers.new('edge highlights','BEVEL');mod.width=bevel;mod.segments=2
        bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=mod.name)
    o.data.materials.append(mat);o.parent=parent;return o

def cylinder(name,radius,depth,pos,mat,parent=None,axis='up',segments=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=segments,radius=radius,depth=depth,location=xyz(pos))
    o=bpy.context.object;o.name=name
    if axis=='axle':o.rotation_euler.y=math.pi/2
    if axis=='forward':o.rotation_euler.x=math.pi/2
    o.data.materials.append(mat);o.parent=parent
    for face in o.data.polygons:face.use_smooth=len(face.vertices)==4
    return o

def fragment(name,size,pos,parent=None,detail=1):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=detail+1,radius=1,location=xyz(pos));o=bpy.context.object;o.name=name
    for v in o.data.vertices:
        v.co *= .85+random.random()*.3
        v.co.x*=size[0];v.co.y*=size[2];v.co.z*=size[1]
    o.data.materials.append(rock);o.parent=parent;return o

def descendants(root):return [root]+list(root.children_recursive)
def export(root,name,save=True):
    # Merge static siblings while retaining named wheel/bed/component pivots.
    for parent in reversed(descendants(root)):
        meshes=[c for c in parent.children if c.type=='MESH']
        if len(meshes)>1:
            bpy.ops.object.select_all(action='DESELECT')
            for obj in meshes:obj.select_set(True)
            bpy.context.view_layer.objects.active=meshes[0]
            bpy.ops.object.join()
            bpy.context.object.name=parent.name+'_surfaces'
    bpy.ops.object.select_all(action='DESELECT')
    for obj in descendants(root):obj.select_set(True)
    bpy.context.view_layer.objects.active=root
    bpy.ops.export_scene.gltf(filepath=OUTPUT+name+'.glb',export_format='GLB',use_selection=True,export_yup=True,export_apply=True,export_animations=True)
    if save:bpy.ops.wm.save_as_mainfile(filepath=SOURCE+name+'.blend',compress=True)
    triangles=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in descendants(root) if o.type=='MESH')
    print('KESSEL_ASSET',name,'triangles',triangles,'objects',len(descendants(root)))
    for o in descendants(root):o.hide_set(True);o.hide_render=True

# The cutaway keeps the original authored clearance envelope. Deformation is
# inward on vertical faces; top/bottom caps remain closed and flat.
geo=empty('geology')
for i,spec in enumerate([EXPERIENCE['mine']['base']]+EXPERIENCE['mine']['pillars']+EXPERIENCE['mine']['rims']):
    o=cube('geology_section_'+str(i),spec['size'],spec['position'],rock,geo,0)
    bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.subdivide_edges(bm,edges=list(bm.edges),cuts=10,use_grid_fill=True)
    sx,sy,sz=spec['size'][0]/2,spec['size'][2]/2,spec['size'][1]/2
    for v in bm.verts:
        shrink=min(min(sx,sy)*.22,.35+2.4*(.5+.5*math.sin(v.co.z*.47+v.co.x*.23+v.co.y*.17))+.7*math.sin(v.co.x*.67-v.co.y*.45)**2)
        if abs(abs(v.co.x)-sx)<.001:v.co.x-=math.copysign(shrink,v.co.x)
        if abs(abs(v.co.y)-sy)<.001:v.co.y-=math.copysign(shrink,v.co.y)
    bm.to_mesh(o.data);bm.free()
    o.data.materials.append(section)
    for face in o.data.polygons:
        if abs(face.normal.z)>.99:face.material_index=1
export(geo,'geology')

portal=empty('portal')
for side in (-1,1):
    cube('portal_footing',(1.1,.65,15),(side*4.6,.325,-5),concrete,portal)
    cube('portal_abutment',(.8,4.9,2),(side*4.45,2.8,-.7),concrete,portal)
    for y in (.8,1.7,2.6,3.5):cube('hazard_guard',(.25,.16,.9),(side*4.1,y,1.1),paint,portal)
    cylinder('service_pipe',.13,18,(side*3.7,4.4,-7),steel,portal,'forward')
for k in range(18):
    a=(k+.5)*math.pi/18;x=4.3*math.cos(a);y=4.6+2.2*math.sin(a)
    o=cube('arch_segment',(.83,.48,1.8),(x,y,-.7),concrete,portal);o.rotation_euler.y=-(a-math.pi/2)
for k in range(8):
    for side in (-1,1):cube('retaining_bond',(2.6,.55,1.8),(side*(6.5+k%2*.15),.3+k*.52,0),rock,portal,.09)
for side in (-1,1):
    cube('corrugated_service_cabin',(4.2,2.6,5.5),(side*13,1.4,5),steel,portal,.06)
    for k in range(18):cube('corrugation',(.05,2.45,.045),(side*13-2.1+k*.247,1.4,7.78),white,portal,.006)
    cube('cabin_door',(1,2.05,.08),(side*13,.99,7.82),dark,portal)
export(portal,'portal-yard')

hauler=empty('hauler')
for spec in TRUCK['parts']:
    cube('chassis_'+spec['material'],spec['size_m'],spec['position_m'],{'body':paint,'dark':dark,'glass':glass,'steel':steel,'cargo':rock,'lamp':white,'rear_lamp':paint}.get(spec['material'],steel),hauler)
bed_spec=TRUCK['dump_bed'];bed=empty('DumpBed',hauler,bed_spec['position_m'])
cube('bed_floor',bed_spec['body_size_m'],bed_spec['body_position_m'],paint,bed)
for p in bed_spec['panels']:cube('bed_panel',p['size_m'],p['position_m'],paint,bed)
for side in (-1,1):
    for k in range(8):cube('bed_reinforcement',(.08,.55,.08),(side*.99,1.1,-1.6+k*.48),steel,hauler,.012)
    for k in range(5):cube('engine_grille',(.018,.35,.055),(side*.985,1.24,1.1+k*.11),dark,hauler,.005)
    cube('cab_grab_rail',(.045,.8,.045),(side*1.04,1.4,2.5),steel,hauler,.006)
    cylinder('hydraulic_body',.065,1.2,(side*.74,1.1,-.4),steel,hauler)
    cylinder('hydraulic_rod',.035,.9,(side*.74,1.65,-.4),white,hauler)
w=TRUCK['wheels']
for side in (-1,1):
    for axle,z in enumerate(w['axle_z_m']):
        pivot=empty('Wheel_'+str(side)+'_'+str(axle),hauler,(side*w['side_offset_m'],w['centre_y_m'],z))
        cylinder('tyre',w['radius_m'],w['width_m'],(0,0,0),dark,pivot,'axle')
        cylinder('hub',w['hub_radius_m'],w['width_m'],(0,0,0),steel,pivot,'axle')
        for k in range(24):
            a=k*math.pi/12;o=cube('tread',(.9*w['width_m'],.055,.13),(0,math.cos(a)*w['radius_m'],math.sin(a)*w['radius_m']),dark,pivot,.008);o.rotation_euler.x=a
export(hauler,'hauler-close')
# A second real mesh LOD, not a renamed copy.
for o in descendants(hauler):
    o.hide_set(False);o.hide_render=False
    if o.type=='MESH' and len(o.data.polygons)>30:
        mod=o.modifiers.new('overview reduction','DECIMATE');mod.ratio=.42
        bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=mod.name)
export(hauler,'hauler-overview')

ore=empty('ore')
for k in range(70):
    a=random.random()*math.tau;r=math.sqrt(random.random())*2.7
    h=max(.15,1.5*(1-r/3));fragment('ore_granule',(.22+random.random()*.2,.16+random.random()*.18,.2+random.random()*.2),(r*math.cos(a),h,r*math.sin(a)),ore)
export(ore,'ore-pile')

kit=empty('kit')
for spec in EXPERIENCE['kit']['components']:
    group=empty(spec['id'],kit);group.scale=(.1,.1,.1);sx,sy,sz=spec['size'];mat=pcb if spec['id'] in ('compute','controls','power') else steel
    cube(spec['id']+'_body',spec['size'],(0,0,0),mat,group,.035)
    if spec['id'] in ('cover','enclosure'):
        for k in range(24):cube('heat_fin',(.055,.19,sz*.88),(-sx*.46+k*sx*.92/23,sy/2+.08,0),steel,group,.008)
        for side in (-1,1):
            for end in (-1,1):cylinder('mount_bolt',.055,.035,(side*sx*.43,sy/2+.025,end*sz*.4),white,group,segments=12)
    if spec['id'] in ('compute','controls','power'):
        cube('processor',(.48,.075,.48),(0,sy/2+.04,0),dark,group,.01)
        for k in range(18):cube('surface_component',(.075,.04,.13),((k%6-2.5)*.19,sy/2+.025,(k//6-1)*.36),white,group,.005)
        for k in range(3):cube('connector',(.21,.14,.15),((k-1)*.31,.1,sz/2+.055),steel,group,.01)
    if spec['id'] in ('camera','lidar'):
        cylinder('optical_housing',min(sx,sz)*.32,.16,(0,.05,sz/2),dark,group,'forward')
        cylinder('optical_lens',min(sx,sz)*.25,.015,(0,.05,sz/2+.085),glass,group,'forward')
export(kit,'retrofit-kit')
print('KESSEL_AUTHORING_COMPLETE')
