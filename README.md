# LeMSIC Advent Calendar

Artwork for the LeMSIC Christmas advent calendar (1–24 December).

## The tree calendar (main design)

`images/lemsic-tree-calendar.svg` (PNG: `images/png/lemsic-tree-calendar.png`)

The tree follows the LeMSIC emblem: a cedar made of a serpent winding around a staff,
framed by laurel branches, on LeMSIC blue (`#3C6BAD`). Ornaments for days 1–23 hang from
the serpent's tiers in a mixed order, so students have to find today's number. Day 24 is the
gold star on top of the tree.

Each ornament is also saved on its own, for use as clickable elements on the website:

- `images/ornaments/day-01.svg` … `day-24.svg`
- `images/png/ornaments/day-01.png` … `day-24.png`

In the full calendar SVG each ornament is a group with `id="cal-day-N"`, so the website
can find and highlight a given day.

## Earlier design: square doors

`images/advent-calendar.svg` is a wooden board of 24 painted doors, each with its own
festive picture (star, tree, gift, candy cane, bell, bauble, snowflake, stocking, snowman,
mitten, gingerbread, holly, candle, hot cocoa, wreath, moon, Santa hat, cabin, reindeer,
snow globe, letter to Santa, lantern, peppermint and the Christmas Eve star). Single doors
are in `images/doors/` and `images/png/doors/`.

## Regenerating

All the artwork is drawn by code, so colours, layout and the day order can be changed in
`tools/generate_tree.py` (tree) and `tools/generate_doors.py` (doors).

```bash
python3 tools/generate_doors.py
```

```bash
python3 tools/generate_tree.py
```

```bash
node tools/render_png.js
```

The last command needs Playwright.
