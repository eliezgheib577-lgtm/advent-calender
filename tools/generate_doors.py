#!/usr/bin/env python3
"""Generate the LeMSIC Advent Calendar artwork.

Outputs:
  images/doors/day-01.svg ... day-24.svg   one door per day (300x300)
  images/advent-calendar.svg               the full wooden wall calendar

Run:  python3 tools/generate_doors.py
"""
import math
import os
import random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOOR_DIR = os.path.join(ROOT, "images", "doors")

# ---------------------------------------------------------------- palette
GOLD, GOLD_D, GOLD_L = "#E8B84A", "#A8761F", "#FFE39A"
CREAM, WHITE, SNOW = "#FFF4DC", "#FFFFFF", "#F2F7FB"
RED, RED_D = "#D63A3A", "#951B22"
GREEN, GREEN_D, GREEN_L = "#2E8B57", "#1B5E3A", "#5DB37E"
BROWN, BROWN_D, BROWN_L = "#9A6532", "#5E3A1A", "#C99158"
ORANGE, INK = "#F08A24", "#22150C"

BACKGROUNDS = {
    "red": ("#B02A33", "#6E141B"),
    "green": ("#23663F", "#103A24"),
    "navy": ("#26406A", "#0F1C33"),
    "plum": ("#7A2140", "#43101F"),
    "teal": ("#22675C", "#0F3A33"),
}

FONT = "Georgia, 'Times New Roman', 'DejaVu Serif', serif"


def star_points(cx, cy, r_out, r_in, n=5, rot=-90):
    pts = []
    for i in range(n * 2):
        r = r_out if i % 2 == 0 else r_in
        a = math.radians(rot + i * 180 / n)
        pts.append(f"{cx + r * math.cos(a):.1f},{cy + r * math.sin(a):.1f}")
    return " ".join(pts)


def star(cx, cy, r, fill=GOLD, stroke=GOLD_D, sw=2):
    return (f'<polygon points="{star_points(cx, cy, r, r * 0.42)}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round"/>')


def sparkle(cx, cy, s, fill=GOLD_L):
    return (f'<path d="M{cx} {cy - s} Q{cx} {cy} {cx + s} {cy} Q{cx} {cy} {cx} {cy + s} '
            f'Q{cx} {cy} {cx - s} {cy} Q{cx} {cy} {cx} {cy - s}Z" fill="{fill}"/>')


# ---------------------------------------------------------------- icons
# Every icon is drawn around (0,0) and fits roughly inside a 120x120 box.
# `p` is the id prefix so gradients/masks stay unique when doors are combined.

def icon_star(p):
    return f"""
  <circle r="60" fill="{GOLD_L}" opacity="0.18"/>
  {star(0, 0, 56, GOLD, GOLD_D, 3)}
  <polygon points="{star_points(0, 0, 30, 13)}" fill="{GOLD_L}" opacity="0.75"/>
  {sparkle(-52, -40, 9)}{sparkle(54, -30, 7)}{sparkle(46, 46, 8)}{sparkle(-48, 44, 6)}"""


def icon_tree(p):
    return f"""
  <rect x="-9" y="38" width="18" height="18" rx="2" fill="{BROWN}"/>
  <polygon points="0,-50 -32,-12 32,-12" fill="{GREEN}" stroke="{GREEN_D}" stroke-width="2" stroke-linejoin="round"/>
  <polygon points="0,-30 -44,14 44,14" fill="{GREEN}" stroke="{GREEN_D}" stroke-width="2" stroke-linejoin="round"/>
  <polygon points="0,-6 -55,40 55,40" fill="{GREEN}" stroke="{GREEN_D}" stroke-width="2" stroke-linejoin="round"/>
  <path d="M-24 -10 Q0 2 22 -14 M-36 16 Q0 30 38 12" stroke="{GOLD}" stroke-width="3" fill="none" stroke-dasharray="2 5" stroke-linecap="round"/>
  <circle cx="-14" cy="-20" r="5" fill="{RED}"/><circle cx="16" cy="-2" r="5" fill="{GOLD}"/>
  <circle cx="-22" cy="6" r="5" fill="{CREAM}"/><circle cx="-30" cy="32" r="6" fill="{GOLD}"/>
  <circle cx="6" cy="28" r="6" fill="{RED}"/><circle cx="34" cy="32" r="5" fill="{CREAM}"/>
  {star(0, -54, 14, GOLD, GOLD_D, 2)}"""


def icon_gift(p):
    return f"""
  <rect x="-44" y="-12" width="88" height="66" rx="4" fill="{RED}" stroke="{RED_D}" stroke-width="2"/>
  <rect x="-52" y="-30" width="104" height="22" rx="4" fill="#E04A4A" stroke="{RED_D}" stroke-width="2"/>
  <rect x="-9" y="-30" width="18" height="84" fill="{GOLD}" stroke="{GOLD_D}" stroke-width="1.5"/>
  <rect x="-44" y="-8" width="88" height="5" fill="{RED_D}" opacity="0.35"/>
  <path d="M0 -30 C-10 -58 -46 -56 -36 -38 C-30 -28 -12 -30 0 -30Z" fill="{GOLD}" stroke="{GOLD_D}" stroke-width="2"/>
  <path d="M0 -30 C10 -58 46 -56 36 -38 C30 -28 12 -30 0 -30Z" fill="{GOLD}" stroke="{GOLD_D}" stroke-width="2"/>
  <circle cx="0" cy="-31" r="7" fill="{GOLD_L}" stroke="{GOLD_D}" stroke-width="2"/>
  <circle cx="-26" cy="20" r="4" fill="{CREAM}" opacity="0.8"/><circle cx="26" cy="36" r="4" fill="{CREAM}" opacity="0.8"/>
  <circle cx="24" cy="6" r="3" fill="{CREAM}" opacity="0.8"/><circle cx="-24" cy="42" r="3" fill="{CREAM}" opacity="0.8"/>"""


def icon_candy_cane(p):
    d = "M14 58 L14 -22 A26 26 0 0 0 -38 -22 L-38 -12"
    return f"""
  <path d="{d}" stroke="{RED_D}" stroke-width="24" fill="none" stroke-linecap="round"/>
  <path d="{d}" stroke="{WHITE}" stroke-width="19" fill="none" stroke-linecap="round"/>
  <path d="{d}" stroke="{RED}" stroke-width="19" fill="none" stroke-dasharray="9 11"/>
  <path d="M8 50 L8 -20 A20 20 0 0 0 -24 -36" stroke="{WHITE}" stroke-width="3" fill="none" opacity="0.55" stroke-linecap="round"/>
  <g transform="translate(26 30) rotate(-20)">
    <path d="M0 0 C10 -14 26 -14 30 -4 C18 -4 10 0 0 0Z" fill="{GREEN}"/>
    <path d="M0 0 C-4 -16 6 -28 16 -26 C10 -18 6 -10 0 0Z" fill="{GREEN_L}"/>
    <circle r="5" fill="{RED}"/>
  </g>"""


