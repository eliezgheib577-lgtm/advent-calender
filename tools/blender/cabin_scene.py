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
from lemsic_tree import (box, link, mesh_object, needles, new_material, principled,  # noqa: E402
                         simple_material, tubes, icosphere_template, spheres, tri_mesh_object)

ROOT = os.path.dirname(os.path.dirname(HERE))
OUT_DIR = os.path.join(ROOT, "site", "assets", "cabin")
BUILD_DIR = os.path.join(ROOT, "build")

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

WINDOW_X = (2.05, 3.25)
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
def stone_material():
    m, nt, out = new_material("Stone")
    L = nt.links.new
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = node(nt, "ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1.0, 1.0, 1.35)
    edge = nt.nodes.new("ShaderNodeTexVoronoi")
    edge.feature = "DISTANCE_TO_EDGE"
    edge.inputs["Scale"].default_value = 7.0
    cell = nt.nodes.new("ShaderNodeTexVoronoi")
    cell.inputs["Scale"].default_value = 7.0
    mortar = node(nt, "ShaderNodeMapRange")
    mortar.inputs["From Min"].default_value = 0.0
    mortar.inputs["From Max"].default_value = 0.05
    stone_ramp = nt.nodes.new("ShaderNodeValToRGB")
    stone_ramp.color_ramp.elements[0].color = (0.13, 0.115, 0.10, 1)
    stone_ramp.color_ramp.elements[1].color = (0.36, 0.32, 0.27, 1)
    grain = node(nt, "ShaderNodeTexNoise", Scale=28.0, Detail=8.0)
    mix_grain = nt.nodes.new("ShaderNodeMix")
    mix_grain.data_type = "RGBA"
    mix_grain.blend_type = "MULTIPLY"
    mix_grain.inputs["Factor"].default_value = 0.35
    mix_mortar = nt.nodes.new("ShaderNodeMix")
    mix_mortar.data_type = "RGBA"
    mix_mortar.inputs["A"].default_value = (0.20, 0.19, 0.17, 1)
    height = node(nt, "ShaderNodeMath")
    height.operation = "MULTIPLY_ADD"
    height.inputs[1].default_value = 0.15
    bump = node(nt, "ShaderNodeBump", Strength=0.75, Distance=0.04)
    b = principled(nt, (0.3, 0.28, 0.25), rough=0.88)
    L(tc.outputs["Object"], mp.inputs["Vector"])
    L(mp.outputs[0], edge.inputs["Vector"])
    L(mp.outputs[0], cell.inputs["Vector"])
    L(mp.outputs[0], grain.inputs["Vector"])
    L(edge.outputs["Distance"], mortar.inputs["Value"])
    L(cell.outputs["Color"], stone_ramp.inputs["Fac"])
    L(stone_ramp.outputs["Color"], mix_grain.inputs["A"])
    L(grain.outputs["Color"], mix_grain.inputs["B"])
    L(mortar.outputs[0], mix_mortar.inputs["Factor"])
    L(mix_grain.outputs["Result"], mix_mortar.inputs["B"])
    L(mix_mortar.outputs["Result"], b.inputs["Base Color"])
    L(grain.outputs["Fac"], height.inputs[0])
    L(mortar.outputs[0], height.inputs[2])
    L(height.outputs[0], bump.inputs["Height"])
    L(bump.outputs["Normal"], b.inputs["Normal"])
    L(b.outputs[0], out.inputs["Surface"])
    return m


def log_material(name, light, dark, stretch_axis="X"):
    m, nt, out = new_material(name)
    L = nt.links.new
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (0.5, 14, 14) if stretch_axis == "X" else (14, 0.5, 14)
    noise = node(nt, "ShaderNodeTexNoise", Scale=2.5, Detail=12.0, Roughness=0.62, Distortion=0.6)
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*dark, 1)
    ramp.color_ramp.elements[1].color = (*light, 1)
    bump = node(nt, "ShaderNodeBump", Strength=0.35)
    b = principled(nt, light, rough=0.55)
    b.inputs["Coat Weight"].default_value = 0.15
    L(tc.outputs["Object"], mp.inputs["Vector"])
    L(mp.outputs[0], noise.inputs["Vector"])
    L(noise.outputs["Fac"], ramp.inputs["Fac"])
    L(noise.outputs["Fac"], bump.inputs["Height"])
    L(ramp.outputs["Color"], b.inputs["Base Color"])
    L(bump.outputs["Normal"], b.inputs["Normal"])
    L(b.outputs[0], out.inputs["Surface"])
    return m


