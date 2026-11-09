"""Realistic building blocks for the cabin: fieldstone masonry, hewn logs, plank
floor, a braided rug and knitted stockings. Everything is real geometry with
procedural materials, generated with numpy so it builds in seconds.
"""
import math

import bmesh
import bpy
import numpy as np

from lemsic_tree import link, new_material, principled


# ---------------------------------------------------------------- generic mesh builder
def build_mesh(name, verts, faces, attrs=None, mats=None, mat_index=None, smooth=True):
    """faces: (N,4) quads; a triangle is written as a quad with its last index repeated."""
    verts = np.asarray(verts, np.float32)
    faces = np.asarray(faces, np.int32)
    tri = faces[:, 2] == faces[:, 3]
    sizes = np.where(tri, 3, 4)
    loops = np.concatenate([f[:n] for f, n in zip(faces, sizes)]) if tri.any() else faces.ravel()
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(verts))
    me.vertices.foreach_set("co", verts.ravel())
    me.loops.add(len(loops))
    me.loops.foreach_set("vertex_index", loops.astype(np.int32))
    me.polygons.add(len(faces))
    me.polygons.foreach_set("loop_start", np.concatenate([[0], np.cumsum(sizes)[:-1]]).astype(np.int32))
    me.update(calc_edges=True)
    if smooth:
        me.polygons.foreach_set("use_smooth", np.ones(len(faces), bool))
    for aname, (domain, data) in (attrs or {}).items():
        data = np.asarray(data, np.float32)
        if data.ndim == 1:
            at = me.attributes.new(aname, "FLOAT", domain)
            at.data.foreach_set("value", data)
        elif data.shape[1] == 3:
            at = me.attributes.new(aname, "FLOAT_VECTOR", domain)
            at.data.foreach_set("vector", data.ravel())
        else:
            at = me.attributes.new(aname, "FLOAT_COLOR", domain)
            at.data.foreach_set("color", data.ravel())
    for m in mats or []:
        me.materials.append(m)
    if mat_index is not None:
        me.polygons.foreach_set("material_index", np.asarray(mat_index, np.int32))
    return link(bpy.data.objects.new(name, me))


def node(nt, kind, **inputs):
    n = nt.nodes.new(kind)
    for k, v in inputs.items():
        n.inputs[k].default_value = v
    return n


def attr_node(nt, name, kind="GEOMETRY"):
    a = nt.nodes.new("ShaderNodeAttribute")
    a.attribute_name = name
    a.attribute_type = kind
    return a


def mix_rgb(nt, mode="MIX", fac=0.5):
    m = nt.nodes.new("ShaderNodeMix")
    m.data_type = "RGBA"
    m.blend_type = mode
    m.inputs["Factor"].default_value = fac
    return m


# ---------------------------------------------------------------- fieldstone
def rounded_box_template(cuts=5):
    bpy.ops.mesh.primitive_cube_add(size=2)
    ob = bpy.context.active_object
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)
    bm.to_mesh(ob.data)
    bm.free()
    v = np.array([vx.co[:] for vx in ob.data.vertices])
    q = np.array([p.vertices[:] for p in ob.data.polygons])
    bpy.data.objects.remove(ob, do_unlink=True)
    inner = 0.38
    c = np.clip(v, -inner, inner)
    d = v - c
    d /= np.linalg.norm(d, axis=1, keepdims=True) + 1e-9
    return c + d * (1 - inner), q


STONE_TONES = np.array([
    (0.30, 0.28, 0.25), (0.36, 0.33, 0.28), (0.24, 0.23, 0.22), (0.33, 0.27, 0.21),
    (0.40, 0.37, 0.32), (0.27, 0.25, 0.24), (0.31, 0.25, 0.19), (0.22, 0.21, 0.20),
])


