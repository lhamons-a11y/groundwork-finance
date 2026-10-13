"""Possible futures (SCENARIOS.md, item 66): the record's futures side by side, which the person can correct.

Plain arithmetic over the person's record and the one payoff engine; no model. Computed on every read (SC5): nothing
derived is stored. What is kept is the person's own word: possibilities they state (SC3), their answer to "Does this
reflect your situation?" (SC4), and a path they chose (SC6).

Every figure carries its kind (SC3): 'observed' (the record), 'projected' (what follows from named assumptions),
'user_supplied' (a possibility the person stated). A possibility never becomes a transaction, a budget line or a balance.
"""
import hashlib
import json
from statistics import median

from core.consequence import simulate_payoff

HORIZON = 12                 # months shown
MIN_INCOME_MONTHS = 2        # SC2: fewer complete months of income on record and there is no baseline to vary
MIN_SPEND_MONTHS = 6         # the costliest-months scenario needs this many complete months of spending on record
COSTLY_MONTHS = 3
KNOWN_COST_DAYS = 90
ANSWERS = ('yes', 'partly', 'unlikely', 'explore', 'show')
POSSIBILITY_KINDS = {
    'income': 'Another income continues',
    'cost': 'A known cost',
    'cut': 'Hours or pay being cut',
}
GOALS = ('debt', 'savings', 'goal', 'invest', 'unsure')


def _fmt(x):
    return f'-${-x:,.0f}' if x < 0 else f'${x:,.0f}'


def _months_after(month_key, n):
    y, m = int(month_key[:4]), int(month_key[5:7])
    m += n
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    return f'{y}-{m:02d}'


def possibilities_in_force(said):
    """The person's possibilities as they stand: the latest statement per id, withdrawn ones left out."""
    latest = {}
    for p in said or []:
        if isinstance(p, dict) and p.get('id'):
            latest[p['id']] = p
    return [p for p in latest.values() if not p.get('withdrawn') and p.get('kind') in POSSIBILITY_KINDS]


def hidden_keys(answers):
    """SC4: a scenario the person called unlikely for them is hidden, until they ask to see it again."""
    last = {}
    for a in answers or []:
        if isinstance(a, dict) and a.get('key') and a.get('answer') in ANSWERS:
            last[a['key']] = a['answer']
    return sorted(k for k, v in last.items() if v == 'unlikely')


def _apply_possibilities(income, costs, start_month, poss):
    """Each month's income and one-time costs with the person's possibilities laid on: [(income, cost)]."""
    inc, cost = list(income), list(costs)
    for p in poss:
        amt = float(p.get('amount') or 0)
        if amt <= 0:
            continue
        frm = p.get('month') or start_month
        for i in range(HORIZON):
            mk = _months_after(start_month, i)
            if p['kind'] == 'income' and mk >= frm:
                inc[i] += amt
            elif p['kind'] == 'cut' and mk >= frm:
                inc[i] -= amt
            elif p['kind'] == 'cost' and mk == frm:
                cost[i] += amt
    return inc, cost


def run(inputs, spec):
    """One future, month by month. `spec`: income and one-time costs per month, and the monthly debt payment.

    cash moves by income - spending (debt payments apart) - debt payment - one-time costs + extra; when it would go
    below $0 the shortfall is borrowed (counted, never hidden). Debt follows the one payoff engine.
    """
    cards, start_month = inputs['cards'], inputs['start_month']
    debt_pay = spec['debt_pay']
    path = []
    payoff = None
    if cards:
        payoff = simulate_payoff(cards, debt_pay, strategy=inputs['strategy'], today_key=start_month,
                                 start_month=start_month, path=path)
    covers = (not cards) or payoff is not None
    cash = inputs['cash'] if inputs['cash'] is not None else 0.0
    borrowed, cash_line, owed_line, low = 0.0, [], [], cash
    for i in range(HORIZON):
        # a month's debt payment is made while anything is owed at its start; a budget below the minimums has no
        # payoff path, and its balance is shown where it stands
        start = inputs['owed'] if (i == 0 or payoff is None) else (path[i - 1] if i - 1 < len(path) else 0.0)
        paid = debt_pay if (cards and start > 0.01) else 0.0
        flow = spec['income'][i] - inputs['spend'] - paid - spec['costs'][i]
        cash += flow
        if cash < 0:
            borrowed += -cash
            cash = 0.0
        low = min(low, cash)
        cash_line.append(round(cash, 2))
        debt_now = inputs['owed'] if payoff is None else (path[i] if i < len(path) else 0.0)
        owed_line.append(round(debt_now + borrowed, 2))
    return {'cash': cash_line, 'owed': owed_line, 'borrowed': round(borrowed, 2), 'lowest_cash': round(low, 2),
            'debt_months': payoff['months'] if payoff else None, 'covers_minimums': covers}


