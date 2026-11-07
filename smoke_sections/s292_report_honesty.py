"""The report builder says what the record shows, and says so when it cannot (independent review, 2026-11).

    N1  a Net Worth report keeps to its period: no match is "doesn't know yet", not the whole history instead
    N2  words that name no period are said, not ignored
    N3  a month recorded without figures is not a net worth of $0 - in a report or to the assistant
    N4  a period older than the route's default 24 months is still found
    B1  an unreadable account is left out of the total and named, never added in as $0
    B2  a figure no bank confirmed is named as such
    F1  a failed read is said, not a crash
    W1  a snapshot covers one calendar month, and says so when asked for more; a date-to-date total keeps to its days
    R1  a period before the record starts is not "no transactions yet"
"""
from datetime import date


def _snap(key, value, blank=False):
    return {'month_label': key, 'date': key, 'net_worth': value, 'total_assets': value, 'total_liabilities': 0,
            'without_figures': blank}


def _acct(name, balance, basis):
    return {'name': name, 'type': 'checking', 'balance': balance, 'balance_basis': basis}


def _txn(i, day, amount):
    return {'id': i, 'date': day, 'payee': 'Shop', 'category': 'Food', 'account': 'Checking', 'amount': amount,
            'type': 'debit', 'kind': 'spending', 'held': False}


def run(ctx):
    check = ctx.check
    from core import agent_hands as ah, report_sections as rs

    def reader(**routes):
        paths = {'snapshots': '/api/net-worth/snapshots', 'accounts': '/api/accounts/with-balances'}
        seen = []

        def get(path):
            seen.append(path)
            for k, v in routes.items():
                if paths[k] in path:
                    return v
            return []
        r = ah.Reader(get, None, today=date(2026, 11, 6))
        r.seen = seen
        return r

    rows = [_txn(1, '2026-06-01', 100), _txn(2, '2026-06-20', 10), _txn(3, '2026-07-10', 20), _txn(4, '2026-09-10', 30),
            _txn(5, '2026-09-25', 1000)]
    real_rows = ah._rows
    ah._rows = lambda reader_: (rows, 0)
    try:
        history = [_snap('2025-01', 1000.0), _snap('2025-02', 0.0, True), _snap('2025-03', 1200.0)]
        nw = reader(snapshots=history)

        o = rs.run(nw, '1.7', {'period': 'June 2026'})
        check(f"s292 N1 no snapshot in the period is not the whole history ({o['sentences']})",
              not o['enough'] and not o.get('chart') and 'June 2026' in o['sentences'][0])
        o = rs.run(nw, '1.7', {'period': '2025'})
        check(f"s292 N1 a period that has snapshots shows those ({o['sentences']})",
              o['enough'] and [p['label'] for p in o['chart']['points']] == ['2025-01', '2025-03'])
        o = rs.run(nw, '1.7', {'period': 'whenever'})
        check(f"s292 N2 words that name no period are said ({o['sentences']})",
              not o['enough'] and 'not a period' in o['sentences'][0])

        o = rs.run(nw, '1.7', {})
        check(f"s292 N3 a month without figures is not charted as $0 ({o['chart']['points']})",
              [p['value'] for p in o['chart']['points']] == [1000.0, 1200.0])
        o = rs.run(reader(snapshots=[_snap('2025-02', 0.0, True)]), '1.7', {})
        check('s292 N3 a history of only such months has no net worth to show', not o['enough'])
        told = ah.lk_net_worth(nw, {})
        check(f"s292 N3 the assistant does not hear such a month as $0, and hears it was blank ({told})",
              [m['net_worth'] for m in told['months']] == ['$1,000.00', '$1,200.00']
              and told['recorded_without_figures'] == ['2025-02'])
        check('s292 N4 a period asks for the whole history, not the last 24 months', any('months=' in p for p in nw.seen))
        o = rs.run(reader(snapshots=[_snap('2025-01', 1000.0)]), '5.7', {'period': '2025'})
        check(f"s292 N3 one month is not a comparison with itself ({o['sentences']})", not o['enough'])

        o = rs.run(reader(snapshots={'ok': False, 'error': 'x'}), '1.7', {})
        check(f"s292 F1 a failed history read is said ({o['sentences']})", not o['enough'] and 'could not be read' in o['sentences'][0])
        check('s292 F1 the assistant hears a failed history read as failed',
              ah.lk_net_worth(reader(snapshots={'ok': False, 'error': 'x'}), {}).get('enough') is False)
        o = rs.run(reader(accounts={'ok': False, 'error': 'x'}), '3.7', {})
        check(f"s292 F1 a failed accounts read is said ({o['sentences']})", not o['enough'] and 'could not be read' in o['sentences'][0])

        mixed = reader(accounts=[_acct('Good', 500.0, 'bank'), _acct('Broken', None, 'error')])
        o = rs.run(mixed, '3.7', {})
        check(f"s292 B1 an unreadable account is named and not counted ({o['sentences']})",
              o['sentences'][0] == '1 of 2 accounts read, $500.00 in all.' and 'Broken' in o['sentences'][1])
        check(f"s292 B1 the table does not show it as a figure ({o['table']['rows'][1]})", o['table']['rows'][1][1] == 'Could not be read')
        o = rs.run(mixed, '4.7', {})
        check(f"s292 B1 the tile says so too ({o['sentences']})", 'Broken' in ' '.join(o['sentences']))
        o = rs.run(reader(accounts=[_acct('Broken', None, 'error')]), '3.7', {})
        check(f"s292 B1 no readable account is no total, not $0 ({o['sentences']})", not o['enough'])
        o = rs.run(reader(accounts=[_acct('Imported', 42.0, 'activity')]), '3.7', {})
        check(f"s292 B2 an activity total is named as unconfirmed ({o['sentences']})",
              o['sentences'][0] == '1 account, $42.00 in all.' and 'Not confirmed by a bank: Imported' in o['sentences'][1]
              and 'not a confirmed balance' in o['table']['rows'][0][4])
        o = rs.run(reader(accounts=[_acct('Good', 500.0, 'bank')]), '3.7', {})
        check(f"s292 B2 a bank's balance carries no such warning ({o['sentences']})", o['sentences'] == ['1 account, $500.00 in all.'])

        o = rs.run(reader(), '1.1', {'period': 'June 15 to September 15, 2026'})
        check(f"s292 W1 a date-to-date total keeps to its days ({o['sentences'][0]})", '$60.00 in all' in o['sentences'][0])
        o = rs.run(reader(), '4.1', {'period': 'June 15 to September 15, 2026'})
        check(f"s292 W1 a snapshot says it is one calendar month ({o['sentences']})",
              any('one whole calendar month' in s and 'September 2026' in s for s in o['sentences']))
        o = rs.run(reader(), '4.1', {'period': 'September 2026'})
        check(f"s292 W1 a snapshot of one month needs no such note ({o['sentences']})",
              not any('one whole calendar month' in s for s in o['sentences']))
        o = rs.run(reader(), '1.1', {'period': 'January 2025'})
        check(f"s292 R1 a period before the record is not 'no transactions' ({o['sentences']})",
              not o['enough'] and 'no transactions yet' not in o['sentences'][0] and 'June 2026' in o['sentences'][0])
    finally:
        ah._rows = real_rows
