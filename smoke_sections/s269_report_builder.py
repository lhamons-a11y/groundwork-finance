"""Item 115 stages 1-3 (gw 2.0/ASK_FOR_A_REPORT.md; Rob 2026-10-31: C1-C11 accepted, C3 "Accept, all 40 at once"):
a report built from sections.

    C1/C3  six shapes, ten subjects, and exactly the pairings section 11's table ticks (39 - the table's own count)
    C2     the reports are templates, every section in them catalogued; health is not a subject (TM7)
    H22    every section is drawn by Groundwork - no model call - and says "doesn't know yet" rather than guess
    P11    a saved report is its sections and the style the person chose; nothing saved without a name
    C9-C11 six styles, text and charts the default; a section may carry its own style; a list is always a table (P14)
"""
import json


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    from core import engine, report_sections as rs

    cat = c.get('/api/reports/builder/catalog', headers=H).get_json()['data']
    ids = {s['id'] for s in cat['sections']}
    ticks = {1: '12345', 2: '12345', 3: '135', 4: '12345', 5: '1235', 6: '23456', 7: '12345', 8: '234', 9: '34', 10: '46'}
    want = {f'{s}.{subj}' for subj, shapes in ticks.items() for s in shapes}
    check('s269 C1/C3 six shapes, ten subjects, and exactly section 11\'s pairings (shape.subject - 1.5 is monthly debt payments)',
          len(cat['shapes']) == 6 and len(cat['subjects']) == 10 and ids == want and len(ids) == 39
          and next(s for s in cat['sections'] if s['id'] == '1.5')['title'] == 'Debt payments, each month')
    check('s269 C2 every template is built of catalogued sections; health is no subject (TM7)',
          len(cat['templates']) >= 10 and all(s['id'] in ids for t in cat['templates'] for s in t['sections'])
          and not any('health' in (s['key'] + s['name']).lower() for s in cat['subjects']))
    st = {s['key']: s for s in cat['styles']}
    check('s269 C9/C10 six styles; text and charts on screen, print / PDF when printing',
          len(st) == 6 and st['text_charts'].get('default') and st['print'].get('print_default'))

    calls = []
    real = engine.complete_json
    engine.complete_json = lambda *a, **k: calls.append(1) or {'ok': False}
    try:
        everything = [{'id': i, 'settings': {'category': 'Groceries', 'payee': 'a', 'amount': 100, 'period_b': 'last month'}}
                      for i in sorted(ids)]
        r = c.post('/api/reports/builder/run', headers=HJ, data=json.dumps({'sections': everything[:20]}))
        r2 = c.post('/api/reports/builder/run', headers=HJ, data=json.dumps({'sections': everything[20:]}))
        out = r.get_json()['data']['sections'] + r2.get_json()['data']['sections']
    finally:
        engine.complete_json = real
    check('s269 H22 all 39 sections run with no model call, each with Groundwork\'s own sentences',
          r.status_code == 200 and len(out) == 39 and not calls and all(o['sentences'] for o in out))
    check('s269 H5 a section the record cannot speak to says it does not know yet, and what would let it',
          all(o['enough'] or o['sentences'][0].startswith("Groundwork doesn't know yet") for o in out))
    check('s269 P14 a list draws a table, never a chart',
          all(o['chart'] is None for o in out if o.get('shape') == 'list' and o['enough']))
    bad = c.post('/api/reports/builder/run', headers=HJ, data=json.dumps({'sections': [{'id': '6.1'}, {'id': 'x'},
                                                                                       {'id': '4.1', 'style': 'neon'}]}))
    b = bad.get_json()['data']['sections']
    check('s269 C3 a pairing the table does not tick is not run; a style not one of the six is dropped',
          [x['id'] for x in b] == ['4.1'] and 'style' not in b[0])
    p = rs.run(type('R', (), {'today': __import__('datetime').date.today(), 'get': lambda s, path: {},
                              'session_factory': __import__('core.database', fromlist=['db_session']).db_session})(),
               '1.5', {'period': 'the 5th of never'})
    check('s269 P5 a period Groundwork cannot read is said, not guessed', not p['enough'] and 'not a period' in p['sentences'][0])

    none = c.post('/api/reports/builder/saved', headers=HJ, data=json.dumps({'name': '', 'sections': [{'id': '4.1'}]}))
    sv = c.post('/api/reports/builder/saved', headers=HJ, data=json.dumps(
        {'name': 'Debt payments', 'style': 'text_grid', 'sections': [{'id': '1.5', 'settings': {'period': 'June to September'}},
                                                                     {'id': '4.6', 'style': 'compact'}]}))
    saved = c.get('/api/reports/builder/saved', headers=H).get_json()['data']['saved']
    one = next((x for x in saved if x['name'] == 'Debt payments'), {})
    check('s269 P11 a saved report is its sections and the person\'s style (C11: one section its own); none without a name',
          none.status_code == 400 and sv.status_code == 200 and one.get('style') == 'text_grid'
          and one['sections'][0]['settings'] == {'period': 'June to September'} and one['sections'][1].get('style') == 'compact')
    c.delete(f"/api/reports/builder/saved/{one.get('id')}", headers=H)
    after = c.get('/api/reports/builder/saved', headers=H).get_json()['data']['saved']
    check('s269 P11 a saved report is removed on the person\'s word', not any(x.get('id') == one.get('id') for x in after))

    js = ctx.app_src
    check('s269 the Report Center offers Build a report, its styles and Save; Print redraws in the print style',
          "id:        'builder'" in js and "case 'builder':         _rcRenderBuilder()" in js
          and "await _rbRun('print')" in js and "'/api/reports/builder/saved'" in js)
