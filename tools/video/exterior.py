"""The LeMSIC cabin in its snowy spruce forest at night, for the promo video's first and last shots.

The whole cabin (the website's door scene from tools/blender/cabin_door.py, plus side and back walls,
a gable roof and a stone chimney) stands in a clearing of a spruce forest. The camera flies in from
above the trees, down a gap between them, across the clearing to the front door, and ends on the
camera of the website's door picture (site/assets/door/door.jpg), so the film can cut to the site.

    python tools/video/exterior.py [--preview] [--still=0,120,300] [--frames=0-335] [--samples=N]

Writes build/video/exterior/####.png (one per frame, 24 a second) and exterior.json (where the
chimney top is in each frame, so the smoke can be drawn over it).
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

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools", "blender"))
import cabin_door as D  # noqa: E402
import cabin_props as P  # noqa: E402
import lemsic_tree as T  # noqa: E402
from lemsic_tree import box, link, mesh_object, new_material, principled, simple_material  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
PREVIEW = "--preview" in ARGS
OUT = os.path.join(ROOT, "build", "video", "exterior-preview" if "--preview" in ARGS else "exterior")
FPS = 24
SECONDS = 14.0
NFRAMES = int(SECONDS * FPS)
RES = (480, 270) if PREVIEW else (1280, 720)
SAMPLES = 16 if PREVIEW else 28
for a in ARGS:
    if a.startswith("--samples="):
        SAMPLES = int(a.split("=")[1])
rng = np.random.default_rng(2412)

SILL = D.SILL
WALL_X = 4.45                        # the side walls' log centres
BACK_Y = 6.9
PITCH = math.radians(26)
RIDGE_Y = -1.0 + 5.0 * math.cos(PITCH)
RIDGE_Z = 3.3 + 5.0 * math.sin(PITCH)
CHIMNEY_TOP = (-5.06, 3.5, 6.42)
CABIN_C = np.array([0.0, 3.0])
FOG = (0.018, 0.026, 0.05)

# the flight: (time s, camera position, where it looks, lens mm)
PATH = [
    (0.0, (9.0, -128.0, 27.0), (0.0, 0.0, 1.0), 26),
    (3.5, (5.0, -92.0, 15.5), (0.0, 0.0, 2.0), 26),
    (7.0, (1.5, -58.0, 6.2), (0.0, 0.0, 2.6), 27),
    (10.0, (0.4, -30.0, 3.4), (0.0, 0.0, 2.4), 28),
    (12.5, (0.05, -13.0, 2.0), (0.0, 0.0, 2.1), 29.5),
    (14.0, tuple(D.CAMERA), tuple(D.TARGET), 30),
]


# ---------------------------------------------------------------- the camera path
def hermite(t):
    """Position, target and lens at time t: a smooth curve through PATH that comes to rest at the door."""
    ts = np.array([p[0] for p in PATH])
    P_ = np.array([p[1] for p in PATH], float)
    G_ = np.array([p[2] for p in PATH], float)
    L_ = np.array([p[3] for p in PATH], float)
    def curve(Y):
        V = np.zeros_like(Y)
        for i in range(len(ts)):
            if i == 0:
                V[i] = (Y[1] - Y[0]) / (ts[1] - ts[0])
            elif i == len(ts) - 1:
                V[i] = 0                                   # it settles on the door
            else:
                V[i] = (Y[i + 1] - Y[i - 1]) / (ts[i + 1] - ts[i - 1])
        k = min(max(np.searchsorted(ts, t) - 1, 0), len(ts) - 2)
        h = ts[k + 1] - ts[k]
        s = (t - ts[k]) / h
        h00, h10, h01, h11 = 2 * s**3 - 3 * s**2 + 1, s**3 - 2 * s**2 + s, -2 * s**3 + 3 * s**2, s**3 - s**2
        return h00 * Y[k] + h10 * h * V[k] + h01 * Y[k + 1] + h11 * h * V[k + 1]
    return curve(P_), curve(G_), float(curve(L_[:, None])[0])


def path_xy(samples=400):
    return np.array([hermite(t)[0] for t in np.linspace(0, SECONDS, samples)])


# ---------------------------------------------------------------- materials
def with_fog(m, nt, out, surface, density=1 / 95.0):
    """Mix a surface towards the night haze with distance from the camera."""
    cam = nt.nodes.new("ShaderNodeCameraData")
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = -density
    nt.links.new(cam.outputs["View Distance"], mul.inputs[0])
    ex = nt.nodes.new("ShaderNodeMath"); ex.operation = "EXPONENT"; nt.links.new(mul.outputs[0], ex.inputs[0])
    inv = nt.nodes.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1.0
    nt.links.new(ex.outputs[0], inv.inputs[1])
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (*FOG, 1); em.inputs["Strength"].default_value = 1.0
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(inv.outputs[0], mix.inputs[0]); nt.links.new(surface, mix.inputs[1]); nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return m


def snow_fog_material(name="SnowFar", tint=(0.8, 0.85, 0.92)):
    m, nt, out = new_material(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    n = nt.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = 3.0; n.inputs["Detail"].default_value = 6
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.12
    b = principled(nt, tint, rough=0.6)
    nt.links.new(tc.outputs["Object"], n.inputs["Vector"]); nt.links.new(n.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return with_fog(m, nt, out, b.outputs[0])


def world_with_stars(scene):
    world = scene.world
    nt = world.node_tree
    bg = nt.nodes["Background"]
    sky = bg.inputs["Color"].links[0].from_socket
    tc = nt.nodes.new("ShaderNodeTexCoord")
    vor = nt.nodes.new("ShaderNodeTexVoronoi"); vor.inputs["Scale"].default_value = 260.0
    nt.links.new(tc.outputs["Generated"], vor.inputs["Vector"])
    star = nt.nodes.new("ShaderNodeMapRange")
    star.inputs["From Min"].default_value = 0.0; star.inputs["From Max"].default_value = 0.07
    star.inputs["To Min"].default_value = 1.6; star.inputs["To Max"].default_value = 0.0
    nt.links.new(vor.outputs["Distance"], star.inputs["Value"])
    pick = nt.nodes.new("ShaderNodeMath"); pick.operation = "GREATER_THAN"; pick.inputs[1].default_value = 0.82
    nt.links.new(vor.outputs["Color"], pick.inputs[0])
    on = nt.nodes.new("ShaderNodeMath"); on.operation = "MULTIPLY"
    nt.links.new(star.outputs[0], on.inputs[0]); nt.links.new(pick.outputs[0], on.inputs[1])
    add = nt.nodes.new("ShaderNodeMix"); add.data_type = "RGBA"; add.blend_type = "ADD"
    add.inputs[0].default_value = 1.0
    nt.links.new(sky, add.inputs[6])
    nt.links.new(on.outputs[0], add.inputs[7])
    nt.links.new(add.outputs[2], bg.inputs["Color"])


# ---------------------------------------------------------------- the rest of the cabin
def walls():
    side = bpy.data.materials["FacadeLogs"]
    endg = bpy.data.materials["EndGrain"]
    r, pitch = 0.15, 0.324
    win_r = [(1.6, 2.6), (4.3, 5.3)]                   # the right wall's windows (y)
    win_l = [(5.2, 6.1)]
    logs = []
    z = SILL + r - 0.02 + pitch / 2                    # interlocked with the front logs at the corners
    while z < 3.3:
        for sx, wins in ((1, win_r), (-1, win_l)):
            spans = [(-0.3, BACK_Y + 0.3)]
            if D.WIN_Z[0] - 0.1 < z < D.WIN_Z[1] + 0.1:
                for a, b in wins:
                    spans = [(s0, s1) for p0, p1 in spans for s0, s1 in ((p0, min(p1, a - 0.07)), (max(p0, b + 0.07), p1)) if s1 - s0 > 0.05]
            for a, b in spans:
                rr = r * rng.uniform(0.92, 1.06)
                logs.append(((sx * WALL_X, a, z), (sx * WALL_X, b, z), rr))
        z += pitch
    z = SILL + r - 0.02
    while z < 3.3:                                     # the back wall
        logs.append(((-4.6, BACK_Y, z), (4.6, BACK_Y, z), r * rng.uniform(0.92, 1.06)))
        z += pitch
    z = 3.3 + pitch / 2                                # the gables, shortening up to the ridge
    while z < RIDGE_Z - 0.25:
        run = (z - 3.3) / math.tan(PITCH)
        for sx in (1, -1):
            logs.append(((sx * WALL_X, -0.7 + run, z), (sx * WALL_X, BACK_Y + 0.7 - run, z), r * rng.uniform(0.92, 1.06)))
        z += pitch
    P.logs_mesh("SideWalls", logs, rng, [side, endg])
    # dark chinking behind the logs, so the gaps between them are filled
    chink = bpy.data.materials["ChinkingOut"]
    for sx in (1, -1):
        bpy.ops.mesh.primitive_plane_add(size=1, location=(sx * (WALL_X - 0.05), BACK_Y / 2, 1.8), rotation=(0, math.radians(90), 0))
        pl = bpy.context.active_object
        pl.scale = (3.0, BACK_Y + 0.4, 1)
        pl.data.materials.append(chink)
        gx = sx * (WALL_X - 0.05)                     # and the gable triangle, under the roof
        mesh_object("GableChink", [(gx, -0.3, 3.28), (gx, BACK_Y + 0.3, 3.28), (gx, RIDGE_Y, RIDGE_Z - 0.12)],
                    np.array([(0, 1, 2, 2)]), mat=chink)
    for sx, wins in ((1, win_r), (-1, win_l)):
        for a, b in wins:
            side_window(sx, a, b)


def side_window(sx, a, b):
    trim = bpy.data.materials["WinTrim"]
    glass = bpy.data.materials["WinGlass"]
    warm = bpy.data.materials["RoomGlow"]
    curtain = bpy.data.materials["Curtain"]
    snow = D.snow_material()
    z0, z1 = D.WIN_Z
    cy, cz, w, h = (a + b) / 2, (z0 + z1) / 2, b - a, z1 - z0
    x = sx * (WALL_X + 0.17)
    for (sy, sz, y, z) in ((w + 0.2, 0.1, cy, z1 + 0.05), (w + 0.3, 0.08, cy, z0 - 0.04), (0.1, h, a - 0.05, cz), (0.1, h, b + 0.05, cz)):
        box("WinFrame", (0.18, sy, sz), (x, y, z), trim)
    box("WinBar", (0.05, 0.04, h), (x - sx * 0.05, cy, cz), trim)
    box("WinBar", (0.05, w, 0.04), (x - sx * 0.05, cy, cz), trim)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(x - sx * 0.08, cy, cz), rotation=(0, math.radians(90), 0))
    g = bpy.context.active_object; g.scale = (h, w, 1); g.data.materials.append(glass)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(sx * (WALL_X - 0.5), cy, cz), rotation=(0, math.radians(90), 0))
    gl = bpy.context.active_object; gl.scale = (h + 0.6, w + 0.6, 1); gl.data.materials.append(warm)
    for side in (-1, 1):
        box("Curtain", (0.02, w * 0.22, h + 0.1), (sx * (WALL_X - 0.15), cy + side * (w / 2 - w * 0.09), cz), curtain)
    s = box("SillSnow", (0.2, w + 0.3, 0.06), (x + sx * 0.12, cy, z0), snow)
    s.modifiers["bevel"].width = 0.025
    spill = bpy.data.lights.new("WindowSpill", "AREA")       # the window's warm light on the snow outside
    spill.energy = 35
    spill.color = (1.0, 0.6, 0.3)
    spill.size = w
    lo = link(bpy.data.objects.new("WindowSpill", spill))
    lo.location = (x + sx * 0.2, cy, cz)
    lo.rotation_euler = Vector((sx, 0, -0.6)).to_track_quat("-Z", "Y").to_euler()


def front_spill():
    for a, b in D.WINDOWS:
        spill = bpy.data.lights.new("WindowSpill", "AREA")
        spill.energy = 35
        spill.color = (1.0, 0.6, 0.3)
        spill.size = b - a
        lo = link(bpy.data.objects.new("WindowSpill", spill))
        lo.location = ((a + b) / 2, -0.25, sum(D.WIN_Z) / 2)
        lo.rotation_euler = Vector((0, -1, -0.6)).to_track_quat("-Z", "Y").to_euler()


def back_roof():
    wood = bpy.data.materials["Eave"]
    snow = D.snow_material()
    up = np.array([0, -math.cos(PITCH), math.sin(PITCH)])
    front = np.array([0, BACK_Y + 1.0 + 0.1, 3.3])
    L = 5.0
    c = front + up * (L / 2)
    e = box("RoofBack", (9.6, L, 0.12), tuple(c + np.array([0, 0, 0.06])), wood)
    e.rotation_euler = (-PITCH, 0, 0)
    s = box("RoofSnowBack", (9.9, L + 0.15, 0.3), tuple(c + np.array([0, 0.05, 0.26])), snow)
    s.rotation_euler = (-PITCH, 0, 0)
    s.modifiers["bevel"].width = 0.12
    s.modifiers["bevel"].segments = 6
    sub = s.modifiers.new("smooth", "SUBSURF"); sub.subdivision_type = "SIMPLE"; sub.levels = sub.render_levels = 5
    dsp = s.modifiers.new("lumps", "DISPLACE"); dsp.texture = bpy.data.textures["SnowLumps"]; dsp.strength = 0.09
    dsp.texture_coords = "GLOBAL"
    bpy.ops.mesh.primitive_cylinder_add(radius=0.32, depth=9.9, location=(0, RIDGE_Y + 0.05, RIDGE_Z + 0.32), rotation=(0, math.radians(90), 0))
    cap = bpy.context.active_object
    cap.scale = (0.55, 1.0, 1.0)
    cap.data.materials.append(snow)


def chimney():
    stone = bpy.data.materials["Fieldstone"]
    x0, x1, y0, y1 = -5.5, -4.62, 2.95, 4.05
    stones = []
    for (orig, u, n, w) in (((x0, y0, 0.0), (0, 1, 0), (-1, 0, 0), y1 - y0), ((x0, y0, 0.0), (1, 0, 0), (0, -1, 0), x1 - x0),
                            ((x1, y1, 0.0), (-1, 0, 0), (0, 1, 0), x1 - x0)):
        stones += P.lay_stones(rng, orig, u, (0, 0, 1), n, w, CHIMNEY_TOP[2] - 0.1, course=(0.14, 0.24), length=(0.22, 0.44))
    P.stone_mesh("Chimney", stones, rng, stone)
    box("ChimneyCore", (x1 - x0 - 0.06, y1 - y0 - 0.06, CHIMNEY_TOP[2] - 0.05), ((x0 + x1) / 2, (y0 + y1) / 2, (CHIMNEY_TOP[2] - 0.05) / 2),
        simple_material("ChimneyCore", (0.08, 0.075, 0.07), rough=0.9))
    box("ChimneyCap", (x1 - x0 + 0.16, y1 - y0 + 0.16, 0.1), ((x0 + x1) / 2, (y0 + y1) / 2, CHIMNEY_TOP[2]),
        simple_material("CapStone", (0.12, 0.115, 0.11), rough=0.8))
    box("Flue", (0.4, 0.4, 0.05), ((x0 + x1) / 2, (y0 + y1) / 2, CHIMNEY_TOP[2] + 0.04), simple_material("Soot", (0.01, 0.01, 0.01), rough=1))
    sn = box("CapSnow", (x1 - x0 + 0.2, 0.18, 0.08), ((x0 + x1) / 2, y0 - 0.0, CHIMNEY_TOP[2] + 0.07), D.snow_material())
    sn.modifiers["bevel"].width = 0.03


# ---------------------------------------------------------------- ground and forest
def height(x, y):
    """The land: flat snow in the clearing, rolling further out, rising into hills behind."""
    d = np.hypot(x - CABIN_C[0], (y - CABIN_C[1]) * 0.8)
    out = np.clip((d - 24) / 45, 0, 1)
    out = out * out * (3 - 2 * out)
    hills = (2.2 * np.sin(x * 0.031 + 1.3) * np.sin(y * 0.027 + 0.4) + 1.4 * np.sin(x * 0.07 + y * 0.05 + 2.0)
             + 0.8 * np.sin(x * 0.13 - y * 0.11))
    rise = 0.09 * np.clip(y - 50, 0, None) + 0.04 * np.clip(np.abs(x) - 80, 0, None)
    return SILL - 0.16 + out * (hills + rise) + 0.03 * np.sin(x * 1.3) * np.sin(y * 1.1)


def ground(snow_far):
    # the wide land, coarse, and the clearing in fine detail (drifts against the walls, a path to the door)
    xs = np.linspace(-300, 300, 241)
    ys = np.linspace(-300, 300, 241)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    Z = height(X, Y) - 0.04 * ((np.abs(X) < 17) & (Y > -15) & (Y < 23))
    V = np.stack([X, Y, Z], -1).reshape(-1, 3)
    nx, ny = len(xs), len(ys)
    q = [(i * ny + j, (i + 1) * ny + j, (i + 1) * ny + j + 1, i * ny + j + 1) for i in range(nx - 1) for j in range(ny - 1)]
    mesh_object("Land", V, np.array(q), mat=snow_far, smooth=True)
    xs = np.linspace(-17, 17, 341)
    ys = np.linspace(-15, 23, 381)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    Z = height(X, Y)
    for _ in range(10):
        f = rng.normal(0, 0.6, 2)
        Z += np.sin(X * f[0] + Y * f[1] + rng.uniform(0, 6)) * rng.uniform(0.02, 0.06)
    near = lambda d, w: np.exp(-(d ** 2) / w)
    Z += 0.14 * near(Y - 0.15, 0.3) * (np.abs(X) > 0.9) * (np.abs(X) < 4.7)          # drifts against the walls
    Z += 0.14 * near(np.abs(X) - (WALL_X + 0.2), 0.3) * (Y > -0.3) * (Y < BACK_Y + 0.3)
    Z -= 0.12 * near(X, 0.35) * (Y < 0)                                                 # the trodden path
    inside = (np.abs(X) < WALL_X - 0.1) & (Y > 0.3) & (Y < BACK_Y - 0.1)
    Z[inside] -= 1.0
    edge = np.clip(np.minimum.reduce([X + 17, 17 - X, Y + 15, 23 - Y]) / 1.5, 0, 1)    # (meet the wide land at the edge)
    Z = height(X, Y) * (1 - edge) + Z * edge
    V = np.stack([X, Y, Z], -1).reshape(-1, 3)
    nx, ny = len(xs), len(ys)
    q = [(i * ny + j, (i + 1) * ny + j, (i + 1) * ny + j + 1, i * ny + j + 1) for i in range(nx - 1) for j in range(ny - 1)]
    mesh_object("Snow", V, np.array(q), mat=D.snow_material(), smooth=True)
    stones = [(np.array([0.0, -0.32, SILL - 0.12]), np.array([0.62, 0.28, 0.12]), np.eye(3), np.zeros(3), 3)]
    P.stone_mesh("Step", stones, rng, bpy.data.materials["Fieldstone"])


def tree_material():
    """Spruce needles, with snow settled on whatever faces up (clumped, not painted on)."""
    m, nt, out = new_material("SpruceSnowy")
    L = nt.links.new
    tc = nt.nodes.new("ShaderNodeTexCoord")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); L(geo.outputs["True Normal"], sep.inputs[0])
    clump = nt.nodes.new("ShaderNodeTexNoise"); clump.inputs["Scale"].default_value = 3.5; clump.inputs["Detail"].default_value = 6
    L(tc.outputs["Object"], clump.inputs["Vector"])
    off = nt.nodes.new("ShaderNodeMath"); off.operation = "MULTIPLY_ADD"
    off.inputs[1].default_value = 0.9; off.inputs[2].default_value = -0.45
    L(clump.outputs["Fac"], off.inputs[0])
    add = nt.nodes.new("ShaderNodeMath"); add.operation = "ADD"; L(sep.outputs["Z"], add.inputs[0]); L(off.outputs[0], add.inputs[1])
    fac = nt.nodes.new("ShaderNodeMapRange")
    fac.inputs["From Min"].default_value = 0.42; fac.inputs["From Max"].default_value = 0.72
    L(add.outputs[0], fac.inputs["Value"])
    nee = nt.nodes.new("ShaderNodeTexNoise"); nee.inputs["Scale"].default_value = 26.0; nee.inputs["Detail"].default_value = 8
    nee.inputs["Roughness"].default_value = 0.75
    L(tc.outputs["Object"], nee.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.003, 0.01, 0.006, 1)
    ramp.color_ramp.elements[1].color = (0.02, 0.045, 0.024, 1)
    L(nee.outputs["Fac"], ramp.inputs["Fac"])
    fine = nt.nodes.new("ShaderNodeTexNoise"); fine.inputs["Scale"].default_value = 140.0; fine.inputs["Detail"].default_value = 3
    L(tc.outputs["Object"], fine.inputs["Vector"])
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.7; L(fine.outputs["Fac"], bump.inputs["Height"])
    pine = principled(nt, (0.01, 0.03, 0.015), rough=0.8)
    L(ramp.outputs["Color"], pine.inputs["Base Color"]); L(bump.outputs["Normal"], pine.inputs["Normal"])
    sb = nt.nodes.new("ShaderNodeBump"); sb.inputs["Strength"].default_value = 0.35; L(clump.outputs["Fac"], sb.inputs["Height"])
    snow = principled(nt, (0.74, 0.79, 0.87), rough=0.65)
    L(sb.outputs["Normal"], snow.inputs["Normal"])
    mix = nt.nodes.new("ShaderNodeMixShader")
    L(fac.outputs["Result"], mix.inputs[0]); L(pine.outputs[0], mix.inputs[1]); L(snow.outputs[0], mix.inputs[2])
    return with_fog(m, nt, out, mix.outputs[0])


def spruce(name, h, seed, mat):
    """A snow-laden spruce: tiers of ragged, drooping branches around a dense core."""
    r_ = np.random.default_rng(seed)
    VV, QQ = [], []
    nv = 0
    def add(verts, quads):
        nonlocal nv
        VV.append(np.asarray(verts, float)); QQ.append(np.asarray(quads) + nv); nv += len(verts)
    n = int(10 + h * 0.9)
    for z0 in np.linspace(0.15 * h, 0.95 * h, n):
        frac = (z0 - 0.15 * h) / (0.8 * h)
        R = (0.31 * h * (1 - frac) ** 0.95 + 0.2) * r_.uniform(0.9, 1.08)
        # the dense core of the tier, so you can't see through the tree
        segs, rings = 22, 3
        ang = np.linspace(0, 2 * np.pi, segs, endpoint=False) + r_.uniform(0, 1)
        rc = 0.62 * R
        v = [(0, 0, z0 + 0.35 * R)]
        for t in np.linspace(0.35, 1.0, rings):
            v += [(rc * t * math.cos(a_), rc * t * math.sin(a_), z0 + 0.35 * R * (1 - t) - 0.22 * R * t ** 1.6) for a_ in ang]
        k = np.arange(segs)
        q = [np.stack([np.zeros(segs, int), 1 + k, 1 + (k + 1) % segs, 1 + (k + 1) % segs], 1)]
        for ring in range(rings - 1):
            a0, a1 = 1 + ring * segs, 1 + (ring + 1) * segs
            q.append(np.stack([a0 + k, a1 + k, a1 + (k + 1) % segs, a0 + (k + 1) % segs], 1))
        add(v, np.concatenate(q))
        # the branches: drooping, arched, ragged fronds reaching out past the core
        m = int(7 + R * 2.6)
        for j in range(m):
            a_ = 2 * math.pi * j / m + r_.normal(0, 0.12)
            Lf = R * r_.uniform(0.8, 1.08)
            W = 2.3 * math.pi * 0.55 * R / m
            droop = R * r_.uniform(0.25, 0.4)
            d = np.array([math.cos(a_), math.sin(a_), 0.0])
            e = np.array([-math.sin(a_), math.cos(a_), 0.0])
            nt_, ns = 12, 6
            verts = []
            for t in np.linspace(0, 1, nt_):
                c = d * (0.12 * R + t * Lf * 0.88) + np.array([0, 0, z0 + 0.22 * R * (1 - t) - droop * t ** 1.8])
                wdt = W * (0.3 + 0.7 * math.sin(math.pi * min(t * 1.08, 1.0)) ** 0.6) * (1 - 0.55 * t ** 3)
                for sgn in np.linspace(-1, 1, ns):
                    jitter = r_.normal(0, 0.04 * R, 3) * (abs(sgn) ** 2 + 0.3 * t)
                    verts.append(c + e * sgn * wdt / 2 + np.array([0, 0, -0.22 * wdt * sgn * sgn]) + jitter)
            q = [(i * ns + s_, i * ns + s_ + 1, (i + 1) * ns + s_ + 1, (i + 1) * ns + s_) for i in range(nt_ - 1) for s_ in range(ns - 1)]
            add(verts, q)
    col = bpy.data.collections.new(name)
    tree = mesh_object(name + "Branches", np.concatenate(VV), np.concatenate(QQ), mat=mat, smooth=True)
    sub = tree.modifiers.new("smooth", "SUBSURF"); sub.levels = sub.render_levels = 1
    tex = bpy.data.textures.new(name + "Clumps", "CLOUDS"); tex.noise_scale = 0.22
    dsp = tree.modifiers.new("clumps", "DISPLACE"); dsp.texture = tex; dsp.strength = 0.07; dsp.texture_coords = "LOCAL"
    tex2 = bpy.data.textures.new(name + "Twigs", "CLOUDS"); tex2.noise_scale = 0.05; tex2.noise_depth = 1
    dsp2 = tree.modifiers.new("twigs", "DISPLACE"); dsp2.texture = tex2; dsp2.strength = 0.035; dsp2.texture_coords = "LOCAL"
    bpy.ops.mesh.primitive_cylinder_add(radius=0.025 * h ** 0.9, depth=0.6 * h, location=(0, 0, 0.3 * h), vertices=10)
    trunk = bpy.context.active_object
    trunk.data.materials.append(bpy.data.materials.get("Bark") or simple_material("Bark", (0.03, 0.02, 0.015), rough=0.9))
    for ob in (tree, trunk):
        for c in list(ob.users_collection):
            c.objects.unlink(ob)
        col.objects.link(ob)
    return col


HEIGHTS = (7.5, 9.5, 11.5, 13.5, 16.0, 19.0)


def seen_by_camera(px, py, pz, cams):
    """Whether a tree at (px, py) is ever in (or near) the camera's view during the flight."""
    for pos, fwd, half in cams:
        v = np.array([px, py, pz]) - pos
        dist = np.linalg.norm(v)
        if dist < 12:
            return True
        if dist < 300 and v @ fwd / dist > math.cos(half):
            return True
    return False


