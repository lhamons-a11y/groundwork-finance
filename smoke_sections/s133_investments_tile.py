"""An Investments tile on the dashboard (`gw 2.0/INVESTMENTS_TILE.md`, item 29, ruled 2026-09-30: all six).

    I1  cached prices only, each with its date - opening the dashboard fetches no price (In11)
    I2  a position with no price is named and left out of value and gain - never valued at cost (In3)
    I3  a lot with no purchase price counts in value and is named and left out of the gain (In4)
    I4  value, unrealized gain, realized this year (short / long), allocation only against a set target
    I5  investment accounts with a balance and no holdings listed as a fact (In10)
    I6  a seventh tile, present only when investments are on record, user-arranged (In1, In13)
    I7  2.0 through the seam; the words pass the BANNED lexicon (In12)
"""
import json
import shutil
import subprocess
from datetime import date, datetime

_RUN = [0]


def _node(base):
    node = shutil.which('node')
    if not node:
        return None
    path = str(base.joinpath('static/js/teaching/tiletext.js')).replace('\\', '/')
    prog = f"""
const T = require({json.dumps(path)});
const F = {{money: n => '$' + Number(n).toFixed(2), date: s => s}};
const d = {{present: true, value: 1300, prices_from: '2026-09-22', prices_to: '2026-09-29', manual_prices: ['ZZZ'],
  unrealized: {{gain: 100, pct: 10}}, unpriced: [{{ticker: 'BBB', shares: 3}}], no_basis: [{{ticker: 'CCC', shares: 4}}],
  realized_this_year: {{total: 30, short: 0, long: 30, unstated: 1, lots: 2}}, year: 2026,
  allocation: [{{asset_class: 'us_equity', target_pct: 60, actual_pct: 72.5}}], allocation_unclassified: [],
  balance_only: [{{account: '401(k)', balance: 62400}}]}};
const out = {{}};
out.t = T.investments(d, F);
out.loss = T.investments(Object.assign({{}}, d, {{unrealized: {{gain: -40, pct: -4}}}}), F).lines[1];
out.absent = T.investments({{present: false}}, F);
out.no_target = T.investments(Object.assign({{}}, d, {{allocation: null}}), F).lines.some(l => l.indexOf('target') >= 0);
out.unclassified = T.investments(Object.assign({{}}, d, {{allocation: [{{asset_class: 'us_equity', target_pct: 60, actual_pct: 0}}],
  allocation_unclassified: [{{ticker: 'VOO', pct: 73.1}}]}}), F).lines.find(l => l.indexOf('target') >= 0);
out.banned = T.banned(out.t.lines.join(' ') + ' ' + out.t.source + ' ' + out.loss);
console.log(JSON.stringify(out));
"""
    r = subprocess.run([node, '-e', prog], capture_output=True, text=True, timeout=30)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        print('        node stderr:', r.stderr[:400])
        return {}