def floor_material():
    m, nt, out = new_material("Floor")
    L = nt.links.new
    tc = nt.nodes.new("ShaderNodeTexCoord")
    brick = nt.nodes.new("ShaderNodeTexBrick")
    brick.offset = 0.37
    brick.inputs["Color1"].default_value = (0.20, 0.095, 0.04, 1)
    brick.inputs["Color2"].default_value = (0.13, 0.06, 0.025, 1)
    brick.inputs["Mortar"].default_value = (0.02, 0.01, 0.005, 1)
    brick.inputs["Scale"].default_value = 1.0
    brick.inputs["Mortar Size"].default_value = 0.004
    brick.inputs["Brick Width"].default_value = 2.1
    brick.inputs["Row Height"].default_value = 0.19
    brick.inputs["Bias"].default_value = 0.2
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (0.4, 12, 1)
    grain = node(nt, "ShaderNodeTexNoise", Scale=3.0, Detail=10.0, Distortion=0.4)
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs["Factor"].default_value = 0.55
    b = principled(nt, (0.2, 0.1, 0.05), rough=0.42)
    b.inputs["Coat Weight"].default_value = 0.35
    b.inputs["Coat Roughness"].default_value = 0.25
    bump = node(nt, "ShaderNodeBump", Strength=0.3)
    inv = node(nt, "ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    L(tc.outputs["Object"], brick.inputs["Vector"])
    L(tc.outputs["Object"], mp.inputs["Vector"])
    L(mp.outputs[0], grain.inputs["Vector"])
    L(brick.outputs["Color"], mix.inputs["A"])
    L(grain.outputs["Color"], mix.inputs["B"])
    L(mix.outputs["Result"], b.inputs["Base Color"])
    L(brick.outputs["Fac"], inv.inputs[1])
    L(inv.outputs[0], bump.inputs["Height"])
    L(bump.outputs["Normal"], b.inputs["Normal"])
    L(b.outputs[0], out.inputs["Surface"])
    return m


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


def plaid_material():
    m, nt, out = new_material("Rug")
    L = nt.links.new
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")

    def stripes(axis_out, period, width):
        mod = node(nt, "ShaderNodeMath")
        mod.operation = "PINGPONG"
        mod.inputs[1].default_value = period
        thr = node(nt, "ShaderNodeMath")
        thr.operation = "LESS_THAN"
        thr.inputs[1].default_value = width
        L(axis_out, mod.inputs[0])
        L(mod.outputs[0], thr.inputs[0])
        return thr

    sx, sy = stripes(sep.outputs["X"], 0.16, 0.05), stripes(sep.outputs["Y"], 0.16, 0.05)
    fx, fy = stripes(sep.outputs["X"], 0.16, 0.008), stripes(sep.outputs["Y"], 0.16, 0.008)
    both = node(nt, "ShaderNodeMath")
    both.operation = "ADD"
    fine = node(nt, "ShaderNodeMath")
    fine.operation = "MAXIMUM"
    c1 = nt.nodes.new("ShaderNodeMix")
    c1.data_type = "RGBA"
    c1.inputs["A"].default_value = (0.22, 0.008, 0.012, 1)        # red
    c1.inputs["B"].default_value = (0.02, 0.055, 0.025, 1)        # green
    mixf = node(nt, "ShaderNodeMath")
    mixf.operation = "MULTIPLY"
    mixf.inputs[1].default_value = 0.5
    c2 = nt.nodes.new("ShaderNodeMix")
    c2.data_type = "RGBA"
    c2.inputs["B"].default_value = (0.5, 0.42, 0.25, 1)           # cream lines
    b = principled(nt, (0.2, 0.02, 0.02), rough=0.97)
    b.inputs["Sheen Weight"].default_value = 0.6
    L(tc.outputs["Object"], sep.inputs[0])
    L(sx.outputs[0], both.inputs[0])
    L(sy.outputs[0], both.inputs[1])
    L(both.outputs[0], mixf.inputs[0])
    L(mixf.outputs[0], c1.inputs["Factor"])
    L(fx.outputs[0], fine.inputs[0])
    L(fy.outputs[0], fine.inputs[1])
    L(fine.outputs[0], c2.inputs["Factor"])
    L(c1.outputs["Result"], c2.inputs["A"])
    L(c2.outputs["Result"], b.inputs["Base Color"])
    L(b.outputs[0], out.inputs["Surface"])
    return m


def knit_material(name, color):
    m, nt, out = new_material(name)
    L = nt.links.new
    tc = nt.nodes.new("ShaderNodeTexCoord")
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.inputs["Scale"].default_value = 60
    wave.bands_direction = "Z"
    bump = node(nt, "ShaderNodeBump", Strength=0.5)
    b = principled(nt, color, rough=0.95)
    b.inputs["Sheen Weight"].default_value = 0.8
    L(tc.outputs["Object"], wave.inputs["Vector"])
    L(wave.outputs["Fac"], bump.inputs["Height"])
    L(bump.outputs["Normal"], b.inputs["Normal"])
    L(b.outputs[0], out.inputs["Surface"])
    return m


# ---------------------------------------------------------------- room
def log_wall_x(y, x0, x1, z0, z1, mat, gaps=()):
    """A wall of horizontal logs running along X at depth y (logs centred just behind y)."""
    A, B, ra, rb = [], [], [], []
    r = 0.125
    z = z0 + r
    while z < z1 + r:
        spans = [(x0, x1)]
        for gx0, gx1, gz0, gz1 in gaps:
            if gz0 - r * 0.6 < z < gz1 + r * 0.6:
                spans = [(a, b) for a0, b0 in spans for a, b in ((a0, min(b0, gx0)), (max(a0, gx1), b0)) if b - a > 0.05]
        for a, b in spans:
            rr = r * rng.uniform(0.92, 1.05)
            yy = y + rr * 0.85
            A.append((a, yy, z)); B.append((b, yy, z)); ra.append(rr); rb.append(rr * rng.uniform(0.93, 1.0))
        z += 2 * r * 0.93
    v, q = tubes(np.array(A), np.array(B), np.array(ra), np.array(rb), sides=24)
    return mesh_object("LogWall", v, q, mat=mat, smooth=True)


def log_wall_y(x, y0, y1, z0, z1, mat):
    A, B, ra, rb = [], [], [], []
    r = 0.125
    z = z0 + r
    while z < z1 + r:
        rr = r * rng.uniform(0.92, 1.05)
        xx = x - rr * 0.85
        A.append((xx, y0, z)); B.append((xx, y1, z)); ra.append(rr); rb.append(rr)
        z += 2 * r * 0.93
    v, q = tubes(np.array(A), np.array(B), np.array(ra), np.array(rb), sides=24)
    return mesh_object("LogWallLeft", v, q, mat=mat, smooth=True)


def build_room():
    logs = log_material("Logs", (0.42, 0.21, 0.08), (0.17, 0.075, 0.025))
    logs_y = log_material("LogsY", (0.42, 0.21, 0.08), (0.17, 0.075, 0.025), stretch_axis="Y")
    chink = simple_material("Chinking", (0.42, 0.38, 0.31), rough=0.95)
    gaps = [(WINDOW_X[0], WINDOW_X[1], WINDOW_Z[0], WINDOW_Z[1])]
    log_wall_x(BACK_Y, LEFT_X, RIGHT_X, 0, CEILING + 0.3, logs, gaps)
    log_wall_y(LEFT_X, -8, BACK_Y + 0.3, 0, CEILING + 0.3, logs_y)
    # chinking behind the logs
    bpy.ops.mesh.primitive_plane_add(size=1, location=((LEFT_X + RIGHT_X) / 2, BACK_Y + 0.2, CEILING / 2),
                                     rotation=(math.radians(90), 0, 0))
    pl = bpy.context.active_object
    pl.scale = (RIGHT_X - LEFT_X, CEILING, 1)
    pl.data.materials.append(chink)
    # the chinking needs a hole for the window: cut it with a boolean
    hole = place_box("WindowHole", (WINDOW_X[1] - WINDOW_X[0], 0.6, WINDOW_Z[1] - WINDOW_Z[0]),
                     ((WINDOW_X[0] + WINDOW_X[1]) / 2, BACK_Y + 0.2, (WINDOW_Z[0] + WINDOW_Z[1]) / 2),
                     chink, in_fireplace=False)
    boo = pl.modifiers.new("hole", "BOOLEAN")
    boo.object = hole
    boo.operation = "DIFFERENCE"
    hole.hide_render = True
    hole.hide_viewport = True
    bpy.ops.mesh.primitive_plane_add(size=1, location=(LEFT_X - 0.2, -3, CEILING / 2), rotation=(0, math.radians(90), 0))
    pl = bpy.context.active_object
    pl.scale = (CEILING, 12, 1)
    pl.data.materials.append(chink)

    # floor
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0.6, -3.2, 0))
    fl = bpy.context.active_object
    fl.scale = (RIGHT_X - LEFT_X + 1, 10, 1)
    fl.data.materials.append(floor_material())

    # ceiling planks + beams
    beam_mat = log_material("Beams", (0.30, 0.15, 0.06), (0.10, 0.045, 0.015), stretch_axis="Y")
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0.6, -3.2, CEILING + 0.25), rotation=(math.radians(180), 0, 0))
    ce = bpy.context.active_object
    ce.scale = (RIGHT_X - LEFT_X + 1, 10, 1)
    ce.data.materials.append(log_material("CeilingBoards", (0.26, 0.13, 0.05), (0.09, 0.04, 0.015)))
    for x in np.arange(-3.2, RIGHT_X, 1.6):
        b = box("Beam", (0.24, 10, 0.28), (x, -3.2, CEILING + 0.1), beam_mat)
        b.modifiers["bevel"].width = 0.02

    # window: frame, mullions, sill
    frame = log_material("WindowFrame", (0.30, 0.15, 0.06), (0.12, 0.055, 0.02))
    wx0, wx1 = WINDOW_X
    wz0, wz1 = WINDOW_Z
    cx, cz = (wx0 + wx1) / 2, (wz0 + wz1) / 2
    y = BACK_Y + 0.12
    box("Frame", (wx1 - wx0 + 0.16, 0.18, 0.08), (cx, y, wz1 + 0.04), frame)
    box("Frame", (wx1 - wx0 + 0.16, 0.18, 0.08), (cx, y, wz0 - 0.04), frame)
    box("Frame", (0.08, 0.18, wz1 - wz0), (wx0 - 0.04, y, cz), frame)
    box("Frame", (0.08, 0.18, wz1 - wz0), (wx1 + 0.04, y, cz), frame)
    box("Mullion", (0.045, 0.06, wz1 - wz0), (cx, y + 0.05, cz), frame)
    for zz in (wz0 + (wz1 - wz0) / 3, wz0 + 2 * (wz1 - wz0) / 3):
        box("Mullion", (wx1 - wx0, 0.06, 0.045), (cx, y + 0.05, zz), frame)
    box("Sill", (wx1 - wx0 + 0.36, 0.30, 0.06), (cx, BACK_Y - 0.02, wz0 - 0.08), frame)
    snow = simple_material("Snow", (0.85, 0.9, 0.97), rough=0.7)
    snow.node_tree.nodes["Principled BSDF"].inputs["Subsurface Weight"].default_value = 0.3

    # outside: snowy ground, pines, night sky (world)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(2.6, 25, 0.25))
    g = bpy.context.active_object
    g.scale = (80, 46, 1)
    g.data.materials.append(snow)
    moon = simple_material("MoonDisc", (0, 0, 0), emit=(0.85, 0.9, 1.0), emit_strength=6.0)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.5, location=(26.5, 60, 6.9))
    bpy.context.active_object.data.materials.append(moon)
    bpy.context.active_object.visible_shadow = False
    pine = simple_material("OutsidePine", (0.01, 0.03, 0.02), rough=0.9)
    for k in range(26):
        px, py = rng.uniform(-8, 14), rng.uniform(11, 40)
        h = rng.uniform(3, 8)
        for tier in range(4):
            r = h * 0.28 * (1 - tier * 0.2)
            bpy.ops.mesh.primitive_cone_add(vertices=10, radius1=r, depth=h * 0.45,
                                            location=(px, py, h * (0.2 + tier * 0.2)))
            c = bpy.context.active_object
            c.data.materials.append(pine)
            bpy.ops.mesh.primitive_cone_add(vertices=10, radius1=r * 0.7, depth=h * 0.12,
                                            location=(px, py, h * (0.2 + tier * 0.2) + h * 0.17))
            bpy.context.active_object.data.materials.append(snow)

    # rug in front of the tree
    bpy.ops.mesh.primitive_plane_add(size=1, location=(-0.1, -1.55, 0.006))
    rug = bpy.context.active_object
    rug.scale = (3.4, 2.4, 1)
    rug.data.materials.append(plaid_material())
    sol = rug.modifiers.new("thick", "SOLIDIFY")
    sol.thickness = 0.012
    bev = rug.modifiers.new("bevel", "BEVEL")
    bev.width = 0.006


