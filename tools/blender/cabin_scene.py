"""Render the LeMSIC tree inside a log cabin, with a stone fireplace on the left.

The tree stands in the middle of the room; a corner fireplace on the left throws
warm light across it, and a window on the right shows a snowy night.

The render is split into light groups (fire left / fire right / embers / tree
lights / room) so the website can make the firelight flicker for real: it blends
images lit by brighter and dimmer fire, in time with the animated flames.

Run with Blender:          blender -b -P tools/blender/cabin_scene.py -- [--preview]
or with the bpy module:    python tools/blender/cabin_scene.py [--preview]
                           (also needs:  pip install OpenEXR)

Writes (into site/assets/cabin/):
  cabin-low.jpg, cabin-left.jpg, cabin-right.jpg   the room with the fire dim / leaning left / leaning right
  cabin.jpg                                        the room with the fire at normal strength
  scene.json                                       where the fire, window and ornaments are in the image
"""
import json
import math
import os
import sys
import time

import numpy as np
import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lemsic_tree as T  # noqa: E402
import cabin_props as P  # noqa: E402
import fares as FARES  # noqa: E402
from lemsic_tree import (box, link, mesh_object, needles, new_material, principled,  # noqa: E402
                         simple_material, tubes, icosphere_template, spheres, tri_mesh_object)

ROOT = os.path.dirname(os.path.dirname(HERE))
OUT_DIR = os.path.join(ROOT, "site", "assets", "cabin")
BUILD_DIR = os.path.join(ROOT, "build")
EMBLEM = os.path.join(HERE, "textures", "lemsic-emblem.png")
TREE_STYLE = "cedar_lemsic"          # see lemsic_tree.STYLES
FARES_AT = (1.95, 0.55, 0.0)

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
PREVIEW = "--preview" in ARGS
RES = (640, 360) if PREVIEW else (1920, 1080)
SAMPLES = 64 if PREVIEW else 640
for _a in ARGS:
    if _a.startswith("--res="):
        RES = tuple(int(x) for x in _a[6:].split("x"))
    if _a.startswith("--samples="):
        SAMPLES = int(_a[10:])

rng = np.random.default_rng(7)

# ---------------------------------------------------------------- room layout (metres)
BACK_Y = 1.55            # back wall
LEFT_X = -3.75           # left wall
RIGHT_X = 5.2
CEILING = 3.95
CAMERA = Vector((-0.3, -5.3, 1.66))
TARGET = Vector((-0.3, 0.0, 1.62))
LENS = 27

# fireplace: a corner fireplace facing into the room
FP_ANGLE = math.radians(45)                      # rotation about Z
FP_FRONT = Vector((-2.80, 0.68, 0.0))            # centre of the hearth front, on the floor
OPEN_W, OPEN_H, OPEN_D = 0.96, 0.74, 0.55        # firebox opening
HEARTH_H = 0.16
SURROUND_W, MANTEL_Z = 1.80, 1.30

WINDOW_X = (2.35, 3.55)
WINDOW_Z = (0.95, 2.45)


# ---------------------------------------------------------------- helpers
def fp(local):
    """Fireplace local coordinates (x across the face, y into the wall, z up) to world."""
    c, s = math.cos(FP_ANGLE), math.sin(FP_ANGLE)
    x, y, z = local
    return Vector((FP_FRONT.x + c * x - s * y, FP_FRONT.y + s * x + c * y, z))


def place_box(name, size, local_center, mat, bevel=0.01, in_fireplace=True):
    loc = fp(local_center) if in_fireplace else Vector(local_center)
    ob = box(name, size, loc, mat, FP_ANGLE if in_fireplace else 0.0)
    ob.modifiers["bevel"].width = bevel
    return ob


def set_lightgroup(ob, group):
    ob.lightgroup = group


def point_light(name, loc, power, color, radius, group):
    ld = bpy.data.lights.new(name, "POINT")
    ld.energy = power
    ld.color = color
    ld.shadow_soft_size = radius
    ob = link(bpy.data.objects.new(name, ld))
    ob.location = loc
    set_lightgroup(ob, group)
    return ob


def area_light(name, loc, target, power, size, color, group, shape="SQUARE", size_y=None):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy = power
    ld.size = size
    ld.shape = shape
    if size_y:
        ld.size_y = size_y
    ld.color = color
    ob = link(bpy.data.objects.new(name, ld))
    ob.location = loc
    ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    set_lightgroup(ob, group)
    return ob


def node(nt, kind, **inputs):
    n = nt.nodes.new(kind)
    for k, v in inputs.items():
        n.inputs[k].default_value = v
    return n


# ---------------------------------------------------------------- materials
def ember_material(name, base, glow_scale, strength, threshold=0.52):
    """Charred wood / coals with glowing cracks."""
    m, nt, out = new_material(name)
    L = nt.links.new
    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = node(nt, "ShaderNodeTexNoise", Scale=glow_scale, Detail=8.0, Roughness=0.6)
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = threshold, (0, 0, 0, 1)
    els[1].position, els[1].color = threshold + 0.18, (1.0, 0.36, 0.05, 1)
    e2 = els.new(threshold + 0.09)
    e2.color = (0.55, 0.06, 0.01, 1)
    b = principled(nt, base, rough=0.9)
    b.inputs["Emission Strength"].default_value = strength
    L(tc.outputs["Object"], noise.inputs["Vector"])
    L(noise.outputs["Fac"], ramp.inputs["Fac"])
    L(ramp.outputs["Color"], b.inputs["Emission Color"])
    L(b.outputs[0], out.inputs["Surface"])
    return m


