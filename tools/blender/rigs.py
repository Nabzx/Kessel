"""Original logged reference rig and non-destructive licensed excavator round trip."""
import bpy
import math
for old in list(bpy.data.objects):bpy.data.objects.remove(old,do_unlink=True)
bpy.data.orphans_purge(do_recursive=True)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.render.fps=10
OUTPUT=REPO_ROOT+'/assets/authored/';SOURCE=REPO_ROOT+'/tools/blender/source/'

def xyz(p):return (p[0],-p[2],p[1])
def empty(name,parent=None,pos=(0,0,0)):
    obj=bpy.data.objects.new(name,None);scene.collection.objects.link(obj);obj.parent=parent;obj.location=xyz(pos);return obj

def mat(name,colour,metal=0):
    m=bpy.data.materials.new(name);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*colour,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=.5 if metal else .7;return m
paint=mat('Kessel_PaintedSteel',(.52,.28,.06));steel=mat('Kessel_BareSteel',(.21,.25,.26),.8);dark=mat('Kessel_Rubber',(.012,.017,.019));glass=mat('Kessel_Lens',(.015,.08,.095))

def part(name,size,pos,m,parent):
    bpy.ops.mesh.primitive_cube_add(size=1);o=bpy.context.object;o.name=name;o.dimensions=(size[0],size[2],size[1]);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.location=xyz(pos);o.parent=parent;o.data.materials.append(m)
    b=o.modifiers.new('edge radii','BEVEL');b.width=.025;b.segments=2;bpy.ops.object.modifier_apply(modifier=b.name);return o
root=empty('ReferenceLoader');front=empty('FrontJoint',root,(0,0,1.8));boom=empty('Boom',front,(0,.75,1.6));bucket=empty('Bucket',front)
part('rear_chassis',(1.28,.35,3.65),(0,.65,-.025),steel,root);part('engine',(1.3,.65,1.75),(0,1.06,-.9),paint,root);part('cab',(1.1,.77,1.15),(0,1.475,.65),paint,root);part('cab_glass',(1.03,.49,.96),(0,1.54,.73),glass,root);part('front_chassis',(1.2,.32,1.9),(0,.7,.8),paint,front)
for side in (-1,1):
    for k in range(7):part('engine_louvre',(.02,.3,.045),(side*.66,1.1,-1.5+k*.13),dark,root)
    part('boom_arm',(.12,.15,1),(side*.46,0,.5),paint,boom)
    part('piston',(.05,.065,.82),(side*.34,-.12,.45),steel,boom)
part('bucket_floor',(1.5,.07,.9),(0,-.035,.6),steel,bucket);part('bucket_back',(1.5,.35,.08),(0,.175,.18),paint,bucket)
for side in (-1,1):part('bucket_side',(.065,.35,.9),(side*.717,.175,.6),paint,bucket)
wheels=[]
for axle,parent in ((0,root),(1.6,front)):
    for side in (1,-1):
        pivot=empty('Wheel_'+str(len(wheels)),parent,(side*.65,.55,axle));wheels.append(pivot)
        bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=.55,depth=.2);o=bpy.context.object;o.name='tyre';o.parent=pivot;o.rotation_euler.y=math.pi/2;o.data.materials.append(dark)
        bpy.ops.mesh.primitive_cylinder_add(vertices=16,radius=.23,depth=.195);o=bpy.context.object;o.name='hub';o.parent=pivot;o.rotation_euler.y=math.pi/2;o.data.materials.append(steel)
# Every pose is keyed on recorded time, never an independent looping clip.
for row in REFERENCE_TRACE['records']:
    s=row['state'];frame=s[10]*10+1
    root.location=(s[0],s[1],0);root.rotation_euler.z=math.pi/2+s[2];front.rotation_euler.z=s[4]
    bucket.rotation_euler.x=-s[6];bucket.location=xyz((0,.35+2*math.sin(s[5])-.6*math.sin(s[6]),1.6+1.2*math.cos(s[5])-.6*math.cos(s[6])))
    dy=.35+2*math.sin(s[5])-.6*math.sin(s[6])-.75;dz=1.2*math.cos(s[5])-.6*math.cos(s[6]);boom.rotation_euler.x=-math.atan2(dy,dz);boom.scale.y=math.hypot(dy,dz)
    for i,wheel in enumerate(wheels):
        wheel.rotation_euler.x=row['wheel_angles_rad'][i];wheel.keyframe_insert(data_path='rotation_euler',frame=frame)
    for obj,paths in ((root,('location','rotation_euler')),(front,('rotation_euler',)),(bucket,('location','rotation_euler')),(boom,('rotation_euler','scale'))):
        for path in paths:obj.keyframe_insert(data_path=path,frame=frame)
for action in bpy.data.actions:
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for point in curve.keyframe_points:point.interpolation='LINEAR'
scene.frame_start=1;scene.frame_end=math.ceil(REFERENCE_TRACE['records'][-1]['next_t_s']*10)+1;scene.frame_set(1)
bpy.ops.object.select_all(action='SELECT');bpy.ops.export_scene.gltf(filepath=OUTPUT+'reference-loader.glb',export_format='GLB',export_force_sampling=False)
bpy.ops.wm.save_as_mainfile(filepath=SOURCE+'reference-loader.blend',compress=True)
print('KESSEL_REFERENCE_RIG',len(REFERENCE_TRACE['records']),'recorded frames')
for old in list(bpy.data.objects):bpy.data.objects.remove(old,do_unlink=True)
bpy.data.orphans_purge(do_recursive=True)
bpy.ops.import_scene.gltf(filepath=EXCAVATOR_COPY)
bpy.ops.export_scene.gltf(filepath=OUTPUT+'excavator.glb',export_format='GLB',export_animations=True)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=SOURCE+'excavator.blend',compress=True)
print('KESSEL_EXCAVATOR_RIG',[(a.name,len(a.data.bones)) for a in bpy.data.objects if a.type=='ARMATURE'])
