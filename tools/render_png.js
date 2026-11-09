// Render the SVG artwork to PNG (2x) with Playwright's Chromium.
// Usage: node tools/render_png.js
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const root = path.resolve(__dirname, '..');
const img = path.join(root, 'images');
const pad = (d) => String(d).padStart(2, '0');

const jobs = [
  ['lemsic-tree-calendar.svg', 'png/lemsic-tree-calendar.png', 1800, 2040],
  ['advent-calendar.svg', 'png/advent-calendar.png', 1800, 1550],
];
for (let d = 1; d <= 24; d++) {
  jobs.push([`ornaments/day-${pad(d)}.svg`, `png/ornaments/day-${pad(d)}.png`, d === 24 ? 220 : 120, d === 24 ? 220 : 108]);
  jobs.push([`doors/day-${pad(d)}.svg`, `png/doors/day-${pad(d)}.png`, 300, 300]);
}

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ deviceScaleFactor: 2 });
  for (const [src, dest, w, h] of jobs) {
    const out = path.join(img, dest);
    fs.mkdirSync(path.dirname(out), { recursive: true });
    await page.setViewportSize({ width: w, height: h });
    const svg = fs.readFileSync(path.join(img, src), 'utf8');
    await page.setContent(`<html><body style="margin:0;background:transparent">${svg}</body></html>`);
    await page.locator('svg').first().screenshot({ path: out, omitBackground: true });
  }
  await browser.close();
  console.log(`Rendered ${jobs.length} PNGs into images/png/`);
})();
