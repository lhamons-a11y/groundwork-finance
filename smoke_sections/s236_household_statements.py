"""Item 93 stages 3 and 4 (gw 2.0/BANK_SIDE_RECORDS.md B2, B3, B4, B8, B11; Rob 2026-10-18 "go ahead stage 3 and 4",
with that day's two rulings: who is answering is asked once and remembered, with a switch; earlier answers are confirmed
once by a person). Master only.

    who   nothing is minted until a person is answering; then every statement is that person's utterance
    B2    a bank is a party once, by the household's word; the same name again is the same party; "not a bank" mints none
    B3    a line is a payment only by a statement - one at a time, or a standing statement (scoped, dated, listed,
          withdrawable, suggested after three answers, never made without a yes); no statement, no payment
    B4    an expense only by the household's say-so (a care-for answer), incurred_by the person; a change adds a claim
    B8    a reversal is linked only on a yes (payment_counteracts); a no is not asked again; nothing netted
    B11   earlier answers wait until a person confirms them; then each is the same statement, first date kept
    and through it all: every total is unchanged, and every audit of the minting rule stays empty
"""
import json
from datetime import date, datetime


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    from sqlalchemy import func, text
    import core.database as db
    from core.database import (Account, AppSetting, CareFor, Category, CheckingTransactionLink, DebtAccount,
                               DebtLedgerEntry, Person, Transaction, db_session)

    post = lambda path, body: c.post(path, headers=HJ, data=json.dumps(body))
    data = lambda r: (r.get_json() or {}).get('data')
    TABLES = ('evidence', 'propositions', 'ledger_line_records', 'earlier_answers', 'reversal_answers',
              'standing_statements', 'account_banks', 'payments', 'expenses', 'obligations', 'utterances', 'parties',
              'people', 'care_for', 'checking_transaction_links', 'debt_ledger_entries', 'reimbursement_matches',
              'reimbursable_items')
    with db_session() as s:
        snap = {t: s.execute(text(f'SELECT COALESCE(MAX(id), 0) FROM {t}')).scalar() for t in TABLES}
        had_speaker = s.query(AppSetting).filter_by(key='speaker_person_id').first()
        had_speaker = had_speaker.value if had_speaker else None
        if had_speaker is not None:
            s.query(AppSetting).filter_by(key='speaker_person_id').delete(); s.commit()
        a = Account(name='S236 Checking', type='checking', is_active=True, institution='SUPERIOR CU')
        b = Account(name='S236 Savings', type='savings', is_active=True)
        cc = Account(name='S236 Cash Book', type='checking', is_active=True)
        s.add_all([a, b, cc]); s.commit()
        aid, bid, cid = a.id, b.id, cc.id
        health = s.query(Category).filter(func.lower(Category.name).in_(['doctor', 'medical', 'healthcare', 'health']))\
            .first()
        health_name = health.name if health else 'Medical'
    rec = lambda d, desc, amt, typ='debit', cat='Other': {'date': d, 'description': desc, 'amount': amt, 'type': typ,
                                                          'category': cat, 'source': 'csv'}
    total = lambda s: round(s.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        Transaction.account_id.in_([aid, bid, cid])).scalar(), 2)
    count = lambda s, t: s.execute(text(f'SELECT COUNT(*) FROM {t}')).scalar()
    line = lambda s, desc: s.query(Transaction).filter(Transaction.account_id == aid, Transaction.description == desc).first().id
    def hs_bank_none(s):
        from core import household_statements as _h
        return _h.bank_of(s, aid) is None

    try:
        post('/api/import/commit', {'account_id': aid, 'records': [
            rec('2026-05-01', 'S236 AEP OHIO 1001', 120.00), rec('2026-05-02', 'S236 KROGER 7', 50.00),
            rec('2026-06-01', 'S236 AEP OHIO 1002', 130.00), rec('2026-07-01', 'S236 AEP OHIO 1003', 125.00),
            rec('2026-07-03', 'S236 AEP OHIO 1004', 15.00), rec('2026-07-05', 'S236 PAYROLL', 900.00, 'credit'),
            rec('2026-07-06', 'S236 SHOE STORE 9', 80.00), rec('2026-07-20', 'REFUND S236 SHOE STORE 9', 80.00, 'credit'),
            rec('2026-07-07', 'S236 MERCY CLINIC', 60.00, cat=health_name), rec('2026-07-08', 'S236 CHASE CARD PMT', 200.00),
            rec('2026-07-09', 'S236 DENTAL ARTS', 90.00, cat=health_name)]})
        with db_session() as s:
            before_total, before_pay = total(s), count(s, 'payments')
            utt0, par0 = count(s, 'utterances'), count(s, 'parties')

        # ── who is answering ──────────────────────────────────────────────────
        r = post(f'/api/accounts/banks/{aid}', {'name': 'Superior Credit Union'})
        with db_session() as s:
            nothing = count(s, 'utterances') == utt0 and count(s, 'parties') == par0 and hs_bank_none(s)
        check("s236 who: with no one answering, a statement is refused with the question, and nothing is written",
              r.status_code == 409 and "Who is answering?" in (r.get_json() or {}).get('error', '') and nothing)
        sp = data(post('/api/accounts/speaker', {'name': 'S236 Rob'}))
        got = data(c.get('/api/accounts/speaker', headers=H))
        check("s236 who: the answering person is set once (added by name if new) and remembered",
              sp['name'] == 'S236 Rob' and got['person_id'] == sp['person_id'])
        with db_session() as s:
            rob_party = s.get(Person, sp['person_id']).party.id

        # ── B2 ────────────────────────────────────────────────────────────────
        q = data(c.get('/api/accounts/banks', headers=H))
        mine = next(x for x in q['accounts'] if x['account_id'] == aid)
        check("s236 B2 the account's institution text is offered as the candidate, never taken as the answer",
              mine['candidate'] == 'SUPERIOR CU' and mine['said'] is None)
        post(f'/api/accounts/banks/{aid}', {'name': 'Superior Credit Union'})
        post(f'/api/accounts/banks/{bid}', {'name': 'superior credit union'})
        with db_session() as s:
            from core import household_statements as hs
            ba, bb = hs.bank_of(s, aid), hs.bank_of(s, bid)
            bank_party = s.get(db.Party, ba.party_id)
            minted_by = s.get(db.Utterance, bank_party.minted_by_id)
        check("s236 B2 the bank is a party minted by the answering person's statement; the same name again is the same party",
              ba.party_id is not None and ba.party_id == bb.party_id and minted_by.origin_party_id == rob_party)
        post(f'/api/accounts/banks/{bid}', {'not_a_bank': True})
        with db_session() as s:
            nb = hs.bank_of(s, bid)
            kept = s.query(db.AccountBank).filter_by(account_id=bid).count()
        check('s236 B2 "not a bank account" mints nothing; the earlier answer stays on record', nb.party_id is None and kept == 2)

        # ── B3, one line at a time ────────────────────────────────────────────
        with db_session() as s:
            l1, l2, l3, kro = (line(s, 'S236 AEP OHIO 1001'), line(s, 'S236 AEP OHIO 1002'), line(s, 'S236 AEP OHIO 1003'),
                               line(s, 'S236 KROGER 7'))
            pay_id, credit_id = line(s, 'S236 PAYROLL'), None
        v1 = data(post(f'/api/accounts/line-statement/{l1}', {'payee': 'AEP OHIO'}))
        with db_session() as s:
            r1 = hs.record_of(s, l1)
            mv = s.get(db.Proposition, r1.movement_id)
            kinds = {p.kind for p in s.query(db.Proposition).filter(
                (db.Proposition.subject_payment_id == r1.payment_id) | (db.Proposition.object_payment_id == r1.payment_id)).all()}
        check("s236 B3 \"that was my payment to AEP\": a payment minted by the answering person, the bank's line relayed and tied to it",
              v1['payment']['payee'] == 'AEP OHIO' and v1['payment']['by'] == 'S236 Rob'
              and mv.kind == 'movement' and mv.subject_party_id == ba.party_id
              and kinds >= {'proposition_concerns', 'amount', 'occurred_on', 'paid_to'})
        again = post(f'/api/accounts/line-statement/{l1}', {'payee': 'AEP OHIO'})
        money_in = post(f'/api/accounts/line-statement/{pay_id}', {'payee': 'Employer'})
        check('s236 B3 one payment per line; money in is never "my payment"', again.status_code == 400 and money_in.status_code == 400)
        post(f'/api/accounts/line-statement/{l2}', {'payee': 'AEP OHIO'})
        v3 = data(post(f'/api/accounts/line-statement/{l3}', {'payee': 'AEP OHIO'}))
        check('s236 B3 after three answers for one payee a standing statement is suggested - offered, not made',
              v3['suggest_standing'] and v3['suggest_standing']['answers'] == 3 and v3['suggest_standing']['covers'] == 1
              and not data(c.get('/api/accounts/standing', headers=H))['standing'])
        with db_session() as s:
            kro_rec = hs.record_of(s, kro)
        check('s236 B3 a line no one spoke about is no payment', kro_rec is None)

        # ── B2 first: a line is relayed as its bank's statement, so the bank is named before anything is said ──
        post('/api/import/commit', {'account_id': cid, 'records': [rec('2026-07-11', 'S236 FARM STAND', 25.00)]})
        post('/api/import/commit', {'account_id': bid, 'records': [rec('2026-07-12', 'S236 TRANSFER OUT', 30.00)]})
        with db_session() as s:
            farm = s.query(Transaction).filter_by(account_id=cid, description='S236 FARM STAND').first().id
            sav = s.query(Transaction).filter_by(account_id=bid, description='S236 TRANSFER OUT').first().id
            u_before, p_before = count(s, 'utterances'), count(s, 'payments')
        nb = post(f'/api/accounts/line-statement/{farm}', {'payee': 'Farm stand'})
        st_nb = post('/api/accounts/standing', {'account_id': cid, 'payee': 'FARM STAND'})
        with db_session() as s:
            unchanged_nb = count(s, 'utterances') == u_before and count(s, 'payments') == p_before
        check("s236 B2 an account nobody has named a bank for: the statement asks which bank first, and writes nothing",
              nb.status_code == 409 and (nb.get_json() or {}).get('need_bank', {}).get('account_id') == cid
              and st_nb.status_code == 409 and unchanged_nb)
        own = data(post(f'/api/accounts/line-statement/{sav}', {'payee': 'Savings move'}))
        with db_session() as s:
            mv_own = s.get(db.Proposition, hs.record_of(s, sav).movement_id)
        check("s236 B2 an account said not to be a bank account: the line is the household's own record (the person answering)",
              own['payment'] and mv_own.subject_party_id == rob_party)

        # ── B3, the standing statement ────────────────────────────────────────
        prev = data(c.get(f'/api/accounts/standing?account_id={aid}&payee=AEP%20OHIO', headers=H))['covers']
        st = data(post('/api/accounts/standing', {'account_id': aid, 'payee': 'AEP OHIO'}))
        check('s236 B3 a standing statement covers the lines already here (shown before the yes) and is listed, dated, by whom',
              prev == 1 and st['payments'] == 1 and st['standing'][0]['payee'] == 'AEP OHIO'
              and st['standing'][0]['by'] == 'S236 Rob' and st['standing'][0]['said_on'])
        imp = data(post('/api/import/commit', {'account_id': aid, 'records': [
            rec('2026-08-01', 'S236 AEP OHIO 1005', 140.00), rec('2026-08-02', 'S236 COLUMBIA GAS', 40.00),
            rec('2026-08-03', 'S236 AEP OHIO REFUND', 10.00, 'credit')]}))
        with db_session() as s:
            new_aep = hs.record_of(s, line(s, 'S236 AEP OHIO 1005'))
            gas = hs.record_of(s, line(s, 'S236 COLUMBIA GAS'))
            refund = hs.record_of(s, line(s, 'S236 AEP OHIO REFUND'))
            stmt = s.get(db.StandingStatement, st['id'])
        check('s236 B3 a new debit the statement covers becomes a payment by that statement; others do not, nor money in',
              imp['standing_payments'] == 1 and new_aep and new_aep.via == 'standing' and new_aep.utterance_id == stmt.utterance_id
              and gas is None and refund is None)
        wd = data(post(f"/api/accounts/standing/{st['id']}/withdraw", {}))
        data(post('/api/import/commit', {'account_id': aid, 'records': [rec('2026-09-01', 'S236 AEP OHIO 1006', 150.00)]}))
        with db_session() as s:
            after_wd = hs.record_of(s, line(s, 'S236 AEP OHIO 1006'))
            still = hs.record_of(s, line(s, 'S236 AEP OHIO 1005'))
        check('s236 B3 withdrawing stops new lines and undoes nothing already recorded',
              wd['standing'][0]['withdrawn_on'] and after_wd is None and still is not None and still.payment_id)

        # ── B4: the care-for answer ───────────────────────────────────────────
        with db_session() as s:
            clinic, dental = line(s, 'S236 MERCY CLINIC'), line(s, 'S236 DENTAL ARTS')
        sam = data(post('/api/accounts/people', {'name': 'S236 Sam'}))
        sam_id = (sam.get('person') or {}).get('id') if isinstance(sam, dict) and sam.get('person') else None
        with db_session() as s:
            sam_id = sam_id or s.query(Person).filter_by(display_name='S236 Sam').first().id
            kim = Person(display_name='S236 Kim', active=True); s.add(kim); s.commit(); kim_id = kim.id
        post('/api/accounts/care-for', {'transaction_id': clinic, 'person_id': sam_id})
        with db_session() as s:
            rc = hs.record_of(s, clinic)
            inc = s.query(db.Proposition).filter_by(kind='incurred_by', object_expense_id=rc.expense_id).all() if rc else []
            in_respect = s.query(db.Proposition).filter_by(kind='payment_in_respect_of', object_expense_id=rc.expense_id).count() if rc else 0
            sam_party = s.get(Person, sam_id).party.id
        check("s236 B4 \"for Sam\" with someone answering: an expense minted by the answer, incurred_by Sam, the payment toward it",
              rc and rc.expense_id and len(inc) == 1 and inc[0].subject_party_id == sam_party and in_respect == 1)
        post('/api/accounts/care-for', {'transaction_id': clinic, 'person_id': kim_id})
        with db_session() as s:
            rc2 = hs.record_of(s, clinic)
            inc2 = s.query(db.Proposition).filter_by(kind='incurred_by', object_expense_id=rc2.expense_id).count()
            n_exp = s.query(db.LedgerLineRecord).filter_by(transaction_id=clinic).count()
        check('s236 B4 a change of person is a new claim on the same expense; the earlier one stays',
              rc2.expense_id == rc.expense_id and inc2 == 2 and n_exp == 1)
        with db_session() as s:
            no_exp = hs.record_of(s, l1).expense_id is None
        check('s236 B4 a payment is never assumed to be an expense', no_exp)
        post('/api/import/commit', {'account_id': cid, 'records': [rec('2026-07-13', 'S236 EYE CARE', 45.00, cat=health_name)]})
        with db_session() as s:
            eye = s.query(Transaction).filter_by(account_id=cid, description='S236 EYE CARE').first().id
            u_b = count(s, 'utterances')
        r_eye = post('/api/accounts/care-for', {'transaction_id': eye, 'person_id': sam_id})
        with db_session() as s:
            eye_waits = hs.record_of(s, eye) is None and count(s, 'utterances') == u_b \
                and s.query(CareFor).filter_by(transaction_id=eye).count() == 1
        waiting = [x for x in data(c.get('/api/accounts/earlier-answers', headers=H))['answers'] if x['line']['id'] == eye]
        check('s236 B4 a care answer on an account with no bank named is kept as before and waits - nothing half-written',
              r_eye.status_code == 200 and eye_waits and len(waiting) == 1)

        # ── B8 ────────────────────────────────────────────────────────────────
        cands = data(c.get('/api/accounts/reversals', headers=H))['candidates']
        shoe = next((x for x in cands if x['credit']['description'] == 'REFUND S236 SHOE STORE 9'), None)
        check('s236 B8 a money-in line that may undo a charge is suggested, with the charge', shoe and shoe['debit']['description'] == 'S236 SHOE STORE 9')
        with db_session() as s:
            t_before = total(s)
        post('/api/accounts/reversals', {'credit_id': shoe['credit']['id'], 'debit_id': shoe['debit']['id'], 'answer': 'yes'})
        with db_session() as s:
            pc = hs.record_of(s, shoe['credit']['id']); pd = hs.record_of(s, shoe['debit']['id'])
            rel = s.query(db.Proposition).filter_by(kind='payment_counteracts', subject_payment_id=pc.payment_id,
                                                    object_payment_id=pd.payment_id).count()
            t_after = total(s)
        left = data(c.get('/api/accounts/reversals', headers=H))['candidates']
        check('s236 B8 a yes is the household\'s claim (payment_counteracts, the money back as another payment); nothing netted',
              rel == 1 and t_before == t_after and not any(x['credit']['id'] == shoe['credit']['id'] for x in left))

        # ── B11: earlier answers ──────────────────────────────────────────────
        with db_session() as s:
            s.query(AppSetting).filter_by(key='speaker_person_id').delete(); s.commit()
        post('/api/accounts/care-for', {'transaction_id': dental, 'person_id': sam_id})     # no one answering
        with db_session() as s:
            chase = line(s, 'S236 CHASE CARD PMT')
            d = DebtAccount(name='S236 Chase'); s.add(d); s.flush(); debt_id = d.id
            e = DebtLedgerEntry(debt_account_id=d.id, entry_type='payment', amount=200.0, entry_date=date(2026, 7, 8),
                                linked_checking_transaction_id=chase); s.add(e); s.flush()
            s.add(CheckingTransactionLink(checking_transaction_id=chase, debt_ledger_entry_id=e.id, link_indicator='payment_to_card',
                                          user_confirmed_at=datetime(2026, 7, 10))); s.commit()
            dent_rec = hs.record_of(s, dental)
        ea = data(c.get('/api/accounts/earlier-answers', headers=H))
        mine = [x for x in ea['answers'] if x['line']['id'] in (dental, chase)]
        check('s236 B11 an answer given with no one answering is kept as before, minted nothing, and waits to be confirmed',
              dent_rec is None and len(mine) == 2 and ea['person_id'] is None)
        refused = post('/api/accounts/earlier-answers', {'items': [{'source': x['source'], 'source_id': x['source_id']} for x in mine]})
        post('/api/accounts/speaker', {'person_id': sp['person_id']})
        ok_ = data(post('/api/accounts/earlier-answers', {'items': [{'source': x['source'], 'source_id': x['source_id']} for x in mine]}))
        with db_session() as s:
            dr, cr = hs.record_of(s, dental), hs.record_of(s, chase)
            u = s.get(db.Utterance, dr.utterance_id)
            content = json.loads(u.content)
            toward = s.query(db.Proposition).filter_by(kind='payment_in_respect_of_obligation', subject_payment_id=cr.payment_id).first()
            ob = s.get(db.Obligation, toward.object_obligation_id) if toward else None
            first = {x['source']: x['first_said'] for x in content['answers']}
        check("s236 B11 \"these were mine\": one statement by the person today, each answer's first date kept, the same statement in 2.0",
              refused.status_code == 409 and ok_['confirmed'] == 2 and u.origin_party_id == rob_party
              and first.get('debt') == '2026-07-10' and dr.expense_id and ob is not None and ob.minted_by_id == u.id
              and not [x for x in ok_['answers'] if x['line']['id'] in (dental, chase)])

        # ── through it all ────────────────────────────────────────────────────
        with db_session() as s:
            audits = (db.payments_without_minting_utterance(s), db.expenses_without_minting_utterance(s),
                      db.obligations_without_minting_utterance(s), db.parties_without_one_anchor(s))
            bad_props = [p.id for p in s.query(db.Proposition).filter(db.Proposition.id > snap['propositions']).all()
                         if db.participant_violations(p)]
            unchanged = round(total(s) - before_total, 2) == round(140 + 40 + 10 + 150 + 25 + 30 + 45, 2)   # the lines imported here, nothing else
        check('s236 every payment, expense, obligation and institution here was minted by a person\'s statement; every claim well-formed',
              not any(audits) and not bad_props)
        check('s236 statements change no total (only the imported lines moved the sum)', unchanged)
        src = open(ctx.BASE / 'core' / 'household_statements.py', encoding='utf-8').read()
        check('s236 nothing in the statements module logs', 'logging' not in src and 'print(' not in src)
    finally:
        with db_session() as s:
            ids = [t.id for t in s.query(Transaction).filter(Transaction.account_id.in_([aid, bid, cid])).all()]
            for t in ('evidence', 'propositions', 'ledger_line_records', 'earlier_answers', 'reversal_answers',
                      'standing_statements', 'account_banks', 'payments', 'expenses', 'obligations'):
                s.execute(text(f'DELETE FROM {t} WHERE id > :n'), {'n': snap[t]})
            s.execute(text('DELETE FROM parties WHERE id > :n AND minted_by_id IS NOT NULL'), {'n': snap['parties']})
            s.execute(text('DELETE FROM utterances WHERE id > :n'), {'n': snap['utterances']})
            for t in ('care_for', 'checking_transaction_links', 'debt_ledger_entries'):
                s.execute(text(f'DELETE FROM {t} WHERE id > :n'), {'n': snap[t]})
            s.execute(text('DELETE FROM parties WHERE id > :n'), {'n': snap['parties']})
            s.execute(text('DELETE FROM people WHERE id > :n'), {'n': snap['people']})
            s.query(DebtAccount).filter(DebtAccount.name == 'S236 Chase').delete()
            s.query(db.SetAsideTransaction).filter(db.SetAsideTransaction.account_id.in_([aid, bid, cid])).delete(synchronize_session=False)
            s.query(Transaction).filter(Transaction.id.in_(ids)).delete(synchronize_session=False)
            s.query(Account).filter(Account.id.in_([aid, bid, cid])).delete(synchronize_session=False)
            s.query(AppSetting).filter_by(key='speaker_person_id').delete()
            if had_speaker is not None:
                s.add(AppSetting(key='speaker_person_id', value=had_speaker))
            s.commit()
