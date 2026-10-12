"""Item 65 W2 (gw 2.0/AGENT_W_ITEMS.md; Rob 2026-10-12: "approve as recommended"): price changes on recurring charges.

    W2-a  a step, not noise: 2+ charges at the new level, beyond the payee's own swing; null-modelled first
    W2-b  no reason invented: only what the record shows (a frequency change, a usage bill), else just the change
    W2-c  the check-in names it the week it became a step; the Budget page keeps the list; one tap, shown first, Undo
"""
import json
import subprocess
import sys
from datetime import date, timedelta


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    from core import checkin as ck
    from core import price_change as pc
    from core.database import BudgetItem, Category, Transaction, db_session

    d0 = date(2025, 1, 10)
    mon = lambda n, f: [(d0 + timedelta(days=30 * i), f(i)) for i in range(n)]
    steady = pc.step(mon(12, lambda i: 15.49))
    up = pc.step(mon(10, lambda i: 15.49 if i < 8 else 17.99))
    one_odd = pc.step(mon(10, lambda i: 15.49 if i != 9 else 21.00))
    one_after = pc.step(mon(10, lambda i: 15.49 if i < 9 else 17.99))
    seasonal = pc.step(mon(12, lambda i: [140, 180, 120, 90, 70, 85, 130, 150, 110, 80, 75, 160][i]), 'Electric')
    interest = pc.step(mon(10, lambda i: 78.08 if i < 8 else 82.94), 'Interest / Fees')
    check('s211 W2-a a step is 2+ charges at a new level; a steady price, one odd charge, one new charge, a seasonal bill, and interest are not',
          steady is None and up and up['before'] == 15.49 and up['after'] == 17.99 and up['after_count'] == 2
          and one_odd is None and one_after is None and seasonal is None and interest is None)
    yearly = pc.step([(d0 + timedelta(days=30 * i), 12.0) for i in range(6)]
                     + [(d0 + timedelta(days=150 + 365 * k), 120.0) for k in (1, 2)])
    level = pc.step(mon(10, lambda i: 150.0 if i < 7 else 172.0), 'Electric')
    check(f"s211 W2-b the kind is only what the record shows: the gaps for a frequency change, the category for a usage bill ({yearly and yearly['kind']}, {level and level['kind']})",
          yearly and yearly['kind'] == 'frequency' and 'from monthly to yearly' in pc.sentence('X', yearly)
          and level and level['kind'] == 'usage' and up['kind'] == 'price')
    words = pc.sentence('Netflix', up)
    check(f's211 W2-b the sentence says what the charges say, and never why ({words})',
          words.startswith('Netflix: $15.49 through') and '$17.99 since' in words and '(2 charges)' in words
          and not any(w in words.lower() for w in ('because', 'raised', 'hike', 'increase', 'decided', 'likely')))
    nm = subprocess.run([sys.executable, str(ctx.BASE / 'scripts' / 'w2_null_model.py')], capture_output=True, text=True, timeout=600)
    last = (nm.stdout.strip().splitlines() or [''])[-1]
    check(f's211 W2-a the null model passes (false alarms <= 2% on trend-free series, 8%+ steps found >= 95%): {last[:60]}',
          nm.returncode == 0 and last.startswith('PASS'))

    # the record: a steady charge that stepped, its second new charge inside last week (W2-c)
    today = date.today()
    w0, w1 = ck.week_bounds(today)
    second = w0 + timedelta(days=2)
    with db_session() as s:
        cat = s.query(Category).filter_by(name='Streaming Video').first()
        cid = cat.id if cat else None
        dates = [second - timedelta(days=30 * k) for k in range(7, 0, -1)] + [second]
        for i, d in enumerate(dates):
            s.add(Transaction(date=d, amount=15.49 if i < 6 else 17.99, type='debit', merchant='S211 STREAMCO',
                              description='S211 STREAMCO', category_id=cid))
        b = BudgetItem(name='S211 Streamco', category='Streaming Video', amount=15.49, type='expense', is_active=True)
        s.add(b); s.commit(); bid = b.id
    got = (c.get('/api/price-changes', headers=H).get_json() or {}).get('data') or {}
    mine = next((x for x in got.get('changes', []) if x['payee'] == 'S211 STREAMCO'), None)
    check(f"s211 W2 the Budget list finds it from the ledger, with its charges and the line it lives on ({mine and mine['sentence']})",
          mine and mine['before'] == 15.49 and mine['after'] == 17.99 and mine['seen_on'] == second.isoformat()
          and mine['line'] and mine['line']['id'] == bid and not mine['line_matches'] and len(mine['records']) >= 4)
    ckf = (c.get('/api/checkin', headers=H).get_json() or {}).get('data') or {}
    check("s211 W2-c the Sunday check-in names it the week it became a step",
          any(p['payee'] == 'S211 STREAMCO' for p in ckf.get('price_changes', [])))

    ap = c.post('/api/price-changes/apply', headers=HJ, data=json.dumps({'payee': 'S211 STREAMCO'}))
    a = (ap.get_json() or {}).get('data') or {}
    with db_session() as s:
        after_tap = s.get(BudgetItem, bid).amount
    un = c.post('/api/price-changes/undo', headers=HJ, data=json.dumps({'kind': a.get('kind'), 'id': a.get('id'), 'amount': a.get('from')}))
    with db_session() as s:
        after_undo = s.get(BudgetItem, bid).amount
    nope = c.post('/api/price-changes/apply', headers=HJ, data=json.dumps({'payee': 'NOBODY S211'}))
    check(f"s211 W2 one tap moves the line to the record's new price, and Undo puts it back ({a.get('from')} -> {after_tap} -> {after_undo})",
          ap.status_code == 200 and a.get('from') == 15.49 and after_tap == 17.99 and un.status_code == 200
          and after_undo == 15.49 and nope.status_code == 404)

    app, html = ctx.app_src, ctx.html_src
    page = app.split('async function renderPriceChanges() {')[1].split('\n}\n')[0]
    check('s211 W2 the Budget page lists price changes with their charges, shows the change on the button, and offers Undo',
          'id="budgetPriceChanges"' in html and 'renderPriceChanges();' in app.split("if (name === 'budget')")[1][:300]
          and 'The charges' in page and 'Change it to ${fmt(c.after)}' in page and "doesn't know why a price changed" in page
          and "'/api/price-changes/undo'" in app and 'p.sentence' in app.split('function _checkinLines(f) {')[1].split('\n}\n')[0])

    with db_session() as s:
        s.query(Transaction).filter_by(merchant='S211 STREAMCO').delete(synchronize_session=False)
        s.query(BudgetItem).filter_by(name='S211 Streamco').delete()
        s.commit()
