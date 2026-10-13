"""Item 80 (gw 2.0/PLAN_EDITS.md E1-E6, RULED 2026-10-11; Rob: "build 80"): a plan's Undo is not 33 decisions.

    E1  "Make this my budget" and its Undo mark their budget edits with the plan they belong to
    E2  an undone plan contributes nothing to the Willingness Layer
    E3  a kept plan's cut is read like the person's own edit; a line the person changed after the plan stays theirs
    E4  old unmarked entries are found by their shape, shown, and marked on the tap - never deleted
    E6  a hand edit is read exactly as before
"""
import json
from datetime import datetime, timedelta


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    from core import plan_edits as pe
    from core.database import AppSetting, BudgetItem, HistorianEntry, db_session

    # ── E2 / E3: the reader rule ──
    ents = [(1, {'source': 'income_change_apply', 'plan_at': 'T', 'budget_item_id': 10}),
            (2, {'source': 'income_change_apply', 'plan_at': 'T', 'budget_item_id': 11}),
            (3, {'source': 'income_change_apply', 'plan_at': 'T', 'budget_item_id': 12}),
            (4, {'source': 'income_change_undo', 'plan_at': 'T', 'budget_item_id': 10}),
            (5, {'source': 'income_change_undo', 'plan_at': 'T', 'budget_item_id': 11}),
            (6, {'budget_item_id': 10})]                                    # a hand edit
    out = pe.leave_out(ents)
    check(f'E2/E3 an undone line\'s cut and restore are left out; a line the Undo left alone (edited since) stays; a hand edit stays ({sorted(out)})',
          out == {1, 2, 4, 5})

    # ── E4: finding old entries by shape ──
    t0 = datetime(2026, 10, 10, 22, 2, 30)
    t1 = datetime(2026, 10, 10, 23, 19, 3)
    rows = [(100 + i, t0, {'budget_item_id': i, 'name': f'L{i}'}, 100.0 * i, 50.0 * i) for i in range(1, 5)]
    rows += [(200 + i, t1, {'budget_item_id': i, 'name': f'L{i}'}, 50.0 * i, 100.0 * i) for i in range(1, 5)]
    rows += [(300, t1 + timedelta(minutes=5), {'budget_item_id': 1}, 100.0, 90.0)]                 # a hand edit after
    rows += [(400 + i, t0 + timedelta(days=1), {'budget_item_id': 20 + i}, 10.0, 5.0) for i in range(3)]   # a kept bulk change
    pr = pe.unmarked_pairs(rows)
    check(f'E4 the apply and its Undo are found by their shape; a hand edit and an un-undone group are not ({[(p["apply_at"], len(p["lines"])) for p in pr]})',
          len(pr) == 1 and pr[0]['apply_ids'] == [101, 102, 103, 104] and pr[0]['undo_ids'] == [201, 202, 203, 204])
    near = rows[:4] + [(201, t1, {'budget_item_id': 1}, 50.0, 99.0)]
    check('E4 a group that does not restore exactly the old amounts is not taken for an Undo', pe.unmarked_pairs(near) == [])

    # ── E1 + the routes, end to end ──
    with db_session() as s:
        items = [BudgetItem(name=f's206 Line {i}', category=f's206 Cat {i}', amount=200.0, type='expense', is_active=True) for i in range(4)]
        s.add_all(items); s.commit()
        ids = [i.id for i in items]
        plan = {'changes': [{'id': i, 'name': f's206 Line {n}', 'old': 200.0, 'new': 150.0} for n, i in enumerate(ids)], 'at': 'x'}
    import server
    with db_session() as s:
        last_id = s.query(HistorianEntry.id).order_by(HistorianEntry.id.desc()).first()
        last_id = last_id[0] if last_id else 0          # only entries written from here on are this test's
    real_state = server._income_change_state
    server._income_change_state = lambda session: {'change': {'month': '2026-07'},
                                                   'scenarios': [{'key': 'budget_follows', 'plan': plan}]}
    try:
        a = c.post('/api/income-change/apply', headers=HJ, data='{}')
        u = c.post('/api/income-change/undo', headers=HJ, data='{}')
    finally:
        server._income_change_state = real_state
    with db_session() as s:
        mine = [e for e in s.query(HistorianEntry).filter(HistorianEntry.event_category == 'budget_adjusted',
                                                           HistorianEntry.id > last_id).all()
                if json.loads(e.context_json or '{}').get('budget_item_id') in ids]
        srcs = sorted(json.loads(e.context_json)['source'] for e in mine)
        plan_ats = {json.loads(e.context_json)['plan_at'] for e in mine}
        w = server._willingness_inputs(s)
    check(f'E1 the apply and the Undo each mark their entries with the plan and one shared time ({srcs})',
          a.status_code == 200 and u.status_code == 200
          and srcs == ['income_change_apply'] * 4 + ['income_change_undo'] * 4 and len(plan_ats) == 1)
    check('E2 the undone plan is not in the Willingness Layer\'s edits at all',
          not any(e['category'].startswith('s206 Cat') for e in w['edits']))

    # E4 through the routes: legacy entries (no source), shown then marked, never deleted
    with db_session() as s:
        now = datetime.utcnow().replace(microsecond=0) - timedelta(hours=2)
        for n, i in enumerate(ids):
            s.add(HistorianEntry(event_category='budget_adjusted', expected_value=200.0, actual_value=120.0, created_at=now,
                                 context_json=json.dumps({'budget_item_id': i, 'name': f's206 Line {n}', 'item_type': 'expense'})))
            s.add(HistorianEntry(event_category='budget_adjusted', expected_value=120.0, actual_value=200.0,
                                 created_at=now + timedelta(minutes=30),
                                 context_json=json.dumps({'budget_item_id': i, 'name': f's206 Line {n}', 'item_type': 'expense'})))
        s.commit()
        before = s.query(HistorianEntry).filter_by(event_category='budget_adjusted').count()
    shown = c.get('/api/willingness/plan-repair', headers=H).get_json()['data']['pairs']
    mine_pair = next((p for p in shown if p['apply_at'] == now.strftime('%Y-%m-%d %H:%M:%S')), None)
    marked = c.post('/api/willingness/plan-repair/mark', headers=HJ, data=json.dumps({'apply_at': mine_pair['apply_at'] if mine_pair else ''}))
    nope = c.post('/api/willingness/plan-repair/mark', headers=HJ, data=json.dumps({'apply_at': '1999-01-01 00:00:00'}))
    with db_session() as s:
        after = s.query(HistorianEntry).filter_by(event_category='budget_adjusted').count()
        logged = s.query(HistorianEntry).filter_by(event_category='plan_edits_marked').count()
        w2 = server._willingness_inputs(s)
    check('E4 the old pair is shown line by line, then marked on the tap - nothing deleted, the marking recorded',
          mine_pair is not None and len(mine_pair['lines']) == 4 and marked.status_code == 200
          and marked.get_json()['data']['marked'] == 8 and after == before and logged >= 1 and nope.status_code == 404)
    check('E2 after marking, the old undone plan is not read either',
          not any(e['category'].startswith('s206 Cat') for e in w2['edits']))

    # E6: a hand edit still reads as before
    with db_session() as s:
        s.add(HistorianEntry(event_category='budget_adjusted', expected_value=200.0, actual_value=180.0,
                             context_json=json.dumps({'budget_item_id': ids[0], 'name': 's206 Line 0', 'item_type': 'expense'})))
        s.commit()
        w3 = server._willingness_inputs(s)
    check('E6 a hand edit is read exactly as before', any(e['category'] == 's206 Cat 0' and e['new'] == 180.0 for e in w3['edits']))

    with db_session() as s:
        for e in s.query(HistorianEntry).filter(HistorianEntry.event_category.in_(['budget_adjusted', 'plan_edits_marked'])).all():
            cj = json.loads(e.context_json or '{}')
            if cj.get('budget_item_id') in ids or e.event_category == 'plan_edits_marked':
                s.delete(e)
        s.query(BudgetItem).filter(BudgetItem.name.like('s206%')).delete(synchronize_session=False)
        s.query(AppSetting).filter_by(key='income_change_applied').delete()
        s.commit()
