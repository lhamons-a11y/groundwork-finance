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

from core.utility_estimate import STATE_DIVISION

SOURCES = ('onboarding', 'settings', 'inline_prompt', 'carried_over')

# The question-to-consumer matrix (O7). `values`: the answers that exist. `consumers`: what reads the fact - each
# names the code that reads it, so the matrix test can find it. `lines`: where the fact is asked ('both' or '2.0').
# `asks`: the canonical question; onboarding, Settings and inline prompts all ask THIS fact.
FACTS = {
    'home_state': {
        'asks': 'Which state is your home in?',
        'values': tuple(sorted(STATE_DIVISION)),
        'lines': 'both',
        'consumers': [
            ('server.py', '_home_state', 'the Budget page EIA benchmarks (both lines)'),
            ('server.py', 'gas_estimate', 'item 26: the region for the natural gas estimate'),
            ('server.py', 'electric_estimate', 'item 26: the region for the electricity estimate'),
            ('server.py', 'gasoline_estimate', 'item 26: the area for the gasoline estimate'),
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
    'housing_status': {
        'asks': 'Do you own or rent your home?',
        'values': ('own', 'rent', 'other'),
        'lines': '2.0',
        'consumers': [
            ('server.py', 'utility_applies', 'item 26: whether a home utility estimate applies at all'),
            ('static/js/teaching/household.js', '_housingLabel', 'the bills screen: Mortgage or Rent'),
        ],
    },
    'electricity_included': {
        'asks': 'Does your rent include electricity?',
        'values': ('yes', 'no', 'not_sure'),
        'lines': '2.0',
        'consumers': [
            ('server.py', 'utility_applies', 'item 26: no electricity estimate when rent includes it'),
        ],
    },
    'heating_fuel': {
        'asks': 'What heats your home?',
        'values': ('natural_gas', 'propane', 'electric', 'heating_oil', 'wood_pellets', 'included', 'other',
                   'not_sure'),
        'lines': '2.0',
        'consumers': [
            ('server.py', 'utility_applies', 'item 26/34: natural gas is priced only for natural gas, propane and heating '
                                             'oil from deliveries only when they heat the home; else it says why'),
            ('static/js/teaching/household.js', '_heatingLabel', 'the bills screen: the home heating fuel line'),
        ],
    },
    'heating_payment': {
        'asks': 'How do you pay for your heating fuel?',
        'values': ('by_bill', 'even_monthly', 'prepaid', 'not_sure'),
        'lines': '2.0',
        'consumers': [
            ('server.py', 'utility_applies', 'item 26: an even-monthly or prepaid bill cannot be fitted, and it says so'),
        ],
    },
    'vehicle_fuel': {
        'asks': 'What type of fuel does your vehicle use?',
        'values': ('gasoline', 'diesel', 'electric', 'other', 'none'),
        'lines': '2.0',
        'consumers': [
            ('server.py', 'utility_applies', 'item 26/34: the vehicle-fuel estimate prices gasoline or diesel; none for '
                                             'an electric vehicle or no vehicle'),
            ('server.py', 'gasoline_estimate', 'item 34 F1: diesel is priced from EIA\'s weekly diesel series'),
        ],
    },
    # Item 56 (MUNICIPAL_UTILITIES.md, U2): the services one municipal utility bill covers - a SET of answers, kept as
    # a sorted, comma-joined list ('sewer,trash,water'), or 'none' alone. A changed set is a new history row.
    'municipal_covers': {
        'asks': 'What does your municipal utility bill cover?',
        'values': ('water', 'sewer', 'trash', 'electricity', 'natural_gas', 'none'),
        'multi': True,
        'lines': '2.0',
        'consumers': [
            ('server.py', 'utility_applies', 'item 56 U5: no gas or electricity estimate from a bundle that covers it - '
                                             'it says the bill cannot be separated'),
            ('static/js/teaching/household.js', '_municipalServices', 'item 56 U3: each service on the municipal bill, '
                                                                     'or its own company and category'),
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
    if value is not None and FACTS[key].get('multi'):
        value = canonical_set(key, value)
    elif value is not None and value not in FACTS[key]['values']:
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


def canonical_set(key, value):
    """A multi-answer fact's value in its one stored form: each part an allowed answer, sorted, no repeats; 'none'
    only alone. Raises FactError otherwise."""
    parts = sorted({p.strip() for p in str(value).split(',') if p.strip()})
    bad = [p for p in parts if p not in FACTS[key]['values']]
    if not parts or bad:
        raise FactError(f'{key} cannot be {value!r}')
    if 'none' in parts and len(parts) > 1:
        raise FactError(f"{key}: 'none' cannot be combined with services")
    return ','.join(parts)


def covers(session, service):
    """Item 56: True when the household said its municipal utility bill covers this service."""
    v = current(session, 'municipal_covers')
    return bool(v) and service in v.split(',')


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