def lay_stones(rnd, origin, ax_u, ax_v, normal, width, height, holes=(), course=(0.075, 0.15),
               length=(0.13, 0.33), depth=(0.07, 0.11), proud=0.028, gap=0.014):
    """Stones in rough courses over the rectangle [0,width]x[0,height] of a wall face.

    origin is the bottom-left corner of the face, ax_u / ax_v span it, and normal points out.
    holes are (u0, v0, u1, v1) rectangles left empty. Returns a list of stone records.
    """
    origin, ax_u, ax_v, normal = (np.asarray(x, float) for x in (origin, ax_u, ax_v, normal))
    stones = []
    v = 0.0
    while v < height - 0.03:
        h = rnd.uniform(*course)
        if height - (v + h) < 0.05:
            h = height - v
        u = -rnd.uniform(0.0, 0.12)
        while u < width:
            w = rnd.uniform(*length)
            pieces = [(max(u, 0.0), min(u + w, width))]
            for hu0, hv0, hu1, hv1 in holes:
                if v < hv1 and v + h > hv0:
                    pieces = [p for a, b in pieces for p in ((a, min(b, hu0)), (max(a, hu1), b))]
            for a, b in pieces:
                if b - a < 0.05:
                    continue
                hh = (h - gap) * rnd.uniform(0.8, 1.0)
                hs = np.array([(b - a - gap) / 2, hh / 2, rnd.uniform(*depth) / 2])
                cu, cv = (a + b) / 2, v + h / 2 + rnd.uniform(-0.006, 0.006)
                pr = proud * rnd.uniform(0.6, 1.25)
                center = origin + ax_u * cu + ax_v * cv + normal * (pr - hs[2])
                ang = rnd.normal(0, 0.035, 3)
                stones.append((center, hs, np.stack([ax_u, ax_v, normal], 1), ang, rnd.integers(len(STONE_TONES))))
            u += w
        v += h
    return stones


def rot_xyz(a):
    cx, sx, cy, sy, cz, sz = math.cos(a[0]), math.sin(a[0]), math.cos(a[1]), math.sin(a[1]), math.cos(a[2]), math.sin(a[2])
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def stone_mesh(name, stones, rnd, mat, soot_center=None, soot_radius=0.5):
    tv, tq = rounded_box_template(5)
    V, Q, C, S = [], [], [], []
    for k, (center, hs, basis, ang, tone) in enumerate(stones):
        p = tv.copy()
        lump = np.zeros(len(p))
        for _ in range(5):
            f = rnd.normal(0, 2.4, 3)
            lump += np.sin(p @ f + rnd.uniform(0, 6.3)) * rnd.uniform(0.02, 0.07)
        p *= (1 + lump)[:, None]
        p[:, 2] *= np.where(p[:, 2] > 0, 1.0, 0.6)          # flatter at the back
        p = (p * hs) @ rot_xyz(ang).T @ basis.T + center
        V.append(p)
        Q.append(tq + k * len(tv))
        col = STONE_TONES[tone] * rnd.uniform(0.85, 1.12)
        C.append(np.tile(np.append(col, 1), (len(p), 1)))
        if soot_center is not None:
            d = np.linalg.norm(p - soot_center, axis=1)
            S.append(np.clip(1 - d / soot_radius, 0, 1) ** 1.5)
        else:
            S.append(np.zeros(len(p)))
    return build_mesh(name, np.concatenate(V), np.concatenate(Q),
                      attrs={"scol": ("POINT", np.concatenate(C)), "soot": ("POINT", np.concatenate(S))},
                      mats=[mat])


def fieldstone_material():
    m, nt, out = new_material("Fieldstone")
    L = nt.links.new
    tc = nt.nodes.new("ShaderNodeTexCoord")
    col = attr_node(nt, "scol")
    soot = attr_node(nt, "soot")
    mottle = node(nt, "ShaderNodeTexNoise", Scale=9.0, Detail=6.0, Roughness=0.6)
    fine = node(nt, "ShaderNodeTexNoise", Scale=70.0, Detail=8.0, Roughness=0.7)
    speck = nt.nodes.new("ShaderNodeTexVoronoi")
    speck.inputs["Scale"].default_value = 140.0
    m1 = mix_rgb(nt, "OVERLAY", 0.55)
    m2 = mix_rgb(nt, "MULTIPLY", 0.25)
    soot_mix = mix_rgb(nt, "MIX")
    soot_mix.inputs["B"].default_value = (0.02, 0.018, 0.016, 1)
    soot_fac = node(nt, "ShaderNodeMath")
    soot_fac.operation = "MULTIPLY"
    soot_fac.inputs[1].default_value = 0.9
    h = node(nt, "ShaderNodeMath")
    h.operation = "MULTIPLY_ADD"
    h.inputs[1].default_value = 0.35
    bump = node(nt, "ShaderNodeBump", Strength=0.55, Distance=0.01)
    rough = node(nt, "ShaderNodeMapRange")
    rough.inputs["To Min"].default_value = 0.68
    rough.inputs["To Max"].default_value = 0.95
    b = principled(nt, (0.3, 0.28, 0.25), rough=0.85)
    L(tc.outputs["Object"], mottle.inputs["Vector"])
    L(tc.outputs["Object"], fine.inputs["Vector"])
    L(tc.outputs["Object"], speck.inputs["Vector"])
    L(col.outputs["Color"], m1.inputs["A"])
    L(mottle.outputs["Color"], m1.inputs["B"])
    L(m1.outputs["Result"], m2.inputs["A"])
    L(speck.outputs["Color"], m2.inputs["B"])
    L(soot.outputs["Fac"], soot_fac.inputs[0])
    L(soot_fac.outputs[0], soot_mix.inputs["Factor"])
    L(m2.outputs["Result"], soot_mix.inputs["A"])
    L(soot_mix.outputs["Result"], b.inputs["Base Color"])
    L(fine.outputs["Fac"], h.inputs[0])
    L(mottle.outputs["Fac"], h.inputs[2])
    L(h.outputs[0], bump.inputs["Height"])
    L(bump.outputs["Normal"], b.inputs["Normal"])
    L(mottle.outputs["Fac"], rough.inputs["Value"])
    L(rough.outputs[0], b.inputs["Roughness"])
    L(b.outputs[0], out.inputs["Surface"])
    return m


