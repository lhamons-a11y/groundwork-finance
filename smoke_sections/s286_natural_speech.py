"""Item 116 V24: Groundwork understands how people talk (Rob 2026-11-05: "stronger and feel more natural talking and
understanding of the user asks"; VOICE_ASSISTANT.md 4h). Run on the page's own code in Node:

    N1  scripts/voice_natural_asks.json: the build set all routes as meant, the held-out set stays at or above what it was
        measured at, and no real question or passing remark is taken for a command
    N2  a store is only a store when it is in the record or sounds like one: "show me the money" searches nothing
    N3  said aloud with AI off, a spending question hears the record's own sum, the same charges the Ledger then shows,
        and a date range counts only its own lines; a store with no charges says so
    N4  a sentence that stops on a word that cannot end one waits for the rest, is joined to it, is asked as it stands if
        nothing comes, and what sounds like someone struggling never waits
    N5  what a person says to cut in, and to end it: "Groundwork, stop", "hold on", "one more time"; a spoken reply can be
        said again, and "One moment" is not what is repeated
    N6  said aloud with AI off, a question about a figure says where it is and opens the page (V4); with nothing to answer
        it, a person's reply, not how Groundwork is built
    N7  corrections and follow-ups: "no, I meant Walmart", "next week?" after what's coming, and the week said is the week
        looked up
    N8  the first page opened uses Rob's words, and later ones are shorter
"""
import importlib.util
import json
import os
import shutil
import subprocess
import tempfile

# Measured 2026-11-05 when the fix was finished: only this total was looked at while fixing. If a change lowers it, read
# what stopped working; raising it here needs a new set of held-out phrases to mean anything.
HELD_OUT_FLOOR = 74


