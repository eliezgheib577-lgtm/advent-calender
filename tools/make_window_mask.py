#!/usr/bin/env python3
"""Make the window's clear-glass mask from the room image.

    python3 tools/make_window_mask.py        (needs Pillow and numpy)

On Christmas Eve the page draws a moon and Santa's sleigh outside the window. They must sit
behind the window frame, the glazing bars and the frost on the glass, so they are only drawn
where this mask is white: the clear glass, found by colour in site/assets/cabin/cabin-low.jpg
(the wood is warm brown, the frost pale and bright). Writes site/assets/cabin/window-mask.png,
covering the window's bounding box (scene.json "window"). Run it after re-rendering the cabin.
"""
import json
import os

import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CABIN = os.path.join(ROOT, "site", "assets", "cabin")


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
    mask = Image.fromarray((glass * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.8))
    out = Image.new("RGBA", mask.size, (255, 255, 255, 0))
    out.putalpha(mask)
    out.save(os.path.join(CABIN, "window-mask.png"), optimize=True)
    print("wrote site/assets/cabin/window-mask.png", mask.size)


if __name__ == "__main__":
    main()
