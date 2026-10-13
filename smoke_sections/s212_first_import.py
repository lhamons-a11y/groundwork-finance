"""Item 65 W1 (gw 2.0/AGENT_W_ITEMS.md; Rob 2026-10-12: "approve as recommended"): patterns a long history shows.

    W1-a  both rules null-modelled first (scripts/w1_null_model.py, run here)
    W1-b  asked, never assumed: each finding shown with its records and asked about; only a yes changes anything,
          and no / not sure are kept so it isn't asked again
    W1-c  under about a year of history it says so
"""
import json
import os
import subprocess
import sys
from datetime import date, timedelta


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    from core import first_import as fi
    from core.database import AppSetting, Category, Transaction, db_session

    check('s212 complete months: a partial first and last month are not small months (absence is not zero)',
          fi.complete_months([date(2025, 1, 15), date(2025, 4, 10)]) == ['2025-02', '2025-03']
          and fi.complete_months([date(2025, 1, 1), date(2025, 3, 31)]) == ['2025-01', '2025-02']
          and fi.complete_months([]) == [])

    d0 = date(2024, 3, 3)
    yearly = {'GEICO': [(d0, 612.0), (d0 + timedelta(days=366), 598.0)]}
    found = fi.renewals(yearly, {'GEICO': 'Auto Insurance'}, (date(2023, 1, 1), d0 + timedelta(days=380)))
    every = fi.renewals(yearly, {'GEICO': 'Restaurants'}, (date(2023, 1, 1), d0 + timedelta(days=380)))
    stopped = fi.renewals(yearly, {'GEICO': 'Auto Insurance'}, (date(2023, 1, 1), d0 + timedelta(days=366 + 420)))
    apart = fi.renewals({'X': [(d0, 100.0), (d0 + timedelta(days=366), 160.0)]}, {'X': 'Insurance'}, (d0, d0 + timedelta(days=380)))
    twice = fi.renewals({'Y': [(d0 + timedelta(days=k), 300.0) for k in (0, 183, 365)]}, {'Y': 'Insurance'}, (d0, d0 + timedelta(days=380)))
    check(f"s212 W1 a yearly bill is two charges a year apart at a similar amount; everyday spending, a stopped bill, and amounts that disagree are not ({found and found[0]['months']})",
          found and found[0]['rhythm'] == 'yearly' and found[0]['months'] == [3] and found[0]['amount'] == 605.0
          and not every and not stopped and not apart and twice and twice[0]['rhythm'] == 'twice a year'
          and twice[0]['months'] == [3, 9])
    s = fi.sentence(found[0])
    check(f's212 W1-b the finding says what the records say, and never why ({s})',
          s == 'GEICO: $612.00 on Mar 3, 2024 and $598.00 on Mar 4, 2025, about a year apart.')

    def yrs(n, dec):
        return {f'{2023 + i // 12}-{i % 12 + 1:02d}': 4000.0 * (1 + 0.03 * ((i * 7) % 5 - 2)) * (dec if i % 12 == 11 else 1)
                for i in range(12 * n)}
    check('s212 W1-a a heavy month needs two full years: one year is never judged; a December heavy in both is found; a flat record finds none',
          fi.heavy_months(yrs(1, 1.6)) == [] and [h['month'] for h in fi.heavy_months(yrs(2, 1.6))] == [12]
          and fi.heavy_months(yrs(2, 1.0)) == [])
    nm = subprocess.run([sys.executable, str(ctx.BASE / 'scripts' / 'w1_null_model.py')], capture_output=True, text=True,
                        timeout=900, env={**os.environ, 'W1_N': '4000'})
    last = (nm.stdout.strip().splitlines() or [''])[-1]
    check(f's212 W1-a the null model passes (4,000 runs a case here; 20,000 when run by hand): {last[:70]}',
          nm.returncode == 0 and last.startswith('PASS'))

    # the record: a long history, and a yearly bill in it
    today = date.today()
    with db_session() as s:
        cat = s.query(Category).filter_by(name='Auto Insurance').first()
        if not cat:
            cat = Category(name='Auto Insurance'); s.add(cat); s.flush()
        s.add(Transaction(date=today - timedelta(days=800), amount=5.0, type='debit', merchant='S212 OLD', description='S212 OLD'))
        for k, a in ((565, 612.0), (200, 598.0)):    # next due in about 165 days: inside the futures' twelve months
            s.add(Transaction(date=today - timedelta(days=k), amount=a, type='debit', merchant='S212 GEICO',
                              description='S212 GEICO', category_id=cat.id))
        for key in ('yearly_bills_json', 'heavy_months_json', 'first_import_offered'):
            s.query(AppSetting).filter_by(key=key).delete()
        s.commit()
    data = lambda r: (r.get_json() or {}).get('data') or {}
    f = data(c.get('/api/first-import', headers=H))
    mine = next((x for x in f.get('renewals', []) if x['payee'] == 'S212 GEICO'), None)
    check(f"s212 W1 a long history is looked through: the yearly bill is found with its records, not yet answered ({f.get('months')} months)",
          f.get('enough') and mine and mine['answer'] is None and len(mine['records']) == 2)
    off1 = data(c.get('/api/first-import/offer', headers=H))
    c.post('/api/first-import/offered', headers=HJ, data='{}')
    off2 = data(c.get('/api/first-import/offer', headers=H))
    check('s212 W1 an import offers the look-through once for this length of history, not on every import',
          off1.get('offer') is True and off2.get('offer') is False)

    no = c.post('/api/first-import/answer', headers=HJ, data=json.dumps({'kind': 'renewal', 'payee': 'S212 GEICO', 'answer': 'no'}))
    cal_no = [e for e in data(c.get('/api/calendar', headers=H)).get('entries', []) if e['title'] == 'S212 GEICO']
    again = next(x for x in data(c.get('/api/first-import', headers=H))['renewals'] if x['payee'] == 'S212 GEICO')
    fp0 = data(c.get('/api/futures/fingerprint', headers=H)).get('fingerprint')
    yes = c.post('/api/first-import/answer', headers=HJ, data=json.dumps({'kind': 'renewal', 'payee': 'S212 GEICO', 'answer': 'yes'}))
    cal = [e for e in data(c.get('/api/calendar', headers=H)).get('entries', []) if e['title'] == 'S212 GEICO']
    fp1 = data(c.get('/api/futures/fingerprint', headers=H)).get('fingerprint')
    import server
    with db_session() as s:
        said = json.loads(s.query(AppSetting).filter_by(key='yearly_bills_json').first().value)
        poss = server._first_import_possibilities(s)
    fut = [p for p in poss if p['label'] == 'S212 GEICO (a yearly bill you confirmed)']
    fake = c.post('/api/first-import/answer', headers=HJ, data=json.dumps({'kind': 'renewal', 'payee': 'NOT IN S212', 'answer': 'yes'}))
    check(f"s212 W1-b only a yes changes anything: No is kept (shown answered, not on the calendar); Yes puts it on the calendar as possible and in the futures as a known cost ({[e['date'] for e in cal]})",
          no.status_code == 200 and not cal_no and again['answer'] == 'no' and yes.status_code == 200
          and len(said) == 1 and said[0]['answer'] == 'yes'
          and cal and all(e['certainty'] == 'possible' for e in cal)
          and len(fut) == 1 and fut[0]['kind'] == 'cost' and fut[0]['month'] == cal[0]['date'][:7] and fp1 != fp0
          and fake.status_code == 404)

    app, html = ctx.app_src, ctx.html_src
    page = app.split('async function renderLookThrough() {')[1].split('\n}\n')[0]
    check('s212 W1 the Calendar page holds the look-through: on a tap, each finding with its records and Yes / No / Not sure; an import offers it',
          'id="calendarLookThrough"' in html and "Look through it" in page and "'Is this a regular bill?'" in page
          and "'Does this happen every year?'" in page and "btn('not_sure', 'Not sure')" in page
          and '_offerLookThrough();' in app.split('async function confirmImport() {')[1].split('\nasync function ')[0])

    with db_session() as s:
        s.query(Transaction).filter(Transaction.merchant.in_(['S212 GEICO', 'S212 OLD'])).delete(synchronize_session=False)
        for key in ('yearly_bills_json', 'heavy_months_json', 'first_import_offered'):
            s.query(AppSetting).filter_by(key=key).delete()
        s.commit()
