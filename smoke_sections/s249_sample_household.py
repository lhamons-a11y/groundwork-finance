"""Item 105 (gw 2.0/SAMPLE_HOUSEHOLD.md; Rob 2026-10-20: "we need test data can you add that please. Also that way if I
want to send this for people to review I think sending them test data would assist them to get an understanding of the
software" - "remember they will get the welcome screen on first launch").

    S1 the welcome screen offers "Look around with a sample household first"; it goes only into an empty Groundwork
    S2 the Morgans arrive whole: budget lines, three debts with their balance history, six months of transactions up to
       today, investments priced by hand, savings goals, gifts, a medical bill they said is theirs, net worth history
    S3 this month's Restaurants is the five visits that make $500.00 (by today's date)
    S4 only the sample's own load marks it as the sample: the settings route can't, so real records can never be
       cleared this way; "Start with my own" clears the sample, keeps the terms and the AI and backup choices, and the
       welcome screen comes back
    S5 while it is here, every page says so, with "Start with my own"
Run in its own process and folder, so the sample never touches the other sections' database.
"""
import json
import os
import subprocess
import sys
import tempfile

_SCRIPT = r'''
import json, os, sys
sys.path.insert(0, os.getcwd()); sys.path.insert(0, os.path.join(os.getcwd(), 'core'))
from datetime import date
from server import create_app, _GW_TOKEN
app = create_app(); c = app.test_client(); H = {'X-GW-Token': _GW_TOKEN, 'Content-Type': 'application/json'}
out = {}
c.patch('/api/settings', headers=H, data=json.dumps({'terms_accepted': 'v-test', 'ai_enabled': 'false', 'sample_household': 'true'}))
out['planted'] = c.get('/api/sample', headers=H).get_json()['data']
c.post('/api/accounts', headers=H, data=json.dumps({'name': 'Mine', 'type': 'checking'}))
out['busy'] = c.post('/api/sample/load', headers=H).get_json()
out['busy_clear'] = c.post('/api/sample/clear', headers=H).get_json()
from core.database import Account, db_session
with db_session() as s:
    s.query(Account).delete(); s.commit()
out['load'] = c.post('/api/sample/load', headers=H).get_json()
out['status'] = c.get('/api/sample', headers=H).get_json()['data']
boot = c.get('/api/settings/bootstrap', headers=H).get_json()['data']
out['incomes'] = len(boot['incomes']); out['expenses'] = len(boot['expenses']); out['debts'] = len(boot['debts'])
tx = c.get('/api/transactions?per_page=5000', headers=H).get_json()['data']
out['txns'] = len(tx); out['last'] = max(t['date'] for t in tx); out['first'] = min(t['date'] for t in tx)
m = date.today().strftime('%Y-%m')
r = [t['amount'] for t in tx if t['category'] == 'Restaurants' and t['date'].startswith(m)]
out['restaurants_now'] = [len(r), round(sum(r), 2)]
out['history'] = {k: len(v) for k, v in (c.get('/api/debt/history/all', headers=H).get_json().get('data') or {}).items()}
out['positions'] = len(c.get('/api/investments/positions?skip_refresh=true', headers=H).get_json().get('data', {}).get('positions', []) or [])
out['funds'] = len(c.get('/api/sinking-funds', headers=H).get_json().get('data') or [])
mb = c.get('/api/medical-bills', headers=H).get_json().get('data') or {}
out['medical'] = json.dumps(mb)[:4000]
out['snapshots'] = len(c.get('/api/net-worth/snapshots?months=24', headers=H).get_json().get('data') or [])
w = c.get('/api/willingness', headers=H).get_json()['data']
out['picture'] = {'record': sorted(r['category'] for r in w['readings'] if r['stance'] in ('flexible', 'sacred') or r['reason'] == 'probation'),
                  'said': sorted(d['category'] for d in w['current']), 'asks': [x['category'] for x in w['contradictions']]}
out['again'] = c.post('/api/sample/load', headers=H).get_json()
out['clear'] = c.post('/api/sample/clear', headers=H).get_json()
st = c.get('/api/settings', headers=H).get_json(); st = st.get('data', st)
out['after'] = c.get('/api/sample', headers=H).get_json()['data']
out['kept'] = [st.get('terms_accepted'), st.get('ai_enabled'), st.get('onboarding_complete')]
out['after_txns'] = c.get('/api/transactions?per_page=5', headers=H).get_json().get('total')
out['clear_again'] = c.post('/api/sample/clear', headers=H).get_json()
print('@@' + json.dumps(out))
'''


