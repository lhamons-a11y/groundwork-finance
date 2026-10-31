"""Item 115 stage 1 (gw 2.0/ASK_FOR_A_REPORT.md; Rob 2026-10-31: C1-C11 accepted; C3 "Accept, all 40 at once"): a
report is a stack of prebuilt sections. Each section is a shape crossed with a subject over a period (P1), drawn by
Groundwork from item 114's lookups and the record's own rows - every figure is Groundwork's (H22); the model has no
part here. The section's shape picks its chart (P14); the style only says whether visuals are shown (P13).

Section ids are shape.subject, Rob's order ("Monthly totals catalog is 1-9, Monthly Debt is in Catalog 5"): 1.5 is
monthly totals of debt payments.

    catalog()                        -> shapes, subjects, sections, templates, styles
    run(reader, section_id, settings) -> {id, title, enough, sentences, table, chart, ...}

settings: period ('June to September', or {'start': 'YYYY-MM', 'end': 'YYYY-MM'}), period_b (comparisons), category,
payee, amount, debt. Health is not a subject (TM7): it stays behind item 45's H6 boundary, on its own page.
"""
from core import agent_hands as ah
from core import periods

SHAPES = [
    {'n': 1, 'key': 'monthly', 'name': 'Monthly totals', 'draws': 'bars'},
    {'n': 2, 'key': 'trend', 'name': 'Trend over time', 'draws': 'line'},
    {'n': 3, 'key': 'list', 'name': 'List of items', 'draws': 'table'},
    {'n': 4, 'key': 'snapshot', 'name': 'Snapshot', 'draws': 'tile'},
    {'n': 5, 'key': 'compare', 'name': 'Comparison', 'draws': 'paired'},
    {'n': 6, 'key': 'whatif', 'name': 'What-if', 'draws': 'tile'},
]
SUBJECTS = [
    {'n': 1, 'key': 'spending', 'name': 'Spending by category'},
    {'n': 2, 'key': 'category', 'name': 'One category', 'needs': 'category'},
    {'n': 3, 'key': 'payees', 'name': 'Payees'},
    {'n': 4, 'key': 'income', 'name': 'Income'},
    {'n': 5, 'key': 'debt_payments', 'name': 'Debt payments'},
    {'n': 6, 'key': 'debt_balances', 'name': 'Debt balances'},
    {'n': 7, 'key': 'net_worth', 'name': 'Net worth and balances'},
    {'n': 8, 'key': 'recurring', 'name': 'Recurring charges and price steps'},
    {'n': 9, 'key': 'bills', 'name': 'Bills due'},
    {'n': 10, 'key': 'headroom', 'name': 'Budget headroom'},
]
# C3, section 11's table as ruled: subject -> the shapes that make a section with it
PAIRS = {1: (1, 2, 3, 4, 5), 2: (1, 2, 3, 4, 5), 3: (1, 3, 5), 4: (1, 2, 3, 4, 5), 5: (1, 2, 3, 5),
         6: (2, 3, 4, 5, 6), 7: (1, 2, 3, 4, 5), 8: (2, 3, 4), 9: (3, 4), 10: (4, 6)}