def icon_bell(p):
    return f"""
  <defs><linearGradient id="{p}bell" x1="0" x2="1"><stop offset="0" stop-color="{GOLD_D}"/>
  <stop offset="0.45" stop-color="{GOLD_L}"/><stop offset="1" stop-color="{GOLD_D}"/></linearGradient></defs>
  <circle cx="0" cy="-46" r="7" fill="none" stroke="{GOLD_D}" stroke-width="4"/>
  <path d="M-44 32 C-38 26 -34 14 -33 -2 C-31 -30 -18 -42 0 -42 C18 -42 31 -30 33 -2 C34 14 38 26 44 32Z"
        fill="url(#{p}bell)" stroke="{GOLD_D}" stroke-width="2.5"/>
  <rect x="-48" y="30" width="96" height="10" rx="5" fill="{GOLD}" stroke="{GOLD_D}" stroke-width="2"/>
  <circle cx="0" cy="46" r="9" fill="{GOLD}" stroke="{GOLD_D}" stroke-width="2"/>
  <path d="M-22 -4 C-20 -24 -10 -32 -2 -34" stroke="{WHITE}" stroke-width="4" fill="none" opacity="0.6" stroke-linecap="round"/>
  <g transform="translate(0 -40)">
    <path d="M0 0 C-14 -10 -30 -4 -26 6 C-20 14 -8 6 0 0Z" fill="{RED}" stroke="{RED_D}" stroke-width="1.5"/>
    <path d="M0 0 C14 -10 30 -4 26 6 C20 14 8 6 0 0Z" fill="{RED}" stroke="{RED_D}" stroke-width="1.5"/>
    <circle r="5" fill="{RED_D}"/>
  </g>"""


def icon_bauble(p):
    return f"""
  <defs><radialGradient id="{p}orb" cx="0.35" cy="0.3" r="0.8"><stop offset="0" stop-color="#FF7A7A"/>
  <stop offset="0.55" stop-color="{RED}"/><stop offset="1" stop-color="{RED_D}"/></radialGradient>
  <clipPath id="{p}orbclip"><circle cx="0" cy="10" r="46"/></clipPath></defs>
  <path d="M0 -60 L0 -44" stroke="{GOLD_L}" stroke-width="2"/>
  <circle cx="0" cy="-50" r="7" fill="none" stroke="{GOLD}" stroke-width="3"/>
  <circle cx="0" cy="10" r="46" fill="url(#{p}orb)"/>
  <g clip-path="url(#{p}orbclip)">
    <path d="M-50 4 L-40 -6 L-30 4 L-20 -6 L-10 4 L0 -6 L10 4 L20 -6 L30 4 L40 -6 L50 4 L50 14 L40 4 L30 14 L20 4 L10 14 L0 4 L-10 14 L-20 4 L-30 14 L-40 4 L-50 14Z" fill="{GOLD}"/>
    <rect x="-50" y="26" width="100" height="5" fill="{GOLD}"/>
    <circle cx="-24" cy="40" r="3" fill="{CREAM}"/><circle cx="0" cy="44" r="3" fill="{CREAM}"/><circle cx="24" cy="40" r="3" fill="{CREAM}"/>
  </g>
  <rect x="-13" y="-42" width="26" height="12" rx="2" fill="{GOLD}" stroke="{GOLD_D}" stroke-width="2"/>
  <ellipse cx="-18" cy="-12" rx="9" ry="14" fill="{WHITE}" opacity="0.45" transform="rotate(30 -18 -12)"/>"""


def icon_snowflake(p):
    arm = (f'<line x1="0" y1="0" x2="0" y2="-56"/>'
           f'<polyline points="-13,-40 0,-28 13,-40" fill="none"/>'
           f'<polyline points="-10,-56 0,-46 10,-56" fill="none"/>')
    arms = "".join(f'<g transform="rotate({a})">{arm}</g>' for a in range(0, 360, 60))
    return f"""
  <circle r="58" fill="{WHITE}" opacity="0.08"/>
  <g stroke="#CFE6FF" stroke-width="10" stroke-linecap="round" stroke-linejoin="round" opacity="0.35">{arms}</g>
  <g stroke="{WHITE}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round">{arms}</g>
  <polygon points="{star_points(0, 0, 12, 7, 6, -90)}" fill="{WHITE}"/>
  <circle r="4" fill="#9CC9F5"/>"""


def icon_stocking(p):
    return f"""
  <path d="M-24 -34 L22 -34 L22 8 L44 22 C60 32 52 56 32 56 L-2 56 C-26 56 -28 40 -24 26Z"
        fill="{RED}" stroke="{RED_D}" stroke-width="2.5" stroke-linejoin="round"/>
  <path d="M30 24 C50 30 52 52 32 54 C38 46 38 34 30 24Z" fill="{WHITE}" opacity="0.9"/>
  <path d="M-24 34 C-26 50 -12 56 0 56 C-10 50 -14 42 -12 34Z" fill="{WHITE}" opacity="0.9"/>
  <g fill="{GREEN}" opacity="0.9"><rect x="-24" y="-6" width="46" height="5"/><rect x="-24" y="8" width="46" height="5"/></g>
  <rect x="-32" y="-56" width="62" height="24" rx="10" fill="{WHITE}" stroke="#D9E4EC" stroke-width="2"/>
  <circle cx="-20" cy="-44" r="3" fill="#D9E4EC"/><circle cx="-4" cy="-48" r="3" fill="#D9E4EC"/>
  <circle cx="12" cy="-42" r="3" fill="#D9E4EC"/><circle cx="22" cy="-48" r="2.5" fill="#D9E4EC"/>
  <path d="M28 -54 C40 -64 50 -60 46 -50" stroke="{GOLD}" stroke-width="3" fill="none"/>"""