def forest(mat):
    variants = [spruce(f"Spruce{k}", h, 100 + k, mat) for k, h in enumerate(HEIGHTS)]
    path = path_xy()
    cams = []
    for t in np.linspace(0, SECONDS, 60):
        pos, tgt, lens = hermite(t)
        fwd = (tgt - pos) / np.linalg.norm(tgt - pos)
        cams.append((pos, fwd, math.atan(18 / lens) + math.radians(14)))
    pts, kept = 0, 0
    step = 5.2
    for x in np.arange(-280, 280, step):
        for y in np.arange(-280, 280, step):
            px, py = x + rng.uniform(-0.45, 0.45) * step, y + rng.uniform(-0.45, 0.45) * step
            d_cabin = np.hypot((px - CABIN_C[0]) / 1.0, (py - CABIN_C[1]) / 1.25)
            if d_cabin < 19 + 3 * math.sin(math.atan2(py, px) * 3) or rng.random() < 0.12:
                continue
            k = int(rng.integers(len(HEIGHTS)))
            s = rng.uniform(0.8, 1.2)
            top, reach = HEIGHTS[k] * s, 0.33 * HEIGHTS[k] * s + 2.5
            near = np.hypot(path[:, 0] - px, path[:, 1] - py) < reach
            if np.any(near & (path[:, 2] < top + 2)):
                continue                                          # the gap the camera flies down
            pz = float(height(px, py))
            pts += 1
            if not seen_by_camera(px, py, pz + top / 2, cams):
                continue
            kept += 1
            e = bpy.data.objects.new("Tree", None)
            e.instance_type = "COLLECTION"
            e.instance_collection = variants[k]
            e.scale = (s, s, s * rng.uniform(0.92, 1.1))
            e.rotation_euler = (rng.normal(0, 0.02), rng.normal(0, 0.02), rng.uniform(0, 6.3))
            e.location = (px, py, pz - 0.15)
            bpy.context.scene.collection.objects.link(e)
    print("trees:", pts, "kept in view:", kept)


