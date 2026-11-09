// Makes one of the website's walkthrough videos from the real app, on its sample household (made-up figures).
//
//   1. start the app on a throwaway database:   set GW_DEV_PORT=8791 && python dev_server.py
//   2. node scripts/site_video/make.mjs health   (or reports, privacy, debt, start)
//
// fetch (Get my accounts) also drives the bank window, on the published demo bank (gw 2.0/DEMO_BANK.md). Start the
// dev server so that window opens a debugging port the maker can reach (Windows, WebView2):
//      set WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--remote-debugging-port=9340 && set GW_DEV_PORT=8791 && python dev_server.py
//      node scripts/site_video/make.mjs fetch
// It saves the demo's login (morgan / demo) to this computer's vault for the sample household (forgotten again when
// the sample is cleared), and the demo statement lands in Downloads, as it would for anyone.
//
// It plays each scene of scripts/site_video/<name>.json in the app and takes a screenshot, finds the part of the
// screen being talked about, speaks the narration in Groundwork's own voice (narrate.py), then composes and records the
// video in Chrome (compose.html). Out come Website/static/video/<name>.mp4, .webm, .jpg (poster) and .vtt (captions).
// Nothing is downloaded: it uses the Chrome or Edge already installed, and Node's own fetch and WebSocket.
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { createServer } from 'node:http';
import { spawnSync } from 'node:child_process';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';
import { launch, newPage, sleep } from './cdp.mjs';
import { openSample, openFresh, view, clickText } from './app.mjs';
import { seedHealth } from './seed.mjs';
import { bankWindow, bankClosed, bankStep, pngSize } from './bank.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const BASE = resolve(HERE, '..', '..');
const name = process.argv[2];
if (!name || !existsSync(join(HERE, name + '.json'))) { console.error('usage: node make.mjs <health|reports|privacy|fetch|debt|start>'); process.exit(2); }
const script = JSON.parse(readFileSync(join(HERE, name + '.json'), 'utf8'));
const OUT = join(BASE, 'Website', 'static', 'video');
const WORK = join(tmpdir(), 'gw_site_video', name);
mkdirSync(WORK, { recursive: true });
const W = 1600, H = 1000;

// Helpers the scenes' JavaScript can call inside the app.
const HELPERS = `
window.__vis = (e) => { const r = e.getBoundingClientRect(); return e.offsetParent !== null && r.width > 0 && r.height > 0; };
window.__find = (text, up = 0, sel = '*') => {
  let best = null;
  for (const e of document.querySelectorAll(sel)) {
    if (!__vis(e) || !(e.innerText || '').includes(text)) continue;
    if (!best || best.contains(e)) best = e;
  }
  for (let i = 0; best && i < up; i++) best = best.parentElement;
  return best;
};
window.__card = (text) => { const e = __find(text); return e && (e.closest('.card, details, section') || e); };
window.__span = (a, b) => {           // the box from the line holding text a down to the line holding text b
  const x = __find(a), y = __find(b);
  if (!x || !y) return x || y;
  return {getBoundingClientRect: () => { const p = x.getBoundingClientRect(), q = y.getBoundingClientRect();
    const l = Math.min(p.left, q.left), t = Math.min(p.top, q.top), r = Math.max(p.right, q.right), b2 = Math.max(p.bottom, q.bottom);
    return {left: l, top: t, width: r - l, height: b2 - t, right: r, bottom: b2}; }, scrollIntoView: (o) => x.scrollIntoView(o)};
};
window.__both = (a, b) => {           // the smallest element holding both texts
  let e = __find(a);
  while (e && !(e.innerText || '').includes(b)) e = e.parentElement;
  return e;
};
window.__next = () => { const ov = document.getElementById('onboardingOverlay');        // the setup screen's main button
  const b = [...(ov || document).querySelectorAll('button.btn-primary')].filter(x => x.offsetParent !== null && !x.disabled);
  if (b.length) b[b.length - 1].click(); return b.length > 0; };
window.__set = (id, v) => { const e = document.getElementById(id); if (!e) return false; e.value = v;
  e.dispatchEvent(new Event('input', {bubbles: true})); e.dispatchEvent(new Event('change', {bubbles: true})); return true; };
window.__tab = (label) => { const b = [...document.querySelectorAll('button, .tab, [role=tab]')].find(e => __vis(e) && e.textContent.trim() === label); if (b) b.click(); return !!b; };
`;

// The part of a page a scene talks about, scrolled into view, as {x, y, w, h} in that page's CSS pixels.
async function findFocus(pg, expr, vw, vh, block = 'center') {
  const there = await pg.eval(`(() => { const e = (${expr}); if (!e) return null;
    const r0 = e.getBoundingClientRect();
    if (r0.top < 70 || r0.bottom > ${vh} - 110) e.scrollIntoView({block: '${block}'});
    return true; })()`);
  if (!there) return null;
  await sleep(500);
  return pg.eval(`(() => { const r = (${expr}).getBoundingClientRect();
    return {x: Math.max(0, r.left), y: Math.max(0, r.top), w: Math.min(r.width, ${vw}), h: Math.min(r.height, ${vh})}; })()`);
}

