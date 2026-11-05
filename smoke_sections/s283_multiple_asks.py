"""Item 116: one ask, several commands (Rob 2026-11-01: "Groundwork to open the ledger, and then show me all of Chiefs
Supermarket transactions" - "It should be able to understand a multiple ask"). Run on app.js's own routing code in Node:

    M1  Rob's sentence is two commands - the Ledger, then the Ledger searched for Chiefs Supermarket - in that order
    M2  it splits only where every part is a command; "my Kroger and Walmart transactions" stays one ask, and so does a
        single command with "Groundwork," in front (the stores are then one search for several stores, M4)
    M3  the parts are done in turn, and a spoken ask hears one reply naming them all
    M4  several stores in one search ("my Kroger and Walmart transactions") - each searched, when each is in the record
        and the whole phrase is not (so "Barnes and Noble" stays one name); the Ledger search takes "kroger or walmart"
    M5  "meyer is meijer" (Rob): a store name that matches nothing is the record's store it sounds like, and the toast
        says what was heard
    M6  in a list, a name that is no store in the record is named as not found and the rest are shown ("admire and
        walmart", whisper's hearing of "my Meijer and Walmart")
    M7  "when I say admire, I mean Meijer": kept, shown in Settings, removable, applied to spoken words only
    M10 "go" in front of anything is a lead-in ("go get my accounts", "go budget"); "go back" stays its own words
    M8  learned from the person (Rob 2026-11-01): the third time, within a minute each, that a spoken word found nothing
        and one store was looked for next - counted in memory only, said when learned, with an Undo
"""
import json
import os
import shutil
import subprocess
import tempfile


