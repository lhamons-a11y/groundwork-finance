"""Item 73 stage 3 (gw 2.0/BYB_AGENT.md Y3 + Y4; Rob 2026-10-11: "build ... item 73 stage 3").

    Y3  the monthly cost from the person's figures, their confirmed insurance bill reading and EIA's published gas
        price - each part with its source; a part with no source is left out and named, never guessed
    Y4  a financing offer read (APR, term, payment, price, fees, deferred interest), beside paying cash and the
        person's own highest-rate debt; a no-interest promotion costs the price if paid in time
"""
import json
import re
from datetime import date, datetime


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    app = ctx.app_src
    from core.purchase_cost import full_cost, read_offer, compare
    from core.database import BillReading, BudgetItem, DebtAccount, db_session

    ins = {'name': 'GEICO', 'amount': 187.50, 'date': '2026-10-01'}
    gas = {'price': 3.19, 'period': '2026-10-06', 'live': True}
    car = full_cost('car', {'payment': 474.10, 'miles_per_month': 1000, 'mpg': 28, 'registration_yearly': 120}, ins, gas)
    parts = {p['label']: p for p in car['parts']}
    check(f'Y3 a car: payment, insurance from the bill reading, fuel from EIA, registration - each with its source ({car["monthly"]})',
          parts['Insurance']['kind'] == 'observed' and 'GEICO bill reading' in parts['Insurance']['source']
          and parts['Fuel']['kind'] == 'published' and abs(parts['Fuel']['monthly'] - 1000 / 28 * 3.19) < 0.01
          and parts['Registration']['monthly'] == 10.0 and abs(car['monthly'] - (474.10 + 187.50 + 113.93 + 10.0)) < 0.02)
    check('Y3 what Groundwork has no source for is left out and named, never guessed (repairs, an unpublished gas price)',
          any('Repairs' in x for x in car['left_out'])
          and 'Fuel' not in {p['label'] for p in full_cost('car', {'miles_per_month': 1000, 'mpg': 28}, None, {'price': 3.4, 'live': False})['parts']}
          and any('Insurance' in x for x in full_cost('car', {'payment': 300}, None, None)['left_out']))
    ph = full_cost('phone', {'device_payment': 35, 'plan_change': -5}, None, None)
    an = full_cost('annual', {'yearly': 139}, None, None)
    check('Y3 a phone (a plan that costs less counts as less) and a yearly charge shown a month at a time',
          ph['monthly'] == 30.0 and an['monthly'] == round(139 / 12, 2) and an['yearly'] == round(round(139 / 12, 2) * 12, 2)
          and full_cost('boat', {}, None, None) is None)

    promo = read_offer('No interest if paid in full within 12 months on purchases of $1,499.00. Cash price: $1,499.00. '
                       'Standard APR 29.99%. Interest will be charged from the purchase date if the promotional balance '
                       'is not paid in full within 12 months.')
    cp = compare(promo, [{'name': 'Capital One', 'balance': 2400.0, 'rate': 24.99}, {'name': 'Kohls', 'balance': 300.0, 'rate': 27.0}])
    check('Y4 a deferred-interest offer: its own words kept, the price if paid in time, and what it costs if not',
          promo['deferred'] and 'purchase date' in promo['deferred_phrase'] and promo['promo_months'] == 12 and promo['apr'] == 29.99
          and cp['rows'][1]['total'] == 1499.0 and cp['extra'] == 0.0 and cp['deferred']['cost'] == round(1499 * 0.2999, 2))
    check('Y4 the person\'s own debt beside it: the highest-rate balance, and what the cash would save there in a year',
          cp['own_debt']['name'] == 'Kohls' and cp['own_debt']['year_interest_on_cash'] == round(300 * 0.27, 2))
    loan = read_offer('Auto loan: amount financed $24,000.00 at 6.9% APR for 60 months. Monthly payment of $474.10. Origination fee $150.00.')
    cl = compare(loan, [])
    check('Y4 a loan: payment x term + fees, against the price',
          loan == {'apr': 6.9, 'term_months': 60, 'payment': 474.1, 'price': 24000.0, 'fees': 150.0, 'deferred': False, 'warnings': []}
          and cl['rows'][1]['total'] == 28596.0 and cl['extra'] == 4596.0)
    noprice = compare(read_offer('Finance at 9.99% APR for 24 months.'), [])
    check('Y4 an offer that states no price or payment gives no totals rather than invented ones', noprice['rows'] == [] and noprice['extra'] is None)

    # the routes, on the record
    with db_session() as s:
        b = BudgetItem(name='s200 GEICO', category='Insurance', amount=187.50, type='expense', is_active=True)
        s.add(b); s.flush()
        s.add(BillReading(budget_item_id=b.id, amount=251.40, read_at=datetime(2026, 10, 2, 9, 0), source_host='geico.com'))
        s.add(DebtAccount(name='s200 Card', current_balance=1800.0, interest_rate=22.0, minimum_payment=60.0, is_active=True))
        s.commit()
    import gas_price
    real = gas_price.get_national_gas_price
    gas_price.get_national_gas_price = lambda key: {'price': 3.25, 'period': '2026-10-06', 'live': True}
    try:
        r = c.post('/api/byb/full-cost', headers=HJ, data=json.dumps({'kind': 'car', 'inputs': {'payment': 400, 'miles_per_month': 800, 'mpg': 25}})).get_json()['data']
    finally:
        gas_price.get_national_gas_price = real
    rp = {p['label']: p for p in r['parts']}
    check('Y3 the route reads the person\'s confirmed insurance bill and the published gas price',
          rp['Insurance']['monthly'] == 251.40 and 's200 GEICO' in rp['Insurance']['source'] and rp['Fuel']['monthly'] == round(800 / 25 * 3.25, 2))
    f = c.post('/api/byb/financing', headers=HJ, data=json.dumps({'text': 'Cash price $900.00. 18 months special financing. APR 26.99%. Deferred interest applies.'})).get_json()['data']
    check('Y4 the route reads a pasted offer and lays it beside the person\'s own debt; nothing is saved',
          f['offer']['price'] == 900.0 and f['offer']['deferred'] and f['compare']['own_debt'] is not None
          and c.post('/api/byb/financing', headers=HJ, data=json.dumps({'text': ' '})).status_code == 400)

    js = app.split('function renderBybCost(')[1].split('\nfunction renderBYB(')[0]
    check('Y3/Y4 on the page: sources shown, what is not included said, no model, no verdict',
          'callAI(' not in js and 'Not included' in js and 'Nothing is saved' in js
          and not re.search(r'\b(should|bad deal|good deal|avoid|smart|mistake|you need)\b', js, re.I))

    with db_session() as s:
        ids = [x.id for x in s.query(BudgetItem).filter(BudgetItem.name.like('s200%'))]
        s.query(BillReading).filter(BillReading.budget_item_id.in_(ids)).delete(synchronize_session=False)
        s.query(BudgetItem).filter(BudgetItem.name.like('s200%')).delete(synchronize_session=False)
        s.query(DebtAccount).filter(DebtAccount.name.like('s200%')).delete(synchronize_session=False)
        s.commit()