def mortar_material():
    m, nt, out = new_material("Mortar")
    L = nt.links.new
    tc = nt.nodes.new("ShaderNodeTexCoord")
    n = node(nt, "ShaderNodeTexNoise", Scale=90.0, Detail=10.0)
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.17, 0.16, 0.145, 1)
    ramp.color_ramp.elements[1].color = (0.30, 0.285, 0.26, 1)
    bump = node(nt, "ShaderNodeBump", Strength=0.6, Distance=0.004)
    b = principled(nt, (0.25, 0.24, 0.22), rough=0.97)
    L(tc.outputs["Object"], n.inputs["Vector"])
    L(n.outputs["Fac"], ramp.inputs["Fac"])
    L(n.outputs["Fac"], bump.inputs["Height"])
    L(ramp.outputs["Color"], b.inputs["Base Color"])
    L(bump.outputs["Normal"], b.inputs["Normal"])
    L(b.outputs[0], out.inputs["Surface"])
    return m


# ---------------------------------------------------------------- hewn logs
def logs_mesh(name, logs, rnd, mats, sides=30, rings_per_m=14):
    """logs: list of (start, end, radius). Uneven, slightly bowed logs with end caps.
    Material 0 is the side of the log, material 1 the sawn end grain."""
    V, Q, MI, TONE = [], [], [], []
    base = 0
    for start, end, r in logs:
        start, end = np.asarray(start, float), np.asarray(end, float)
        axis = end - start
        L = np.linalg.norm(axis)
        axis /= L
        ref = np.array([0.0, 0, 1]) if abs(axis[2]) < 0.9 else np.array([1.0, 0, 0])
        u = np.cross(axis, ref)
        u /= np.linalg.norm(u)
        w = np.cross(axis, u)
        nr = max(4, int(L * rings_per_m))
        t = np.linspace(0, 1, nr + 1)
        bow = rnd.normal(0, 0.012, 2)
        ang = np.linspace(0, 2 * np.pi, sides, endpoint=False)
        # radius: slow taper, lumps along the length, flattish hewn faces around
        rr = r * (1 + 0.05 * (t - 0.5) * rnd.choice([-1, 1]))
        for _ in range(3):
            rr = rr * (1 + rnd.uniform(0.01, 0.03) * np.sin(t * rnd.uniform(3, 12) + rnd.uniform(0, 6)))
        around = np.ones(sides)
        for _ in range(3):
            around += rnd.uniform(0.01, 0.035) * np.cos(ang * rnd.integers(2, 6) + rnd.uniform(0, 6))
        centers = start + np.outer(t * L, axis) + np.outer(np.sin(np.pi * t), bow[0] * u + bow[1] * w)
        ring = np.cos(ang)[:, None] * u + np.sin(ang)[:, None] * w
        pts = centers[:, None, :] + (rr[:, None, None] * around[None, :, None]) * ring[None]
        pts = pts.reshape(-1, 3)
        k = np.arange(sides)
        q = []
        for i in range(nr):
            a0, a1 = i * sides, (i + 1) * sides
            q.append(np.stack([a0 + k, a0 + (k + 1) % sides, a1 + (k + 1) % sides, a1 + k], 1))
        q = np.concatenate(q) + base
        caps_v = np.array([centers[0], centers[-1]])
        c0, c1 = base + len(pts), base + len(pts) + 1
        cap0 = np.stack([np.full(sides, c0), base + (k + 1) % sides, base + k, base + k], 1)
        last = base + nr * sides
        cap1 = np.stack([np.full(sides, c1), last + k, last + (k + 1) % sides, last + (k + 1) % sides], 1)
        V += [pts, caps_v]
        Q += [q, cap0, cap1]
        MI += [np.zeros(len(q)), np.ones(sides), np.ones(sides)]
        tone = rnd.uniform(0, 1)
        TONE.append(np.full(len(pts) + 2, tone))
        base += len(pts) + 2
    return build_mesh(name, np.concatenate(V), np.concatenate(Q),
                      attrs={"ltone": ("POINT", np.concatenate(TONE))},
                      mats=mats, mat_index=np.concatenate(MI))


