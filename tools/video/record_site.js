// Records the real calendar website for the promo video, frame by frame from the browser's compositor.
//
//   node tools/video/record_site.js <clip> <out-dir> [site-url]
//
// The page runs in slow motion while it is recorded (its clock, timers, frames and animations all
// SLOW times slower), so the browser's ~15 frames a second become ~60 of the page's own time;
// times.json is in page time, so the film plays it back at normal speed.
//
// Clips: door (the door, the login, the door opening, walking in), room (the room on 2 December, idle),
// ornament (today's ornament opened, its picture hung), timelapse (3 to 24 December, one after another).
// For the recording only: the test-mode panel, the countdown and test notes are hidden, the
// "How it works" sheet is skipped, a glowing pointer shows the clicks, and the day pictures are
// swapped for mystery cards (build/video/mystery, from tools/video/mystery_cards.py) with no captions. Writes <out-dir>/<clip>/
// NNNNN.jpg with times.json (the time of each frame, in seconds).
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const [clip, outDir, site = 'http://localhost:8765/index.html'] = process.argv.slice(2);
const SLOW = { door: 4, room: 3, ornament: 4, timelapse: 1.5 }[clip] || 1;
const POINTER = `
  #vidPointer { position: fixed; left: 0; top: 0; width: 44px; height: 44px; margin: -6px 0 0 -6px; z-index: 99999;
    pointer-events: none; transition: transform .12s ease; filter: drop-shadow(0 0 10px rgba(255, 214, 140, .9)) drop-shadow(0 3px 4px rgba(0,0,0,.5)); }
  #vidPointer.down { transform: scale(.82); }
  #vidPointer .ring { position: absolute; left: -20px; top: -20px; width: 52px; height: 52px; border-radius: 50%;
    border: 3px solid rgba(255, 220, 150, .95); opacity: 0; }
  #vidPointer.down .ring { animation: vidring .6s ease-out; }
  @keyframes vidring { 0% { opacity: 1; transform: scale(.3); } 100% { opacity: 0; transform: scale(1.6); } }
  #testPanel, #countdown { display: none !important; }`;

