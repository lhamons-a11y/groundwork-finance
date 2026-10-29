"""Item 76: the Sunday check-in - the week behind, the week ahead, and why it matters (gw 2.0/SUNDAY_CHECKIN.md
S1-S12, RULED 2026-10-11; Rob: "build 76"). A fixed past week (Sunday 2019-06-16) keeps it clear of other records.

    S1/S2  narration runs only when the newest import is under 48 hours old and nothing was written since it; the
           month's review moves there too (item 75 M1 amended)
    S3  transfers are not spending          S4  the week against the week before, the month against its budget
    S5  interest as a week and a month      S6  bills due this week        S7  pay expected, named by whose pay
    S8  an overdue employer is not mentioned                                S9  facts with AI off
    S11 the written part teaches with the figures, never recites them      S12 at the top, Sundays, with Done
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import date, datetime, timedelta


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    app, html = ctx.app_src, ctx.html_src
    from core import checkin as ck
    from core.database import Account, AppSetting, Category, DebtAccount, Transaction, db_session

    sun = date(2019, 6, 16)
    check('s195 S4 the week behind is the last full Sunday to Saturday',
          ck.week_bounds(sun) == (date(2019, 6, 9), date(2019, 6, 15))
          and ck.week_bounds(date(2019, 6, 19)) == (date(2019, 6, 9), date(2019, 6, 15))
          and ck.week_bounds(date(2019, 6, 15)) == (date(2019, 6, 2), date(2019, 6, 8)))
    with db_session() as s:
        tr = s.query(Category).filter(Category.name == 'Transfer').first() or Category(name='Transfer', type='transfer')
        food = Category(name='s195 Food', type='expense')
        s.add_all([tr, food]); s.flush()
        acct = Account(name='s195 Checking'); s.add(acct); s.flush()
        acct_id = acct.id
        T = lambda d, a, cat, desc: Transaction(date=d, amount=a, type='debit', category_id=cat.id, account_id=acct.id, description=desc)
        s.add_all([T(date(2019, 6, 10), 100.0, food, 's195 a'), T(date(2019, 6, 12), 50.0, food, 's195 b'),
                   T(date(2019, 6, 11), 1500.0, tr, 's195 move'), T(date(2019, 6, 4), 90.0, food, 's195 c'),
                   T(date(2019, 6, 1), 25.0, food, 's195 d')])
        d = DebtAccount(name='s195 Card', current_balance=3650.0, interest_rate=20.0, minimum_payment=73.0, due_day=18, is_active=True)
        s.add(d); s.commit()
        pay = [{'payer': 's195 city', 'state': 'steady', 'every': 14, 'last': '2019-06-05'},
               {'payer': 's195 plant', 'state': 'missing', 'every': 7, 'last': '2019-05-01'},
               {'payer': 's195 shop', 'state': 'steady', 'every': 7, 'last': '2019-06-14'}]
        f = ck.facts(s, sun, budget_month=1000.0, pay=pay, payer_people={'s195 city': 'Rob'},
                     recurring=[{'name': 's195 Water', 'amount': 60, 'dayOfMonth': 20}, {'name': 's195 Gym', 'amount': 30, 'dayOfMonth': 2}])
    check(f's195 S3 transfers are not spending, and are named ({f["week"]})',
          f['week']['spent'] == 150.0 and f['week']['moved'] == 1500.0 and f['week']['last_week'] == 90.0 and f['week']['change'] == 60.0)
    check(f's195 S4 the month so far against its budget, with what is left and the days that remain ({f["month"]})',
          f['month']['spent'] == 265.0 and f['month']['left'] == 735.0 and f['month']['days_left'] == 14)
    check(f's195 S5 interest as a week and a month at these balances ({f["interest"]})',
          f['interest']['week'] >= 14.0 and abs(f['interest']['month'] - 3650 * 0.20 / 12) < 1)
    names = [b['name'] for b in f['bills']]
    check(f's195 S6 bills due in the week ahead, from the debt\'s due day and the recurring bills, and only those ({names})',
          names == ['s195 Card', 's195 Water'] and f['bills'][0]['amount'] == 73.0)
    check(f's195 S7/S8 pay expected this week by schedule, named by whose pay; an overdue employer is never mentioned ({f["pay"]})',
          [(p['payer'], p['person']) for p in f['pay']] == [('s195 city', 'Rob'), ('s195 shop', None)]
          and 's195 plant' not in json.dumps(f) and f['ask_whose'] == ['s195 shop'])

    # the page: the lines, run in Node
    node = shutil.which('node')
    out = None
    if node:
        fn = lambda name: re.search(r'\nfunction ' + name + r'\(.*?\n\}\n', app, re.S).group(0)
        js = ('const fmt = n => "$" + Number(n).toFixed(2);\n' + fn('_checkinWho') + fn('_movedWords') + fn('_checkinLines') +
              'console.log(JSON.stringify(_checkinLines(' + json.dumps(f) + ')));')
        fd, p = tempfile.mkstemp(suffix='.js')
        with os.fdopen(fd, 'w', encoding='utf-8') as fh:
            fh.write(js)
        try:
            out = json.loads(subprocess.run([node, p], capture_output=True, text=True, encoding='utf-8', timeout=60).stdout or 'null')
        except Exception:                      # noqa: BLE001
            out = None
        finally:
            os.remove(p)
    text = ' '.join(out or [])
    check(f's195 S4/S6/S7/S9 the facts read as written, run in Node ({out})',
          out is not None and '$150.00 spent, $60.00 more than the week before ($90.00)' in text
          and '$1500.00 moved between your own accounts - not spending' in text and 'with $735.00 left for the 14 days' in text
          and "Groundwork expects Rob's pay and S195 Shop pay this week" in text and 'Due this week: s195 Card ($73.00)' in text)
    check('s195 S9 no verdict words in the facts', out is not None and not re.search(r'\b(great|good|bad|over your|should|must|need to|pace)\b', text, re.I))

    # S1/S2: the overnight rule
    with db_session() as s:
        s.query(AppSetting).filter_by(key='narration_last_at').delete(); s.commit()
        s.add(Transaction(date=date.today(), amount=1.0, type='debit', account_id=acct_id, description='s195 fresh', source='csv'))
        s.commit()
    due1 = c.get('/api/checkin/narration-due', headers=H).get_json()['data']
    c.post('/api/checkin/narration-done', headers=HJ, data='{}')
    due2 = c.get('/api/checkin/narration-due', headers=H).get_json()['data']
    import server
    now = datetime(2019, 6, 16, 2, 0)
    rule = [server._narration_rule(now - timedelta(hours=h), last, now) for h, last in
            ((10, None), (60, None), (10, now - timedelta(hours=1)), (10, now - timedelta(hours=20)))]
    check(f's195 S1 narration runs only when the newest import is under 48 hours old and nothing was written since it ({due1}, {due2}, {rule})',
          due1['run'] is True and due2['run'] is False and due2['unwritten'] is False
          and rule == [(True, True), (False, True), (True, False), (True, True)])
    night = app.split('async function _nightNarration() {')[1].split('\n}\n')[0]
    ci = app.split('async function confirmImport() {')[1].split('\nasync function ')[0]
    check('s195 S1/S2 the night run writes the check-in and the due monthly review, between 1 and 4 a.m.; an import no longer writes the review',
          'now.getHours() < 1 || now.getHours() > 4' in night and 'writeSundayCheckin(false)' in night
          and 'monthlyReviewAfterImport()' in night and 'monthlyReviewAfterImport()' not in ci)

    # the last download, and the 48-hour notice (Rob 2026-10-18: a week with no download read as current)
    li = [server._last_import_state(n, now) for n in (now - timedelta(hours=10), now - timedelta(hours=48), now - timedelta(days=4), None, now - timedelta(days=5))]
    route = c.get('/api/checkin', headers=H).get_json()['data']['last_import']
    check(f's195 the check-in carries the last download, stale at 48 hours or more and when there is none; past 4 days too old for a review ({li}, {route})',
          [x['stale'] for x in li] == [False, True, True, True, True] and [x['too_old'] for x in li] == [False, False, False, True, True]
          and li[3]['at'] is None and li[2]['hours'] == 96.0 and route['too_old'] is False
          and route['stale'] is False and route['at'])
    imp = None
    if node:
        js = ('function esc(s){return s}\n' + re.search(r'\nfunction _checkinImportLine\(.*?\n\}\n', app, re.S).group(0) +
              'console.log(JSON.stringify([' + ','.join('_checkinImportLine(' + json.dumps({'last_import': x}) + ')' for x in li) + ']));')
        fd, p = tempfile.mkstemp(suffix='.js')
        with os.fdopen(fd, 'w', encoding='utf-8') as fh:
            fh.write(js)
        try:
            imp = json.loads(subprocess.run([node, p], capture_output=True, text=True, encoding='utf-8', timeout=60).stdout or 'null')
        except Exception:                      # noqa: BLE001
            imp = None
        finally:
            os.remove(p)
    check(f's195 the card names the last download, and past 48 hours says the figures may be out of date, run in Node ({imp})',
          imp is not None and imp[0]['text'].startswith('Last download: ') and 'out of date' not in imp[0]['text']
          and '4 days ago' in imp[2]['text'] and 'past 48 hours, so these figures may be out of date' in imp[2]['text']
          and not imp[2]['too_old'] and imp[3]['too_old'] and 'No transactions have been downloaded yet' in imp[3]['text']
          and imp[4]['too_old'] and '5 days ago' in imp[4]['text'] and "can't process this week's review because there is too little recent data" in imp[4]['text']
          and 'if (imp.too_old) {' in app.split('async function renderSundayCard() {')[1].split('\n}\n')[0]
          and '_checkinImportLine(f)' in app.split('async function renderSundayCard() {')[1].split('\n}\n')[0]
          and '_checkinImportLine' not in app.split('async function writeSundayCheckin(show) {')[1].split('\n}\n')[0])

    # S7 whose pay; S12 done
    w = c.post('/api/checkin/whose', headers=HJ, data=json.dumps({'payer': 'S195 Shop', 'person': 'Sam'})).get_json()['data']
    k = date.today().isoformat()
    c.post('/api/checkin/close', headers=HJ, data=json.dumps({'date': k}))
    got = c.get('/api/checkin', headers=H).get_json()['data']
    check('s195 S7/S12 whose pay is kept; Done closes the check-in for the day',
          w['payer_people'].get('s195 shop') == 'Sam' and got['closed'] is True)
    top = html.index('id="dashSundayCard"')
    check('s195 S12 the check-in sits at the top of the dashboard, before everything but the greeting, with Done',
          top < html.index('id="dashRecordStatus"') and top < html.index('id="dashWhatChanged"')
          and 'onclick="closeSundayCard()"' in html)
    write = app.split('async function writeSundayCheckin(show) {')[1].split('\n}\n')[0]
    check('s195 S11 the written part is told to explain what the figures mean together, never to repeat them, and to add none',
          'without repeating them one by one' in write and 'Use only figures listed above' in write and "surface: 'sunday_checkin'" in write)

    # the "not needed" list on the dashboard
    with db_session() as s:
        s.add(Transaction(date=date(2019, 5, 2), amount=3.0, type='debit', account_id=acct_id, description='s195 old import', source='csv',
                          created_at=datetime(2019, 5, 2)))
        s.query(Transaction).filter(Transaction.account_id == acct_id).update({Transaction.created_at: datetime(2019, 5, 2)}, synchronize_session=False)
        s.commit()
    b1 = [x['account'] for x in c.get('/api/dashboard/attention/imports', headers=H).get_json()['data']['behind_this_month']]
    c.post('/api/reports/review/skip-account', headers=HJ, data=json.dumps({'account_id': acct_id}))
    att = c.get('/api/dashboard/attention/imports', headers=H).get_json()['data']
    check('s195 the dashboard honours "not needed for reviews": the account stops holding this month and stops being called stale',
          's195 Checking' in b1 and 's195 Checking' not in [x['account'] for x in att['behind_this_month']]
          and 's195 Checking' not in [x['account'] for x in att['stale']])

    with db_session() as s:
        s.query(Transaction).filter(Transaction.description.like('s195%')).delete(synchronize_session=False)
        s.query(DebtAccount).filter(DebtAccount.name.like('s195%')).delete(synchronize_session=False)
        s.query(Account).filter(Account.name.like('s195%')).delete(synchronize_session=False)
        s.query(Category).filter(Category.name.like('s195%')).delete(synchronize_session=False)
        for key in ('narration_last_at', 'payer_people', 'review_skip_accounts', f'checkin_closed_{k}'):
            s.query(AppSetting).filter_by(key=key).delete()
        s.commit()