def log_side_material(name, along="X"):
    """Aged, lightly varnished pine with checking cracks and knots, grain along the log."""
    m, nt, out = new_material(name)
    L = nt.links.new
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    stretch = (0.35, 9, 9) if along == "X" else (9, 0.35, 9)
    mp.inputs["Scale"].default_value = stretch
    grain = node(nt, "ShaderNodeTexNoise", Scale=3.0, Detail=12.0, Roughness=0.65, Distortion=1.2)
    # checking: a few long, thin splits running along the grain
    mp2 = nt.nodes.new("ShaderNodeMapping")
    mp2.inputs["Scale"].default_value = (0.22, 20, 20) if along == "X" else (20, 0.22, 20)
    split = node(nt, "ShaderNodeTexNoise", Scale=1.0, Detail=2.0)
    off = node(nt, "ShaderNodeMath")
    off.operation = "SUBTRACT"
    off.inputs[1].default_value = 0.5
    dist = node(nt, "ShaderNodeMath")
    dist.operation = "ABSOLUTE"
    line = node(nt, "ShaderNodeMapRange")
    line.inputs["From Min"].default_value = 0.0
    line.inputs["From Max"].default_value = 0.01
    line.inputs["To Min"].default_value = 1.0
    line.inputs["To Max"].default_value = 0.0
    sparse = node(nt, "ShaderNodeTexNoise", Scale=1.3, Detail=1.0)
    sparse_m = node(nt, "ShaderNodeMapRange")
    sparse_m.inputs["From Min"].default_value = 0.56
    sparse_m.inputs["From Max"].default_value = 0.64
    crack_line = node(nt, "ShaderNodeMath")
    crack_line.operation = "MULTIPLY"
    L(mp2.outputs[0], split.inputs["Vector"])
    L(split.outputs["Fac"], off.inputs[0])
    L(off.outputs[0], dist.inputs[0])
    L(dist.outputs[0], line.inputs["Value"])
    L(sparse.outputs["Fac"], sparse_m.inputs["Value"])
    L(line.outputs[0], crack_line.inputs[0])
    L(sparse_m.outputs[0], crack_line.inputs[1])
    wood = node(nt, "ShaderNodeMath")                      # 1 on sound wood, 0 in a split
    wood.operation = "SUBTRACT"
    wood.inputs[0].default_value = 1.0
    L(crack_line.outputs[0], wood.inputs[1])
    knots = nt.nodes.new("ShaderNodeTexVoronoi")
    knots.inputs["Scale"].default_value = 1.1
    knot_mask = node(nt, "ShaderNodeMapRange")
    knot_mask.inputs["From Min"].default_value = 0.045
    knot_mask.inputs["From Max"].default_value = 0.02
    tone = attr_node(nt, "ltone")
    tone_ramp = nt.nodes.new("ShaderNodeValToRGB")
    tone_ramp.color_ramp.elements[0].color = (0.20, 0.095, 0.035, 1)
    tone_ramp.color_ramp.elements[1].color = (0.34, 0.18, 0.075, 1)
    grain_mix = mix_rgb(nt, "MULTIPLY", 0.35)
    knot_mix = mix_rgb(nt, "MIX")
    knot_mix.inputs["B"].default_value = (0.05, 0.022, 0.01, 1)
    crack_mix = mix_rgb(nt, "MIX")
    crack_mix.inputs["A"].default_value = (0.02, 0.01, 0.006, 1)
    height = node(nt, "ShaderNodeMath")
    height.operation = "MULTIPLY_ADD"
    height.inputs[1].default_value = 0.25
    bump = node(nt, "ShaderNodeBump", Strength=0.6, Distance=0.015)
    rough = node(nt, "ShaderNodeMapRange")
    rough.inputs["To Min"].default_value = 0.42
    rough.inputs["To Max"].default_value = 0.75
    b = principled(nt, (0.3, 0.15, 0.06), rough=0.55)
    b.inputs["Coat Weight"].default_value = 0.12
    L(tc.outputs["Object"], mp.inputs["Vector"])
    L(tc.outputs["Object"], mp2.inputs["Vector"])
    L(tc.outputs["Object"], sparse.inputs["Vector"])
    L(tc.outputs["Object"], knots.inputs["Vector"])
    L(mp.outputs[0], grain.inputs["Vector"])
    L(knots.outputs["Distance"], knot_mask.inputs["Value"])
    L(tone.outputs["Fac"], tone_ramp.inputs["Fac"])
    L(tone_ramp.outputs["Color"], grain_mix.inputs["A"])
    L(grain.outputs["Color"], grain_mix.inputs["B"])
    L(knot_mask.outputs[0], knot_mix.inputs["Factor"])
    L(grain_mix.outputs["Result"], knot_mix.inputs["A"])
    L(wood.outputs[0], crack_mix.inputs["Factor"])
    L(knot_mix.outputs["Result"], crack_mix.inputs["B"])
    L(crack_mix.outputs["Result"], b.inputs["Base Color"])
    L(grain.outputs["Fac"], height.inputs[0])
    L(wood.outputs[0], height.inputs[2])
    L(height.outputs[0], bump.inputs["Height"])
    L(bump.outputs["Normal"], b.inputs["Normal"])
    L(grain.outputs["Fac"], rough.inputs["Value"])
    L(rough.outputs[0], b.inputs["Roughness"])
    L(b.outputs[0], out.inputs["Surface"])
    return m


