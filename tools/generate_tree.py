#!/usr/bin/env python3
"""Generate the LeMSIC tree advent calendar.

The tree follows the LeMSIC emblem: a cedar formed by a serpent winding
around a staff. Days 1-23 hang from its tiers as ornaments; day 24 is the
star on top.

Outputs:
  images/lemsic-tree-calendar.svg     the full calendar
  images/ornaments/day-01.svg ...     each ornament on its own (for the website)

Run:  python3 tools/generate_tree.py
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_doors import (  # noqa: E402  shared palette + helpers
    GOLD, GOLD_D, GOLD_L, CREAM, WHITE, RED, RED_D, GREEN, GREEN_D, INK,
    star_points, sparkle)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORN_DIR = os.path.join(ROOT, "images", "ornaments")

BLUE = "#3C6BAD"          # LeMSIC blue, sampled from the emblem
BLUE_D = "#284D85"
SANS = "'Avenir Next', 'Segoe UI', Inter, 'Helvetica Neue', Arial, sans-serif"
SERIF = "Georgia, 'Times New Roman', 'DejaVu Serif', serif"

# ---------------------------------------------------------------- layout
W, H = 1800, 2040
CX = 900                  # staff x
BODY = 42                 # serpent thickness
GAP = 6                   # blue gap drawn around white shapes (emblem style)
ROD = 21                  # staff half-width
TIERS = 9
TIER_Y0 = 575             # centre-line y of the first sweep
TIER_DY = 136             # vertical distance between sweeps
SLOPE = 18                # each sweep drops this much along its length
ROD_TOP, ROD_BOTTOM = 492, 1790
STAR_Y = 418


def half_width(i):
    return 100 + 56 * i


# ornaments per sweep (sweep 0 is the short one under the head)
PER_TIER = [0, 1, 2, 2, 3, 3, 4, 4, 4]          # 23 ornaments

ORN_R = 38
ORN_COLOURS = [
    # (light, mid, dark, number fill, number shadow)
    ("#FF7B7B", RED, RED_D, CREAM, "#5A0E12"),
    (GOLD_L, GOLD, GOLD_D, "#7A1018", "#FFF3C8"),
    ("#6FD49A", GREEN, GREEN_D, CREAM, "#0C3320"),
    ("#E486B8", "#B0306F", "#6A1640", CREAM, "#3A0A22"),
    ("#FFFFFF", "#D9E3EE", "#93A6BC", BLUE_D, "#FFFFFF"),
]


# ---------------------------------------------------------------- serpent
def sweeps():
    """Return a list of sweeps: (x_start, y_start, x_end, y_end)."""
    out = []
    x = CX - 66                                 # start just right of the head
    for i in range(TIERS):
        y = TIER_Y0 + i * TIER_DY
        going_right = i % 2 == 0
        x_end = CX + half_width(i) if going_right else CX - half_width(i)
        out.append((x, y, x_end, y + SLOPE))
        x = x_end
    return out


TAIL_SPLIT = 0.58   # fraction of the last sweep drawn at full thickness


def serpent_path(sw):
    d = f"M{sw[0][0]} {sw[0][1]}"
    for i, (xa, ya, xb, yb) in enumerate(sw):
        if i == len(sw) - 1:
            xm = xa + (xb - xa) * TAIL_SPLIT
            ym = ya + (yb - ya) * TAIL_SPLIT
            d += f" L{xm:.1f} {ym:.1f}"
            break
        d += f" L{xb} {yb}"
        ny = sw[i + 1][1]
        k = 0.7 * (ny - yb) * (1 if xb > xa else -1)
        d += f" C{xb + k:.1f} {yb} {xb + k:.1f} {ny} {xb} {ny}"
    return d


def tail_shape(sw):
    xa, ya, xb, yb = sw[-1]
    xm = xa + (xb - xa) * TAIL_SPLIT
    ym = ya + (yb - ya) * TAIL_SPLIT
    h = BODY / 2
    tip_x, tip_y = xb + 30, yb + 34      # tail flicks down a little, like the emblem
    return (f"M{xm - 1:.1f} {ym - h:.1f} Q{(xm + tip_x) / 2:.1f} {ym - h + 4:.1f} {tip_x:.1f} {tip_y:.1f} "
            f"Q{(xm + tip_x) / 2 - 20:.1f} {ym + h - 2:.1f} {xm - 1:.1f} {ym + h:.1f}Z")


def head_group():
    """Serpent head at the start of the first sweep, wearing a Santa hat."""
    x, y = sweeps()[0][0], sweeps()[0][1]
    head = (f"M{x + 2} {y - 17} C{x - 20} {y - 22} {x - 48} {y - 18} {x - 56} {y - 4} "
            f"C{x - 60} {y + 6} {x - 50} {y + 16} {x - 30} {y + 15} C{x - 16} {y + 15} {x - 6} {y + 17} {x + 2} {y + 17}Z")
    hat = (f'<g transform="translate({x - 34} {y - 16}) rotate(-24)">'
           f'<path d="M-20 0 C-16 -22 0 -40 22 -38 C14 -30 10 -16 18 0Z" fill="{RED}" stroke="{RED_D}" stroke-width="2"/>'
           f'<circle cx="23" cy="-38" r="7" fill="{WHITE}" stroke="#C9D8E4" stroke-width="1.5"/>'
           f'<rect x="-24" y="-5" width="46" height="12" rx="6" fill="{WHITE}" stroke="#C9D8E4" stroke-width="1.5"/></g>')
    tongue = (f'<path d="M{x - 57} {y + 4} L{x - 72} {y + 6} M{x - 68} {y + 5} L{x - 76} {y} '
              f'M{x - 68} {y + 5} L{x - 75} {y + 12}" stroke="{RED}" stroke-width="2.5" '
              f'stroke-linecap="round" fill="none"/>')
    eye = f'<circle cx="{x - 34}" cy="{y + 1}" r="4" fill="{BLUE_D}"/>'
    k = BODY / 34
    scale = f'transform="translate({x} {y}) scale({k:.3f}) translate({-x} {-y})"'
    return head, f'<g {scale}>{tongue + eye + hat}</g>', scale


def staff_parts():
    """Staff (rod) and its crossbar as filled shapes."""
    crossbar = (f"M{CX - 86} {ROD_TOP - 14} L{CX + 86} {ROD_TOP - 14} L{CX + 70} {ROD_TOP + 8} "
                f"L{CX + ROD} {ROD_TOP + 14} L{CX - ROD} {ROD_TOP + 14} L{CX - 70} {ROD_TOP + 8}Z")
    rod = (f"M{CX - ROD} {ROD_TOP} L{CX + ROD} {ROD_TOP} L{CX + ROD} {ROD_BOTTOM - 40} "
           f"Q{CX + ROD} {ROD_BOTTOM} {CX + 34} {ROD_BOTTOM} L{CX - 34} {ROD_BOTTOM} "
           f"Q{CX - ROD} {ROD_BOTTOM} {CX - ROD} {ROD_BOTTOM - 40}Z")
    return crossbar, rod


def tree_svg():
    sw = sweeps()
    path = serpent_path(sw)
    tail = tail_shape(sw)
    head, head_details, head_scale = head_group()
    crossbar, rod = staff_parts()

    g = []
    # staff first (white with a blue gap around it)
    for shape in (rod, crossbar):
        g.append(f'<path d="{shape}" fill="{WHITE}" stroke="{BLUE}" stroke-width="{GAP * 2}" paint-order="stroke"/>')
    # serpent: all blue outlines first, then all white, so joins stay seamless
    g.append(f'<path d="{path}" fill="none" stroke="{BLUE}" stroke-width="{BODY + GAP * 2}" stroke-linejoin="round"/>')
    g.append(f'<path d="{tail}" fill="{BLUE}" stroke="{BLUE}" stroke-width="{GAP * 2}" stroke-linejoin="round"/>')
    g.append(f'<path d="{head}" {head_scale} fill="{BLUE}" stroke="{BLUE}" stroke-width="{GAP * 2}"/>')
    g.append(f'<path d="{path}" fill="none" stroke="url(#snow)" stroke-width="{BODY}" stroke-linejoin="round"/>')
    g.append(f'<path d="{tail}" fill="url(#snow)"/>')
    g.append(f'<path d="{head}" {head_scale} fill="{WHITE}"/>')
    # weave: staff passes in front of every other sweep
    for i, (xa, ya, xb, yb) in enumerate(sw):
        if i % 2 == 1:
            t = (CX - xa) / (xb - xa)
            yc = ya + (yb - ya) * t
            top, h = yc - BODY / 2 - GAP - 4, BODY + GAP * 2 + 8
            g.append(f'<rect x="{CX - ROD - GAP}" y="{top:.1f}" width="{(ROD + GAP) * 2}" height="{h}" fill="{BLUE}"/>'
                     f'<rect x="{CX - ROD}" y="{top - 2:.1f}" width="{ROD * 2}" height="{h + 4}" fill="{WHITE}"/>')
    g.append(head_details)

    # fairy lights along the serpent
    rnd = random.Random(7)
    lights = []
    for i, (xa, ya, xb, yb) in enumerate(sw[:-1]):
        n = int(abs(xb - xa) // 46)
        for k in range(1, n):
            t = k / n
            x = xa + (xb - xa) * t
            if abs(x - CX) < ROD + 10:
                continue
            y = ya + (yb - ya) * t + rnd.uniform(-5, 5)
            c = rnd.choice([GOLD, GOLD, "#FF6B6B", "#7DE39C", GOLD_L])
            lights.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="9" fill="{c}" opacity="0.25"/>'
                          f'<circle cx="{x:.0f}" cy="{y:.0f}" r="3.6" fill="{c}"/>')
    g.append("".join(lights))
    return "\n  ".join(g)


# ---------------------------------------------------------------- ornaments
def ornament_positions():
    """Hanging points along each sweep, kept clear of the staff and the bends."""
    pts = []
    for i, (xa, ya, xb, yb) in enumerate(sweeps()):
        n = PER_TIER[i]
        if not n:
            continue
        lo, hi = min(xa, xb) + 32, max(xa, xb) - 32
        if i == TIERS - 1:                       # keep off the thin tail tip
            hi = min(hi, xa + (xb - xa) * 0.9)
        segs = [(lo, CX - 68), (CX + 68, hi)]
        lens = [max(0, b - a) for a, b in segs]
        n_left = round(n * lens[0] / sum(lens)) if sum(lens) else 0
        n_left = min(max(n_left, 1 if lens[0] > 0 else 0), n)
        counts = [n_left, n - n_left]
        if counts[1] and lens[1] <= 0:
            counts = [n, 0]
        for (a, b), c in zip(segs, counts):
            for k in range(c):
                x = a + (k + 0.5) * (b - a) / c
                t = (x - xa) / (xb - xa)
                y = ya + (yb - ya) * t + BODY / 2 - 2
                pts.append((x, y, i))
    return pts


# Day numbers mixed across the tree (fixed, so the layout never changes).
# Each tier holds a spread of early, middle and late days.
def day_order(n):
    rnd = random.Random(1964)                    # LeMSIC's founding year
    days = list(range(1, n + 1))
    rnd.shuffle(days)
    return days


def ornament(day, idx, p, string_len):
    """Ornament hanging from (0,0) downward. `idx` picks colour and pattern."""
    light, mid, dark, num_fill, num_shadow = ORN_COLOURS[idx % len(ORN_COLOURS)]
    pattern = (idx * 3 + day) % 4
    r = ORN_R
    cap_y = string_len
    cy = cap_y + 10 + r - 2
    clip = f"{p}clip"
    pat = ""
    if pattern == 0:     # zig-zag band
        zz = " ".join(f"L{-r + k * 8} {cy - 29 + (6 if k % 2 else 0)}" for k in range(int(2 * r / 8) + 2))
        zz2 = " ".join(f"L{r - k * 8} {cy - 22 + (6 if k % 2 else 0)}" for k in range(int(2 * r / 8) + 2))
        pat = f'<path d="M{-r} {cy - 29} {zz} {zz2}Z" fill="{GOLD if idx % 5 != 1 else RED}" opacity="0.9"/>'
    elif pattern == 1:   # two thin bands
        band = GOLD if idx % 5 != 1 else RED
        pat = (f'<rect x="{-r}" y="{cy - 24}" width="{2 * r}" height="4" fill="{band}"/>'
               f'<rect x="{-r}" y="{cy + 21}" width="{2 * r}" height="4" fill="{band}"/>')
    elif pattern == 2:   # dots
        dot = WHITE if idx % 5 not in (1, 4) else RED
        pat = "".join(f'<circle cx="{r * 0.68 * math.cos(math.radians(a)):.1f}" '
                      f'cy="{cy + r * 0.68 * math.sin(math.radians(a)):.1f}" r="2.6" fill="{dot}" opacity="0.85"/>'
                      for a in range(0, 360, 36))
    else:                # snowy top
        pat = (f'<path d="M{-r} {cy - 14} Q{-r * 0.6} {cy - 6} {-r * 0.3} {cy - 13} Q0 {cy - 4} {r * 0.3} {cy - 12} '
               f'Q{r * 0.6} {cy - 5} {r} {cy - 14} L{r} {cy - r} L{-r} {cy - r}Z" fill="{WHITE}" opacity="0.85"/>')
    size = 33 if day < 10 else 31
    return f"""<g>
    <defs>
      <radialGradient id="{p}g" cx="0.35" cy="0.3" r="0.85">
        <stop offset="0" stop-color="{light}"/><stop offset="0.55" stop-color="{mid}"/><stop offset="1" stop-color="{dark}"/>
      </radialGradient>
      <clipPath id="{clip}"><circle cx="0" cy="{cy}" r="{r}"/></clipPath>
    </defs>
    <line x1="0" y1="0" x2="0" y2="{cap_y}" stroke="{GOLD_L}" stroke-width="2"/>
    <circle cx="0" cy="{cap_y - 1}" r="4" fill="none" stroke="{GOLD}" stroke-width="2"/>
    <circle cx="2" cy="{cy + 4}" r="{r}" fill="#000" opacity="0.22"/>
    <circle cx="0" cy="{cy}" r="{r}" fill="url(#{p}g)" stroke="{dark}" stroke-width="1.5"/>
    <g clip-path="url(#{clip})">{pat}</g>
    <rect x="-9" y="{cap_y + 2}" width="18" height="11" rx="2" fill="{GOLD}" stroke="{GOLD_D}" stroke-width="1.5"/>
    <ellipse cx="{-r * 0.42:.1f}" cy="{cy - r * 0.45:.1f}" rx="7" ry="12" fill="{WHITE}" opacity="0.45"
             transform="rotate(35 {-r * 0.42:.1f} {cy - r * 0.45:.1f})"/>
    <text x="1.5" y="{cy + size * 0.36 + 1.5:.1f}" text-anchor="middle" font-family="{SERIF}" font-weight="bold"
          font-size="{size}" fill="{num_shadow}" opacity="0.6">{day}</text>
    <text x="0" y="{cy + size * 0.36:.1f}" text-anchor="middle" font-family="{SERIF}" font-weight="bold"
          font-size="{size}" fill="{num_fill}">{day}</text>
  </g>"""


def topper_star(p):
    """Day 24: the star on top of the tree."""
    rays = "".join(
        f'<polygon points="0,-5 {92 if i % 2 == 0 else 70},0 0,5" fill="{GOLD_L}" '
        f'opacity="{0.45 if i % 2 == 0 else 0.28}" transform="rotate({i * 22.5 + 11.25})"/>' for i in range(16))
    return f"""<g>
    <defs>
      <radialGradient id="{p}halo"><stop offset="0" stop-color="{GOLD_L}" stop-opacity="0.85"/>
        <stop offset="1" stop-color="{GOLD_L}" stop-opacity="0"/></radialGradient>
      <linearGradient id="{p}star" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="{GOLD_L}"/><stop offset="0.6" stop-color="{GOLD}"/><stop offset="1" stop-color="{GOLD_D}"/>
      </linearGradient>
    </defs>
    <circle r="96" fill="url(#{p}halo)"/>
    {rays}
    <polygon points="{star_points(0, 4, 66, 28)}" fill="#000" opacity="0.2"/>
    <polygon points="{star_points(0, 0, 66, 28)}" fill="url(#{p}star)" stroke="{GOLD_D}" stroke-width="3" stroke-linejoin="round"/>
    <polygon points="{star_points(0, 0, 50, 21)}" fill="none" stroke="{GOLD_L}" stroke-width="1.5" opacity="0.8"/>
    <text x="1.5" y="15.5" text-anchor="middle" font-family="{SERIF}" font-weight="bold" font-size="38" fill="#FFF3C8" opacity="0.6">24</text>
    <text x="0" y="14" text-anchor="middle" font-family="{SERIF}" font-weight="bold" font-size="38" fill="#7A1018">24</text>
    {sparkle(-74, -44, 9, WHITE)}{sparkle(76, -38, 7, WHITE)}{sparkle(62, 60, 6, WHITE)}{sparkle(-66, 56, 7, WHITE)}
  </g>"""


def placed_ornaments(prefix):
    pts = ornament_positions()
    days = day_order(len(pts))
    rnd = random.Random(24)
    out = []
    meta = []
    for idx, ((x, y, tier), day) in enumerate(zip(pts, days)):
        L = rnd.choice([6, 9, 12, 15])
        out.append(f'<g transform="translate({x:.1f} {y:.1f})" id="{prefix}day-{day}">'
                   f'{ornament(day, idx, f"{prefix}o{day}-", L)}</g>')
        meta.append((day, idx, L))
    return "\n  ".join(out), meta


# ---------------------------------------------------------------- frame + text
def laurel(side):
    """A laurel branch in the style of the emblem: chevron leaves along an arc."""
    cx, cy, r = CX, 1180, 840
    leaves = []
    for k in range(12):
        a = 168 - 4.2 * k                        # from about 9 o'clock round towards 6
        ar = math.radians(a)
        if side == "left":
            x, rot = cx + r * math.cos(ar), a + 180
        else:
            x, rot = cx - r * math.cos(ar), 180 - a
        y = cy + r * math.sin(ar)
        size = 1.15 - k * 0.03
        leaves.append(
            f'<g transform="translate({x:.1f} {y:.1f}) rotate({rot:.1f}) scale({size:.2f})">'
            f'<path d="M0 0 L-16 -26 L-8 -28 L0 -12 L8 -28 L16 -26Z" fill="{WHITE}"/></g>')
    return "".join(leaves)


def calendar_svg():
    rnd = random.Random(1964)
    snow = "".join(
        f'<circle cx="{rnd.uniform(60, W - 60):.0f}" cy="{rnd.uniform(60, H - 60):.0f}" '
        f'r="{rnd.choice([1.5, 2, 2.5, 3.2])}" fill="#fff" opacity="{rnd.uniform(0.15, 0.5):.2f}"/>'
        for _ in range(170))
    twinkles = "".join(sparkle(round(rnd.uniform(90, W - 90)), round(rnd.uniform(140, 1500)),
                               rnd.choice([5, 6, 8]), WHITE) for _ in range(14))
    ornaments, _ = placed_ornaments("cal-")
    arc_c = (CX, 1150)
    r_out, r_in = 950, 880

    def arc(r):
        x0, x1 = arc_c[0] - r, arc_c[0] + r
        return f"M{x0} {arc_c[1]} A{r} {r} 0 0 1 {x1} {arc_c[1]}"

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="LeMSIC Advent Calendar">
  <title>LeMSIC Advent Calendar</title>
  <defs>
    <linearGradient id="frame" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#7A4A22"/><stop offset="0.5" stop-color="#5A3517"/><stop offset="1" stop-color="#3A210D"/>
    </linearGradient>
    <linearGradient id="snow" gradientUnits="userSpaceOnUse" x1="0" y1="{ROD_TOP}" x2="0" y2="{ROD_BOTTOM}">
      <stop offset="0" stop-color="#FFFFFF"/><stop offset="1" stop-color="#EEF4FB"/>
    </linearGradient>
    <radialGradient id="vig" cx="0.5" cy="0.45" r="0.75">
      <stop offset="0.6" stop-color="#0A1A33" stop-opacity="0"/><stop offset="1" stop-color="#0A1A33" stop-opacity="0.45"/>
    </radialGradient>
    <path id="arcOut" d="{arc(r_out)}"/>
    <path id="arcIn" d="{arc(r_in)}"/>
  </defs>

  <rect width="{W}" height="{H}" rx="30" fill="url(#frame)"/>
  <rect x="14" y="14" width="{W - 28}" height="{H - 28}" rx="22" fill="none" stroke="#9A6532" stroke-width="3" opacity="0.6"/>
  <rect x="40" y="40" width="{W - 80}" height="{H - 80}" rx="14" fill="{BLUE}"/>
  {snow}
  {twinkles}

  <text font-family="{SANS}" font-weight="600" font-size="66" letter-spacing="8" fill="{WHITE}">
    <textPath href="#arcOut" startOffset="50%" text-anchor="middle">LeMSIC Advent Calendar</textPath>
  </text>
  <text font-family="{SANS}" font-size="28" letter-spacing="9" fill="{WHITE}" opacity="0.92">
    <textPath href="#arcIn" startOffset="50%" text-anchor="middle">1 – 24 december 2026</textPath>
  </text>

  {laurel("left")}
  {laurel("right")}

  {tree_svg()}

  <g transform="translate({CX} {STAR_Y})" id="cal-day-24">{topper_star("cal-o24-")}</g>
  {ornaments}

  <text x="{CX}" y="{ROD_BOTTOM + 84}" text-anchor="middle" font-family="{SANS}" font-size="64" letter-spacing="3" fill="{WHITE}">LeMSIC</text>
  <text x="{CX}" y="{ROD_BOTTOM + 134}" text-anchor="middle" font-family="{SANS}" font-size="24" letter-spacing="8" fill="{WHITE}" opacity="0.85">OPEN ONE ORNAMENT EACH DAY</text>

  <rect x="40" y="40" width="{W - 80}" height="{H - 80}" rx="14" fill="url(#vig)"/>
  <rect x="40" y="40" width="{W - 80}" height="{H - 80}" rx="14" fill="none" stroke="{GOLD}" stroke-width="4"/>
</svg>
"""