def chinking_material():
    m, nt, out = new_material("Chinking")
    L = nt.links.new
    tc = nt.nodes.new("ShaderNodeTexCoord")
    n = node(nt, "ShaderNodeTexNoise", Scale=60.0, Detail=10.0)
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.13, 0.12, 0.10, 1)
    ramp.color_ramp.elements[1].color = (0.24, 0.22, 0.19, 1)
    bump = node(nt, "ShaderNodeBump", Strength=0.7, Distance=0.006)
    b = principled(nt, (0.45, 0.42, 0.37), rough=0.97)
    L(tc.outputs["Object"], n.inputs["Vector"])
    L(n.outputs["Fac"], ramp.inputs["Fac"])
    L(n.outputs["Fac"], bump.inputs["Height"])
    L(ramp.outputs["Color"], b.inputs["Base Color"])
    L(bump.outputs["Normal"], b.inputs["Normal"])
    L(b.outputs[0], out.inputs["Surface"])
    return m


def window_glass_material():
    """Clear glass with a little reflection, frosted along the edges of each pane."""
    m, nt, out = new_material("WindowGlass")
    L = nt.links.new
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    def math_node(op, a=None, b=None):
        n = nt.nodes.new("ShaderNodeMath")
        n.operation = op
        if a is not None:
            n.inputs[0].default_value = a
        if b is not None:
            n.inputs[1].default_value = b
        return n
    ux = math_node("MULTIPLY", b=2.0)
    vy = math_node("MULTIPLY", b=3.0)
    fu, fv = math_node("FRACT"), math_node("FRACT")
    iu, iv = math_node("SUBTRACT", a=1.0), math_node("SUBTRACT", a=1.0)
    mu, mv = math_node("MINIMUM"), math_node("MINIMUM")
    edge = math_node("MINIMUM")
    noise = node(nt, "ShaderNodeTexNoise", Scale=14.0, Detail=8.0)
    jitter = math_node("MULTIPLY_ADD")
    jitter.inputs[1].default_value = 0.14
    jitter.inputs[2].default_value = -0.07
    add = math_node("ADD")
    frost = node(nt, "ShaderNodeMapRange")
    frost.inputs["From Min"].default_value = 0.13
    frost.inputs["From Max"].default_value = 0.02
    L(tc.outputs["UV"], sep.inputs[0])
    L(sep.outputs["X"], ux.inputs[0]); L(sep.outputs["Y"], vy.inputs[0])
    L(ux.outputs[0], fu.inputs[0]); L(vy.outputs[0], fv.inputs[0])
    L(fu.outputs[0], iu.inputs[1]); L(fv.outputs[0], iv.inputs[1])
    L(fu.outputs[0], mu.inputs[0]); L(iu.outputs[0], mu.inputs[1])
    L(fv.outputs[0], mv.inputs[0]); L(iv.outputs[0], mv.inputs[1])
    L(mu.outputs[0], edge.inputs[0]); L(mv.outputs[0], edge.inputs[1])
    L(tc.outputs["Object"], noise.inputs["Vector"])
    L(noise.outputs["Fac"], jitter.inputs[0])
    L(edge.outputs[0], add.inputs[0]); L(jitter.outputs[0], add.inputs[1])
    L(add.outputs[0], frost.inputs["Value"])
    clear = nt.nodes.new("ShaderNodeBsdfTransparent")
    gloss = nt.nodes.new("ShaderNodeBsdfGlossy")
    gloss.inputs["Roughness"].default_value = 0.03
    fres = node(nt, "ShaderNodeFresnel", IOR=1.5)
    glass = nt.nodes.new("ShaderNodeMixShader")
    L(fres.outputs[0], glass.inputs[0]); L(clear.outputs[0], glass.inputs[1]); L(gloss.outputs[0], glass.inputs[2])
    ice = nt.nodes.new("ShaderNodeBsdfTranslucent")
    ice.inputs["Color"].default_value = (0.75, 0.82, 0.92, 1)
    ice_d = nt.nodes.new("ShaderNodeBsdfDiffuse")
    ice_d.inputs["Color"].default_value = (0.7, 0.75, 0.82, 1)
    ice_mix = nt.nodes.new("ShaderNodeMixShader")
    ice_mix.inputs[0].default_value = 0.4
    L(ice.outputs[0], ice_mix.inputs[1]); L(ice_d.outputs[0], ice_mix.inputs[2])
    final = nt.nodes.new("ShaderNodeMixShader")
    L(frost.outputs[0], final.inputs[0]); L(glass.outputs[0], final.inputs[1]); L(ice_mix.outputs[0], final.inputs[2])
    L(final.outputs[0], out.inputs["Surface"])
    return m


