"""Render the fire in the cabin's fireplace as a seamless animated loop (Blender, Cycles).

The flames are a procedural volume: rising, domain-warped 4D noise shaped over the
logs, glowing with blackbody colour from deep red to white-yellow, plus a few sparks
drifting up. Everything else in the fireplace (logs, grate, stones, stockings) is a
holdout, so the frames are pure firelight that the website adds on top of the room.

Run after cabin_scene.py (same camera):
    python tools/blender/cabin_fire.py [--preview]

Writes (into site/assets/cabin/):
  fire-sprite.jpg     the loop as a grid of frames
  fire.json / fire.js frame layout, where the frames go in the room image, and the fire's
                      brightness per frame (drives the flickering firelight on the room)
"""
import json
import math
import os
import sys
import time

import numpy as np
import bpy
import bmesh
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lemsic_tree as T  # noqa: E402
import cabin_scene as C  # noqa: E402
from lemsic_tree import link, new_material  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
PREVIEW = "--preview" in ARGS
FPS = 24
LOOP = 96                     # frames in the loop (4 seconds)
FADE = 24                     # frames used to blend the end of the loop into the start
SCALE = 100 if PREVIEW else 150          # render at 1.5x the room image, then scale down
SAMPLES = 16 if PREVIEW else 20
FRAME_W = 340                 # width of each frame in the sprite sheet
FRAMES_DIR = os.path.join(C.BUILD_DIR, "fire")
rng = np.random.default_rng(5)


