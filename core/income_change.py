"""Item 71 (gw 2.0/INCOME_CHANGE_SCENARIOS.md, ruled 2026-10-10), on item 66's frame (gw 2.0/SCENARIOS.md):
when recorded income drops, the scenarios that show what follows, and the budget that would follow it.

Everything here is arithmetic over what it is handed - no database, no clock of its own, nothing stored. The
server gathers the record; the person's answer and their tap are the only things kept, and the server keeps them.

  I1  as amended (section 4, D1-D10): `detect_pay` judges each payer on its own checks - the typical check for steady
      pay, the ordinary week for hourly pay - never calendar months. A paycheck that has not come in is asked about,
      never counted as zero. It never says why.
  I3  `scenarios`: five futures, each with its assumptions in words and every figure tagged by kind (item 66 SC3:
      observed / projected / user_supplied), each scored against the person's goal (SC1).
  I4  `order`: which leads - from the person's own answer first, then the smallest change that keeps the goal.
  I6  `budget_follows`: the lines that would change and to what (the person's flexible categories first, never the
      necessity floor or a protected one); applied only on the person's tap, by the server.
"""
from core.consequence import simulate_payoff
from core.solution import is_protected

LINE_CUT_SHARE = 0.5       # a line gives at most half of itself in the budget-follows scenario: spread, not emptied
KIND = ('observed', 'projected', 'user_supplied')


# ── Item 71 amendment D3-D10 (section 4, RULED 2026-10-10): each payer's own paychecks, not calendar months ──
# Tested on real pay before it was built (section 4.2 / 4.5): the average fails (overtime and double checks lift it);
# the typical check works for steady pay; for hourly pay the ordinary week, as built in section 4.6.
PAY_FLOOR = 0.08          # D6: a drop is at least 8% ...
SWING_TIMES = 2           # ... and at least twice the payer's own normal swing
MOVE = 0.10               # D10: a check more than 10% from the one before it is a move ...
VARIES = 0.30             # ... and more than 30% of checks moving is pay that varies -> ask. A single step down (one
                          # move) or a double check (two) is not; overtime coming and going is (tested in section 4.6)
HOURLY_WEEKS = 12         # D8 as built (section 4.6): 12-week windows ...
HOURLY_LOW = 0.10         # ... measured at the 10th percentile (the ordinary week, below any overtime) ...
OT_MOST_WEEKS = 0.65      # ... and when overtime fills more than 65% of the weeks, no ordinary week can be told: facts only
SCHEDULES = ((6, 8, 7, 52 / 12), (12, 17, 14, 26 / 12), (26, 35, 30, 1.0))    # (low, high, nominal days, checks/month)