def build_room():
    rnd = np.random.default_rng(31)
    side_x = P.log_side_material("LogsX", "X")
    side_y = P.log_side_material("LogsY", "Y")
    endg = P.end_grain_material()
    chink = chinking_material()
    r = 0.13
    pitch = 2 * r + 0.028                  # leaves a band of chinking between the logs
    wx0, wx1 = WINDOW_X
    wz0, wz1 = WINDOW_Z
    logs = []
    z = r
    while z < CEILING + 0.4:
        spans = [(LEFT_X - 0.3, RIGHT_X)]
        if wz0 - r * 0.8 < z < wz1 + r * 0.8:
            spans = [(LEFT_X - 0.3, wx0 - 0.05), (wx1 + 0.05, RIGHT_X)]
        for a, b in spans:
            rr = r * rnd.uniform(0.9, 1.07)
            logs.append(((a, BACK_Y + rr * 0.75, z), (b, BACK_Y + rr * 0.75, z), rr))
        z += pitch
    P.logs_mesh("LogWall", logs, rnd, [side_x, endg])
    logs = []
    z = r + pitch / 2                      # offset by half a log, as notched corners are
    while z < CEILING + 0.4:
        rr = r * rnd.uniform(0.9, 1.07)
        logs.append(((LEFT_X - rr * 0.75, -8.5, z), (LEFT_X - rr * 0.75, BACK_Y + 0.35, z), rr))
        z += pitch
    P.logs_mesh("LogWallLeft", logs, rnd, [side_y, endg])

    # chinking between the logs (recessed), with a hole for the window
    bpy.ops.mesh.primitive_plane_add(size=1, location=((LEFT_X + RIGHT_X) / 2, BACK_Y + 0.07, CEILING / 2),
                                     rotation=(math.radians(90), 0, 0))
    pl = bpy.context.active_object
    pl.scale = (RIGHT_X - LEFT_X, CEILING + 0.6, 1)
    pl.data.materials.append(chink)
    hole = place_box("WindowHole", (wx1 - wx0, 0.6, wz1 - wz0), ((wx0 + wx1) / 2, BACK_Y + 0.07, (wz0 + wz1) / 2),
                     chink, in_fireplace=False)
    boo = pl.modifiers.new("hole", "BOOLEAN")
    boo.object = hole
    boo.operation = "DIFFERENCE"
    hole.hide_render = True
    hole.hide_viewport = True
    bpy.ops.mesh.primitive_plane_add(size=1, location=(LEFT_X - 0.07, -3, CEILING / 2), rotation=(0, math.radians(90), 0))
    pl = bpy.context.active_object
    pl.scale = (CEILING + 0.6, 12, 1)
    pl.data.materials.append(chink)

    # wide-plank floor
    P.plank_floor("Floor", rnd, LEFT_X - 0.3, RIGHT_X, -8.5, BACK_Y + 0.25)

    # ceiling boards and hewn beams
    beam_mat = P.log_side_material("Beams", "Y")
    board_mat = P.log_side_material("CeilingBoards", "X")
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0.6, -3.2, CEILING + 0.3), rotation=(math.radians(180), 0, 0))
    ce = bpy.context.active_object
    ce.scale = (RIGHT_X - LEFT_X + 1, 11, 1)
    ce.data.materials.append(board_mat)
    for x in np.arange(-3.2, RIGHT_X, 1.6):
        b = box("Beam", (0.26, 11, 0.30), (x, -3.2, CEILING + 0.14), beam_mat)
        b.modifiers["bevel"].width = 0.03
        b.modifiers["bevel"].segments = 3

    # window: casing over the log ends, sash bars, frosted glass, sill
    trim = P.log_side_material("WindowTrim", "Z")
    cx, cz = (wx0 + wx1) / 2, (wz0 + wz1) / 2
    yt = BACK_Y - 0.065
    box("Casing", (0.13, 0.04, wz1 - wz0 + 0.16), (wx0 - 0.055, yt, cz + 0.02), trim)
    box("Casing", (0.13, 0.04, wz1 - wz0 + 0.16), (wx1 + 0.055, yt, cz + 0.02), trim)
    box("Casing", (wx1 - wx0 + 0.36, 0.045, 0.17), (cx, yt, wz1 + 0.1), trim)
    box("Sill", (wx1 - wx0 + 0.40, 0.26, 0.05), (cx, BACK_Y - 0.06, wz0 - 0.03), trim)
    box("Apron", (wx1 - wx0 + 0.24, 0.035, 0.12), (cx, yt + 0.005, wz0 - 0.11), trim)
    for xx in (wx0 + 0.02, wx1 - 0.02):
        box("Jamb", (0.04, 0.24, wz1 - wz0), (xx, BACK_Y + 0.07, cz), trim)
    box("Head", (wx1 - wx0, 0.24, 0.04), (cx, BACK_Y + 0.07, wz1 - 0.02), trim)
    yb = BACK_Y + 0.12
    box("Bar", (0.04, 0.05, wz1 - wz0), (cx, yb, cz), trim)
    for zz in (wz0 + (wz1 - wz0) / 3, wz0 + 2 * (wz1 - wz0) / 3):
        box("Bar", (wx1 - wx0, 0.05, 0.04), (cx, yb, zz), trim)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(cx, yb + 0.03, cz), rotation=(math.radians(90), 0, 0))
    gl = bpy.context.active_object
    gl.scale = (wx1 - wx0, wz1 - wz0, 1)
    gl.data.materials.append(window_glass_material())
    gl.visible_shadow = False

    snow = simple_material("Snow", (0.85, 0.9, 0.97), rough=0.7)
    snow.node_tree.nodes["Principled BSDF"].inputs["Subsurface Weight"].default_value = 0.3
    box("SillSnow", (wx1 - wx0 + 0.1, 0.25, 0.06), (cx, BACK_Y + 0.42, wz0 - 0.02), snow).modifiers["bevel"].width = 0.025

    # outside: snowy ground, snow-laden spruces, night sky (world)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(2.6, 25, 0.25))
    g = bpy.context.active_object
    g.scale = (80, 46, 1)
    g.data.materials.append(snow)
    pine = simple_material("OutsidePine", (0.008, 0.022, 0.014), rough=0.9)
    for k in range(34):
        px, py = rng.uniform(-8, 16), rng.uniform(9, 42)
        h = rng.uniform(4, 10)
        tiers = 7
        for tier in range(tiers):
            f = tier / tiers
            r_t = h * 0.30 * (1 - f) + 0.15
            zc = h * (0.08 + 0.13 * tier)
            bpy.ops.mesh.primitive_cone_add(vertices=14, radius1=r_t, depth=h * 0.22, location=(px, py, zc))
            bpy.context.active_object.data.materials.append(pine)
            bpy.ops.mesh.primitive_cone_add(vertices=14, radius1=r_t * 0.92, depth=h * 0.12,
                                            location=(px, py, zc + h * 0.06))
            bpy.context.active_object.data.materials.append(snow)

    # braided rug in front of the tree
    P.braided_rug("Rug", center=(-0.1, -1.05))

    emblem_frame()


