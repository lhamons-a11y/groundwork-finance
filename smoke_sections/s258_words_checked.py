"""Item 110 (gw 2.0/WORDS_CHECKED.md; Rob 2026-10-22: "I agree with 1-3" / "I approve push, build"): every sentence
checked against what it claims.

    V1  the Projection's redirect is one payment, said as one        V2 asked once, when the facts are in
    V3  the prompt asks for facts, names as written                  V4 R8 also checks month counts and dates
    V5  R12: no kind of borrowing the facts don't hold               V6 the fixed words meet the same rules
    V7  the 50/30/20 suggestion keeps its number, loses its verdict
"""
import json
import re
import shutil
import subprocess

# V6: lists a fixed sentence is held to (the verdict, advice, cheer, label and borrowing lists)
SWEPT = ('COMMAND_PHRASES', 'CHEER_PHRASES', 'JUDGMENT_JARGON', 'DECISION_VERDICTS', 'INTENT_PHRASES', 'JUDGE_LABELS',
         'NEW_BORROWING', 'EDITORIALIZING')
NOT_SWEPT = {'stop': 'a button or a verb in the interface ("Stop bringing up", "One of these should stop"), not a command'}
# A fixed sentence allowed to keep a listed phrase: (file, phrase, words of the sentence; '=' the whole of it) -> why
ALLOWED = {
    ('app.js', 'a new card', 'Added a new card or loan'): "the person's own action, said back to them",
    ('app.js', 'you must', 'the least you must pay'): 'what a minimum payment is: the contract, not Groundwork',
    ('index.html', 'a credit card', 'credit card statement PDF'): 'a file type',
    ('willingness.js', 'you keep', 'something you keep'): "the Working picture's word for a line the person keeps",
    ('tiletext.js', 'you keep', 'something you keep'): "the Working picture's word for a line the person keeps",
    ('willingness.js', 'you tend to', 'no reading of what you tend to do'): 'says Groundwork has no such reading',
    ('app.js', 'crisis', ''): 'the crisis lines by name (item 104, CARE.md, fixed on purpose)',
    ('app.js', 'consider', 'consider getting legal advice'): "Rob's ruled words for a debt in collections (COLLECTIONS.md)",
    ('app.js', 'consider', "what the consumer financial protection bureau recommends"): "the CFPB's own steps, attributed and linked",
    ('app.js', 'consider', 'no oil change'): 'by design (Rob 2026-10-22): no oil change in the ledger, check before a long drive',
    ('app.js', 'consider', 'electric vehicle detected'): 'the same trip check, for an electric vehicle',
    ('app.js', 'a credit card', '=a credit card'): 'the name of a kind of debt the person picks from',
    ('app.js', 'a credit card', 'paying down a credit card is a guaranteed return'): "the person's own card, explained",
    ('app.js', 'you need to', 'type delete to confirm'): 'how to confirm deleting everything: the person asked to',
    ('app.js', 'you should', 'lean budget mode'): 'text sent to the model, telling it what not to write',
    ('app.js', 'consider', 'lean budget mode'): 'text sent to the model, telling it what not to write',
    ('app.js', 'overage', 'most consistent overage category'): 'text sent to the model',
    ('app.js', 'overage', 'spending trends requiring attention'): 'text sent to the model',
}
PROMPT = re.compile(r'content\s*:|system\s*:|prompt|role\s*:', re.I)


def _says(allowed, low):
    """An ALLOWED entry's words in the sentence - or, starting '=', the whole sentence."""
    return low.strip() == allowed[1:].lower() if allowed.startswith('=') else allowed.lower() in low


def _strings(src):
    """(line, visible text, the code before it on its line) for each string literal, template literals across lines."""
    src = re.sub(r'/\*.*?\*/', lambda m: '\n' * m.group(0).count('\n'), src, flags=re.S)
    src = '\n'.join(re.sub(r'(^|[^:\\])//.*$', r'\1', ln) for ln in src.split('\n'))
    for m in re.finditer(r'`((?:\\.|[^`\\])*)`|\'((?:\\.|[^\'\\\n])*)\'|"((?:\\.|[^"\\\n])*)"', src):
        s = next(g for g in m.groups() if g is not None)
        start = src.rfind('\n', 0, m.start()) + 1
        before = src[start:m.start()]
        vis = re.sub(r'\$\{[^{}]*\}', ' ', s)
        vis = re.sub(r'<[^>]*>', ' ', vis)
        vis = re.sub(r'\s+', ' ', vis).strip()
        if re.search(r'[A-Za-z]{3,} [A-Za-z]{3,}', vis):
            yield src.count('\n', 0, m.start()) + 1, vis, before


