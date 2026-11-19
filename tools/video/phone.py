"""An iPhone 18 Pro Max on a wooden table by the fire, Christmas lights out of focus behind it (one still).

The screen is left plain; the film lays the animated LeMSIC story into it (phone.json gives the
screen's corners in the image).

    python tools/video/phone.py [--preview]

Writes build/video/phone/phone.png (3840 x 2160, so the film can push in on the link) and phone.json.
"""
import json
import math
import os
import sys

import numpy as np
import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Matrix, Vector

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools", "blender"))
import cabin_props as P  # noqa: E402
import lemsic_tree as T  # noqa: E402
from lemsic_tree import box, link, simple_material  # noqa: E402

PREVIEW = "--preview" in sys.argv
OUT = os.path.join(ROOT, "build", "video", "phone")
RES = (1280, 720) if PREVIEW else (3840, 2160)
rng = np.random.default_rng(7)
TILT = math.radians(14)                 # the phone leans back on its stand
# an iPhone 18 Pro Max (reported: 163.4 x 78 x 8.75 mm, 6.9-inch screen), its frame in Dark Cherry
W, H, D = 0.078, 0.1634, 0.00875
RC = 0.0118                             # the corners' radius, seen from the front
BEZEL = 0.00165                         # glass edge to the lit screen
BASE = Vector((0.0, 0.0, 0.0))


