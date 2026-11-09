// Render the SVG artwork to PNG (2x) with Playwright's Chromium.
// Usage: node tools/render_png.js
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const root = path.resolve(__dirname, '..');
const out = path.join(root, 'images', 'png');

(async () => {
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch();
  const jobs = [['advent-calendar.svg', 1800, 1550]];
  for (let d = 1; d <= 24; d++) jobs.push([`doors/day-${String(d).padStart(2, '0')}.svg`, 300, 300]);

  const page = await browser.newPage({ deviceScaleFactor: 2 });
  for (const [rel, w, h] of jobs) {
    await page.setViewportSize({ width: w, height: h });
    const svg = fs.readFileSync(path.join(root, 'images', rel), 'utf8');
    await page.setContent(`<html><body style="margin:0;background:transparent">${svg}</body></html>`);
    const file = path.join(out, path.basename(rel, '.svg') + '.png');
    await page.locator('svg').first().screenshot({ path: file, omitBackground: true });
  }
  await browser.close();
  console.log(`Rendered ${jobs.length} PNGs to images/png/`);
})();
