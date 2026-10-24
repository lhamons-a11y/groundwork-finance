"""The simulated user panel's issues (groundwork-panel-sim, 2026-10-24), each fixed and held here.

    I-01/I-04  debt payments are budgeted wherever they are spent: one rule (_debt_month_plan, _debtMonthPlan) for the
               check-in, Before You Buy, the income page and the Budget page - the payoff plan, never below the
               minimums, or the minimums when no plan was saved; a payment on a debt is never offered as a purchase
    I-03/I-06  a payoff that can't be dated is said (below the minimums by $X, or never clearing), never a 500 or a
               blank; Debt Payoff offers "use my minimums"; the budget typed there is the one the server reads
"""
import json
from datetime import date, timedelta


def run(ctx):
    check, c, H = ctx.check, ctx.c, ctx.H
    import server
    from core import income_change as ic
    from core.database import AppSetting, BudgetItem, Category, DebtAccount, Transaction, db_session

    # ── I-01 / I-04: one rule for a month's debt payments ───────────────────────────────────────────────────────
    with db_session() as s:
        others = [d.id for d in s.query(DebtAccount).filter_by(is_active=True).all()]
        s.query(DebtAccount).filter(DebtAccount.id.in_(others)).update({'is_active': False}, synchronize_session=False)
        mb = s.query(AppSetting).filter_by(key='monthly_budget').first()
        saved_mb = mb.value if mb else None
        if mb:
            s.delete(mb)
        loan = DebtAccount(name='S260 Auto Loan', current_balance=5000.0, begin_balance=6000.0, interest_rate=6.0,
                           minimum_payment=260.0, is_active=True)
        card = DebtAccount(name='S260 Visa', current_balance=1200.0, begin_balance=1500.0, interest_rate=24.0,
                           minimum_payment=40.0, is_active=True)
        done = DebtAccount(name='S260 Paid Card', current_balance=0.0, begin_balance=900.0, interest_rate=20.0,
                           minimum_payment=25.0, is_active=True)
        s.add_all([loan, card, done])
        s.commit()

    def plan():
        with db_session() as s:
            return server._debt_month_plan(s)

    def set_mb(v):
        with db_session() as s:
            row = s.query(AppSetting).filter_by(key='monthly_budget').first()
            if v is None:
                if row:
                    s.delete(row)
            elif row:
                row.value = str(v)
            else:
                s.add(AppSetting(key='monthly_budget', value=str(v)))
            s.commit()

    p0 = plan()
    set_mb(450)
    p1 = plan()
    set_mb(200)
    p2 = plan()
    check(f"s260 I-01 a month's debt payments: the minimums with no saved plan (never the 1500 default), the plan when "
          f"saved, the minimums when the plan is below them; a paid-off debt owes nothing ({p0['amount']}, {p1['amount']}, {p2['amount']})",
          p0 == {'amount': 300.0, 'minimums': 300.0, 'plan': None, 'basis': 'minimums'}
          and p1['amount'] == 450.0 and p1['basis'] == 'plan'
          and p2['amount'] == 300.0 and p2['basis'] == 'minimums_above_plan')
    set_mb(450)

    ck = (c.get('/api/checkin', headers=H).get_json() or {}).get('data') or {}
    bp = ck.get('budget_parts') or {}
    check(f"s260 I-01 the check-in measures spending against spending lines plus debt payments, and says so ({bp})",
          bp.get('debt') == 450.0 and bp.get('debt_basis') == 'plan'
          and abs((ck.get('month') or {}).get('budget', 0) - (bp.get('spending', 0) + 450.0)) < 0.01
          and '${fmt(bp.debt)} of debt payments' in ctx.app_src)

    with db_session() as s:
        im = server._byb_impact(s)
        items = s.query(BudgetItem).filter_by(is_active=True).all()
        amts = server.budget_month_amounts(s)
        income = sum(float(i.amount or 0) for i in items if i.type == 'income')
        outflow = sum((amts.get(i.id) or {}).get('month_amount', i.amount or 0) or 0 for i in items if i.type == 'expense')
    check(f"s260 I-04 Before You Buy's 'left each month' takes off the debt payments, as its own calculator does ({im['left_now']})",
          abs(im['left_now'] - round(income - outflow - 450.0, 2)) < 0.01)

    today = date.today()
    debt_cat = None
    with db_session() as s:
        debt_cat = (s.query(Category).filter_by(name='Debt').first() or Category(name='Debt'))
        s.add(debt_cat)
        s.commit()
        for k in (60, 30, 2):
            d = today - timedelta(days=k)
            s.add(Transaction(date=d, amount=260.0, type='debit', merchant='S260 AUTO LOAN PMT', description='S260 AUTO LOAN PMT'))
            s.add(Transaction(date=d, amount=99.0, type='debit', merchant='S260 LENDER', description='S260 LENDER',
                              category_id=debt_cat.id))
            s.add(Transaction(date=d, amount=45.0, type='debit', merchant='S260 GYM', description='S260 GYM'))
        s.commit()
    offers = ((c.get('/api/byb/offers', headers=H).get_json() or {}).get('data') or {}).get('offers', [])
    names = {o['name'] for o in offers}
    check(f"s260 I-04 a payment on a debt (named for it, or filed under Debt) is not offered as a new purchase; a new "
          f"subscription still is ({sorted(n for n in names if 'S260' in n)})",
          any('S260 GYM' in n for n in names) and not any('AUTO LOAN' in n or 'S260 LENDER' in n for n in names))

    sc = ic.scenarios({'from': 4000.0, 'to': 3000.0, 'month': '2026-09'}, 2600.0, [], {}, [], 0.0, None,
                      debt_payments=450.0)
    sc0 = ic.scenarios({'from': 4000.0, 'to': 3000.0, 'month': '2026-09'}, 2600.0, [], {}, [], 0.0, None)
    check(f"s260 I-04 an income drop's gap counts the debt payments income must also cover ({sc['gap']} vs {sc0['gap']})",
          sc['gap'] == 50.0 and sc0['gap'] == 0.0
          and any(f['label'] == 'Debt payments' for f in sc['scenarios'][0]['figures']))
    check("s260 I-01 the Budget page's planned 'out' and What's Left use the same rule, and say which it is",
          'function _debtMonthPlan()' in ctx.app_src and ctx.app_src.count('_debtMonthPlan().amount') >= 2
          and '(your payoff plan; minimums' in ctx.app_src and "'monthlyBudgetSaved'" in ctx.server_src)

    # ── I-03 / I-06: a payoff that can't be dated is said, with the gap and the way back ─────────────────────────────
    set_mb(200)
    t1 = c.get('/api/debt/teaching', headers=H)
    d1 = (t1.get_json() or {}).get('data') or {}
    with db_session() as s:
        s.query(DebtAccount).filter(DebtAccount.name.in_(['S260 Auto Loan', 'S260 Visa'])).update(
            {'is_active': False}, synchronize_session=False)
        s.add(DebtAccount(name='S260 Big Card', current_balance=100000.0, begin_balance=100000.0, interest_rate=30.0,
                          minimum_payment=2000.0, is_active=True))
        s.commit()
    set_mb(2400)                                  # above the minimums, below the $2,500 a month of interest
    d2 = ((c.get('/api/debt/teaching', headers=H).get_json() or {}).get('data') or {})
    check(f"s260 I-03 a payoff the engine can't date is a reason, not a crash: below the minimums with the gap, or "
          f"never clearing ({t1.status_code} {d1.get('reason')} gap {d1.get('gap')}; {d2.get('reason')})",
          t1.status_code == 200 and d1.get('reason') == 'below_minimums' and d1.get('gap') == 100.0
          and d1.get('findings') == [] and d2.get('reason') == 'never_clears')
    rep = (ctx.BASE / 'static' / 'js' / 'teaching' / 'reports.js').read_text(encoding='utf-8')
    check("s260 I-03/I-06 Reports and Debt Payoff say why there is no date, with the gap and a one-tap 'use my minimums'; "
          "the budget typed on Debt Payoff is the one the server reads",
          "d.reason === 'below_minimums'" in rep and "d.reason === 'never_clears'" in rep
          and '_useMinimumsAsBudget(' in ctx.app_src and 'Use my minimums, ${fmt(totalMin)}' in ctx.app_src
          and 'calculate();_saveDebtBudgetSoon()' in ctx.html_src
          and "API.patch('/api/settings', { monthly_budget: String(v) })" in ctx.app_src)

    # ── I-05: a balance the record brings to $0 is asked about, and $0 is a real balance ────────────────────────────
    from core.database import DebtLedgerEntry
    with db_session() as s:
        s.query(DebtAccount).filter_by(name='S260 Big Card').update({'is_active': False}, synchronize_session=False)
        z = DebtAccount(name='S260 Zero Card', current_balance=0.0, begin_balance=900.0, interest_rate=20.0,
                        minimum_payment=25.0, is_active=True)
        s.add(z)
        s.flush()
        s.add(DebtLedgerEntry(debt_account_id=z.id, entry_type='payment', amount=900.0,
                              entry_date=date.today() - timedelta(days=12), source_type='manual'))
        s.commit()
        zid = z.id
        ser = server.serialize_debt_account(s.get(DebtAccount, zid), s)
    trophies = {t['id']: t for t in ((c.get('/api/trophies', headers=H).get_json() or {}).get('data') or {}).get('trophies', [])}
    zero_open = next((p['value'] for p in (trophies.get('zero') or {}).get('proof') or []
                      if p.get('label') == 'balances still open'), None)
    np = c.post(f'/api/debt/{zid}/not-paid-off', headers=H)
    with db_session() as s:
        ser2 = server.serialize_debt_account(s.get(DebtAccount, zid), s)
    check(f"s260 I-05 a balance brought to $0 and not called paid off is asked about from its last payment's date; "
          f"'not yet' is kept for that zero; the Trophy Room counts $0 as closed ({ser['reached_zero']} "
          f"{ser['zero_since']}; after not yet {ser2['reached_zero']}; open {zero_open})",
          ser['reached_zero'] and ser['zero_since'] == (date.today() - timedelta(days=12)).isoformat()
          and np.status_code == 200 and not ser2['reached_zero'] and zero_open == 0)
    check("s260 I-05 the Debt Payoff row asks 'Is it paid off?' and a yes is dated when it reached $0",
          'function _paidOffAskHTML(c)' in ctx.app_src and "card.paidOffAt = card.zeroSince" in ctx.app_src
          and ctx.app_src.count('${_paidOffAskHTML(c)}') == 2 and 'reachedZero: !!d.reached_zero' in ctx.app_src)

    with db_session() as s:
        s.query(DebtLedgerEntry).filter_by(debt_account_id=zid).delete()
        s.query(DebtAccount).filter(DebtAccount.name.in_(['S260 Big Card', 'S260 Zero Card'])).delete(synchronize_session=False)
        row = s.query(AppSetting).filter_by(key='paid_off_not_yet').first()
        if row:
            s.delete(row)
        s.commit()
    with db_session() as s:
        s.query(Transaction).filter(Transaction.merchant.in_(['S260 AUTO LOAN PMT', 'S260 LENDER', 'S260 GYM'])).delete(
            synchronize_session=False)
        s.query(DebtAccount).filter(DebtAccount.name.in_(['S260 Auto Loan', 'S260 Visa', 'S260 Paid Card'])).delete(
            synchronize_session=False)
        s.query(DebtAccount).filter(DebtAccount.id.in_(others)).update({'is_active': True}, synchronize_session=False)
        row = s.query(AppSetting).filter_by(key='monthly_budget').first()
        if saved_mb is None:
            if row:
                s.delete(row)
        else:
            row.value = saved_mb
        s.commit()
