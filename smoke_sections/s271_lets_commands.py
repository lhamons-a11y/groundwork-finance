"""Rob 2026-10-31: in conversation, "let's" opens too - "Groundwork lets build a report" opens the report builder, and
"Groundwork Lets view my budget" opens the Budget. So does "I want" - "Groundwork I want to see my budget", and
"I want my budget" without the "to".

    L1  "let's", "lets" and "let us" lead a command the way "Groundwork" and "let me" already do (_ASK_LEAD); what
        follows is read as if it were said alone, so every place and command that works alone works after it
    L2  "build / make / create a report" opens Build a report (item 115), and so does naming "the report builder";
        "make my monthly report" still opens the monthly report, and "view reports" still the Reports page
    L3  Rob: "Show me my Kroger transactions" - "ok showing your Kroger's transactions in Ledger": the Ledger, searched
        for Kroger, with AI on or off; "my recent transactions" is the whole Ledger
    L4  Rob: "Groundwork open Budget" - "sure opening budget for you": a command said aloud is answered aloud in
        Groundwork's voice; typed, only the toast says it, and nothing after it is read
    Conversation mode hands anything that is not a reading command to the Ask bar, so this one path covers both.
"""
import json
import os
import shutil
import subprocess
import tempfile


def run(ctx):
    check = ctx.check
    app = (ctx.BASE / 'static' / 'js' / 'app.js').read_text(encoding='utf-8')
    check('s271 L1 "let\'s", "lets" and "let us" are lead-ins, beside "let me" and "groundwork"',
          r"|let me|let\x27s|lets|let us|" in app[app.index('const _ASK_LEAD = '):app.index('function _askNorm(')])
    node = shutil.which('node')
    if not node:
        return
    js = (app[app.index('const _ASK_SHORT = '):app.index('function _askSay(')]
          + app[app.index('const ASK_PLACES = ['):app.index('function askGo(')]
          + app[app.index('const ASK_DO = ['):app.index('// Questions about the person')]
          + """
const cases = """ + json.dumps([
        ['Groundwork lets build a report', 'Opened the report builder'],
        ['Groundwork Lets view my budget', 'budget'],
        ["Groundwork, let's open the report builder", 'report:builder'],
        ['let us see my debts', 'debt'],
        ["Groundwork let's make a new report", 'Opened the report builder'],
        ['lets go to net worth', 'networth'],
        ['Groundwork lets create a custom report', 'Opened the report builder'],
        ['make my monthly report', 'Opened the monthly report'],
        ['view reports', 'reports'],
        ["let's view the calendar", 'budget'],
        ['Groundwork I want to see my budget', 'budget'],
        ['Groundwork I want to build a report', 'Opened the report builder'],
        ['Groundwork I want my budget', 'budget'],
        ["Groundwork I'd like the calendar", 'budget'],
        ['I want to go to investments', 'investments'],
        ['I need help', None],
        ['I want to know why my budget is short', None],
        ['lets talk about why restaurants is so high', None],
    ]) + """;
console.log(JSON.stringify(cases.map(([q, want]) => {
  const n = _askNorm(q);
  const d = ASK_DO.find(x => x.re.test(n));
  const bare = n.replace(/^(?:my|the|our|all)\\s+/, '');      // askIntent's last step: a page's name alone opens it
  const p = d ? null : (askPlace(n) || ASK_PLACES.find(pl => pl.names.includes(bare)));
  const got = d ? d.said : p ? (p.report ? 'report:' + p.report : p.view) : null;
  return [q, got, want];
})));
""")
    d = tempfile.mkdtemp(prefix='s271_')
    f = os.path.join(d, 'lets.js')
    open(f, 'w', encoding='utf-8').write(js)
    out = json.loads(subprocess.run([node, f], capture_output=True, text=True, encoding='utf-8', timeout=30).stdout or '[]')
    wrong = [(q, got) for q, got, want in out if got != want]
    check(f's271 L1/L2 each phrase lands where it means; "make my monthly report" and "view reports" are unchanged ({wrong})',
          out and not wrong)
    js2 = (app[app.index('function _askShowTxns(n) {'):app.index('function askLedgerSearch(term) {')] + """
const shows = """ + json.dumps([
        ['show me my kroger transactions', 'kroger'], ["show me kroger's transactions", 'kroger'],
        ['show my transactions at walmart', 'walmart'], ['view all the amazon purchases', 'amazon'],
        ['show me my recent transactions', None], ['show me my transactions', None], ["show me this month's transactions", None],
    ]) + """;
const replies = """ + json.dumps([['Opened Import', 'Sure, opening Import for you.'],
                                  ['Opened the report builder', 'Sure, opening the report builder for you.'],
                                  ["Here's the AI switch", "Here's the AI switch."], ['', '']]) + """;
console.log(JSON.stringify({ shows: shows.map(([q, want]) => [q, _askShowTxns(q), want]),
                             replies: replies.map(([d, want]) => [d, _askSaidFor(d), want]) }));
""")
    f2 = os.path.join(d, 'replies.js')
    open(f2, 'w', encoding='utf-8').write(js2)
    o2 = json.loads(subprocess.run([node, f2], capture_output=True, text=True, encoding='utf-8', timeout=30).stdout or '{}')
    bad = [x for x in o2.get('shows', []) if x[1] != x[2]] + [x for x in o2.get('replies', []) if x[1] != x[2]]
    check(f's271 L3/L4 "show me my Kroger transactions" searches the Ledger for Kroger; a command\'s spoken reply is "Sure, '
          f'opening ... for you." ({bad})', o2.get('shows') and not bad)
    ledger = app[app.index('function askLedgerSearch(term) {'):app.index('// A budget line or category the person named')]
    intent = app[app.index('function askIntent(q, p, head, assist = false) {'):app.index('// ─── Item 103: Explain this page')]
    ask = app[app.index('async function askGroundwork('):]
    check('s271 L3/L4 the Ledger search says "OK, showing your Kroger transactions in the Ledger"; pages, commands and '
          'Get my accounts answer aloud; the show command runs with AI on too; the spoken flag is spent on a command',
          "_askSaid(`OK, showing your ${_askTitle(term)} transactions in the Ledger.`)" in ledger
          and "_askSaid(_askSaidFor(d.said));" in intent and 'const shown = _askShowTxns(n);' in intent
          and '!assist' not in intent[intent.index('const shown = _askShowTxns(n);') - 40:intent.index('const shown = _askShowTxns(n);')]
          and "_askSaid('Sure, getting your accounts now.')" in app
          and 'if (spoken && window._gwVoiceAsked) { window._gwVoiceAsked = false; _askSpeakPanel(); }' in ask[:1500]
          and 'if (!window._gwVoiceAsked) return;' in app)
    go = app[app.index('function askGo(pl)'):app.index('// ── Item 102 (Rob 2026-10-19: "add those four')]
    check('s271 L3/L4 opening the Ledger shows all of it, and a page opened is answered "Sure, opening ... for you."',
          "_askSaid(`Sure, opening ${pl.label} for you.`);" in go and "g('ledgerSearch').value = '';" in go)
    check('s271 L2 a place that names a report opens that report on the Reports page',
          'if (pl.report) setTimeout(() => _rcOpenReport(pl.report), 80);' in go
          and "{ label: 'the report builder', names: ['report builder', 'build a report', 'build your own report'], view: 'reports', report: 'builder' }" in app)
