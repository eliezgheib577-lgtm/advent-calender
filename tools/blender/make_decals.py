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
