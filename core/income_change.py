"""Item 71 (gw 2.0/INCOME_CHANGE_SCENARIOS.md, ruled 2026-10-10), on item 66's frame (gw 2.0/SCENARIOS.md):
when recorded income drops, the scenarios that show what follows, and the budget that would follow it.

Everything here is arithmetic over what it is handed - no database, no clock of its own, nothing stored. The
server gathers the record; the person's answer and their tap are the only things kept, and the server keeps them.

  I1  `detect`: a step (the existing break detector, core/breaks) or a slide (four months below the three before,
      every one of them under the lowest of those) in recorded income. Months with no income on record are unknown,
      never zero. It never says why.
  I3  `scenarios`: five futures, each with its assumptions in words and every figure tagged by kind (item 66 SC3:
      observed / projected / user_supplied), each scored against the person's goal (SC1).
  I4  `order`: which leads - from the person's own answer first, then the smallest change that keeps the goal.
  I6  `budget_follows`: the lines that would change and to what (the person's flexible categories first, never the
      necessity floor or a protected one); applied only on the person's tap, by the server.
"""
from core.breaks import detect_break
from core.consequence import simulate_payoff
from core.solution import is_protected

DROP_SHARE = 0.10          # a tenth is where a pay change stops being noise (as E.2a's INCOME_CHANGE_SHARE)
SLIDE_RECENT = 3           # the recent months, each below the lowest of the PRIOR months
SLIDE_PRIOR = 3           # at least this many earlier months to judge against
PRIOR_MAX = 6             # and up to this many: the recent months must sit under every one of them
SLIDE_MARGIN = 0.02        # "below" means under that lowest month by more than 2%, so a level month is not a slide
LINE_CUT_SHARE = 0.5       # a line gives at most half of itself in the budget-follows scenario: spread, not emptied
KIND = ('observed', 'projected', 'user_supplied')


def _consecutive(months):
    def nxt(m):
        y, mo = int(m[:4]), int(m[5:7])
        return f'{y + 1}-01' if mo == 12 else f'{y}-{mo + 1:02d}'
    return all(nxt(a) == b for a, b in zip(months, months[1:]))


def detect(income):
    """A drop in recorded income, or None. `income` is {'YYYY-MM': amount} over complete months, only months with
    income on record. {'kind': 'step'|'slide', 'from', 'to', 'month', 'months': [...]}"""
    series = sorted((m, float(a)) for m, a in income.items() if a and a > 0)
    if len(series) < SLIDE_RECENT + SLIDE_PRIOR:
        return None
    b = detect_break(series)
    if b and b['after'] < b['before'] * (1 - DROP_SHARE):
        return {'kind': 'step', 'from': round(b['before'], 2), 'to': round(b['after'], 2), 'month': b['month'],
                'months': [m for m, _ in series if m >= b['month']]}
    # The break detector only names changes of 30% or more; a pay cut of 10-30% is found here. The longest recent run
    # of at least SLIDE_RECENT consecutive months, every one under the lowest of the SLIDE_PRIOR months just before
    # it (by more than SLIDE_MARGIN), averaging DROP_SHARE or more below them. A run that holds level is a step; one
    # still falling is a slide.
    best = None
    for start in range(SLIDE_PRIOR, len(series) - SLIDE_RECENT + 1):    # the longest run first
        window = series[max(0, start - PRIOR_MAX):]
        if not _consecutive([m for m, _ in window]):
            continue                       # a gap is unknown; nothing is read across it
        cut = start - max(0, start - PRIOR_MAX)
        prior, recent = window[:cut], window[cut:]
        floor = min(a for _, a in prior) * (1 - SLIDE_MARGIN)
        if not all(a < floor for _, a in recent):
            continue
        p = [a for _, a in prior]
        p_mean = sum(p) / len(p)
        spread = (sum((a - p_mean) ** 2 for a in p) / len(p)) ** 0.5
        r_mean = sum(a for _, a in recent) / len(recent)
        # the drop must be a tenth AND stand clear of the months' own swing (twice their spread)
        if p_mean - r_mean >= max(p_mean * DROP_SHARE, 2 * spread):
            best = (prior, recent, p_mean, r_mean)
            break
    if not best:
        return None
    prior, recent, p_mean, r_mean = best
    vals = [a for _, a in recent]
    level = (max(vals) - min(vals)) <= r_mean * 0.05
    return {'kind': 'step' if level else 'slide', 'from': round(p_mean, 2), 'to': round(r_mean if level else vals[-1], 2),
            'month': recent[0][0], 'months': [m for m, _ in recent]}