def emblem_frame():
    """The LeMSIC emblem, framed, on the log wall beside the tree, lit by a small picture light."""
    w_img, h_img = 0.46, 0.46 * 378 / 453
    cx, cz = 1.62, 2.30
    y = BACK_Y - 0.06
    walnut = P.log_side_material("FrameWood", "Z")
    mould = 0.05
    W, H = w_img + 2 * 0.045 + 2 * mould, h_img + 2 * 0.045 + 2 * mould
    for (sx, sz, x, z) in ((W, mould, cx, cz + H / 2 - mould / 2), (W, mould, cx, cz - H / 2 + mould / 2),
                           (mould, H, cx - W / 2 + mould / 2, cz), (mould, H, cx + W / 2 - mould / 2, cz)):
        b = box("FrameMoulding", (sx, 0.035, sz), (x, y - 0.0175, z), walnut)
        b.modifiers["bevel"].width = 0.012
        b.modifiers["bevel"].segments = 3
    mat_board = simple_material("FrameMat", (0.72, 0.68, 0.6), rough=0.9)
    box("FrameMatBoard", (W - 2 * mould, 0.01, H - 2 * mould), (cx, y - 0.008, cz), mat_board)
    img = bpy.data.images.load(EMBLEM, check_existing=True)
    m, nt, out = new_material("EmblemPrint")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    b = principled(nt, (0.2, 0.3, 0.5), rough=0.45)
    b.inputs["Coat Weight"].default_value = 0.5           # behind glass
    b.inputs["Coat Roughness"].default_value = 0.02
    nt.links.new(tex.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    bpy.ops.mesh.primitive_plane_add(size=1, location=(cx, y - 0.0145, cz), rotation=(math.radians(90), 0, 0))
    pic = bpy.context.active_object
    pic.scale = (w_img, h_img, 1)
    pic.data.materials.append(m)
    # brass picture light above the frame
    brass = simple_material("Brass", (0.75, 0.52, 0.22), rough=0.3, metal=1.0)
    lamp = box("PictureLamp", (0.34, 0.05, 0.035), (cx, y - 0.11, cz + H / 2 + 0.07), brass)
    lamp.modifiers["bevel"].width = 0.012
    v, q = tubes([(cx, y - 0.01, cz + H / 2 + 0.07)], [(cx, y - 0.1, cz + H / 2 + 0.07)], [0.007], [0.007], sides=8)
    mesh_object("PictureLampArm", v, q, mat=brass, smooth=True)
    area_light("PictureLight", (cx, y - 0.12, cz + H / 2 + 0.045), (cx, y + 0.1, cz - 0.05), 9, 0.3,
               (1.0, 0.8, 0.55), "room", shape="RECTANGLE", size_y=0.03)


# ---------------------------------------------------------------- fireplace
def build_fireplace():
    stone = P.mortar_material()                        # the backing shows only in the joints
    soot = simple_material("Soot", (0.006, 0.0045, 0.0035), rough=1.0)
    iron = simple_material("Iron", (0.03, 0.03, 0.03), rough=0.45, metal=1.0)
    mantel_mat = P.log_side_material("Mantel", "X")
    depth = 1.35                                       # reaches back into the corner

    W, H = SURROUND_W, MANTEL_Z
    half_open = OPEN_W / 2
    side_w = (W - OPEN_W) / 2
    # hearth slab
    place_box("Hearth", (W + 0.4, 0.62 + depth, HEARTH_H), (0, (depth - 0.62) / 2, HEARTH_H / 2), stone, 0.02)
    # pillars either side of the opening and the lintel above it
    for sgn in (-1, 1):
        place_box("Pillar", (side_w, depth, H - HEARTH_H),
                  (sgn * (half_open + side_w / 2), depth / 2, HEARTH_H + (H - HEARTH_H) / 2), stone, 0.02)
    lintel_h = H - HEARTH_H - OPEN_H
    place_box("Lintel", (OPEN_W + 0.02, depth, lintel_h), (0, depth / 2, H - lintel_h / 2), stone, 0.02)
    # chimney breast up to the ceiling
    place_box("Chimney", (W - 0.3, depth - 0.15, CEILING - H + 0.3), (0, depth / 2 + 0.07, H + (CEILING - H) / 2 + 0.15), stone, 0.02)
    # firebox: soot-black back, sides and floor
    place_box("FireBack", (OPEN_W, 0.06, OPEN_H), (0, OPEN_D, HEARTH_H + OPEN_H / 2), soot, 0.0)
    for sgn in (-1, 1):
        place_box("FireSide", (0.04, OPEN_D, OPEN_H), (sgn * (half_open - 0.02), OPEN_D / 2, HEARTH_H + OPEN_H / 2), soot, 0.0)
    place_box("FireTop", (OPEN_W, OPEN_D, 0.04), (0, OPEN_D / 2, HEARTH_H + OPEN_H - 0.02), soot, 0.0)
    ash = simple_material("Ash", (0.03, 0.028, 0.026), rough=1.0)
    place_box("Ash", (OPEN_W - 0.06, OPEN_D - 0.04, 0.02), (0, OPEN_D / 2, HEARTH_H + 0.01), ash, 0.0)
    # mantel beam
    mb = place_box("MantelBeam", (W + 0.3, 0.34, 0.16), (0, -0.05, H + 0.08), mantel_mat, 0.015)

    # iron grate
    for k in range(5):
        x = -0.28 + k * 0.14
        a, b = fp((x, 0.08, HEARTH_H + 0.08)), fp((x, 0.40, HEARTH_H + 0.08))
        v, q = tubes([a], [b], [0.008], [0.008], sides=8)
        mesh_object("Grate", v, q, mat=iron, smooth=True)
    for sgn in (-1, 1):
        a, b = fp((sgn * 0.32, 0.08, HEARTH_H)), fp((sgn * 0.32, 0.08, HEARTH_H + 0.16))
        v, q = tubes([a], [b], [0.012], [0.012], sides=8)
        mesh_object("GrateLeg", v, q, mat=iron, smooth=True)

    # logs and glowing coals
    coal_mat = ember_material("Coals", (0.015, 0.012, 0.01), 6.0, 2.0, 0.47)
    char = P.charred_log_material()
    logs = [((-0.31, 0.17, 0.30), (0.27, 0.31, 0.31), 0.066),
            ((-0.23, 0.35, 0.31), (0.30, 0.21, 0.30), 0.06),
            ((-0.06, 0.09, 0.385), (0.13, 0.43, 0.425), 0.052),
            ((0.05, 0.12, 0.27), (0.33, 0.40, 0.26), 0.035)]          # a split piece of kindling
    logs = [(fp((a[0], a[1], HEARTH_H + a[2] - 0.12)), fp((b[0], b[1], HEARTH_H + b[2] - 0.12)), r)
            for a, b, r in logs]
    ob = P.logs_mesh("BurningLogs", logs, np.random.default_rng(3), [char, char], sides=20, rings_per_m=30)
    set_lightgroup(ob, "embers")
    centers, sizes = [], []
    for _ in range(110):
        centers.append(fp((rng.uniform(-0.38, 0.38), rng.uniform(0.04, 0.48), HEARTH_H + rng.uniform(0.015, 0.06))))
        sizes.append(rng.uniform(0.012, 0.032))
    tv, tt = icosphere_template(2)
    v = (np.array(centers)[:, None, :] + tv[None] * np.array(sizes)[:, None, None]).reshape(-1, 3)
    q = (tt[None] + (np.arange(len(centers)) * len(tv))[:, None, None]).reshape(-1, 3)
    ob = tri_mesh_object("Coals", v * np.array([1, 1, 0.7]) + np.array([0, 0, 0.012]), q, mat=coal_mat)
    set_lightgroup(ob, "embers")

    # fire light: two flickering sources, plus the steady glow of the coals
    point_light("FireL", fp((-0.17, 0.10, HEARTH_H + 0.36)), 6, (1.0, 0.45, 0.12), 0.12, "fire_l")
    point_light("FireR", fp((0.17, 0.10, HEARTH_H + 0.38)), 6, (1.0, 0.43, 0.11), 0.12, "fire_r")
    point_light("CoalGlow", fp((0.0, 0.18, HEARTH_H + 0.10)), 12, (1.0, 0.30, 0.07), 0.2, "embers")
    # the firelight that reaches into the room and across the tree
    for name, x, group in (("FireSpotL", -0.15, "fire_l"), ("FireSpotR", 0.15, "fire_r")):
        ld = bpy.data.lights.new(name, "SPOT")
        ld.energy = 650
        ld.color = (1.0, 0.47, 0.13)
        ld.spot_size = math.radians(80)
        ld.spot_blend = 1.0
        ld.shadow_soft_size = 0.15
        ob = link(bpy.data.objects.new(name, ld))
        ob.location = fp((x, -0.03, HEARTH_H + 0.42))
        ob.rotation_euler = (Vector((0.2, -0.4, 1.45)) - ob.location).to_track_quat("-Z", "Y").to_euler()
        set_lightgroup(ob, group)

    lay_fieldstone(W, H, depth)
    decorate_mantel(H)
    log_pile()


def lay_fieldstone(W, H, depth):
    """Face the fireplace with real stones: courses on the surround and chimney, a long
    lintel stone over the opening, flagstones on the hearth, soot above the fire."""
    rnd = np.random.default_rng(1964)
    c, s = math.cos(FP_ANGLE), math.sin(FP_ANGLE)
    X, Y, Z = np.array([c, s, 0.0]), np.array([-s, c, 0.0]), np.array([0.0, 0, 1])
    o = lambda x, y, z: np.array(fp((x, y, z)))
    stones = []
    u0 = W / 2 - OPEN_W / 2
    lintel_h = 0.17
    holes = [(u0, 0, u0 + OPEN_W, OPEN_H), (u0 - 0.15, OPEN_H, u0 + OPEN_W + 0.15, OPEN_H + lintel_h)]
    stones += P.lay_stones(rnd, o(-W / 2, 0, HEARTH_H), X, Z, -Y, W, H - HEARTH_H, holes)
    stones.append((o(0, 0.03, HEARTH_H + OPEN_H + lintel_h / 2), np.array([OPEN_W / 2 + 0.14, lintel_h / 2 - 0.006, 0.06]),
                   np.stack([X, Z, -Y], 1), np.array([0, 0, 0.004]), 2))
    stones += P.lay_stones(rnd, o(-W / 2, 0.75, HEARTH_H), -Y, Z, -X, 0.75, H - HEARTH_H)
    cw = W - 0.3
    stones += P.lay_stones(rnd, o(-cw / 2, 0.145, H + 0.16), X, Z, -Y, cw, CEILING + 0.3 - H - 0.16)
    stones += P.lay_stones(rnd, o(-cw / 2, 0.9, H + 0.16), -Y, Z, -X, 0.755, CEILING + 0.3 - H - 0.16)
    hw = W + 0.4
    stones += P.lay_stones(rnd, o(-hw / 2, -0.62, 0), X, Z, -Y, hw, HEARTH_H, course=(0.075, 0.085),
                           length=(0.18, 0.4))
    stones += P.lay_stones(rnd, o(-hw / 2, -0.62, HEARTH_H), X, Y, Z, hw, 0.62, course=(0.2, 0.31),
                           length=(0.24, 0.5), depth=(0.05, 0.06), proud=0.012, gap=0.012)
    P.stone_mesh("Fieldstone", stones, rnd, P.fieldstone_material(),
                 soot_center=o(0, -0.03, HEARTH_H + OPEN_H + 0.04), soot_radius=0.5)


def decorate_mantel(H):
    # stockings hanging from the mantel
    colours = [(0.26, 0.006, 0.012), (0.025, 0.075, 0.27), (0.018, 0.075, 0.03)]    # red, LeMSIC blue, green
    cuff = P.knit_material("Cuff", (0.78, 0.76, 0.70))
    brass = simple_material("HookBrass", (0.7, 0.5, 0.22), rough=0.3, metal=1.0)
    c, s = math.cos(FP_ANGLE), math.sin(FP_ANGLE)
    for k, xloc in enumerate((-0.55, 0.0, 0.55)):
        top = np.array(fp((xloc, -0.25, H - 0.05)))
        P.stocking(f"Stocking{k}", top, (c, s, 0.0), P.knit_material(f"Stocking{k}", colours[k]), cuff, rng)
        v, q = tubes([top + np.array([0, 0, 0.0])], [np.array(fp((xloc, -0.25, H + 0.005)))], [0.004], [0.004], sides=6)
        mesh_object("Hook", v, q, mat=brass, smooth=True)

    # pine garland with berries along the mantel, draping at the ends
    xs = np.linspace(-1.15, 1.15, 70)
    path = [fp((x, -0.14, H + 0.18 - (0.0 if abs(x) < 0.95 else (abs(x) - 0.95) * 1.6))) for x in xs]
    TP, TD, TL = [], [], []
    for p in path:
        for _ in range(6):
            d = np.array([rng.normal(), rng.normal(), rng.normal() * 0.5])
            d /= np.linalg.norm(d)
            TP.append(np.array(p)); TD.append(d); TL.append(rng.uniform(0.06, 0.12))
    v, q, c = needles(np.array(TP), np.array(TD), np.array(TL), spacing=0.006)
    mesh_object("MantelGarland", v, q, colors=c, mat=bpy.data.materials["Needles"])
    berries = [np.array(path[int(i)]) + rng.normal(0, 0.03, 3) for i in rng.integers(0, len(path), 40)]
    v, q = spheres(np.array(berries), 0.011, icosphere_template(2))
    tri_mesh_object("Berries", v, q[:, :3], mat=simple_material("Berry", (0.4, 0.01, 0.015), rough=0.2, coat=1))

    # wreath on the chimney breast
    centre = fp((0, 0.08, H + 0.75))
    TP, TD, TL = [], [], []
    c, s = math.cos(FP_ANGLE), math.sin(FP_ANGLE)
    right = np.array([c, s, 0])
    for k in range(220):
        a = rng.uniform(0, 2 * math.pi)
        rr = 0.22 + rng.normal(0, 0.03)
        p = np.array(centre) + right * rr * math.cos(a) + np.array([0, 0, 1]) * rr * math.sin(a)
        p += np.array([-s, c, 0]) * -0.04                    # stand a little proud of the stone
        tang = -right * math.sin(a) + np.array([0, 0, 1]) * math.cos(a)
        d = tang + rng.normal(0, 0.5, 3)
        d /= np.linalg.norm(d)
        TP.append(p); TD.append(d); TL.append(rng.uniform(0.08, 0.13))
    v, q, col = needles(np.array(TP), np.array(TD), np.array(TL), spacing=0.006)
    mesh_object("Wreath", v, q, colors=col, mat=bpy.data.materials["Needles"])
    bow = simple_material("Bow", (0.30, 0.004, 0.01), rough=0.35, coat=0.6)
    for sgn in (-1, 1):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.06, minor_radius=0.018,
                                         location=Vector(centre) + Vector(right * sgn * 0.06) + Vector((0, 0, -0.22)) + Vector((-s, c, 0)) * -0.08,
                                         rotation=(math.radians(90), math.radians(sgn * 25), FP_ANGLE))
        bpy.context.active_object.scale = (1, 0.6, 1)
        bpy.context.active_object.data.materials.append(bow)
        bpy.ops.object.shade_smooth()


