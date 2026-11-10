"""Render the steam rising from Fares' tumbler as a seamless animated loop (Blender, Cycles).

Builds the cabin exactly as cabin_scene.py does (same camera, same lights), with the
steam volume switched on and every other object a holdout: the frames hold only the
lit wisps, which the website adds over the room image, the same way as the fire.

    python tools/blender/cabin_steam.py [--preview]

Writes (into site/assets/cabin/):
  steam-sprite.jpg      the loop as a grid of frames
  steam.json / steam.js frame layout and where the frames go in the room image
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

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
PREVIEW = "--preview" in ARGS
FPS = 24
LOOP = 72                     # frames in the loop (3 seconds)
FADE = 24                     # frames used to blend the end of the loop into the start
SCALE = 200                   # render at 2x the room image, then scale down
SAMPLES = 12 if PREVIEW else 32
FRAMES_DIR = os.path.join(C.BUILD_DIR, "steam")


def build():
    scene, _ = C.build_cabin(steam=True)
    steam = bpy.data.objects["Steam"]
    for ob in scene.objects:
        if ob.type in {"MESH", "CURVE", "SURFACE", "META", "FONT"} and ob != steam:
            ob.is_holdout = True              # hides the steam behind it, renders nothing itself
    r = scene.render
    r.resolution_percentage = SCALE
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGB"
    r.use_persistent_data = True
    c = scene.cycles
    c.samples = SAMPLES
    c.use_adaptive_sampling = False
    c.volume_step_rate = 0.25
    c.max_bounces = 3
    c.volume_bounces = 1
    scene.view_settings.view_transform = "Standard"    # added on top of the tone-mapped room
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 1.5

    # crop to the steam volume as the camera sees it
    bpy.context.view_layer.update()
    corners = [steam.matrix_world @ Vector(c) for c in steam.bound_box]
    pts = [world_to_camera_view(scene, scene.camera, p) for p in corners]
    pad = 0.004
    x0, x1 = max(0.0, min(p.x for p in pts) - pad), min(1.0, max(p.x for p in pts) + pad)
    y0, y1 = max(0.0, min(p.y for p in pts) - pad), min(1.0, max(p.y for p in pts) + pad)
    r.use_border = True
    r.use_crop_to_border = True
    r.border_min_x, r.border_max_x, r.border_min_y, r.border_max_y = x0, x1, y0, y1
    crop = {"x0": round(x0, 5), "x1": round(x1, 5), "y0": round(1 - y1, 5), "y1": round(1 - y0, 5)}
    return scene, steam.active_material, crop


def main():
    os.makedirs(FRAMES_DIR, exist_ok=True)
    t0 = time.time()
    scene, mat, crop = build()
    print(f"scene built in {time.time() - t0:.0f}s, crop {crop}", flush=True)
    tnode = mat.node_tree.nodes["time"]
    total = LOOP + FADE
    count = int(os.environ.get("STEAM_TEST_FRAMES", 4 if PREVIEW else total))
    t0 = time.time()
    for f in range(count):
        tnode.outputs[0].default_value = f / FPS
        scene.render.filepath = os.path.join(FRAMES_DIR, f"s{f:03d}.png")
        bpy.ops.render.render(write_still=True)
        if f % 12 == 0:
            print(f"  frame {f}/{count}  {time.time() - t0:.0f}s", flush=True)
    if count < total:
        return

    frames = [FIRE.read_png(os.path.join(FRAMES_DIR, f"s{f:03d}.png")) for f in range(total)]
    loop = []
    for i in range(LOOP):
        if i < FADE:
            a = i / FADE
            loop.append(frames[i] * a + frames[LOOP + i] * (1 - a))
        else:
            loop.append(frames[i])
    loop = [0.2 * loop[i - 1] + 0.6 * loop[i] + 0.2 * loop[(i + 1) % LOOP] for i in range(LOOP)]

    cols = 12
    rows = math.ceil(LOOP / cols)
    frame_w = round((crop["x1"] - crop["x0"]) * 1920)
    small = [FIRE.resize(fr, frame_w) for fr in loop]
    fh, fw = small[0].shape[:2]
    sheet = np.zeros((rows * fh, cols * fw, 3), np.float32)
    for i, fr in enumerate(small):
        r, c = divmod(i, cols)
        sheet[r * fh:(r + 1) * fh, c * fw:(c + 1) * fw] = fr
    FIRE.write_jpeg(scene, np.clip(sheet, 0, 1), os.path.join(C.OUT_DIR, "steam-sprite.jpg"), quality=90)
    info = {"frames": LOOP, "fps": FPS, "cols": cols, "rows": rows, "frameWidth": fw, "frameHeight": fh,
            "crop": crop,
            "note": "crop is where the frames go in the room image (fractions, y from the top); "
                    "the frames are added on top (lighter blend)"}
    with open(os.path.join(C.OUT_DIR, "steam.json"), "w") as f:
        json.dump(info, f)
    with open(os.path.join(C.OUT_DIR, "steam.js"), "w") as f:
        f.write("window.CABIN_STEAM = " + json.dumps(info) + ";\n")
    print("wrote steam-sprite.jpg", sheet.shape, "in", round(time.time() - t0), "s")


if __name__ == "__main__":
    main()
