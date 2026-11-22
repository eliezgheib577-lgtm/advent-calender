"""Puts the LeMSIC promo film together: renders, website recordings, titles, snow and smoke.

    python3 tools/video/compose.py [--preview] [--frames=A-B] [--tag=NAME]

Reads build/video/{exterior,site,story,phone,wheel} and build/video/vo/timing.json (the narration),
writes build/video/out/picture.mp4 (no sound) and build/video/out/cues.json (where each narration
line and each sound effect goes, for tools/video/audio.py). 1920 x 1080, 24 frames a second.
"""
import bisect
import functools
import json
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
B = os.path.join(ROOT, "build", "video")
ARGS = sys.argv[1:]
PREVIEW = "--preview" in ARGS
W, H = (960, 540) if PREVIEW else (1920, 1080)
FPS = 24
FONT_T = os.path.join(ROOT, "build", "fonts", "AlegreyaSC-Bold.ttf")
FONT_B = os.path.join(ROOT, "build", "fonts", "AlegreyaSans-Medium.ttf")
CREAM = (246, 237, 220)
GOLD = (242, 194, 122)


# ---------------------------------------------------------------- small helpers
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def smooth(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease_out(x, p=3):
    return 1 - (1 - clamp(x)) ** p


def lerp(a, b, u):
    return a + (b - a) * u


def keys(t, ks, f=smooth):
    """Interpolate a value (number or tuple) through (time, value) keys, eased between them."""
    if t <= ks[0][0]:
        return ks[0][1]
    for (t0, v0), (t1, v1) in zip(ks, ks[1:]):
        if t <= t1:
            u = f((t - t0) / max(t1 - t0, 1e-6))
            if isinstance(v0, tuple):
                return tuple(lerp(a, b, u) for a, b in zip(v0, v1))
            return lerp(v0, v1, u)
    return ks[-1][1]


def warp(t, anchors):
    """Piecewise-linear time map through (out, in) anchor pairs."""
    xs = [a for a, _ in anchors]
    ys = [b for _, b in anchors]
    return float(np.interp(t, xs, ys))


@functools.lru_cache(maxsize=48)
def load(path, size=None):
    im = Image.open(path).convert("RGB")
    if size and im.size != size:
        im = im.resize(size, Image.LANCZOS)
    return im


@functools.lru_cache(maxsize=16)
def load_rgba(path):
    return Image.open(path).convert("RGBA")


@functools.lru_cache(maxsize=32)
def font(path, size):
    return ImageFont.truetype(path, size)


def camera(img, cx, cy, zoom):
    """The part of img around (cx, cy) (its pixels), zoom times closer than the whole frame, at W x H."""
    iw, ih = img.size
    vw = iw / zoom
    vh = vw * H / W
    x0, y0 = cx - vw / 2, cy - vh / 2
    x0 = clamp(x0, 0, iw - vw)
    y0 = clamp(y0, 0, ih - vh)
    return img.transform((W, H), Image.EXTENT, (x0, y0, x0 + vw, y0 + vh), Image.BICUBIC)


def crossfade(a, b, u):
    return Image.blend(a, b, clamp(u)) if 0 < u < 1 else (b if u >= 1 else a)


def fade_black(img, u):
    return ImageEnhance.Brightness(img).enhance(clamp(u)) if u < 1 else img


# ---------------------------------------------------------------- the sources
EXT_DIR = os.path.join(B, "exterior")
EXT = json.load(open(os.path.join(EXT_DIR, "exterior.json")))
EXT_HAVE = sorted(int(f[:4]) for f in os.listdir(EXT_DIR) if f[:4].isdigit() and f.endswith(".png") and "-" not in f)


PRE_DIR = os.path.join(B, "exterior-preview")
PRE_HAVE = sorted(int(f[:4]) for f in os.listdir(PRE_DIR) if f[:4].isdigit() and f.endswith(".png")) if os.path.isdir(PRE_DIR) else []


def ext_frame(fi):
    """The forest flight at (fractional) frame fi, blended between neighbours. Frames not rendered yet
    come from the rough preview pass (every 4th frame, blended), so the film can be previewed early."""
    def one(k):
        k = int(clamp(k, 0, EXT["frames"] - 1))
        interp = os.path.join(B, "exterior-interp", f"{k:04d}.png")
        if k not in EXT_HAVE and os.path.exists(interp):            # an in-between frame made by interpolation
            return load(interp, (W, H))
        if k in EXT_HAVE or not PRE_HAVE:
            if k not in EXT_HAVE:
                j = bisect.bisect_left(EXT_HAVE, k)
                k = EXT_HAVE[min(j, len(EXT_HAVE) - 1)] if EXT_HAVE else 0
            return load(os.path.join(EXT_DIR, f"{k:04d}.png"), (W, H))
        j = bisect.bisect_right(PRE_HAVE, k) - 1
        a_, b_ = PRE_HAVE[max(j, 0)], PRE_HAVE[min(j + 1, len(PRE_HAVE) - 1)]
        pa = load(os.path.join(PRE_DIR, f"{a_:04d}.png"), (W, H))
        if b_ == a_:
            return pa
        return Image.blend(pa, load(os.path.join(PRE_DIR, f"{b_:04d}.png"), (W, H)), (k - a_) / (b_ - a_))
    a = int(math.floor(fi))
    u = fi - a
    if u < 0.02:
        return one(a)
    return Image.blend(one(a), one(a + 1), u)


SITE = {}


def site_frame(clip, t):
    if clip not in SITE:
        tt = json.load(open(os.path.join(B, "site", clip, "times.json")))
        SITE[clip] = ([x[1] for x in tt], [x[0] for x in tt])
    ts, names = SITE[clip]
    i = max(0, bisect.bisect_right(ts, t) - 1)
    return load(os.path.join(B, "site", clip, names[i]))


def site_len(clip):
    site_frame(clip, 0)
    return SITE[clip][0][-1]


STAGE = (960, 502, 1920 / 1785)          # the site's scene area (above its title bar), filling the frame


def site_view(clip, t, cx=None, cy=None, zoom=1.0):
    """A recorded website frame through the film's camera (its own pixels, 1920 x 1080)."""
    img = site_frame(clip, t)
    return camera(img, cx if cx is not None else STAGE[0], cy if cy is not None else STAGE[1], STAGE[2] * zoom)


# ---------------------------------------------------------------- snow and smoke
RNG = np.random.default_rng(1225)
FLAKES = RNG.random((420, 5))            # x, y, depth, sway phase, size jitter


def snow(img, t, amount=1.0, wind=0.04):
    """Falling snow in front of everything: near flakes big, soft and fast; far ones fine and slow."""
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    s = W / 1920
    n = int(len(FLAKES) * amount)
    for x, y, z, ph, j in FLAKES[:n]:
        depth = 0.25 + 0.75 * z * z
        speed = 0.05 + 0.13 * depth
        yy = ((y + t * speed) % 1.1) - 0.05
        xx = (x + t * wind * depth + 0.012 * depth * math.sin(t * 1.3 + ph * 6.3)) % 1.04 - 0.02
        r = (0.8 + 4.2 * depth ** 2 * (0.7 + 0.6 * j)) * s
        a = int(150 + 90 * (1 - depth)) if depth < 0.8 else int(110)
        d.ellipse((xx * W - r, yy * H - r, xx * W + r, yy * H + r), fill=(240, 244, 255, a))
    lay = lay.filter(ImageFilter.GaussianBlur(1.1 * s))
    out = img.convert("RGBA")
    out.alpha_composite(lay)
    return out.convert("RGB")


PUFFS = RNG.random((26, 4))


def smoke(img, fi, t):
    """Wood smoke rising from the chimney (where it is in this frame of the flight), drifting with the wind."""
    k = int(clamp(round(fi), 0, EXT["frames"] - 1))
    c = EXT["chimney"][k]
    if c["depth"] <= 0 or not (-0.2 < c["x"] < 1.2 and -0.3 < c["y"] < 1.2):
        return img
    m = c["metre"] * H                    # pixels per metre at the chimney
    if m < 0.6:
        return img
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for a, b, cc, dd in PUFFS:
        age = (t * 0.22 + a) % 1.0                     # each puff takes ~4.5 s to rise and fade
        rise = 0.3 + 4.2 * age
        x = c["x"] * W + m * (0.9 * age * age * 2.2 + 0.25 * math.sin(age * 7 + b * 6)) + m * 0.15 * (cc - 0.5)
        y = c["y"] * H - m * rise
        r = m * (0.18 + 0.85 * age)
        alpha = int(70 * (1 - age) ** 1.4 * min(1, age * 8))
        g = int(150 + 40 * dd)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(g, g + 6, g + 16, alpha))
    lay = lay.filter(ImageFilter.GaussianBlur(max(1.0, m * 0.18)))
    out = img.convert("RGBA")
    out.alpha_composite(lay)
    return out.convert("RGB")