// Where the bank window sits in the frame: centred, with a title bar, at most 80% wide and 84% high.
const TITLE_H = 38;
function placeWindow(w, h) {
  const s = Math.min(1, (W * 0.8) / w, (H * 0.84 - TITLE_H) / h);
  const x = (W - w * s) / 2, y = (H - (h * s + TITLE_H)) / 2 + TITLE_H;
  return { x, y, w: w * s, h: h * s, s };
}

async function capture() {
  const chrome = await launch({ width: W, height: H, port: 9334 });
  const shots = [];
  let bank = null;                       // the bank window, while one is open (fetch.json)
  const theBank = async () => {
    if (bank && bank.alive()) {
      try { await Promise.race([bank.eval('1'), sleep(3000).then(() => { throw new Error('gone'); })]); return bank; } catch { /* closed */ }
    }
    if (bank) bank.close();
    bank = null;
    bank = await bankWindow();
    return bank;
  };
  try {
    // "fresh": a brand-new install met at its welcome (start.json); otherwise the sample household
    const page = script.fresh ? await openFresh(chrome) : await openSample(chrome);
    if (!script.fresh && script.seed !== false) await seedHealth(page);
    if (!script.fresh) await page.goto(page.url || (await page.eval('location.href')), 2500);
    await page.eval(`document.head.insertAdjacentHTML('beforeend', '<style>.toast, .toast-container, #toastContainer, [class*=achievement-toast], [id*=toast] {display:none !important} *{caret-color:transparent !important; scroll-behavior:auto !important}</style>')`);
    const until = process.env.GW_VIDEO_UNTIL ? Number(process.env.GW_VIDEO_UNTIL) : Infinity;   // with --shots: stop early
    for (const [i, sc] of script.scenes.entries()) {
      if (i > until) break;
      if (sc.card) { shots.push(null); continue; }
      await page.eval(HELPERS);
      if (sc.view) await view(page, sc.view);
      if (sc.do) { await page.eval(`(async () => { ${sc.do} })()`); }
      if (sc.appWait) await page.waitFor(sc.appWait, sc.appWaitMs || 60000);
      if (sc.bank) {                     // steps in the bank window, as a person takes them
        const b = await theBank();
        for (const st of sc.bank) await bankStep(b, st);
      }
      if (sc.then) { await page.eval(HELPERS); await page.eval(`(async () => { ${sc.then} })()`); }
      if (sc.thenWait) await page.waitFor(sc.thenWait, sc.thenWaitMs || 60000);
      await sleep(sc.wait ?? 1400);
      if (sc.last) { await page.eval(HELPERS); await page.eval(`(async () => { ${sc.last} })()`); await sleep(sc.lastWait ?? 400); }   // right before the shot
      const file = `scene_${String(i).padStart(2, '0')}.png`;
      if (sc.in === 'bank') {            // the bank window, drawn over the app behind it
        const b = await theBank();
        if (sc.bankWait) await b.waitFor(sc.bankWait, sc.bankWaitMs || 30000);
        await b.eval(HELPERS);
        const { w, h } = await b.size();
        let f = sc.focus ? await findFocus(b, sc.focus, w, h, sc.block) : null;
        if (sc.focus && !f) console.warn(`  scene ${i}: focus not found in the bank window: ${sc.focus}`);
        const png = await b.shot(), real = pngSize(png);
        const winFile = `scene_${String(i).padStart(2, '0')}_bank.png`;
        writeFileSync(join(WORK, winFile), png);
        writeFileSync(join(WORK, file), await page.shot());
        const at = placeWindow(w, h);
        const focus = f && { x: at.x + f.x * at.s, y: at.y + f.y * at.s, w: f.w * at.s, h: f.h * at.s };
        shots.push({ file, focus, win: { file: winFile, x: at.x, y: at.y, w: at.w, h: at.h, titleH: TITLE_H,
          title: sc.winTitle || (await b.title()), px: real } });
        console.log(`  scene ${i} captured (bank window ${w}x${h})${focus ? ' focus ' + JSON.stringify(focus) : ''}`);
      } else {
        const focus = sc.focus ? await findFocus(page, sc.focus, W, H, sc.block) : null;
        if (sc.focus && !focus) console.warn(`  scene ${i}: focus not found: ${sc.focus}`);
        writeFileSync(join(WORK, file), await page.shot());
        shots.push({ file, focus });
        console.log(`  scene ${i} captured${focus ? ' focus ' + JSON.stringify(focus) : ''}`);
      }
      if (i === until) break;            // its shot only: nothing it would go on to do
      if (sc.after) { await page.eval(HELPERS); await page.eval(`(async () => { ${sc.after} })()`); }
      if (sc.bankAfter) { const b = await theBank(); for (const st of sc.bankAfter) await bankStep(b, st); }
      if (sc.untilClosed) { await bankClosed(); bank = null; }
    }
    if (page.errors.length) console.warn('  page errors:', page.errors);
  } finally { await chrome.close(); if (bank) bank.close(); }
  return shots;
}

