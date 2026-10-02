"""A budget row's amount for this month (gw 2.0/BUDGET_MONTH_AMOUNT.md, item 26's totals pass; Rob, 2026-10-02).

Two figures per row, never one overwritten (M1):
    amount         what the user saved - the only figure any write path ever sends
    month_amount   what this month's totals use: the saved amount, unless the user follows an estimate for that
                   row's kind AND the estimate has a figure for the bill paid this month

Nothing writes month_amount; it is derived on every read. When there is no figure (the estimate needs something, the
household's answers rule it out, or the bill paid this month is not one the estimate covers), the saved amount is
used and the reason is carried, so the row can say why (M5: absence is not zero).
"""


def bill_month(this_month, lag):
    """The service month whose bill is paid in `this_month` ('YYYY-MM'), for a bill paid `lag` months later."""
    y, m = (int(x) for x in this_month.split('-'))
    m -= int(lag)
    while m < 1:
        y, m = y - 1, m + 12
    return f'{y:04d}-{m:02d}'


def pick_estimate(est_out, kind, this_month):
    """From an item 26 estimate route's output, the estimate dict for the bill paid this month, or (None, why)."""
    if not est_out:
        return None, 'the estimate could not be worked out'
    if est_out.get('not_applicable'):
        return None, est_out['not_applicable']
    if kind == 'gasoline':                                  # fill-ups are paid when bought: a typical month, today's price
        e = est_out.get('estimate')
        return (e, None) if e and e.get('method') not in (None, 'none') else (None, _needs(est_out, e))
    want = bill_month(this_month, est_out.get('lag', 1))
    for key in ('estimate', 'previous'):
        e = est_out.get(key)
        if e and e.get('month') == want:
            return (e, None) if e.get('method') not in (None, 'none') else (None, _needs(est_out, e))
    return None, (f"the bill paid this month is for {want}'s service, which the estimate does not cover")


def _needs(est_out, e):
    n = (e or {}).get('needs') or est_out.get('needs')
    return f'the estimate needs {n}' if n else 'the estimate has no figure yet'


def month_amount(saved, followed, est):
    """M1: (amount for this month, source 'estimate' | 'saved'). `est` is the picked estimate dict or None."""
    saved = float(saved or 0)
    if followed and est and est.get('amount') is not None:
        return round(float(est['amount']), 2), 'estimate'
    return round(saved, 2), 'saved'