def run(ctx):
    check = ctx.check
    node = shutil.which('node')
    if not node:
        check('s286 node is available for the page test', False)
        return
    spec = importlib.util.spec_from_file_location('voice_natural_measure', ctx.BASE / 'scripts' / 'voice_natural_measure.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    res = mod.measure(ctx.BASE)

    build_bad = [(q, w, g) for q, w, g in res['build'] if g != w]
    check(f's286 N1 every phrase in the build set does what is meant, {len(res["build"])} of them ({build_bad[:6]})', not build_bad)
    held = sum(g == w for _q, w, g in res['held_out'])
    check(f's286 N1 the held-out set stays at {HELD_OUT_FLOOR} or better of {len(res["held_out"])} (now {held})', held >= HELD_OUT_FLOOR)
    taken = [(q, g) for q, _w, g in res['not_commands'] if g is not None]
    check(f's286 N1 no real question or passing remark is taken for a command, of {len(res["not_commands"])} ({taken[:6]})', not taken)

    code = mod.STUBS + mod.HOUSE + mod.page_code(ctx.BASE)
    js = code + r"""
const spoken = [];
window.GWVoice = { say: w => spoken.push(w), first: () => false };
S.transactions = [
  { merchant: 'Kroger', description: 'KROGER 123', category: 'Groceries', amount: 40.5, type: 'debit', date: '2026-11-02' },
  { merchant: 'Kroger', description: 'KROGER 123', category: 'Groceries', amount: 20, type: 'debit', date: '2026-10-15' },
  { merchant: 'Kroger', description: 'KROGER REFUND', category: 'Groceries', amount: 5, type: 'credit', date: '2026-10-16' },
  { merchant: 'Costco', description: 'COSTCO', category: 'Groceries', amount: 100, type: 'debit', date: '2025-06-01' },
];
function ask(q, assist) {
  spoken.length = 0; log.length = 0; window._askPlace = null;
  Object.keys(els).forEach(k => delete els[k]);
  const panel = { innerHTML: '' };
  window._gwVoiceAsked = true;
  const hit = askIntent(q, panel, '', !!assist);
  return { hit, box: els.ledgerSearch ? els.ledgerSearch.value : '', spoken: spoken.slice(), toasts: log.filter(x => x[0] === 'toast').map(x => x[1]), views: log.filter(x => x[0] === 'view').map(x => x[1]), apis: log.filter(x => x[0] === 'api').map(x => x[1]) };
}
const now = new Date();
const thisM = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
const prev = new Date(now.getFullYear(), now.getMonth() - 1, 1);
const lastM = `${prev.getFullYear()}-${String(prev.getMonth() + 1).padStart(2, '0')}`;
S.transactions[0].date = thisM + '-02'; S.transactions[1].date = lastM + '-15'; S.transactions[2].date = lastM + '-16';
const out = {};
_askLast = null;
out.money = ['show me the money', 'show me more', 'find a way to save'].map(q => ask(q).box);
out.total = ask('how much have I spent at Kroger');
out.lastMonth = ask('how much did I spend at Kroger last month');
out.lastGo = ask('when did I last go to Costco');
out.noneThisMonth = ask('did I go to Costco this month');
out.withAi = ask('what did I spend at Kroger', true);
out.record = ask('how much do I owe');
_askOpenedAt = 0; _askOpenedTurn = 0;
out.opens = [ask('open my budget').spoken[0], ask('open the ledger').spoken[0], ask('open the calendar').spoken[0]];
_askLast = null; ask('show me Kroger');
out.fix = ask('no I meant Costco').box;
_askLast = null; ask('show me Kroger');
out.instead = ask('Costco instead').box;
_askLast = null;
out.fixAlone = ask('I mean it is a lot of money').hit;
out.nextWeek = ask('what bills are due next week').apis;
out.followNext = ask('and next month').apis;
out.neverMind = ask('never mind');
out.parts = [_askParts('open the budget, actually the ledger'), _askParts('open the budget and then show me Kroger')];
console.log(JSON.stringify(out));
"""
    d = tempfile.mkdtemp(prefix='s286_')
    f = os.path.join(d, 'page.js')
    open(f, 'w', encoding='utf-8').write(js)
    r = subprocess.run([node, f], capture_output=True, text=True, encoding='utf-8', timeout=60)
    o = json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else {}
    check(f's286 the page test ran ({r.stderr[-300:] if r.returncode else ""})', bool(o))
    if not o:
        return
    check(f's286 N2 a phrase that names nothing in the record searches nothing ({o["money"]})', o['money'] == ['', '', ''])
    check(f's286 N3 a spoken total is the record\'s charges only, not the refund ({o["total"]["spoken"]})',
          o['total']['box'] == 'kroger' and '$60.50' in o['total']['spoken'][0] and '2 purchases' in o['total']['spoken'][0])
    check(f's286 N3 "last month" counts only that month ({o["lastMonth"]["spoken"]})',
          '$20.00' in o['lastMonth']['spoken'][0] and 'last month' in o['lastMonth']['spoken'][0] and '1 purchase,' not in o['lastMonth']['spoken'][0])
    check(f's286 N3 the last visit is its date and amount ({o["lastGo"]["spoken"]})',
          'June 1, 2025' in o['lastGo']['spoken'][0] and '$100.00' in o['lastGo']['spoken'][0])
    check(f's286 N3 a store with no charges in the span says so ({o["noneThisMonth"]["spoken"]})',
          o['noneThisMonth']['spoken'][0] == "I don't see any Costco purchases this month.")
    check(f's286 N3 the sum is followed by where the lines are; the last visit by where it is ({o["total"]["spoken"]}, {o["lastGo"]["spoken"]})',
          o['total']['spoken'][0].endswith('Here they are in the Ledger.') and o['lastGo']['spoken'][0].endswith("It's in the Ledger."))
    check('s286 N3 with AI on the question goes to the assistant, not this sum', not o['withAi']['hit'])
    check(f's286 N6 AI off, spoken: the sentence, then the page ({o["record"]})',
          o['record']['spoken'] == ['What each debt owes, and the total, are on Debt Payoff.'] and o['record']['views'] == ['debt'])
    check(f's286 N7 "no, I meant" and "instead" put the search right ({o["fix"]}, {o["instead"]})', o['fix'] == 'costco' and o['instead'] == 'costco')
    check('s286 N7 "I mean" with nothing to put right, and nothing real named, stays a question', not o['fixAlone'])
    check(f's286 N7 next week is looked up past this week; a follow-up carries on ({o["nextWeek"]}, {o["followNext"]})',
          o['nextWeek'] == ['/api/calendar?days=14'] and o['followNext'] == ['/api/calendar?days=62'])
    check(f's286 N1 never mind is answered and does nothing ({o["neverMind"]["spoken"]})',
          o['neverMind']['spoken'] == ['OK, never mind.'] and not o['neverMind']['views'])
    check(f's286 N1 a correction is one ask, two commands are two ({o["parts"]})', o['parts'][0] is None and len(o['parts'][1]) == 2)
    check(f's286 N8 the first page opened in Rob\'s words, then shorter, and never the same twice running ({o["opens"]})',
          o['opens'][0] == 'Sure, opening the Budget for you.' and o['opens'][1] == "OK, here's the Ledger." and o['opens'][2] == "Here's the Calendar.")

    # The microphone's half, access.js's own code
    acc = (ctx.BASE / 'static' / 'js' / 'teaching' / 'access.js').read_text(encoding='utf-8')
    hold = acc[acc.index('  var HOLD_MS = '):acc.index('  // V7 (item 116): the first time the microphone is turned on')]
    js2 = r"""
var window = globalThis, conv = null, routed = [], timers = [];
var setTimeout = (f, ms) => { timers.push(f); return timers.length; }, clearTimeout = () => { timers.length = 0; };
var route = t => routed.push(t);
window.careLevel = t => /want to die/i.test(t) ? 'danger' : null;
""" + hold + r"""
const out = {};
_routeWhole('Show me my'); out.waited = routed.length;
_routeWhole('Kroger transactions.'); out.joined = routed.slice();
routed.length = 0; timers.length = 0;
_routeWhole('Open the'); const t = timers.shift(); t(); out.alone = routed.slice();
routed.length = 0; timers.length = 0;
_routeWhole('I want to die and'); out.care = routed.slice(); out.careTimers = timers.length;
routed.length = 0;
['Open my budget.', 'Stop', 'What is an APR?'].forEach(_routeWhole); out.whole = routed.slice();
console.log(JSON.stringify(out));
"""
    f2 = os.path.join(d, 'hold.js')
    open(f2, 'w', encoding='utf-8').write(js2)
    r2 = subprocess.run([node, f2], capture_output=True, text=True, encoding='utf-8', timeout=30)
    h = json.loads(r2.stdout) if r2.returncode == 0 and r2.stdout.strip() else {}
    check(f's286 N4 the hold ran ({r2.stderr[-300:] if r2.returncode else ""})', bool(h))
    if h:
        check(f's286 N4 "show me my ... Kroger transactions" is one ask ({h["joined"]})', h['waited'] == 0 and h['joined'] == ['Show me my Kroger transactions.'])
        check(f's286 N4 nothing more said: it is asked as it stands, never lost ({h["alone"]})', h['alone'] == ['Open the'])
        check(f's286 N4 what sounds like someone struggling never waits ({h["care"]})', h['care'] == ['I want to die and'] and h['careTimers'] == 0)
        check(f's286 N4 a finished sentence goes straight through ({h["whole"]})', h['whole'] == ['Open my budget.', 'Stop', 'What is an APR?'])
    barge = acc[acc.index('  var BARGE = {'):acc.index('  // The room\'s level')]
    check('s286 N5 how people cut in: hold on, wait, never mind, one more time',
          all(f"'{w}'" in barge for w in ('hold on', 'wait', 'never mind', 'one more time', 'what did you say', 'too fast')))
    check('s286 N5 "Groundwork, stop." and "okay stop please" are matched as "stop"',
          "var t = _norm(text).replace(/^(?:(?:hey |ok |okay )?groundwork|ok|okay|hey|please|um|uh)\\s+(?=\\S)/, '').replace(/\\s+please$/, '');" in acc)
    check('s286 N5 a spoken reply can be said again; "One moment" is not what is repeated',
          "if (w && w !== 'One moment.') last = { words: w, section: null };" in acc)
    check('s286 N5 people end it in their own words too', all(w in acc[acc.index('var MIC_OFF = '):acc.index('var YES_NO = ')] for w in ("i'm done", 'all done', 'that is all')))
    app = (ctx.BASE / 'static' / 'js' / 'app.js').read_text(encoding='utf-8')
    check('s286 N6 nothing to answer it, AI off, spoken: what it can do, not how it is built',
          "_askSaid(\"Sorry, I didn't get that. You could say open my budget" in app)
    groundwork = app[app.index('async function _askGroundwork('):]
    check('s286 N4 the care check still comes before any understanding of the words',
          groundwork.index('if (careAsk(q, p, head)) return;') < groundwork.index('askIntent(q, p, head'))
