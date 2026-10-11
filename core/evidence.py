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
from pathlib import Path

LIBRARY = Path(__file__).parent / 'data' / 'evidence.json'
FIELDS = ('id', 'finding', 'limits', 'source', 'strength', 'applies_when', 'surfaces', 'offer', 'status')
STRENGTHS = ('meta-analysis', 'randomized trial', 'field study', 'survey')
SURFACES = ('goal', 'debt_plan', 'willingness', 'card_payoff')
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


def select(session, surface):
    """The accepted entries for a surface whose every applies_when fact is true. An entry with no facts listed is
    about the surface itself (the working picture's own rhythm view)."""
    if surface not in SURFACES:
        return []
    f = facts(session)
    return [e for e in accepted() if surface in e['surfaces'] and all(f.get(x) for x in e['applies_when'])]