def icon_snowman(p):
    return f"""
  <circle cx="0" cy="34" r="28" fill="{SNOW}" stroke="#C9D8E4" stroke-width="2"/>
  <circle cx="0" cy="-6" r="21" fill="{SNOW}" stroke="#C9D8E4" stroke-width="2"/>
  <circle cx="0" cy="-38" r="16" fill="{SNOW}" stroke="#C9D8E4" stroke-width="2"/>
  <path d="M-19 -22 Q0 -14 19 -22 L20 -14 Q0 -6 -20 -14Z" fill="{GREEN}"/>
  <path d="M10 -16 L22 8 L14 10 L6 -14Z" fill="{GREEN}"/>
  <path d="M10 -2 L21 1 M12 4 L20 6" stroke="{GREEN_D}" stroke-width="2"/>
  <rect x="-20" y="-55" width="40" height="5" rx="2" fill="{INK}"/>
  <rect x="-13" y="-76" width="26" height="23" rx="2" fill="{INK}"/>
  <rect x="-13" y="-61" width="26" height="5" fill="{RED}"/>
  <circle cx="-6" cy="-41" r="2.5" fill="{INK}"/><circle cx="6" cy="-41" r="2.5" fill="{INK}"/>
  <path d="M0 -36 L18 -33 L0 -32Z" fill="{ORANGE}"/>
  <path d="M-7 -30 Q0 -26 7 -30" stroke="{INK}" stroke-width="1.5" fill="none" stroke-linecap="round"/>
  <circle cx="0" cy="-4" r="3" fill="{INK}"/><circle cx="0" cy="8" r="3" fill="{INK}"/><circle cx="0" cy="26" r="3" fill="{INK}"/>
  <path d="M-19 -8 L-44 -26 M-36 -20 L-42 -34 M19 -8 L44 -24 M37 -19 L46 -14" stroke="{BROWN_D}" stroke-width="3" stroke-linecap="round"/>"""


def icon_mitten(p):
    return f"""
  <path d="M-24 40 L-24 -12 C-24 -50 30 -52 30 -12 L30 40Z" fill="{RED}" stroke="{RED_D}" stroke-width="2.5"/>
  <path d="M-22 14 C-44 12 -52 -12 -40 -20 C-32 -26 -24 -16 -22 -6" fill="{RED}" stroke="{RED_D}" stroke-width="2.5"/>
  <g fill="{WHITE}" opacity="0.85">
    <polygon points="{star_points(4, -14, 9, 4, 6)}"/>
    <circle cx="-10" cy="10" r="2.5"/><circle cx="18" cy="10" r="2.5"/><circle cx="4" cy="16" r="2.5"/>
  </g>
  <path d="M-24 0 L30 0" stroke="{WHITE}" stroke-width="3" stroke-dasharray="4 4" opacity="0.7"/>
  <rect x="-30" y="34" width="66" height="22" rx="8" fill="{WHITE}" stroke="#D9E4EC" stroke-width="2"/>
  <path d="M-22 40 L-22 50 M-12 40 L-12 50 M-2 40 L-2 50 M8 40 L8 50 M18 40 L18 50 M28 40 L28 50" stroke="#D9E4EC" stroke-width="3"/>
  <path d="M34 50 C48 58 52 40 44 30" stroke="{GOLD}" stroke-width="3" fill="none" stroke-linecap="round"/>"""


def icon_gingerbread(p):
    return f"""
  <g stroke="{BROWN}" stroke-width="22" stroke-linecap="round" fill="none">
    <path d="M-38 -6 L0 -14 L38 -6"/><path d="M-6 14 L-22 46 M6 14 L22 46"/>
  </g>
  <ellipse cx="0" cy="4" rx="22" ry="26" fill="{BROWN}"/>
  <circle cx="0" cy="-36" r="19" fill="{BROWN}"/>
  <g stroke="{WHITE}" stroke-width="3" fill="none" stroke-linecap="round">
    <path d="M-44 -12 q3 6 0 12 M44 -12 q-3 6 0 12"/>
    <path d="M-30 42 q6 4 0 10 M30 42 q-6 4 0 10"/>
    <path d="M-8 -30 Q0 -24 8 -30"/>
  </g>
  <circle cx="-7" cy="-40" r="3" fill="{WHITE}"/><circle cx="7" cy="-40" r="3" fill="{WHITE}"/>
  <circle cx="0" cy="-6" r="4" fill="{RED}"/><circle cx="0" cy="6" r="4" fill="{GREEN_L}"/><circle cx="0" cy="18" r="4" fill="{RED}"/>
  <path d="M-10 -18 L0 -14 L10 -18 L10 -10 L0 -14 L-10 -10Z" fill="{RED}"/>"""


def holly_leaf(rot, fill=GREEN):
    d = ("M0 0 C6 -4 10 -2 14 -6 C14 -12 20 -14 24 -12 C26 -18 32 -20 36 -18 C38 -24 46 -26 52 -24 "
         "C48 -18 50 -12 46 -8 C48 -2 44 2 40 2 C40 8 34 10 30 8 C28 14 22 14 18 12 C14 16 6 12 0 0Z")
    return (f'<g transform="rotate({rot})"><path d="{d}" fill="{fill}" stroke="{GREEN_D}" stroke-width="2"/>'
            f'<path d="M2 0 C18 -4 34 -10 48 -22" stroke="{GREEN_D}" stroke-width="1.5" fill="none"/></g>')


def icon_holly(p):
    return f"""
  <g transform="scale(1.15)">
    {holly_leaf(-30)}{holly_leaf(195, GREEN_L)}{holly_leaf(95)}
    <circle cx="-6" cy="-4" r="9" fill="{RED}" stroke="{RED_D}" stroke-width="1.5"/>
    <circle cx="8" cy="-6" r="9" fill="{RED}" stroke="{RED_D}" stroke-width="1.5"/>
    <circle cx="1" cy="8" r="9" fill="{RED}" stroke="{RED_D}" stroke-width="1.5"/>
    <circle cx="-9" cy="-7" r="2.5" fill="{WHITE}" opacity="0.7"/><circle cx="5" cy="-9" r="2.5" fill="{WHITE}" opacity="0.7"/>
    <circle cx="-2" cy="5" r="2.5" fill="{WHITE}" opacity="0.7"/>
  </g>"""


