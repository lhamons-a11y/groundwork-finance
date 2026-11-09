"""Math audit, half 2: recompute every figure from the raw records alone and compare with what the app shows.

    python math_check.py <math.json from math_collect.mjs>

Shares no code with Groundwork: the payoff simulation, the sums and the ratios are written here from their textbook
definitions. Where a convention could differ (whole-dollar interest, which transactions count as spending), the
convention used here is stated, and a mismatch is reported with both figures, never silently tolerated.
"""
import json
import re
import sys
from collections import defaultdict
from datetime import date, timedelta

d = json.load(open(sys.argv[1], encoding='utf-8'))
raw, shown = d['raw'], d['shown']
today = date.fromisoformat(raw['today'])
rows = []


def report(what, ours, theirs, tol=0.01, note=''):
    ok = ours is not None and theirs is not None and abs(float(ours) - float(theirs)) <= tol
    rows.append((ok, what, ours, theirs, note))


def money(s):
    return float(s.replace('$', '').replace(',', '').replace('−', '-').strip())


def find(text, label_re):
    """The first $ figure after a label in a page's text."""
    m = re.search(label_re + r'[^$]*?(−?\$[\d,]+\.\d\d)', text, re.S)
    return money(m.group(1)) if m else None


# ── 1. Debt payoff, simulated here ───────────────────────────────────────────────────────────────────────────────
debts = [x for x in raw['debts'] if x.get('is_active', True)]
cards = [{'name': x['name'], 'bal': float(x['current_balance'] if x['current_balance'] is not None else x['begin_balance']),
          'apr': float(x['interest_rate'] or 0), 'min': float(x['minimum_payment'] or 0)} for x in debts]
budget = float(raw['settings'].get('monthly_budget') or sum(c['min'] for c in cards if c['bal'] > 0.01))


def simulate(cards, budget, strategy='avalanche', one_time=0.0, extra_monthly=0.0):
    """Month by month: interest at APR/12 on the opening balance, every minimum paid (never more than is owed), and
    whatever is left of the budget to one debt at a time - highest APR first (avalanche) or smallest balance first
    (snowball) - so a cleared debt's minimum rolls into the next. A one-time cost takes the extra above the minimums
    until it is paid. None when the budget can't cover the minimums or nothing clears in 50 years."""
    cs = [dict(c) for c in cards if c['bal'] > 0.005]
    budget += extra_monthly
    if budget < sum(c['min'] for c in cs) - 0.005:
        return None
    owed_cost, months, interest = one_time, 0, 0.0
    while any(c['bal'] > 0.005 for c in cs):
        months += 1
        if months > 600:
            return None
        for c in cs:
            if c['bal'] > 0.005:
                i = c['bal'] * c['apr'] / 1200
                c['bal'] += i
                interest += i
        left = budget
        for c in cs:
            if c['bal'] > 0.005:
                p = min(c['min'], c['bal'])
                c['bal'] -= p
                left -= p
        if owed_cost > 0:
            take = min(left, owed_cost)
            owed_cost -= take
            left -= take
        order = sorted([c for c in cs if c['bal'] > 0.005],
                       key=(lambda c: -c['apr']) if strategy == 'avalanche' else (lambda c: c['bal']))
        for c in order:
            if left <= 0.005:
                break
            p = min(left, c['bal'])
            c['bal'] -= p
            left -= p
    return {'months': months, 'interest': interest}


base = simulate(cards, budget, raw['settings'].get('debt_method') or 'avalanche')
client = shown['client']['payoff0'] or {}
eng = shown['engine']
report('Payoff: months to debt-free (the Debt page)', base and base['months'], client.get('months'), 0)
report('Payoff: total interest (the Debt page)', base and base['interest'], client.get('totalInterest'), 2.0,
       'the app shows whole dollars')
report('Payoff: months, the server engine agrees with the page', client.get('months'),
       eng['base']['base']['months'], 0)
p200 = simulate(cards, budget, extra_monthly=200)
report('Extra $200/mo: months sooner', base['months'] - p200['months'], -eng['plus200']['months_delta'], 0)
report('Extra $200/mo: interest saved', base['interest'] - p200['interest'], -eng['plus200']['interest_delta'], 2.0)
trip = simulate(cards, budget, one_time=591)
report('A $591 trip paid from the extra: months later', trip['months'] - base['months'], eng['trip591']['months_delta'], 0)
report('A $591 trip: interest added', trip['interest'] - base['interest'], eng['trip591']['interest_delta'], 2.0)
snow = simulate(cards, budget, 'snowball')
report('Snowball: months (the sample: same as avalanche?)', snow['months'], base['months'], 99,
       f"snowball {snow['months']} mo / ${snow['interest']:.0f}; avalanche {base['months']} mo / ${base['interest']:.0f}")