# ---------------------------------------------------------------- titles
def text_layer(lines, centre_y, alpha=1.0, glow=True):
    """Lines of (text, font path, size at 1080p, colour), centred, with a soft shadow and warm glow."""
    s = H / 1080
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    heights = [int(sz * s * 1.18) for _, _, sz, _ in lines]
    y = centre_y * H - sum(heights) / 2
    boxes = []
    for (txt, fp, sz, col), h in zip(lines, heights):
        f = font(fp, max(8, int(sz * s)))
        wdt = d.textlength(txt, font=f)
        boxes.append((txt, f, (W - wdt) / 2, y, col))
        y += h
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    for txt, f, x, yy, col in boxes:
        sd.text((x, yy + 3 * s), txt, font=f, fill=(0, 0, 0, 200))
    shadow = shadow.filter(ImageFilter.GaussianBlur(7 * s))
    lay.alpha_composite(shadow)
    if glow:
        gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(gl)
        for txt, f, x, yy, col in boxes:
            gd.text((x, yy), txt, font=f, fill=(255, 190, 110, 150))
        lay.alpha_composite(gl.filter(ImageFilter.GaussianBlur(14 * s)))
    for txt, f, x, yy, col in boxes:
        d.text((x, yy), txt, font=f, fill=col + (255,))
    if alpha < 1:
        a = lay.getchannel("A").point(lambda v: int(v * clamp(alpha)))
        lay.putalpha(a)
    return lay


