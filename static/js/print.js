// Every page prints as a report (gw 2.0/PRINT_REPORTS.md; Rob 2026-11-05). With AI on, "print this page" asks for it; with
// AI off, a Print button stands where the Ask box was. The report is built on a sheet of its own, outside the app, so
// the page behind it is not changed: what you press is left out and what you typed is shown as text.
//
//   gwPrintPage()        the page in front: its own report if it has one, otherwise the page itself, redrawn
//   gwPrintIntent(...)   the Ask bar's words for it, typed or spoken
//
// Nothing is sent or kept. Printing or saving a PDF is the person's own act, in the browser's own print window.

const GW_PRINT_LEDGER_MODES = ['detail', 'overview'];
let _gwPrintLedgerAsked = false;

function _prEsc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c])); }
function _prLong(iso) {
  if (!iso) return '';
  const d = new Date(iso + 'T12:00:00');
  return isNaN(d) ? String(iso) : d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
}
function _prShort(iso) {
  const d = new Date(String(iso) + 'T12:00:00');
  return isNaN(d) ? String(iso || '') : d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}
function _prToday() { return new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' }); }
function _prStat(label, value, sub, cls) {
  return `<div class="pr-stat"><div class="pr-stat-l">${_prEsc(label)}</div><div class="pr-stat-v ${cls || ''}">${value}</div>${sub ? `<div class="pr-stat-s">${_prEsc(sub)}</div>` : ''}</div>`;
}
function _prSheet(title, sub, body) {
  return `<div class="pr-head"><div><div class="pr-brand">Groundwork</div><div class="pr-title">${_prEsc(title)}</div>${sub ? `<div class="pr-sub">${_prEsc(sub)}</div>` : ''}</div>
      <div class="pr-date">Prepared ${_prEsc(_prToday())}</div></div>
    ${body}
    <div class="pr-foot">Prepared by Groundwork from the records on this computer.</div>`;
}

// ── A whole page, redrawn ──────────────────────────────────────────────────────────────────────────────────────────
const PR_DROP = 'button, nav, script, style, template, [role="tablist"], .row-del, .modal, .tooltip, [id^="fvb-"], [data-no-print]';

// Marks what is not on screen before the copy is taken, because the copy cannot be measured once it is apart from the page.
function _prCloneVisible(src) {
  const copy = src.cloneNode(true);
  const from = [src, ...src.querySelectorAll('*')];
  const to = [copy, ...copy.querySelectorAll('*')];
  from.forEach((el, i) => {
    if (i === 0) return;
    if (el.tagName === 'CANVAS' && el.width && el.height) {
      try { const img = document.createElement('img'); img.src = el.toDataURL('image/png'); img.alt = el.getAttribute('aria-label') || ''; to[i].dataset.prImg = '1'; to[i]._prImg = img; } catch (_e) { /* a canvas it cannot read stays out */ }
    }
    const st = getComputedStyle(el);
    if (st.display === 'none' || st.visibility === 'hidden') to[i].dataset.prHidden = '1';
    // A typed value lives on the live element, not in the copied markup.
    if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') to[i].dataset.prValue = el.type === 'checkbox' || el.type === 'radio' ? (el.checked ? 'yes' : '') : el.value;
    if (el.tagName === 'SELECT') {
      to[i].dataset.prValue = el.selectedOptions[0] ? el.selectedOptions[0].textContent : '';
      if (el.value) to[i].dataset.prChosen = '1';
    }
    if (el.tagName === 'DETAILS') to[i].dataset.prOpen = el.open ? '1' : '';
  });
  return copy;
}

// A form nobody has filled in is not part of a report. Its card is left out whole, words and all, unless it also holds
// figures: a card can list your debts above an empty "add a debt" form.
function _prIsEmptyForm(card) {
  return card.dataset.prEmptied === '1' && !card.querySelector('table, svg, img, .pr-value') && !/\$\s?\d/.test(card.textContent);
}

// What you press that reads as words: "Arrange", "Use this", "See full payoff plan →". A row you can press that holds a
// figure or a name is kept; these are only the words of a command.
const PR_COMMAND_WORDS = /(?:→|›|\?)$|^(?:arrange|use this|see |show |view |edit|add |change|open |hide|more|less|manage|tap |click )/i;
function _prIsCommand(el) {
  const text = el.textContent.trim();
  return text.length <= 80 && !/\d/.test(text) && !el.querySelector('table, svg, img') && PR_COMMAND_WORDS.test(text);
}

function _prTidy(copy) {
  copy.querySelectorAll('[data-pr-hidden]').forEach(el => el.remove());
  copy.querySelectorAll('[data-pr-img]').forEach(el => { if (el._prImg) el.replaceWith(el._prImg); else el.remove(); });
  copy.querySelectorAll(PR_DROP).forEach(el => el.remove());
  copy.querySelectorAll('details').forEach(d => {
    const name = d.querySelector('summary')?.textContent || '';
    // The working behind a figure stays with the figure (transparency standard); help folded away stays folded away.
    if (d.dataset.prOpen === '1' || /assum|working|how (?:this|these|it)|why/i.test(name)) d.setAttribute('open', ''); else d.remove();
  });
  copy.querySelectorAll('input, textarea, select').forEach(f => {
    if (f.type === 'hidden' || f.type === 'password' || f.type === 'file') { f.remove(); return; }
    const val = String(f.dataset.prValue || '').trim();
    if (f.type === 'checkbox' || f.type === 'radio') {           // an unticked box beside a row is a control; in Settings it is the setting
      if (val || f.closest('#view-settings, .pr-settings')) f.replaceWith(document.createTextNode(val ? '☑ ' : '☐ ')); else f.remove();
      return;
    }
    const field = f.closest('.field');
    // A filter set to "All accounts" says nothing; a setting left at its default still does.
    if (f.tagName === 'SELECT' && !field && !f.dataset.prChosen) { f.remove(); return; }
    if (!val) { const c = f.closest('.card'); if (c) c.dataset.prEmptied = '1'; (field || f).remove(); return; }
    const span = document.createElement('span');
    span.className = 'pr-value';
    span.textContent = val;
    f.replaceWith(span);
  });
  copy.querySelectorAll('.card').forEach(c => { if (_prIsEmptyForm(c)) c.remove(); });
  // An offer to run an analysis is not a finding. Once it has run, its words are longer than the offer and it stays.
  copy.querySelectorAll('.card').forEach(c => { if (/AI-powered/.test(c.textContent) && c.textContent.trim().length < 220) c.remove(); });
  copy.querySelectorAll('[onclick]').forEach(el => { if (_prIsCommand(el)) el.remove(); });
  copy.querySelectorAll('a').forEach(a => a.replaceWith(...a.childNodes));
  copy.querySelectorAll('*').forEach(el => {
    [...el.attributes].forEach(at => { if (/^on/i.test(at.name) || /^data-pr-/.test(at.name) || at.name === 'contenteditable' || at.name === 'tabindex') el.removeAttribute(at.name); });
    if (!el.closest('svg')) el.removeAttribute('id');
  });
  // What was only a frame around controls is now an empty box.
  [...copy.querySelectorAll('*')].reverse().forEach(el => {
    if (el.closest('svg') || /^(IMG|SVG|HR|BR|TD|TH|TR|COL|LINE)$/i.test(el.tagName)) return;
    if (!el.textContent.trim() && !el.querySelector('img, svg, canvas, hr')) el.remove();
  });
  // A long card may cross a page rather than leave most of one blank.
  copy.querySelectorAll('.card').forEach(c => { if (c.querySelector('tbody tr:nth-child(12)') || c.textContent.length > 900) c.classList.add('pr-long'); });
  return copy;
}

function _prActiveView() {
  const v = document.querySelector('.view.active');
  return v ? v.id.replace(/^view-/, '') : 'dashboard';
}

function _prActiveTabName(view) {
  const tab = view.querySelector('[role="tab"][aria-selected="true"]');
  return tab ? tab.textContent.replace(/\s+/g, ' ').trim() : '';
}

function _prPageName(name) {
  if (VIEW_LABELS[name]) return VIEW_LABELS[name];
  const nav = document.querySelector(`.nav-item[data-view="${name}"]`);
  const said = nav ? nav.textContent.replace(/\s+/g, ' ').replace(/^[^A-Za-z]+|[^A-Za-z]+$/g, '') : '';
  return said || (name[0].toUpperCase() + name.slice(1));
}

// A page's own big title and line under it are on the sheet's heading already.
function _prDropOwnHeading(copy, heading, sub) {
  [heading, sub].filter(Boolean).forEach(words => {
    const hit = [...copy.querySelectorAll('*')].find(e => !e.children.length && e.textContent.trim() === words);
    if (hit) hit.remove();
  });
}

function _prWholePage(name) {
  const view = g(`view-${name}`);
  const src = (name === 'reports' && g('rcReportBody')) || view;
  if (!src) return null;
  const sub = view.querySelector('.section-sub')?.textContent.trim() || '';
  const tab = _prActiveTabName(view);
  const cloned = _prCloneVisible(src);
  if (name === 'settings') cloned.classList.add('pr-settings');
  const copy = _prTidy(cloned);
  const inReport = name === 'reports' && src !== view;
  const heading = inReport ? (copy.querySelector('h2')?.textContent.trim() || 'Report') : _prPageName(name);
  if (inReport) copy.querySelector('h2')?.remove();
  else _prDropOwnHeading(copy, heading, sub);
  copy.classList.remove('view', 'active');
  copy.classList.add('pr-page');
  copy.style.cssText = '';
  return _prSheet(heading, tab || sub, copy.outerHTML);
}

// ── The Ledger: asks which, then either one ────────────────────────────────────────────────────────────────────────
function _prLedgerRows() {
  const rows = _ledgerFilteredTxns().slice();
  rows.sort((a, b) => String(a.date || '').localeCompare(String(b.date || '')));
  return rows;
}

// The same rule as the Ledger's own In and Out: with every account showing, a payment arriving on a card is not income.
function prLedgerSummary(rows, debtNames, allAccounts) {
  const names = new Set(debtNames || []);
  const counted = allAccounts ? rows.filter(t => !(t.type === 'credit' && t.account && names.has(t.account))) : rows;
  const money = counted.reduce((m, t) => {
    const amt = Number(t.amount) || 0;
    if (t.type === 'credit') m.in += amt;
    if (t.type === 'debit') {
      m.out += amt;
      const cat = t.category || 'Uncategorized', who = t.merchant || t.description || 'Unnamed';
      const c = m.cats[cat] || (m.cats[cat] = { name: cat, total: 0, count: 0 });
      c.total += amt; c.count += 1;
      const w = m.who[who] || (m.who[who] = { name: who, total: 0, count: 0 });
      w.total += amt; w.count += 1;
    }
    return m;
  }, { in: 0, out: 0, cats: {}, who: {} });
  const byTotal = o => Object.values(o).sort((a, b) => b.total - a.total || a.name.localeCompare(b.name));
  return { count: rows.length, in: money.in, out: money.out, net: money.in - money.out, cats: byTotal(money.cats), who: byTotal(money.who) };
}

function _prLedgerScope(rows) {
  const bits = [];
  const search = g('ledgerSearch')?.value?.trim(), cat = g('ledgerCatFilter')?.value, acct = g('ledgerAccountFilter')?.value;
  if (search) bits.push(`matching "${search}"`);
  if (cat) bits.push(cat);
  if (acct) bits.push(acct);
  const f = rows[0]?.date, l = rows[rows.length - 1]?.date;
  const span = f ? (f === l ? _prLong(f) : `${_prLong(f)} to ${_prLong(l)}`) : 'No lines';
  return [span, ...bits].join(' · ');
}

function _prLedgerOverview() {
  const rows = _prLedgerRows();
  const allAccounts = !g('ledgerAccountFilter')?.value;
  const s = prLedgerSummary(rows, (S.debtCards || []).map(c => c.name).filter(Boolean), allAccounts);
  const top = s.cats.length ? s.cats[0].total : 1;
  const body = `<div class="pr-stats">${_prStat('Money in', fmt(s.in), '', 'pr-good')}${_prStat('Money out', fmt(s.out), '', 'pr-bad')}
      ${_prStat('Net', `${s.net >= 0 ? '+' : '-'}${fmt(Math.abs(s.net))}`, '', s.net >= 0 ? 'pr-good' : 'pr-bad')}${_prStat('Lines', String(s.count))}</div>
    <div class="pr-section pr-long"><div class="pr-h">Where the money went, by category</div>
      <table class="pr-t"><thead><tr><th>Category</th><th style="width:30%"></th><th class="num">Lines</th><th class="num">Total</th><th class="num">Share</th></tr></thead><tbody>
      ${s.cats.map(c => `<tr><td>${_prEsc(c.name)}</td><td><div class="pr-bar"><div style="width:${Math.max(2, Math.round(c.total / top * 100))}%"></div></div></td><td class="num">${c.count}</td><td class="num">${fmt(c.total)}</td><td class="num">${s.out > 0 ? Math.round(c.total / s.out * 100) : 0}%</td></tr>`).join('')}
      </tbody></table></div>
    <div class="pr-section"><div class="pr-h">Biggest places, by total spent</div>
      <table class="pr-t"><thead><tr><th>Place</th><th class="num">Lines</th><th class="num">Total</th></tr></thead><tbody>
      ${s.who.slice(0, 10).map(w => `<tr><td>${_prEsc(w.name)}</td><td class="num">${w.count}</td><td class="num">${fmt(w.total)}</td></tr>`).join('')}
      </tbody></table></div>
    <div class="pr-note">Totals use the lines showing in the Ledger when this was printed.${allAccounts ? ' A payment arriving on a card is not counted as money in, the same as the Ledger.' : ''}</div>`;
  return _prSheet('Ledger Overview', _prLedgerScope(rows), body);
}

function _prLedgerDetail() {
  const rows = _prLedgerRows();
  const allAccounts = !g('ledgerAccountFilter')?.value;
  const s = prLedgerSummary(rows, (S.debtCards || []).map(c => c.name).filter(Boolean), allAccounts);
  const body = `<div class="pr-stats">${_prStat('Money in', fmt(s.in), '', 'pr-good')}${_prStat('Money out', fmt(s.out), '', 'pr-bad')}${_prStat('Lines', String(s.count))}</div>
    <div class="pr-section pr-long"><table class="pr-t"><thead><tr><th>Date</th><th>Description</th><th>Category</th><th>Account</th><th class="num">Amount</th></tr></thead><tbody>
    ${rows.map(t => `<tr><td style="white-space:nowrap">${_prEsc(_prShort(t.date))}</td><td>${_prEsc(t.merchant || t.description || '')}</td><td>${_prEsc(t.category || '')}</td><td>${_prEsc(t.account || '')}</td><td class="num ${t.type === 'credit' ? 'pr-good' : ''}">${t.type === 'credit' ? '+' : '-'}${fmt(Number(t.amount) || 0)}</td></tr>`).join('')}
    </tbody></table></div>`;
  return _prSheet('Ledger Detail', _prLedgerScope(rows), body);
}

function _prAskLedger() {
  _gwPrintLedgerAsked = true;
  if (typeof _askPanel !== 'function') { gwPrintPage('detail'); return; }
  const p = _askPanel();
  p.innerHTML = `<div style="font-size:var(--fs-base);color:var(--ink);font-weight:600;margin-bottom:4px">Print the Ledger</div>
    <div style="font-size:var(--fs-base);color:var(--ink);line-height:1.6;margin-bottom:10px">Would you like a detail page or an overview page?</div>
    <div class="byb-in" style="display:flex;gap:6px;flex-wrap:wrap">
      <button class="btn btn-primary btn-sm" onclick="gwPrintPage('detail')">Detail: every line</button>
      <button class="btn btn-secondary btn-sm" onclick="gwPrintPage('overview')">Overview: totals by category</button>
      <button class="btn btn-ghost btn-sm" onclick="_gwPrintLedgerAsked = false; closeAsk()">Not now</button></div>`;
  if (typeof _askSaid === 'function') _askSaid('Would you like a detail page or an overview page?');
}

// ── Trip Planner: an itinerary ─────────────────────────────────────────────────────────────────────────────────────
// A simplified outline of the lower 48 states, longitude and latitude, drawn on this computer: no map service is asked.
const PR_US_OUTLINE = [[-124.7,48.4],[-123.0,48.3],[-122.8,49],[-95.15,49],[-95.15,49.4],[-94.6,48.7],[-93,48.6],[-91.5,48.1],[-89.6,48],[-92,46.7],[-90.8,46.9],[-88.4,47.4],[-87.9,47.47],[-87.5,46.5],[-85,46.7],[-84.4,46.5],[-84.7,45.95],[-87,45.7],[-87.6,45.1],[-88,44.5],[-87.3,44.9],[-87.7,43.5],[-87.9,42.5],[-87.6,41.8],[-87,41.65],[-86.5,42.1],[-86.2,43],[-86.5,44],[-86.2,44.7],[-85.5,45.2],[-85,45.7],[-84.2,45.6],[-83.4,45.1],[-83.3,44.3],[-83.9,43.7],[-82.9,44.05],[-82.45,43],[-83.1,42.2],[-83.4,41.7],[-82.5,41.4],[-81.7,41.5],[-80.1,42.2],[-78.9,42.85],[-79.05,43.27],[-77.5,43.25],[-76.2,43.55],[-76.3,44.2],[-75,45],[-71.5,45],[-71,45.3],[-70.3,45.9],[-70,46.7],[-69.2,47.45],[-68.3,47.35],[-67.8,47.05],[-67.8,45.7],[-67,44.85],[-68.8,44.3],[-70.2,43.6],[-70.7,42.7],[-71,42.3],[-70,41.8],[-71.2,41.5],[-72.9,41.25],[-73.7,40.9],[-72,41],[-73.9,40.55],[-74.1,39.7],[-74.9,38.95],[-75.5,39.5],[-75.1,38.5],[-75.9,37.15],[-76,37],[-75.5,35.3],[-76.6,34.7],[-77.9,33.9],[-79.2,33.2],[-81,32],[-81.4,30.7],[-81.2,29.6],[-80.55,28.4],[-80.05,26.8],[-80.2,25.4],[-81.1,25.15],[-81.8,26.1],[-82.7,27.7],[-82.7,28.9],[-83.7,29.9],[-84.3,30.05],[-85.3,29.7],[-86.5,30.4],[-88,30.25],[-89.4,30.25],[-89.2,29.1],[-90.8,29.1],[-92,29.6],[-93.8,29.7],[-94.8,29.3],[-96.4,28.4],[-97.3,27.4],[-97.15,25.95],[-99.1,26.4],[-99.5,27.5],[-100.7,29.1],[-101.5,29.75],[-102.7,29.7],[-103.2,29],[-104.5,29.6],[-106.5,31.75],[-108.2,31.78],[-108.2,31.33],[-111.07,31.33],[-114.8,32.5],[-117.12,32.53],[-117.3,33.1],[-118.4,33.75],[-119.2,34.15],[-120.6,34.55],[-120.7,35.2],[-121.9,36.6],[-122.5,37.5],[-123,38],[-123.8,39.3],[-124.4,40.4],[-124.2,41.8],[-124.5,42.8],[-124,44.6],[-124,46.25],[-124.7,47.9]];
// For finding your way on the map; only the ones that fit are drawn.
const PR_CITIES = [['Seattle',-122.33,47.61],['Portland',-122.68,45.52],['San Francisco',-122.42,37.77],['Los Angeles',-118.24,34.05],['San Diego',-117.16,32.72],['Las Vegas',-115.14,36.17],['Phoenix',-112.07,33.45],['Salt Lake City',-111.89,40.76],['Boise',-116.2,43.62],['Denver',-104.99,39.74],['Albuquerque',-106.65,35.08],['El Paso',-106.49,31.76],['Billings',-108.5,45.78],['Fargo',-96.79,46.88],['Minneapolis',-93.27,44.98],['Omaha',-95.93,41.26],['Kansas City',-94.58,39.1],['Oklahoma City',-97.52,35.47],['Dallas',-96.8,32.78],['Houston',-95.37,29.76],['San Antonio',-98.49,29.42],['New Orleans',-90.07,29.95],['Memphis',-90.05,35.15],['St. Louis',-90.2,38.63],['Chicago',-87.63,41.88],['Milwaukee',-87.91,43.04],['Detroit',-83.05,42.33],['Indianapolis',-86.16,39.77],['Columbus',-83,39.96],['Louisville',-85.76,38.25],['Nashville',-86.78,36.16],['Atlanta',-84.39,33.75],['Birmingham',-86.8,33.52],['Jacksonville',-81.66,30.33],['Tampa',-82.46,27.95],['Miami',-80.19,25.76],['Charlotte',-80.84,35.23],['Raleigh',-78.64,35.78],['Pittsburgh',-80,40.44],['Washington',-77.04,38.91],['Philadelphia',-75.17,39.95],['New York',-74,40.71],['Boston',-71.06,42.36],['Buffalo',-78.88,42.89],['Portland ME',-70.26,43.66]];

// Width and height are fixed; the view fits the two ends with room around them. Pure, so a test can read it.
function prMapFrame(a, b, w, h) {
  const midLat = (a.lat + b.lat) / 2;
  const kx = Math.cos(midLat * Math.PI / 180);
  const spanX = Math.max(Math.abs(a.lon - b.lon) * kx, 3.2), spanY = Math.max(Math.abs(a.lat - b.lat), 2.2);
  const scale = Math.min(w / (spanX * 1.5), h / (spanY * 1.6));
  const cx = (a.lon + b.lon) / 2, cy = midLat;
  return { scale, project: (lon, lat) => [w / 2 + (lon - cx) * kx * scale, h / 2 - (lat - cy) * scale] };
}

function prRouteMapSVG(pts, fromName, toName, miles) {
  const W = 680, H = 300;
  const a = pts.origin, b = pts.destination;
  const f = prMapFrame(a, b, W, H);
  const xy = (lon, lat) => f.project(lon, lat).map(n => Math.round(n * 10) / 10);
  const land = PR_US_OUTLINE.map(([lon, lat]) => xy(lon, lat).join(',')).join(' ');
  const [ax, ay] = xy(a.lon, a.lat), [bx, by] = xy(b.lon, b.lat);
  // A label stays inside the map and off the route: above or below its dot on a route that runs across, and to the
  // side on one that runs up and down.
  const across = Math.abs(ax - bx) >= Math.abs(ay - by);
  const label = (x, y, otherY, text, cls) => {
    if (across) {
      const below = y >= otherY ? y < H - 30 : y < 30;
      const anchor = x < 70 ? 'start' : x > W - 70 ? 'end' : 'middle';
      return `<text x="${x}" y="${below ? y + 22 : y - 13}" text-anchor="${anchor}" ${cls}>${_prEsc(text)}</text>`;
    }
    const left = x > W - 150;
    return `<text x="${left ? x - 11 : x + 11}" y="${y + 4}" text-anchor="${left ? 'end' : 'start'}" ${cls}>${_prEsc(text)}</text>`;
  };
  const near = (x, y, ox, oy, d) => Math.hypot(x - ox, y - oy) < d;
  const placed = [];
  const towns = PR_CITIES.map(([n, lon, lat]) => [n, ...xy(lon, lat)])
    .filter(([, x, y]) => x > 20 && x < W - 90 && y > 16 && y < H - 12 && !near(x, y, ax, ay, 70) && !near(x, y, bx, by, 70))
    .filter(([, x, y]) => { if (placed.some(([px, py]) => Math.abs(px - x) < 92 && Math.abs(py - y) < 18)) return false; placed.push([x, y]); return true; })
    .map(([n, x, y]) => `<circle cx="${x}" cy="${y}" r="2" fill="#94a3b8"/><text x="${x + 5}" y="${y + 3}" font-size="9" fill="#64748b" font-family="Inter,Arial,sans-serif">${_prEsc(n)}</text>`).join('');
  const mx = (ax + bx) / 2, my = (ay + by) / 2;
  const tag = `~${Number(miles).toLocaleString('en-US')} mi by road`;
  const tagW = tag.length * 6.6 + 16;
  return `<svg class="it-map" viewBox="0 0 ${W} ${H}" role="img" aria-label="${_prEsc(`Map from ${fromName} to ${toName}, about ${miles} miles by road`)}">
    <rect width="${W}" height="${H}" fill="#e8f1f8"/>
    <polygon points="${land}" fill="#f7f5ef" stroke="#b9c3cf" stroke-width="1.2" stroke-linejoin="round"/>
    ${towns}
    <line x1="${ax}" y1="${ay}" x2="${bx}" y2="${by}" stroke="#166534" stroke-width="2.5" stroke-dasharray="7,5" stroke-linecap="round"/>
    <circle cx="${ax}" cy="${ay}" r="6" fill="#fff" stroke="#166534" stroke-width="2.5"/>
    <circle cx="${bx}" cy="${by}" r="6.5" fill="#166534" stroke="#fff" stroke-width="1.5"/>
    ${label(ax, ay, by, fromName, 'font-size="12" font-weight="600" fill="#0d1117" font-family="Inter,Arial,sans-serif"')}
    ${label(bx, by, ay, toName, 'font-size="12" font-weight="700" fill="#0d1117" font-family="Inter,Arial,sans-serif"')}
    <rect x="${mx - tagW / 2}" y="${my - 11}" width="${tagW}" height="22" rx="11" fill="#166534"/>
    <text x="${mx}" y="${my + 4}" text-anchor="middle" font-size="11" font-weight="600" fill="#fff" font-family="Inter,Arial,sans-serif">${_prEsc(tag)}</text>
  </svg>`;
}

function _prHours(miles) {
  const h = Math.round(miles / 60 * 2) / 2;
  return `about ${h} hour${h === 1 ? '' : 's'}`;
}

async function _prDriveSection(d) {
  const origin = g('tripOrigin')?.value?.trim() || '';
  const mpg = parseFloat(g('tripMPG')?.value) || 28;
  const car = [g('tripVehicleYear')?.value, g('tripVehicle')?.value].filter(Boolean).join(' ');
  if (!origin) {
    return `<div class="pr-section"><div class="pr-h">The drive</div><div class="pr-callout">Add your home city on the Trip Planner to see the map and the distance. The fuel line below uses a 400-mile placeholder each way until then.</div></div>`;
  }
  let pts = null;
  try { pts = await API.get(`/api/trip/route-points?origin=${encodeURIComponent(origin)}&destination=${encodeURIComponent(d.dest)}`); } catch (e) { _gwErr('print route')(e); }
  if (!pts || !pts.found) {
    return `<div class="pr-section"><div class="pr-h">The drive</div><div class="pr-callout">Groundwork could not find ${_prEsc(origin)} and ${_prEsc(d.dest)} on a map just now, so there is no map or distance here. The fuel line below uses a 400-mile placeholder each way.</div></div>`;
  }
  const round = pts.miles * 2, gallons = round / mpg;
  return `<div class="pr-section"><div class="pr-h">The drive</div>
    ${prRouteMapSVG(pts, origin, d.dest, pts.miles)}
    <div class="pr-stats" style="margin-top:10px;margin-bottom:6px">
      ${_prStat('Each way', `~${pts.miles.toLocaleString('en-US')} mi`, _prHours(pts.miles) + ' at 60 mph, before stops')}
      ${_prStat('Round trip', `~${round.toLocaleString('en-US')} mi`, car || `at ${mpg} mpg`)}
      ${_prStat('Fuel', fmt(d.transport), `${Math.round(gallons)} gal at $${Number(d.gasRate).toFixed(2)}${d.gasPriceLive ? ', U.S. average' : ', estimated'}`)}
    </div>
    <div class="pr-note">The map shows the two ends, not the roads to take. The road distance is estimated: the straight-line distance plus ${Math.round(((pts.road_factor || 1.25) - 1) * 100)}%. Use your own navigation for directions.</div></div>`;
}

function _prTicket(kind, fromCode, fromCity, toCode, toCity, iso, priceLabel, price, travelers) {
  return `<div class="it-ticket"><div class="it-t-main"><div class="it-t-kind">✈ ${_prEsc(kind)}</div>
      <div class="it-t-route"><div><div class="it-t-code">${_prEsc(fromCode || '—')}</div><div class="it-t-city">${_prEsc(fromCity)}</div></div><div class="it-t-arrow"></div>
      <div style="text-align:right"><div class="it-t-code">${_prEsc(toCode || '—')}</div><div class="it-t-city">${_prEsc(toCity)}</div></div></div></div>
    <div class="it-t-side"><div class="it-t-lab">Flight date</div><div class="it-t-val">${_prEsc(iso ? _prLong(iso) : 'Not set')}</div>
      <div class="it-t-lab">Price of flight</div><div class="it-t-price">${_prEsc(price)}</div><div class="it-t-city">${_prEsc(priceLabel)}${travelers > 1 ? `, ${travelers} travelers` : ''}</div></div></div>`;
}

// What the flight line is, in the words of where the figure came from. Never presented as more certain than it is.
function _prFlightPrice(d) {
  const roundTrip = g('tripRoundTrip')?.checked !== false;
  const est = typeof airfareEstimate === 'function' ? airfareEstimate(_airfareCurrent(), roundTrip, d.travelers) : null;
  const known = typeof tripBookingCost === 'function' && tripBookingCost(_tripBookings);
  const typed = _tripQuoteData?.flightTotal != null || _tripItineraryTotals()?.flight != null;
  if (!known && !typed && est) {
    const leg = est.fare * est.travelers;
    return { perLeg: true, price: fmt(leg), label: 'DOT average fare, an estimate, not a quote', total: est.total };
  }
  if (!d.transport) return { perLeg: false, price: 'Not known', label: 'enter your fare on the Trip Planner', total: 0 };
  const source = known ? (known.trip_cost.label === 'charged' ? `charged by ${known.airline}` : `booked with ${known.airline}`) : (_tripQuoteData?.label ? `from ${_tripQuoteData.label}` : 'from your itinerary');
  return { perLeg: false, price: fmt(d.transport), label: `${roundTrip ? 'round trip, ' : ''}${source}`, total: d.transport };
}

function _prFlySection(d) {
  const from = g('tripFromCity')?.value?.trim() || '', to = g('tripToCity')?.value?.trim() || d.dest;
  const a = (g('tripAirport')?.value || '').trim().toUpperCase(), b = (g('tripDestAirport')?.value || '').trim().toUpperCase();
  const roundTrip = g('tripRoundTrip')?.checked !== false;
  const pr = _prFlightPrice(d);
  const back = pr.perLeg ? [pr.label, pr.price] : ['part of the round-trip price above', 'Included'];
  return `<div class="pr-section"><div class="pr-h">Your flights</div>
    ${_prTicket(roundTrip ? 'Going' : 'One way', a, from, b, to, d.depart, pr.label, pr.price, d.travelers)}
    ${roundTrip ? _prTicket('Coming home', b, to, a, from, d.ret, back[0], back[1], d.travelers) : ''}
    <div class="pr-note">Times and flight numbers are not shown because Groundwork does not hold them. Your airline's confirmation is the one to travel by.</div></div>`;
}

function _prDays(d) {
  const going = _tripMode === 'fly' ? `Fly to ${d.dest}` : `Drive to ${d.dest}`;
  const back = _tripMode === 'fly' ? 'Fly home' : 'Drive home';
  const nights = `${d.nights} night${d.nights === 1 ? '' : 's'} in ${d.dest}`;
  return `<div class="pr-section"><div class="pr-h">Your trip, start to finish</div>
    <div class="it-day"><b>${_prEsc(_prLong(d.depart))}</b><div>${_prEsc(going)}</div></div>
    <div class="it-day"><b>During your stay</b><div>${_prEsc(nights)}</div></div>
    <div class="it-day"><b>${_prEsc(_prLong(d.ret))}</b><div>${_prEsc(back)}</div></div></div>`;
}

function _prCostTable(d) {
  const line = (name, amt, src) => `<tr><td>${_prEsc(name)}</td><td style="color:var(--slate)">${_prEsc(src || '')}</td><td class="num">${amt ? fmt(amt) : '—'}</td></tr>`;
  return `<div class="pr-section"><div class="pr-h">What it should cost</div>
    <table class="pr-t"><thead><tr><th>Item</th><th>Where the figure comes from</th><th class="num">Amount</th></tr></thead><tbody>
      ${line(_tripMode === 'fly' ? 'Flights' : 'Fuel', d.transport, d.transportNote)}
      ${line('Lodging', d.hotel, d.hotelSource)}
      ${line('Meals', d.dining, d.diningSource)}
      ${line('Activities', d.activities, d.activitiesSource)}
      ${d.other ? line('Other', d.other, d.otherSource) : ''}
      ${line('Buffer', d.buffer, '10% for what comes up')}
    </tbody><tfoot><tr><td colspan="2">Estimated total</td><td class="num">${fmt(d.total)}</td></tr></tfoot></table></div>`;
}

function _prSavedTrips() {
  const list = (typeof _trips !== 'undefined' && _trips) || [];
  if (!list.length) return '';
  return `<div class="pr-section pr-long"><div class="pr-h">Your saved trips</div>
    ${list.map(t => `<div style="break-inside:avoid;margin-bottom:12px"><div style="display:flex;justify-content:space-between;gap:10px"><b>${_prEsc(t.label)}</b><span class="pr-value">${fmt(t.total)}</span></div>
      <div class="pr-note" style="margin:0 0 4px">${_prEsc(_tripDates(t))} · ${_prEsc(t.status === 'going' ? "you're going" : t.status === 'done' ? 'done' : 'planning')}</div>
      ${(t.lines || []).length ? `<table class="pr-t"><tbody>${t.lines.map(l => `<tr><td>${_prEsc(l.label)}</td><td class="num">${fmt(l.amount)}</td></tr>`).join('')}</tbody></table>` : ''}</div>`).join('')}</div>`;
}

async function _prTrip() {
  if (typeof tripUpdateBudget === 'function') tripUpdateBudget();
  const d = (g('tripDestination')?.value?.trim() || g('tripToCity')?.value?.trim()) ? _tripBudgetData : null;
  const saved = _prSavedTrips();
  // Each tab prints what it shows: Your trips the saved trips, Plan a trip the trip being planned
  if (_prActiveTabName(g('view-trip')).startsWith('Your trips')) return saved ? _prSheet('Your Trips', '', saved) : null;
  if (!d || !d.dest) {
    if (!saved) return null;
    return _prSheet('Your Trips', '', saved);
  }
  const travel = _tripMode === 'fly' ? _prFlySection(d) : await _prDriveSection(d);
  const hero = `<div class="it-hero"><div class="it-where">${_prEsc(d.dest)}</div>
    <div class="it-when">${_prEsc(_prLong(d.depart))} to ${_prEsc(_prLong(d.ret))}</div>
    <div class="pr-sub">${d.nights} night${d.nights === 1 ? '' : 's'} · ${d.travelers} traveler${d.travelers === 1 ? '' : 's'} · estimated ${fmt(d.total)}</div></div>`;
  return _prSheet('Trip Itinerary', '', hero + _prDays(d) + travel + _prCostTable(d));
}

// ── Before You Buy: the purchase, and a possible future budget ─────────────────────────────────────────────────────
function _prBybInputs() {
  const name = g('bybItemName')?.value?.trim() || _byb.name || '';
  const monthly = parseFloat(g('bybMonthlyAmount')?.value) || _byb.monthly || 0;
  if (!name || !(monthly > 0)) return null;
  const replacing = _byb.replaceCardId ? _activeDebtCards().find(c => c.id === _byb.replaceCardId) : null;
  const useSandbox = _byb.sandboxIncomes.length || _byb.sandboxExpenses.length;
  const income = useSandbox ? _byb.sandboxIncomes.reduce((s, i) => s + i._sandboxAmt, 0) : (S.incomes || []).reduce((s, i) => s + i.amount, 0);
  const budget = useSandbox ? _byb.sandboxExpenses.reduce((s, e) => s + e._sandboxAmt, 0) : (S.expenses || []).reduce((s, e) => s + _rowMonth(e), 0);
  const fin = _bybFinancing();
  const fixed = _byb.type === 'vehicle' || _byb.type === 'purchase';
  return { name, monthly, income, budget, fin, kind: fixed ? 'fixed' : 'rises', replacing,
    debtMins: _activeDebtCards().reduce((s, c) => s + (parseFloat(c.minimum) || 0), 0),
    setAsides: (_sinkingFunds || []).reduce((s, f) => s + (parseFloat(f.monthlyContrib) || 0), 0),
    typeWord: { vehicle: _byb.subtype === 'loan' ? 'Vehicle loan' : 'Vehicle lease', subscription: 'Subscription', purchase: 'Credit purchase', other: 'Monthly cost' }[_byb.type] || 'Purchase' };
}

// Each year's month as stacked bars against today's income. Pure, so a test can read it.
function prFutureChartSVG(rows) {
  const W = 680, H = 210, L = 12, R = 12, T = 22, B = 34;
  const top = Math.max(...rows.map(r => Math.max(r.income, r.budget + r.debt_minimums + r.set_asides + r.purchase)), 1);
  const y = v => T + (H - T - B) * (1 - v / top);
  const band = (W - L - R) / rows.length, bw = Math.min(70, band * 0.56);
  const bars = rows.map((r, i) => {
    const x = L + band * i + (band - bw) / 2;
    let at = 0;
    const seg = (v, color) => { if (!(v > 0)) return ''; const out = `<rect x="${x}" y="${y(at + v)}" width="${bw}" height="${Math.max(0, y(at) - y(at + v))}" fill="${color}"/>`; at += v; return out; };
    const parts = seg(r.budget, '#94a3b8') + seg(r.debt_minimums, '#64748b') + seg(r.set_asides, '#cbd5e1') + seg(r.purchase, '#d97706');
    const label = r.year === 0 ? 'Today' : `In ${r.year} year${r.year === 1 ? '' : 's'}`;
    return `${parts}<text x="${x + bw / 2}" y="${H - 16}" text-anchor="middle" font-size="11" fill="#0d1117" font-family="Inter,Arial,sans-serif">${label}</text>`;
  }).join('');
  const inc = y(rows[0].income);
  return `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;display:block" role="img" aria-label="A possible monthly budget today and in later years, against today's income">
    ${bars}<line x1="${L}" y1="${H - B}" x2="${W - R}" y2="${H - B}" stroke="#526073"/>
    <line x1="${L}" y1="${inc}" x2="${W - R}" y2="${inc}" stroke="#166534" stroke-width="2" stroke-dasharray="6,4"/>
    <text x="${W - R}" y="${inc - 5}" text-anchor="end" font-size="11" font-weight="600" fill="#166534" font-family="Inter,Arial,sans-serif">Income today</text>
  </svg>
  <div class="pr-note" style="display:flex;gap:14px;flex-wrap:wrap;margin-top:2px">
    <span><span style="color:#94a3b8">■</span> Everyday budget</span><span><span style="color:#64748b">■</span> Debt minimums</span>${rows[0].set_asides > 0 ? '<span><span style="color:#cbd5e1">■</span> Set-asides</span>' : ''}<span><span style="color:#d97706">■</span> This purchase</span></div>`;
}

async function _prByb() {
  // The goals are only read when the Budget page opens; the set-asides here must not read $0 because it has not been.
  if (!(_sinkingFunds || []).length && typeof loadSinkingFunds === 'function') { try { await loadSinkingFunds(); } catch (e) { _gwErr('print goals')(e); } }
  const inp = _prBybInputs();
  if (!inp) return null;
  let pj = null;
  try {
    pj = await API.post('/api/byb/projection', { income: inp.income, budget: inp.budget, debt_minimums: inp.debtMins, set_asides: inp.setAsides, monthly: inp.monthly,
      kind: inp.kind, term_months: inp.fin.term || null, replaces_monthly: inp.replacing ? (parseFloat(inp.replacing.minimum) || 0) : 0 });
  } catch (e) { _gwErr('print projection')(e); }
  if (!pj || !pj.rows) return null;
  const f = inp.fin;
  const hasLoan = f.needed && f.term && f.amount > 0;
  const totalPaid = hasLoan ? inp.monthly * f.term : null;
  const signed = v => `${v < 0 ? '-' : ''}${fmt(Math.abs(v))}`;
  const costRows = [
    ['Monthly cost', `${fmt(inp.monthly)} a month`],
    inp.replacing ? ['It replaces', `${inp.replacing.name}, ${fmt(parseFloat(inp.replacing.minimum) || 0)} a month`] : null,
    ['First 12 months', fmt(pj.first_year_cost)],
    ['Over the next 5 years', `${fmt(pj.five_year_cost)}${pj.kind === 'rises' ? ', rising with the assumed inflation' : ''}${pj.term_months && pj.term_months < 60 ? `, ending after month ${pj.term_months}` : ''}`],
    hasLoan ? ['Amount financed', `${fmt(f.amount)} at ${f.apr}% APR for ${f.term} months`] : null,
    hasLoan ? ['Total of all payments', fmt(totalPaid)] : null,
    hasLoan ? ['Added cost of borrowing', fmt(Math.max(0, totalPaid - f.amount))] : null,
  ].filter(Boolean);
  const col = fn => pj.rows.map(r => `<td class="num">${fn(r)}</td>`).join('');
  const body = `<div class="it-hero"><div class="it-where">${_prEsc(inp.name)}</div><div class="it-when">${_prEsc(inp.typeWord)}</div></div>
    <div class="pr-section"><div class="pr-h">What it costs</div><table class="pr-t"><tbody>${costRows.map(([a, b]) => `<tr><td>${_prEsc(a)}</td><td class="num">${_prEsc(b)}</td></tr>`).join('')}</tbody></table></div>
    <div class="pr-section"><div class="pr-h">A possible future budget, per month</div>
      ${prFutureChartSVG(pj.rows)}
      <table class="pr-t" style="margin-top:10px"><thead><tr><th></th>${pj.rows.map(r => `<th class="num" style="text-align:right">${r.year === 0 ? 'Today' : `In ${r.year} yr`}</th>`).join('')}</tr></thead><tbody>
        <tr><td>Income (kept at today's)</td>${col(r => fmt(r.income))}</tr>
        <tr><td>Everyday budget, with inflation</td>${col(r => fmt(r.budget))}</tr>
        <tr><td>Debt minimums</td>${col(r => fmt(r.debt_minimums))}</tr>
        ${pj.rows[0].set_asides > 0 ? `<tr><td>Set-asides</td>${col(r => fmt(r.set_asides))}</tr>` : ''}
        <tr><td><b>${_prEsc(inp.name)}</b></td>${col(r => fmt(r.purchase))}</tr>
      </tbody><tfoot><tr><td>Left with it</td>${col(r => `<span class="${r.left_with < 0 ? 'pr-bad' : ''}">${signed(r.left_with)}</span>`)}</tr>
        <tr><td style="font-weight:400">Left without it</td>${col(r => `<span style="font-weight:400">${signed(r.left_without)}</span>`)}</tr></tfoot></table>
      <div class="pr-callout"><b>This is a projection, not actual inflation.</b> It assumes prices rise ${pj.rate_pct}% a year, which is Groundwork's illustration and not a published or predicted rate. Real inflation will differ. It also cannot account for other expenses that are not known today. Income, debt minimums and set-asides are held at today's amounts, and a ${pj.kind === 'rises' ? 'running cost like this one rises with everything else' : 'fixed payment like this one stays the same until its term ends'}.</div>
    </div>`;
  return _prSheet('Before You Buy', 'The cost of this purchase, and a possible future budget', body);
}

// ── Net Worth: the report the Report Center already has ────────────────────────────────────────────────────────────
async function _prNetWorth() {
  if ((!_nwHistory || !_nwHistory.length) && typeof loadNWHistory === 'function') { try { await loadNWHistory(); } catch (e) { _gwErr('print net worth')(e); } }
  if (!_nwHistory || !_nwHistory.length) return null;
  const holder = document.createElement('div');
  holder.innerHTML = _rcNetWorthTimelineHTML(_nwHistory);
  holder.querySelector('h2')?.parentElement?.remove();         // the sheet carries the title
  holder.querySelectorAll('.card').forEach(c => { if (c.querySelector('tbody tr:nth-child(12)')) c.classList.add('pr-long'); });
  return _prSheet('Net Worth', 'All-time, from the first saved month to today', `<div class="pr-page">${holder.innerHTML}</div>`);
}

// ── Printing ───────────────────────────────────────────────────────────────────────────────────────────────────────
function _prSend(html) {
  const sheet = g('gwPrintSheet');
  sheet.innerHTML = html;
  const done = () => { document.body.classList.remove('gw-printing'); sheet.innerHTML = ''; window.removeEventListener('afterprint', done); };
  window.addEventListener('afterprint', done);
  document.body.classList.add('gw-printing');
  window.print();
}

// The report for the page in front, as HTML. Exposed so it can be looked at without a printer.
async function gwPrintHTML(ledgerMode) {
  const name = _prActiveView();
  if (name === 'ledger') return ledgerMode === 'overview' ? _prLedgerOverview() : _prLedgerDetail();
  let html = null;
  if (name === 'trip') html = await _prTrip();
  if (name === 'byb' && _prActiveTabName(g('view-byb')).startsWith('Thinking')) html = await _prByb();
  if (name === 'networth') html = await _prNetWorth();
  return html || _prWholePage(name);
}

async function gwPrintPage(ledgerMode) {
  const name = _prActiveView();
  if (name === 'ledger' && !GW_PRINT_LEDGER_MODES.includes(ledgerMode)) { _prAskLedger(); return; }
  _gwPrintLedgerAsked = false;
  if (typeof closeAsk === 'function') closeAsk();
  try {
    const html = await gwPrintHTML(ledgerMode);
    if (document.fonts && document.fonts.ready) await document.fonts.ready;
    _prSend(html);
  } catch (e) {
    _gwErr('gwPrintPage')(e);
    if (typeof showToast === 'function') showToast('That page could not be made into a report.', '', 'error');
  }
}

// Ctrl+P on any page: the report too, rather than a blank sheet. The other things that print have their own sheets.
function _prBeforePrint() {
  const b = document.body;
  if (b.classList.contains('gw-printing') || b.classList.contains('bk-printing') || b.classList.contains('rb-printing')) return;
  const shown = id => { const el = g(id); return el && getComputedStyle(el).display !== 'none'; };
  if (shown('reportModal') || shown('gwFeedbackModal')) return;
  const name = _prActiveView();
  const html = name === 'ledger' ? _prLedgerDetail() : _prWholePage(name);
  if (!html) return;
  g('gwPrintSheet').innerHTML = html;
  b.classList.add('gw-printing');
  const done = () => { b.classList.remove('gw-printing'); g('gwPrintSheet').innerHTML = ''; window.removeEventListener('afterprint', done); };
  window.addEventListener('afterprint', done);
}
if (typeof window !== 'undefined' && window.addEventListener) window.addEventListener('beforeprint', _prBeforePrint);

// ── The words for it ───────────────────────────────────────────────────────────────────────────────────────────────
const PR_ASK_THIS = /^(?:(?:can|could|would|will) you |i (?:want|need|would like|d like|'d like) to |let'?s |please |go |just )*(?:print(?: out)?|make a (?:printout|printed copy)(?: of)?|save)(?: (?:this|that|it|the|my|me a|a copy of)){0,2}(?: (?:page|screen|view|report|tab|one|copy))?(?: (?:out|off|for me|please|now|as a pdf|to pdf|to a pdf|as pdf))*$/;
const PR_ASK_PLACE = /^(?:(?:can|could|would|will) you |i (?:want|need|would like) to |let'?s |please |go |just )*print(?: out)?(?: (?:my|the|our))? (.+?)(?: (?:page|tab|report|please|for me|out))*$/;

// "said" is the words as heard, "n" the same words with their leads and fillers taken off. True when it was for printing.
function gwPrintIntent(said, n) {
  const words = String(n || said || '');
  if (_gwPrintLedgerAsked) {
    const pick = /\b(?:detail|details|detailed|everything|every line|all (?:of )?the lines)\b/.test(words) ? 'detail'
      : /\b(?:overview|summary|summarized|totals?|short)\b/.test(words) ? 'overview' : null;
    if (pick) { _prAskAnswer(`Sure, printing the ${pick} page.`); gwPrintPage(pick); return true; }
    _gwPrintLedgerAsked = false;
  }
  const mode = /\b(?:detail|detailed|details)\b/.test(words) ? 'detail' : /\b(?:overview|summary)\b/.test(words) ? 'overview' : null;
  if (PR_ASK_THIS.test(words) && !/^save$/.test(words) && (/^(?:.* )?print/.test(words) || /\bpdf\b/.test(words) || /printout|printed/.test(words))) {
    if (_prActiveView() === 'ledger' && !mode) { _prAskLedger(); return true; }
    _prAskAnswer('Sure, getting this page ready to print.');
    gwPrintPage(mode);
    return true;
  }
  const place = words.match(PR_ASK_PLACE);
  if (place && typeof ASK_PLACES !== 'undefined') {
    const key = place[1].replace(/ (?:detail|detailed|details|overview|summary)$/, '').trim();
    const pl = ASK_PLACES.find(x => x.names.includes(key));
    if (!pl || pl.report) return false;              // a named report has its own way to open (ASK_RECORD)
    askGo(pl);
    setTimeout(() => {
      if (pl.view === 'ledger' && !mode) { _prAskLedger(); return; }
      _prAskAnswer(`Sure, getting ${pl.label} ready to print.`);
      gwPrintPage(mode);
    }, 700);                                          // the page draws before it is copied
    return true;
  }
  return false;
}

function _prAskAnswer(words) {
  if (typeof _askDone === 'function') _askDone();
  if (typeof _askSaid === 'function') _askSaid(words);
}

if (typeof module !== 'undefined') module.exports = { prLedgerSummary, prMapFrame, PR_ASK_THIS, PR_ASK_PLACE };