TITLES = {
    '1.1': 'Spending by category, each month', '2.1': 'All spending over time', '3.1': 'Categories ranked',
    '4.1': 'Budget against spending', '5.1': 'Spending by category, two periods',
    '1.2': '{category}, each month', '2.2': '{category} over time', '3.2': '{category}: the transactions',
    '4.2': '{category} against its budget line', '5.2': '{category}, two periods',
    '1.3': '{payee}, each month', '3.3': 'Top payees', '5.3': 'Payees, two periods',
    '1.4': 'Income, each month', '2.4': 'Income over time', '3.4': 'Paychecks and other income',
    '4.4': 'Income lines against what came in', '5.4': 'Income, two periods',
    '1.5': 'Debt payments, each month', '2.5': 'Debt payments over time', '3.5': 'The debt payments',
    '5.5': 'Debt payments, two periods',
    '2.6': 'Debt balances over time', '3.6': 'Each debt', '4.6': 'What is owed today', '5.6': 'Debt balances, then and now',
    '6.6': 'Debt payoff: what if',
    '1.7': 'Net worth at each month end', '2.7': 'Net worth over time', '3.7': 'Each account',
    '4.7': 'Balances today: set aside and available', '5.7': 'Net worth, then and now',
    '2.8': 'Price changes over time', '3.8': 'Charges that recur', '4.8': 'What recurs each month, in all',
    '3.9': 'Bills due in the next 30 days', '4.9': 'What is due, in all',
    '4.10': 'Room in the budget', '6.10': 'Finding {amount} in the budget',
}
# P2 / C2: the reports as content templates - their own pages unchanged. The visit report (health, TM7) and the
# import audit (about imports, not money) have no sections and stay their own pages only.
TEMPLATES = [
    {'id': 'monthly', 'name': 'Monthly Spending Summary', 'sections': [('4.1', {}), ('3.1', {'period': 'this month'}),
                                                                        ('4.4', {})]},
    {'id': 'category', 'name': 'Category Deep-Dive', 'sections': [('1.2', {}), ('2.2', {}), ('3.2', {})]},
    {'id': 'budget_vs_actual', 'name': 'Spending vs. Budget', 'sections': [('4.1', {})]},
    {'id': 'annual', 'name': 'Annual Summary', 'sections': [('1.4', {'period': 'this year'}), ('1.1', {'period': 'this year'}),
                                                            ('3.1', {'period': 'this year'})]},
    {'id': 'year_end', 'name': 'Year-end packet', 'sections': [('3.4', {'period': 'last year'}),
                                                               ('3.1', {'period': 'last year'}), ('3.3', {'period': 'last year'})]},
    {'id': 'distance_traveled', 'name': 'Distance Traveled', 'sections': [('2.6', {}), ('1.5', {}), ('4.6', {})]},
    {'id': 'debt_payoff', 'name': 'Debt Payoff Analysis', 'sections': [('3.6', {}), ('4.6', {}), ('6.6', {'amount': 100})]},
    {'id': 'debt_progress', 'name': 'Debt Progress', 'sections': [('2.6', {}), ('1.5', {}), ('4.6', {})]},
    {'id': 'income_savings', 'name': 'Income & Savings Rate', 'sections': [('1.4', {}), ('2.4', {}), ('2.1', {})]},
    {'id': 'net_worth', 'name': 'Net Worth Timeline', 'sections': [('2.7', {}), ('1.7', {}), ('3.7', {})]},
]
# P13 / C9-C10: six styles; text and charts on screen, print / PDF when printing
STYLES = [
    {'key': 'text_grid', 'name': 'Text and grid', 'visuals': False, 'tables': True, 'text': True},
    {'key': 'text_charts', 'name': 'Text and charts', 'visuals': True, 'tables': False, 'text': True, 'default': True},
    {'key': 'charts_first', 'name': 'Charts first', 'visuals': True, 'tables': False, 'text': True, 'charts_first': True},
    {'key': 'text_only', 'name': 'Text only', 'visuals': False, 'tables': False, 'text': True},
    {'key': 'print', 'name': 'Print / PDF', 'visuals': True, 'tables': True, 'text': True, 'print_default': True},
    {'key': 'compact', 'name': 'Compact summary', 'visuals': False, 'tables': False, 'text': True, 'compact': True},
]


def section_ids():
    return [f'{s}.{subj}' for subj, shapes in PAIRS.items() for s in shapes]


def catalog():
    secs = []
    for sid in section_ids():
        shape, subj = (int(x) for x in sid.split('.'))
        sh, su = SHAPES[shape - 1], SUBJECTS[subj - 1]
        needs = [su['needs']] if su.get('needs') else []
        if sid == '1.3':
            needs.append('payee')
        if shape == 5:
            needs.append('period_b')
        if sid in ('6.6', '6.10'):
            needs.append('amount')
        secs.append({'id': sid, 'shape': sh['key'], 'subject': su['key'], 'title': TITLES[sid],
                     'shape_name': sh['name'], 'subject_name': su['name'], 'draws': sh['draws'], 'needs': needs})
    return {'shapes': SHAPES, 'subjects': SUBJECTS, 'sections': secs, 'styles': STYLES,
            'templates': [{'id': t['id'], 'name': t['name'],
                           'sections': [{'id': i, 'settings': s} for i, s in t['sections']]} for t in TEMPLATES]}


