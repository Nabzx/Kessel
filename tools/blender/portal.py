"""Rebuild the Rutongo surface portal as a mine portal set.

Runs through client.py under MCP safe mode, or headless:

    /Applications/Blender.app/Contents/MacOS/Blender --background \
      --factory-startup --python tools/blender/run-headless.py -- portal

REPO_ROOT is supplied by the caller. Coordinate helper matches author.py:
Three.js x/right, y/up, z/forward -> Blender x, -y/forward, z/up.

The previous collar was an eighteen-segment arch of 0.48 m blocks on thin
abutments, which rendered as an ornamental masonry arch standing proud of the
ground rather than as the mouth of a working adit. A real portal is dominated
by mass: a thick concrete set framing the opening, a headwall carrying the
weight of the cut above it, wing walls retaining the faces either side, and
services entering over the crown. Dimensions follow the opening the browser
already uses, eight metres wide by seven high, which is a plausible trackless
adit for the hauler in the underground scene.
"""
import bpy
import math
import random

random.seed(20261108)
for old in list(bpy.data.objects):
    bpy.data.objects.remove(old, do_unlink=True)
bpy.data.orphans_purge(do_recursive=True)

scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1
OUTPUT = REPO_ROOT + '/assets/authored/'
SOURCE = REPO_ROOT + '/tools/blender/source/'

HALF, HEIGHT = 4.0, 7.0          # matches design.portal_width_m / portal_height_m
SPRING = HEIGHT * 0.5            # where the arch leaves the jambs
SET_DEPTH = 1.1                  # concrete thickness front to back
JAMB = 1.5                       # jamb thickness either side of the opening


def xyz(v):
    return (v[0], -v[2], v[1])


def material(name, colour, metal=0, rough=.7):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*colour, 1)
    p.inputs['Metallic'].default_value = metal
    p.inputs['Roughness'].default_value = rough
    return m


# Concrete is dirtier than the old near-white set: this is a working adit in
# iron-rich ground, not a civic structure.
concrete = material('Kessel_Concrete', (.158, .162, .149), 0, .94)
shotcrete = material('Kessel_Section', (.112, .108, .095), 0, .97)
steel = material('Kessel_BareSteel', (.20, .225, .232), .85, .40)
paint = material('Kessel_PaintedSteel', (.47, .255, .055), 0, .55)
rock = material('Kessel_Rock', (.20, .185, .16), 0, .96)
dark = material('Kessel_Rubber', (.010, .014, .016), 0, .95)
white = material('Kessel_Ceramic', (.62, .64, .58), 0, .68)


def empty(name, parent=None, position=(0, 0, 0)):
    o = bpy.data.objects.new(name, None)
    scene.collection.objects.link(o)
    o.parent = parent
    o.location = xyz(position)
    return o


def cube(name, size, pos, mat, parent=None, bevel=.03, rot=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=xyz(pos))
    o = bpy.context.object
    o.name = name
    o.dimensions = xyz((size[0], size[1], -size[2]))
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if rot:
        o.rotation_euler = rot
    if bevel:
        mod = o.modifiers.new('edge highlights', 'BEVEL')
        mod.width = bevel
        mod.segments = 2
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_apply(modifier=mod.name)
    o.data.materials.append(mat)
    o.parent = parent
    return o


def cylinder(name, radius, depth, pos, mat, parent=None, axis='up', segments=20):
    bpy.ops.mesh.primitive_cylinder_add(vertices=segments, radius=radius, depth=depth, location=xyz(pos))
    o = bpy.context.object
    o.name = name
    if axis == 'axle':
        o.rotation_euler.y = math.pi / 2
    if axis == 'forward':
        o.rotation_euler.x = math.pi / 2
    o.data.materials.append(mat)
    o.parent = parent
    for face in o.data.polygons:
        face.use_smooth = len(face.vertices) == 4
    return o


def descendants(root):
    return [root] + list(root.children_recursive)


def export(root, name):
    for parent in reversed(descendants(root)):
        meshes = [c for c in parent.children if c.type == 'MESH']
        if len(meshes) > 1:
            bpy.ops.object.select_all(action='DESELECT')
            for obj in meshes:
                obj.select_set(True)
            bpy.context.view_layer.objects.active = meshes[0]
            bpy.ops.object.join()
            bpy.context.object.name = parent.name + '_surfaces'
    bpy.ops.object.select_all(action='DESELECT')
    for obj in descendants(root):
        obj.select_set(True)
    bpy.context.view_layer.objects.active = root
    bpy.ops.export_scene.gltf(filepath=OUTPUT + name + '.glb', export_format='GLB',
                              use_selection=True, export_yup=True, export_apply=True)
    bpy.ops.wm.save_as_mainfile(filepath=SOURCE + name + '.blend', compress=True)
    triangles = sum(sum(len(p.vertices) - 2 for p in o.data.polygons)
                    for o in descendants(root) if o.type == 'MESH')
    print('KESSEL_ASSET', name, 'triangles', triangles, 'objects', len(descendants(root)))


