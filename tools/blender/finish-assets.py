"""Original engineering detail, preserving named kinematic pivots and metre scale."""
import bpy, math, random
from mathutils import Vector
R=REPO_ROOT; random.seed(5301)
def clear():
    for o in list(bpy.data.objects):bpy.data.objects.remove(o,do_unlink=True)
def xyz(v):return(v[0],-v[2],v[1])
def mat(name,c,metal=0,rough=.6):
    m=bpy.data.materials.new(name);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*c,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough;return m
def cube(name,size,pos,m,parent=None,b=.008):
    bpy.ops.mesh.primitive_cube_add(size=1);o=bpy.context.object;o.name=name;o.dimensions=(size[0],size[2],size[1]);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.location=xyz(pos);o.parent=parent;o.data.materials.append(m)
    if b:
        mod=o.modifiers.new('machined edge','BEVEL');mod.width=b;mod.segments=2;bpy.ops.object.modifier_apply(modifier=mod.name)
    return o
def cyl(name,r,d,pos,m,parent=None,axis='up',n=16):
    bpy.ops.mesh.primitive_cylinder_add(vertices=n,radius=r,depth=d);o=bpy.context.object;o.name=name;o.location=xyz(pos);o.parent=parent;o.data.materials.append(m)
    if axis=='x':o.rotation_euler.y=math.pi/2
    if axis=='z':o.rotation_euler.x=math.pi/2
    return o
def empty(name,parent=None):
    o=bpy.data.objects.new(name,None);bpy.context.scene.collection.objects.link(o);o.parent=parent;return o
def export(name):
    bpy.ops.object.select_all(action='SELECT');bpy.ops.export_scene.gltf(filepath=R+'/assets/authored/'+name+'.glb',export_format='GLB',export_animations=name=='reference-loader')
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=R+'/tools/blender/source/'+name+'.blend',compress=True)

# Keep the simulator's exact loader envelope and every articulation attachment.
bpy.ops.wm.open_mainfile(filepath=R+'/tools/blender/source/reference-loader-base.blend')
paint=bpy.data.materials.get('Kessel_PaintedSteel');steel=bpy.data.materials.get('Kessel_BareSteel');dark=bpy.data.materials.get('Kessel_Rubber');glass=bpy.data.materials.get('Kessel_Lens')
root=bpy.data.objects['ReferenceLoader'];front=bpy.data.objects['FrontJoint'];boom=bpy.data.objects['Boom'];bucket=bpy.data.objects['Bucket']
for side in [-1,1]:
    for z in [-1.5,-.7,.15,.95]:cube('guardrail_upright',(.025,.22,.025),(side*.64,1.42,z),steel,root)
    cube('cab_roof',(1.17,.065,1.18),(0,1.89,.65),paint,root)
    for z in [.22,1.13]:cube('window_pillar',(.045,.53,.045),(side*.51,1.59,z),steel,root)
    cube('door_sill',(.05,.06,1.05),(side*.52,1.30,.7),steel,root)
    cube('door_handle',(.045,.025,.16),(side*.565,1.5,.75),steel,root)
    cube('rear_grille',(.045,.36,1.32),(side*.67,1.05,-.98),dark,root)
    for k in range(12):cube('grille_fin',(.052,.018,.98),(side*.69,.9+k*.027,-1),steel,root,b=.002)
    cyl('hydraulic_barrel',.055,.8,(side*.35,-.12,.44),dark,boom,axis='z');cyl('hydraulic_rod',.031,.62,(side*.35,-.12,.92),steel,boom,axis='z')
    for z in [.12,.95]:cyl('bucket_pin',.065,.13,(side*.73,.17,z),steel,bucket,axis='x')
    cube('bucket_wear_plate',(.09,.03,.85),(side*.53,-.075,.62),steel,bucket)
for i in range(4):
    wheel=bpy.data.objects['Wheel_'+str(i)];side=1 if i%2==0 else -1
    for k in range(28):
        a=k*math.tau/28;o=cube('chevron_tread',(.19,.028,.055),(0,.545*math.cos(a),.545*math.sin(a)),dark,wheel,b=.004);o.rotation_euler.x=-a
    for k in range(8):
        a=k*math.tau/8;cyl('wheel_lug',.022,.021,(side*.11,.16*math.cos(a),.16*math.sin(a)),steel,wheel,axis='x',n=6)
for side in [-1,1]:
    cube('worklamp_housing',(.2,.14,.08),(side*.52,1.12,1.93),dark,front)
    cube('worklamp_lens',(.16,.10,.012),(side*.52,1.12,1.976),glass,front)
# Merge meshes per rigid attachment/material. Existing pivots stay separate.
for parent in [root,front,boom,bucket]+[bpy.data.objects['Wheel_'+str(i)] for i in range(4)]:
    meshes=[o for o in parent.children if o.type=='MESH']
    for m in set(o.active_material for o in meshes):
        group=[o for o in parent.children if o.type=='MESH' and o.active_material==m]
        bpy.ops.object.select_all(action='DESELECT')
        for o in group:o.select_set(True)
        if group:bpy.context.view_layer.objects.active=group[0];bpy.ops.object.join()
