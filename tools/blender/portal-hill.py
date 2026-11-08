"""A closed excavated rock mass with a real horizontal adit void."""
import bpy,math
for o in list(bpy.data.objects):bpy.data.objects.remove(o,do_unlink=True)
d=EXPERIENCE['visuals']['surface']['portal_hill'];face=EXPERIENCE['assets']['surface']['portal_position'][2];n=80
verts=[];faces=[]
def smooth(v,a,b):
    t=max(0,min(1,(v-a)/(b-a)));return t*t*(3-2*t)
for i in range(n+1):
 for j in range(n+1):
    x=(i/n-.5)*d['size'][0];z=d['position'][2]+(j/n-.5)*d['size'][2]
    r=(x/(d['size'][0]/2))**2+((z-d['position'][2])/(d['size'][2]/2))**2
    ground=d['size'][1]*max(0,1-r)*smooth(-z,66,95)*(.9+.08*math.sin(x*.041)+.06*math.cos(z*.031))
    lateral=smooth(abs(x),d['aperture_half_width_m'],d['aperture_half_width_m']+d['cut_batter_m']);ahead=smooth(z,face-5,face-1)
    h=ground*(1-(1-lateral)*ahead)
    verts.append((x,-z,h))
for i in range(n):
 for j in range(n):
    a=i*(n+1)+j;b=a+n+1;faces.append((a,b,b+1,a+1))
border=[i*(n+1) for i in range(n+1)]+[n*(n+1)+j for j in range(1,n+1)]+[i*(n+1)+n for i in range(n-1,-1,-1)]+[j for j in range(n-1,0,-1)]
bottom=[]
for idx in border:
 x,y,h=verts[idx];bottom.append(len(verts));verts.append((x,y,-12))
for k in range(len(border)):
 q=(k+1)%len(border);faces.append((border[k],bottom[k],bottom[q],border[q]))
faces.append(tuple(reversed(bottom)))
mesh=bpy.data.meshes.new('excavated_mass');mesh.from_pydata(verts,[],faces);mesh.update();hill=bpy.data.objects.new('PortalHill',mesh);bpy.context.collection.objects.link(hill)
bpy.context.view_layer.objects.active=hill;hill.select_set(True);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.mesh.primitive_cube_add(size=1,location=(0,-(face-14),3.6));cut=bpy.context.object;cut.dimensions=(8.5,32,7.5);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
bpy.context.view_layer.objects.active=hill;mod=hill.modifiers.new('horizontal adit','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cut;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cut,do_unlink=True)
m=bpy.data.materials.new('Kessel_Rock');m.diffuse_color=(.2,.18,.16,1);hill.data.materials.append(m)
for p in hill.data.polygons:p.use_smooth=True
bpy.ops.object.select_all(action='SELECT');bpy.ops.export_scene.gltf(filepath=REPO_ROOT+'/assets/authored/portal-hill.glb',export_format='GLB',export_animations=False)
bpy.ops.wm.save_as_mainfile(filepath=REPO_ROOT+'/tools/blender/source/portal-hill.blend',compress=True)
print('KESSEL_CLOSED_PORTAL_HILL')
