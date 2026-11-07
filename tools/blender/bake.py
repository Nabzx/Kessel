"""Original procedural ore normal/AO baking and a matched lighting reference."""
import bpy
import math
from mathutils import Vector
for old in list(bpy.data.objects):bpy.data.objects.remove(old,do_unlink=True)
bpy.ops.mesh.primitive_uv_sphere_add(segments=48,ring_count=24,radius=1)
obj=bpy.context.object;obj.name='original_ore_bake'
for v in obj.data.vertices:
    v.co*=.9+.07*math.sin(v.co.x*13+v.co.z*17)+.04*math.sin(v.co.y*29)
mat=bpy.data.materials.new('original_fractured_ore');mat.use_nodes=True;obj.data.materials.append(mat)
nodes=mat.node_tree.nodes;links=mat.node_tree.links;p=nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(.23,.20,.16,1);p.inputs['Roughness'].default_value=.92
noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=22
bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.4;bump.inputs['Distance'].default_value=.045
links.new(noise.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs['Normal'],p.inputs['Normal'])
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16;scene.render.bake.margin=8
baked={}
for kind in ('NORMAL','AO'):
    image=bpy.data.images.new('ore_'+kind.lower(),512,512);image.colorspace_settings.name='Non-Color'
    node=nodes.new('ShaderNodeTexImage');node.image=image;nodes.active=node
    bpy.ops.object.bake(type=kind)
    image.filepath_raw=REPO_ROOT+'/tools/blender/bakes/ore_'+kind.lower()+'.png';image.file_format='PNG';image.save();baked[kind]=image
normalImage=nodes.new('ShaderNodeTexImage');normalImage.image=baked['NORMAL'];normal=nodes.new('ShaderNodeNormalMap');links.new(normalImage.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],p.inputs['Normal'])
# Calibration uses the exact preview camera and documented AgX rather than
# pretending the offline filmic render is the browser's ACES output.
for k,colour in enumerate(((.18,.18,.18),(.6,.6,.6),(.045,.045,.045))):
    bpy.ops.mesh.primitive_cube_add(size=.55,location=(k*.7-0.7,-1.8,-.7));m=bpy.data.materials.new('calibration_'+str(k));m.diffuse_color=(*colour,1);bpy.context.object.data.materials.append(m)
bpy.ops.object.camera_add(location=(4,-6,3));camera=bpy.context.object;camera.rotation_euler=(Vector((0,0,0))-camera.location).to_track_quat('-Z','Y').to_euler();scene.camera=camera
bpy.ops.object.light_add(type='POINT',location=(2,-3,5));bpy.context.object.data.energy=600
scene.world.color=(.03,.03,.03);scene.view_settings.view_transform='AgX';scene.render.resolution_x=960;scene.render.resolution_y=600;scene.render.resolution_percentage=100
scene.render.filepath=REPO_ROOT+'/docs/phase-11/blender-evidence/material-calibration.png';bpy.ops.render.render(write_still=True)
bpy.ops.export_scene.gltf(filepath=REPO_ROOT+'/docs/phase-11/blender-evidence/material-calibration.glb',export_format='GLB',export_cameras=False,export_lights=False)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=REPO_ROOT+'/tools/blender/source/material-calibration.blend',compress=True)
print('KESSEL_BAKE_COMPLETE',bpy.app.version_string,'512px tangent +Y normal and AO; AgX reference')