# interest per month and per week (the check-in's sentence)
monthly_int = sum(c['bal'] * c['apr'] / 1200 for c in cards)
report('Interest a month at these balances (check-in)', monthly_int, find(shown['dashboard'], r'about \$[\d,.]+ in interest this week - about'), 0.01)
report('Interest a week (check-in)', monthly_int * 12 / 365 * 7, find(shown['dashboard'], r'Your debts cost about'), 0.01,
       'convention: a month x 12 / 365 x 7 (by days; x 12 / 52 gives a few cents more)')

# ── 2. Ratios ───────────────────────────────────────────────────────────────────────────────────────────────────────
income = sum(float(i['amount']) for i in shown['client']['incomes'])
mins = sum(c['min'] for c in cards if c['bal'] > 0.01)
dti_page = re.search(r'DTI ([\d.]+)%', shown['debt'])
report('Debt-to-income (minimums / income), Debt page', round(mins / income * 100, 1), dti_page and float(dti_page.group(1)), 0.05)

# ── 3. Budget page totals ──────────────────────────────────────────────────────────────────────────────────────────
b = shown['budget']
spend_lines = sum(float(e['amount']) for e in shown['client']['expenses'])
report('Budget: income = the income lines', income, find(b, r'INCOME'), 0.01)
out_page, left_page = find(b, r'\bOUT'), find(b, r'\bLEFT')
report('Budget: left = income - out', income - (out_page or 0), left_page, 0.01)
report('Budget: planned left = income - spending lines - the debt plan (the page says planned)', income - spend_lines - budget,
       find(b, r'Left to save or spend'), 0.01)
# ── 4. Spending from the ledger ────────────────────────────────────────────────────────────────────────────────────
tx = raw['transactions'] if isinstance(raw['transactions'], list) else raw['transactions'].get('transactions', [])
NOT_SPENDING = {'Transfer', 'Debt', 'Income'}


def spent(t):
    """Spending: money out, not a transfer between own accounts and not a debt payment (kind/category say which)."""
    if t['type'] != 'debit':
        return 0.0
    if (t.get('kind') or '') in ('transfer', 'debt_payment', 'own_move') or (t.get('category') or '') in NOT_SPENDING:
        return 0.0
    return float(t['amount'])


month0 = today.replace(day=1)
mtd = [t for t in tx if month0.isoformat() <= t['date'][:10] <= today.isoformat()]
by_cat = defaultdict(float)
for t in mtd:
    by_cat[t.get('category') or ''] += spent(t)
# the header's OUT is the month PROJECTED: each line's own "proj." figure as the page shows it (its budget where it shows
# none), plus the debt plan - the page's "Projected at this rate". (Fixed bills aren't scaled by the pace, so the
# projection itself is the page's; what is checked is that the header adds up what the lines say.)
proj = 0.0
for e in shown['client']['expenses']:
    m = re.search(re.escape(e['name']) + r'\n\$[\d,]+\.\d\d\n[^\n$]*\$([\d,]+\.\d\d) proj\.', b)
    proj += money('$' + m.group(1)) if m else float(e['amount'])
report("Budget: out (header) = the lines' projections + the debt plan", proj + budget, out_page, 0.01,
       f'projected spending {proj:.2f} + debt {budget:.2f}; the header does not say it is a projection')
report('This month so far: spent (check-in)', sum(by_cat.values()), find(shown['dashboard'], r'This month so far:'), 0.01,
       f'{len(mtd)} transactions since {month0}')
debt_paid = sum(float(t['amount']) for t in mtd if t['type'] == 'debit' and ((t.get('kind') or '') == 'debt_payment' or t.get('category') == 'Debt'))
report('This month so far: paid to cards and loans (check-in)', debt_paid, find(shown['dashboard'], r'spent and'), 0.01)
for name, cat in (('Restaurants', 'Restaurants'), ('Coffee', 'Coffee Shops'), ('Internet', 'Internet'), ('Gas', 'Gasoline / Diesel'),
                  ('Rent', 'Rent / Mortgage')):
    m = re.search(re.escape(name) + r'\s*\n\s*(\$[\d,]+\.\d\d)', b)
    report(f'Budget: {name} spent this month = its ledger lines', by_cat.get(cat, 0.0), money(m.group(1)) if m else None, 0.01)
