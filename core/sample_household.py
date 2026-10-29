"""Item 105 - a sample household to look around in (gw 2.0/SAMPLE_HOUSEHOLD.md; Rob 2026-10-20: "we need test data can
you add that please. Also that way if I want to send this for people to review I think sending them test data would
assist them to get an understanding of the software" - and "remember they will get the welcome screen on first launch").

The Morgans - Sam and Jordan, fictional, renting, two paychecks, a credit card, a car loan, a student loan, some savings
and investments - with six months of everyday spending up to today. Every business named here is made up.

It is built only into an empty Groundwork (the welcome screen's "Look around with a sample household"), through
Groundwork's own routes so every record is shaped exactly as the app shapes it, and it is marked as the sample so
"Start with my own" can clear it - which nothing else can ever do to a household's real records.
"""
import json
import random
from datetime import date, datetime, time, timedelta

SAMPLE_FLAG = 'sample_household'
# Kept when the sample is cleared: the terms the person accepted, their AI choice, where backups go
KEEP_PREFIXES = ('terms_', 'ai_', 'backup_')

# October this year: Restaurants comes to exactly $500.00 over five visits (Rob's example - "someone see Restaurants
# $500.00 they don't think that is right")
RESTAURANT_MONTH_NOW = [(2, 'BAYSIDE GRILL #12', 'Bayside Grill', 112.40), (6, 'LUNA TAQUERIA', 'Luna Taqueria', 86.25),
                        (11, 'PINE STREET PIZZA', 'Pine Street Pizza', 131.80), (15, 'GOLDEN WOK', 'Golden Wok', 74.55),
                        (18, 'BAYSIDE GRILL #12', 'Bayside Grill', 95.00)]


def empty_reason(session):
    """None when Groundwork holds nothing of a household's own yet; otherwise what is already there."""
    from core.database import Account, AppSetting, BudgetItem, DebtAccount, Transaction
    if session.query(BudgetItem).count():
        return 'there is a budget here already'
    if session.query(Transaction).count():
        return 'there are transactions here already'
    if session.query(Account).count():
        return 'there are accounts here already'
    if session.query(DebtAccount).count():
        return 'there are debts here already'
    snap = session.query(AppSetting).filter_by(key='app_snapshot').first()
    if snap and snap.value:
        try:
            s = json.loads(snap.value) or {}
        except ValueError:
            s = {}
        if s.get('incomes') or s.get('expenses') or s.get('debtCardRows'):
            return 'there is a budget here already'
    return None


def _months(today, n=6):
    out, y, m = [], today.year, today.month
    for _ in range(n):
        out.append((y, m))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return list(reversed(out))


def _day(y, m, d):
    import calendar
    return date(y, m, min(d, calendar.monthrange(y, m)[1]))