def icon_candle(p):
    return f"""
  <defs><radialGradient id="{p}glow"><stop offset="0" stop-color="{GOLD_L}" stop-opacity="0.8"/>
  <stop offset="1" stop-color="{GOLD_L}" stop-opacity="0"/></radialGradient></defs>
  <circle cx="0" cy="-42" r="36" fill="url(#{p}glow)"/>
  <path d="M0 -62 C10 -50 10 -40 0 -32 C-10 -40 -10 -50 0 -62Z" fill="{ORANGE}"/>
  <path d="M0 -54 C5 -46 5 -40 0 -35 C-5 -40 -5 -46 0 -54Z" fill="{GOLD_L}"/>
  <line x1="0" y1="-32" x2="0" y2="-24" stroke="{INK}" stroke-width="2"/>
  <rect x="-16" y="-24" width="32" height="64" rx="3" fill="{CREAM}" stroke="#E2CFA8" stroke-width="2"/>
  <path d="M-16 -20 L-16 -8 C-16 -2 -10 -2 -10 -8 L-10 -16 C-10 -10 -4 -10 -4 -16 L4 -16 L4 2 C4 8 10 8 10 2 L10 -16 L16 -16 L16 -24 L-16 -24Z" fill="{WHITE}"/>
  <rect x="-8" y="-20" width="5" height="54" rx="2" fill="{WHITE}" opacity="0.6"/>
  <ellipse cx="0" cy="44" rx="44" ry="10" fill="{GOLD}" stroke="{GOLD_D}" stroke-width="2"/>
  <path d="M-44 44 Q0 62 44 44" fill="{GOLD_D}"/>
  <g transform="translate(-26 38) scale(0.45)">{holly_leaf(200)}{holly_leaf(160, GREEN_L)}</g>
  <circle cx="-26" cy="38" r="4.5" fill="{RED}"/><circle cx="-20" cy="42" r="4" fill="{RED}"/>"""


def icon_cocoa(p):
    return f"""
  <path d="M-12 -40 C-20 -48 -4 -54 -12 -62 M6 -38 C-2 -46 14 -52 6 -60 M22 -40 C14 -48 30 -54 22 -62"
        stroke="{CREAM}" stroke-width="4" fill="none" stroke-linecap="round" opacity="0.75"/>
  <path d="M30 -10 C56 -10 56 34 30 30" stroke="{RED_D}" stroke-width="12" fill="none"/>
  <path d="M30 -10 C56 -10 56 34 30 30" stroke="{RED}" stroke-width="7" fill="none"/>
  <path d="M-38 -24 L38 -24 L32 44 C31 52 25 56 18 56 L-18 56 C-25 56 -31 52 -32 44Z" fill="{RED}" stroke="{RED_D}" stroke-width="2.5"/>
  <ellipse cx="0" cy="-24" rx="38" ry="9" fill="{BROWN_D}" stroke="{RED_D}" stroke-width="2.5"/>
  <rect x="-22" y="-34" width="14" height="12" rx="3" fill="{WHITE}" transform="rotate(-12 -15 -28)"/>
  <rect x="-4" y="-36" width="14" height="12" rx="3" fill="#FFE8EE"/>
  <rect x="14" y="-33" width="13" height="11" rx="3" fill="{WHITE}" transform="rotate(15 20 -27)"/>
  <g fill="{WHITE}" opacity="0.9">
    <polygon points="{star_points(0, 16, 14, 6, 6)}"/>
    <circle cx="-22" cy="4" r="3"/><circle cx="22" cy="4" r="3"/><circle cx="-18" cy="34" r="3"/><circle cx="18" cy="34" r="3"/>
  </g>"""


def icon_wreath(p):
    rnd = random.Random(15)
    leaves = []
    for i in range(30):
        a = i * 12 + rnd.uniform(-3, 3)
        rad = 40 + rnd.uniform(-9, 9)
        x, y = rad * math.cos(math.radians(a)), rad * math.sin(math.radians(a))
        col = rnd.choice([GREEN, GREEN_L, GREEN_D])
        leaves.append(f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="11" ry="5" fill="{col}" '
                      f'transform="rotate({a + rnd.uniform(30, 70):.0f} {x:.1f} {y:.1f})"/>')
    berries = "".join(
        f'<circle cx="{40 * math.cos(math.radians(a)):.1f}" cy="{40 * math.sin(math.radians(a)):.1f}" r="4.5" fill="{RED}"/>'
        for a in (200, 230, 260, 300, 330, 0, 20, 160, 140))
    return f"""
  <circle r="40" fill="none" stroke="{GREEN_D}" stroke-width="28"/>
  {''.join(leaves)}
  {berries}
  <g transform="translate(0 40)">
    <path d="M-4 4 L-18 34 L-10 30 L-6 38 L2 6Z" fill="{RED}" stroke="{RED_D}" stroke-width="1.5"/>
    <path d="M4 4 L18 34 L10 30 L6 38 L-2 6Z" fill="{RED}" stroke="{RED_D}" stroke-width="1.5"/>
    <path d="M0 0 C-12 -16 -34 -10 -28 2 C-22 12 -8 6 0 0Z" fill="{RED}" stroke="{RED_D}" stroke-width="2"/>
    <path d="M0 0 C12 -16 34 -10 28 2 C22 12 8 6 0 0Z" fill="{RED}" stroke="{RED_D}" stroke-width="2"/>
    <circle r="6" fill="{RED_D}"/>
  </g>"""


def icon_moon(p):
    return f"""
  <defs><mask id="{p}moon"><rect x="-70" y="-70" width="140" height="140" fill="#000"/>
  <circle cx="-6" cy="0" r="46" fill="#fff"/><circle cx="18" cy="-14" r="40" fill="#000"/></mask></defs>
  <circle cx="-6" cy="0" r="52" fill="{GOLD_L}" opacity="0.15" mask="url(#{p}moon)"/>
  <circle cx="-6" cy="0" r="46" fill="{GOLD_L}" mask="url(#{p}moon)"/>
  <g mask="url(#{p}moon)" fill="{GOLD}" opacity="0.7">
    <circle cx="-34" cy="14" r="6"/><circle cx="-20" cy="34" r="4"/><circle cx="-40" cy="-10" r="3"/>
  </g>
  {star(30, 20, 13, GOLD_L, GOLD, 1.5)}{star(44, -40, 8, GOLD_L, GOLD, 1)}
  {sparkle(10, 46, 6, WHITE)}{sparkle(52, 0, 5, WHITE)}{sparkle(-50, -46, 5, WHITE)}"""