# ── reading ─────────────────────────────────────────────────────────────────────────────────────────────────────────
def _m(x):
    """Money as people write it: -$246.79, not $-246.79."""
    return None if x is None else ('-' + ah.money(-x) if x < 0 else ah.money(x))


def _change(x):
    """A change from the second period to the first: +$246.79 more, -$17.74 less."""
    return ('+' if x > 0 else '') + _m(x)


def _f(x):
    return float(str(x).replace('$', '').replace(',', '')) if x not in (None, '') else 0.0


def _months(reader, rows, setting, default='record'):
    """The months a section covers, inside the record. setting: words, or {'start','end'} as 'YYYY-MM'."""
    first, _ = ah._span(rows)
    this = reader.today.strftime('%Y-%m')
    if isinstance(setting, dict) and setting.get('start'):
        start, end = setting['start'], setting.get('end') or setting['start']
        months, k = [], start
        while k <= min(end, this):
            months.append(k)
            k = ah.month_add(k, 1)
        said = f"{ah.month_label(start)} to {ah.month_label(end)}" if end != start else ah.month_label(start)
    elif isinstance(setting, str) and setting.strip():
        p = periods.read_period(setting, reader.today)
        if not p:
            return None, f'"{setting}" is not a period Groundwork can read'
        months, said = p['months'], p['said']
    elif default == 'this':
        months, said = [this], 'this month'
    else:
        if not first:
            return [], 'the record'
        months, k = [], first[:7]
        while k <= this:
            months.append(k)
            k = ah.month_add(k, 1)
        said = 'the whole record'
    if first:
        months = [m for m in months if m >= first[:7]]
    return months, said


def _label(months):
    if not months:
        return ''
    return ah.month_label(months[0]) if len(months) == 1 else f'{ah.month_label(months[0])} to {ah.month_label(months[-1])}'


def _out(sid, settings, **kw):
    title = TITLES[sid].format(category=settings.get('category') or 'One category', payee=settings.get('payee') or 'A payee',
                               amount=_m(_f(settings.get('amount'))) if settings.get('amount') else 'an amount')
    o = {'id': sid, 'title': title, 'enough': True, 'sentences': [], 'table': None, 'chart': None, 'settings': settings}
    o.update(kw)
    return o


def _not_enough(sid, settings, why, would_know=None):
    return _out(sid, settings, enough=False, why=why, would_know=would_know,
                sentences=[f"Groundwork doesn't know yet: {why}." + (f' It would know with {would_know}.' if would_know else '')])


def _sum_by(rows, months, key, pred, value):
    out = {}
    for r in rows:
        if r['date'][:7] in months and pred(r):
            k = key(r)
            out[k] = round(out.get(k, 0.0) + value(r), 2)
    return out


def _monthly_series(rows, months, pred, value):
    by = _sum_by(rows, months, lambda r: r['date'][:7], pred, value)
    return [{'label': ah.month_label(m), 'key': m, 'value': by.get(m, 0.0)} for m in months]


def _is_spend(r):
    return ah._spend(r)


def _is_income(r):
    return r['kind'] == 'income'


def _is_debt_payment(r):
    return r['kind'] == 'debt_payment'


def _amount(r):
    return abs(r['amount'])


def _cats(rows):
    return sorted({r['category'] for r in rows if r['category']})


def _series_sentence(what, series, said):
    total = round(sum(p['value'] for p in series), 2)
    parts = '; '.join(f"{p['label']} {_m(p['value'])}" for p in series)
    return f"{what}, {said}: {_m(total)} in all. {parts}." if series else f'{what}: nothing in {said}.'


def _subject_rows(subj, rows, settings):
    """The rows a flow subject reads, its value, and a word for it - or why it cannot."""
    if subj == 1:
        return rows, _is_spend, ah._signed, 'Spending', None
    if subj == 2:
        names = ah._category_match(settings.get('category'), _cats(rows))
        if not names:
            return None, None, None, None, (f'there is no category called "{settings.get("category") or ""}" in the record',
                                            'choosing one of: ' + ', '.join(_cats(rows)))
        return rows, (lambda r: _is_spend(r) and r['category'] in names), ah._signed, ', '.join(names), None
    if subj == 3:
        p = (settings.get('payee') or '').lower()
        return rows, (lambda r: _is_spend(r) and (not p or p in r['payee'].lower())), ah._signed, settings.get('payee') or 'Payees', None
    if subj == 4:
        return rows, _is_income, _amount, 'Income', None
    if subj == 5:
        return rows, _is_debt_payment, _amount, 'Debt payments', None
    return None, None, None, None, ('this subject has no rows to add up', None)


