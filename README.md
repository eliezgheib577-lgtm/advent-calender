# LeMSIC Advent Calendar

Artwork for the LeMSIC Christmas advent calendar (1–24 December).

## Images

| File | What it is |
| --- | --- |
| `images/advent-calendar.svg` / `images/png/advent-calendar.png` | The full wooden wall calendar with all 24 doors |
| `images/doors/day-01.svg` … `day-24.svg` | One door per day (300×300, scalable) |
| `images/png/day-01.png` … `day-24.png` | The same doors as 600×600 PNGs |

| Day | Door | Day | Door | Day | Door |
| --- | --- | --- | --- | --- | --- |
| 1 | Shining Star | 9 | Snowman | 17 | Santa Hat |
| 2 | Christmas Tree | 10 | Mitten | 18 | Snowy Cabin |
| 3 | Wrapped Gift | 11 | Gingerbread | 19 | Reindeer |
| 4 | Candy Cane | 12 | Holly | 20 | Snow Globe |
| 5 | Jingle Bell | 13 | Candle | 21 | Letter to Santa |
| 6 | Bauble | 14 | Hot Cocoa | 22 | Lantern |
| 7 | Snowflake | 15 | Wreath | 23 | Peppermint |
| 8 | Stocking | 16 | Winter Moon | 24 | Christmas Eve (gold star) |

## Regenerating

The artwork is drawn by code, so colours and icons can be changed in `tools/generate_doors.py`.

```bash
python3 tools/generate_doors.py
```

```bash
node tools/render_png.js
```

The second command needs Playwright.
