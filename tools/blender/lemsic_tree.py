"""Build and render the realistic LeMSIC Christmas tree in Blender (Cycles).

The tree is a real-looking evergreen grown in the silhouette of the cedar in the
LeMSIC emblem: nine flat tiers, alternately reaching further left and right.
The ornaments trace the serpent of the LeMSIC emblem: a pearl serpent winds
down across the trunk (the staff) and days 1-23 hang along it from head to
tail; day 24 is the star on top.

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
TRUNK_BOTTOM, TRUNK_TOP = 0.20, 3.00
STAR_Z = 3.17
FLOOR_LIFT = 0.0          # raise the skirt and presents when they stand on a rug
BAUBLE_R = 0.072
CAMERA = Vector((0.0, -9.4, 2.15))
CAMERA_TARGET = Vector((0.0, 0.0, 1.66))


# ---------------------------------------------------------------- tree styles
# A style picks the tree's shape, needles, decorations and topper. "serpent" is the
# original design; the others are alternatives to choose from.
SHAPES = {
    "tiers": dict(n=9, z=(2.84, 0.64), r=[0.30, 0.42, 0.55, 0.67, 0.79, 0.91, 1.02, 1.13, 1.24],
                  lop=0.11, nb=(12, 2.0), prof=(0.10, 0.15), tilt=(-0.18, 0.30), twig=1.0),
    "fir": dict(n=17, z=(2.95, 0.50), r=None, lop=0.0, nb=(7, 0.7), prof=(0.12, 0.24),
                tilt=(-0.35, 0.45), twig=0.85),
    "cedar": dict(n=9, z=(2.86, 0.62), r=[0.34, 0.50, 0.65, 0.79, 0.92, 1.03, 1.13, 1.21, 1.28], lop=0.14,
                  nb=(16, 2.6), prof=(0.05, 0.10), tilt=(-0.10, 0.22), twig=1.05, jitter=(0.74, 1.06)),
}
# Lebanese cedar (arz) options: the same needles, colours and decorations as "cedar_lemsic",
# only the tree's form changes. Like the cedar in the LeMSIC emblem (and the real Cedrus libani),
# most grow in a few flat, wide layers with the trunk showing between them.
ARZ_SHAPES = {
    "arz_emblem5": ("Emblem, 5 layers", dict(n=5, z=(2.62, 0.72), r=[0.48, 0.74, 0.96, 1.15, 1.32], lop=0.20, nb=(20, 5),
                                             prof=(0.03, 0.17), tilt=(-0.08, 0.12), twig=1.15, jitter=(0.82, 1.04))),
    "arz_emblem6": ("Emblem, 6 layers", dict(n=6, z=(2.70, 0.66), r=[0.40, 0.62, 0.82, 1.00, 1.16, 1.30], lop=0.18,
                                             nb=(18, 4), prof=(0.03, 0.15), tilt=(-0.08, 0.14), twig=1.10,
                                             jitter=(0.80, 1.04))),
    "arz_flag7": ("Flag cedar, 7 even layers", dict(n=7, z=(2.75, 0.62), r=[0.30, 0.50, 0.70, 0.88, 1.04, 1.18, 1.30],
                                                     lop=0.0, nb=(16, 3.5), prof=(0.02, 0.10), tilt=(-0.06, 0.12),
                                                     twig=1.05, jitter=(0.90, 1.02))),
    "arz_young": ("Young arz, full cone", dict(n=11, z=(2.92, 0.55), r=[0.22, 0.33, 0.44, 0.55, 0.66, 0.76, 0.86, 0.96, 1.06,
                                                                        1.16, 1.25], lop=0.08, nb=(12, 2.2),
                                                 prof=(0.07, 0.12), tilt=(-0.15, 0.28), twig=1.0)),
    "arz_ancient": ("Ancient arz, flat crown", dict(n=6, z=(2.55, 0.75), r=[0.80, 1.00, 1.13, 1.23, 1.30, 1.34], lop=0.16,
                                                    nb=(20, 4), prof=(0.02, 0.12), tilt=(-0.06, 0.12), twig=1.10,
                                                    top=2.74)),
    "arz_sweep": ("Sweeping layers", dict(n=5, z=(2.62, 0.72), r=[0.48, 0.74, 0.96, 1.15, 1.32], lop=0.38, nb=(20, 5),
                                          prof=(0.05, 0.22), tilt=(-0.08, 0.12), twig=1.15, jitter=(0.82, 1.04))),
    "arz_airy": ("Airy layers", dict(n=6, z=(2.70, 0.66), r=[0.40, 0.62, 0.82, 1.00, 1.16, 1.30], lop=0.16, nb=(9, 2),
                                     prof=(0.03, 0.15), tilt=(-0.08, 0.14), twig=0.9, jitter=(0.70, 1.05))),
    "arz_slender": ("Tall and slender", dict(n=7, z=(2.85, 0.60), r=[0.26, 0.40, 0.54, 0.67, 0.79, 0.90, 1.00], lop=0.12,
                                             nb=(14, 3), prof=(0.03, 0.12), tilt=(-0.08, 0.14), twig=1.0)),
    "arz_drooping": ("Drooping layers", dict(n=6, z=(2.70, 0.66), r=[0.40, 0.62, 0.82, 1.00, 1.16, 1.30], lop=0.14,
                                             nb=(18, 4), prof=(0.12, 0.34), tilt=(-0.20, 0.08), twig=1.10)),
}
SHAPES.update({k: v for k, (_, v) in ARZ_SHAPES.items()})
NEEDLE_SETS = {
    "fir": dict(dark=(0.012, 0.040, 0.016), mid=(0.030, 0.085, 0.030), tip=(0.085, 0.190, 0.045),
                blue=(0.016, 0.055, 0.048), length=(0.020, 0.032)),
    "cedar": dict(dark=(0.008, 0.030, 0.024), mid=(0.020, 0.062, 0.048), tip=(0.050, 0.120, 0.080),
                  blue=(0.020, 0.055, 0.065), length=(0.013, 0.024), rosette=True),
}
STYLES = {
    "serpent": dict(label="Pearl Serpent", shape="tiers", needles="fir", palette="classic", placement="serpent",
                    serpent="pearl", topper="star", lights="warm", ornament="bauble", flock=0.0),
    "classic": dict(label="Classic Fir", shape="fir", needles="fir", palette="classic", placement="scatter",
                    serpent="none", topper="star", lights="warm", ornament="bauble", flock=0.0),
    "lemsic": dict(label="LeMSIC Blue", shape="fir", needles="fir", palette="blue_silver", placement="serpent",
                   serpent="ribbon", topper="emblem", lights="white", ornament="bauble", flock=0.0),
    "snowy": dict(label="Snowy", shape="fir", needles="fir", palette="blue_silver", placement="scatter",
                  serpent="none", topper="silver_star", lights="warm", ornament="bauble", flock=0.75),
    "cedar": dict(label="Cedar of Lebanon", shape="cedar", needles="cedar", palette="gold_white",
                  placement="serpent", serpent="gold", topper="star", lights="warm", ornament="bauble", flock=0.0),
    "rustic": dict(label="Rustic", shape="fir", needles="fir", palette="classic", placement="scatter",
                   serpent="none", topper="wood_star", lights="warm", ornament="wood", flock=0.0),
    "cedar_lemsic": dict(label="LeMSIC Cedar", shape="cedar", needles="cedar", palette="lemsic",
                         placement="tiers", serpent="none", topper="emblem", lights="warm", ornament="bauble",
                         flock=0.0, bows=None, skirt=True),
    "cedar_classic": dict(label="Traditional Cedar", shape="cedar", needles="cedar", palette="gold_white",
                          placement="tiers", serpent="none", topper="star", lights="warm", ornament="bauble",
                          flock=0.0, bows="red", skirt=True),
    "cedar_snow": dict(label="Snow-dusted Cedar", shape="cedar", needles="cedar", palette="lemsic",
                       placement="tiers", serpent="none", topper="emblem", lights="warm", ornament="bauble",
                       flock=0.45, bows="blue", skirt=True),
    "glow": dict(label="Glowing Serpent", shape="fir", needles="fir", palette="classic", placement="serpent",
                 serpent="lights", topper="star", lights="warm_few", ornament="bauble", flock=0.0),
}
for _k, (_label, _) in ARZ_SHAPES.items():
    STYLES[_k] = dict(STYLES["cedar_lemsic"], label=_label, shape=_k)
STYLE_NAME = "serpent"
STYLE = STYLES[STYLE_NAME]
SHAPE = SHAPES["tiers"]
NEEDLES = NEEDLE_SETS["fir"]


def apply_style(name):
    """Switch the tree to one of STYLES (call before build_tree)."""
    global STYLE_NAME, STYLE, SHAPE, NEEDLES, N_TIERS, TIER_Z, TIER_R, TRUNK_BOTTOM, TRUNK_TOP, STAR_Z
    STYLE_NAME, STYLE = name, STYLES[name]
    TRUNK_BOTTOM = 0.0 if STYLE.get("skirt") else 0.20         # no crate: the trunk stands in the skirt
    SHAPE = SHAPES[STYLE["shape"]]
    TRUNK_TOP = SHAPE.get("top", 3.00)
    STAR_Z = TRUNK_TOP + 0.17
    NEEDLES = NEEDLE_SETS[STYLE["needles"]]
    N_TIERS = SHAPE["n"]
    TIER_Z = np.linspace(SHAPE["z"][0], SHAPE["z"][1], N_TIERS)
    if SHAPE["r"] is None:                                   # a cone, slightly full in the middle
        t = np.linspace(0, 1, N_TIERS)
        TIER_R = 0.14 + 1.01 * t ** 0.9
    else:
        TIER_R = np.array(SHAPE["r"])


for _a in ARGS:
    if _a.startswith("--style="):
        apply_style(_a[8:])
        OUT_DIR = os.path.join(OUT_DIR, "options")
        OUT_NAME = f"tree-{STYLE_NAME}.png"
    if _a.startswith("--density="):
        DENSITY = float(_a[10:])


def trunk_radius(z):
    t = (z - TRUNK_BOTTOM) / (TRUNK_TOP - TRUNK_BOTTOM)
    return 0.078 * (1 - t) ** 0.85 + 0.006


def lopsided(theta, i):
    """Tiers reach further left and right alternately, like the emblem."""
    bias = math.pi if i % 2 else 0.0
    return 1.0 + SHAPE["lop"] * np.cos(theta - bias)


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


def needles(P, D, Lt, spacing=0.0042, per=3, length=None, width=0.0024, flock=0.0):
    length = length or NEEDLES["length"]
    if NEEDLES.get("rosette") and length == NEEDLES["length"]:
        return rosette_needles(P, D, Lt, length, width * 0.8, flock)
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
    dark, mid, tipc, bluec = (np.array(NEEDLES[k]) for k in ("dark", "mid", "tip", "blue"))
    mix = rng.random(n)[:, None]
    col = dark + (mid - dark) * mix
    blue = rng.random(n) < 0.25
    col[blue] = col[blue] * 0.5 + bluec * 0.5
    col += (tipc - col) * (u ** 5 * 0.85)[:, None]
    if flock:                                    # snow resting on the upward-facing needles
        snowy = (nd[:, 2] > 0.05) & (rng.random(n) < flock * np.clip(nd[:, 2] + 0.6, 0, 1))
        col[snowy] = np.array([0.80, 0.82, 0.86]) * rng.uniform(0.85, 1.0, (snowy.sum(), 1))
    rgba = np.concatenate([col, np.ones((n, 1))], axis=1)
    return verts, quads, np.repeat(rgba, 4, axis=0)


def rosette_needles(P, D, Lt, length, width, flock, spacing=0.017, per=14):
    """Cedar foliage: short needles in tufts (rosettes) on spur shoots along each twig."""
    spacing = spacing / DENSITY
    counts = np.maximum((Lt / spacing).astype(int), 1)
    tw = np.repeat(np.arange(len(P)), counts)
    m = len(tw)
    u = rng.random(m)
    d = D[tw]
    centers = P[tw] + d * (u * Lt[tw])[:, None]
    up = np.array([0.0, 0, 1])
    axis = d * 0.35 + up * 0.75 + rng.normal(0, 0.25, (m, 3))   # tufts stand up off the spray
    axis /= np.linalg.norm(axis, axis=1, keepdims=True)
    centers += axis * 0.004
    idx = np.repeat(np.arange(m), per)
    n = len(idx)
    ax = axis[idx]
    ref = np.where(np.abs(ax[:, 2:3]) < 0.9, [[0.0, 0, 1]], [[1.0, 0, 0]])
    e1 = np.cross(ax, ref)
    e1 /= np.linalg.norm(e1, axis=1, keepdims=True)
    e2 = np.cross(ax, e1)
    spread = np.radians(rng.uniform(10, 62, n))
    rot = rng.uniform(0, 2 * np.pi, n)
    nd = (np.cos(spread)[:, None] * ax + np.sin(spread)[:, None]
          * (np.cos(rot)[:, None] * e1 + np.sin(rot)[:, None] * e2))
    ln = rng.uniform(*length, n) * (0.75 + 0.25 * np.cos(spread))[:]
    base = centers[idx]
    tip = base + nd * ln[:, None]
    wv = np.cross(nd, ax + 1e-3)
    wv /= np.linalg.norm(wv, axis=1, keepdims=True) + 1e-9
    w = width / 2
    verts = np.stack([base - wv * w, base + wv * w, tip + wv * w * 0.2, tip - wv * w * 0.2], axis=1).reshape(-1, 3)
    quads = np.arange(n * 4).reshape(-1, 4)
    dark, mid, tipc, bluec = (np.array(NEEDLES[k]) for k in ("dark", "mid", "tip", "blue"))
    tone = rng.random(m)[idx][:, None] * 0.7 + rng.random(n)[:, None] * 0.3
    col = dark + (mid - dark) * tone
    blue = rng.random(m)[idx] < 0.3
    col[blue] = col[blue] * 0.5 + bluec * 0.5
    fresh = u[idx] ** 4                                   # newer, lighter tufts at the twig ends
    col += (tipc - col) * (fresh * 0.8)[:, None]
    if flock:
        snowy = (nd[:, 2] > 0.3) & (rng.random(n) < flock)
        col[snowy] = np.array([0.80, 0.82, 0.86]) * rng.uniform(0.85, 1.0, (snowy.sum(), 1))
    rgba = np.concatenate([col, np.ones((n, 1))], axis=1)
    return verts, quads, np.repeat(rgba, 4, axis=0)


def rotate_z(vecs, angles):
    c, s = np.cos(angles), np.sin(angles)
    x, y = vecs[:, 0] * c - vecs[:, 1] * s, vecs[:, 0] * s + vecs[:, 1] * c
    return np.stack([x, y, vecs[:, 2]], axis=1)


def build_tier(i):
    """One flat tier of branches. Returns wood segments, twigs, and tier surface samples."""
    z0, R = TIER_Z[i], TIER_R[i]
    nb = int(SHAPE["nb"][0] + SHAPE["nb"][1] * i)
    thetas = rng.uniform(0, 2 * np.pi) + np.arange(nb) * 2 * np.pi / nb + rng.uniform(-0.2, 0.2, nb)
    wood = ([], [], [], [])
    tw_P, tw_D, tw_L = [], [], []
    r0 = trunk_radius(z0)
    for th in thetas:
        L = R * rng.uniform(*SHAPE.get("jitter", (0.86, 1.02))) * lopsided(th, i)
        t = np.linspace(0, 1, 13)
        ang = th + rng.uniform(-0.25, 0.25) * t ** 2
        rad = r0 + t * L
        zz = z0 + L * (SHAPE["prof"][0] * t - SHAPE["prof"][1] * t ** 2) + rng.uniform(-0.05, 0.05)
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
            d2[2] = rng.uniform(*SHAPE["tilt"])
            d2 /= np.linalg.norm(d2)
            l2 = ((0.08 + 0.36 * (1 - tk)) * min(L, 1.15) * rng.uniform(0.8, 1.15) + 0.05) * SHAPE["twig"]
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
    z = TIER_Z[i] + L * (SHAPE["prof"][0] * t - SHAPE["prof"][1] * t ** 2) + 0.02
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
    v, q, c = needles(P, D, Lt, flock=STYLE["flock"])
    mesh_object("Needles", v, q, colors=c, mat=mat_needles)
    print(f"  needles: {len(q):,}  twigs: {len(P):,}")

    fairy_lights()
    stand_and_presents()
    return ornaments()


def fairy_lights():
    kind = STYLE["lights"]
    n = int((120 if kind == "warm_few" else 260) * max(DENSITY, 0.6))
    pts = []
    for _ in range(n):
        i = int(rng.integers(0, N_TIERS))
        th = rng.uniform(0, 2 * np.pi)
        p = tier_surface(i, th, rng.uniform(0.35, 0.97))
        p[2] += rng.uniform(-0.03, 0.02)
        pts.append(p)
    v, q = spheres(np.array(pts), 0.011, icosphere_template(1))
    glow = (0.80, 0.88, 1.0) if kind == "white" else (1.0, 0.62, 0.28)
    mat = simple_material("Bulb", (1.0, 0.75, 0.4), rough=0.3, emit=glow, emit_strength=28)
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


EMBLEM = os.path.join(HERE, "textures", "lemsic-emblem.png")


def emblem_paper():
    """Wrapping paper printed with the LeMSIC emblem (white on LeMSIC blue)."""
    m, nt, out = new_material("PaperLeMSIC")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (9, 9, 9)
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(EMBLEM, check_existing=True)
    tex.projection = "BOX"
    tex.projection_blend = 0.2
    b = principled(nt, (0.05, 0.12, 0.35), rough=0.4)
    b.inputs["Coat Weight"].default_value = 0.3
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs[0], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    return m


def tree_skirt():
    """A LeMSIC-blue velvet tree skirt with soft folds, a white fur trim and the emblem embroidered at the front."""
    rr = np.linspace(0.07, 0.86, 26)
    aa = np.linspace(0, 2 * np.pi, 160, endpoint=False)
    R, A = np.meshgrid(rr, aa, indexing="ij")
    fold = np.sin(A * 11 + 0.6 * np.sin(A * 3)) * (R / 0.86) ** 1.5
    Z = 0.035 * (1 - R / 0.86) + 0.012 + 0.022 * fold * (R > 0.2) + FLOOR_LIFT
    V = np.stack([R * np.cos(A), R * np.sin(A), Z], -1).reshape(-1, 3)
    nr, na = len(rr), len(aa)
    q = [(i * na + j, i * na + (j + 1) % na, (i + 1) * na + (j + 1) % na, (i + 1) * na + j)
         for i in range(nr - 1) for j in range(na)]
    m, nt, out = new_material("SkirtVelvet")
    L = nt.links.new
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    w, h, cy = 0.40, 0.40 * 378 / 453, -0.56
    u = nt.nodes.new("ShaderNodeMath"); u.operation = "MULTIPLY_ADD"
    u.inputs[1].default_value = 1 / w; u.inputs[2].default_value = 0.5
    v = nt.nodes.new("ShaderNodeMath"); v.operation = "MULTIPLY_ADD"
    v.inputs[1].default_value = 1 / h; v.inputs[2].default_value = 0.5 - cy / h
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(EMBLEM, check_existing=True)
    tex.extension = "CLIP"
    bw = nt.nodes.new("ShaderNodeRGBToBW")
    thread = nt.nodes.new("ShaderNodeMapRange")
    thread.inputs["From Min"].default_value = 0.45
    thread.inputs["From Max"].default_value = 0.7
    mixc = nt.nodes.new("ShaderNodeMix"); mixc.data_type = "RGBA"
    mixc.inputs["A"].default_value = (0.02, 0.06, 0.21, 1)
    mixc.inputs["B"].default_value = (0.78, 0.78, 0.80, 1)
    b = principled(nt, (0.02, 0.06, 0.21), rough=0.7)
    b.inputs["Sheen Weight"].default_value = 0.45
    b.inputs["Sheen Roughness"].default_value = 0.35
    b.inputs["Sheen Tint"].default_value = (0.25, 0.4, 0.85, 1)
    L(tc.outputs["Object"], sep.inputs[0])
    L(sep.outputs["X"], u.inputs[0]); L(sep.outputs["Y"], v.inputs[0])
    L(u.outputs[0], comb.inputs["X"]); L(v.outputs[0], comb.inputs["Y"])
    L(comb.outputs[0], tex.inputs["Vector"])
    L(tex.outputs["Color"], bw.inputs[0])
    L(bw.outputs[0], thread.inputs["Value"])
    L(thread.outputs[0], mixc.inputs["Factor"])
    L(mixc.outputs["Result"], b.inputs["Base Color"])
    L(b.outputs[0], out.inputs["Surface"])
    ob = mesh_object("TreeSkirt", V, np.array(q), mat=m, smooth=True)
    # white fur trim around the edge
    fur = simple_material("Fur", (0.82, 0.82, 0.80), rough=1.0)
    fur.node_tree.nodes["Principled BSDF"].inputs["Sheen Weight"].default_value = 1.0
    edge = V.reshape(nr, na, 3)[-1]
    v2, q2 = tubes(edge, np.roll(edge, -1, axis=0), np.full(na, 0.03), np.full(na, 0.03), sides=10)
    mesh_object("SkirtTrim", v2, q2, mat=fur, smooth=True)
    return ob


def stand_and_presents():
    if STYLE.get("skirt"):
        tree_skirt()
    else:
        crate = wood_material("Crate", (0.20, 0.10, 0.045), (0.36, 0.20, 0.09), scale=(3, 30, 3))
        for k in range(3):     # stacked planks
            z = 0.05 + k * 0.105
            box("Plank", (0.62, 0.62, 0.095), (0, 0, z), crate)
    papers = [simple_material("PaperRed", (0.20, 0.003, 0.007), rough=0.55),
              simple_material("PaperGreen", (0.01, 0.08, 0.03), rough=0.4, coat=0.3),
              simple_material("PaperCream", (0.55, 0.47, 0.34), rough=0.5),
              emblem_paper()]                                                     # LeMSIC paper
    gold = simple_material("RibbonGold", (0.9, 0.6, 0.2), rough=0.25, metal=1.0)
    red = simple_material("RibbonRed", (0.5, 0.01, 0.02), rough=0.35, coat=0.6)
    z = FLOOR_LIFT + 0.02 if STYLE.get("skirt") else 0.0
    present((-0.62, -0.30, z), (0.34, 0.30, 0.26), 0.25, papers[0], gold)
    present((-0.95, -0.05, z), (0.24, 0.24, 0.20), -0.3, papers[2], red)
    present((0.60, -0.32, z), (0.30, 0.30, 0.30), -0.2, papers[3], gold)
    present((0.95, -0.10, z), (0.22, 0.26, 0.17), 0.4, papers[1], gold)
    present((0.80, -0.66, FLOOR_LIFT) if STYLE.get("skirt") else (0.30, -0.62, 0), (0.18, 0.18, 0.14), 0.1, papers[0], gold)


BAUBLE_STYLES = [
    # base finish, number finish
    (dict(color=(0.50, 0.015, 0.025), rough=0.12, metal=0.6, coat=1.0),
     dict(color=(0.92, 0.86, 0.72), rough=0.45)),                                         # red
    (dict(color=(0.95, 0.62, 0.20), rough=0.28, metal=0.75, coat=0.6),
     dict(color=(0.20, 0.004, 0.01), rough=0.4)),                                          # gold
    (dict(color=(0.015, 0.17, 0.05), rough=0.14, metal=0.5, coat=1.0),
     dict(color=(0.92, 0.86, 0.72), rough=0.45)),                                         # green
    (dict(color=(0.26, 0.015, 0.10), rough=0.30, metal=0.4, coat=0.5),
     dict(color=(0.92, 0.86, 0.72), rough=0.45)),                                         # plum, satin
    (dict(color=(0.86, 0.88, 0.92), rough=0.26, metal=0.6, coat=0.6),
     dict(color=(0.035, 0.11, 0.33), rough=0.3)),                                          # silver, LeMSIC blue
]
WHITE_NUM = dict(color=(0.92, 0.92, 0.94), rough=0.4)
BLUE_NUM = dict(color=(0.03, 0.10, 0.32), rough=0.35)
GOLD_NUM = dict(color=(1.0, 0.72, 0.30), rough=0.25, metal=1.0)
PALETTES = {
    "classic": BAUBLE_STYLES,
    "blue_silver": [
        (dict(color=(0.025, 0.08, 0.30), rough=0.12, metal=0.5, coat=1.0), WHITE_NUM),     # LeMSIC blue
        (dict(color=(0.85, 0.87, 0.90), rough=0.14, metal=1.0), BLUE_NUM),                 # mirror silver
        (dict(color=(0.80, 0.80, 0.82), rough=0.45, coat=0.3), BLUE_NUM),                  # white satin
        (dict(color=(0.30, 0.45, 0.72), rough=0.35, metal=0.3, coat=0.5), WHITE_NUM),      # ice blue
        (dict(color=(0.008, 0.02, 0.07), rough=0.12, coat=1.0), WHITE_NUM),                # midnight
    ],
    "lemsic": [
        (dict(color=(0.025, 0.08, 0.30), rough=0.12, metal=0.5, coat=1.0), WHITE_NUM),     # LeMSIC blue
        (dict(color=(0.85, 0.87, 0.90), rough=0.14, metal=1.0), BLUE_NUM),                 # mirror silver
        (dict(color=(0.80, 0.80, 0.82), rough=0.45, coat=0.3), BLUE_NUM),                  # white satin
        (dict(color=(0.95, 0.66, 0.25), rough=0.22, metal=0.85, coat=0.5), BLUE_NUM),      # warm gold
        (dict(color=(0.30, 0.45, 0.72), rough=0.35, metal=0.3, coat=0.5), WHITE_NUM),      # ice blue
    ],
    "gold_white": [
        (dict(color=(0.95, 0.62, 0.20), rough=0.22, metal=0.85, coat=0.6), dict(color=(0.25, 0.005, 0.01), rough=0.4)),
        (dict(color=(0.72, 0.68, 0.60), rough=0.2, coat=1.0), GOLD_NUM),                   # ivory pearl
        (dict(color=(0.40, 0.012, 0.02), rough=0.15, metal=0.5, coat=1.0), GOLD_NUM),      # deep red
        (dict(color=(0.75, 0.58, 0.40), rough=0.45, metal=0.5), WHITE_NUM),                # champagne satin
        (dict(color=(0.02, 0.10, 0.04), rough=0.15, metal=0.4, coat=1.0), GOLD_NUM),       # forest green
    ],
}


def face_camera_angle(pos):
    v = Vector(CAMERA) - Vector(pos)
    return math.atan2(v.x, -v.y)


# ---------------------------------------------------------------- the serpent
SERPENT_SWEEPS = 7
SERPENT_TOP, SERPENT_BOTTOM = 2.62, 0.86
SERPENT_SPAN = math.radians(66)


def surface_radius(z, theta):
    """Outer radius of the foliage at height z (between tiers it follows the cone)."""
    r = np.interp(z, TIER_Z[::-1], TIER_R[::-1])
    i = int(np.argmin(np.abs(TIER_Z - z)))
    return r * lopsided(theta, i)


def serpent_path():
    """The LeMSIC serpent winding down the front of the tree, head (top) to tail (bottom).

    Like the emblem, it sweeps across the staff (the trunk) from side to side,
    each sweep slanting down and turning in a rounded loop at the side.
    """
    front = -math.pi / 2
    dz = (SERPENT_TOP - SERPENT_BOTTOM) / SERPENT_SWEEPS
    pts = []
    for k in range(SERPENT_SWEEPS):
        d = 1 if k % 2 == 0 else -1                 # first sweep runs left to right
        z0 = SERPENT_TOP - k * dz
        for t in np.linspace(0, 1, 90, endpoint=False):
            phi = d * SERPENT_SPAN * (2 * t - 1)
            pts.append((front + phi, z0 - 0.62 * dz * t))
        if k < SERPENT_SWEEPS - 1:                  # rounded turn at the side
            for t in np.linspace(0, 1, 24, endpoint=False):
                phi = d * (SERPENT_SPAN + math.radians(9) * math.sin(math.pi * t))
                pts.append((front + phi, z0 - 0.62 * dz - 0.38 * dz * t))
    out = []
    for th, z in pts:
        r = surface_radius(z, th) * 0.98 + 0.035
        out.append((r * math.cos(th), r * math.sin(th), z))
    side = np.array([abs(th - front) for th, z in pts])
    return np.array(out), side


def serpent_body(path, kind):
    """Draw the serpent along `path`: pearls or gold beads with a head, a satin ribbon, or lights."""
    if kind == "none":
        return
    seg = np.linalg.norm(np.diff(path, axis=0), axis=1)
    arc = np.concatenate([[0], np.cumsum(seg)])
    L = arc[-1]
    at = lambda s_at: np.array([np.interp(s_at, arc, path[:, k]) for k in range(3)])

    if kind == "ribbon":
        tang = np.gradient(path, axis=0)
        tang /= np.linalg.norm(tang, axis=1, keepdims=True)
        radial = path.copy()
        radial[:, 2] = 0
        radial /= np.linalg.norm(radial, axis=1, keepdims=True)
        across = np.cross(tang, radial)
        across /= np.linalg.norm(across, axis=1, keepdims=True)
        width = 0.032 * (1 - 0.55 * (arc / L))[:, None]
        verts = np.concatenate([path + across * width, path - across * width])
        n = len(path)
        quads = np.array([(i, i + 1, n + i + 1, n + i) for i in range(n - 1)])
        satin = simple_material("Satin", (0.80, 0.80, 0.80), rough=0.32)
        satin.node_tree.nodes["Principled BSDF"].inputs["Sheen Weight"].default_value = 0.8
        mesh_object("SerpentRibbon", verts, quads, mat=satin, smooth=True)
        return

    if kind == "lights":
        wire = simple_material("Wire", (0.01, 0.025, 0.012), rough=0.5)
        v, q = tubes(path[:-1], path[1:], np.full(len(path) - 1, 0.0028), np.full(len(path) - 1, 0.0028), sides=5)
        mesh_object("SerpentWire", v, q, mat=wire, smooth=True)
        bulbs = np.array([at(x) for x in np.arange(0.02, L, 0.042)])
        v, q = spheres(bulbs, 0.0105, icosphere_template(2))
        mat = simple_material("SerpentBulb", (1.0, 0.8, 0.5), rough=0.3, emit=(1.0, 0.66, 0.30), emit_strength=40)
        ob = tri_mesh_object("SerpentLights", v, q[:, :3], mat=mat)
        ob.visible_shadow = False
        return

    # beads (pearl or gold), tapering to the tail, with a head at the top
    centers, radii = [], []
    s_at = 0.05
    while s_at < L:
        f = s_at / L
        r = 0.016 - 0.011 * f ** 0.8
        centers.append(at(s_at))
        radii.append(r)
        s_at += r * 1.9
    v, tris = icosphere_template(2)
    centers, radii = np.array(centers), np.array(radii)
    verts = (centers[:, None, :] + v[None] * radii[:, None, None]).reshape(-1, 3)
    faces = (tris[None] + (np.arange(len(centers)) * len(v))[:, None, None]).reshape(-1, 3)
    if kind == "gold":
        bead = simple_material("SerpentGold", (0.95, 0.66, 0.25), rough=0.18, metal=1.0)
    else:
        bead = simple_material("SerpentPearl", (0.66, 0.63, 0.56), rough=0.2, coat=1.0)
        bead.node_tree.nodes["Principled BSDF"].inputs["Sheen Weight"].default_value = 0.4
    tri_mesh_object("Serpent", verts, faces, mat=bead)

    head_pos = path[0]
    out_dir = path[0] - path[6]
    out_dir[2] = 0.0
    out_dir = out_dir / np.linalg.norm(out_dir)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=40, ring_count=20, radius=1.0)
    head = bpy.context.active_object
    hv = np.array([vx.co[:] for vx in head.data.vertices])
    taper = 1 - 0.42 * np.clip(hv[:, 0], 0, 1)
    hv[:, 0] *= 0.085
    hv[:, 1] *= 0.050 * taper
    hv[:, 2] *= 0.036 * taper * (1 + 0.15 * (hv[:, 2] > 0))
    for vx, co in zip(head.data.vertices, hv):
        vx.co = co
    head.data.update()
    bpy.ops.object.shade_smooth()
    head.data.materials.append(bead)
    head.rotation_euler = Vector((out_dir[0], out_dir[1], 0.25)).to_track_quat("X", "Z").to_euler()
    head.location = Vector(head_pos) + Vector(out_dir.tolist()) * 0.06 + Vector((0, 0, 0.014))
    head.name = "SerpentHead"
    eye = simple_material("SerpentEye", (0.01, 0.01, 0.012), rough=0.05, coat=1.0)
    tongue = simple_material("SerpentTongue", (0.35, 0.01, 0.02), rough=0.4)
    for side in (-1, 1):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=0.0085,
                                             location=(0.036, side * 0.033, 0.016))
        e = bpy.context.active_object
        e.data.materials.append(eye)
        e.parent = head
    for side in (-1, 1):
        a = Vector((0.08, 0, -0.006))
        b = Vector((0.118, side * 0.011, -0.008))
        v2, q2 = tubes([a[:], (0.097, 0, -0.007)], [(0.097, 0, -0.007), b[:]], [0.0022, 0.0019], [0.0019, 0.0013], sides=6)
        t = mesh_object("Tongue", v2, q2, mat=tongue, smooth=True)
        t.parent = head


def tier_counts(total):
    """Spread `total` ornaments over the layers below the top one, more on the wider layers."""
    w = np.array(TIER_R, float) ** 1.3
    w[0] = 0.0
    raw = w / w.sum() * total
    counts = np.floor(raw).astype(int)
    for i in np.argsort(-(raw - counts))[: total - counts.sum()]:
        counts[i] += 1
    return [int(c) for c in counts]


def ornament_slots():
    """Where days 1-23 hang: along the serpent (in order) or scattered over the tree (mixed)."""
    if STYLE["placement"] == "serpent":
        path, side = serpent_path()
        serpent_body(path, STYLE["serpent"])
        seg = np.linalg.norm(np.diff(path, axis=0), axis=1)
        arc = np.concatenate([[0], np.cumsum(seg)])
        facing = (side < SERPENT_SPAN * 0.80) & (arc > 0.12) & (arc < arc[-1] - 0.12)
        seg_facing = np.concatenate([[0], np.where(facing[1:] & facing[:-1], seg, 0)])
        usable = np.cumsum(seg_facing)
        slots = []
        for u in (np.arange(23) + 0.5) / 23 * usable[-1]:
            s_at = np.interp(u, usable, arc)
            slots.append(np.array([np.interp(s_at, arc, path[:, k]) for k in range(3)]))
        return list(zip(range(1, 24), slots))
    days = list(range(1, 24))
    random.Random(1964).shuffle(days)
    if STYLE["placement"] == "tiers":
        # hung from the edges of the layers, spread across the front; days in a mixed order
        counts = {9: [0, 1, 2, 2, 3, 3, 4, 4, 4]}.get(N_TIERS) or tier_counts(23)
        slots = []
        for i, count in enumerate(counts):
            if not count:
                continue
            span = math.radians(60 if count > 1 else 0)
            phis = np.linspace(-span, span, count) if count > 1 else np.array([math.radians(-10)])
            for phi in phis:
                th = -math.pi / 2 + phi + rng.uniform(-0.07, 0.07)
                p = tier_surface(i, th, rng.uniform(0.86, 0.94))
                p[2] -= 0.02
                slots.append(p)
        return list(zip(days, slots))
    # scattered in staggered rows over the front of the tree; days in a mixed order
    rows = [1, 2, 3, 3, 4, 5, 5]
    zs = np.linspace(2.55, 0.95, len(rows))
    slots = []
    for count, z in zip(rows, zs):
        span = math.radians(14 + 7 * count)
        phis = np.linspace(-span, span, count) if count > 1 else np.array([0.0])
        for phi in phis:
            th = -math.pi / 2 + phi + rng.uniform(-0.06, 0.06)
            zz = z + rng.uniform(-0.05, 0.05)
            r = surface_radius(zz, th) * 0.97 + 0.03
            slots.append(np.array([r * math.cos(th), r * math.sin(th), zz + 0.06]))
    return list(zip(days, slots))


def hang_bauble(day, n, attach, gold, thread):
    palette = PALETTES[STYLE["palette"]]
    center = attach - np.array([0, 0, 0.018 + 0.02 + BAUBLE_R])
    base_kw, dec_kw = palette[n % len(palette)]
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
    return center, BAUBLE_R


def hang_wood_slice(day, attach, twine):
    """A slice of log with the day burnt into it, hung on red twine."""
    r, d = 0.075, 0.022
    center = attach - np.array([0, 0, 0.03 + r])
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=r, depth=d)
    ob = bpy.context.active_object
    me = ob.data
    for vx in me.vertices:                       # disc axis along local Y, face towards -Y
        x, y, z = vx.co
        jag = 1 + 0.05 * math.sin(7 * math.atan2(y, x)) * (abs(z) < d / 2 + 1e-6)
        vx.co = (x * jag, -z, y * jag)
    me.update()
    face = decal_material(f"Slice{day}", dict(color=(0.48, 0.32, 0.18), rough=0.7),
                          dict(color=(0.05, 0.022, 0.01), rough=0.85),
                          os.path.join(DECALS, f"num-{day:02d}.png"), r * 0.82)
    me.materials.append(face)
    me.materials.append(bpy.data.materials["Bark"])
    for poly in me.polygons:
        poly.material_index = 0 if abs(poly.normal.y) > 0.5 else 1
    bpy.ops.object.shade_smooth()
    bev = ob.modifiers.new("bevel", "BEVEL")
    bev.width = 0.004
    ob.location = center
    ob.rotation_euler = (0, 0, face_camera_angle(center))
    ob.name = f"Ornament{day:02d}"
    v, q = tubes([center + np.array([0, 0, r * 0.95])], [attach], [0.0016], [0.0016], sides=5)
    mesh_object("Twine", v, q, mat=twine)
    return center, r


def star_mesh(name, mat):
    verts = [(0, -0.11, 0), (0, 0.11, 0)]
    for k in range(10):
        rr = 0.23 if k % 2 == 0 else 0.10
        a = math.radians(k * 36)
        verts.append((rr * math.sin(a), 0, rr * math.cos(a)))
    tris = []
    for k in range(10):
        a, b = 2 + k, 2 + (k + 1) % 10
        tris += [(0, a, b), (1, b, a)]
    star = tri_mesh_object(name, verts, tris, mat=mat, smooth=False)
    star.location = (0, 0, STAR_Z)
    star.rotation_euler = (0, 0, face_camera_angle((0, 0, STAR_Z)))
    return star


def topper():
    """Day 24 on top of the tree: a star, or the LeMSIC emblem."""
    kind = STYLE["topper"]
    num24 = os.path.join(DECALS, "num-24.png")
    glow_col = (1.0, 0.75, 0.4)
    if kind == "star":
        mat = decal_material("Star", dict(color=(1.0, 0.50, 0.06), rough=0.22, metal=1.0, coat=0.5,
                                          emit=(1.0, 0.45, 0.06), emit_strength=0.45),
                             dict(color=(0.16, 0.002, 0.006), rough=0.4), num24, 0.10)
        star_mesh("Star", mat)
    elif kind == "silver_star":
        mat = decal_material("Star", dict(color=(0.88, 0.9, 0.95), rough=0.15, metal=1.0,
                                          emit=(0.7, 0.8, 1.0), emit_strength=0.25), BLUE_NUM, num24, 0.10)
        star_mesh("Star", mat)
        glow_col = (0.85, 0.9, 1.0)
    elif kind == "wood_star":
        mat = decal_material("Star", dict(color=(0.45, 0.28, 0.14), rough=0.6),
                             dict(color=(0.05, 0.022, 0.01), rough=0.85), num24, 0.10)
        star_mesh("Star", mat)
    else:                                        # the LeMSIC emblem as a medallion
        R = 0.165
        bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=R, depth=0.03)
        ob = bpy.context.active_object
        for vx in ob.data.vertices:
            x, y, z = vx.co
            vx.co = (x, -z, y)
        ob.data.update()
        m, nt, out = new_material("Star")
        tc = nt.nodes.new("ShaderNodeTexCoord")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        u = nt.nodes.new("ShaderNodeMath"); u.operation = "MULTIPLY_ADD"
        u.inputs[1].default_value = 0.5 / R * 378 / 453; u.inputs[2].default_value = 0.5
        v = nt.nodes.new("ShaderNodeMath"); v.operation = "MULTIPLY_ADD"
        v.inputs[1].default_value = 0.5 / R; v.inputs[2].default_value = 0.5
        comb = nt.nodes.new("ShaderNodeCombineXYZ")
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(EMBLEM, check_existing=True)
        tex.extension = "EXTEND"
        b = principled(nt, (0.1, 0.2, 0.5), rough=0.45, emit=(1, 1, 1), emit_strength=0.0)
        b.inputs["Coat Weight"].default_value = 0.15             # satin, so lights don't wash it out
        em = nt.nodes.new("ShaderNodeMath"); em.operation = "MULTIPLY"; em.inputs[1].default_value = 0.0
        L = nt.links.new
        L(tc.outputs["Object"], sep.inputs[0])
        L(sep.outputs["X"], u.inputs[0]); L(sep.outputs["Z"], v.inputs[0])
        L(u.outputs[0], comb.inputs["X"]); L(v.outputs[0], comb.inputs["Y"])
        L(comb.outputs[0], tex.inputs["Vector"])
        L(tex.outputs["Color"], b.inputs["Base Color"])
        L(tex.outputs["Color"], b.inputs["Emission Color"])
        L(tex.outputs["Alpha"], em.inputs[0])
        L(em.outputs[0], b.inputs["Emission Strength"])
        L(b.outputs[0], out.inputs["Surface"])
        ob.data.materials.append(m)
        ob.location = (0, 0, STAR_Z)
        ob.rotation_euler = (0, 0, face_camera_angle((0, 0, STAR_Z)))
        ob.name = "Star"
        rim = simple_material("MedallionRim", (0.88, 0.9, 0.95), rough=0.15, metal=1.0)
        bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=0.014, major_segments=64,
                                         location=(0, 0, STAR_Z), rotation=(math.radians(90), 0, 0))
        tor = bpy.context.active_object
        tor.rotation_euler = (math.radians(90), 0, face_camera_angle((0, 0, STAR_Z)))
        tor.data.materials.append(rim)
        bpy.ops.object.shade_smooth()
        glow_col = (1.0, 0.85, 0.65)
    glow = bpy.data.lights.new("StarGlow", "POINT")
    glow.energy = 6 if kind == "emblem" else 25
    glow.color = glow_col
    glow.shadow_soft_size = 0.05
    gl = link(bpy.data.objects.new("StarGlow", glow))
    gl.location = (0, -0.25, STAR_Z - (0.3 if kind == "emblem" else 0.05))
    return {"day": 24, "center": [0, 0, STAR_Z], "radius": 0.23}


def ornaments():
    gold = simple_material("CapGold", (0.9, 0.62, 0.22), rough=0.2, metal=1.0)
    thread = simple_material("Thread", (0.9, 0.7, 0.3), rough=0.4, metal=0.6)
    twine = simple_material("Twine", (0.35, 0.02, 0.02), rough=0.9)
    spots = []
    for n, (day, attach) in enumerate(ornament_slots()):
        if STYLE["ornament"] == "wood":
            c, r = hang_wood_slice(day, attach, twine)
        else:
            c, r = hang_bauble(day, n, attach, gold, thread)
        spots.append({"day": day, "center": c.tolist(), "radius": r})
    spots.append(topper())
    if STYLE.get("bows"):
        velvet_bows(spots)
    return spots


def velvet_bow(loc, facing, mat, size=0.095):
    """A velvet bow: two loops, a knot and two tails, tied onto a branch."""
    parts = []
    for side in (-1, 1):
        bpy.ops.mesh.primitive_torus_add(major_radius=size * 0.55, minor_radius=size * 0.16,
                                         major_segments=32, minor_segments=10)
        lp = bpy.context.active_object
        lp.scale = (1.0, 0.68, 0.5)
        lp.location = (side * size * 0.55, 0, 0.0)
        lp.rotation_euler = (math.radians(90), math.radians(side * 18), 0)
        parts.append(lp)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=size * 0.2, segments=16, ring_count=8)
    knot = bpy.context.active_object
    knot.scale = (1, 0.7, 1.1)
    parts.append(knot)
    for side in (-1, 1):
        bpy.ops.mesh.primitive_cube_add(size=1)
        t = bpy.context.active_object
        t.scale = (size * 0.32, size * 0.05, size * 1.5)
        t.location = (side * size * 0.28, 0.005, -size * 0.75)
        t.rotation_euler = (0, math.radians(side * -14), 0)
        parts.append(t)
    for ob in parts:
        ob.data.materials.append(mat)
        ob.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    with bpy.context.temp_override(active_object=parts[0], selected_editable_objects=parts, selected_objects=parts):
        bpy.ops.object.join()
    bow = parts[0]
    with bpy.context.temp_override(active_object=bow, object=bow, selected_objects=[bow],
                                   selected_editable_objects=[bow]):
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.shade_smooth()
    bow.location = loc
    bow.rotation_euler = (0, 0, facing)
    bow.name = "Bow"
    return bow


def velvet_bows(spots):
    colour = (0.02, 0.06, 0.22) if STYLE["bows"] == "blue" else (0.28, 0.004, 0.01)
    mat = simple_material("Velvet", colour, rough=0.6)
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Sheen Weight"].default_value = 0.6
    bsdf.inputs["Sheen Roughness"].default_value = 0.35
    bsdf.inputs["Sheen Tint"].default_value = (*[min(1, c * 4) for c in colour], 1)
    taken = [np.array(s["center"]) for s in spots]
    placed = 0
    for i in range(2, N_TIERS):
        for phi in (-0.95, -0.35, 0.3, 0.9):
            if placed >= 11:
                return
            th = -math.pi / 2 + phi + rng.uniform(-0.12, 0.12)
            p = tier_surface(i, th, 0.97)
            p[2] += 0.025
            if min(np.linalg.norm(p - t) for t in taken) < 0.3 or rng.random() < 0.55:
                continue
            velvet_bow(p, face_camera_angle(p), mat)
            taken.append(p)
            placed += 1


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
