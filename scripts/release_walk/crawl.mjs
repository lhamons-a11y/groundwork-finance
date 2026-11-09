// Click every control on every page of a throwaway Groundwork, and record what breaks.
//   node crawl.mjs <app url> <out dir> [views,comma,separated] [--empty]
// Per page: reset the sample household (unless --empty), open the page, then repeatedly click the first visible
// control not yet tried, until none are left. Groundwork's own confirm dialogs are answered Cancel; other windows are
// closed. Recorded per click: uncaught errors, console errors, failed API calls (4xx/5xx), blocked calls, windows.
// Blocked (never reach the server): anything that opens a bank/airline/hotel window, uninstalls, clears or restores.
import { launch, newPage, sleep } from '../site_video/cdp.mjs';
import { writeFileSync, mkdirSync } from 'node:fs';

const [APP, OUT, viewsArg, ...flags] = process.argv.slice(2);
const EMPTY = flags.includes('--empty') || viewsArg === '--empty';
const FILL = flags.includes('--fill') || viewsArg === '--fill';
const ONCE = flags.includes('--once') || viewsArg === '--once';     // the sample loaded once; every page adds to it
mkdirSync(OUT, { recursive: true });
const ALL = ['dashboard', 'reports', 'automation', 'picture', 'ledger', 'budget', 'health', 'byb', 'trip', 'debt',
  'investments', 'networth', 'trophy', 'settings'];
const VIEWS = viewsArg && !viewsArg.startsWith('--') ? viewsArg.split(',') : ALL;
const MAX_CLICKS = Number(process.env.CRAWL_MAX || 260), MAX_MS = Number(process.env.CRAWL_MS || 420000);

// Installed before the app's own scripts: watch every API call, block the unsafe ones, and never let a native
// dialog, a print or a new window stop the run.
const PRELUDE = `(() => {
  const BLOCK = [/\\/portal\\/open/, /\\/bank-agent\\/(record|fetch|fetch-all|pay-open)$/, /\\/trip\\/(flights|hotels)-window$/,
    /\\/ollama-notice\\/uninstall/, /\\/sample\\/clear/, /\\/backup\\/restore/, /\\/auto-import\\/remove-download/,
    /\\/road-map\\/download/, /\\/api\\/update-check/];
  window.__crawl = { http: [], blocked: [], dialogs: [], opened: [], rejections: [] };
  const of = window.fetch.bind(window);
  window.__rawFetch = of;              // the crawl's own setup calls, never blocked
  window.fetch = async (input, init = {}) => {
    const url = typeof input === 'string' ? input : input.url, method = (init.method || 'GET').toUpperCase();
    const path = url.replace(location.origin, '');
    if (method !== 'GET' && BLOCK.some(b => b.test(path))) {
      window.__crawl.blocked.push(method + ' ' + path);
      return new Response(JSON.stringify({ ok: false, error: 'blocked by the crawl' }), { status: 418, headers: { 'Content-Type': 'application/json' } });
    }
    const r = await of(input, init);
    if (r.status >= 400 && path.startsWith('/api/')) {
      let body = ''; try { body = (await r.clone().text()).slice(0, 300); } catch (e) {}
      window.__crawl.http.push({ s: r.status, m: method, p: path.slice(0, 160), body });
    }
    return r;
  };
  window.alert = (m) => { window.__crawl.dialogs.push('alert: ' + String(m).slice(0, 200)); };
  window.confirm = (m) => { window.__crawl.dialogs.push('confirm: ' + String(m).slice(0, 200)); return false; };
  window.prompt = (m) => { window.__crawl.dialogs.push('prompt: ' + String(m).slice(0, 200)); return null; };
  window.print = () => { window.__crawl.dialogs.push('print'); };
  window.open = (u) => { window.__crawl.opened.push(String(u).slice(0, 200)); return null; };
  window.addEventListener('unhandledrejection', (e) => {
    window.__crawl.rejections.push(String((e.reason && (e.reason.stack || e.reason.message)) || e.reason).slice(0, 400)); });
})();`;

