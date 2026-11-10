"""Render the Lebanese cedar (arz) tree options in the cabin, from the room's own camera.

Builds the room once, then for each option swaps in that tree (same needles, colours and
decorations; only the form changes) and renders the part of the room around it.

    python tools/blender/tree_options.py [--samples=48] [only these: arz_emblem5 arz_flag7 ...]

Writes build/tree-options/<option>.png.
"""
import os
import sys
import time

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lemsic_tree as T  # noqa: E402
import cabin_scene as C  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
SAMPLES = int(next((a.split("=")[1] for a in ARGS if a.startswith("--samples=")), 48))
OPTIONS = [a for a in ARGS if not a.startswith("--")] or (["cedar_lemsic"] + list(T.ARZ_SHAPES))
OUT = os.path.join(C.BUILD_DIR, "tree-options")


def build_tree(style):
    T.apply_style(style)
    T.FLOOR_LIFT = 0.03
    T.CAMERA = C.CAMERA
    before = set(bpy.data.objects)
    T.build_tree()
    return set(bpy.data.objects) - before


def remove(objects):
    for ob in objects:
        bpy.data.objects.remove(ob, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.curves, bpy.data.lights):
        for block in [b for b in coll if b.users == 0]:
            coll.remove(block)


def main():
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    scene = T.reset_scene()
    tree = build_tree(OPTIONS[0])
    C.build_room()
    C.build_fireplace()
    C.setup(scene)
    r = scene.render
    r.resolution_x, r.resolution_y, r.resolution_percentage = 1920, 1080, 100
    r.use_border, r.use_crop_to_border = True, True
    r.border_min_x, r.border_max_x, r.border_min_y, r.border_max_y = 0.2, 0.82, 0.0, 1.0
    r.image_settings.media_type = "IMAGE"
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGB"
    scene.cycles.samples = SAMPLES
    print(f"room built in {time.time() - t0:.0f}s", flush=True)
    for k, style in enumerate(OPTIONS):
        t1 = time.time()
        if k:
            remove(tree)
            tree = build_tree(style)
        r.filepath = os.path.join(OUT, f"{style}.png")
        bpy.ops.render.render(write_still=True)
        print(f"  {style}: {T.STYLES[style]['label']}  {time.time() - t1:.0f}s", flush=True)


if __name__ == "__main__":
    main()
