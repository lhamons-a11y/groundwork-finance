"""Item 89 (gw 2.0/CARE_NEVER_A_LEVER.md; Rob 2026-10-16: "I approve C1-C4 and U1-U5 as recommended", "Build item 89").

    C1  protected and uncertain care is counted, described, and never offered as a cut or priced in months
    C2  every function that calls the lever machinery is listed in LEVER_SURFACES (scanned against the code)
    C3  the sweep: a record where an uncertain category is the biggest, most flexible spending, through the engine
        and the real routes; a mutation that lets it through is caught
    C4  the narrator's findings (/api/debt/teaching) carry no price for it
    U1  three outcomes; U2 the counterparty signals, a supermarket's weak signal only on single rows (measured);
    U3  uncertain = protected for every lever; U4 only the person's answer settles it, the floor is never overridden;
    U5  the uncertain reading is never stored; a household with no health signals sees exactly the floor, as before
"""
import ast
import json
import re
from datetime import date, timedelta

MONTHS_RE = re.compile(r'\d+\s*month', re.I)


def run(ctx):
    check, c, H, HJ, BASE = ctx.check, ctx.c, ctx.H, ctx.HJ, ctx.BASE
    import server
    from core import care_status as cs
    from core import solution as sol
    from core.consequence import Card
    from core.database import CareAnswer, Category, Transaction, db_session
    from core.income_change import budget_follows

    post = lambda path, body: c.post(path, headers=HJ, data=json.dumps(body))
    data = lambda r: (r.get_json() or {}).get('data')
    W, D, RX, SH = 'S228 Wellness Studio', 'S228 Dining Out', 'Prescriptions', 'S228 Shopping'
    today = date.today()

    # ── a record: an uncertain category (a clinic payment in it), a control, a supermarket row ─────────────
    with db_session() as s:
        ids = {}
        for n in (W, D, SH):
            cat = s.query(Category).filter_by(name=n).first() or Category(name=n, type='expense')
            s.add(cat); s.flush(); ids[n] = cat.id
        s.query(CareAnswer).filter(CareAnswer.category_id.in_(list(ids.values()))).delete(synchronize_session=False)
        rows = [Transaction(date=today - timedelta(days=5), description='MILLBROOK FAMILY CLINIC 4471', amount=900,
                            type='debit', category_id=ids[W], source='csv'),
                Transaction(date=today - timedelta(days=4), description='S228 BISTRO', amount=900, type='debit',
                            category_id=ids[D], source='csv'),
                Transaction(date=today - timedelta(days=3), description='WALMART SUPERCENTER', amount=60, type='debit',
                            category_id=ids[SH], source='csv')]
        s.add_all(rows); s.commit()
        row_ids = [t.id for t in rows]
        cs.refresh(s, force=True)

    # ── U1 / U2 ───────────────────────────────────────────────────────────────
    check('s228 U1 three outcomes: the floor protected, a clinic payment makes its category uncertain, a control not matched',
          cs.status(RX) == cs.PROTECTED and cs.status(W) == cs.UNCERTAIN and cs.status(D) == cs.NOT_MATCHED)
    check('s228 U2 a supermarket row alone does not make a category uncertain (measured: it would have taken Shopping)',
          cs.status(SH) == cs.NOT_MATCHED)
    check('s228 U2 ... but on a single row it is one weak signal, and that row is never a lever',
          cs.row_never_lever('WALMART PHARMACY 12', '', '', SH) and not cs.row_never_lever('S228 BISTRO', '', '', D))
    check('s228 U2 a health card code on a row is a signal', cs.row_never_lever('ACME', '', '8011', D))
    with db_session() as s:
        other = s.query(Category).filter_by(name='Other').first()
        if other:
            t = Transaction(date=today - timedelta(days=2), description='S228 RIVER CLINIC', amount=50, type='debit',
                            category_id=other.id, source='csv')
            s.add(t); s.commit(); row_ids.append(t.id)
            cs.refresh(s, force=True)
    check('s228 U2 a catch-all ("Other") is never asked about as a whole; its clinic payment is judged on its own row',
          cs.status('Other') == cs.NOT_MATCHED and cs.row_never_lever('S228 RIVER CLINIC', '', '', 'Other'))
    with db_session() as s:
        qs = {q['name']: q for q in cs.questions(s)}
    check('s228 U4 the question names the category and why', W in qs and 'pharmacy, clinic' in qs[W]['why'] and D not in qs)

    # ── C3 / U3: the engine, every registered helper ─────────────────────────
    cards = [Card(balance=8000, rate=22, minimum=200, name='Visa'), Card(balance=3000, rate=6, minimum=75, name='Store')]
    budget = 775
    cats = [{'name': W, 'budgeted': 100, 'min_observed': 260, 'max_observed': 300, 'months_observed': 6},   # over, every month
            {'name': D, 'budgeted': 100, 'min_observed': 260, 'max_observed': 300, 'months_observed': 6},
            {'name': RX, 'budgeted': 100, 'min_observed': 260, 'max_observed': 300, 'months_observed': 6}]
    head = [{'name': W, 'budgeted': 900, 'max_observed': 200, 'months_observed': 6},
            {'name': D, 'budgeted': 900, 'max_observed': 200, 'months_observed': 6}]
    rec = [{'name': 'Monthly class', 'monthly': 120, 'category': W}, {'name': 'Wine club', 'monthly': 120, 'category': D},
           {'name': 'WALMART PHARMACY', 'monthly': 40, 'category': SH}]
    flex = [{'name': W, 'willingness': {'stance': 'flexible', 'source': 'declared'}},
            {'name': D, 'willingness': {'stance': 'flexible', 'source': 'declared'}}]

    def engine_clean():
        names = lambda xs: {x.get('name') for x in xs}
        bp = {r['name']: r for r in sol.budget_pressure(cards, budget, categories=[dict(x) for x in cats])}
        lines = [{'id': 1, 'name': W, 'category': W, 'amount': 600}, {'id': 2, 'name': D, 'category': D, 'amount': 600}]
        follows = json.dumps(budget_follows(lines, 300, {W.lower(): {'stance': 'flexible', 'source': 'declared'}, D.lower(): {'stance': 'flexible', 'source': 'declared'}}))
        paths = json.dumps(sol.solve_one_time_cost(cards, budget, 2500, categories=[dict(x) for x in head],
                                                   recurring=[dict(x) for x in rec], demonstrated=flex), default=str)
        return {
            'headroom': W not in names(sol._headroom(head)) and D in names(sol._headroom(head)),
            'trims': {'Monthly class', 'WALMART PHARMACY'}.isdisjoint(names(sol._trims(rec))) and 'Wine club' in names(sol._trims(rec)),
            'flexible': W not in names(sol._flexible_named(flex)) and D in names(sol._flexible_named(flex)),
            'pressure': W in bp and bp[W]['priced'] is False and bp[W]['months_cost'] is None
                        and D in bp and bp[D]['priced'] is True,
            'follows': W not in follows and D in follows,
            'paths': W not in paths and 'Monthly class' not in paths,
        }

    eng = engine_clean()
    check(f's228 C3 the engine: no lever names the uncertain category, the control still does ({eng})', all(eng.values()))

    # ── C3 / C4: the real routes ──────────────────────────────────────────────
    real = (server._consequence_inputs, server.reallocation_candidates, server.trim_candidates)
    server._consequence_inputs = lambda session: (cards, budget, 'avalanche', [])
    server.reallocation_candidates = lambda session, *a, **k: [dict(x) for x in cats]
    server.trim_candidates = lambda session, *a, **k: []
    try:
        nl = set(data(c.get('/api/budget/not-levers', headers=H))['not_levers'])
        bp = {r['name']: r for r in (data(c.get('/api/budget/pressure', headers=H)) or {}).get('pressure', [])
              if isinstance(r, dict)}
        lesson = json.dumps(data(c.get('/api/transactions/lesson', headers=H)))
        teach = json.dumps(data(c.get('/api/debt/teaching', headers=H)))
        offers = json.dumps(data(c.get('/api/byb/offers', headers=H)))
        nxt = json.dumps(data(c.get('/api/proactive/next', headers=H)))
        check('s228 C3 the page\'s one list (/api/budget/not-levers) holds the uncertain category, not the control',
              W in nl and D not in nl)
        check('s228 C3 the Budget page\'s pressure route never prices it', W not in bp or bp[W].get('priced') is False)
        check('s228 C3 the Ledger lesson, Before You Buy and the dashboard brake never name it',
              W not in lesson and 'MILLBROOK FAMILY CLINIC' not in lesson and W not in offers and W not in nxt)
        wt = [m.start() for m in re.finditer(re.escape(W), teach)]
        check('s228 C4 the narrator\'s findings carry no months for it',
              all(not MONTHS_RE.search(teach[i:i + 200].split('}')[0]) for i in wt))
    finally:
        server._consequence_inputs, server.reallocation_candidates, server.trim_candidates = real

    # ── C3: a mutation the sweep must catch ───────────────────────────────────
    keep = cs.never_lever
    cs.never_lever = lambda name: keep(name) and name != W
    try:
        caught = not all(engine_clean().values())
    finally:
        cs.never_lever = keep
    check('s228 C3 mutation caught: the uncertain category let into the lever set', caught)

    # ── U4: the answer settles it; the floor is never overridden ─────────────
    rx_id = None
    with db_session() as s:
        rx_cat = s.query(Category).filter_by(name=RX).first()
        rx_id = rx_cat.id if rx_cat else None
    r_no = post('/api/accounts/care-questions', {'category_id': ids[W], 'answer': 'no'})
    check('s228 U4 "No" makes it not matched: offered like any category again, and no longer asked',
          r_no.status_code == 200 and cs.status(W) == cs.NOT_MATCHED and W not in {q['name'] for q in data(r_no)['questions']}
          and W in {x['name'] for x in sol._headroom(head)})
    post('/api/accounts/care-questions', {'category_id': ids[W], 'answer': 'yes'})
    check('s228 U4 "Yes" makes it protected; the newest answer is current', cs.status(W) == cs.PROTECTED)
    got = {a['name']: a['answer'] for a in data(c.get('/api/accounts/care-questions', headers=H))['answered']}
    check('s228 U4 the answers on record are listed (newest per category), so one can be changed', got.get(W) == 'yes')
    if rx_id:
        post('/api/accounts/care-questions', {'category_id': rx_id, 'answer': 'no'})
        check('s228 U4 an answer never takes a category off the necessity floor', cs.status(RX) == cs.PROTECTED)
    bad = post('/api/accounts/care-questions', {'category_id': ids[W], 'answer': 'maybe'})
    check('s228 U4 only yes or no is accepted', bad.status_code == 400)

    # ── U5: never stored; nothing changes for a household with no signals ────
    with db_session() as s:
        cols = [r[1] for r in s.execute(__import__('sqlalchemy').text('PRAGMA table_info(care_answers)')).fetchall()]
    src = (BASE / 'core' / 'care_status.py').read_text(encoding='utf-8')
    check('s228 U5 only the answer is stored - no reason, no uncertain flag - and nothing here logs',
          set(cols) == {'id', 'category_id', 'answer', 'created_at'} and 'logging' not in src and 'logger' not in src)
    names = ['Groceries', 'Rent / Mortgage', 'Dining Out', 'Streaming', 'Doctor / Co-pays', 'Water', 'Hospitality',
             'Health Club', 'Medicine', 'Entertainment', 'Clothing']
    with db_session() as s:
        s.query(CareAnswer).filter(CareAnswer.category_id.in_(list(ids.values()))).delete(synchronize_session=False)
        s.query(Transaction).filter(Transaction.id.in_(row_ids)).delete(synchronize_session=False)
        s.commit()
        cs.refresh(s, force=True)
    check('s228 U5 with no health signals the rule is exactly the floor, as before item 89',
          all(cs.never_lever(n) == sol.is_protected(n) for n in names))

    # ── C2: every caller of the machinery is listed ──────────────────────────
    found = set()
    for path in ['server.py'] + [f'core/{p.name}' for p in sorted((BASE / 'core').glob('*.py'))]:
        if path in ('core/care_status.py', 'core/health_boundary.py', 'core/classification.py'):
            continue
        tree = ast.parse((BASE / path).read_text(encoding='utf-8'))
        for fn in ast.walk(tree):
            if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for n in ast.walk(fn):
                    if isinstance(n, ast.Call) and (getattr(n.func, 'id', None) or getattr(n.func, 'attr', None)) in cs.MACHINERY:
                        found.add((path, fn.name))
                        break
    missing = sorted(found - set(cs.LEVER_SURFACES))
    stale = sorted(k for k in cs.LEVER_SURFACES if k not in found)
    check(f's228 C2 every function that calls the lever machinery is listed ({missing})', not missing)
    check(f's228 C2 nothing listed that no longer calls it ({stale})', not stale)
    lever_src = ''.join((BASE / f).read_text(encoding='utf-8') for f in ('core/solution.py', 'core/willingness.py', 'core/income_change.py'))
    check('s228 C1 no lever decision reads the floor alone any more (is_protected only where it labels the floor)',
          len(re.findall(r'(?<!def )\bis_protected\(', lever_src)) == 0)

    with db_session() as s:
        s.query(Category).filter(Category.id.in_(list(ids.values()))).delete(synchronize_session=False)
        s.commit()
        cs.refresh(s, force=True)