def log_pile():
    bark = bpy.data.materials["Bark"]
    base = fp((1.35, 0.05, 0))
    c, s = math.cos(FP_ANGLE), math.sin(FP_ANGLE)
    along = np.array([-s, c, 0])          # logs point into the wall
    across = np.array([c, s, 0])
    k = 0
    for row, n in enumerate((4, 3, 2)):
        for i in range(n):
            centre = np.array(base) + across * ((i - (n - 1) / 2) * 0.15) + np.array([0, 0, 0.07 + row * 0.125])
            r = rng.uniform(0.06, 0.07)
            a = centre - along * 0.28
            b = centre + along * 0.28
            v, q = tubes([a], [b], [r], [r * 0.95], sides=14)
            mesh_object("Firewood", v, q, mat=bark, smooth=True)
            k += 1


# ---------------------------------------------------------------- camera, lights, render
def setup(scene):
    cam_data = bpy.data.cameras.new("Camera")
    cam_data.lens = LENS
    cam_data.dof.use_dof = True
    cam_data.dof.focus_distance = (Vector((0, -0.55, 1.5)) - CAMERA).length    # focus on the front of the tree
    cam_data.dof.aperture_fstop = 2.0
    cam = link(bpy.data.objects.new("Camera", cam_data))
    cam.location = CAMERA
    cam.rotation_euler = (TARGET - CAMERA).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam

    vl = scene.view_layers[0]
    for name in ("fire_l", "fire_r", "embers", "tree", "room"):
        vl.lightgroups.add(name=name)

    # tree lights (fairy lights, star) twinkle separately from the fire
    for name in ("FairyLights", "Star", "StarGlow"):
        set_lightgroup(bpy.data.objects[name], "tree")

    # moonlight through the window, and a dim bounce fill from the room
    sun = bpy.data.lights.new("Moon", "SUN")
    sun.energy = 1.6
    sun.color = (0.62, 0.74, 1.0)
    sun.angle = math.radians(1.5)
    so = link(bpy.data.objects.new("Moon", sun))
    so.rotation_euler = (Vector((-0.55, -1.0, -0.75))).to_track_quat("-Z", "Y").to_euler()
    set_lightgroup(so, "room")
    wg = area_light("WindowGlow", (2.65, BACK_Y + 0.25, 1.7), (2.2, -1.0, 0.6), 40, 1.2, (0.55, 0.68, 1.0), "room",
                    shape="RECTANGLE", size_y=1.5)
    wg.visible_camera = False
    wg.visible_glossy = False
    area_light("Fill", (0.8, -6.5, 2.6), (0, 0, 1.3), 55, 4.0, (1.0, 0.82, 0.62), "room")
    area_light("TreeKey", (1.6, -3.2, 3.6), (0, 0, 1.6), 70, 1.5, (1.0, 0.85, 0.7), "room")

    world = bpy.data.worlds.new("Night")
    scene.world = world
    nt = world.node_tree
    bg = nt.nodes.get("Background") or nt.nodes.new("ShaderNodeBackground")
    # night sky: lighter towards the horizon
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (0.05, 0.075, 0.16, 1)
    ramp.color_ramp.elements[1].position = 0.45
    ramp.color_ramp.elements[1].color = (0.006, 0.012, 0.035, 1)
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.0
    out = nt.nodes.get("World Output") or nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(bg.outputs[0], out.inputs[0])
    world.lightgroup = "room"

    r = scene.render
    r.engine = "CYCLES"
    r.resolution_x, r.resolution_y = RES
    r.resolution_percentage = 100
    r.film_transparent = False
    c = scene.cycles
    c.device = "CPU"
    c.samples = SAMPLES
    c.use_adaptive_sampling = True
    c.adaptive_threshold = 0.015
    c.use_denoising = True
    c.max_bounces = 8
    c.diffuse_bounces = 4
    c.glossy_bounces = 4
    c.transmission_bounces = 6
    c.sample_clamp_indirect = 6
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = 0.35


