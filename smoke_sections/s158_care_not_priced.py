"""Necessary care is never priced in months (gw 2.0/CARE_NOT_PRICED.md, item 46 = item 45 H1; Rob 2026-10-08: "H1 is a
correctness fix ... The tests should verify the actual rendered conclusions, not merely that a category is marked
`protected`").

Each check runs the real path to the user: the route (or the dashboard's candidate builder) on a ledger that holds a
protected item, then the surface's own renderer on what came back. The same is run against an unprotected item, to
show the surfaces still price everything else.

    C1  the charge lesson skips necessary care - a protected category, or an uncategorised charge named like it -
        on the Ledger, the dashboard and the report
    C2  an overspent protected category is described ("the budget is set $X/mo below what it costs") and never priced:
        no months or interest on the Budget page or in the report, and never the dashboard brake
    C3  the narrator's findings carry no months or interest for it
"""
import json
import re
import shutil
import subprocess
from datetime import date, timedelta

MONTHS_RE = re.compile(r'\d+\s*month', re.I)


def _fn(src, name):
    m = re.search(r'\n\s*function ' + name + r'\(.*?\n  \}\n', src, re.S)
    return m.group(0) if m else ''


def _node(node, src, call, data):
    runner = r'''
const esc = s => String(s); const escJs = esc; const fmt = n => '$' + Number(n).toFixed(2);
const _joinNames = a => (a || []).map(x => x.name || x).join(', ');
const g = () => null; const _gwErr = () => () => {}; const _payoffDateLabel = () => 'Jan 2028';
''' + src + '\nconsole.log(JSON.stringify(' + call + '(JSON.parse(process.argv[1]))));'
    p = subprocess.run([node, '-e', runner, json.dumps(data)], capture_output=True, text=True, encoding='utf-8', timeout=60)
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        print('        node stderr:', p.stderr[-600:])
        return None


