"""Putting a trip on a card (gw 2.0/TRIP_ON_CREDIT.md, item 49; Rob 2026-10-08: R1-R7 approved as recommended).

    R1  a third option, the user's credit cards only, available credit only where a limit is entered
    R2  3 / 6 / 12-month payoffs at the card's APR, verified against the amortisation formula, and the whole plan at
        current payments
    R3  each row says what is left of the surplus, as a fact - never "afford"
    R4  the grace period and the APR are named as assumptions
    R5  the user's own savings rate from 6 complete months of income, or a rate they pick - never "good"
    R6  choosing a card saves nothing
    R7  render-level: the real routes, then the real renderer
"""
import json
import re
import shutil
import subprocess

VERDICTS = re.compile(r'\b(afford|can\'t afford|should|recommend|good|bad|wise|unwise|don\'t|avoid)\b', re.I)


def _fn(src, name):
    m = re.search(r'\nfunction ' + name + r'\(.*?\n\}\n', src, re.S)
    return m.group(0) if m else ''


def run(ctx):
    check, c, H, BASE, app, html = ctx.check, ctx.c, ctx.H, ctx.BASE, ctx.app_src, ctx.html_src
    from core.database import DebtAccount, db_session
    from core.trip_card import payoff_rows

    made = []
    try:
        with db_session() as session:
            rows = [DebtAccount(name='s161 Visa', current_balance=1000.0, interest_rate=22.0, minimum_payment=40.0,
                                credit_limit=5000.0, debt_type='credit', is_active=True),
                    DebtAccount(name='s161 Store Card', current_balance=600.0, interest_rate=0.0, minimum_payment=25.0,
                                credit_limit=None, debt_type='credit', is_active=True),
                    DebtAccount(name='s161 Small Card', current_balance=900.0, interest_rate=18.0, minimum_payment=30.0,
                                credit_limit=1500.0, debt_type='credit', is_active=True),
                    DebtAccount(name='s161 Car Loan', current_balance=9000.0, interest_rate=6.0, minimum_payment=250.0,
                                debt_type='loan', is_active=True)]
            session.add_all(rows)
            session.commit()
            made = [r.id for r in rows]
        visa, store, small, loan = made

        cards = c.get('/api/trip/cards', headers=H).get_json()['data']['cards']
        by = {x['name']: x for x in cards}
        check('s161 R1 the list holds the credit cards and not the loan',
              's161 Visa' in by and 's161 Store Card' in by and 's161 Car Loan' not in by)
        check('s161 R1 available credit is limit minus balance, and unknown where no limit is entered',
              by['s161 Visa']['available'] == 4000.0 and by['s161 Store Card']['available'] is None)
        check('s161 R1 the trip planner offers "Put it on a card" beside the other two',
              'onclick="setTripFunding(\'card\')"' in html and 'Put it on a card' in html)

        p = c.get(f'/api/trip/card-plan?card_id={visa}&amount=2140', headers=H).get_json()['data']
        check('s161 R2 the 3 / 6 / 12-month rows are the amortisation at the card\'s APR',
              [r['months'] for r in p['rows']] == [3, 6, 12] and p['rows'] == payoff_rows(2140, 22.0)
              and abs(p['rows'][0]['payment'] - 739.65) < 0.01 and abs(p['rows'][0]['interest'] - 78.95) < 0.01)
        check('s161 R2 at current payments, the whole plan is re-run with the trip on the card',
              p['current'] and p['current']['payable'] and p['current']['interest_added'] > 0
              and p['current']['months_after'] >= p['current']['months_before'])
        check('s161 R1 a trip that fits says so; one that does not says by how much; an unknown limit says it can\'t tell',
              p['fits'] is True and p['short_by'] is None
              and c.get(f'/api/trip/card-plan?card_id={small}&amount=2140', headers=H).get_json()['data']['short_by'] == 1540.0
              and c.get(f'/api/trip/card-plan?card_id={store}&amount=2140', headers=H).get_json()['data']['fits'] is None)
        check('s161 R2 a 0% card costs no interest on any row',
              all(r['interest'] == 0 for r in c.get(f'/api/trip/card-plan?card_id={store}&amount=1200', headers=H)
                  .get_json()['data']['rows']))
        check('s161 R4 the assumptions are named: the trip alone at the APR, the grace period, a promotional rate',
              len(p['assumptions']) == 3 and 'grace period' in p['assumptions'][1] and '0%' in p['assumptions'][2]
              and p['statement']['grace_period_known'] is False)
        r = c.get(f'/api/trip/card-plan?card_id={loan}&amount=500', headers=H)
        check('s161 R1 a loan is refused as a place to put a trip', r.status_code == 404)

        # R6 - nothing saved
        with db_session() as session:
            before = session.query(DebtAccount).filter(DebtAccount.id.in_(made)).all()
            balances = sorted(round(d.current_balance, 2) for d in before)
        check('s161 R6 asking for a plan changes no balance and saves nothing', balances == [600.0, 900.0, 1000.0, 9000.0])

        check('s161 R7 the teaching layer\'s save line no longer overwrites the card plan',
              "_tripFunding === 'save' && _tripBudgetData" in (BASE / 'static/js/teaching/trip.js').read_text(encoding='utf-8'))

        node = shutil.which('node')
        check('s161 node is available to run the renderer (skip the rest if not)', bool(node))
        if not node:
            return
        src = ''.join(_fn(app, n) for n in ('_catParentName', '_catByName', '_kind', '_isSpend', '_isEarn', '_spendAmt', 'tripOwnSavingsRate', 'tripCardDetailHTML'))
        runner = r'''
const esc = s => String(s); const escJs = esc; const fmt = n => '$' + Number(n).toFixed(2);
const S = {categories: []};
''' + src + r'''
const p = JSON.parse(process.argv[1]); const out = {};
const strip = h => h.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
out.own = strip(tripCardDetailHTML(p, 400, {rate: 12.5, monthlyIncome: 5000}, null, 5000));
out.pick = strip(tripCardDetailHTML(p, 400, null, 10, 5000));
out.none = strip(tripCardDetailHTML(p, 400, null, null, 5000));
const today = new Date(2026, 9, 8), tx = [];
for (let i = 1; i <= 6; i++) { const m = `2026-${String(10 - i).padStart(2, '0')}`;
  tx.push({date: m + '-05', type: 'credit', amount: 4000, category: 'Income', kind: 'income'});      // item 111: the server's kind
  tx.push({date: m + '-10', type: 'debit', amount: 3000, category: 'Groceries', kind: 'spending'}); }
out.rate = tripOwnSavingsRate(tx, today);
out.gap = tripOwnSavingsRate(tx.filter(t => !t.date.startsWith('2026-07')), today);
console.log(JSON.stringify(out));'''
        res = subprocess.run([node, '-e', runner, json.dumps(p)], capture_output=True, text=True, encoding='utf-8', timeout=60)
        try:
            o = json.loads(res.stdout.strip().splitlines()[-1])
        except Exception:
            print('        node stderr:', res.stderr[-800:])
            o = {}
        t = o.get('own', '')
        check('s161 R7 the rendered plan says whether it fits, the in-full row with its grace-period condition, and each row',
              'has $4000.00 of available credit' in t and 'no interest if your card has a grace period' in t
              and '$739.65/mo' in t and '$78.95' in t and '3 months' in t and '12 months' in t)
        check('s161 R3 each row says what is left of the surplus, or how far over it is, as a fact',
              '$339.65/mo more than your surplus' in t and '$199.71/mo left' in t)
        check('s161 R3 no rendered sentence passes a verdict (afford, should, recommend, good, avoid ...)',
              all(not VERDICTS.search(o.get(k, '')) for k in ('own', 'pick', 'none')))
        check('s161 R5 the user\'s own rate is stated as theirs, counted as the annual summary counts it',
              "You've kept 12.5% of your income over the last 6 months" in t)
        check('s161 R5 a picked rate is called the user\'s choice', 'At the 10% you chose' in o.get('pick', ''))
        check('s161 R5 without 6 months of income, it says so and offers rates to pick, none called good',
              "can't tell what you usually keep" in o.get('none', '') and '5%' in o.get('none', ''))
        check('s161 R5 the own rate needs every one of 6 months to have income (absence is not zero)',
              o.get('rate') and abs(o['rate']['rate'] - 25.0) < 0.01 and o.get('gap') is None)
    finally:
        if made:
            with db_session() as session:
                session.query(DebtAccount).filter(DebtAccount.id.in_(made)).delete(synchronize_session=False)
                session.commit()
