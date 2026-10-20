"""Item 103 (gw 2.0/EXPLAIN_PAGE.md; Rob 2026-10-19: "Is their a way to add explain this page to me? and the search
feature reads the page and explains what the page is calculating in simple words and what the numbers mean").

    E1 "Explain" in the top bar and "explain this page" / "what am I looking at" / "explain my budget" in the Ask box
       open one panel for the page and tab on screen; it is AI help (shown only with AI on), like the Ask box
    E2 first, what the page works out: Groundwork's own fixed words for every page and its tabs
    E3 then, with AI on, what the figures mean - from the figures on screen only, each read with its own label; a
       line in anyone else's words (a bank's description) never crosses; Groundwork's short labels said in full
    E4 every number in the answer is a whole figure on the page, or only the fixed words show; the answer says the
       AI can mix up which figure is which and the page is always right
    E5 Health and the Ledger get the fixed words only; nothing is saved or changed
"""
import re


def run(ctx):
    check, app, html = ctx.check, ctx.app_src, ctx.html_src
    ex = app[app.index('const PAGE_EXPLAIN = {'):app.index('// ─── Item 104: when money feels like too much')]
    fn = ex[ex.index('async function explainPage() {'):]
    check('s248 E1 the Explain button is AI help, in the top bar beside the guide',
          'class="btn btn-sm btn-secondary ai-feature" onclick="explainPage()"' in html
          and 'aria-label="Explain this page">Explain</button>' in html)
    intent = app[app.index('function askIntent(q, p, head) {'):]
    intent = intent[:intent.index('if (askFetch(n)) return true;')]
    check('s248 E1 the Ask box: "explain this page", "what am I looking at", "explain my budget" (the page, then explained)',
          'explainPage(); return true;' in intent and 'what am i looking at' in intent
          and 'askGo(expPlace); setTimeout(explainPage, 450)' in intent)

    views = set(re.findall(r'id="view-([a-z]+)"', html))
    described = set(re.findall(r'^  ([a-z]+): \{ what: ', ex, re.M))
    check(f's248 E2 every page has Groundwork\'s own description (missing: {sorted(views - described)})', views <= described)
    tabs = {'budget': ['plan', 'futures', 'bills', 'calendar', 'gifts'], 'debt': ['setup', 'tracker', 'advisor'],
            'health': ['bills', 'plan', 'spending', 'people'], 'byb': ['before', 'after']}
    missing = []
    for v, ts in tabs.items():
        block = ex[ex.index(f'  {v}: {{ what: ') + 5:]
        block = block[:re.search(r'\n  [a-z]+: \{ what: |\n\};', block).start()]
        missing += [f'{v}.{t}' for t in ts if f'      {t}: ' not in block]
    check(f's248 E2 and each tab of Budget, Debt Payoff, Health and Before You Buy ({missing})', not missing)

    check('s248 E3 only lines with a figure and Groundwork\'s own words cross: every other word must be in Groundwork\'s page or code',
          "for (const url of ['/js/app.js', location.pathname || '/'])" in ex
          and "!vocab.has(w.replace(" in ex and "if (!_EXPLAIN_FIG.test(bare)) return null;" in ex)
    check('s248 E3 a figure is read with its label in front; the short labels are said in full ("min" was read as interest)',
          "a figure is read only with its label in front of it" in ex and "'minimum payment $1'" in ex and '_explainSay(line)' in ex)
    check('s248 E3 the call declares what it carries, fences the page as data, and is limited to five sentences',
          "surface: 'explain_page', findings_kinds: EXPLAIN_KINDS[name], max_sentences: 5" in fn
          and "_asData(lines.join('\\n'))" in fn and 'skipGate' not in fn
          and not any(k in ex[ex.index('const EXPLAIN_KINDS = {'):ex.index('const EXPLAIN_SYSTEM')]
                      for k in ("'description'", "'memo'", "'free_text'", "'transaction_text'", "'merchant_text'")))
    sysmsg = ex[ex.index('const EXPLAIN_SYSTEM = '):ex.index('function _explainWhere()')]
    check('s248 E3 the model is told: each sentence one line, its own label, never connect or compute figures, no advice',
          'never work out a new number' in sysmsg and 'Never connect, compare' in sysmsg
          and 'Never say what they should, could or' in sysmsg)

    # E4 - the number check, run here exactly as the page runs it
    lines = ['Income · $5,200.00', 'Debt-free by Jan 2027', 'Visa · $4,200.00 · 22.9% APR']

    def ok(text):
        fig = lambda n: re.sub(r'\.00$', '', re.sub(r'[.,]+$', '', n))
        page = {fig(n) for n in re.findall(r'\d[\d,.]*', ' '.join(lines))}
        return all(fig(n) in page for n in re.findall(r'\d[\d,.]*', text))
    check('s248 E4 the number check: figures on the page pass ("$4,200" is "$4,200.00"); a new one, or a "2" from "2026", does not',
          ok('Your income is $5,200.00 and Visa has $4,200 at 22.9% APR, debt-free by Jan 2027.')
          and not ok('You could save $1,000.') and not ok('In October 2dictated you spent.')
          and "const page = new Set((lines.join(' ').match(/\\d[\\d,.]*/g) || []).map(fig));" in ex
          and "replace(/\\.00$/, '')" in ex)
    check('s248 E4 a failed check shows the fixed words only; a shown answer says the AI can mix up figures',
          'if (text && _explainNumbersOk(text, lines)) {' in fn
          and "it can mix up which figure is which, and the page itself is always right" in fn
          and "only Groundwork\\'s own description is shown" in fn)
    fixed = ex[ex.index('const EXPLAIN_FIXED_ONLY = {'):ex.index('const EXPLAIN_KINDS = {')]
    check('s248 E5 Health and the Ledger get the fixed words only (health stays out of the AI; the Ledger is bank wording)',
          'health:' in fixed and 'ledger:' in fixed and 'health:' not in ex[ex.index('const EXPLAIN_KINDS = {'):ex.index('const EXPLAIN_SYSTEM')]
          and 'if (EXPLAIN_FIXED_ONLY[name] || !EXPLAIN_KINDS[name] || !aiEnabled()) {' in fn)
    check('s248 E5 nothing is saved or changed: no write, no storage',
          not re.search(r'API\.(post|put|patch|delete)\(', ex) and 'localStorage' not in ex)
