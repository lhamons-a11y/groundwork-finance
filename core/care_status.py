"""Care is never a lever (gw 2.0/CARE_NEVER_A_LEVER.md, item 89; C1-C4 and U1-U5 ruled 2026-10-16).

C1, the invariant: a protected expense is counted in every accurate calculation, but no conclusion shown to the person
may present reducing, delaying or giving up that care as a way to improve their money.

U1, three outcomes for a category:
    protected     on the necessity floor (core/solution.is_protected, version 3), or the person said it is health care
    uncertain     a health signal exists but is not conclusive - never a lever, never priced in months (U3)
    not_matched   no signal, or the person said it is not health care

U2: the signals are core/classification.py's counterparty axis, as written - its narrow merchant terms, its health card
codes, and its health category terms on a name the floor does not take. Measured on Rob's record 2026-10-16 (104
categories, 1,492 payments): a supermarket with a pharmacy counter (MIXED_RETAIL_TERMS) would have made Shopping
uncertain from 41 rows, so that weak signal works on single rows only (`row_never_lever`), as the module describes it -
one weak signal, not a category's verdict.

U4: only the person's answer settles an uncertain category, and only that answer is stored (`care_answers`). U5: an
uncertain reading and its reason are worked out here when asked for and are never written to the database, a log, an
export or the model's context.
"""
import hashlib
import threading

from core import classification as cl
from core.solution import is_protected

PROTECTED, UNCERTAIN, NOT_MATCHED = 'protected', 'uncertain', 'not_matched'
# A catch-all is not a kind of spending, so "Is Other health care?" is not a question anyone can answer. Its payments
# are judged one by one (row_never_lever), as an uncategorised payment is. Found in the app 2026-10-16.
CATCH_ALL = frozenset(('other', 'uncategorized', 'uncategorised', 'miscellaneous', 'misc'))

_lock = threading.Lock()
_marker = None
_answers = {}          # lower name -> 'yes' | 'no'
_uncertain = {}        # lower name -> reason (in memory only, U5)


def _key(name):
    return ' '.join(str(name or '').split()).lower()


def _signal(merchant, description, mcc):
    """A strong counterparty signal on one payment: a health merchant term or a health card code."""
    text = f'{merchant or ""} {description or ""}'
    if cl._matches(text, cl.HEALTH_MERCHANT_TERMS):
        return 'a payment named like a pharmacy, clinic or other care provider'
    if str(mcc or '') in cl.HEALTH_MCC:
        return f'a payment under card code {mcc}, which card networks use for health care'
    return None


def _state_marker(session):
    from sqlalchemy import text
    parts = [session.execute(text('SELECT COUNT(*), COALESCE(MAX(id), 0) FROM transactions')).fetchone(),
             session.execute(text('SELECT COUNT(*), COALESCE(MAX(id), 0) FROM care_answers')).fetchone(),
             session.execute(text("SELECT group_concat(id || ':' || name, '|') FROM categories")).fetchone()]
    return hashlib.sha1(repr(parts).encode()).hexdigest()


def refresh(session, force=False):
    """Work the uncertain set out again when the record changed. Pure reads; nothing stored."""
    global _marker
    from core.database import CareAnswer, Category, Transaction
    try:
        marker = _state_marker(session)
    except Exception:          # a database from before the table existed: the floor alone, as before item 89
        return
    if not force and marker == _marker:
        return
    cats = {c.id: c.name for c in session.query(Category).all()}
    answers = {}
    for a in session.query(CareAnswer).order_by(CareAnswer.id).all():
        if a.category_id in cats:
            answers[_key(cats[a.category_id])] = a.answer
    uncertain = {}
    for cid, name in cats.items():
        k = _key(name)
        if is_protected(name) or k in answers or k in CATCH_ALL:
            continue
        if cl._matches(name, cl.HEALTH_CATEGORY_TERMS):
            uncertain[k] = 'its name is close to a health care name'
    for cid, m, d, mcc in session.query(Transaction.category_id, Transaction.merchant, Transaction.description,
                                        Transaction.mcc).filter(Transaction.type == 'debit').all():
        name = cats.get(cid)
        if not name:
            continue
        k = _key(name)
        if k in uncertain or k in answers or k in CATCH_ALL or is_protected(name):
            continue
        why = _signal(m, d, mcc)
        if why:
            uncertain[k] = why
    with _lock:
        _answers.clear(); _answers.update(answers)
        _uncertain.clear(); _uncertain.update(uncertain)
        _marker = marker


def _fresh():
    try:
        from core.database import db_session
        with db_session() as s:
            refresh(s)
    except Exception:
        pass


def status(name):
    """U1 for a category name. The floor is ruled and no answer overrides it."""
    if not name:
        return NOT_MATCHED
    if is_protected(name):
        return PROTECTED
    _fresh()
    k = _key(name)
    a = _answers.get(k)
    if a == 'yes':
        return PROTECTED
    if a == 'no':
        return NOT_MATCHED
    return UNCERTAIN if k in _uncertain else NOT_MATCHED


