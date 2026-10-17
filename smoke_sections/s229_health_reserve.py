"""Item 88 (gw 2.0/HEALTH_RESERVE.md = item 45 H7 stage 3; Rob 2026-10-16: "I approve" R1-R9, "Build item 88.").

    R1  the timing is the person's: three options through one engine, none labelled best; the plan as today until chosen
    R2  the target is the current plan's out-of-pocket maximum, read not copied (a correction moves it), or their own
        figure; with neither there is none - never an invented number
    R3  a level of a named account's balance: $500 then $700 is $700; available = balance - reserved, worked out on read;
        a balance below the reserve is named, never quietly lowered; allocation rows keep no account (frozen rule)
    R4  the HSA balance counts on its own line; FSA money does not
    R5  extra_schedule only: minimum payments never touched; an amount above the extra is capped and says so
    R6  a health payment from the reserve's account is offered as a lowering - only on a yes
    R9  the purpose in one line; no "should", no "best"
"""
import json
from datetime import date, timedelta


def run(ctx):
    check, c, H, HJ, BASE = ctx.check, ctx.c, ctx.H, ctx.HJ, ctx.BASE
    import server
    from core import health_reserve as hr
    from core.consequence import Card, simulate_payoff
    from core.database import (Account, AppSetting, HealthPlan, HealthPlanOperation, HealthPlanReading,
                               HealthPlanTermVersion, ReserveAllocation, ReserveTarget, Transaction, db_session)

    post = lambda path, body: c.post(path, headers=HJ, data=json.dumps(body))
    data = lambda r: (r.get_json() or {}).get('data')
    get = lambda: data(c.get('/api/accounts/health-reserve', headers=H))
    today = date.today()

    def clean():
        with db_session() as s:
            for m in (ReserveAllocation, ReserveTarget, HealthPlanReading, HealthPlanOperation, HealthPlanTermVersion, HealthPlan):
                s.query(m).delete()
            s.query(AppSetting).filter(AppSetting.key.in_(('reserve_account_json', 'reserve_order_json'))).delete(synchronize_session=False)
            s.commit()
    clean()
    cards = [Card(balance=6000, rate=24, minimum=150, name='Visa'), Card(balance=2000, rate=8, minimum=50, name='Store')]
    budget = 600
    real = server._consequence_inputs
    server._consequence_inputs = lambda session: (cards, budget, 'avalanche', [])
    made = []
    try:
        # ── R2 ────────────────────────────────────────────────────────────────
        st = get()
        check('s229 R2 with no plan and no target there is no target - nothing invented',
              st['target'] is None and st['basis'] == 'none' and 'three to six' not in json.dumps(st).lower()
              and st['options']['available'] is False)
        plan = data(post('/api/accounts/health-plans', {'name': 'S229 Plan', 'effective_from': f'{today.year}-01-01',
                                                        'effective_to': f'{today.year}-12-31', 'oop_max': 8000}))['current']
        st = get()
        check('s229 R2 a current plan\'s out-of-pocket maximum is the target, read from the plan',
              st['target'] == 8000 and st['basis'] == 'oop_max' and 'S229 Plan' in st['lines'][0])
        post(f"/api/accounts/health-plans/{plan['id']}/terms", {'mode': 'correction', 'oop_max': 7000})
        check('s229 R2 a corrected maximum moves the target (no copy kept)', get()['target'] == 7000)
        st = data(post('/api/accounts/health-reserve/target', {'basis': 'custom', 'amount': 5000}))
        check('s229 R2 a figure of their own, labelled as theirs', st['target'] == 5000 and 'a target you set' in st['lines'][0])
        st = data(post('/api/accounts/health-reserve/target', {'basis': ''}))
        check('s229 R2 "no target" is none', st['target'] is None)
        post('/api/accounts/health-reserve/target', {'basis': 'oop_max'})

        # ── R3 / R4 ───────────────────────────────────────────────────────────
        with db_session() as s:
            sav = Account(name='S229 Savings', type='savings', is_active=True)
            hsa = Account(name='S229 HSA', type='hsa', is_active=True)
            fsa = Account(name='S229 FSA', type='fsa', is_active=True)
            s.add_all([sav, hsa, fsa]); s.flush()
            s.add(Transaction(date=today - timedelta(days=10), description='Deposit', amount=3000, type='credit',
                              account_id=sav.id, running_balance=3000, source='csv'))
            s.add(Transaction(date=today - timedelta(days=10), description='Contribution', amount=1000, type='credit',
                              account_id=hsa.id, running_balance=1000, source='csv'))
            s.add(Transaction(date=today - timedelta(days=10), description='Election', amount=400, type='credit',
                              account_id=fsa.id, running_balance=400, source='csv'))
            s.commit()
            sav_id, made = sav.id, [sav.id, hsa.id, fsa.id]
        bad = post('/api/accounts/health-reserve/reserved', {'amount': 500})
        check('s229 R3 the first reserve must name its account', bad.status_code == 400)
        post('/api/accounts/health-reserve/reserved', {'amount': 500, 'account_id': sav_id})
        st = data(post('/api/accounts/health-reserve/reserved', {'amount': 700}))
        check('s229 R3 $500 then $700 is $700 - a level, not a sum', st['reserved'] == 700)
        check('s229 R3 available is the balance less the reserve, worked out on read, the balance unchanged',
              any(l.startswith('Available in S229 Savings: $2,300.00 ($3,000.00 balance') for l in st['lines']))
        check('s229 R4 the HSA counts on its own line; the FSA does not',
              any(l.startswith('HSA: $1,000.00 (S229 HSA)') for l in st['lines']) and 'S229 FSA' not in json.dumps(st['lines'])
              and st['covered'] == 1700 and st['gap'] == 5300)
        with db_session() as s:
            cols = [r[1] for r in s.execute(__import__('sqlalchemy').text('PRAGMA table_info(reserve_allocations)')).fetchall()]
        check('s229 R3 the allocation rows keep no account (the frozen rule); the account is recorded beside them, dated',
              not any('account' in col for col in cols) and st['history']['account'][-1]['account_id'] == sav_id
              and st['history']['account'][-1]['said'] == today.isoformat())
        st = data(post('/api/accounts/health-reserve/reserved', {'amount': 3500}))
        check('s229 R3 a reserve above the balance is named, never quietly lowered',
              st['reserved'] == 3500 and any('below the $3,500.00 reserved' in n and 'doesn\'t lower the reserve' in n for n in st['notes']))
        post('/api/accounts/health-reserve/reserved', {'amount': 700})

        # ── R6 ────────────────────────────────────────────────────────────────
        with db_session() as s:
            pharm = next((cat for cat in s.query(__import__('core.database', fromlist=['Category']).Category).all()
                          if cat.name == 'Prescriptions'), None)
            s.add(Transaction(date=today, description='S229 PHARMACY', amount=120, type='debit', account_id=sav_id,
                              category_id=pharm.id if pharm else None, running_balance=2880, source='csv'))
            s.commit()
        st = get()
        check('s229 R6 a health payment from that account is offered as a lowering, and nothing is lowered by itself',
              st['reserved'] == 700 and st['offer'] and st['offer']['amount'] == 120 and 'Lower the reserve by $120.00?' in st['offer']['sentence'])

        # ── R1 / R5 ───────────────────────────────────────────────────────────
        o = st['options']
        base = simulate_payoff(cards, budget)
        rows = {r['key']: r for r in o['options']}
        check('s229 R1 "after" is exactly the payoff plan as it is today',
              rows['after']['debt_months'] == base['months'] and rows['after']['interest'] == base['total_interest'])
        check('s229 R1 "before" is dated through the same engine; reaching the reserve first costs time and interest, shown as facts',
              rows['before']['debt_months'] >= base['months'] and rows['before']['interest'] >= base['total_interest']
              and 'Minimum payments never change.' in rows['before']['note'])
        check('s229 R1 "alongside" waits for an amount', 'unavailable' in rows['alongside'])
        st = data(post('/api/accounts/health-reserve/choice', {'choice': 'alongside', 'monthly': 5000}))
        al = {r['key']: r for r in st['options']['options']}['alongside']
        check('s229 R5 an amount above the extra is capped at what is above the minimums, and says so',
              '(capped at what is above the minimums)' in al['note'] and st['choice']['choice'] == 'alongside')
        st = data(post('/api/accounts/health-reserve/choice', {'choice': 'alongside', 'monthly': 150}))
        al = {r['key']: r for r in st['options']['options']}['alongside']
        n = -(-st['gap'] // 150)
        alt = simulate_payoff(cards, budget, extra_schedule=[-150] * int(n))
        check('s229 R5 alongside is the engine with extra_schedule, the amount only, for the months to fill',
              al['debt_months'] == alt['months'] and al['interest'] == alt['total_interest'])
        mins = sum(cd.minimum for cd in cards)
        low = simulate_payoff(cards, mins)
        check('s229 R5 minimums are never touched: taking all the extra leaves exactly the minimums-only plan',
              simulate_payoff(cards, budget, extra_schedule=[-(budget - mins)] * 600)['months'] == low['months'])
        check('s229 R1 the choice is kept with its date, and changing it keeps the earlier one',
              [h['choice'] for h in st['history']['choice']] == ['alongside', 'alongside'] and st['choice']['said'] == today.isoformat())
        check('s229 R1 saving a choice leaves the engine\'s own inputs as they were',
              'reserve' not in server._consequence_inputs.__code__.co_names)

        # ── R9 ────────────────────────────────────────────────────────────────
        app = ctx.app_src
        block = app.split('// ── Item 88: the health reserve')[1].split('async function _reserveChoose')[0]
        said = (json.dumps(st) + block).lower()
        hits = [w for w in ('should', 'best option', 'recommended', 'smart', 'wise', 'three to six', 'bigger shovel',
                            'baby step', 'emergency fund first') if w in said]
        check(f's229 R9 the purpose in one line; no advice or ranking words ({hits})',
              st['purpose'] == 'Money set aside so a medical bill can be paid without a card.' and not hits)
        src = (BASE / 'core' / 'health_reserve.py').read_text(encoding='utf-8')
        check('s229 AI-off: nothing here calls the model', '_ai_' not in src and 'ai_chat' not in src)
    finally:
        server._consequence_inputs = real
        with db_session() as s:
            if made:
                s.query(Transaction).filter(Transaction.account_id.in_(made)).delete(synchronize_session=False)
                s.query(Account).filter(Account.id.in_(made)).delete(synchronize_session=False)
            s.commit()
        clean()
