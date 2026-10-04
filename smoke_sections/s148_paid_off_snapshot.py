"""A payoff is a note on the month's net worth, never a $0 net worth (gw 2.0/PAID_OFF_SNAPSHOT.md, item 38; Rob
2026-10-04: "I accept your recommendations" / "Yes I authorize 38 build").

Marking a debt paid posted a snapshot with no figures, read as $0: the month was recorded at $0 net worth (with a $0
milestone reading) whenever it reached the server first, the real snapshot was then refused, and sent alongside the
real one it wrote two rows for the month in 20 of 20 trials.
    P1  the payoff is the month's note; a month already taken gets the note, its figures untouched
    P2  a snapshot without figures is refused
    P3  one snapshot per month, under a lock
    P4  rows already written are never deleted or rewritten; the readers use the month's figures, and a month with
        only an all-zero record is returned marked `without_figures`
    P5  a $0 milestone reading logged the day an all-zero snapshot was written is left out, and said
"""
import json
import threading
from datetime import date, datetime, timedelta


def run(ctx):
    check, HJ = ctx.check, ctx.HJ
    import server
    from core.database import AppSetting, HistorianEntry, NetWorthSnapshot

    month = date.today().strftime('%Y-%m')

    def post(app_client, **body):
        return app_client.post('/api/net-worth/snapshot', headers=HJ, data=json.dumps(body))

    def month_rows():
        with ctx.dbs() as s:
            return [(r.assets, r.liabilities, r.net_worth, r.notes) for r in
                    s.query(NetWorthSnapshot).filter_by(snapshot_date=month).order_by(NetWorthSnapshot.id).all()]

    def clear_month():
        with ctx.dbs() as s:
            s.query(NetWorthSnapshot).filter_by(snapshot_date=month).delete()
            s.commit()

    with ctx.dbs() as s:
        saved = [(r.id, r.snapshot_date, r.assets, r.liabilities, r.net_worth, r.notes, r.created_at)
                 for r in s.query(NetWorthSnapshot).filter_by(snapshot_date=month).all()]
        s.query(NetWorthSnapshot).filter_by(snapshot_date=month).delete()
        s.commit()
    c = ctx.c
    try:
        # Ps3 - P2
        bare = [post(c, force=False, note='Paid off: Visa').status_code, post(c, force=True).status_code,
                post(c, assets=1000).status_code, post(c, assets='9000', liabilities=0).status_code,
                post(c, assets=True, liabilities=0).status_code]
        check('s148 Ps3 P2 a snapshot without assets and liabilities as numbers is refused (never read as $0)',
              bare == [400, 400, 400, 400, 400] and month_rows() == [])

        # Ps1 - P1: no snapshot yet; the one real snapshot carries the payoff note
        r = post(c, force=False, assets=52000, liabilities=4000, note='Paid off: Visa')
        check('s148 Ps1 P1 the payoff month is recorded once, with its real figures and the payoff as its note',
              r.status_code == 200 and month_rows() == [(52000.0, 4000.0, 48000.0, 'Paid off: Visa')])

        # Ps2 - P1: the month already taken - the note is added, the figures untouched, and only once
        r2 = post(c, force=False, assets=52000, liabilities=0, note='Paid off: Mastercard')
        post(c, force=False, assets=1, liabilities=1, note='Paid off: Mastercard')
        rows = month_rows()
        check('s148 Ps2 P1 a payoff in a month already taken adds its note and leaves the figures alone (once)',
              r2.status_code == 200 and ((r2.get_json() or {}).get('data') or {}).get('noted') is True
              and len(rows) == 1 and rows[0][:3] == (52000.0, 4000.0, 48000.0)
              and rows[0][3] == 'Paid off: Visa Paid off: Mastercard')

        # P1, found in the browser: totals all zero (the last debt just paid, nothing else entered) - the note alone
        r3 = post(c, note_only=True, note='Paid off: Amex')
        rows = month_rows()
        clear_month()
        r4 = post(c, note_only=True, note='Paid off: Amex')
        check('s148 P1 a note-only request adds the payoff to the month\'s snapshot, and never creates one',
              ((r3.get_json() or {}).get('data') or {}).get('noted') is True and rows[0][3].endswith('Paid off: Amex')
              and len(rows) == 1 and ((r4.get_json() or {}).get('data') or {}).get('noted') is False
              and month_rows() == [])

        # Ps4 - P3: two creates at once never make two rows for the month
        dups = 0
        for _ in range(20):
            clear_month()
            ts = [threading.Thread(target=lambda: post(c.application.test_client(), force=False,
                                                       assets=52000, liabilities=4000)) for _ in range(2)]
            [t.start() for t in ts]
            [t.join() for t in ts]
            dups += len(month_rows()) != 1
        check('s148 Ps4 P3 two snapshots sent at once: one row for the month in 20 of 20 trials', dups == 0)

        # Ps5 / Ps6 - P4: rows the old marker wrote are read for what they are, never deleted or rewritten
        clear_month()
        with ctx.dbs() as s:
            s.add(NetWorthSnapshot(snapshot_date='1999-01', assets=0, liabilities=0, net_worth=0, notes='Paid off: Old'))
            s.add(NetWorthSnapshot(snapshot_date='1999-01', assets=30000, liabilities=5000, net_worth=25000, notes=''))
            s.add(NetWorthSnapshot(snapshot_date='1999-02', assets=0, liabilities=0, net_worth=0, notes='Paid off: Old2'))
            s.add(NetWorthSnapshot(snapshot_date='1999-03', assets=31000, liabilities=5000, net_worth=26000, notes=''))
            s.commit()
            before = s.query(NetWorthSnapshot).filter(NetWorthSnapshot.snapshot_date.like('1999-%')).count()
        hist = (c.get('/api/net-worth/snapshots?months=500', headers=HJ).get_json() or {}).get('data') or []
        old = [h for h in hist if h['date'].startswith('1999-')]
        check('s148 Ps5 P4 a month with an all-zero record beside a real one is read as the real one (one row, $25,000)',
              [(h['date'], h['net_worth'], h['without_figures']) for h in old if h['date'] == '1999-01']
              == [('1999-01', 25000.0, False)])
        check('s148 Ps6 P4 a month whose only record has no figures is returned marked without_figures, not as a value',
              [(h['date'], h['without_figures']) for h in old if h['date'] == '1999-02'] == [('1999-02', True)])
        with ctx.dbs() as s:
            after = s.query(NetWorthSnapshot).filter(NetWorthSnapshot.snapshot_date.like('1999-%')).count()
        check('s148 P4 nothing was deleted or rewritten to read them', after == before == 4)
        with ctx.dbs() as s:
            only_nw = NetWorthSnapshot(snapshot_date='1999-04', assets=0, liabilities=0, net_worth=12000, notes='')
            s.add(only_nw)
            s.commit()
        hist = (c.get('/api/net-worth/snapshots?months=500', headers=HJ).get_json() or {}).get('data') or []
        check('s148 P4 a row with a net worth but no breakdown is a figure, never set aside (only 0 / 0 / 0 is)',
              [(h['net_worth'], h['without_figures']) for h in hist if h['date'] == '1999-04'] == [(12000.0, False)])

        # P4: a real snapshot this month is added beside an old all-zero row, never written over it
        with ctx.dbs() as s:
            s.add(NetWorthSnapshot(snapshot_date=month, assets=0, liabilities=0, net_worth=0, notes='Paid off: Visa'))
            s.commit()
        r = post(c, force=False, assets=52000, liabilities=4000)
        rows = month_rows()
        check('s148 P4 the real snapshot is not refused by an old all-zero row for the month; both rows remain',
              r.status_code == 200 and ((r.get_json() or {}).get('data') or {}).get('taken') is True
              and sorted(x[2] for x in rows) == [0.0, 48000.0])

        # Ps7 - P5
        goal = 's148goal'
        with ctx.dbs() as s:
            prior = s.query(AppSetting).filter_by(key='nw_goals_json').first()
            prior_val = prior.value if prior else None
            day = datetime.utcnow()
            zero_snap = s.query(NetWorthSnapshot).filter_by(snapshot_date=month, net_worth=0).first()
            zero_snap.created_at = day
            for actual, when in ((0.0, day), (48000.0, day - timedelta(days=40)), (50000.0, day - timedelta(days=10))):
                e = HistorianEntry(event_category='net_worth_milestone_variance', expected_value=49000.0,
                                   actual_value=actual, variance_pct=round((actual - 49000) / 49000 * 100, 2),
                                   context_json=json.dumps({'milestone_id': goal}))
                e.created_at = when
                s.add(e)
            s.commit()
            res = server.get_net_worth_milestone_confidence(s, goal)
        check('s148 Ps7 P5 the $0 reading from the day an all-zero snapshot was written is left out, and said',
              res['samples'] == 2 and res['left_out'] == 1 and 'left out' in res['reasoning'])
    finally:
        with ctx.dbs() as s:
            s.query(NetWorthSnapshot).filter(NetWorthSnapshot.snapshot_date.like('1999-%')).delete(synchronize_session=False)
            s.query(NetWorthSnapshot).filter_by(snapshot_date=month).delete()
            s.query(HistorianEntry).filter(HistorianEntry.context_json.like('%s148goal%')).delete(synchronize_session=False)
            for (_id, d, a, l, n, notes, ca) in saved:
                s.add(NetWorthSnapshot(snapshot_date=d, assets=a, liabilities=l, net_worth=n, notes=notes, created_at=ca))
            s.commit()

    app = ctx.app_src
    paid = app.split('function setCardPaidInFull', 1)[1][:2500] if 'function setCardPaidInFull' in app else ''
    check('s148 P1 marking a debt paid sends no snapshot of its own: the one real snapshot carries the payoff note',
          "autoSnapshotNetWorthIfDue(`Paid off: ${card.name || 'Debt account'}`)" in paid
          and "note:  `Paid off:" not in paid and 'async function autoSnapshotNetWorthIfDue(extraNote)' in app
          and 'note: _nwSnapshotNote(extraNote)' in app
          and "if (extraNote) await API.post('/api/net-worth/snapshot', { note_only: true, note: extraNote });" in app)
    check('s148 P4 the page never draws or compares a month recorded without figures, and says so',
          '_nwHistory = rows.filter(r => !r.without_figures);' in app and 'recorded without figures' in app
          and "(nwRes.data || []).filter(r => !r.without_figures)" in app)
    check('s148 P5 the milestone shows how many $0 readings were left out', 'conf.left_out' in app
          and 'confBadge + leftOut' in app)
