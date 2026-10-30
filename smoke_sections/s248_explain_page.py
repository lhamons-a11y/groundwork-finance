"""Item 103 (gw 2.0/EXPLAIN_PAGE.md; Rob 2026-10-19: "Is their a way to add explain this page to me? and the search
feature reads the page and explains what the page is calculating in simple words and what the numbers mean"), as
amended 2026-10-20 (Rob: "meta data that the user can see but is attached behind the values that tells the agent where
in the historian and database these values are located and then the result is only reading the same way that the
report is"; and "someone see Restaurants $500.00 they don't think that is right it should show the transactions").

    E1 "Explain" in the top bar and "explain this page" / "what am I looking at" / "explain my budget" in the Ask box
       open one panel for the page and tab on screen; it is AI help (shown only with AI on), like the Ask box
    E2 first, what the page works out: Groundwork's own fixed words for every page and its tabs
    E3 every figure Explain may read carries its key (data-fig) - what it is, how it is worked out, the record it is
       kept in - shown on hover; Explain reads only these, never the page's text
    E4 one line per figure, starting with its number; a line is kept only when every number in it is that figure's
       own; the name and value shown are Groundwork's, the sentence the AI's
    E5 a spent figure opens the transactions behind it in a grid, from the same list the figure adds up
    E6 Health and the Ledger get the fixed words only; nothing is saved or changed
"""
import re


