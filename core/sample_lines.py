"""The Morgans' everyday transactions (item 105), as plain lines - the one source for both the sample household
(core/sample_household.py posts them through the app's own routes) and the website's demo bank (item 117 D5: its
downloads are these lines, dated from the day they're downloaded).

Imports nothing of Groundwork's: the website carries a byte-for-byte copy as Website/sample_lines.py, and s293 fails
the gate if the two ever differ. Every business named here is made up.
"""
import calendar
import random
from datetime import date, timedelta

SEED = 20261020

# This month: Restaurants comes to exactly $500.00 over five visits (Rob's example - "someone see Restaurants $500.00
# they don't think that is right")
RESTAURANT_MONTH_NOW = [(2, 'BAYSIDE GRILL #12', 'Bayside Grill', 112.40), (6, 'LUNA TAQUERIA', 'Luna Taqueria', 86.25),
                        (11, 'PINE STREET PIZZA', 'Pine Street Pizza', 131.80), (15, 'GOLDEN WOK', 'Golden Wok', 74.55),
                        (18, 'BAYSIDE GRILL #12', 'Bayside Grill', 95.00)]

# Category wishes, most wanted first: the app files each line under the first of these its categories hold
DEBT_PAY = ('Debt', 'Loan Payment', 'Credit Card Payment', 'Debt Payment')


def months(today, n=6):
    out, y, m = [], today.year, today.month
    for _ in range(n):
        out.append((y, m))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return list(reversed(out))


def day(y, m, d):
    return date(y, m, min(d, calendar.monthrange(y, m)[1]))