def icon_santa_hat(p):
    return f"""
  <path d="M-46 30 C-44 -14 -18 -52 18 -48 C40 -46 52 -30 50 -8 C46 -22 36 -30 26 -28 C14 -26 26 0 30 28Z"
        fill="{RED}" stroke="{RED_D}" stroke-width="2.5" stroke-linejoin="round"/>
  <path d="M-30 24 C-28 -10 -10 -38 14 -40" stroke="{WHITE}" stroke-width="4" fill="none" opacity="0.3" stroke-linecap="round"/>
  <circle cx="50" cy="-4" r="13" fill="{SNOW}" stroke="#C9D8E4" stroke-width="2"/>
  <rect x="-56" y="22" width="98" height="26" rx="13" fill="{SNOW}" stroke="#C9D8E4" stroke-width="2"/>
  <g fill="#C9D8E4"><circle cx="-40" cy="34" r="3"/><circle cx="-22" cy="30" r="3"/><circle cx="-4" cy="38" r="3"/>
  <circle cx="14" cy="31" r="3"/><circle cx="30" cy="38" r="3"/><circle cx="46" cy="-8" r="3"/><circle cx="54" cy="0" r="2.5"/></g>"""


def icon_cabin(p):
    return f"""
  <path d="M26 -40 C36 -50 22 -56 32 -64" stroke="{CREAM}" stroke-width="4" fill="none" opacity="0.6" stroke-linecap="round"/>
  <rect x="18" y="-38" width="14" height="26" fill="{BROWN_D}"/>
  <rect x="15" y="-42" width="20" height="7" rx="3" fill="{SNOW}"/>
  <rect x="-42" y="-4" width="84" height="56" fill="{BROWN}" stroke="{BROWN_D}" stroke-width="2"/>
  <g stroke="{BROWN_D}" stroke-width="2" opacity="0.6"><line x1="-42" y1="10" x2="42" y2="10"/>
  <line x1="-42" y1="24" x2="42" y2="24"/><line x1="-42" y1="38" x2="42" y2="38"/></g>
  <polygon points="0,-44 -54,0 54,0" fill="{RED_D}" stroke="{INK}" stroke-width="2" stroke-linejoin="round"/>
  <path d="M0 -44 L-54 0 L-46 6 C-40 0 -36 4 -30 -2 C-24 4 -20 -4 -12 -6 L0 -16 L12 -6 C20 -4 24 4 30 -2 C36 4 40 0 46 6 L54 0Z" fill="{SNOW}"/>
  <rect x="-32" y="12" width="22" height="20" fill="{GOLD_L}" stroke="{BROWN_D}" stroke-width="3"/>
  <path d="M-21 12 L-21 32 M-32 22 L-10 22" stroke="{BROWN_D}" stroke-width="2.5"/>
  <rect x="8" y="16" width="22" height="36" rx="2" fill="{GREEN_D}" stroke="{INK}" stroke-width="2"/>
  <circle cx="25" cy="35" r="2" fill="{GOLD}"/>
  <circle cx="19" cy="28" r="6" fill="none" stroke="{GREEN_L}" stroke-width="3"/>
  <path d="M-60 52 Q-30 44 0 52 Q30 60 60 52 L60 58 L-60 58Z" fill="{SNOW}"/>"""


def icon_reindeer(p):
    antler = ("M-14 -30 C-20 -44 -26 -52 -38 -58 M-24 -46 C-34 -46 -40 -40 -46 -38 "
              "M-30 -54 C-30 -62 -26 -66 -22 -70")
    return f"""
  <g stroke="{BROWN_L}" stroke-width="6" fill="none" stroke-linecap="round">
    <path d="{antler}"/><path d="{antler}" transform="scale(-1 1)"/>
  </g>
  <ellipse cx="-30" cy="-18" rx="14" ry="7" fill="{BROWN}" transform="rotate(-30 -30 -18)"/>
  <ellipse cx="30" cy="-18" rx="14" ry="7" fill="{BROWN}" transform="rotate(30 30 -18)"/>
  <ellipse cx="-30" cy="-18" rx="8" ry="3" fill="#E7B98A" transform="rotate(-30 -30 -18)"/>
  <ellipse cx="30" cy="-18" rx="8" ry="3" fill="#E7B98A" transform="rotate(30 30 -18)"/>
  <path d="M-26 -14 C-28 -40 28 -40 26 -14 C26 10 18 44 0 46 C-18 44 -26 10 -26 -14Z" fill="{BROWN}" stroke="{BROWN_D}" stroke-width="2"/>
  <ellipse cx="0" cy="32" rx="18" ry="14" fill="#E7B98A"/>
  <circle cx="-11" cy="-8" r="5" fill="{INK}"/><circle cx="11" cy="-8" r="5" fill="{INK}"/>
  <circle cx="-9" cy="-10" r="1.8" fill="{WHITE}"/><circle cx="13" cy="-10" r="1.8" fill="{WHITE}"/>
  <circle cx="-18" cy="6" r="4" fill="#E58C7A" opacity="0.6"/><circle cx="18" cy="6" r="4" fill="#E58C7A" opacity="0.6"/>
  <circle cx="0" cy="24" r="16" fill="{RED}" opacity="0.25"/>
  <circle cx="0" cy="24" r="10" fill="{RED}" stroke="{RED_D}" stroke-width="1.5"/>
  <circle cx="-3" cy="21" r="3" fill="{WHITE}" opacity="0.7"/>
  <path d="M-6 38 Q0 42 6 38" stroke="{BROWN_D}" stroke-width="2" fill="none" stroke-linecap="round"/>"""


def icon_snow_globe(p):
    rnd = random.Random(20)
    flakes = "".join(f'<circle cx="{rnd.uniform(-32, 32):.0f}" cy="{rnd.uniform(-40, 14):.0f}" r="{rnd.uniform(1.2, 2.6):.1f}" fill="{WHITE}"/>'
                     for _ in range(16))
    return f"""
  <defs><radialGradient id="{p}glass" cx="0.35" cy="0.3"><stop offset="0" stop-color="#E9F6FF"/>
  <stop offset="1" stop-color="#7FB6E0"/></radialGradient>
  <clipPath id="{p}globe"><circle cx="0" cy="-10" r="42"/></clipPath></defs>
  <circle cx="0" cy="-10" r="42" fill="url(#{p}glass)" opacity="0.9"/>
  <g clip-path="url(#{p}globe)">
    <ellipse cx="0" cy="26" rx="50" ry="14" fill="{SNOW}"/>
    <polygon points="0,-30 -14,-6 14,-6" fill="{GREEN_D}"/><polygon points="0,-18 -18,12 18,12" fill="{GREEN_D}"/>
    <rect x="-3" y="12" width="6" height="8" fill="{BROWN}"/>
    {star(0, -32, 5, GOLD, GOLD_D, 1)}
    {flakes}
  </g>
  <circle cx="0" cy="-10" r="42" fill="none" stroke="{WHITE}" stroke-width="2.5" opacity="0.8"/>
  <path d="M-26 -34 A34 34 0 0 1 -6 -46" stroke="{WHITE}" stroke-width="5" fill="none" stroke-linecap="round" opacity="0.8"/>
  <path d="M-36 28 L36 28 L44 54 L-44 54Z" fill="{BROWN}" stroke="{BROWN_D}" stroke-width="2"/>
  <rect x="-40" y="24" width="80" height="8" rx="3" fill="{GOLD}" stroke="{GOLD_D}" stroke-width="1.5"/>
  <rect x="-20" y="36" width="40" height="12" rx="2" fill="{GOLD}" opacity="0.9"/>"""