# ── the sections ────────────────────────────────────────────────────────────────────────────────────────────────────
def _flow(reader, sid, shape, subj, settings, rows):
    """Subjects 1-5: rows added up - monthly, trend, list, snapshot, comparison."""
    src, pred, val, what, bad = _subject_rows(subj, rows, settings)
    if bad:
        return _not_enough(sid, settings, *bad)
    months, said = _months(reader, rows, settings.get('period'), default='this' if shape in (4, 5) else 'record')
    if months is None:
        return _not_enough(sid, settings, said, 'words like "June to September", "last month" or "this year"')
    if not months:
        return _not_enough(sid, settings, 'the record has no transactions yet', 'importing a statement')
    said = _label(months) if said not in ('this month',) else said
    if shape in (1, 2):
        series = _monthly_series(src, months, pred, val)
        o = _out(sid, settings, sentences=[_series_sentence(what, series, said)],
                 chart={'kind': 'bars' if shape == 1 else 'line', 'points': series},
                 table={'columns': ['Month', what], 'rows': [[p['label'], _m(p['value'])] for p in series]})
        if shape == 1 and subj in (1, 5):          # by category or by debt, each month
            key = (lambda r: r['category'] or 'Uncategorised') if subj == 1 else (lambda r: r['payee'])
            grid = {}
            for r in src:
                if r['date'][:7] in months and pred(r):
                    k = key(r)
                    grid.setdefault(k, {})
                    grid[k][r['date'][:7]] = round(grid[k].get(r['date'][:7], 0.0) + val(r), 2)
            o['table'] = {'columns': ['', *[ah.month_label(m) for m in months], 'Total'],
                          'rows': [[k, *[_m(v.get(m, 0.0)) for m in months], _m(sum(v.values()))]
                                   for k, v in sorted(grid.items(), key=lambda kv: -sum(kv[1].values()))]}
        if shape == 2 and subj == 2:
            line = sum(float(i['amount']) for i in ah._budget_items(reader) if i.get('type') == 'expense'
                       and i.get('category') in ah._category_match(settings.get('category'), _cats(rows)))
            if line:
                o['chart']['reference'] = {'label': 'Budget line', 'value': line}
                o['sentences'].append(f'The budget line is {_m(line)} a month.')
        if shape == 2 and len(series) >= 2:
            o['sentences'].append(f"From {_m(series[0]['value'])} in {series[0]['label']} to "
                                  f"{_m(series[-1]['value'])} in {series[-1]['label']}"
                                  + (' (so far).' if months[-1] == reader.today.strftime('%Y-%m') else '.'))
        return o
    if shape == 3:
        if subj in (1, 3):
            key = (lambda r: r['category'] or 'Uncategorised') if subj == 1 else (lambda r: r['payee'])
            by = _sum_by(src, months, key, pred, val)
            ranked = sorted(by.items(), key=lambda kv: -kv[1])
            top = ranked[:25] if subj == 3 else ranked
            word = 'categories' if subj == 1 else 'payees'
            sent = (f"{len(ranked)} {word}, {said}. The largest: " + '; '.join(f'{k} {_m(v)}' for k, v in top[:3]) + '.'
                    if ranked else f'Nothing spent in {said}.')
            return _out(sid, settings, sentences=[sent], table={'columns': ['Category' if subj == 1 else 'Payee', 'Spent'],
                                                                'rows': [[k, _m(v)] for k, v in top]})
        sel = [r for r in src if r['date'][:7] in months and pred(r)]
        total = round(sum(val(r) for r in sel), 2)
        return _out(sid, settings, sentences=[f'{len(sel)} {what.lower()} rows, {said}: {_m(total)} in all.'],
                    table={'columns': ['Date', 'Payee', 'Category', 'Account', 'Amount'],
                           'rows': [[r['date'], r['payee'], r['category'], r['account'], _m(val(r))] for r in sel[-200:]]})
    if shape == 4:
        month = months[-1]
        if subj == 1:
            b = ah.lk_budget_vs_spent(reader, {'month': month})
            if not b.get('enough'):
                return _not_enough(sid, settings, b['why'], b.get('would_know'))
            budgeted = round(sum(_f(x['budgeted']) for x in b['lines']), 2)
            spent = round(sum(_f(x['spent']) for x in b['lines']), 2)
            sents = [f"{b['month']}{' so far' if b['partial_month'] else ''}: {_m(spent)} spent against "
                     f"{_m(budgeted)} budgeted."]
            if b['over_budget']:
                sents.append('Over their line: ' + ', '.join(b['over_budget']) + '.')
            if b['spent_with_no_budget_line']:
                sents.append('Spent with no budget line: ' + '; '.join(f"{x['category']} {x['spent']}"
                                                                         for x in b['spent_with_no_budget_line']) + '.')
            return _out(sid, settings, sentences=sents,
                        chart={'kind': 'tile', 'points': [{'label': 'Spent', 'value': spent}, {'label': 'Budgeted', 'value': budgeted}]},
                        table={'columns': ['Line', 'Budgeted', 'Spent', 'Over', 'Left'],
                               'rows': [[x['line'], x['budgeted'], x['spent'], x['over'] or '', x['left'] or ''] for x in b['lines']]})
        if subj == 2:
            c = ah.lk_category_by_month(reader, {'category': settings.get('category'), 'month': month})
            if not c.get('enough'):
                return _not_enough(sid, settings, c['why'], c.get('would_know'))
            sents = [f"{c['category']}, {c['month']}{' so far' if c.get('partial_month') else ''}: {c['spent']} over "
                     f"{c['charges']} charges."]
            if c.get('against_budget'):
                sents.append(f"Against the {c['budget_line']} line: {c['against_budget']}.")
            pts = [{'label': 'Spent', 'value': _f(c['spent'])}]
            if c['budget_line'] != 'no budget line':
                pts.append({'label': 'Budget line', 'value': _f(c['budget_line'])})
            return _out(sid, settings, sentences=sents, chart={'kind': 'tile', 'points': pts})
        if subj == 4:
            inc = ah.lk_income_lines(reader, {})
            came = round(sum(_amount(r) for r in rows if _is_income(r) and r['date'][:7] == month), 2)
            planned = _f(inc['budgeted_total'])
            return _out(sid, settings, sentences=[f"{ah.month_label(month)}: {_m(came)} came in; the income lines "
                                                  f"plan {_m(planned)}."],
                        chart={'kind': 'tile', 'points': [{'label': 'Came in', 'value': came}, {'label': 'Planned', 'value': planned}]},
                        table={'columns': ['Income line', 'Amount'], 'rows': [[x['name'], x['amount']] for x in inc['budgeted']]})
    if shape == 5:
        months_b, said_b = _months(reader, rows, settings.get('period_b'), default='record')
        if not settings.get('period_b') or months_b is None or not months_b:
            return _not_enough(sid, settings, 'a comparison needs a second period', 'choosing the period to compare against')
        key = {1: lambda r: r['category'] or 'Uncategorised', 2: lambda r: r['category'], 3: lambda r: r['payee'],
               4: lambda r: r['payee'], 5: lambda r: r['payee']}[subj]
        a, b = _sum_by(src, months, key, pred, val), _sum_by(src, months_b, key, pred, val)
        la, lb = _label(months), _label(months_b)
        keys = sorted(set(a) | set(b), key=lambda k: -(a.get(k, 0) + b.get(k, 0)))
        ta, tb = round(sum(a.values()), 2), round(sum(b.values()), 2)
        return _out(sid, settings, sentences=[f'{what}: {_m(ta)} in {la}; {_m(tb)} in {lb}.'],
                    chart={'kind': 'paired', 'labels': [la, lb],
                           'points': [{'label': k, 'value': a.get(k, 0.0), 'value_b': b.get(k, 0.0)} for k in keys[:12]]},
                    table={'columns': ['', la, lb, f'Change from {lb}'],
                           'rows': [[k, _m(a.get(k, 0.0)), _m(b.get(k, 0.0)),
                                     _change(round(a.get(k, 0.0) - b.get(k, 0.0), 2))] for k in keys]})
    return _not_enough(sid, settings, 'this pairing is not a section')