(async () => {
  const dir = path.join(outDir, clip);
  fs.mkdirSync(dir, { recursive: true });
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  await ctx.route('**/index.html', async (route) => {
    const res = await route.fetch();
    let html = await res.text();
    html = html.replace(" · test, nothing is saved", '').replace("${n} of 24 · ${practice ? 'practice run' : 'test mode'}", '${n} of 24 pictures hung');
    html = html.replace("toast(testDay === null ? 'Every ornament opens.'", "void (testDay === null ? 'Every ornament opens.'");   // (no test-mode notes)
    html = html.replace('</head>', `<style>${POINTER}</style></head>`);
    await route.fulfill({ response: res, body: html });
  });
  await ctx.route('**/pictures.js', async (route) => {
    const res = await route.fetch();
    const js = (await res.text()).replace(/caption: "[^"]*"/g, 'caption: ""');     // no captions under the pictures
    await route.fulfill({ response: res, body: js });
  });
  // the day pictures stay a surprise: each is swapped for its mystery card (tools/video/mystery_cards.py)
  const MYSTERY = path.join(__dirname, '..', '..', 'build', 'video', 'mystery');
  await ctx.route('**/assets/days/day-*.png', async (route) => {
    const name = route.request().url().split('/').pop().split('?')[0];
    await route.fulfill({ path: path.join(MYSTERY, name), contentType: 'image/png' });
  });
  const page = await ctx.newPage();
  await page.addInitScript((SLOW) => {
    // slow motion: the page's clock, timers and animation frames run SLOW times slower
    const pnow = performance.now.bind(performance), start = pnow();
    performance.now = () => start + (pnow() - start) / SLOW;
    const RealDate = Date, d0 = RealDate.now();
    const fake = () => d0 + (RealDate.now() - d0) / SLOW;
    window.Date = class extends RealDate { constructor(...a) { if (a.length) super(...a); else super(fake()); } static now() { return fake(); } };
    const raf = window.requestAnimationFrame.bind(window);
    window.requestAnimationFrame = (cb) => raf((t) => cb(start + (t - start) / SLOW));
    const st = window.setTimeout.bind(window), si = window.setInterval.bind(window);
    window.setTimeout = (f, ms, ...a) => st(f, (ms || 0) * SLOW, ...a);
    window.setInterval = (f, ms, ...a) => si(f, (ms || 0) * SLOW, ...a);
    // and its animations: Web Animations as they start, CSS animations and transitions as they appear
    const slowed = new WeakSet();
    const slow = (an) => { if (!slowed.has(an)) { slowed.add(an); an.playbackRate = an.playbackRate / SLOW; } return an; };
    const animate = Element.prototype.animate;
    Element.prototype.animate = function (...a) { return slow(animate.apply(this, a)); };
    const sweep = () => { try { document.getAnimations().forEach(slow); } catch (e) {} raf(sweep); };
    raf(sweep);
    const show = HTMLDialogElement.prototype.showModal;
    HTMLDialogElement.prototype.showModal = function () { if (this.id === 'howto') return; return show.call(this); };
    try { localStorage.clear(); } catch (e) {}
    addEventListener('DOMContentLoaded', () => {
      const p = document.createElement('div');
      p.id = 'vidPointer';
      p.innerHTML = '<span class="ring"></span><svg viewBox="0 0 24 24" width="44" height="44"><path d="M4 2 L4 19 L8.6 14.8 L11.7 21.5 L14.6 20.2 L11.6 13.6 L17.8 13.4 Z" fill="#fff6e3" stroke="#6b3d12" stroke-width="1.2" stroke-linejoin="round"/></svg>';
      p.style.opacity = '0';
      document.body.appendChild(p);
      addEventListener('mousemove', (e) => { p.style.left = e.clientX + 'px'; p.style.top = e.clientY + 'px'; });
      addEventListener('mousedown', () => { p.classList.remove('down'); void p.offsetWidth; p.classList.add('down'); });
      addEventListener('mouseup', () => setTimeout(() => p.classList.remove('down'), 120));
    });
  }, SLOW);
  page.on('pageerror', (e) => console.log('PAGE ERROR', e.message));
  page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') console.log('CONSOLE', m.text()); });
  const cdp = await ctx.newCDPSession(page);
  const times = [];
  let n = 0, t0 = null;
  cdp.on('Page.screencastFrame', async (f) => {
    const t = f.metadata.timestamp;
    if (t0 === null) t0 = t;
    const name = String(n++).padStart(5, '0') + '.jpg';
    fs.writeFileSync(path.join(dir, name), Buffer.from(f.data, 'base64'));
    times.push([name, +((t - t0) / SLOW).toFixed(4)]);
    try { await cdp.send('Page.screencastFrameAck', { sessionId: f.sessionId }); } catch (e) {}
  });
  const rec = async (on) => {
    if (on) await cdp.send('Page.startScreencast', { format: 'jpeg', quality: 93, maxWidth: 1920, maxHeight: 1080, everyNthFrame: 1 });
    else await cdp.send('Page.stopScreencast');
  };
  const wait = (ms) => page.waitForTimeout(ms * SLOW);          // (in the page's time)
  const pointer = (on) => page.evaluate((v) => { document.getElementById('vidPointer').style.opacity = v ? '1' : '0'; }, on);
  let mx = 960, my = 700;
  const glide = async (x, y, ms = 900) => {                      // an eased, human-ish move
    const steps = Math.max(8, Math.round(ms / 16));
    const x0 = mx, y0 = my;
    for (let i = 1; i <= steps; i++) {
      const s = i / steps, e = s * s * (3 - 2 * s);
      await page.mouse.move(x0 + (x - x0) * e, y0 + (y - y0) * e + Math.sin(Math.PI * s) * 18);
      await wait(16);
    }
    mx = x; my = y;
  };
  const centre = async (sel) => {
    const b = await page.locator(sel).first().boundingBox();
    return [b.x + b.width / 2, b.y + b.height / 2];
  };
  const clickAt = async (sel, ms = 900) => {
    const [x, y] = await centre(sel);
    await glide(x, y, ms);
    await wait(250);
    await page.mouse.down(); await wait(90); await page.mouse.up();
  };
  const enterTest = async (day) => {
    await page.goto(site + `#day-${day}`);
    await page.fill('#lemsicId', 'nta27');
    await page.click('#loginBtn');
    await wait(7500);
  };
  const setDay = async (d) => {
    await page.evaluate((v) => { const el = document.getElementById('testDate'); el.value = v; el.dispatchEvent(new Event('change')); }, String(d));
  };

  if (clip === 'door') {
    await page.goto(site);
    await wait(2500);
    await page.mouse.move(mx, my);
    await rec(true);
    await wait(1800);
    await pointer(true);
    await clickAt('#lemsicId', 1100);
    await wait(500);
    for (const ch of '0000') { await page.keyboard.type(ch); await wait(260); }
    await wait(700);
    await clickAt('#loginBtn', 700);
    await wait(400);
    await pointer(false);
    await wait(9000);
    await rec(false);
  } else if (clip === 'room') {
    await enterTest(2);
    await rec(true);
    await wait(16000);
    await rec(false);
  } else if (clip === 'ornament') {
    await enterTest(2);
    await page.mouse.move(mx, my);
    await rec(true);
    await wait(1200);
    await pointer(true);
    await clickAt('.orn[aria-label^="Day 2"]', 1300);
    await wait(3600);
    await clickAt('#hangBtn', 900);
    await wait(250);
    await pointer(false);
    await wait(4500);
    await rec(false);
  } else if (clip === 'timelapse') {
    await enterTest(1);
    await page.mouse.move(mx, my);
    await rec(true);
    await pointer(true);
    for (let d = 1; d <= 24; d++) {
      if (d > 1) { await setDay(d); await wait(900); }
      await clickAt(`.orn[aria-label^="Day ${d}"]`, 420);
      await wait(1500);
      await clickAt('#hangBtn', 300);
      await wait(1900);
    }
    await wait(1500);
    if (await page.locator('#popClose').isVisible().catch(() => false)) await clickAt('#popClose', 500);   // (the prize note)
    await wait(300);
    await pointer(false);
    await page.mouse.move(1900, 1000);
    await wait(6000);
    await rec(false);
  }
  fs.writeFileSync(path.join(dir, 'times.json'), JSON.stringify(times));
  const span = times.length ? times[times.length - 1][1] : 0;
  console.log(clip, times.length, 'frames over', span.toFixed(1), 's =', (times.length / Math.max(span, 0.001)).toFixed(1), 'fps');
  await browser.close();
})();
