#!/usr/bin/env python3
"""Make the picture shown when the calendar's link is shared, and the small icons.

    python3 tools/make_share_card.py        (needs Pillow and numpy)

Run it after re-rendering the cabin. Writes site/assets/share-card.jpg (1200 x 630: the room
with the tree lights on, and the title in the calendar's fonts), icon-64.png (the cedar from the
emblem, for the browser tab) and icon-180.png (the emblem, for a phone's home screen).
The Alegreya fonts are downloaded once from the Google Fonts repository into build/fonts/.
"""
import os
import urllib.request

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "site", "assets")
CABIN = os.path.join(ASSETS, "cabin")
FONTS = os.path.join(ROOT, "build", "fonts")
FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/"


def font(path, size):
    local = os.path.join(FONTS, os.path.basename(path))
    if not os.path.exists(local):
        os.makedirs(FONTS, exist_ok=True)
        urllib.request.urlretrieve(FONT_URL + path, local)
    return ImageFont.truetype(local, size)


def room_lit():
    """The room as the page shows it once the tree lights are up (firelight half way)."""
    load = lambda name: np.asarray(Image.open(os.path.join(CABIN, name)).convert("RGB")).astype(np.float32) / 255
    base = load("cabin-low.jpg") * 0.5 + load("cabin-left.jpg") * 0.5
    a, b = load("cabin-glow-a.jpg"), load("cabin-glow-b.jpg")
    lit = 1 - (1 - base) * (1 - 0.72 * a) * (1 - 0.72 * b)
    return Image.fromarray((np.clip(lit, 0, 1) * 255).astype(np.uint8))


def main():
    card = room_lit().crop((0, 36, 1920, 1044)).resize((1200, 630), Image.LANCZOS)
    arr = np.asarray(card).astype(np.float32) / 255
    shade = (np.clip((np.arange(630) - 400) / 170, 0, 1) ** 1.3 * 0.88)[:, None, None]
    arr = arr * (1 - shade) + np.array([13, 10, 8]) / 255 * shade         # a dark band for the title
    card = Image.fromarray((arr * 255).astype(np.uint8))
    d = ImageDraw.Draw(card)
    d.text((48, 486), "LeMSIC Advent Calendar", font=font("alegreyasc/AlegreyaSC-Bold.ttf", 66), fill=(242, 236, 228))
    d.text((50, 562), "One ornament a day  ·  1–24 December", font=font("alegreyasans/AlegreyaSans-Medium.ttf", 30),
           fill=(242, 162, 79))
    card.save(os.path.join(ASSETS, "share-card.jpg"), quality=88)

    emblem = Image.open(os.path.join(ASSETS, "lemsic-emblem.png")).convert("RGB")
    w, h = emblem.size
    emblem.crop(((w - h) // 2, 0, (w - h) // 2 + h, h)).resize((180, 180), Image.LANCZOS).save(
        os.path.join(ASSETS, "icon-180.png"))
    emblem.crop((150, 90, 330, 270)).resize((64, 64), Image.LANCZOS).save(os.path.join(ASSETS, "icon-64.png"))
    print("wrote share-card.jpg, icon-64.png and icon-180.png in", os.path.relpath(ASSETS, ROOT))


if __name__ == "__main__":
    main()
