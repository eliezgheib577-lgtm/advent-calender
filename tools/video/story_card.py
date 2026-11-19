"""The Instagram story in the phone scene: LeMSIC's Canva design, cut out of a phone screenshot of the
Canva editor, cleaned and scaled to a 1080 x 1920 story:
    python3 tools/video/story_card.py <canva-screenshot.png>
The design sits at (187, 381)-(1019, 1860) of the 1206 x 2622 screenshot. Takes out Canva's comment
bubble (bottom left, over the red banner's top edge) and the "sticker link" placeholder (story.html
puts the real ENTER THE CABIN link sticker there). Writes build/video/ig/story-card.png.
"""
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "build", "video", "ig")
os.makedirs(OUT, exist_ok=True)
img = Image.open(sys.argv[1]).convert("RGB").crop((187, 381, 1019, 1860))
a = np.asarray(img).astype(float)
h, w = a.shape[:2]
RED = np.array([181, 39, 27], float)            # the banner, one flat colour
BANNER_TOP = 1064
yy, xx = np.mgrid[0:h, 0:w]

# Canva's comment bubble: a round bubble with a tail, and a red dot on its rim (plus a few pixels of edge)
pin = ((xx - 68.3) ** 2 + (yy - 1027.3) ** 2 < 58 ** 2) | ((xx - 107.7) ** 2 + (yy - 988.7) ** 2 < 20 ** 2) \
    | ((xx >= 90) & (xx <= 122) & (yy >= 1050) & (yy <= 1082))
# where it covers the banner, the banner's red
a[pin & (yy >= BANNER_TOP)] = RED
# where it covers the cream background (and a lamp's soft glow), fill smoothly from the pixels around it
hole = pin & (yy < BANNER_TOP)
y0, y1, x0, x1 = 955, BANNER_TOP, 0, 140
sub = a[y0:y1, x0:x1].copy()
m = hole[y0:y1, x0:x1]
sub[m] = sub[~m].mean(0)
for _ in range(4000):                           # Laplace fill: each hole pixel becomes the mean of its neighbours
    p = np.pad(sub, ((1, 1), (1, 1), (0, 0)), mode="edge")
    avg = (p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:]) / 4
    sub[m] = avg[m]
a[y0:y1, x0:x1] = sub

# the "sticker link" placeholder pill: banner red underneath
a[1190:1266, 344:488] = RED

out = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).resize((1080, 1920), Image.LANCZOS)
out.save(os.path.join(OUT, "story-card.png"))
print("wrote", os.path.join(OUT, "story-card.png"))
