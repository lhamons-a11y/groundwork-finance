"""
Groundwork - the evidence library (gw 2.0/EVIDENCE_LIBRARY.md, item 58, E1-E10)
==============================================================================
Checked research findings, shipped with the app (core/data/evidence.json), offered where the person's own record
shows the situation a finding is about.

  - E1  one record per finding: id, finding, limits, source, strength, applies_when, surfaces, offer.
  - E2  an entry is chosen by a plain rule: every fact in its applies_when is true of the person's own financial
        record. Nothing here reads how often or when the app is used - ruling 6 and the dashboard rule.
  - E6  only an entry Rob has accepted (status 'accepted' with accepted_on) is ever offered. Drafts stay in the file.
  - The narrator never chooses an entry; the voice check's R11 blocks a research claim that carries no accepted id.
"""
import json
from datetime import date
from pathlib import Path

LIBRARY = Path(__file__).parent / 'data' / 'evidence.json'
FIELDS = ('id', 'finding', 'limits', 'source', 'strength', 'applies_when', 'surfaces', 'offer', 'status')
STRENGTHS = ('meta-analysis', 'randomized trial', 'field study', 'survey')
SURFACES = ('goal', 'debt_plan', 'willingness', 'card_payoff')
# E3: how the narrator names each surface ("shown next to ..."). Kept here, so the page's code names no layer.
SURFACE_WORDS = {'goal': 'a savings goal', 'debt_plan': 'a debt payoff plan', 'willingness': 'the working picture',
                 'card_payoff': 'a plan to pay a trip off a card'}
STATUSES = ('draft', 'accepted')

# E2: the facts an entry may apply to - each read from the person's own financial record.
FACTS = {
    'has_savings_goal': 'at least one active savings goal (sinking fund)',
    'has_debt': 'at least one active debt with a balance',
    'multiple_debts': 'two or more active debts with a balance',
    'has_card_balance': 'a credit card with a balance',
    'no_savings_goal': 'no active savings goal (sinking fund)',
}
# E5's follow-through on a yes: open the page where it is done, or the Sunday check-in names the goals / is the reminder
ACT_KINDS = ('open', 'checkin_goals', 'checkin_weekly')


def library():
    with open(LIBRARY, encoding='utf-8') as f:
        return json.load(f)


def problems(e):
    """What keeps an entry from being well-formed (E1, E6); [] when it is."""
    out = [f'missing {k}' for k in FIELDS if e.get(k) in (None, '')]
    src = e.get('source') or {}
    out += [f'source has no {k}' for k in ('authors', 'year', 'journal', 'title') if not src.get(k)]
    if e.get('strength') not in STRENGTHS:
        out.append(f"strength {e.get('strength')!r} is not one of {STRENGTHS}")
    out += [f'unknown fact {f!r}' for f in e.get('applies_when') or [] if f not in FACTS]
    out += [f'unknown surface {s!r}' for s in e.get('surfaces') or [] if s not in SURFACES]
    if e.get('status') not in STATUSES:
        out.append(f"status {e.get('status')!r}")
    if e.get('status') == 'accepted' and not e.get('accepted_on'):
        out.append('accepted with no accepted_on date')
    if not str(e.get('offer') or '').rstrip().endswith('?'):
        out.append('the offer is not a question (E5)')
    act = e.get('act')
    if act is not None and (not isinstance(act, dict) or act.get('kind') not in ACT_KINDS
                            or (act.get('kind') == 'open' and not (act.get('open') or {}).get('view'))):
        out.append(f'act {act!r} is not one Groundwork can follow through')
    return out


def accepted():
    return [e for e in library()['entries'] if e.get('status') == 'accepted' and e.get('accepted_on') and not problems(e)]


def accepted_ids():
    return sorted(e['id'] for e in accepted())


def facts(session):
    """E2: the facts, from the person's financial record only (goals and debts)."""
    from core.database import DebtAccount, SinkingFund
    goals = session.query(SinkingFund).filter_by(is_active=True).count()
    debts = [d for d in session.query(DebtAccount).filter_by(is_active=True).all() if (d.current_balance or 0) > 0]
    return {
        'has_savings_goal': goals > 0,
        'has_debt': len(debts) > 0,
        'multiple_debts': len(debts) >= 2,
        'has_card_balance': any((d.debt_type or 'credit') == 'credit' for d in debts),
        'no_savings_goal': goals == 0,
    }


def _money(x):
    return f'${x:,.2f}'


def _months_to(deadline, today):
    """Whole months from today to a goal's YYYY-MM-DD date (at least 1), or None with no date or one already past."""
    try:
        dl = date.fromisoformat(deadline) if deadline else None
    except ValueError:
        return None
    return max(1, (dl.year - today.year) * 12 + dl.month - today.month) if dl and dl > today else None


def _span(months):
    y, m = divmod(months, 12)
    return ' '.join(x for x in (f'{y} year{"s" if y != 1 else ""}' if y else '', f'{m} month{"s" if m != 1 else ""}' if m else '') if x)


