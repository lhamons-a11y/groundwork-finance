"""Item 115 P5 (gw 2.0/ASK_FOR_A_REPORT.md; Rob 2026-10-31, C1-C11 ruled): dates are read by code, never by the model -
core/periods.py, shared by the assistant (item 114) and Ask for a report. And the three item 114 misses it closes (C7):

    Q07  "gas this month" reads this month, not every month          Q05  a month the model made up is dropped
    Q10  "what day do we usually pay" reads the recurring charges, not what is due next
"""
from datetime import date


def run(ctx):
    check = ctx.check
    from core import periods, agent_hands as ah
    from core.database import db_session

    t = date(2026, 10, 31)

    def span(s):
        p = periods.read_period(s, t)
        return p and (p['months'][0], p['months'][-1], len(p['months']))

    check('s268 P5 Rob\'s example: "from June to September" is June-September 2026, four months',
          span('Monthly totals of debt payments from June to September') == ('2026-06', '2026-09', 4))
    check('s268 P5 a month not reached yet this year is last year\'s; a range crosses the new year',
          span('spending in December') == ('2025-12', '2025-12', 1)
          and span('November to February') == ('2025-11', '2026-02', 4))
    check('s268 P5 this month, last month, this year, last year, since, Q3, the last 3 months',
          span('this month') == ('2026-10', '2026-10', 1) and span('last month') == ('2026-09', '2026-09', 1)
          and span('this year') == ('2026-01', '2026-10', 10) and span('last year') == ('2025-01', '2025-12', 12)
          and span('since January') == ('2026-01', '2026-10', 10) and span('Q3') == ('2026-07', '2026-09', 3)
          and span('the last 3 months') == ('2026-08', '2026-10', 3))
    mid = date(2026, 10, 15)
    six = periods.read_period('the last six months', mid)
    check('s268 Rob 2026-10-31 calendar months: this month counts once complete (its last day); before that it is left '
          'out, and said',
          span('the last six months') == ('2026-05', '2026-10', 6) and not periods.read_period('the last six months', t).get('note')
          and (six['months'][0], six['months'][-1]) == ('2026-04', '2026-09') and 'October 2026 is left out' in six['note'])
    w = lambda s_, d=mid: (lambda p: p and (str(p['start']), str(p['end']), bool(p.get('window'))))(periods.read_period(s_, d))
    check('s268 Rob 2026-10-31 date to date: "to date", the last N days or weeks, day to day, since a day',
          w('the last six months to date') == ('2026-04-16', '2026-10-15', True)
          and w('the last 30 days') == ('2026-09-16', '2026-10-15', True) and w('past 2 weeks') == ('2026-10-02', '2026-10-15', True)
          and w('June 15 to September 15') == ('2026-06-15', '2026-09-15', True)
          and w('since June 15') == ('2026-06-15', '2026-10-15', True)
          and w('November 20 to February 10') == ('2025-11-20', '2026-02-10', True))
    check('s268 P5 words that are not periods read as none ("may we", "market", "since we cut that budget")',
          span('may we see it') is None and span('the market report') is None
          and span('What have we spent on coffee since we cut that budget?') is None
          and span('spending in May') == ('2026-05', '2026-05', 1))
    check('s268 P5 a period that has not begun is none; one that runs past today is cut to today',
          periods.read_period('in 2027', t) is None and periods.read_period('this month', t)['end'] == t)

    reader = ah.Reader(lambda *a, **k: {}, db_session, today=t)

    def fixed(q, lookups):
        p = ah.repair(q, {'intent': 'answer', 'lookups': lookups}, reader)
        return p['lookups'], p['repaired']

    lk, rep = fixed('How much did we pay for gas this month?', [{'name': 'transactions', 'category': 'Gasoline / Diesel'}])
    check('s268 Q07 "this month" is the month read - the model left it out', lk[0].get('month') == '2026-10'
          and any('as the question says' in r for r in rep))
    lk, rep = fixed('What have we spent on coffee since we cut that budget?',
                    [{'name': 'category_by_month', 'category': 'coffee', 'month': '2023-01'},
                     {'name': 'category_by_month', 'category': 'coffee', 'month': '2026-10'}])
    check('s268 Q05 a month the question does not name is dropped; this month stays',
          'month' not in lk[0] and lk[1].get('month') == '2026-10' and any('2023-01 dropped' in r for r in rep))
    lk, rep = fixed('In August, what did we spend on groceries?', [{'name': 'category_by_month', 'category': 'groceries',
                                                                    'month': 'this_month'}])
    check('s268 P5 a month the person named wins over the model\'s', lk[0]['month'] == '2026-08')
    real_rows = ah._rows                       # the gate's record has no Electric line: two of the bill's rows, stood in
    ah._rows = lambda r: ([{'id': i, 'date': f'2026-0{m}-12', 'payee': 'Metro Power & Light', 'category': 'Electric',
                            'account': 'Checking', 'amount': -110.0, 'type': 'debit', 'kind': 'spending', 'held': False}
                           for i, m in ((1, 8), (2, 9))], 0)
    try:
        lk, rep = fixed('What day do we usually pay the electric bill?', [{'name': 'bills_due'}])
    finally:
        ah._rows = real_rows
    check('s268 Q10 "what day do we usually pay" reads the recurring charges, and the bill\'s own rows (its amount varies)',
          [x['name'] for x in lk] == ['recurring', 'transactions'] and lk[1].get('category') == 'Electric'
          and any('recurring for bills_due' in r for r in rep))
    lk, _ = fixed('When is the electric bill due?', [{'name': 'bills_due'}])
    check('s268 Q10 "when is it due" still reads what is due', [x['name'] for x in lk] == ['bills_due'])
