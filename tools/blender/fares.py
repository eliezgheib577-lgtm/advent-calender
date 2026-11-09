"""Fares, the LeMSIC mascot, as a plush doll (Blender).

A fabric doll in traditional dress: red felt tarboush with a gold band and a black
yarn pom-pom, black curly yarn hair, thick eyebrows and a handlebar mustache, bead
eyes, a red-and-white neck scarf, a black jacket trimmed in gold over a green vest
with gold buttons, a cream sash, and baggy black sherwal.

Here he sits on the floor, sipping from a white LeMSIC tumbler.

    build_fares()  -> an Empty; move and turn it to place him. Built facing -Y, about
                      0.9 m tall sitting (a large plush, as in the photos).
"""
import math
import os

import numpy as np
import bpy
from mathutils import Vector

from lemsic_tree import link, new_material, principled

HERE = os.path.dirname(os.path.abspath(__file__))
EMBLEM = os.path.join(HERE, "textures", "lemsic-emblem.png")
rng = np.random.default_rng(1964)


# ---------------------------------------------------------------- materials
def fabric(name, color, sheen=0.7, rough=0.92, fuzz=0.25, scale=500.0):
    """Felt / fleece: matte with a soft sheen and a fine fibrous bump."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m, nt, out = new_material(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = 4.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = fuzz
    bump.inputs["Distance"].default_value = 0.002
    b = principled(nt, color, rough=rough)
    b.inputs["Sheen Weight"].default_value = sheen
    b.inputs["Sheen Roughness"].default_value = 0.35
    nt.links.new(tc.outputs["Object"], n.inputs["Vector"])
    nt.links.new(n.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    return m


def yarn():
    """Black wool yarn: lumpy and twisted."""
    if "Yarn" in bpy.data.materials:
        return bpy.data.materials["Yarn"]
    m, nt, out = new_material("Yarn")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    w = nt.nodes.new("ShaderNodeTexWave")
    w.inputs["Scale"].default_value = 180.0
    w.inputs["Distortion"].default_value = 6.0
    w.inputs["Detail"].default_value = 3.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.8
    bump.inputs["Distance"].default_value = 0.003
    b = principled(nt, (0.005, 0.0045, 0.0045), rough=0.7)
    b.inputs["Sheen Weight"].default_value = 0.12
    nt.links.new(tc.outputs["Object"], w.inputs["Vector"])
    nt.links.new(w.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    return m


def gold_braid():
    if "GoldBraid" in bpy.data.materials:
        return bpy.data.materials["GoldBraid"]
    m, nt, out = new_material("GoldBraid")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    w = nt.nodes.new("ShaderNodeTexWave")
    w.inputs["Scale"].default_value = 220.0
    w.inputs["Distortion"].default_value = 1.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.5
    b = principled(nt, (0.78, 0.58, 0.26), rough=0.38, metal=0.85)
    nt.links.new(tc.outputs["Object"], w.inputs["Vector"])
    nt.links.new(w.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    return m


def glossy(name, color, rough=0.08):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m, nt, out = new_material(name)
    b = principled(nt, color, rough=rough, coat=1.0)
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    return m


def tumbler_material():
    """White powder-coated tumbler with the LeMSIC emblem on the front."""
    m, nt, out = new_material("Tumbler")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    u = nt.nodes.new("ShaderNodeMath"); u.operation = "MULTIPLY_ADD"
    u.inputs[1].default_value = 1 / 0.05; u.inputs[2].default_value = 0.5
    v = nt.nodes.new("ShaderNodeMath"); v.operation = "MULTIPLY_ADD"
    v.inputs[1].default_value = 1 / 0.042; v.inputs[2].default_value = 0.5 - 0.0 / 0.042
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(EMBLEM, check_existing=True)
    tex.extension = "CLIP"
    front = nt.nodes.new("ShaderNodeMath"); front.operation = "LESS_THAN"
    front.inputs[1].default_value = 0.0
    fac = nt.nodes.new("ShaderNodeMath"); fac.operation = "MULTIPLY"
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    mix.inputs["A"].default_value = (0.82, 0.82, 0.8, 1)
    b = principled(nt, (0.82, 0.82, 0.8), rough=0.55)
    L = nt.links.new
    L(tc.outputs["Object"], sep.inputs[0])
    L(sep.outputs["X"], u.inputs[0]); L(sep.outputs["Z"], v.inputs[0])
    L(u.outputs[0], comb.inputs["X"]); L(v.outputs[0], comb.inputs["Y"])
    L(comb.outputs[0], tex.inputs["Vector"])
    L(sep.outputs["Y"], front.inputs[0])
    L(tex.outputs["Alpha"], fac.inputs[0]); L(front.outputs[0], fac.inputs[1])
    L(fac.outputs[0], mix.inputs["Factor"])
    L(tex.outputs["Color"], mix.inputs["B"])
    L(mix.outputs["Result"], b.inputs["Base Color"])
    L(b.outputs[0], out.inputs["Surface"])
    return m


# ---------------------------------------------------------------- geometry helpers
def mesh_from(name, verts, faces, mat, smooth=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(map(float, p)) for p in verts], [], [tuple(map(int, f)) for f in faces])
    me.update()
    if smooth:
        me.polygons.foreach_set("use_smooth", np.ones(len(me.polygons), bool))
    me.materials.append(mat)
    return link(bpy.data.objects.new(name, me))


def blob(name, center, radii, mat, rot=(0, 0, 0), segments=40, rings=20):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, radius=1.0, location=center, rotation=rot)
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = radii
    ob.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    return ob


def tube(name, points, radii, mat, sides=18, caps=True):
    """A smooth tube along a polyline (radius per point), with rounded-off ends."""
    P = np.asarray(points, float)
    R = np.asarray(radii, float)
    # resample smoothly
    t = np.linspace(0, 1, len(P))
    tt = np.linspace(0, 1, max(24, len(P) * 8))
    P = np.stack([np.interp(tt, t, P[:, k]) for k in range(3)], 1)
    R = np.interp(tt, t, R)
    T = np.gradient(P, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    ref = np.array([0.0, 0, 1]) if abs(T[0, 2]) < 0.9 else np.array([1.0, 0, 0])
    N = [np.cross(T[0], ref)]
    N[0] /= np.linalg.norm(N[0])
    for i in range(1, len(P)):                          # parallel transport, no twisting
        n = N[-1] - np.dot(N[-1], T[i]) * T[i]
        N.append(n / np.linalg.norm(n))
    N = np.array(N)
    B = np.cross(T, N)
    ang = np.linspace(0, 2 * np.pi, sides, endpoint=False)
    ring = (np.cos(ang)[None, :, None] * N[:, None, :] + np.sin(ang)[None, :, None] * B[:, None, :])
    V = (P[:, None, :] + R[:, None, None] * ring).reshape(-1, 3)
    n = len(P)
    k = np.arange(sides)
    F = [(i * sides + a, i * sides + (a + 1) % sides, (i + 1) * sides + (a + 1) % sides, (i + 1) * sides + a)
         for i in range(n - 1) for a in k]
    V = list(V)
    if caps:
        for end, sgn in ((0, -1), (n - 1, 1)):
            c = len(V)
            V.append(P[end] + T[end] * R[end] * 0.6 * sgn)
            base = end * sides
            F += [(c, base + (a + 1) % sides, base + a) if sgn < 0 else (c, base + a, base + (a + 1) % sides) for a in k]
    return mesh_from(name, V, F, mat)


def on_ellipsoid(center, radii, x, z, front=True):
    """The point on the front (or back) of an ellipsoid at the given x and z."""
    cx, cy, cz = center
    rx, ry, rz = radii
    s = 1 - ((x - cx) / rx) ** 2 - ((z - cz) / rz) ** 2
    y = cy - ry * math.sqrt(max(s, 0)) if front else cy + ry * math.sqrt(max(s, 0))
    return np.array([x, y, z])


# ---------------------------------------------------------------- Fares
def build_fares():
    black = fabric("FaresBlack", (0.006, 0.0055, 0.0055), sheen=0.18)
    red = fabric("FaresRed", (0.40, 0.010, 0.010), sheen=0.2)
    green = fabric("FaresGreen", (0.012, 0.045, 0.02), sheen=0.45, rough=0.7)
    cream = fabric("FaresSash", (0.62, 0.55, 0.42), sheen=0.6, rough=0.5, fuzz=0.4, scale=120)
    skin = fabric("FaresSkin", (0.86, 0.74, 0.62), sheen=0.5, fuzz=0.12)
    skin.node_tree.nodes["Principled BSDF"].inputs["Subsurface Weight"].default_value = 0.15
    white = fabric("FaresWhite", (0.8, 0.8, 0.78), sheen=0.5)
    gold = gold_braid()
    yn = yarn()
    bead = glossy("Bead", (0.005, 0.005, 0.006))
    lip = fabric("FaresLip", (0.4, 0.03, 0.04), sheen=0.3)

    parts = []
    add = parts.append

    # --- body, sitting on the floor, legs out in front
    add(blob("Seat", (0, 0.03, 0.13), (0.18, 0.16, 0.13), black))
    for s in (-1, 1):
        add(tube("Leg", [(s * 0.085, -0.04, 0.12), (s * 0.1, -0.2, 0.12), (s * 0.11, -0.36, 0.1), (s * 0.115, -0.44, 0.085)],
                 [0.085, 0.08, 0.068, 0.05], black))
        add(blob("Shoe", (s * 0.118, -0.49, 0.08), (0.052, 0.075, 0.06), fabric("Leather", (0.01, 0.009, 0.009), sheen=0.05, rough=0.5, fuzz=0.05),
                 rot=(math.radians(-30), 0, 0)))
    torso_c, torso_r = (0.0, 0.03, 0.34), (0.165, 0.13, 0.2)
    add(blob("Jacket", torso_c, torso_r, black))
    add(blob("Vest", (0.0, -0.005, 0.36), (0.085, 0.11, 0.15), green))
    for k, z in enumerate(np.linspace(0.27, 0.47, 7)):        # gold buttons down the vest
        p = on_ellipsoid((0.0, -0.005, 0.36), (0.085, 0.11, 0.15), 0.0, z) + np.array([0, -0.004, 0])
        add(blob("Button", p, (0.008, 0.006, 0.008), gold, segments=12, rings=6))
    for s in (-1, 1):                                          # gold trim along the jacket's open front
        zs = np.linspace(0.18, 0.49, 12)
        xs = s * (0.07 + 0.012 * np.sin((zs - 0.18) / 0.31 * math.pi))
        pts = [on_ellipsoid(torso_c, torso_r, x, z) + np.array([0, -0.004, 0]) for x, z in zip(xs, zs)]
        add(tube("Trim", pts, [0.007] * len(pts), gold, sides=10))
    hem = [on_ellipsoid(torso_c, torso_r, 0.155 * math.cos(a), 0.175, front=math.sin(a) < 0) for a in np.linspace(0, 2 * math.pi, 40)]
    hem = [p * np.array([1.02, 1.02, 1]) + np.array([0, 0.0, 0]) for p in hem]
    add(tube("HemTrim", hem, [0.007] * len(hem), gold, sides=8, caps=False))
    bpy.ops.mesh.primitive_torus_add(major_radius=0.15, minor_radius=0.04, location=(0, 0.025, 0.215))
    sash = bpy.context.active_object
    sash.scale = (1.0, 0.85, 0.8)
    sash.data.materials.append(cream)
    bpy.ops.object.shade_smooth()
    add(sash)

    # --- neck scarf
    bpy.ops.mesh.primitive_torus_add(major_radius=0.075, minor_radius=0.024, location=(0, 0.02, 0.515))
    sc = bpy.context.active_object
    sc.scale = (1.0, 0.9, 0.7)
    sc.data.materials.append(red)
    bpy.ops.object.shade_smooth()
    add(sc)
    add(blob("ScarfTip", (0.03, -0.07, 0.505), (0.032, 0.008, 0.02), white, rot=(0, math.radians(25), 0)))

    # --- head
    head_c, head_r = (0.0, 0.01, 0.64), (0.125, 0.118, 0.132)
    add(blob("Head", head_c, head_r, skin, segments=48, rings=24))
    add(blob("Nose", on_ellipsoid(head_c, head_r, 0.0, 0.625) + np.array([0, -0.008, 0]), (0.017, 0.015, 0.015), skin))
    for s in (-1, 1):
        e = on_ellipsoid(head_c, head_r, s * 0.042, 0.66) + np.array([0, -0.006, 0])
        add(blob("Eye", e, (0.013, 0.01, 0.015), bead, segments=16, rings=8))
        add(blob("EyeShine", e + np.array([-0.004 * s, -0.009, 0.005]), (0.0035, 0.002, 0.0035), white, segments=8, rings=4))
        brow = [on_ellipsoid(head_c, head_r, s * x, z) + np.array([0, -0.004, 0])
                for x, z in ((0.015, 0.69), (0.04, 0.698), (0.066, 0.692))]
        add(tube("Brow", brow, [0.008, 0.009, 0.007], yn, sides=10))
        for k in range(3):                                     # little lashes
            a = on_ellipsoid(head_c, head_r, s * (0.03 + 0.009 * k), 0.672)
            add(tube("Lash", [a, a + np.array([s * 0.004, -0.006, 0.009])], [0.0018, 0.001], yn, sides=6))
        # handlebar mustache: thick yarn sweeping out from under the nose and curling down
        mpts = [on_ellipsoid(head_c, head_r, s * x, z) + np.array([0, -d, 0])
                for x, z, d in ((0.004, 0.605, 0.012), (0.03, 0.602, 0.013), (0.06, 0.598, 0.01), (0.083, 0.588, 0.004), (0.088, 0.573, 0.0))]
        add(tube("Mustache", mpts, [0.014, 0.017, 0.015, 0.011, 0.006], yn, sides=14))
    mouth = [on_ellipsoid(head_c, head_r, x, 0.578) + np.array([0, -0.004, 0]) for x in (-0.016, 0.0, 0.016)]
    add(tube("Mouth", mouth, [0.005, 0.006, 0.005], lip, sides=8))

    # black curly yarn hair round the back and sides, below the hat
    for k in range(150):
        a = rng.uniform(math.radians(-10), math.radians(190))  # sides and back
        z = rng.uniform(0.56, 0.72)
        rr = 0.122 * math.sqrt(max(0.1, 1 - ((z - 0.64) / 0.14) ** 2)) + 0.012
        p = np.array([rr * math.cos(a), 0.01 + rr * math.sin(a) * 1.0, z])
        if p[1] < -0.02 and z < 0.7:                          # keep the face clear
            continue
        bpy.ops.mesh.primitive_torus_add(major_radius=rng.uniform(0.011, 0.016), minor_radius=0.0055,
                                         major_segments=14, minor_segments=6, location=p,
                                         rotation=tuple(rng.uniform(0, math.pi, 3)))
        c = bpy.context.active_object
        c.data.materials.append(yn)
        add(c)

    # tarboush: red felt with a gold band and a black yarn pom-pom
    fez_base, fez_top = 0.705, 0.86
    verts, faces = [], []
    seg = 40
    prof = [(0.122, fez_base), (0.121, fez_base + 0.05), (0.115, fez_top - 0.03), (0.105, fez_top - 0.008), (0.07, fez_top),
            (0.0, fez_top + 0.004)]
    for r_, z_ in prof:
        for a in np.linspace(0, 2 * math.pi, seg, endpoint=False):
            verts.append((r_ * math.cos(a), 0.01 + r_ * math.sin(a), z_))
    for i in range(len(prof) - 1):
        for a in range(seg):
            faces.append((i * seg + a, i * seg + (a + 1) % seg, (i + 1) * seg + (a + 1) % seg, (i + 1) * seg + a))
    fez = mesh_from("Tarboush", verts, faces, red)
    fez.rotation_euler = (math.radians(-4), math.radians(6), 0)
    add(fez)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.122, minor_radius=0.009, location=(0, 0.01, fez_base + 0.016))
    band = bpy.context.active_object
    band.scale = (1, 1, 2.2)
    band.data.materials.append(gold)
    band.rotation_euler = (math.radians(-4), math.radians(6), 0)
    bpy.ops.object.shade_smooth()
    add(band)
    add(blob("BandKnot", (-0.12, -0.02, fez_base + 0.02), (0.022, 0.018, 0.02), gold))
    top = np.array([0.008, 0.012, fez_top + 0.005])
    for k in range(46):
        d = np.array([rng.normal(0, 0.45), rng.normal(0, 0.45), rng.uniform(0.6, 1.0)])
        d /= np.linalg.norm(d)
        L = rng.uniform(0.035, 0.065)
        add(tube("Pompom", [top, top + d * L * 0.5 + rng.normal(0, 0.004, 3), top + d * L], [0.0045, 0.004, 0.003], yn, sides=6))

    # --- arms: right hand brings the tumbler up to sip, left hand rests on the knee
    sleeve_r = [0.05, 0.047, 0.044, 0.04]
    right = [(-0.15, 0.03, 0.46), (-0.205, -0.03, 0.36), (-0.18, -0.1, 0.33), (-0.1, -0.16, 0.45)]
    left = [(0.15, 0.03, 0.46), (0.2, -0.02, 0.33), (0.19, -0.12, 0.22), (0.15, -0.24, 0.18)]
    for pts in (right, left):
        add(tube("Sleeve", pts, sleeve_r, black))
        w = np.array(pts[-1])
        d = w - np.array(pts[-2])
        d /= np.linalg.norm(d)
        bpy.ops.mesh.primitive_torus_add(major_radius=0.042, minor_radius=0.006, location=tuple(w - d * 0.01))
        cuff = bpy.context.active_object
        cuff.rotation_euler = Vector(d.tolist()).to_track_quat("Z", "Y").to_euler()
        cuff.data.materials.append(gold)
        add(cuff)
        hand = blob("Hand", tuple(w + d * 0.035), (0.034, 0.03, 0.045), skin)
        hand.rotation_euler = Vector(d.tolist()).to_track_quat("Z", "Y").to_euler()
        add(hand)
        add(blob("Thumb", tuple(w + d * 0.03 + np.array([0, -0.025, 0.01])), (0.012, 0.012, 0.018), skin))

    # the LeMSIC tumbler, tilted up to his mouth
    tb = bpy.data.objects.new("TumblerRig", None)
    link(tb)
    mouth_pt = np.array(on_ellipsoid(head_c, head_r, -0.035, 0.585)) + np.array([0, -0.01, 0])
    hand_pt = np.array(right[-1]) + np.array([0.0, -0.02, 0.05])
    axis = mouth_pt - hand_pt
    axis /= np.linalg.norm(axis)
    tmat = tumbler_material()
    bpy.ops.mesh.primitive_cone_add(vertices=40, radius1=0.028, radius2=0.034, depth=0.17, location=(0, 0, 0.085))
    body = bpy.context.active_object
    body.data.materials.append(tmat)
    bpy.ops.object.shade_smooth()
    steel = glossy("Steel", (0.7, 0.7, 0.72), rough=0.25)
    steel.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = 1.0
    bpy.ops.mesh.primitive_cylinder_add(vertices=40, radius=0.0345, depth=0.012, location=(0, 0, 0.176))
    bpy.context.active_object.data.materials.append(steel)
    ring = bpy.context.active_object
    bpy.ops.mesh.primitive_cylinder_add(vertices=40, radius=0.036, depth=0.022, location=(0, 0, 0.193))
    lid = bpy.context.active_object
    lid.data.materials.append(glossy("Lid", (0.03, 0.03, 0.035), rough=0.2))
    for ob in (body, ring, lid):
        ob.parent = tb
    tb.location = hand_pt - axis * 0.06
    tb.rotation_euler = Vector(axis.tolist()).to_track_quat("Z", "Y").to_euler()
    add(tb)

    root = bpy.data.objects.new("Fares", None)
    link(root)
    for ob in parts:
        if ob.parent is None:
            ob.parent = root
    return root


if __name__ == "__main__":
    # quick look: python tools/blender/fares.py  (writes build/fares-preview.png)
    import sys
    sys.path.insert(0, HERE)
    import lemsic_tree as T
    scene = T.reset_scene()
    root = build_fares()
    cam_data = bpy.data.cameras.new("Cam")
    cam_data.lens = 50
    cam = link(bpy.data.objects.new("Cam", cam_data))
    cam.location = (0.55, -1.75, 0.75)
    cam.rotation_euler = (Vector((0, 0, 0.42)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    for loc, power in (((-1.5, -1.5, 2.0), 300), ((1.8, -0.8, 1.2), 120), ((0.4, 1.5, 1.5), 150)):
        ld = bpy.data.lights.new("L", "AREA")
        ld.energy = power
        ld.size = 1.2
        ob = link(bpy.data.objects.new("L", ld))
        ob.location = loc
        ob.rotation_euler = (Vector((0, 0, 0.4)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    bpy.ops.mesh.primitive_plane_add(size=6)
    bpy.context.active_object.data.materials.append(T.simple_material("Floor", (0.15, 0.08, 0.04), rough=0.5))
    world = bpy.data.worlds.new("W")
    scene.world = world
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.05, 0.04, 0.035, 1)
    r = scene.render
    r.engine = "CYCLES"
    r.resolution_x, r.resolution_y = 720, 900
    scene.cycles.samples = 48
    scene.cycles.use_denoising = True
    scene.view_settings.view_transform = "AgX"
    out = os.path.join(os.path.dirname(os.path.dirname(HERE)), "build", "fares-preview.png")
    r.filepath = out
    bpy.ops.render.render(write_still=True)
    print("wrote", out)
