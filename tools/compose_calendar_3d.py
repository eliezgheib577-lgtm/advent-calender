#!/usr/bin/env python3
"""Put the Blender-rendered tree onto the LeMSIC calendar card.

Needs images/render/lemsic-tree.png and images/render/ornaments.json
(made by tools/blender/lemsic_tree.py).

Writes:
  images/render/lemsic-tree-glow.png      the render with a soft glow on lights and star
  images/lemsic-tree-calendar-3d.svg      the full calendar card (rasterise with tools/render_png.js)
  images/render/calendar-hotspots.json    where each ornament sits on the card

Run:  python3 tools/compose_calendar_3d.py
"""
import json
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_doors import GOLD, sparkle  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, "images")
RENDER = os.path.join(IMG, "render")

BLUE = "#3C6BAD"
WHITE = "#FFFFFF"
SANS = "'Avenir Next', 'Segoe UI', Inter, 'Helvetica Neue', Arial, sans-serif"

W, H = 1800, 2200
CX = W / 2
TREE_W = 1380                       # width of the tree image on the card
TREE_Y = 250


def add_glow(src, dst):
    """Bloom: blur the brightest pixels (fairy lights, star, highlights) and add them back."""
    im = Image.open(src).convert("RGBA")
    a = np.asarray(im).astype(np.float32) / 255
    rgb, alpha = a[..., :3], a[..., 3:4]
    lum = (rgb * [0.2126, 0.7152, 0.0722]).sum(-1, keepdims=True)
    bright = np.clip((lum - 0.80) / 0.2, 0, 1) * rgb * alpha
    b8 = Image.fromarray((bright * 255).astype(np.uint8))
    glow = sum(np.asarray(b8.filter(ImageFilter.GaussianBlur(r))).astype(np.float32) / 255 * w
               for r, w in ((4, 0.9), (12, 0.8), (30, 0.6)))
    glow *= np.array([1.0, 0.85, 0.62])            # warm the glow
    prem = rgb * alpha + glow
    g_a = np.clip(glow.max(-1, keepdims=True), 0, 1)
    out_a = np.clip(alpha + g_a * (1 - alpha), 0, 1)
    out_rgb = np.clip(prem / np.maximum(out_a, 1e-4), 0, 1)
    out = np.concatenate([out_rgb, out_a], -1)
    Image.fromarray((out * 255).round().astype(np.uint8)).save(dst)
    return im.size


def laurel(side, cx, cy, r, a0, a1, n):
    leaves = []
    for k in range(n):
        a = a0 + (a1 - a0) * k / (n - 1)
        ar = math.radians(a)
        if side == "left":
            x, rot = cx + r * math.cos(ar), a + 180
        else:
            x, rot = cx - r * math.cos(ar), 180 - a
        y = cy + r * math.sin(ar)
        s = 1.15 - 0.35 * k / (n - 1)
        leaves.append(f'<g transform="translate({x:.1f} {y:.1f}) rotate({rot:.1f}) scale({s:.2f})">'
                      f'<path d="M0 0 L-16 -26 L-8 -28 L0 -12 L8 -28 L16 -26Z" fill="{WHITE}"/></g>')
    return "".join(leaves)


