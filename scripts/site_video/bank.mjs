// The bank window, for the "Get my accounts" walkthrough (fetch.json).
//
// Groundwork opens a bank in its own window (bank_window.py, bank_agent_window.py), a separate process the dev server
// starts. On Windows that window is WebView2, which opens a debugging port when the dev server was started with
//     set WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--remote-debugging-port=9340
// The window inherits it. Nothing in Groundwork changes: the window still opens only https sites, here the demo bank
// on groundworkfinance.app (gw 2.0/DEMO_BANK.md).
//
// Clicks and typing go in as real input events (Input.*), as a person's do: the "show me once" script notes only
// those, the same as when someone uses the window.
import { connect, sleep } from './cdp.mjs';

export const BANK_PORT = Number(process.env.GW_BANK_PORT || 9340);
const DEMO = process.env.GW_DEMO_SITE || 'https://groundworkfinance.app';

async function pages() {
  try { return (await (await fetch(`http://127.0.0.1:${BANK_PORT}/json/list`)).json()).filter((p) => p.type === 'page'); }
  catch { return []; }
}

// The bank window's page once it is on the demo site; waits for the window to open.
export async function bankWindow(ms = 45000) {
  const end = Date.now() + ms;
  while (Date.now() < end) {
    const p = (await pages()).find((x) => x.url.startsWith(DEMO));
    if (p) return attach(p);
    await sleep(400);
  }
  throw new Error(`No bank window on ${DEMO} showed up on port ${BANK_PORT}. Was the dev server started with WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS?`);
}

// Waits until no bank window is open (the window closes itself when a run ends).
export async function bankClosed(ms = 60000) {
  const end = Date.now() + ms;
  while (Date.now() < end && (await pages()).some((x) => x.url.startsWith(DEMO))) await sleep(500);
}

async function attach(target) {
  const c = await connect(target.webSocketDebuggerUrl);
  await c.send('Page.enable');
  await c.send('Runtime.enable');
  const page = {
    target,
    alive: () => c.ws.readyState === 1,
    async eval(expr) {
      const r = await c.send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true });
      if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
      return r.result.value;
    },
    async waitFor(expr, ms = 20000) {
      const end = Date.now() + ms;
      while (Date.now() < end) {
        try { if (await page.eval(expr)) return true; } catch { /* the page is changing */ }
        await sleep(200);
      }
      throw new Error('Bank window: timed out waiting for ' + expr);
    },
    // The middle of the first visible element matching sel whose text holds `text` (CSS px, in the viewport).
    async where(sel, text = '') {
      return page.eval(`(() => { const e = [...document.querySelectorAll(${JSON.stringify(sel)})].find(x => x.offsetParent !== null
          && ((x.innerText || x.value || '').includes(${JSON.stringify(text)})));
        if (!e) return null; e.scrollIntoView({block: 'center'}); const r = e.getBoundingClientRect();
        return {x: r.left + r.width / 2, y: r.top + r.height / 2}; })()`);
    },
    async click(sel, text = '') {
      const at = await page.where(sel, text);
      if (!at) throw new Error(`Bank window: nothing to click for ${sel} "${text}"`);
      await sleep(150);
      for (const type of ['mouseMoved', 'mousePressed', 'mouseReleased']) {
        await c.send('Input.dispatchMouseEvent', { type, x: at.x, y: at.y, button: 'left', clickCount: 1 });
      }
    },
    async type(sel, text) {
      await page.click(sel);
      await c.send('Input.insertText', { text });
    },
    // The demo bank shows its code on the page ("A real bank would text this code to you"); a person reads it and
    // types it, and so does this.
    async typeShownCode() {
      const code = await page.eval(`(document.querySelector('.code')?.textContent || '').replace(/\\D/g, '')`);
      if (!/^\d{6}$/.test(code)) throw new Error('Bank window: no code on the page');
      await page.type('#code', code);
    },
    async size() { return page.eval(`({w: innerWidth, h: innerHeight})`); },
    async shot() {
      const { w, h } = await page.size();
      const r = await c.send('Page.captureScreenshot', { format: 'png', clip: { x: 0, y: 0, width: w, height: h, scale: 1 } });
      return Buffer.from(r.data, 'base64');
    },
    async title() { return page.eval('document.title'); },
    close() { try { c.ws.close(); } catch { /* gone */ } },
  };
  return page;
}

// One step of a scene's "bank" list: {click: [sel, text]}, {type: [sel, text]}, {code: true}, {wait: expr}, {ms: n}
export async function bankStep(page, st) {
  if (st.wait) await page.waitFor(st.wait, st.timeout || 20000);
  if (st.click) await page.click(...[].concat(st.click));
  if (st.type) await page.type(...st.type);
  if (st.code) await page.typeShownCode();
  if (st.ms) await sleep(st.ms);
  await sleep(st.after ?? 500);
}

// A PNG's own width and height, from its header.
export function pngSize(buf) { return { w: buf.readUInt32BE(16), h: buf.readUInt32BE(20) }; }
