"""Mystery versions of the 24 day pictures, for the promo film (the real ones stay a surprise):
    python3 tools/video/mystery_cards.py [A|B]
Each keeps its day card's frame, snow, colour, gold dots and number (site/assets/days/day-NN.png), and
swaps the picture for a big gold "?"; version B also writes STAY TUNED above the number.
Writes build/video/mystery/day-NN.png (600 x 600); tools/video/record_site.js serves these in place
of the real pictures while it records.
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DAYS = os.path.join(ROOT, "site", "assets", "days")
OUT = os.path.join(ROOT, "build", "video", "mystery")
FONT = os.path.join(ROOT, "build", "fonts", "AlegreyaSC-Bold.ttf")
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(1224)
VARIANT = (sys.argv[1:] or ["A"])[0].upper()


def gold_text(card, text, size, cy, glow=0.0, track=0):
    """Gold lettering like the day numbers: light at the top, deeper below, with a dark drop shadow."""
    font = ImageFont.truetype(FONT, size)
    W, H = card.size
    mask = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(mask)
    widths = [d.textlength(ch, font=font) for ch in text]
    total = sum(widths) + track * (len(text) - 1)
    x = (W - total) / 2
    for ch, w in zip(text, widths):
        d.text((x, cy), ch, font=font, fill=255, anchor="lm")
        x += w + track
    if glow:
        halo = mask.filter(ImageFilter.GaussianBlur(size * 0.22)).point(lambda v: int(v * glow))
        card.alpha_composite(Image.merge("RGBA", (Image.new("L", (W, H), 255), Image.new("L", (W, H), 214),
                                                   Image.new("L", (W, H), 140), halo)))
    shadow = mask.filter(ImageFilter.GaussianBlur(3)).point(lambda v: int(v * 0.8))
    card.alpha_composite(Image.merge("RGBA", (Image.new("L", (W, H), 30), Image.new("L", (W, H), 12),
                                               Image.new("L", (W, H), 6), shadow)), (3, 5))
    bbox = mask.getbbox()
    y0, y1 = bbox[1], bbox[3]
    t = np.clip((np.arange(H) - y0) / max(1, y1 - y0), 0, 1)[:, None]
    top, bot = np.array([252, 226, 140]), np.array([196, 142, 40])
    grad = (top * (1 - t)[..., None] + bot * t[..., None]).astype(np.uint8)
    grad = np.broadcast_to(grad, (H, W, 3)).copy()
    card.alpha_composite(Image.merge("RGBA", (*Image.fromarray(grad).split(), mask)))


def cream_text(card, text, size, cy, track=4):
    font = ImageFont.truetype(FONT, size)
    d = ImageDraw.Draw(card)
    widths = [d.textlength(ch, font=font) for ch in text]
    x = (card.width - sum(widths) - track * (len(text) - 1)) / 2
    for ch, w in zip(text, widths):
        d.text((x, cy), ch, font=font, fill=(246, 236, 214, 235), anchor="lm")
        x += w + track


for day in range(1, 25):
    card = Image.open(os.path.join(DAYS, f"day-{day:02d}.png")).convert("RGBA")
    a = np.asarray(card).astype(float)
    # the background's colour row by row, from the plain strips either side of the picture
    sides = np.concatenate([a[:, 70:170, :3], a[:, 440:520, :3]], axis=1)
    row = np.median(sides, axis=1)
    bg = np.broadcast_to(row[:, None, :], a[:, :, :3].shape)
    # paint it over the picture only (feathered; the number below stays), and scatter a few snowflakes back in
    m = Image.new("L", card.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((130, 100, 470, 418), radius=60, fill=255)
    m = np.asarray(m.filter(ImageFilter.GaussianBlur(10))).astype(float)[..., None] / 255
    m[:96] = 0                                   # leave the snow along the top as it is
    a[:, :, :3] = a[:, :, :3] * (1 - m) + bg * m
    card = Image.fromarray(a.clip(0, 255).astype(np.uint8), "RGBA")
    d = ImageDraw.Draw(card)
    n = 0
    while n < 9:                                 # (none on the lettering)
        x, y, r = rng.uniform(150, 450), rng.uniform(125, 400), rng.uniform(1.5, 4)
        if abs(x - 300) < 80 and 150 < y < 400:
            continue
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, int(rng.uniform(40, 110))))
        n += 1
    if VARIANT == "B":
        gold_text(card, "?", 250, 236, glow=0.55)
        cream_text(card, "STAY TUNED", 34, 392, track=4)
    else:
        gold_text(card, "?", 290, 262, glow=0.55)
    card.save(os.path.join(OUT, f"day-{day:02d}.png"))
print("wrote", OUT)
