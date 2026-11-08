"""Closed stratified section masses, with fracture relief kept inside clearance."""
import bpy,math,random
random.seed(5302)
for o in list(bpy.data.objects):bpy.data.objects.remove(o,do_unlink=True)
rock=bpy.data.materials.new('Kessel_Rock');rock.diffuse_color=(.23,.22,.20,1)
cap=bpy.data.materials.new('Kessel_Section');cap.diffuse_color=(.28,.27,.24,1)
root=bpy.data.objects.new('geology',None);bpy.context.collection.objects.link(root)
for k,spec in enumerate([EXPERIENCE['mine']['base']]+EXPERIENCE['mine']['pillars']+EXPERIENCE['mine']['rims']):
 w,h,d=spec['size'];px,py,pz=spec['position'];count=64;layers=7;v=[];f=[]
 for layer in range(layers):
  for i in range(count):
   a=i*math.tau/count;c=math.cos(a);s=math.sin(a);power=.31 if k else .22
   x=math.copysign(abs(c)**power,c)*w/2;z=math.copysign(abs(s)**power,s)*d/2
   relief=min(w,d)*(.025+.035*math.sin(i*1.73+k+layer*.7)**2)
   x-=math.copysign(relief,x);z-=math.copysign(relief,z)
   y=py-h/2+h*layer/(layers-1)
   if k==0 and layer==0:y-=2+math.sin(i*1.8)*2
   v.append((px+x,-(pz+z),y))
 for layer in range(layers-1):
  for i in range(count):
   a=layer*count+i;b=layer*count+(i+1)%count;f.append((a,b,b+count,a+count))
 f.append(tuple(reversed(range(count))));f.append(tuple((layers-1)*count+i for i in range(count)))
 mesh=bpy.data.meshes.new('fractured_section');mesh.from_pydata(v,[],f);mesh.update();o=bpy.data.objects.new('section_'+str(k),mesh);bpy.context.collection.objects.link(o);o.parent=root;o.data.materials.append(rock);o.data.materials.append(cap)
 for face in o.data.polygons:face.material_index=1 if abs(face.normal.z)>.9 and k>0 else 0
 bpy.context.view_layer.objects.active=o;o.select_set(True);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT');o.select_set(False)
bpy.ops.object.select_all(action='SELECT');bpy.ops.export_scene.gltf(filepath=REPO_ROOT+'/assets/authored/geology.glb',export_format='GLB',export_animations=False)
bpy.ops.wm.save_as_mainfile(filepath=REPO_ROOT+'/tools/blender/source/geology.blend',compress=True)
print('KESSEL_GEOLOGY_SECTION_COMPLETE')
