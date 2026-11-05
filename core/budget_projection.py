"""
Before You Buy's printed future budget (gw 2.0/PRINT_REPORTS.md; Rob 2026-11-05): the cost of a purchase and a possible
monthly budget in later years, with what is budgeted today raised by an assumed inflation rate.

It is arithmetic on the person's own monthly figures and one named assumption, not a forecast:
  - the budget's everyday lines rise by the assumed rate, compounded yearly
  - income stays as it is today: no raise is assumed, because none is known
  - debt minimums and monthly set-asides stay as they are: they are fixed amounts, not prices
  - a loan, lease or financed payment stays fixed and stops at the end of its term; a subscription or other running
    cost rises with everything else
Nothing here is stored.
"""
import math

ASSUMED_INFLATION_PCT = 3.0
YEARS_SHOWN = (0, 1, 2, 3, 5)
PURCHASE_KINDS = ('fixed', 'rises')


def _money(value, name):
    try:
        out = float(value)
    except (TypeError, ValueError):
        raise ValueError(f'{name} must be a number')
    if not math.isfinite(out) or out < 0:
        raise ValueError(f'{name} must be zero or more')
    return out


def _monthly_at(monthly, kind, term_months, year, rate):
    """The purchase's monthly cost in the first month of the given year from now."""
    if term_months and year * 12 >= term_months:
        return 0.0
    return monthly * ((1 + rate) ** year) if kind == 'rises' else monthly


def _paid_in_year(monthly, kind, term_months, year, rate):
    months = 12 if not term_months else max(0, min(12, term_months - year * 12))
    return months * _monthly_at(monthly, kind, term_months, year, rate) if months else 0.0


def project(income, budget, debt_minimums, set_asides, monthly, kind='fixed', term_months=None,
            replaces_monthly=0, rate_pct=ASSUMED_INFLATION_PCT):
    """The rows for the printed table. Raises ValueError on a figure it cannot stand behind."""
    income = _money(income, 'income')
    budget = _money(budget, 'budget')
    debt_minimums = _money(debt_minimums, 'debt minimums')
    set_asides = _money(set_asides, 'set-asides')
    monthly = _money(monthly, 'monthly cost')
    replaces_monthly = _money(replaces_monthly, 'what it replaces')
    rate_pct = _money(rate_pct, 'inflation rate')
    if kind not in PURCHASE_KINDS:
        raise ValueError('kind must be fixed or rises')
    if term_months in (None, '', 0):
        term_months = None
    else:
        term_months = int(_money(term_months, 'term'))
        if term_months < 1:
            term_months = None
    rate = rate_pct / 100.0
    fixed_other = max(0.0, debt_minimums - replaces_monthly)

    rows = []
    for year in YEARS_SHOWN:
        everyday = budget * ((1 + rate) ** year)
        purchase = _monthly_at(monthly, kind, term_months, year, rate)
        without = income - everyday - debt_minimums - set_asides
        with_it = income - everyday - fixed_other - set_asides - purchase
        rows.append({
            'year': year,
            'income': round(income, 2),
            'budget': round(everyday, 2),
            'debt_minimums': round(fixed_other, 2),
            'set_asides': round(set_asides, 2),
            'purchase': round(purchase, 2),
            'left_without': round(without, 2),
            'left_with': round(with_it, 2),
        })

    horizon_years = max(YEARS_SHOWN)
    return {
        'rate_pct': rate_pct,
        'rows': rows,
        'kind': kind,
        'term_months': term_months,
        'first_year_cost': round(_paid_in_year(monthly, kind, term_months, 0, rate), 2),
        'five_year_cost': round(sum(_paid_in_year(monthly, kind, term_months, y, rate) for y in range(horizon_years)), 2),
    }
