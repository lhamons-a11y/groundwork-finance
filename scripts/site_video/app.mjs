// Opening Groundwork on its sample household (the Morgans, made-up figures) in a fresh, throwaway dev server.
import { newPage, sleep } from './cdp.mjs';

export const APP = process.env.GW_VIDEO_APP || 'http://127.0.0.1:8791';

// Click the first element matching `sel` whose text contains `text` (or any match when text is empty).
export const clickText = (page, sel, text = '') => page.eval(`(() => {
  const el = [...document.querySelectorAll(${JSON.stringify(sel)})]
    .find(e => e.offsetParent !== null && (e.textContent || '').includes(${JSON.stringify(text)}));
  if (!el) return false;
  el.scrollIntoView({block: 'center'}); el.click(); return true;
})()`);

export async function openSample(chrome) {
  const page = await newPage(chrome, APP + '/');
  // A first launch shows the terms: this is a throwaway database on the dev server.
  if (await page.eval(`!!document.querySelector('input[type=checkbox]') && document.body.innerText.includes('Before you begin')`)) {
    await page.eval(`(() => { const c = [...document.querySelectorAll('input[type=checkbox]')].find(e => e.offsetParent); c.click(); })()`);
    await sleep(300);
    await clickText(page, 'button', 'Agree');
    await sleep(1500);
  }
  if (!(await page.eval(`fetch('/api/sample', {headers: {'X-GW-Token': window.GW_SESSION_TOKEN || ''}}).then(r => r.json()).then(d => !!(d.loaded || (d.data && d.data.loaded)))`))) {
    await page.waitFor(`typeof sampleLoad === 'function'`, 20000);
    await page.eval(`sampleLoad()`);       // the onboarding's own "Look around with a sample household first"
  }
  await page.waitFor(`document.querySelector('.nav-item[data-view=health]') && document.querySelector('.nav-item[data-view=health]').offsetParent !== null`, 30000);
  await sleep(1500);
  return page;
}

// A brand-new Groundwork on an empty throwaway database: the terms accepted, and the welcome left where a person
// first meets it (the AI check). A notice about an Ollama install on THIS computer is closed: it shows this computer's
// own folders and is not part of Groundwork as anyone else meets it.
export async function openFresh(chrome) {
  const page = await newPage(chrome, APP + '/');
  await sleep(1500);
  if (await page.eval(`!!document.querySelector('input[type=checkbox]') && document.body.innerText.includes('Before you begin')`)) {
    await page.eval(`(() => { const c = [...document.querySelectorAll('input[type=checkbox]')].find(e => e.offsetParent); c.click(); })()`);
    await sleep(300);
    await clickText(page, 'button', 'Agree');
    await sleep(2500);
  }
  await page.waitFor(`!!document.getElementById('obStepAICapability') && document.getElementById('obStepAICapability').offsetParent !== null`, 20000);
  await sleep(2500);
  // (offsetParent is null for a fixed-position window, so it is found by its size on screen)
  for (let i = 0; i < 3; i++) {
    const closed = await page.eval(`(() => { const shown = (m) => { const r = m.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
      const d = [...document.querySelectorAll('.modal-overlay, #confirmDialog, [role=dialog]')].find(m => shown(m) && !m.classList.contains('hidden') && /Ollama/.test(m.innerText));
      if (!d) return false; const b = [...d.querySelectorAll('button')].find(b => /^(cancel|close|×)$/i.test(b.textContent.trim()));
      if (b) b.click(); else d.classList.add('hidden'); return true; })()`);
    if (!closed) break;
    await sleep(800);
  }
  return page;
}

export async function view(page, name, settle = 1800) {
  await page.eval(`showView(${JSON.stringify(name)})`);
  await sleep(settle);
  await page.eval(`window.scrollTo(0, 0); (document.querySelector('.main, main, #main') || document.scrollingElement).scrollTop = 0`);
  await sleep(200);
}
