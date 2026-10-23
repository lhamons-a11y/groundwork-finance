"""Item 111 measurement (gw 2.0/TRANSFERS.md section 1): how a ledger's transfers, card payments, refunds and cash
are counted today. Read-only: the database is opened read-only and nothing is written. It prints counts and totals
only - no names, no descriptions, no account numbers - so its output can be pasted into the spec.

Usage: python3 scripts/transfer_measure.py [path/to/groundwork.db]
       (default: this computer's Groundwork database)
"""
import os
import re
import sqlite3
import sys
from collections import defaultdict
from datetime import date, timedelta

PAIR_DAYS = 3          # the two sides of a move between the person's own accounts land within this many days
CARD_DAYS = 5          # a card payment leaves checking and reaches the card within this many days

REFUND = re.compile(r'\brefund\b|\breversal\b|\bchargeback\b|\bcredit memo\b|\breturn.{0,10}(credit|merch)|\bmerchandise return\b', re.I)
ATM = re.compile(r'\batm\b|\bcash withdrawal\b', re.I)
PERSON_APP = re.compile(r'\bvenmo\b|\bcash app\b|\bzelle\b|\bpaypal\b', re.I)
OWN_WORDS = re.compile(r'\btransfer (to|from)\b|\binternal transfer\b|\bonline transfer\b|\bach transfer\b|\bsavings\b', re.I)


def default_db():
    home = os.path.expanduser('~')
    if sys.platform == 'win32':
        return os.path.join(os.environ.get('LOCALAPPDATA', home), 'Groundwork', 'groundwork.db')
    if sys.platform == 'darwin':
        return os.path.join(home, 'Library', 'Application Support', 'Groundwork', 'groundwork.db')
    return os.path.join(home, '.local', 'share', 'Groundwork', 'groundwork.db')


def main(path):
    con = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
    cats = {r[0]: {'name': r[1] or '', 'type': (r[2] or '').lower(), 'parent': r[3]}
            for r in con.execute('SELECT id, name, type, parent_id FROM categories')}
    accts = {r[0]: (r[1] or '').lower() for r in con.execute('SELECT id, type FROM accounts')}

    def top(cid):
        c = cats.get(cid)
        while c and c['parent'] in cats:
            c = cats[c['parent']]
        return c

    def filed(cid):
        c, t = cats.get(cid), top(cid)
        if not c:
            return 'uncategorized'
        if c['type'] == 'transfer' or (t and t['type'] == 'transfer') or c['name'] == 'Transfer' or (t and t['name'] == 'Transfer'):
            return 'transfer'
        if c['name'] == 'Debt' or (t and t['name'] == 'Debt'):
            return 'debt'
        if c['type'] == 'income' or (t and t['type'] == 'income'):
            return 'income'
        return 'other'

    rows = [{'id': r[0], 'date': date.fromisoformat(str(r[1])[:10]), 'amount': abs(float(r[2] or 0)), 'type': r[3],
             'cat': r[4], 'acct': r[5], 'text': f'{r[6] or ""} {r[7] or ""}', 'filed': filed(r[4])}
            for r in con.execute('SELECT id, date, amount, type, category_id, account_id, description, merchant FROM transactions')
            if r[1]]
    if not rows:
        print('No transactions.')
        return
    print(f'Transactions: {len(rows)}, {min(r["date"] for r in rows)} to {max(r["date"] for r in rows)}, '
          f'{len({r["acct"] for r in rows})} accounts')

    # own-account pairs: a debit on one account, a credit of the same amount on another within PAIR_DAYS
    credits = defaultdict(list)
    for r in rows:
        if r['type'] == 'credit':
            credits[round(r['amount'], 2)].append(r)
    paired, used = [], set()
    for r in sorted((x for x in rows if x['type'] == 'debit'), key=lambda x: x['date']):
        for c in credits.get(round(r['amount'], 2), []):
            if c['id'] in used or c['acct'] == r['acct'] or abs((c['date'] - r['date']).days) > PAIR_DAYS:
                continue
            used.add(c['id'])
            paired.append((r, c))
            break
    print(f'\nMoney leaving one of your accounts and the same amount arriving in another within {PAIR_DAYS} days: '
          f'{len(paired)} pairs, ${sum(d["amount"] for d, _ in paired):,.2f}')
    kinds = defaultdict(int)
    for d, c in paired:
        kinds[(d['filed'], c['filed'], accts.get(c['acct'], '?'))] += 1
    for (fd, fc, at), n in sorted(kinds.items(), key=lambda x: -x[1]):
        print(f'  out filed {fd:13} -> in filed {fc:13} (into a {at or "?"} account): {n}')
    counted = [(d, c) for d, c in paired if d['filed'] not in ('transfer',)]
    print(f'  of these, the leaving side counted as spending today (not filed Transfer): {len(counted)}, '
          f'${sum(d["amount"] for d, _ in counted):,.2f}')
    inc = [(d, c) for d, c in paired if c['filed'] == 'income']
    print(f'  the arriving side counted as income: {len(inc)}, ${sum(c["amount"] for _, c in inc):,.2f}')

    debt = [r for r in rows if r['type'] == 'debit' and r['filed'] == 'debt']
    card_seen = [r for r in debt if any(c['id'] in used for d, c in paired if d['id'] == r['id'])]
    print(f'\nDebits filed under Debt (card and loan payments): {len(debt)}, ${sum(r["amount"] for r in debt):,.2f} '
          f'- all counted as spending by the page today')
    print(f'  of these, the card or loan side is also in the ledger (so its purchases count too): {len(card_seen)}, '
          f'${sum(r["amount"] for r in card_seen):,.2f}')

    tr = [r for r in rows if r['filed'] == 'transfer']
    print(f'\nRows filed Transfer: {len(tr)}')
    for label, rx in (('refunds', REFUND), ('cash withdrawals', ATM), ('Venmo / Zelle / Cash App / PayPal', PERSON_APP),
                      ('"transfer to/from", savings', OWN_WORDS)):
        hit = [r for r in tr if rx.search(r['text'])]
        print(f'  {label:36}: {len(hit):4}, ${sum(r["amount"] for r in hit):,.2f}'
              + ('  (a refund filed Transfer never reduces spending)' if label == 'refunds' else ''))
    unpaired = [r for r in tr if r['type'] == 'debit' and not any(d['id'] == r['id'] for d, _ in paired)]
    print(f'  Transfer debits with no arriving side in the ledger: {len(unpaired)}, ${sum(r["amount"] for r in unpaired):,.2f}')

    print('\nSpending by month - today\'s rule (a debit not filed Transfer) against one that leaves out own-account '
          'pairs and debt payments and nets refunds:')
    pair_out = {d['id'] for d, _ in paired}
    by_now, by_new = defaultdict(float), defaultdict(float)
    for r in rows:
        m = r['date'].strftime('%Y-%m')
        if r['type'] == 'debit' and r['filed'] != 'transfer':
            by_now[m] += r['amount']
        if r['type'] == 'debit' and r['filed'] not in ('transfer', 'debt') and r['id'] not in pair_out:
            by_new[m] += r['amount']
        if r['type'] == 'credit' and REFUND.search(r['text']):
            by_new[m] -= r['amount']
    for m in sorted(by_now)[-8:]:
        print(f'  {m}: ${by_now[m]:>11,.2f}  ->  ${by_new[m]:>11,.2f}   ({by_new[m] - by_now[m]:+,.2f})')


if __name__ == '__main__':
    p = sys.argv[1] if len(sys.argv) > 1 else default_db()
    if not os.path.exists(p):
        sys.exit(f'No Groundwork database at {p}')
    main(p)
