#!/usr/bin/env python3
"""Make the number textures printed on the 3D ornaments (white digits on transparent).

Run:  python3 tools/blender/make_decals.py      (needs Pillow)
"""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "decals")
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
SIZE = 512

os.makedirs(OUT, exist_ok=True)
for day in range(1, 25):
    img = Image.new("RGBA", (SIZE, SIZE), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)
    text = str(day)
    # pick the largest font that fits 78% of the width / 62% of the height
    fs = 400
    while True:
        font = ImageFont.truetype(FONT, fs)
        l, t, r, b = d.textbbox((0, 0), text, font=font)
        if r - l <= SIZE * 0.78 and b - t <= SIZE * 0.62:
            break
        fs -= 6
    x = (SIZE - (r - l)) / 2 - l
    y = (SIZE - (b - t)) / 2 - t
    d.text((x, y), text, font=font, fill=(255, 255, 255, 255))
    img.save(os.path.join(OUT, f"num-{day:02d}.png"))
print("decals written to", OUT)

# edged numbers: the digits in red and the digits grown by a thin edge in green, on black
# (lemsic_tree.edged_decal_material paints the edge in a colour that stands out on the ornament)
EDGE = 15
for day in range(1, 25):
    text = str(day)
    probe = ImageDraw.Draw(Image.new("L", (SIZE, SIZE)))
    fs = 400
    while True:
        font = ImageFont.truetype(FONT, fs)
        l, t, r, b = probe.textbbox((0, 0), text, font=font, stroke_width=EDGE)
        if r - l <= SIZE * 0.80 and b - t <= SIZE * 0.66:
            break
        fs -= 6
    x = (SIZE - (r - l)) / 2 - l
    y = (SIZE - (b - t)) / 2 - t
    fill = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(fill).text((x, y), text, font=font, fill=255)
    edge = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(edge).text((x, y), text, font=font, fill=255, stroke_width=EDGE, stroke_fill=255)
    Image.merge("RGB", (fill, edge, Image.new("L", (SIZE, SIZE), 0))).save(
        os.path.join(OUT, f"edged-{day:02d}.png"))
print("edged decals written to", OUT)
