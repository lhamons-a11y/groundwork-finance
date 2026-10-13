"""Item 65 W3 (gw 2.0/AGENT_W_ITEMS.md; Rob 2026-10-12: "approve as recommended"): the one calendar of what's coming.

    W3-a  every entry confirmed / expected / possible, never mixed, each labelled with where it came from
    W3-b  the Calendar page, the dashboard's Upcoming card and the Sunday check-in read one source
    W3-c  nothing reminds or pushes; nothing is inferred from purchases (TM5)
"""
import json
from datetime import date, timedelta


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    app = ctx.app_src
    from core import upcoming as up
    from core.database import (AppSetting, BillReading, BudgetItem, DebtAccount, SinkingFund, Transaction, Trip,
                               db_session)
    from datetime import datetime

    check('s210 a monthly day clamps to short months (the 31st is Feb 28 / 29), and lands every month in range',
          up.monthly_dates(31, date(2027, 2, 1), date(2027, 3, 31)) == [date(2027, 2, 28), date(2027, 3, 31)]
          and up.monthly_dates(15, date(2026, 11, 1), date(2027, 1, 31)) == [date(2026, 11, 15), date(2026, 12, 15), date(2027, 1, 15)]
          and up.monthly_dates('x', date(2026, 1, 1), date(2026, 2, 1)) == [])

    today = date.today()
    soon = today + timedelta(days=5)
    with db_session() as s:
        d = DebtAccount(name='s210 Visa', current_balance=900, begin_balance=900, minimum_payment=35, due_day=soon.day,
                        is_active=True, debt_type='credit')
        item = BudgetItem(name='s210 Electric', category='Utilities', amount=120, type='expense', is_active=True)
        s.add_all([d, item]); s.flush()
        br = BillReading(budget_item_id=item.id, amount=131.40, due_date=soon, read_at=datetime.now(), source_host='s210.example')
        fund = SinkingFund(name='s210 Tires', target_amount=600, current_amount=100, deadline=(today + timedelta(days=40)).isoformat(), is_active=True)
        trip = Trip(label='s210 Denver', depart=(today + timedelta(days=20)).isoformat(), ret=(today + timedelta(days=24)).isoformat(), total=900, status='going')
        plan = Trip(label='s210 Maybe', depart=(today + timedelta(days=21)).isoformat(), total=500, status='planning')
        # a steady monthly charge nobody budgeted, 4 months running; and a weekly coffee (not a monthly bill)
        for k in range(1, 5):
            m = (today.replace(day=1) - timedelta(days=28 * k)).replace(day=9)
            s.add(Transaction(date=m, amount=15.49, type='debit', merchant='S210 STREAMCO', description='S210 STREAMCO'))
        for k in range(1, 9):
            s.add(Transaction(date=today - timedelta(days=7 * k), amount=4.50, type='debit', merchant='S210 COFFEE', description='S210 COFFEE'))
        s.add_all([br, fund, trip, plan])
        s.query(AppSetting).filter_by(key='yearly_bills_json').delete()
        s.add(AppSetting(key='yearly_bills_json', value=json.dumps([
            {'payee': 's210 Geico', 'amount': 612, 'months': [((today + timedelta(days=60)).month)], 'day': 10, 'answer': 'yes'},
            {'payee': 's210 Not mine', 'amount': 80, 'months': [((today + timedelta(days=60)).month)], 'day': 10, 'answer': 'no'}])))
        s.commit()
        pay = [{'payer': 's210 ACME', 'state': 'steady', 'every': 14, 'last': (today - timedelta(days=10)).isoformat()},
               {'payer': 's210 GONE', 'state': 'missing', 'every': 14, 'last': (today - timedelta(days=40)).isoformat()}]
        ents = up.entries(s, today, today + timedelta(days=90), pay=pay,
                          recurring=[{'name': 's210 Gym', 'amount': 30, 'dayOfMonth': soon.day}], people={'s210 ACME': 'Rob'})
    mine = [e for e in ents if 's210' in e['title'] or 'S210' in e['title']]
    by = {}
    for e in mine:
        by.setdefault(e['title'], []).append(e)
    cert = {t: {x['certainty'] for x in v} for t, v in by.items()}
    check(f"s210 W3-a every kind carries its certainty: entered or stated dates confirmed, worked-out ones expected, a yearly yes possible ({sorted(cert.items())[:6]})",
          cert.get('s210 Visa') == {'confirmed'} and cert.get('s210 Gym') == {'confirmed'} and cert.get('s210 Electric') == {'confirmed'}
          and cert.get('Trip to s210 Denver') == {'confirmed'} and cert.get('s210 Tires') == {'confirmed'}
          and cert.get('s210 ACME') == {'expected'} and cert.get('S210 STREAMCO') == {'expected'}
          and cert.get('s210 Geico') == {'possible'}
          and all(e['certainty'] in ('confirmed', 'expected', 'possible') and e['source'] for e in ents))
    check('s210 W3-a what is not on the record is not on the calendar: a trip still being planned, a missing payer, a weekly coffee, a yearly "no"',
          'Trip to s210 Maybe' not in by and 's210 GONE' not in by and 'S210 COFFEE' not in by and 's210 Not mine' not in by)
    sc = by.get('S210 STREAMCO', [{}])[0]
    check(f"s210 W3-a a worked-out date says how it was worked out ({sc.get('source')})",
          sc.get('source', '').startswith('about the 9th') and by['s210 ACME'][0]['person'] == 'Rob'
          and by['s210 ACME'][0]['source'].startswith('every 14 days'))
    check('s210 entries are in date order', [e['date'] for e in ents] == sorted(e['date'] for e in ents))

    # W3-b: one source
    r = c.get('/api/calendar?days=30', headers=H)
    d = (r.get_json() or {}).get('data') or {}
    ck = (c.get('/api/checkin', headers=H).get_json() or {}).get('data') or {}
    week_bills = {(b['name'], b['date']) for b in ((ck.get('facts') or ck).get('bills') or [])}
    cal_week = {(e['title'], e['date']) for e in d.get('entries', []) if e['kind'] in ('debt', 'recurring', 'bill')
                and e['date'] <= (today + timedelta(days=6)).isoformat() and (e['kind'] != 'debt' or e['amount'])}
    check(f's210 W3-b the Sunday check-in\'s week ahead is the calendar\'s week ({len(week_bills)} bills)',
          r.status_code == 200 and week_bills == cal_week and ('s210 Visa', soon.isoformat()) in week_bills)
    import inspect
    from core import checkin as ckm
    dash = app.split('function _renderDashUpcoming() {')[1].split('\n}\n')[0]
    check('s210 W3-b the check-in and the dashboard card read the calendar; neither works out dates of its own any more',
          'upcoming.entries(' in inspect.getsource(ckm.facts) and 'def next_day' not in inspect.getsource(ckm.facts)
          and "API.get('/api/calendar?days=7')" in app and '_dashCalendar' in dash
          and 'const due  = new Date(today.getFullYear(), today.getMonth(), day)' not in dash)
    cal_js = app.split('async function renderCalendar() {')[1].split('\n}\n')[0]
    check('s210 W3 the Calendar page: in the sidebar, by week for four weeks then folded by month (item 79 U3), each entry labelled, linked to where it lives',
          'data-view="calendar"' in ctx.html_src and 'id="calendarContent"' in ctx.html_src and "calendar: 'Calendar'" in app
          and "'Week of '" in cal_js and "_CAL_CERT[e.certainty]" in cal_js and "showView('${e.view}')" in cal_js)
    check('s210 W3-c nothing reminds or pushes, and no model is called',
          not any(w in cal_js for w in ('Notification', 'setInterval', 'setTimeout', 'callAI'))
          and 'Nothing here reminds or pushes' in ctx.html_src)

    with db_session() as s:
        s.query(Transaction).filter(Transaction.merchant.in_(['S210 STREAMCO', 'S210 COFFEE'])).delete(synchronize_session=False)
        s.query(BillReading).filter(BillReading.source_host == 's210.example').delete(synchronize_session=False)
        s.query(BudgetItem).filter_by(name='s210 Electric').delete()
        s.query(DebtAccount).filter_by(name='s210 Visa').delete()
        s.query(SinkingFund).filter_by(name='s210 Tires').delete()
        s.query(Trip).filter(Trip.label.like('s210%')).delete(synchronize_session=False)
        s.query(AppSetting).filter_by(key='yearly_bills_json').delete()
        s.commit()
