"""Fee drag in one unit (found in item 35's browser check, 2026-10-03; Rob: "Do this task here").

The page reads `expense_ratio` as a fraction of the value a year. The defaults were written in percent, so VOO showed
"3.00% ER" and $614.76/yr on $20,492 - about 100x the real ~$6.15. The prompt asked for a percent but stored an entry
<= 1 as typed (0.03 -> 3%). Now the user's entry is kept as the percent they typed, with its unit; the page gets a
fraction; a value saved the old way is used only where its unit can be proven, and otherwise asks to be confirmed.
"""
import json
from datetime import date, datetime


def run(ctx):
    check, c, HJ = ctx.check, ctx.c, ctx.HJ
    import server
    from core.database import Account, AppSetting, InvestmentLot, PriceCache

    f = server._expense_ratio_for
    check('s146 the defaults are percent, handed over as a fraction: VOO 0.03% -> 0.0003',
          f('VOO', {}, {}, {'VOO': 0.03}) == (0.0003, 'default', None))
    check('s146 a saved entry in percent is used as such: 0.20% -> 0.002, yours',
          f('QQQ', {'QQQ': 0.2}, {}, {}) == (0.002, 'yours', None))
    check('s146 an old entry whose unit is provable is read as the percent it was typed in (<= 0.01, or > 0.03)',
          f('A', {}, {'A': 0.005}, {})[0] == 0.00005 and f('B', {}, {'B': 0.5}, {})[0] == 0.005)
    check('s146 an old entry that could be either unit is not guessed: no figure, and it asks',
          f('C', {}, {'C': 0.02}, {'C': 0.04}) == (None, None, 0.02))
    check('s146 a percent entry wins over an old one and over the default',
          f('D', {'D': 0.1}, {'D': 0.02}, {'D': 0.03}) == (0.001, 'yours', None))

    made = {}
    with ctx.dbs() as s:
        for k in ('inv_expense_ratios_json', 'inv_expense_ratios_pct_json'):
            s.query(AppSetting).filter_by(key=k).delete()
        acct = Account(name='S146 Brokerage', type='investment', balance=0)
        s.add(acct)
        s.flush()
        made['acct'] = acct.id
        s.add(PriceCache(ticker='VOO', price=512.30, last_updated=datetime.now())) if not s.get(PriceCache, 'VOO') else None
        s.add(InvestmentLot(account_id=acct.id, ticker='VOO', shares_original=40, shares_remaining=40,
                            cost_basis_per_share=410.0, purchase_date=date(2024, 3, 1)))
        s.add(InvestmentLot(account_id=acct.id, ticker='S146AMB', shares_original=1, shares_remaining=1,
                            cost_basis_per_share=10.0, purchase_date=date(2024, 3, 1)))
        s.add(AppSetting(key='inv_expense_ratios_json', value=json.dumps({'S146AMB': 0.02})))
        s.commit()
        voo_price = s.get(PriceCache, 'VOO').price
    try:
        with ctx.dbs() as s:
            pos, _ = server._compute_portfolio_positions(s, account_id=made['acct'], skip_refresh=True)
        by = {p['ticker']: p for p in pos}
        fee = by['VOO']['market_value'] * by['VOO']['expense_ratio']
        check('s146 VOO\'s annual fee is value x 0.03%: about $6.15 on $20,492 - not $614.76',
              by['VOO']['expense_ratio'] == 0.0003 and abs(fee - 40 * voo_price * 0.0003) < 0.01
              and (voo_price != 512.30 or abs(fee - 6.15) < 0.01))
        check('s146 the ambiguous old entry is carried for the page to ask about, and has no figure',
              by['S146AMB']['expense_ratio'] is None and by['S146AMB']['expense_ratio_unconfirmed'] == 0.02)

        bad = c.patch('/api/investments/expense-ratios', headers=HJ, data=json.dumps({'S146AMB': 0.0002}))
        check('s146 the old unit-less body is refused (it is how 0.03% became 3%)', bad.status_code == 400)
        r = c.patch('/api/investments/expense-ratios', headers=HJ,
                    data=json.dumps({'unit': 'percent', 'ratios': {'s146amb': 0.02}}))
        g = (c.get('/api/investments/expense-ratios', headers=HJ).get_json() or {}).get('data') or {}
        with ctx.dbs() as s:
            pos2, _ = server._compute_portfolio_positions(s, account_id=made['acct'], skip_refresh=True)
            legacy = json.loads(server._get_setting(s, 'inv_expense_ratios_json').value)
        amb = {p['ticker']: p for p in pos2}['S146AMB']
        check('s146 confirming in percent saves it as typed and retires the old entry',
              r.status_code == 200 and g.get('ratios', {}).get('S146AMB') == 0.02 and 'S146AMB' not in legacy
              and amb['expense_ratio'] == 0.0002 and amb['expense_ratio_unconfirmed'] is None)
        out = [c.patch('/api/investments/expense-ratios', headers=HJ,
                       data=json.dumps({'unit': 'percent', 'ratios': {'X': v}})).status_code for v in (-1, 101, 'abc')]
        check('s146 a percent outside 0-100, or not a number, is refused', out == [400, 400, 400])
    finally:
        with ctx.dbs() as s:
            s.query(InvestmentLot).filter_by(account_id=made['acct']).delete()
            s.query(Account).filter_by(id=made['acct']).delete()
            for k in ('inv_expense_ratios_json', 'inv_expense_ratios_pct_json'):
                s.query(AppSetting).filter_by(key=k).delete()
            s.commit()

    app = ctx.app_src
    check('s146 the page saves what the user typed, in percent, with its unit (no "<= 1 means a fraction" rule)',
          "{ unit: 'percent', ratios: { [ticker]: val } }" in app and 'val > 1 ? val / 100 : val' not in app)
    check('s146 the fee flags compare fractions: over 1% red, over 0.5% gold', 'er > 0.01' in app and 'er > 0.005' in app
          and 'feeFlag = er > 1.0' not in app)
    check('s146 an unconfirmed ratio is named, left out of the fee, and the prompt explains both readings',
          'Confirm ER' in app and 'expense ratio needs confirming' in app
          and 'before Groundwork said which unit it meant' in app)
