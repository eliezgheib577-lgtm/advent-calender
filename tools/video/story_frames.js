// Screenshots the phone story (tools/video/story.html) frame by frame: node tools/video/story_frames.js <out-dir> [fps]
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
const [out, fps = '24'] = process.argv.slice(2);
(async () => {
  fs.mkdirSync(out, { recursive: true });
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  await p.goto('file://' + path.join(__dirname, 'story.html'));
  await p.waitForTimeout(800);
  const end = await p.evaluate(() => window.STORY_T.end);
  const n = Math.round(end * +fps);
  for (let i = 0; i < n; i++) {
    await p.evaluate((t) => window.render(t), i / +fps);
    await p.screenshot({ path: path.join(out, String(i).padStart(4, '0') + '.png') });
  }
  console.log('story frames', n);
  await b.close();
})();