def _q(xs, p):
    xs = sorted(xs)
    if not xs:
        return 0.0
    k = (len(xs) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def _median(xs):
    return _q(xs, 0.5)


def pay_schedule(dates):
    """(nominal days, checks a month) when the dates keep a weekly, every-two-weeks or monthly rhythm, else None."""
    if len(dates) < 4:
        return None
    gaps = [(b - a).days for a, b in zip(dates, dates[1:])]
    g = _median(gaps)
    for lo, hi, nominal, per_month in SCHEDULES:
        if lo <= g <= hi and sum(lo <= x <= hi for x in gaps) >= 0.6 * len(gaps):
            return nominal, per_month
    return None


GIG_WEEKS = 13               # P1: the weekly view reads the last thirteen weeks
GIG_PER_WEEK = 1.5           # P1: pay with no schedule landing this often (a week, over the last 8) is read by the week


def weekly_view(checks, end):
    """P1: pay with no schedule, by the week - a typical week, a low week and a high week over the last GIG_WEEKS. Weeks
    with nothing count as $0 (for gig work they are real). None unless it lands often enough to read this way."""
    from datetime import timedelta
    recent = [d for d, _ in checks if end - timedelta(weeks=8) < d <= end]
    if len(recent) < GIG_PER_WEEK * 8:
        return None
    weeks = [0.0] * GIG_WEEKS
    for d, a in checks:
        i = (end - d).days // 7
        if 0 <= i < GIG_WEEKS:
            weeks[i] += a
    return {'weeks': GIG_WEEKS, 'typical': round(_median(weeks), 2), 'low': round(_q(weeks, 0.1), 2),
            'high': round(max(weeks), 2)}


def _window(checks, end, weeks):
    from datetime import timedelta
    return [a for d, a in checks if end - timedelta(weeks=weeks) < d <= end]


def judge_payer(name, checks, kind, today, records_end):
    """One payer. `checks` [(date, amount)] in date order; `kind` the person's answer ('hourly'|'salary'|None);
    `records_end` the last date the account has any record. -> a dict with 'state':
      'drop'     D4-D6 (steady pay) or D8 (hourly): a drop, with the per-check and monthly figures
      'missing'  D7: the usual payday passed and the account kept recording - asked, never counted as zero
      'ask'      D10: checks spread widely and the kind of pay is not known - no alarm, only facts
      'weekly'   item 112 P1: no schedule, but several deposits a week (gig work) - read by the week, facts only
      'steady'   nothing to say
      'unknown'  too few checks, or no regular rhythm"""
    from datetime import timedelta
    dates = [d for d, _ in checks]
    sched = pay_schedule(dates)
    out = {'payer': name, 'kind': kind, 'checks': len(checks)}
    if not sched:
        wk = weekly_view(checks, dates[-1]) if dates else None
        if wk:
            # Item 112 P1 (panel I-11): pay that lands several times a week with no schedule (gig work, Uber) was
            # "unknown" for two years, and every income feature skipped it. It is read by the week instead - facts,
            # never an alarm - and its typical week counts toward monthly income.
            return {**out, 'state': 'weekly', 'every': 7, 'per_month': round(52 / 12, 4), 'last': dates[-1].isoformat(),
                    'typical': wk['typical'], 'weekly': wk}
        return {**out, 'state': 'unknown'}
    every, per_month = sched
    out.update(every=every, per_month=round(per_month, 4), last=dates[-1].isoformat())
    due = dates[-1] + timedelta(days=every)
    grace = 3 if every < 20 else 5
    if today > due + timedelta(days=grace):
        if records_end and records_end > due + timedelta(days=grace):
            return {**out, 'state': 'missing', 'since': dates[-1].isoformat()}
        return {**out, 'state': 'not_on_record_yet', 'records_end': records_end.isoformat() if records_end else None}
    amounts = [a for _, a in checks]
    recent16 = _window(checks, dates[-1], 16) or amounts
    typical_all = _median(recent16)
    moves = sum(abs(b - a) > a * MOVE for a, b in zip(amounts, amounts[1:])) / max(1, len(amounts) - 1)
    kind_used = kind if kind else (None if moves > VARIES else 'salary')
    if kind_used is None:
        return {**out, 'state': 'ask', 'moves': round(moves, 3), 'typical': round(typical_all, 2),
                'low': round(min(recent16), 2), 'high': round(max(recent16), 2)}

    if kind_used == 'hourly':
        # D8 as built (section 4.6): the ordinary week - the 10th percentile of the last 12 weeks - against the 12
        # weeks before. Fixed windows: searching back over every start date gave overtime streaks too many chances.
        end = dates[-1]
        recent = _window(checks, end, HOURLY_WEEKS)
        before = [a for d, a in checks if end - timedelta(weeks=2 * HOURLY_WEEKS) < d <= end - timedelta(weeks=HOURLY_WEEKS)]
        if len(recent) < 4 or len(before) < 4:
            return {**out, 'state': 'unknown', 'rule': 'hourly'}
        r, b = _q(recent, HOURLY_LOW), _q(before, HOURLY_LOW)
        overtime = {'recent': round(sum(max(0.0, a - r) for a in recent), 2),
                    'before': round(sum(max(0.0, a - b) for a in before), 2), 'weeks': HOURLY_WEEKS}
        out.update(rule='hourly', ordinary=round(r, 2), ordinary_before=round(b, 2), overtime=overtime)
        # the ordinary week is a pay level that repeats (base pay does; overtime amounts and a short week don't). No
        # repeating level, or overtime above it in most weeks, and no ordinary week can be told apart (AP9).
        def level(xs):
            xs = sorted(xs)
            return next((x for i, x in enumerate(xs) if any(abs(y - x) <= x * 0.02 for j, y in enumerate(xs) if j != i)), None)
        lr, lb = level(recent), level(before)
        ot_share = 1.0 if lr is None or lb is None else max(sum(a > lr * 1.10 for a in recent) / len(recent),
                                                            sum(a > lb * 1.10 for a in before) / len(before))
        if ot_share > OT_MOST_WEEKS:
            return {**out, 'state': 'cannot_tell', 'overtime_share': round(ot_share, 2)}
        if r < b * (1 - PAY_FLOOR):
            start = next((d for d, a in checks if d > end - timedelta(weeks=HOURLY_WEEKS) and a <= r * 1.02), end)
            return {**out, 'state': 'drop', 'per_check_before': round(b, 2), 'per_check_now': round(r, 2),
                    'monthly_drop': round((b - r) * per_month, 2), 'since': start.isoformat()}
        return {**out, 'state': 'steady'}

    # D4-D6: steady pay - the checks since a date against the typical check of the ~8 weeks before it (8 weekly,
    # 4 every-two-weeks or 3 monthly checks), at least 4 / 2 / 2 checks long. The earliest start that holds wins, so a
    # cut that has lasted months is still measured against the pay before it.
    n_recent = 4 if every == 7 else 2
    k_before = {7: 8, 14: 4, 30: 3}[every]
    if len(amounts) < n_recent + k_before:
        return {**out, 'state': 'unknown', 'rule': 'salary'}
    found = None
    for i in range(len(amounts) - n_recent, k_before - 1, -1):
        before = amounts[i - k_before:i]
        typical = _median(before)
        swing = _median([abs(a - typical) for a in before]) / typical if typical else 0
        thr = max(PAY_FLOOR, SWING_TIMES * swing)
        if typical and all(a < typical * (1 - thr) for a in amounts[i:]):
            found = (i, typical, thr)
    if found:
        i, typical, thr = found
        now = _median(amounts[i:])
        out.update(rule='salary', typical=round(typical, 2), threshold=round(thr, 4))
        return {**out, 'state': 'drop', 'per_check_before': round(typical, 2), 'per_check_now': round(now, 2),
                'monthly_drop': round((typical - now) * per_month, 2), 'since': dates[i].isoformat()}
    before = amounts[-(n_recent + k_before):-n_recent]
    out.update(rule='salary', typical=round(_median(before), 2))
    return {**out, 'state': 'steady'}


def detect_pay(deposits, kinds, records_end, today):
    """D3: every payer judged on its own checks. `deposits` [{'date', 'amount', 'payer', 'account_id'}] (income only,
    D1); `kinds` {payer: 'hourly'|'salary'} from the person (D10); `records_end` {account_id: date}.
    -> {'change': the largest drop, shaped for scenarios() | None, 'payers': [...judged...]}"""
    by = {}
    for d in sorted(deposits, key=lambda x: x['date']):
        by.setdefault(d['payer'], []).append(d)
    judged = []
    for payer, ds in by.items():
        checks = [(d['date'], float(d['amount'])) for d in ds]
        # two deposits on one day are one paycheck (a split deposit)
        merged = {}
        for day, amt in checks:
            merged[day] = merged.get(day, 0.0) + amt
        checks = sorted(merged.items())
        judged.append(judge_payer(payer, checks, kinds.get(payer), today, records_end.get(ds[-1]['account_id'])))
    monthly = 0.0
    for j in judged:
        if j.get('per_month'):
            base = j.get('per_check_before') or j.get('typical') or j.get('ordinary_before') or j.get('ordinary') or 0
            monthly += base * j['per_month']
    drops = sorted((j for j in judged if j['state'] == 'drop'), key=lambda j: -j['monthly_drop'])
    change = None
    if drops:
        top = drops[0]
        lost = sum(j['monthly_drop'] for j in drops)
        change = {'kind': 'step', 'from': round(monthly, 2), 'to': round(monthly - lost, 2), 'month': top['since'][:7],
                  'months': [], 'payer': top['payer'], 'rule': top.get('rule'), 'per_check_before': top['per_check_before'],
                  'per_check_now': top['per_check_now'], 'monthly_drop': round(lost, 2), 'every': top['every'],
                  'payers_dropped': [j['payer'] for j in drops]}
    return {'change': change, 'payers': judged}


def budget_follows(lines, gap, effective, fixed=()):
    """I3 scenario 2 / I6: close `gap` from budget lines. `lines`: [{'id', 'name', 'category', 'amount'}].
    `effective`: the Willingness Layer's per-category stance ({key: {'stance', 'source'}}).

    Order (E.3 rule 2): declared or observed flexible first, then unclassified, then what the record says is kept
    ('sacred'); within each, larger lines first. Never a line on the necessity floor, never a protected one. Each
    line gives at most LINE_CUT_SHARE of itself. Returns {'changes': [{id, name, category, old, new, why}],
    'closed': amount, 'left': what could not be closed}.

    D11 (section 4.7): never a line in `fixed` - a payment set by a contract (loan, lease, debt, insurance), or one
    that may be and is waiting for the person's answer."""
    rank = {'flexible': 0, 'unclassified': 1, 'sacred': 2}
    pool = []
    for ln in lines:
        cat = (ln.get('category') or ln.get('name') or '').strip()
        if __import__('core.care_status', fromlist=['never_lever']).never_lever(cat) or float(ln.get('amount') or 0) <= 0 or ln['id'] in fixed:   # item 89
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


def scenarios(change, outflow, lines, effective, cards, debt_budget, cushion, answer=None, kw=None, fixed=(),
              debt_payments=0.0):
    """I3: five futures for one recorded drop. `change` from detect; `outflow` the month's budgeted expenses;
    `debt_payments` what goes to debt each month (server _debt_month_plan) - income has to cover it as well as the
    expenses, so the gap counts it (panel review I-04: without it every gap was short by the debt payments);
    `cushion` cash the person holds above their own floors (None when not known); `answer` the person's word on
    whether it lasts ('lasting' | 'temporary' | 'unsure' | None). Debt figures use the one payoff engine.

    Each: {'key', 'title', 'assumptions': [str], 'gap', 'debt_months', 'figures': [{label, value, kind}], ...}."""
    kw = kw or {}
    level, before = change['to'], change['from']
    debt_payments = round(float(debt_payments or 0), 2)
    gap = round(max(0.0, outflow + debt_payments - level), 2)
    base_months = _payoff(cards, debt_budget, kw)
    minimums = round(sum(c.minimum for c in cards), 2) if cards else 0.0
    extra = max(0.0, round(debt_budget - minimums, 2))
    obs = [{'label': 'Recorded income now', 'value': level, 'kind': 'observed'},
           {'label': 'Recorded income before', 'value': before, 'kind': 'observed'},
           {'label': 'Budgeted spending', 'value': round(outflow, 2), 'kind': 'observed'}]
    if debt_payments:
        obs.append({'label': 'Debt payments', 'value': debt_payments, 'kind': 'observed'})
    _res = __import__('core.health_reserve', fromlist=['input_line']).input_line(cards, debt_budget)
    if _res:
        obs.append(_res)            # item 90 D4
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
    plan = budget_follows(lines, gap, effective, fixed)
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
                'gap': round(max(0.0, outflow + debt_payments - before), 2), 'debt_months': base_months,
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
