"""Ask for a tile, remaining slices (`gw 2.0/ASK_FOR_A_TILE.md`, item 28; Rob 2026-10-01: "Build Item 28").

    entries   savings funds, recurring charges, one category over time, EIA energy prices, the working picture -
              each offered only when the record backs it (K3), each saying what it needs when it doesn't
    R2        one category over time is the one parameterised shape: 'cat:<a category in the ledger>', seen in at least
              three recorded months; anything else is refused
    matching  a category the ledger names competes on the same scale as the catalogue - "gas prices" is the energy
              tile even with a category called Gas
    K2 / R7   the local model may pick ONE catalogue id when the search finds nothing; a sentence, a parameterised id,
              a timeout or no model is "none"; it writes nothing the user sees
    words     every tile's sentences pass the BANNED lexicon; gaps say "none recorded", never zero
"""
import json
import shutil
import subprocess
import time
from datetime import date, timedelta

_RUN = [0]


class _Q:
    def __init__(self, n):
        self.n = n

    def filter_by(self, **_k):
        return self

    def count(self):
        return self.n


class _S:
    def __init__(self, n):
        self.n = n

    def query(self, *_a):
        return _Q(self.n)


def _node(base):
    node = shutil.which('node')
    if not node:
        return None
    path = str(base.joinpath('static/js/teaching/tiletext.js')).replace('\\', '/')
    prog = f"""
const T = require({json.dumps(path)});
const F = {{money: n => '$' + Number(n).toFixed(2), date: s => s, month: s => s}};
const out = {{}};
out.funds = T.funds({{backed: true, funds: [
  {{name: 'Car', pace: {{funded: false, remaining: 3800, pace_monthly: 200, pace_source: 'plan', finish_months: 19,
     deadline_months: 18, since_break: {{month: '2026-07'}}, insufficient_since_break: true}}}},
  {{name: 'Trip', pace: {{funded: true}}}}]}}, F);
out.recurring = T.recurring({{backed: true, items: [{{name: 'Netflix', monthly: 15.49, category: 'Entertainment'}},
  {{name: 'Gym', monthly: 40, category: null}}]}}, F);
out.category = T.category({{backed: true, category: 'Dining', months: [{{month: '2026-06', amount: 310}},
  {{month: '2026-07', amount: null}}, {{month: '2026-08', amount: 290}}]}}, F);
out.energy = T.energy({{backed: true, prices: {{elec: {{area: 'Ohio', price: 19.45, period: '2026-07'}},
  gasoline: {{price: 4.478, period: '2026-09-21'}}}}}}, F);
out.picture = T.picture({{backed: true, claims: [{{category: 'Dining', stance: 'flexible', reason: 'cut_held'}},
  {{category: 'Hobbies', stance: 'unclassified', reason: 'break'}}], said: [{{category: 'Rent', stance: 'protect', said_at: '2026-09-28'}}]}}, F);
out.needs = T.funds({{backed: false, needs: 'Savings funds needs at least one savings fund; you have none yet.'}}, F);
const all = ['funds','recurring','category','energy','picture'].map(k => out[k].lines.join(' ') + ' ' + out[k].source).join(' ');
out.banned = T.banned(all);
console.log(JSON.stringify(out));
"""
    r = subprocess.run([node, '-e', prog], capture_output=True, text=True, timeout=30)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        print('        node stderr:', r.stderr[:400])
        return {}


