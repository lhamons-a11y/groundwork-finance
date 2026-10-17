"""Item 90 (gw 2.0/RESERVE_AWARE_DATES.md; Rob 2026-10-16: "I approve D1-D7 as recommended. Build item 90.").

    D1  every payoff date follows the choice: the page's one route (/api/debt/simulate, all 32 page calculations) and
        the server's engines, both sides of a what-if alike - one engine, so the two cannot disagree
    D2  the schedule is worked out fresh per request from the gap still to fill; it shortens as the reserve fills
    D3  no choice, "after", no target or a full reserve: every date identical to today's
    D4  a reserve-aware date says so: the line under the Debt Payoff date, and an input line where inputs are listed
    D5  item 88's own comparison is asked without the choice (the one sanctioned opt-out)
    D6  nothing is written by the hook; trophies read no projected date
"""
import ast
import json
import math
from datetime import date, timedelta


def run(ctx):
    check, c, H, HJ, BASE = ctx.check, ctx.c, ctx.H, ctx.HJ, ctx.BASE
    import server
    from core import consequence as cq
    from core import futures, health_reserve as hr
    from core.consequence import Card, simulate_payoff
    from core.database import (Account, AppSetting, HealthPlan, HealthPlanOperation, HealthPlanReading,
                               HealthPlanTermVersion, ReserveAllocation, ReserveTarget, Transaction, db_session)

    post = lambda path, body: c.post(path, headers=HJ, data=json.dumps(body))
    data = lambda r: (r.get_json() or {}).get('data')
    today = date.today()
    raw = [{'id': 's230a', 'name': 'Visa', 'balance': 6000, 'rate': 24, 'minimum': 150},
           {'id': 's230b', 'name': 'Store', 'balance': 2000, 'rate': 8, 'minimum': 50}]
    cards = [Card(balance=r['balance'], rate=r['rate'], minimum=r['minimum'], name=r['name']) for r in raw]
    budget = 600
    tk = today.strftime('%Y-%m')
    page = lambda: data(post('/api/debt/simulate', {'cards': raw, 'budget': budget, 'extra': 0, 'strategy': 'avalanche'}))['result']
    base = simulate_payoff(cards, budget, today_key=tk, start_month=tk)

    def clean():
        with db_session() as s:
            for m in (ReserveAllocation, ReserveTarget, HealthPlanReading, HealthPlanOperation, HealthPlanTermVersion, HealthPlan):
                s.query(m).delete()
            s.query(AppSetting).filter(AppSetting.key.in_(('reserve_account_json', 'reserve_order_json'))).delete(synchronize_session=False)
            s.commit()
    clean()
    made = []
    real = server._consequence_inputs
    server._consequence_inputs = lambda session: (cards, budget, 'avalanche', [])
    try:
        # ── D3: nothing chosen ────────────────────────────────────────────────
        p0 = page()
        check('s230 D3 with no choice the page\'s date is exactly today\'s engine answer',
              p0['months'] == base['months'] and p0['totalInterest'] == base['total_interest'])
        post('/api/accounts/health-plans', {'name': 'S230 Plan', 'effective_from': f'{today.year}-01-01',
                                            'effective_to': f'{today.year}-12-31', 'oop_max': 3000})
        with db_session() as s:
            sav = Account(name='S230 Savings', type='savings', is_active=True)
            s.add(sav); s.commit(); made.append(sav.id); sav_id = sav.id
        post('/api/accounts/health-reserve/reserved', {'amount': 0, 'account_id': sav_id})
        post('/api/accounts/health-reserve/choice', {'choice': 'after'})
        check('s230 D3 "after" leaves every date as it is', page()['months'] == base['months'])

        # ── D1 / D2: before ───────────────────────────────────────────────────
        post('/api/accounts/health-reserve/choice', {'choice': 'before'})
        extra = budget - 200
        n = math.ceil(3000 / extra)
        want = simulate_payoff(cards, budget, today_key=tk, start_month=tk, extra_schedule=[-extra] * n)
        p1 = page()
        check('s230 D1 "before": the page\'s date is the engine with the reserve\'s schedule (one engine, one answer)',
              p1['months'] == want['months'] and p1['totalInterest'] == want['total_interest'] and p1['months'] > base['months'])
        st = data(c.get('/api/accounts/health-reserve', headers=H))
        rows = {r['key']: r for r in st['options']['options']}
        check('s230 D5 item 88\'s card still compares against today\'s plan ("after" unchanged by the choice)',
              rows['after']['debt_months'] == base['months'] and rows['before']['debt_months'] == want['months'])
        check('s230 D4 the date says so: one line, how much and until when',
              st['applied'] and st['applied']['line'] == f"Includes your health reserve: ${extra:,.2f} a month until "
                                                         f"{hr.month_label(n)}.")
        post('/api/accounts/health-reserve/reserved', {'amount': 1800})
        n2 = math.ceil(1200 / extra)
        p2 = page()
        check('s230 D2 raising the reserve shortens the schedule by itself (worked out fresh, nothing stored)',
              p2['months'] == simulate_payoff(cards, budget, today_key=tk, start_month=tk, extra_schedule=[-extra] * n2)['months']
              and p2['months'] <= p1['months'])

        # ── D1: alongside, and both sides of a what-if ───────────────────────
        post('/api/accounts/health-reserve/choice', {'choice': 'alongside', 'monthly': 100})
        n3 = math.ceil(1200 / 100)
        p3 = page()
        check('s230 D1 "alongside": the person\'s amount for the months the gap needs',
              p3['months'] == simulate_payoff(cards, budget, today_key=tk, start_month=tk, extra_schedule=[-100] * n3)['months'])
        what_if = data(post('/api/debt/simulate', {'cards': raw, 'budget': budget, 'extra': 100, 'strategy': 'avalanche'}))['result']
        check('s230 D1 a what-if gets the schedule too, so its difference stays like for like',
              what_if['months'] == simulate_payoff(cards, budget + 100, today_key=tk, start_month=tk,
                                                   extra_schedule=[-100] * n3)['months'])

        # ── D4: a surface that lists its inputs ───────────────────────────────
        tok = cq.RESERVE_PLAN.set({'choice': 'alongside', 'monthly': 100, 'gap': 1200})
        try:
            line = hr.input_line(cards, budget)
        finally:
            cq.RESERVE_PLAN.reset(tok)
        fsrc = (BASE / 'core' / 'futures.py').read_text(encoding='utf-8') + (BASE / 'core' / 'income_change.py').read_text(encoding='utf-8')
        check('s230 D4 possible futures and income changes list the reserve with their inputs',
              line and line['label'] == 'Health reserve: $100.00 a month for 12 months (your choice).'
              and fsrc.count("input_line(") == 2)

        # ── D3 again: a full reserve, and no target ──────────────────────────
        post('/api/accounts/health-reserve/reserved', {'amount': 3000})
        check('s230 D3 a full reserve changes nothing', page()['months'] == base['months'])
        post('/api/accounts/health-reserve/reserved', {'amount': 0})
        post('/api/accounts/health-reserve/target', {'basis': ''})
        check('s230 D3 no target changes nothing', page()['months'] == base['months'])
        check('s230 D3 outside a request (tests, scripts) the engine is as before',
              cq.RESERVE_PLAN.get() is None and simulate_payoff(cards, budget)['months'] == simulate_payoff(cards, budget)['months'])

        # ── D5 / D6: the only opt-out, and nothing written ───────────────────
        callers = set()
        for path in ['server.py'] + [f'core/{p.name}' for p in sorted((BASE / 'core').glob('*.py'))]:
            tree = ast.parse((BASE / path).read_text(encoding='utf-8'))
            for fn in ast.walk(tree):
                if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for nd in ast.walk(fn):
                        if isinstance(nd, ast.Call) and (getattr(nd.func, 'id', None) or getattr(nd.func, 'attr', None)) == 'no_reserve':
                            callers.add((path, fn.name))
        check(f's230 D5 no_reserve() is used only by item 88\'s comparison ({sorted(callers)})',
              callers == {('core/health_reserve.py', 'options')})
        csrc = (BASE / 'core' / 'consequence.py').read_text(encoding='utf-8')
        hook = csrc.split('# ── Item 90')[1].split('\n@dataclass')[0]
        trophies = (BASE / 'core' / 'trophies.py').read_text(encoding='utf-8')
        check('s230 D6 the hook writes nothing, and trophies read no projected date',
              'session' not in hook and 'commit' not in hook and 'simulate_payoff' not in trophies)
    finally:
        server._consequence_inputs = real
        with db_session() as s:
            if made:
                s.query(Transaction).filter(Transaction.account_id.in_(made)).delete(synchronize_session=False)
                s.query(Account).filter(Account.id.in_(made)).delete(synchronize_session=False)
            s.commit()
        clean()