def rounded_rect(w, h, r, seg=18, y0=0.0):
    """Outline points (x, y) of a rounded rectangle w x h from y0, centred on x = 0, counter-clockwise."""
    pts = []
    for cx, cy, a0 in ((w / 2 - r, y0 + h - r, 0), (-w / 2 + r, y0 + h - r, 90), (-w / 2 + r, y0 + r, 180), (w / 2 - r, y0 + r, 270)):
        for k in range(seg + 1):
            a = math.radians(a0 + 90 * k / seg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def slab(name, outline, z0, z1, mat, bevel=0.0):
    """A flat slab with that outline, from z0 (back) to z1 (front)."""
    n = len(outline)
    verts = [(x, y, z0) for x, y in outline] + [(x, y, z1) for x, y in outline]
    faces = [list(range(n))[::-1], list(range(n, 2 * n))]
    faces += [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    ob = link(bpy.data.objects.new(name, me))
    ob.data.materials.append(mat)
    if bevel:
        bv = ob.modifiers.new("bevel", "BEVEL"); bv.width = bevel; bv.segments = 4; bv.limit_method = "ANGLE"
        bv.angle_limit = math.radians(50)
    for poly in me.polygons:
        poly.use_smooth = True
    return ob


def phone():
    cherry = simple_material("DarkCherry", (0.3, 0.02, 0.045), rough=0.3, metal=0.9)       # anodised aluminium
    back = simple_material("BackGlass", (0.12, 0.012, 0.02), rough=0.55)
    black = simple_material("ScreenBlack", (0.0, 0.0, 0.0), rough=0.03)
    black.node_tree.nodes["Principled BSDF"].inputs["Coat Weight"].default_value = 1.0
    rot = Matrix.Rotation(math.radians(90) - TILT, 4, "X")          # standing up, leaning back
    piv = Matrix.Translation(BASE + Vector((0, 0.012, 0.012)))
    m = piv @ rot
    parts = []
    parts.append(slab("Frame", rounded_rect(W, H, RC), -D, -0.0004, cherry, bevel=0.0011))
    parts.append(slab("Back", rounded_rect(W - 0.0016, H - 0.0016, RC - 0.0008, y0=0.0008), -D - 0.0001, -D + 0.0006, back))
    parts.append(slab("Glass", rounded_rect(W - 0.0007, H - 0.0007, RC - 0.0004, y0=0.00035), -0.0006, 0.0, black, bevel=0.0005))
    # the buttons: on the right the side button and Camera Control, on the left the Action button and volume
    for side, y_lo, length in ((1, 0.104, 0.019), (1, 0.052, 0.017), (-1, 0.122, 0.009), (-1, 0.104, 0.013), (-1, 0.086, 0.013)):
        btn = box("Button", (0.0012, length, 0.0034), (side * (W / 2 + 0.0004), y_lo + length / 2, -D / 2), cherry)
        btn.modifiers["bevel"].width = 0.0005
        parts.append(btn)
    for ob in parts:                                  # (from each part's own transform: matrix_world isn't updated yet)
        ob.matrix_world = m @ Matrix.LocRotScale(ob.location, ob.rotation_euler, ob.scale)
    # the lit screen, inside the bezel (the film lays the story there, rounded like the glass)
    sw, sh = W - 2 * BEZEL, H - 2 * BEZEL
    corners = [m @ Vector((x, y, 0.0002)) for x, y in ((-sw / 2, BEZEL + sh), (sw / 2, BEZEL + sh), (sw / 2, BEZEL), (-sw / 2, BEZEL))]
    return corners, (RC - BEZEL) / sw


def stand_and_table():
    wood = P.log_side_material("StandWood", "X")
    st = box("Stand", (0.09, 0.05, 0.012), (0, 0.012, 0.006), wood)
    st.modifiers["bevel"].width = 0.004
    lip = box("StandLip", (0.09, 0.008, 0.02), (0, -0.006, 0.012), wood)
    lip.modifiers["bevel"].width = 0.003
    back = box("StandBack", (0.06, 0.012, 0.08), (0, 0.045, 0.035), wood)
    back.rotation_euler = (TILT, 0, 0)
    back.modifiers["bevel"].width = 0.003
    tb = box("Table", (2.4, 1.8, 0.04), (0, 0.55, -0.02), P.plank_material())
    tb.modifiers["bevel"].width = 0.004
    # a mug of cocoa and a little pine sprig with baubles, to the side
    mug = simple_material("MugRed", (0.45, 0.03, 0.03), rough=0.25, coat=1.0)
    MX, MY = 0.2, 0.26
    bpy.ops.mesh.primitive_cylinder_add(radius=0.04, depth=0.095, location=(MX, MY, 0.0475), vertices=96)
    m = bpy.context.active_object; m.data.materials.append(mug); bpy.ops.object.shade_smooth()
    sol = m.modifiers.new("wall", "SOLIDIFY"); sol.thickness = 0.004
    bpy.ops.mesh.primitive_cylinder_add(radius=0.037, depth=0.004, location=(MX, MY, 0.085), vertices=96)
    c = bpy.context.active_object; c.data.materials.append(simple_material("Cocoa", (0.12, 0.05, 0.02), rough=0.2))
    bpy.ops.mesh.primitive_torus_add(major_radius=0.026, minor_radius=0.007, location=(MX + 0.045, MY, 0.05), rotation=(math.radians(90), 0, 0))
    bpy.context.active_object.data.materials.append(mug); bpy.ops.object.shade_smooth()
    for k, (x, y, r, col) in enumerate(((-0.17, 0.1, 0.022, (0.6, 0.45, 0.12)), (-0.13, 0.17, 0.017, (0.5, 0.03, 0.03)),
                                         (-0.21, 0.2, 0.019, (0.05, 0.25, 0.1)))):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=(x, y, r), segments=48, ring_count=24)
        bpy.context.active_object.data.materials.append(simple_material(f"Bauble{k}", col, rough=0.12, metal=1.0))
    for k in range(40):                                 # pine needles in a loose sprig
        a = rng.uniform(-0.6, 0.6)
        x0, y0 = -0.2 + rng.normal(0, 0.03), 0.12 + rng.normal(0, 0.03)
        bpy.ops.mesh.primitive_cylinder_add(radius=0.0018, depth=rng.uniform(0.05, 0.09),
                                            location=(x0, y0, 0.004), rotation=(math.radians(90), 0, a), vertices=6)
        bpy.context.active_object.data.materials.append(simple_material(f"Needle{k % 3}", (0.01, 0.06 + 0.02 * (k % 3), 0.02), rough=0.6))


def background():
    logs = P.log_side_material("BackLogs", "X")
    endg = P.end_grain_material()
    P.logs_mesh("BackWall", [((-3, 1.5, z), (3, 1.5, z), 0.15) for z in np.arange(-0.2, 1.6, 0.31)], rng, [logs, endg])
    bulb_cols = [(1.0, 0.72, 0.38), (1.0, 0.62, 0.3), (1.0, 0.8, 0.5)]
    bulb_cols = [(1.0, 0.55, 0.18), (1.0, 0.45, 0.12), (1.0, 0.65, 0.28)]
    mats = [simple_material(f"Fairy{k}", (1, 1, 1), emit=c, emit_strength=22) for k, c in enumerate(bulb_cols)]
    for row, (yy, zz, n) in enumerate(((0.75, 0.035, 34), (1.15, 0.16, 40), (1.42, 0.32, 44))):   # garlands behind, out of focus
        for k in range(n):
            x = -1.1 + 2.2 * k / (n - 1) + rng.normal(0, 0.01)
            z = zz + 0.05 * math.sin(x * 5 + row) + rng.normal(0, 0.008)
            bpy.ops.mesh.primitive_uv_sphere_add(radius=0.008, location=(x, yy + rng.normal(0, 0.03), z), segments=12, ring_count=6)
            bpy.context.active_object.data.materials.append(mats[k % 3])
    for name, loc, power, col, size in (("RimRight", (0.3, 0.32, 0.16), 6, (1.0, 0.82, 0.7), 0.12),    # the frame's edge catches it
                                        ("RimTop", (-0.05, 0.25, 0.45), 3, (1.0, 0.85, 0.7), 0.15)):
        ld = bpy.data.lights.new(name, "AREA"); ld.energy = power; ld.color = col; ld.size = size
        lo = link(bpy.data.objects.new(name, ld)); lo.location = loc
        lo.rotation_euler = (Vector((0, 0.02, 0.1)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    for loc, power, col in (((-0.9, -0.6, 0.6), 30, (1.0, 0.55, 0.22)), ((0.7, 0.4, 0.9), 6, (1.0, 0.7, 0.4))):
        ld = bpy.data.lights.new("Warm", "AREA"); ld.energy = power; ld.color = col; ld.size = 0.5
        lo = link(bpy.data.objects.new("Warm", ld)); lo.location = loc
        lo.rotation_euler = (Vector((0, 0.05, 0.08)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()


def main():
    os.makedirs(OUT, exist_ok=True)
    scene = T.reset_scene()
    corners, radius = phone()
    stand_and_table()
    background()
    cam_d = bpy.data.cameras.new("Cam"); cam_d.lens = 70
    cam_d.dof.use_dof = True; cam_d.dof.aperture_fstop = 1.8
    cam = link(bpy.data.objects.new("Cam", cam_d))
    target = Vector((0.0, 0.03, 0.094))
    cam.location = Vector((0.13, -0.665, 0.18))
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam_d.dof.focus_distance = (target - cam.location).length
    scene.camera = cam
    world = bpy.data.worlds.new("Dark"); scene.world = world
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.004, 0.003, 0.003, 1)
    r = scene.render
    r.engine = "CYCLES"
    r.resolution_x, r.resolution_y = RES
    r.image_settings.file_format = "PNG"
    c = scene.cycles
    c.device = "CPU"; c.samples = 48 if PREVIEW else 96; c.use_denoising = True
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    bpy.context.view_layer.update()
    pts = [world_to_camera_view(scene, cam, p) for p in corners]
    info = {"size": RES, "screen": [[round(p.x, 5), round(1 - p.y, 5)] for p in pts], "corner": round(radius, 4),
            "note": "screen corners: top-left, top-right, bottom-right, bottom-left, fractions of the image, y from the top"}
    with open(os.path.join(OUT, "phone.json"), "w") as f:
        json.dump(info, f, indent=1)
    r.filepath = os.path.join(OUT, "phone.png")
    bpy.ops.render.render(write_still=True)
    print("screen", info["screen"])


if __name__ == "__main__":
    main()
