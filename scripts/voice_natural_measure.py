"""V24 (item 116, VOICE_ASSISTANT.md 4h): does the Ask bar understand how people talk?

    python scripts/voice_natural_measure.py [--misses]

Every phrase in scripts/voice_natural_asks.json goes through the Ask bar's own code from app.js, run in Node with the
page's objects stubbed, as a spoken ask with AI off. Prints how many did what was meant, per set. --misses prints the
build set's misses (and the not-commands wrongly taken); the held-out set's misses are never printed by this script.
Nothing here is a real person's speech: it measures the router, not the microphone.
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASKS = ROOT / 'scripts' / 'voice_natural_asks.json'

HOUSE = r"""
var S = { transactions: ['Kroger', 'Walmart', 'Meijer', 'Costco', 'Shell', 'Netflix', 'Chief Supermarket 2 Millbrook', 'Target']
            .map(m => ({ merchant: m, description: m.toUpperCase(), category: 'Other', amount: 10, type: 'debit', date: '2026-10-05' })),
          categories: [{ name: 'Groceries' }, { name: 'Dining' }, { name: 'Gas' }, { name: 'Utilities' }],
          expenses: [{ name: 'Groceries', cat: 'Groceries' }, { name: 'Gas', cat: 'Gas' }], debtCards: [] };
"""

STUBS = r"""
var log = [];
var els = {};
var window = globalThis;
var _categoriesCache = [];
function g(id) { return els[id] || (els[id] = { id, value: '', style: {}, focus() {}, options: [], scrollIntoView() {} }); }
var document = { querySelector: s => null, querySelectorAll: () => [], addEventListener() {}, body: { closest: () => null } };
var showView = v => log.push(['view', v]);
var showToast = (t) => log.push(['toast', String(t)]);
var closeAsk = () => {}, renderLedger = () => {}, updateLedgerStats = () => {}, _ledgerMonthKey = null;
var _budShowTab = () => {}, healthShowTab = () => {}, bybShowTab = () => {}, _debtShowTab = () => {}, _settingsShowTab = () => {};
var _rcOpenReport = () => {}, _rcUpdateCategoryDeepDive = () => {}, showImportModal = () => {}, openAddModal = () => {};
var openBackupModal = () => {}, addCard = () => {}, openFeedbackModal = () => {}, showHelpOverlay = () => {}, openWhy = () => {};
var explainPage = () => log.push(['explain']);
var startFetchAll = () => log.push(['fetch']);
var showFigTxns = () => {}, ledgerMonthStep = () => {}, setLedgerRange = () => {}, _ledgerAvailableMonths = () => [];
var _ledgerSortCol, _ledgerSortDir;
var fmt = n => '$' + Number(n).toFixed(2), today = () => '2026-11-05', _localISODate = d => '2026-11-04';
var _categoryNames = () => S.categories.map(c => c.name);
var esc = s => String(s), _gwErr = () => () => {};
var API = { get: async (u) => { log.push(['api', u]); return { entries: [], chains: [] }; } };
window._gwChains = [];
window.setTimeout = globalThis.setTimeout = (f) => { try { f(); } catch (e) { /* a stub page */ } return 0; };
var clearTimeout = () => {};
"""

JUDGE = r"""
function label(panel) {
  const box = els.ledgerSearch && els.ledgerSearch.value;
  if (box) return 'ledger:' + box;
  if (log.some(x => x[0] === 'fetch')) return 'fetch';
  if (log.some(x => x[0] === 'explain')) return 'explain';
  if (log.some(x => x[0] === 'api' && /calendar/.test(x[1]))) return 'coming';
  const toast = log.filter(x => x[0] === 'toast').map(x => x[1])[0];
  if (toast && /^Opened /.test(toast)) return 'open:' + toast.slice(7);
  if (window._askPlace) return 'open:' + window._askPlace.label;
  const said = (panel.innerHTML || '') + ' ' + (spoken.join(' '));
  if (/welcome/i.test(said)) return 'say:welcome';
  if (/\bOK, never mind|Never mind\b/i.test(said) || (toast && /never mind/i.test(toast))) return 'say:never mind';
  if (/\bHi!/.test(said)) return 'say:hello';
  if (/You can say|Ask how to do/.test(said)) return 'say:help';
  return toast ? 'toast:' + toast : null;
}
const spoken = [];
window.GWVoice = { say: w => spoken.push(w), first: () => false };
function run(q) {
  log.length = 0; spoken.length = 0; window._askPlace = null; _askLast = null;
  Object.keys(els).forEach(k => delete els[k]);
  els.gwFetchAllBtn = { style: { display: '' } };
  const panel = { innerHTML: '' };
  const parts = _askParts(q);
  const list = parts || [q];
  let hit = false;
  for (const one of list) {
    window._gwVoiceAsked = true;
    hit = askIntent(one, panel, '', false) || hit;
  }
  return hit ? label(panel) : null;
}
const asks = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));
const out = {};
for (const set of ['build', 'held_out']) out[set] = asks[set].map(([q, want]) => [q, want, run(q)]);
out.not_commands = asks.not_commands.map(q => [q, null, run(q)]);
console.log(JSON.stringify(out));
"""


def page_code(root=ROOT):
    app = (Path(root) / 'static' / 'js' / 'app.js').read_text(encoding='utf-8')
    return (app[app.index('const ASK_PLACES = ['):app.index('// ─── Item 103: Explain this page')]
            + app[app.index('const _ASK_JOIN = '):app.index('async function askGroundwork(')]
            + app[app.index('function _ledgerTermMatch('):app.index('function _ledgerFilteredTxns(')])


def measure(root=ROOT):
    """{set: [[asked, wanted, got], ...]}"""
    d = Path(tempfile.mkdtemp(prefix='gw_natural_'))
    (d / 'run.js').write_text(STUBS + HOUSE + page_code(root) + JUDGE, encoding='utf-8')
    r = subprocess.run([shutil.which('node'), str(d / 'run.js'), str(Path(root) / 'scripts' / 'voice_natural_asks.json')],
                       capture_output=True, text=True, encoding='utf-8', timeout=120)
    if r.returncode:
        raise RuntimeError(r.stderr[-2000:])
    return json.loads(r.stdout)


def main():
    res = measure()
    for name in ('build', 'held_out'):
        rows = res[name]
        print(f'{name}: {sum(g == w for _q, w, g in rows)}/{len(rows)} did what was meant')
    wrong = [r for r in res['not_commands'] if r[2] is not None]
    print(f'not_commands: {len(res["not_commands"]) - len(wrong)}/{len(res["not_commands"])} left for the assistant')
    if '--misses' in sys.argv:
        print('\nbuild misses:')
        for q, w, g in res['build']:
            if g != w:
                print(f'  {q!r}: wanted {w}, got {g}')
        print('\nnot-commands taken as commands:')
        for q, _w, g in wrong:
            print(f'  {q!r}: {g}')


if __name__ == '__main__':
    main()
