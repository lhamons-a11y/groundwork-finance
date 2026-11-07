// A small Chrome DevTools Protocol client for making the website's walkthrough videos.
// No packages: Node's own fetch and WebSocket drive a Chrome that is already installed.
import { spawn } from 'node:child_process';
import { mkdtempSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const CHROMES = [
  process.env.GW_CHROME,
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/usr/bin/google-chrome',
].filter(Boolean);

export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export async function launch({ width = 1600, height = 1000, port = 9333, headless = true } = {}) {
  const exe = CHROMES.find((p) => existsSync(p));
  if (!exe) throw new Error('No Chrome or Edge found; set GW_CHROME to its path.');
  const profile = mkdtempSync(join(tmpdir(), 'gw_video_chrome_'));
  const args = [
    `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, `--window-size=${width},${height}`,
    '--no-first-run', '--no-default-browser-check', '--hide-scrollbars', '--mute-audio',
    '--autoplay-policy=no-user-gesture-required', '--force-device-scale-factor=1', '--disable-extensions',
  ];
  if (headless) args.push('--headless=new');
  const proc = spawn(exe, [...args, 'about:blank'], { stdio: 'ignore' });
  let version;
  for (let i = 0; i < 100 && !version; i++) {
    try { version = await (await fetch(`http://127.0.0.1:${port}/json/version`)).json(); } catch { await sleep(100); }
  }
  if (!version) { proc.kill(); throw new Error('Chrome did not open its debugging port.'); }
  const browser = await connect(version.webSocketDebuggerUrl);
  return { proc, browser, port, width, height, close: async () => { try { await browser.send('Browser.close'); } catch {} proc.kill(); } };
}

export async function connect(url) {
  const ws = new WebSocket(url);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  let id = 0;
  const pending = new Map();
  const listeners = new Map();
  ws.onmessage = (ev) => {
    const msg = JSON.parse(typeof ev.data === 'string' ? ev.data : ev.data.toString());
    if (msg.id && pending.has(msg.id)) {
      const { res, rej } = pending.get(msg.id);
      pending.delete(msg.id);
      msg.error ? rej(new Error(`${msg.error.message} ${msg.error.data || ''}`)) : res(msg.result);
    } else if (msg.method) {
      for (const fn of listeners.get(msg.method + '|' + (msg.sessionId || '')) || []) fn(msg.params);
    }
  };
  const send = (method, params = {}, sessionId) => new Promise((res, rej) => {
    const msg = { id: ++id, method, params };
    if (sessionId) msg.sessionId = sessionId;
    pending.set(msg.id, { res, rej });
    ws.send(JSON.stringify(msg));
  });
  const on = (method, fn, sessionId) => {
    const k = method + '|' + (sessionId || '');
    listeners.set(k, [...(listeners.get(k) || []), fn]);
  };
  return { send, on, ws };
}

// A page (tab) with a few helpers over its session.
export async function newPage(chrome, url = 'about:blank') {
  const { browser, width, height } = chrome;
  const { targetId } = await browser.send('Target.createTarget', { url: 'about:blank' });
  const { sessionId } = await browser.send('Target.attachToTarget', { targetId, flatten: true });
  const send = (m, p) => browser.send(m, p, sessionId);
  await send('Page.enable');
  await send('Runtime.enable');
  await send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: false });
  const errors = [];
  browser.on('Runtime.exceptionThrown', (p) => errors.push(p.exceptionDetails?.exception?.description || p.exceptionDetails?.text), sessionId);
  const page = {
    send, errors, sessionId,
    async goto(u, settle = 1200) {
      const loaded = new Promise((r) => browser.on('Page.loadEventFired', r, sessionId));
      await send('Page.navigate', { url: u });
      await Promise.race([loaded, sleep(15000)]);
      await sleep(settle);
    },
    async eval(expr) {
      const r = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true });
      if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
      return r.result.value;
    },
    async waitFor(expr, ms = 15000) {
      const end = Date.now() + ms;
      while (Date.now() < end) {
        try { if (await page.eval(expr)) return true; } catch {}
        await sleep(150);
      }
      throw new Error('Timed out waiting for: ' + expr);
    },
    async shot(clip) {
      const p = { format: 'png', captureBeyondViewport: false };
      if (clip) p.clip = { ...clip, scale: 1 };
      const r = await send('Page.captureScreenshot', p);
      return Buffer.from(r.data, 'base64');
    },
  };
  if (url !== 'about:blank') await page.goto(url);
  return page;
}
