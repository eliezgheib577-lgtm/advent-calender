"""Cuts the LeMSIC Instagram profile's pieces (avatar, highlight covers, post tiles) out of two phone
screenshots of the profile, for the phone scene (tools/video/story.html):
    python3 tools/video/ig_crops.py <profile-top.png> <profile-grid.png>
Both are 1206 x 2622 iPhone screenshots: the first shows the header (avatar, highlights, first row of
posts), the second is scrolled to the grid. Writes build/video/ig/.
"""
import os
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "build", "video", "ig")
os.makedirs(OUT, exist_ok=True)
top, grid = (Image.open(p).convert("RGB") for p in sys.argv[1:3])


def disc(img, cx, cy, d, name, size=None):
    """A round crop, transparent outside the circle (drawn 4x and scaled down, for a smooth edge)."""
    r = d / 2
    c = img.crop((round(cx - r), round(cy - r), round(cx + r), round(cy + r))).convert("RGBA")
    m = Image.new("L", (c.width * 4, c.height * 4), 0)
    ImageDraw.Draw(m).ellipse((0, 0, m.width - 1, m.height - 1), fill=255)
    c.putalpha(m.resize(c.size, Image.LANCZOS))
    if size:
        c = c.resize((size, size), Image.LANCZOS)
    c.save(os.path.join(OUT, name))


disc(top, 176.5, 508.5, 256, "avatar.png", 512)
for i, (cx, name) in enumerate(zip((137.5, 383.5, 629.5, 875.5, 1121.5), ("scome", "scora", "score", "scoph", "scope"))):
    disc(top, cx, 1472.5, 156, f"hl-{name}.png", 312)
# the posts: 400 x 533 tiles, three across with 3 px gaps; rows start at y 490 / 1026 / 1562 in the scrolled shot
k = 0
for y in (490, 1026, 1562):
    for x in (0, 403, 806):
        grid.crop((x, y, x + 400, y + 533)).save(os.path.join(OUT, f"post-{k}.png"))
        k += 1
print("wrote", OUT)