def build(c, headers, today=None):
    """Fill an empty Groundwork with the Morgans through the app's own routes (c: a test client of the app)."""
    today = today or date.today()
    rnd = random.Random(20261020)
    H = {**headers, 'Content-Type': 'application/json'}

    def post(path, body, method='post'):
        r = getattr(c, method)(path, headers=H, data=json.dumps(body))
        d = r.get_json(silent=True) or {}
        if r.status_code >= 400 or d.get('ok') is False:
            raise RuntimeError(f'{path}: {d.get("error") or r.status_code}')
        return d.get('data', d)

    # who is answering on this computer (statements are the household's own)
    for name in ('Sam', 'Jordan'):
        post('/api/accounts/people', {'name': name})
    people = c.get('/api/accounts/speaker', headers=H).get_json()['data']['people']
    post('/api/accounts/speaker', {'person_id': next(p['id'] for p in people if p['name'] == 'Sam')})

    cats = {x['name']: x for x in c.get('/api/categories', headers=H).get_json()['data']}

    def cat(*names):
        return next((n for n in names if n in cats), names[-1])

    checking = post('/api/accounts', {'name': 'Everyday Checking', 'type': 'checking', 'institution': 'Lakeside Credit Union'})['id']
    savings = post('/api/accounts', {'name': 'High-Yield Savings', 'type': 'savings', 'institution': 'Lakeside Credit Union'})['id']
    brokerage = post('/api/accounts', {'name': 'Brokerage', 'type': 'investment', 'institution': 'Harbor Invest'})['id']

    debts = [
        dict(name='Cashback Visa', debt_type='credit', begin_balance=5200, current_balance=3840, interest_rate=24.99,
             minimum_payment=115, due_day=22),
        dict(name='Riverside Auto loan', debt_type='loan', begin_balance=22000, current_balance=14200, interest_rate=6.4,
             minimum_payment=389, due_day=3, start_date=f'{today.year - 2}-09-01', end_date=f'{today.year + 3}-09-01'),
        dict(name='Student loan', debt_type='loan', begin_balance=26000, current_balance=18750, interest_rate=4.5,
             minimum_payment=210, due_day=20),
    ]
    for d in debts:
        d['_dbId'] = post('/api/debt', d)['id']
    accounts = {a['name']: a['id'] for a in (c.get('/api/accounts', headers=H).get_json()['data'])}
    visa = accounts.get('Cashback Visa', checking)

    txns = []

    def tx(acct, d, desc, merchant, amount, category, kind='debit'):
        if d <= today:
            txns.append({'account_id': acct, 'date': d.isoformat(), 'posted_date': (min(d + timedelta(days=1), today)).isoformat(),
                         'description': desc, 'merchant': merchant, 'amount': round(amount, 2), 'type': kind,
                         'category': category, 'source': 'csv', 'cleared': True})

    months = _months(today)
    start = _day(*months[0], 1)
    # two paychecks, every other Friday, a week apart
    first_friday = start + timedelta(days=(4 - start.weekday()) % 7)
    d = first_friday
    while d <= today:
        tx(checking, d, 'NORTHWIND LOGISTICS PAYROLL', 'Northwind Logistics', 2150.00, cat('Paycheck / Salary'), 'credit')
        tx(checking, d + timedelta(days=7), 'RIVERSIDE SCHOOLS PAYROLL', 'Riverside Schools', 1780.00, cat('Paycheck / Salary'), 'credit')
        d += timedelta(days=14)

    # item 111 X9: filed as a real import files them - card and loan payments under Debt (the importer's own word),
    # the card's payment thank you on the card, and one refund - so the sample shows the kinds working
    debt_pay = cat('Debt', 'Loan Payment', 'Credit Card Payment', 'Debt Payment')
    for i, (y, m) in enumerate(months):
        now = (y, m) == (today.year, today.month)
        tx(checking, _day(y, m, 1), 'LAKESIDE PROPERTY MGMT', 'Lakeside Property Management', 1650.00, cat('Rent / Mortgage'))
        tx(checking, _day(y, m, 2), 'TRANSFER TO SAVINGS', 'Transfer to savings', 300.00, cat('Transfer'))
        tx(savings, _day(y, m, 2), 'TRANSFER FROM CHECKING', 'Transfer from checking', 300.00, cat('Transfer'), 'credit')
        tx(checking, _day(y, m, 3), 'RIVERSIDE AUTO FINANCE', 'Riverside Auto Finance', 389.00, debt_pay)
        tx(checking, _day(y, m, 5), 'CLEARWAVE INTERNET', 'ClearWave Internet', 69.99, cat('Internet'))
        tx(checking, _day(y, m, 8), 'BRIGHTCELL WIRELESS', 'BrightCell Wireless', 94.00, cat('Phone / Cell'))
        tx(checking, _day(y, m, 12), 'METRO POWER & LIGHT', 'Metro Power & Light', rnd.uniform(86, 142), cat('Electric'))
        tx(checking, _day(y, m, 15), 'SAFEHARBOR AUTO INS', 'SafeHarbor Auto Insurance', 138.50, cat('Auto Insurance'))
        tx(checking, _day(y, m, 20), 'STUDENTAID SERVICER', 'StudentAid Servicer', 210.00, debt_pay)
        tx(checking, _day(y, m, 22), 'CASHBACK VISA PAYMENT', 'Cashback Visa payment', 600.00, debt_pay)
        tx(visa, _day(y, m, 23), 'PAYMENT THANK YOU', 'Payment - thank you', 600.00, debt_pay, 'credit')
        tx(visa, _day(y, m, 4), 'IRONWORKS GYM', 'Ironworks Gym', 45.00, cat('Gym / Fitness'))
        tx(visa, _day(y, m, 9), 'STREAMBOX', 'StreamBox', 15.49, cat('Streaming Video'))
        if i >= len(months) - 3:                     # item 107 D11: StreamBox from checking too, so the review sees one
            tx(checking, _day(y, m, 3), 'STREAMBOX.COM', 'StreamBox', 15.49, cat('Streaming Video'))
        tx(visa, _day(y, m, 14), 'TUNEFLOW', 'TuneFlow', 10.99, cat('Streaming Music', 'Streaming Video'))
        for _ in range(rnd.randint(6, 8)):
            store = rnd.choice([('FRESH FARM MARKET', 'Fresh Farm Market'), ('VALLEY FOODS #31', 'Valley Foods'), ('CORNER MARKET', 'Corner Market')])
            tx(visa, _day(y, m, rnd.randint(1, 28)), store[0], store[1], rnd.uniform(38, 165), cat('Groceries'))
        if now:
            for dd, desc, merch, amt in RESTAURANT_MONTH_NOW:
                tx(visa, _day(y, m, dd), desc, merch, amt, cat('Restaurants'))
        else:
            for _ in range(rnd.randint(3, 5)):
                place = rnd.choice([('BAYSIDE GRILL #12', 'Bayside Grill'), ('LUNA TAQUERIA', 'Luna Taqueria'),
                                    ('PINE STREET PIZZA', 'Pine Street Pizza'), ('GOLDEN WOK', 'Golden Wok')])
                tx(visa, _day(y, m, rnd.randint(1, 28)), place[0], place[1], rnd.uniform(24, 96), cat('Restaurants'))
        # Coffee: about $50 a month until they cut its line from $60 to $40 in the second month, and under $40 since
        for _ in range(rnd.randint(7, 9) if i <= 1 else rnd.randint(4, 5)):
            tx(visa, _day(y, m, rnd.randint(1, 28)), 'LANTERN CAFE', 'Lantern Cafe', rnd.uniform(4.75, 7.9 if i <= 1 else 7.5), cat('Coffee Shops'))
        for _ in range(rnd.randint(3, 4)):
            tx(visa, _day(y, m, rnd.randint(1, 28)), 'QUICKFUEL #214', 'QuickFuel', rnd.uniform(38, 62), cat('Gasoline / Diesel'))
        for _ in range(rnd.randint(1, 2)):
            tx(visa, _day(y, m, rnd.randint(1, 28)), 'HAPPY PAWS PET SUPPLY', 'Happy Paws Pet Supply', rnd.uniform(32, 68), cat('Pet Food / Supplies'))
        tx(visa, _day(y, m, rnd.randint(1, 28)), 'PARCELMART ORDER', 'ParcelMart', rnd.uniform(22, 74), cat('Household Supplies'))
        if i % 2 == 0:
            tx(visa, _day(y, m, rnd.randint(1, 28)), 'THREADLINE', 'Threadline', rnd.uniform(35, 120), cat('Clothing'))
        if i == 2:
            tx(visa, _day(y, m, 17), 'NORTHSIDE URGENT CARE', 'Northside Urgent Care', 40.00, cat('Doctor / Co-pays'))
        if i == 3:
            tx(visa, _day(y, m, 6), 'GIFTNOOK', 'GiftNook', 64.30, cat('Gifts'))
            tx(visa, _day(y, m, 11), 'PARCELMART REFUND', 'ParcelMart', 42.18, cat('Household Supplies'), 'credit')
    for t in sorted(txns, key=lambda x: x['date']):
        post('/api/transactions', t)

    # investments: three funds, priced by hand (no lookup leaves the computer)
    for ticker, shares, paid, price, ago in (('VTI', 42, 210.15, 268.40, 300), ('VXUS', 60, 58.20, 64.10, 240), ('BND', 25, 72.05, 73.30, 180)):
        post('/api/investments/transactions', {'type': 'buy', 'ticker': ticker, 'account_id': brokerage, 'shares': shares,
                                               'price_per_share': paid, 'date': (today - timedelta(days=ago)).isoformat(),
                                               'security_type': 'etf'})
        post('/api/investments/price', {'ticker': ticker, 'price': price}, 'patch')

    # savings goals, gifts
    post('/api/sinking-funds', {'name': 'Car repairs', 'target_amount': 1200, 'monthly_contribution': 40, 'current_amount': 640,
                                'deadline': f'{today.year + 1}-06-30'})
    post('/api/sinking-funds', {'name': 'Holidays', 'target_amount': 800, 'monthly_contribution': 60, 'current_amount': 420,
                                'deadline': f'{today.year}-12-15'})
    mom = post('/api/gifts/people', {'name': 'Mom', 'relationship': 'family'})['id']
    post('/api/gifts/occasions', {'person_id': mom, 'type': 'birthday', 'date': f'{today.year}-12-03'})
    ava = post('/api/gifts/people', {'name': 'Ava (niece)', 'relationship': 'family'})['id']
    post('/api/gifts/occasions', {'person_id': ava, 'type': 'birthday', 'date': f'{today.year + 1}-02-14'})
    post('/api/gifts/occasions', {'shared': True, 'name': 'Holiday gifts', 'type': 'christmas', 'date': f'{today.year}-12-25', 'budget': 400})

    # a medical bill, as the provider sent it (the Health page)
    bill = post('/api/medical-bills/statement', {'provider': 'Northside Urgent Care', 'account_number': 'NUC-48213', 'source': 'provider',
                                                 'statement_date': (today - timedelta(days=24)).isoformat(), 'amount': 285.40,
                                                 'due_date': (today + timedelta(days=12)).isoformat()})['id']
    post(f'/api/medical-bills/{bill}/mine', {})          # "This bill is mine to pay" - now it is owed

    # the budget: its lines (budget_items), the debt payment budget and the net worth fields, as the app keeps them
    post('/api/budget/items', {'type': 'income', 'name': "Sam's paycheck", 'amount': 4658, 'category': cat('Paycheck / Salary'), 'sort_order': 0})
    post('/api/budget/items', {'type': 'income', 'name': "Jordan's paycheck", 'amount': 3857, 'category': cat('Paycheck / Salary'), 'sort_order': 1})
    lines = {}
    for k, (name, catname, amount) in enumerate([
            ('Rent', 'Rent / Mortgage', 1650), ('Groceries', 'Groceries', 650), ('Restaurants', 'Restaurants', 300),
            ('Coffee', 'Coffee Shops', 60), ('Electric', 'Electric', 120), ('Internet', 'Internet', 70),
            ('Phones', 'Phone / Cell', 94), ('Car insurance', 'Auto Insurance', 139), ('Gas', 'Gasoline / Diesel', 180),
            ('Streaming', 'Streaming Video', 27), ('Gym', 'Gym / Fitness', 45), ('Pet supplies', 'Pet Food / Supplies', 80),
            ('Household', 'Household Supplies', 60), ('Clothing', 'Clothing', 75)]):
        lines[name] = post('/api/budget/items', {'type': 'expense', 'name': name, 'amount': amount, 'category': cat(catname), 'sort_order': k})['id']
    post('/api/settings', {'monthly_budget': '900', 'debt_method': 'avalanche', 'savings_balance': '6700',
                           'retirement_401k': '38500', 'retirement_ira': '9200'}, 'patch')

    # each debt's monthly balance, as its statements gave it (the Historian's debt_balance_history) - so the balances
    # read as kept up, not typed once
    steps = {'Cashback Visa': (160, 600), 'Riverside Auto loan': (330, 389), 'Student loan': (140, 210)}
    for k, (y, m) in enumerate(months):
        back = len(months) - 1 - k
        post('/api/debt/history', {'month': f'{y}-{m:02d}', 'snapshots': [
            {'debt_id': d['_dbId'], 'balance': d['current_balance'] + steps[d['name']][0] * back, 'payment': steps[d['name']][1],
             'min_payment': d['minimum_payment'], 'apr': d['interest_rate']} for d in debts]})

    # the Working picture's record (Rob 2026-10-21: "add enough data to show a full page in working picture"): what
    # they did to their budget, and what Sam said on the decision screens. Each goes through the app's own route, as
    # the app records it, and is then dated to when it happened - the routes stamp "now".
    from core.database import HistorianEntry, NetWorthSnapshot, WillingnessDeclaration, db_session

    def edit(name, amount, when):
        post(f'/api/budget/items/{lines[name]}', {'amount': amount}, 'patch')
        with db_session() as session:
            e = session.query(HistorianEntry).filter_by(event_category='budget_adjusted').order_by(HistorianEntry.id.desc()).first()
            e.created_at = datetime.combine(when, time(20, 15))
            session.commit()

    def said(category, stance, proposal, when):
        post('/api/willingness/declarations', {'category': category, 'stance': stance,
                                               'answer': {'kind': 'proposal', 'text': proposal}})
        with db_session() as session:
            d = session.query(WillingnessDeclaration).order_by(WillingnessDeclaration.id.desc()).first()
            d.said_at = datetime.combine(when, time(20, 40))
            session.commit()

    m0, m1, m2, m3 = months[:4]
    groceries, streaming, coffee, gym = (cat(n) for n in ('Groceries', 'Streaming Video', 'Coffee Shops', 'Gym / Fitness'))
    said(groceries, 'protect', f'Move $50 a month from {groceries} to Car repairs', _day(*m0, 18))
    edit('Coffee', 40, _day(*m1, 4))                  # a cut that held: three months under $40 since
    said(streaming, 'flexible', f'Trim {streaming} by $7 a month toward Holidays', _day(*m1, 20))
    edit('Gym', 25, _day(*m1, 9))                     # a cut, then put back: kept
    edit('Gym', 45, _day(*m3, 6))
    edit('Streaming', 20, _day(*m2, 5))               # flexible, they said - then cut and put back: "which do you mean?"
    edit('Streaming', 27, _day(*m3, 12))
    said(cat('Restaurants'), 'flexible', f'Spend $50 less on {cat("Restaurants")} each month toward Car repairs', today - timedelta(days=9))

    # the valuation change item 35 notes on a snapshot is history this household never had
    post('/api/settings', {'inv_valuation_v35_noted': today.isoformat()}, 'patch')
    # net worth: the months before this one, then this month's own snapshot through the app
    with db_session() as session:
        for k, (y, m) in enumerate(months[:-1]):
            back = len(months) - 1 - k
            assets = 6700 - 300 * back + 38500 - 650 * back + 9200 - 150 * back
            liab = 3840 + 160 * back + 14200 + 330 * back + 18750 + 140 * back
            session.add(NetWorthSnapshot(snapshot_date=f'{y}-{m:02d}', assets=assets, liabilities=liab, net_worth=assets - liab, notes=''))
        session.commit()
    post('/api/net-worth/snapshot', {'assets': 6700 + 38500 + 9200, 'liabilities': 3840 + 14200 + 18750})

    post('/api/settings', {'onboarding_complete': 'true'}, 'patch')
    # the mark that lets "Start with my own" clear this - set here and nowhere else (the settings route refuses it)
    from core.database import AppSetting
    with db_session() as session:
        session.add(AppSetting(key=SAMPLE_FLAG, value='true'))
        session.commit()
    return {'transactions': len(txns), 'accounts': len(accounts), 'debts': len(debts)}