# ---------------------------------------------------------------- post: flicker variants
def read_exr(path):
    import OpenEXR
    with OpenEXR.File(path, separate_channels=True) as f:
        layers = {}
        for part in f.parts:                        # one part per pass
            for name, ch in part.channels.items():
                layers[name] = np.asarray(ch.pixels, np.float32)
    passes = {}
    for name, px in layers.items():
        if "." not in name:
            continue
        base, comp = name.rsplit(".", 1)
        base = base.split(".", 1)[-1]               # drop the view layer name
        passes.setdefault(base, {})[comp] = px
    return {k: np.stack([v["R"], v["G"], v["B"]], -1) for k, v in passes.items() if {"R", "G", "B"} <= set(v)}


def blur(img, sigma):
    if sigma <= 0:
        return img
    rad = int(sigma * 3)
    x = np.arange(-rad, rad + 1)
    k = np.exp(-x ** 2 / (2 * sigma ** 2))
    k /= k.sum()
    out = img.copy()
    for axis in (0, 1):
        pad = [(0, 0)] * 3
        pad[axis] = (rad, rad)
        p = np.pad(out, pad, mode="edge")
        acc = np.zeros_like(out)
        for i, w in enumerate(k):
            sl = [slice(None)] * 3
            sl[axis] = slice(i, i + out.shape[axis])
            acc += w * p[tuple(sl)]
        out = acc
    return out