def everyday(today=None):
    """(rnd, lines): the random source, left where the lines leave it (the sample household draws on from there), and
    the six months of lines up to today. A line is a dict: acct ('checking', 'savings' or 'visa'), date, description,
    merchant, amount (positive), kind ('debit' or 'credit'), cats (category wishes, most wanted first)."""
    today = today or date.today()
    rnd = random.Random(SEED)
    lines = []

    def tx(acct, d, desc, merchant, amount, cats, kind='debit'):
        if d <= today:
            lines.append({'acct': acct, 'date': d, 'description': desc, 'merchant': merchant,
                          'amount': round(amount, 2), 'kind': kind, 'cats': tuple(cats) if isinstance(cats, tuple) else (cats,)})

    ms = months(today)
    start = day(*ms[0], 1)
    # two paychecks, every other Friday, a week apart
    d = start + timedelta(days=(4 - start.weekday()) % 7)
    while d <= today:
        tx('checking', d, 'NORTHWIND LOGISTICS PAYROLL', 'Northwind Logistics', 2150.00, 'Paycheck / Salary', 'credit')
        tx('checking', d + timedelta(days=7), 'RIVERSIDE SCHOOLS PAYROLL', 'Riverside Schools', 1780.00, 'Paycheck / Salary', 'credit')
        d += timedelta(days=14)

    # item 111 X9: filed as a real import files them - card and loan payments under Debt (the importer's own word),
    # the card's payment thank you on the card, and one refund - so the sample shows the kinds working
    for i, (y, m) in enumerate(ms):
        now = (y, m) == (today.year, today.month)
        tx('checking', day(y, m, 1), 'LAKESIDE PROPERTY MGMT', 'Lakeside Property Management', 1650.00, 'Rent / Mortgage')
        tx('checking', day(y, m, 2), 'TRANSFER TO SAVINGS', 'Transfer to savings', 300.00, 'Transfer')
        tx('savings', day(y, m, 2), 'TRANSFER FROM CHECKING', 'Transfer from checking', 300.00, 'Transfer', 'credit')
        tx('checking', day(y, m, 3), 'RIVERSIDE AUTO FINANCE', 'Riverside Auto Finance', 389.00, DEBT_PAY)
        tx('checking', day(y, m, 5), 'CLEARWAVE INTERNET', 'ClearWave Internet', 69.99, 'Internet')
        tx('checking', day(y, m, 8), 'BRIGHTCELL WIRELESS', 'BrightCell Wireless', 94.00, 'Phone / Cell')
        tx('checking', day(y, m, 12), 'METRO POWER & LIGHT', 'Metro Power & Light', rnd.uniform(86, 142), 'Electric')
        tx('checking', day(y, m, 15), 'SAFEHARBOR AUTO INS', 'SafeHarbor Auto Insurance', 138.50, 'Auto Insurance')
        tx('checking', day(y, m, 20), 'STUDENTAID SERVICER', 'StudentAid Servicer', 210.00, DEBT_PAY)
        tx('checking', day(y, m, 22), 'CASHBACK VISA PAYMENT', 'Cashback Visa payment', 600.00, DEBT_PAY)
        tx('visa', day(y, m, 23), 'PAYMENT THANK YOU', 'Payment - thank you', 600.00, DEBT_PAY, 'credit')
        tx('visa', day(y, m, 4), 'IRONWORKS GYM', 'Ironworks Gym', 45.00, 'Gym / Fitness')
        tx('visa', day(y, m, 9), 'STREAMBOX', 'StreamBox', 15.49, 'Streaming Video')
        if i >= len(ms) - 3:                     # item 107 D11: StreamBox from checking too, so the review sees one
            tx('checking', day(y, m, 3), 'STREAMBOX.COM', 'StreamBox', 15.49, 'Streaming Video')
        tx('visa', day(y, m, 14), 'TUNEFLOW', 'TuneFlow', 10.99, ('Streaming Music', 'Streaming Video'))
        for _ in range(rnd.randint(6, 8)):
            store = rnd.choice([('FRESH FARM MARKET', 'Fresh Farm Market'), ('VALLEY FOODS #31', 'Valley Foods'), ('CORNER MARKET', 'Corner Market')])
            tx('visa', day(y, m, rnd.randint(1, 28)), store[0], store[1], rnd.uniform(38, 165), 'Groceries')
        if now:
            for dd, desc, merch, amt in RESTAURANT_MONTH_NOW:
                tx('visa', day(y, m, dd), desc, merch, amt, 'Restaurants')
        else:
            for _ in range(rnd.randint(3, 5)):
                place = rnd.choice([('BAYSIDE GRILL #12', 'Bayside Grill'), ('LUNA TAQUERIA', 'Luna Taqueria'),
                                    ('PINE STREET PIZZA', 'Pine Street Pizza'), ('GOLDEN WOK', 'Golden Wok')])
                tx('visa', day(y, m, rnd.randint(1, 28)), place[0], place[1], rnd.uniform(24, 96), 'Restaurants')
        # Coffee: about $50 a month until they cut its line from $60 to $40 in the second month, and under $40 since
        for _ in range(rnd.randint(7, 9) if i <= 1 else rnd.randint(4, 5)):
            tx('visa', day(y, m, rnd.randint(1, 28)), 'LANTERN CAFE', 'Lantern Cafe', rnd.uniform(4.75, 7.9 if i <= 1 else 7.5), 'Coffee Shops')
        for _ in range(rnd.randint(3, 4)):
            tx('visa', day(y, m, rnd.randint(1, 28)), 'QUICKFUEL #214', 'QuickFuel', rnd.uniform(38, 62), 'Gasoline / Diesel')
        for _ in range(rnd.randint(1, 2)):
            tx('visa', day(y, m, rnd.randint(1, 28)), 'HAPPY PAWS PET SUPPLY', 'Happy Paws Pet Supply', rnd.uniform(32, 68), 'Pet Food / Supplies')
        tx('visa', day(y, m, rnd.randint(1, 28)), 'PARCELMART ORDER', 'ParcelMart', rnd.uniform(22, 74), 'Household Supplies')
        if i % 2 == 0:
            tx('visa', day(y, m, rnd.randint(1, 28)), 'THREADLINE', 'Threadline', rnd.uniform(35, 120), 'Clothing')
        if i == 2:
            tx('visa', day(y, m, 17), 'NORTHSIDE URGENT CARE', 'Northside Urgent Care', 40.00, 'Doctor / Co-pays')
        if i == 3:
            tx('visa', day(y, m, 6), 'GIFTNOOK', 'GiftNook', 64.30, 'Gifts')
            tx('visa', day(y, m, 11), 'PARCELMART REFUND', 'ParcelMart', 42.18, 'Household Supplies', 'credit')
    return rnd, sorted(lines, key=lambda x: x['date'])
