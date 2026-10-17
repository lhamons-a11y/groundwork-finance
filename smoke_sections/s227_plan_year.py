"""Item 87 (gw 2.0/PLAN_YEAR_TRACKING.md = item 45 H7 stage 2; Rob 2026-10-15: "I approve P1-P9 as recommended.
Build item 87.").

    P1  progress is what the insurer reports, typed with its date - never summed from health spending
    P2  plan_year.py's rules over the tables: a correction keeps and names the old figure; a change closes the plan
        the day before and starts a new one (the earlier months untouched); two plans on one date are refused
    P3  readings kept with their dates, the newest current; a reading older than the last health payment is said to be
    P4  unknown stays unknown: no plan, no deductible, no reading - never $0, never "met"
    P5  per-person amounts in a family plan are named as not tracked
    P7  the terms taught; the reset stated as a fact; no advice about care or timing
    P8  the plan's name is scrubbed from the moment it is saved; plans leave an export only on the health tick
    P9  no Needs attention kind for the reset
"""
import json
import subprocess
import tempfile
from datetime import date, timedelta
from pathlib import Path


def run(ctx):
    check, c, H, HJ, BASE = ctx.check, ctx.c, ctx.H, ctx.HJ, ctx.BASE
    app = ctx.app_src
    from core import health_boundary as hb
    from core import health_plan as hp
    from core.database import (Account, AppSetting, HealthPlan, HealthPlanOperation, HealthPlanReading,
                               HealthPlanTermVersion, Transaction, db_session)

    post = lambda path, body: c.post(path, headers=HJ, data=json.dumps(body))
    data = lambda r: (r.get_json() or {}).get('data')
    today = date.today()
    y = today.year

    def clear():
        with db_session() as s:
            for m in (HealthPlanReading, HealthPlanOperation, HealthPlanTermVersion, HealthPlan):
                s.query(m).delete()
            s.commit()
    clear()

    # ── P4: nothing entered ───────────────────────────────────────────────────
    st0 = data(c.get('/api/accounts/health-plans', headers=H))
    check('s227 P4 with no plan there is no current plan and nothing invented', st0['current'] is None and st0['plans'] == [])

    # ── P2: a plan, and the overlap refused ───────────────────────────────────
    r1 = post('/api/accounts/health-plans', {'name': 'S227 Maple Gold PPO', 'effective_from': f'{y}-01-01',
                                             'effective_to': f'{y}-12-31', 'tier': 'family'})
    cur = data(r1)['current']
    check('s227 P4 a plan without a deductible says "not entered", never $0 or met',
          r1.status_code == 200 and cur['lines'][0] == 'Deductible: not entered.'
          and cur['lines'][1] == 'Out-of-pocket maximum: not entered.')
    pid = cur['id']
    r2 = post('/api/accounts/health-plans', {'name': 'S227 Other', 'effective_from': f'{y}-06-01'})
    check('s227 P2 two plans covering one date are refused', r2.status_code == 400 and 'already covers' in (r2.get_json() or {}).get('error', ''))
    r3 = post(f'/api/accounts/health-plans/{pid}/terms', {'deductible': 3000, 'oop_max': 8000})
    check('s227 P2 a term edit must say whether it changed or was always so', r3.status_code == 400)
    post(f'/api/accounts/health-plans/{pid}/terms', {'mode': 'correction', 'deductible': 3000, 'oop_max': 8000, 'tier': 'family'})
    cur = data(post(f'/api/accounts/health-plans/{pid}/terms', {'mode': 'correction', 'deductible': 2000, 'oop_max': 8000,
                                                                 'tier': 'family'}))['current']
    check('s227 P4 terms but no reading: "Met so far: not entered yet", and no amount left',
          cur['lines'][0] == 'Deductible: $2,000.00. Met so far: not entered yet.' and 'left' not in cur['lines'][0])
    check('s227 P2 a correction keeps the old figure and names it',
          any('it was deductible $3,000.00 before' in n for n in cur['notes']))
    check('s227 P5 per-person amounts in a family plan are named as not tracked',
          'Per-person amounts: none entered yet. Your insurer shows them member by member.' in cur['notes'])   # item 92 N5b

    # ── P1 / P3: readings ─────────────────────────────────────────────────────
    with db_session() as s:
        hsa = Account(name='S227 HSA', type='hsa', is_active=True)
        s.add(hsa); s.commit()
        hsa_id = hsa.id
        s.add(Transaction(date=today - timedelta(days=3), description='S227 BIRCH CLINIC', amount=900, type='debit',
                          account_id=hsa_id, source='csv'))
        s.commit()
    cur = data(c.get('/api/accounts/health-plans', headers=H))['current']
    check('s227 P1 health spending on record is never summed into the deductible', cur['deductible_met'] is None
          and cur['lines'][0] == 'Deductible: $2,000.00. Met so far: not entered yet.')
    early = (today - timedelta(days=20)).isoformat()
    bad = post(f'/api/accounts/health-plans/{pid}/readings', {'deductible_met': 100, 'as_of': (today + timedelta(days=2)).isoformat()})
    post(f'/api/accounts/health-plans/{pid}/readings', {'deductible_met': 1450, 'oop_met': 1900, 'as_of': early})
    cur = data(c.get('/api/accounts/health-plans', headers=H))['current']
    check('s227 P3 a reading dated in the future is refused', bad.status_code == 400)
    check('s227 P1 the reading is shown as the insurer\'s figure, with its date and what is left',
          cur['lines'][0] == f'Deductible: $1,450.00 of $2,000.00 met, $550.00 left, as of {hp.day(early)}.'
          and cur['lines'][1] == f'Out-of-pocket maximum: $1,900.00 of $8,000.00 met, $6,100.00 left, as of {hp.day(early)}.'
          and 'From your insurer, as you entered it.' in cur['lines'][2])
    check('s227 P3 a reading older than the last health payment is said to be, with no guess',
          any(n.startswith(f'Your last reading is from {hp.day(early)}; you\'ve paid health bills since then')
              and 'doesn\'t guess' in n for n in cur['notes']))
    post(f'/api/accounts/health-plans/{pid}/readings', {'deductible_met': 2000, 'as_of': today.isoformat()})
    cur = data(c.get('/api/accounts/health-plans', headers=H))['current']
    check('s227 P3 the newest reading of each figure is current; the earlier one kept',
          cur['lines'][0] == f'Deductible: met - $2,000.00 of $2,000.00, as of {hp.day(today.isoformat())}.'
          and cur['oop_met'] == 1900 and len(cur['readings']) == 2
          and not any(n.startswith('Your last reading') for n in cur['notes']))

    # ── P7: the reset as a fact ───────────────────────────────────────────────
    reset = date(y + 1, 1, 1)
    days = (reset - today).days
    check('s227 P7 the reset is stated as a fact, with the days to it',
          f'These figures start over on {hp.day(reset.isoformat())} ({days} day{"s" if days != 1 else ""}).' in cur['notes'])

    # ── P2: a change from a date - the earlier months untouched ──────────────
    switch_on = f'{y}-07-01'
    if today.isoformat() > switch_on:
        rc = post(f'/api/accounts/health-plans/{pid}/terms', {'mode': 'change', 'from': switch_on, 'deductible': 2500,
                                                               'oop_max': 9000, 'tier': 'family'})
        st = data(rc)
        first = next(p for p in st['plans'] if p['id'] == pid)
        second = next(p for p in st['plans'] if p['id'] != pid)
        check('s227 P2 a change closes the plan the day before and starts the rest of the year with the new terms',
              first['to'] == f'{y}-06-30' and first['deductible'] == 2000 and second['from'] == switch_on
              and second['to'] == f'{y}-12-31' and second['deductible'] == 2500 and st['current']['id'] == second['id'])
        check('s227 P2 the readings stay with the plan they were taken under', len(first['readings']) == 2
              and second['readings'] == [] and second['lines'][0] == 'Deductible: $2,500.00. Met so far: not entered yet.')
    rbad = post(f'/api/accounts/health-plans/{pid}/terms', {'mode': 'change', 'from': f'{y}-01-01', 'deductible': 1})
    check('s227 P2 a "change" on the plan\'s first day is refused - that is a correction', rbad.status_code == 400)

    # ── P8: privacy ───────────────────────────────────────────────────────────
    check('s227 P8 the plan\'s name is scrubbed from the moment it is saved',
          'Maple Gold' not in hb.scrub('opened S227 Maple Gold PPO card'))
    out_dir = Path(tempfile.mkdtemp(prefix='gw_s227_'))
    with db_session() as s:
        s.query(AppSetting).filter_by(key='export_dir').delete()
        s.add(AppSetting(key='export_dir', value=str(out_dir))); s.commit()
    ex = lambda body: Path(c.post('/api/settings/export-to-file', headers=HJ, data=json.dumps(body)).get_json()['data']['path']).read_text(encoding='utf-8')
    j1, c1 = ex({'format': 'json'}), ex({'format': 'csv'})
    j2, c2 = ex({'format': 'json', 'include_health': True}), ex({'format': 'csv', 'include_health': True})
    check('s227 P8 plans leave an export only on the health tick (JSON and CSV)',
          'Maple Gold' not in j1 and 'Maple Gold' not in c1 and '"health_plans"' in j2 and 'Maple Gold' in j2
          and '--- HEALTH PLANS ---' in c2 and 'Maple Gold' in c2)

    # ── P7 / P9: no advice; no attention kind ────────────────────────────────
    block = app.split('// ── Item 87: the health plan')[1].split('async function saveHealthPlanForm')[0]
    said = ' '.join(hp.HELP.split()) + ' ' + ' '.join(cur['lines'] + cur['notes']) + ' ' + block
    banned = ('should', 'before it resets', 'schedule', 'book ', 'get care', 'good plan', 'bad plan', 'recommend',
              'consider ', 'max out', 'wise', 'smart', 'bigger shovel', 'baby step')
    hits = [w for w in banned if w in said.lower()]
    check(f's227 P7 no advice about care or timing, in the sentences, the help or the card ({hits})', not hits)
    check('s227 P7 the help teaches deductible, coinsurance and the out-of-pocket maximum, and that the insurer decides',
          all(w in hp.HELP for w in ('A deductible is', 'coinsurance', 'out-of-pocket maximum is', 'decided by your insurer')))
    att = (BASE / 'static' / 'js' / 'teaching' / 'attention.js').read_text(encoding='utf-8')
    check('s227 P9 no Needs attention kind for the reset', 'plan_reset' not in att and 'health_plan' not in att)
    src = (BASE / 'core' / 'health_plan.py').read_text(encoding='utf-8')
    check('s227 AI-off: nothing here calls the model', '_ai_' not in src and 'ai_chat' not in src)
    try:
        ok = subprocess.run(['node', '--check', str(BASE / 'static' / 'js' / 'app.js')], capture_output=True, timeout=120).returncode == 0
    except Exception:
        ok = False
    check('s227 app.js parses (a broken script drops the whole page)', ok)

    with db_session() as s:
        s.query(AppSetting).filter_by(key='export_dir').delete()
        s.query(Transaction).filter_by(account_id=hsa_id).delete()
        s.query(Account).filter_by(id=hsa_id).delete()
        s.commit()
    clear()
    with db_session() as s:
        hb.refresh(s)
