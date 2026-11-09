"""Build and render the realistic LeMSIC Christmas tree in Blender (Cycles).

The tree is a real-looking evergreen grown in the silhouette of the cedar in the
LeMSIC emblem: nine flat tiers, alternately reaching further left and right.
Days 1-23 are numbered baubles hanging from the tiers; day 24 is the star on top.

Run with Blender:          blender -b -P tools/blender/lemsic_tree.py -- [--preview]
or with the bpy module:    python tools/blender/lemsic_tree.py [--preview]

Writes:
  images/render/lemsic-tree.png          tree on a transparent background
  images/render/ornaments.json           where each ornament sits in that image
"""
import json
import math
import os
import random
import sys
import time

import numpy as np
import bpy
import addon_utils
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT_DIR = os.path.join(ROOT, "images", "render")
DECALS = os.path.join(HERE, "decals")

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
PREVIEW = "--preview" in ARGS
RES = (480, 600) if PREVIEW else (1600, 2000)
for _a in ARGS:
    if _a.startswith("--res="):
        RES = tuple(int(x) for x in _a[6:].split("x"))
SAMPLES = 48 if PREVIEW else 384
for _a in ARGS:
    if _a.startswith("--samples="):
        SAMPLES = int(_a[10:])
DENSITY = 0.45 if PREVIEW else 1.0
OUT_NAME = "lemsic-tree-preview.png" if PREVIEW else "lemsic-tree.png"

rng = np.random.default_rng(1964)

# ---------------------------------------------------------------- tree profile
N_TIERS = 9
TIER_Z = np.linspace(2.84, 0.64, N_TIERS)
TIER_R = np.array([0.30, 0.42, 0.55, 0.67, 0.79, 0.91, 1.02, 1.13, 1.24])
PER_TIER = [0, 1, 2, 2, 3, 3, 4, 4, 4]           # ornaments per tier, 23 in all
TRUNK_BOTTOM, TRUNK_TOP = 0.20, 3.00
STAR_Z = 3.17
BAUBLE_R = 0.072
CAMERA = Vector((0.0, -9.4, 2.15))
CAMERA_TARGET = Vector((0.0, 0.0, 1.66))


def trunk_radius(z):
    t = (z - TRUNK_BOTTOM) / (TRUNK_TOP - TRUNK_BOTTOM)
    return 0.078 * (1 - t) ** 0.85 + 0.006


def lopsided(theta, i):
    """Tiers reach further left and right alternately, like the emblem."""
    bias = math.pi if i % 2 else 0.0
    return 1.0 + 0.11 * np.cos(theta - bias)


# ---------------------------------------------------------------- mesh helpers
def link(ob):
    bpy.context.scene.collection.objects.link(ob)
    return ob


def mesh_object(name, verts, quads, colors=None, mat=None, smooth=False):
    me = bpy.data.meshes.new(name)
    nv, nf = len(verts), len(quads)
    me.vertices.add(nv)
    me.vertices.foreach_set("co", np.asarray(verts, np.float32).ravel())
    me.loops.add(nf * 4)
    me.loops.foreach_set("vertex_index", np.asarray(quads, np.int32).ravel())
    me.polygons.add(nf)
    me.polygons.foreach_set("loop_start", np.arange(0, nf * 4, 4, dtype=np.int32))
    me.update(calc_edges=True)
    if smooth:
        me.polygons.foreach_set("use_smooth", np.ones(nf, bool))
    if colors is not None:
        attr = me.color_attributes.new("col", "FLOAT_COLOR", "POINT")
        attr.data.foreach_set("color", np.asarray(colors, np.float32).ravel())
    if mat:
        me.materials.append(mat)
    return link(bpy.data.objects.new(name, me))


