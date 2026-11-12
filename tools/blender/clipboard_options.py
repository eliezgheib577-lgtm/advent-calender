"""Render where the "How it works" clipboard could hang, from the room's own camera.

    python tools/blender/clipboard_options.py [--samples=32] [window emblem]

Writes build/clipboard-options/<place>.png: the right-hand part of the room.
"""
import os
import sys
import time

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cabin_scene as C  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
SAMPLES = int(next((a.split("=")[1] for a in ARGS if a.startswith("--samples=")), 32))
PLACES = [a for a in ARGS if not a.startswith("--")] or list(C.CLIPBOARD_AT)
OUT = os.path.join(C.BUILD_DIR, "clipboard-options")
NAMES = ("ClipBoard", "ClipSheet", "ClipPlate", "ClipLever", "Cylinder")


def main():
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    C.CLIPBOARD = PLACES[0]
    scene, _ = C.build_cabin()
    r = scene.render
    r.resolution_x, r.resolution_y, r.resolution_percentage = 1920, 1080, 100
    r.use_border, r.use_crop_to_border = True, True
    r.border_min_x, r.border_max_x, r.border_min_y, r.border_max_y = 0.58, 1.0, 0.3, 1.0
    r.image_settings.media_type = "IMAGE"
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGB"
    scene.cycles.samples = SAMPLES
    print(f"room built in {time.time() - t0:.0f}s", flush=True)
    for k, place in enumerate(PLACES):
        if k:
            for ob in [o for o in bpy.data.objects if o.name.startswith(NAMES) and o.parent is None
                       and abs(o.location.y - (C.BACK_Y - 0.06)) < 0.03]:
                bpy.data.objects.remove(ob, do_unlink=True)
            C.CLIPBOARD = place
            C.clipboard()
        t1 = time.time()
        r.filepath = os.path.join(OUT, f"{place}.png")
        bpy.ops.render.render(write_still=True)
        print(f"  {place}: {time.time() - t1:.0f}s", flush=True)


if __name__ == "__main__":
    main()