def never_lever(name):
    """C1/U3: protected or uncertain - never offered as a cut, never priced in months."""
    return status(name) in (PROTECTED, UNCERTAIN)


def row_never_lever(merchant='', description='', mcc='', category=''):
    """One payment (lever 4's recurring items, the large-charge lesson for an uncategorised row): its category's
    status, or any counterparty signal on the row itself - classification.is_lever_candidate as written, the
    supermarket's weak signal included."""
    if category and never_lever(category):
        return True
    if is_protected(merchant) or is_protected(description):
        return True
    c = cl.classify(merchant=f'{merchant or ""} {description or ""}', mcc=mcc or '', category=category or '')
    return not cl.is_lever_candidate(c)


def questions(session):
    """U4: the categories to ask about, each with why - worked out now, never stored or logged (U5)."""
    from core.database import Category
    refresh(session, force=True)
    out = []
    for c in session.query(Category).order_by(Category.name).all():
        why = _uncertain.get(_key(c.name))
        if why:
            out.append({'category_id': c.id, 'name': c.name, 'why': why})
    return out


def answered(session):
    """U4: the answers on record, the newest per category - so a person can see and change what they said."""
    from core.database import CareAnswer, Category
    cats = {c.id: c.name for c in session.query(Category).all()}
    latest = {}
    for a in session.query(CareAnswer).order_by(CareAnswer.id).all():
        if a.category_id in cats:
            latest[a.category_id] = a
    return [{'category_id': cid, 'name': cats[cid], 'answer': a.answer} for cid, a in
            sorted(latest.items(), key=lambda x: cats[x[0]].lower())]


def answer(session, category_id, value):
    """U4: the person's answer, stored with its date. Yes = health care (protected); no = not matched."""
    from core.database import CareAnswer, Category
    if value not in ('yes', 'no'):
        return None, 'answer yes or no'
    cat = session.get(Category, int(category_id or 0))
    if not cat:
        return None, 'That category was not found.'
    row = CareAnswer(category_id=cat.id, answer=value)
    session.add(row)
    session.flush()
    refresh(session, force=True)
    return row, None


# ── C2: every surface that can put a change to spending in front of the person ─────────────────────────────────
# (file, function) -> how C1 holds there. s228 scans the code: a function that calls the lever machinery (MACHINERY)
# and is not listed here fails the gate, so a new surface cannot slip past the rule.
MACHINERY = ('never_lever', 'row_never_lever', '_never_lever', '_row_never_lever', 'is_protected', 'offsetting_monthly_delta', '_flexible_named',
             'budget_pressure', 'large_charge_lesson', 'not_levers')
_CATS = 'protected and uncertain categories are skipped (never_lever)'
_PASS = 'passes on what the engine allowed; adds no category of its own'
LEVER_SURFACES = {
    ('core/solution.py', '_never_lever'): 'the one test, from this module',
    ('core/solution.py', '_row_never_lever'): 'the one test for a single payment, from this module',
    ('core/solution.py', '_flexible_named'): 'a generic lever may name only a flexible category that is not never_lever',
    ('core/solution.py', '_headroom'): 'lever 1: ' + _CATS,
    ('core/solution.py', '_trims'): 'lever 4: a recurring item whose category or own row is never_lever is skipped',
    ('core/solution.py', '_overspend'): 'budget pressure: a protected / uncertain overspend is described, never priced',
    ('core/solution.py', 'solve_one_time_cost'): 'names only what _headroom / _trims / _flexible_named allow',
    ('core/solution.py', 'solve_monthly_cost'): 'names only what _flexible_named allows',
    ('core/solution.py', '_named_target'): 'an amount to free, attached to a category only through the helpers above',
    ('core/willingness.py', 'observed_readings'): 'the flexible readings: ' + _CATS,
    ('core/income_change.py', 'budget_follows'): 'budget lines offered to change: ' + _CATS,
    ('server.py', 'not_levers'): 'the one list the page reads: protected + uncertain + contracts + not spending',
    ('server.py', 'budget_not_levers'): 'serves not_levers to the page (_loadNotLevers)',
    ('server.py', 'large_charge_lesson'): 'a protected / uncertain charge, or an uncategorised row read as possibly care, is never priced',
    ('server.py', 'willingness_state'): 'display only: marks a category on the floor; offers nothing',
    ('server.py', 'budget_pressure_route'): _PASS,
    ('server.py', 'debt_decision_impact'): _PASS,
    ('server.py', 'ledger_lesson'): _PASS,
    ('server.py', '_proactive_candidates'): _PASS,
    ('server.py', 'report_teaching'): _PASS,
    ('server.py', 'byb_offers'): _PASS,
}