def budget_follows(lines, gap, effective):
    """I3 scenario 2 / I6: close `gap` from budget lines. `lines`: [{'id', 'name', 'category', 'amount'}].
    `effective`: the Willingness Layer's per-category stance ({key: {'stance', 'source'}}).

    Order (E.3 rule 2): declared or observed flexible first, then unclassified, then what the record says is kept
    ('sacred'); within each, larger lines first. Never a line on the necessity floor, never a protected one. Each
    line gives at most LINE_CUT_SHARE of itself. Returns {'changes': [{id, name, category, old, new, why}],
    'closed': amount, 'left': what could not be closed}."""
    rank = {'flexible': 0, 'unclassified': 1, 'sacred': 2}
    pool = []
    for ln in lines:
        cat = (ln.get('category') or ln.get('name') or '').strip()
        if is_protected(cat) or float(ln.get('amount') or 0) <= 0:
            continue
        w = (effective or {}).get(cat.lower()) or {'stance': 'unclassified', 'source': None}
        if w['stance'] == 'protected':
            continue
        pool.append((rank.get(w['stance'], 1), -float(ln['amount']), ln, w))
    pool.sort(key=lambda x: (x[0], x[1]))
    left, changes = round(float(gap), 2), []
    for _, _, ln, w in pool:
        if left <= 0:
            break
        give = min(round(float(ln['amount']) * LINE_CUT_SHARE, 2), left)
        if give <= 0:
            continue
        why = ('you marked it flexible' if w['stance'] == 'flexible' and w['source'] == 'declared'
               else 'your record shows a cut there held' if w['stance'] == 'flexible'
               else 'nothing says to keep it' if w['stance'] == 'unclassified' else 'the last place to look')
        changes.append({'id': ln['id'], 'name': ln['name'], 'category': ln.get('category'),
                        'old': round(float(ln['amount']), 2), 'new': round(float(ln['amount']) - give, 2), 'why': why})
        left = round(left - give, 2)
    return {'changes': changes, 'closed': round(float(gap) - max(left, 0), 2), 'left': max(left, 0)}


def _payoff(cards, budget, kw):
    if not cards:
        return None
    try:
        r = simulate_payoff(cards, budget, **kw)
    except Exception:
        return None
    return r['months'] if r else None