def _history(reader):
    """Debt balances by month from the record's debt history (statements), summed across debts."""
    h = reader.get('/api/debt/history/all') or {}
    names = {str(d.get('id')): d.get('name') for d in (reader.get('/api/debt') or []) if isinstance(d, dict)}
    by, per = {}, {}
    for did, rs in h.items():
        for r in rs or []:
            if r.get('balance') is None:
                continue
            by[r['month']] = round(by.get(r['month'], 0.0) + float(r['balance']), 2)
            per.setdefault(names.get(did, did), {})[r['month']] = float(r['balance'])
    return by, per


def _debt(reader, sid, shape, settings):
    if shape in (2, 5):
        by, per = _history(reader)
        if len(by) < 2:
            return _not_enough(sid, settings, 'the record holds fewer than two months of debt balances',
                               'linking each debt to its statements')
        ms = sorted(by)
        if shape == 2:
            pts = [{'label': ah.month_label(m), 'key': m, 'value': by[m]} for m in ms]
            return _out(sid, settings, sentences=[f"Owed across the debts: {_m(pts[0]['value'])} in {pts[0]['label']}; "
                                                  f"{_m(pts[-1]['value'])} in {pts[-1]['label']}."],
                        chart={'kind': 'line', 'points': pts},
                        table={'columns': ['Month', 'Owed'], 'rows': [[p['label'], _m(p['value'])] for p in pts]})
        a, b = ms[0], ms[-1]
        return _out(sid, settings, sentences=[f'Owed: {_m(by[a])} in {ah.month_label(a)}; {_m(by[b])} in '
                                              f'{ah.month_label(b)}.'],
                    chart={'kind': 'paired', 'labels': [ah.month_label(a), ah.month_label(b)],
                           'points': [{'label': n, 'value': v.get(a, 0.0), 'value_b': v.get(b, 0.0)} for n, v in per.items()]},
                    table={'columns': ['Debt', ah.month_label(a), ah.month_label(b)],
                           'rows': [[n, _m(v.get(a, 0.0)), _m(v.get(b, 0.0))] for n, v in per.items()]})
    d = ah.lk_debts(reader, {})
    if not d['debts']:
        return _not_enough(sid, settings, 'no debt is in the record', 'adding a debt')
    if shape == 3:
        return _out(sid, settings, sentences=[f"{len(d['debts'])} debts."],
                    table={'columns': ['Debt', 'Balance', 'Rate', 'Minimum', 'Due day'],
                           'rows': [[x['name'], x['balance'], x['rate'], x['minimum'], x['due_day'] or ''] for x in d['debts']]})
    plan = ah.lk_debt_whatif(reader, {'extra_monthly': _f(settings.get('amount')) if shape == 6 else 0,
                                      **({'debt': settings['debt']} if shape == 6 and settings.get('debt') else {})})
    total = round(sum(_f(x['balance']) for x in d['debts']), 2)
    if shape == 4:
        sents = [f'Owed today: {_m(total)} across {len(d["debts"])} debts.']
        if plan.get('now'):
            sents.append(f"On the plan ({plan['strategy']}, {plan['debt_budget']} a month): debt-free {plan['now']['debt_free']},"
                         f" {plan['now']['interest_to_pay']} in interest. Assumes {plan['assumptions']}.")
        elif plan.get('why'):
            sents.append(f"No payoff date: {plan['why']}.")
        return _out(sid, settings, sentences=sents, chart={'kind': 'tile', 'points': [{'label': 'Owed', 'value': total}]})
    if plan.get('clarify') or plan.get('ask'):
        return _not_enough(sid, settings, f'there is no debt called "{settings.get("debt")}"', 'choosing one of the debts')
    if not plan.get('enough'):
        return _not_enough(sid, settings, plan['why'], plan.get('would_know'))
    sents = [f"Now: debt-free {plan['now']['debt_free']}, {plan['now']['interest_to_pay']} in interest."]
    if plan.get('with_extra'):
        sents.append(f"With {plan['extra_monthly']} more a month ({plan['aimed_at']}): debt-free "
                     f"{plan['with_extra']['debt_free']} - {plan['months_sooner']} months sooner, {plan['interest_saved']} "
                     f"less interest.")
    mo = ah.lk_minimums_only(reader, {})
    if mo.get('enough'):
        sents.append(f"Paying only the minimums: debt-free {mo['debt_free']}, {mo['interest_to_pay']} in interest.")
    sents.append(f"Assumes {plan['assumptions']}.")
    pts = [{'label': 'Now', 'value': plan['now']['months']}]
    if plan.get('with_extra'):
        pts.append({'label': f"With {plan['extra_monthly']}", 'value': plan['with_extra']['months']})
    return _out(sid, settings, sentences=sents, chart={'kind': 'tile', 'unit': 'months', 'points': pts})