def tubes(A, B, ra, rb, sides=6):
    """Tapered tubes from A[i] to B[i]."""
    A, B = np.asarray(A, float), np.asarray(B, float)
    d = B - A
    d /= np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-9)
    ref = np.where(np.abs(d[:, 2:3]) < 0.9, [[0.0, 0, 1]], [[1.0, 0, 0]])
    u = np.cross(d, ref)
    u /= np.linalg.norm(u, axis=1, keepdims=True)
    v = np.cross(d, u)
    ang = np.linspace(0, 2 * np.pi, sides, endpoint=False)
    ring = np.cos(ang)[None, :, None] * u[:, None, :] + np.sin(ang)[None, :, None] * v[:, None, :]
    va = A[:, None, :] + np.asarray(ra)[:, None, None] * ring
    vb = B[:, None, :] + np.asarray(rb)[:, None, None] * ring
    verts = np.concatenate([va, vb], axis=1).reshape(-1, 3)
    k = np.arange(sides)
    quads = np.stack([k, (k + 1) % sides, (k + 1) % sides + sides, k + sides], axis=1)
    base = (np.arange(len(A)) * 2 * sides)[:, None, None]
    return verts, (base + quads[None]).reshape(-1, 4)


def icosphere_template(subdiv):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdiv, radius=1.0)
    ob = bpy.context.active_object
    v = np.array([vx.co[:] for vx in ob.data.vertices])
    tris = np.array([p.vertices[:] for p in ob.data.polygons])
    bpy.data.objects.remove(ob, do_unlink=True)
    return v, tris


def spheres(centers, radius, template):
    v, tris = template
    n = len(centers)
    verts = (np.asarray(centers)[:, None, :] + v[None] * radius).reshape(-1, 3)
    faces = (tris[None] + (np.arange(n) * len(v))[:, None, None]).reshape(-1, 3)
    # degenerate quad (repeat last index) so mesh_object can take triangles too
    quads = np.concatenate([faces, faces[:, 2:3]], axis=1)
    return verts, quads


def tri_mesh_object(name, verts, tris, mat=None, smooth=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(p) for p in verts], [], [tuple(t) for t in tris])
    me.update()
    if smooth:
        me.polygons.foreach_set("use_smooth", np.ones(len(me.polygons), bool))
    if mat:
        me.materials.append(mat)
    return link(bpy.data.objects.new(name, me))


# ---------------------------------------------------------------- materials
def new_material(name):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    return m, nt, out


def principled(nt, color, rough=0.5, metal=0.0, coat=0.0, emit=None, emit_strength=0.0):
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Coat Weight"].default_value = coat
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = emit_strength
    return b


def simple_material(name, color, **kw):
    m, nt, out = new_material(name)
    nt.links.new(principled(nt, color, **kw).outputs[0], out.inputs["Surface"])
    return m


