"""Coming back to a saved trip (gw 2.0/TRIP_SAVED.md; Rob 2026-11-05).

    S1  what was typed in the planner is kept with the trip, and comes back from the record in a new read
    S2  a confirmation number is never kept, at any depth; anything else outside the list is dropped
    S3  updating changes the figures, dates and details; the name, the status and the sources stay; the fund follows the date
    S4  a finished trip cannot be updated; a bad total is refused and changes nothing
    S5  the page: the costs on the card, reopening changes nothing until Update, a different destination is a new trip
    S6  saying it offers the button and saves nothing; real questions about trips are not taken for it
    S7  Your trips has its own tab, and each tab prints what it shows
"""
import json
import re
import shutil
import subprocess
from datetime import date, timedelta


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    from core import trips as tr
    from core.database import SinkingFund, Trip, db_session

    post = lambda b: c.post('/api/trips', headers=HJ, data=json.dumps(b))
    patch = lambda i, b: c.patch(f'/api/trips/{i}', headers=HJ, data=json.dumps(b))
    data = lambda r: (r.get_json() or {}).get('data')
    fresh = lambda i: next(t for t in data(c.get('/api/trips', headers=H))['trips'] if t['id'] == i)

    soon = date.today() + timedelta(days=90)
    planner = {'dest': 's289 Nashville', 'origin': 'Millbrook, OH', 'depart': soon.isoformat(), 'travelers': '2', 'mode': 'drive',
               'mpg': '31', 'roundTrip': True, 'activities': '150', 'password': 'not on the list',
               'quote': {'hotelTotal': 612.5, 'confirmation': 'ABC123'},
               'itinerary': {'sender': 'Example', 'parts': [{'kind': 'flight', 'amount': 300, 'Confirmation_Number': 'XYZ'}]}}
    made = data(post({'dest': 's289 Nashville', 'depart': soon.isoformat(), 'ret': (soon + timedelta(days=3)).isoformat(),
                      'transport': 180, 'hotel': 612.5, 'buffer': 79, 'total': 871.5, 'planner': planner}))
    tid = made['id']
    back = fresh(tid)['planner']
    check('s289 S1 what was typed comes back from the record',
          back['origin'] == 'Millbrook, OH' and back['mpg'] == '31' and back['mode'] == 'drive' and back['roundTrip'] is True
          and back['quote']['hotelTotal'] == 612.5 and back['itinerary']['parts'][0]['amount'] == 300)
    with db_session() as s:
        raw = s.get(Trip, tid).planner_json
    check('s289 S2 a confirmation number is not kept, at any depth, and what is off the list is dropped',
          'ABC123' not in raw and 'XYZ' not in raw and 'password' not in raw)
    check('s289 S2 a quote too large to be one is not kept',
          'quote' not in tr.planner_inputs({'quote': {'x': 'y' * (tr.PLANNER_MAX + 1)}})
          and tr.planner_inputs('not a form') == {} and tr.planner_inputs({'mode': 'teleport'}) == {})

    src = data(patch(tid, {'sources': [{'kind': 'save_ahead', 'amount': 800}]}))
    fund_id = src['fund_id']
    later = soon + timedelta(days=7)
    up = data(patch(tid, {'replan': {'dest': 'Somewhere Else', 'label': 'Somewhere Else', 'status': 'done', 'depart': later.isoformat(),
                                     'ret': (later + timedelta(days=3)).isoformat(), 'transport': 150, 'hotel': 500, 'buffer': 65,
                                     'total': 715, 'planner': {'origin': 'Dayton, OH'}}}))
    with db_session() as s:
        deadline = s.get(SinkingFund, fund_id).deadline
    check('s289 S3 an update changes the figures, dates, lines and details',
          up['total'] == 715 and up['depart'] == later.isoformat() and up['planner'] == {'origin': 'Dayton, OH'}
          and [x['amount'] for x in up['lines']] == [150, 500, 65])
    check('s289 S3 the name and status stay: a booking finds its trip by name',
          up['label'] == 's289 Nashville' and up['status'] == 'going')
    check('s289 S3 the sources stay, and show they now exceed the trip; the fund follows the date',
          up['assigned'] == 800 and up['left_to_assign'] == -85 and deadline == later.isoformat())

    for bad in ({'total': 0}, {'total': 'lots'}, {}):
        check(f's289 S4 a bad total is refused ({bad})', patch(tid, {'replan': bad}).status_code == 400)
    check('s289 S4 and nothing changed', fresh(tid)['total'] == 715)
    with db_session() as s:
        s.get(Trip, tid).status = 'done'
        s.commit()
    check('s289 S4 a finished trip stays as it was',
          patch(tid, {'replan': {'total': 1}}).status_code == 400 and fresh(tid)['total'] == 715)
    with db_session() as s:
        s.delete(s.get(Trip, tid))
        f = s.get(SinkingFund, fund_id)
        if f is not None:
            s.delete(f)
        s.commit()

    # ── The page ──
    app = ctx.app_src
    card = app[app.index('function _tripCardHTML(t)'):app.index('// ── Item 114 H20c')]
    check('s289 S5 the card shows the trip\'s costs and offers the way back in', '_tripLinesHTML(t)' in card and 'tripReopen(' in card)
    reopen = app[app.index('function tripReopen(id)'):app.index('function tripLeaveOpen()')]
    check('s289 S5 reopening asks nothing of the server, so the saved trip cannot change',
          'API.' not in reopen and 'generateTripBudget' not in reopen)
    check('s289 S5 only one call writes an update, behind its own button',
          app.count('replan:') == 1 and 'onclick="tripUpdateOpen()"' in app)
    check('s289 S5 a finished trip opens as a start, not for updating', "t.status === 'done' ? null : t.id" in reopen)
    check('s289 S5 a different destination is not an update', 'd.dest === open.label' in app)

    html = (ctx.BASE / 'static' / 'index.html').read_text(encoding='utf-8')
    plan_at, trips_at, card_at = html.index('id="tripPanel-plan"'), html.index('id="tripPanel-trips"'), html.index('id="tripTripsCard"')
    check('s289 S7 Your trips has its own tab: the card is in its panel, the planner in the other',
          plan_at < html.index('id="tripStep1"') < trips_at < card_at and 'id="tripTab-trips"' in html)
    check('s289 S7 reopening goes back to the planner tab, and saving goes to Your trips',
          "tripShowTab('plan')" in reopen and app.count("tripShowTab('trips')") >= 3)
    pr = (ctx.BASE / 'static' / 'js' / 'print.js').read_text(encoding='utf-8')
    check('s289 S7 each tab prints what it shows',
          "startsWith('Your trips')" in pr and '_prCostTable(d) + saved' not in pr)

    # ── Saying it ──
    def regex(name):
        return re.search(r'const ' + name + r' = (/.+/);', app).group(1)

    says = ['im saving for this trip', "i'm saving up for a trip", "i'm creating a savings for this trip", "i'm using money for this trip",
            "we're setting money aside for our vacation", "i'm going on a trip to nashville", "we're putting money away for the trip"]
    no = ['how do i save for a trip', 'what does a trip cost', 'trip planner', 'open the trip planner', 'how much did my trip cost',
          "i'm saving", 'going on', 'show me my transactions', 'save money']
    node = shutil.which('node')
    if node:
        js = (f'const a={regex("ASK_TRIP_COMMIT")};const t=x=>x.map(s=>a.test(s));'
              f'console.log(JSON.stringify([t({json.dumps(says)}),t({json.dumps(no)})]));')
        out = json.loads(subprocess.run([node, '-e', js], capture_output=True, text=True, timeout=60).stdout)
        check('s289 S6 saying you are saving or using money for a trip offers it', all(out[0]))
        check('s289 S6 real questions are left for what answers them', not any(out[1]))
    places = app[app.index('const ASK_PLACES = ['):app.index('const ASK_GO = ')]
    yours = next(x for x in places.splitlines() if "label: 'Your trips'" in x)
    planner_row = next(x for x in places.splitlines() if "label: 'the Trip Planner'" in x)
    check('s289 S6 Your trips is a page to the voice, opening its tab',
          "'your trips'" in yours and "tab: ['trip', 'trips']" in yours and 'trip: tripShowTab' in app
          and "(?:my|our) trips$/, 'your trips')" in app)
    check('s289 S6 and "trips" is the planner (Rob 2026-11-05)', "'trip planner'" in planner_row and "'trips'" in planner_row
          and "'trips'" not in yours.split('view:')[0]
          and "tab: ['trip', 'plan']" in planner_row)
    body = app[app.index('function _askTrip('):app.index('function askIntent(')]
    check('s289 S6 saying it writes nothing: the only way on is the button',
          'API.' not in body and 'onclick="closeAsk(); tripImGoing()"' in body and body.count('tripImGoing()') == 1)
