"""The cabin's front door at night, and the door opening (Blender, Cycles).

Students arrive here: snow, a lantern, glowing windows, a carved LeMSIC sign over
the door. When their LeMSIC ID checks out, the door swings open and warm light
spills onto the snow, then the website carries them inside.

Run:  python tools/blender/cabin_door.py [--preview]

Writes (into site/assets/door/):
  door.jpg              the closed door, full frame
  open-00.jpg ...       the door opening (only the part of the frame that changes)
  door.json / door.js   where the opening frames go, and where the doorway is
"""
import json
import math
import os
import sys
import time

import numpy as np
import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lemsic_tree as T  # noqa: E402
import cabin_props as P  # noqa: E402
from lemsic_tree import box, link, mesh_object, new_material, principled, simple_material, tubes, needles  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
OUT_DIR = os.path.join(ROOT, "site", "assets", "door")
BUILD_DIR = os.path.join(ROOT, "build", "door")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
PREVIEW = "--preview" in ARGS
RES = (960, 540) if PREVIEW else (1920, 1080)
SAMPLES = 32 if PREVIEW else 96
FRAMES = (int(os.environ.get("DOOR_FRAMES", 6)) if PREVIEW else 24)
rng = np.random.default_rng(11)

CAMERA = Vector((0.0, -7.8, 1.65))
TARGET = Vector((0.0, 0.0, 2.05))
DOOR_W, DOOR_H, SILL = 1.04, 2.05, 0.32          # door leaf, and the threshold height
WINDOWS = [(-2.45, -1.45), (1.45, 2.45)]
WIN_Z = (1.05, 2.15)


def log_facade():
    side = P.log_side_material("FacadeLogs", "X")
    endg = P.end_grain_material()
    r = 0.15
    pitch = 2 * r + 0.024
    logs = []
    z = SILL + r - 0.02
    hw = DOOR_W / 2 + 0.07
    while z < 3.25:
        spans = [(-4.6, 4.6)]
        cuts = []
        if z < SILL + DOOR_H + 0.12:
            cuts.append((-hw, hw))
        if WIN_Z[0] - 0.1 < z < WIN_Z[1] + 0.1:
            cuts += [(a - 0.07, b + 0.07) for a, b in WINDOWS]
        for c0, c1 in cuts:
            spans = [(a, b) for s0, s1 in spans for a, b in ((s0, min(s1, c0)), (max(s0, c1), s1)) if b - a > 0.05]
        for a, b in spans:
            rr = r * rng.uniform(0.92, 1.06)
            logs.append(((a, rr * 0.75, z), (b, rr * 0.75, z), rr))
        z += pitch
    P.logs_mesh("Facade", logs, rng, [side, endg])
    chink = simple_material("ChinkingOut", (0.2, 0.19, 0.17), rough=0.95)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0.1, 1.8), rotation=(math.radians(90), 0, 0))
    pl = bpy.context.active_object
    pl.scale = (9.2, 3.6, 1)
    pl.data.materials.append(chink)
    holes = [((DOOR_W + 0.02, 1.0, DOOR_H + 0.1), (0, 0.1, SILL + DOOR_H / 2))]
    holes += [((b - a, 1.0, WIN_Z[1] - WIN_Z[0]), ((a + b) / 2, 0.1, sum(WIN_Z) / 2)) for a, b in WINDOWS]
    for k, (size, loc) in enumerate(holes):
        hole = box(f"Hole{k}", size, loc, chink)
        boo = pl.modifiers.new(f"hole{k}", "BOOLEAN")
        boo.object = hole
        boo.operation = "DIFFERENCE"
        hole.hide_render = hole.hide_viewport = True
    # fieldstone foundation along the bottom of the wall
    stones = P.lay_stones(rng, (-4.6, -0.02, -0.05), (1, 0, 0), (0, 0, 1), (0, -1, 0), 9.2, SILL + 0.05,
                          course=(0.12, 0.2), length=(0.2, 0.42), holes=[(4.6 - 0.75, 0, 4.6 + 0.75, 1)])
    P.stone_mesh("Foundation", stones, rng, P.fieldstone_material())