def needle_material():
    m, nt, out = new_material("Needles")
    attr = nt.nodes.new("ShaderNodeAttribute")
    attr.attribute_name = "col"
    b = principled(nt, (0.03, 0.08, 0.03), rough=0.42)
    b.inputs["Specular IOR Level"].default_value = 0.35
    tr = nt.nodes.new("ShaderNodeBsdfTranslucent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    mix.inputs[0].default_value = 0.22
    nt.links.new(attr.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(attr.outputs["Color"], tr.inputs["Color"])
    nt.links.new(b.outputs[0], mix.inputs[1])
    nt.links.new(tr.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return m


def bark_material():
    m, nt, out = new_material("Bark")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (70, 70, 9)
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Detail"].default_value = 10
    noise.inputs["Roughness"].default_value = 0.65
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.025, 0.014, 0.008, 1)
    ramp.color_ramp.elements[1].color = (0.11, 0.065, 0.035, 1)
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.8
    b = principled(nt, (0.06, 0.035, 0.02), rough=0.85)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs[0], noise.inputs["Vector"])
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    return m


def wood_material(name, color_a, color_b, scale=(2, 2, 30)):
    m, nt, out = new_material(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = scale
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.inputs["Scale"].default_value = 3
    wave.inputs["Distortion"].default_value = 6
    wave.inputs["Detail"].default_value = 4
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*color_a, 1)
    ramp.color_ramp.elements[1].color = (*color_b, 1)
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.25
    b = principled(nt, color_a, rough=0.6)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs[0], wave.inputs["Vector"])
    nt.links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(wave.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    return m


def decal_material(name, base_kw, decal_kw, image_path, half_size):
    """Glossy surface with a number printed on the side facing the camera (local -Y)."""
    m, nt, out = new_material(name)
    base = principled(nt, **base_kw)
    dec = principled(nt, **decal_kw)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    u = nt.nodes.new("ShaderNodeMath")
    u.operation = "MULTIPLY_ADD"
    u.inputs[1].default_value = 0.5 / half_size
    u.inputs[2].default_value = 0.5
    v = nt.nodes.new("ShaderNodeMath")
    v.operation = "MULTIPLY_ADD"
    v.inputs[1].default_value = 0.5 / half_size
    v.inputs[2].default_value = 0.5
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    img = nt.nodes.new("ShaderNodeTexImage")
    img.image = bpy.data.images.load(image_path, check_existing=True)
    img.extension = "CLIP"
    img.interpolation = "Cubic"
    front = nt.nodes.new("ShaderNodeMath")
    front.operation = "LESS_THAN"
    front.inputs[1].default_value = 0.0
    fac = nt.nodes.new("ShaderNodeMath")
    fac.operation = "MULTIPLY"
    mix = nt.nodes.new("ShaderNodeMixShader")
    L = nt.links.new
    L(tc.outputs["Object"], sep.inputs[0])
    L(sep.outputs["X"], u.inputs[0])
    L(sep.outputs["Z"], v.inputs[0])
    L(u.outputs[0], comb.inputs["X"])
    L(v.outputs[0], comb.inputs["Y"])
    L(comb.outputs[0], img.inputs["Vector"])
    L(sep.outputs["Y"], front.inputs[0])
    L(img.outputs["Alpha"], fac.inputs[0])
    L(front.outputs[0], fac.inputs[1])
    L(fac.outputs[0], mix.inputs[0])
    L(base.outputs[0], mix.inputs[1])
    L(dec.outputs[0], mix.inputs[2])
    L(mix.outputs[0], out.inputs["Surface"])
    return m


# ---------------------------------------------------------------- foliage
NEEDLE_DARK = np.array([0.012, 0.040, 0.016])
NEEDLE_MID = np.array([0.030, 0.085, 0.030])
NEEDLE_TIP = np.array([0.085, 0.190, 0.045])
NEEDLE_BLUE = np.array([0.016, 0.055, 0.048])


def needles(P, D, Lt, spacing=0.0042, per=3, length=(0.020, 0.032), width=0.0024):
    spacing = spacing / DENSITY
    counts = np.maximum((Lt / spacing).astype(int), 2) * per
    idx = np.repeat(np.arange(len(P)), counts)
    n = len(idx)
    u = rng.random(n)
    d = D[idx]
    side = np.cross(d, [0.0, 0, 1])
    side /= np.linalg.norm(side, axis=1, keepdims=True) + 1e-9
    upv = np.cross(side, d)
    base = P[idx] + d * (u * Lt[idx])[:, None]
    phi = rng.uniform(np.radians(-30), np.radians(210), n)
    a = rng.uniform(np.radians(35), np.radians(72), n)
    nd = np.cos(a)[:, None] * d + np.sin(a)[:, None] * (np.cos(phi)[:, None] * side + np.sin(phi)[:, None] * upv)
    ln = rng.uniform(*length, n) * (1 - 0.5 * u ** 2)
    tip = base + nd * ln[:, None]
    wv = np.cross(nd, d)
    wv /= np.linalg.norm(wv, axis=1, keepdims=True) + 1e-9
    w = width / 2
    verts = np.stack([base - wv * w, base + wv * w, tip + wv * w * 0.15, tip - wv * w * 0.15], axis=1).reshape(-1, 3)
    quads = np.arange(n * 4).reshape(-1, 4)
    # colour: dark inside, fresh light-green growth at the twig tips, some bluish needles
    mix = rng.random(n)[:, None]
    col = NEEDLE_DARK + (NEEDLE_MID - NEEDLE_DARK) * mix
    blue = rng.random(n) < 0.25
    col[blue] = col[blue] * 0.5 + NEEDLE_BLUE * 0.5
    col += (NEEDLE_TIP - col) * (u ** 5 * 0.85)[:, None]
    rgba = np.concatenate([col, np.ones((n, 1))], axis=1)
    return verts, quads, np.repeat(rgba, 4, axis=0)


def rotate_z(vecs, angles):
    c, s = np.cos(angles), np.sin(angles)
    x, y = vecs[:, 0] * c - vecs[:, 1] * s, vecs[:, 0] * s + vecs[:, 1] * c
    return np.stack([x, y, vecs[:, 2]], axis=1)


def build_tier(i):
    """One flat tier of branches. Returns wood segments, twigs, and tier surface samples."""
    z0, R = TIER_Z[i], TIER_R[i]
    nb = int(12 + 2.0 * i)
    thetas = rng.uniform(0, 2 * np.pi) + np.arange(nb) * 2 * np.pi / nb + rng.uniform(-0.2, 0.2, nb)
    wood = ([], [], [], [])
    tw_P, tw_D, tw_L = [], [], []
    r0 = trunk_radius(z0)
    for th in thetas:
        L = R * rng.uniform(0.86, 1.02) * lopsided(th, i)
        t = np.linspace(0, 1, 13)
        ang = th + rng.uniform(-0.25, 0.25) * t ** 2
        rad = r0 + t * L
        zz = z0 + L * (0.10 * t - 0.15 * t ** 2) + rng.uniform(-0.05, 0.05)
        pts = np.stack([rad * np.cos(ang), rad * np.sin(ang), zz], axis=1)
        rb = (0.010 + 0.011 * R) * (1 - 0.8 * t)
        wood[0].append(pts[:-1]); wood[1].append(pts[1:]); wood[2].append(rb[:-1]); wood[3].append(rb[1:])
        # the spine carries needles too, beyond the bare inner part
        seg_d = pts[1:] - pts[:-1]
        seg_l = np.linalg.norm(seg_d, axis=1)
        keep = t[:-1] > 0.25
        tw_P.append(pts[:-1][keep]); tw_D.append((seg_d / seg_l[:, None])[keep]); tw_L.append(seg_l[keep])
        # side twigs, longer near the trunk so the tier forms a flat plate
        nt = max(4, int(L / 0.024))
        for k in range(nt):
            tk = 0.14 + 0.84 * (k + rng.random() * 0.6) / nt
            j = min(int(tk * 12), 11)
            f = tk * 12 - j
            p = pts[j] * (1 - f) + pts[j + 1] * f
            dsp = seg_d[j] / seg_l[j]
            s = 1 if k % 2 else -1
            rot = s * np.radians(rng.uniform(38, 68))
            d2 = rotate_z(dsp[None], np.array([rot]))[0]
            d2[2] = rng.uniform(-0.18, 0.30)
            d2 /= np.linalg.norm(d2)
            l2 = (0.08 + 0.36 * (1 - tk)) * min(L, 1.15) * rng.uniform(0.8, 1.15) + 0.05
            tw_P.append(p[None]); tw_D.append(d2[None]); tw_L.append(np.array([l2]))
            wood[0].append(p[None]); wood[1].append((p + d2 * l2 * 0.9)[None])
            wood[2].append(np.array([0.003])); wood[3].append(np.array([0.0012]))
            # twiglets off each twig give the foliage depth
            for q in range(int(rng.integers(3, 7))):
                tq = rng.uniform(0.15, 0.85)
                pq = p + d2 * l2 * tq
                dq = rotate_z(d2[None], np.array([rng.choice([-1, 1]) * np.radians(rng.uniform(30, 60))]))[0]
                dq[2] += rng.uniform(-0.25, 0.4)
                dq /= np.linalg.norm(dq)
                tw_P.append(pq[None]); tw_D.append(dq[None]); tw_L.append(np.array([l2 * rng.uniform(0.25, 0.45)]))
    return ([np.concatenate(w) for w in wood],
            (np.concatenate(tw_P), np.concatenate(tw_D), np.concatenate(tw_L)))


def build_top():
    """Leader shoot above the top tier."""
    z = np.linspace(TIER_Z[0], TRUNK_TOP, 6)
    P = np.stack([np.zeros(5), np.zeros(5), z[:-1]], axis=1)
    D = np.tile([0.0, 0, 1], (5, 1))
    Ls = np.diff(z)
    extra_P, extra_D, extra_L = [P], [D], [Ls]
    for k in range(36):
        a = rng.uniform(0, 2 * np.pi)
        zz = rng.uniform(TIER_Z[0] - 0.04, TRUNK_TOP - 0.03)
        d = np.array([np.cos(a), np.sin(a), rng.uniform(0.6, 1.4)])
        d /= np.linalg.norm(d)
        extra_P.append(np.array([[0, 0, zz]])); extra_D.append(d[None])
        extra_L.append(np.array([0.06 + 0.12 * (TRUNK_TOP - zz)]))
    return np.concatenate(extra_P), np.concatenate(extra_D), np.concatenate(extra_L)


def tier_surface(i, theta, frac=0.92):
    """Approximate point on the outer upper surface of tier i at angle theta."""
    r = TIER_R[i] * lopsided(theta, i) * frac
    L = TIER_R[i]
    t = frac
    z = TIER_Z[i] + L * (0.10 * t - 0.15 * t ** 2) + 0.02
    return np.array([r * math.cos(theta), r * math.sin(theta), z])


# ---------------------------------------------------------------- scene
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    addon_utils.enable("cycles", default_set=True)
    return bpy.context.scene


def build_scene():
    scene = reset_scene()
    hotspots = build_tree()
    camera_and_lights(scene)
    return scene, hotspots


def build_tree():
    """Add the decorated tree (with crate and presents) to the current scene.

    Ornaments turn to face CAMERA, so set lemsic_tree.CAMERA first when using
    another camera. Returns the ornament positions in world space.
    """
    mat_needles = needle_material()
    mat_bark = bark_material()

    # trunk
    zs = np.linspace(TRUNK_BOTTOM, TRUNK_TOP, 40)
    A = np.stack([np.zeros(39), np.zeros(39), zs[:-1]], axis=1)
    B = np.stack([np.zeros(39), np.zeros(39), zs[1:]], axis=1)
    v, q = tubes(A, B, trunk_radius(zs[:-1]), trunk_radius(zs[1:]), sides=14)
    mesh_object("Trunk", v, q, mat=mat_bark, smooth=True)

    wood_parts, twig_parts = [], []
    for i in range(N_TIERS):
        w, tw = build_tier(i)
        wood_parts.append(w); twig_parts.append(tw)
    twig_parts.append(build_top())

    A = np.concatenate([w[0] for w in wood_parts]); B = np.concatenate([w[1] for w in wood_parts])
    ra = np.concatenate([w[2] for w in wood_parts]); rb = np.concatenate([w[3] for w in wood_parts])
    v, q = tubes(A, B, ra, rb, sides=5)
    mesh_object("Branches", v, q, mat=mat_bark, smooth=True)

    P = np.concatenate([t[0] for t in twig_parts])
    D = np.concatenate([t[1] for t in twig_parts])
    Lt = np.concatenate([t[2] for t in twig_parts])
    v, q, c = needles(P, D, Lt)
    mesh_object("Needles", v, q, colors=c, mat=mat_needles)
    print(f"  needles: {len(q):,}  twigs: {len(P):,}")

    fairy_lights()
    stand_and_presents()
    return ornaments()


def fairy_lights():
    n = int(260 * max(DENSITY, 0.6))
    pts = []
    for _ in range(n):
        i = int(rng.integers(0, N_TIERS))
        th = rng.uniform(0, 2 * np.pi)
        p = tier_surface(i, th, rng.uniform(0.35, 0.97))
        p[2] += rng.uniform(-0.03, 0.02)
        pts.append(p)
    v, q = spheres(np.array(pts), 0.011, icosphere_template(1))
    mat = simple_material("Bulb", (1.0, 0.75, 0.4), rough=0.3, emit=(1.0, 0.62, 0.28), emit_strength=28)
    ob = tri_mesh_object("FairyLights", v, q[:, :3], mat=mat)
    ob.visible_shadow = False


def box(name, size, loc, mat, rot=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=(0, 0, rot))
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = size
    ob.data.materials.append(mat)
    bev = ob.modifiers.new("bevel", "BEVEL")
    bev.width = 0.006
    bev.segments = 2
    return ob


def present(loc, size, rot, paper, ribbon):
    x, y, z = loc
    sx, sy, sz = size
    box("Present", (sx, sy, sz), (x, y, z + sz / 2), paper, rot)
    box("Ribbon", (sx * 1.01, 0.03, sz * 1.01), (x, y, z + sz / 2), ribbon, rot)
    box("Ribbon", (0.03, sy * 1.01, sz * 1.01), (x, y, z + sz / 2), ribbon, rot)
    for side in (-1, 1):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.04, minor_radius=0.011,
                                         location=(x + side * 0.03 * math.cos(rot), y + side * 0.03 * math.sin(rot), z + sz + 0.025),
                                         rotation=(math.radians(90), math.radians(side * 30), rot))
        bow = bpy.context.active_object
        bow.scale = (1, 0.7, 1)
        bow.data.materials.append(ribbon)
        bpy.ops.object.shade_smooth()