export('reference-loader')

# A proposed 340 x 260 mm enclosure. Browser presentation magnification is 10x.
clear();steel=mat('Kessel_AnodisedAluminium',(.13,.16,.175),.85,.32);edge=mat('Kessel_MachinedMetal',(.43,.46,.44),.9,.26);black=mat('Kessel_Gasket',(.009,.014,.016),0,.85);pcb=mat('Kessel_PCB',(.012,.065,.05),0,.65);chip=mat('Kessel_Packages',(.023,.027,.03),.1,.48);copper=mat('Kessel_Contacts',(.43,.31,.13),.9,.32);ceramic=mat('Kessel_Ceramic',(.40,.39,.31),.2,.68);glass=mat('Kessel_SensorWindow',(.014,.04,.05),.3,.12)
kit=empty('kit')
for spec in EXPERIENCE['kit']['components']:
    name=spec['id'];g=empty(name,kit);g.scale=(.1,.1,.1);sx,sy,sz=spec['size'];board=name in ['compute','controls','power']
    if name=='enclosure':
        cube('base_plate',(sx,.09,sz),(0,-.18,0),steel,g)
        for side in [-1,1]:
            cube('case_wall',(.10,.83,sz),(side*(sx/2-.05),.18,0),steel,g)
            cube('gasket_land',(.035,.025,sz-.1),(side*(sx/2-.075),.61,0),black,g)
            cube('mounting_foot',(.32,.07,sz+.3),(side*1.75,-.18,0),steel,g)
            for z in [-.85,0,.85]:
                cyl('M12_connector',.105,.16,(side*1.78,.15,z),edge,g,'x');cyl('connector_insert',.077,.17,(side*1.79,.15,z),black,g,'x')
                for k in range(4):cyl('connector_contact',.009,.018,(side*1.884,.15+(.03 if k<2 else -.03),z+(.03 if k%2 else -.03)),copper,g,'x',8)
        for side in [-1,1]:cube('end_wall',(sx-.15,.83,.09),(0,.18,side*(sz/2-.045)),steel,g)
        for x in [-1.45,1.45]:
            for z in [-1.05,1.05]:cyl('mount_standoff',.07,.42,(x,.07,z),edge,g)
    elif name=='cover':
        cube('lid',(sx,.12,sz),(0,0,0),steel,g)
        for k in range(27):cube('heatsink_fin',(.035,.17,sz-.16),((k-13)*.12,.13,0),steel,g,b=.005)
        for x in [-1.52,1.52]:
            for z in [-1.13,1.13]:cyl('captive_fastener',.045,.05,(x,.08,z),edge,g,n=12);cube('screw_slot',(.05,.008,.01),(x,.111,z),black,g,b=.001)
    elif board:
        cube('FR4_board',(sx,.045,sz),(0,0,0),pcb,g,b=.008)
        cube('processor_package',(sx*.36,.09,sz*.35),(0,.07,0),chip,g)
        for side in [-1,1]:
            for k in range(7):
                z=(k-3)*sz*.11;cube('capacitor',(.07,.04,.035),(side*sx*.39,.05,z),ceramic,g,b=.003)
                cube('copper_route',(.12,.003,.007),(side*sx*.24,.024,z),copper,g,b=0)
            cube('board_header',(.12,.12,sz*.72),(side*(sx/2-.08),.085,0),black,g)
            for k in range(10):cube('header_pin',(.015,.025,.023),(side*(sx/2-.08),.15,(k-4.5)*sz*.065),copper,g,b=.001)
        for x in [-sx*.4,sx*.4]:
            for z in [-sz*.4,sz*.4]:cyl('board_support',.035,.07,(x,-.045,z),edge,g,n=8)
        if name=='power':
            for k in range(3):cyl('power_capacitor',.08,.18,((k-1)*.23,.12,.27),chip,g)
        if name=='compute':cube('thermal_spreader',(sx*.58,.025,sz*.56),(0,.13,0),edge,g)
    else:
        cube('sensor_housing',(sx,sy,sz),(0,0,0),steel,g,b=.035)
        for x in [-sx*.3,sx*.3] if name=='camera' else [0]:
            cyl('optical_collar',.14,.08,(x,0,sz*.5),black,g,'z');cyl('optical_window',.115,.085,(x,0,sz*.5+.01),glass,g,'z',32)
        cube('sensor_bracket',(sx+.18,.06,sz+.1),(0,-sy*.6,0),edge,g)
        cyl('sensor_cable_gland',.05,.16,(sx*.5,0,0),black,g,'x')
# Merge by component/material, keeping distinct mechanical parts as named meshes.
for g in list(kit.children):
    meshes=[o for o in g.children if o.type=='MESH']
    for m in set(o.active_material for o in meshes):
        group=[o for o in g.children if o.type=='MESH' and o.active_material==m];bpy.ops.object.select_all(action='DESELECT')
        for o in group:o.select_set(True)
        if group:bpy.context.view_layer.objects.active=group[0];bpy.ops.object.join()
export('retrofit-kit')
print('KESSEL_FINISH_ASSETS_COMPLETE')