def _goal_figure(kind, sf, today):
    """One goal's figure for the study it sits beside."""
    saved, target = sf.current_amount or 0, sf.target_amount or 0
    left, months = max(0.0, target - saved), _months_to(sf.deadline, today)
    if kind == 'progress':                       # Harkin: how far along
        pct = f'{saved / target:.0%} of the way, ' if target > 0 else ''
        return f'{sf.name}: {pct}{_money(saved)} of {_money(target)}.'
    if kind == 'left':                           # Karlan: what is left, and by when
        if left <= 0:
            return f'{sf.name}: reached.'
        return f'{sf.name}: {_money(left)} to go' + (f' by {sf.deadline}.' if sf.deadline else '.')
    if kind == 'monthly':                        # Madrian: the one monthly amount that gets there
        if left <= 0:
            return f'{sf.name}: reached.'
        if not months:
            return f'{sf.name}: {_money(left)} to go, with no date set.'
        return f'{sf.name}: {_money(left / months)} a month reaches {_money(target)} by {sf.deadline}.'
    # Ashraf: the date and the amount the goal holds to
    return f'{sf.name}: {_money(target)} by {sf.deadline}.' if sf.deadline else f'{sf.name}: {_money(target)}, no date set.'


GOAL_FIGURE = {'harkin2016_monitoring': 'progress', 'karlan2016_reminders': 'left', 'madrian2001_defaults': 'monthly',
               'ashraf2006_commitment': 'commitment'}


def yours(session, e, cushion=None, today=None):
    """Rob 2026-10-21: the card shows the person's own record on top, then the finding - "give each card the one
    figure its study is about". Plain facts from their goals and debts (the same record E2 selects on) - never a why,
    never a should. `cushion`: cash in checking and savings above their floors, or None when no balance is known."""
    from core.consequence import minimums_only
    from core.database import DebtAccount, SinkingFund
    today = today or date.today()
    want = set(e.get('applies_when') or [])
    goals = session.query(SinkingFund).filter_by(is_active=True).order_by(SinkingFund.id).all() if 'has_savings_goal' in want else []
    debts = [d for d in session.query(DebtAccount).filter_by(is_active=True).order_by(DebtAccount.id).all()
             if (d.current_balance or 0) > 0] if want & {'has_debt', 'multiple_debts', 'has_card_balance'} else []
    out = []
    if 'no_savings_goal' in want:                # Gjertson: nothing set aside yet, and the cash there is
        out.append('You have no savings fund set up in Groundwork yet.')
        if cushion is not None:
            out.append(f'Your checking and savings hold {_money(cushion)} above the floors you set.')
    if e['id'] in GOAL_FIGURE:
        out += [_goal_figure(GOAL_FIGURE[e['id']], sf, today) for sf in goals[:4]]
        if len(goals) > 4:
            out.append(f'And {len(goals) - 4} more savings goal{"s" if len(goals) > 5 else ""}.')
    elif e['id'] == 'thaler2004_smart' and goals:    # a share of a raise: what the goals take a month now
        need = sum((max(0.0, (sf.target_amount or 0) - (sf.current_amount or 0)) / m)
                   for sf in goals if (m := _months_to(sf.deadline, today)))
        dated = sum(1 for sf in goals if _months_to(sf.deadline, today))
        if dated:
            out.append(f'Your goal needs {_money(need)} a month to reach its date.' if dated == 1
                       else f'Your {dated} goals with a date need {_money(need)} a month together to reach their dates.')
    elif e['id'] == 'gal2012_small_wins' and debts:  # small wins: the debt that could close first
        small = min(debts, key=lambda d: d.current_balance)
        out.append(f'Your smallest balance: {small.name}, {_money(small.current_balance)}, of your {len(debts)} debts with a balance.')
    elif e['id'] == 'stewart2009_anchor':            # the minimum anchor: each card, and paying only its minimum
        for d in [d for d in debts if (d.debt_type or 'credit') == 'credit'][:5]:
            line = f'{d.name}: {_money(d.current_balance)} owed' + (f', minimum {_money(d.minimum_payment)} a month' if d.minimum_payment else '') + '.'
            mo = minimums_only([{'balance': d.current_balance, 'rate': d.interest_rate, 'debt_type': 'credit'}]) if d.interest_rate else None
            if mo and not mo['capped']:
                line += f' Paying only the minimum, which falls as the balance does: {_span(mo["months"])}, and {_money(mo["total_interest"])} in interest.'
            out.append(line)
    elif want & {'has_debt', 'multiple_debts'} and debts:
        names = ', '.join(f'{d.name} {_money(d.current_balance)}' for d in debts[:5])
        more = f' and {len(debts) - 5} more' if len(debts) > 5 else ''
        out.append(f'Your debts with a balance: {names}{more} - {_money(sum(d.current_balance for d in debts))} in all.')
    return out


def select(session, surface):
    """The accepted entries for a surface whose every applies_when fact is true. An entry with no facts listed is
    about the surface itself (the working picture's own rhythm view)."""
    if surface not in SURFACES:
        return []
    f = facts(session)
    return [e for e in accepted() if surface in e['surfaces'] and all(f.get(x) for x in e['applies_when'])]