def end_grain_material():
    m, nt, out = new_material("EndGrain")
    L = nt.links.new
    tc = nt.nodes.new("ShaderNodeTexCoord")
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = "RINGS"
    wave.inputs["Scale"].default_value = 7.0
    wave.inputs["Distortion"].default_value = 3.0
    wave.inputs["Detail"].default_value = 6.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.16, 0.08, 0.03, 1)
    ramp.color_ramp.elements[1].color = (0.42, 0.25, 0.12, 1)
    b = principled(nt, (0.3, 0.18, 0.08), rough=0.8)
    L(tc.outputs["Object"], wave.inputs["Vector"])
    L(wave.outputs["Fac"], ramp.inputs["Fac"])
    L(ramp.outputs["Color"], b.inputs["Base Color"])
    L(b.outputs[0], out.inputs["Surface"])
    return m


# ---------------------------------------------------------------- plank floor
def plank_floor(name, rnd, x0, x1, y0, y1, width=(0.13, 0.17), length=(1.1, 2.8), gap=0.0025):
    V, Q, TONE, OFS = [], [], [], []
    y = y0
    k = 0
    while y < y1:
        w = rnd.uniform(*width)
        x = x0 - rnd.uniform(0, 1.5)
        while x < x1:
            L = rnd.uniform(*length)
            xa, xb = max(x, x0), min(x + L, x1)
            if xb - xa > 0.05:
                z1 = rnd.uniform(-0.0006, 0.0006)
                xa2, xb2, ya2, yb2 = xa + gap / 2, xb - gap / 2, y + gap / 2, y + w - gap / 2
                vs = np.array([(xa2, ya2, -0.02), (xb2, ya2, -0.02), (xb2, yb2, -0.02), (xa2, yb2, -0.02),
                               (xa2, ya2, z1), (xb2, ya2, z1), (xb2, yb2, z1), (xa2, yb2, z1)])
                fs = np.array([(4, 5, 6, 7), (0, 3, 2, 1), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])
                V.append(vs)
                Q.append(fs + k * 8)
                TONE.append(np.full(8, rnd.uniform(0, 1)))
                OFS.append(np.tile(rnd.uniform(-50, 50, 3), (8, 1)))
                k += 1
            x += L
        y += w
    return build_mesh(name, np.concatenate(V), np.concatenate(Q),
                      attrs={"ptone": ("POINT", np.concatenate(TONE)), "pofs": ("POINT", np.concatenate(OFS))},
                      mats=[plank_material()], smooth=False)


def plank_material():
    m, nt, out = new_material("Planks")
    L = nt.links.new
    tc = nt.nodes.new("ShaderNodeTexCoord")
    ofs = attr_node(nt, "pofs")
    add = node(nt, "ShaderNodeVectorMath")
    add.operation = "ADD"
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (0.5, 22, 22)
    grain = node(nt, "ShaderNodeTexNoise", Scale=2.0, Detail=12.0, Roughness=0.6, Distortion=1.5)
    tone = attr_node(nt, "ptone")
    tone_ramp = nt.nodes.new("ShaderNodeValToRGB")
    tone_ramp.color_ramp.elements[0].color = (0.11, 0.05, 0.02, 1)
    tone_ramp.color_ramp.elements[1].color = (0.24, 0.12, 0.05, 1)
    gm = mix_rgb(nt, "MULTIPLY", 0.6)
    scuff = node(nt, "ShaderNodeTexNoise", Scale=4.0, Detail=4.0)
    rough = node(nt, "ShaderNodeMapRange")
    rough.inputs["To Min"].default_value = 0.28
    rough.inputs["To Max"].default_value = 0.62
    bump = node(nt, "ShaderNodeBump", Strength=0.15, Distance=0.004)
    b = principled(nt, (0.2, 0.1, 0.05), rough=0.3)
    b.inputs["Coat Weight"].default_value = 0.25
    b.inputs["Coat Roughness"].default_value = 0.3
    L(tc.outputs["Object"], add.inputs[0])
    L(ofs.outputs["Vector"], add.inputs[1])
    L(add.outputs[0], mp.inputs["Vector"])
    L(mp.outputs[0], grain.inputs["Vector"])
    L(tone.outputs["Fac"], tone_ramp.inputs["Fac"])
    L(tone_ramp.outputs["Color"], gm.inputs["A"])
    L(grain.outputs["Color"], gm.inputs["B"])
    L(gm.outputs["Result"], b.inputs["Base Color"])
    L(tc.outputs["Object"], scuff.inputs["Vector"])
    L(scuff.outputs["Fac"], rough.inputs["Value"])
    L(rough.outputs[0], b.inputs["Roughness"])
    L(grain.outputs["Fac"], bump.inputs["Height"])
    L(bump.outputs["Normal"], b.inputs["Normal"])
    L(b.outputs[0], out.inputs["Surface"])
    return m


