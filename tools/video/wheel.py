"""The lucky-draw wheel for the promo video, in layers the film puts together (Blender, Cycles).

A wooden prize wheel of 24 numbered segments (red, cream and green, gold pegs), a ring of warm
bulbs, the LeMSIC emblem on the hub and a gold pointer, with ornaments and presents floating
around it, and the wrapped gift that appears when it stops. The wheel faces the camera square on,
so the film can spin the disc layer exactly by turning the picture.

    python tools/video/wheel.py [--preview]

Writes build/video/wheel/{disc,frame,float-a,float-b,gift}.png (transparent) and wheel.json
(where the wheel's centre is, and its radius, in the picture).
"""
import json
import math
import os
import sys

import numpy as np
import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools", "blender"))
import cabin_props as P  # noqa: E402
import lemsic_tree as T  # noqa: E402
from lemsic_tree import box, link, new_material, principled, simple_material  # noqa: E402

PREVIEW = "--preview" in sys.argv
OUT = os.path.join(ROOT, "build", "video", "wheel")
RES = (960, 540) if PREVIEW else (1920, 1080)
FONT = os.path.join(ROOT, "build", "fonts", "AlegreyaSC-Bold.ttf")
R = 1.0                                   # the disc's radius
rng = np.random.default_rng(24)
COLS = [(0.11, 0.002, 0.005), (0.72, 0.64, 0.5), (0.008, 0.1, 0.04)]


def collect(name, obs):
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    for ob in obs:
        for c in list(ob.users_collection):
            c.objects.unlink(ob)
        col.objects.link(ob)
    return col


def text(body, size, loc, mat, rot=(math.radians(90), 0, 0)):
    cu = bpy.data.curves.new("Txt", "FONT")
    cu.body = body
    cu.size = size
    cu.extrude = 0.006
    cu.bevel_depth = 0.002
    cu.align_x, cu.align_y = "CENTER", "CENTER"
    cu.font = bpy.data.fonts.load(FONT, check_existing=True)
    cu.materials.append(mat)
    ob = link(bpy.data.objects.new("Txt", cu))
    ob.location = loc
    ob.rotation_euler = rot
    return ob


def disc():
    """The turning part: 24 segments with their numbers and the gold pegs between them."""
    obs = []
    mats = [simple_material(f"Seg{k}", c, rough=0.35, coat=0.6) for k, c in enumerate(COLS)]
    gold = simple_material("Gold", (0.95, 0.68, 0.25), rough=0.22, metal=1.0)
    ink = [simple_material("InkCream", (0.93, 0.87, 0.74), rough=0.4), simple_material("InkRed", (0.42, 0.025, 0.035), rough=0.4)]
    n = 24
    for k in range(n):
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        ang = np.linspace(a0, a1, 12)
        verts = [(0, 0, 0)] + [(R * math.cos(a), 0, R * math.sin(a)) for a in ang]
        me = bpy.data.meshes.new("Seg")
        me.from_pydata(verts, [], [(0, i, i + 1) for i in range(1, len(verts) - 1)])
        ob = link(bpy.data.objects.new("Seg", me))
        ob.data.materials.append(mats[k % 3])
        sol = ob.modifiers.new("t", "SOLIDIFY"); sol.thickness = 0.04
        obs.append(ob)
        am = (a0 + a1) / 2
        num = text(str(k + 1), 0.13, (0.78 * R * math.cos(am), -0.03, 0.78 * R * math.sin(am)), ink[1 if k % 3 == 1 else 0])
        num.rotation_euler = (math.radians(90), -(am - math.radians(90)), 0)   # reading outward along its segment
        obs.append(num)
        bpy.ops.mesh.primitive_cylinder_add(radius=0.022, depth=0.08, location=(0.96 * R * math.cos(a0), -0.05, 0.96 * R * math.sin(a0)),
                                            rotation=(math.radians(90), 0, 0), vertices=20)
        peg = bpy.context.active_object; peg.data.materials.append(gold); obs.append(peg)
        v = [(0.32 * R * math.cos(a0), -0.022, 0.32 * R * math.sin(a0)), (0.995 * R * math.cos(a0), -0.022, 0.995 * R * math.sin(a0))]
        bpy.ops.mesh.primitive_cylinder_add(radius=0.006, depth=0.675 * R, location=tuple((np.array(v[0]) + np.array(v[1])) / 2),
                                            rotation=(0, math.pi / 2 - a0, 0), vertices=8)
        ln = bpy.context.active_object; ln.data.materials.append(gold); obs.append(ln)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.33 * R, minor_radius=0.012, location=(0, -0.025, 0), rotation=(math.radians(90), 0, 0))
    ring = bpy.context.active_object; ring.data.materials.append(gold); obs.append(ring)
    return collect("Disc", obs)