# last week, Sunday to Saturday
sun = today - timedelta(days=(today.weekday() + 1) % 7) - timedelta(days=7)
wk = [t for t in tx if sun.isoformat() <= t['date'][:10] <= (sun + timedelta(days=6)).isoformat()]
report(f'Last week ({sun} to {sun + timedelta(days=6)}): spent (check-in)', sum(spent(t) for t in wk),
       find(shown['dashboard'], r'Last week \([^)]*\):'), 0.01)

# ── 5. Accounts ──────────────────────────────────────────────────────────────────────────────────────────────────
for a in raw['accounts']:
    own = [t for t in tx if t.get('account_id') == a['id']]
    if not own:
        continue
    net = sum(float(t['amount']) * (1 if t['type'] == 'credit' else -1) for t in own)
    report(f"Account {a['name']}: credits - debits = its activity", net, a.get('activity_net'), 0.01, f'{len(own)} transactions')

# ── 6. Investments ───────────────────────────────────────────────────────────────────────────────────────────────
pos = raw['holdings'].get('positions', []) if isinstance(raw['holdings'], dict) else []
tot_val = tot_cost = 0.0
for p in pos:
    shares = sum(float(l['shares']) for l in p.get('lots', [])) or float(p['total_shares'])
    cost = sum(float(l['shares']) * float(l['cost_basis']) for l in p.get('lots', [])) or float(p['total_cost'])
    val = shares * float(p['current_price'])
    report(f"{p['ticker']}: market value = shares x price", val, p['market_value'], 0.01)
    report(f"{p['ticker']}: gain = value - cost", val - cost, p['unrealized_gain'], 0.01)
    tot_val += val
    tot_cost += cost
inv = shown['investments']
report('Portfolio value (Investments page)', tot_val, find(inv, r'PORTFOLIO VALUE'), 0.01)
report('Invested (Investments page)', tot_cost, find(inv, r'PORTFOLIO VALUE\s*\n\s*\$[\d,.]+\s*\n'), 0.01)
report('Unrealized gain (Investments page)', tot_val - tot_cost, find(inv, r'UNREALIZED GAIN'), 0.01)
g = re.search(r'UNREALIZED GAIN\s*\n\s*\+?\$[\d,.]+\s*\n\s*\+?([\d.]+)%', inv)
report('Unrealized gain %', round((tot_val - tot_cost) / tot_cost * 100, 1) if tot_cost else None, g and float(g.group(1)), 0.05)

# ── 7. Net worth ─────────────────────────────────────────────────────────────────────────────────────────────────
s = raw['settings']
savings = float(s.get('savings_balance') or 0)
k401, ira = float(s.get('retirement_401k') or 0), float(s.get('retirement_ira') or 0)
debt_total = sum(c['bal'] for c in cards)
nw = shown['networth']
assets_page, liab_page = find(nw, r'Total assets'), find(nw, r'Total liabilities')
report('Net worth: liabilities = the debts', debt_total, liab_page, 0.01)
report('Net worth: assets = savings + portfolio + 401(k) + IRA', savings + tot_val + k401 + ira, assets_page, 0.01,
       f'{savings} + {tot_val:.2f} + {k401} + {ira}')
report('Net worth = assets - liabilities (headline)', savings + tot_val + k401 + ira - debt_total, find(nw, r'CURRENT NET WORTH'), 0.01)

# ── 8. The minimum shown beside each loan ────────────────────────────────────────────────────────────────────────
for x in debts:
    if (x.get('debt_type') or 'credit') != 'credit':
        m = re.search(re.escape(x['name']) + r'.{0,4}min \$([\d,]+\.\d\d)', b)
        report(f"Budget: no card-formula 'min' beside {x['name']} (a fixed payment)", 0, money('$' + m.group(1)) if m else 0, 0.001)

# ── report ───────────────────────────────────────────────────────────────────────────────────────────────────────
w = max(len(r[1]) for r in rows)
bad = 0
for ok, what, ours, theirs, note in rows:
    bad += not ok
    f = lambda v: '-' if v is None else (f'{v:,.2f}' if isinstance(v, float) else str(v))
    print(f"{'OK  ' if ok else 'DIFF'} {what.ljust(w)}  ours {f(ours):>12}  app {f(theirs):>12}  {note}")
print(f'\n{len(rows) - bad} agree, {bad} differ')
