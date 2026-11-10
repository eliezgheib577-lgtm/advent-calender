"""Fares, the LeMSIC mascot rag doll, in his rocking chair (Blender, Cycles).

Built the way the real doll is made, so it renders as a stuffed fabric toy rather
than a cartoon:

  * stuffed parts (the mitten hands, the tarboush) are cloth meshes inflated with
    Blender's cloth pressure solver, with the seams drawn in so the panels puff out
    between them;
  * the long black robe and the sleeves are cloth simulations: pinned at the shoulders
    and waist and dropped under gravity onto his body, the chair seat and the armrests,
    then edged with a flat gold braid that follows the simulated hem;
  * the face is cream stockinette with glossy black safety eyes, satin-stitched brows
    and eyelashes, red felt lips and a compact curly-yarn mustache; curly black yarn
    hair under a red tarboush with a twisted gold lame band and a yarn pom-pom.

He sits back in a varnished wooden rocking chair, legs hanging over the seat, arms
along the armrests with his mittens resting on the scrolled ends. The chair rocks on
its rockers about ROCKER_CENTRE (see rock_matrix), which cabin_rock.py uses to render
him rocking.

    build_fares()  -> an Empty; move and turn it to place him. Built facing -Y.
    python tools/blender/fares.py [front|face|cabin]  renders build/fares-<view>.png
"""
import math
import os
from collections import defaultdict

import numpy as np
import bpy
import bmesh
from mathutils import Matrix, Vector

from lemsic_tree import link, new_material, principled

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, "textures")
rng = np.random.default_rng(1964)

# ---------------------------------------------------------------- pose and chair
# Doll units: the cabin scales him (and his chair) 1.2x, so 1 unit = 1.2 m.
SEAT_Z = 0.36                    # top of the chair seat
ARM_Z = 0.55                     # top of the armrests
RECLINE = math.radians(14)       # the chair back leans back this much
ROCKER_R = 0.92                  # radius of the rockers' curve
ROCKER_Y = -0.02                 # where the rockers touch the floor at rest
ROCKER_CENTRE = Vector((0.0, ROCKER_Y, ROCKER_R))

LEAN = math.radians(-13)         # he leans back into the chair (about X)
PIVOT = Vector((0.0, 0.03, 0.07))
NECK = Vector((0.0, 0.03, 0.455))
TILT = math.radians(9)           # head tips forward a little, so he looks out into the room
ROLL = math.radians(4)
HC = np.array([0.0, 0.02, 0.578])  # head centre and radii, head-local (upright)
HR = np.array([0.115, 0.104, 0.122])

M_SEAT = Matrix.Translation((0.0, 0.0, SEAT_Z))
M_UP = M_SEAT @ Matrix.Translation(PIVOT) @ Matrix.Rotation(LEAN, 4, "X") @ Matrix.Translation(-PIVOT)
M_HEAD = (M_UP @ Matrix.Translation(NECK) @ Matrix.Rotation(TILT, 4, "X") @ Matrix.Rotation(ROLL, 4, "Y")
          @ Matrix.Translation(-NECK))


def rock_matrix(angle):
    """Doll-local transform of the chair (and Fares) rocked forward by `angle` radians:
    the rockers roll on the floor, so the curve's centre moves forward as it tips."""
    roll = Matrix.Translation((0.0, -ROCKER_R * angle, 0.0))
    return roll @ Matrix.Translation(ROCKER_CENTRE) @ Matrix.Rotation(angle, 4, "X") @ Matrix.Translation(-ROCKER_CENTRE)


# ---------------------------------------------------------------- node helpers
def _set(nt, sock, val):
    if isinstance(val, bpy.types.NodeSocket):
        nt.links.new(val, sock)
    else:
        sock.default_value = val


def _math(nt, op, a, b=0.0, c=None, clamp=False):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    n.use_clamp = clamp
    _set(nt, n.inputs[0], a)
    _set(nt, n.inputs[1], b)
    if c is not None:
        _set(nt, n.inputs[2], c)
    return n.outputs[0]


def _noise(nt, vec, scale, detail=4.0, rough=0.5, distortion=0.0, dims="3D", w=None):
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.noise_dimensions = dims
    _set(nt, n.inputs["Vector"], vec)
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = rough
    n.inputs["Distortion"].default_value = distortion
    if w is not None:
        _set(nt, n.inputs["W"], w)
    return n


def _bump(nt, height, strength, distance, normal=None):
    b = nt.nodes.new("ShaderNodeBump")
    b.inputs["Strength"].default_value = strength
    b.inputs["Distance"].default_value = distance
    _set(nt, b.inputs["Height"], height)
    if normal is not None:
        _set(nt, b.inputs["Normal"], normal)
    return b.outputs["Normal"]


def _cached(name):
    return bpy.data.materials.get("Fares " + name)


def _new_material(name):
    """Fares' materials get their own names, so they never pick up a cabin material of the same name."""
    return new_material("Fares " + name)