const ENUM = `(() => {
  const vis = (e) => { if (!e.isConnected) return false; const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' && !e.closest('[inert]'); };
  const modal = [...document.querySelectorAll('.modal-overlay, #confirmDialog, [role=dialog]')].find(m => vis(m) && !m.classList.contains('hidden'));
  const root = modal || document;
  const els = [...root.querySelectorAll('button, [onclick], summary, a[href], [role=tab], [role=button], input[type=checkbox], input[type=radio], select')]
    .filter(e => vis(e) && !e.disabled && !e.closest('.sidebar, nav.sidebar, #sidebar') && !e.classList.contains('nav-item'));
  // Leaving goes last: a window's fields, choices and Save are pressed before its ×, Cancel or Back
  const leaves = (e) => /^(←|‹|✕|×)|^(cancel|close|back|dismiss|not now|no thanks|skip)\\b/i.test((e.innerText || e.getAttribute('aria-label') || '').trim()) || e.classList.contains('modal-close');
  els.sort((a, b) => leaves(a) - leaves(b));
  window.__els = els;
  return els.map((e, i) => {
    const t = (e.innerText || e.value || e.getAttribute('aria-label') || e.title || '').replace(/\\s+/g, ' ').trim().slice(0, 60);
    const oc = (e.getAttribute('onclick') || e.getAttribute('onchange') || e.getAttribute('href') || '').replace(/\\s+/g, ' ').slice(0, 90);
    return { i, sig: e.tagName + '|' + (e.id || '') + '|' + t + '|' + oc, tag: e.tagName, text: t, oc, inModal: !!modal };
  });
})()`;

// Never pressed: they leave the page, clear the household, or are the sample bar's own "Start with my own".
const SKIP = /Start with my own|Clear the sample|Restore (from|backup)|Installed apps|^Uninstall|Report a problem|Open in mail|mailto:|^https?:|target=_blank/i;

