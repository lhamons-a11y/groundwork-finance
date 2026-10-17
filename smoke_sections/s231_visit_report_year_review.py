"""Item 91 (gw 2.0/VISIT_REPORT_YEAR_REVIEW.md = item 45 H7 stage 4; Rob 2026-10-16: "I approve Q3, V1-V4 and Y1-Y7
as recommended. Build item 91.").

    Q3  neither document is sent anywhere: the visit report has no write path; the packet's CSV is the registered sink
    V1  per provider, from the exact payee names on the record; no person, no medications, no pending bills - said
    V2  a payment is a payment: dated lines, "not a price list"
    V3  templated, no AI: no clinical or causal sentence, no advice
    V4  the pick is not stored
    Y1  a Schedule A section of the year-end packet, only on the health tick (screen and CSV)
    Y2  counted = health categories from ordinary accounts, less refunds; HSA/FSA payments and premiums set aside, with why
    Y3  what can't be seen is said; Y4 the floor only with the person's AGI, "on these numbers"; Y5 the 8889 detail;
    Y6  missing months mark it possibly low; Y7 no mileage, said
"""
import json
import re
import subprocess
import tempfile
from datetime import date, timedelta
from pathlib import Path


def run(ctx):
    check, c, H, HJ, BASE = ctx.check, ctx.c, ctx.H, ctx.HJ, ctx.BASE
    from core import health_documents as hd
    from core.database import Account, AppSetting, Category, Transaction, db_session

    post = lambda path, body: c.post(path, headers=HJ, data=json.dumps(body))
    data = lambda r: (r.get_json() or {}).get('data')
    today = date.today()
    y = today.year
    d1, d2 = date(y, 1, 15), date(y, 2, 20)
    P = 'S231 MAPLE CLINIC'
    with db_session() as s:
        def cat(name):
            x = s.query(Category).filter_by(name=name).first()
            if not x:
                x = Category(name=name, type='expense'); s.add(x); s.flush()
            return x.id
        doc, ins = cat('Doctor / Co-pays'), cat('Health Insurance')
        chk = Account(name='S231 Checking', type='checking', is_active=True)
        hsa = Account(name='S231 HSA', type='hsa', is_active=True)
        s.add_all([chk, hsa]); s.flush()
        rows = [Transaction(date=d1, description=P, amount=220, type='debit', category_id=doc, account_id=chk.id, source='csv'),
                Transaction(date=d2, description=P, amount=220, type='debit', category_id=doc, account_id=chk.id, source='csv'),
                Transaction(date=d2, description='S231 MAPLE CLINIC REFUND', amount=40, type='credit', category_id=doc,
                            account_id=chk.id, source='csv'),
                Transaction(date=d2, description=P, amount=150, type='debit', category_id=doc, account_id=hsa.id, source='csv'),
                Transaction(date=d1, description='S231 ACME HEALTH PLAN', amount=300, type='debit', category_id=ins,
                            account_id=chk.id, source='csv'),
                Transaction(date=d1, description='Payroll contribution', amount=1000, type='credit', account_id=hsa.id,
                            source='csv')]
        s.add_all(rows); s.commit()
        made_acc, made_rows = [chk.id, hsa.id], [t.id for t in rows]
        keys_before = {k for (k,) in s.query(AppSetting.key).all()}

    try:
        # ── V1 / V4 ───────────────────────────────────────────────────────────
        ps = {p['name']: p for p in data(c.get('/api/accounts/health-providers', headers=H))['providers']}
        check('s231 V1 the providers are the exact payee names on the record, with their counts',
              P in ps and ps[P]['payments'] == 3 and 'S231 MAPLE' not in ps)
        bad = post('/api/accounts/visit-report', {'names': ['S231 MAPLE']})
        check('s231 V1 a name not on the record is refused (never matched loosely)', bad.status_code == 400)
        r = data(post('/api/accounts/visit-report', {'names': [P]}))
        check('s231 V2 each payment with its date and account; the total; "not a price list"',
              r['summary'] == f'3 payments to {P}, $590.00 in all, from {hd.day(d1.isoformat())} to {hd.day(d2.isoformat())}.'
              and f'{hd.day(d1.isoformat())}: $220.00 from S231 Checking.' in [p['line'] for p in r['payments']]
              and f'{hd.day(d2.isoformat())}: $150.00 from S231 HSA.' in [p['line'] for p in r['payments']]
              and r['not_a_price'].startswith('A record of payments, not a price list'))
        check('s231 V1 no person, no medications, no pending bills - and it says so',
              'named people' in r['not_included'] and 'medications' in r['not_included'] and 'not yet paid' in r['not_included'])
        with db_session() as s:
            keys_after = {k for (k,) in s.query(AppSetting.key).all()}
        check('s231 V4 the pick is not stored', keys_after == keys_before)

        # ── Y1 / Y2 / Y3 / Y5 / Y6 / Y7 ──────────────────────────────────────
        q = lambda inc: data(c.get(f'/api/year-end?year={y}&include_health={1 if inc else 0}', headers=H))
        off, on = q(False), q(True)
        sa = on['health_schedule_a']
        check('s231 Y1 the Schedule A section appears only on the health tick', off['health_schedule_a'] is None and sa)
        check('s231 Y2 counted = health payments from ordinary accounts less refunds (here $440 - $40)',
              sa['total'] >= 400 and any(x['name'] == P and x['amount'] == 220 for x in sa['counted'])
              and any(x['amount'] == 40 for x in sa['refunds']))
        aside = {g['reason'][:20]: g for g in sa['set_aside']}
        hsa_g = next(g for g in sa['set_aside'] if g['reason'].startswith('Paid from an HSA'))
        prem_g = next(g for g in sa['set_aside'] if g['reason'].startswith('Health insurance premiums'))
        check('s231 Y2 HSA payments and premiums are set aside, each with its reason, never counted',
              any(x['amount'] == 150 for x in hsa_g['rows']) and any(x['amount'] == 300 for x in prem_g['rows'])
              and not any(x['amount'] in (150, 300) and x['name'] in (P, 'S231 ACME HEALTH PLAN') for x in sa['counted'])
              and 'after-tax' in prem_g['reason'])
        check('s231 Y3 / Y7 what can\'t be seen is said, and mileage is named as not included',
              hd.CANT_SEE in sa['lines'] and hd.NO_MILEAGE in sa['lines'] and sa['statement'] == hd.NOT_ADVICE)
        check('s231 Y5 the HSA detail for Form 8889, with the custodian\'s forms named as authoritative',
              sa['hsa_8889'] and sa['hsa_8889']['distributions'] >= 150 and '5498-SA' in sa['hsa_8889']['note']
              and any('S231 HSA' in x for x in sa['hsa_8889']['contributions']))
        empty = {'contributions': [], 'distributions': None}
        with db_session() as s:
            h2 = Account(name='S231 Empty HSA', type='hsa', is_active=True); s.add(h2); s.commit(); made_acc.append(h2.id)
            only = hd.schedule_a(s, y - 5)
        check('s231 Y5 absence is not zero: an HSA with nothing imported for the year has payments out "not known", never $0',
              only['hsa_8889'] and only['hsa_8889']['distributions'] is None)
        check('s231 Y6 missing months or accounts mark the total possibly low, exactly when the packet is incomplete',
              (('may be low' in ' '.join(sa['lines'])) == (not on['complete'])))

        # ── Y4 ────────────────────────────────────────────────────────────────
        check('s231 Y4 with no AGI it can\'t tell', sa['agi'] is None and any('can\'t be known without your adjusted gross income' in l for l in sa['lines']))
        post('/api/year-end/agi', {'year': y, 'value': 2000})
        sa2 = q(True)['health_schedule_a']
        floor = 150.0
        check('s231 Y4 with AGI: the floor and the amount above it, "on these numbers"',
              sa2['floor'] == floor and any(l.startswith(f'On these numbers, the counted total is ${sa2["total"] - floor:,.2f} above the 7.5% floor ($150.00')
                                            for l in sa2['lines']))
        post('/api/year-end/agi', {'year': y, 'value': 1000000})
        sa3 = q(True)['health_schedule_a']
        check('s231 Y4 below the floor it says so, and never "you can deduct"',
              any('doesn\'t reach the 7.5% floor' in l for l in sa3['lines']) and hd.ITEMISE in sa3['lines'])

        # ── Y1: the CSV, on the tick only ─────────────────────────────────────
        out_dir = Path(tempfile.mkdtemp(prefix='gw_s231_'))
        with db_session() as s:
            s.query(AppSetting).filter_by(key='export_dir').delete()
            s.add(AppSetting(key='export_dir', value=str(out_dir))); s.commit()
        csv_on = Path(data(post('/api/year-end/export', {'year': y, 'include_health': True}))['path']).read_text(encoding='utf-8')
        csv_off = Path(data(post('/api/year-end/export', {'year': y, 'include_health': False}))['path']).read_text(encoding='utf-8')
        check('s231 Y1 the CSV carries the section only on the health tick',
              '--- HEALTH CARE, FOR SCHEDULE A ---' in csv_on and P in csv_on and 'HEALTH CARE, FOR SCHEDULE A' not in csv_off and P not in csv_off)

        # ── V3 / Q3 ───────────────────────────────────────────────────────────
        said = json.dumps(r) + json.dumps(sa3)
        src = (BASE / 'core' / 'health_documents.py').read_text(encoding='utf-8')
        banned = ('diagnos', 'symptom', 'condition', 'treatment', 'should', 'ask your doctor', 'because of your',
                  'you can deduct', 'your next visit will cost', 'recommend', 'consider ', 'bigger shovel')
        hits = [w for w in banned if w in said.lower()]
        check(f's231 V3 no clinical, causal or advice wording in either document ({hits})', not hits)
        check('s231 V3 / AI-off: templated - nothing here calls the model', '_ai_' not in src and 'ai_chat' not in src)
        srv = ctx.server_src
        vr = srv.split('def visit_report():')[1].split('\n@')[0]
        check('s231 Q3 the visit report has no write path: it is only shown, then printed or saved by the person',
              'write_text' not in vr and 'open(' not in vr and 'commit' not in vr)
        try:
            ok = subprocess.run(['node', '--check', str(BASE / 'static' / 'js' / 'app.js')], capture_output=True, timeout=120).returncode == 0
        except Exception:
            ok = False
        check('s231 app.js parses', ok)
    finally:
        with db_session() as s:
            s.query(AppSetting).filter(AppSetting.key.in_(('export_dir', 'agi_by_year_json'))).delete(synchronize_session=False)
            s.query(Transaction).filter(Transaction.id.in_(made_rows)).delete(synchronize_session=False)
            s.query(Account).filter(Account.id.in_(made_acc)).delete(synchronize_session=False)
            s.commit()