# ---------------------------------------------------------------- materials
def fabric(name, color, rough=0.9, sheen=0.35, sheen_rough=0.5, tint=(1, 1, 1), fibre=0.25, scale=900.0,
           mottle=0.12, sss=0.0):
    """Felt, fleece, cotton: matte, a soft sheen at grazing angles, fibrous bump, slight mottling."""
    if _cached(name):
        return _cached(name)
    m, nt, out = _new_material(name)
    tc = nt.nodes.new("ShaderNodeTexCoord").outputs["Object"]
    fine = _noise(nt, tc, scale, 8.0, 0.6)
    pill = _noise(nt, tc, scale * 0.12, 3.0, 0.5)
    mott = _noise(nt, tc, 22.0, 3.0, 0.5)
    hsv = nt.nodes.new("ShaderNodeHueSaturation")
    hsv.inputs["Color"].default_value = (*color, 1)
    _set(nt, hsv.inputs["Value"], _math(nt, "MULTIPLY_ADD", mott.outputs["Fac"], 2 * mottle, 1 - mottle))
    height = _math(nt, "MULTIPLY_ADD", pill.outputs["Fac"], 0.5, fine.outputs["Fac"])
    b = principled(nt, color, rough=rough)
    nt.links.new(hsv.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Sheen Weight"].default_value = sheen
    b.inputs["Sheen Roughness"].default_value = sheen_rough
    b.inputs["Sheen Tint"].default_value = (*tint, 1)
    b.inputs["Specular IOR Level"].default_value = 0.35
    if sss:
        b.inputs["Subsurface Weight"].default_value = sss
        b.inputs["Subsurface Radius"].default_value = (1.0, 0.55, 0.35)
        b.inputs["Subsurface Scale"].default_value = 0.004
    nt.links.new(_bump(nt, height, fibre, 0.0009), b.inputs["Normal"])
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    return m


def face_fabric():
    """Cream cotton stockinette over stuffing, a touch of blush on the cheeks and nose."""
    if _cached("FaceKnit"):
        return _cached("FaceKnit")
    base = (0.62, 0.49, 0.36)
    m = fabric("FaceKnit", base, rough=0.8, sheen=0.3, sheen_rough=0.45, tint=(1, 0.9, 0.8), fibre=0.18,
               scale=1400, mottle=0.06, sss=0.12)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    hsv = nt.nodes["Hue/Saturation/Value"]
    tc = nt.nodes["Texture Coordinate"].outputs["Object"]
    blush = None
    for c, r, k in (((0.052, -0.07, 0.548), 0.026, 0.55), ((-0.052, -0.07, 0.548), 0.026, 0.55),
                    ((0.0, -0.088, 0.566), 0.011, 0.7)):
        d = nt.nodes.new("ShaderNodeVectorMath")
        d.operation = "DISTANCE"
        _set(nt, d.inputs[0], tc)
        d.inputs[1].default_value = c
        f = _math(nt, "MULTIPLY", _math(nt, "SUBTRACT", 1.0, _math(nt, "DIVIDE", d.outputs["Value"], r), clamp=True), k)
        blush = f if blush is None else _math(nt, "MAXIMUM", blush, f)
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    _set(nt, mix.inputs["Factor"], _math(nt, "POWER", blush, 1.6))
    nt.links.new(hsv.outputs["Color"], mix.inputs["A"])
    mix.inputs["B"].default_value = (0.72, 0.34, 0.28, 1)
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    return m


def satin(name, color, rough=0.32, sheen=0.25, metal=0.0, crease=0.4, scale=45.0):
    """Satin / taffeta: glossy weave with soft crushed creases."""
    if _cached(name):
        return _cached(name)
    m, nt, out = _new_material(name)
    tc = nt.nodes.new("ShaderNodeTexCoord").outputs["Object"]
    cr = _noise(nt, tc, scale, 6.0, 0.55, distortion=0.6)
    weave = _noise(nt, tc, 2200.0, 2.0, 0.5)
    b = principled(nt, color, rough=rough, metal=metal)
    b.inputs["Sheen Weight"].default_value = sheen
    b.inputs["Sheen Roughness"].default_value = 0.3
    n = _bump(nt, weave.outputs["Fac"], 0.12, 0.0004)
    nt.links.new(_bump(nt, cr.outputs["Fac"], crease, 0.003, n), b.inputs["Normal"])
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    return m


def yarn(name="Yarn", color=(0.006, 0.0055, 0.0055)):
    """Wool yarn: twisted plies, a woolly sheen."""
    if _cached(name):
        return _cached(name)
    m, nt, out = _new_material(name)
    tc = nt.nodes.new("ShaderNodeTexCoord").outputs["Object"]
    w = nt.nodes.new("ShaderNodeTexWave")
    w.wave_type = "BANDS"
    w.bands_direction = "DIAGONAL"
    _set(nt, w.inputs["Vector"], tc)
    w.inputs["Scale"].default_value = 380.0
    w.inputs["Distortion"].default_value = 6.0
    w.inputs["Detail"].default_value = 3.0
    fuzz = _noise(nt, tc, 2500.0, 4.0, 0.6)
    b = principled(nt, color, rough=0.6)
    b.inputs["Sheen Weight"].default_value = 0.15
    b.inputs["Sheen Roughness"].default_value = 0.45
    b.inputs["Sheen Tint"].default_value = (0.4, 0.4, 0.43, 1)
    b.inputs["Specular IOR Level"].default_value = 0.4
    n = _bump(nt, w.outputs["Fac"], 0.8, 0.0012)
    nt.links.new(_bump(nt, fuzz.outputs["Fac"], 0.3, 0.0004, n), b.inputs["Normal"])
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    return m


def thread(name="Thread", color=(0.006, 0.006, 0.006)):
    """Embroidery floss: glossy, finely twisted."""
    if _cached(name):
        return _cached(name)
    m, nt, out = _new_material(name)
    tc = nt.nodes.new("ShaderNodeTexCoord").outputs["Object"]
    w = nt.nodes.new("ShaderNodeTexWave")
    w.bands_direction = "DIAGONAL"
    _set(nt, w.inputs["Vector"], tc)
    w.inputs["Scale"].default_value = 1500.0
    b = principled(nt, color, rough=0.42)
    b.inputs["Sheen Weight"].default_value = 0.12
    b.inputs["Sheen Roughness"].default_value = 0.3
    nt.links.new(_bump(nt, w.outputs["Fac"], 0.5, 0.0003), b.inputs["Normal"])
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    return m


def gold_braid():
    """Woven metallic gold braid (the jacket edging and cuffs)."""
    if _cached("GoldBraid"):
        return _cached("GoldBraid")
    m, nt, out = _new_material("GoldBraid")
    tc = nt.nodes.new("ShaderNodeTexCoord").outputs["Object"]
    w = nt.nodes.new("ShaderNodeTexWave")
    w.bands_direction = "DIAGONAL"
    _set(nt, w.inputs["Vector"], tc)
    w.inputs["Scale"].default_value = 520.0
    w.inputs["Distortion"].default_value = 1.5
    tone = _noise(nt, tc, 300.0, 3.0)
    hsv = nt.nodes.new("ShaderNodeHueSaturation")
    hsv.inputs["Color"].default_value = (0.78, 0.55, 0.24, 1)
    _set(nt, hsv.inputs["Value"], _math(nt, "MULTIPLY_ADD", tone.outputs["Fac"], 0.5, 0.75))
    b = principled(nt, (0.78, 0.55, 0.24), rough=0.34, metal=1.0)
    nt.links.new(hsv.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(_bump(nt, w.outputs["Fac"], 0.9, 0.0007), b.inputs["Normal"])
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    return m


def gold_lame():
    """Crinkled gold lame (the hat band)."""
    if _cached("GoldLame"):
        return _cached("GoldLame")
    m, nt, out = _new_material("GoldLame")
    tc = nt.nodes.new("ShaderNodeTexCoord").outputs["Object"]
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.feature = "F1"
    _set(nt, vor.inputs["Vector"], tc)
    vor.inputs["Scale"].default_value = 160.0
    n = _noise(nt, tc, 60.0, 8.0, 0.6, distortion=1.2)
    b = principled(nt, (0.80, 0.60, 0.28), rough=0.28, metal=1.0)
    nb = _bump(nt, vor.outputs["Distance"], 0.5, 0.0012)
    nt.links.new(_bump(nt, n.outputs["Fac"], 0.6, 0.003, nb), b.inputs["Normal"])
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    return m


def plain(name, color, rough=0.5, metal=0.0, coat=0.0, transmission=0.0, ior=1.45):
    if _cached(name):
        return _cached(name)
    m, nt, out = _new_material(name)
    b = principled(nt, color, rough=rough, metal=metal, coat=coat)
    b.inputs["Transmission Weight"].default_value = transmission
    b.inputs["IOR"].default_value = ior
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    return m


# ---------------------------------------------------------------- geometry helpers
def mesh_from(name, verts, faces, mat, smooth=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(map(float, p)) for p in verts], [], [tuple(map(int, f)) for f in faces])
    me.update()
    if smooth:
        me.polygons.foreach_set("use_smooth", np.ones(len(me.polygons), bool))
    if mat is not None:
        me.materials.append(mat)
    return link(bpy.data.objects.new(name, me))


def place(ob, M):
    ob.matrix_world = M @ ob.matrix_basis
    return ob


def subsurf(ob, levels=1):
    s = ob.modifiers.new("smooth", "SUBSURF")
    s.levels = s.render_levels = levels
    return ob


def wrinkles(ob, strength, size, depth=2):
    tex = bpy.data.textures.new(ob.name + "Wrinkles", "CLOUDS")
    tex.noise_scale = size
    tex.noise_depth = depth
    d = ob.modifiers.new("wrinkles", "DISPLACE")
    d.texture = tex
    d.strength = strength
    d.mid_level = 0.5
    d.texture_coords = "OBJECT"
    return ob


def bake(ob):
    """Apply the whole modifier stack."""
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    ob.modifiers.clear()
    old = ob.data
    ob.data = me
    if old.users == 0:
        bpy.data.meshes.remove(old)
    return ob


def smooth_shade(ob):
    ob.data.polygons.foreach_set("use_smooth", np.ones(len(ob.data.polygons), bool))
    return ob


def ellipsoid(name, center, radii, mat, seg=40, rings=20):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=rings, radius=1.0, location=tuple(center))
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = tuple(radii)
    ob.data.materials.append(mat)
    smooth_shade(ob)
    return ob


def oriented(name, center, radii, normal, mat, seg=24, rings=12, up=(0, 0, 1)):
    """An ellipsoid whose local Y axis points into the surface along -normal."""
    ob = ellipsoid(name, center, radii, mat, seg=seg, rings=rings)
    q = Vector((-np.asarray(normal)).tolist()).to_track_quat("Y", "Z")
    ob.rotation_euler = q.to_euler()
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


def resample(points, n):
    P = np.asarray(points, float)
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    t = np.linspace(0, s[-1], n)
    return np.stack([np.interp(t, s, P[:, k]) for k in range(3)], 1)


def smooth_path(points, n, passes=3):
    """Resample a polyline and round its corners (Chaikin)."""
    P = np.asarray(points, float)
    for _ in range(passes):
        Q = [P[0]]
        for a, b in zip(P[:-1], P[1:]):
            Q += [0.75 * a + 0.25 * b, 0.25 * a + 0.75 * b]
        Q.append(P[-1])
        P = np.array(Q)
    return resample(P, n)


def tube(name, points, radii, mat, sides=20, caps=True, squash=1.0, n=None):
    """A smooth tube along a path, radius per point; squash < 1 flattens it."""
    P = np.asarray(points, float)
    R = np.asarray(radii, float)
    t = np.linspace(0, 1, len(P))
    n = n or max(28, len(P) * 10)
    P = smooth_path(P, n, 2) if len(P) > 2 else resample(P, n)
    R = np.interp(np.linspace(0, 1, n), t, R)
    T, N, B = frames_along(P)
    ang = np.linspace(0, 2 * np.pi, sides, endpoint=False)
    ring = np.cos(ang)[None, :, None] * N[:, None, :] + squash * np.sin(ang)[None, :, None] * B[:, None, :]
    V = list((P[:, None, :] + R[:, None, None] * ring).reshape(-1, 3))
    F = [(i * sides + a, i * sides + (a + 1) % sides, (i + 1) * sides + (a + 1) % sides, (i + 1) * sides + a)
         for i in range(n - 1) for a in range(sides)]
    if caps:
        for end, sgn in ((0, -1), (n - 1, 1)):
            c = len(V)
            V.append(P[end] + T[end] * R[end] * 0.6 * sgn)
            base = end * sides
            F += [(c, base + (a + 1) % sides, base + a) if sgn < 0 else (c, base + a, base + (a + 1) % sides)
                  for a in range(sides)]
    return mesh_from(name, V, F, mat)