def scenarios(change, outflow, lines, effective, cards, debt_budget, cushion, answer=None, kw=None):
    """I3: five futures for one recorded drop. `change` from detect; `outflow` the month's budgeted expenses;
    `cushion` cash the person holds above their own floors (None when not known); `answer` the person's word on
    whether it lasts ('lasting' | 'temporary' | 'unsure' | None). Debt figures use the one payoff engine.

    Each: {'key', 'title', 'assumptions': [str], 'gap', 'debt_months', 'figures': [{label, value, kind}], ...}."""
    kw = kw or {}
    level, before = change['to'], change['from']
    gap = round(max(0.0, outflow - level), 2)
    base_months = _payoff(cards, debt_budget, kw)
    minimums = round(sum(c.minimum for c in cards), 2) if cards else 0.0
    extra = max(0.0, round(debt_budget - minimums, 2))
    obs = [{'label': 'Recorded income now', 'value': level, 'kind': 'observed'},
           {'label': 'Recorded income before', 'value': before, 'kind': 'observed'},
           {'label': 'Budgeted spending', 'value': round(outflow, 2), 'kind': 'observed'}]
    out = []

    # 1. Nothing changes - the gap is borrowed
    out.append({'key': 'nothing_changes', 'title': 'Nothing changes',
                'assumptions': [f'Income stays at about ${level:,.0f} a month.', 'The budget stays as saved.',
                                'The difference is put on cards or taken from savings.'],
                'gap': gap, 'borrowed_monthly': gap,
                'debt_months': _payoff(cards, debt_budget - gap, kw) if gap else base_months,
                'figures': obs + [{'label': 'Short each month', 'value': gap, 'kind': 'projected'},
                                  {'label': 'Added to what you owe each month', 'value': gap, 'kind': 'projected'}]})

    # 2. The budget follows the income
    plan = budget_follows(lines, gap, effective)
    out.append({'key': 'budget_follows', 'title': 'The budget follows the income',
                'assumptions': [f'Income stays at about ${level:,.0f} a month.',
                                'The gap comes out of the categories you marked or showed flexible first; never rent, food, insurance or anything you protected.'],
                'gap': plan['left'], 'plan': plan, 'debt_months': base_months if not plan['left'] else _payoff(cards, debt_budget - plan['left'], kw),
                'figures': obs + [{'label': 'Moved out of the budget', 'value': plan['closed'], 'kind': 'projected'},
                                  {'label': 'Still short after that', 'value': plan['left'], 'kind': 'projected'}]})

    # 3. A goal moves instead - less goes to the debt; nothing is borrowed while the extra covers it
    covered = round(min(gap, extra), 2)
    out.append({'key': 'goal_moves', 'title': 'The debt-free date moves instead',
                'assumptions': [f'Income stays at about ${level:,.0f} a month.', 'The budget stays as saved.',
                                f'Up to ${extra:,.0f} a month that was going beyond your minimum payments covers the gap.'],
                'gap': round(gap - covered, 2), 'from_extra': covered,
                'debt_months': _payoff(cards, debt_budget - covered, kw) if covered else base_months,
                'figures': obs + [{'label': 'Taken from extra debt payments', 'value': covered, 'kind': 'projected'},
                                  {'label': 'Still short after that', 'value': round(gap - covered, 2), 'kind': 'projected'}]})

    # 4. It is temporary - a bridge
    months = int(cushion // gap) if (cushion is not None and gap > 0) else None
    out.append({'key': 'bridge', 'title': "It's temporary: a bridge",
                'assumptions': ['Income comes back later.', 'Savings above your own floors cover the gap meanwhile.'],
                'gap': gap, 'bridge_months': months, 'cushion': cushion, 'debt_months': base_months,
                'figures': obs + [{'label': 'Savings above your floors', 'value': cushion, 'kind': 'observed'},
                                  {'label': 'Months that covers', 'value': months, 'kind': 'projected'}]
                + ([{'label': 'You said', 'value': 'temporary', 'kind': 'user_supplied'}] if answer == 'temporary' else [])})

    # 5. Income comes back - for comparison
    out.append({'key': 'income_returns', 'title': 'Income comes back',
                'assumptions': [f'Income returns to about ${before:,.0f} a month.'],
                'gap': round(max(0.0, outflow - before), 2), 'debt_months': base_months,
                'figures': [{'label': 'Recorded income before', 'value': before, 'kind': 'observed'}]})

    for s in out:
        s['keeps_debt_date'] = (base_months is not None and s['debt_months'] is not None and s['debt_months'] <= base_months)
    return {'gap': gap, 'base_debt_months': base_months, 'scenarios': out, 'order': order(out, answer)}


def order(scens, answer):
    """I4: which leads. The person's word first - temporary leads with the bridge, lasting with the budget following;
    then the scenario that keeps the debt date with the smallest change (lines touched, then dollars moved). Never
    chosen for the person: the order only says which is shown first."""
    keyed = {s['key']: s for s in scens}
    first = {'temporary': 'bridge', 'lasting': 'budget_follows'}.get(answer)

    def cost(s):
        plan = s.get('plan') or {}
        return (0 if s['keeps_debt_date'] else 1, len(plan.get('changes', [])), plan.get('closed', 0))
    rest = sorted((s for s in scens if s['key'] not in (first, 'income_returns', 'nothing_changes')), key=cost)
    lead = [first] if first in keyed else []
    return lead + [s['key'] for s in rest if s['key'] not in lead] + ['nothing_changes', 'income_returns']
