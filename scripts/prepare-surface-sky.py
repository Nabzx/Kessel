"""Run with Blender --background --python to tone-map the cleared local HDR source.

Source: /private/tmp/kessel-surface-sky.hdr (download URL in sky-manifest.json).
Output: /private/tmp/kessel-surface-sky.png, converted to WebP with Pillow.
"""
import bpy
image=bpy.data.images.load('/private/tmp/kessel-surface-sky.hdr')
scene=bpy.context.scene;scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB';scene.render.image_settings.color_depth='8'
image.save_render('/private/tmp/kessel-surface-sky.png',scene=scene)
p=image.pixels[:];i=max(range(len(p)//4),key=lambda i:sum(p[i*4:i*4+3]));print('SKY_SUN_UV',i%image.size[0]/image.size[0],1-(i//image.size[0])/image.size[1])