def measure(goal, r):
    """SC1: the goal's own measure. debt: the debt-free date, then debt taken on; savings / a named goal: cash in a
    year; invest: what is left each month on average; unsure: no ranking, the futures side by side."""
    if goal == 'debt':
        if r['debt_months'] is None:
            return {'label': 'Debt-free in', 'value': None, 'unit': 'months'}
        return {'label': 'Debt-free in', 'value': r['debt_months'], 'unit': 'months'}
    if goal in ('savings', 'goal'):
        return {'label': 'Cash in 12 months', 'value': r['cash'][-1], 'unit': 'dollars'}
    if goal == 'invest':
        return {'label': 'Left over a year', 'value': round(r['cash'][-1] - r['borrowed'], 2), 'unit': 'dollars'}
    return {'label': None, 'value': None, 'unit': None}


def _behind(goal, base, other):
    """How much further from the goal `other` leaves the person than the baseline (positive = behind)."""
    a, b = measure(goal, base)['value'], measure(goal, other)['value']
    if a is None or b is None or goal == 'unsure':
        return None
    return (b - a) if goal == 'debt' else (a - b)


def build(inputs, possibilities=(), answers=()):
    """Every future the record supports, the gaps the record leaves, and the questions SC6 answers.

    inputs: income (observed monthly), income_months, spend (budgeted spending, debt payments apart), spend_note,
    debt_pay, minimums, owed, cards, strategy, cash (above the person's floors, or None), goal, start_month,
    spend_record [(month, total)] complete months, known_costs [{label, month, amount}].
    """
    goal = inputs['goal'] if inputs['goal'] in GOALS else 'unsure'
    sm = inputs['start_month']
    gaps = []
    if inputs['income'] is None:
        return {'offered': False, 'why': f'Groundwork needs at least {MIN_INCOME_MONTHS} complete months of income '
                                         f'on record to show possible futures.', 'scenarios': [], 'gaps': []}
    poss = possibilities_in_force(possibilities)
    base_income = [inputs['income']] * HORIZON
    base_costs = [0.0] * HORIZON
    inc, costs = _apply_possibilities(base_income, base_costs, sm, poss)
    surplus = round(inputs['income'] - inputs['spend'] - inputs['debt_pay'], 2)
    said = [{'label': f"{POSSIBILITY_KINDS[p['kind']]}: {p.get('label') or ''} {_fmt(float(p['amount']))}"
                      + (' a month' if p['kind'] != 'cost' else '') + (f" from {p['month']}" if p.get('month') else ''),
             'value': float(p['amount']), 'kind': 'user_supplied', 'id': p['id']} for p in poss]
    obs = [{'label': 'Income a month (recorded)', 'value': inputs['income'], 'kind': 'observed'},
           {'label': 'Budgeted spending a month, debt payments apart', 'value': inputs['spend'], 'kind': 'observed'},
           {'label': 'Debt payments a month', 'value': inputs['debt_pay'], 'kind': 'observed'},
           {'label': 'Cash above your own floors', 'value': inputs['cash'], 'kind': 'observed'}]
    common = [f"Income stays at about {_fmt(inputs['income'])} a month, the middle of your last "
              f"{inputs['income_months']} complete months on record.",
              f"Spending follows your budget: {_fmt(inputs['spend'])} a month, plus {_fmt(inputs['debt_pay'])} to debt."]
    if inputs['cash'] is None:
        common.append('Your cash on hand is not known, so cash starts at $0.')
    out = []

    def add(key, title, kind, assumptions, spec, figures=()):
        r = run(inputs, spec)
        out.append({'key': key, 'title': title, 'kind': kind, 'assumptions': assumptions + [x['label'] for x in said],
                    'figures': obs + list(figures) + said, **r, 'measure': measure(goal, r)})

    add('baseline', 'As things are', 'baseline', list(common),
        {'income': inc, 'costs': costs, 'debt_pay': inputs['debt_pay']},
        [{'label': 'Left each month after the budget', 'value': surplus, 'kind': 'projected'}])

    # goal-oriented: the month's surplus put to the goal
    if goal == 'debt' and surplus > 0 and inputs['cards']:
        add('surplus_to_goal', 'What is left goes to the debt', 'goal', common + [
            f'The {_fmt(surplus)} left each month is added to the debt payment, so it is '
            f"{_fmt(inputs['debt_pay'] + surplus)} a month."],
            {'income': inc, 'costs': costs, 'debt_pay': round(inputs['debt_pay'] + surplus, 2)},
            [{'label': 'New debt payment a month', 'value': round(inputs['debt_pay'] + surplus, 2), 'kind': 'projected'}])
        out[-1]['new_debt_pay'] = round(inputs['debt_pay'] + surplus, 2)
    elif goal == 'debt':
        gaps.append('A future with more going to the debt needs money left after the budget; '
                    + ('there is none at the moment.' if inputs['cards'] else 'no debt is on record.'))

    # adverse, each from the person's own record (SC2)
    rec = [(m, t) for m, t in inputs['spend_record'] if t is not None]
    if len(rec) >= MIN_SPEND_MONTHS:
        mid = median(t for _, t in rec)
        top = sorted(rec, key=lambda x: -x[1])[:COSTLY_MONTHS]
        over = [round(max(0.0, t - mid), 2) for _, t in top]
        c2 = list(costs)
        for i, x in enumerate(over):
            c2[i] += x
        names = ', '.join(f'{m} ({_fmt(t)})' for m, t in top)
        add('costly_months', 'Your costliest months come again', 'adverse', common + [
            f'Your three costliest months of the last year, {names}, happen again over the next three months: '
            f'{_fmt(sum(over))} more than a middle month ({_fmt(mid)}).'],
            {'income': inc, 'costs': c2, 'debt_pay': inputs['debt_pay']},
            [{'label': 'Spending in your costliest months', 'value': round(sum(t for _, t in top), 2), 'kind': 'observed'},
             {'label': 'More than a middle month', 'value': round(sum(over), 2), 'kind': 'projected'}])
    else:
        gaps.append(f'Repeating your costliest months needs {MIN_SPEND_MONTHS} complete months of spending on record; '
                    f'there are {len(rec)}.')

    i0 = list(inc)
    i0[0] = 0.0
    add('no_income_month', 'A month without income', 'adverse', common + [
        'No income arrives next month; the budget and the debt payments go on as usual.'],
        {'income': i0, 'costs': costs, 'debt_pay': inputs['debt_pay']},
        [{'label': 'Income missed', 'value': inc[0], 'kind': 'projected'}])

    if inputs['cards'] and inputs['debt_pay'] > inputs['minimums'] + 0.5:
        freed = round(inputs['debt_pay'] - inputs['minimums'], 2)
        add('minimums_only', 'Minimum payments only', 'adverse', common + [
            f"Only the minimum payments are made ({_fmt(inputs['minimums'])} a month); the other {_fmt(freed)} stays as cash."],
            {'income': inc, 'costs': costs, 'debt_pay': inputs['minimums']},
            [{'label': 'Minimum payments a month', 'value': inputs['minimums'], 'kind': 'observed'}])
    elif inputs['cards']:
        gaps.append('Minimum payments only would change nothing: your debt payment is already the minimums.')

    known = [k for k in inputs['known_costs'] if k['amount'] > 0]
    if known:
        c3 = list(costs)
        for k in known:
            for i in range(HORIZON):
                if _months_after(sm, i) == k['month']:
                    c3[i] += k['amount']
        total = round(sum(k['amount'] for k in known), 2)
        add('known_cost', 'Known costs ahead land', 'adverse', common + [
            'These costs on record in the next 90 days are paid from cash, outside the budget: '
            + '; '.join(f"{k['label']} {_fmt(k['amount'])} ({k['month']})" for k in known) + '.'],
            {'income': inc, 'costs': c3, 'debt_pay': inputs['debt_pay']},
            [{'label': 'Known costs ahead', 'value': total, 'kind': 'observed'}])
    else:
        gaps.append('No one-time cost is on record for the next 90 days. Tell Groundwork about one below and every '
                    'future counts it.')

    base = out[0]
    for s in out:
        s['behind'] = None if s is base else _behind(goal, base, s)
    hidden = hidden_keys(answers)
    shown = [s for s in out if s['key'] not in hidden]
    return {'offered': True, 'goal': goal, 'start_month': sm, 'scenarios': shown,
            'hidden': [{'key': s['key'], 'title': s['title']} for s in out if s['key'] in hidden],
            'gaps': gaps, 'questions': questions(goal, base, out, inputs, surplus, poss, possibilities_effect(inputs, poss, goal)),
            'possibilities': poss, 'months': [_months_after(sm, i) for i in range(HORIZON)]}