def run(ctx):
    check, app, html = ctx.check, ctx.app_src, ctx.html_src
    check('s249 S1 the welcome screen offers the sample household first, beside importing, setting up by hand and restoring',
          'id="obSampleOption" onclick="sampleLoad()"' in html and 'Look around with a sample household first' in html
          and html.index('obSampleOption') < html.index('onclick="obChooseMigrate()"'))
    env = {**os.environ, 'GROUNDWORK_DATA_DIR': tempfile.mkdtemp(prefix='s249_')}
    p = subprocess.run([sys.executable, '-c', _SCRIPT], cwd=str(ctx.BASE), env=env, capture_output=True, text=True, timeout=300)
    line = next((l for l in p.stdout.splitlines() if l.startswith('@@')), None)
    if not line:
        check(f's249 the sample household ran ({(p.stderr or "")[-600:]})', False)
        return
    o = json.loads(line[2:])
    check('s249 S1 it goes only into an empty Groundwork', o['busy'].get('ok') is False and 'only into an empty' in o['busy']['error']
          and o['again'].get('ok') is False)
    check(f's249 S2 the Morgans arrive whole: 2 incomes, 14 budget lines, 3 debts with history, ~6 months of transactions, '
          f'3 holdings, 2 savings goals, net worth history ({o["incomes"]}, {o["expenses"]}, {o["debts"]}, {o["history"]}, '
          f'{o["txns"]}, {o["positions"]}, {o["funds"]}, {o["snapshots"]})',
          o['load'].get('ok') and o['incomes'] == 2 and o['expenses'] == 14 and o['debts'] == 3
          and len(o['history']) == 3 and all(v == 6 for v in o['history'].values()) and o['txns'] > 150
          and o['last'] <= __import__('datetime').date.today().isoformat() and o['positions'] == 3 and o['funds'] == 2
          and o['snapshots'] >= 6)
    check('s249 S2 the medical bill is one they said is theirs (it shows as owed on the Health page)',
          'Northside Urgent Care' in o['medical'] and '285.4' in o['medical'])
    from datetime import date
    from core.sample_household import RESTAURANT_MONTH_NOW
    want = [amt for day, _desc, _merchant, amt in RESTAURANT_MONTH_NOW if day <= date.today().day]
    check(f's249 S3 this month\'s Restaurants is the five visits that make $500.00, as far as today ({o["restaurants_now"]})',
          o['restaurants_now'] == [len(want), round(sum(want), 2)])
    check('s249 S4 the settings route cannot mark records as the sample, so it cannot make them clearable',
          o['planted']['sample'] is False and o['busy_clear'].get('ok') is False
          and "body.pop('sample_household', None)" in ctx.server_src)
    check(f's249 S4 "Start with my own" clears the sample and keeps the terms and the AI choice; the welcome screen comes back '
          f'({o["kept"]}, {o["after"]})',
          o['clear'].get('ok') and o['after'] == {'can_load': True, 'sample': False, 'why_not': None} and o['after_txns'] == 0
          and o['kept'][0] == 'v-test' and o['kept'][1] == 'false' and o['kept'][2] in (None, '', 'false')
          and o['clear_again'].get('ok') is False)
    check(f's249 (Rob 2026-10-21) the Working picture has something in each tab: conclusions from their budget edits, what Sam '
          f'said, and a question about it ({o.get("picture")})',
          o.get('picture') == {'record': ['Coffee Shops', 'Gym / Fitness', 'Streaming Video'],
                               'said': ['Groceries', 'Restaurants', 'Streaming Video'], 'asks': ['Streaming Video']})
    check('s249 S5 while the sample is here every page says so, with "Start with my own"',
          'async function sampleNotice()' in app and 'Sample household (made up)' in app and 'onclick="sampleClear()">Start with my own' in app
          and "sampleNotice().catch(_gwErr('sampleNotice'))" in app and "location.reload();" in app[app.index('function sampleClear()'):])
    check('s249 the Dashboard reads the debts\' balance history at boot, not only once the Budget page has opened',
          'await _budgetLoadDebtHistory();' in app[app.index('async function bootFromDB()'):app.index('async function bootFromDB()') + 1500])