def run(ctx):
    check, app, html = ctx.check, ctx.app_src, ctx.html_src
    ex = app[app.index('const PAGE_EXPLAIN = {'):app.index('// ─── Item 104: when money feels like too much')]
    fn = ex[ex.index('async function explainPage() {'):]
    check('s248 E1 the Explain button is AI help, in the top bar beside the guide',
          'class="btn btn-sm btn-secondary ai-feature" onclick="explainPage()"' in html
          and 'aria-label="Explain this page">Explain</button>' in html)
    intent = app[app.index('function askIntent(q, p, head, assist = false) {'):]
    intent = intent[:intent.index('if (askFetch(n)) return true;')]
    check('s248 E1 the Ask box: "explain this page", "what am I looking at", "explain my budget" (the page, then explained)',
          'explainPage(); return true;' in intent and 'what am i looking at' in intent
          and '^(?:explain|describe|break down)(?: this| the| these| my| all)? (?:page|screen|numbers|figures|totals)' in intent   # "explain these numbers to me" (Rob 2026-10-20)
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

    # E3 - the keys: every tag used names a registered figure, and every registered figure says what it is and where it is kept
    figs = ex[ex.index('const FIGS = {'):ex.index('function gwFig(')]
    keys = dict(re.findall(r"'([a-z_]+\.[a-z_]+)':\s*\{ label: '((?:[^'\\]|\\.)*)'", figs))
    whole = app + html
    used = set(re.findall(r"""gwFig\('([a-z_.]+)'""", whole)) | set(re.findall(r'data-fig="([a-z_.]+)"', whole))
    for call in re.findall(r'_figSet\([^;]*\);', app):
        used |= set(re.findall(r"'([a-z_]+\.[a-z_]+)'", call))
    unknown = sorted(k for k in used if k not in keys)
    check(f's248 E3 every figure tag names a registered figure ({unknown})', used and not unknown)
    rows = re.findall(r"'([a-z_]+\.[a-z_]+)':\s*\{ label: '.*?', means: '.*?', record: '(.*?)' \}", figs)
    check(f's248 E3 every registered figure says what it means and the record it is kept in ({len(rows)} of {len(keys)})',
          len(rows) == len(keys) >= 30 and all(r for _, r in rows))
    pages = {'budget': ['wl-left', 'wl-income', 'bhs-out', 'budget.line_spent', 'budget.group_spent'],
             'debt': ['debt.free_date', 'debt.total_owed', 'debt.card_balance', 'debt.card_min'],
             'networth': ['nw.total', 'nw.assets', 'nw.liabilities'], 'dashboard': ['dash.debt_free_date', 'dash.interest_saved'],
             # Rob 2026-10-20: "Tag the figures on the remaining pages ... with transaction grids where a figure is spending"
             'investments': ['inv.value', 'inv.gain', 'inv.pos_value', 'inv.pos_gain'], 'trophy': ['trophy.earned', 'trophy.progress'],
             'byb': ['byb.left_after', 'byb.dti_with', 'byb.free_with'], 'trip': ['trip.total', 'trip.lodging', 'trip.surplus'],
             'reports': ['report.line', 'rc.cat_total', 'rc.cat_high']}
    absent = [k for ks in pages.values() for k in ks if k not in whole]
    check(f's248 E3 every page with figures tags them - Budget, Debt Payoff, Net Worth, the Dashboard, Investments, the Trophy Room, Before You Buy, the Trip Planner, Reports ({absent})', not absent)
    check('s248 E3 hovering a figure shows what it is and where it is kept',
          "document.addEventListener('mouseover'" in ex and 'el.title = figWhere(el)' in ex and 'Kept in: ${f.record}' in ex)
    reader = ex[ex.index('function _explainFigures(view) {'):ex.index('const _explainNums')]
    check('s248 E3 Explain reads only tagged figures, never the page\'s own text',
          "view.querySelectorAll('[data-fig]')" in reader and 'FIGS[el.dataset.fig]' in reader
          and '_explainVocab' not in app and "querySelectorAll('*')" not in reader)
    check('s248 E3 the call declares what it carries, fences the figures as data, and is limited',
          "surface: 'explain_page', findings_kinds: EXPLAIN_KINDS[name], max_sentences: 5" in fn
          and '_asData(list)' in fn and 'skipGate' not in fn
          and not any(k in ex[ex.index('const EXPLAIN_KINDS = {'):ex.index('const EXPLAIN_SYSTEM')]
                      for k in ("'description'", "'memo'", "'free_text'", "'transaction_text'", "'merchant_text'")))

    # E4 - the per-line check, run here exactly as the page runs it
    nums = lambda t: [re.sub(r'\.00$', '', n.rstrip('.,')) for n in re.findall(r'\d[\d,.]*', t)]
    figs_ = [{'of': '', 'label': 'Income this month', 'value': '$5,200.00'},
             {'of': 'Groceries', 'label': 'Projected by month-end', 'value': '$66.00 proj.'},
             {'of': '', 'label': 'Debt-free date', 'value': 'Jan 2027'}]

    def lines(raw):
        kept = []
        for line in [l.strip() for l in raw.split('\n') if l.strip()]:
            m = re.match(r'^\[(\d+)\]\s*(.+)$', line)
            f = figs_[int(m.group(1)) - 1] if m and 1 <= int(m.group(1)) <= len(figs_) else None
            if not f:
                continue
            body = m.group(2)
            for e in [f['of'] and f['of'] + ' - ' + f['label'], f['label'], f['value']]:
                if e and body.lower().startswith(e.lower()):
                    body = re.sub(r'^[\s:–—-]+', '', body[len(e):])
            own = set(nums(f['value'] + ' ' + f['of']))
            if body and all(n in own for n in nums(body)):
                kept.append(f['label'])
        return kept
    got = lines('[1] Income this month: $5,200.00 - All your income lines this month.\n[2] $600.00 - Your total expenses.\n'
                '[3] Debt-free date: Jan 2dict - When the last debt is paid.\n[9] Something else.\nSummary: these show your month.')
    check(f's248 E4 a line is kept only with its own figure\'s numbers: a wrong pairing, a garbled value, a missing figure '
          f'and a summary are dropped ({got})', got == ['Income this month'])
    check('s248 E4 the shown name and value are Groundwork\'s; the AI\'s sentence sits under them',
          'kept.push({ f, i: figs.indexOf(f), body:' in ex and '${esc(f.key === \'report.line\' ? f.of : (f.of ? f.of + \' - \' : \'\') + f.label)}: ${esc(f.value)}' in fn
          and '${figName(k.f, k.i)}' in fn
          and "the sentence under it is the AI's" in fn)
    check('s248 E4 when the AI doesn\'t answer, or its wording fails the check, every figure is still explained - in '
          'Groundwork\'s own words from its tag (what it is, where it is kept) - and the note says which happened',
          "sectionHead('Your numbers, in Groundwork\\'s words') + ownWords(all)" in fn
          and "The AI on this computer didn't answer this time" in fn and "The AI's wording didn't pass Groundwork's check this time" in fn
          and 'in Groundwork\'s words</summary>${ownWords(rest)}' in fn and "doesn't belong to the figure it named" not in fn)

    # E5 - the transactions behind a spent figure
    check('s248 E5 the spent figure and its grid read one list: the figure is that list\'s sum',
          'function _catTxnsInMonth(catName, monthKey) {' in app
          and 'return _catTxnsInMonth(catName, monthKey).reduce((s, t) => s + t.amount, 0);' in app
          and 'return _budgetTxnsForCat(catName).reduce((sum, t) => sum + t.amount, 0);' in app
          and "_catTxnsInMonth(cat.slice(1), _budgetMonthKey) : _budgetTxnsForCat(cat)" in ex)
    check('s248 E5 a spent figure on Budget opens the grid; Explain and "why is restaurants so high" open it too',
          "gwFig('budget.line_spent', `${fmt(spent)} spent`, exp.name || catName, catName)" in app
          and "'@' + parentName)" in app and "ev.target.closest('[data-fig-cat]')" in ex
          and 'See the transactions' in fn and 'showFigTxns(el)' in intent and 'function _askBudgetCat(' in app)
    check('s248 E5 the category report\'s total, highest and lowest months and each merchant open their grid, from the '
          'list the report adds up; a merchant\'s name (the bank\'s words) opens a grid but never reaches the AI',
          'const txns = _rcCatTxns(cat, moRange);' in app and "gwFig('rc.cat_total', fmt(total), cat, null, { cat, from, to })" in app
          and "_figGridAttr({ cat, from, to, merchant: name })" in app and 'data-fig="${key}"' in ex
          and "gwFig('rc.cat_total'" in app and 'merchant: name' in app
          and not re.search(r"gwFig\([^)]*merchant", app))
    grid = ex[ex.index('function showFigTxns(el) {'):ex.index("document.addEventListener('click'")]
    check('s248 E5 the grid lists each transaction - date, where, account, category, amount - with the count and total, '
          'and says whether that total is the page\'s figure',
          all(h in grid for h in ('>Date<', '>Where<', '>Account<', '>Category<', '>Amount<', 'Total - ${rows.length} transaction'))
          and 'The same ${fmt(total)} the page shows' in grid and 'The page shows ${esc(shown)}; these add up to' in grid
          and 'Bank says:' in grid)

    fixed = ex[ex.index('const EXPLAIN_FIXED_ONLY = {'):ex.index('const EXPLAIN_KINDS = {')]
    check('s248 E6 Health and the Ledger get the fixed words only (health stays out of the AI; the Ledger is bank wording)',
          'health:' in fixed and 'ledger:' in fixed and 'health:' not in ex[ex.index('const EXPLAIN_KINDS = {'):ex.index('const EXPLAIN_SYSTEM')]
          and 'if (EXPLAIN_FIXED_ONLY[name]) {' in fn and 'if (!EXPLAIN_KINDS[name] || !aiEnabled()) {' in fn)
    check('s248 E6 nothing is saved or changed: no write, no storage',
          not re.search(r'API\.(post|put|patch|delete)\(', ex) and 'localStorage' not in ex)
