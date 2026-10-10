"""Item 71 amendment (gw 2.0/INCOME_CHANGE_SCENARIOS.md section 4, D1-D10 RULED 2026-10-10; Rob: "build it").
The detection rules themselves (D3-D8, D10 and their null models) are in s183; this section holds the rest.

    D1   one definition of income, the same on the server and in the page
    D2   a budget income line names an income category; a category already made the other way is repaired by a
         previewed fix with Undo (item 72's C4)
    D9   the card leads with dollars a month and what is left after the budgeted spending
    D10  the kind of pay is the person's statement, kept, changeable, and it picks the rule
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import date, timedelta


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    app = ctx.app_src
    from core.database import AppSetting, BudgetItem, Category, HistorianEntry, Transaction, db_session
    from core.income_def import income_category_ids

    made = {}
    with db_session() as s:
        inc = s.query(Category).filter_by(name='Income').first()
        if not inc:
            inc = Category(name='Income', type='income'); s.add(inc); s.flush()
        old = Category(name="s190 Sam's pay", type='expense')            # made the old way: a spending category
        child = Category(name='s190 Bonus', type='expense', parent_id=inc.id)
        spend = Category(name='s190 Groceries', type='expense')
        s.add_all([old, child, spend]); s.flush()
        s.add(BudgetItem(name="s190 Sam's pay", category="s190 Sam's pay", amount=2000.0, type='income', is_active=True))
        s.commit()
        made.update(inc=inc.id, old=old.id, child=child.id, spend=spend.id)
        ids = income_category_ids(s)
    check('s190 D1 income is an income-type category, one under Income, or one named for a budget income line - not a spending category',
          {made['inc'], made['old'], made['child']} <= ids and made['spend'] not in ids)

    # D1 in the willingness inputs: a deposit in the person-named category counts toward monthly income
    import server
    with db_session() as s:
        m = (date.today().replace(day=1) - timedelta(days=1)).replace(day=10)
        s.add(Transaction(date=m, amount=1234.56, type='credit', category_id=made['old'], description='s190 pay'))
        s.commit()
        w = server._willingness_inputs(s)
    check('s190 D1 the monthly income figure counts pay filed under a category named for an income line',
          w['income'].get(f'{m.year}-{m.month:02d}', 0) >= 1234.56)

    # D1 in the page: the same rule, run in Node
    node = shutil.which('node')
    out = None
    if node:
        fn = re.search(r'\nfunction _isIncomeCategory\(.*?\n\}\n', app, re.S).group(0)
        js = ('const S = {incomes: [{name: "Sam\'s pay"}], categories: [{id: 1, name: "Income", type: "income"},'
              '{id: 2, name: "Bonus", type: "expense", parent_id: 1}, {id: 3, name: "Groceries", type: "expense"}]};\n' + fn +
              'console.log(JSON.stringify(["Income", "Bonus", "Sam\'s pay", "sam\'s PAY", "Groceries", ""].map(_isIncomeCategory)));')
        fd, p = tempfile.mkstemp(suffix='.js')
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(js)
        try:
            out = json.loads(subprocess.run([node, p], capture_output=True, text=True, encoding='utf-8', timeout=60).stdout or 'null')
        except Exception:                      # noqa: BLE001
            out = None
        finally:
            os.remove(p)
    check(f's190 D1 the page uses the same definition ({out})', out == [True, True, True, True, False, False]
          and "(t.category === 'Income' || t.category === 'income'))" not in app)

    # D2: a new income line makes an income category under Income
    r = c.post('/api/budget/items', headers=HJ, data=json.dumps({'type': 'income', 'name': 's190 Alex pay', 'amount': 1500,
                                                                  'category': "s190 Alex's income"}))
    with db_session() as s:
        new = s.query(Category).filter_by(name="s190 Alex's income").first()
        made['new_item'] = r.get_json()['data'].get('id') if r.status_code in (200, 201) else None
        made['new_cat'] = new.id if new else None
    check('s190 D2 an income line\'s new category is an income category under Income, never a spending one',
          new is not None and new.type == 'income' and new.parent_id == made['inc'])

    # D2: the repair, through Ask why - previewed, applied, undone
    inv = c.get('/api/why?figure=records', headers=H).get_json()['data']
    f = next((r for r in inv['results'] if r.get('retype') and r.get('category') == "s190 Sam's pay"), None)
    check('s190 D2 a category named for an income line but set up for spending is found, with a fix that says exactly what it does',
          f is not None and f['fixes'][0]['kind'] == 'retype_category' and 'named for one of your budget' in f['text'])
    if f:
        pv = c.post('/api/why/preview', headers=HJ, data=json.dumps({'fix': f['fixes'][0]})).get_json()['data']
        ap = c.post('/api/why/apply', headers=HJ, data=json.dumps({'fix': pv['fix'], 'fingerprint': pv['fingerprint']}))
        with db_session() as s:
            cat = s.get(Category, made['old'])
            after = (cat.type, cat.parent_id)
        hid = ap.get_json()['data']['historian_id']
        un = c.post('/api/why/undo', headers=HJ, data=json.dumps({'historian_id': hid}))
        with db_session() as s:
            cat = s.get(Category, made['old'])
            back = (cat.type, cat.parent_id)
        check('s190 D2 shown first, then applied on the tap, recorded, and undone back to how it was',
              pv['deposits'] >= 1 and pv['to']['type'] == 'income' and ap.status_code == 200
              and after == ('income', made['inc']) and un.status_code == 200 and back == ('expense', None))

    # D10: the kind of pay, said by the person
    k1 = c.post('/api/income-change/pay-kind', headers=HJ, data=json.dumps({'payer': 'S190 Plant', 'kind': 'hourly'}))
    k2 = c.post('/api/income-change/pay-kind', headers=HJ, data=json.dumps({'payer': 's190 plant', 'kind': 'salary'}))
    bad = c.post('/api/income-change/pay-kind', headers=HJ, data=json.dumps({'payer': 's190 plant', 'kind': 'commission'}))
    with db_session() as s:
        said = [x for x in json.loads(s.query(AppSetting).filter_by(key='pay_kinds').first().value) if x['payer'] == 's190 plant']
        kinds = server._pay_kinds(s)
    check('s190 D10 the answer is kept as said, in order, the latest wins, and only hourly or salary',
          k1.status_code == k2.status_code == 200 and [x['kind'] for x in said] == ['hourly', 'salary']
          and kinds['s190 plant'] == 'salary' and bad.status_code == 400)

    # D9 / D7 / D8 / D10 on the page
    card = app.split('function incomeChangeHtml(st) {')[1].split('\n}\n')[0]
    facts = app.split('function _payFactsHtml(st) {')[1].split('\n}\n')[0]
    check('s190 D9 the card leads with the dollars a month and what is left after the budgeted spending, then the checks',
          card.index('a month less') < card.index('Your checks were about') and 'st.left_now' in card)
    check('s190 D7/D8/D10 a missing paycheck is a question, hourly pay shows its ordinary week and overtime, and the kind of pay is asked',
          "hasn't come in since" in facts and 'Is it filed somewhere else, or did it stop?' in facts
          and 'Overtime added' in facts and 'Is this job hourly, with overtime?' in facts
          and "incomePayKind(" in facts and "'/api/income-change/pay-kind'" in app)
    check('s190 D7 never zero, never a verdict: no "lost", "fell", "missing income" or "you should" on the card',
          not re.search(r'\b(lost|fell|missing income|you should|you need)\b', card + facts, re.I))

    with db_session() as s:
        s.query(Transaction).filter(Transaction.description == 's190 pay').delete(synchronize_session=False)
        s.query(BudgetItem).filter(BudgetItem.name.like('s190%')).delete(synchronize_session=False)
        s.query(Category).filter(Category.name.like('s190%')).delete(synchronize_session=False)
        s.query(AppSetting).filter_by(key='pay_kinds').delete()
        s.query(HistorianEntry).filter(HistorianEntry.event_category.in_(['record_fix', 'record_fix_undone'])).delete(synchronize_session=False)
        s.commit()