portal = empty('portal')

# ---- concrete set: jambs, arch ring and headwall -------------------------
# The jambs are full-depth piers rather than the old 0.8 m abutments, so the
# opening reads as cut through mass instead of framed by a rib.
for side in (-1, 1):
    x = side * (HALF + JAMB / 2)
    cube('portal_jamb', (JAMB, SPRING + .6, SET_DEPTH), (x, (SPRING + .6) / 2, 0), concrete, portal)
    cube('portal_footing', (JAMB + .7, .55, SET_DEPTH + .9), (x, .275, 0), concrete, portal)
    # Wing wall splaying back into the cut face, retaining the excavated sides.
    for k in range(4):
        cube('wing_wall', (1.0, 3.4 - k * .55, 2.2),
             (side * (HALF + JAMB + .35 + k * .95), (3.4 - k * .55) / 2, -1.5 - k * 2.1),
             shotcrete, portal, .04)

# Arch ring. Voussoirs are 1.1 m deep and 0.9 m thick, so the ring carries
# visual weight; the old 0.48 m blocks read as decorative banding.
RING = 16
for k in range(RING):
    a = (k + .5) * math.pi / RING
    x = (HALF + .45) * math.cos(a)
    y = SPRING + (HEIGHT - SPRING + .45) * math.sin(a)
    o = cube('voussoir', (.98, .92, SET_DEPTH), (x, y, 0), concrete, portal)
    o.rotation_euler.y = -(a - math.pi / 2)

# Headwall above the crown, tied into the cut.
cube('headwall', (2 * (HALF + JAMB), 1.9, SET_DEPTH * .8), (0, HEIGHT + 1.25, .05), concrete, portal)
cube('headwall_capping', (2 * (HALF + JAMB) + .5, .34, SET_DEPTH * 1.15), (0, HEIGHT + 2.32, 0), shotcrete, portal)

# ---- steel sets receding into the opening --------------------------------
# Visible arch ribs give the mouth depth even before the tunnel shading.
for s, z in enumerate((-2.6, -5.4, -8.4)):
    for k in range(9):
        a = (k + .5) * math.pi / 9
        x = (HALF - .25) * math.cos(a)
        y = SPRING + (HEIGHT - SPRING - .2) * math.sin(a)
        o = cube('steel_set', (.62, .22, .22), (x, y, z), steel, portal, .015)
        o.rotation_euler.y = -(a - math.pi / 2)
    for side in (-1, 1):
        cube('set_leg', (.22, SPRING, .22), (side * (HALF - .25), SPRING / 2, z), steel, portal, .015)

# ---- services over the crown ---------------------------------------------
# Ventilation duct is the dominant service on a real portal; at 1.0 m it reads
# at a glance and gives the opening scale.
cylinder('vent_duct', 1.0, 26, (-HALF + 1.5, HEIGHT - 1.1, -9), steel, portal, 'forward', 24)
for k in range(7):
    cylinder('duct_flange', 1.12, .16, (-HALF + 1.5, HEIGHT - 1.1, 1.4 - k * 3.6), steel, portal, 'forward', 24)
cube('cable_tray', (.75, .18, 26), (HALF - 1.2, HEIGHT - 1.4, -9), steel, portal, .02)
for k in range(5):
    cube('tray_hanger', (.1, 1.0, .1), (HALF - 1.2, HEIGHT - .75, -.6 - k * 4.4), steel, portal, .015)
cylinder('water_pipe', .17, 26, (HALF - 2.1, .85, -9), paint, portal, 'forward', 14)

# ---- furniture: lighting, signage, kerbs ---------------------------------
for side in (-1, 1):
    cube('portal_lamp_body', (.62, .26, .34), (side * 2.5, HEIGHT + .35, .62), steel, portal, .02)
    cube('portal_lamp_lens', (.5, .16, .06), (side * 2.5, HEIGHT + .3, .78), white, portal, .01)
    cube('kerb', (.5, .34, 11), (side * (HALF - .35), .17, -5), paint, portal, .03)
    cube('hazard_post', (.22, 1.5, .22), (side * (HALF + JAMB + .25), .75, 1.9), paint, portal, .02)

cube('sign_board', (3.0, 1.0, .09), (0, HEIGHT + 1.3, .62), white, portal, .02)
cube('sign_frame', (3.2, 1.2, .06), (0, HEIGHT + 1.3, .58), steel, portal, .02)

# Spoil and rock debris at the toes, where a real cut sheds material.
for side in (-1, 1):
    for k in range(5):
        cube('toe_rubble',
             (1.5 + random.random() * 1.6, .5 + random.random() * .7, 1.2 + random.random() * 1.4),
             (side * (HALF + JAMB + .9 + random.random() * 2.4), .3, 1.6 - k * 1.5),
             rock, portal, .05,
             rot=(0, random.random() * math.pi, 0))

export(portal, 'portal-yard')
