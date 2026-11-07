"""Reusable cleared PBR swatches at their declared physical repeat scale."""
import bpy
for old in list(bpy.data.objects):bpy.data.objects.remove(old,do_unlink=True)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=8;scene.unit_settings.system='METRIC'
for index,spec in enumerate((EXPERIENCE['visuals']['rock'],EXPERIENCE['visuals']['surface']['ground'])):
    repeat=spec['repeat_m'];bpy.ops.mesh.primitive_plane_add(size=repeat,location=(index*18,0,0));obj=bpy.context.object;obj.name='cleared_swatch_'+str(index)
    mat=bpy.data.materials.new('ClearedPBR_'+str(index));mat.use_nodes=True;obj.data.materials.append(mat);nodes=mat.node_tree.nodes;links=mat.node_tree.links;shader=nodes.get('Principled BSDF')
    for key in ('diff','normal','roughness','ao'):
        if key not in spec:continue
        image=bpy.data.images.load(REPO_ROOT+'/'+spec[key],check_existing=True);image.colorspace_settings.name='sRGB' if key=='diff' else 'Non-Color'
        texture=nodes.new('ShaderNodeTexImage');texture.image=image;texture.label=key+'; physical repeat '+str(repeat)+' m'
        if key=='diff':links.new(texture.outputs['Color'],shader.inputs['Base Color'])
        if key=='roughness':links.new(texture.outputs['Color'],shader.inputs['Roughness'])
        if key=='normal':
            normal=nodes.new('ShaderNodeNormalMap');links.new(texture.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],shader.inputs['Normal'])
    mat['physical_repeat_m']=repeat;mat['source_notice']='Individually cleared CC0 maps; assets/materials/manifest.json and source notices'
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=REPO_ROOT+'/tools/blender/source/material-library.blend',compress=True)
print('KESSEL_MATERIAL_LIBRARY','two cleared physical-scale swatches; packed images; sRGB colour and linear GL normals/roughness')