def with_text(img, lines, centre_y, alpha):
    if alpha <= 0.003:
        return img
    out = img.convert("RGBA")
    out.alpha_composite(text_layer(lines, centre_y, alpha))
    return out.convert("RGB")


def flash(img, u, centre=(0.5, 0.5)):
    """A warm magical burst of light (u: 0 none .. 1 full white-gold)."""
    if u <= 0:
        return img
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.hypot(xx / W - centre[0], (yy / H - centre[1]) * H / W)
    glow = np.clip(1 - r / (0.15 + 1.2 * u), 0, 1) ** 1.5 * clamp(u * 1.6)
    a = np.asarray(img).astype(np.float32)
    tint = np.array([255, 238, 205], np.float32)
    out = a + (tint - a) * glow[..., None]
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


# ---------------------------------------------------------------- the phone and its story
PHONE = json.load(open(os.path.join(B, "phone", "phone.json")))


def homography(src, dst):
    """Coefficients mapping dst (output) points to src (image) points, for Image.transform PERSPECTIVE."""
    A, bb = [], []
    for (x, y), (u, v) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); bb.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); bb.append(v)
    return np.linalg.solve(np.array(A, float), np.array(bb, float))


@functools.lru_cache(maxsize=2)
def rounded_mask(sw, sh):
    r = PHONE.get("corner", 0.0) * sw
    m = Image.new("L", (sw, sh), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, sw - 1, sh - 1), radius=int(r), fill=255)
    return m


def phone_shot(story_t, cx, cy, zoom):
    """The phone on its stand, the story on its screen, through the camera (cx, cy in the 4K still's pixels)."""
    ph = load(os.path.join(B, "phone", "phone.png"))
    pw, phh = ph.size
    view = camera(ph, cx, cy, zoom)
    vw = pw / zoom
    vh = vw * H / W
    x0 = clamp(cx - vw / 2, 0, pw - vw)
    y0 = clamp(cy - vh / 2, 0, phh - vh)
    sc = W / vw
    quad = [((qx * pw - x0) * sc, (qy * phh - y0) * sc) for qx, qy in PHONE["screen"]]
    k = int(clamp(story_t * 24, 0, 383))
    story = load(os.path.join(B, "story", f"{k:04d}.png"))
    sw, sh = story.size
    coef = homography([(0, 0), (sw, 0), (sw, sh), (0, sh)], quad)
    warped = story.transform((W, H), Image.PERSPECTIVE, tuple(coef), Image.BICUBIC)
    mask = rounded_mask(sw, sh).transform((W, H), Image.PERSPECTIVE, tuple(coef), Image.BILINEAR)   # the screen's round corners
    # the screen glows a little and catches a soft reflection
    warped = ImageEnhance.Brightness(warped).enhance(0.93)
    view.paste(warped, (0, 0), mask)
    return view, quad


# ---------------------------------------------------------------- the wheel
WHEEL = json.load(open(os.path.join(B, "wheel", "wheel.json")))


def wheel_layers():
    return {n: load_rgba(os.path.join(B, "wheel", n + ".png")).resize((W, H), Image.LANCZOS) for n in ("disc", "frame", "float-a", "float-b", "gift")}


@functools.lru_cache(maxsize=1)
def wheel_cached():
    return wheel_layers()


SPIN = 5 * 360 + 97.5                    # five turns, stopping with a segment centred under the pointer


_SU = np.linspace(0, 1, 4001)
_SV = np.clip(_SU / 0.08, 0, 1) ** 2 * (3 - 2 * np.clip(_SU / 0.08, 0, 1)) * (1 - _SU) ** 2.2
_SA = np.concatenate([[0], np.cumsum((_SV[1:] + _SV[:-1]) / 2)])
_SA /= _SA[-1]


def spin_angle(u):
    return SPIN * float(np.interp(clamp(u), _SU, _SA))


