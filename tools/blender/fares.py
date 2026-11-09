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
    b = principled(nt, (0.006, 0.0055, 0.0055), rough=0.62)
    b.inputs["Sheen Weight"].default_value = 0.35
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
    u.inputs[1].default_value = 1 / 0.052; u.inputs[2].default_value = 0.5
    v = nt.nodes.new("ShaderNodeMath"); v.operation = "MULTIPLY_ADD"
    v.inputs[1].default_value = 1 / 0.044; v.inputs[2].default_value = 0.5
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
def build_fares():
    black = fabric("FleeceBlack", (0.006, 0.0055, 0.0055), sheen=0.14, sheen_tint=(0.5, 0.5, 0.52))
    red = fabric("FeltRed", (0.30, 0.006, 0.006), sheen=0.08, fuzz=0.45, scale=900, sheen_tint=(1, 0.4, 0.4))
    scarf_red = fabric("ScarfRed", (0.42, 0.015, 0.018), sheen=0.3, rough=0.7)
    green = fabric("VelvetGreen", (0.012, 0.035, 0.016), sheen=0.6, rough=0.75, sheen_tint=(0.4, 0.7, 0.45))
    satin = fabric("SatinSash", (0.45, 0.37, 0.24), sheen=0.4, rough=0.38, fuzz=0.15, scale=200)
    skin = fabric("FaceCotton", (0.80, 0.68, 0.56), sheen=0.25, fuzz=0.1, scale=900)
    skin.node_tree.nodes["Principled BSDF"].inputs["Subsurface Weight"].default_value = 0.2
    white = fabric("FeltWhite", (0.78, 0.78, 0.76), sheen=0.3)
    gold = gold_cord()
    yn = yarn()
    bead = plain("EyeBead", (0.012, 0.007, 0.005), rough=0.06, coat=1.0)
    lip = fabric("FeltLip", (0.36, 0.02, 0.03), sheen=0.2)
    parts = []
    add = parts.append

    # ---------- sherwal: a baggy seat and two billowing legs, gathered at the ankle
    seat = ellipsoid("Seat", (0, 0.04, 0.125), (0.19, 0.17, 0.125), black)
    add(soften(seat, 1, 0.012, 0.05))
    for s in (-1, 1):
        leg = tube("Leg", [(s * 0.09, -0.02, 0.13), (s * 0.105, -0.17, 0.14), (s * 0.115, -0.31, 0.12),
                           (s * 0.12, -0.42, 0.095), (s * 0.122, -0.47, 0.085)],
                   [0.1, 0.104, 0.092, 0.07, 0.048], black, sides=28)
        add(soften(leg, 1, 0.014, 0.045))
        cuff = tube("AnkleCuff", [(s * 0.122, -0.455, 0.086), (s * 0.123, -0.478, 0.084)], [0.05, 0.05], black, sides=24)
        add(soften(cuff, 1))
        add(ellipsoid("Shoe", (s * 0.125, -0.53, 0.085), (0.05, 0.08, 0.052), black, rot=(math.radians(-38), 0, 0)))

    # ---------- body: vest, sash and the open jacket
    def jacket_gap(z):
        return math.radians(26 + 24 * max(0.0, (0.3 - z) / 0.14))     # opens wider towards the hem
    vest, _ = lathe("Vest", [(0.22, 0.135, 0.105, 0.03), (0.32, 0.14, 0.11, 0.03), (0.42, 0.135, 0.105, 0.03),
                             (0.5, 0.11, 0.09, 0.03), (0.54, 0.075, 0.07, 0.03)], green)
    add(soften(vest, 2))
    for z in np.linspace(0.29, 0.5, 9):                                    # gold buttons
        ry = 0.11 if z < 0.45 else 0.092
        add(ellipsoid("Button", (0.0, 0.03 - ry - 0.002, z), (0.007, 0.005, 0.007), gold, seg=12, rings=6))
    for s in (-1, 1):                                                      # gold braid down the vest
        zs = np.linspace(0.29, 0.5, 10)
        pts = [(s * 0.03, 0.03 - (0.107 if z < 0.45 else 0.09) - 0.001, z) for z in zs]
        add(tube("VestBraid", pts, [0.0035] * len(pts), gold, sides=8))
    sash_rows = []
    for k, z in enumerate(np.linspace(0.19, 0.29, 7)):
        bulge = 0.012 * math.sin(k / 6 * math.pi) + 0.004 * math.sin(k * 2.7)
        sash_rows.append((z, 0.165 + bulge, 0.135 + bulge, 0.03))
    sash, _ = lathe("Sash", sash_rows, satin)
    add(soften(sash, 2, 0.008, 0.03))
    jacket, rows = lathe("Jacket", [(0.16, 0.2, 0.17, 0.035), (0.2, 0.18, 0.15, 0.03), (0.28, 0.165, 0.13, 0.03),
                                    (0.38, 0.165, 0.13, 0.03), (0.46, 0.16, 0.12, 0.03), (0.52, 0.13, 0.1, 0.03),
                                    (0.555, 0.085, 0.075, 0.03)], black, gap=jacket_gap)
    sol = jacket.modifiers.new("thick", "SOLIDIFY")
    sol.thickness = 0.01
    add(soften(jacket, 2, 0.006, 0.05))
    for side in (0, -1):                                                   # braid along both open edges
        edge = [np.array(r[side]) for r in rows]
        edge = [e + (e - np.array([0, 0.03, e[2]])) * 0.05 for e in edge]
        add(tube("EdgeBraid", edge, [0.006] * len(edge), gold, sides=10))
    hem = [np.array(p) * np.array([1.04, 1.04, 1]) for p in rows[0]]
    add(tube("HemBraid", hem, [0.006] * len(hem), gold, sides=10))

    # ---------- scarf
    sc = tube("Scarf", [(0.075 * math.cos(a), 0.03 + 0.07 * math.sin(a), 0.548 + 0.008 * math.sin(3 * a))
                        for a in np.linspace(0, 2 * math.pi, 40)], [0.024] * 40, scarf_red, sides=16, caps=False,
              squash=0.7)
    add(soften(sc, 1, 0.006, 0.02))
    tip = mesh_from("ScarfTip", [(0.0, -0.045, 0.55), (0.07, -0.05, 0.545), (0.05, -0.058, 0.515), (0.015, -0.055, 0.52)],
                    [(0, 1, 2, 3)], white)
    tip.modifiers.new("thick", "SOLIDIFY").thickness = 0.006
    add(soften(tip, 2))

    # ---------- head: soft cream fabric, a little wider at the jaw
    hc, hr = (0.0, 0.025, 0.665), (0.128, 0.115, 0.14)
    head = ellipsoid("Head", hc, hr, skin, seg=56, rings=28)
    for vx in head.data.vertices:              # widen the jaw, flatten the face a touch
        x, y, z = vx.co
        if z < 0:
            vx.co.x = x * (1 + 0.06 * (-z))
        if y < 0:
            vx.co.y = y * 0.93
    head.data.update()
    add(head)
    nose_p, _ = on_head(hc, hr, 0.0, 0.648)
    add(ellipsoid("Nose", tuple(nose_p - np.array([0, 0.004, 0])), (0.016, 0.012, 0.014),
                  fabric("NoseCotton", (0.8, 0.6, 0.5), sheen=0.2, fuzz=0.1, scale=900)))
    catch = plain("Catch", (0.9, 0.9, 0.9), rough=0.2)
    for s in (-1, 1):
        ep, en = on_head(hc, hr, s * 0.043, 0.68)
        add(ellipsoid("EyeWhite", tuple(ep - en * 0.003), (0.017, 0.006, 0.019), white, seg=24, rings=12))
        add(ellipsoid("EyeBead", tuple(ep + en * 0.002), (0.0115, 0.006, 0.0125), bead, seg=20, rings=10))
        add(ellipsoid("Catchlight", tuple(ep + en * 0.008 + np.array([-0.003 * s, 0, 0.004])),
                      (0.0025, 0.0015, 0.0025), catch, seg=8, rings=4))
        lashes = []
        for k in range(4):
            a, an = on_head(hc, hr, s * (0.03 + 0.008 * k), 0.697, 0.002)
            lashes.append([a, a + an * 0.006 + np.array([s * 0.004, 0, 0.007])])
        add(curves("Lashes", lashes, 0.0011, yn, res=1))
        brow = []                              # looped yarn eyebrows, inner ends lower
        for k in range(26):
            f = rng.uniform(0, 1)
            x = s * (0.018 + 0.06 * f)
            z = 0.718 + 0.012 * math.sin(f * math.pi) - 0.008 * (1 - f) + rng.normal(0, 0.003)
            p, n = on_head(hc, hr, x, z, 0.004)
            brow.append(curl(p, n, rng.uniform(0.004, 0.006), 1.4, 0.004, 16))
        add(curves("Brow", brow, 0.0028, yn))

    # bushy yarn mustache: two lobes sweeping out under the nose, the ends curling down
    mus = []
    for s in (-1, 1):
        for k in range(230):
            f = rng.uniform(0, 1) ** 0.85
            x = s * (0.006 + 0.082 * f)
            zc = 0.628 - 0.018 * f ** 2.2
            half_h = 0.019 * (1 - 0.55 * f) + 0.006
            z = zc + rng.uniform(-half_h, half_h)
            p, n = on_head(hc, hr, x, z, rng.uniform(0.004, 0.022) * (1 - 0.4 * f))
            mus.append(curl(p, n, rng.uniform(0.006, 0.009), rng.uniform(1.2, 1.8), 0.005, 18))
    add(curves("Mustache", mus, 0.0032, yn))
    mouth = [on_head(hc, hr, x, 0.6 - 0.006 * (1 - (x / 0.018) ** 2), 0.002)[0] for x in np.linspace(-0.018, 0.018, 7)]
    add(tube("Mouth", mouth, [0.0045] * 7, lip, sides=8))

    # black curly yarn hair: round the back and sides below the tarboush, full at the sides
    hair = []
    for k in range(900):
        az = rng.uniform(math.radians(-40), math.radians(220))           # 0 = his left side, 90 = back
        zz = rng.uniform(0.555, 0.745)
        if math.sin(az) < -0.35:                                           # keep the face clear
            continue
        cosz = (zz - hc[2]) / hr[2]
        if abs(cosz) >= 1:
            continue
        rad = math.sqrt(1 - cosz ** 2)
        p = np.array([hc[0] + hr[0] * rad * math.cos(az) * (1 + 0.06 * max(0, -cosz)),
                      hc[1] + hr[1] * rad * math.sin(az), zz])
        n = (p - np.array(hc)) / np.array(hr) ** 2
        n /= np.linalg.norm(n)
        side = abs(math.cos(az))
        volume = 0.008 + 0.03 * side * (1 - abs(cosz)) + rng.uniform(0, 0.012)
        hair.append(curl(p + n * rng.uniform(0.003, volume), n, rng.uniform(0.009, 0.014), rng.uniform(1.3, 2.0), 0.006, 22))
    add(curves("Hair", hair, 0.0038, yn))

    # ---------- tarboush: red felt, a twisted gold cord round the base, a black yarn pom-pom
    base, height = 0.732, 0.15
    prof = [(0.132, base - 0.012), (0.134, base + 0.02), (0.13, base + 0.08), (0.124, base + height - 0.02),
            (0.112, base + height - 0.004), (0.08, base + height + 0.004), (0.0, base + height + 0.008)]
    seg = 56
    V, F = [], []
    for r_, z_ in prof:
        for a in np.linspace(0, 2 * math.pi, seg, endpoint=False):
            V.append((r_ * math.cos(a), hc[1] + r_ * math.sin(a), z_))
    for i in range(len(prof) - 1):
        for a in range(seg):
            F.append((i * seg + a, i * seg + (a + 1) % seg, (i + 1) * seg + (a + 1) % seg, (i + 1) * seg + a))
    fez = soften(mesh_from("Tarboush", V, F, red), 2, 0.003, 0.03)
    add(fez)
    plies = []
    for ph in (0.0, math.pi):
        pts = []
        for u in np.linspace(0, 2 * math.pi, 600):
            c = np.array([0.139 * math.cos(u), hc[1] + 0.139 * math.sin(u), base + 0.012])
            nrm = np.array([math.cos(u), math.sin(u), 0.0])
            w = 46 * u + ph
            pts.append(c + 0.008 * (math.cos(w) * nrm + math.sin(w) * np.array([0, 0, 1.0])))
        plies.append(pts)
    add(curves("GoldCord", plies, 0.0078, gold, res=3))
    knot_at = np.array([-0.142, hc[1] - 0.02, base + 0.012])
    add(ellipsoid("CordKnot", tuple(knot_at), (0.02, 0.022, 0.024), gold))
    ends = [[knot_at + np.array([-0.004 + 0.003 * math.sin(t * 6), -0.008 * k, -0.01 - 0.012 * t])
             for t in np.linspace(0, 3, 12)] for k in range(2)]
    add(curves("CordEnds", ends, 0.0065, gold))
    top = np.array([0.012, hc[1] + 0.018, base + height + 0.006])
    pom = []
    for k in range(110):
        d = np.array([rng.normal(0.15, 0.4), rng.normal(0.25, 0.4), rng.uniform(0.5, 1.0)])
        d /= np.linalg.norm(d)
        L = rng.uniform(0.04, 0.085)
        wob = rng.normal(0, 1, 3)
        pom.append([top + d * L * t + wob * 0.004 * math.sin(t * 5) for t in np.linspace(0, 1, 8)])
    add(curves("PomPom", pom, 0.0026, yn))

    # ---------- arms: the right hand holds the tumbler to his lips, the left rests on his knee
    mouth_pt = on_head(hc, hr, -0.03, 0.598, 0.004)[0]
    axis = np.array([0.42, -0.35, 0.84])
    axis /= np.linalg.norm(axis)
    lid_top = mouth_pt + np.array([-0.012, -0.02, -0.004])
    t_center = lid_top - axis * 0.11                                    # middle of the tumbler
    side = np.cross(axis, [0.0, -1.0, 0.0])
    side /= np.linalg.norm(side)
    toward = np.cross(side, axis)
    grip = t_center - axis * 0.035
    wrist = grip - toward * 0.05 + side * 0.04 - axis * 0.015
    right = [(-0.15, 0.03, 0.47), (-0.215, -0.02, 0.37), (-0.2, -0.09, 0.33), tuple(wrist)]
    left = [(0.15, 0.03, 0.47), (0.21, 0.0, 0.35), (0.205, -0.09, 0.285), (0.16, -0.2, 0.27)]
    for pts in (right, left):
        sl = tube("Sleeve", pts, [0.054, 0.052, 0.048, 0.043], black, sides=26)
        add(soften(sl, 1, 0.01, 0.035))
        w = np.array(pts[-1])
        d = w - np.array(pts[-2])
        add(tube("CuffBraid", ring_around(w - d / np.linalg.norm(d) * 0.012, d, 0.046), [0.0055] * 30, gold,
                 sides=8, caps=False))
    # right hand round the tumbler: palm behind it, fingers wrapped across the front, thumb above
    add(ellipsoid("Palm", tuple(grip - toward * 0.042), (0.036, 0.022, 0.04), skin,
                  rot=tuple(Vector(axis.tolist()).to_track_quat("Z", "Y").to_euler())))
    for k in range(4):
        h = -0.03 + 0.017 * k
        arc = [grip + axis * h + 0.041 * (math.cos(a) * -toward + math.sin(a) * side) for a in np.linspace(-1.9, 0.6, 9)]
        add(tube("Finger", arc, [0.0105, 0.011, 0.011, 0.0105, 0.01, 0.0095, 0.009, 0.0085, 0.008], skin, sides=12))
    thumb = [grip + axis * 0.035 - toward * 0.03 + side * 0.03, grip + axis * 0.04 + side * 0.04,
             grip + axis * 0.035 + toward * 0.025 + side * 0.035]
    add(tube("Thumb", thumb, [0.012, 0.0115, 0.01], skin, sides=12))
    lw = np.array(left[-1])                                             # left hand resting on the knee
    ld = np.array([-0.15, -1.0, -0.25])
    ld /= np.linalg.norm(ld)
    add(tube("LeftHand", [lw + ld * 0.01, lw + ld * 0.045, lw + ld * 0.075], [0.03, 0.036, 0.026], skin, sides=20,
             squash=0.6))
    add(tube("LeftThumb", [lw + ld * 0.025 + np.array([-0.03, 0, 0.012]), lw + ld * 0.05 + np.array([-0.04, 0, 0.016])],
             [0.012, 0.01], skin, sides=12))

    # the white LeMSIC tumbler with its steel ring and smoky lid
    rig = bpy.data.objects.new("TumblerRig", None)
    link(rig)
    bpy.ops.mesh.primitive_cone_add(vertices=48, radius1=0.031, radius2=0.037, depth=0.18, location=(0, 0, -0.01))
    body = bpy.context.active_object
    body.data.materials.append(tumbler_material())
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=0.0378, depth=0.014, location=(0, 0, 0.087))
    steel = bpy.context.active_object
    steel.data.materials.append(plain("Steel", (0.75, 0.75, 0.76), rough=0.22, metal=1.0))
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=0.039, depth=0.024, location=(0, 0, 0.105))
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
    cam.location = (0.35, -1.9, 0.72) if view == "front" else (-0.9, -2.6, 1.2)
    cam.rotation_euler = (Vector((0, 0, 0.44)) - cam.location).to_track_quat("-Z", "Y").to_euler()
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
