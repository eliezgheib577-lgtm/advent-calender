"""Render Fares rocking in his chair, for the website (Blender, Cycles).

Builds the cabin exactly as cabin_scene.py does and renders the patch of the room around
Fares with his chair rolled back and forward on its rockers, at evenly spaced angles. When
someone clicks him, the page swings through these with a damped rocking motion,
crossfading between neighbouring angles. A soft mask limits the frames to where the chair
and Fares actually move, so the rest of the room keeps its own flickering firelight.

    python tools/blender/cabin_rock.py [--preview]

Run it after cabin_scene.py: the room image shows him at rest (angle 0).

Writes (into site/assets/cabin/):
  rock-sprite.jpg      the frames as a grid, from leaning furthest back to furthest forward
  rock-mask.png        where the frames replace the room: white, with a soft alpha edge
  rock.json / rock.js  layout, angles, where the frames go in the room image, and the
                       clickable area around Fares
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

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cabin_scene as C  # noqa: E402
import cabin_fire as FIRE  # noqa: E402
import fares as FARES  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
PREVIEW = "--preview" in ARGS
MAX_ANGLE = 7.0                        # degrees either way
STEPS = 3 if PREVIEW else 15           # odd, so the middle frame is the chair at rest
SAMPLES = 24 if PREVIEW else 160
FRAMES_DIR = os.path.join(C.BUILD_DIR, "rock")


def extent(scene, parts):
    pts = []
    for ob in parts:
        for c in ob.bound_box:
            p = world_to_camera_view(scene, scene.camera, ob.matrix_world @ Vector(c))
            pts.append((p.x, 1 - p.y))
    pts = np.array(pts)
    return pts[:, 0].min(), pts[:, 0].max(), pts[:, 1].min(), pts[:, 1].max()


def build():
    scene, _ = C.build_cabin()
    root = bpy.data.objects["Fares"]
    bpy.context.view_layer.update()
    rest = root.matrix_world.copy()
    parts = [o for o in root.children_recursive if o.type in {"MESH", "CURVE"}]

    # the clickable area: Fares and his chair at rest; the crop: everything they sweep through
    hx0, hx1, hy0, hy1 = extent(scene, parts)
    boxes = [(hx0, hx1, hy0, hy1)]
    for a in (-MAX_ANGLE, MAX_ANGLE):
        root.matrix_world = rest @ FARES.rock_matrix(math.radians(a))
        bpy.context.view_layer.update()
        boxes.append(extent(scene, parts))
    root.matrix_world = rest
    bpy.context.view_layer.update()
    b = np.array(boxes)
    pad = 0.012
    x0, x1 = max(0.0, b[:, 0].min() - pad), min(1.0, b[:, 1].max() + pad)
    y0, y1 = max(0.0, b[:, 2].min() - pad), min(1.0, b[:, 3].max() + pad)

    r = scene.render
    r.use_border = True
    r.use_crop_to_border = True
    r.border_min_x, r.border_max_x = x0, x1
    r.border_min_y, r.border_max_y = 1 - y1, 1 - y0
    r.use_persistent_data = True
    scene.cycles.samples = SAMPLES
    crop = {"x0": round(float(x0), 5), "x1": round(float(x1), 5), "y0": round(float(y0), 5), "y1": round(float(y1), 5)}
    hotspot = {"x0": round(float(hx0), 5), "x1": round(float(hx1), 5), "y0": round(float(hy0), 5), "y1": round(float(hy1), 5)}
    return scene, root, rest, crop, hotspot


def read_linear(path):
    img = bpy.data.images.load(path)
    w, h = img.size
    px = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    return px.reshape(h, w, 4)[::-1, :, :3]


def vignette(img, crop):
    """The room image's vignette (cabin_scene.photo_finish), for this patch of it."""
    h, w, _ = img.shape
    W, H = w / (crop["x1"] - crop["x0"]), h / (crop["y1"] - crop["y0"])
    xx = crop["x0"] * W + np.arange(w)[None, :] + 0.5
    yy = crop["y0"] * H + np.arange(h)[:, None] + 0.5
    rr = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 * 0.8 + ((yy - H / 2) / (H / 2)) ** 2 * 0.6)
    return img * (1 - 0.32 * np.clip(rr, 0, 1.2) ** 2.4)[..., None]