def ornament_file(day):
    """A single ornament on a transparent 120x150 canvas."""
    if day == 24:
        body = f'<g transform="translate(110 110)">{topper_star("s24-")}</g>'
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 220 220" width="220" height="220" '
                f'role="img" aria-label="Day 24 star"><title>Day 24 — Christmas Eve star</title>{body}</svg>\n')
    _, meta = placed_ornaments("x-")
    day_meta = {d: (i, L) for d, i, L in meta}
    idx, _ = day_meta[day]
    body = f'<g transform="translate(60 4)">{ornament(day, idx, f"s{day}-", 14)}</g>'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 108" width="120" height="108" '
            f'role="img" aria-label="Day {day} ornament"><title>Day {day}</title>{body}</svg>\n')


def main():
    os.makedirs(ORN_DIR, exist_ok=True)
    with open(os.path.join(ROOT, "images", "lemsic-tree-calendar.svg"), "w") as f:
        f.write(calendar_svg())
    for day in range(1, 25):
        with open(os.path.join(ORN_DIR, f"day-{day:02d}.svg"), "w") as f:
            f.write(ornament_file(day))
    pts = ornament_positions()
    print(f"Wrote lemsic-tree-calendar.svg with {len(pts)} hanging ornaments + star, and 24 ornament files")


if __name__ == "__main__":
    main()
