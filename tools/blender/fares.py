"""Fares, the LeMSIC mascot doll (Blender, Cycles).

Modelled on the real plush doll: a soft cream fabric head framed by black curly
yarn hair, a red felt tarboush with a twisted gold cord and a black yarn pom-pom,
stitched eyes, thick looped yarn eyebrows and a bushy yarn mustache, a red and
white neck scarf, a black fleece jacket edged in gold braid and worn open over a
green vest with gold buttons, a creased cream satin sash, baggy black sherwal
gathered at the ankle, and soft black shoes.

Here he sits on the floor sipping from a white LeMSIC tumbler.

    build_fares()  -> an Empty; move and turn it to place him. Built facing -Y.
    python tools/blender/fares.py   renders a close-up to build/fares-preview.png
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
def fabric(name, color, sheen=0.3, rough=0.92, fuzz=0.3, scale=600.0, sheen_tint=(1, 1, 1)):
    """Felt, fleece or cotton: matte, a soft sheen at grazing angles, fine fibrous bump."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m, nt, out = new_material(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = 6.0
    n2 = nt.nodes.new("ShaderNodeTexNoise")
    n2.inputs["Scale"].default_value = 40.0
    n2.inputs["Detail"].default_value = 3.0
    tone = nt.nodes.new("ShaderNodeMix")
    tone.data_type = "RGBA"
    tone.blend_type = "MULTIPLY"
    tone.inputs["Factor"].default_value = 0.12
    tone.inputs["A"].default_value = (*color, 1)
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = fuzz
    bump.inputs["Distance"].default_value = 0.0015
    b = principled(nt, color, rough=rough)
    b.inputs["Sheen Weight"].default_value = sheen
    b.inputs["Sheen Roughness"].default_value = 0.4
    b.inputs["Sheen Tint"].default_value = (*sheen_tint, 1)
    L = nt.links.new
    L(tc.outputs["Object"], n.inputs["Vector"])
    L(tc.outputs["Object"], n2.inputs["Vector"])
    L(n2.outputs["Color"], tone.inputs["B"])
    L(tone.outputs["Result"], b.inputs["Base Color"])
    L(n.outputs["Fac"], bump.inputs["Height"])
    L(bump.outputs["Normal"], b.inputs["Normal"])
    L(b.outputs[0], out.inputs["Surface"])
    return m