def band(name, points, normals, inward, width, thick, mat, sides=12):
    """A flat braid bound over a cloth edge: lies in the surface, covering `width` in from the edge."""
    P = np.asarray(points, float)
    T = np.gradient(P, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-9
    N = np.asarray(normals, float)
    N = N - (N * T).sum(1, keepdims=True) * T
    N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-9
    B = np.cross(T, N)
    flip = np.sign((B * np.asarray(inward, float)).sum(1, keepdims=True))
    B = B * np.where(flip == 0, 1, flip)
    C = P + B * width * 0.42
    ang = np.linspace(0, 2 * np.pi, sides, endpoint=False)
    ring = (np.cos(ang)[None, :, None] * B[:, None, :] * width * 0.5
            + np.sin(ang)[None, :, None] * N[:, None, :] * thick * 0.5)
    V = (C[:, None, :] + ring).reshape(-1, 3)
    n = len(P)
    F = [(i * sides + a, i * sides + (a + 1) % sides, (i + 1) * sides + (a + 1) % sides, (i + 1) * sides + a)
         for i in range(n - 1) for a in range(sides)]
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


def curl(center, normal, r, turns, pitch, n=24, phase=None):
    """A loop of curly yarn lying on a surface: a short helix around an axis tangent to it."""
    normal = normal / np.linalg.norm(normal)
    t = np.cross(normal, rng.normal(size=3))
    t /= np.linalg.norm(t)
    b = np.cross(normal, t)
    th = np.linspace(0, 2 * np.pi * turns, n) + (rng.uniform(0, 6.3) if phase is None else phase)
    along = np.linspace(-0.5, 0.5, n) * pitch * turns + rng.normal(0, pitch * 0.15, n)
    rad = r * (1 + 0.28 * np.sin(th * rng.uniform(0.4, 0.9) + rng.uniform(0, 6.3))) * rng.uniform(0.8, 1.15)
    wob = np.cumsum(rng.normal(0, r * 0.06, (n, 3)), 0)
    return [center + t * a + rr * (math.cos(x) * normal + math.sin(x) * b) + w
            for a, x, rr, w in zip(along, th, rad, wob)]


def lathe(name, sections, mat, gap=None, seg=64, cap=False):
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
    if cap and not gap:
        for row, flip in ((0, True), (len(rows) - 1, False)):
            c = len(V)
            z = sections[row][0]
            V.append((0.0, sections[row][3], z))
            for j in range(w):
                f = (c, row * w + (j + 1) % w, row * w + j)
                F.append(f if flip else f[::-1])
    return mesh_from(name, V, F, mat), rows


def ring_around(center, d, radius, n=30):
    d = d / np.linalg.norm(d)
    a = np.cross(d, [0.0, 0, 1]) if abs(d[2]) < 0.9 else np.cross(d, [1.0, 0, 0])
    a /= np.linalg.norm(a)
    b = np.cross(d, a)
    return [center + radius * (math.cos(t) * a + math.sin(t) * b) for t in np.linspace(0, 2 * math.pi, n)]


def vgroup(ob, name, weights):
    g = ob.vertex_groups.new(name=name)
    w = np.asarray(weights, float)
    for val in np.unique(np.round(w, 2)):
        if val <= 0:
            continue
        idx = np.nonzero(np.round(w, 2) == val)[0].tolist()
        g.add(idx, float(val), "REPLACE")
    return g


def coords(ob):
    co = np.zeros(len(ob.data.vertices) * 3, np.float32)
    ob.data.vertices.foreach_get("co", co)
    return co.reshape(-1, 3).astype(float)


def remesh(ob, voxel, smooth_iter=10):
    r = ob.modifiers.new("remesh", "REMESH")
    r.mode = "VOXEL"
    r.voxel_size = voxel
    s = ob.modifiers.new("relax", "SMOOTH")
    s.factor = 1.0
    s.iterations = smooth_iter
    return bake(ob)


def boundary_loops(ob):
    """Boundary edge chains of a mesh, as vertex index lists."""
    count = defaultdict(int)
    for p in ob.data.polygons:
        for ek in p.edge_keys:
            count[ek] += 1
    adj = defaultdict(list)
    for (a, b), c in count.items():
        if c == 1:
            adj[a].append(b)
            adj[b].append(a)
    seen, loops = set(), []
    for start in list(adj):
        if start in seen:
            continue
        loop, prev, cur = [start], None, start
        seen.add(start)
        while True:
            nxt = [v for v in adj[cur] if v != prev and v not in seen]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            loop.append(cur)
            seen.add(cur)
        loops.append(loop)
    return loops


# ---------------------------------------------------------------- cloth
SIM_FRAMES = 60


def sim_collection(name, objects, thickness=0.004, friction=8.0):
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    for ob in objects:
        if "collision" not in ob.modifiers:
            ob.modifiers.new("collision", "COLLISION")
        ob.collision.thickness_outer = thickness
        ob.collision.cloth_friction = friction
        ob.collision.damping = 0.6
        col.objects.link(ob)
    return col


def cloth(ob, *, gravity=1.0, pressure=0.0, shrink_group=None, shrink=0.0, pin=None, colliders=None,
          tension=15.0, bending=0.5, mass=0.15, quality=8, self_collide=False, distance=0.003, damping=1.0):
    c = ob.modifiers.new("cloth", "CLOTH")
    s, cs = c.settings, c.collision_settings
    s.quality = quality
    s.mass = mass
    s.air_damping = damping
    s.tension_stiffness = s.compression_stiffness = tension
    s.shear_stiffness = tension * 0.4
    s.bending_stiffness = bending
    s.effector_weights.gravity = gravity
    if pressure:
        s.use_pressure = True
        s.uniform_pressure_force = pressure
    if shrink_group:
        s.vertex_group_shrink = shrink_group
        s.shrink_min = 0.0
        s.shrink_max = shrink
    if pin:
        s.vertex_group_mass = pin
        s.pin_stiffness = 1.0
    if colliders is not None:
        cs.use_collision = True
        cs.collection = colliders
        cs.distance_min = distance
        cs.collision_quality = 3
    else:
        cs.use_collision = False
    cs.use_self_collision = self_collide
    if self_collide:
        cs.self_distance_min = 0.003
    c.point_cache.frame_start = 1
    c.point_cache.frame_end = SIM_FRAMES + 5
    return c


def simulate(objects, frames=SIM_FRAMES):
    scene = bpy.context.scene
    f0 = scene.frame_current
    for f in range(1, frames + 1):
        scene.frame_set(f)
    for ob in objects:
        bake(ob)
        for g in list(ob.vertex_groups):
            ob.vertex_groups.remove(g)
    scene.frame_set(f0)


def release(col):
    for ob in list(col.objects):
        if "collision" in ob.modifiers:
            ob.modifiers.remove(ob.modifiers["collision"])
    bpy.data.collections.remove(col)


# ---------------------------------------------------------------- the head
def head_front(x, z):
    """y of the front of the head at (x, z), head-local: a full round face, slightly flattened,
    a soft dent along the eye line, plump cheeks and a little nose."""
    dz = (z - HC[2]) / HR[2]
    jaw = 1 + 0.06 * max(0.0, -dz)
    s = 1 - (x / (HR[0] * jaw)) ** 2 - dz ** 2
    y = HC[1] - 0.93 * HR[1] * math.sqrt(max(s, 0.0))
    y += 0.0022 * math.exp(-((z - 0.594) / 0.012) ** 2) * math.exp(-(x / 0.07) ** 2)          # eye line
    y -= 0.0065 * math.exp(-((x / 0.012) ** 2 + ((z - 0.566) / 0.011) ** 2))                  # nose
    y -= 0.004 * math.exp(-(((abs(x) - 0.05) / 0.026) ** 2 + ((z - 0.55) / 0.024) ** 2))       # cheeks
    return y


def face_point(x, z, out=0.0):
    """Point on the face and its outward normal, head-local."""
    y = head_front(x, z)
    e = 1e-4
    gx = (head_front(x + e, z) - head_front(x - e, z)) / (2 * e)
    gz = (head_front(x, z + e) - head_front(x, z - e)) / (2 * e)
    n = np.array([gx, -1.0, gz])
    n /= np.linalg.norm(n)
    p = np.array([x, y, z])
    return p + n * out, n


def build_head():
    """The head, face, hair, mustache and hat, head-local (upright). Returns objects."""
    obs = []
    skin = face_fabric()
    # the head: a UV sphere pushed onto the face shape
    seg, rings = 112, 56
    V, F = [], []
    for i in range(1, rings):
        th = math.pi * i / rings
        cz = math.cos(th)
        for j in range(seg):
            ph = 2 * math.pi * j / seg
            sx, sy = math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph)
            z = HC[2] + HR[2] * cz
            jaw = 1 + 0.06 * max(0.0, -cz)
            x = HR[0] * jaw * sx
            if sy < 0:
                y = head_front(x, z)
            else:
                y = HC[1] + HR[1] * sy
            V.append((x, y, z))
    for i in range(rings - 2):
        for j in range(seg):
            j2 = (j + 1) % seg
            F.append((i * seg + j, i * seg + j2, (i + 1) * seg + j2, (i + 1) * seg + j))
    top, bot = len(V), len(V) + 1
    V += [(0, HC[1], HC[2] + HR[2]), (0, HC[1], HC[2] - HR[2])]
    F += [(top, j, (j + 1) % seg)[::-1] for j in range(seg)]
    base = (rings - 2) * seg
    F += [(bot, base + (j + 1) % seg, base + j)[::-1] for j in range(seg)]
    head = mesh_from("Head", V, F, skin)
    obs.append(subsurf(head, 1))

    black = thread("Thread")
    eye = plain("SafetyEye", (0.004, 0.004, 0.005), rough=0.05, coat=1.0)
    for s in (-1, 1):
        ep, en = face_point(s * 0.04, 0.592, -0.0014)
        obs.append(oriented("Eye", ep, (0.0125, 0.0055, 0.0108), en, eye, seg=32, rings=16))
        # eyelashes: five stitches fanning up from the outer upper rim
        lashes = []
        for k in range(5):
            a = math.radians(30 + 22 * k)
            x0 = s * (0.04 + 0.0125 * math.cos(a) * 0.95)
            z0 = 0.592 + 0.0108 * math.sin(a) * 0.95
            p0, n0 = face_point(x0, z0, 0.0015)
            p1, _ = face_point(x0 + s * 0.006 * math.cos(a), z0 + 0.0075 * math.sin(a) + 0.002, 0.0012)
            lashes.append([p0, (p0 + p1) / 2 + n0 * 0.0016, p1])
        obs.append(curves("Lashes", lashes, 0.0006, black, res=1))
        # thick satin-stitched brows, low at the nose, rising outward
        path = [np.array([s * x, 0, z]) for x, z in ((0.016, 0.611), (0.03, 0.617), (0.047, 0.622), (0.066, 0.624))]
        path = smooth_path(path, 60, 2)
        stitches = []
        for k, c in enumerate(path):
            w = 0.0075 - 0.0028 * k / len(path)
            slant = 0.004 * s
            a, _ = face_point(c[0] - slant / 2, c[2] - w, 0.0006)
            b, nb = face_point(c[0] + slant / 2, c[2] + w, 0.0006)
            m, nm = face_point(c[0], c[2], 0.0018)
            stitches.append([a, m, b])
        obs.append(curves("Brow", stitches, 0.001, black, res=1))
    # red felt lips under the mustache, the line of the mouth stitched across them in a little smile
    felt = fabric("FeltRed", (0.36, 0.018, 0.024), rough=0.85, sheen=0.3, sheen_rough=0.4, tint=(1, 0.5, 0.5),
                  fibre=0.2, scale=1600)
    lp, ln = face_point(0.0, 0.5155, -0.0008)
    obs.append(subsurf(oriented("Lips", lp, (0.0135, 0.0027, 0.0052), ln, felt, seg=32, rings=16), 1))
    dark = thread("MouthThread", (0.09, 0.004, 0.006))
    obs.append(curves("Mouth", [[face_point(x, 0.5158 + 7 * x * x, 0.0021)[0] for x in np.linspace(-0.0125, 0.0125, 11)]],
                      0.0007, dark, res=1))

    # the mustache: a compact pad of curly black yarn stitched flat just under the nose,
    # a little thinner in the middle, the ends drooping and finished with a small curl
    wool = yarn()
    loops = []
    for s in (-1, 1):
        ctrl = np.array([(0.002, 0.539), (0.014, 0.542), (0.027, 0.542), (0.039, 0.537), (0.047, 0.53), (0.051, 0.523)])
        path = smooth_path([(s * c[0], 0, c[1]) for c in ctrl], 80, 2)
        for k in range(260):
            t = rng.uniform(0, 1) ** 0.9
            c = path[int(t * (len(path) - 1))]
            half = 0.0128 * (1 - 0.3 * t) * (0.82 + 0.18 * min(1.0, abs(c[0]) / 0.012))
            dz = rng.uniform(-1, 1) * half
            p, n = face_point(c[0], c[2] + dz, 0.0)
            depth = (0.002 + 0.005 * (1 - abs(dz) / half) ** 0.5) * rng.uniform(0.7, 1.0)
            loops.append(curl(p + n * depth, n, rng.uniform(0.0028, 0.004), rng.uniform(1.2, 1.9), 0.0032, 16))
        p, n = face_point(path[-1][0], path[-1][2] - 0.004, 0.003)
        loops.append(curl(p, n, 0.0045, 1.6, 0.003, 20))
    obs.append(curves("Mustache", loops, 0.0019, wool))

    # curly black yarn hair at the sides and back, under the hat
    locks = []
    for k in range(1500):
        az = rng.uniform(math.radians(-48), math.radians(228))
        z = rng.uniform(0.47, 0.648)
        side = abs(math.cos(az))
        if math.sin(az) < -0.55 and z < 0.52:
            continue
        dz = (z - HC[2]) / HR[2]
        if abs(dz) >= 0.98:
            continue
        rad = math.sqrt(1 - dz * dz)
        p = np.array([HR[0] * rad * math.cos(az), HC[1] + HR[1] * rad * math.sin(az), z])
        n = (p - HC) / HR ** 2
        n /= np.linalg.norm(n)
        lift = rng.uniform(0.003, 0.007 + 0.012 * side * (1 - max(0.0, (z - 0.6) / 0.05)))
        locks.append(curl(p + n * lift, n, rng.uniform(0.006, 0.0105), rng.uniform(1.2, 2.2), 0.0055, 22))
    obs.append(curves("Hair", locks, 0.0029, wool))

    # the tarboush: soft red cotton gores, stuffed and puffed between the seams
    red = fabric("ClothRed", (0.30, 0.006, 0.008), rough=0.9, sheen=0.2, sheen_rough=0.5, tint=(1, 0.3, 0.3),
                 fibre=0.25, scale=1000)
    prof = [(1.0, 0.626), (1.035, 0.645), (1.065, 0.668), (1.07, 0.692), (1.03, 0.716), (0.94, 0.739), (0.78, 0.757),
            (0.55, 0.769), (0.28, 0.776), (0.0, 0.778)]
    hat, _ = lathe("Tarboush", [(z, 0.121 * r, 0.113 * r, HC[1]) for r, z in prof], red, seg=96, cap=True)
    hat = remesh(hat, 0.0035, 6)
    co = coords(hat)
    az = np.arctan2(co[:, 1] - HC[1], co[:, 0])
    rr = np.hypot(co[:, 0], co[:, 1] - HC[1])
    gore = (az - math.radians(15)) % (math.pi / 3)
    dist = np.minimum(gore, math.pi / 3 - gore) * rr
    seam = np.exp(-(dist / 0.003) ** 2) * (co[:, 2] > 0.63)
    seam = np.maximum(seam, np.exp(-((co[:, 2] - 0.628) / 0.003) ** 2))
    vgroup(hat, "seam", seam)
    smooth_shade(hat)
    hat.data.materials.append(red)
    cloth(hat, gravity=0.0, pressure=1.0, shrink_group="seam", shrink=0.035, tension=12, bending=0.05, mass=0.3,
          damping=5)
    obs.append(hat)

    # the twisted gold lame band, knotted at his right side, and the black yarn pom-pom
    lame = gold_lame()
    strands = []
    for ph in (0.0, math.pi):
        pts = []
        for a in np.linspace(0, 2 * math.pi, 361):
            tw = a * 9 + ph
            rx, ry = 0.1255 + 0.0055 * math.cos(tw), 0.117 + 0.0055 * math.cos(tw)
            pts.append((rx * math.cos(a), HC[1] + ry * math.sin(a), 0.637 + 0.0062 * math.sin(tw)))
        strands.append(pts)
    for pts in strands:
        obs.append(subsurf(tube("HatBand", pts, [0.0072] * len(pts), lame, sides=14, caps=False, squash=0.8, n=len(pts)), 1))
    ka = math.radians(196)
    kp = np.array([0.131 * math.cos(ka), HC[1] + 0.122 * math.sin(ka), 0.636])
    obs.append(subsurf(oriented("BandKnot", kp, (0.014, 0.008, 0.012), -(kp - np.array([0, HC[1], 0.636])), lame), 1))
    for k, (dx, dz) in enumerate(((-0.004, -0.035), (0.01, -0.03))):
        out = (kp - np.array([0, HC[1], kp[2]]))
        out /= np.linalg.norm(out)
        tail = [kp, kp + out * 0.008 + np.array([dx * 0.4, 0, dz * 0.5]), kp + out * 0.012 + np.array([dx, 0, dz])]
        obs.append(subsurf(tube("BandTail", tail, [0.006, 0.005, 0.004], lame, sides=10, squash=0.4), 1))
    pom = []
    for k in range(170):
        d = rng.normal(size=3)
        d[2] = abs(d[2]) * 1.6 + 0.4
        d /= np.linalg.norm(d)
        p0 = np.array([0, HC[1], 0.776]) + d * 0.004
        L = rng.uniform(0.022, 0.04)
        bend = rng.normal(size=3) * 0.004
        pom.append([p0 + d * L * t + bend * t * t + np.array([0, 0, -0.006 * t * t]) for t in np.linspace(0, 1, 7)])
    obs.append(curves("PomPom", pom, 0.0019, wool))
    return obs


