"""Item 94 (gw 2.0/BILL_THAT_LANDS.md = item 45 H7 stage 6; L1-L10 ruled 2026-10-19, Rob: "I accept item 94 as
written"; built on "Build item 94, the bill that lands, as ruled"). core/medical_bills.py and /api/medical-bills.

    L1  a bill is the provider's statement, typed in; it mints no obligation until "mine to pay" (by a person)
    L2  the amount owed now with its parts; a payment the newest bill may not show is said; a disagreement is named
    L3  a pending claim marks "may change" and keeps the bill out of judgements and dates
    L4  an arrangement as the provider agreed it, reported by the household; a budget line only on a tap
    L5  a card charge that looks like the bill is named, both counted until said; linked, it is one payment by card
    L6  bill_due about the reserve and the floor, never the bill's size
    L7  the non-profit facts only where the household said so, with "doesn't show whether"; never directs
    L8  what the record sustains, never an offer; too thin says so
    L9  the all-obligations date, or which obligations can't be dated - beside the card-free date
    L10 health data: scrubbed, no model, no log, no network; nothing contacts anyone
"""
import json
import re
from datetime import date, timedelta


def run(ctx):
    check, c, H, HJ, BASE = ctx.check, ctx.c, ctx.H, ctx.HJ, ctx.BASE
    from core import health_boundary as hb, medical_bills as mb
    from core.database import (Account, AppSetting, BudgetItem, DebtAccount, MedicalBillAccount, MedicalBillStatement,
                               MedicalProvider, Obligation, Transaction, Utterance, db_session)
    post = lambda path, body: c.post(path, headers=HJ, data=json.dumps(body))
    data = lambda r: (r.get_json() or {}).get('data')
    bills = lambda: data(c.get('/api/medical-bills', headers=H))
    mine = lambda: [b for b in bills()['bills'] if b['provider'].startswith('S243')]
    today = date.today()
    d = lambda n: (today + timedelta(days=n)).isoformat()

    with db_session() as s:
        speaker_before = s.query(AppSetting).filter_by(key='speaker_person_id').first()
        speaker_before = speaker_before.value if speaker_before else None
        s.query(AppSetting).filter_by(key='speaker_person_id').delete()
        chk = Account(name='S243 Checking', type='checking', is_active=True)
        card = Account(name='S243 Card', type='credit_card', is_active=True)
        s.add_all([chk, card, DebtAccount(name='S243 Visa', begin_balance=1200, current_balance=1200, interest_rate=20,
                                          minimum_payment=60, is_active=True)]); s.commit()
        chk_id, card_id = chk.id, card.id
        s.add_all([Transaction(account_id=chk_id, date=today - timedelta(days=20), description='S243 RIVERSIDE ONLINE PMT',
                               merchant='S243 Riverside', amount=300.0, type='debit'),
                   Transaction(account_id=card_id, date=today, description='S243 RIVERSIDE HOSP',
                               merchant='S243 Riverside', amount=900.0, type='debit')])
        s.commit()
        pay_id, card_txn = [t.id for t in s.query(Transaction).filter(Transaction.description.like('S243%'))
                            .order_by(Transaction.date).all()]
    try:
        # ── L1 ──
        ob_before = None
        with db_session() as s:
            ob_before = s.query(Obligation).count()
        r0 = post('/api/medical-bills/statement', {'provider': 'S243 Riverside Hospital', 'account_number': 'A-77',
                                                   'statement_date': d(-40), 'amount': 4000, 'due_date': d(10)})
        check('s243 L1 a statement is a person\'s statement: no one answering, no statement (asked, then tried again)',
              r0.status_code == 409)
        post('/api/accounts/speaker', {'name': 'S243 Sam'})
        for a_id in (chk_id, card_id):
            post(f'/api/accounts/banks/{a_id}', {'not_a_bank': True})
        r1 = post('/api/medical-bills/statement', {'provider': 'S243 Riverside Hospital', 'account_number': 'A-77',
                                                   'statement_date': d(-40), 'amount': 4000, 'due_date': d(10)})
        b = mine()[0]
        with db_session() as s:
            ob_after = s.query(Obligation).count()
        check('s243 L1 the bill arrives as the provider\'s statement and mints no obligation; it says it isn\'t yours yet',
              r1.status_code == 200 and not b['mine'] and ob_after == ob_before and b['owed'] == 4000
              and any('Not yours to pay yet' in n for n in b['notes']))
        post(f'/api/medical-bills/{b["id"]}/mine', {})
        with db_session() as s:
            acct = s.get(MedicalBillAccount, b['id'])
            u = s.get(Utterance, acct.mine_utterance_id)
            ob = s.get(Obligation, acct.obligation_id)
            minted_by_word = ob is not None and ob.minted_by_id == u.id and json.loads(u.content)['statement'] == 'bill_mine_to_pay'
        check('s243 L1 "mine to pay" mints the obligation, by that utterance', minted_by_word)

        # ── L2 / L5 ──
        b = mine()[0]
        cand = [x for x in b['candidates'] if x['transaction_id'] == card_txn]
        check('s243 L5 a card charge that looks like the bill is named, never linked: both counted until you say',
              cand and 'may be this bill; Groundwork counts both until you say.' in cand[0]['sentence']
              and 'card charge' in cand[0]['sentence'] and b['owed'] == 4000)
        post(f'/api/medical-bills/{b["id"]}/payment', {'transaction_id': pay_id})
        post('/api/medical-bills/statement', {'provider': 'S243 Riverside Hospital', 'account_number': 'A-77',
                                              'statement_date': d(-2), 'amount': 3700, 'due_date': d(20)})
        post(f'/api/medical-bills/{b["id"]}/payment', {'transaction_id': card_txn})
        b = mine()[0]
        check('s243 L2 the newest bill, less what you said you paid after it - each part said',
              b['owed'] == 2800 and any('gives $3,700.00' in l for l in b['lines'])
              and any(l.startswith('Less $900.00 you said you paid toward it') and 'by card' in l for l in b['lines'])
              and any('Amount owed now: $2,800.00' in l for l in b['lines']))
        check('s243 L2 a payment between two bills: the newer bill doesn\'t show whether it was applied - said, not assumed',
              any("doesn't show whether the $300.00 paid on" in n for n in b['notes']))
        check('s243 L5 a linked card charge is one payment toward the bill (the card\'s balance is card debt, counted once)',
              [p['card'] for p in b['payments']] == [False, True] and not [x for x in b['candidates'] if x['transaction_id'] == card_txn])
        post('/api/medical-bills/statement', {'provider': 'S243 Riverside Hospital', 'account_number': 'A-77',
                                              'source': 'insurer', 'statement_date': d(-1), 'amount': 2500})
        b = mine()[0]
        check('s243 L2 provider and insurer disagree: both shown with dates, the newer used, the difference not resolved',
              any("the difference isn't resolved" in n and '$3,700.00' in n and '$2,500.00' in n for n in b['notes'])
              and b['owed'] == 1600 and not b['datable'])          # the insurer's $2,500, less the $900 card payment after it

        # ── L3 / L4 / L9 ──
        post(f'/api/medical-bills/{b["id"]}/claim', {'pending': True})
        b = mine()[0]
        check('s243 L3 a claim you say is pending: "may change", no alarm, no date',
              any('May change: the insurer\'s claim is pending (as you said).' == n for n in b['notes'])
              and b['attention'] is None and not b['datable'])
        post(f'/api/medical-bills/{b["id"]}/claim', {'pending': False})
        post('/api/medical-bills/statement', {'provider': 'S243 Riverside Hospital', 'account_number': 'A-77',
                                              'statement_date': d(0), 'amount': 2500, 'due_date': d(25)})
        dates = bills()['dates']
        check('s243 L9 an obligation with no schedule: no all-obligations date, it is named, the card-free date stands',
              dates['all'] is None and re.search(r'Card balances only: (\w+ \d{4}|not reached)', dates['card_free']) and 'S243 Riverside Hospital, no payment arrangement' in dates['sentence']
              and dates['card_free'].startswith('Card balances only'))
        bad = post(f'/api/medical-bills/{b["id"]}/arrangement', {'monthly': 0})
        post(f'/api/medical-bills/{b["id"]}/arrangement', {'monthly': 125, 'first_date': d(25), 'payments': 20})
        b = mine()[0]
        dates = bills()['dates']
        check('s243 L4 the provider\'s terms as you reported them (incomplete terms refused)',
              bad.status_code == 400 and any('as you reported the provider\'s terms: $125.00 a month, 20 payments' in l for l in b['lines']))
        check('s243 L9 every obligation dated: the all-obligations date, labelled, beside card balances only',
              dates['all'] and 'All obligations on record:' in dates['sentence'])
        with db_session() as s:
            n_items = s.query(BudgetItem).count()
        rb = data(post(f'/api/medical-bills/{b["id"]}/budget', {}))
        with db_session() as s:
            item = s.get(BudgetItem, rb['budget_item_id'])
            budget_ok = s.query(BudgetItem).count() == n_items + 1 and item.amount == 125
            s.delete(item); s.commit()
        check('s243 L4 the arrangement reaches the budget only on your tap', budget_ok)

        # ── L6 / L8, on the module with set figures ──
        with db_session() as s:
            acct = s.get(MedicalBillAccount, b['id'])
            v = mb.view(s, acct, {'liquid': 3000, 'liquid_known': True, 'reserve': 2000, 'floor': 1500,
                                  'capacity': {'thin': False, 'months': 6, 'leanest': 'March 2026', 'left': 300.0,
                                               'reserve_monthly': 50.0, 'monthly': 250.0}})
            v_big = mb.view(s, acct, {'liquid': 50000, 'liquid_known': True, 'reserve': 2000, 'floor': 1500,
                                      'capacity': {'thin': True, 'months': 2}})
            v_none = mb.view(s, acct, {'liquid': 0, 'liquid_known': False, 'reserve': 0, 'floor': 0, 'capacity': None})
        check('s243 L6 the alarm is about the reserve: "would leave $500.00 in savings, below your $2,000.00 reserve"',
              v['attention'] and v['attention']['kind'] == 'bill_due'
              and v['attention']['sentence'] == 'Paying this $2,500.00 bill in full would leave $500.00 in savings, below your $2,000.00 reserve.')
        check('s243 L6 never the bill\'s size: a bill the savings cover above the reserve raises nothing; none on record says so',
              v_big['attention'] is None and "can't be paid in full from what's on record: no savings balance is on record" in v_none['attention']['sentence'])
        rows = v['capacity']['rows']
        check('s243 L8 what the record sustains, with its working, three durations - never an offer; too thin says so',
              'Your leanest month on record, March 2026, left $300.00 after its spending, less $50.00 a month going to your reserve.' in v['capacity']['sentence']
              and [r['months'] for r in rows] == [6, 12, 24] and [r['sustained'] for r in rows] == [False, True, True]
              and v_big['capacity']['thin'] and not re.search(r'\boffer\b', json.dumps([v['capacity'], v_big['capacity']]), re.I))

        # ── L7 ──
        plain = mine()[0]
        post(f'/api/medical-bills/providers/{b["provider_id"]}/kind', {'value': True})
        np_ = mine()[0]
        src = (BASE / 'core' / 'medical_bills.py').read_text(encoding='utf-8')
        check('s243 L7 the non-profit facts only once you said so, cited, with "doesn\'t show whether" - and never a direction',
              plain['facts'] == [] and any('240 days' in f for f in np_['facts']) and any('501(r)' in f for f in np_['facts'])
              and mb.NO_ASSISTANCE_SHOWN in np_['facts']
              and not re.search(r"\byou should\b|call them|\bapply now\b|\bnegotiate\b|we recommend", src, re.I))

        # ── L10 ──
        hb_n = None
        with db_session() as s:
            hb_n = hb.refresh(s)
        check('s243 L10 the provider\'s name is health data: the scrubber removes it from anything bound for a log or the model',
              'S243 Riverside Hospital' not in (hb.scrub('a note about S243 Riverside Hospital') or ''))
        check('s243 L10 the module logs nothing, calls no model, reaches no network, and its routes write nothing on a read',
              not re.search(r'logging\.|print\(|callAI|engine\.|urlopen|egress', src))
        att = (BASE / 'static' / 'js' / 'teaching' / 'attention.js').read_text(encoding='utf-8')
        dash = (BASE / 'static' / 'js' / 'teaching' / 'dashboard.js').read_text(encoding='utf-8')
        check('s243 L6 bill_due is a ruled attention kind, shown with its source and no action that pays',
              "'bill_due'];" in att and 'billsDue: billsDue' in att and "i.kind === 'bill_due'" in dash
              and 'Groundwork never contacts anyone or pays anything.' in dash and 'bill_due' in ctx.server_src)
        check('s243 the card lives on the Health page (item 100), every sentence from the server',
              'renderMedicalBillsCard();' in ctx.app_src.split('async function renderHealthPage()')[1][:400]
              and 'id="medicalBillsCard"' in ctx.html_src)
    finally:
        with db_session() as s:
            ids = [a.id for a in s.query(MedicalBillAccount).join(MedicalProvider, MedicalProvider.id == MedicalBillAccount.provider_id)
                   .filter(MedicalProvider.name.like('S243%')).all()]
            s.query(MedicalBillStatement).filter(MedicalBillStatement.account_id.in_(ids)).delete(synchronize_session=False)
            s.query(MedicalBillAccount).filter(MedicalBillAccount.id.in_(ids)).delete(synchronize_session=False)
            s.query(MedicalProvider).filter(MedicalProvider.name.like('S243%')).delete(synchronize_session=False)
            s.query(DebtAccount).filter(DebtAccount.name == 'S243 Visa').delete(synchronize_session=False)
            s.query(AppSetting).filter_by(key='speaker_person_id').delete()
            if speaker_before is not None:
                s.add(AppSetting(key='speaker_person_id', value=speaker_before))
            s.commit()
