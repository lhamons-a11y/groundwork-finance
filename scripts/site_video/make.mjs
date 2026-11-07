// Makes one of the website's walkthrough videos from the real app, on its sample household (made-up figures).
//
//   1. start the app on a throwaway database:   set GW_DEV_PORT=8791 && python dev_server.py
//   2. node scripts/site_video/make.mjs health   (or reports, privacy)
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
import { openSample, view, clickText } from './app.mjs';
import { seedHealth } from './seed.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const BASE = resolve(HERE, '..', '..');
const name = process.argv[2];
if (!name || !existsSync(join(HERE, name + '.json'))) { console.error('usage: node make.mjs <health|reports|privacy>'); process.exit(2); }
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
window.__tab = (label) => { const b = [...document.querySelectorAll('button, .tab, [role=tab]')].find(e => __vis(e) && e.textContent.trim() === label); if (b) b.click(); return !!b; };
`;

async function capture() {
  const chrome = await launch({ width: W, height: H, port: 9334 });
  const shots = [];
  try {
    const page = await openSample(chrome);
    await seedHealth(page);
    await page.goto(page.url || (await page.eval('location.href')), 2500);
    await page.eval(`document.head.insertAdjacentHTML('beforeend', '<style>.toast, .toast-container, #toastContainer, [class*=achievement-toast], [id*=toast] {display:none !important} *{caret-color:transparent !important; scroll-behavior:auto !important}</style>')`);
    for (const [i, sc] of script.scenes.entries()) {
      if (sc.card) { shots.push(null); continue; }
      await page.eval(HELPERS);
      if (sc.view) await view(page, sc.view);
      if (sc.do) { await page.eval(`(async () => { ${sc.do} })()`); }
      await sleep(sc.wait ?? 1400);
      let focus = null;
      if (sc.focus) {
        focus = await page.eval(`(() => { const e = (${sc.focus}); if (!e) return null;
          const r0 = e.getBoundingClientRect();
          if (r0.top < 70 || r0.bottom > ${H} - 110) e.scrollIntoView({block: '${sc.block || 'center'}'});
          return true; })()`);
        await sleep(500);
        focus = focus && await page.eval(`(() => { const r = (${sc.focus}).getBoundingClientRect();
          return {x: Math.max(0, r.left), y: Math.max(0, r.top), w: Math.min(r.width, ${W}), h: Math.min(r.height, ${H})}; })()`);
        if (!focus) console.warn(`  scene ${i}: focus not found: ${sc.focus}`);
      }
      const file = `scene_${String(i).padStart(2, '0')}.png`;
      writeFileSync(join(WORK, file), await page.shot());
      shots.push({ file, focus });
      console.log(`  scene ${i} captured${focus ? ' focus ' + JSON.stringify(focus) : ''}`);
    }
    if (page.errors.length) console.warn('  page errors:', page.errors);
  } finally { await chrome.close(); }
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
      maxZoom: sc.maxZoom, audio: len ? `line_${String(i).padStart(2, '0')}.wav` : null, audioAt, start: t, dur, len };
    t += dur;
    return s;
  });
  const posterScene = scenes[script.poster ?? 1];
  const plan = { name, width: W, height: H, scenes, total: t + 0.4, poster: posterScene.start + Math.min(2.6, posterScene.dur - 0.3) };
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
