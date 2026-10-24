"""The simulated user panel's issues (groundwork-panel-sim, 2026-10-24), each fixed and held here.

    I-01/I-04  debt payments are budgeted wherever they are spent: one rule (_debt_month_plan, _debtMonthPlan) for the
               check-in, Before You Buy, the income page and the Budget page - the payoff plan, never below the
               minimums, or the minimums when no plan was saved; a payment on a debt is never offered as a purchase
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