def main():
    src = os.path.join(RENDER, "lemsic-tree.png")
    rw, rh = add_glow(src, os.path.join(RENDER, "lemsic-tree-glow.png"))
    tree_h = TREE_W * rh / rw
    tree_x = CX - TREE_W / 2

    rnd = random.Random(1964)
    snow = "".join(
        f'<circle cx="{rnd.uniform(60, W - 60):.0f}" cy="{rnd.uniform(60, H - 60):.0f}" '
        f'r="{rnd.choice([1.5, 2, 2.5, 3.2])}" fill="#fff" opacity="{rnd.uniform(0.15, 0.5):.2f}"/>'
        for _ in range(190))
    twinkles = "".join(sparkle(round(rnd.choice([rnd.uniform(90, 420), rnd.uniform(1380, W - 90)])),
                               round(rnd.uniform(160, 1500)), rnd.choice([5, 6, 8]), WHITE) for _ in range(14))
    arc_cy, r_out, r_in = 1150, 950, 880

    def arc(r):
        return f"M{CX - r} {arc_cy} A{r} {r} 0 0 1 {CX + r} {arc_cy}"

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="LeMSIC Advent Calendar">
  <title>LeMSIC Advent Calendar</title>
  <defs>
    <linearGradient id="frame" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#7A4A22"/><stop offset="0.5" stop-color="#5A3517"/><stop offset="1" stop-color="#3A210D"/>
    </linearGradient>
    <radialGradient id="glow" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="#6E9BDA" stop-opacity="0.5"/><stop offset="0.6" stop-color="#6E9BDA" stop-opacity="0.18"/>
      <stop offset="1" stop-color="#6E9BDA" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="vig" cx="0.5" cy="0.45" r="0.75">
      <stop offset="0.6" stop-color="#0A1A33" stop-opacity="0"/><stop offset="1" stop-color="#0A1A33" stop-opacity="0.5"/>
    </radialGradient>
    <radialGradient id="floor" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="#0A1A33" stop-opacity="0.45"/><stop offset="1" stop-color="#0A1A33" stop-opacity="0"/>
    </radialGradient>
    <path id="arcOut" d="{arc(r_out)}"/>
    <path id="arcIn" d="{arc(r_in)}"/>
  </defs>

  <rect width="{W}" height="{H}" rx="30" fill="url(#frame)"/>
  <rect x="14" y="14" width="{W - 28}" height="{H - 28}" rx="22" fill="none" stroke="#9A6532" stroke-width="3" opacity="0.6"/>
  <rect x="40" y="40" width="{W - 80}" height="{H - 80}" rx="14" fill="{BLUE}"/>
  <ellipse cx="{CX}" cy="{TREE_Y + tree_h * 0.55:.0f}" rx="{TREE_W * 0.62:.0f}" ry="{tree_h * 0.55:.0f}" fill="url(#glow)"/>
  {snow}
  {twinkles}

  <text font-family="{SANS}" font-weight="600" font-size="66" letter-spacing="8" fill="{WHITE}">
    <textPath href="#arcOut" startOffset="50%" text-anchor="middle">LeMSIC Advent Calendar</textPath>
  </text>
  <text font-family="{SANS}" font-size="28" letter-spacing="9" fill="{WHITE}" opacity="0.92">
    <textPath href="#arcIn" startOffset="50%" text-anchor="middle">1 – 24 december 2026</textPath>
  </text>

  {laurel("left", CX, 1300, 880, 160, 122, 13)}
  {laurel("right", CX, 1300, 880, 160, 122, 13)}

  <ellipse cx="{CX}" cy="{TREE_Y + tree_h * 0.945:.0f}" rx="{TREE_W * 0.42:.0f}" ry="44" fill="url(#floor)"/>
  <image href="render/lemsic-tree-glow.png" x="{tree_x:.0f}" y="{TREE_Y}" width="{TREE_W}" height="{tree_h:.0f}"/>

  <text x="{CX}" y="{H - 170}" text-anchor="middle" font-family="{SANS}" font-size="64" letter-spacing="3" fill="{WHITE}">LeMSIC</text>
  <text x="{CX}" y="{H - 118}" text-anchor="middle" font-family="{SANS}" font-size="24" letter-spacing="8" fill="{WHITE}" opacity="0.85">OPEN ONE ORNAMENT EACH DAY</text>

  <rect x="40" y="40" width="{W - 80}" height="{H - 80}" rx="14" fill="url(#vig)"/>
  <rect x="40" y="40" width="{W - 80}" height="{H - 80}" rx="14" fill="none" stroke="{GOLD}" stroke-width="4"/>
</svg>
"""
    with open(os.path.join(IMG, "lemsic-tree-calendar-3d.svg"), "w") as f:
        f.write(svg)

    with open(os.path.join(RENDER, "ornaments.json")) as f:
        spots = json.load(f)["ornaments"]
    hot = [{"day": s["day"],
            "x": round((tree_x + s["x"] * TREE_W) / W, 4),
            "y": round((TREE_Y + s["y"] * tree_h) / H, 4),
            "r": round(s["r"] * TREE_W / W, 4)} for s in spots]
    with open(os.path.join(RENDER, "calendar-hotspots.json"), "w") as f:
        json.dump({"image": "png/lemsic-tree-calendar-3d.png", "width": W, "height": H,
                   "note": "x, y and r are fractions of the card width/height (y from the top, r of the width)",
                   "ornaments": hot}, f, indent=1)
    print("wrote lemsic-tree-calendar-3d.svg, lemsic-tree-glow.png and calendar-hotspots.json")


if __name__ == "__main__":
    main()