def stand_and_presents():
    crate = wood_material("Crate", (0.20, 0.10, 0.045), (0.36, 0.20, 0.09), scale=(3, 30, 3))
    for k in range(3):     # stacked planks
        z = 0.05 + k * 0.105
        box("Plank", (0.62, 0.62, 0.095), (0, 0, z), crate)
    papers = [simple_material("PaperRed", (0.20, 0.003, 0.007), rough=0.55),
              simple_material("PaperGreen", (0.01, 0.08, 0.03), rough=0.4, coat=0.3),
              simple_material("PaperCream", (0.55, 0.47, 0.34), rough=0.5),
              simple_material("PaperBlue", (0.02, 0.06, 0.2), rough=0.4, coat=0.3)]   # LeMSIC blue
    gold = simple_material("RibbonGold", (0.9, 0.6, 0.2), rough=0.25, metal=1.0)
    red = simple_material("RibbonRed", (0.5, 0.01, 0.02), rough=0.35, coat=0.6)
    present((-0.62, -0.30, 0), (0.34, 0.30, 0.26), 0.25, papers[0], gold)
    present((-0.95, -0.05, 0), (0.24, 0.24, 0.20), -0.3, papers[2], red)
    present((0.60, -0.32, 0), (0.30, 0.30, 0.30), -0.2, papers[3], gold)
    present((0.95, -0.10, 0), (0.22, 0.26, 0.17), 0.4, papers[1], gold)
    present((0.30, -0.62, 0), (0.18, 0.18, 0.14), 0.1, papers[0], gold)


