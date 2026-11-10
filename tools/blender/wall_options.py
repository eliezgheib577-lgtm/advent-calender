"""Render picture-wall layouts in the cabin, from the room's own camera, to choose between.

Builds the room once (without Fares, who is out of the shot), then for each layout swaps in
that set of frames and renders the part of the room around the wall.

    python tools/blender/wall_options.py [--samples=32] [only these: grid5_emblem grid5_star rows5_24 ...]

Writes build/wall-options/<layout>.png.
"""
import math
import os
import sys
import time

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lemsic_tree as T  # noqa: E402
import cabin_scene as C  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
SAMPLES = int(next((a.split("=")[1] for a in ARGS if a.startswith("--samples=")), 32))
OUT = os.path.join(C.BUILD_DIR, "wall-options")

# five columns of bigger frames (0.9 of the original size, against 0.82 now), five rows
S5 = 0.9
XS5 = [-2.286, -1.963, -1.640, -1.317, -0.994]
ZS5 = [3.659, 3.371, 3.083, 2.795, 2.507]
LAYOUTS = {
    "grid5_emblem": ("5 x 5, the 25th frame holds the LeMSIC emblem", S5, [(z, XS5) for z in ZS5[:4]] + [(ZS5[4], XS5[:4])],
                     "emblem"),
    "grid5_star": ("5 x 5, the 25th frame is a gold star for Christmas Day", S5, [(z, XS5) for z in ZS5[:4]] + [(ZS5[4], XS5[:4])],
                   "star"),
    "rows5_24": ("5 across, 24 frames: the last row of 4 centred", S5,
                 [(z, XS5) for z in ZS5[:4]] + [(ZS5[4], [round((a + b) / 2, 3) for a, b in zip(XS5, XS5[1:])])], None),
}
# four across, six down, the same bigger frames
XS4 = [-2.286, -1.997, -1.708, -1.419]
ZS6 = [3.659, 3.375, 3.091, 2.807, 2.523, 2.239]
LAYOUTS["grid4x6"] = ("4 across, 6 down", S5, [(z, XS4) for z in ZS6], None)
ORDER = [a for a in ARGS if not a.startswith("--")] or list(LAYOUTS)
BASE = dict(img=C.G_IMG, mat=C.G_MAT, mould=C.G_MOULD, scale=C.G_SCALE)
ORIGINAL_WALL = C.picture_wall


def build_wall(name):
    label, scale, rows, extra = LAYOUTS[name]
    k = scale / BASE["scale"]
    C.G_SCALE = scale
    C.G_IMG = (BASE["img"][0] * k, BASE["img"][1] * k)
    C.G_MAT, C.G_MOULD = BASE["mat"] * k, BASE["mould"] * k
    C.GALLERY = rows
    before = set(bpy.data.objects)
    ORIGINAL_WALL()
    if extra:
        cx, cz = XS5[-1], ZS5[-1]
        if extra == "emblem":
            C.framed(cx, cz, C.G_IMG[0], C.G_IMG[1], C.G_MAT, C.G_MOULD, C.print_material("EmblemPrint25", image=C.EMBLEM),
                     depth=0.026, y=C.G_Y)
        else:
            card = C.print_material("GalleryCard25", color=(0.05, 0.13, 0.36))
            W, H = C.framed(cx, cz, C.G_IMG[0], C.G_IMG[1], C.G_MAT, C.G_MOULD, card, depth=0.026, y=C.G_Y)
            gold = C.simple_material("StarGold", (0.95, 0.68, 0.25), rough=0.25, metal=1.0)
            cu = bpy.data.curves.new("GalleryStar", "FONT")
            cu.body = "★"
            cu.align_x, cu.align_y = "CENTER", "CENTER"
            cu.size = 0.11 * scale
            if os.path.exists("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
                cu.font = bpy.data.fonts.load("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", check_existing=True)
            cu.materials.append(gold)
            ob = C.link(bpy.data.objects.new("GalleryStar", cu))
            ob.location = (cx, C.G_Y - 0.0152, cz)
            ob.rotation_euler = (math.radians(90), 0, 0)
            brass = bpy.data.materials.get("Brass")
            C.box("GalleryPlate", (0.078 * scale, 0.006, 0.028 * scale), (cx, C.G_Y - 0.003, cz - H / 2 - 0.036 * scale), brass)
    return set(bpy.data.objects) - before, label


def remove(objects):
    for ob in objects:
        bpy.data.objects.remove(ob, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.curves):
        for block in [b for b in coll if b.users == 0]:
            coll.remove(block)


def main():
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    scene = T.reset_scene()
    T.apply_style(C.TREE_STYLE)
    T.FLOOR_LIFT = 0.03
    T.CAMERA = C.CAMERA
    T.build_tree()
    C.picture_wall = lambda: None              # the room without its frames; each layout adds its own
    C.build_room()
    C.build_fireplace()
    C.setup(scene)
    r = scene.render
    r.resolution_x, r.resolution_y, r.resolution_percentage = 1920, 1080, 100
    r.use_border, r.use_crop_to_border = True, True
    r.border_min_x, r.border_max_x, r.border_min_y, r.border_max_y = 0.22, 0.6, 0.5, 1.0
    r.image_settings.media_type = "IMAGE"
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGB"
    scene.cycles.samples = SAMPLES
    print(f"room built in {time.time() - t0:.0f}s", flush=True)
    wall = set()
    for name in ORDER:
        t1 = time.time()
        remove(wall)
        wall, label = build_wall(name)
        r.filepath = os.path.join(OUT, f"{name}.png")
        bpy.ops.render.render(write_still=True)
        print(f"  {name}: {label}  {time.time() - t1:.0f}s", flush=True)


if __name__ == "__main__":
    main()