# ---------------------------------------------------------------- the camera
def animate_camera(scene):
    cam = scene.camera
    scene.render.fps = FPS
    scene.frame_start, scene.frame_end = 0, NFRAMES - 1
    cam.data.dof.use_dof = True
    for f in range(NFRAMES):
        t = f / FPS
        pos, tgt, lens = hermite(t)
        cam.location = Vector(pos)
        cam.rotation_euler = (Vector(tgt) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
        cam.data.lens = lens
        settle = np.clip((t - 11.5) / 2.5, 0, 1)
        cam.data.dof.aperture_fstop = 16 * (1 - settle) + 2.8 * settle
        cam.data.dof.focus_distance = float(np.linalg.norm(np.array(pos) - np.array([0, 0, 1.6]))) if settle < 1 else \
            (Vector((0, 0, 1.4)) - D.CAMERA).length
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)
        cam.data.keyframe_insert("lens", frame=f)
        cam.data.dof.keyframe_insert("aperture_fstop", frame=f)
        cam.data.dof.keyframe_insert("focus_distance", frame=f)
    for fc in (cam.animation_data.action.fcurves if hasattr(cam.animation_data.action, "fcurves") else []):
        for k in fc.keyframe_points:
            k.interpolation = "LINEAR"


def chimney_track(scene):
    out = []
    for f in range(NFRAMES):
        scene.frame_set(f)
        cam = scene.camera
        p = world_to_camera_view(scene, cam, Vector(CHIMNEY_TOP))
        q = world_to_camera_view(scene, cam, Vector(CHIMNEY_TOP) + Vector((0, 0, 1.0)))
        out.append({"x": round(p.x, 5), "y": round(1 - p.y, 5), "depth": round(p.z, 3), "metre": round(abs(q.y - p.y), 5)})
    return out