BAUBLE_STYLES = [
    # base finish, number finish
    (dict(color=(0.50, 0.015, 0.025), rough=0.12, metal=0.6, coat=1.0),
     dict(color=(0.92, 0.86, 0.72), rough=0.45)),                                                         # red
    (dict(color=(0.95, 0.62, 0.20), rough=0.28, metal=0.75, coat=0.6),
     dict(color=(0.20, 0.004, 0.01), rough=0.4)),                                          # gold
    (dict(color=(0.015, 0.17, 0.05), rough=0.14, metal=0.5, coat=1.0),
     dict(color=(0.92, 0.86, 0.72), rough=0.45)),                                                         # green
    (dict(color=(0.26, 0.015, 0.10), rough=0.30, metal=0.4, coat=0.5),
     dict(color=(0.92, 0.86, 0.72), rough=0.45)),                                                         # plum, satin
    (dict(color=(0.86, 0.88, 0.92), rough=0.26, metal=0.6, coat=0.6),
     dict(color=(0.035, 0.11, 0.33), rough=0.3)),                                          # silver, LeMSIC blue
]


def day_order(n):
    r = random.Random(1964)          # same mixed order as the flat design
    days = list(range(1, n + 1))
    r.shuffle(days)
    return days


def face_camera_angle(pos):
    v = Vector(CAMERA) - Vector(pos)
    return math.atan2(v.x, -v.y)