def possibilities_effect(inputs, poss, goal):
    """For each possibility in force: how far the baseline moves on the goal's measure without it."""
    out = []
    if not poss:
        return out
    full_inc, full_costs = _apply_possibilities([inputs['income']] * HORIZON, [0.0] * HORIZON, inputs['start_month'], poss)
    with_all = run(inputs, {'income': full_inc, 'costs': full_costs, 'debt_pay': inputs['debt_pay']})
    for p in poss:
        rest = [q for q in poss if q['id'] != p['id']]
        inc, costs = _apply_possibilities([inputs['income']] * HORIZON, [0.0] * HORIZON, inputs['start_month'], rest)
        without = run(inputs, {'income': inc, 'costs': costs, 'debt_pay': inputs['debt_pay']})
        out.append({'id': p['id'], 'cash_12': round(with_all['cash'][-1] - without['cash'][-1], 2),
                    'borrowed': round(with_all['borrowed'] - without['borrowed'], 2)})
    return out


def questions(goal, base, scens, inputs, surplus, poss, effects):
    """SC6: the questions the comparison answers, each a fact from the figures above it."""
    q = []
    adverse = [s for s in scens if s['kind'] == 'adverse' and s['behind'] is not None]
    if goal == 'unsure':
        worst = max((s for s in scens if s['kind'] == 'adverse'), key=lambda s: s['borrowed'], default=None)
        if worst and worst['borrowed'] > 0:
            q.append({'q': 'What would put me behind?',
                      'a': f"Of these, {worst['title'].lower()} borrows the most: {_fmt(worst['borrowed'])} over the year."})
    elif adverse:
        worst = max(adverse, key=lambda s: s['behind'])
        if worst['behind'] > 0:
            unit = 'months later' if goal == 'debt' else 'less'
            amt = f"{worst['behind']} {unit}" if goal == 'debt' else f"{_fmt(worst['behind'])} {unit}"
            q.append({'q': 'What would put me behind?', 'a': f"Of these, {worst['title'].lower()} sets the goal back most: {amt}."})
    kc = next((s for s in scens if s['key'] == 'known_cost'), None)
    big = max([(k['amount'], k['label']) for k in inputs['known_costs']] +
              [(float(p['amount']), p.get('label') or POSSIBILITY_KINDS[p['kind']]) for p in poss if p['kind'] == 'cost'],
              default=None)
    if big:
        q.append({'q': 'Which upcoming expense changes the outcome most?',
                  'a': f'The largest one-time cost ahead is {big[1]}, {_fmt(big[0])}.' + (
                      f" With every known cost paid, cash is {_fmt(kc['cash'][-1])} in a year." if kc else '')})
    q.append({'q': 'How much room do I actually have?',
              'a': (f"After the budget and debt payments, {_fmt(surplus)} a month is left. " if surplus >= 0 else
                    f"The budget and debt payments come to {_fmt(-surplus)} a month more than the income. ")
              + f"As things are, cash is lowest at {_fmt(base['lowest_cash'])}."})
    if effects:
        bits = []
        by = {p['id']: p for p in poss}
        for e in effects:
            p = by[e['id']]
            bits.append(f"{POSSIBILITY_KINDS[p['kind']].lower()} ({p.get('label') or ''}) moves cash in a year by {_fmt(e['cash_12'])}")
        q.append({'q': 'Which correction would change this result?', 'a': 'What you have said: ' + '; '.join(bits) + '.'})
    else:
        q.append({'q': 'Which correction would change this result?',
                  'a': 'Another income, a known cost, or hours being cut: tell Groundwork about any of them and every future counts it.'})
    return q