def run(ctx):
    check, c, HJ = ctx.check, ctx.c, ctx.HJ
    import server
    from core.database import Category, Transaction

    # Evidence for each entry, through sessions and readers whose answers are known.
    ok0, n0 = server._tile_evidence(_S(0), 'gwFundsCard')
    ok1, _ = server._tile_evidence(_S(1), 'gwFundsCard')
    check('s135 savings funds: offered with an active fund; without one, says so', ok1 and not ok0 and 'at least one savings fund' in n0)
    real_trim = server.trim_candidates
    try:
        server.trim_candidates = lambda session, **k: []
        okr0, nr0 = server._tile_evidence(None, 'gwRecurringCard')
        server.trim_candidates = lambda session, **k: [{'name': 'Netflix', 'monthly': 15.49, 'category': 'Fun'}]
        okr1, _ = server._tile_evidence(None, 'gwRecurringCard')
    finally:
        server.trim_candidates = real_trim
    check('s135 recurring charges: offered when a charge repeats; otherwise says what it needs',
          okr1 and not okr0 and 'repeats for at least three months' in nr0)
    real_e = server._energy_on_record
    try:
        server._energy_on_record = lambda session: {}
        oke0, ne0 = server._tile_evidence(None, 'gwEnergyCard')
        server._energy_on_record = lambda session: {'elec': {'price': 19.45}}
        oke1, _ = server._tile_evidence(None, 'gwEnergyCard')
    finally:
        server._energy_on_record = real_e
    check('s135 energy prices: offered only with an EIA price already on record (nothing is fetched to decide)',
          oke1 and not oke0 and 'EIA price on record' in ne0)
    real_w = server.willingness_state
    try:
        server.willingness_state = lambda session: {'readings': [], 'current': []}
        okp0, np0 = server._tile_evidence(None, 'gwPictureCard')
        server.willingness_state = lambda session: {'readings': [{'stance': 'flexible', 'reason': 'cut_held'}], 'current': []}
        okp1, _ = server._tile_evidence(None, 'gwPictureCard')
    finally:
        server.willingness_state = real_w
    check('s135 the working picture: offered with a conclusion or a statement; otherwise says there are none yet',
          okp1 and not okp0 and 'none yet' in np0)

    # One category over time, end to end, on this run's own category (R2).
    _RUN[0] += 1
    name = f'S135 Dining {_RUN[0]}'
    first = date.today().replace(day=1)
    months = [(first - timedelta(days=31 * k)).replace(day=12) for k in (1, 2, 4)]
    with ctx.dbs() as s:
        cat = Category(name=name, type='expense')
        s.add(cat)
        s.flush()
        for d, amt in zip(months[:2], (310.0, 290.0)):
            s.add(Transaction(date=d, description='S135', amount=amt, type='debit', category_id=cat.id))
        s.commit()
        cid = cat.id
    with ctx.dbs() as s:
        ok2, n2 = server._tile_evidence(s, 'cat:' + name)
    check('s135 R2 a category in two recorded months is not yet backed, and says how many it appears in',
          not ok2 and n2 == f'{name} over time needs {name} in at least three recorded months; it appears in 2.')
    with ctx.dbs() as s:
        s.add(Transaction(date=months[2], description='S135', amount=330.0, type='debit', category_id=cid))
        s.commit()
    r = c.post('/api/dashboard/add', headers=HJ, data=json.dumps({'id': 'cat:' + name}))
    lay = ((r.get_json() or {}).get('data') or {})
    check('s135 R2 with three recorded months it is added, under its parameterised id', r.status_code == 200 and 'cat:' + name in lay.get('added', []))
    t = (c.get('/api/dashboard/tile/category', headers=HJ, query_string={'name': name}).get_json() or {}).get('data') or {}
    got = {m['month']: m['amount'] for m in t.get('months', [])}
    gap = (first - timedelta(days=31 * 3)).replace(day=12).strftime('%Y-%m')     # the month between, with no Dining
    check('s135 the tile lists the months the ledger holds, the category\'s spending where it appears - a gap stays a gap',
          bool(t.get('backed')) and got.get(months[0].strftime('%Y-%m')) == 310.0
          and got.get(months[2].strftime('%Y-%m')) == 330.0 and got.get(gap) is None)
    p = (c.get('/api/dashboard/prefs', headers=HJ).get_json() or {}).get('data') or {}
    check('s135 R1 /prefs gives the added category tile its title from the catalogue', p.get('titles', {}).get('cat:' + name) == name + ' over time')
    r1 = c.post('/api/dashboard/add', headers=HJ, data=json.dumps({'id': 'cat:No Such Category Here'}))
    r2 = c.post('/api/dashboard/add', headers=HJ, data=json.dumps({'id': 'cat:'}))
    r3 = c.post('/api/dashboard/add', headers=HJ, data=json.dumps({'id': 'gw:anything'}))
    check('s135 R2 a category the ledger does not have, an empty parameter, or any other shape is refused',
          r1.status_code == 409 and r2.status_code == 400 and r3.status_code == 400)

    # Matching with the ledger's categories.
    m = server.match_tile_request
    C = ['Dining', 'Groceries', 'Gas']
    check('s135 a category the ledger names is the category tile ("my spending on dining by month")',
          (m('my spending on dining by month', C) or {}).get('id') == 'cat:Dining')
    check('s135 a category name does not hijack a better match ("gas prices" is energy prices, not "Gas over time")',
          (m('gas prices', C) or {}).get('id') == 'gwEnergyCard' and (m('show gas over time', C) or {}).get('id') == 'cat:Gas')
    check('s135 each new entry is found by its own words', [(m(q) or {}).get('id') for q in
          ('my savings goals', 'show my subscriptions', 'electricity price', 'what groundwork has concluded')]
          == ['gwFundsCard', 'gwRecurringCard', 'gwEnergyCard', 'gwPictureCard'])

    # K2 / R7: the model matcher.
    real_en, real_ai, real_to = server._ai_is_enabled, server._ai_complete_text, server.MODEL_MATCH_TIMEOUT_S
    real_ready = server._model_ready
    outcomes = {}
    try:
        server._ai_is_enabled = lambda: True
        server._model_ready = lambda: True
        for label, fn in (('exact id', lambda *a, **k: 'gwFundsCard'),
                          ('a sentence', lambda *a, **k: 'Sure! I think gwFundsCard fits.'),
                          ('a parameterised id', lambda *a, **k: 'cat:Dining'),
                          ('an unknown id', lambda *a, **k: 'gwMadeUpCard'),
                          ('an error', lambda *a, **k: (_ for _ in ()).throw(RuntimeError('no model')))):
            server._ai_complete_text = fn
            with c.application.test_request_context():
                outcomes[label] = (server.model_match_tile('how are my rainy day pots doing') or {}).get('id')
        server.MODEL_MATCH_TIMEOUT_S = 0.3
        server._ai_complete_text = lambda *a, **k: (time.sleep(1.5), 'gwFundsCard')[1]
        t0 = time.time()
        with c.application.test_request_context():
            outcomes['slow'] = (server.model_match_tile('how are my rainy day pots doing') or {}).get('id')
        waited = time.time() - t0
        server._ai_is_enabled = lambda: False
        with c.application.test_request_context():
            outcomes['no model'] = (server.model_match_tile('anything') or {}).get('id')
        server._ai_is_enabled = lambda: True
        server._model_ready = lambda: False
        calls = []
        server._ai_complete_text = lambda *a, **k: calls.append(1) or 'gwFundsCard'
        t1 = time.time()
        with c.application.test_request_context():
            outcomes['not running'] = (server.model_match_tile('anything') or {}).get('id')
        outcomes['not running cost'] = (time.time() - t1, len(calls))
    finally:
        server._ai_is_enabled, server._ai_complete_text, server.MODEL_MATCH_TIMEOUT_S = real_en, real_ai, real_to
        server._model_ready = real_ready
    check('s135 K2 the model may pick exactly one catalogue id - and that is a match', outcomes.get('exact id') == 'gwFundsCard')
    check('s135 K2 a sentence, a parameterised id, an unknown id or an error from the model is "none"',
          outcomes.get('a sentence') is None and outcomes.get('a parameterised id') is None
          and outcomes.get('an unknown id') is None and outcomes.get('an error') is None)
    check('s135 R7 a slow model is cut off at the timeout and is "none" - the request is never held',
          outcomes.get('slow') is None and waited < 1.2)
    check('s135 with no local model, only the search matches (local-only AI)', outcomes.get('no model') is None)
    cost, ncalls = outcomes.get('not running cost', (99, 1))
    check('s135 AI switched on but no model running: "none" at once - the model is never asked, nothing waits',
          outcomes.get('not running') is None and ncalls == 0 and cost < 0.5)
    check('s135 the model is only asked when the search finds nothing',
          'match_tile_request(text, cats) or model_match_tile(text)' in ctx.server_src)

    o = _node(ctx.BASE)
    check('s135 node is available to run the tiles\' words (skip the next if not)', o is not None)
    if o is not None:
        check('s135 savings funds: remaining, pace, finish, deadline - and a break with too few months says the date is the plan\'s',
              o['funds']['lines'][0].startswith('Car: $3800.00 still to go; at the $200.00/mo planned it finishes in 19 months, with 18 months to its deadline')
              and "so this is the plan's" in o['funds']['lines'][0] and o['funds']['lines'][1] == 'Trip: funded.')
        check('s135 recurring charges: the count, the monthly total, each at its monthly cost',
              o['recurring']['lines'][0] == '2 recurring charges, about $55.49 a month together:'
              and 'Netflix: $15.49/mo (Entertainment)' in o['recurring']['lines'])
        check('s135 one category over time: a month without it says "none recorded", and the average counts only months it appears',
              'none recorded' in o['category']['lines'][0] and o['category']['lines'][1] == 'Average over the 2 months it appears: $300.00.')
        check('s135 energy prices: each price with its area and period; natural gas with none on record says so',
              'Electricity (Ohio): 19.45' in o['energy']['lines'][0] and 'Natural gas: no EIA price on record yet.' in o['energy']['lines']
              and 'U.S. Energy Information Administration' in o['energy']['source'])
        check('s135 the working picture: readings said as the record\'s, the user\'s word as theirs',
              'Dining: reads as flexible, from your record.' in o['picture']['lines']
              and 'Hobbies: set aside after its spending changed level.' in o['picture']['lines']
              and 'You marked Rent protected on 2026-09-28.' in o['picture']['lines'])
        check('s135 R3 a tile without its evidence shows only what it needs', o['needs']['lines'] == ['Savings funds needs at least one savings fund; you have none yet.'])
        check('s135 no verdict or advice word in any new tile', o['banned'] == [])

    # Item 38 (PAID_OFF_SNAPSHOT.md P4): the net worth tile never draws, or counts as evidence, an all-zero record.
    from core.database import NetWorthSnapshot as _NWS
    with ctx.dbs() as s:
        s.add(_NWS(snapshot_date='1998-01', assets=0, liabilities=0, net_worth=0, notes='Paid off: Old'))
        s.add(_NWS(snapshot_date='1998-01', assets=30000, liabilities=5000, net_worth=25000, notes=''))
        s.add(_NWS(snapshot_date='1998-02', assets=0, liabilities=0, net_worth=0, notes='Paid off: Old2'))
        s.add(_NWS(snapshot_date='1998-03', assets=31000, liabilities=5000, net_worth=26000, notes=''))
        s.commit()
    try:
        r = ctx.c.get('/api/dashboard/tile/net-worth', headers=ctx.HJ)
        pts = [p for p in ((r.get_json() or {}).get('data') or {}).get('points') or [] if p['date'].startswith('1998-')]
        check('s135 item 38 the net worth tile draws one point per month with figures, and none for an all-zero record',
              pts == [{'date': '1998-01', 'net_worth': 25000.0}, {'date': '1998-03', 'net_worth': 26000.0}])
    finally:
        with ctx.dbs() as s:
            s.query(_NWS).filter(_NWS.snapshot_date.like('1998-%')).delete(synchronize_session=False)
            s.commit()