def yarn():
    """Black wool yarn: twisted plies, fuzzy, slightly shiny."""
    if "Yarn" in bpy.data.materials:
        return bpy.data.materials["Yarn"]
    m, nt, out = new_material("Yarn")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    w = nt.nodes.new("ShaderNodeTexWave")
    w.wave_type = "BANDS"
    w.bands_direction = "DIAGONAL"
    w.inputs["Scale"].default_value = 260.0
    w.inputs["Distortion"].default_value = 4.0
    w.inputs["Detail"].default_value = 3.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.9
    bump.inputs["Distance"].default_value = 0.0012
    b = principled(nt, (0.004, 0.0038, 0.0038), rough=0.7)
    b.inputs["Sheen Weight"].default_value = 0.08
    b.inputs["Sheen Roughness"].default_value = 0.3
    nt.links.new(tc.outputs["Object"], w.inputs["Vector"])
    nt.links.new(w.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    return m


def gold_cord():
    if "GoldCord" in bpy.data.materials:
        return bpy.data.materials["GoldCord"]
    m, nt, out = new_material("GoldCord")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    w = nt.nodes.new("ShaderNodeTexWave")
    w.inputs["Scale"].default_value = 420.0
    w.inputs["Distortion"].default_value = 2.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.6
    bump.inputs["Distance"].default_value = 0.001
    b = principled(nt, (0.62, 0.40, 0.11), rough=0.36, metal=0.9)
    nt.links.new(tc.outputs["Object"], w.inputs["Vector"])
    nt.links.new(w.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    return m


def plain(name, color, rough=0.5, metal=0.0, coat=0.0):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m, nt, out = new_material(name)
    b = principled(nt, color, rough=rough, metal=metal, coat=coat)
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    return m


def tumbler_material():
    """White powder-coated tumbler with the LeMSIC emblem printed on the front."""
    if "Tumbler" in bpy.data.materials:
        return bpy.data.materials["Tumbler"]
    m, nt, out = new_material("Tumbler")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    u = nt.nodes.new("ShaderNodeMath"); u.operation = "MULTIPLY_ADD"
    u.inputs[1].default_value = 1 / 0.044; u.inputs[2].default_value = 0.5
    v = nt.nodes.new("ShaderNodeMath"); v.operation = "MULTIPLY_ADD"
    v.inputs[1].default_value = 1 / 0.037; v.inputs[2].default_value = 0.5
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(EMBLEM, check_existing=True)
    tex.extension = "CLIP"
    front = nt.nodes.new("ShaderNodeMath"); front.operation = "LESS_THAN"
    front.inputs[1].default_value = 0.0
    fac = nt.nodes.new("ShaderNodeMath"); fac.operation = "MULTIPLY"
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
    mix.inputs["A"].default_value = (0.8, 0.8, 0.78, 1)
    b = principled(nt, (0.8, 0.8, 0.78), rough=0.5)
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


def soften(ob, levels=2, wrinkle=0.0, wrinkle_scale=0.06):
    """Subdivide, and add soft fabric wrinkles."""
    sub = ob.modifiers.new("smooth", "SUBSURF")
    sub.levels = sub.render_levels = levels
    if wrinkle:
        tex = bpy.data.textures.new(ob.name + "Wrinkles", "CLOUDS")
        tex.noise_scale = wrinkle_scale
        tex.noise_depth = 2
        d = ob.modifiers.new("wrinkles", "DISPLACE")
        d.texture = tex
        d.strength = wrinkle
        d.mid_level = 0.5
        d.texture_coords = "OBJECT"
    return ob


def ellipsoid(name, center, radii, mat, rot=(0, 0, 0), seg=40, rings=20):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=rings, radius=1.0, location=center, rotation=rot)
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = radii
    ob.data.materials.append(mat)
    bpy.ops.object.shade_smooth()
    return ob


def frames_along(P):
    T = np.gradient(P, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    ref = np.array([0.0, 0, 1]) if abs(T[0, 2]) < 0.9 else np.array([1.0, 0, 0])
    N = [np.cross(T[0], ref)]
    N[0] /= np.linalg.norm(N[0])
    for i in range(1, len(P)):
        n = N[-1] - np.dot(N[-1], T[i]) * T[i]
        N.append(n / np.linalg.norm(n))
    N = np.array(N)
    return T, N, np.cross(T, N)


def tube(name, points, radii, mat, sides=20, caps=True, squash=1.0):
    """A smooth tube along a path, radius per point; squash < 1 flattens it."""
    P = np.asarray(points, float)
    R = np.asarray(radii, float)
    t = np.linspace(0, 1, len(P))
    tt = np.linspace(0, 1, max(28, len(P) * 10))
    P = np.stack([np.interp(tt, t, P[:, k]) for k in range(3)], 1)
    R = np.interp(tt, t, R)
    T, N, B = frames_along(P)
    ang = np.linspace(0, 2 * np.pi, sides, endpoint=False)
    ring = np.cos(ang)[None, :, None] * N[:, None, :] + squash * np.sin(ang)[None, :, None] * B[:, None, :]
    V = list((P[:, None, :] + R[:, None, None] * ring).reshape(-1, 3))
    n = len(P)
    F = [(i * sides + a, i * sides + (a + 1) % sides, (i + 1) * sides + (a + 1) % sides, (i + 1) * sides + a)
         for i in range(n - 1) for a in range(sides)]
    if caps:
        for end, sgn in ((0, -1), (n - 1, 1)):
            c = len(V)
            V.append(P[end] + T[end] * R[end] * 0.7 * sgn)
            base = end * sides
            F += [(c, base + (a + 1) % sides, base + a) if sgn < 0 else (c, base + a, base + (a + 1) % sides)
                  for a in range(sides)]
    return mesh_from(name, V, F, mat)


def curves(name, strands, radius, mat, res=2):
    """Many yarn strands in one curve object (each strand: a list of points)."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radius
    cu.bevel_resolution = res
    cu.use_fill_caps = True
    for pts in strands:
        sp = cu.splines.new("POLY")
        sp.points.add(len(pts) - 1)
        for p, co in zip(sp.points, pts):
            p.co = (float(co[0]), float(co[1]), float(co[2]), 1.0)
    cu.materials.append(mat)
    return link(bpy.data.objects.new(name, cu))


def curl(center, normal, r, turns, pitch, n=24):
    """A loop of yarn lying on a surface: a short helix around an axis tangent to it."""
    normal = normal / np.linalg.norm(normal)
    t = np.cross(normal, rng.normal(size=3))
    t /= np.linalg.norm(t)
    b = np.cross(normal, t)
    th = np.linspace(0, 2 * np.pi * turns, n)
    along = (th / (2 * np.pi) - turns / 2) * pitch
    return [center + t * a + r * (math.cos(x) * normal + math.sin(x) * b) for a, x in zip(along, th)]


def lathe(name, sections, mat, gap=None, seg=64):
    """A body of revolution through elliptical sections (z, rx, ry, cy).
    gap(z) leaves a half-angle (radians) open at the front (-Y), for an open jacket."""
    rows = []
    for z, rx, ry, cy in sections:
        if gap:
            g = gap(z)
            a = np.linspace(-math.pi / 2 + g, 3 * math.pi / 2 - g, seg)
        else:
            a = np.linspace(0, 2 * math.pi, seg, endpoint=False)
        rows.append([(rx * math.cos(x), cy + ry * math.sin(x), z) for x in a])
    V = [p for r in rows for p in r]
    w = len(rows[0])
    F = []
    for i in range(len(rows) - 1):
        for j in range(w - 1 if gap else w):
            j2 = (j + 1) % w
            F.append((i * w + j, i * w + j2, (i + 1) * w + j2, (i + 1) * w + j))
    return mesh_from(name, V, F, mat), rows


def on_head(c, r, x, z, out=0.0, front=True):
    """Point on the front (or back) of the head ellipsoid at x, z, pushed out along the normal."""
    s = 1 - ((x - c[0]) / r[0]) ** 2 - ((z - c[2]) / r[2]) ** 2
    s = math.sqrt(max(s, 0.0))
    y = c[1] - r[1] * s if front else c[1] + r[1] * s
    p = np.array([x, y, z])
    n = (p - np.array(c)) / np.array(r) ** 2
    n /= np.linalg.norm(n)
    return p + n * out, n


def ring_around(center, d, radius, n=30):
    """Points on a circle of `radius` around `center`, in the plane perpendicular to d."""
    d = d / np.linalg.norm(d)
    a = np.cross(d, [0.0, 0, 1]) if abs(d[2]) < 0.9 else np.cross(d, [1.0, 0, 0])
    a /= np.linalg.norm(a)
    b = np.cross(d, a)
    return [center + radius * (math.cos(t) * a + math.sin(t) * b) for t in np.linspace(0, 2 * math.pi, n)]


# ---------------------------------------------------------------- Fares
def gold_lame():
    """Crinkled gold lamé fabric (the hat band and the sash)."""
    if "GoldLame" in bpy.data.materials:
        return bpy.data.materials["GoldLame"]
    m, nt, out = new_material("GoldLame")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = 70.0
    n.inputs["Detail"].default_value = 8.0
    n.inputs["Distortion"].default_value = 1.5
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.7
    bump.inputs["Distance"].default_value = 0.004
    b = principled(nt, (0.70, 0.50, 0.20), rough=0.3, metal=0.9)
    nt.links.new(tc.outputs["Object"], n.inputs["Vector"])
    nt.links.new(n.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    return m


def yarn_coloured(name, color):
    m = yarn().copy()
    m.name = name
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*color, 1)
    return m


def oriented(name, center, radii, normal, mat, seg=24, rings=12):
    """An ellipsoid whose local Y axis follows `normal` (for flat patches on a surface)."""
    ob = ellipsoid(name, tuple(center), radii, mat, seg=seg, rings=rings)
    ob.rotation_euler = Vector((-np.asarray(normal)).tolist()).to_track_quat("Y", "Z").to_euler()
    return ob


def bow(name, at, size, mat, facing=(0, -1, 0)):
    """A small ribbon bow: two loops and two tails."""
    f = np.asarray(facing, float)
    f /= np.linalg.norm(f)
    right = np.cross(f, [0, 0, 1.0])
    right /= np.linalg.norm(right)
    parts = []
    for s in (-1, 1):
        loop = [at + right * s * size * (0.55 + 0.45 * math.cos(t)) + np.array([0, 0, 1.0]) * size * 0.45 * math.sin(t)
                for t in np.linspace(0, 2 * math.pi, 16)]
        parts.append(tube(name + "Loop", loop, [size * 0.12] * 16, mat, sides=8, caps=False, squash=0.4))
        tail = [at, at + right * s * size * 0.3 - np.array([0, 0, size * 0.8]),
                at + right * s * size * 0.45 - np.array([0, 0, size * 1.4])]
        parts.append(tube(name + "Tail", tail, [size * 0.12, size * 0.12, size * 0.1], mat, sides=8, squash=0.35))
    parts.append(ellipsoid(name + "Knot", tuple(at), (size * 0.18, size * 0.12, size * 0.18), mat, seg=12, rings=6))
    return parts


def build_fares():
    """Fares as the real rag doll: soft cloth body, embroidered face, yarn hair and mustache."""
    black = fabric("ClothBlack", (0.006, 0.0056, 0.0056), sheen=0.07, rough=0.85, fuzz=0.2, scale=700,
                   sheen_tint=(0.5, 0.5, 0.52))
    red = fabric("ClothRed", (0.40, 0.008, 0.01), sheen=0.06, rough=0.85, fuzz=0.25, scale=700, sheen_tint=(1, 0.3, 0.3))
    green = fabric("ClothGreen", (0.014, 0.045, 0.02), sheen=0.4, rough=0.75, sheen_tint=(0.4, 0.7, 0.45))
    skin = fabric("ClothBeige", (0.66, 0.54, 0.41), sheen=0.12, fuzz=0.15, scale=900)
    lame = gold_lame()
    trim = gold_cord()
    black_yarn = yarn()
    navy_yarn = yarn_coloured("YarnNavy", (0.004, 0.005, 0.013))
    thread = plain("Thread", (0.003, 0.003, 0.003), rough=0.6)
    nose_thread = yarn_coloured("NoseThread", (0.12, 0.02, 0.015))
    ribbon = plain("RibbonWhite", (0.82, 0.78, 0.8), rough=0.22)
    ribbon.node_tree.nodes["Principled BSDF"].inputs["Sheen Weight"].default_value = 0.6
    pink = plain("RibbonPink", (0.6, 0.08, 0.32), rough=0.3)
    parts = []
    add = parts.append
    extend = parts.extend

    # ---------- legs: thin black cloth legs stretched out in front, rounded feet
    for s in (-1, 1):
        add(soften(tube("Leg", [(s * 0.07, -0.08, 0.058), (s * 0.09, -0.25, 0.052), (s * 0.11, -0.42, 0.046)],
                        [0.043, 0.041, 0.038], black, sides=22), 1, 0.006, 0.04))
        add(ellipsoid("Foot", (s * 0.113, -0.46, 0.055), (0.04, 0.046, 0.052), black, rot=(math.radians(-15), 0, 0)))

    # ---------- the long black robe: open over a green vest, skirt spread on the floor
    vest, _ = lathe("Vest", [(0.19, 0.14, 0.11, 0.03), (0.3, 0.142, 0.112, 0.03), (0.4, 0.13, 0.104, 0.03),
                             (0.45, 0.1, 0.085, 0.03)], green)
    add(soften(vest, 2))
    for x in (-0.05, -0.032, -0.014, 0.014, 0.032, 0.05):                  # gold embroidery down the vest
        pts = []
        for z in np.linspace(0.24, 0.44, 9):
            rx, ry = (0.141, 0.111) if z < 0.4 else (0.12, 0.096)
            pts.append((x, 0.03 - ry * math.sqrt(max(0.0, 1 - (x / rx) ** 2)) - 0.0015, z))
        add(tube("VestStripe", pts, [0.0022] * 9, trim, sides=6))
    sash_rows = [(z, 0.158 + 0.006 * math.sin(k * 1.9), 0.128 + 0.006 * math.sin(k * 1.9), 0.03)
                 for k, z in enumerate(np.linspace(0.175, 0.235, 6))]
    sash, _ = lathe("Sash", sash_rows, lame)
    add(soften(sash, 2, 0.006, 0.02))

    def upper_gap(z):
        return math.radians(20 + 12 * max(0.0, (0.42 - z) / 0.22))
    upper, urows = lathe("Robe", [(0.2, 0.158, 0.13, 0.03), (0.28, 0.152, 0.124, 0.03), (0.36, 0.146, 0.118, 0.03),
                                  (0.42, 0.132, 0.106, 0.03), (0.458, 0.092, 0.08, 0.03)], black, gap=upper_gap)
    upper.modifiers.new("thick", "SOLIDIFY").thickness = 0.006
    add(soften(upper, 2, 0.004, 0.05))

    def skirt_gap(z):
        return math.radians(32 + 30 * (0.2 - z) / 0.2)
    skirt, srows = lathe("RobeSkirt", [(0.2, 0.162, 0.134, 0.03), (0.14, 0.19, 0.165, 0.045), (0.08, 0.232, 0.212, 0.055),
                                       (0.035, 0.27, 0.255, 0.06), (0.01, 0.288, 0.275, 0.06)], black, gap=skirt_gap)
    skirt.modifiers.new("thick", "SOLIDIFY").thickness = 0.006
    add(soften(skirt, 2, 0.012, 0.06))
    for rows in (urows, srows):                                            # thin gold trim on the open edges
        for side in (0, -1):
            edge = [np.array(r[side]) + np.array([0, -0.004, 0]) for r in rows]
            add(tube("RobeTrim", edge, [0.0035] * len(edge), trim, sides=8))
    hem = [np.array(p) + np.array([0, 0, 0.004]) for p in srows[-1]]
    add(tube("HemTrim", hem, [0.0035] * len(hem), trim, sides=8))

    # ---------- neck: knotted red scarf, a white satin bow pinned beside it
    scarf = tube("Scarf", [(0.068 * math.cos(a), 0.03 + 0.062 * math.sin(a), 0.452 + 0.006 * math.sin(2 * a))
                           for a in np.linspace(0, 2 * math.pi, 36)], [0.02] * 36, red, sides=14, caps=False, squash=0.7)
    add(soften(scarf, 1, 0.005, 0.02))
    knot = np.array([0.025, -0.035, 0.44])
    add(ellipsoid("ScarfKnot", tuple(knot), (0.022, 0.014, 0.02), red))
    for tail in ([knot, knot + np.array([0.05, -0.012, -0.02]), knot + np.array([0.09, -0.01, -0.035])],
                 [knot, knot + np.array([0.035, -0.018, -0.035]), knot + np.array([0.055, -0.02, -0.07])]):
        add(soften(tube("ScarfTail", tail, [0.016, 0.014, 0.01], red, sides=12, squash=0.35), 1))
    extend(bow("ChestBow", np.array([0.075, -0.09, 0.405]), 0.03, ribbon))
    extend(bow("PinkPin", np.array([-0.075, -0.1, 0.36]), 0.012, pink))

    # ---------- head: round beige cloth with an embroidered face
    hc, hr = (0.0, 0.02, 0.565), (0.112, 0.102, 0.118)
    head = ellipsoid("Head", hc, hr, skin, seg=56, rings=28)
    for vx in head.data.vertices:
        if vx.co.y < 0:
            vx.co.y *= 0.92
    head.data.update()
    add(head)
    for s in (-1, 1):
        ep, en = on_head(hc, hr, s * 0.04, 0.578, 0.001)
        add(oriented("EyeStitch", ep, (0.013, 0.0025, 0.0085), en, thread))
        lid = [on_head(hc, hr, s * x, 0.578 + 0.006 * math.sin((x - 0.024) / 0.032 * math.pi), 0.002)[0]
               for x in np.linspace(0.024, 0.056, 7)]
        lashes = [lid]
        for k in range(4):
            a, an = on_head(hc, hr, s * (0.03 + 0.007 * k), 0.587, 0.002)
            lashes.append([a, a + np.array([s * 0.003, -0.002, 0.008])])
        add(curves("Lashes", lashes, 0.0011, thread, res=1))
        brow = [on_head(hc, hr, s * x, 0.604 + 0.006 * math.sin((x - 0.02) / 0.045 * math.pi), 0.0015)[0]
                for x in np.linspace(0.02, 0.065, 8)]
        add(curves("Brow", [brow], 0.0017, thread, res=1))
    add(curves("Nose", [[on_head(hc, hr, 0.0, z, 0.0015)[0] for z in np.linspace(0.565, 0.54, 5)]], 0.0018, nose_thread, res=1))
    # the thick black yarn mustache: a bundle of strands sweeping out and curling down at the ends
    mus = []
    for s in (-1, 1):
        ctrl = [(0.004, 0.528), (0.03, 0.531), (0.058, 0.524), (0.076, 0.511), (0.082, 0.495)]
        cx = np.array([c[0] for c in ctrl])
        cz = np.array([c[1] for c in ctrl])
        tt = np.linspace(0, 1, len(ctrl))
        for k in range(60):
            dz, dout = rng.uniform(-1, 1), rng.uniform(0, 1)
            strand = []
            for t in np.linspace(0, 1, 14):
                taper = 1 - 0.55 * t
                x = s * np.interp(t, tt, cx)
                z = np.interp(t, tt, cz) + dz * 0.011 * taper
                strand.append(on_head(hc, hr, x, z, 0.004 + dout * 0.012 * taper)[0] + rng.normal(0, 0.0008, 3))
            mus.append(strand)
    add(curves("Mustache", mus, 0.0032, black_yarn))
    # navy curly yarn hair at the sides and back, under the hat
    hair = []
    for k in range(650):
        az = rng.uniform(math.radians(-35), math.radians(215))
        zz = rng.uniform(0.47, 0.63)
        if math.sin(az) < -0.3:
            continue
        cosz = (zz - hc[2]) / hr[2]
        if abs(cosz) >= 1:
            continue
        rad = math.sqrt(1 - cosz ** 2)
        p = np.array([hc[0] + hr[0] * rad * math.cos(az), hc[1] + hr[1] * rad * math.sin(az), zz])
        n = (p - np.array(hc)) / np.array(hr) ** 2
        n /= np.linalg.norm(n)
        side = abs(math.cos(az))
        hair.append(curl(p + n * rng.uniform(0.003, 0.008 + 0.022 * side), n, rng.uniform(0.008, 0.012),
                         rng.uniform(1.3, 2.0), 0.006, 20))
    add(curves("Hair", hair, 0.0034, navy_yarn))

    # ---------- the tarboush: soft red cloth, puffy, wrapped at the base in gold lamé
    prof = [(0.116, 0.615), (0.124, 0.64), (0.13, 0.668), (0.128, 0.695), (0.119, 0.72), (0.104, 0.742),
            (0.083, 0.758), (0.056, 0.769), (0.028, 0.774), (0.0, 0.775)]
    seg = 56
    V, F = [], []
    for r_, z_ in prof:
        for a in np.linspace(0, 2 * math.pi, seg, endpoint=False):
            V.append((r_ * math.cos(a), hc[1] + r_ * math.sin(a), z_))
    for i in range(len(prof) - 1):
        for a in range(seg):
            F.append((i * seg + a, i * seg + (a + 1) % seg, (i + 1) * seg + (a + 1) % seg, (i + 1) * seg + a))
    add(soften(mesh_from("Tarboush", V, F, red), 2, 0.008, 0.04))
    band_rows = [(z, 0.127 + 0.004 * math.sin(k * 2.3), 0.127 + 0.004 * math.sin(k * 2.3), hc[1])
                 for k, z in enumerate(np.linspace(0.615, 0.66, 5))]
    band, _ = lathe("HatBand", band_rows, lame)
    add(soften(band, 2, 0.006, 0.015))

    # ---------- arms: wide black sleeves with gold cuffs, cream mitten hands
    mouth_pt = on_head(hc, hr, -0.02, 0.515, 0.006)[0]
    axis = np.array([0.45, -0.3, 0.84])
    axis /= np.linalg.norm(axis)
    lid_top = mouth_pt + np.array([-0.01, -0.016, -0.004])
    t_center = lid_top - axis * 0.092
    side = np.cross(axis, [0.0, -1.0, 0.0])
    side /= np.linalg.norm(side)
    toward = np.cross(side, axis)
    grip = t_center - axis * 0.02
    wrist = grip - toward * 0.045 + side * 0.03 - axis * 0.02
    right = [(-0.12, 0.03, 0.43), (-0.21, -0.01, 0.37), (-0.2, -0.1, 0.34), tuple(wrist)]
    left = [(0.12, 0.03, 0.43), (0.22, 0.0, 0.39), (0.31, -0.04, 0.33), (0.38, -0.07, 0.29)]
    for pts in (right, left):
        add(soften(tube("Sleeve", pts, [0.05, 0.052, 0.056, 0.062], black, sides=26), 1, 0.008, 0.035))
        w = np.array(pts[-1])
        d = w - np.array(pts[-2])
        add(tube("Cuff", ring_around(w - d / np.linalg.norm(d) * 0.006, d, 0.062), [0.0035] * 30, trim, sides=8,
                 caps=False))
    # right mitten round the tumbler
    add(ellipsoid("RightMitten", tuple(grip - toward * 0.036), (0.034, 0.024, 0.042), skin,
                  rot=tuple(Vector(axis.tolist()).to_track_quat("Z", "Y").to_euler())))
    add(tube("RightThumb", [grip - toward * 0.02 + side * 0.03, grip + side * 0.036, grip + toward * 0.02 + side * 0.03],
             [0.012, 0.0115, 0.01], skin, sides=12))
    # left mitten held out to the side, thumb up, a white ribbon tied at the wrist
    lw = np.array(left[-1])
    ld = lw - np.array(left[-2])
    ld /= np.linalg.norm(ld)
    add(tube("LeftMitten", [lw + ld * 0.005, lw + ld * 0.04, lw + ld * 0.075], [0.03, 0.036, 0.026], skin, sides=20,
             squash=0.65))
    add(tube("LeftThumb", [lw + ld * 0.025 + np.array([0, -0.004, 0.02]), lw + ld * 0.04 + np.array([0, -0.006, 0.042])],
             [0.012, 0.01], skin, sides=12))
    add(tube("WristRibbon", ring_around(lw - ld * 0.004, ld, 0.05), [0.003] * 30, ribbon, sides=6, caps=False))
    for k in range(2):
        add(tube("WristRibbonTail", [lw + np.array([0, -0.04, -0.03]), lw + np.array([0.005 * k, -0.05, -0.08]),
                                     lw + np.array([0.012 * k - 0.004, -0.045, -0.12])], [0.0035, 0.003, 0.0025],
                 ribbon, sides=6, squash=0.4))
    # a white pin badge on the left sleeve
    badge = bpy.data.objects.new("BadgeRig", None)
    link(badge)
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.017, depth=0.004)
    disc = bpy.context.active_object
    disc.data.materials.append(plain("BadgeWhite", (0.8, 0.8, 0.8), rough=0.3, coat=0.8))
    disc.parent = badge
    bp = np.array([0.23, -0.045, 0.39])
    badge.location = tuple(bp)
    badge.rotation_euler = Vector((0.4, -1.0, 0.2)).to_track_quat("Z", "Y").to_euler()
    add(badge)

    # the white LeMSIC tumbler
    rig = bpy.data.objects.new("TumblerRig", None)
    link(rig)
    bpy.ops.mesh.primitive_cone_add(vertices=48, radius1=0.026, radius2=0.031, depth=0.15, location=(0, 0, -0.008))
    body = bpy.context.active_object
    body.data.materials.append(tumbler_material())
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=0.0318, depth=0.012, location=(0, 0, 0.073))
    steel = bpy.context.active_object
    steel.data.materials.append(plain("Steel", (0.75, 0.75, 0.76), rough=0.22, metal=1.0))
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=0.033, depth=0.02, location=(0, 0, 0.089))
    lid = bpy.context.active_object
    lid.data.materials.append(plain("SmokyLid", (0.03, 0.03, 0.035), rough=0.12, coat=1.0))
    for ob in (body, steel, lid):
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.shade_smooth()
        ob.parent = rig
    rig.location = tuple(t_center)
    rig.rotation_euler = Vector(axis.tolist()).to_track_quat("Z", "Y").to_euler()
    add(rig)

    root = bpy.data.objects.new("Fares", None)
    link(root)
    for ob in parts:
        if ob.parent is None:
            ob.parent = root
    return root


if __name__ == "__main__":
    import sys
    sys.path.insert(0, HERE)
    import lemsic_tree as T
    view = sys.argv[-1] if sys.argv[-1] in ("front", "cabin") else "front"
    scene = T.reset_scene()
    build_fares()
    cam_data = bpy.data.cameras.new("Cam")
    cam_data.lens = 60
    cam = link(bpy.data.objects.new("Cam", cam_data))
    cam.location = (0.15, -1.75, 0.62) if view == "front" else (-0.9, -2.6, 1.2)
    cam.rotation_euler = (Vector((0, 0, 0.37)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    for loc, power, size in (((-1.2, -1.6, 1.6), 260, 1.6), ((1.6, -1.0, 1.0), 90, 1.2), ((0.3, 1.4, 1.6), 140, 1.0)):
        ld = bpy.data.lights.new("L", "AREA")
        ld.energy = power
        ld.size = size
        ob = link(bpy.data.objects.new("L", ld))
        ob.location = loc
        ob.rotation_euler = (Vector((0, 0, 0.45)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    bpy.ops.mesh.primitive_plane_add(size=8)
    bpy.context.active_object.data.materials.append(plain("Floor", (0.35, 0.36, 0.38), rough=0.7))
    world = bpy.data.worlds.new("W")
    scene.world = world
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.09, 0.16, 0.3, 1)
    r = scene.render
    r.engine = "CYCLES"
    r.resolution_x, r.resolution_y = 720, 900
    scene.cycles.samples = 64
    scene.cycles.use_denoising = True
    scene.view_settings.view_transform = "AgX"
    out = os.path.join(os.path.dirname(os.path.dirname(HERE)), "build", "fares-preview.png")
    r.filepath = out
    bpy.ops.render.render(write_still=True)
    print("wrote", out)