def icon_letter(p):
    return f"""
  <g transform="rotate(-6)">
    <rect x="-52" y="-32" width="104" height="70" rx="4" fill="{CREAM}" stroke="#D8C49A" stroke-width="2"/>
    <path d="M-52 -32 L0 10 L52 -32" fill="#F6E6C4" stroke="#D8C49A" stroke-width="2" stroke-linejoin="round"/>
    <path d="M-52 38 L-12 4 M52 38 L12 4" stroke="#D8C49A" stroke-width="2"/>
    <rect x="28" y="-26" width="18" height="22" fill="{GREEN}" stroke="{WHITE}" stroke-width="2" stroke-dasharray="3 2"/>
    <polygon points="{star_points(37, -15, 6, 2.6)}" fill="{GOLD_L}"/>
    <circle cx="0" cy="10" r="12" fill="{RED}" stroke="{RED_D}" stroke-width="2"/>
    <path d="M0 16 C-10 8 -6 0 0 5 C6 0 10 8 0 16Z" fill="{RED_D}"/>
  </g>
  {sparkle(-50, -46, 8)}{sparkle(50, 44, 7)}"""


def icon_lantern(p):
    return f"""
  <defs><radialGradient id="{p}lamp"><stop offset="0" stop-color="{GOLD_L}"/><stop offset="0.6" stop-color="{GOLD}"/>
  <stop offset="1" stop-color="{ORANGE}"/></radialGradient></defs>
  <circle cx="0" cy="8" r="56" fill="{GOLD_L}" opacity="0.14"/>
  <circle cx="0" cy="-58" r="8" fill="none" stroke="{INK}" stroke-width="4"/>
  <polygon points="-16,-50 16,-50 30,-34 -30,-34" fill="{INK}"/>
  <rect x="-30" y="-36" width="60" height="6" rx="2" fill="{GOLD_D}"/>
  <rect x="-24" y="-30" width="48" height="66" fill="url(#{p}lamp)" stroke="{INK}" stroke-width="3"/>
  <line x1="0" y1="-30" x2="0" y2="36" stroke="{INK}" stroke-width="3"/>
  <line x1="-24" y1="3" x2="24" y2="3" stroke="{INK}" stroke-width="2" opacity="0.4"/>
  <rect x="-6" y="0" width="12" height="22" fill="{CREAM}"/>
  <path d="M0 -14 C6 -6 6 -2 0 2 C-6 -2 -6 -6 0 -14Z" fill="{ORANGE}"/>
  <rect x="-32" y="36" width="64" height="8" rx="2" fill="{GOLD_D}"/>
  <polygon points="-26,44 26,44 20,52 -20,52" fill="{INK}"/>
  <path d="M-36 -36 C-46 -40 -48 -30 -40 -26 M36 -36 C46 -40 48 -30 40 -26" stroke="{RED}" stroke-width="5" fill="none" stroke-linecap="round"/>
  <g transform="translate(0 -36)">
    <path d="M0 0 C-10 -8 -24 -4 -20 4 C-16 10 -6 4 0 0Z" fill="{RED}"/><path d="M0 0 C10 -8 24 -4 20 4 C16 10 6 4 0 0Z" fill="{RED}"/>
    <circle r="4" fill="{RED_D}"/>
  </g>"""


def icon_sweet(p):
    return f"""
  <g transform="rotate(-18)">
    <polygon points="-34,0 -62,-22 -56,0 -62,22" fill="{GOLD}" stroke="{GOLD_D}" stroke-width="2" stroke-linejoin="round"/>
    <polygon points="34,0 62,-22 56,0 62,22" fill="{GOLD}" stroke="{GOLD_D}" stroke-width="2" stroke-linejoin="round"/>
    <path d="M-60 -14 L-40 -2 M-60 14 L-40 2 M60 -14 L40 -2 M60 14 L40 2" stroke="{GOLD_D}" stroke-width="1.5"/>
    <circle r="34" fill="{WHITE}" stroke="{RED_D}" stroke-width="2.5"/>
    <g fill="{RED}">
      <path d="M0 0 L0 -34 A34 34 0 0 1 29.4 -17Z"/><path d="M0 0 L29.4 17 A34 34 0 0 1 0 34Z"/>
      <path d="M0 0 L-29.4 17 A34 34 0 0 1 -29.4 -17Z"/>
    </g>
    <circle r="9" fill="{WHITE}" stroke="{RED}" stroke-width="2"/>
    <ellipse cx="-12" cy="-18" rx="7" ry="12" fill="{WHITE}" opacity="0.4" transform="rotate(40 -12 -18)"/>
  </g>
  {sparkle(40, -44, 8)}{sparkle(-44, 46, 7)}"""


def icon_north_star(p):
    rays = "".join(
        f'<polygon points="0,-8 {70 if i % 2 == 0 else 52},0 0,8" fill="{GOLD_L}" opacity="{0.5 if i % 2 == 0 else 0.3}" transform="rotate({i * 22.5})"/>'
        for i in range(16))
    return f"""
  <defs><radialGradient id="{p}halo"><stop offset="0" stop-color="{GOLD_L}" stop-opacity="0.9"/>
  <stop offset="1" stop-color="{GOLD_L}" stop-opacity="0"/></radialGradient></defs>
  <circle r="70" fill="url(#{p}halo)"/>
  {rays}
  <polygon points="{star_points(0, 0, 58, 16, 4, -90)}" fill="{GOLD}" stroke="{GOLD_D}" stroke-width="2.5" stroke-linejoin="round"/>
  <polygon points="{star_points(0, 0, 36, 10, 4, -45)}" fill="{GOLD_L}" stroke="{GOLD_D}" stroke-width="1.5"/>
  <circle r="9" fill="{WHITE}"/>
  {sparkle(-50, -46, 7, WHITE)}{sparkle(52, 44, 6, WHITE)}{sparkle(50, -50, 5, WHITE)}"""