# ---------------------------------------------------------------- braided oval rug
RUG_COLOURS = np.array([(0.22, 0.012, 0.016), (0.55, 0.47, 0.33), (0.025, 0.07, 0.035),
                        (0.20, 0.09, 0.04), (0.16, 0.012, 0.03), (0.50, 0.42, 0.30)])


def braided_rug(name, center, ax=1.25, ay=0.82, pitch=0.026, tube=0.0135, sides=8):
    """A braided rag rug: one braid spiralling out from an elongated centre."""
    a0, b0 = ax - ay + 0.04, 0.04
    turns = (ay - b0) / pitch
    n = int(turns * 260)
    phi = np.linspace(0, 2 * np.pi * turns, n)
    grow = pitch * phi / (2 * np.pi)
    path = np.stack([center[0] + (a0 + grow) * np.cos(phi), center[1] + (b0 + grow) * np.sin(phi),
                     np.full(n, tube * 0.85)], 1)
    tang = np.gradient(path, axis=0)
    tang /= np.linalg.norm(tang, axis=1, keepdims=True)
    up = np.array([0.0, 0, 1])
    side = np.cross(tang, up)
    side /= np.linalg.norm(side, axis=1, keepdims=True)
    ang = np.linspace(0, 2 * np.pi, sides, endpoint=False)
    ring = np.cos(ang)[None, :, None] * side[:, None, :] * 1.0 + np.sin(ang)[None, :, None] * up[None, None, :] * 0.75
    pts = (path[:, None, :] + tube * ring).reshape(-1, 3)
    k = np.arange(sides)
    q = np.concatenate([np.stack([i * sides + k, i * sides + (k + 1) % sides,
                                  (i + 1) * sides + (k + 1) % sides, (i + 1) * sides + k], 1) for i in range(n - 1)])
    ring_index = np.floor(phi / (2 * np.pi)).astype(int)
    band = (ring_index // 2) % len(RUG_COLOURS)
    col = RUG_COLOURS[band]
    col = np.concatenate([col, np.ones((n, 1))], 1)
    seglen = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))])
    along = np.repeat(seglen, sides)
    around = np.tile(ang, n)
    return build_mesh(name, pts, q, attrs={"rcol": ("POINT", np.repeat(col, sides, 0)),
                                           "along": ("POINT", along), "around": ("POINT", around)},
                      mats=[rug_material()])


def rug_material():
    m, nt, out = new_material("BraidedRug")
    L = nt.links.new
    col = attr_node(nt, "rcol")
    along = attr_node(nt, "along")
    around = attr_node(nt, "around")
    # braid: strands crossing diagonally along the rope
    s = node(nt, "ShaderNodeMath")
    s.operation = "MULTIPLY_ADD"
    s.inputs[1].default_value = 110.0
    s2 = node(nt, "ShaderNodeMath")
    s2.operation = "SINE"
    s3 = node(nt, "ShaderNodeMath")
    s3.operation = "ABSOLUTE"
    tc = nt.nodes.new("ShaderNodeTexCoord")
    fuzz = node(nt, "ShaderNodeTexNoise", Scale=400.0, Detail=4.0)
    fm = mix_rgb(nt, "MULTIPLY", 0.25)
    shade = mix_rgb(nt, "MULTIPLY", 0.45)
    bump = node(nt, "ShaderNodeBump", Strength=0.7, Distance=0.006)
    b = principled(nt, (0.3, 0.1, 0.05), rough=0.95)
    b.inputs["Sheen Weight"].default_value = 0.9
    b.inputs["Sheen Roughness"].default_value = 0.4
    L(along.outputs["Fac"], s.inputs[0])
    L(around.outputs["Fac"], s.inputs[2])
    L(s.outputs[0], s2.inputs[0])
    L(s2.outputs[0], s3.inputs[0])
    L(col.outputs["Color"], shade.inputs["A"])
    L(s3.outputs[0], shade.inputs["B"])
    L(shade.outputs["Result"], fm.inputs["A"])
    L(tc.outputs["Object"], fuzz.inputs["Vector"])
    L(fuzz.outputs["Color"], fm.inputs["B"])
    L(fm.outputs["Result"], b.inputs["Base Color"])
    L(s3.outputs[0], bump.inputs["Height"])
    L(bump.outputs["Normal"], b.inputs["Normal"])
    L(b.outputs[0], out.inputs["Surface"])
    return m


