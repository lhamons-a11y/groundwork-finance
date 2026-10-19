"""Item 98 (core/new_vendor.py; Rob 2026-10-19: "accept"): a vendor Groundwork has never seen, filed by the bank's
own category label, is asked about on the Ledger - once, one vendor at a time, never decided for the person.

    N1  only rows the bank's label filed (bank_category): not a row with no label, not one the person's rule or
        preview choice filed
    N2  only a vendor never seen before (in any account), and not one an import rule covers
    N3  never on an account's first import
    N4  one question per vendor however many of its rows came in; answered once, never asked again
    N5  Yes opens the transaction to change it, No keeps it and offers the usual rule; the answer changes nothing itself
"""
import json


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    from core import new_vendor as nv
    from core.database import Account, AppSetting, Category, Transaction, db_session

    post = lambda path, body: c.post(path, headers=HJ, data=json.dumps(body))
    data = lambda r: (r.get_json() or {}).get('data')
    waiting = lambda: data(c.get('/api/tidy/new-vendors', headers=H))['waiting']
    mine = lambda: [w for w in waiting() if w['key'].startswith('s238')]

    def rec(d, merchant, amt, label='', cat='Groceries'):
        r = {'date': d, 'description': merchant.upper() + ' 0042', 'merchant': merchant, 'amount': amt,
             'type': 'debit', 'category': cat, 'source': 'csv'}
        if label:
            r['bank_category'] = label
        return r

    def setting(key, value=None):
        with db_session() as s:
            row = s.query(AppSetting).filter_by(key=key).first()
            if value is None:
                return row.value if row else None
            if row:
                row.value = value
            else:
                s.add(AppSetting(key=key, value=value))
            s.commit()

    with db_session() as s:
        a = Account(name='S238 Card', type='credit', is_active=True); s.add(a)
        b = Account(name='S238 Other Card', type='credit', is_active=True); s.add(b)
        s.commit()
        aid, bid = a.id, b.id
        if not s.query(Category).filter(Category.name == 'Groceries').first():
            s.add(Category(name='Groceries', type='expense')); s.commit()
    rules_before, queue_before = setting('import_rules_json'), setting(nv.SETTING)
    try:
        # ── N3: an account's first import asks nothing, however new its vendors ──
        r1 = data(post('/api/import/commit', {'account_id': aid, 'records': [
            rec('2026-04-01', 'S238 Corner Market', 12.50, 'Grocery'),
            rec('2026-04-02', 'S238 Old Bakery', 6.00, 'Food and Drink')]}))
        check("s238 N3 an account's first import asks about nothing (its whole history is new)",
              r1['created'] == 2 and r1['new_vendors'] == 0 and mine() == [])

        # ── N1, N2, N4 on the next import ──
        with db_session() as s:
            s.query(AppSetting).filter_by(key='import_rules_json').delete(); s.commit()
        setting('import_rules_json', json.dumps([{'id': 1, 'type': 'contains', 'value': 's238 ruled shop', 'category': 'Groceries'}]))
        r2 = data(post('/api/import/commit', {'account_id': aid, 'records': [
            rec('2026-04-10', 'S238 Fresh Farm', 30.00, 'Grocery'),             # new + bank label: asked
            rec('2026-04-12', 'S238 Fresh Farm', 18.25, 'Grocery'),             # same vendor again: one question
            rec('2026-04-11', 'S238 Corner Market', 9.00, 'Grocery'),           # seen before: not asked
            rec('2026-04-11', 'S238 Quiet Store', 4.00),                        # no bank label: not asked
            rec('2026-04-11', 'S238 Ruled Shop', 7.00, 'Shopping')]}))          # an import rule covers it: not asked
        w = mine()
        check('s238 N1/N2 only the new vendor the bank labelled is asked about (not a known vendor, an unlabelled row, '
              'or one an import rule covers)', r2['created'] == 5 and r2['new_vendors'] == 1
              and [x['key'] for x in w] == ['s238 fresh farm'])
        f = w[0] if w else {}
        check("s238 N4 one question per vendor: both of its rows, the bank's label, where it is filed, its first row",
              f.get('count') == 2 and f.get('label') == 'Grocery' and f.get('category') == 'Groceries'
              and f.get('merchant') == 'S238 Fresh Farm' and f.get('txn', {}).get('date') == '2026-04-10'
              and f.get('txn', {}).get('amount') == 30.00)
        r3 = data(post('/api/import/commit', {'account_id': bid, 'records': [
            rec('2026-04-20', 'S238 Fresh Farm', 5.00, 'Grocery')]}))
        check("s238 N3 a different account's first import adds nothing, even for a vendor still waiting",
              r3['new_vendors'] == 0 and [x['count'] for x in mine()] == [2])
        r4 = data(post('/api/import/commit', {'account_id': aid, 'records': [
            rec('2026-04-21', 'S238 Lantern Cafe', 11.00, 'Food and Drink', cat='Groceries')]}))
        check('s238 N2 a vendor seen in any account is known; a second new vendor waits behind the first',
              r4['new_vendors'] == 1 and [x['key'] for x in mine()] == ['s238 fresh farm', 's238 lantern cafe'])

        # ── N5: the answers ──
        bad = post('/api/tidy/new-vendors/answer', {'key': 's238 fresh farm', 'answer': 'maybe'})
        with db_session() as s:
            before = {t.id: t.category_id for t in s.query(Transaction).filter(Transaction.account_id == aid).all()}
        yes = data(post('/api/tidy/new-vendors/answer', {'key': 's238 fresh farm', 'answer': 'yes'}))
        no = data(post('/api/tidy/new-vendors/answer', {'key': 's238 lantern cafe', 'answer': 'no'}))
        again = post('/api/tidy/new-vendors/answer', {'key': 's238 lantern cafe', 'answer': 'no'})
        with db_session() as s:
            after = {t.id: t.category_id for t in s.query(Transaction).filter(Transaction.account_id == aid).all()}
        check('s238 N5 only yes or no is an answer; each is recorded once, and the vendor is asked no more',
              bad.status_code == 400 and yes['answer'] == 'yes' and no['answer'] == 'no' and again.status_code == 404
              and mine() == [])
        check('s238 N5 an answer changes no transaction and makes no rule (the person does, on the Ledger)',
              before == after and json.loads(setting('import_rules_json'))[0]['value'] == 's238 ruled shop'
              and len(json.loads(setting('import_rules_json'))) == 1)
        items = nv.queue(json.loads(setting(nv.SETTING)),
                         {'s238 fresh farm': {'merchant': 'S238 Fresh Farm', 'label': 'Grocery', 'category': 'Groceries', 'ids': [1]}})
        check('s238 N4 an answered vendor is never queued again', not [x for x in items if x['key'] == 's238 fresh farm'
                                                                       and not x.get('answer')])
        with db_session() as s:
            gone = [{'key': 's238 gone', 'merchant': 'S238 Gone', 'label': 'X', 'category': 'Other', 'ids': [987654321]}]
            check('s238 a vendor whose transactions were all deleted is not asked about', nv.waiting(s, gone) == [])

        # ── the page ──
        app = ctx.app_src
        html = (ctx.BASE / 'static' / 'index.html').read_text(encoding='utf-8')
        imp = (ctx.BASE / 'bank_importer.py').read_text(encoding='utf-8')
        check("s238 N1 Apple Card rows carry Apple's own label; a QIF row only when its category came from the file",
              'bank_category: appleCategory || undefined' in app
              and "'bank_category': raw_cat if mapped_cat else ''" in imp)
        check("s238 N1 a row the person's import rule or preview choice files drops the bank's label",
              app.count('delete t.bank_category') == 2 and 'delete _importRecords[idx].bank_category' in app)
        check('s238 the question waits on the Ledger (after an import and whenever the Ledger opens)',
              'id="newVendorCard"' in html and app.count('renderNewVendorCard();') >= 2
              and "Would you like to change it?" in app)
        yes_src = app[app.index('async function newVendorAnswer('):app.index('// Yes: the Ledger shows')]
        check('s238 N5 Yes opens that transaction to edit; No offers the usual "always categorize" rule',
              "_openTxnToEdit(v.txn.id)" in yes_src and '_offerVendorRule(v.merchant, v.category)' in yes_src
              and 'ledgerRowDblClick(id)' in app and "on future imports?`);" in app)
        rule_src = app[app.index('function _offerVendorRule('):app.index('// Click outside bloom')]
        check('s238 N5 the rule is not offered when the person said never ask, or a rule already covers the vendor',
              '_recurringRuleSuppressions.has(k)' in rule_src and '_importRules.some(' in rule_src)
    finally:
        with db_session() as s:
            s.query(Transaction).filter(Transaction.account_id.in_([aid, bid])).delete(synchronize_session=False)
            s.query(Account).filter(Account.id.in_([aid, bid])).delete(synchronize_session=False)
            s.commit()
        for k, v in (('import_rules_json', rules_before), (nv.SETTING, queue_before)):
            with db_session() as s:
                s.query(AppSetting).filter_by(key=k).delete(); s.commit()
            if v is not None:
                setting(k, v)