def run(ctx):
    check = ctx.check
    base = ctx.BASE
    o = _node(base)
    check('s133 node is available to run the tile\'s words (skip the next if not)', o is not None)
    if o is not None:
        L = o['t']['lines']
        check('s133 I1 value at prices with their dates, and a hand-entered price said to be one',
              L[0] == 'Value: $1300.00, at prices from 2026-09-22 to 2026-09-29. Hand-entered price: ZZZ.')
        check('s133 I4 unrealized gain on holdings with a recorded purchase price; a loss said as a loss',
              L[1] == 'Unrealized gain: $100.00 (10.0%) on holdings with a recorded purchase price.'
              and o['loss'] == 'Unrealized loss: $40.00 (4.0%) on holdings with a recorded purchase price.')
        check('s133 In3 I2 a holding with no price is named and not included', 'Not included: BBB - no price on record.' in L)
        check('s133 In4 I3 shares with no purchase price: their gain not stated, named',
              'Gain not stated for 4 CCC shares: no purchase price recorded.' in L)
        check('s133 In7 realized this year, long / short, and sales with no gain recorded said so',
              'Realized in 2026: $30.00 (long-term $30.00); 1 sale with no gain recorded.' in L)
        check('s133 In8 / In9 allocation against the target as facts, and no line without a target',
              'Against your target: us equity 72.5% (target 60%).' in L and o['no_target'] is False)
        check('s133 found in the page run: a holding with no asset class is named with its share, never read as 0%',
              o['unclassified'] == 'Against your target: us equity 0% (target 60%); not yet assigned a class: VOO 73.1%.')
        check('s133 In10 I5 an account with a balance and no holdings is listed as a fact',
              'Also on record: 401(k), $62400.00 balance - holdings not recorded, so not in the figures above.' in L)
        check('s133 In1 no investments on record: no tile at all', o['absent'] is None)
        check('s133 In12 no verdict or advice word in the tile, and its source line is there',
              o['banned'] == [] and 'prices are not refreshed here' in o['t']['source'])

    # The server, end to end on the real database - asserted on this run's own tickers and account.
    import server
    from core.database import InvestmentLot, PriceCache, Account
    _RUN[0] += 1
    n = _RUN[0]
    a, b, c, d = f'S133A{n}', f'S133B{n}', f'S133C{n}', f'S133D{n}'
    with ctx.dbs() as s:
        acct = Account(name=f'S133 Brokerage {n}', type='investment', balance=0)
        bal_only = Account(name=f'S133 401k {n}', type='investment', balance=62400)
        s.add_all([acct, bal_only])
        s.flush()
        s.add(PriceCache(ticker=a, price=110.0, last_updated=datetime(2026, 9, 29, 16, 0)))
        s.add(PriceCache(ticker=c, price=50.0, last_updated=datetime(2026, 9, 22, 16, 0), is_manual=True))
        s.add(InvestmentLot(account_id=acct.id, ticker=a, shares_original=10, shares_remaining=10,
                            cost_basis_per_share=100.0, purchase_date=date(2025, 1, 5)))
        s.add(InvestmentLot(account_id=acct.id, ticker=b, shares_original=3, shares_remaining=3,
                            cost_basis_per_share=20.0, purchase_date=date(2025, 2, 5)))
        s.add(InvestmentLot(account_id=acct.id, ticker=c, shares_original=4, shares_remaining=4,
                            cost_basis_per_share=0.0, purchase_date=date(2025, 3, 5)))
        s.commit()
        before = server.investments_tile(s)
        page_pos, page = server._compute_portfolio_positions(s, skip_refresh=True)
    with ctx.dbs() as s:
        s.add(InvestmentLot(account_id=acct.id, ticker=d, shares_original=1, shares_remaining=0, cost_basis_per_share=10,
                            purchase_date=date(2024, 1, 5), is_closed=True, closed_date=date.today(),
                            sell_price_per_share=40, realized_gain=30.0, holding_period_days=400))
        s.commit()
        after = server.investments_tile(s)

    import price_engine
    calls = []
    real = price_engine.refresh_stale_prices
    try:
        price_engine.refresh_stale_prices = lambda *x, **k: calls.append(1) or {}
        with ctx.dbs() as s:
            server.investments_tile(s)
    finally:
        price_engine.refresh_stale_prices = real
    check('s133 In11 I1 building the tile fetches no price (refresh never called)', calls == [])

    unpriced = {u['ticker'] for u in before['unpriced']}
    nob = {x['ticker']: x['shares'] for x in before['no_basis']}
    check('s133 In3 I2 on the server: the unpriced holding is named and adds nothing to the value',
          b in unpriced and b not in nob)
    check('s133 In4 I3 on the server: the no-basis lot is named, its shares counted',
          nob.get(c) == 4)
    check('s133 In2 the tile is present, with value, an as-of range covering the prices, and the hand-entered one named',
          before['present'] and before['value'] >= 1100 + 200 and c in before['manual_prices']
          and before['prices_from'] <= '2026-09-22' and before['prices_to'] >= '2026-09-29')
    check('s133 In7 a sale closed this year adds its realized gain as long-term',
          after['realized_this_year']['lots'] == before['realized_this_year']['lots'] + 1
          and round(after['realized_this_year']['total'] - before['realized_this_year']['total'], 2) == 30.0
          and round(after['realized_this_year']['long'] - before['realized_this_year']['long'], 2) == 30.0)
    check('s133 In10 I5 on the server: the investment account with a balance and no holdings is listed',
          any(x['account'] == f'S133 401k {n}' and x['balance'] == 62400 for x in before['balance_only'])
          and not any(x['account'] == f'S133 Brokerage {n}' for x in before['balance_only']))
    # Item 35 V1 (INVESTMENT_VALUATION.md): one valuation - the tile reads the summary the Investments page and Net
    # Worth read, so the two screens can no longer disagree about the same holdings.
    check('s133 item 35 the tile and the Investments page / Net Worth say the same value, gain and exclusions',
          before['value'] == page['total_market_value']
          and (before['unrealized'] or {}).get('gain') == page['total_gain']
          and sorted(u['ticker'] for u in before['unpriced']) == sorted(u['ticker'] for u in page['unpriced'])
          and sorted(u['ticker'] for u in before['no_basis']) == sorted(u['ticker'] for u in page['no_basis']))
    tile_src = ctx.server_src.split('def investments_tile(', 1)[1].split('\ndef ', 1)[0]
    check('s133 item 35 the tile no longer re-derives the exclusions at lot level',
          "summary['unpriced']" in tile_src and "for lot in p.get('lots')" not in tile_src)
    r = ctx.c.get('/api/dashboard/investments', headers=ctx.HJ)
    check('s133 the tile\'s endpoint answers', r.status_code == 200 and 'present' in ((r.get_json() or {}).get('data') or {}))

    r = ctx.c.put('/api/dashboard/layout', headers=ctx.HJ, data=json.dumps(
        {'order': ['dashInvestmentsCard'], 'pinned': ['dashInvestmentsCard'], 'hidden': []}))
    check('s133 In13 I6 the seventh tile is arrangeable like the rest (pin / hide / reorder)', r.status_code == 200)
    dash = base.joinpath('static/js/teaching/dashboard.js').read_text(encoding='utf-8')
    tiles = base.joinpath('static/js/teaching/tiles.js').read_text(encoding='utf-8')
    check('s133 I6 the card exists hidden and is shown only when investments are on record',
          "inv.style.display = 'none'" in dash and "if (!t) { card.style.display = 'none'" in tiles)
    check('s133 I1 the server reads positions without refreshing prices',
          '_compute_portfolio_positions(session, skip_refresh=True)' in
          ctx.server_src.split('def investments_tile(', 1)[1].split('\ndef ', 1)[0])
    check('s133 I7 1.x untouched: app.js and index.html know nothing of the tile',
          'dashInvestmentsCard' not in ctx.app_src
          and 'dashInvestmentsCard' not in base.joinpath('static/index.html').read_text(encoding='utf-8'))