# day: (title, icon fn, background)
DAYS = {
    1: ("Shining Star", icon_star, "navy"),
    2: ("Christmas Tree", icon_tree, "red"),
    3: ("Wrapped Gift", icon_gift, "green"),
    4: ("Candy Cane", icon_candy_cane, "teal"),
    5: ("Jingle Bell", icon_bell, "plum"),
    6: ("Bauble", icon_bauble, "green"),
    7: ("Snowflake", icon_snowflake, "navy"),
    8: ("Stocking", icon_stocking, "teal"),
    9: ("Snowman", icon_snowman, "red"),
    10: ("Mitten", icon_mitten, "green"),
    11: ("Gingerbread", icon_gingerbread, "navy"),
    12: ("Holly", icon_holly, "plum"),
    13: ("Candle", icon_candle, "teal"),
    14: ("Hot Cocoa", icon_cocoa, "green"),
    15: ("Wreath", icon_wreath, "red"),
    16: ("Winter Moon", icon_moon, "navy"),
    17: ("Santa Hat", icon_santa_hat, "teal"),
    18: ("Snowy Cabin", icon_cabin, "plum"),
    19: ("Reindeer", icon_reindeer, "green"),
    20: ("Snow Globe", icon_snow_globe, "red"),
    21: ("Letter to Santa", icon_letter, "navy"),
    22: ("Lantern", icon_lantern, "green"),
    23: ("Peppermint", icon_sweet, "teal"),
    24: ("Christmas Eve", icon_north_star, "red"),
}


# ---------------------------------------------------------------- door
def door_body(day, p):
    """Inner markup of a 300x300 door. All ids are prefixed with `p`."""
    title, icon_fn, bg = DAYS[day]
    top, bottom = BACKGROUNDS[bg]
    special = day == 24
    rnd = random.Random(day * 7919)

    snow = "".join(
        f'<circle cx="{rnd.uniform(28, 272):.0f}" cy="{rnd.uniform(50, 272):.0f}" '
        f'r="{rnd.choice([1.2, 1.6, 2.2, 2.8])}" fill="#fff" opacity="{rnd.uniform(0.15, 0.45):.2f}"/>'
        for _ in range(26))

    # wavy snow cap along the top edge, with a few drips
    cap = "M6 30 L6 22 Q6 6 22 6 L278 6 Q294 6 294 22 L294 30 "
    x = 294
    while x > 6:
        nx = max(6, x - rnd.uniform(18, 30))
        depth = rnd.uniform(30, 40) if rnd.random() > 0.25 else rnd.uniform(44, 52)
        cap += f"Q{(x + nx) / 2:.0f} {depth:.0f} {nx:.0f} {rnd.uniform(28, 33):.0f} "
        x = nx
    cap += "Z"

    frame = GOLD_L if special else GOLD
    extra = ""
    if special:
        extra = (f'<rect x="30" y="30" width="240" height="240" rx="10" fill="none" stroke="{GOLD_L}" '
                 f'stroke-width="1.5" stroke-dasharray="2 6" opacity="0.8"/>'
                 f'<text x="150" y="203" text-anchor="middle" font-family="{FONT}" font-style="italic" '
                 f'font-size="16" letter-spacing="1" fill="{GOLD_L}">Christmas Eve</text>')

    return f"""
  <defs>
    <linearGradient id="{p}bg" x1="0" y1="0" x2="0.3" y2="1">
      <stop offset="0" stop-color="{top}"/><stop offset="1" stop-color="{bottom}"/>
    </linearGradient>
    <linearGradient id="{p}num" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{GOLD_L}"/><stop offset="0.55" stop-color="{GOLD}"/><stop offset="1" stop-color="{GOLD_D}"/>
    </linearGradient>
    <radialGradient id="{p}vig" cx="0.5" cy="0.42" r="0.7">
      <stop offset="0.6" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity="0.35"/>
    </radialGradient>
  </defs>
  <rect x="2" y="2" width="296" height="296" rx="22" fill="{GOLD_D}"/>
  <rect x="6" y="6" width="288" height="288" rx="18" fill="url(#{p}bg)"/>
  <rect x="6" y="6" width="288" height="288" rx="18" fill="url(#{p}vig)"/>
  {snow}
  <rect x="20" y="20" width="260" height="260" rx="12" fill="none" stroke="{CREAM}" stroke-opacity="0.28" stroke-width="2"/>
  {extra}
  <g fill="{frame}">
    <circle cx="32" cy="268" r="3.5"/><circle cx="268" cy="268" r="3.5"/>
    <circle cx="32" cy="58" r="3.5"/><circle cx="268" cy="58" r="3.5"/>
  </g>
  <path d="{cap}" fill="{SNOW}"/>
  <path d="{cap}" fill="none" stroke="#C9D8E4" stroke-width="1.2" opacity="0.7"/>
  <rect x="6" y="6" width="288" height="288" rx="18" fill="none" stroke="{frame}" stroke-width="5"/>
  <g transform="translate(150 {128 if not special else 112}) scale({1.0 if not special else 0.82})">{icon_fn(p)}
  </g>
  <text x="152" y="{266}" text-anchor="middle" font-family="{FONT}" font-weight="bold"
        font-size="{56 if not special else 62}" fill="#000" opacity="0.35">{day}</text>
  <text x="150" y="{263}" text-anchor="middle" font-family="{FONT}" font-weight="bold"
        font-size="{56 if not special else 62}" fill="url(#{p}num)" stroke="{GOLD_D}" stroke-width="1"
        paint-order="stroke">{day}</text>
  <g transform="translate(274 160)">
    <circle r="7" fill="{GOLD_D}"/><circle r="5.5" fill="{GOLD}"/><circle cx="-1.8" cy="-1.8" r="2" fill="{GOLD_L}"/>
  </g>"""


def door_svg(day):
    p = f"d{day:02d}-"
    title = DAYS[day][0]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 300" width="300" height="300" '
            f'role="img" aria-label="Day {day}: {title}">\n  <title>Day {day} — {title}</title>'
            f'{door_body(day, p)}\n</svg>\n')


