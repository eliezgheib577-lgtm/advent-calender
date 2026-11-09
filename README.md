# LeMSIC Advent Calendar

An advent calendar for LeMSIC members, 1–24 December.

## The website

Open `site/index.html`. This is what students see:

1. **The cabin door.** A snowy log cabin at night with a carved LeMSIC sign over the door.
   A popup asks for their **LeMSIC ID**, which is checked against the member list.
2. **The door opens.** It swings open with warm light spilling onto the snow, and they're
   carried inside.
3. **The tree.** In the cabin, by the live fire, today's ornament glows on the cedar. It's
   the only one they can open.
4. **The question.** Tapping the ornament shows the day's LeMSIC question. Any answer
   counts. Once they log it, the ornament opens and reveals the day's picture.
5. **The prize.** Students who answer all 24 days see the prize message.

### Member IDs (from the Excel sheet)

```bash
python3 tools/import_members.py path/to/members.xlsx
```

This reads the first sheet, takes the column whose header mentions "ID" (or the one named
with `--column "LeMSIC ID"`), and writes `site/assets/members.js`. The website never gets
the IDs themselves, only salted SHA-256 fingerprints of them. The browser fingerprints what a
student types the same way and looks for a match. IDs are compared ignoring case, spaces and
dashes. Re-run it whenever the member list changes.

The list in the repository now is a **sample** (`tools/sample-members.csv`). For testing, use
`DEMO-0001`, `DEMO-0002` or `TEST-1234`.

### Questions, pictures and settings

- `site/questions.js`: one question per day, multiple choice or free text, with an optional
  fun fact shown after answering. Please check the facts before launch.
- `site/assets/days/day-01.png` … `day-24.png`: the picture revealed each day. Replace them
  with your own, or point a day at another file with `picture:` in `questions.js`.
- `site/config.js`: the year, the time zone (Lebanon), the prize message, and optional
  answer recording.

**Trying it before December:** add `#day-7` (any day) to the page address, or set
`previewDay` in `config.js`. Preview answers are kept apart and never sent to the sheet.

### Recording answers (who wins the prize)

Without a back end, answers are kept in each student's own browser. To collect them in one
place, use the Google Sheet script in `backend/answers-sheet.gs`; setup steps are at the top
of the file. It logs every answer, marks whether it was given on the right day, and keeps a
**Progress** tab showing who has answered all 24. If the sheet has a **Members** tab, it also
refuses IDs that aren't on it.

## The cabin

The cabin is the scene students land in: the LeMSIC tree in the middle of a log
cabin at night, a stone fireplace burning on the left, and snow falling past the window on the
right. Everything you see is rendered in Blender (Cycles).

- **The tree is a cedar of Lebanon,** the tree in the LeMSIC emblem: broad flat layers of
  tufted needles. It wears baubles in LeMSIC blue, silver, white and gold, numbered 1–23 and
  scattered in a mixed order. The LeMSIC emblem medallion on top is day 24, and a blue velvet
  tree skirt has the emblem embroidered on it. Other tree designs can be rendered with
  `--style` (see `STYLES` in `tools/blender/lemsic_tree.py`; previews are in
  `images/render/options/`).
- **The LeMSIC emblem** hangs framed on the wall beside the tree, lit by a picture light, and
  one present is wrapped in paper printed with it.
- **The front door** (`tools/blender/cabin_door.py`) is rendered separately: the closed door,
  plus 24 frames of it opening.
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