function narrate() {
  writeFileSync(join(WORK, 'script.json'), JSON.stringify({ scenes: script.scenes }));
  const py = process.env.PYTHON || 'python';
  const r = spawnSync(py, [join(HERE, 'narrate.py'), join(WORK, 'script.json'), WORK], { cwd: BASE, stdio: 'inherit' });
  if (r.status) throw new Error('narration failed');
  return JSON.parse(readFileSync(join(WORK, 'narration.json'), 'utf8')).lengths;
}

function vttTime(s) {
  const ms = Math.round(s * 1000), h = Math.floor(ms / 3600000), m = Math.floor(ms / 60000) % 60, sec = (ms / 1000) % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${sec.toFixed(3).padStart(6, '0')}`;
}

async function compose(shots, lengths) {
  let t = 0;
  const scenes = script.scenes.map((sc, i) => {
    const audioAt = sc.card ? 0.6 : 0.35, len = lengths[i] || 0;
    const dur = Math.max(len + audioAt + (sc.card ? 0.9 : 0.5), sc.card ? 3.2 : 2.8);
    const s = { card: sc.card || null, say: sc.say || '', img: shots[i] && shots[i].file, focus: shots[i] && shots[i].focus,
      win: (shots[i] && shots[i].win) || null,
      maxZoom: sc.maxZoom, audio: len ? `line_${String(i).padStart(2, '0')}.wav` : null, audioAt, start: t, dur, len };
    t += dur;
    return s;
  });
  const posterScene = scenes[script.poster ?? 1];
  const plan = { name, width: W, height: H, scenes, total: t + 0.4, badge: script.badge || 'Sample household · made-up figures', poster: posterScene.start + Math.min(2.6, posterScene.dur - 0.3) };
  writeFileSync(join(WORK, 'scenes.json'), JSON.stringify(plan, null, 1));
  const cues = scenes.filter((s) => s.len).map((s, i) =>
    `${i + 1}\n${vttTime(s.start + s.audioAt)} --> ${vttTime(s.start + s.audioAt + s.len)}\n${s.say}\n`);
  writeFileSync(join(OUT, name + '.vtt'), ['WEBVTT', '', ...cues].join('\n'));

  let finished;
  const done = new Promise((r) => { finished = r; });
  const server = createServer((req, res) => {
    if (req.method === 'POST') {
      const chunks = [];
      req.on('data', (c) => chunks.push(c));
      req.on('end', () => {
        const body = Buffer.concat(chunks);
        if (req.url.startsWith('/save/')) { const f = req.url.slice(6); writeFileSync(join(OUT, f), body); console.log(`  saved ${f} (${(body.length / 1e6).toFixed(2)} MB)`); }
        if (req.url === '/done') finished(body.toString());
        res.end('ok');
      });
      return;
    }
    const f = req.url === '/' ? join(HERE, 'compose.html') : join(WORK, decodeURIComponent(req.url.slice(1)));
    if (!f.startsWith(WORK) && !f.endsWith('compose.html')) { res.statusCode = 403; return res.end(); }
    try { res.end(readFileSync(f)); } catch { res.statusCode = 404; res.end(); }
  });
  await new Promise((r) => server.listen(8799, '127.0.0.1', r));
  const chrome = await launch({ width: W, height: H, port: 9335 });
  try {
    const page = await newPage(chrome);
    console.log(`  recording ${plan.total.toFixed(1)} s in real time…`);
    await page.send('Page.navigate', { url: 'http://127.0.0.1:8799/' });
    const msg = await Promise.race([done, sleep((plan.total + 90) * 1000).then(() => 'ERROR timed out')]);
    if (msg.startsWith('ERROR')) throw new Error(msg);
  } finally { await chrome.close(); server.close(); }
}

console.log(`Making ${name}: capturing scenes from ${process.env.GW_VIDEO_APP || 'http://127.0.0.1:8791'}`);
const shots = await capture();
if (process.argv.includes('--shots')) { console.log(`Screenshots only, in ${WORK}`); process.exit(0); }
console.log('Narrating');
const lengths = narrate();
console.log('Composing');
await compose(shots, lengths);
console.log(`Done: Website/static/video/${name}.{mp4,webm,jpg,vtt}`);