def frame():
    """What stays still: the wooden rim with its bulbs, the hub with the emblem, the pointer, the stand."""
    obs = []
    wood = P.log_side_material("WheelWood", "Z")
    gold = bpy.data.materials["Gold"]
    bpy.ops.mesh.primitive_torus_add(major_radius=R + 0.07, minor_radius=0.075, location=(0, -0.01, 0), rotation=(math.radians(90), 0, 0),
                                     major_segments=96, minor_segments=24)
    rim = bpy.context.active_object; rim.data.materials.append(wood); bpy.ops.object.shade_smooth(); obs.append(rim)
    bulb = simple_material("Bulb", (1, 1, 1), emit=(1.0, 0.72, 0.35), emit_strength=14)
    for k in range(36):
        a = 2 * math.pi * k / 36
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.024, location=((R + 0.07) * math.cos(a), -0.085, (R + 0.07) * math.sin(a)), segments=16, ring_count=8)
        b = bpy.context.active_object; b.data.materials.append(bulb); obs.append(b)
    # the hub: a gold boss with the LeMSIC emblem
    bpy.ops.mesh.primitive_cylinder_add(radius=0.2, depth=0.08, location=(0, -0.06, 0), rotation=(math.radians(90), 0, 0), vertices=96)
    hub = bpy.context.active_object; hub.data.materials.append(gold); bpy.ops.object.shade_smooth(); obs.append(hub)
    em, nt, out = new_material("Emblem")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (401 / 480, 1.0, 1.0)
    mp.inputs["Location"].default_value = ((1 - 401 / 480) / 2, 0, 0)
    nt.links.new(tc.outputs["UV"], mp.inputs["Vector"])
    img = nt.nodes.new("ShaderNodeTexImage"); img.image = bpy.data.images.load(os.path.join(ROOT, "site", "assets", "lemsic-emblem.png"))
    nt.links.new(mp.outputs["Vector"], img.inputs["Vector"])
    b = principled(nt, (1, 1, 1), rough=0.35); b.inputs["Coat Weight"].default_value = 0.6
    nt.links.new(img.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    bpy.ops.mesh.primitive_circle_add(vertices=96, radius=0.165, fill_type="NGON", location=(0, -0.102, 0), rotation=(math.radians(90), 0, 0))
    face = bpy.context.active_object
    me = face.data
    me.uv_layers.new(name="UV")                        # UVs straight from the circle's own shape
    uv = me.uv_layers.active.data
    for poly in me.polygons:
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uv[li].uv = (co.x / 0.33 + 0.5, co.y / 0.33 + 0.5)
    face.data.materials.append(em); obs.append(face)
    # the pointer at the top, and the stand
    me = bpy.data.meshes.new("Pointer")
    me.from_pydata([(-0.09, 0, 0.0), (0.09, 0, 0.0), (0, 0, -0.26)], [], [(0, 1, 2)])
    pt = link(bpy.data.objects.new("Pointer", me)); pt.location = (0, -0.12, R + 0.2)
    sol = pt.modifiers.new("t", "SOLIDIFY"); sol.thickness = 0.04
    bev = pt.modifiers.new("b", "BEVEL"); bev.width = 0.012; bev.segments = 3
    pt.data.materials.append(gold); obs.append(pt)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.06, location=(0, -0.12, R + 0.22)); s = bpy.context.active_object; s.data.materials.append(gold); obs.append(s)
    for sx in (-1, 1):
        leg = box("Leg", (0.09, 0.09, 1.9), (sx * 0.45, 0.12, -R - 0.55), wood); leg.rotation_euler = (0, sx * math.radians(14), 0)
        obs.append(leg)
    obs.append(box("Axle", (0.12, 0.3, 0.12), (0, 0.1, 0), wood))
    return collect("Frame", obs)


def gift(loc, size, paper, ribbon, name, yaw=28, tilt=14):
    """A wrapped present with a ribbon both ways and a bow, turned to show its depth."""
    obs = []
    piv = link(bpy.data.objects.new(name + "Pivot", None))
    x, y, z = 0, 0, 0
    w, d, h = size
    b = box(name, size, (0, 0, 0), paper); b.modifiers["bevel"].width = 0.01; obs.append(b)
    obs.append(box(name + "RibbonA", (w + 0.006, 0.08 * w, h + 0.006), (0, 0, 0), ribbon))
    obs.append(box(name + "RibbonB", (0.08 * w, d + 0.006, h + 0.006), (0, 0, 0), ribbon))
    for sx in (-1, 1):                                   # the bow: two loops and tails
        bpy.ops.mesh.primitive_torus_add(major_radius=0.19 * w, minor_radius=0.045 * w, location=(x + sx * 0.17 * w, y, z + h / 2 + 0.1 * w),
                                         rotation=(math.radians(90), sx * math.radians(-30), 0))
        lp = bpy.context.active_object; lp.scale = (1, 0.45, 0.7); lp.data.materials.append(ribbon); bpy.ops.object.shade_smooth(); obs.append(lp)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.05 * w, location=(x, y - 0.01, z + h / 2 + 0.05 * w))
    k = bpy.context.active_object; k.data.materials.append(ribbon); obs.append(k)
    for ob in obs:
        ob.parent = piv
    piv.location = loc
    piv.rotation_euler = (math.radians(tilt), 0, math.radians(yaw))
    return obs + [piv]