# ---------------------------------------------------------------- knitted stocking
def stocking(name, top, right, mat, cuff_mat, rnd):
    """A soft knitted stocking hanging from `top`; the foot points along `right`."""
    right = np.asarray(right, float)
    right /= np.linalg.norm(right)
    up = np.array([0.0, 0, 1])
    depth = np.cross(up, right)
    # centre line: down the leg, round the heel, out to the toe
    ctrl = np.array([(0, 0.0), (0, -0.10), (0.005, -0.22), (0.02, -0.31), (0.07, -0.37), (0.14, -0.385), (0.19, -0.37)])
    t = np.linspace(0, 1, 44)
    xs = np.interp(t, np.linspace(0, 1, len(ctrl)), ctrl[:, 0])
    zs = np.interp(t, np.linspace(0, 1, len(ctrl)), ctrl[:, 1])
    centre = np.asarray(top) + np.outer(xs, right) + np.outer(zs, up)
    tang = np.gradient(centre, axis=0)
    tang /= np.linalg.norm(tang, axis=1, keepdims=True)
    nrm = np.cross(depth, tang)
    sides = 28
    ang = np.linspace(0, 2 * np.pi, sides, endpoint=False)
    half_w = np.interp(t, [0, 0.55, 0.85, 1], [0.068, 0.062, 0.058, 0.0])
    half_w = np.where(t > 0.92, half_w * np.sqrt(np.clip((1 - t) / 0.08, 0, 1)), half_w)
    half_d = half_w * 0.42 + 0.004
    ring = (np.cos(ang)[None, :, None] * nrm[:, None, :] * half_w[:, None, None]
            + np.sin(ang)[None, :, None] * depth[None, None, :] * half_d[:, None, None])
    pts = (centre[:, None, :] + ring).reshape(-1, 3)
    k = np.arange(sides)
    q = np.concatenate([np.stack([i * sides + k, i * sides + (k + 1) % sides,
                                  (i + 1) * sides + (k + 1) % sides, (i + 1) * sides + k], 1) for i in range(len(t) - 1)])
    ob = build_mesh(name, pts, q, mats=[mat])
    sub = ob.modifiers.new("smooth", "SUBSURF")
    sub.levels = sub.render_levels = 1
    # fluffy cuff
    cv = []
    for zz in np.linspace(-0.085, 0.005, 6):
        for a in ang:
            bulge = 1.12 + 0.05 * math.sin(math.pi * (zz + 0.085) / 0.09)
            cv.append(np.asarray(top) + up * zz + right * (math.cos(a) * 0.072 * bulge)
                      + depth * (math.sin(a) * 0.036 * bulge))
    cq = np.concatenate([np.stack([i * sides + k, i * sides + (k + 1) % sides,
                                   (i + 1) * sides + (k + 1) % sides, (i + 1) * sides + k], 1) for i in range(5)])
    cuff = build_mesh(name + "Cuff", np.array(cv), cq, mats=[cuff_mat])
    sol = cuff.modifiers.new("thick", "SOLIDIFY")
    sol.thickness = 0.012
    sub = cuff.modifiers.new("smooth", "SUBSURF")
    sub.levels = sub.render_levels = 1
    return ob


