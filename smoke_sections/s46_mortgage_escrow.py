"""V3: a mortgage's escrow never reduces the balance, so projections use principal & interest.

1.x treated every debt payment as principal and interest, so a mortgage payment
that included escrow (property tax, insurance), PMI or fees projected payoff
early. Now a Mortgage debt type calculates principal & interest from the
balance, APR and maturity date - as the extra-payment tool already does -
projections use it, and the payoff budget leaves the escrow share out (it goes
to taxes and insurance, not debt). Budgets and debt-to-income keep the whole
payment. Without the figures, the whole payment is used, as before.
"""
from datetime import date
from pathlib import Path
from types import SimpleNamespace


def _months_ahead(n):
    t = date.today()
    y, m = divmod(t.month - 1 + n, 12)
    return date(t.year + y, m + 1, 1)


def run(ctx):
    check = ctx.check
    from core.consequence import Card, simulate_payoff
    from core.database import DebtAccount
    from server import _consequence_inputs, _mortgage_split, _payoff_minimum, db_session

    def debt(**kw):
        base = dict(debt_type='mortgage', current_balance=187000.0, begin_balance=187000.0,
                    interest_rate=6.25, minimum_payment=1420.0, end_date=_months_ahead(300))
        base.update(kw)
        return SimpleNamespace(**base)

    months = 300
    r = 6.25 / 1200
    expected_pi = 187000 * r / (1 - (1 + r) ** -months)

    s = _mortgage_split(debt())
    check('V3: a mortgage with balance, APR and maturity date splits its payment',
          s['known'] and abs(s['pi'] - round(expected_pi, 2)) < 0.01
          and abs(s['other'] - round(1420 - expected_pi, 2)) < 0.01)
    check('and projections use the principal & interest, not the whole payment',
          abs(_payoff_minimum(debt()) - round(expected_pi, 2)) < 0.01)

    sim = simulate_payoff([Card(balance=187000.0, rate=6.25, minimum=s['pi'])], s['pi'])
    check('a mortgage simulated at its calculated P&I pays off at its maturity date, not early',
          sim is not None and abs(sim['months'] - months) <= 1)
    early = simulate_payoff([Card(balance=187000.0, rate=6.25, minimum=1420.0)], 1420.0)
    check('whereas the whole payment (the old behaviour) projected it years early',
          early is not None and early['months'] < months - 24)

    check('a loan or card is untouched: its whole payment is used',
          _mortgage_split(debt(debt_type='loan')) is None
          and _payoff_minimum(debt(debt_type='loan')) == 1420.0)
    check('a mortgage without a maturity date falls back to the whole payment',
          not _mortgage_split(debt(end_date=None))['known']
          and _payoff_minimum(debt(end_date=None)) == 1420.0)
    check('a mortgage with an unknown APR falls back too (V6: unknown stays unknown)',
          _payoff_minimum(debt(interest_rate=None)) == 1420.0)
    low = _mortgage_split(debt(minimum_payment=900.0))
    check('a payment at or below the calculated P&I is all P&I, with nothing counted as escrow',
          low['known'] and low['pi'] == 900.0 and low['other'] == 0.0)

    # The server's engine inputs: the mortgage's card uses P&I, and the budget leaves out its escrow.
    with db_session() as sess:
        _, budget_before, _, _ = _consequence_inputs(sess)
        m = DebtAccount(name='V3 Mortgage', debt_type='mortgage', current_balance=187000,
                        begin_balance=187000, interest_rate=6.25, minimum_payment=1420,
                        end_date=_months_ahead(300), is_active=True)
        sess.add(m); sess.commit()
        cards, budget_after, _, _ = _consequence_inputs(sess)
        card = next((c for c in cards if c.name == 'V3 Mortgage'), None)
        check('the engine gets the mortgage at its principal & interest',
              card is not None and abs(card.minimum - round(expected_pi, 2)) < 0.01)
        check('and the payoff budget leaves out the escrow share, so it is not handed to other debts',
              abs((budget_before - budget_after) - round(1420 - expected_pi, 2)) < 0.01)
        sess.delete(m); sess.commit()

    app_js = (Path(__file__).resolve().parent.parent / 'static' / 'js' / 'app.js').read_text(encoding='utf-8')
    check('the client builds engine cards from principal & interest',
          app_js.count('_payoffPayment(c) || 25') >= 4 and 'minimum:  Math.max(1, parseFloat(c.minimum) || 25),' not in app_js)
    check('and takes the escrow share of the cards it simulates out of the budget',
          'budget = budget - (cards || []).reduce((s, c) => s + (c.non_principal || 0), 0);' in app_js)
    check('Mortgage is a type the user can choose, and its row shows the split',
          'data-type="mortgage">Mortgage</button>' in app_js and 'function _mortgageSplitHTML' in app_js)
    dti = app_js[app_js.index('function calcDTI'):][:1500]
    check('debt-to-income still uses the whole payment - it is what leaves the account',
          '_payoffPayment' not in dti)