def save_tonemapped(scene, rgb, path):
    h, w, _ = rgb.shape
    img = bpy.data.images.new("tmp", w, h, float_buffer=True, alpha=False)
    rgba = np.concatenate([rgb, np.ones((h, w, 1), np.float32)], -1)[::-1]      # Blender images are bottom-up
    img.pixels.foreach_set(np.ascontiguousarray(rgba, dtype=np.float32).ravel())
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "JPEG"
    scene.render.image_settings.quality = 90
    scene.render.image_settings.color_mode = "RGB"
    img.save_render(path, scene=scene)
    bpy.data.images.remove(img)


def downsample(img, f):
    h, w, c = img.shape
    h2, w2 = h // f, w // f
    return img[:h2 * f, :w2 * f].reshape(h2, f, w2, f, c).mean(axis=(1, 3))


def upsample(img, f, shape):
    out = np.repeat(np.repeat(img, f, axis=0), f, axis=1)
    pad_h, pad_w = shape[0] - out.shape[0], shape[1] - out.shape[1]
    return np.pad(out, ((0, pad_h), (0, pad_w), (0, 0)), mode="edge")


def photo_finish(img):
    """What a camera adds: a soft bloom around bright lights and a gentle vignette."""
    h, w, _ = img.shape
    k = w / 1920
    bright = np.clip(img - 1.2, 0, None)
    small = downsample(bright, 4)
    glow = 0.6 * blur(small, 2.5 * k) + 0.4 * blur(small, 9 * k)
    img = img + 0.22 * blur(upsample(glow, 4, img.shape), 2 * k)
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 * 0.8 + ((yy - h / 2) / (h / 2)) ** 2 * 0.6)
    return img * (1 - 0.32 * np.clip(r, 0, 1.2) ** 2.4)[..., None]