def knit_material(name, color):
    """Knitted wool: rows of little V stitches, soft sheen."""
    m, nt, out = new_material(name)
    L = nt.links.new
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    # V stitches: |sin(x*a)| shifted rows in z
    sx = node(nt, "ShaderNodeMath")
    sx.operation = "MULTIPLY"
    sx.inputs[1].default_value = 260.0
    sxs = node(nt, "ShaderNodeMath")
    sxs.operation = "SINE"
    absx = node(nt, "ShaderNodeMath")
    absx.operation = "ABSOLUTE"
    rowz = node(nt, "ShaderNodeMath")
    rowz.operation = "MULTIPLY_ADD"
    rowz.inputs[1].default_value = 210.0
    rows = node(nt, "ShaderNodeMath")
    rows.operation = "SINE"
    st = node(nt, "ShaderNodeMath")
    st.operation = "MULTIPLY"
    fuzz = node(nt, "ShaderNodeTexNoise", Scale=600.0, Detail=3.0)
    cm = mix_rgb(nt, "MULTIPLY", 0.35)
    cm.inputs["A"].default_value = (*color, 1)
    bump = node(nt, "ShaderNodeBump", Strength=0.8, Distance=0.004)
    b = principled(nt, color, rough=0.95)
    b.inputs["Sheen Weight"].default_value = 1.0
    b.inputs["Sheen Roughness"].default_value = 0.35
    L(tc.outputs["Object"], sep.inputs[0])
    L(tc.outputs["Object"], fuzz.inputs["Vector"])
    L(sep.outputs["X"], sx.inputs[0])
    L(sx.outputs[0], sxs.inputs[0])
    L(sxs.outputs[0], absx.inputs[0])
    L(sep.outputs["Z"], rowz.inputs[0])
    L(absx.outputs[0], rowz.inputs[2])
    L(rowz.outputs[0], rows.inputs[0])
    L(rows.outputs[0], st.inputs[0])
    L(absx.outputs[0], st.inputs[1])
    L(fuzz.outputs["Color"], cm.inputs["B"])
    L(cm.outputs["Result"], b.inputs["Base Color"])
    L(st.outputs[0], bump.inputs["Height"])
    L(bump.outputs["Normal"], b.inputs["Normal"])
    L(b.outputs[0], out.inputs["Surface"])
    return m


# ---------------------------------------------------------------- burning logs
def charred_log_material(name="CharredLog", glow=2.2):
    """Charred wood broken into alligator cracks that glow orange, most on the underside."""
    m, nt, out = new_material(name)
    L = nt.links.new
    tc = nt.nodes.new("ShaderNodeTexCoord")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    cracks = nt.nodes.new("ShaderNodeTexVoronoi")
    cracks.feature = "DISTANCE_TO_EDGE"
    cracks.inputs["Scale"].default_value = 34.0
    crack = node(nt, "ShaderNodeMapRange")
    crack.inputs["From Min"].default_value = 0.0
    crack.inputs["From Max"].default_value = 0.07
    crack.inputs["To Min"].default_value = 1.0
    crack.inputs["To Max"].default_value = 0.0
    patch = node(nt, "ShaderNodeTexNoise", Scale=5.0, Detail=4.0)
    hot = node(nt, "ShaderNodeMapRange")
    hot.inputs["From Min"].default_value = 0.42
    hot.inputs["From Max"].default_value = 0.62
    sepn = nt.nodes.new("ShaderNodeSeparateXYZ")
    under = node(nt, "ShaderNodeMapRange")                  # facing down glows more
    under.inputs["From Min"].default_value = 0.6
    under.inputs["From Max"].default_value = -0.6
    under.inputs["To Min"].default_value = 0.25
    under.inputs["To Max"].default_value = 1.0
    g1 = node(nt, "ShaderNodeMath")
    g1.operation = "MULTIPLY"
    g2 = node(nt, "ShaderNodeMath")
    g2.operation = "MULTIPLY"
    g3 = node(nt, "ShaderNodeMath")
    g3.operation = "MULTIPLY"
    g3.inputs[1].default_value = glow
    bump = node(nt, "ShaderNodeBump", Strength=0.9, Distance=0.008)
    b = principled(nt, (0.012, 0.010, 0.009), rough=0.9)
    b.inputs["Emission Color"].default_value = (1.0, 0.30, 0.045, 1)
    L(tc.outputs["Object"], cracks.inputs["Vector"])
    L(tc.outputs["Object"], patch.inputs["Vector"])
    L(cracks.outputs["Distance"], crack.inputs["Value"])
    L(patch.outputs["Fac"], hot.inputs["Value"])
    L(geo.outputs["Normal"], sepn.inputs[0])
    L(sepn.outputs["Z"], under.inputs["Value"])
    L(crack.outputs[0], g1.inputs[0]); L(hot.outputs[0], g1.inputs[1])
    L(g1.outputs[0], g2.inputs[0]); L(under.outputs[0], g2.inputs[1])
    L(g2.outputs[0], g3.inputs[0])
    L(g3.outputs[0], b.inputs["Emission Strength"])
    L(crack.outputs[0], bump.inputs["Height"])
    L(bump.outputs["Normal"], b.inputs["Normal"])
    L(b.outputs[0], out.inputs["Surface"])
    return m
