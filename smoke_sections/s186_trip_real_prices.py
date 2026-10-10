"""Item 59 P1 on 1.x: the trip budget never shows or saves a model's prices (gw 2.0/TRIP_REAL_PRICES.md, RULED
2026-10-09 "P1 on both lines"; built on "build all items that have been ruled on"). Master also has P2-P5.

    P1  no model is asked for a price, nothing is labelled live, no web-search tool; aiResult is never saved again;
        an old saved one says what it was
"""
import json


def run(ctx):
    check, c, H, HJ, app = ctx.check, ctx.c, ctx.H, ctx.HJ, ctx.app_src
    from core.database import AppSetting, db_session
    gen = app.split('async function generateTripBudget(')[1].split('\n}')[0]
    check('s186 P1 no model is asked for a price, nothing is labelled live, and no web-search tool is passed',
          'callAI(' not in gen and 'live prices' not in app and 'web_search_20250305' not in gen
          and 'Always search for real current prices' not in app and '_renderTripBudgetResult' not in app)
    r = c.post('/api/trip/budget', headers=HJ, data=json.dumps({'dest': 's186', 'total': 900, 'aiResult': {'hotel': {'cost': 999}}}))
    with db_session() as s:
        saved = json.loads(s.query(AppSetting).filter_by(key='trip_budget').first().value)
        s.query(AppSetting).filter_by(key='trip_budget').first().value = json.dumps({'dest': 'old', 'aiResult': {'total': 1234}})
        s.commit()
    old = c.get('/api/trip/budget', headers=H).get_json()['data']
    check('s186 P1 a budget is never saved with the model\'s prices again; an old one says what it was',
          r.status_code == 200 and 'aiResult' not in saved and saved['total'] == 900
          and old['aiResult_label'] == 'estimated by the AI model in an earlier version, not a price')
    with db_session() as s:
        s.query(AppSetting).filter_by(key='trip_budget').delete(); s.commit()