def run(ctx):
    check, c, H, BASE = ctx.check, ctx.c, ctx.H, ctx.BASE
    import server
    from core.consequence import Card
    from core.database import Transaction, Category, db_session

    cards = [Card(balance=8000, rate=22, minimum=200, name='Visa'),
             Card(balance=3000, rate=6, minimum=75, name='Store')]
    budget = 775
    cats = [
        {'name': 'Prescriptions', 'budgeted': 100, 'min_observed': 260, 'max_observed': 300, 'months_observed': 6},
        {'name': 'Dining Out', 'budgeted': 100, 'min_observed': 240, 'max_observed': 280, 'months_observed': 6},
        {'name': 'Shopping', 'budgeted': 500, 'min_observed': 100, 'max_observed': 150, 'months_observed': 6},
    ]
    real = (server._consequence_inputs, server.reallocation_candidates, server.trim_candidates)
    server._consequence_inputs = lambda session: (cards, budget, 'avalanche', [])
    server.reallocation_candidates = lambda session, *a, **k: [dict(x) for x in cats]
    server.trim_candidates = lambda session, *a, **k: []
    added = []
    try:
        # ── C2: the engine ──
        from core.solution import budget_pressure
        rows = {r['name']: r for r in budget_pressure(cards, budget, categories=[dict(x) for x in cats])}
        rx, dine = rows.get('Prescriptions'), rows.get('Dining Out')
        check('s158 C2 an overspent protected category is returned, described, and carries no price',
              rx is not None and rx['protected'] and rx['priced'] is False and rx['months_cost'] is None
              and rx['interest_cost'] is None and rx['monthly'] == 160.0)
        check('s158 C2 an unprotected overspend is still priced in months and interest',
              dine is not None and dine['priced'] and dine['months_cost'] >= 1 and dine['interest_cost'] > 0)

        node = shutil.which('node')
        check('s158 node is available to run the renderers (skip those if not)', bool(node))
        budget_js = (BASE / 'static/js/teaching/budget.js').read_text(encoding='utf-8')
        reports_js = (BASE / 'static/js/teaching/reports.js').read_text(encoding='utf-8')
        ledger_js = (BASE / 'static/js/teaching/ledger.js').read_text(encoding='utf-8')

        # ── C2: the Budget page, route to rendered text ──
        bp = c.get('/api/budget/pressure', headers=H).get_json()['data']
        if node:
            src = _fn(budget_js, '_budgetPressureHTML')
            html = _node(node, src, '_budgetPressureHTML', bp) or ''
            text = re.sub(r'<[^>]+>', ' ', html)
            rx_part = text.split('Prescriptions', 1)[1].split('Dining Out', 1)[0] if 'Prescriptions' in text else ''
            dine_part = text.split('Dining Out', 1)[1] if 'Dining Out' in text else ''
            check('s158 C2 the Budget page says the Prescriptions budget is set below what it costs, with no months or interest',
                  'below what it costs' in rx_part and not MONTHS_RE.search(rx_part.replace('in 6 months', ''))
                  and 'debt-free' not in rx_part and 'interest' not in rx_part)
            check('s158 C2 the Budget page still prices Dining Out in months on the debt-free date',
                  'debt-free date' in dine_part and MONTHS_RE.search(dine_part) is not None)

        # ── C1 + C2 + C3: the report, route to rendered sentences and the narrator's findings ──
        rep = c.get('/api/debt/teaching', headers=H).get_json()['data']
        findings = rep.get('findings') or []
        over = [f for f in findings if f.get('kind') == 'overspend']
        if over and over[0].get('subject') == 'Prescriptions':
            check('s158 C3 the report\'s finding for a protected overspend carries no months or interest for the narrator',
                  over[0].get('months') is None and over[0].get('interest') is None)
        else:
            check('s158 C3 the report\'s finding for a protected overspend carries no months or interest for the narrator',
                  all(f.get('months') is None for f in over if f.get('protected')))
        app_src = ctx.app_src
        check('s158 C3 the narrator block states months and interest only when a finding has them',
              "if (f.months != null)" in app_src and "if (f.interest != null)" in app_src)
        if node:
            src = _fn(reports_js, '_rcTeachingSentence')
            prot = _node(node, src, '_rcTeachingSentence',
                         {'kind': 'overspend', 'subject': 'Prescriptions', 'protected': True, 'monthly': 160,
                          'months': None, 'interest': None}) or ''
            unprot = _node(node, src, '_rcTeachingSentence',
                           {'kind': 'overspend', 'subject': 'Dining Out', 'protected': False, 'monthly': 140,
                            'months': 2, 'interest': 210.5}) or ''
            check('s158 C2 the report describes a protected overspend without months or interest',
                  'below what it' in prot and not MONTHS_RE.search(prot) and 'interest' not in prot)
            check('s158 C2 the report still prices an unprotected overspend', '2 months' in prot + unprot and 'interest' in unprot)

        # ── C2: the dashboard brake ──

        with db_session() as session:
            cands = server._proactive_candidates(session, cards, budget, 'avalanche')
        # A large charge is a brake too (its key starts "charge:"), and other sections leave charges in the gate's
        # database - so the overspend brake is found by its own key, not by its place in the list.
        brakes = [x for x in cands if x.get('kind') == 'brake']
        over_brakes = [x for x in brakes if str(x.get('key', '')).startswith('overspend:')]
        check('s158 C2 a protected category is never the dashboard brake; the priced overspend is',
              all(b.get('category') != 'Prescriptions' for b in brakes)
              and [b['category'] for b in over_brakes] == ['Dining Out'])

        # ── C1: the charge lesson, on real transactions ──
        with db_session() as session:
            def cat_id(name):
                row = session.query(Category).filter_by(name=name).first()
                if not row:
                    row = Category(name=name, type='expense')
                    session.add(row)
                    session.flush()
                return row.id
            d = date.today() - timedelta(days=5)
            txs = [
                Transaction(date=d, description='ST MARYS HOSPITAL', merchant="St. Mary's Hospital", amount=4200.0,
                            type='debit', category_id=cat_id('Healthcare')),
                Transaction(date=d, description='CVS PHARMACY #1234', merchant='CVS Pharmacy', amount=3900.0,
                            type='debit', category_id=None),
                Transaction(date=d, description='BEST BUY 0042', merchant='Best Buy', amount=2600.0,
                            type='debit', category_id=cat_id('Shopping')),
            ]
            session.add_all(txs)
            session.commit()
            added = [t.id for t in txs]
        les = c.get('/api/transactions/lesson', headers=H).get_json()['data']
        # The two care charges are the largest in the window, so if either could be the lesson it would be. Other
        # sections may leave larger non-care charges in the gate's database; the rule is about care, not Best Buy.
        care = ("St. Mary's Hospital", 'CVS Pharmacy')
        check('s158 C1 the Ledger lesson skips the hospital charge (protected category) and the uncategorised pharmacy charge',
              les.get('lesson') is not None and (les.get('charge') or {}).get('name') not in care)
        if node and les.get('lesson'):
            src = _fn(ledger_js, '_ledgerLessonHTML')
            html = re.sub(r'<[^>]+>', ' ', _node(node, src, '_ledgerLessonHTML', les) or '')
            check('s158 C1 what the Ledger shows names no care charge',
                  bool(html.strip()) and 'Hospital' not in html and 'CVS' not in html)
        rep = c.get('/api/debt/teaching', headers=H).get_json()['data']
        charge = [f for f in rep.get('findings') or [] if f.get('kind') == 'charge']
        check('s158 C1 the report\'s charge finding is not a care charge', charge and charge[0]['subject'] not in care)
        with db_session() as session:
            cands = server._proactive_candidates(session, cards, budget, 'avalanche')
        ch = [x for x in cands if str(x.get('key', '')).startswith('charge:')]
        check('s158 C1 the dashboard\'s charge item is not a care charge', ch and not any(name in ch[0]['key'] for name in care))

        # ── mutations: each must break a check above ──
        sp = (BASE / 'server.py').read_text(encoding='utf-8')
        sol = (BASE / 'core/solution.py').read_text(encoding='utf-8')
        guard = "if (cat and never_lever(cat.name)) or (not cat and row_never_lever(t.merchant, t.description, t.mcc)):"   # item 89
        brake = "if o['priced']][:1]:"
        price = "priced = not over['protected']"
        page = "const cost = !o.priced ? ''"
        check('s158 mutations: the charge guard, the brake filter, the engine\'s refusal to price and the page\'s are each '
              'present exactly once (removing any one is what the checks above catch)',
              sp.count(guard) == 1 and sp.count(brake) == 1 and sol.count(price) == 1 and budget_js.count(page) == 1)
    finally:
        server._consequence_inputs, server.reallocation_candidates, server.trim_candidates = real
        if added:
            with db_session() as session:
                session.query(Transaction).filter(Transaction.id.in_(added)).delete(synchronize_session=False)
                session.commit()
