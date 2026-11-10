# LeMSIC Advent Calendar

An advent calendar for LeMSIC members, 1–24 December.

## The website

Open `site/index.html`. This is what students see:

1. **The cabin door.** A snowy log cabin at night with a carved LeMSIC sign over the door.
   A popup asks for their **LeMSIC ID**, which is checked against the member list. As soon
   as they've typed a valid ID, their first name appears under it. Non-members type `0000`
   to come in as guests (said in small print under the button).
2. **The door opens.** It swings open with warm light spilling onto the snow, and they're
   carried inside.
3. **The tree.** In the cabin, by the live fire, today's ornament glows on the cedar. It's
   the only one they can open.
4. **The picture.** Tapping the ornament opens it: a picture pops out and lands in front of
   them like a photo print, with a caption written underneath. You choose both.
5. **Hang it on the wall.** The print flies into its numbered frame on the picture wall,
   24 frames like the LeMSIC emblem's on the log wall left of the tree. Their pictures stay
   there from day to day, and tapping one shows it big again.
6. **The prize.** Students who hang all 24 pictures, one each day, see the prize message.

### Member IDs (the shared Excel sheet)

The member list is read from its **shared link**, so daily updates reach the website by
themselves. The workflow `.github/workflows/publish-site.yml` runs every 30 minutes:

1. it downloads the sheet from the link;
2. it turns the IDs into salted SHA-256 fingerprints, and seals each member's full name with
   a key made from their own ID (`site/assets/members.js`);
3. it publishes the site to GitHub Pages.

The website never contains the IDs, the link, or a readable list of names. The browser
fingerprints what a student types the same way and looks for a match, ignoring case, spaces
and dashes; on a match it opens that one member's first name to greet them. Only first names are kept
(`--full-names` in `tools/import_members.py` would keep whole names), and each ID is
stretched with 100,000 rounds of PBKDF2, so guessing IDs to read names off the site is slow.

**The sheet needs** an ID column (a header with "ID" in it) and a **Full Name** column (or
"Name", or "First Name" + "Last Name"). If the sheet can't be
read, nothing is published and the last good version stays online.

Setup, once, in the repository's **Settings**:

1. **Secrets and variables › Actions › New repository secret**: name it `MEMBERS_SHEET_URL`
   and paste the shared link. Excel links from OneDrive or SharePoint and Google Sheets links
   all work. The link must let *anyone with the link view* the file without signing in.
2. If the ID column's header doesn't contain "ID", add a **variable** `MEMBERS_ID_COLUMN`
   with the header's exact text; likewise `MEMBERS_NAME_COLUMN` for the names.
3. **Pages › Build and deployment › Source: GitHub Actions.**

It runs from the default branch. To refresh straight away, use **Actions › Publish site ›
Run workflow**. To update the list by hand instead, run
`python3 tools/fetch_members.py "<shared link>"` or
`python3 tools/import_members.py members.xlsx`.

The `site/assets/members.js` in the repository is always the **sample** list
(`tools/sample-members.csv`; try `DEMO-0001`, `DEMO-0002` or `TEST-1234`). The real one is
built by the workflow when it publishes, so the member list never enters the repository's
history. The LeMSIC workbook is read from its **ID** tab: IDs from **ID_to_email**, names from
**Full Name** (set in the workflow; change them with the variables `MEMBERS_SHEET_TAB`,
`MEMBERS_ID_COLUMN` and `MEMBERS_NAME_COLUMN` if the sheet changes). To build it by hand:
`python3 tools/import_members.py LeMSIC_Membership_Sheet.xlsx --tab ID --column ID_to_email`
(but don't commit the result).

**Codes:** `0000` lets non-members in as guests (`guestCode` in `config.js`); their wall stays
in their own browser. `nta27` opens test mode (`testCode`).

### Pictures and settings

- `site/pictures.js`: what pops out of each ornament, a **picture** and a **caption** of your
  choice. Put your pictures in `site/assets/days/` (any name, `.jpg`, `.png` or `.webp`, any
  shape) and write each day's file and caption there. The pictures there now are placeholders.
- `site/config.js`: the year, the time zone (Lebanon), the prize message, the test code, and
  the optional progress sheet.

**Test mode:** type `nta27` (the `testCode` in `config.js`) instead of a LeMSIC ID at
the door. Every ornament on the tree opens, and nothing is saved or sent. *Exit the Cabin* leaves test mode. Anyone who reads `config.js` can see the
code, so it only guards the surprise; set it to `""` to switch test mode off.

**Trying a single day:** add `#day-7` (any day) to the page address, or set `previewDay` in
`config.js`. Preview days are kept apart and never sent to the sheet.

### Keeping track of everyone's progress (who wins the prize)

Connect a Google Sheet and it fills in by itself: `backend/progress-sheet.gs` has the
5-minute setup at the top (make a sheet, paste the script, deploy it as a web app, put its
URL in `site/config.js` as `progressEndpoint`). Then:

- the **Progress** tab has one row per member: ID, name, how many of the 24 pictures they've
  hung, which days, when they were last in, and **All 24: Yes** once they're done;
- the **Log** tab has one row per picture hung, and whether it was on its own day;
- a member's wall follows them to another phone or computer.

Add a **Members** tab (IDs in column A, names in column B) and only those IDs are recorded.
Without the sheet, each student's wall is kept only in their own browser. Guests (`0000`)
are never sent to the sheet.

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
- **Fares, the LeMSIC mascot doll** (`tools/blender/fares.py`) sits by the tree in a varnished
  wooden rocking chair. He is built the way the real rag doll is made: the long black robe and
  the sleeves are cloth simulations draped over his body, the seat and the armrests; the hat and
  mitten hands are stuffed cloth inflated with the cloth pressure solver; his hair and mustache
  are curly yarn. **Click him and he rocks:** the chair is rendered rolling on its rockers at a
  range of angles (`tools/blender/cabin_rock.py`), and the page plays them with a damped swing.
- **The picture wall:** 24 frames built like the LeMSIC emblem's (walnut moulding, cream mat,
  the print behind glass), stepping down the log wall between the chimney and the tree, each
  holding a blue card with its number until that day's picture is hung. The website lays the
  hung picture over its card, shaded by how the frame is lit in the room images and following
  the firelight (`gallery` in `scene.json`).
- **Snow** falls outside the window, softly out of focus and behind the window bars.
- **Fire sound:** a crackling sound can be switched on. It is generated in the browser, so
  there are no audio files.
- **On phones** the scene scrolls sideways.
- **Data:** `site/assets/cabin/scene.json` (and `scene.js`) give the position of the window
  and every ornament in the image, so the ornaments can be made clickable. `fire.json` (and
  `fire.js`) describe the fire loop, and `rock.json` (and `rock.js`) Fares' rocking frames.

To re-render (about 45 minutes for the room, 25 for the fire and 15 for Fares rocking, on a 4-core CPU):

```bash
pip install bpy==5.2.3 OpenEXR
```

```bash
python tools/blender/cabin_scene.py
```

```bash
python tools/blender/cabin_fire.py
```

```bash
python tools/blender/cabin_rock.py
```

Add `--preview` to any of them for a quick low-resolution test. `python tools/blender/fares.py`
renders Fares on his own (`front`, `face` or `cabin` view) to `build/`. Intermediate files go to `build/`,
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
