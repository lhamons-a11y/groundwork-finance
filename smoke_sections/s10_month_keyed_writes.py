"""Month-keyed writes: net worth snapshot; and sinking fund auto-credit, now retired (item 114 F1).

Both branch on date.today().strftime('%Y-%m'), so what they do depends on what
month it is. Month-boundary logic only misbehaves on the 1st, which is the day
nobody is watching.
"""
from pathlib import Path
import json
import re
from datetime import date as _date, timedelta as _timedelta


def run(ctx):
    check, BASE, c, H, HJ, _dbs = ctx.check, ctx.BASE, ctx.c, ctx.H, ctx.HJ, ctx.dbs
    # Both of these key off date.today().strftime('%Y-%m') and decide whether
    # to write based on what month it is. Neither behaviour was covered: the
    # snapshot route was only ever called with force=True (which skips the
    # guard entirely), and /api/sinking-funds/auto-credit had no test at all.
    # Month-boundary logic misbehaves on the 1st, which is the day nobody is
    # watching, so it is worth pinning down here.
    from core.database import NetWorthSnapshot as _NWS, SinkingFund as _SF2

    _this_month = _date.today().strftime('%Y-%m')
    _prev_month = (_date.today().replace(day=1) - _timedelta(days=1)).strftime('%Y-%m')

    # create_snapshot(): the month it lands in, and the no-overwrite guard.
    with _dbs() as session:
        session.query(_NWS).filter_by(snapshot_date=_this_month).delete()
        session.commit()

    r = c.post('/api/net-worth/snapshot', headers=HJ,
               json={'assets': 9000, 'liabilities': 2000})
    _snap = ((r.get_json() or {}).get('data') or {}).get('snapshot') or {}
    check('POST /api/net-worth/snapshot keys the snapshot to the current month',
          r.status_code == 200 and _snap.get('date') == _this_month
          and _snap.get('net_worth') == 7000.0)

    r = c.post('/api/net-worth/snapshot', headers=HJ,
               json={'assets': 1.0, 'liabilities': 0})
    check('a second snapshot in the same month is refused without force=true',
          r.status_code == 200
          and ((r.get_json() or {}).get('data') or {}).get('taken') is False)

    with _dbs() as session:
        rows = session.query(_NWS).filter_by(snapshot_date=_this_month).all()
        check('the refused snapshot neither overwrote the row nor added a second',
              len(rows) == 1 and rows[0].net_worth == 7000.0)

    c.post('/api/net-worth/snapshot', headers=HJ,
           json={'force': True, 'assets': 12000, 'liabilities': 2000})
    with _dbs() as session:
        rows = session.query(_NWS).filter_by(snapshot_date=_this_month).all()
        check('force=true overwrites the month in place rather than adding a row',
              len(rows) == 1 and rows[0].net_worth == 10000.0)

    # Item 114 F1 (Rob 2026-10-30): auto-credit is retired. It added each fund's plan every month the Budget or Gift
    # page loaded, whether or not money moved. A fund now holds what was put in, and nothing adds the plan as saved.
    with _dbs() as session:
        session.add(_SF2(name='Smoke F1 Fund', target_amount=1000.0, current_amount=250.0,
                          monthly_contribution=100.0, is_active=True, last_contributed_month=_prev_month))
        session.commit()
    r = c.post('/api/sinking-funds/auto-credit', headers=H)
    check('F1: /api/sinking-funds/auto-credit is gone', r.status_code in (404, 405))
    _app_js = (Path(BASE) / 'static' / 'js' / 'app.js').read_text(encoding='utf-8')
    check('F1: neither the Budget page nor the Gift page asks for auto-credit',
          "/api/sinking-funds/auto-credit" not in _app_js)
    c.get('/api/sinking-funds', headers=H)
    with _dbs() as session:
        f1 = session.query(_SF2).filter_by(name='Smoke F1 Fund').first()
        check('F1: reading the funds adds nothing - a fund holds what was put in', f1.current_amount == 250.0)
    _fid = f1.id
    r = c.post(f'/api/sinking-funds/{_fid}/deposit', headers=HJ, data='{"amount": 40}')
    with _dbs() as session:
        check('F1: "Add to fund" still adds what the person put in', session.get(_SF2, _fid).current_amount == 290.0)
