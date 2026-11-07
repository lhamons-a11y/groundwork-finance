// Checks a made video plays as a browser would play it: its duration is known, it seeks, it has sound, and frames
// at a few moments are saved for a look.   node scripts/site_video/check.mjs <name> <out_dir>
import { createServer } from 'node:http';
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { launch, newPage } from './cdp.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const VID = resolve(HERE, '..', '..', 'Website', 'static', 'video');
const [name, out = '.'] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
const server = createServer((req, res) => {
  try {
    const buf = readFileSync(join(VID, decodeURIComponent(req.url.slice(1))));
    const range = /bytes=(\d+)-(\d*)/.exec(req.headers.range || '');
    const type = req.url.endsWith('.mp4') ? 'video/mp4' : req.url.endsWith('.webm') ? 'video/webm' : 'text/html';
    if (range) {
      const a = +range[1], b = range[2] ? +range[2] : buf.length - 1;
      res.writeHead(206, { 'Content-Type': type, 'Content-Range': `bytes ${a}-${b}/${buf.length}`, 'Accept-Ranges': 'bytes', 'Content-Length': b - a + 1 });
      return res.end(buf.subarray(a, b + 1));
    }
    res.writeHead(200, { 'Content-Type': type, 'Accept-Ranges': 'bytes', 'Content-Length': buf.length });
    res.end(buf);
  } catch {
    if (req.url === '/') { res.writeHead(200, { 'Content-Type': 'text/html' }); return res.end('<!doctype html><title>check</title>'); }
    res.statusCode = 404; res.end();
  }
});
await new Promise((r) => server.listen(8798, '127.0.0.1', r));
const chrome = await launch({ width: 1600, height: 1000, port: 9336 });
try {
  const page = await newPage(chrome, 'http://127.0.0.1:8798/');
  for (const ext of ['mp4', 'webm'].filter((e) => existsSync(join(VID, `${name}.${e}`)))) {
    const r = await page.eval(`(async () => {
      const v = document.createElement('video'); v.muted = true; v.preload = 'auto'; v.src = '/${name}.${ext}';
      document.body.appendChild(v);
      await new Promise((ok, no) => { v.onloadedmetadata = ok; v.onerror = () => no(new Error('cannot play: ' + (v.error && (v.error.code + ' ' + v.error.message)))); });
      const c = document.createElement('canvas'); c.width = v.videoWidth; c.height = v.videoHeight;
      const shots = [];
      const d = isFinite(v.duration) ? v.duration : null;
      for (const t of [2, 10, 25, 45, 70].filter(t => !d || t < d)) {
        v.currentTime = t;
        await new Promise((ok) => { v.onseeked = ok; setTimeout(ok, 4000); });
        c.getContext('2d').drawImage(v, 0, 0);
        shots.push([t, c.toDataURL('image/jpeg', 0.8)]);
      }
      return {duration: v.duration, w: v.videoWidth, h: v.videoHeight, seekable: v.seekable.length ? v.seekable.end(0) : 0,
              audio: v.mozHasAudio ?? (v.audioTracks ? v.audioTracks.length : 'n/a'), shots};
    })()`);
    console.log(`${name}.${ext}: duration ${r.duration} s, ${r.w}x${r.h}, seekable to ${r.seekable}`);
    if (ext === 'mp4') for (const [t, url] of r.shots) writeFileSync(join(out, `${name}_${t}s.jpg`), Buffer.from(url.split(',')[1], 'base64'));
  }
  const audio = await page.eval(`(async () => {
    const v = document.createElement('video'); v.src = '/${name}.mp4'; v.muted = false; document.body.appendChild(v);
    await new Promise((ok) => { v.oncanplay = ok; });
    const ac = new AudioContext(); const src = ac.createMediaElementSource(v); const an = ac.createAnalyser(); src.connect(an);
    v.currentTime = 3; await v.play(); await new Promise((ok) => setTimeout(ok, 2500));
    const a = new Float32Array(an.fftSize); an.getFloatTimeDomainData(a); v.pause();
    return Math.max(...a.map(Math.abs));
  })()`);
  console.log(`${name}.mp4: peak audio level ${audio.toFixed(3)} (0 means silent)`);
} finally { await chrome.close(); server.close(); }