def roof():
    wood = P.log_side_material("Eave", "X")
    snow = snow_material()
    # a pitched roof rising away from us: boards, rafter tails, a thick load of snow, icicles
    pitch = math.radians(26)
    up = np.array([0, math.cos(pitch), math.sin(pitch)])
    front = np.array([0, -1.0, 3.3])                       # bottom front edge of the eave
    L = 5.0
    c = front + up * (L / 2)
    e = box("Roof", (9.6, L, 0.12), tuple(c + np.array([0, 0, 0.06])), wood)
    e.rotation_euler = (pitch, 0, 0)
    for x in np.arange(-4.5, 4.7, 0.6):
        rt = box("Rafter", (0.1, 1.0, 0.15), tuple(front + up * 0.5 + np.array([x, 0, -0.04])), wood)
        rt.rotation_euler = (pitch, 0, 0)
    s = box("RoofSnow", (9.9, L + 0.15, 0.3), tuple(c + np.array([0, -0.05, 0.26])), snow)
    s.rotation_euler = (pitch, 0, 0)
    s.modifiers["bevel"].width = 0.12
    s.modifiers["bevel"].segments = 6
    sub = s.modifiers.new("smooth", "SUBSURF")
    sub.subdivision_type = "SIMPLE"
    sub.levels = sub.render_levels = 5
    tex = bpy.data.textures.new("SnowLumps", "CLOUDS")
    tex.noise_scale = 0.45
    dsp = s.modifiers.new("lumps", "DISPLACE")
    dsp.texture = tex
    dsp.strength = 0.09
    dsp.texture_coords = "GLOBAL"
    ice = simple_material("Ice", (0.8, 0.9, 1.0), rough=0.05)
    ice.node_tree.nodes["Principled BSDF"].inputs["Transmission Weight"].default_value = 0.9
    for x in rng.uniform(-4.4, 4.4, 70):
        Li = rng.uniform(0.04, 0.32) * (rng.random() < 0.8) + 0.02
        bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=rng.uniform(0.008, 0.02), radius2=0.0005, depth=Li,
                                        location=(x, -1.02, 3.26 - Li / 2), rotation=(math.radians(180), 0, 0))
        bpy.context.active_object.data.materials.append(ice)