# ---------------------------------------------------------------- mitten hands
def mitten_slab(name, mat):
    """A stuffed mitten: two cut cloth panels sewn round the edge, inflated. Local: width x, length z."""
    outline = [(0.031 * math.cos(a), 0.044 + 0.041 * math.sin(a)) for a in np.linspace(math.radians(-25), math.radians(195), 44)]
    outline += [(-0.029, 0.026), (-0.041, 0.031), (-0.052, 0.045), (-0.053, 0.058), (-0.046, 0.063), (-0.037, 0.055),
                (-0.031, 0.042)][1:]
    outline += [(-0.027, 0.012), (-0.025, -0.012), (0.025, -0.012), (0.028, 0.012)]
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    vs = [bm.verts.new((x, 0, z)) for x, z in outline]
    f = bm.faces.new(vs)
    r = bmesh.ops.extrude_face_region(bm, geom=[f])
    for v in [e for e in r["geom"] if isinstance(e, bmesh.types.BMVert)]:
        v.co.y += 0.005
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, -0.0025, 0))
    bm.to_mesh(me)
    bm.free()
    ob = link(bpy.data.objects.new(name, me))
    ob = remesh(ob, 0.0021, 12)
    co = coords(ob)
    vgroup(ob, "seam", np.exp(-(co[:, 1] / 0.0018) ** 2))
    ob.data.materials.append(mat)
    smooth_shade(ob)
    cloth(ob, gravity=0.0, pressure=4.0, shrink_group="seam", shrink=0.05, tension=14, bending=0.1, mass=0.3,
          damping=5, quality=12)
    return ob


