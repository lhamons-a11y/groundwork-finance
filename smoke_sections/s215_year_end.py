"""Item 65 W9 (gw 2.0/AGENT_W_ITEMS.md; Rob 2026-10-12: "approve as recommended"): the year-end packet.

    W9-a  a summary, never tax advice: the year's figures from the records, and what they don't include
    W9-b  health spending only on its tick (H6 P3), in the packet and in its CSV
    W9-c  complete or it says what is missing: a month or an account with nothing imported is listed, never zero
"""
import json
from datetime import date
from pathlib import Path


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    app = ctx.app_src
    import server
    from core.database import Account, Category, Transaction, db_session

    Y = 2017
    with db_session() as s:
        def cat(name, **kw):
            x = s.query(Category).filter_by(name=name).first()
            if not x:
                x = Category(name=name, **kw); s.add(x); s.flush()
            return x.id
        inc = cat('s215 Pay', type='income')
        food, doc = cat('Groceries'), cat('Doctor / Co-pays')
        give, intr = cat('Charitable Donations'), cat('Interest / Fees')
        chk = Account(name='s215 Checking', type='checking', is_active=True)
        card = Account(name='s215 Card', type='credit', is_active=True)
        idle = Account(name='s215 Never imported', type='savings', is_active=True)
        s.add_all([chk, card, idle]); s.flush()
        for m in range(1, 13):
            if m == 6:
                continue                                        # June: nothing at all on record
            d = date(Y, m, 15)
            s.add_all([Transaction(date=d, amount=2000, type='credit', merchant='S215 ACME', description='S215 ACME', category_id=inc, account_id=chk.id),
                       Transaction(date=d, amount=300, type='debit', merchant='S215 MARKET', description='S215 MARKET', category_id=food, account_id=chk.id)])
            if m <= 9:                                          # the card stops after September
                s.add(Transaction(date=d, amount=12.5, type='debit', merchant='S215 INTEREST CHARGE', description='S215 INTEREST CHARGE', category_id=intr, account_id=card.id))
        s.add_all([Transaction(date=date(Y, 3, 2), amount=80, type='debit', merchant='S215 CLINIC', description='S215 CLINIC', category_id=doc, account_id=chk.id),
                   Transaction(date=date(Y, 12, 1), amount=150, type='debit', merchant='S215 FOOD BANK', description='S215 FOOD BANK', category_id=give, account_id=chk.id)])
        s.commit()
        ids = (chk.id, card.id, idle.id)
    data = lambda r: (r.get_json() or {}).get('data') or {}
    try:
        p = data(c.get(f'/api/year-end?year={Y}', headers=H))
        cats = {r['name']: r['total'] for r in p.get('categories', [])}
        check(f"s215 W9 the year from the record: income by payer, categories, interest and fees, donations ({p.get('income')})",
              p['income'] == [{'payer': 'S215 ACME', 'total': 22000.0, 'deposits': 11}] and cats.get('Groceries') == 3300.0
              and p['interest'] == [{'name': 'S215 INTEREST CHARGE', 'total': 100.0}]    # eight months: January to September, June missing
              and p['donations'] == [{'name': 'S215 FOOD BANK', 'total': 150.0}] and p['gains']['lots'] == 0)
        check("s215 W9-a a summary, never tax advice: it says the preparer decides, and what it doesn't include",
              p['statement'] == "These are the year's figures from your records. Your tax preparer decides how they are treated."
              and any('deductible' in n for n in p['not_included']) and len(p['not_included']) >= 4)
        gaps = {gp['account']: gp['months'] for gp in p['account_gaps']}
        check(f"s215 W9-c complete or it says what is missing: June has no records, the card stops in September, one account was never imported ({p['missing_months']}, {sorted(gaps)})",
              p['missing_months'] == [f'{Y}-06'] and gaps.get('s215 Card') == [f'{Y}-06', f'{Y}-10', f'{Y}-11', f'{Y}-12']
              and len(gaps.get('s215 Never imported', [])) == 12 and p['complete'] is False)
        h = data(c.get(f'/api/year-end?year={Y}&include_health=1', headers=H))
        check(f"s215 W9-b health spending only on its tick: left out and counted, then in ({p['health_left_out']})",
              p['health_left_out'] == 1 and 'Doctor / Co-pays' not in cats and h['health_left_out'] == 0
              and {r['name']: r['total'] for r in h['categories']}.get('Doctor / Co-pays') == 80.0)
        out = data(c.post('/api/year-end/export', headers=HJ, data=json.dumps({'year': Y})))
        f = Path(out['path']); txt = f.read_text(encoding='utf-8'); f.unlink()
        out2 = data(c.post('/api/year-end/export', headers=HJ, data=json.dumps({'year': Y, 'include_health': True})))
        f2 = Path(out2['path']); txt2 = f2.read_text(encoding='utf-8'); f2.unlink()
        check('s215 W9-b the CSV stays on this computer and keeps health out unless ticked; it carries what is missing and what it leaves out',
              'S215 CLINIC' not in txt and 'Doctor / Co-pays' not in txt and '1 health spending transaction(s) left out' in txt
              and 'Doctor / Co-pays' in txt2 and f'no records at all,{Y}-06' in txt and 'WHAT THIS DOES NOT INCLUDE' in txt
              and "Your tax preparer decides how they are treated." in txt)
        from core import health_boundary
        check('s215 W9-b the CSV is a registered sink in the H6 boundary',
              ('server.py', 'year_end_export', 'file') in health_boundary.HEALTH_SINKS)
        page = app.split('async function _rcRenderYearEnd() {')[1].split('\n}\n')[0]
        check('s215 W9 the packet is a report: printable, saved as CSV, a year chosen, health on its own tick, never a verdict',
              "id:        'year_end'" in app and "case 'year_end':        _rcRenderYearEnd(); break;" in app
              and 'Print or save as PDF' in page and 'yearEndCsv()' in page and 'Include health spending' in page
              and 'not counted as zero' in page
              and not any(w in page.lower() for w in ('you can deduct', 'write off', 'you owe', 'tax break', 'should claim')))
    finally:
        with db_session() as s:
            s.query(Transaction).filter(Transaction.merchant.like('S215%')).delete(synchronize_session=False)
            s.query(Account).filter(Account.id.in_(ids)).delete(synchronize_session=False)
            s.query(Category).filter_by(name='s215 Pay').delete()
            s.commit()
