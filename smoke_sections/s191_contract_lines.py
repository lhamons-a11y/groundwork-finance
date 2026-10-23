"""Item 71 amendment D11 (gw 2.0/INCOME_CHANGE_SCENARIOS.md section 4.7, RULED 2026-10-10; Rob: "build d11"):
a payment set by a contract - a loan, lease, debt or insurance payment - is never cut by a plan that moves budget
money. A line that may be one is asked about once and left alone until answered.

The case behind it: on 2026-10-10 the budget-follows option halved Debt, two car leases and an insurance premium."""
import json
from datetime import date, timedelta


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    from core.contracts import classify
    from core import income_change as ic
    from core.database import AppSetting, BudgetItem, Category, DebtAccount, Transaction, db_session

    lines = [{'id': 1, 'name': 'Debt', 'category': 'Debt', 'amount': 1500.0},
             {'id': 2, 'name': 'Ford Lease', 'category': 'Car Lease Payment', 'amount': 450.00},
             {'id': 3, 'name': 'Stellantis Lease', 'category': '', 'amount': 425.00},
             {'id': 4, 'name': 'GEICO', 'category': '', 'amount': 180.00},
             {'id': 5, 'name': 'OneMain Financial', 'category': '', 'amount': 75.00},
             {'id': 6, 'name': 'Restaurants', 'category': 'Restaurants', 'amount': 600.0},
             {'id': 7, 'name': 'Apple', 'category': '', 'amount': 19.85},
             {'id': 8, 'name': 'Kohls card', 'category': '', 'amount': 40.0}]
    k = classify(lines, ['Apple Master Card Sam', 'Kohls'])
    check('s191 D11 contract payments are known by name or category, or by naming a debt account; a lender\'s name alone is asked',
          {i: k[i]['kind'] for i in k} == {1: 'contract', 2: 'contract', 3: 'contract', 4: 'ask', 5: 'contract', 8: 'contract'})
    check('s191 D11 a line inside a debt account\'s name is not that account ("Apple" is not "Apple Master Card")', 7 not in k)
    said = classify(lines, [], {4: 'no', 6: 'yes'})
    check('s191 D11 the person\'s word decides: a no frees the line, a yes holds any line', 4 not in said and said[6]['kind'] == 'contract')

    plan = ic.budget_follows(lines, 4000.0, {}, fixed=set(k))
    cut = {x['id'] for x in plan['changes']}
    check(f's191 D11 the plan never cuts a contract payment or one waiting for an answer (cut: {sorted(cut)})',
          not (cut & set(k)) and 6 in cut and plan['left'] > 0)
    old = ic.budget_follows(lines, 4000.0, {})
    check('s191 D11 mutation caught: without the rule, the plan halves the debt and the leases (the 2026-10-10 case)',
          {1, 2, 3} <= {x['id'] for x in old['changes']})

    # the route: a real drop, real lines, the question, the answer, and the tap
    made = {}
    today = date.today()
    with db_session() as s:
        inc = s.query(Category).filter_by(name='Income').first() or Category(name='Income', type='income')
        s.add(inc); s.flush()
        for n in range(20):
            d = today - timedelta(days=3 + 14 * (19 - n))
            s.add(Transaction(date=d, amount=2400.0 if n < 15 else 1900.0, type='credit', category_id=inc.id,
                              merchant='S191 Employer', description='S191 EMPLOYER PAYROLL'))
        items = [BudgetItem(name=n, category=cat, amount=a, type='expense', is_active=True) for n, cat, a in
                 (('s191 Debt', 'Debt', 900.0), ('s191 Ford Lease', 'Car Lease Payment', 500.0), ('s191 GEICO', '', 250.0),
                  ('s191 Restaurants', 's191 Restaurants', 800.0), ('s191 Rent', 'Rent', 1800.0))]
        s.add_all(items); s.commit()
        made = {it.name: it.id for it in items}
    st = c.get('/api/income-change', headers=H).get_json()['data']
    plan = next((x['plan'] for x in st.get('scenarios', []) if x['key'] == 'budget_follows'), {}) or {}
    names = {x['name'] for x in plan.get('changes', [])}
    qs = [q['name'] for q in st.get('contract_questions', [])]
    check(f's191 D11 on the card: contract lines are named as never cut, GEICO is asked about, and the plan cuts neither ({sorted(names)})',
          st.get('change') and 's191 Debt' not in names and 's191 Ford Lease' not in names and 's191 GEICO' not in names
          and 's191 GEICO' in qs and {'s191 Debt', 's191 Ford Lease'} <= {x['name'] for x in st.get('contracts', [])})
    no = c.post('/api/income-change/contract', headers=HJ, data=json.dumps({'line_id': made['s191 GEICO'], 'answer': 'no'})).get_json()['data']
    yes = c.post('/api/income-change/contract', headers=HJ, data=json.dumps({'line_id': made['s191 GEICO'], 'answer': 'yes'})).get_json()['data']
    bad = c.post('/api/income-change/contract', headers=HJ, data=json.dumps({'line_id': made['s191 GEICO'], 'answer': 'maybe'}))
    check('s191 D11 the answer is kept as said, the latest wins: no lets the line be offered, yes keeps it out',
          's191 GEICO' not in [q['name'] for q in no['contract_questions']] and 's191 GEICO' not in [x['name'] for x in no['contracts']]
          and 's191 GEICO' in {x['name'] for x in yes['contracts']} and bad.status_code == 400)
    c.post('/api/income-change/apply', headers=HJ, data='{}')
    with db_session() as s:
        amounts = {n: s.get(BudgetItem, i).amount for n, i in made.items()}
    check(f's191 D11 the tap changes no contract line ({amounts})',
          amounts['s191 Debt'] == 900.0 and amounts['s191 Ford Lease'] == 500.0 and amounts['s191 GEICO'] == 250.0
          and amounts['s191 Rent'] == 1800.0)
    c.post('/api/income-change/undo', headers=HJ, data='{}')

    with db_session() as s:
        s.query(Transaction).filter(Transaction.merchant == 'S191 Employer').delete(synchronize_session=False)
        s.query(BudgetItem).filter(BudgetItem.name.like('s191%')).delete(synchronize_session=False)
        for key in ('contract_lines', 'income_change_applied', 'income_change_answers'):
            s.query(AppSetting).filter_by(key=key).delete()
        s.commit()
