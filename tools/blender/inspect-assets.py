"""Measure actual GLB bounds and welded closed-section topology through Blender."""
import bpy
import bmesh
import json
for name in ('geology','portal-yard','hauler-close','hauler-overview','ore-pile','reference-loader','excavator','retrofit-kit'):
    for old in list(bpy.data.objects):bpy.data.objects.remove(old,do_unlink=True)
    bpy.ops.import_scene.gltf(filepath=REPO_ROOT+'/assets/authored/'+name+'.glb')
    bpy.context.view_layer.update();depsgraph=bpy.context.evaluated_depsgraph_get()
    points=[];triangles=0;boundary=0;non_manifold=0
    for obj in bpy.context.scene.objects:
        if obj.type!='MESH' or obj.hide_render:continue
        evaluated=obj.evaluated_get(depsgraph);mesh=evaluated.to_mesh()
        points.extend([evaluated.matrix_world@v.co for v in mesh.vertices]);triangles+=sum(len(p.vertices)-2 for p in mesh.polygons)
        evaluated.to_mesh_clear()
        if name=='geology':
            bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0001)
            boundary+=sum(e.is_boundary for e in bm.edges);non_manifold+=sum(not e.is_manifold for e in bm.edges);bm.free()
    low=[min(v[i] for v in points) for i in range(3)];high=[max(v[i] for v in points) for i in range(3)]
    print('KESSEL_BOUNDS',json.dumps({'asset':name,'blender_xyz_min':low,'blender_xyz_max':high,'span_m':[b-a for a,b in zip(low,high)],'triangles':triangles,'open_boundary_edges':boundary if name=='geology' else None,'non_manifold_edges':non_manifold if name=='geology' else None}))
    if name=='geology':
        assert boundary==0,'Geological section has open boundaries after GLB round trip'
        assert high[0]<=82.001 and low[0]>=-82.001 and high[1]<=66.001 and low[1]>=-66.001,'Geometry intrudes beyond authored bounds'
