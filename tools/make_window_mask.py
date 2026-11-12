#!/usr/bin/env python3
"""Make the window's open-sky mask from the room image.

    python3 tools/make_window_mask.py        (needs Pillow and numpy)

On Christmas Eve the page draws a moon and Santa's sleigh outside the window. They are far away
in the sky, so they must sit behind the window frame, the glazing bars, the frost on the glass
and the snowy spruces outside: they are only drawn where this mask is white, the open sky seen
through clear glass, found by colour in site/assets/cabin/cabin-low.jpg (the sky is blue, the
spruces nearly black, the wood warm brown, the frost pale). Writes site/assets/cabin/window-mask.png,
covering the window's bounding box (scene.json "window"), and prints where the biggest patch of
sky is, for the moon. Run it after re-rendering the cabin.
"""
import json
import os

import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CABIN = os.path.join(ROOT, "site", "assets", "cabin")


def big_patches(on, min_share):
    """Only the patches of sky that are a real opening between the trees (at least min_share of the
    window), not the pale snow on the branches."""
    h, w = on.shape
    label = np.zeros((h, w), np.int32)
    keep = np.zeros((h, w), np.uint8)
    n = 0
    for y0, x0 in zip(*np.nonzero(on)):
        if label[y0, x0]:
            continue
        n += 1
        stack, cells = [(y0, x0)], []
        label[y0, x0] = n
        while stack:
            y, x = stack.pop()
            cells.append((y, x))
            for yy, xx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                if 0 <= yy < h and 0 <= xx < w and on[yy, xx] and not label[yy, xx]:
                    label[yy, xx] = n
                    stack.append((yy, xx))
        if len(cells) >= min_share * h * w:
            ys, xs = zip(*cells)
            keep[list(ys), list(xs)] = 1
    return keep


def main():
    scene = json.load(open(os.path.join(CABIN, "scene.json")))
    room = Image.open(os.path.join(CABIN, "cabin-low.jpg")).convert("RGB")
    W, H = room.size
    xs = [p[0] * W for p in scene["window"]]
    ys = [p[1] * H for p in scene["window"]]
    box = (int(np.floor(min(xs))), int(np.floor(min(ys))), int(np.ceil(max(xs))), int(np.ceil(max(ys))))
    img = np.asarray(room.crop(box)).astype(np.float32)
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    lum = 0.3 * r + 0.59 * g + 0.11 * b
    sat = img.max(-1) - img.min(-1)
    wood = np.clip((r - b - 12) / 20, 0, 1)
    frost = np.clip((lum - 95) / 55, 0, 1) * np.clip(1 - (sat - 40) / 60, 0, 1)
    glass = np.clip(1 - wood - frost, 0, 1)
    sky = np.clip((b - 38) / 25, 0, 1) * np.clip((b - r - 20) / 15, 0, 1) * glass
    # open it up (drop thin glints along the frost and the snow on the branches), then soften the edge
    mask = Image.fromarray((sky * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(5)).filter(ImageFilter.MaxFilter(5))
    mask = Image.fromarray(np.asarray(mask) * big_patches(np.asarray(mask) > 100, 0.02))
    deep, k = mask.point(lambda v: 255 if v > 128 else 0), 0
    while True:                                                     # the deepest point of sky, for the moon
        smaller = deep.filter(ImageFilter.MinFilter(3))
        if not np.asarray(smaller).any():
            break
        deep, k = smaller, k + 1
    ys, xs = np.nonzero(np.asarray(deep))
    w, h = mask.size
    print(f"biggest patch of sky: u {xs.mean() / w:.3f}, v {1 - ys.mean() / h:.3f}, radius {k / w:.3f} of the width")
    mask = mask.filter(ImageFilter.GaussianBlur(0.8))
    out = Image.new("RGBA", mask.size, (255, 255, 255, 0))
    out.putalpha(mask)
    out.save(os.path.join(CABIN, "window-mask.png"), optimize=True)
    print("wrote site/assets/cabin/window-mask.png", mask.size)


if __name__ == "__main__":
    main()