def _net_worth(reader, sid, shape, settings, rows):
    if shape in (3, 4):
        b = ah.lk_balances(reader, {})
        if not b['accounts']:
            return _not_enough(sid, settings, 'no checking, savings or cash account is in the record', 'adding one')
        total = round(sum(_f(x['balance']) for x in b['accounts']), 2)
        aside = round(sum(_f(x.get('set_aside')) for x in b['accounts']), 2)
        table = {'columns': ['Account', 'Balance', 'Set aside', 'Available'],
                 'rows': [[x['account'], x['balance'], x.get('set_aside') or '', x.get('available') or x['balance']]
                          for x in b['accounts']]}
        if shape == 3:
            return _out(sid, settings, sentences=[f"{len(b['accounts'])} accounts, {_m(total)} in all."], table=table)
        return _out(sid, settings, sentences=[f'{_m(total)} in the accounts; {_m(aside)} set aside in goals; '
                                              f'{_m(round(total - aside, 2))} available.'],
                    chart={'kind': 'tile', 'points': [{'label': 'Balance', 'value': total}, {'label': 'Available',
                                                                                             'value': round(total - aside, 2)}]},
                    table=table)
    snaps = reader.get('/api/net-worth/snapshots') or []
    if not snaps:
        return _not_enough(sid, settings, 'there are no net worth snapshots yet', 'visiting Net Worth once a month')
    pts = [{'label': s['month_label'], 'key': (s.get('date') or '')[:7], 'value': round(float(s['net_worth']), 2)} for s in snaps]
    if settings.get('period'):
        months, _ = _months(reader, rows, settings['period'])
        if months:
            pts = [p for p in pts if p['key'] in months] or pts
    if shape == 5:
        a, b = pts[0], pts[-1]
        return _out(sid, settings, sentences=[f"Net worth: {_m(a['value'])} in {a['label']}; {_m(b['value'])} in "
                                              f"{b['label']}."],
                    chart={'kind': 'paired', 'labels': [a['label'], b['label']],
                           'points': [{'label': 'Net worth', 'value': a['value'], 'value_b': b['value']}]})
    return _out(sid, settings, sentences=[f"Net worth: {_m(pts[0]['value'])} in {pts[0]['label']}; "
                                          f"{_m(pts[-1]['value'])} in {pts[-1]['label']}."],
                chart={'kind': 'bars' if shape == 1 else 'line', 'points': pts},
                table={'columns': ['Month', 'Net worth'], 'rows': [[p['label'], _m(p['value'])] for p in pts]})