# ---------------------------------------------------------------- fireplace
def build_fireplace():
    stone = stone_material()
    soot = simple_material("Soot", (0.006, 0.0045, 0.0035), rough=1.0)
    iron = simple_material("Iron", (0.03, 0.03, 0.03), rough=0.45, metal=1.0)
    mantel_mat = log_material("Mantel", (0.24, 0.11, 0.04), (0.07, 0.03, 0.01))
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
    log_mat = ember_material("BurningLog", (0.02, 0.012, 0.008), 9.0, 1.4, 0.58)
    coal_mat = ember_material("Coals", (0.015, 0.012, 0.01), 6.0, 2.0, 0.47)
    logs = [((-0.30, 0.18, 0.30), (0.26, 0.30, 0.31), 0.065),
            ((-0.22, 0.34, 0.31), (0.30, 0.22, 0.30), 0.06),
            ((-0.05, 0.10, 0.38), (0.12, 0.42, 0.42), 0.055)]
    for a, b, r in logs:
        A = fp((a[0], a[1], HEARTH_H + a[2] - 0.12))
        B = fp((b[0], b[1], HEARTH_H + b[2] - 0.12))
        v, q = tubes([A], [B], [r], [r * 0.9], sides=16)
        ob = mesh_object("Log", v, q, mat=log_mat, smooth=True)
        set_lightgroup(ob, "embers")
    centers = []
    for _ in range(70):
        centers.append(fp((rng.uniform(-0.36, 0.36), rng.uniform(0.06, 0.46), HEARTH_H + rng.uniform(0.02, 0.07))))
    v, q = spheres(np.array(centers), 0.028, icosphere_template(2))
    ob = tri_mesh_object("Coals", v * np.array([1, 1, 0.75]) + np.array([0, 0, 0.01]), q[:, :3], mat=coal_mat)
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

    decorate_mantel(H)
    log_pile()