WHAT_IF_LABELS = {'income': 'Income a month', 'spend': 'Spending a month, debt payments apart',
                  'debt_pay': 'Debt payment a month', 'save': 'Set aside each month', 'one_time': 'A one-time cost'}


def what_if(inputs, possibilities, changes):
    """Item 65 W5 (AGENT_W_ITEMS.md): the person's own figures moved together, through the same run() and the one
    payoff engine every future uses (W5-a) - never a second calculation. Nothing is stored here (W5-b).

    changes: any of income, spend, debt_pay, save (a month), one_time {amount, month}. Returns as things are and the
    what-if side by side, each with its goal measure, and every changed input named with its from and to."""
    sm = inputs['start_month']
    goal = inputs['goal'] if inputs['goal'] in GOALS else 'unsure'
    poss = possibilities_in_force(possibilities)
    inc, costs = _apply_possibilities([inputs['income']] * HORIZON, [0.0] * HORIZON, sm, poss)
    base = run(inputs, {'income': inc, 'costs': costs, 'debt_pay': inputs['debt_pay']})

    def num(k, default):
        try:
            v = float(changes.get(k, default))
        except (TypeError, ValueError):
            return default
        return max(0.0, round(v, 2))
    income, spend = num('income', inputs['income']), num('spend', inputs['spend'])
    debt_pay, save = num('debt_pay', inputs['debt_pay']), num('save', 0.0)
    one = changes.get('one_time') or {}
    try:
        one_amt = max(0.0, round(float(one.get('amount') or 0), 2))
    except (TypeError, ValueError):
        one_amt = 0.0
    one_month = str(one.get('month') or sm)[:7]
    months = [_months_after(sm, i) for i in range(HORIZON)]
    inc2 = [x + (income - inputs['income']) for x in inc]
    costs2 = [c + save + (one_amt if months[i] == one_month else 0.0) for i, c in enumerate(costs)]
    r = run({**inputs, 'spend': spend}, {'income': inc2, 'costs': costs2, 'debt_pay': debt_pay})
    # what is set aside is still the person's: borrowing counts it as spent (it left the cash), the total counts it back
    r['set_aside'] = round(save * HORIZON, 2)
    r['cash_with_set_aside'] = round(r['cash'][-1] + r['set_aside'], 2)
    base['set_aside'], base['cash_with_set_aside'] = 0.0, base['cash'][-1]
    m = lambda x: measure(goal, {**x, 'cash': x['cash'][:-1] + [x['cash_with_set_aside']]})
    changed = []
    for k, frm, to in (('income', inputs['income'], income), ('spend', inputs['spend'], spend),
                       ('debt_pay', inputs['debt_pay'], debt_pay), ('save', 0.0, save)):
        if abs(to - frm) >= 0.005:
            changed.append({'key': k, 'label': WHAT_IF_LABELS[k], 'from': round(frm, 2), 'to': to})
    if one_amt > 0:
        changed.append({'key': 'one_time', 'label': WHAT_IF_LABELS['one_time'], 'from': 0.0, 'to': one_amt,
                        'month': one_month if one_month in months else months[0]})
    return {'goal': goal, 'months': months, 'note': 'A what-if, not a prediction.',
            'as_things_are': {**base, 'measure': m(base)}, 'what_if': {**r, 'measure': m(r)}, 'changed': changed,
            'minimums': inputs['minimums'], 'below_minimums': bool(inputs['cards']) and debt_pay < inputs['minimums'] - 0.005}


def fingerprint(inputs, possibilities, answers):
    """SC5: what a result was computed from. A page holding an older fingerprint marks its figures stale."""
    raw = {k: v for k, v in inputs.items() if k != 'cards'}
    raw['cards'] = [(c.name, round(c.balance, 2), c.rate, c.minimum) for c in inputs['cards']]
    blob = json.dumps([raw, possibilities, answers], sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def pre_budget(income, rows):
    """SC7: a starting point from the record - each monthly row with its source and kind, and what remains."""
    total = round(sum(r['amount'] for r in rows), 2)
    return {'income': income, 'rows': rows, 'total': total,
            'remains': None if income is None else round(income - total, 2)}