def snow_material():
    if "SnowOut" in bpy.data.materials:
        return bpy.data.materials["SnowOut"]
    m, nt, out = new_material("SnowOut")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = 180.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.15
    b = principled(nt, (0.82, 0.86, 0.92), rough=0.55)
    b.inputs["Subsurface Weight"].default_value = 0.4
    b.inputs["Subsurface Radius"].default_value = (0.4, 0.5, 0.7)
    b.inputs["Specular IOR Level"].default_value = 0.6
    nt.links.new(tc.outputs["Object"], n.inputs["Vector"])
    nt.links.new(n.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    return m


def ground():
    snow = snow_material()
    xs = np.linspace(-14, 14, 281)
    ys = np.linspace(-14, 30, 331)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    Z = np.zeros_like(X)
    for _ in range(10):
        f = rng.normal(0, 0.6, 2)
        Z += np.sin(X * f[0] + Y * f[1] + rng.uniform(0, 6)) * rng.uniform(0.02, 0.07)
    Z += 0.12 * np.exp(-((Y - 0.2) ** 2) / 0.3) * (np.abs(X) > 0.9)     # drifts against the wall
    Z -= 0.12 * np.exp(-((X) ** 2) / 0.35) * (Y < 0)                    # a trodden path to the door
    Z += SILL - 0.16
    Z[:, ys > 0.3] -= 1.0                                               # under the cabin
    V = np.stack([X, Y, Z], -1).reshape(-1, 3)
    nx, ny = len(xs), len(ys)
    q = [(i * ny + j, (i + 1) * ny + j, (i + 1) * ny + j + 1, i * ny + j + 1) for i in range(nx - 1) for j in range(ny - 1)]
    mesh_object("Snow", V, np.array(q), mat=snow, smooth=True)
    # stone step at the door
    stones = [(np.array([0.0, -0.32, SILL - 0.12]), np.array([0.62, 0.28, 0.12]), np.eye(3), np.zeros(3), 3)]
    P.stone_mesh("Step", stones, rng, bpy.data.materials["Fieldstone"])


def door():
    """The door leaf on a hinge (an empty at its left edge), so it can swing inwards."""
    hinge = bpy.data.objects.new("Hinge", None)
    link(hinge)
    hinge.location = (-DOOR_W / 2, 0.05, SILL)
    planks = P.log_side_material("DoorPlanks", "Z")
    iron = simple_material("WroughtIron", (0.02, 0.02, 0.02), rough=0.55, metal=1.0)
    n = 6
    w = DOOR_W / n
    for k in range(n):
        p = box("Plank", (w - 0.003, 0.06, DOOR_H), (w * (k + 0.5), 0, DOOR_H / 2), planks)
        p.modifiers["bevel"].width = 0.008
        p.parent = hinge
    for zz in (0.35, DOOR_H - 0.35):
        st = box("Strap", (0.78, 0.012, 0.055), (0.39, -0.036, zz), iron)
        st.parent = hinge
        bpy.ops.mesh.primitive_cylinder_add(radius=0.04, depth=0.012, location=(0.78, -0.036, zz),
                                            rotation=(math.radians(90), 0, 0))
        c = bpy.context.active_object
        c.data.materials.append(iron)
        c.parent = hinge
        for x in np.linspace(0.08, 0.7, 5):
            bpy.ops.mesh.primitive_uv_sphere_add(radius=0.011, location=(x, -0.043, zz))
            b = bpy.context.active_object
            b.data.materials.append(iron)
            b.parent = hinge
    bpy.ops.mesh.primitive_torus_add(major_radius=0.055, minor_radius=0.009, location=(DOOR_W - 0.16, -0.07, 1.0),
                                     rotation=(math.radians(90), 0, 0))
    ring = bpy.context.active_object
    ring.data.materials.append(iron)
    ring.parent = hinge
    # a wreath on the door
    TP, TD, TL = [], [], []
    centre = np.array([DOOR_W / 2, -0.08, 1.45])
    for k in range(260):
        a = rng.uniform(0, 2 * math.pi)
        rr = 0.2 + rng.normal(0, 0.03)
        p = centre + np.array([rr * math.cos(a), 0, rr * math.sin(a)])
        tang = np.array([-math.sin(a), 0, math.cos(a)])
        d = tang + rng.normal(0, 0.5, 3)
        d /= np.linalg.norm(d)
        TP.append(p); TD.append(d); TL.append(rng.uniform(0.08, 0.13))
    v, q, col = needles(np.array(TP), np.array(TD), np.array(TL), spacing=0.005)
    wr = mesh_object("Wreath", v, q, colors=col, mat=bpy.data.materials["Needles"])
    wr.parent = hinge
    berries = [centre + np.array([0.2 * math.cos(a), -0.03, 0.2 * math.sin(a)]) + rng.normal(0, 0.02, 3)
               for a in rng.uniform(0, 2 * math.pi, 30)]
    bv, bq = T.spheres(np.array(berries), 0.012, T.icosphere_template(2))
    be = T.tri_mesh_object("Berries", bv, bq[:, :3], mat=simple_material("BerryRed", (0.35, 0.01, 0.015), rough=0.2, coat=1))
    be.parent = hinge
    return hinge


def trim_and_sign():
    trim = P.log_side_material("DoorTrim", "Z")
    hw = DOOR_W / 2
    box("Jamb", (0.14, 0.2, DOOR_H + 0.1), (-hw - 0.07, -0.02, SILL + DOOR_H / 2), trim)
    box("Jamb", (0.14, 0.2, DOOR_H + 0.1), (hw + 0.07, -0.02, SILL + DOOR_H / 2), trim)
    box("Lintel", (DOOR_W + 0.5, 0.24, 0.2), (0, -0.04, SILL + DOOR_H + 0.1), trim)
    box("Threshold", (DOOR_W + 0.2, 0.3, 0.05), (0, -0.05, SILL - 0.02), trim)
    # the LeMSIC sign over the door: dark wood, raised off-white letters, lit by a small lamp
    board = P.log_side_material("SignBoard", "X")
    sz = SILL + DOOR_H + 0.46
    sb = box("Sign", (1.95, 0.06, 0.48), (0, -0.16, sz), board)
    sb.modifiers["bevel"].width = 0.03
    sb.modifiers["bevel"].segments = 3
    paint = simple_material("SignPaint", (0.86, 0.84, 0.78), rough=0.45)
    curve = bpy.data.curves.new("SignText", "FONT")
    curve.body = "LeMSIC"
    curve.size = 0.34
    curve.extrude = 0.012
    curve.bevel_depth = 0.002
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    txt = link(bpy.data.objects.new("SignText", curve))
    txt.location = (0, -0.205, sz)
    txt.rotation_euler = (math.radians(90), 0, 0)
    txt.data.materials.append(paint)
    iron = bpy.data.materials["WroughtIron"]
    for x in (-0.75, 0.75):
        v, q = tubes([(x, -0.16, sz + 0.24)], [(x, -0.02, sz + 0.4)], [0.008], [0.008], sides=6)
        mesh_object("SignChain", v, q, mat=iron, smooth=True)
    # gooseneck lamp lighting the sign
    v, q = tubes([(0, -0.02, sz + 0.42), (0, -0.25, sz + 0.5)], [(0, -0.25, sz + 0.5), (0, -0.42, sz + 0.42)],
                 [0.012, 0.012], [0.012, 0.012], sides=8)
    mesh_object("SignLampArm", v, q, mat=iron, smooth=True)
    shade = box("SignLampShade", (0.22, 0.12, 0.06), (0, -0.45, sz + 0.4), iron)
    shade.modifiers["bevel"].width = 0.02
    ld = bpy.data.lights.new("SignLamp", "SPOT")
    ld.energy = 40
    ld.color = (1.0, 0.86, 0.7)
    ld.spot_size = math.radians(95)
    ld.spot_blend = 0.6
    ld.shadow_soft_size = 0.05
    lo = link(bpy.data.objects.new("SignLamp", ld))
    lo.location = (0, -0.46, sz + 0.36)
    lo.rotation_euler = (Vector((0, -0.2, sz)) - Vector((0, -0.46, sz + 0.36))).to_track_quat("-Z", "Y").to_euler()


def windows():
    trim = P.log_side_material("WinTrim", "Z")
    glass = simple_material("WinGlass", (0.9, 0.9, 0.9), rough=0.02)
    glass.node_tree.nodes["Principled BSDF"].inputs["Transmission Weight"].default_value = 1.0
    warm = simple_material("RoomGlow", (0, 0, 0), emit=(1.0, 0.48, 0.17), emit_strength=0.75)
    curtain = simple_material("Curtain", (0.5, 0.12, 0.08), rough=0.9)
    curtain.node_tree.nodes["Principled BSDF"].inputs["Subsurface Weight"].default_value = 0.5
    snow = snow_material()
    z0, z1 = WIN_Z
    for a, b in WINDOWS:
        cx, cz, w, h = (a + b) / 2, (z0 + z1) / 2, b - a, z1 - z0
        for (sx, sz, x, z) in ((w + 0.2, 0.1, cx, z1 + 0.05), (w + 0.3, 0.08, cx, z0 - 0.04),
                               (0.1, h, a - 0.05, cz), (0.1, h, b + 0.05, cz)):
            box("WinFrame", (sx, 0.18, sz), (x, -0.03, z), trim)
        box("WinBar", (0.04, 0.05, h), (cx, 0.02, cz), trim)
        box("WinBar", (w, 0.05, 0.04), (cx, 0.02, cz), trim)
        bpy.ops.mesh.primitive_plane_add(size=1, location=(cx, 0.05, cz), rotation=(math.radians(90), 0, 0))
        g = bpy.context.active_object
        g.scale = (w, h, 1)
        g.data.materials.append(glass)
        bpy.ops.mesh.primitive_plane_add(size=1, location=(cx, 0.6, cz), rotation=(math.radians(90), 0, 0))
        r = bpy.context.active_object
        r.scale = (w + 0.6, h + 0.6, 1)
        r.data.materials.append(warm)
        for side in (-1, 1):                         # curtains drawn back to each side
            cu = box("Curtain", (w * 0.22, 0.02, h + 0.1), (cx + side * (w / 2 - w * 0.09), 0.22, cz), curtain)
            cu.modifiers["bevel"].width = 0.008
        s = box("SillSnow", (w + 0.3, 0.2, 0.06), (cx, -0.12, z0 - 0.0), snow)
        s.modifiers["bevel"].width = 0.025


def lantern():
    iron = bpy.data.materials["WroughtIron"]
    x, z = DOOR_W / 2 + 0.42, SILL + 1.75
    box("LanternArm", (0.03, 0.2, 0.03), (x, -0.1, z + 0.22), iron)
    box("LanternTop", (0.18, 0.18, 0.04), (x, -0.22, z + 0.15), iron)
    box("LanternBase", (0.16, 0.16, 0.03), (x, -0.22, z - 0.12), iron)
    flame = simple_material("LanternGlass", (0, 0, 0), emit=(1.0, 0.62, 0.28), emit_strength=9.0)
    g = box("LanternGlass", (0.13, 0.13, 0.24), (x, -0.22, z), flame)
    for dx in (-0.07, 0.07):
        for dy in (-0.07, 0.07):
            box("LanternPost", (0.012, 0.012, 0.26), (x + dx, -0.22 + dy, z), iron)
    ld = bpy.data.lights.new("Lantern", "POINT")
    ld.energy = 45
    ld.color = (1.0, 0.62, 0.3)
    ld.shadow_soft_size = 0.06
    lo = link(bpy.data.objects.new("Lantern", ld))
    lo.location = (x, -0.3, z)


def interior_glow():
    """What you see through the open door: warm light and the out-of-focus sparkle of the tree's lights."""
    warm = simple_material("Inside", (0.25, 0.12, 0.05), rough=0.8)
    box("InsideFloor", (3, 4, 0.05), (0, 2.1, SILL - 0.03), P.plank_material())
    box("InsideBack", (3, 0.1, 3), (0, 4.0, SILL + 1.5), warm)
    box("InsideL", (0.1, 4, 3), (-1.4, 2.0, SILL + 1.5), warm)
    box("InsideR", (0.1, 4, 3), (1.4, 2.0, SILL + 1.5), warm)
    bulbs = np.stack([rng.uniform(-0.9, 0.9, 90), rng.uniform(3.0, 3.6, 90), SILL + rng.uniform(0.3, 2.4, 90)], 1)
    bv, bq = T.spheres(bulbs, 0.012, T.icosphere_template(1))
    T.tri_mesh_object("InsideLights", bv, bq[:, :3],
                      mat=simple_material("InsideBulb", (1, 0.8, 0.5), emit=(1.0, 0.65, 0.3), emit_strength=40))
    for loc, power in (((0, 2.6, SILL + 2.2), 320), ((-0.5, 3.4, SILL + 0.6), 150)):
        ld = bpy.data.lights.new("FireInside", "POINT")
        ld.energy = power
        ld.color = (1.0, 0.55, 0.22)
        ld.shadow_soft_size = 0.4
        link(bpy.data.objects.new("FireInside", ld)).location = loc


def background():
    snow = snow_material()
    pine = simple_material("PineOut", (0.008, 0.022, 0.014), rough=0.9)
    for _ in range(40):
        px = rng.uniform(-16, 16)
        py = rng.uniform(4, 30) if abs(px) < 6 else rng.uniform(-2, 30)
        if abs(px) < 5 and py < 6:
            continue
        h = rng.uniform(4, 10)
        for tier in range(6):
            r_t = h * 0.3 * (1 - tier / 6) + 0.15
            zc = h * (0.08 + 0.15 * tier) - 0.2
            bpy.ops.mesh.primitive_cone_add(vertices=14, radius1=r_t, depth=h * 0.24, location=(px, py, zc))
            bpy.context.active_object.data.materials.append(pine)
            bpy.ops.mesh.primitive_cone_add(vertices=14, radius1=r_t * 0.9, depth=h * 0.13,
                                            location=(px, py, zc + h * 0.07))
            bpy.context.active_object.data.materials.append(snow)


def setup(scene):
    cam_data = bpy.data.cameras.new("Camera")
    cam_data.lens = 30
    cam_data.dof.use_dof = True
    cam_data.dof.focus_distance = (Vector((0, 0, 1.4)) - CAMERA).length
    cam_data.dof.aperture_fstop = 2.8
    cam = link(bpy.data.objects.new("Camera", cam_data))
    cam.location = CAMERA
    cam.rotation_euler = (TARGET - CAMERA).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    sun = bpy.data.lights.new("Moon", "SUN")
    sun.energy = 0.55
    sun.color = (0.6, 0.72, 1.0)
    sun.angle = math.radians(1.0)
    so = link(bpy.data.objects.new("Moon", sun))
    so.rotation_euler = Vector((0.45, 0.8, -0.6)).to_track_quat("-Z", "Y").to_euler()
    world = bpy.data.worlds.new("Night")
    scene.world = world
    nt = world.node_tree
    bg = nt.nodes["Background"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.035, 0.05, 0.11, 1)
    ramp.color_ramp.elements[1].position = 0.5
    ramp.color_ramp.elements[1].color = (0.004, 0.008, 0.025, 1)
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    r = scene.render
    r.engine = "CYCLES"
    r.resolution_x, r.resolution_y = RES
    r.image_settings.file_format = "PNG"
    r.use_persistent_data = True
    c = scene.cycles
    c.device = "CPU"
    c.samples = SAMPLES
    c.use_adaptive_sampling = True
    c.adaptive_threshold = 0.02
    c.use_denoising = True
    c.max_bounces = 6
    c.sample_clamp_indirect = 6
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = 0.6


def project(scene, cam, co):
    p = world_to_camera_view(scene, cam, Vector(co))
    return [round(p.x, 4), round(1 - p.y, 4)]


def to_jpeg(png, jpg, quality=88):
    img = bpy.data.images.load(png)
    img.file_format = "JPEG"
    bpy.context.scene.render.image_settings.file_format = "JPEG"
    bpy.context.scene.render.image_settings.quality = quality
    img.save_render(jpg)
    bpy.data.images.remove(img)
    bpy.context.scene.render.image_settings.file_format = "PNG"


def main():
    t0 = time.time()
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(BUILD_DIR, exist_ok=True)
    scene = T.reset_scene()
    T.needle_material()
    T.bark_material()
    log_facade()
    roof()
    ground()
    hinge = door()
    trim_and_sign()
    windows()
    lantern()
    interior_glow()
    background()
    setup(scene)
    bpy.context.view_layer.update()
    cam = scene.camera
    print(f"scene built in {time.time() - t0:.0f}s")

    # 1) the closed door, full frame
    scene.render.filepath = os.path.join(BUILD_DIR, "door.png")
    bpy.ops.render.render(write_still=True)
    to_jpeg(scene.render.filepath, os.path.join(OUT_DIR, "door.jpg"))
    print(f"  closed door in {time.time() - t0:.0f}s", flush=True)

    # 2) the door opening: only the doorway area changes, so render just that region
    x0, x1, y0, y1 = 0.27, 0.73, 0.0, 0.86          # border, y measured from the bottom
    r = scene.render
    r.use_border = True
    r.use_crop_to_border = True
    r.border_min_x, r.border_max_x, r.border_min_y, r.border_max_y = x0, x1, y0, y1
    r.resolution_percentage = 100 if PREVIEW else 50     # a one-second swing: half resolution is plenty
    scene.cycles.samples = max(32, SAMPLES // 2)
    for f in range(FRAMES):
        t = (f + 1) / FRAMES
        ease = t * t * (3 - 2 * t)
        hinge.rotation_euler = (0, 0, math.radians(92) * ease)
        scene.render.filepath = os.path.join(BUILD_DIR, f"open-{f:02d}.png")
        bpy.ops.render.render(write_still=True)
        to_jpeg(scene.render.filepath, os.path.join(OUT_DIR, f"open-{f:02d}.jpg"))
        print(f"  frame {f + 1}/{FRAMES}  {time.time() - t0:.0f}s", flush=True)

    hw = DOOR_W / 2
    info = {
        "width": RES[0], "height": RES[1], "frames": FRAMES,
        "crop": {"x0": x0, "x1": x1, "y0": round(1 - y1, 4), "y1": round(1 - y0, 4)},
        "doorway": [project(scene, cam, c) for c in ((-hw, 0, SILL), (hw, 0, SILL), (hw, 0, SILL + DOOR_H), (-hw, 0, SILL + DOOR_H))],
        "note": "fractions of the image, y from the top; crop is where the opening frames go",
    }
    with open(os.path.join(OUT_DIR, "door.json"), "w") as f:
        json.dump(info, f, indent=1)
    with open(os.path.join(OUT_DIR, "door.js"), "w") as f:
        f.write("window.CABIN_DOOR = " + json.dumps(info) + ";\n")
    print(f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