# ---------------------------------------------------------------- the flame volume
def flame_material():
    m, nt, out = new_material("Flames")
    L = nt.links.new

    def n(kind, **inputs):
        x = nt.nodes.new(kind)
        for k, v in inputs.items():
            x.inputs[k].default_value = v
        return x

    def math_node(op, a=None, b=None, clamp=False):
        x = nt.nodes.new("ShaderNodeMath")
        x.operation = op
        x.use_clamp = clamp
        if a is not None:
            x.inputs[0].default_value = a
        if b is not None:
            x.inputs[1].default_value = b
        return x

    def smooth(lo, hi):
        x = nt.nodes.new("ShaderNodeMapRange")
        x.interpolation_type = "SMOOTHSTEP"
        x.inputs["From Min"].default_value = lo
        x.inputs["From Max"].default_value = hi
        return x

    tc = nt.nodes.new("ShaderNodeTexCoord")
    tval = nt.nodes.new("ShaderNodeValue")
    tval.name = "time"
    tval.outputs[0].default_value = 0.0
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    L(tc.outputs["Object"], sep.inputs[0])

    # rising coordinates
    rise = math_node("MULTIPLY", b=0.62)
    L(tval.outputs[0], rise.inputs[0])
    lift = nt.nodes.new("ShaderNodeCombineXYZ")
    L(rise.outputs[0], lift.inputs["Z"])
    q = n("ShaderNodeVectorMath")
    q.operation = "SUBTRACT"
    L(tc.outputs["Object"], q.inputs[0])
    L(lift.outputs[0], q.inputs[1])

    # domain warp
    w_t = math_node("MULTIPLY", b=0.45)
    L(tval.outputs[0], w_t.inputs[0])
    warp = n("ShaderNodeTexNoise", Scale=3.2, Detail=3.0)
    warp.noise_dimensions = "4D"
    L(q.outputs[0], warp.inputs["Vector"])
    L(w_t.outputs[0], warp.inputs["W"])
    centred = n("ShaderNodeVectorMath")
    centred.operation = "SUBTRACT"
    centred.inputs[1].default_value = (0.5, 0.5, 0.5)
    L(warp.outputs["Color"], centred.inputs[0])
    wscale = n("ShaderNodeVectorMath")
    wscale.operation = "SCALE"
    wscale.inputs["Scale"].default_value = 0.22
    L(centred.outputs[0], wscale.inputs[0])
    qw = n("ShaderNodeVectorMath")
    qw.operation = "ADD"
    L(q.outputs[0], qw.inputs[0])
    L(wscale.outputs[0], qw.inputs[1])
    stretch = n("ShaderNodeVectorMath")
    stretch.operation = "MULTIPLY"
    stretch.inputs[1].default_value = (7.5, 7.5, 2.1)
    L(qw.outputs[0], stretch.inputs[0])

    # the flame body: licking noise
    n_t = math_node("MULTIPLY", b=1.1)
    L(tval.outputs[0], n_t.inputs[0])
    body = n("ShaderNodeTexNoise", Scale=1.0, Detail=6.0, Roughness=0.58)
    body.noise_dimensions = "4D"
    L(stretch.outputs[0], body.inputs["Vector"])
    L(n_t.outputs[0], body.inputs["W"])

    # shape: over the logs, narrowing and dying out upward
    h = math_node("DIVIDE", b=0.50)                      # 0 at the logs, 1 at the flame tips
    L(sep.outputs["Z"], h.inputs[0])
    hc = math_node("MINIMUM", b=1.0)
    L(h.outputs[0], hc.inputs[0])
    hc0 = math_node("MAXIMUM", b=0.0)
    L(hc.outputs[0], hc0.inputs[0])
    halfw = math_node("MULTIPLY_ADD")                    # 0.34 * (1 - 0.6 h)
    halfw.inputs[1].default_value = -0.204
    halfw.inputs[2].default_value = 0.34
    L(hc0.outputs[0], halfw.inputs[0])
    ax = math_node("ABSOLUTE")
    L(sep.outputs["X"], ax.inputs[0])
    ex = math_node("DIVIDE")
    L(ax.outputs[0], ex.inputs[0])
    L(halfw.outputs[0], ex.inputs[1])
    sx = smooth(1.0, 0.55)
    L(ex.outputs[0], sx.inputs["Value"])
    ay = math_node("ABSOLUTE")
    L(sep.outputs["Y"], ay.inputs[0])
    sy = smooth(0.17, 0.07)
    L(ay.outputs[0], sy.inputs["Value"])
    sz_top = smooth(1.0, 0.2)
    L(h.outputs[0], sz_top.inputs["Value"])
    sz_bot = smooth(-0.04, 0.03)
    L(sep.outputs["Z"], sz_bot.inputs["Value"])
    m1 = math_node("MULTIPLY")
    L(sx.outputs[0], m1.inputs[0]); L(sy.outputs[0], m1.inputs[1])
    m2 = math_node("MULTIPLY")
    L(m1.outputs[0], m2.inputs[0]); L(sz_top.outputs[0], m2.inputs[1])
    mask = math_node("MULTIPLY")
    L(m2.outputs[0], mask.inputs[0]); L(sz_bot.outputs[0], mask.inputs[1])

    # flame = clamp((noise - 0.40 - 0.22 h) * 3.2) * mask
    thr = math_node("MULTIPLY_ADD")
    thr.inputs[1].default_value = -0.22
    thr.inputs[2].default_value = 0.0
    L(hc0.outputs[0], thr.inputs[0])
    d = math_node("ADD")
    L(body.outputs["Fac"], d.inputs[0]); L(thr.outputs[0], d.inputs[1])
    d2 = math_node("MULTIPLY_ADD", clamp=True)
    d2.inputs[1].default_value = 4.8
    d2.inputs[2].default_value = -0.41 * 4.8
    L(d.outputs[0], d2.inputs[0])
    flame = math_node("MULTIPLY")
    L(d2.outputs[0], flame.inputs[0]); L(mask.outputs[0], flame.inputs[1])

    # colour by temperature, brightness rising steeply with heat
    kelvin = math_node("MULTIPLY_ADD")
    kelvin.inputs[1].default_value = 1900.0
    kelvin.inputs[2].default_value = 1000.0
    L(flame.outputs[0], kelvin.inputs[0])
    bb = nt.nodes.new("ShaderNodeBlackbody")
    L(kelvin.outputs[0], bb.inputs["Temperature"])
    sq = math_node("POWER", b=2.2)
    L(flame.outputs[0], sq.inputs[0])
    strength = math_node("MULTIPLY", b=120.0)
    L(sq.outputs[0], strength.inputs[0])
    em = nt.nodes.new("ShaderNodeEmission")
    L(bb.outputs[0], em.inputs["Color"])
    L(strength.outputs[0], em.inputs["Strength"])
    L(em.outputs[0], out.inputs["Volume"])
    try:
        m.cycles.volume_step_rate = 0.4
    except AttributeError:
        pass
    return m


