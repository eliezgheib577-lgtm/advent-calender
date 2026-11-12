#!/usr/bin/env python3
"""Make the printed sheet on the clipboard in the cabin ("How it works").

    python3 tools/blender/make_clipboard_sheet.py        (needs Pillow and numpy)

Writes tools/blender/textures/clipboard-sheet.png. In the room the sheet is small, so it only has
to read as a printed page of instructions: the heading, the emblem, and five numbered steps.
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from make_share_card import font  # noqa: E402  (downloads the Alegreya fonts once)

W, H = 900, 1240
STEPS = [
    "Find today's ornament: it has a little gift tag saying “Today”.",
    "Tap it, and a picture pops out.",
    "Hang it on your wall, in its numbered frame.",
    "Come back every day: each ornament opens only on its own day.",
    "Hang all 24 pictures to win the LeMSIC prize!",
]


def wrap(draw, text, fnt, width):
    lines, line = [], ""
    for word in text.split():
        trial = (line + " " + word).strip()
        if draw.textlength(trial, font=fnt) <= width:
            line = trial
        else:
            lines.append(line)
            line = word
    return lines + [line]


def main():
    rng = np.random.default_rng(12)
    paper = np.ones((H, W, 3)) * np.array([0.95, 0.92, 0.85])
    paper *= 1 - 0.035 * rng.random((H, W, 1))                       # a little fibre
    img = Image.fromarray((paper * 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    ink, accent = (40, 30, 22), (150, 70, 20)
    emblem = Image.open(os.path.join(ROOT, "site", "assets", "lemsic-emblem.png")).convert("RGB")
    ew, eh = emblem.size
    emblem = emblem.crop(((ew - eh) // 2, 0, (ew - eh) // 2 + eh, eh)).resize((150, 150), Image.LANCZOS)
    mask = Image.new("L", (150, 150), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 149, 149), fill=255)
    img.paste(emblem, (W // 2 - 75, 70), mask)
    title = font("alegreyasc/AlegreyaSC-Bold.ttf", 92)
    d.text((W // 2, 300), "How it works", font=title, fill=ink, anchor="mm")
    d.line((140, 370, W - 140, 370), fill=accent, width=4)
    num, body = font("alegreyasc/AlegreyaSC-Bold.ttf", 64), font("alegreyasans/AlegreyaSans-Medium.ttf", 42)
    y = 420
    for k, step in enumerate(STEPS, 1):
        d.text((110, y - 6), str(k), font=num, fill=accent)
        for line in wrap(d, step, body, W - 280):
            d.text((190, y), line, font=body, fill=ink)
            y += 52
        y += 28
    d.text((W // 2, H - 70), "Merry Christmas from LeMSIC", font=font("alegreyasans/AlegreyaSans-Medium.ttf", 40),
           fill=accent, anchor="mm")
    out = os.path.join(HERE, "textures", "clipboard-sheet.png")
    img.save(out)
    print("wrote", os.path.relpath(out, ROOT))


if __name__ == "__main__":
    main()