# ---------------------------------------------------------------- the rocking chair
def wood():
    """Varnished cherry: warm red-brown with a flowing grain under a satin clear coat."""
    if _cached("Cherry"):
        return _cached("Cherry")
    m, nt, out = _new_material("Cherry")
    tc = nt.nodes.new("ShaderNodeTexCoord").outputs["Object"]
    sq = nt.nodes.new("ShaderNodeVectorMath")
    sq.operation = "MULTIPLY"
    _set(nt, sq.inputs[0], tc)
    sq.inputs[1].default_value = (1.0, 1.0, 0.25)          # grain runs mostly up the posts and spindles
    grain = _noise(nt, sq.outputs[0], 60.0, 9.0, 0.62, distortion=4.0)
    fine = _noise(nt, tc, 900.0, 4.0, 0.5)
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.3
    ramp.color_ramp.elements[0].color = (0.042, 0.017, 0.008, 1)
    ramp.color_ramp.elements[1].position = 0.75
    ramp.color_ramp.elements[1].color = (0.12, 0.05, 0.022, 1)
    nt.links.new(grain.outputs["Fac"], ramp.inputs["Fac"])
    b = principled(nt, (0.15, 0.06, 0.025), rough=0.42)
    b.inputs["Coat Weight"].default_value = 0.45
    b.inputs["Coat Roughness"].default_value = 0.12
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    n = _bump(nt, grain.outputs["Fac"], 0.12, 0.0006)
    nt.links.new(_bump(nt, fine.outputs["Fac"], 0.05, 0.0002, n), b.inputs["Normal"])
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    return m


