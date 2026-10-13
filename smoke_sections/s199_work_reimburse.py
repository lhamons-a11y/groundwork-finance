"""Item 72 stage 4 (gw 2.0/ASK_WHY.md C5 as revised in section 5; Rob 2026-10-11: "build item 72 stage 4").

    C5  told, never guessed: nothing can be marked until the person says they buy things for work and get paid back
        a marked purchase and a repayment that is all repayment are neither spending nor income (inside Transfer)
        a deposit that carries other money too stays where it is; the paid-back part is recorded
        partial repayments, undoing a match, "it won't be paid back" and "not a work purchase" all restore exactly
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
    from core.database import (AppSetting, Category, HistorianEntry, ReimbursableItem, ReimbursementMatch, Transaction,
                               db_session)
    from core.income_def import income_category_ids

    first = date.today().replace(day=1)
    lm = (first - timedelta(days=1)).replace(day=1)
    with db_session() as s:
        inc = s.query(Category).filter_by(name='Income').first() or Category(name='Income', type='income')
        shop = Category(name='s199 Supplies', type='expense')
        s.add_all([inc, shop]); s.flush()
        T = lambda d, amt, kind, cat, m: Transaction(date=d, amount=amt, type=kind, category_id=cat.id, merchant=m, description=m)
        buy = T(lm.replace(day=3), 120.0, 'debit', shop, 's199 Office Depot')
        buy2 = T(lm.replace(day=4), 50.0, 'debit', shop, 's199 Staples')
        back = T(lm.replace(day=20), 120.0, 'credit', inc, 's199 ACME CORP EXPENSE REIMB')
        pay = T(lm.replace(day=25), 2000.0, 'credit', inc, 's199 ACME CORP PAYROLL')
        s.add_all([buy, buy2, back, pay]); s.commit()
        ids = {'buy': buy.id, 'buy2': buy2.id, 'back': back.id, 'pay': pay.id, 'shop': shop.id, 'inc': inc.id}

    post = lambda path, body: c.post(path, headers=HJ, data=json.dumps(body))
    early = post('/api/reimburse/mark', {'transaction_id': ids['buy']})
    st0 = c.get('/api/reimburse', headers=H).get_json()['data']
    check('C5 told, never guessed: nothing can be marked before the person says they do this, and nothing is offered',
          early.status_code == 409 and st0['items'] == [] and st0['said'] is None)
    post('/api/reimburse/said', {'answer': 'yes'})
    m1 = post('/api/reimburse/mark', {'transaction_id': ids['buy'], 'employer': 'Acme Corp'})
    m_again = post('/api/reimburse/mark', {'transaction_id': ids['buy']})
    m_credit = post('/api/reimburse/mark', {'transaction_id': ids['back']})
    with db_session() as s:
        t = s.get(Transaction, ids['buy'])
        cat = s.get(Category, t.category_id)
        parent = s.get(Category, cat.parent_id) if cat.parent_id else None
        item = s.query(ReimbursableItem).filter_by(transaction_id=ids['buy']).first()
    check('C5 a marked purchase moves under "Paid back by work", inside Transfer, keeping where it was; a second mark and a deposit are refused',
          m1.status_code == 200 and cat.name == 'Paid back by work' and cat.type == 'transfer' and parent and parent.name == 'Transfer'
          and item.original_category_id == ids['shop'] and m_again.status_code == 400 and m_credit.status_code == 400)

    st = c.get('/api/reimburse', headers=H).get_json()['data']
    it = next(i for i in st['items'] if i['id'] == item.id)
    cands = it['candidates']
    check(f'C5 the deposits offered as the repayment: on or after the purchase, the one naming the employer first ({[x["name"] for x in cands][:2]})',
          cands and cands[0]['id'] == ids['back'] and cands[0]['names_employer'] and not cands[0]['carries_more'])

    post('/api/reimburse/match', {'item_id': item.id, 'credit_id': ids['back']})
    with db_session() as s:
        back_cat = s.get(Category, s.get(Transaction, ids['back']).category_id).name
        status = s.get(ReimbursableItem, item.id).status
        inc_ids = income_category_ids(s)
        moved_cat = s.get(Transaction, ids['back']).category_id
    check('C5 a deposit that was all repayment moves too, so it is not income; the purchase is paid back',
          back_cat == 'Paid back by work' and status == 'paid' and moved_cat not in inc_ids)

    # the paycheck that carries a reimbursement: not moved, the part recorded
    post('/api/reimburse/mark', {'transaction_id': ids['buy2'], 'employer': 'Acme Corp'})
    with db_session() as s:
        it2 = s.query(ReimbursableItem).filter_by(transaction_id=ids['buy2']).first().id
    mm = post('/api/reimburse/match', {'item_id': it2, 'credit_id': ids['pay']}).get_json()['data']['result']
    with db_session() as s:
        pay_cat = s.get(Transaction, ids['pay']).category_id
        st2 = s.get(ReimbursableItem, it2).status
    check('C5 a paycheck carrying the repayment stays income; the $50 paid back is recorded against the purchase',
          mm['amount'] == 50.0 and mm['deposit_moved'] is False and pay_cat == ids['inc'] and st2 == 'paid')

    # neither counts: the server's monthly spending and income, and the page's own test
    import server
    with db_session() as s:
        w = server._willingness_inputs(s)
    key = f'{lm.year}-{lm.month:02d}'
    spend = sum(v for (n, m), v in w['spend'].items() if m == key and n in ('Paid back by work', 's199 Supplies'))
    check(f'C5 the server counts neither the marked purchases nor the moved repayment ({spend})',
          spend == 0.0 and w['income'].get(key, 0) >= 2000.0)
    node = shutil.which('node')
    out = None
    if node:
        fns = ''.join(re.search(r'\nfunction ' + n + r'\(.*?\n\}\n', app, re.S).group(0) for n in ('_isSpend', '_isEarn', '_catParentName', '_catByName', '_isTransferCat'))
        js = ('const S = {categories: [{id: 1, name: "Transfer", type: "transfer"}, {id: 2, name: "Paid back by work", type: "transfer", parent_id: 1},'
              '{id: 3, name: "Supplies", type: "expense"}]};\n' + fns +
              'console.log(JSON.stringify([_isSpend({type: "debit", category: "Paid back by work"}), _isEarn({type: "credit", category: "Paid back by work"}),'
              '_isSpend({type: "debit", category: "Supplies"})]));')
        fd, p = tempfile.mkstemp(suffix='.js')
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(js)
        try:
            out = json.loads(subprocess.run([node, p], capture_output=True, text=True, encoding='utf-8', timeout=60).stdout or 'null')
        except Exception:                      # noqa: BLE001
            out = None
        finally:
            os.remove(p)
    check(f'C5 the page\'s own spending and income tests leave it out too, run in Node ({out})', out == [False, False, True])

    # changes of mind restore exactly
    with db_session() as s:
        mid = s.query(ReimbursementMatch).filter_by(item_id=item.id).first().id
    post('/api/reimburse/unmatch', {'match_id': mid})
    with db_session() as s:
        r1 = (s.get(Transaction, ids['back']).category_id, s.get(ReimbursableItem, item.id).status)
    blocked = post('/api/reimburse/unmark', {'item_id': it2})
    post('/api/reimburse/write-off', {'item_id': item.id})
    with db_session() as s:
        r2 = s.get(Transaction, ids['buy']).category_id
        r3 = s.get(ReimbursableItem, item.id).status
        notes = s.query(HistorianEntry).filter(HistorianEntry.event_category.like('reimbursement_%')).count()
    check('C5 undoing a match puts the deposit back and the purchase back to waiting; "it won\'t be paid back" puts the purchase back',
          r1 == (ids['inc'], 'waiting') and r2 == ids['shop'] and r3 == 'written_off')
    check('C5 "not a work purchase" only before a repayment is matched; every step is in the Historian',
          blocked.status_code == 400 and notes >= 6)

    check('C5 on the page: asked once, the row mark only after a yes, and the paycheck case said where it happens',
          'Do you buy things for work and get paid back by your employer?' in app and "((_reimburseState || {}).said || {}).answer === 'yes'" in app
          and 'this deposit carries other money too, so it stays where it is' in app and 'id="ledgerReimburse"' in ctx.html_src)

    with db_session() as s:
        s.query(ReimbursementMatch).delete(); s.query(ReimbursableItem).delete()
        s.query(Transaction).filter(Transaction.merchant.like('s199 %')).delete(synchronize_session=False)
        s.query(Category).filter(Category.name.like('s199%')).delete(synchronize_session=False)
        s.query(AppSetting).filter_by(key='work_reimbursements_said').delete()
        s.query(HistorianEntry).filter(HistorianEntry.event_category.like('reimbursement_%')).delete(synchronize_session=False)
        s.commit()