# ---------------------------------------------------------------- full board
def calendar_svg():
    W, H = 1800, 1550
    cols, size, gap = 6, 250, 30
    left = (W - (cols * size + (cols - 1) * gap)) // 2
    top = 340
    rnd = random.Random(2026)

    grain = []
    for i in range(70):
        y = 40 + i * 20 + rnd.uniform(-6, 6)
        amp = rnd.uniform(2, 7)
        d = f"M40 {y:.0f} " + " ".join(
            f"Q{x + 60:.0f} {y + rnd.uniform(-amp, amp):.1f} {x + 120:.0f} {y + rnd.uniform(-amp / 2, amp / 2):.1f}"
            for x in range(40, W - 40, 120))
        grain.append(f'<path d="{d}" stroke="{rnd.choice(["#3E2410", "#6E4520", "#2E1A0B"])}" '
                     f'stroke-width="{rnd.uniform(0.8, 2.6):.1f}" fill="none" opacity="{rnd.uniform(0.12, 0.35):.2f}"/>')
    knots = "".join(
        f'<ellipse cx="{rnd.uniform(120, W - 120):.0f}" cy="{rnd.uniform(120, H - 120):.0f}" rx="{rnd.uniform(10, 18):.0f}" '
        f'ry="{rnd.uniform(4, 7):.0f}" fill="none" stroke="#3E2410" stroke-width="2" opacity="0.25"/>'
        for _ in range(7))

    # garland of pine needles + string lights across the top
    garland = []
    for i in range(160):
        t = i / 159
        x = 60 + t * (W - 120)
        y = 86 + math.sin(t * math.pi * 3) * 22 + rnd.uniform(-10, 10)
        garland.append(f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{rnd.uniform(14, 22):.0f}" ry="6" '
                       f'fill="{rnd.choice([GREEN, GREEN_D, "#2A7048", GREEN_L])}" '
                       f'transform="rotate({rnd.uniform(-60, 60):.0f} {x:.0f} {y:.0f})"/>')
    lights = []
    colors = ["#FF5A5A", GOLD_L, "#6FD3FF", "#8CF08C", "#FF9BE0"]
    for i in range(28):
        t = (i + 0.5) / 28
        x = 60 + t * (W - 120)
        y = 100 + math.sin(t * math.pi * 3) * 22
        c = colors[i % len(colors)]
        lights.append(f'<circle cx="{x:.0f}" cy="{y + 10:.0f}" r="16" fill="{c}" opacity="0.25"/>'
                      f'<rect x="{x - 4:.0f}" y="{y - 2:.0f}" width="8" height="6" fill="#333"/>'
                      f'<ellipse cx="{x:.0f}" cy="{y + 10:.0f}" rx="6" ry="9" fill="{c}"/>')

    doors = []
    for day in range(1, 25):
        r, c = divmod(day - 1, cols)
        x, y = left + c * (size + gap), top + r * (size + gap)
        doors.append(f'<rect x="{x + 6}" y="{y + 10}" width="{size}" height="{size}" rx="20" fill="#000" opacity="0.35"/>'
                     f'<svg x="{x}" y="{y}" width="{size}" height="{size}" viewBox="0 0 300 300">'
                     f'{door_body(day, f"c{day:02d}-")}</svg>')

    nails = "".join(f'<circle cx="{x}" cy="{y}" r="9" fill="#5a5a5a"/><circle cx="{x - 2}" cy="{y - 2}" r="4" fill="#bbb"/>'
                    for x, y in ((50, 50), (W - 50, 50), (50, H - 50), (W - 50, H - 50)))

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="LeMSIC Advent Calendar">
  <title>LeMSIC Advent Calendar</title>
  <defs>
    <linearGradient id="wood" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#8A5A2E"/><stop offset="0.5" stop-color="#744822"/><stop offset="1" stop-color="#5A3517"/>
    </linearGradient>
    <linearGradient id="frame" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#4A2A10"/><stop offset="1" stop-color="#2C1808"/>
    </linearGradient>
    <linearGradient id="title" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{GOLD_L}"/><stop offset="0.6" stop-color="{GOLD}"/><stop offset="1" stop-color="{GOLD_D}"/>
    </linearGradient>
    <radialGradient id="boardvig" cx="0.5" cy="0.45" r="0.75">
      <stop offset="0.55" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity="0.45"/>
    </radialGradient>
  </defs>
  <rect width="{W}" height="{H}" rx="34" fill="url(#frame)"/>
  <rect x="26" y="26" width="{W - 52}" height="{H - 52}" rx="20" fill="url(#wood)"/>
  <g>{''.join(grain)}{knots}</g>
  <rect x="26" y="26" width="{W - 52}" height="{H - 52}" rx="20" fill="url(#boardvig)"/>
  <rect x="26" y="26" width="{W - 52}" height="{H - 52}" rx="20" fill="none" stroke="#C99158" stroke-opacity="0.35" stroke-width="3"/>
  {nails}
  <path d="M60 100 Q{W / 4:.0f} 140 {W / 2:.0f} 100 T{W - 60} 100" stroke="#1E1E1E" stroke-width="2" fill="none" opacity="0.6"/>
  {''.join(garland)}
  {''.join(lights)}

  <g transform="translate({W / 2} 0)">
    <text x="4" y="232" text-anchor="middle" font-family="{FONT}" font-weight="bold" font-size="104" letter-spacing="10" fill="#000" opacity="0.4">LeMSIC</text>
    <text x="0" y="226" text-anchor="middle" font-family="{FONT}" font-weight="bold" font-size="104" letter-spacing="10"
          fill="url(#title)" stroke="{GOLD_D}" stroke-width="2" paint-order="stroke">LeMSIC</text>
    <path d="M-330 252 L330 252 L310 274 L330 296 L-330 296 L-310 274Z" fill="{RED_D}"/>
    <path d="M-300 248 L300 248 L300 300 L-300 300Z" fill="#B02A33" stroke="{GOLD}" stroke-width="2"/>
    <text x="0" y="285" text-anchor="middle" font-family="{FONT}" font-weight="bold" font-size="34" letter-spacing="9" fill="{CREAM}">ADVENT CALENDAR</text>
    {star(-372, 200, 22, GOLD, GOLD_D, 2)}{star(372, 200, 22, GOLD, GOLD_D, 2)}
    {sparkle(-420, 150, 10)}{sparkle(420, 150, 10)}
  </g>

  {''.join(doors)}

  <text x="{W / 2}" y="{H - 46}" text-anchor="middle" font-family="{FONT}" font-style="italic" font-size="28"
        letter-spacing="2" fill="{CREAM}" opacity="0.85">Open one door each day · 1 – 24 December</text>
</svg>
"""


def main():
    os.makedirs(DOOR_DIR, exist_ok=True)
    for day in DAYS:
        with open(os.path.join(DOOR_DIR, f"day-{day:02d}.svg"), "w") as f:
            f.write(door_svg(day))
    with open(os.path.join(ROOT, "images", "advent-calendar.svg"), "w") as f:
        f.write(calendar_svg())
    print(f"Wrote {len(DAYS)} doors + advent-calendar.svg")


if __name__ == "__main__":
    main()
