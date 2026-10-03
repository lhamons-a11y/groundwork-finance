"""The Investments page and net worth value only what they can price (gw 2.0/INVESTMENT_VALUATION.md, item 35;
Rob 2026-10-03: "I accept V1-V8 as recommended" / "yes i authorize").

    V1  one valuation at its source (_compute_portfolio_positions): no price on record = no value and no gain - never
        the cost, never zero; the summary names what it leaves out
    V3  a lot with no cost basis counts in value, is left out of the gain, and is named
    V4  every price carries its date (manual says so); no threshold
    V5  Net Worth reads cached prices only
    V6  the drift log logs nothing for an allocation with an unpriced holding; the page, Net Worth and the advisor
        prompt each say what they leave out
    V7  history is never rewritten; the first snapshot after the change says valuation changed
"""
import json
import re
import shutil
import subprocess
from datetime import date, datetime, timedelta


def run(ctx):
    check, c, HJ, BASE = ctx.check, ctx.c, ctx.HJ, ctx.BASE
    import server
    from core.database import Account, AppSetting, HistorianEntry, InvestmentLot, NetWorthSnapshot, PriceCache

    now = datetime.utcnow()
    made = {'accounts': [], 'tickers': ['S145VOO', 'S145VXUS', 'S145NEW', 'S145MIX', 'S145MAN']}

    def wipe():
        with ctx.dbs() as s:
            for a in made['accounts']:
                s.query(InvestmentLot).filter_by(account_id=a).delete()
                s.query(Account).filter_by(id=a).delete()
            for t in made['tickers']:
                s.query(PriceCache).filter_by(ticker=t).delete()
            s.query(AppSetting).filter(AppSetting.key.in_(['inv_target_alloc', 'inv_asset_classes_json'])).delete(
                synchronize_session=False)
            s.commit()
        made['accounts'] = []

    def holdings(*rows, prices=None, manual=()):
        """rows: (ticker, shares, basis). prices: {ticker: (price, days_old)}."""
        wipe()
        with ctx.dbs() as s:
            # every other open lot in the gate DB is set aside for the measurement (restored in `finally`)
            acct = Account(name='S145 Brokerage', type='investment', balance=0)
            s.add(acct)
            s.flush()
            made['accounts'].append(acct.id)
            for t, sh, basis in rows:
                s.add(InvestmentLot(account_id=acct.id, ticker=t, shares_original=sh, shares_remaining=sh,
                                    cost_basis_per_share=basis, purchase_date=date(2024, 3, 1)))
            for t, (price, days) in (prices or {}).items():
                s.add(PriceCache(ticker=t, price=price, last_updated=now - timedelta(days=days), is_manual=t in manual))
            s.commit()
            return acct.id

    def figures(acct):
        with ctx.dbs() as s:
            return server._compute_portfolio_positions(s, account_id=acct, skip_refresh=True)

    with ctx.dbs() as s:
        others = [l.id for l in s.query(InvestmentLot).filter_by(is_closed=False).all()]
        for l in s.query(InvestmentLot).filter(InvestmentLot.id.in_(others)).all():
            l.is_closed = True
        s.commit()
    try:
        # Iv1 - the measured portfolio (INVESTMENT_VALUATION.md s1)
        a = holdings(('S145VOO', 40, 410.0), ('S145VXUS', 120, 58.0), ('S145NEW', 15, 0.0),
                     prices={'S145VOO': (512.30, 1), 'S145NEW': (30.0, 2)})
        pos, summ = figures(a)
        by = {p['ticker']: p for p in pos}
        check('s145 Iv1 V1 the value is what is priced: $20,942.00, not $27,902.00 (VXUS is never valued at its cost)',
              summ['total_market_value'] == 20942.0)
        check('s145 Iv1 V1/V3 the gain is on lots with a cost basis: +$4,092.00 (+24.95%), not +$4,542.00',
              summ['total_gain'] == 4092.0 and summ['total_gain_pct'] == 24.95 and summ['gain_basis'] == 16400.0)
        check('s145 Iv1 V1 the unpriced holding has no price, no value and no gain - not its cost, not zero - and is named',
              by['S145VXUS']['current_price'] is None and by['S145VXUS']['market_value'] is None
              and by['S145VXUS']['unrealized_gain'] is None and by['S145VXUS']['priced'] is False
              and summ['unpriced'] == [{'ticker': 'S145VXUS', 'shares': 120.0, 'account_id': a}])
        check('s145 Iv1 V3 the basis-0 lot is in the value, out of the gain, and named',
              by['S145NEW']['market_value'] == 450.0 and by['S145NEW']['unrealized_gain'] is None
              and by['S145NEW']['no_basis_shares'] == 15.0 and summ['no_basis'] == [{'ticker': 'S145NEW', 'shares': 15.0}])
        check('s145 Iv1 V4 every price carries its date; the summary gives the range',
              by['S145VOO']['price_date'] == (now - timedelta(days=1)).date().isoformat()
              and summ['prices_from'] == (now - timedelta(days=2)).date().isoformat()
              and summ['prices_to'] == (now - timedelta(days=1)).date().isoformat())
        check('s145 Iv1 holdings with no price are listed last, not sorted in at a made-up value',
              [p['ticker'] for p in pos][-1] == 'S145VXUS')

        # Iv2 - every holding priced with a basis: today's figures, unchanged
        a = holdings(('S145VOO', 40, 410.0), prices={'S145VOO': (512.30, 0)})
        _, s2 = figures(a)
        check('s145 Iv2 all priced and with a basis: the figures are as before',
              s2['total_market_value'] == 20492.0 and s2['total_gain'] == 4092.0 and s2['unpriced'] == [] and s2['no_basis'] == [])

        # Iv3 - nothing priced
        a = holdings(('S145VXUS', 120, 58.0), ('S145VOO', 40, 410.0))
        p3, s3 = figures(a)
        check('s145 Iv3 nothing priced: no gain, every holding named, and no value from cost',
              s3['total_market_value'] == 0 and s3['total_gain'] is None and s3['total_gain_pct'] is None
              and len(s3['unpriced']) == 2 and all(p['market_value'] is None for p in p3))

        # Iv4 - only basis-0 lots; a mixed position
        a = holdings(('S145NEW', 15, 0.0), prices={'S145NEW': (30.0, 0)})
        _, s4 = figures(a)
        check('s145 Iv4 only lots with no cost basis: the value is shown, the gain is not computed',
              s4['total_market_value'] == 450.0 and s4['total_gain'] is None)
        a = holdings(('S145MIX', 10, 100.0), ('S145MIX', 5, 0.0), prices={'S145MIX': (120.0, 0)})
        p5, s5 = figures(a)
        check('s145 a position with one lot with a basis and one without: value of all 15 shares, gain on the 10 only',
              p5[0]['market_value'] == 1800.0 and p5[0]['unrealized_gain'] == 200.0 and p5[0]['no_basis_shares'] == 5.0
              and p5[0]['unrealized_pct'] == 20.0)

        # Iv5 / Iv6 - a manual price says so; an old price is valued and dated, with no verdict
        a = holdings(('S145MAN', 2, 50.0), ('S145VOO', 1, 400.0), prices={'S145MAN': (60.0, 0), 'S145VOO': (500.0, 95)},
                     manual=('S145MAN',))
        p6, s6 = figures(a)
        b6 = {p['ticker']: p for p in p6}
        check('s145 Iv5 a manual price is valued and says it was set by the user', b6['S145MAN']['price_manual'] is True
              and s6['manual_prices'] == ['S145MAN'])
        check('s145 Iv6 a price from three months ago is valued, with its date - no threshold, no verdict',
              b6['S145VOO']['market_value'] == 500.0
              and b6['S145VOO']['price_date'] == (now - timedelta(days=95)).date().isoformat())

        # Iv8 - the drift log
        a = holdings(('S145VOO', 40, 410.0), ('S145VXUS', 120, 58.0), prices={'S145VOO': (512.30, 0)})
        with ctx.dbs() as s:
            s.add(AppSetting(key='inv_target_alloc', value=json.dumps({'us_equity': 70, 'international_equity': 30})))
            s.add(AppSetting(key='inv_asset_classes_json', value=json.dumps({'S145VOO': 'us_equity',
                                                                              'S145VXUS': 'international_equity'})))
            s.commit()
            before = s.query(HistorianEntry).filter_by(event_category='investment_allocation_drift').count()
            server._log_investment_allocation_drift(s)
            s.commit()
            after_unpriced = s.query(HistorianEntry).filter_by(event_category='investment_allocation_drift').count()
            s.add(PriceCache(ticker='S145VXUS', price=63.0, last_updated=now))
            s.commit()
            server._log_investment_allocation_drift(s)
            s.commit()
            after_priced = s.query(HistorianEntry).filter_by(event_category='investment_allocation_drift').count()
        check('s145 Iv8 V6 an allocation with an unpriced holding is not logged as drift (it would be read as evidence)',
              after_unpriced == before)
        check('s145 Iv8 ...and once every holding is priced, the drift is logged as before', after_priced == before + 2)

        # Iv10 - snapshots: the note is kept; the first after the change says valuation changed, once
        month = date.today().strftime('%Y-%m')
        with ctx.dbs() as s:
            s.query(AppSetting).filter_by(key='inv_valuation_v35_noted').delete()
            old = s.query(NetWorthSnapshot).filter(NetWorthSnapshot.snapshot_date != month).all()
            old_rows = sorted((o.id, o.net_worth, o.notes) for o in old)
            s.commit()
        r1 = (c.post('/api/net-worth/snapshot', headers=HJ, data=json.dumps(
            {'force': True, 'assets': 25000, 'liabilities': 1000, 'note': 'Investments leave out S145VXUS: no price on record.'}))
              .get_json() or {}).get('data', {}).get('snapshot', {})
        r2 = (c.post('/api/net-worth/snapshot', headers=HJ, data=json.dumps(
            {'force': True, 'assets': 25000, 'liabilities': 1000})).get_json() or {}).get('data', {}).get('snapshot', {})
        with ctx.dbs() as s:
            old2 = sorted((o.id, o.net_worth, o.notes) for o in
                          s.query(NetWorthSnapshot).filter(NetWorthSnapshot.snapshot_date != month).all())
        check('s145 Iv10 V6 a snapshot keeps the page\'s note of what its investments leave out',
              'Investments leave out' in (r1.get('notes') or ''))
        # r2 re-takes the same month: that month keeps its note (it marks the change), and the note is never added twice
        with ctx.dbs() as s:
            noted = bool(server._get_setting(s, 'inv_valuation_v35_noted'))
        check('s145 Iv10 V7 the first snapshot after the change says valuation changed - once, and not added again',
              'Investment valuation changed on' in (r1.get('notes') or '') and noted
              and (r2.get('notes') or '').count('Investment valuation changed') == 1)
        check('s145 Iv10 V7 earlier snapshots are untouched', old2 == old_rows)
    finally:
        wipe()
        with ctx.dbs() as s:
            for l in s.query(InvestmentLot).filter(InvestmentLot.id.in_(others)).all():
                l.is_closed = False
            s.commit()

    # V5 and the page - in the source the user runs
    app = ctx.app_src
    check('s145 Iv7 V5 Net Worth reads cached prices only (skip_refresh), so opening it never fetches',
          "API.get('/api/investments/positions?skip_refresh=true')" in app
          and "API.get('/api/investments/positions').then" not in app)
    check('s145 the page never shows an unpriced holding\'s cost as its price, or a gain nobody computed',
          "'No price on record \\u2014 set a price'" in app and "'Not valued'" in app and "'Not shown'" in app
          and "${fmt(p.current_price||0)}/share" not in app)
    check('s145 V6 the target-allocation card never says "within tolerance" on an incomplete total',
          'Allocation against your targets needs every holding priced.' in app)
    check('s145 V6 found in the browser: no concentration share of an incomplete total, and no $0 fee for an unpriced '
          'holding', 'Concentration needs every holding priced.' in app
          and "&& p.market_value !== null && p.market_value !== undefined);" in app.split('function _renderFeeAnalysis')[1][:500])
    check('s145 Iv9 V6 the advisor prompt carries only computed figures and what they leave out',
          'Not valued, left out of every figure above' in app and 'gain not computed: no cost basis on record' in app
          and "p.unrealized_pct.toFixed(1)}%)`\n  );" not in app.split('async function _invLaunchAdvisorAI')[1][:600])
    check('s145 V2 Net Worth names what its investments figure leaves out, beside the field and the headline',
          'leaves out ${x}: no price on record. Set a price on the Investments page.' in app and "nwGapEl.id = 'nwInvGap'" in app)
    check('s145 V2 a figure saved earlier is never silently replaced: the portfolio\'s value is offered, the user decides',
          "Your portfolio's priced value is" in app and 'onclick="_nwUsePortfolioValue(event)"' in app)
    check('s145 found in the browser: a saved figure equal to the portfolio\'s priced value is the portfolio\'s, so it '
          'still names what it leaves out after a reload',
          'const same = field.value !== \'\' && Math.abs((parseFloat(field.value) || 0) - value) < 0.01;' in app
          and "parseFloat(field.value)===prev || same) {" in app)
    check('s145 V7 a snapshot\'s note is shown on its point in the chart', 'd.notes ? `<title>' in app)
    check('s145 found in the browser: the allocation donut gives no share to a holding with no price, and names it',
          "if (p.market_value === null || p.market_value === undefined) return;   // item 35: no price, no share" in app
          and 'Of priced holdings only.' in app)
    check('s145 the page has its valuation note', 'id="invValuationNote"' in ctx.html_src)

    node = shutil.which('node')
    check('s145 node is available to run the words (skip the next if not)', bool(node))
    if not node:
        return
    src = '\n'.join(re.search(r'\nfunction ' + n + r'\(.*?\n}\n', app, re.S).group(0)
                    for n in ('_invDate', '_invShares', '_invExclusions'))
    prog = src + """
const s = {unpriced: [{ticker: 'VXUS', shares: 120}], no_basis: [{ticker: 'NEWCO', shares: 15}]};
console.log(JSON.stringify([_invExclusions(s), _invExclusions({}), _invShares(1), _invShares(2.5)]));
"""
    r = subprocess.run([node, '-e', prog], capture_output=True, text=True, encoding='utf-8', timeout=30)
    try:
        o = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:                                   # noqa: BLE001 - reported below
        o = [{}, {}, '', '']
        print('        node:', r.stderr[:300])
    check('s145 the words name each holding left out, with its shares',
          o[0] == {'unpriced': 'No price on record: VXUS · 120 shares',
                   'noBasis': 'No cost basis on record: NEWCO · 15 shares', 'unpricedNames': 'VXUS · 120 shares'}
          and o[1] == {'unpriced': '', 'noBasis': '', 'unpricedNames': ''} and o[2] == '1 share' and o[3] == '2.5 shares')
