# LeMSIC Advent Calendar

Artwork for the LeMSIC Christmas advent calendar (1–24 December).

## The 3D tree calendar (main design)

`images/png/lemsic-tree-calendar-3d.png` (source: `images/lemsic-tree-calendar-3d.svg`)

A realistic Christmas tree rendered in Blender (Cycles). It is a real evergreen with bark,
branches and about 2.9 million individual needles, grown in the silhouette of the cedar in
the LeMSIC emblem: nine flat tiers that alternately reach further left and right. It sits on
the LeMSIC-blue card (`#3C6BAD`) with the emblem's laurel branches.

- Days 1–23 are glass baubles with the day number printed on them, hanging from the tiers in a
  mixed order, so students have to find today's number.
- Day 24 is the gold star on top.
- Fairy lights glow in the branches, and presents (one in LeMSIC blue) sit around a wooden crate.

| File | What it is |
| --- | --- |
| `images/render/lemsic-tree.png` | The tree alone on a transparent background (to place in the cabin scene) |
| `images/render/lemsic-tree-glow.png` | The same with a soft glow on the lights and star |
| `images/render/ornaments.json` | Where each ornament sits in `lemsic-tree.png` |
| `images/render/calendar-hotspots.json` | Where each ornament sits on the full card |

The JSON files give each day's centre (`x`, `y`) and radius (`r`) as fractions of the image
size, so the website can make each ornament clickable.

## Flat tree calendar

`images/lemsic-tree-calendar.svg` is a flat illustrated version of the emblem tree: the
serpent winding around the staff with numbered ornaments hanging from it. Single ornaments
are in `images/ornaments/` and `images/png/ornaments/`.

## Earlier design: square doors

`images/advent-calendar.svg` is a wooden board of 24 painted doors, each with its own
festive picture (star, tree, gift, candy cane, bell, bauble, snowflake, stocking, snowman,
mitten, gingerbread, holly, candle, hot cocoa, wreath, moon, Santa hat, cabin, reindeer,
snow globe, letter to Santa, lantern, peppermint and the Christmas Eve star). Single doors
are in `images/doors/` and `images/png/doors/`.

## Regenerating

### 3D tree

The tree is built entirely by `tools/blender/lemsic_tree.py`: tier sizes, ornament colours,
lights and camera are all set there. It runs in Blender 5.x, or with the `bpy` module from PyPI.

```bash
blender -b -P tools/blender/lemsic_tree.py
```

Or, without installing Blender:

```bash
pip install bpy==5.2.3
```

```bash
python tools/blender/lemsic_tree.py
```

Add `-- --preview` (Blender) or `--preview` (bpy) for a quick low-resolution test.
A full render takes roughly 15 minutes on a 4-core CPU.

Then place the render on the card:

```bash
python3 tools/compose_calendar_3d.py
```

The numbers printed on the baubles come from `tools/blender/decals/`, made by
`python3 tools/blender/make_decals.py`.

### Flat artwork

```bash
python3 tools/generate_tree.py
```

```bash
python3 tools/generate_doors.py
```

### PNG exports

```bash
node tools/render_png.js
```

This needs Playwright.