def bar(name, points, width, height, mat, up=(0.0, 0.0, 1.0), sides=28, n=None, caps=True, power=0.4):
    """A wooden bar along a path with a rounded-rectangle section: `width` across, `height` along `up`."""
    P = np.asarray(points, float)
    n = n or max(24, len(P) * 10)
    P = smooth_path(P, n, 2) if len(P) > 2 else resample(P, n)
    T = np.gradient(P, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    U = np.asarray(up, float)[None, :] - (T @ np.asarray(up, float))[:, None] * T
    U /= np.linalg.norm(U, axis=1, keepdims=True)
    S = np.cross(T, U)
    ang = np.linspace(0, 2 * np.pi, sides, endpoint=False)
    cx = np.sign(np.cos(ang)) * np.abs(np.cos(ang)) ** power * width / 2
    cy = np.sign(np.sin(ang)) * np.abs(np.sin(ang)) ** power * height / 2
    V = list((P[:, None, :] + cx[None, :, None] * S[:, None, :] + cy[None, :, None] * U[:, None, :]).reshape(-1, 3))
    F = [(i * sides + a, i * sides + (a + 1) % sides, (i + 1) * sides + (a + 1) % sides, (i + 1) * sides + a)
         for i in range(n - 1) for a in range(sides)]
    if caps:
        for end, sgn in ((0, -1), (n - 1, 1)):
            c = len(V)
            V.append(P[end] + T[end] * min(width, height) * 0.25 * sgn)
            base = end * sides
            F += [(c, base + (a + 1) % sides, base + a) if sgn < 0 else (c, base + a, base + (a + 1) % sides)
                  for a in range(sides)]
    return subsurf(mesh_from(name, V, F, mat), 1)


def turned(name, p0, p1, profile, mat, sides=24):
    """A lathe-turned spindle from p0 to p1; profile is [(t along it, radius), ...]."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    ts = np.linspace(0, 1, 48)
    radii = np.interp(ts, [q[0] for q in profile], [q[1] for q in profile])
    return tube(name, [p0 + (p1 - p0) * t for t in ts], radii, mat, sides=sides, n=48)


def seat_mesh(name, mat):
    """A saddled wooden seat: wider at the front, a shallow dish, rounded edges."""
    yc, hd = -0.025, 0.185
    def outline(a):
        ux = np.sign(math.cos(a)) * abs(math.cos(a)) ** 0.42
        uy = np.sign(math.sin(a)) * abs(math.sin(a)) ** 0.42
        y = yc + hd * uy
        hw = 0.2 - 0.024 * (y + 0.21) / 0.37
        return np.array([ux * hw, y - 0.012 * (1 - ux * ux) * (uy < 0)])     # front edge bowed forward
    # (scale of the outline, height): across the dished top, round the rolled edge, under the seat
    prof = [(0.0, -0.011), (0.3, -0.010), (0.55, -0.007), (0.75, -0.004), (0.88, -0.0015), (0.95, -0.0003),
            (0.985, -0.003), (1.0, -0.01), (1.0, -0.022), (0.985, -0.03), (0.95, -0.034), (0.5, -0.034), (0.0, -0.034)]
    K = 96
    V, F = [], []
    for r, dz in prof:
        for k in range(K):
            o = outline(2 * math.pi * k / K) * r
            V.append((o[0], o[1] + yc * (1 - r), SEAT_Z + dz))
    for i in range(len(prof) - 1):
        for k in range(K):
            k2 = (k + 1) % K
            F.append((i * K + k, (i + 1) * K + k, (i + 1) * K + k2, i * K + k2))
    return subsurf(mesh_from(name, V, F, mat), 1)


def build_rocking_chair():
    """A Windsor rocking chair in doll units. Returns (objects, seat, armrests)."""
    w = wood()
    obs = []

    def rocker_bottom(y):
        return ROCKER_R - math.sqrt(ROCKER_R ** 2 - (y - ROCKER_Y) ** 2)

    def rocker_top(y):
        return rocker_bottom(y) + 0.052

    tan_r = math.tan(RECLINE)
    for s in (-1, 1):
        ys = np.linspace(-0.43, 0.4, 40)
        obs.append(bar("Rocker", [(s * 0.215, y, rocker_bottom(y) + 0.026) for y in ys], 0.026, 0.052, w,
                       up=(0, 0, 1), n=80))
        # front leg and back leg, standing on the rocker, splayed slightly outward
        obs.append(turned("ChairLeg", (s * 0.215, -0.175, rocker_top(-0.175) - 0.004), (s * 0.19, -0.165, SEAT_Z - 0.03),
                          [(0, 0.016), (0.15, 0.019), (0.3, 0.014), (0.55, 0.017), (0.8, 0.014), (1, 0.016)], w))
        obs.append(turned("ChairLeg", (s * 0.215, 0.14, rocker_top(0.14) - 0.004), (s * 0.18, 0.13, SEAT_Z - 0.03),
                          [(0, 0.016), (0.15, 0.019), (0.3, 0.014), (0.55, 0.017), (0.8, 0.014), (1, 0.016)], w))
        # side stretcher between the legs
        obs.append(turned("Stretcher", (s * 0.205, -0.17, 0.2), (s * 0.198, 0.137, 0.2),
                          [(0, 0.009), (0.5, 0.012), (1, 0.009)], w, sides=16))
        # back post, reclined, with a ball finial
        top = np.array([s * 0.172, 0.13 + 0.52 * tan_r, SEAT_Z + 0.52])
        obs.append(turned("BackPost", (s * 0.18, 0.13, SEAT_Z - 0.03), top,
                          [(0, 0.017), (0.08, 0.02), (0.14, 0.015), (0.5, 0.016), (0.88, 0.014), (0.93, 0.018), (1, 0.013)], w))
        obs.append(ellipsoid("Finial", top + np.array([0, 0.003, 0.014]), (0.017, 0.017, 0.02), w, 24, 12))
        # armrest: from the back post, flaring out to a rounded scroll that curls down at the front
        arm = bar("Armrest", [(s * 0.17, 0.13 + (ARM_Z - SEAT_Z) * tan_r, ARM_Z - 0.011), (s * 0.205, 0.0, ARM_Z - 0.011),
                              (s * 0.226, -0.15, ARM_Z - 0.011), (s * 0.229, -0.205, ARM_Z - 0.013),
                              (s * 0.229, -0.232, ARM_Z - 0.026), (s * 0.229, -0.236, ARM_Z - 0.045)],
                  0.056, 0.022, w, n=60)
        obs.append(arm)
        # the turned post holding up the front of the armrest
        obs.append(turned("ArmPost", (s * 0.19, -0.158, SEAT_Z - 0.01), (s * 0.226, -0.18, ARM_Z - 0.02),
                          [(0, 0.014), (0.2, 0.012), (0.45, 0.016), (0.7, 0.011), (1, 0.013)], w))
    obs.append(turned("Stretcher", (-0.208, -0.172, 0.23), (0.208, -0.172, 0.23), [(0, 0.01), (0.5, 0.014), (1, 0.01)],
                      w, sides=16))
    seat = seat_mesh("Seat", w)
    obs.append(seat)
    # crest rail across the top of the back, bowed backward, and the spindles under it
    def back_y(z, x):
        return 0.13 + (z - SEAT_Z) * tan_r + 0.028 * (1 - (x / 0.17) ** 2)
    rail_z = SEAT_Z + 0.465
    obs.append(bar("CrestRail", [(x, back_y(rail_z, x), rail_z) for x in np.linspace(-0.185, 0.185, 15)], 0.024, 0.075, w,
                   up=(0, math.sin(RECLINE), math.cos(RECLINE)), n=50))
    for x in np.linspace(-0.11, 0.11, 5):
        obs.append(turned("Spindle", (x, 0.125, SEAT_Z - 0.01), (x, back_y(rail_z - 0.03, x), rail_z - 0.03),
                          [(0, 0.0085), (0.3, 0.0105), (0.7, 0.008), (1, 0.0075)], w, sides=16))
    arms = [o for o in obs if o.name.startswith("Armrest")]
    return obs, seat, arms


# ---------------------------------------------------------------- mitten hands at rest
def rest_mitten(ob, s):
    """Lay a baked mitten palm-down along the armrest, its tip curling over the scrolled end."""
    co = coords(ob)
    w, n, l = co[:, 0], co[:, 1], co[:, 2]
    n = n - n.min()
    lb, rb = 0.062, 0.022
    along = np.where(l <= lb, l, lb + (rb + n) * np.sin((l - lb) / rb))
    height = np.where(l <= lb, n, -rb + (rb + n) * np.cos((l - lb) / rb))
    out = np.stack([s * 0.228 + s * w, -0.13 - (along + 0.012), ARM_Z + 0.001 + height], 1)
    ob.data.vertices.foreach_set("co", out.astype(np.float32).ravel())
    ob.data.update()
    if s < 0:
        ob.data.flip_normals()
    return ob


# ---------------------------------------------------------------- Fares
def build_fares():
    """Fares as the real rag doll, sitting back in his rocking chair."""
    black = fabric("ClothBlack", (0.0062, 0.0058, 0.0058), rough=0.9, sheen=0.22, sheen_rough=0.55, tint=(0.62, 0.62, 0.66),
                   fibre=0.3, scale=900)
    jersey = fabric("JerseyBlack", (0.0055, 0.0053, 0.0053), rough=0.82, sheen=0.18, sheen_rough=0.4, fibre=0.12, scale=1500)
    skin = face_fabric()
    green = satin("VestGreen", (0.016, 0.05, 0.022), rough=0.4, sheen=0.35, crease=0.25)
    sash_mat = satin("SashCream", (0.5, 0.36, 0.16), rough=0.34, sheen=0.25, metal=0.55, crease=1.0, scale=26)
    braid = gold_braid()
    red = fabric("ClothRed", (0.30, 0.006, 0.008), rough=0.9, sheen=0.2, sheen_rough=0.5, tint=(1, 0.3, 0.3),
                 fibre=0.25, scale=1000)
    ribbon = satin("RibbonWhite", (0.78, 0.76, 0.74), rough=0.22, sheen=0.5, crease=0.2)
    pink = plain("PinkPin", (0.62, 0.07, 0.33), rough=0.25, coat=0.6)
    gold = plain("GoldButton", (0.8, 0.6, 0.3), rough=0.25, metal=1.0)
    parts = []
    add, extend = parts.append, parts.extend

    # the rocking chair, and a floor for the cloth (removed after the simulations)
    chair, seat, armrests = build_rocking_chair()
    extend(chair)
    bpy.ops.mesh.primitive_plane_add(size=3, location=(0, 0, 0))
    floor = bpy.context.active_object
    floor.name = "SimFloor"

    # ---------- torso (hidden under the clothes; the cloth rests on it)
    torso_secs = [(0.012, 0.09, 0.075), (0.04, 0.13, 0.108), (0.09, 0.148, 0.118), (0.16, 0.146, 0.112),
                  (0.24, 0.14, 0.105), (0.32, 0.136, 0.1), (0.38, 0.132, 0.096), (0.42, 0.118, 0.087),
                  (0.445, 0.085, 0.066), (0.46, 0.05, 0.045)]
    torso, _ = lathe("Torso", [(z, rx, ry, 0.03) for z, rx, ry in torso_secs], black, seg=48, cap=True)
    place(torso, M_UP)
    add(torso)
    neck, _ = lathe("Neck", [(z, 0.046, 0.042, 0.03) for z in (0.43, 0.47, 0.5)], skin, seg=32)
    add(place(smooth_shade(neck), M_UP))

    # ---------- legs: along the seat, bending over its front edge, hanging down in baggy sherwal
    legs = []
    Z = SEAT_Z
    for s in (-1, 1):
        ctrl = [(s * 0.066, 0.005, Z + 0.072), (s * 0.077, -0.1, Z + 0.07), (s * 0.086, -0.2, Z + 0.064),
                (s * 0.092, -0.252, Z + 0.032), (s * 0.095, -0.272, Z - 0.035), (s * 0.097, -0.272, Z - 0.11),
                (s * 0.099, -0.268, Z - 0.155), (s * 0.101, -0.288, Z - 0.188), (s * 0.103, -0.318, Z - 0.183)]
        path = smooth_path(ctrl, 90, 2)
        t = np.linspace(0, 1, len(path))
        t_ankle = t[np.argmin(np.linalg.norm(path - np.array(ctrl[6]), axis=1))]
        radius = np.interp(t, [0, 0.35, t_ankle - 0.12, t_ankle, t_ankle + 0.06, 0.94, 1.0],
                           [0.055, 0.052, 0.052, 0.038, 0.044, 0.042, 0.034])
        T_, N_, B_ = frames_along(path)
        sides = 40
        ang = np.linspace(0, 2 * np.pi, sides, endpoint=False)
        V = []
        for i in range(len(path)):
            gather = math.exp(-((t[i] - t_ankle) / 0.04) ** 2)          # sherwal gathered at the ankle
            rr = radius[i] * (1 + 0.07 * gather * np.sin(11 * ang + i * 0.3))
            V += list(path[i] + rr[:, None] * (np.cos(ang)[:, None] * N_[i] + np.sin(ang)[:, None] * B_[i]))
        F = [(i * sides + a, i * sides + (a + 1) % sides, (i + 1) * sides + (a + 1) % sides, (i + 1) * sides + a)
             for i in range(len(path) - 1) for a in range(sides)]
        tip = len(V)
        V.append(path[-1] + T_[-1] * radius[-1] * 0.7)
        F += [(tip, (len(path) - 1) * sides + a, (len(path) - 1) * sides + (a + 1) % sides) for a in range(sides)]
        root_c = len(V)
        V.append(path[0] - T_[0] * 0.02)
        F += [(root_c, (a + 1) % sides, a) for a in range(sides)]
        legs.append(mesh_from("Leg", V, F, jersey))

    # ---------- head (head-local, placed on the leaning body)
    head_obs = build_head()
    for ob in head_obs:
        place(ob, M_HEAD)
    hat = next(o for o in head_obs if o.name.startswith("Tarboush"))

    # ---------- stuffed parts: the hat and the mittens
    mittens = [mitten_slab("Mitten", skin), mitten_slab("Mitten", skin)]
    simulate([hat] + mittens, 40)
    extend(head_obs)
    for mit, s in zip(mittens, (1, -1)):
        add(subsurf(rest_mitten(mit, s), 1))

    # ---------- arms (inside the sleeves) along the armrests, and the sleeves draped over them
    arms, sleeves = [], []
    for s in (1, -1):
        sh = np.array(M_UP @ Vector((s * 0.132, 0.035, 0.405)))
        el = np.array([s * 0.217, 0.03, ARM_Z + 0.064])
        wr = np.array([s * 0.226, -0.125, ARM_Z + 0.062])
        arm = tube("Arm", [sh, (sh + el) / 2 + np.array([s * 0.012, 0, 0]), el, (el + wr) / 2, wr],
                   [0.036, 0.034, 0.033, 0.03, 0.027], black, sides=20, n=40)
        arms.append(arm)
        path = smooth_path([sh - np.array([s * 0.02, 0, -0.005]), (sh + el) / 2 + np.array([s * 0.015, 0, 0]), el,
                            (el + wr) / 2, wr + np.array([0, -0.004, 0])], 46, 2)
        T, N, B = frames_along(path)
        radii = np.interp(np.linspace(0, 1, len(path)), [0, 0.45, 1], [0.05, 0.056, 0.058])
        sides = 40
        ang = np.linspace(0, 2 * np.pi, sides, endpoint=False)
        V = (path[:, None, :] + radii[:, None, None] * (np.cos(ang)[None, :, None] * N[:, None, :]
                                                         + np.sin(ang)[None, :, None] * B[:, None, :])).reshape(-1, 3)
        F = [(i * sides + a, i * sides + (a + 1) % sides, (i + 1) * sides + (a + 1) % sides, (i + 1) * sides + a)
             for i in range(len(path) - 1) for a in range(sides)]
        sl = mesh_from("Sleeve", V, F, black)
        pin = np.zeros(len(V))
        pin[: sides * 4] = 1.0
        pin[-sides * 2:] = 0.85
        vgroup(sl, "pin", pin)
        sleeves.append(sl)

    # ---------- vest, sash
    vest, _ = lathe("Vest", [(z, rx + 0.005, ry + 0.005, 0.03) for z, rx, ry in torso_secs[3:9]], green, seg=72)
    add(place(subsurf(wrinkles(vest, 0.003, 0.03), 2), M_UP))
    trim = []
    for x in (-0.042, -0.03, -0.018, 0.018, 0.03, 0.042):
        pts = []
        for z in np.linspace(0.235, 0.43, 14):
            rx = np.interp(z, [t[0] for t in torso_secs], [t[1] for t in torso_secs]) + 0.005
            ry = np.interp(z, [t[0] for t in torso_secs], [t[2] for t in torso_secs]) + 0.005
            if abs(x) > rx * 0.95:
                continue
            pts.append((x, 0.03 - ry * math.sqrt(1 - (x / rx) ** 2) - 0.0012, z))
        trim.append(pts)
    add(place(curves("VestCord", trim, 0.0013, braid, res=1), M_UP))
    for z in np.linspace(0.26, 0.42, 7):
        ry = np.interp(z, [t[0] for t in torso_secs], [t[2] for t in torso_secs]) + 0.005
        add(place(ellipsoid("VestButton", (0, 0.03 - ry - 0.002, z), (0.0045, 0.003, 0.0045), gold, 16, 8), M_UP))
    sash_secs = []
    for k, z in enumerate(np.linspace(0.165, 0.24, 9)):
        bulge = 0.004 * math.sin(math.pi * k / 8) + 0.0015 * rng.normal()
        rx = np.interp(z, [t[0] for t in torso_secs], [t[1] for t in torso_secs]) + 0.011 + bulge
        ry = np.interp(z, [t[0] for t in torso_secs], [t[2] for t in torso_secs]) + 0.011 + bulge
        sash_secs.append((z, rx, ry, 0.03))
    sash, _ = lathe("Sash", sash_secs, sash_mat, seg=96)
    add(place(subsurf(wrinkles(wrinkles(sash, 0.007, 0.012, 3), 0.003, 0.005), 2), M_UP))

    # ---------- the long black robe: bodice pinned on the shoulders, skirt dropped onto the seat and legs
    def gap(z):
        if z >= 0.2:
            return math.radians(30 - 8 * (0.44 - z) / 0.24)
        return math.radians(22 - 12 * min(1.0, (0.2 - z) / 0.09))      # the front edges close over his lap
    seg = 150
    rows = []
    bodice = [(0.452, 0.074, 0.066), (0.437, 0.118, 0.094), (0.41, 0.146, 0.112), (0.37, 0.15, 0.115), (0.32, 0.153, 0.117),
              (0.27, 0.156, 0.119), (0.235, 0.16, 0.124), (0.205, 0.165, 0.128)]
    for z, rx, ry in bodice:
        rows.append((z, rx, ry))
    K = 30
    for k in range(1, K + 1):
        t = k / K
        rows.append((0.205 - 0.09 * t, 0.165 + 0.25 * t, 0.128 + 0.25 * t))
    V = []
    for i, (z, rx, ry) in enumerate(rows):
        g = gap(z)
        flare_t = max(0.0, (i - len(bodice) + 1) / K)
        for a in np.linspace(-math.pi / 2 + g, 3 * math.pi / 2 - g, seg):
            # the back of the skirt stays close: he is sitting on it, against the chair back
            back = max(0.0, math.sin(a))
            k = 1 - 0.55 * back * flare_t
            V.append((rx * k * math.cos(a), 0.03 + ry * k * math.sin(a), z))
    F = [(i * seg + j, i * seg + j + 1, (i + 1) * seg + j + 1, (i + 1) * seg + j)
         for i in range(len(rows) - 1) for j in range(seg - 1)]
    robe = mesh_from("Robe", V, F, black)
    place(robe, M_UP)
    pin = np.zeros(len(V))
    pin[: seg * len(bodice)] = 1.0
    vgroup(robe, "pin", pin)

    # second pass: robe and sleeves drape under gravity
    col_body = sim_collection("SimBody", [floor, torso, seat] + legs, thickness=0.004, friction=40.0)
    col_arms = sim_collection("SimArms", arms + [torso] + armrests, thickness=0.004)
    cloth(robe, pin="pin", colliders=col_body, tension=20, bending=1.2, mass=0.25, quality=8, self_collide=True,
          distance=0.004, damping=2)
    for sl in sleeves:
        cloth(sl, pin="pin", colliders=col_arms, tension=20, bending=0.8, mass=0.2, quality=8, distance=0.004, damping=2)
    simulate([robe] + sleeves, SIM_FRAMES)
    release(col_body)
    release(col_arms)
    bpy.data.objects.remove(floor)

    # gold braid along every edge of the robe and round the sleeve cuffs
    for cl, which in ((robe, "all"), (sleeves[0], "cuff"), (sleeves[1], "cuff")):
        cl.data.update()
        co = coords(cl)
        nrm = np.zeros(len(co) * 3, np.float32)
        cl.data.vertices.foreach_get("normal", nrm)
        nrm = nrm.reshape(-1, 3).astype(float)
        nbr = defaultdict(list)
        for e in cl.data.edges:
            a, b = e.vertices
            nbr[a].append(b)
            nbr[b].append(a)
        for loop in boundary_loops(cl):
            if which == "cuff" and loop[0] < len(co) // 2:
                continue
            if len(loop) < 4:
                continue
            pts = co[loop]
            inward = []
            bset = set(loop)
            for i in loop:
                inner = [co[j] for j in nbr[i] if j not in bset]
                inward.append((np.mean(inner, 0) - co[i]) if inner else np.zeros(3))
            if which == "cuff":
                pts = np.vstack([pts, pts[:1]])
                inward.append(inward[0])
                nl = np.vstack([nrm[loop], nrm[loop[:1]]])
            else:
                nl = nrm[loop]
            br = band("Braid", pts, nl, inward, 0.011, 0.0075, braid)
            br.matrix_world = cl.matrix_world.copy()
            add(subsurf(br, 1))
    for leg in legs:
        add(subsurf(wrinkles(leg, 0.0035, 0.022), 1))
    for cl in [robe] + sleeves:
        sol = cl.modifiers.new("thick", "SOLIDIFY")
        sol.thickness = 0.004
        sol.offset = 0.0
        smooth_shade(cl)
        add(subsurf(wrinkles(cl, 0.0025, 0.025), 1))
    for arm in arms:
        add(arm)

    # ---------- the red scarf knotted at the throat, a white satin bow and a pink pin on the chest
    nk = []
    for a in np.linspace(0, 2 * math.pi, 48):
        nk.append((0.074 * math.cos(a), 0.03 + 0.066 * math.sin(a), 0.458 + 0.006 * math.sin(2 * a + 0.5)))
    add(place(subsurf(wrinkles(tube("Scarf", nk, [0.021] * 48, red, sides=16, caps=False, squash=0.7, n=48), 0.004, 0.015), 1),
              M_UP))
    knot = np.array([-0.024, -0.05, 0.444])
    add(place(subsurf(ellipsoid("ScarfKnot", knot, (0.022, 0.015, 0.019), red), 1), M_UP))
    for tail in ([knot, knot + np.array([-0.03, -0.012, -0.03]), knot + np.array([-0.045, -0.012, -0.075])],
                 [knot, knot + np.array([0.0, -0.016, -0.034]), knot + np.array([0.012, -0.014, -0.08])]):
        add(place(subsurf(wrinkles(tube("ScarfTail", tail, [0.017, 0.016, 0.012], red, sides=14, squash=0.3), 0.003, 0.02), 1),
                  M_UP))
    bow_at = np.array([0.072, -0.083, 0.392])
    for s in (-1, 1):
        loop = [bow_at + np.array([s * 0.018 * (0.5 + 0.5 * math.cos(t)), -0.003 * math.sin(t), 0.011 * math.sin(t)])
                for t in np.linspace(0, 2 * math.pi, 18)]
        add(place(subsurf(tube("BowLoop", loop, [0.0055] * 18, ribbon, sides=10, caps=False, squash=0.25, n=36), 1), M_UP))
        tail = [bow_at, bow_at + np.array([s * 0.008, -0.004, -0.03]), bow_at + np.array([s * 0.016, -0.006, -0.07]),
                bow_at + np.array([s * 0.012, -0.004, -0.1])]
        add(place(subsurf(tube("BowTail", tail, [0.005] * 4, ribbon, sides=10, squash=0.22), 1), M_UP))
    add(place(ellipsoid("BowKnot", bow_at + np.array([0, -0.002, 0]), (0.005, 0.004, 0.006), ribbon, 16, 8), M_UP))
    pin_at = np.array([-0.083, -0.09, 0.36])
    for s in (-1, 1):
        add(place(oriented("PinWing", pin_at + np.array([s * 0.006, 0, 0.002]), (0.0065, 0.0015, 0.0055),
                           np.array([0, -1.0, 0]), pink, 16, 8), M_UP))
    # the round white LeMSIC badge on the outside of his left upper arm
    left_sleeve = sleeves[0]
    sh = np.array(M_UP @ Vector((0.132, 0.035, 0.405)))
    el = np.array([0.217, 0.03, ARM_Z + 0.064])
    dg = bpy.context.evaluated_depsgraph_get()
    target = left_sleeve.matrix_world.inverted() @ Vector(((sh + el) / 2 + np.array([0.07, -0.03, 0.0])).tolist())
    ok, loc, nrm_, _ = left_sleeve.evaluated_get(dg).closest_point_on_mesh(target)
    if ok:
        wl = left_sleeve.matrix_world @ loc
        wn = (left_sleeve.matrix_world.to_3x3() @ nrm_).normalized()
        bpy.ops.mesh.primitive_cylinder_add(vertices=40, radius=0.016, depth=0.003)
        badge = bpy.context.active_object
        badge.data.materials.append(plain("BadgeWhite", (0.82, 0.82, 0.8), rough=0.25, coat=0.8))
        badge.location = wl + wn * 0.004
        badge.rotation_euler = wn.to_track_quat("Z", "Y").to_euler()
        smooth_shade(badge)
        add(badge)

    root = bpy.data.objects.new("Fares", None)
    link(root)
    for ob in parts:
        if ob.parent is None:
            mw_ = ob.matrix_world.copy()
            ob.parent = root
            ob.matrix_world = mw_
    return root


if __name__ == "__main__":
    import sys
    sys.path.insert(0, HERE)
    import lemsic_tree as T
    view = next((a for a in sys.argv[1:] if a in ("front", "side", "cabin", "face")), "front")
    scene = T.reset_scene()
    import time
    t0 = time.time()
    build_fares()
    print("built in %.0fs" % (time.time() - t0))
    cam_data = bpy.data.cameras.new("Cam")
    cam_data.lens = {"face": 85, "cabin": 50}.get(view, 50)
    cam = link(bpy.data.objects.new("Cam", cam_data))
    cam.location = {"front": (-0.45, -2.0, 1.0), "side": (-1.6, -1.0, 0.9), "cabin": (-1.0, -2.6, 1.35),
                    "face": (-0.15, -0.95, 0.98)}[view]
    aim = {"face": (0, -0.03, 0.92)}.get(view, (0, -0.05, 0.55))
    cam.rotation_euler = (Vector(aim) - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    # firelight from the left, tree lights behind right, a dim cool fill from the window
    for loc, power, size, color in (((-1.6, -0.6, 0.7), 120, 0.8, (1.0, 0.55, 0.25)),
                                    ((0.7, 0.5, 0.9), 25, 0.5, (1.0, 0.75, 0.45)),
                                    ((0.5, -1.4, 1.6), 30, 1.5, (0.6, 0.7, 1.0))):
        ld = bpy.data.lights.new("L", "AREA")
        ld.energy = power
        ld.size = size
        ld.color = color
        ob = link(bpy.data.objects.new("L", ld))
        ob.location = loc
        ob.visible_camera = False
        ob.rotation_euler = (Vector((0, 0, 0.4)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    bpy.ops.mesh.primitive_plane_add(size=8)
    bpy.context.active_object.data.materials.append(plain("Floor", (0.16, 0.085, 0.045), rough=0.5))
    world = bpy.data.worlds.new("W")
    scene.world = world
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.01, 0.008, 0.007, 1)
    r = scene.render
    r.engine = "CYCLES"
    res = next((a.split("=")[1] for a in sys.argv if a.startswith("--res=")), "800x1000")
    r.resolution_x, r.resolution_y = map(int, res.split("x"))
    scene.cycles.samples = int(next((a.split("=")[1] for a in sys.argv if a.startswith("--samples=")), "48"))
    scene.cycles.use_denoising = True
    scene.cycles.volume_step_rate = 0.5
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    out = os.path.join(os.path.dirname(os.path.dirname(HERE)), "build", "fares-%s.png" % view)
    r.filepath = out
    bpy.ops.render.render(write_still=True)
    print("wrote", out, "%.0fs" % (time.time() - t0))