def run(ctx):
    check, base = ctx.check, ctx.BASE
    app = ctx.app_src
    rules = json.loads((base / 'static/voice_rules.json').read_text(encoding='utf-8'))['wordlists']

    # ── V1-V3: the Projection ────────────────────────────────────────────────────────────────────────────────────
    load = app[app.index('async function _loadDashProjection('):app.index('async function _loadDashProjection(') + 3000]
    check('s258 V1 the redirect is one payment: this month\'s amount paid once to the highest-rate debt',
          'function _simulatePayoffOnce(amount, cardId)' in app and '_simulatePayoffOnce(leverage.surplus' in load
          and '_simulatePayoff(leverage.surplus)' not in load)
    rend = app[app.index('async function _renderProjectionAI('):app.index('function _renderProjectionFallback(')]
    check('s258 V1/V3 the prompt says one payment, facts only, names as written',
          "If this month's $${d.surplus} went once to" in rend and 'It is one payment, not every month.' in rend
          and 'State only the facts given.' in rend and 'Use every account name exactly as written.' in rend
          and 'Keep all advice focused' not in app)
    check('s258 V2 asked once the engine has answered, and once per change of facts',
          'baseline === undefined || withRedirect === undefined' in load
          and "if (_projLast && _projLast.fp === prompt) { content.innerHTML = _projLast.html; return; }" in rend
          and 'if (_projAsking === prompt) return;' in rend)

    # ── V4/V5: the check, in the harness (the page's is checked in Node where it is available) ─────────────────────
    import importlib
    import sys
    sys.path.insert(0, str(base))
    v = importlib.import_module('voice_discipline_test')

    class Case:
        name = 'projection'
        findings = ("If this month's $287 went once to Cashback Visa: payoff Aug 2030→Aug 2029, 12 months sooner, saves "
                    "$1303 interest.")
    res = lambda t: {k for k, x in v.check(t, Case()).items() if not x[0] and not k.startswith('R6')}
    check('s258 V4 a month count or a date not in the facts fails R8; the ones that are pass',
          'R8_number_provenance' in res('Restaurants are $287 over, delaying debt freedom by one month.')
          and 'R8_number_provenance' in res('Payoff moves to March 2028.')
          and not res("Paying this month's $287 to Cashback Visa once moves payoff to August 2029, 12 months sooner."))
    check('s258 V5 R12: "a cashback credit card" fails; the person\'s own card by name passes',
          'R12_no_new_borrowing' in res('Redirect it to a cashback credit card to save $1303.')
          and 'R12_no_new_borrowing' not in res("This month's $287 to Cashback Visa saves $1303."))
    check('s258 V4/V5 the page\'s check has the same two rules',
          'function _monthFigures(s)' in app and "invented.push(...[..._monthFigures(text)]" in app
          and "record('R12_no_new_borrowing'," in app and 'NEW_BORROWING: [' in app
          and 'unhealthy' in rules['JUDGMENT_JARGON'] and 'healthy' in rules['JUDGMENT_JARGON'])
    if shutil.which('node'):
        body = app[app.index('const _MONTH_WORDS'):app.index('function _financialNumbers(')]
        js = body + ("\nconsole.log(JSON.stringify([[..._monthFigures('Aug 2030 to August 2029, 12 months sooner, "
                     "one month later')].sort()]));")
        r = subprocess.run(['node', '-e', js], capture_output=True, text=True)
        check(f's258 V4 in Node: the page reads months and dates the harness way ({r.stdout.strip()})',
              r.stdout.strip() == '[["12mo","1mo","aug2029","aug2030"]]')

    # ── V6: the fixed words ──────────────────────────────────────────────────────────────────────────────────────
    # the voice text and the word lists themselves are blanked (lines kept, so line numbers still match)
    a0 = app.index('const _GW_VOICE_FALLBACK'); a1 = app.index('};', app.index('const _VOICE_RULES_FALLBACK')) + 2
    swept_app = app[:a0] + re.sub(r'[^\n]', ' ', app[a0:a1]) + app[a1:]
    files = [('app.js', swept_app)] + [(f.name, f.read_text(encoding='utf-8')) for f in sorted((base / 'static/js/teaching').glob('*.js'))]
    found = []
    for name, src in files:
        for line, vis, before in _strings(src):
            if PROMPT.search(before) or 'Rules:' in vis or 'Second person' in vis or 'GROUNDWORK VOICE' in vis:
                continue                                                        # text sent to the model
            low = ' ' + vis.lower() + ' '
            for k in SWEPT:
                for p in rules.get(k, []):
                    w = p.strip()
                    if w in NOT_SWEPT or not re.search(r'(?<![a-z])' + re.escape(w) + r'(?![a-z])', low):
                        continue
                    if any(f == name and q == w and _says(s, low) for (f, q, s) in ALLOWED):
                        continue
                    found.append(f'{name}:{line} "{w}" in "{vis[:80]}"')
    html = re.sub(r'<script.*?</script>|<style.*?</style>', ' ', ctx.html_src, flags=re.S)
    for m in re.finditer(r'>([^<>]{8,})<', html):
        vis = re.sub(r'\s+', ' ', m.group(1)).strip()
        low = ' ' + vis.lower() + ' '
        for k in SWEPT:
            for p in rules.get(k, []):
                w = p.strip()
                if w in NOT_SWEPT or not re.search(r'(?<![a-z])' + re.escape(w) + r'(?![a-z])', low):
                    continue
                if any(f == 'index.html' and q == w and _says(s, low) for (f, q, s) in ALLOWED):
                    continue
                found.append(f'index.html "{w}" in "{vis[:80]}"')
    check(f's258 V6 every fixed sentence the app shows meets the voice rules, or is named with its reason ({found[:5]})',
          not found)
    check('s258 V6 the reworded lines: the concentration fact, the achievement, the trip, the savings goal',
          '% of your portfolio.\n' in app and 'consider diversifying' not in app
          and "behavior:'Counts a month that saved more than its target.'" in app
          and 'so you can decide with the cost in front of you.' in app
          and 'takes net worth growing by' in app)

    # ── V7 ───────────────────────────────────────────────────────────────────────────────────────────────────────
    check('s258 V7 the 50/30/20 suggestion keeps its number and says where it comes from, with no verdict',
          ': your minimums plus 20% of your income, from the 50/30/20 split.' in app and 'healthy 50/30/20' not in app)