def dilate(m, r):
    out = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy <= r * r:
                out = np.maximum(out, np.roll(np.roll(m, dy, 0), dx, 1))
    return out


def main():
    os.makedirs(FRAMES_DIR, exist_ok=True)
    t0 = time.time()
    scene, root, rest, crop, hotspot = build()
    print(f"scene built in {time.time() - t0:.0f}s, crop {crop}", flush=True)
    angles = np.linspace(-MAX_ANGLE, MAX_ANGLE, STEPS)
    frames = []
    t0 = time.time()
    for i, a in enumerate(angles):
        root.matrix_world = rest @ FARES.rock_matrix(math.radians(a))
        exr = os.path.join(FRAMES_DIR, f"r{i:02d}.exr")
        settings = scene.render.image_settings          # (saving the tone-mapped frame changes these)
        settings.media_type = "IMAGE"
        settings.file_format = "OPEN_EXR"
        settings.color_depth = "32"
        scene.render.filepath = exr
        bpy.ops.render.render(write_still=True)
        jpg = os.path.join(FRAMES_DIR, f"r{i:02d}.jpg")
        C.save_tonemapped(scene, vignette(np.clip(read_linear(exr), 0, None), crop), jpg)
        frames.append(FIRE.read_png(jpg))
        print(f"  angle {a:+.1f}  {time.time() - t0:.0f}s", flush=True)
    root.matrix_world = rest

    # the mask: wherever any frame differs from the chair at rest, grown and softened
    still = frames[len(frames) // 2]
    diff = np.max([np.abs(f - still).max(axis=2) for f in frames], axis=0)
    diff = C.blur(diff[..., None], 1.5)[..., 0]
    k = max(1, round(frames[0].shape[1] / 60))
    m = dilate((diff > 0.035).astype(np.float32), 3 * k)
    m = np.clip(C.blur(m[..., None], 2.0 * k)[..., 0] * 1.4, 0, 1)
    h, w = m.shape
    edge = np.minimum.reduce([np.arange(w)[None, :].repeat(h, 0), np.arange(w)[::-1][None, :].repeat(h, 0),
                              np.arange(h)[:, None].repeat(w, 1), np.arange(h)[::-1][:, None].repeat(w, 1)])
    m *= np.clip(edge / (3.0 * k), 0, 1)

    cols = 5
    rows = math.ceil(len(frames) / cols)
    sheet = np.zeros((rows * h, cols * w, 3), np.float32)
    for i, fr in enumerate(frames):
        r, c = divmod(i, cols)
        sheet[r * h:(r + 1) * h, c * w:(c + 1) * w] = fr
    FIRE.write_jpeg(scene, np.clip(sheet, 0, 1), os.path.join(C.OUT_DIR, "rock-sprite.jpg"), quality=88)
    img = bpy.data.images.new("mask", w, h, alpha=True)
    rgba = np.concatenate([np.ones((h, w, 3), np.float32), m[..., None]], -1)[::-1]
    img.pixels.foreach_set(np.ascontiguousarray(rgba, dtype=np.float32).ravel())
    img.filepath_raw = os.path.join(C.OUT_DIR, "rock-mask.png")
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    info = {"frames": len(frames), "angles": [round(float(a), 2) for a in angles], "cols": cols, "rows": rows,
            "frameWidth": w, "frameHeight": h, "crop": crop, "hotspot": hotspot,
            "note": "frames run from leaning furthest back to furthest forward; the middle one is at rest, as in "
                    "the room image. crop is where they go and hotspot is Fares and his chair at rest (fractions "
                    "of the room image, y from the top). rock-mask.png says where the frames replace the room."}
    with open(os.path.join(C.OUT_DIR, "rock.json"), "w") as f:
        json.dump(info, f)
    with open(os.path.join(C.OUT_DIR, "rock.js"), "w") as f:
        f.write("window.CABIN_ROCK = " + json.dumps(info) + ";\n")
    print("wrote rock-sprite.jpg", sheet.shape, "in", round(time.time() - t0), "s")


if __name__ == "__main__":
    main()