def _recurring(reader, sid, shape, settings):
    if shape == 2:
        pc = ah.lk_price_changes(reader, {})
        ch = pc.get('changes') or []
        if not ch:
            return _not_enough(sid, settings, pc.get('why') or 'no price change is in the record', pc.get('would_know'))
        rows_ = [[c.get('label') or c.get('payee') or '', _m(_f(c.get('before'))), _m(_f(c.get('after'))),
                  c.get('first_after') or ''] for c in ch]
        return _out(sid, settings, sentences=[c['sentence'] for c in ch if c.get('sentence')][:6]
                    or [f'{len(ch)} price changes in the record.'],
                    chart={'kind': 'paired', 'labels': ['Was', 'Now'],
                           'points': [{'label': r[0], 'value': _f(c.get('before')), 'value_b': _f(c.get('after'))}
                                      for r, c in zip(rows_, ch)][:12]},
                    table={'columns': ['Charge', 'Was', 'Now', 'Since'], 'rows': rows_})
    r = ah.lk_recurring(reader, {})
    items = r['recurring']
    if not items:
        return _not_enough(sid, settings, 'no charge recurs in the record yet', 'another month of statements')
    total = round(sum(_f(x['monthly']) for x in items), 2)
    if shape == 3:
        return _out(sid, settings, sentences=[f'{len(items)} charges recur, {_m(total)} a month in all.'],
                    table={'columns': ['Charge', 'Category', 'Monthly', 'Day of the month'],
                           'rows': [[x['name'], x['category'] or '', x['monthly'], ', '.join(map(str, x['days_of_month_charged']))]
                                    for x in items]})
    return _out(sid, settings, sentences=[f'{_m(total)} recurs each month, across {len(items)} charges.'],
                chart={'kind': 'tile', 'points': [{'label': 'Each month', 'value': total}]})