def ornaments():
    gold = simple_material("CapGold", (0.9, 0.62, 0.22), rough=0.2, metal=1.0)
    thread = simple_material("Thread", (0.9, 0.7, 0.3), rough=0.4, metal=0.6)
    spots = []
    slots = []
    for i, count in enumerate(PER_TIER):
        if not count:
            continue
        span = math.radians(58 if count > 1 else 0)
        phis = np.linspace(-span, span, count) if count > 1 else np.array([math.radians(-12)])
        for phi in phis:
            phi += rng.uniform(-0.06, 0.06)
            slots.append((i, -math.pi / 2 + phi))
    days = day_order(len(slots))
    for n, ((i, th), day) in enumerate(zip(slots, days)):
        attach = tier_surface(i, th, rng.uniform(0.92, 0.97))
        attach[2] -= 0.03
        drop = rng.uniform(0.006, 0.016)
        center = attach - np.array([0, 0, drop + 0.02 + BAUBLE_R])
        base_kw, dec_kw = BAUBLE_STYLES[n % len(BAUBLE_STYLES)]
        mat = decal_material(f"Bauble{day}", base_kw, dec_kw,
                             os.path.join(DECALS, f"num-{day:02d}.png"), BAUBLE_R * 0.78)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=BAUBLE_R, segments=48, ring_count=24, location=center)
        ob = bpy.context.active_object
        ob.name = f"Ornament{day:02d}"
        ob.rotation_euler = (0, 0, face_camera_angle(center))
        ob.data.materials.append(mat)
        bpy.ops.object.shade_smooth()
        top = center + np.array([0, 0, BAUBLE_R])
        bpy.ops.mesh.primitive_cylinder_add(radius=0.016, depth=0.02, location=top + np.array([0, 0, 0.006]))
        bpy.context.active_object.data.materials.append(gold)
        bpy.ops.mesh.primitive_torus_add(major_radius=0.007, minor_radius=0.0016,
                                         location=top + np.array([0, 0, 0.022]), rotation=(math.radians(90), 0, 0))
        bpy.context.active_object.data.materials.append(gold)
        v, q = tubes([top + np.array([0, 0, 0.024])], [attach], [0.0011], [0.0011], sides=4)
        mesh_object("Thread", v, q, mat=thread)
        spots.append({"day": day, "center": center.tolist(), "radius": BAUBLE_R})

    # day 24: the star on top
    star_mat = decal_material("Star", dict(color=(1.0, 0.50, 0.06), rough=0.22, metal=1.0, coat=0.5,
                                           emit=(1.0, 0.45, 0.06), emit_strength=0.45),
                              dict(color=(0.16, 0.002, 0.006), rough=0.4),
                              os.path.join(DECALS, "num-24.png"), 0.10)
    verts = [(0, -0.11, 0), (0, 0.11, 0)]
    for k in range(10):
        r = 0.23 if k % 2 == 0 else 0.10
        a = math.radians(k * 36)
        verts.append((r * math.sin(a), 0, r * math.cos(a)))
    tris = []
    for k in range(10):
        a, b = 2 + k, 2 + (k + 1) % 10
        tris += [(0, a, b), (1, b, a)]
    star = tri_mesh_object("Star", verts, tris, mat=star_mat, smooth=False)
    star.location = (0, 0, STAR_Z)
    star.rotation_euler = (0, 0, face_camera_angle((0, 0, STAR_Z)))
    glow = bpy.data.lights.new("StarGlow", "POINT")
    glow.energy = 25
    glow.color = (1.0, 0.75, 0.4)
    glow.shadow_soft_size = 0.05
    gl = link(bpy.data.objects.new("StarGlow", glow))
    gl.location = (0, -0.25, STAR_Z - 0.05)
    spots.append({"day": 24, "center": [0, 0, STAR_Z], "radius": 0.23})
    return spots


