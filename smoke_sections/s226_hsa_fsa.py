"""Item 86 (gw 2.0/HSA_FSA.md = item 45 H5; Rob 2026-10-14: "I approve F1-F7 as recommended (60 days for the
attention item). Build item 86.").

    F1  HSA and FSA are account types; the balance is the statement's or the typed one, the newer - never activity
    F2  the terms are the person's own, one row per change (history kept), every one may stay unknown, bad values refused
    F3  the IRS limit from a dated table with its source; a year not in it is said to be missing; catch-up only on a yes
    F4  contributions only from the account's own rows, earnings left out, months with nothing imported named; typed wins
    F5  the two warnings as sentences of fact; an FSA with no terms "can't tell"; Needs attention from 60 days
    F6  every HSA / FSA row is health: scrubbed (its spending, not its money words) and left out of exports unless ticked
    F7  no advice, no judgement, in the sentences and on the page
"""
import json
import subprocess
import tempfile
from datetime import date, datetime
from pathlib import Path


def run(ctx):
    check, c, H, HJ, BASE = ctx.check, ctx.c, ctx.H, ctx.HJ, ctx.BASE
    app = ctx.app_src
    from core import health_boundary as hb
    from core import hsa_fsa as hf
    from core.database import Account, AppSetting, HealthAccountTerms, Transaction, db_session
    import server

    post = lambda path, body: c.post(path, headers=HJ, data=json.dumps(body))
    data = lambda r: (r.get_json() or {}).get('data')
    anchor = server._resolve_bank_anchor

    def mk(name, kind):
        r = data(post('/api/accounts', {'name': name, 'type': kind}))
        return r['id']

    hsa_id, fsa_id = mk('S226 Health Savings', 'hsa'), mk('S226 Flex Spending', 'fsa')
    # ── F1 ────────────────────────────────────────────────────────────────────
    check('s226 F1 HSA and FSA are account types on the page', "hsa:         'HSA'" in app and "fsa:         'FSA'" in app)
    lst = data(c.get('/api/accounts/hsa-fsa', headers=H))
    h0 = next(a for a in lst['accounts'] if a['account_id'] == hsa_id)
    check('s226 F1 no balance yet is unknown, never $0 or the activity sum',
          h0['balance']['amount'] is None and h0['balance']['basis'] == 'unknown' and 'No balance yet' in h0['balance']['working'])
    r = data(post(f'/api/accounts/{hsa_id}/terms', {'plan_year': date.today().year, 'typed_balance': 1240,
                                                     'typed_balance_on': '2026-01-15'}))
    check('s226 F1 a typed balance is used and labelled typed, with its date',
          r['state']['balance']['amount'] == 1240 and r['state']['balance']['basis'] == 'typed'
          and 'you typed on Jan 15, 2026' in r['state']['balance']['working'])
    with db_session() as s:
        s.add(Transaction(date=date(2026, 2, 3), description='Payroll contribution', amount=200, type='credit',
                          account_id=hsa_id, running_balance=1440, source='csv'))
        s.add(Transaction(date=date(2026, 2, 28), description='Interest', amount=1.25, type='credit',
                          account_id=hsa_id, running_balance=1441.25, source='csv'))
        s.add(Transaction(date=date(2026, 3, 9), description='S226 SUNRISE PHARMACY 4471', amount=30, type='debit',
                          account_id=hsa_id, running_balance=1411.25, source='csv'))
        s.commit()
        acct = s.get(Account, hsa_id)
        txns = s.query(Transaction).filter_by(account_id=hsa_id).all()
        bal = hf.balance(s, acct, txns, anchor)
    check('s226 F1 a newer statement balance wins over an older typed one',
          bal['amount'] == 1411.25 and bal['basis'] == 'bank' and 'statement you imported' in bal['working'])

    # ── F2 ────────────────────────────────────────────────────────────────────
    bad = post(f'/api/accounts/{hsa_id}/terms', {'coverage': 'couple'})
    post(f'/api/accounts/{hsa_id}/terms', {'plan_year': 2026, 'coverage': 'self'})
    post(f'/api/accounts/{hsa_id}/terms', {'plan_year': 2026, 'coverage': 'family', 'catch_up': 'yes'})
    hist = data(c.get(f'/api/accounts/{hsa_id}/terms', headers=H))['history']
    with db_session() as s:
        cur = hf.current_by_year(s, hsa_id)[2026]
    check('s226 F2 a wrong value is refused, never guessed', bad.status_code == 400)
    check('s226 F2 every change is a row; the newest is current; earlier terms kept as history',
          len(hist) == 3 and hist[0]['coverage'] == 'family' and hist[1]['coverage'] == 'self' and cur.coverage == 'family')
    check('s226 F2 an unanswered term stays unknown', hist[1]['catch_up'] == '' and hist[1]['year_end'] is None)
    check('s226 F2 the terms table is not the insurance plan year (plan_year.py stays unwired)',
          'plan_year' not in Path(BASE / 'core' / 'hsa_fsa.py').read_text(encoding='utf-8').split('import')[0]
          and 'from core import plan_year' not in Path(BASE / 'core' / 'hsa_fsa.py').read_text(encoding='utf-8'))

    # ── F3 ────────────────────────────────────────────────────────────────────
    l1 = hf.hsa_limit(2026, {'coverage': 'self', 'catch_up': ''})
    l2 = hf.hsa_limit(2026, {'coverage': 'family', 'catch_up': 'yes'})
    l3 = hf.hsa_limit(2026, {'coverage': '', 'catch_up': ''})
    l4 = hf.hsa_limit(2031, {'coverage': 'self'})
    check('s226 F3 the 2026 limit with its IRS source, and a full year named as the assumption',
          l1['amount'] == 4400 and 'Rev. Proc. 2025-19' in l1['working'] and 'full year' in l1['working']
          and 'catch-up isn\'t counted because it hasn\'t been answered' in l1['working'])
    check('s226 F3 family plus the catch-up only on a yes', l2['amount'] == 9750)
    check('s226 F3 coverage unknown: the limit can\'t be checked', l3['amount'] is None and 'can\'t be checked' in l3['working'])
    check('s226 F3 a year not in the table is said to be missing, never borrowed',
          l4['amount'] is None and 'isn\'t in Groundwork\'s table yet' in l4['working'])
    check('s226 F3 the 2026 health FSA figures with their source', hf.LIMITS[2026]['fsa'] == {
        'limit': 3400.0, 'carryover_max': 680.0, 'source': 'IRS Rev. Proc. 2025-32'})

    # ── F4 ────────────────────────────────────────────────────────────────────
    with db_session() as s:
        txns = s.query(Transaction).filter_by(account_id=hsa_id).all()
    k1 = hf.contributions(txns, 2026, date(2026, 3, 20))
    k2 = hf.contributions([], 2026, date(2026, 3, 20))
    k3 = hf.contributions(txns, 2026, date(2026, 3, 20), typed=3000)
    check('s226 F4 deposits counted, the interest row left out and said so',
          k1['total'] == 200 and 'interest or earnings row left out' in k1['working'])
    check('s226 F4 a month with nothing imported is named and the total called incomplete',
          k1['missing_months'] == ['January'] and 'Nothing imported for January' in k1['working'] and not k1['complete'])
    check('s226 F4 no rows: contributions unknown, never $0',
          k2['total'] is None and 'aren\'t known' in k2['working'])
    check('s226 F4 a typed total wins, labelled typed', k3['total'] == 3000 and 'you typed' in k3['working'])

    # ── F5: HSA over the limit ────────────────────────────────────────────────
    with db_session() as s:
        acct = s.get(Account, hsa_id)
        post(f'/api/accounts/{hsa_id}/terms', {'plan_year': 2026, 'coverage': 'self', 'catch_up': 'no',
                                               'typed_contributions': 4500})
        st = hf.hsa_state(s, acct, s.query(Transaction).filter_by(account_id=hsa_id).all(), anchor, date(2026, 6, 1))
    check('s226 F5 contributions over the limit: a sentence of fact, with the amount over',
          st['warning'] == 'over_limit' and st['sentence'] ==
          'Contributions on record for 2026 are $4,500.00, $100.00 more than the $4,400.00 limit for the coverage you entered.')

    # ── F5: the FSA ───────────────────────────────────────────────────────────
    post(f'/api/accounts/{fsa_id}/terms', {'plan_year': 2026, 'typed_balance': 340, 'typed_balance_on': '2026-11-01'})
    with db_session() as s:
        f_acct = s.get(Account, fsa_id)
        f0 = hf.fsa_state(s, f_acct, [], anchor, date(2026, 11, 2))
    check('s226 F5 an FSA without its terms: "can\'t tell", no warning, nothing on the dashboard',
          'Groundwork can\'t tell whether any of this is at risk: the plan\'s deadline and carryover rule haven\'t been entered.'
          in f0['sentence'] and f0['warning'] is None and not f0['attention'])
    post(f'/api/accounts/{fsa_id}/terms', {'plan_year': 2026, 'year_end': '2026-12-31', 'rule': 'carryover',
                                           'typed_balance': 340, 'typed_balance_on': '2026-11-01'})
    with db_session() as s:
        f1 = hf.fsa_state(s, s.get(Account, fsa_id), [], anchor, date(2026, 11, 2))
    check('s226 F5 carryover with no amount entered is still "can\'t tell"', 'can\'t tell' in f1['sentence'] and not f1['attention'])
    post(f'/api/accounts/{fsa_id}/terms', {'plan_year': 2026, 'year_end': '2026-12-31', 'rule': 'carryover',
                                           'carryover_max': 0, 'claims_by': '2027-03-31',
                                           'typed_balance': 340, 'typed_balance_on': '2026-11-01'})
    with db_session() as s:
        fa = s.get(Account, fsa_id)
        f2 = hf.fsa_state(s, fa, [], anchor, date(2026, 11, 2))
        f3 = hf.fsa_state(s, fa, [], anchor, date(2026, 10, 31))
        f4 = hf.fsa_state(s, fa, [], anchor, date(2026, 11, 1))
    check('s226 F5 the FSA sentence states the entered terms and the amount at risk',
          f2['sentence'] == '$340.00 is in your FSA. Under the terms you entered, up to $0.00 carries over and the rest, '
                            '$340.00, is lost after Dec 31, 2026. Claims must be submitted by Mar 31, 2027.'
          and f2['at_risk'] == 340 and f2['days'] == 59)
    check('s226 F5 Needs attention from 60 days before the deadline, not 61',
          f2['attention'] and f4['attention'] and f4['days'] == 60 and not f3['attention'] and f3['days'] == 61
          and hf.FSA_WARN_DAYS == 60)
    with db_session() as s:
        g1 = hf.fsa_state(s, s.get(Account, fsa_id), [], anchor, date(2026, 11, 2))
    post(f'/api/accounts/{fsa_id}/terms', {'plan_year': 2026, 'year_end': '2026-12-31', 'rule': 'carryover',
                                           'carryover_max': 680, 'typed_balance': 340, 'typed_balance_on': '2026-11-01'})
    with db_session() as s:
        f5 = hf.fsa_state(s, s.get(Account, fsa_id), [], anchor, date(2026, 11, 2))
    check('s226 F5 when all of it carries over, nothing is at risk and nothing is raised',
          f5['at_risk'] == 0 and not f5['attention'] and 'so all of it ($340.00) carries past Dec 31, 2026' in f5['sentence'])
    post(f'/api/accounts/{fsa_id}/terms', {'plan_year': 2026, 'year_end': '2026-12-31', 'rule': 'grace',
                                           'grace_until': '2027-03-15', 'typed_balance': 340, 'typed_balance_on': '2026-11-01'})
    with db_session() as s:
        f6 = hf.fsa_state(s, s.get(Account, fsa_id), [], anchor, date(2027, 1, 20))
    check('s226 F5 a grace period: its own last day, still the 2026 plan',
          f6['deadline'] == '2027-03-15' and 'grace period runs to Mar 15, 2027' in f6['sentence'] and f6['attention'])
    dis = c.post('/api/dashboard/dismiss', headers=HJ, data=json.dumps({'fingerprint': f'fsa_deadline|{fsa_id}|x'}))
    check('s226 F5 the attention item can be dismissed (and date_ends now too)', dis.status_code == 200
          and c.post('/api/dashboard/dismiss', headers=HJ, data=json.dumps({'fingerprint': 'date_ends|1|x'})).status_code == 200)
    node = None
    try:
        js = ("const A=require(%s);const it=A.build({fsa:A.fsaDeadlines([{account_id:7,account:'F',deadline:'2026-12-31',"
              "days:12,at_risk:340,sentence:'s'}])},[]);console.log(JSON.stringify([A.KINDS,it.map(i=>[i.kind,i.days,i.fact])]))"
              % json.dumps(str(BASE / 'static' / 'js' / 'teaching' / 'attention.js')))
        node = json.loads(subprocess.run(['node', '-e', js], capture_output=True, text=True, timeout=60).stdout)
    except Exception:
        node = None
    check('s226 F5 the dashboard rule builds the FSA item from the server\'s facts',
          node is not None and 'fsa_deadline' in node[0] and node[1] == [['fsa_deadline', 12, '2026-12-31|340.00']])
    syntax = []
    for f in ('static/js/teaching/dashboard.js', 'static/js/teaching/attention.js', 'static/js/app.js'):
        try:
            if subprocess.run(['node', '--check', str(BASE / f)], capture_output=True, timeout=120).returncode != 0:
                syntax.append(f)
        except Exception:
            syntax.append(f + ' (node not run)')
    check(f's226 the edited scripts parse (a broken file silently drops the whole dashboard) ({syntax})', not syntax)
    dash = (BASE / 'static' / 'js' / 'teaching' / 'dashboard.js').read_text(encoding='utf-8')
    check('s226 F5 the dashboard shows the sentence and its source, and spends or claims nothing',
          "i.kind === 'fsa_deadline'" in dash and 'the plan terms you entered' in dash and "spend or claim anything" in dash)

    # ── F6 ────────────────────────────────────────────────────────────────────
    with db_session() as s:
        is_health = hb.health_rows(s)
        rows = s.query(Transaction).filter_by(account_id=hsa_id).all()
        hb.refresh(s)
    check('s226 F6 every HSA row is health, whatever its category', rows and all(is_health(t) for t in rows))
    check('s226 F6 its spending is scrubbed; its money words are not',
          'SUNRISE PHARMACY' not in hb.scrub('paid S226 SUNRISE PHARMACY 4471 from the HSA')
          and hb.scrub('Interest on the card') == 'Interest on the card'
          and hb.scrub('Payroll contribution') == 'Payroll contribution')
    out_dir = Path(tempfile.mkdtemp(prefix='gw_s226_'))
    with db_session() as s:
        s.query(AppSetting).filter_by(key='export_dir').delete()
        s.add(AppSetting(key='export_dir', value=str(out_dir))); s.commit()
    e1 = c.post('/api/settings/export-to-file', headers=HJ, data=json.dumps({'format': 'json'})).get_json()['data']
    j1 = Path(e1['path']).read_text(encoding='utf-8')
    e2 = c.post('/api/settings/export-to-file', headers=HJ, data=json.dumps({'format': 'csv', 'include_health': True})).get_json()['data']
    j2 = Path(e2['path']).read_text(encoding='utf-8')
    check('s226 F6 an export leaves HSA rows out unless health is ticked',
          'SUNRISE PHARMACY' not in j1 and 'Payroll contribution' not in j1 and e1['health_left_out'] >= 3
          and 'SUNRISE PHARMACY' in j2)
    srv = ctx.server_src
    check('s226 F6 both exports and the year-end packet use the one test (category or HSA / FSA account)',
          srv.count('health_boundary.health_rows(session)') == 2 and 'health_category_ids(session)' not in srv)

    # ── F7 ────────────────────────────────────────────────────────────────────
    said = ' '.join(str(x) for x in (st['sentence'], f0['sentence'], f2['sentence'], f5['sentence'], f6['sentence'],
                                     l1['working'], k1['working'], k2['working']))
    block = app.split('// ── Item 86: HSA and FSA')[1].split('async function saveHsaFsaTerms')[0]
    src = (BASE / 'core' / 'hsa_fsa.py').read_text(encoding='utf-8')
    banned = ('should', 'max out', 'maximize', 'you\'re behind', 'falling behind', 'recommend', 'consider ', 'smart',
              'wise', 'mistake', 'wasting', 'bigger shovel', 'baby step')
    hits = [w for w in banned if w in said.lower() or w in block.lower()]
    check(f's226 F7 no advice and no judgement in the sentences or on the page ({hits})', not hits)
    check('s226 F7 the help says what you do with it is yours to decide', 'what you do with it is yours to decide' in block)
    check('s226 AI-off: nothing here calls the model', 'ai_chat' not in src and '_ai_' not in src)

    # ── Net worth (F1) ────────────────────────────────────────────────────────
    check('s226 F1 net worth counts HSA / FSA balances once, from the accounts, and says how to avoid counting twice',
          app.count('+ _hsaFsaTotal()') == 1 and '+ hsaFsa;' in app and 'counted once' in app)

    # Put everything back.
    with db_session() as s:
        s.query(AppSetting).filter_by(key='export_dir').delete()
        s.query(HealthAccountTerms).filter(HealthAccountTerms.account_id.in_((hsa_id, fsa_id))).delete(synchronize_session=False)
        s.query(Transaction).filter(Transaction.account_id.in_((hsa_id, fsa_id))).delete(synchronize_session=False)
        s.query(Account).filter(Account.id.in_((hsa_id, fsa_id))).delete(synchronize_session=False)
        s.commit()
        hb.refresh(s)