const chrome = await launch({ port: Number(process.env.CRAWL_PORT || 9341), width: 1600, height: 1000 });
const results = [];
try {
  const page = await newPage(chrome);
  await page.send('Page.addScriptToEvaluateOnNewDocument', { source: PRELUDE });
  await chrome.browser.send('Browser.setDownloadBehavior', { behavior: 'deny' }).catch(() => {});
  const consoleErr = [];
  chrome.browser.on('Runtime.consoleAPICalled', (p) => {
    if (p.type === 'error') consoleErr.push(p.args.map(a => a.value ?? a.description ?? '').join(' ').slice(0, 300));
  }, page.sessionId);

  const call = (m, u, b) => page.eval(`window.__rawFetch(${JSON.stringify(u)}, {method: ${JSON.stringify(m)}, headers: {'Content-Type': 'application/json', 'X-GW-Token': window.GW_SESSION_TOKEN || ''}, body: ${b ? JSON.stringify(JSON.stringify(b)) : 'undefined'}}).then(r => r.text())`);

  async function fresh() {
    await page.goto(APP + '/', 2500);
    if (await page.eval(`document.body.innerText.includes('Before you begin')`)) {
      await page.eval(`(() => { const c = [...document.querySelectorAll('input[type=checkbox]')].find(e => e.offsetParent); c && c.click(); })()`);
      await sleep(300);
      await page.eval(`[...document.querySelectorAll('button')].find(b => b.offsetParent && b.textContent.includes('Agree')).click()`);
      await sleep(1500);
    }
  }

  await fresh();
  const tmpExport = process.env.TEMP + '\\gw_crawl_exports';
  await call('PATCH', '/api/settings', { export_dir: tmpExport });

  for (const view of VIEWS) {
    // a fresh household per page, so one page's deletes can't empty the next
    if (ONCE && view === VIEWS[0]) await call('POST', '/api/sample/load', {});
    if (!EMPTY && !ONCE) {
      await call('POST', '/api/sample/clear', {}).catch(() => {});
      await fresh();
      await call('POST', '/api/sample/load', {});
    }
    await fresh();
    // the welcome may still be up on an empty install: answer it as "AI off", "by hand", and leave it
    await page.eval(`(() => { const o = document.getElementById('onboardingOverlay'); if (o && !o.classList.contains('hidden')) {
        if (typeof _onboardingDismiss === 'function') _onboardingDismiss(); else o.classList.add('hidden'); } })()`).catch(() => {});
    await page.eval(`document.querySelectorAll('.modal-overlay').forEach(m => m.classList.add('hidden'))`).catch(() => {});
    const hasView = await page.eval(`!!document.getElementById('view-${view}') || ${view === 'picture'}`);
    if (!hasView) { results.push({ view, missing: true }); continue; }
    const go = async () => { await page.eval(`showView(${JSON.stringify(view)})`).catch(e => results.push({ view, err: 'showView: ' + e.message })); await sleep(1800); };
    await go();
    await page.eval(`window.__crawl.http = []; window.__crawl.blocked = []; window.__crawl.dialogs = []; window.__crawl.opened = []; window.__crawl.rejections = []`);
    page.errors.length = 0; consoleErr.length = 0;
    writeFileSync(`${OUT}\\${view}_0.png`, await page.shot());

    const tried = new Set(); const t0 = Date.now(); let clicks = 0, stuck = 0;
    const log = [];
    while (clicks < MAX_CLICKS && Date.now() - t0 < MAX_MS) {
      let list;
      try { list = await page.eval(ENUM); } catch (e) { log.push({ err: 'enumerate: ' + e.message }); await go(); continue; }
      const next = list.find(c => !tried.has(c.sig) && !SKIP.test(c.text + ' ' + c.oc));
      if (!next) {
        // nothing new here: back out of a sub-page or window (Back / Close), then the page itself; stop when that
        // shows nothing new either
        if (stuck >= 3) break;
        stuck++;
        const backed = await page.eval(`(() => { const b = window.__els.find(e => /^(←|‹|✕|×)|\\b(back|close|cancel|done)\\b/i.test((e.innerText || e.getAttribute('aria-label') || '').trim()));
          if (b && ${stuck} < 3) { b.click(); return true; }
          document.querySelectorAll('.modal-overlay').forEach(m => m.classList.add('hidden')); return false; })()`).catch(() => false);
        if (!backed) await go(); else await sleep(700);
        continue;
      }
      stuck = 0;
      tried.add(next.sig); clicks++;
      const before = await page.eval(`({view: (document.querySelector('.view.active') || {}).id || '', modal: [...document.querySelectorAll('.modal-overlay')].filter(m => !m.classList.contains('hidden')).map(m => m.id).join(',')})`);
      const errMark = page.errors.length, conMark = consoleErr.length;
      let clickErr = null, filled = 0;
      // --fill: before a button that saves or adds, type plausible values into the empty fields around it
      if (FILL && next.tag !== 'SELECT' && /\b(save|add|create|done|import|confirm|next|apply|record|set|update|submit|continue|plan|calculate|log|keep|use)\b/i.test(next.text)) {
        filled = await page.eval(`(() => { const b = window.__els[${next.i}];
          const box = b.closest('.modal, [role=dialog], form, .card, .gw-auto-inner, details, section') || b.parentElement;
          let n = 0; const today = new Date().toISOString().slice(0, 10);
          for (const e of box.querySelectorAll('input, textarea, select')) {
            const r = e.getBoundingClientRect(); if (!r.width || e.disabled || e.readOnly) continue;
            const hint = ((e.placeholder || '') + ' ' + (e.getAttribute('aria-label') || '') + ' ' + (e.id || '') + ' ' + (e.name || '')).toLowerCase();
            let v = null;
            if (e.tagName === 'SELECT') { if (!e.value) { const o = [...e.options].find(o => o.value); if (o) v = o.value; } }
            else if (e.type === 'checkbox' || e.type === 'radio' || e.type === 'file' || e.type === 'range' || e.type === 'hidden') continue;
            else if (e.value) continue;
            else if (e.type === 'date') v = today;
            else if (e.type === 'month') v = today.slice(0, 7);
            else if (e.type === 'number') v = /apr|rate|%|pct|percent/.test(hint) ? '6.5' : /day/.test(hint) ? '15' : /year/.test(hint) ? '2030' : '250';
            else if (e.type === 'url' || /http|website|url/.test(hint)) v = 'https://www.example.com';
            else if (e.type === 'email') v = 'crawl@example.com';
            else if (e.type === 'password') continue;
            else if (/amount|balance|price|cost|\\$|min|payment|income|value|limit|target|budget/.test(hint)) v = '250';
            else if (/apr|rate|%/.test(hint)) v = '6.5';
            else if (/date|yyyy/.test(hint)) v = today;
            else v = 'Crawl test ' + (n + 1);
            if (v === null) continue;
            e.value = v; e.dispatchEvent(new Event('input', {bubbles: true})); e.dispatchEvent(new Event('change', {bubbles: true})); n++;
          }
          return n; })()`).catch(() => 0);
      }
      try {
        await page.eval(`(() => { const e = window.__els[${next.i}]; if (e.tagName === 'SELECT') {
            const o = [...e.options].find(o => !o.selected && o.value !== '') || e.options[e.options.length - 1];
            if (o) { e.value = o.value; e.dispatchEvent(new Event('change', {bubbles: true})); } return; }
          e.scrollIntoView({block: 'center'}); e.click(); })()`);
      } catch (e) { clickErr = e.message.slice(0, 200); }
      await sleep(Number(process.env.CRAWL_WAIT || 700));
      const c = await page.eval(`(() => { const x = window.__crawl; const out = {http: x.http.splice(0), blocked: x.blocked.splice(0), dialogs: x.dialogs.splice(0), opened: x.opened.splice(0), rejections: x.rejections.splice(0)};
          out.view = (document.querySelector('.view.active') || {}).id || '';
          out.modal = [...document.querySelectorAll('.modal-overlay')].filter(m => !m.classList.contains('hidden')).map(m => m.id).join(',');
          return out; })()`).catch(e => ({ evalErr: e.message }));
      const rec = { text: next.text, oc: next.oc, inModal: next.inModal, filled, ...c, clickErr,
        errors: page.errors.slice(errMark), console: consoleErr.slice(conMark) };
      const notable = rec.clickErr || rec.errors.length || rec.console.length || (rec.http && rec.http.length) || (rec.rejections && rec.rejections.length) || rec.evalErr;
      log.push(notable ? rec : { text: rec.text, ok: true, filled: filled || undefined, modal: rec.modal || undefined, blocked: rec.blocked && rec.blocked.length ? rec.blocked : undefined });
      // close whatever opened, and come back to the page
      if (c.modal && c.modal !== before.modal) {
        await page.eval(`(() => { const d = document.getElementById('confirmDialog'); if (d && !d.classList.contains('hidden')) {
            const b = [...d.querySelectorAll('button')].find(b => /cancel|no|close|×/i.test(b.textContent.trim())); if (b) { b.click(); return; } }
          })()`).catch(() => {});
      }
      if (c.view && c.view !== 'view-' + view && view !== 'picture') await go();
    }
    // whatever is still open
    await page.eval(`document.querySelectorAll('.modal-overlay').forEach(m => m.classList.add('hidden'))`).catch(() => {});
    writeFileSync(`${OUT}\\${view}_1.png`, await page.shot());
    const bad = log.filter(r => !r.ok);
    results.push({ view, clicks, seconds: Math.round((Date.now() - t0) / 1000), problems: bad.length, log });
    console.log(`${view}: ${clicks} controls, ${bad.length} with problems, ${Math.round((Date.now() - t0) / 1000)} s`);
    writeFileSync(`${OUT}\\crawl.json`, JSON.stringify(results, null, 1));
  }
} finally { await chrome.close(); }
writeFileSync(`${OUT}\\crawl.json`, JSON.stringify(results, null, 1));