def camera_and_lights(scene):
    cam_data = bpy.data.cameras.new("Camera")
    cam_data.lens = 85
    cam = link(bpy.data.objects.new("Camera", cam_data))
    cam.location = CAMERA
    cam.rotation_euler = (CAMERA_TARGET - CAMERA).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam

    def area(name, loc, power, size, color):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy = power
        ld.size = size
        ld.color = color
        ob = link(bpy.data.objects.new(name, ld))
        ob.location = loc
        ob.rotation_euler = (Vector((0, 0, 1.6)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()

    area("Key", (-3.2, -4.2, 3.6), 1000, 2.5, (1.0, 0.88, 0.75))        # warm, like firelight
    area("Fill", (3.8, -3.6, 1.6), 340, 3.0, (0.80, 0.86, 1.0))
    area("Rim", (0.5, 4.0, 3.8), 1100, 2.0, (1.0, 0.92, 0.85))
    area("Low", (0.0, -3.0, -0.4), 110, 2.0, (1.0, 0.6, 0.35))           # glow from the fire below

    world = bpy.data.worlds.new("World")
    scene.world = world
    try:
        world.use_nodes = True
    except Exception:
        pass
    nt = world.node_tree
    bg = nt.nodes.get("Background") or nt.nodes.new("ShaderNodeBackground")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[0].color = (0.30, 0.17, 0.09, 1)
    ramp.color_ramp.elements[1].position = 0.65
    ramp.color_ramp.elements[1].color = (0.16, 0.22, 0.38, 1)
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = -1
    mr.inputs["From Max"].default_value = 1
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
    nt.links.new(mr.outputs[0], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.0
    out = nt.nodes.get("World Output") or nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(bg.outputs[0], out.inputs[0])

    r = scene.render
    r.engine = "CYCLES"
    r.resolution_x, r.resolution_y = RES
    r.resolution_percentage = 100
    r.film_transparent = True
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGBA"
    c = scene.cycles
    c.device = "CPU"
    c.samples = SAMPLES
    c.use_adaptive_sampling = True
    c.adaptive_threshold = 0.02
    c.use_denoising = True
    c.max_bounces = 8
    c.diffuse_bounces = 3
    c.glossy_bounces = 4
    c.transmission_bounces = 6
    c.sample_clamp_indirect = 8
    try:
        scene.view_settings.view_transform = "AgX"
        scene.view_settings.look = "AgX - Punchy"
    except TypeError:
        pass


def main():
    t0 = time.time()
    os.makedirs(OUT_DIR, exist_ok=True)
    scene, spots = build_scene()
    print(f"scene built in {time.time() - t0:.0f}s")

    # where every ornament lands in the image, for clickable hotspots on the website
    bpy.context.view_layer.update()          # make sure object matrices are current
    cam = scene.camera
    W, H = RES
    right = (cam.matrix_world.to_3x3() @ Vector((1, 0, 0))).normalized()
    items = []
    for s in sorted(spots, key=lambda s: s["day"]):
        c = Vector(s["center"])
        p = world_to_camera_view(scene, cam, c)
        e = world_to_camera_view(scene, cam, c + right * s["radius"])
        items.append({"day": s["day"],
                      "x": round(p.x, 4), "y": round(1 - p.y, 4),
                      "r": round(abs(e.x - p.x), 4)})
    with open(os.path.join(OUT_DIR, "ornaments.json"), "w") as f:
        json.dump({"image": OUT_NAME, "width": W, "height": H,
                   "note": "x, y and r are fractions of the image width/height (y from the top, r of the width)",
                   "ornaments": items}, f, indent=1)

    scene.render.filepath = os.path.join(OUT_DIR, OUT_NAME)
    t1 = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"rendered {OUT_NAME} in {time.time() - t1:.0f}s")


if __name__ == "__main__":
    main()