def floating():
    a, b = [], []
    papers = [simple_material("PaperRed", (0.16, 0.004, 0.008), rough=0.4, coat=0.5), simple_material("PaperGreen", (0.03, 0.22, 0.1), rough=0.4, coat=0.5),
              simple_material("PaperCream", (0.86, 0.8, 0.68), rough=0.45), simple_material("PaperBlue", (0.05, 0.12, 0.36), rough=0.4, coat=0.5)]
    gold = bpy.data.materials["Gold"]
    ribbon = simple_material("RibbonGold", (0.9, 0.62, 0.2), rough=0.3, metal=0.8)
    bauble = [simple_material(f"Bauble{k}", c, rough=0.1, metal=1.0, coat=1.0) for k, c in enumerate(((0.75, 0.05, 0.05), (0.9, 0.65, 0.2), (0.05, 0.35, 0.15), (0.75, 0.75, 0.8)))]
    spots = [(-2.05, 0.3, 0.75, "b"), (-1.75, 0.0, -0.55, "g"), (-2.25, 0.4, -0.05, "b"), (-1.55, 0.2, 1.15, "b"),
             (2.05, 0.3, 0.65, "g"), (1.8, 0.1, -0.7, "b"), (2.3, 0.4, 0.0, "b"), (1.6, 0.0, 1.2, "b")]
    for k, (x, y, z, kind) in enumerate(spots):
        dest = a if x < 0 else b
        if kind == "g":
            s = 0.34
            dest += gift((x, y, z), (s, s, s * 0.8), papers[k % 4], ribbon, f"Float{k}",
                         yaw=rng.uniform(20, 45) * (1 if x < 0 else -1), tilt=rng.uniform(10, 25))
        else:
            r = rng.uniform(0.11, 0.17)
            bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=(x, y, z), segments=48, ring_count=24)
            o = bpy.context.active_object; o.data.materials.append(bauble[k % 4]); bpy.ops.object.shade_smooth(); dest.append(o)
            bpy.ops.mesh.primitive_cylinder_add(radius=r * 0.28, depth=r * 0.3, location=(x, y, z + r * 1.02), vertices=24)
            c = bpy.context.active_object; c.data.materials.append(gold); dest.append(c)
    return collect("FloatA", a), collect("FloatB", b)


def main():
    os.makedirs(OUT, exist_ok=True)
    scene = T.reset_scene()
    cols = {"disc": disc(), "frame": frame()}
    cols["float-a"], cols["float-b"] = floating()
    ribbon = bpy.data.materials["RibbonGold"]
    cols["gift"] = collect("Gift", gift((0, -0.6, 0), (0.62, 0.62, 0.5), simple_material("GiftRed", (0.16, 0.004, 0.008), rough=0.35, coat=0.8), ribbon, "Gift"))
    cam_d = bpy.data.cameras.new("Cam"); cam_d.lens = 85
    cam = link(bpy.data.objects.new("Cam", cam_d))
    cam.location = (0, -10.5, 0.1)
    cam.rotation_euler = (math.radians(90), 0, 0)
    scene.camera = cam
    for loc, power, col, size in (((-3.5, -5, 2.5), 900, (1.0, 0.62, 0.32), 3.0), ((3.5, -3, 1.0), 260, (1.0, 0.8, 0.6), 2.0),
                                  ((0.5, 3, 3.5), 500, (1.0, 0.75, 0.45), 2.0)):
        ld = bpy.data.lights.new("L", "AREA"); ld.energy = power; ld.color = col; ld.size = size
        lo = link(bpy.data.objects.new("L", ld)); lo.location = loc
        lo.rotation_euler = (Vector((0, 0, 0)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    world = bpy.data.worlds.new("W"); scene.world = world
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.07, 0.04, 0.02, 1)    # warm, for the reflections
    r = scene.render
    r.engine = "CYCLES"; r.resolution_x, r.resolution_y = RES; r.film_transparent = True
    r.image_settings.file_format = "PNG"; r.image_settings.color_mode = "RGBA"
    c = scene.cycles; c.device = "CPU"; c.samples = 24 if PREVIEW else 64; c.use_denoising = True
    scene.view_settings.view_transform = "AgX"; scene.view_settings.look = "AgX - Medium High Contrast"
    bpy.context.view_layer.update()
    p = world_to_camera_view(scene, cam, Vector((0, 0, 0)))
    q = world_to_camera_view(scene, cam, Vector((R, 0, 0)))
    info = {"size": RES, "centre": [round(p.x, 5), round(1 - p.y, 5)], "radius": round(abs(q.x - p.x), 5)}
    with open(os.path.join(OUT, "wheel.json"), "w") as f:
        json.dump(info, f, indent=1)
    for name, col in cols.items():                     # each layer on its own
        for other in cols.values():
            other.hide_render = other is not col
        r.filepath = os.path.join(OUT, name + ".png")
        bpy.ops.render.render(write_still=True)
        print("rendered", name, flush=True)
    print(info)


if __name__ == "__main__":
    main()