def _bills(reader, sid, shape, settings):
    b = ah.lk_bills_due(reader, {'amount': 30})
    ents = [e for e in b['calendar_next_10_weeks'] if e['kind'] in ('charge', 'bill', 'debt', 'medical')]
    total = round(sum(_f(e['amount']) for e in ents if e['amount']), 2)
    if shape == 3:
        return _out(sid, settings, sentences=[f'{len(ents)} due in the next 30 days.' if ents else 'Nothing due in the next 30 days.'],
                    table={'columns': ['Date', 'What', 'Amount'], 'rows': [[e['date'], e['what'], e['amount'] or ''] for e in ents]})
    return _out(sid, settings, sentences=[f'{_m(total)} due in the next 30 days, across {len(ents)} bills and payments.'],
                chart={'kind': 'tile', 'points': [{'label': 'Due in 30 days', 'value': total}]})


def _headroom(reader, sid, shape, settings):
    h = ah.lk_budget_headroom(reader, {'amount': _f(settings.get('amount'))} if shape == 6 and settings.get('amount') else {})
    if not h.get('enough'):
        return _not_enough(sid, settings, h['why'], h.get('would_know'))
    sents = [f"Room in every month the record covers: {h['room_together']} a month in all."
             if h['categories_with_room'] else 'No category stayed under its line in every month.']
    if h['left_out_as_protected']:
        sents.append('Left out as protected: ' + ', '.join(h['left_out_as_protected']) + '.')
    if shape == 6:
        if not settings.get('amount'):
            return _not_enough(sid, settings, 'a what-if needs an amount', 'the amount to find')
        sents.insert(0, f"{h['asked_for']}: the room {'covers it' if h['room_covers_it'] else 'does not cover it'}.")
    return _out(sid, settings, sentences=sents,
                chart={'kind': 'tile', 'points': [{'label': 'Room a month', 'value': _f(h['room_together'])}]
                       + ([{'label': 'Asked for', 'value': _f(h['asked_for'])}] if h.get('asked_for') else [])},
                table={'columns': ['Category', 'Budgeted', 'Most in a month', 'Room every month'],
                       'rows': [[x['category'], x['budgeted'], x['most_spent_in_a_month'], x['room_every_month']]
                                for x in h['categories_with_room']]})


def run(reader, section_id, settings=None):
    settings = dict(settings or {})
    if section_id not in TITLES or section_id not in section_ids():
        return {'id': section_id, 'enough': False, 'title': 'Not a section', 'sentences': ['That is not a section.'],
                'why': 'not in the catalog'}
    shape, subj = (int(x) for x in section_id.split('.'))
    rows, held = ah._rows(reader)
    if subj <= 5:
        o = _flow(reader, section_id, shape, subj, settings, rows)
    elif subj == 6:
        o = _debt(reader, section_id, shape, settings)
    elif subj == 7:
        o = _net_worth(reader, section_id, shape, settings, rows)
    elif subj == 8:
        o = _recurring(reader, section_id, shape, settings)
    elif subj == 9:
        o = _bills(reader, section_id, shape, settings)
    else:
        o = _headroom(reader, section_id, shape, settings)
    o.update({'shape': SHAPES[shape - 1]['key'], 'subject': SUBJECTS[subj - 1]['key']})
    if held:
        o['text_held_back'] = held
    return o