def add_flames():
    hw, d, z0 = 0.42, 0.24, C.HEARTH_H + 0.12        # bed centre a little above the hearth
    verts = [(x, y, z) for z in (-0.06, 0.62) for y in (-d, d) for x in (-hw, hw)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    me = bpy.data.meshes.new("FlameVolume")
    me.from_pydata(verts, [], faces)
    bm = bmesh.new()                                      # volumes need outward-facing normals
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()
    ob = link(bpy.data.objects.new("FlameVolume", me))
    ob.location = C.fp((0.0, 0.27, z0))
    ob.rotation_euler = (0, 0, C.FP_ANGLE)
    mat = flame_material()
    me.materials.append(mat)
    return ob, mat


class Sparks:
    """A few sparks that rise from the logs, drift, and fade."""

    def __init__(self, n=12):
        self.mat = new_material("Spark")[0]
        nt = self.mat.node_tree
        em = nt.nodes.new("ShaderNodeEmission")
        em.inputs["Color"].default_value = (1.0, 0.55, 0.18, 1)
        em.inputs["Strength"].default_value = 60.0
        nt.links.new(em.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
        self.obs = []
        for k in range(n):
            bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=4, radius=1.0)
            ob = bpy.context.active_object
            ob.data.materials.append(self.mat)
            self.obs.append(ob)
        span = (LOOP + FADE) / FPS
        self.spawn = rng.uniform(0, span, n)
        self.life = rng.uniform(0.6, 1.3, n)
        self.x0 = rng.uniform(-0.25, 0.25, n)
        self.y0 = rng.uniform(-0.12, 0.12, n)
        self.vz = rng.uniform(0.55, 1.0, n)
        self.vx = rng.normal(0, 0.12, n)
        self.wob = rng.uniform(0, 6.28, n)

    def update(self, t):
        for k, ob in enumerate(self.obs):
            age = (t - self.spawn[k]) % ((LOOP + FADE) / FPS)
            if age > self.life[k]:
                ob.hide_render = True
                continue
            ob.hide_render = False
            f = age / self.life[k]
            x = self.x0[k] + self.vx[k] * age + 0.03 * math.sin(self.wob[k] + age * 7)
            z = C.HEARTH_H + 0.2 + self.vz[k] * age - 0.15 * age * age
            ob.location = C.fp((x, 0.25 + self.y0[k], z))
            vel = Vector((self.vx[k], 0, self.vz[k] - 0.3 * age)).normalized()
            ob.rotation_euler = vel.to_track_quat("Z", "Y").to_euler()
            r = 0.0035 * (1 - f) + 0.001
            ob.scale = (r, r, r * 3.5)                    # a short streak along the motion


# ---------------------------------------------------------------- scene
def build():
    scene = T.reset_scene()
    T.CAMERA = C.CAMERA
    T.bark_material()                                     # used by the firewood
    T.needle_material()                                   # used by the mantel garland
    C.build_fireplace()
    for ob in bpy.data.objects:
        if ob.type == "LIGHT":
            bpy.data.objects.remove(ob, do_unlink=True)
        elif ob.type == "MESH":
            ob.is_holdout = True                          # hides the flames behind it, renders nothing itself
    flames, mat = add_flames()
    sparks = Sparks()

    cam_data = bpy.data.cameras.new("Camera")
    cam_data.lens = C.LENS
    cam_data.dof.use_dof = True
    cam_data.dof.focus_distance = (Vector((0, -0.55, 1.5)) - C.CAMERA).length
    cam_data.dof.aperture_fstop = 2.0
    cam = link(bpy.data.objects.new("Camera", cam_data))
    cam.location = C.CAMERA
    cam.rotation_euler = (C.TARGET - C.CAMERA).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam

    world = bpy.data.worlds.new("Black")
    scene.world = world
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0

    r = scene.render
    r.engine = "CYCLES"
    r.resolution_x, r.resolution_y = 1920, 1080
    r.resolution_percentage = SCALE
    r.film_transparent = False
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGB"
    r.use_persistent_data = True
    c = scene.cycles
    c.device = "CPU"
    c.samples = SAMPLES
    c.use_denoising = True
    c.max_bounces = 2
    c.volume_bounces = 0
    scene.view_settings.view_transform = "Standard"     # keeps the flame colours rich; added on top of the room
    scene.view_settings.look = "None"
    scene.view_settings.exposure = -1.6

    # crop to the fireplace opening
    bpy.context.view_layer.update()
    hw = C.OPEN_W / 2
    corners = [C.fp((x, 0.0, z)) for x in (-hw, hw) for z in (C.HEARTH_H, C.HEARTH_H + C.OPEN_H)]
    pts = [world_to_camera_view(scene, cam, Vector(p)) for p in corners]
    pad = 0.006
    x0, x1 = min(p.x for p in pts) - pad, max(p.x for p in pts) + pad
    y0, y1 = min(p.y for p in pts) - pad, max(p.y for p in pts) + pad
    r.use_border = True
    r.use_crop_to_border = True
    r.border_min_x, r.border_max_x, r.border_min_y, r.border_max_y = x0, x1, y0, y1
    crop = {"x0": round(x0, 5), "x1": round(x1, 5), "y0": round(1 - y1, 5), "y1": round(1 - y0, 5)}
    return scene, mat, sparks, crop


def read_png(path):
    img = bpy.data.images.load(path)
    w, h = img.size
    px = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    return px.reshape(h, w, 4)[::-1, :, :3]


def write_jpeg(scene, rgb, path, quality=86):
    h, w, _ = rgb.shape
    img = bpy.data.images.new("out", w, h, alpha=False)
    img.colorspace_settings.name = "sRGB"
    rgba = np.concatenate([rgb, np.ones((h, w, 1), np.float32)], -1)[::-1]
    img.pixels.foreach_set(np.ascontiguousarray(rgba, dtype=np.float32).ravel())
    img.filepath_raw = path
    img.file_format = "JPEG"
    scene.render.image_settings.file_format = "JPEG"
    scene.render.image_settings.quality = quality
    img.save(filepath=path, quality=quality)
    bpy.data.images.remove(img)


def resize(img, w):
    """Box-filter downscale to width w (keeps aspect)."""
    h0, w0, _ = img.shape
    h = round(h0 * w / w0)
    ys = (np.arange(h + 1) * h0 / h).astype(int)
    xs = (np.arange(w + 1) * w0 / w).astype(int)
    cs = np.cumsum(np.cumsum(np.pad(img, ((1, 0), (1, 0), (0, 0))), 0), 1)
    tot = cs[ys[1:]][:, xs[1:]] - cs[ys[:-1]][:, xs[1:]] - cs[ys[1:]][:, xs[:-1]] + cs[ys[:-1]][:, xs[:-1]]
    area = np.outer(np.diff(ys), np.diff(xs))[..., None]
    return tot / area


def main():
    os.makedirs(FRAMES_DIR, exist_ok=True)
    scene, mat, sparks, crop = build()
    tnode = mat.node_tree.nodes["time"]
    total = LOOP + FADE
    count = (int(os.environ.get("FIRE_TEST_FRAMES", 8)) if PREVIEW else total)
    t0 = time.time()
    for f in range(count):
        t = f / FPS
        tnode.outputs[0].default_value = t
        sparks.update(t)
        scene.render.filepath = os.path.join(FRAMES_DIR, f"f{f:03d}.png")
        bpy.ops.render.render(write_still=True)
        if f % 12 == 0:
            print(f"  frame {f}/{count}  {time.time() - t0:.0f}s", flush=True)
    if PREVIEW:
        return

    # load in sRGB display values; blend the end of the run into its start for a seamless loop
    frames = [read_png(os.path.join(FRAMES_DIR, f"f{f:03d}.png")) for f in range(total)]
    loop = []
    for i in range(LOOP):
        if i < FADE:
            a = i / FADE
            loop.append(frames[i] * a + frames[LOOP + i] * (1 - a))
        else:
            loop.append(frames[i])
    # a touch of motion blur between neighbouring frames, like a real camera
    loop = [0.2 * loop[i - 1] + 0.6 * loop[i] + 0.2 * loop[(i + 1) % LOOP] for i in range(LOOP)]

    # brightness of the fire per frame, left and right half: drives the room's firelight
    lum = np.array([(fr[..., :3] @ [0.2126, 0.7152, 0.0722]) for fr in loop])
    half = lum.shape[2] // 2
    left, right = lum[:, :, :half].mean(axis=(1, 2)), lum[:, :, half:].mean(axis=(1, 2))
    def norm(v):
        v = (v - v.mean()) / (v.std() + 1e-6)
        return np.clip(0.5 + 0.22 * v, 0, 1)
    flicker = np.stack([norm(left), norm(right)], 1).round(3).tolist()

    cols = 12
    rows = math.ceil(LOOP / cols)
    small = [resize(fr, FRAME_W) for fr in loop]
    fh, fw = small[0].shape[:2]
    sheet = np.zeros((rows * fh, cols * fw, 3), np.float32)
    for i, fr in enumerate(small):
        r, c = divmod(i, cols)
        sheet[r * fh:(r + 1) * fh, c * fw:(c + 1) * fw] = fr
    write_jpeg(scene, np.clip(sheet, 0, 1), os.path.join(C.OUT_DIR, "fire-sprite.jpg"))
    info = {"frames": LOOP, "fps": FPS, "cols": cols, "rows": rows, "frameWidth": fw, "frameHeight": fh,
            "crop": crop, "flicker": flicker,
            "note": "crop is where the frames go in the room image (fractions, y from the top); "
                    "flicker is the fire's brightness per frame, [left, right], 0..1"}
    with open(os.path.join(C.OUT_DIR, "fire.json"), "w") as f:
        json.dump(info, f)
    with open(os.path.join(C.OUT_DIR, "fire.js"), "w") as f:
        f.write("window.CABIN_FIRE = " + json.dumps(info) + ";\n")
    print("wrote fire-sprite.jpg", sheet.shape, "in", round(time.time() - t0), "s")


if __name__ == "__main__":
    main()