def main():
    t0 = time.time()
    os.makedirs(OUT, exist_ok=True)
    scene = T.reset_scene()
    T.needle_material()
    T.bark_material()
    D.log_facade()
    D.roof()
    hinge = D.door()
    D.trim_and_sign()
    D.windows()
    D.lantern()
    D.interior_glow()
    D.setup(scene)
    walls()
    front_spill()
    back_roof()
    chimney()
    ground(snow_fog_material())
    forest(tree_material())
    world_with_stars(scene)
    for ob in bpy.data.objects:                       # the moon a little brighter for the wide shots
        if ob.type == "LIGHT" and ob.name.startswith("Moon"):
            ob.data.energy = 0.8
    r = scene.render
    r.resolution_x, r.resolution_y = RES
    r.resolution_percentage = 100
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGB"
    r.use_motion_blur = "--blur" in ARGS
    r.motion_blur_shutter = 0.4
    c = scene.cycles
    c.samples = SAMPLES
    c.adaptive_min_samples = 8
    c.adaptive_threshold = 0.04
    c.use_denoising = True
    c.max_bounces, c.diffuse_bounces, c.glossy_bounces = 4, 2, 1
    c.transmission_bounces, c.transparent_max_bounces, c.volume_bounces = 2, 4, 0
    c.caustics_reflective = c.caustics_refractive = False
    c.blur_glossy = 1.0
    animate_camera(scene)
    track = chimney_track(scene)
    with open(os.path.join(OUT, "exterior.json"), "w") as f:
        json.dump({"fps": FPS, "frames": NFRAMES, "size": RES, "chimney": track}, f)
    print(f"scene built in {time.time() - t0:.0f}s", flush=True)
    stills = next((a.split("=")[1] for a in ARGS if a.startswith("--still=")), None)
    if stills is not None:
        frames = [int(x) for x in stills.split(",")]
    else:
        span = next((a.split("=")[1] for a in ARGS if a.startswith("--frames=")), f"0-{NFRAMES - 1}")
        a, b = (int(x) for x in span.split("-"))
        step = int(next((a_.split("=")[1] for a_ in ARGS if a_.startswith("--step=")), 1))
        frames = list(range(a, b + 1, step))
    dbg = next((a.split("=")[1] for a in ARGS if a.startswith("--debugcam=")), None)
    if dbg:                                            # a look from somewhere else, for checking the model
        x, y, z = (float(v) for v in dbg.split(","))
        cam = scene.camera
        cam.animation_data_clear(); cam.data.animation_data_clear()
        cam.location = (x, y, z)
        cam.rotation_euler = (Vector((0, 3.5, 3.5)) - Vector((x, y, z))).to_track_quat("-Z", "Y").to_euler()
        cam.data.lens = 28
        cam.data.dof.use_dof = False
        r.filepath = os.path.join(OUT, "debug.png")
        bpy.ops.render.render(write_still=True)
        return
    for f in frames:
        path = os.path.join(OUT, f"{f:04d}.png")
        if stills is None and os.path.exists(path):
            continue                                   # (carries on after an interruption)
        t1 = time.time()
        scene.frame_set(f)
        r.filepath = path if stills is None else path.replace(".png", f"-s{SAMPLES}{'b' if r.use_motion_blur else ''}.png")
        bpy.ops.render.render(write_still=True)
        print(f"frame {f} in {time.time() - t1:.0f}s", flush=True)
    print(f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
