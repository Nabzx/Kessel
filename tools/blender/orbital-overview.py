"""Generate a genuinely reduced satellite LOD from the original close export."""
import bpy
for old in list(bpy.data.objects):bpy.data.objects.remove(old,do_unlink=True)
bpy.ops.import_scene.gltf(filepath=REPO_ROOT+'/assets/authored/observation-satellite.glb')
for o in list(bpy.context.scene.objects):
 if o.type!='MESH':continue
 bpy.context.view_layer.objects.active=o;o.select_set(True)
 mod=o.modifiers.new('overview reduction','DECIMATE');mod.ratio=.38;bpy.ops.object.modifier_apply(modifier=mod.name)
 for p in o.data.polygons:p.use_smooth=False
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=REPO_ROOT+'/assets/authored/observation-satellite-overview.glb',export_format='GLB',use_selection=True,export_yup=True,export_apply=True,export_animations=False)
bpy.ops.wm.save_as_mainfile(filepath=REPO_ROOT+'/tools/blender/source/observation-satellite-overview.blend',compress=True)
print('ORBITAL_OVERVIEW',sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in bpy.context.scene.objects if o.type=='MESH'))