def run(ctx):
    check = ctx.check
    node = shutil.which('node')
    if not node:
        check('s283 node is available for the page test', False)
        return
    app = (ctx.BASE / 'static' / 'js' / 'app.js').read_text(encoding='utf-8')
    js = (app[app.index('const _ASK_SHORT = '):app.index('function _askSay(')]
          + app[app.index('const ASK_PLACES = ['):app.index('function askGo(')]
          + app[app.index('const ASK_DO = ['):app.index('// Questions about the person')]
          + app[app.index('function _askShowTxns(n) {'):app.index('// Rob 2026-10-31: with Groundwork')]
          + app[app.index('const ASK_COMING = '):app.index('async function askComingUp(')]
          + app[app.index('const _ASK_JOIN = '):app.index('async function askGroundwork(')]
          + app[app.index('function _ledgerTermMatch('):app.index('function _ledgerFilteredTxns(')]
          + app[app.index('function _askStores('):app.index('function askLedgerSearch(')].replace(
              'const ASK_LEARN_AFTER', 'var ASK_LEARN_AFTER').replace('let _askUnheard', 'var _askUnheard')
          + r"""
const what = (q) => {
  const n = _askNorm(q);
  const s = _askShowTxns(n);
  if (s) return 'ledger:' + s;
  const d = ASK_DO.find(x => x.re.test(n));
  if (d) return 'do:' + d.said;
  const bare = n.replace(/^(?:my|the|our|all)\s+/, '');
  const p = askPlace(n) || ASK_PLACES.find(pl => pl.names.includes(bare));
  return p ? 'place:' + p.label : null;
};
const asks = {
  rob: 'Groundwork to open the ledger, and then show me all of Chiefs Supermarket transactions.',
  then: 'Open the budget then open the calendar',
  three: 'Open my budget, show me my Kroger transactions, and then open settings',
  kroger_walmart: 'Show me my Kroger and Walmart transactions',
  single: 'Groundwork, open my budget',
  question: 'How much did we spend on groceries and gas last month?',
};
const out = {};
for (const [k, q] of Object.entries(asks)) { const p = _askParts(q); out[k] = p ? p.map(what) : null; }
out.robWhole = what('Groundwork to open the ledger');
// two stores in one ask (Rob 2026-11-01: "it fails on asking for two stores")
globalThis.S = { transactions: [{ merchant: 'Kroger', description: 'KROGER #123' }, { merchant: 'Walmart', description: 'WAL-MART' },
  { merchant: 'Aldi', description: 'ALDI 55' }, { merchant: 'Barnes & Noble', description: 'BARNES NOBLE' },
  { merchant: 'Chiefs Supermarket', description: 'CHIEFS' }, { merchant: 'Meijer', description: 'MEIJER # 210' }] };
const term = (q) => _askShowTxns(_askNorm(q));
out.stores = {
  two: _askStores(term('Show me my Kroger and Walmart transactions')),
  three: _askStores(term('Show me Kroger, Walmart and Aldi purchases')),
  orr: _askStores(term('show me my kroger or chiefs supermarket transactions')),
  barnes: _askStores(term('show me my barnes and noble transactions')),
  unknown: _askStores(term('show me my kroger and target transactions')),
  meyer2: _askStores(term('show me my meyer and kroger transactions')),
};
// Rob 2026-11-01: whisper wrote "my Meijer and Walmart" as "admire and walmart" - Walmart is shown, "admire" named
const adm = _askStores(term('Show me admire and Walmart transactions'));
out.admire = adm ? { stores: adm.slice(), missing: adm.missing } : null;
out.unknownMissing = out.stores.unknown ? _askStores(term('show me my kroger and target transactions')).missing : null;
// "meyer is meijer" (Rob 2026-11-01): what whisper writes, taken as the store in the record it sounds like
out.like = { meyer: _askSoundsLike('meyer'), kruger: _askSoundsLike('kruger'), target: _askSoundsLike('target'),
  me: _askSoundsLike('me'), walmart: _askSoundsLike('wallmart') };
// M8: learned from the person - a spoken word that found nothing, then one store looked for next, three times
let nowL = 1000; Date.now = () => nowL;
const learned = [];
globalThis.window = globalThis; window.GWVoice = { learn: (h, m, n) => learned.push([h, m, n]) };
const pair = (store, gap = 5000) => { _askUnheard = { words: ['admire'], found: ['walmart'], at: nowL }; nowL += gap; _askNoteFound([store]); };
pair('meijer'); pair('meijer'); const afterTwo = learned.length; pair('meijer');
pair('aldi'); pair('meijer', 61000);                     // another store, and one past the minute: neither counts toward it
_askUnheard = { words: ['target'], found: [], at: nowL }; _askNoteFound(['walmart', 'aldi']);   // two stores: no one to learn
out.learn = { afterTwo, learned };
out.match = ['kroger or walmart'].map(s => S.transactions.filter(t => s.split(/\s+or\s+/).some(x => _ledgerTermMatch(t, x))).length)[0];
console.log(JSON.stringify(out));
""")
    # M7: "when I say admire, I mean Meijer" - what it hears, the person's way (access.js)
    acc = (ctx.BASE / 'static' / 'js' / 'teaching' / 'access.js').read_text(encoding='utf-8')
    js += (r"""
globalThis.window = globalThis;
const saved = {}, toastsM = [];
var prefs = { heard_as: '' };
async function _save(k, v) { prefs[k] = v; saved[k] = v; }
function showToast(t, s, k, undo) { toastsM.push([t, s, !!undo]); }
function say() {}
""" + acc[acc.index('  // Rob 2026-11-01: whisper heard'):acc.index('  // V17 (item 116)')] + r"""
const teach = acc_route_re.exec('Groundwork, when I say admire, I mean Meijer.');
(async () => {
  await _meanThis(teach[1], teach[2]);
  console.log(JSON.stringify({ m7: { kept: JSON.parse(saved.heard_as || '{}'),
    heard: _heardAs('Show me admire and Walmart transactions'),
    word: _heardAs('I admired the budget'), toast: toastsM[0] } }));
})();
""").replace('acc_route_re', acc[acc.index('var mean = text.match(') + len('var mean = text.match('):
                                          acc.index('if (mean) { _meanThis(')].rstrip().rstrip(';').rstrip(')'))
    f = os.path.join(tempfile.mkdtemp(prefix='s283_'), 'parts.js')
    open(f, 'w', encoding='utf-8').write(js)
    r = subprocess.run([node, f], capture_output=True, text=True, encoding='utf-8', timeout=60)
    try:
        lines = r.stdout.strip().splitlines()
        o = json.loads(lines[-2])
        o.update(json.loads(lines[-1]))
    except Exception:
        o = {'error': (r.stdout + r.stderr)[-600:]}
    check(f"s283 M1 Rob's ask is two commands, in order: the Ledger, then the Ledger searched for Chiefs Supermarket "
          f"({o.get('rob')}; {o.get('error')})",
          o.get('rob') == ['place:the Ledger', 'ledger:chiefs supermarket'])
    check(f"s283 M1 'Groundwork to open the ledger' alone opens the Ledger ({o.get('robWhole')})",
          o.get('robWhole') == 'place:the Ledger')
    check(f"s283 M1 'then' and a list of three are split the same way ({o.get('then')}, {o.get('three')})",
          o.get('then') == ['place:the Budget', 'place:the Calendar']
          and o.get('three') == ['place:the Budget', 'ledger:kroger', 'place:Settings'])
    check(f"s283 M2 it splits only where every part is a command ({o.get('kroger_walmart')}, {o.get('single')}, "
          f"{o.get('question')})",
          o.get('kroger_walmart') is None and o.get('single') is None and o.get('question') is None)
    st = o.get('stores') or {}
    check(f"s283 M4 two or three stores in one ask are each searched; 'or' too; a name with 'and' in it stays one name; "
          f"a store not in the record is named, the rest shown ({st}, {o.get('match')})",
          st.get('two') == ['kroger', 'walmart'] and st.get('three') == ['kroger', 'walmart', 'aldi']
          and st.get('orr') == ['kroger', 'chiefs supermarket'] and st.get('barnes') is None and st.get('unknown') == ['kroger']
          and o.get('unknownMissing') == ['target']
          and o.get('match') == 2)
    check(f"s283 M6 'admire and walmart' (whisper, for 'my Meijer and Walmart'): Walmart is shown and 'admire' is named "
          f"as not found, rather than nothing ({o.get('admire')})",
          o.get('admire') == {'stores': ['walmart'], 'missing': ['admire']}
          and 'nothing in your record is called ' in app)
    ln = o.get('learn') or {}
    check(f"s283 M8 Groundwork learns from the person: the third time a spoken word finds nothing and one store is looked "
          f"for next within a minute, it takes the word as that store - not before, not past the minute ({ln})",
          ln.get('afterTwo') == 0 and ln.get('learned') == [['admire', 'meijer', 3]])
    check('s283 M8 it is said when learned, with an Undo, and listed in Settings; the counting lives in this window only; '
          'a typed search counts too',
          "window.GWVoice.learn(u.words[0], fresh[0], ASK_LEARN_AFTER)" in app and 'const _askLearnSeen = {};' in app
          and 'async function learnHeard(' in acc and "'info', async function () {" in acc[acc.index('async function learnHeard('):]
          and '_askNoteFound(terms);' in app and "localStorage" not in app[app.index('const ASK_LEARN_AFTER'):app.index('function askLedgerSearch(')])
    m7 = o.get('m7') or {}
    check(f"s283 M7 'when I say admire, I mean Meijer' is kept, said back with an Undo, and what is heard is taken that way "
          f"- whole words only ({m7})",
          m7.get('kept') == {'admire': 'Meijer'} and m7.get('heard') == 'Show me Meijer and Walmart transactions'
          and m7.get('word') == 'I admired the budget' and (m7.get('toast') or [None, None, False])[2] is True)
    check("s283 M7 Settings lists each one with Remove; only spoken words are taken that way",
          'data-gw-unhear' in acc and 'id="gwHeardAdd"' in acc and 'text = _heardAs(text);' in acc
          and acc.index('text = _heardAs(text);') < acc.index('window.askGroundwork(text);   // a global'))
    lk = o.get('like') or {}
    check(f"s283 M5 a store whisper wrote as it sounds is the store in the record it sounds like - Meyer is Meijer - and "
          f"a name like nothing there is left as said ({lk}, {st.get('meyer2')})",
          lk.get('meyer') == 'meijer' and lk.get('kruger') == 'kroger' and lk.get('walmart') == 'walmart'
          and lk.get('target') is None and lk.get('me') is None and st.get('meyer2') == ['meijer', 'kroger'])
    check('s283 M4 the Ledger search shows either of "kroger or walmart"',
          r"const terms = search.split(/\s+or\s+/)" in app and "box.value = stores ? stores.join(' or ') : term" in app)
    check('s283 M3 the parts are done in turn, and a spoken ask hears one reply naming them all',
          'for (const part of parts) {' in app and "voice.say(said.join('. Then, ') + '.')" in app
          and 'await _askGroundwork(part);' in app)

    # Rob 2026-11-01: Groundwork's voice said Meijer as "major" (the same sounds, mˈeɪdʒɚ); it says MY-er now
    from core import speak
    said = [speak.spoken('OK, showing your Meijer transactions.'), speak.spoken("Meijer's receipt"),
            speak.spoken('MEIJER # 210'), speak.spoken('Meijer', names={'Meijer': 'my-your'})]
    check(f"s283 Meijer is said MY-er, not major - and the person's own way still wins ({said})",
          said[:3] == ['OK, showing your Myer transactions.', "Myer's receipt", 'Myer # 210'] and said[3] == 'my-your')

    # Rob 2026-11-01: "If it query the transaction and get not response the voice assistant should show that" - a
    # search that finds nothing says so, aloud and in the toast, instead of "Sure, showing your ... transactions"
    i = app.index('function askLedgerSearch(')
    body = app[i:app.index('\n}\n', i)]
    check("s283 M9 a Ledger search that finds nothing says so - 'I didn't find any Fred Meyer transactions' - not "
          "'showing your ... transactions'",
          'if (!any) {' in body and "_askSaid(`I didn't find any ${named} transactions in the Ledger.`);" in body
          and "_askDone(`No ${named} transactions in the Ledger${heard}`);" in body
          and body.index('if (!any) {') < body.index('OK, showing your'))

    # Rob 2026-11-01: "the phrase Go ie: Groundwork go get my accounts. Should trigger get my accounts" ... "go should work
    # for anything like go to Budget"
    go_want = {
        'Groundwork go get my accounts': 'fetch', 'Groundwork, go and get my accounts.': 'fetch',
        'go ahead and get my accounts': 'fetch', 'Groundwork, get my accounts': 'fetch',
        'go to Budget': 'place:the Budget', 'Groundwork go to my budget': 'place:the Budget',
        'go budget': 'place:the Budget', 'go my budget': 'place:the Budget', 'go open the budget': 'place:the Budget',
        'go ledger': 'place:the Ledger', 'go settings': 'place:Settings', 'go debts': 'place:Debt Payoff',
        'go back to the budget': 'place:the Budget', 'go show me my Kroger transactions': 'ledger:kroger',
        'go build a report': 'do:Opened the report builder', 'go back up my data': 'do:Opened Backup',
        "go see what's coming up this week": 'coming',
        'go back': None, 'go ahead': None, 'go': None, 'go over my budget': None,
    }
    gojs = (app[app.index('const _ASK_SHORT = '):app.index('function _askSay(')]
            + app[app.index('const ASK_PLACES = ['):app.index('function askGo(')]
            + app[app.index('const ASK_DO = ['):app.index('// Questions about the person')]
            + app[app.index('function _askShowTxns(n) {'):app.index('// Rob 2026-10-31: with Groundwork')]
            + app[app.index('const ASK_COMING = '):app.index('async function askComingUp(')]
            + r"""
const what = (q) => {
  const n = _askNorm(q);
  if (ASK_FETCH.test(n)) return 'fetch';
  if (ASK_COMING.test(n)) return 'coming';
  const d = ASK_DO.find(x => x.re.test(n));
  if (d) return 'do:' + d.said;
  const s = _askShowTxns(n);
  if (s) return 'ledger:' + s;
  const bare = n.replace(/^(?:my|the|our|all)\s+/, '');
  const p = askPlace(n) || ASK_PLACES.find(pl => pl.names.includes(bare));
  return p ? 'place:' + p.label : null;
};
""" + 'const L = ' + json.dumps(list(go_want)) + ';\nconsole.log(JSON.stringify(Object.fromEntries(L.map(q => [q, what(q)]))));\n')
    gf = os.path.join(tempfile.mkdtemp(prefix='s283go_'), 'go.js')
    open(gf, 'w', encoding='utf-8').write(gojs)
    gr = subprocess.run([node, gf], capture_output=True, text=True, encoding='utf-8', timeout=60)
    try:
        go = json.loads(gr.stdout.strip().splitlines()[-1])
    except Exception:
        go = {'error': (gr.stdout + gr.stderr)[-300:]}
    go_wrong = {q: (go.get(q), w) for q, w in go_want.items() if go.get(q, 'missing') != w}
    check(f"s283 M10 'go' in front of anything is a lead-in - 'go get my accounts', 'go budget', 'go to Budget', 'go show me "
          f"my Kroger transactions' - and 'go back', 'go ahead' and 'go' alone stay their own words "
          f"({len(go_want)} phrases){' - wrong: ' + ascii(go_wrong) if go_wrong else ''}", not go_wrong)
