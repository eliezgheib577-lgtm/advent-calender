# LeMSIC Advent Calendar

Artwork for the LeMSIC Christmas advent calendar (1–24 December).

## The cabin (live scene)

`site/cabin.html` is the scene students will land in: the LeMSIC tree in the middle of a log
cabin at night, a stone fireplace burning on the left, and snow falling past the window on the
right. Everything you see is rendered in Blender (Cycles).

- **The tree draws the LeMSIC serpent.** A pearl serpent with its head at the top winds back
  and forth down across the trunk (the staff), like the snake in the emblem. Days 1–23 hang
  along it in order, from the head to the tail, and day 24 is the gold star on top.
- **The LeMSIC emblem** hangs framed on the wall beside the tree, lit by a picture light, and
  one present is wrapped in paper printed with it.
- **The room is built from real geometry:** fieldstones laid in courses with mortar joints and
  soot above the firebox, hewn logs with checking cracks and chinking, wide floor planks, a
  braided rag rug, knitted stockings, and frosted window panes. The camera has a real depth
  of field.
- **The fire is a Blender render, played as a loop.** The flames are a volumetric fire
  (animated noise glowing at blackbody temperatures) with sparks. They are rendered frame by
  frame behind the logs and stones (`tools/blender/cabin_fire.py`) into a seamless 4-second loop.
- **The firelight is real rendered light, in step with the flames.** The room is rendered once
  with the fire split into its own light groups. Three images are made from it (fire dim,
  leaning left, leaning right). The page fades between them using each fire frame's measured
  brightness, so the glow on the stones, floor and tree rises and falls with the flames.
- **Snow** falls outside the window, softly out of focus and behind the window bars.
- **Fire sound:** a crackling sound can be switched on. It is generated in the browser, so
  there are no audio files.
- **On phones** the scene scrolls sideways.
- **Data:** `site/assets/cabin/scene.json` (and `scene.js`) give the position of the window
  and every ornament in the image, so the ornaments can be made clickable. `fire.json` (and
  `fire.js`) describe the fire loop.

Open `site/cabin.html` in a browser to see it.

To re-render (about 45 minutes for the room and 25 for the fire, on a 4-core CPU):

```bash
pip install bpy==5.2.3 OpenEXR
```

```bash
python tools/blender/cabin_scene.py
```

```bash
python tools/blender/cabin_fire.py
```

Add `--preview` to either for a quick low-resolution test. Intermediate files go to `build/`,
which is not committed. The realistic room parts are generated in `tools/blender/cabin_props.py`.

## The 3D tree calendar

`images/png/lemsic-tree-calendar-3d.png` (source: `images/lemsic-tree-calendar-3d.svg`)

A realistic Christmas tree rendered in Blender (Cycles). It is a real evergreen with bark,
branches and about 2.9 million individual needles, grown in the silhouette of the cedar in
the LeMSIC emblem: nine flat tiers that alternately reach further left and right. It sits on
the LeMSIC-blue card (`#3C6BAD`) with the emblem's laurel branches.

- Days 1–23 are glass baubles with the day number printed on them. They hang along a pearl
  serpent that winds down the tree like the snake in the emblem, in order from its head (1)
  to its tail (23).
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
