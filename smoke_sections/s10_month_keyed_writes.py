"""Month-keyed writes: net worth snapshot + sinking fund auto-credit.

Both branch on date.today().strftime('%Y-%m'), so what they do depends on what
month it is. Month-boundary logic only misbehaves on the 1st, which is the day
nobody is watching.
"""
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

    # auto_credit_sinking_funds(): the gate is last_contributed_month == this
    # month, so it is per-month, not once-ever. A fund last credited in a PRIOR
    # month must credit again - that is the whole purpose of the field, and the
    # part a month-boundary bug would silently break.
    with _dbs() as session:
        session.add(_SF2(name='Smoke AutoCredit Stale', target_amount=1000.0,
                          current_amount=0.0, monthly_contribution=100.0,
                          is_active=True, last_contributed_month=_prev_month))
        session.add(_SF2(name='Smoke AutoCredit Capped', target_amount=500.0,
                          current_amount=480.0, monthly_contribution=100.0,
                          is_active=True, last_contributed_month=''))
        session.add(_SF2(name='Smoke AutoCredit Inactive', target_amount=1000.0,
                          current_amount=0.0, monthly_contribution=100.0,
                          is_active=False, last_contributed_month=''))
        session.commit()

    r = c.post('/api/sinking-funds/auto-credit', headers=H)
    check('POST /api/sinking-funds/auto-credit succeeds and reports the current month',
          r.status_code == 200
          and ((r.get_json() or {}).get('data') or {}).get('month') == _this_month)

    with _dbs() as session:
        stale = session.query(_SF2).filter_by(name='Smoke AutoCredit Stale').first()
        check('a fund last credited in a PRIOR month is credited again '
              '(the gate is per-month, not once-ever)',
              stale.current_amount == 100.0
              and stale.last_contributed_month == _this_month)
        capped = session.query(_SF2).filter_by(name='Smoke AutoCredit Capped').first()
        check('a contribution is capped at the fund target, never overshooting it',
              capped.current_amount == 500.0)
        inactive = session.query(_SF2).filter_by(name='Smoke AutoCredit Inactive').first()
        check('an inactive fund is not credited',
              inactive.current_amount == 0.0 and inactive.last_contributed_month == '')

    c.post('/api/sinking-funds/auto-credit', headers=H)
    with _dbs() as session:
        stale = session.query(_SF2).filter_by(name='Smoke AutoCredit Stale').first()
        capped = session.query(_SF2).filter_by(name='Smoke AutoCredit Capped').first()
        check('a second auto-credit in the same month does not double-credit',
              stale.current_amount == 100.0 and capped.current_amount == 500.0)
