"""Item 93 stage 2 (gw 2.0/BANK_SIDE_RECORDS.md B6 and B9; Rob 2026-10-17 B1-B12 approved, 2026-10-18 "go ahead on
stage 2"). Master only.

    B6  an edit is kept as a dated correction beside the bank's version, never over it; every total uses the
        correction; whatever path changes a line, the change is kept; a set-aside line keeps its history
    B9  a pending line and its posted line are both kept: the bank's own id pairs them, anything else is asked;
        the posted line is current for totals, the pending one set aside with its own date and amount;
        a no leaves both and is not asked again; restoring the pending line undoes the pair
"""
import json
from datetime import datetime


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    from core.database import (Account, ImportHeldLine, PendingPosted, SetAsideTransaction, Transaction,
                               TransactionCorrection, db_session)
    import bank_importer

    post = lambda path, body: c.post(path, headers=HJ, data=json.dumps(body))
    patch = lambda path, body: c.patch(path, headers=HJ, data=json.dumps(body))
    data = lambda r: (r.get_json() or {}).get('data')
    with db_session() as s:
        a = Account(name='S235 Card', type='credit', is_active=True); s.add(a); s.commit()
        aid = a.id
    rec = lambda d, desc, amt, fitid='', pending=False: dict(
        {'date': d, 'description': desc, 'amount': amt, 'type': 'debit', 'category': 'Other', 'fitid': fitid,
         'source': 'csv'}, **({'pending': True} if pending else {}))
    ours = lambda s: s.query(Transaction).filter(Transaction.account_id == aid, Transaction.description.like('%S235%'))
    try:
        # ── B6 ────────────────────────────────────────────────────────────────
        data(post('/api/import/commit', {'account_id': aid, 'records': [rec('2026-03-02', 'S235 HARDWARE 88', 30.00)]}))
        with db_session() as s:
            tid = ours(s).first().id
        patch(f'/api/transactions/{tid}', {'amount': 27.50, 'description': 'S235 Hardware (paint)',
                                           'category': 'Groceries', 'date': '2026-03-01'})
        patch(f'/api/transactions/{tid}', {'amount': 27.50})        # the same amount again: nothing changed
        v = data(c.get(f'/api/transactions/{tid}/versions', headers=H))
        check("s235 B6 the bank's version stays underneath, named as the bank's",
              v['first_kind'] == 'bank' and v['first']['amount'] == '30.00' and v['first']['description'] == 'S235 HARDWARE 88'
              and v['first']['date'] == '2026-03-02' and v['first']['category'] == 'Other')
        check('s235 B6 each correction is kept, dated, with what it replaced (an unchanged value is not one)',
              sorted(x['field'] for x in v['corrections']) == ['amount', 'category', 'date', 'description']
              and all(x['on'] for x in v['corrections'])
              and next(x for x in v['corrections'] if x['field'] == 'amount')['after'] == '27.50')
        with db_session() as s:
            row = s.get(Transaction, tid)
        check('s235 B6 every total uses the correction: the line holds the corrected value',
              abs(row.amount - 27.50) < 0.001 and v['current']['amount'] == '27.50')
        lst = data(c.get(f'/api/transactions?account_id={aid}&per_page=50', headers=H))
        check('s235 B6 the Ledger is told which lines carry corrections',
              next(x for x in lst if x['id'] == tid)['corrected'] is True)
        # any path, not only the Ledger's edit (a category move on a yes, a split)
        with db_session() as s:
            t = s.get(Transaction, tid); t.type = 'credit'; s.commit()
            t = s.get(Transaction, tid); t.type = 'debit'; s.commit()
            kept = s.query(TransactionCorrection).filter_by(transaction_id=tid, field='type').count()
        check('s235 B6 a change made by any path is kept, not only the Ledger edit', kept == 2)
        # a line from before corrections were kept is not called the bank's
        with db_session() as s:
            t = s.get(Transaction, tid); t.created_at = datetime(2020, 1, 1); s.commit()
        v_old = data(c.get(f'/api/transactions/{tid}/versions', headers=H))
        check("s235 B6 a line from before corrections were kept: its earliest version is not claimed as the bank's",
              v_old['first_kind'] == 'earliest_kept' and 'not kept' in v_old['first_label'])
        c.delete(f'/api/transactions/{tid}', headers=H)
        with db_session() as s:
            sa = s.query(SetAsideTransaction).filter_by(original_id=tid, restored_at=None).first()
            hist = s.query(TransactionCorrection).filter_by(transaction_id=tid).count()
        post(f'/api/transactions/set-aside/{sa.id}/restore', {})
        v2 = data(c.get(f'/api/transactions/{tid}/versions', headers=H))
        check('s235 B6 a line set aside and restored keeps its history', hist >= 6 and len(v2['corrections']) == hist)

        # ── B9: the parser ────────────────────────────────────────────────────
        recs, bank, _w = bank_importer.detect_and_parse(
            'Status,Date,Description,Debit,Credit\nPending,03/12/2026,CLARK GAS,48.20,\nCleared,03/10/2026,KROGER,20.00,\n', 'c.csv')
        check('s235 B9 a bank file that marks a line pending is read as pending; the rest as before',
              recs[0].get('pending') is True and recs[0]['cleared'] is False and not recs[1].get('pending'))

        # ── B9: the bank's own id pairs them ──────────────────────────────────
        r1 = data(post('/api/import/commit', {'account_id': aid, 'records': [
            rec('2026-03-12', 'S235 BISTRO', 48.20, fitid='S235-P1', pending=True)]}))
        with db_session() as s:
            pend = ours(s).filter(Transaction.import_id == 'S235-P1').first()
            pend_id, pend_flag = pend.id, (pend.pending, pend.cleared)
        check('s235 B9 a pending line comes in marked pending', r1['created'] == 1 and pend_flag == (True, False))
        r2 = data(post('/api/import/commit', {'account_id': aid, 'records': [
            rec('2026-03-14', 'S235 BISTRO', 51.90, fitid='S235-P1')]}))
        with db_session() as s:
            live = ours(s).filter(Transaction.import_id == 'S235-P1').all()
            kept_p = s.query(SetAsideTransaction).filter_by(original_id=pend_id, restored_at=None).first()
            pair = s.query(PendingPosted).filter_by(pending_id=pend_id).first()
        check("s235 B9 the bank's own id: the posted line comes in (not skipped as a duplicate) and is current",
              r2['created'] == 1 and r2['pending_paired'] == 1 and len(live) == 1 and abs(live[0].amount - 51.90) < 0.001)
        check('s235 B9 the pending line is kept whole, set aside with its own date and amount',
              kept_p is not None and '48.2' in kept_p.row_json and '2026-03-12' in kept_p.row_json
              and pair.state == 'paired' and pair.how == 'bank_id')
        vp = data(c.get(f'/api/transactions/{live[0].id}/versions', headers=H))['pending']
        check('s235 B9 a changed amount is shown, not overwritten (pending $48.20, posted $51.90)',
              vp['changed'] and vp['pending_amount'] == 48.20 and vp['posted_amount'] == 51.90
              and vp['pending_date'] == '2026-03-12')
        r2b = data(post('/api/import/commit', {'account_id': aid, 'records': [
            rec('2026-03-14', 'S235 BISTRO', 51.90, fitid='S235-P1')]}))
        check('s235 B9 the posted file imported again is the same line again (skipped)', r2b['duplicates'] == 1 and r2b['created'] == 0)

        # ── B9: similarity only asks ──────────────────────────────────────────
        data(post('/api/import/commit', {'account_id': aid, 'records': [
            rec('2026-03-20', 'S235 CLARK GAS 4471', 1.00, pending=True),
            rec('2026-03-21', 'S235 KROGER 12', 20.00, pending=True),
            rec('2026-03-22', 'S235 DINER', 12.00, pending=True)]}))
        r3 = data(post('/api/import/commit', {'account_id': aid, 'records': [
            rec('2026-03-22', 'Purchase S235 CLARK GAS 4471 MILLBROOK OH', 42.10),
            rec('2026-03-23', 'S235 KROGER 12 MILLBROOK', 21.40),
            rec('2026-03-22', 'S235 DINER', 12.00)]}))          # exactly like its pending line
        pairs = r3.get('pending_pairs') or []
        with db_session() as s:
            still = ours(s).filter(Transaction.pending.is_(True)).count()
        check('s235 B9 similarity only asks: posted lines come in, each pending line stays until the person answers',
              r3['created'] == 3 and len(pairs) == 3 and still == 3 and not r3.get('held'))
        gas = next(p for p in pairs if p['pending_amount'] == 1.00)
        kro = next(p for p in pairs if p['pending_amount'] == 20.00)
        bad = post(f"/api/import/pending-pairs/{gas['id']}", {'answer': 'maybe'})
        data(post(f"/api/import/pending-pairs/{gas['id']}", {'answer': 'yes'}))
        data(post(f"/api/import/pending-pairs/{kro['id']}", {'answer': 'no'}))
        with db_session() as s:
            gas_pend = s.get(Transaction, gas['pending_id'])
            kro_pend = s.get(Transaction, kro['pending_id'])
            gp = s.get(PendingPosted, gas['id'])
            gp_state, gp_how, gp_sa = gp.state, gp.how, gp.set_aside_id
            from core import bank_versions
            again = bank_versions.suggest(s, s.get(Transaction, kro['posted_id']))
            s.rollback()
        check('s235 B9 a yes pairs them: the pending line is set aside, the posted one current',
              bad.status_code == 400 and gas_pend is None and gp_state == 'paired' and gp_how == 'your_yes')
        check('s235 B9 a no leaves both lines in the ledger, and that pending line is not asked about again',
              kro_pend is not None and again is None)
        listed = data(c.get('/api/import/pending-pairs', headers=H))['pairs']
        check('s235 B9 answered pairs leave the list', not any(p['id'] in (gas['id'], kro['id']) for p in listed))

        # restoring the pending line undoes the pair
        post(f"/api/transactions/set-aside/{gp_sa}/restore", {})
        with db_session() as s:
            st = s.get(PendingPosted, gas['id']).state
        check('s235 B9 restoring a paired pending line undoes the pair (it counts again)', st == 'undone')

        app = ctx.app_src
        bloom = app.split('function _openEditBloom(')[1].split('\nfunction ')[0]
        check('s235 B6/B9 the page: the edit bloom shows the earlier versions; pending lines and pairs are shown, decided only by a yes',
              '_versionsSlot(bloom, id)' in bloom and "t.pending ?" in app and '_pendingPairsHtml(pairs)' in app
              and "'/api/import/pending-pairs'" in app and '_showPendingAfterImport(data)' in app)
        srv = ctx.server_src
        upd = srv.split('def update_transaction(')[1].split('\n@')[0]
        from core import database as _db
        check('s235 B6 the corrections are kept below the edit routes, by a flush listener on every session',
              hasattr(_db, '_keep_corrections') and set(_db.CORRECTED_FIELDS) >= {'date', 'description', 'amount', 'category_id'}
              and 'session.delete(' not in upd)
    finally:
        with db_session() as s:
            ids = [t.id for t in s.query(Transaction).filter(Transaction.account_id == aid).all()]
            sa_ids = [x.original_id for x in s.query(SetAsideTransaction).filter_by(account_id=aid).all()]
            s.query(TransactionCorrection).filter(TransactionCorrection.transaction_id.in_(ids + sa_ids)).delete(synchronize_session=False)
            s.query(PendingPosted).filter_by(account_id=aid).delete()
            s.query(Transaction).filter(Transaction.id.in_(ids)).delete(synchronize_session=False)
            s.query(SetAsideTransaction).filter_by(account_id=aid).delete()
            s.query(ImportHeldLine).filter_by(account_id=aid).delete()
            s.query(Account).filter_by(id=aid).delete()
            s.commit()
