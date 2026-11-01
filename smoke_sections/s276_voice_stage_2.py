"""Item 116 stage 2 (gw 2.0/VOICE_ASSISTANT.md, approved 2026-10-31):

    V6  control the page by voice - scroll anywhere; on the Ledger its own sort, range, month, category, type and clear
    V5  a change asked for aloud is read back with its figures, and made only by a press: "add a 40 dollar grocery
        purchase at Kroger today" fills in Add transaction (Save makes it); with AI on, a proposal's sentences are read
        and "Press Yes on the card to make the change." (H7 unchanged: a spoken yes never makes a change)
"""
import json
import os
import shutil
import subprocess
import tempfile


def run(ctx):
    check = ctx.check
    app = (ctx.BASE / 'static' / 'js' / 'app.js').read_text(encoding='utf-8')
    intent = app[app.index('function askIntent(q, p, head, assist = false) {'):app.index('// ─── Item 103: Explain this page')]
    check('s276 V5/V6 the Ask bar tries a spoken change and the page\'s own controls before its other commands',
          intent.index('if (_askAddTxn(n)) return true;') < intent.index('for (const d of ASK_DO)')
          and intent.index('if (_askPageControl(n)) return true;') < intent.index('for (const d of ASK_DO)'))
    assist = app[app.index('async function askAssistant('):app.index('function _assistHTML(res) {')] if 'async function askAssistant(' in app else ''
    check('s276 V5 with AI on, a proposal asked for aloud is read back and ends "Press Yes on the card to make the change."',
          "(res.proposal ? ' Press Yes on the card to make the change.' : '')" in app)
    add = app[app.index('function _askAddTxn(n) {'):app.index('// Rob 2026-10-31: "show me my Kroger transactions"')]
    check('s276 V5 the spoken change only fills the form - nothing in it saves, posts or presses Save',
          'API.' not in add and 'saveTxn' not in add and '.click()' not in add and 'Press Save to add it.' in add)

    node = shutil.which('node')
    if not node:
        return
    js = (app[app.index('function _localISODate('):app.index('// A moment, in local time with no zone')]
          + app[app.index('const _ASK_SHORT = '):app.index('function _askSay(')]
          + "const _askTitle = s => String(s).replace(/\\b[a-z]/g, c => c.toUpperCase());\n"
          + app[app.index('const _ASK_NUM = '):app.index('// Rob 2026-10-31: "show me my Kroger transactions"')]
          + r"""
const els = {}, log = [];
const el = id => els[id] || (els[id] = { id, value: '', options: [], classList: { add() {}, remove() {}, contains: () => false } });
globalThis.g = el;
el('ledgerCatFilter').options = ['', 'Groceries', 'Restaurants', 'Gas & Fuel'].map(v => ({ value: v }));
let view = 'view-ledger';
const pane = { scrollTop: 0, clientHeight: 500, scrollHeight: 4000, scrollBy(o) { this.scrollTop += o.top; }, scrollTo(o) { this.scrollTop = o.top; } };
globalThis.document = { querySelector: s => s === '.view.active' ? { id: view, closest: () => pane } : s === '.content' ? pane : null };
let _ledgerSortCol = 'date', _ledgerSortDir = -1, _ledgerMonthKey = null;
const renderLedger = () => log.push('render'), updateLedgerStats = () => {}, setLedgerRange = k => log.push('range:' + k);
const ledgerMonthStep = d => log.push('month:' + d), _ledgerAvailableMonths = () => ['2026-11', '2026-10'];
const showView = v => log.push('view:' + v), openAddModal = () => log.push('add-form'), _categoryNames = () => ['Groceries', 'Restaurants', 'Gas & Fuel'];
const today = () => _localISODate(), fmt = n => '$' + Number(n).toFixed(2);
const toasts = []; let spoken = [];
const _askDone = t => toasts.push(t), _askSaid = w => spoken.push(w);
const run = q => { log.length = 0; spoken = []; const n = _askNorm(q); const hit = _askAddTxn(n) || _askPageControl(n); return [hit, log.slice(), spoken[0] || null]; };
const out = {};
out.sort = [run('sort by amount'), _ledgerSortCol, _ledgerSortDir];
out.sortLow = [run('sort by amount lowest first'), _ledgerSortDir];
out.range = run('show the last six months');
out.thisMonth = run('this month');
out.prev = run('previous month');
out.cat = [run('just groceries'), el('ledgerCatFilter').value];
out.income = [run('only income'), el('ledgerTypeFilter').value];
out.clear = [run('clear the filters'), el('ledgerCatFilter').value, el('ledgerTypeFilter').value];
out.down = [run('scroll down'), pane.scrollTop];
out.bottom = [run('go to the bottom'), pane.scrollTop];
out.notPage = run('just a minute');
out.add = [run('add a 40 dollar grocery purchase at kroger today'), el('txnAmount').value, el('txnCategory').value, el('txnDesc').value, el('txnType').value];
out.addCents = [run('log a $12.50 restaurants expense at pine street pizza yesterday'), el('txnAmount').value, el('txnCategory').value, el('txnDate').value === _localISODate(new Date(Date.now() - 864e5))];
out.addWords = [run('add a twenty five dollar gas purchase'), el('txnAmount').value, el('txnCategory').value];
out.refund = [run('record a 15 dollar refund from target'), el('txnType').value];
out.noAmount = run('add a grocery purchase');
view = 'view-budget';
out.offLedger = run('just groceries');
console.log(JSON.stringify(out));
""")
    f = os.path.join(tempfile.mkdtemp(prefix='s276_'), 'stage2.js')
    open(f, 'w', encoding='utf-8').write(js)
    r = subprocess.run([node, f], capture_output=True, text=True, encoding='utf-8', timeout=30)
    try:
        o = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        o = {'error': (r.stdout + r.stderr)[-500:]}
    check(f"s276 V6 the Ledger's own controls by voice: sort, range, this month, the month before, a category, income, "
          f"clear - each said back ({o.get('error') or ''})",
          o.get('sort') == [[True, ['render'], 'OK, sorted by amount.'], 'amount', -1]
          and o.get('sortLow', [None, 0])[1] == 1
          and o.get('range') == [True, ['range:6'], 'OK, showing the last 6 months.']
          and o.get('thisMonth', [None, []])[1][:2] == ['range:1', 'render']
          and o.get('prev') == [True, ['month:1'], 'OK, the month before.']
          and o.get('cat') == [[True, ['render'], 'OK, showing only Groceries.'], 'Groceries']
          and o.get('income', [None, ''])[1] == 'credit'
          and o.get('clear', [None, 'x', 'x'])[1:] == ['', ''])
    check(f"s276 V6 scrolling works on any page; words that are not a control are left for the rest of the Ask bar "
          f"({o.get('down')}, {o.get('bottom')}, {o.get('notPage')}, {o.get('offLedger')})",
          o.get('down', [None, 0])[1] == 400 and o.get('bottom', [None, 0])[1] == 4000
          and o.get('notPage') == [False, [], None] and o.get('offLedger') == [False, [], None])
    check(f"s276 V5 a spoken purchase fills Add transaction - amount, category, payee, date, kind - and is read back for "
          f"Save; without an amount nothing is filled ({o.get('add')}, {o.get('addCents')}, {o.get('addWords')}, "
          f"{o.get('refund')}, {o.get('noAmount')})",
          o.get('add') == [[True, ['view:ledger', 'add-form'], 'Add $40.00, Groceries, Kroger, today? Press Save to add it.'],
                           '40.00', 'Groceries', 'Kroger', 'debit']
          and o.get('addCents', [None])[1:] == ['12.50', 'Restaurants', True]
          and o.get('addWords', [None])[1:] == ['25.00', 'Gas & Fuel']
          and o.get('refund', [None, ''])[1] == 'credit' and o.get('noAmount') == [False, [], None])