def make_variants(scene, exr_path):
    p = read_exr(exr_path)
    print("  passes:", sorted(p))
    C = p["Combined"]
    FL = blur(p["Combined_fire_l"], 1.2)
    FR = blur(p["Combined_fire_r"], 1.2)
    EM = blur(p["Combined_embers"], 1.2)
    # C already contains the fire at strength 1.0; add or remove some of it
    variants = {
        "cabin.jpg": C,
        "cabin-low.jpg": C - 0.45 * (FL + FR) - 0.15 * EM,
        "cabin-left.jpg": C + 0.40 * FL - 0.05 * FR + 0.08 * EM,
        "cabin-right.jpg": C - 0.05 * FL + 0.40 * FR + 0.08 * EM,
    }
    for name, img in variants.items():
        save_tonemapped(scene, photo_finish(np.clip(img, 0, None)), os.path.join(OUT_DIR, name))
        print("  wrote", name)


# ---------------------------------------------------------------- scene info for the website
def project(scene, cam, co):
    p = world_to_camera_view(scene, cam, Vector(co))
    return [round(p.x, 4), round(1 - p.y, 4)]


def scene_info(scene, spots):
    bpy.context.view_layer.update()
    cam = scene.camera
    right = (cam.matrix_world.to_3x3() @ Vector((1, 0, 0))).normalized()
    hw = OPEN_W / 2
    z0, z1 = HEARTH_H, HEARTH_H + OPEN_H
    info = {
        "width": RES[0], "height": RES[1],
        "note": "all positions are fractions of the image width/height, y from the top",
        "fire": {
            "opening": [project(scene, cam, fp(c)) for c in
                        ((-hw, 0.0, z0), (hw, 0.0, z0), (hw, 0.0, z1), (-hw, 0.0, z1))],
            "bed": [project(scene, cam, fp(c)) for c in ((-0.34, 0.25, z0 + 0.20), (0.34, 0.25, z0 + 0.20))],
            "back": [project(scene, cam, fp(c)) for c in ((-hw, OPEN_D, z0), (hw, OPEN_D, z0),
                                                          (hw, OPEN_D, z1), (-hw, OPEN_D, z1))],
        },
        "window": [project(scene, cam, c) for c in
                   ((WINDOW_X[0], BACK_Y + 0.1, WINDOW_Z[0]), (WINDOW_X[1], BACK_Y + 0.1, WINDOW_Z[0]),
                    (WINDOW_X[1], BACK_Y + 0.1, WINDOW_Z[1]), (WINDOW_X[0], BACK_Y + 0.1, WINDOW_Z[1]))],
        "ornaments": [],
    }
    for s in sorted(spots, key=lambda s: s["day"]):
        c = Vector(s["center"])
        x, y = project(scene, cam, c)
        ex, _ = project(scene, cam, c + right * s["radius"])
        info["ornaments"].append({"day": s["day"], "x": x, "y": y, "r": round(abs(ex - x), 4)})
    with open(os.path.join(OUT_DIR, "scene.json"), "w") as f:
        json.dump(info, f, indent=1)
    with open(os.path.join(OUT_DIR, "scene.js"), "w") as f:      # loadable straight from disk
        f.write("window.CABIN_SCENE = " + json.dumps(info) + ";\n")


def build_cabin(steam=False):
    """The whole room, lit and with the camera set. The steam from Fares' tumbler is left out
    unless asked for: the website animates it on top (cabin_steam.py)."""
    scene = T.reset_scene()
    T.apply_style(TREE_STYLE)
    T.FLOOR_LIFT = 0.03                     # the skirt and presents rest on the braided rug
    T.CAMERA = CAMERA                       # baubles turn to face this camera
    spots = T.build_tree()
    build_room()
    build_fireplace()
    mascot = FARES.build_fares(steam=steam)   # Fares, sitting by the tree sipping from his LeMSIC tumbler
    mascot.location = FARES_AT
    mascot.rotation_euler = (0, 0, math.radians(-34))
    mascot.scale = (1.35, 1.35, 1.35)
    setup(scene)
    return scene, spots


def main():
    t0 = time.time()
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(BUILD_DIR, exist_ok=True)
    scene, spots = build_cabin()
    scene_info(scene, spots)
    print(f"scene built in {time.time() - t0:.0f}s")

    exr = os.path.join(BUILD_DIR, "cabin-preview.exr" if PREVIEW else "cabin.exr")
    scene.render.image_settings.media_type = "MULTI_LAYER_IMAGE"
    scene.render.image_settings.file_format = "OPEN_EXR_MULTILAYER"
    scene.render.image_settings.color_depth = "32"
    scene.render.image_settings.exr_codec = "ZIP"
    scene.render.filepath = exr
    t1 = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"rendered in {time.time() - t1:.0f}s")
    make_variants(scene, exr)


if __name__ == "__main__":
    main()
