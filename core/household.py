"""Household facts: what the household told Groundwork, one canonical value each (ONBOARDING_REVISIT.md, item 30).

Rob, 2026-10-02: "Onboarding is a data-collection mechanism, not a conversation script. Every question must create
or update a canonical fact that the product actually uses."

    question (onboarding / Settings / inline prompt)
        -> set_household_fact()            the ONE write path
            -> household_facts row         append-only history: the audit trail, and authoritative
            -> app_settings[key]           the current value: the fast operational copy readers already use
        -> consumer -> estimate / calculation / display

Rules this module enforces:
  - the facts belong to the household, not a person: there is no user id (a joint account has no author)
  - history is append-only: a changed answer is a NEW row; nothing is edited or deleted
  - a withdrawal is a row with no value: the fact is unanswered again, and the earlier answer stays in the history
  - an actual answer ('electric', 'none', 'not_sure') is never collapsed into unanswered, and unanswered is never a
    default - no state is not Ohio, no fuel is not natural gas
  - the latest history row is authoritative: current value == latest history value, for every fact with history
  - every fact names its consumers (O7, a hard acceptance criterion); a fact with no consumer is not asked
"""
from datetime import datetime

# The 50 states and DC - the answers the home-state question has (the same list as app.js US_STATES).
STATES = ('AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'DC', 'FL', 'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY',
          'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH',
          'OK', 'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY')

SOURCES = ('onboarding', 'settings', 'inline_prompt', 'carried_over')

# 1.x asks only the facts it has readers for (O9): the state (the Budget page's EIA benchmarks), how often the
# household is paid (the cash-flow and payday views) and its priority (the onboarding summary). The home, heating
# and vehicle facts are 2.0's, where item 26 reads them.
# The question-to-consumer matrix (O7). `values`: the answers that exist. `consumers`: what reads the fact - each
# names the code that reads it, so the matrix test can find it. `lines`: where the fact is asked ('both' or '2.0').
# `asks`: the canonical question; onboarding, Settings and inline prompts all ask THIS fact.
FACTS = {
    'home_state': {
        'asks': 'Which state is your home in?',
        'values': STATES,
        'lines': 'both',
        'consumers': [
            ('server.py', '_home_state', 'the Budget page EIA benchmarks (both lines)'),
        ],
    },
    'pay_frequency': {
        'asks': 'How often are you paid?',
        'values': ('weekly', 'biweekly', 'semimonthly', 'monthly', 'irregular'),
        'lines': 'both',
        'consumers': [
            ('static/js/app.js', 'S.lifeStage.payFrequency', 'the cash-flow and payday views'),
        ],
    },
    'surplus_goal': {
        'asks': 'When you have money beyond your immediate needs, what would you most like it to accomplish?',
        'values': ('debt', 'savings', 'goal', 'invest', 'unsure'),
        'lines': 'both',
        'consumers': [
            ('static/js/app.js', '_obPriorityLine', "the onboarding summary: the user's own choice and its arithmetic"),
        ],
    },
}


class FactError(ValueError):
    pass


def _model():
    from core.database import HouseholdFact
    return HouseholdFact


def _setting(session, key):
    from core.database import AppSetting
    return session.query(AppSetting).filter_by(key=key).first()


def current(session, key):
    """The fact's current value, or None when unanswered. Readers use this (or the AppSetting it mirrors)."""
    row = _setting(session, key)
    return row.value if row and row.value not in (None, '') else None


def latest(session, key):
    """The latest history row for a fact, or None when the fact has no history."""
    M = _model()
    return session.query(M).filter_by(key=key).order_by(M.id.desc()).first()


def history(session, key):
    M = _model()
    return [{'value': r.value, 'answered_at': r.answered_at.isoformat() if r.answered_at else None,
             'source': r.source} for r in session.query(M).filter_by(key=key).order_by(M.id).all()]


def set_household_fact(session, key, value, source):
    """THE write path. Appends a history row and updates the current value in the same transaction.

    value None (or '') withdraws the answer. A value equal to the current one records nothing (nothing changed).
    Returns True when a row was written. Raises FactError for an unknown fact, value or source. The caller commits.
    """
    if key not in FACTS:
        raise FactError(f'not a household fact: {key}')
    if source not in SOURCES:
        raise FactError(f'not a source: {source}')
    value = None if value in (None, '') else str(value)
    if value is not None and value not in FACTS[key]['values']:
        raise FactError(f'{key} cannot be {value!r}')
    if value == current(session, key):
        return False
    M = _model()
    session.add(M(key=key, value=value, answered_at=datetime.utcnow(), source=source))
    row = _setting(session, key)
    if value is None:
        if row is not None:
            session.delete(row)
    elif row is not None:
        row.value = value
    else:
        from core.database import AppSetting
        session.add(AppSetting(key=key, value=value))
    session.flush()
    return True


def carry_over(session):
    """Facts answered before history existed get one row each, source 'carried_over', with NO answered_at - when
    they were said is not known, so it is not invented. After this every current value has history."""
    M = _model()
    n = 0
    for key in FACTS:
        val = current(session, key)
        if val is not None and latest(session, key) is None:
            session.add(M(key=key, value=val, answered_at=None, source='carried_over'))
            n += 1
    session.flush()
    return n


def inconsistencies(session):
    """Every fact whose current value differs from its latest history row. Empty is the invariant."""
    bad = []
    for key in FACTS:
        last = latest(session, key)
        if last is None:
            if current(session, key) is not None:
                bad.append((key, current(session, key), 'no history'))
            continue
        if (last.value or None) != current(session, key):
            bad.append((key, current(session, key), last.value))
    return bad


def snapshot(session, line='2.0'):
    """Every fact asked on this line: its question, its answers, its current value (None = unanswered)."""
    return {k: {'asks': f['asks'], 'values': list(f['values']), 'value': current(session, k)}
            for k, f in FACTS.items() if f['lines'] == 'both' or line == '2.0'}
