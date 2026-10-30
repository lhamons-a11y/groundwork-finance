"""Item 106's live read (gw 2.0/YEARLY_PRICE_STEPS.md section 4): what yearly price steps finds in your own ledger.

Read-only: the database is opened with SQLite's mode=ro, so nothing in it can change. Nothing is sent anywhere; the
findings are printed here. Plain Python, nothing to install.

    python scripts/y106_live_read.py                  # the usual place for this computer
    python scripts/y106_live_read.py --db PATH        # another copy (a restored backup, say)
    python scripts/y106_live_read.py --all            # every payee with a step, not only the patterns

Close Groundwork first, or run it on a copy: a read while the app is writing can see a half-saved moment.
"""
import argparse
import json
import os
import sqlite3
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import yearly_steps as ys                        # noqa: E402
from core.price_change import USAGE_CATEGORIES            # noqa: E402

ITEM26 = {'electric', 'electricity', 'natural gas', 'propane', 'heating oil'}   # left to item 26 (Rob 2026-10-21)
# A payee whose name reads like a gas or electric bill but is filed under another category. The 2026-10-23 read found
# one item-26 payee where a household has two; these are listed so the other can be found, never moved.
ENERGY_WORDS = ('gas', 'energy', 'electric', 'power', 'propane', 'aep', 'dominion', 'columbia', 'duke', 'firstenergy')
FUEL_CATEGORIES = {'gasoline / diesel', 'gas / fuel', 'ev charging'}


def default_db():
    if os.name == 'nt':
        base = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
    elif sys.platform == 'darwin':
        base = Path.home() / 'Library' / 'Application Support'
    else:
        base = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share'))
    return base / 'Groundwork' / 'groundwork.db'


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--db', type=Path, default=default_db())
    ap.add_argument('--all', action='store_true')
    a = ap.parse_args()
    if not a.db.exists():
        sys.exit(f'No database at {a.db}. Give its path with --db.')
    con = sqlite3.connect(a.db.resolve().as_uri() + '?mode=ro', uri=True)     # file:///C:/... on Windows, spaces escaped
    rows = con.execute(
        "SELECT COALESCE(NULLIF(t.merchant, ''), t.description), t.date, t.amount, COALESCE(c.name, '') "
        "FROM transactions t LEFT JOIN categories c ON c.id = t.category_id "
        "WHERE t.type = 'debit' AND COALESCE(NULLIF(t.merchant, ''), t.description) != ''").fetchall()
    ans = con.execute("SELECT value FROM app_settings WHERE key = 'yearly_step_answers'").fetchone()
    answers = json.loads(ans[0]) if ans and ans[0] else {}
    con.close()

    by, cat = defaultdict(list), {}
    for payee, d, amt, c in rows:
        try:
            dd = date.fromisoformat(str(d)[:10])
        except ValueError:
            continue
        by[payee].append((dd, amt))
        cat[payee] = c
    today = date.today()
    dates = [d for xs in by.values() for d, _ in xs]
    print(f'Ledger: {a.db}')
    if not dates:
        sys.exit('No spending transactions to read.')
    span = (max(dates).year - min(dates).year) * 12 + max(dates).month - min(dates).month + 1
    long = sum(1 for xs in by.values()
               if (max(d for d, _ in xs) - min(d for d, _ in xs)).days >= 700)
    print(f'{len(rows)} spending transactions, {len(by)} payees, {min(dates)} to {max(dates)} ({span} months).')
    print(f'{long} payees have two years or more between their first and last charge - '
          f'a yearly pattern needs that.\n')

    found = {'pattern3': [], 'pattern2': [], 'one': [], 'range': []}
    usage, left, energy_elsewhere = [], [], []
    for payee, xs in sorted(by.items(), key=lambda kv: kv[0].lower()):
        c = cat[payee].strip().lower()
        if c not in ITEM26 and c not in FUEL_CATEGORIES and any(w in payee.lower() for w in ENERGY_WORDS):
            energy_elsewhere.append(f'{payee} (filed under {cat[payee] or "no category"}, {len(xs)} charges)')
        if c in USAGE_CATEGORIES:
            if c in ITEM26:
                left.append(f'{payee} ({cat[payee]})')
                continue
            sm = ys.same_month(xs, today)
            if sm:
                usage.append((payee, cat[payee], sm))
            continue
        info = ys.read(xs, cat[payee])
        if not info:
            continue
        pat = ys.pattern(ys.apply_answers(info['steps'], answers.get(payee, [])))
        if not pat:
            continue
        line = ys.sentence(payee, pat)
        if pat['pattern'] and not pat['agree']:
            found['range'].append(line)
        elif pat['pattern'] and len(pat['steps']) >= ys.MIN_PROJECT:
            nxt = ys.next_expected(pat)
            found['pattern3'].append(f"{line}\n      next step expected {nxt}: about "
                                     f"${info['level'] * (1 + pat['pct']):,.2f} (now ${info['level']:,.2f})")
        elif pat['pattern']:
            found['pattern2'].append(f"{line}\n      asked about when the new price lands in {ys.next_expected(pat)}")
        else:
            found['one'].append(line)

    def show(title, items, every=True):
        print(f'{title}: {len(items)}')
        for x in (items if every else []):
            print('   ', x)
        print()
    show('Yearly patterns of three or more steps - projected ahead of the month', found['pattern3'])
    show('Two steps a year apart - said, and asked about when the new price lands', found['pattern2'])
    show('Steps a year apart that differ too much to project one figure', found['range'])
    show('One price step so far (no pattern yet)', found['one'], a.all)
    if not a.all and found['one']:
        print('    (--all lists them)\n')
    print(f'Usage bills asked about (water, sewer, municipal, utilities): {len(usage)}')
    for payee, c, sm in usage:
        print(f"    {payee} ({c}): {sm['month']} ${sm['this']:,.2f} against ${sm['last_year']:,.2f} a year earlier "
              f"({sm['pct'] * 100:+.1f}%)")
    print(f'\nGas, electric, propane and heating oil payees left to item 26: {len(left)}')
    for x in left:
        print('   ', x)
    print(f'\nNamed like a gas or electric bill but filed under another category: {len(energy_elsewhere)}')
    for x in energy_elsewhere:
        print('   ', x)


if __name__ == '__main__':
    main()