def stocking_profile():
    pts = [(-0.07, 0.0), (0.07, 0.0), (0.07, -0.26), (0.09, -0.30), (0.16, -0.33), (0.21, -0.37),
           (0.21, -0.42), (0.16, -0.45), (0.04, -0.45), (-0.04, -0.42), (-0.07, -0.36)]
    return pts


def decorate_mantel(H):
    # stockings hanging from the mantel
    colours = [(0.30, 0.004, 0.01), (0.03, 0.10, 0.36), (0.02, 0.10, 0.035)]    # red, LeMSIC blue, green
    cuff = knit_material("Cuff", (0.80, 0.78, 0.72))
    for k, xloc in enumerate((-0.55, 0.0, 0.55)):
        mat = knit_material(f"Stocking{k}", colours[k])
        prof = stocking_profile()
        verts = [(x, -0.03, z) for x, z in prof] + [(x, 0.03, z) for x, z in prof]
        n = len(prof)
        faces = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
        faces += [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
        me = bpy.data.meshes.new("Stocking")
        me.from_pydata(verts, [], faces)
        me.update()
        ob = link(bpy.data.objects.new("Stocking", me))
        ob.data.materials.append(mat)
        sub = ob.modifiers.new("sub", "SUBSURF")
        sub.levels = sub.render_levels = 2
        top = fp((xloc, -0.2, H - 0.06))
        ob.location = top
        ob.rotation_euler = (0, 0, FP_ANGLE)
        c = box("Cuff", (0.18, 0.075, 0.09), fp((xloc, -0.2, H - 0.05)), cuff, FP_ANGLE)
        c.modifiers["bevel"].width = 0.025
        c.modifiers["bevel"].segments = 4

    # pine garland with berries along the mantel, draping at the ends
    xs = np.linspace(-1.15, 1.15, 70)
    path = [fp((x, -0.14, H + 0.18 - (0.0 if abs(x) < 0.95 else (abs(x) - 0.95) * 1.6))) for x in xs]
    P, D, Lt = [], [], []
    for p in path:
        for _ in range(6):
            d = np.array([rng.normal(), rng.normal(), rng.normal() * 0.5])
            d /= np.linalg.norm(d)
            P.append(np.array(p)); D.append(d); Lt.append(rng.uniform(0.06, 0.12))
    v, q, c = needles(np.array(P), np.array(D), np.array(Lt), spacing=0.006)
    mesh_object("MantelGarland", v, q, colors=c, mat=bpy.data.materials["Needles"])
    berries = [np.array(path[int(i)]) + rng.normal(0, 0.03, 3) for i in rng.integers(0, len(path), 40)]
    v, q = spheres(np.array(berries), 0.011, icosphere_template(2))
    tri_mesh_object("Berries", v, q[:, :3], mat=simple_material("Berry", (0.4, 0.01, 0.015), rough=0.2, coat=1))

    # wreath on the chimney breast
    centre = fp((0, -0.02, H + 0.75))
    P, D, Lt = [], [], []
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
        P.append(p); D.append(d); Lt.append(rng.uniform(0.08, 0.13))
    v, q, col = needles(np.array(P), np.array(D), np.array(Lt), spacing=0.006)
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
    img.pixels.foreach_set(np.ascontiguousarray(rgba).ravel())
    scene.render.image_settings.media_type = "IMAGE"
    scene.render.image_settings.file_format = "JPEG"
    scene.render.image_settings.quality = 90
    scene.render.image_settings.color_mode = "RGB"
    img.save_render(path, scene=scene)
    bpy.data.images.remove(img)


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
        save_tonemapped(scene, np.clip(img, 0, None), os.path.join(OUT_DIR, name))
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


def main():
    t0 = time.time()
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(BUILD_DIR, exist_ok=True)
    scene = T.reset_scene()
    T.CAMERA = CAMERA                       # baubles turn to face this camera
    spots = T.build_tree()
    build_room()
    build_fireplace()
    setup(scene)
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
