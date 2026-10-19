"""Item 101 (gw 2.0/COLLECTIONS.md = item 45 H7 stage 7; C1-C6 ruled 2026-10-19 by Rob: "lets treat that as a debt but
don't keep that in the debt payoff lets keep that in medical ... a running balance ... We don't need to worry about
interest ... a note that If they feel that this bill is not correct or no longer valid that they should consult legal
advice").

    C1 a debt kept on the Health page - never a Debt Payoff card
    C2 from the household's word; one debt that changed hands; counted once, under the collection
    C3 payments link to the collection
    C4 a running balance from the collector's own statements
    C5 no interest, no fees invented
    C6 the legal note on every collection, and nothing else directed
"""
import json
import re
from datetime import date, timedelta


def run(ctx):
    check, c, H, HJ, BASE = ctx.check, ctx.c, ctx.H, ctx.HJ, ctx.BASE
    from core import medical_bills as mb
    from core.database import (Account, AppSetting, DebtAccount, MedicalBillAccount, MedicalBillStatement,
                               MedicalCollection, MedicalProvider, Transaction, db_session)
    post = lambda path, body: c.post(path, headers=HJ, data=json.dumps(body))
    data = lambda r: (r.get_json() or {}).get('data')
    allb = lambda: data(c.get('/api/medical-bills', headers=H))
    today = date.today()
    d = lambda n: (today + timedelta(days=n)).isoformat()

    with db_session() as s:
        sp = s.query(AppSetting).filter_by(key='speaker_person_id').first()
        speaker_before = sp.value if sp else None
        chk = Account(name='S245 Checking', type='checking', is_active=True); s.add(chk); s.commit()
        chk_id = chk.id
        s.add_all([Transaction(account_id=chk_id, date=today - timedelta(days=50), description='S245 PAY HOSP',
                               amount=200.0, type='debit'),
                   Transaction(account_id=chk_id, date=today - timedelta(days=3), description='S245 PAY COLLECTOR',
                               amount=150.0, type='debit')])
        s.commit()
        early, late = [t.id for t in s.query(Transaction).filter(Transaction.description.like('S245%')).order_by(Transaction.date).all()]
        debts_before = s.query(DebtAccount).count()
    try:
        post('/api/accounts/speaker', {'name': 'S245 Pat'})
        post(f'/api/accounts/banks/{chk_id}', {'not_a_bank': True})
        post('/api/medical-bills/statement', {'provider': 'S245 Lakeside Hospital', 'account_number': 'L-1',
                                              'statement_date': d(-60), 'amount': 1000})
        bill = next(b for b in allb()['bills'] if b['provider'] == 'S245 Lakeside Hospital')
        stray = post('/api/medical-bills/statement', {'provider': 'S245 Recovery Partners', 'account_number': 'R-9',
                                                      'source': 'collector', 'statement_date': d(-5), 'amount': 900})
        check('s245 C2 a collector\'s statement comes in only for a collection already recorded on its bill',
              stray.status_code == 400)
        post(f'/api/medical-bills/{bill["id"]}/mine', {})
        post(f'/api/medical-bills/{bill["id"]}/payment', {'transaction_id': early})
        bad = post(f'/api/medical-bills/{bill["id"]}/collections', {'collector': 'S245 Recovery Partners'})
        r = post(f'/api/medical-bills/{bill["id"]}/collections', {'collector': 'S245 Recovery Partners', 'account_number': 'R-9',
                                                                 'sent_on': d(-20), 'amount': 875})
        st = allb()
        b2 = next(b for b in st['bills'] if b['provider'] == 'S245 Lakeside Hospital')
        col = next(b for b in st['bills'] if b['provider'] == 'S245 Recovery Partners')
        with db_session() as s:
            link = s.query(MedicalCollection).filter_by(of_account_id=bill['id']).first()
            same_debt = s.get(MedicalBillAccount, col['id']).obligation_id == s.get(MedicalBillAccount, bill['id']).obligation_id
            debts_after = s.query(DebtAccount).count()
        check('s245 C2 the household\'s word records it (incomplete details refused): one debt that changed hands',
              bad.status_code == 400 and r.status_code == 200 and link is not None and same_debt)
        check('s245 C2 counted once: the bill says where it went and owes nothing itself; the collection carries the balance',
              b2['owed'] == 0 and b2['sent_to']['collector'] == 'S245 Recovery Partners'
              and any('counted once' in n for n in b2['notes']) and col['owed'] == 875
              and [p['transaction_id'] for p in b2['payments']] == [early])
        check('s245 C1 a debt kept on the Health page - no Debt Payoff card is made', debts_after == debts_before)

        # C3 / C4 / C5
        post(f'/api/medical-bills/{col["id"]}/payment', {'transaction_id': late})
        post('/api/medical-bills/statement', {'provider': 'S245 Recovery Partners', 'account_number': 'R-9',
                                              'source': 'collector', 'statement_date': d(-1), 'amount': 760})
        col = next(b for b in allb()['bills'] if b['provider'] == 'S245 Recovery Partners')
        run = col['collection']['running']
        check('s245 C3 a payment links to the collection, from the hand-off on (an earlier one stays with the bill)',
              [p['transaction_id'] for p in col['payments']] == [late])
        check('s245 C4 a running balance, oldest first: the collector\'s figure, each payment after it, the next figure',
              [(x['what'].split(' - ')[0], x['balance']) for x in run] == [('The collector states $875.00', 875.0),
                                                                          ('You paid $150.00', 725.0),
                                                                          ('The collector states $760.00', 760.0)]
              and col['owed'] == 760)
        src = (BASE / 'core' / 'medical_bills.py').read_text(encoding='utf-8')
        rb = src[src.index('def running_balance('):src.index('def payments(')]
        check('s245 C5 no interest and no fee is computed: the balance moves only by what the collector states and what you paid',
              not re.search(r'interest|apr|\bfee\w*\s*[+*]|rate', rb.split('"""', 2)[2], re.I))

        # C6
        app = ctx.app_src
        check('s245 C6 the legal note, on every collection; nothing else directed',
              col['collection']['legal_note'] == mb.LEGAL_NOTE and 'legal advice' in mb.LEGAL_NOTE
              and '${esc(col.legal_note)}' in app
              and not re.search(r"\byou should\b|call them|\bnegotiate\b|we recommend", src, re.I))
        check('s245 C1 the page keeps collections under their own heading, and says they are not in Debt Payoff',
              '>Collections</div>' in app and 'A debt kept here, not in Debt Payoff.' in app
              and "This bill went to collections" in app and "_mbCollections(${b.id})" in app)
    finally:
        with db_session() as s:
            names = ('S245 Lakeside Hospital', 'S245 Recovery Partners')
            ids = [a.id for a in s.query(MedicalBillAccount).join(MedicalProvider, MedicalProvider.id == MedicalBillAccount.provider_id)
                   .filter(MedicalProvider.name.in_(names)).all()]
            s.query(MedicalCollection).filter(MedicalCollection.collection_account_id.in_(ids)).delete(synchronize_session=False)
            s.query(MedicalBillStatement).filter(MedicalBillStatement.account_id.in_(ids)).delete(synchronize_session=False)
            s.query(MedicalBillAccount).filter(MedicalBillAccount.id.in_(ids)).delete(synchronize_session=False)
            s.query(MedicalProvider).filter(MedicalProvider.name.in_(names)).delete(synchronize_session=False)
            s.query(AppSetting).filter_by(key='speaker_person_id').delete()
            if speaker_before is not None:
                s.add(AppSetting(key='speaker_person_id', value=speaker_before))
            s.commit()