def place(lay, base, scale, dx=0.0, dy=0.0, alpha=1.0, centre=(0.5, 0.54)):
    """Paste a full-frame RGBA layer scaled about centre and shifted (fractions of the frame)."""
    if alpha <= 0.003:
        return base
    l2 = lay
    if abs(scale - 1) > 1e-3:
        w2, h2 = int(W * scale), int(H * scale)
        l2 = lay.resize((w2, h2), Image.BICUBIC)
        cxp, cyp = centre[0] * W, centre[1] * H
        ox, oy = int(cxp - cxp * scale + dx * W), int(cyp - cyp * scale + dy * H)
    else:
        ox, oy = int(dx * W), int(dy * H)
    if alpha < 1:
        l2 = l2.copy()
        l2.putalpha(l2.getchannel("A").point(lambda v: int(v * alpha)))
    out = base.convert("RGBA")
    out.alpha_composite(l2, (max(0, ox), max(0, oy)), (max(0, -ox), max(0, -oy)))
    return out.convert("RGB")


def spun_disc(disc, angle, dangle):
    """The disc turned by angle (degrees, counter-clockwise), blurred along the turn by dangle."""
    c = (WHEEL["centre"][0] * W, WHEEL["centre"][1] * H)
    n = int(clamp(abs(dangle) / 2.0, 1, 10))
    if n <= 1:
        return disc.rotate(angle, Image.BICUBIC, center=c)
    acc = None
    for i in range(n):
        im = disc.rotate(angle - dangle * i / n, Image.BICUBIC, center=c)
        acc = np.asarray(im).astype(np.float32) if acc is None else acc + np.asarray(im)
    return Image.fromarray((acc / n).astype(np.uint8), "RGBA")


