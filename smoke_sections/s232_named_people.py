"""Item 92 (gw 2.0/NAMED_PEOPLE.md = item 45 H7 stage 5; Rob 2026-10-16: N1-N8 as recommended; 2026-10-17: N8 "tag now,
absorb later").

    N1  a person is a name: rename moves nothing; a person with history is made inactive, one without is removed
    N2  whom care was for is said payment by payment, never inferred; only health payments; "Household" = not said
    N3  names are labels, not locks - said where a person is added
    N4  an answer is kept: a change is a correction, the earlier one stays; the same-payee offer acts only on a yes
    N5  (a) the visit report for one person, the rest listed apart; (b) per-person readings in a family plan;
        (c) the per-person split under the household total, which moving a payment never changes
    N6  household mode's names are offered, never copied
    N7  names never reach the model's context, the AI log or the log scrubber ("Rob's Income" stays whole)
    N8  the tag is the household's answer on the ledger row (care_for), nothing else mints anything
"""
import ast
import json
from datetime import date


def run(ctx):
    check, c, H, HJ, BASE = ctx.check, ctx.c, ctx.H, ctx.HJ, ctx.BASE
    from core import health_boundary as hb
    from core import people as pp
    from core.database import (Account, AppSetting, CareFor, Category, Expense, HealthPlan, HealthPlanOperation,
                               HealthPlanReading, HealthPlanTermVersion, Party, Payment, Person, Transaction, db_session)

    post = lambda path, body: c.post(path, headers=HJ, data=json.dumps(body))
    data = lambda r: (r.get_json() or {}).get('data')
    y = date.today().year
    d1, d2, d3 = date(y, 2, 1), date(y, 3, 1), date(y, 4, 1)
    P = 'S232 BIRCH PEDIATRICS'

    with db_session() as s:
        s.query(CareFor).delete(); s.commit()
        doc = s.query(Category).filter_by(name='Doctor / Co-pays').first()
        if not doc:
            doc = Category(name='Doctor / Co-pays', type='expense'); s.add(doc); s.flush()
        food = s.query(Category).filter_by(name='Dining Out').first() or Category(name='Dining Out', type='expense')
        s.add(food); s.flush()
        a = Account(name='S232 Joint Checking', type='checking', is_active=True); s.add(a); s.flush()
        rows = [Transaction(date=d, description=P, amount=amt, type='debit', category_id=doc.id, account_id=a.id,
                            card_last4='4242', source='csv') for d, amt in ((d1, 120), (d2, 80), (d3, 50))]
        meal = Transaction(date=d1, description='S232 BISTRO', amount=40, type='debit', category_id=food.id,
                           account_id=a.id, source='csv')
        s.add_all(rows + [meal]); s.commit()
        t1, t2, t3, tm = [x.id for x in rows] + [meal.id]
        acct_id = a.id
        exp0, pay0 = s.query(Expense).count(), s.query(Payment).count()

    made_people = []
    try:
        # ── N1 / N3 ───────────────────────────────────────────────────────────
        st = data(post('/api/accounts/people', {'name': 'S232 Sam'}))
        sam = next(p for p in st['people'] if p['name'] == 'S232 Sam')['id']
        st = data(post('/api/accounts/people', {'name': 'S232 Rob'}))
        rob = next(p for p in st['people'] if p['name'] == 'S232 Rob')['id']
        made_people += [sam, rob]
        dup = post('/api/accounts/people', {'name': 's232 sam'})
        check('s232 N1 a person is a name; the same name twice is refused', dup.status_code == 400)
        check('s232 N3 names are labels, not locks - said where people are added',
              'Anyone who opens Groundwork on this computer can see everything here' in st['visibility'])
        with db_session() as s:
            check('s232 N1 each person gets their party anchor in the same step', s.query(Party).filter_by(person_id=sam).first() is not None)

        # ── N2 ────────────────────────────────────────────────────────────────
        g1 = data(c.get(f'/api/accounts/care-for/{t1}', headers=H))
        gm = data(c.get(f'/api/accounts/care-for/{tm}', headers=H))
        check('s232 N2 a health payment has no person until one is said; a non-health payment has no slot',
              g1['health'] and g1['person_id'] is None and not g1['answered'] and gm['health'] is False)
        bad = post('/api/accounts/care-for', {'transaction_id': tm, 'person_id': sam})
        check('s232 N2 only a health payment can say whom it was for', bad.status_code == 400)
        r = data(post('/api/accounts/care-for', {'transaction_id': t1, 'person_id': sam}))
        with db_session() as s:
            cur = pp.currents(s)
        check('s232 N2 never inferred: one answer touches only its own payment (same payee, same card, same account)',
              cur.get(t1) == sam and t2 not in cur and t3 not in cur)
        check('s232 N4 the same-payee offer lists only unanswered payments, and assigns nothing by itself',
              r['offer'] and sorted(r['offer']['ids']) == sorted([t2, t3]) and t2 not in cur)

        # ── N4 ────────────────────────────────────────────────────────────────
        post('/api/accounts/care-for', {'transaction_id': t1, 'person_id': rob})
        again = post('/api/accounts/care-for', {'transaction_id': t1, 'person_id': rob})
        with db_session() as s:
            hist = pp.history(s, t1)
            n_rows = s.query(CareFor).filter_by(transaction_id=t1).count()
        check('s232 N4 a change is a correction; the earlier answer stays; the same answer again writes nothing',
              [h['person'] for h in hist] == ['S232 Sam', 'S232 Rob'] and [h['mode'] for h in hist] == ['initial', 'correction']
              and n_rows == 2 and again.status_code == 200)
        post('/api/accounts/care-for', {'ids': [t2], 'person_id': sam})
        post('/api/accounts/care-for', {'transaction_id': t3, 'person_id': 'household'})
        with db_session() as s:
            cur = pp.currents(s)
        check('s232 N4 / N2 the offer acts on a yes; "Household" is said explicitly and means not said',
              cur.get(t2) == sam and t3 in cur and cur[t3] is None)

        # ── N5a ───────────────────────────────────────────────────────────────
        rep = data(post('/api/accounts/visit-report', {'names': [P], 'person_id': sam}))
        check('s232 N5a the visit report for one person: their payments only; the rest listed apart, counted for no one',
              rep['person'] == 'S232 Sam' and [p['amount'] for p in rep['payments']] == [80.0]
              and rep['summary'].startswith(f'1 payment to {P} for S232 Sam')
              and rep['not_said'] and len(rep['not_said']['lines']) == 1)

        # ── N5c ───────────────────────────────────────────────────────────────
        q = lambda: data(c.get(f'/api/year-end?year={y}&include_health=1', headers=H))['health_schedule_a']
        sa1 = q()
        split1 = {b['name']: b['total'] for b in sa1['by_person']}
        post('/api/accounts/care-for', {'transaction_id': t2, 'person_id': rob})
        sa2 = q()
        split2 = {b['name']: b['total'] for b in sa2['by_person']}
        check('s232 N5c the per-person split sits under the household total, and moving a payment never changes the total',
              split1.get('S232 Rob', 0) + 80 == split2.get('S232 Rob', 0) and sa1['total'] == sa2['total']
              and 'Not said' in split2)
        off = data(c.get(f'/api/year-end?year={y}&include_health=0', headers=H))
        check('s232 N7 names appear in the packet only on the health tick', 'S232 Sam' not in json.dumps(off) and 'S232 Rob' not in json.dumps(off))

        # ── N5b ───────────────────────────────────────────────────────────────
        with db_session() as s:
            for m in (HealthPlanReading, HealthPlanOperation, HealthPlanTermVersion, HealthPlan):
                s.query(m).delete()
            s.commit()
        plan = data(post('/api/accounts/health-plans', {'name': 'S232 Family Plan', 'effective_from': f'{y}-01-01',
                                                        'effective_to': f'{y}-12-31', 'tier': 'family',
                                                        'deductible': 4000, 'oop_max': 10000}))['current']
        check('s232 N5b a family plan says per-person amounts can be entered, not that they "aren\'t tracked"',
              'Per-person amounts: none entered yet. Your insurer shows them member by member.' in plan['notes'])
        st = data(post(f"/api/accounts/health-plans/{plan['id']}/readings", {'deductible_met': 600, 'oop_met': 800,
                                                                             'as_of': f'{y}-03-01', 'person_id': sam}))
        cp = st['current']
        check('s232 N5b one person\'s figures, from the insurer, beside the plan\'s own (which stay not entered)',
              cp['lines'][0] == 'Deductible: $4,000.00. Met so far: not entered yet.'
              and any(l.startswith('S232 Sam: $600.00 toward the deductible as of') and l.endswith('(from your insurer).')
                      for l in cp['lines']))

        # ── N1: removal ───────────────────────────────────────────────────────
        st = data(post('/api/accounts/people', {'name': 'S232 Temp'}))
        tmp = next(p for p in st['people'] if p['name'] == 'S232 Temp')['id']
        r1 = data(post(f'/api/accounts/people/{tmp}/remove', {}))
        r2 = data(post(f'/api/accounts/people/{sam}/remove', {}))
        with db_session() as s:
            gone = s.get(Person, tmp) is None and s.query(Party).filter_by(person_id=tmp).first() is None
            kept = s.get(Person, sam)
        check('s232 N1 a person with no history is removed (with their anchor); one with history is made inactive',
              r1['done'] == 'deleted' and gone and r2['done'] == 'inactive' and kept is not None and kept.active is False)
        post(f'/api/accounts/people/{rob}/rename', {'name': 'S232 Robert'})
        with db_session() as s:
            cur = pp.currents(s)
        check('s232 N1 a rename moves nothing: the answers point at the person, not the name', cur.get(t1) == rob)

        # ── N6 ────────────────────────────────────────────────────────────────
        with db_session() as s:
            saved = {k: (lambda r: r.value if r else None)(s.query(AppSetting).filter_by(key=k).first())
                     for k in ('household_mode', 'household_user1', 'household_user2')}
            for k, v in (('household_mode', 'true'), ('household_user1', 'S232 Alex'), ('household_user2', 'S232 Robert')):
                row = s.query(AppSetting).filter_by(key=k).first()
                if row:
                    row.value = v
                else:
                    s.add(AppSetting(key=k, value=v))
            s.commit()
        st = data(c.get('/api/accounts/people', headers=H))
        with db_session() as s:
            no_alex = s.query(Person).filter_by(display_name='S232 Alex').first() is None
            for k, v in saved.items():
                row = s.query(AppSetting).filter_by(key=k).first()
                if v is None:
                    if row:
                        s.delete(row)
                else:
                    row.value = v
            s.commit()
        check('s232 N6 household mode\'s names are offered - only the one not yet a person - and never copied',
              st['offer'] == ['S232 Alex'] and no_alex)

        # ── N7 / N8 ───────────────────────────────────────────────────────────
        with db_session() as s:
            hb.refresh(s)
        check('s232 N7 names are not added to the log scrubber ("S232 Robert\'s Income" stays whole)',
              hb.scrub("S232 Robert's Income") == "S232 Robert's Income")
        srv = ctx.server_src
        tree = ast.parse(srv)
        ai_fns = [fn for fn in ast.walk(tree) if isinstance(fn, ast.FunctionDef)
                  and any(isinstance(n, ast.Call) and (getattr(n.func, 'id', None) or getattr(n.func, 'attr', None))
                          in ('_ai_chat_local', '_ai_chat_stream', '_ai_log_write') for n in ast.walk(fn))]
        leaks = [fn.name for fn in ai_fns if 'display_name' in ast.unparse(fn) or 'people' in ast.unparse(fn).split('import')[-1][:0]]
        hbsrc = (BASE / 'core' / 'health_boundary.py').read_text(encoding='utf-8')
        check(f's232 N7 nothing that reaches the model or the AI log reads a person\'s name ({leaks})',
              ai_fns and not leaks and "'people'" not in hbsrc)
        with db_session() as s:
            minted = (s.query(Expense).count(), s.query(Payment).count())
        check('s232 N8 an answer is a tag on the ledger row; it mints no expense or payment (that waits on the bank side)',
              minted == (exp0, pay0))
    finally:
        with db_session() as s:
            s.query(CareFor).delete()
            for m in (HealthPlanReading, HealthPlanOperation, HealthPlanTermVersion, HealthPlan):
                s.query(m).delete()
            s.query(Transaction).filter(Transaction.id.in_([t1, t2, t3, tm])).delete(synchronize_session=False)
            s.query(Account).filter_by(id=acct_id).delete()
            for pid in made_people:
                s.query(Party).filter_by(person_id=pid).delete()
                s.query(Person).filter_by(id=pid).delete()
            s.commit()