# ---------------------------------------------------------------- the film's look
GRAIN = [RNG.normal(0, 1, (H // 2, W // 2)).astype(np.float32) for _ in range(6)]
YY, XX = np.mgrid[0:H, 0:W]
VIGNETTE = (1 - 0.32 * np.clip((np.hypot((XX - W / 2) / (W / 2), (YY - H / 2) / (H / 2)) - 0.45) / 0.9, 0, 1) ** 1.6).astype(np.float32)


def finish(img, k):
    a = np.asarray(img).astype(np.float32)
    a *= VIGNETTE[..., None]
    g = GRAIN[k % len(GRAIN)]
    g = np.repeat(np.repeat(g, 2, 0), 2, 1)[:H, :W]
    a += g[..., None] * 3.2
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


# ---------------------------------------------------------------- the timeline (from the narration)
VO = json.load(open(os.path.join(B, "vo", "timing.json")))
PLAN = {   # scene: (lead-in before the first line, gap between lines, tail after the last)
    "s1": (1.8, 0.55, 0.9), "s2": (0.5, 0.45, 0.7), "s3": (2.0, 0.5, 2.6), "s4": (0.4, 0.45, 0.7),
    "s5": (0.5, 0.45, 1.0), "s6": (0.3, 0.5, 1.9), "s7": (0.6, 0.45, 1.6), "s8": (0.9, 0.55, 3.6)}


def build_timeline():
    t = 0.0
    scenes, lines = {}, []
    for sc in ("s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8"):
        lead, gap, tail = PLAN[sc]
        names = sorted((n for n in VO["lines"] if n.startswith(sc + "-")), key=lambda n: int(n.split("-")[1]))
        cur = lead
        ls = []
        for n in names:
            ls.append((cur, cur + VO["lines"][n]))
            lines.append({"name": n, "at": round(t + cur, 3)})
            cur += VO["lines"][n] + gap
        dur = cur - gap + tail
        scenes[sc] = {"start": t, "dur": dur, "lines": ls}
        t += dur
    return scenes, lines, t


SC, LINES, TOTAL = build_timeline()
CUES = []


def cue(name, at):
    CUES.append({"sfx": name, "at": round(at, 3)})


# ---------------------------------------------------------------- the scenes (tau: seconds into the scene)
def s1(tau, sc):
    d = sc["dur"]
    u = tau / d
    fi = 258 * (0.55 * u + 0.45 * u * u)
    img = ext_frame(fi)
    img = smoke(img, fi, sc["start"] + tau)
    img = snow(img, sc["start"] + tau, 0.85)
    l2s, l2e = sc["lines"][2]
    a = smooth((tau - l2s + 0.2) / 0.8) * (1 - smooth((tau - d + 0.5) / 0.5))
    img = with_text(img, [("LeMSIC", FONT_T, 120, CREAM), ("Christmas Advent Calendar", FONT_T, 64, GOLD)], 0.3, a)
    return fade_black(img, min(tau / 1.0, (d - tau) / 0.5))


def s2(tau, sc):
    d = sc["dur"]
    (a0, b0), (a1, b1), (a2, b2) = sc["lines"]
    st = warp(tau, [(0, 0), (max(0.6, b0 - 0.3), 3.0), (a1 + 0.2, 4.3), (a2 - 0.1, 10.3), (a2 + 0.6 * (b2 - a2), 12.6), (d, 14.6)])
    pw, phh = load(os.path.join(B, "phone", "phone.png")).size
    q = PHONE["screen"]
    scx = (q[0][0] + q[1][0] + q[2][0] + q[3][0]) / 4 * pw
    scy = (q[0][1] + q[1][1] + q[2][1] + q[3][1]) / 4 * phh
    # where the link sticker's centre sits in the 4K still: story coords (540, 1727) of 1080 x 2340 (see the
    # sticker and the tap in story.html), through the screen's perspective
    g = homography([(qx * pw, qy * phh) for qx, qy in q], [(0, 0), (1080, 0), (1080, 2340), (0, 2340)])
    den = g[6] * 540 + g[7] * 1727 + 1
    sx, sy = (g[0] * 540 + g[1] * 1727 + g[2]) / den, (g[3] * 540 + g[4] * 1727 + g[5]) / den
    tap = a2 + 0.6 * (b2 - a2)
    z = keys(tau, [(0, 1.0), (tap, 1.13)], smooth)
    cx, cy = keys(tau, [(0, (pw / 2, phh / 2)), (tap, (scx, scy))])
    p0 = max(tap + 0.25, d - 1.2)
    push = smooth((tau - p0) / (d - p0))
    if push > 0:
        z = z * (1 + 8 * push ** 2)
        cx, cy = lerp(cx, sx, smooth(push * 1.6)), lerp(cy, sy, smooth(push * 1.6))
    img, quad = phone_shot(st, cx, cy, z)
    if tau < 0.5:
        img = fade_black(img, tau / 0.5)
    img = flash(img, smooth((tau - d + 0.45) / 0.45))
    if abs(tau - (tap - 0.05)) < 0.5 / FPS:
        cue("tap", sc["start"] + tau)
    return img


CARD_GONE = 7.245                 # (door clip, page time) the login card is gone from one frame to the next


def s3(tau, sc):
    d = sc["dur"]
    (a0, b0), (a1, b1) = sc["lines"]
    lead = PLAN["s3"][0]
    if tau < lead + 0.5:
        fi = 258 + 77 * smooth(tau / lead) if tau < lead else 335
        img = ext_frame(fi)
        img = snow(img, sc["start"] + tau, 0.8)
        img = flash(img, 1 - smooth(tau / 0.6))
        if tau < lead - 0.0:
            return img
        ext = img
    # the website's door: the card while the narration speaks, "0000" typed on "zero zero zero zero"
    typed = a1 + 0.62 * (b1 - a1)
    # (the card waits with its caret blinking; "0000" is typed at page 4.5-5.0, at its own speed)
    pt = warp(tau, [(lead, 0.0), (lead + 0.6, 1.4), (typed - 0.55, 4.4), (typed + 0.25, 5.2), (typed + 0.9, 5.5), (b1 + 0.05, 7.15),
                    (d, 7.15 + d - b1 - 0.05)])
    z = keys(tau, [(lead, 1.0), (a0 + 0.5, 1.0), (a0 + 2.5, 1.32), (b1 - 0.6, 1.32), (b1 + 0.4, 1.0)])
    cy = keys(tau, [(a0 + 0.5, 502), (a0 + 2.5, 545), (b1 - 0.6, 545), (b1 + 0.4, 502)])
    img = site_view("door", pt, 960, cy, z)
    if CARD_GONE <= pt < CARD_GONE + 0.4:
        img = crossfade(site_view("door", CARD_GONE - 0.02, 960, cy, z), img, smooth((pt - CARD_GONE) / 0.4))
    img = snow(img, sc["start"] + tau, 0.35 * (1 - smooth((pt - 8.6) / 0.8)))
    if tau < lead + 0.5:
        img = crossfade(ext, img, (tau - lead) / 0.5)
    for k, at in enumerate(np.linspace(typed - 0.45, typed + 0.05, 4)):
        if abs(tau - at) < 0.5 / FPS:
            cue("key", sc["start"] + tau)
    if abs(pt - 7.15) < 0.6 / FPS * 1.0:
        cue("click", sc["start"] + tau)
    if abs(pt - 7.5) < 0.6 / FPS:
        cue("door", sc["start"] + tau)
    return img


def s4(tau, sc):
    d = sc["dur"]
    pt = 1.0 + tau
    path = [(0.0, (420, 640, 1.55)), (0.22 * d, (520, 660, 1.5)), (0.45 * d, (1480, 690, 1.55)), (0.62 * d, (1440, 640, 1.45)),
            (0.85 * d, (1030, 470, 1.25)), (d, (1010, 480, 1.18))]
    cx, cy, z = keys(tau, path)
    img = site_view("room", pt, cx, cy, z)
    return img


def s5(tau, sc):
    d = sc["dur"]
    (a0, b0), (a1, b1), (a2, b2) = sc["lines"]
    # the pointer glides to today's ornament (page 1.2-3.2) at its own speed and clicks; the popup (3.85) stays up,
    # the camera easing in on it, until the picture is hung on "And just like magic" (page 10.39)
    click = a0 + 2.9
    hang = a2 + 0.25
    pt = warp(tau, [(0, 0.2), (click - 2.55, 1.2), (click, 3.75), (hang, 10.33), (d, 10.33 + d - hang)])
    path = [(0.0, (1150, 470, 1.45)), (click - 0.2, (1170, 440, 1.6)), (click + 0.7, (960, 500, 1.15)), (hang - 0.3, (960, 470, 1.38)),
            (hang + 0.9, (700, 260, 1.5)), (d, (660, 250, 1.55))]
    cx, cy, z = keys(tau, path)
    img = site_view("ornament", pt, cx, cy, z)
    if abs(tau - click) < 0.5 / FPS:
        cue("chime", sc["start"] + tau)
    if abs(tau - hang) < 0.5 / FPS:
        cue("whoosh", sc["start"] + tau)
    return img


def tl_states():
    """The time-lapse's popup-free moments (page times): the wall before, after each day is hung, and at the end.
    Found once from the frames' brightness (a popup dims the room) and kept in states.json beside the clip."""
    path = os.path.join(B, "site", "timelapse", "states.json")
    if os.path.exists(path):
        return json.load(open(path))
    tt = json.load(open(os.path.join(B, "site", "timelapse", "times.json")))
    br = []
    for name, _ in tt:
        a = np.asarray(Image.open(os.path.join(B, "site", "timelapse", name)).convert("L").resize((192, 108)), np.float32)
        br.append(np.r_[a[10:90, 0:30].ravel(), a[10:90, 160:192].ravel()].mean())
    br = np.array(br)
    clean = br > 0.85 * np.percentile(br, 90)
    runs, start = [], None
    for i, c in enumerate(list(clean) + [False]):
        if c and start is None:
            start = i
        elif not c and start is not None:
            runs.append((tt[start][1], tt[i - 1][1]))
            start = None
    runs = [r for r in runs if r[1] - r[0] > 1.5]                       # (not the short gap before the prize popup)
    pts = [min(r[0] + 2.0, r[1] - 0.1) for r in runs[:-1]] + [runs[-1][1] - 0.05]
    json.dump(pts, open(path, "w"))
    return pts


TL_PATCH = [(940, 815, 1010, 890), (740, 925, 1180, 995)]     # the resting pointer, and the "Day N is on your wall" note


@functools.lru_cache(maxsize=6)
def tl_frame(k):
    """Time-lapse state k, with the pointer and the note under the tree painted out from the last state."""
    st = tl_states()
    img = site_frame("timelapse", st[k]).copy()
    if k == len(st) - 1:
        return img
    last = site_frame("timelapse", st[-1])
    m = Image.new("L", img.size, 0)
    for box in TL_PATCH:
        ImageDraw.Draw(m).rounded_rectangle(box, radius=18, fill=255)
    return Image.composite(last, img, m.filter(ImageFilter.GaussianBlur(8)))


def tl_view(f, cx, cy, z):
    """The wall at fractional state f, through the film's camera (each new day dissolves in)."""
    n = len(tl_states())
    k = int(clamp(math.floor(f), 0, n - 1))
    u = f - k
    a = camera(tl_frame(k), cx, cy, STAGE[2] * z)
    if u <= 0 or k + 1 >= n:
        return a
    return crossfade(a, camera(tl_frame(k + 1), cx, cy, STAGE[2] * z), u)


def s6(tau, sc):
    d = sc["dur"]
    n = len(tl_states())
    # day after day: each new picture dissolves in over the second half of its slot, a little faster as it goes
    u = clamp((tau - 0.5) / (0.8 * d - 0.5)) ** 1.12 * (n - 1)
    k = math.floor(u)
    f = k + smooth(clamp((u - k - 0.45) / 0.55))
    cx, cy, z = keys(tau, [(0, (680, 300, 1.5)), (0.5 * d, (760, 380, 1.3)), (0.82 * d, (900, 470, 1.08)), (d, (960, 502, 1.0))])
    img = tl_view(f, cx, cy, z)
    if tau < 0.5:
        img = crossfade(SC_LAST.get("s5", img), img, smooth(tau / 0.5))
    return img


def s7(tau, sc):
    d = sc["dur"]
    (a0, b0), (a1, b1), (a2, b2) = sc["lines"]
    cx, cy, z = keys(tau, [(0, (960, 502, 1.0)), (2.2, (900, 470, 1.1))])
    room = tl_view(len(tl_states()) - 1, cx, cy, z)
    blur = smooth((tau - 0.6) / 1.0)
    bg = room.filter(ImageFilter.GaussianBlur(10 * blur * W / 1920)) if blur > 0.01 else room
    bg = ImageEnhance.Brightness(bg).enhance(1 - 0.45 * blur)
    L_ = wheel_cached()
    appear = ease_out((tau - a0 - 0.4) / 0.8, 3)
    spin_start, spin_end = a1 + 0.1, a2 + 0.9
    u = (tau - spin_start) / (spin_end - spin_start)
    ang = spin_angle(u)
    dang = spin_angle(u) - spin_angle(u - 1 / FPS / (spin_end - spin_start))
    img = bg
    gift_t = tau - spin_end - 0.15
    wheel_fade = 1 - 0.55 * smooth(gift_t / 0.6)
    bob = lambda ph: 0.008 * math.sin(tau * 1.6 + ph)
    img = place(L_["float-a"], img, 0.9 + 0.1 * appear, 0, bob(0), appear * wheel_fade)
    img = place(L_["float-b"], img, 0.9 + 0.1 * appear, 0, bob(2.1), appear * wheel_fade)
    if appear > 0:
        disc = spun_disc(L_["disc"], ang, dang)
        img = place(disc, img, 0.55 + 0.45 * appear, 0, 0, appear * wheel_fade, tuple(WHEEL["centre"]))
        img = place(L_["frame"], img, 0.55 + 0.45 * appear, 0, 0, appear * wheel_fade, tuple(WHEEL["centre"]))
    if gift_t > 0:
        g = ease_out(gift_t / 0.7, 3)
        over = 1 + 0.12 * math.sin(clamp(gift_t / 0.7) * math.pi)
        img = flash(img, 0.42 * (1 - smooth(gift_t / 0.9)) * smooth(gift_t / 0.3), (0.5, 0.52))
        img = place(L_["gift"], img, (0.4 + 0.75 * g) * over, 0, 0.02 * math.sin(tau * 1.4), smooth(gift_t / 0.25), (0.5, 0.5))
    # the wheel ticks as each peg passes the pointer
    prev = spin_angle(u - 1 / FPS / (spin_end - spin_start))
    if 0 < u <= 1 and int(ang // 15) != int(prev // 15):
        cue("tick", sc["start"] + tau)
    if abs(gift_t) < 0.5 / FPS:
        cue("tada", sc["start"] + tau)
    if abs(tau - spin_start) < 0.5 / FPS:
        cue("spin", sc["start"] + tau)
    ta = smooth((tau - a1) / 0.5) * (1 - smooth((tau - spin_end + 0.2) / 0.4))
    img = with_text(img, [("Complete all 24 days", FONT_T, 64, CREAM)], 0.9, ta)
    tb = smooth((tau - a2 - 0.4) / 0.5) * (1 - smooth((tau - d + 0.4) / 0.4))
    img = with_text(img, [("Christmas Lucky Draw", FONT_T, 72, GOLD)], 0.9, tb)
    return img


def s8(tau, sc):
    d = sc["dur"]
    (a0, b0), (a1, b1), (a2, b2), (a3, b3) = sc["lines"]
    out_end = 2.2                                  # out through the doorway (the walk-in, backwards)
    shut_end = out_end + 1.2                       # the door closing (it opening, backwards)
    if tau < out_end:
        pt = lerp(10.2, 8.3, smooth(tau / out_end))
        img = site_view("door", pt, 960, 502, 1.0)
        if tau < 0.5:
            img = crossfade(SC_LAST.get("s7", img), img, tau / 0.5)
        return snow(img, sc["start"] + tau, 0.4 * smooth(tau / out_end))
    if tau < shut_end:
        pt = lerp(8.3, 7.35, smooth((tau - out_end) / (shut_end - out_end)))
        img = site_view("door", pt, 960, 502, 1.0)
        if abs(tau - out_end - 0.6) < 0.5 / FPS:
            cue("doorclose", sc["start"] + tau)
        return snow(img, sc["start"] + tau, 0.4)
    # pull back from the door, up over the trees
    v = (tau - shut_end) / (d - shut_end)
    fi = 335 - 215 * (1 - (1 - clamp(v)) ** 1.6)
    img = ext_frame(fi)
    img = smoke(img, fi, sc["start"] + tau)
    img = snow(img, sc["start"] + tau, 0.85)
    if tau - shut_end < 0.6:
        door = snow(site_view("door", 7.35, 960, 502, 1.0), sc["start"] + tau, 0.4)
        img = crossfade(door, img, (tau - shut_end) / 0.6)
    t1 = smooth((tau - a1) / 0.4) * (1 - smooth((tau - a2 + 0.1) / 0.4))
    n = 1 + int(clamp((tau - a1) / ((b1 - a1) / 3), 0, 2))
    words = ["24 days", "24 surprises", "24 LeMSIC memories"][:n]
    img = with_text(img, [(w, FONT_T, 70, CREAM) for w in words], 0.42, t1)
    t2 = smooth((tau - a2) / 0.5) * (1 - smooth((tau - a3 + 0.1) / 0.4))
    img = with_text(img, [("Your cabin is waiting", FONT_T, 66, CREAM), ("See you on 1 December", FONT_T, 54, GOLD)], 0.42, t2)
    end = smooth((tau - a3 + 0.1) / 0.7)
    if end > 0:
        em = load_rgba(os.path.join(ROOT, "site", "assets", "lemsic-emblem.png"))
        ew, eh = em.size
        side = min(ew, eh)
        em = em.crop(((ew - side) // 2, 0, (ew - side) // 2 + side, side)).resize((int(H * 0.2), int(H * 0.2)), Image.LANCZOS)
        m = Image.new("L", em.size, 0)
        ImageDraw.Draw(m).ellipse((0, 0, em.size[0] - 1, em.size[1] - 1), fill=255)
        em.putalpha(m.point(lambda v: int(v * end)))
        o = img.convert("RGBA")
        o.alpha_composite(em, ((W - em.size[0]) // 2, int(H * 0.18)))
        img = o.convert("RGB")
        img = with_text(img, [("LeMSIC Christmas Advent Calendar", FONT_T, 66, CREAM), ("1 – 24 December", FONT_T, 50, GOLD),
                              ("Merry Christmas!", FONT_T, 58, CREAM)], 0.6, end)
    img = fade_black(img, 1 - smooth((tau - d + 0.8) / 0.8))
    return img


SC_LAST = {}
SCENE_FN = {"s1": s1, "s2": s2, "s3": s3, "s4": s4, "s5": s5, "s6": s6, "s7": s7, "s8": s8}
ORDER = ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8"]
XFADE = {"s1": 0.7, "s3": 0.3, "s4": 0.6, "s5": 0.5}       # dissolve into these scenes from the one before


def frame_at(t):
    for i, sc in enumerate(ORDER):
        s = SC[sc]
        if t < s["start"] + s["dur"] or i == len(ORDER) - 1:
            tau = t - s["start"]
            img = SCENE_FN[sc](tau, s)
            nxt = ORDER[i + 1] if i + 1 < len(ORDER) else None
            if nxt in XFADE and tau > s["dur"] - XFADE[nxt]:
                pass
            if sc in XFADE and tau < XFADE[sc] and i > 0:
                prev = ORDER[i - 1]
                pimg = SCENE_FN[prev](SC[prev]["dur"] - 1 / FPS, SC[prev]) if prev not in SC_LAST else SC_LAST[prev]
                img = crossfade(pimg, img, tau / XFADE[sc])
            if tau > s["dur"] - 1.5 / FPS:
                SC_LAST[sc] = img
            return img


def main():
    out_dir = os.path.join(B, "out")
    os.makedirs(out_dir, exist_ok=True)
    n = int(round(TOTAL * FPS))
    if "--total" in ARGS:
        print(n)
        return
    stills = next((a.split("=")[1] for a in ARGS if a.startswith("--stills=")), None)
    if stills:                                      # single moments, as pictures, for checking
        for spec in stills.split(","):
            if spec.startswith("s"):                # e.g. s3:2.5 = 2.5 s into scene 3
                sc, tau = spec.split(":")
                t = SC[sc]["start"] + float(tau)
            else:
                t = float(spec)
            frame_at(t).save(os.path.join(out_dir, f"still-{spec.replace(':', '_')}.jpg"), quality=88)
        print({k: (round(v["start"], 1), round(v["dur"], 1)) for k, v in SC.items()}, "total", round(TOTAL, 1))
        return
    span = next((a.split("=")[1] for a in ARGS if a.startswith("--frames=")), None)
    a, b = (int(x) for x in span.split("-")) if span else (0, n - 1)
    tag = next((a.split("=")[1] for a in ARGS if a.startswith("--tag=")), None)    # one of several parts run side by side
    name = "picture-preview.mp4" if PREVIEW else "picture.mp4"
    if tag:
        name = f"picture-{tag}.mp4"
    ff = subprocess.Popen(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
                           "-crf", "16" if not PREVIEW else "22", "-pix_fmt", "yuv420p", os.path.join(out_dir, name)],
                          stdin=subprocess.PIPE)
    for k in range(a, min(b, n - 1) + 1):
        img = frame_at(k / FPS)
        ff.stdin.write(finish(img, k).tobytes())
        if k % 48 == 0:
            print(f"frame {k}/{n}", flush=True)
    ff.stdin.close()
    ff.wait()
    with open(os.path.join(out_dir, f"cues-{tag}.json" if tag else "cues.json"), "w") as f:
        json.dump({"total": TOTAL, "lines": LINES, "sfx": CUES,
                   "scenes": {k: {"start": round(v["start"], 3), "dur": round(v["dur"], 3)} for k, v in SC.items()}}, f, indent=1)
    print("total", round(TOTAL, 1), "s;", n, "frames")


if __name__ == "__main__":
    main()
