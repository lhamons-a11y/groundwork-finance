# -*- coding: utf-8 -*-
"""Health-domain classification — what the evidence supports, and what may be done with it.

Implements `gw 2.0/CLASSIFICATION_QUESTION.md`, and it is specified by
`tests/test_classification_fixture.py`, which was written before this file existed.

Three layers, kept apart on purpose, because fusing them is the defect
`gw 2.0/ARCHITECTURE_PRINCIPLES.md` §1 keeps finding:

    classifier    what does the evidence support?      -> Axis, Determination
    sensitivity   what kind of information is this?    -> Sensitivity
    policy        what may the application do with it? -> the policy section

`is_protected` in `core/solution.py` is the fourth instance of that fusion — evidence,
classification and verdict in one expression — and it is deliberately left alone. When this
module has real callers it supplies the counterparty state and `is_protected` becomes one
consumer of it rather than the whole path.

**Two axes, and a wall between them.** A merchant match is certain about the counterparty and
silent about the content. No accumulation of counterparty evidence ever establishes what was
bought, so protection reads axis 1 and tax reads axis 2 and only axis 2. Their agreeing on a
given row is a coincidence, not a shared decision.

**Over-inclusion is no longer free, and the vocabulary here is tighter because of it.** The
necessity floor can afford a loose match: a near-miss costs one unavailable lever. This module
cannot, because a near-miss also manufactures a health suspicion about an ordinary transaction,
and by position 3 that manufactured suspicion is the *most* sensitive thing the system holds.
So the merchant terms below are narrow — `healthcare`, never bare `health`, which would take
OhioHealth and a health club with the same shrug.

Nothing here writes to a database. It is a pure interpretation layer over records the caller
holds, the same division of labour `core/solution.py` uses when it takes `months_observed` on
trust: the caller owns the ledger.
"""

from dataclasses import dataclass, field, replace
from datetime import datetime

# ── Rule identity ───────────────────────────────────────────────────────────
# Any interpretation that can change the meaning of a user-visible conclusion must be
# version-identifiable (principle 4). This is that version, and it is NOT
# `NECESSITY_FLOOR_VERSION` — the floor's vocabulary and this classifier's vocabulary
# change for different reasons and must be able to move independently.
#
# Bump on any change to the vocabularies below.
CLASSIFIER_RULE_VERSION = '1'

# The sentinel for "no definitive figure is available". Not zero, and deliberately not
# None — absence is not zero, and a consumer that wants a number must be made to say so.
# It lives here rather than in the test because a test-local sentinel could never compare
# identical to anything a model returns.
UNAVAILABLE = object()


# ── Axis names ──────────────────────────────────────────────────────────────
COUNTERPARTY = 'counterparty'
CONTENT = 'content'
AXES = (COUNTERPARTY, CONTENT)


# ── Evidence states ─────────────────────────────────────────────────────────
# Named in evidence terms, never policy terms. A state called
# SUPPORTED_HEALTH_CLASSIFICATION has already smuggled in a judgement — supported enough
# for *what?* — which is the separation this module exists to keep.
USER_ASSERTED = 'user_asserted'
IMPORTED_ATTESTED = 'imported_attested'
CORROBORATED = 'corroborated'
SINGLE_WEAK_SIGNAL = 'single_weak_signal'
CONTRADICTED = 'contradicted'
NOT_EVALUATED = 'not_evaluated'

# ── Resolution kinds ────────────────────────────────────────────────────────
# How the current conclusion on an axis came to be current - a projection of the evidence
# chain, never a judgement about it. `gw 2.0/RESOLVED_CONFLICT_CASES.md`, Q2. Named in
# history terms: none of these says anything about how strong the conclusion is.
RESOLUTION_NONE = 'none'               # no knowing source ever disagreed
SUPERSEDED = 'superseded'              # the resolver's first statement, after another source disagreed
REAFFIRMATION = 'reaffirmation'        # the resolver had stood for the current conclusion before
SELF_REVERSAL = 'self_reversal'        # the resolver had stood against it before

# States in which supporting evidence exists. This set, and not a threshold, is what
# puts a transaction inside the boundary.
SUPPORTING_STATES = frozenset((USER_ASSERTED, IMPORTED_ATTESTED,
                               CORROBORATED, SINGLE_WEAK_SIGNAL))

# ── Evidence sources ────────────────────────────────────────────────────────
# A typed enum rather than a confidence number. `never establish content on
# merchant_match alone` is checkable; `never below 0.8` is not.
USER_STATED = 'user_stated'
IMPORTED_EOB = 'imported_eob'
MERCHANT_MATCH = 'merchant_match'
MCC = 'mcc'
INFERRED = 'inferred'

# Sources that come from a party with knowledge of the transaction. Only these may take a
# transaction OUT of the boundary, and only these establish content.
KNOWING_SOURCES = frozenset((USER_STATED, IMPORTED_EOB))


# ── The vocabularies ────────────────────────────────────────────────────────
# Counterparty evidence only. None of this says what was bought.

HEALTH_MCC = frozenset((
    '4119',   # ambulance
    '5047',   # medical & dental equipment
    '5122',   # drugs, proprietaries
    '5912',   # drug stores and pharmacies
    '5975',   # hearing aids
    '5976',   # orthopedic goods
    '8011',   # doctors
    '8021',   # dentists
    '8031',   # osteopaths
    '8041',   # chiropractors
    '8042',   # optometrists
    '8043',   # opticians
    '8049',   # podiatrists
    '8050',   # nursing and personal care
    '8062',   # hospitals
    '8071',   # medical and dental labs
    '8099',   # medical services
))

# Narrow on purpose — see the module docstring. Bare 'health' is excluded: it would take
# a health club, and manufacturing a health suspicion about a gym membership is exactly
# the harm position 3 identifies.
HEALTH_MERCHANT_TERMS = (
    'pharmacy', 'drugstore', 'drug store', 'cvs', 'walgreens', 'rite aid',
    'hospital', 'clinic', 'urgent care', 'medical', 'dental', 'dentist',
    'orthodont', 'optometr', 'optical', 'radiolog', 'cardiolog', 'oncolog',
    'pediatric', 'obstetric', 'dermatolog', 'psychiatr', 'psycholog',
    'therapy', 'therapist', 'counseling', 'counselling', 'behavioral health',
    'mental health', 'healthcare', 'health center', 'health centre',
    'labcorp', 'quest diagnostics', 'anesthesi', 'surgery', 'surgical',
)

# Retailers that host a pharmacy counter. Exactly one weak signal: the money went
# somewhere that MIGHT have been the pharmacy, which is not nothing and is a long way
# from evidence.
MIXED_RETAIL_TERMS = (
    'target', 'walmart', 'costco', 'kroger', 'safeway', 'meijer', 'sams club',
    "sam's club", 'publix', 'wegmans',
)

# Category names that assert health CONTENT when a person chose them. The same string
# set by an importer is not this — see `_category_evidence`.
HEALTH_CATEGORY_TERMS = (
    'prescription', 'medication', 'pharmacy', 'medical', 'healthcare',
    'doctor', 'dental', 'vision care', 'therapy', 'mental health',
    'copay', 'co-pay', 'hospital', 'clinic',
)


# ── The classifier layer ────────────────────────────────────────────────────

@dataclass(frozen=True)
class Evidence:
    """One signal bearing on one axis. `amount` is set only when the evidence speaks to
    part of a charge — an EOB line inside a $150 supermarket trip."""
    axis: str
    source: str
    supports: bool
    amount: float = None
    recorded_at: str = None


@dataclass(frozen=True)
class Determination:
    """A current reading of one axis, superseded rather than overwritten.

    Carries its own evidence, the rule version that produced it and the date — because
    without those a rule change silently makes every prior judgement unreproducible,
    which is the C1 defect the necessity floor demonstrated, arriving here with sensitive
    information about a person instead of a budget verdict.
    """
    axis: str
    state: str
    evidence: tuple = ()
    rule_version: str = CLASSIFIER_RULE_VERSION
    determined_at: str = None


@dataclass(frozen=True)
class Axis:
    """What the evidence supports on one axis. Deliberately has no `confidence` and no
    `kind`: the first is an invented number waiting to be thresholded, the second would
    require ranking how disclosive a kind of care is."""
    name: str
    state: str


@dataclass(frozen=True)
class Sensitivity:
    """What kind of information this classification creates.

    Keyed on the QUESTION, not the verdict. Asking whether a named person's transaction is
    health-related creates health-domain information whatever the answer comes back as, so
    `contradicted` still carries a domain — the sensitive act was asking.

    `manufactured` is the inversion: a classification Groundwork inferred is information
    the user cannot correct, because they do not know it exists. No `degree`, ever.
    """
    domain: str = None
    manufactured: bool = False


@dataclass(frozen=True)
class Classification:
    amount: float = 0.0
    merchant: str = ''
    mcc: str = ''
    category: str = ''
    category_set_by: str = 'importer'
    date: str = None
    determinations: tuple = ()
    surfaced: bool = False


def _now():
    return datetime.utcnow().isoformat(timespec='seconds')


def _matches(text, terms):
    t = (text or '').strip().lower()
    return bool(t) and any(term in t for term in terms)


def _counterparty_evidence(merchant, mcc, category, category_set_by):
    """Signals about who received the money. Never about what was bought."""
    out = []
    if _matches(merchant, HEALTH_MERCHANT_TERMS):
        out.append(Evidence(COUNTERPARTY, MERCHANT_MATCH, True, recorded_at=_now()))
    elif _matches(merchant, MIXED_RETAIL_TERMS):
        # A pharmacy counter inside a supermarket. One weak signal, and it stays one:
        # this is the state the whole fail-closed zone was written for.
        out.append(Evidence(COUNTERPARTY, MERCHANT_MATCH, True, recorded_at=_now()))
    if str(mcc or '') in HEALTH_MCC:
        out.append(Evidence(COUNTERPARTY, MCC, True, recorded_at=_now()))
    if category_set_by != 'user' and _matches(category, HEALTH_CATEGORY_TERMS):
        # An importer-assigned health-looking category is a derived label, not a person's
        # statement, so it is counterparty-grade at best.
        out.append(Evidence(COUNTERPARTY, INFERRED, True, recorded_at=_now()))
    return out


def _category_evidence(category, category_set_by):
    """The pair the whole document turns on.

    A category is not evidence — it is an interpretation already applied, and WHOSE
    interpretation decides which axis it lands on. Set by the user it is a statement about
    what was bought; assigned by the importer it says only where the money went. Two
    transactions with identical category strings, different tax treatment, and no
    inspection of the string can tell them apart.
    """
    if category_set_by == 'user' and _matches(category, HEALTH_CATEGORY_TERMS):
        return [Evidence(CONTENT, USER_STATED, True, recorded_at=_now())]
    return []


def _state_from(evidence):
    """Summarise all evidence on one axis into a state.

    Knowing-party evidence supersedes: a merchant rule may never overturn what a person or
    an EOB said, in either direction. That asymmetry is what makes `contradicted` sticky,
    and without it the user answers "no, it was a birthday card" and is asked again next
    month.

    **`knowing[-1]` is valid only while the knowing sequence is in evidence-time order**
    (HAZARD_AUDIT H3 / R2). Among equal knowing parties the most recent stance is current
    (Q2), and "most recent" means on the evidence's own time: when an utterance was made, or
    a document's own as-of. `Evidence.recorded_at` is the import clock and a document's as-of
    is not represented, so position stands in for time. That holds by construction - only
    `record_evidence` appends, and the fixture asserts nothing else does - for stances
    recorded when learned, and it is NOT guaranteed for a document whose date precedes an
    utterance imported before it. Sorting by `recorded_at` would not repair this; it would
    encode import order under a better name. The repair is representation, not here.
    """
    ev = list(evidence)
    if not ev:
        return NOT_EVALUATED

    knowing = [e for e in ev if e.source in KNOWING_SOURCES]
    if knowing:
        latest = knowing[-1]
        if not latest.supports:
            return CONTRADICTED
        return USER_ASSERTED if latest.source == USER_STATED else IMPORTED_ATTESTED

    supporting = [e for e in ev if e.supports]
    distinct = {e.source for e in supporting}
    if len(distinct) >= 2:
        return CORROBORATED
    if supporting:
        return SINGLE_WEAK_SIGNAL
    return NOT_EVALUATED


def _determine(axis, evidence, rule_version=CLASSIFIER_RULE_VERSION):
    return Determination(axis=axis, state=_state_from(evidence),
                         evidence=tuple(evidence), rule_version=rule_version,
                         determined_at=_now())


def classify(amount=0.0, merchant='', mcc='', category='', category_set_by='importer',
             date=None, rule_version=CLASSIFIER_RULE_VERSION):
    """Read one raw transaction into two axis determinations.

    An initial determination is recorded for BOTH axes even when the state is
    `not_evaluated`, because an absence has provenance too: *nothing here bore on this
    question, under rule version N, on this date* is a finding, and a later reader needs
    to tell it from *we never looked*.
    """
    cp = _counterparty_evidence(merchant, mcc, category, category_set_by)
    ct = _category_evidence(category, category_set_by)
    return Classification(
        amount=float(amount or 0.0), merchant=merchant or '', mcc=str(mcc or ''),
        category=category or '', category_set_by=category_set_by, date=date,
        determinations=(_determine(COUNTERPARTY, cp, rule_version),
                        _determine(CONTENT, ct, rule_version)))


def determinations(c, axis):
    """Every determination for one axis, oldest first. Superseded, never overwritten."""
    src = getattr(c, 'classification', c)
    return [d for d in src.determinations if d.axis == axis]


def determination(c, axis):
    """The current determination for one axis."""
    return determinations(c, axis)[-1]


def axis(c, name):
    return Axis(name=name, state=determination(c, name).state)


def evidence(c, axis_name):
    return determination(c, axis_name).evidence


def resolution(c, axis_name):
    """How the current conclusion on this axis was reached. A read-time projection of the
    evidence chain, and deliberately nothing more.

    This function does not evaluate evidence, rank sources, or compute confidence. It reads
    the knowing evidence in order and reports the shape of the history:

        resolver        the event that made the current conclusion current - the FIRST
                        knowing event after the last disagreement. Not the most recent
                        event: that definition was wrong on 42% of all histories to length 6.
        kind            by the resolver's most recent prior stance on this axis - none if no
                        source ever disagreed; superseded if the resolver had no prior stance;
                        reaffirmation if it last stood for the current conclusion;
                        self_reversal if it last stood against it. Exactly one prior stance
                        or none, so exactly one kind.
        contradictions  how many knowing events disagreed with the current conclusion. A
                        count of history, never a confidence score.
        post            the sources of every knowing event strictly after the resolver. All
                        agree with the current conclusion, by construction - and the user
                        conceding after a document overrode them lives here, not in `kind`.

    Derived on every read and never stored, for the reason `strength_of` is: a stored
    summary can drift from the record it summarises. Appending an agreeing event changes
    neither `kind` nor `resolver` - a resolution is a fixed historical event.

    Checked against every history of length 1-6 over {user, EOB} x {yes, no}: 5,460 of them.

    **Domain (HAZARD_AUDIT H4).** The kinds above describe SOURCE history: each knowing event
    is taken to be a distinct source stating its stance. That is correct for utterances and
    for distinct documents - `self_reversal by imported_eob` when two EOBs from the insurer
    disagree is what happened. It is NOT applicable to two readings of one artefact - one EOB
    parsed twice - which is a parse dispute and not a source reversing itself; the record
    cannot currently distinguish the two, because `Evidence.source` is a type and carries no
    referent, so this projection cannot either. It also assumes the ordering `_state_from`
    assumes: position stands in for evidence time, guaranteed by construction and not for
    late-arriving documents. Neither is repaired here; both are representation.
    How the current conclusion on this axis was reached. A read-time projection of the
    evidence chain, and deliberately nothing more.

    This function does not evaluate evidence, rank sources, or compute confidence. It reads
    the knowing evidence in order and reports the shape of the history:

        resolver        the event that made the current conclusion current - the FIRST
                        knowing event after the last disagreement. Not the most recent
                        event: that definition was wrong on 42% of all histories to length 6.
        kind            by the resolver's most recent prior stance on this axis - none if no
                        source ever disagreed; superseded if the resolver had no prior stance;
                        reaffirmation if it last stood for the current conclusion;
                        self_reversal if it last stood against it. Exactly one prior stance
                        or none, so exactly one kind.
        contradictions  how many knowing events disagreed with the current conclusion. A
                        count of history, never a confidence score.
        post            the sources of every knowing event strictly after the resolver. All
                        agree with the current conclusion, by construction - and the user
                        conceding after a document overrode them lives here, not in `kind`.

    Derived on every read and never stored, for the reason `strength_of` is: a stored
    summary can drift from the record it summarises. Appending an agreeing event changes
    neither `kind` nor `resolver` - a resolution is a fixed historical event.

    Checked against every history of length 1-6 over {user, EOB} x {yes, no}: 5,460 of them.

    **Domain (HAZARD_AUDIT H4).** The kinds above describe SOURCE history: each knowing event
    is taken to be a distinct source stating its stance. That is correct for utterances and
    for distinct documents - `self_reversal by imported_eob` when two EOBs from the insurer
    disagree is what happened. It is NOT applicable to two readings of one artefact - one EOB
    parsed twice - which is a parse dispute and not a source reversing itself; the record
    cannot currently distinguish the two, because `Evidence.source` is a type and carries no
    referent, so this projection cannot either. It also assumes the ordering `_state_from`
    assumes: position stands in for evidence time, guaranteed by construction and not for
    late-arriving documents. Neither is repaired here; both are representation.

    Domain (HAZARD_AUDIT H4): source-history kinds over knowing events - correct where each knowing
    event is a distinct source stance (utterances, distinct documents); NOT applicable to multiple
    readings of one artefact, which this 1.x record cannot distinguish. The reading-level answer
    exists in the 2.0 substrate as core.database.parse_disputes (item 7, pass 7A) - a derivation
    this projection may not read past and never resolves.
    """
    knowing = [(e.source, e.supports) for e in evidence(c, axis_name)
               if e.source in KNOWING_SOURCES]
    none = {'kind': RESOLUTION_NONE, 'resolver': None, 'contradictions': 0, 'post': ()}
    if not knowing:
        return none
    current = knowing[-1][1]
    dissent = [i for i, (_, supports) in enumerate(knowing) if supports != current]
    if not dissent:
        return none
    ri = dissent[-1] + 1                       # exists: the last event agrees with itself
    resolver = knowing[ri][0]
    prior = [supports for source, supports in knowing[:ri] if source == resolver]
    kind = (SUPERSEDED if not prior
            else REAFFIRMATION if prior[-1] == current
            else SELF_REVERSAL)
    return {'kind': kind,
            'resolver': resolver,
            'contradictions': len(dissent),
            'post': tuple(source for source, _ in knowing[ri + 1:])}


def record_evidence(c, axis_name, source=None, supports=True, amount=None,
                    rule_version=CLASSIFIER_RULE_VERSION):
    """Add one signal and re-determine that axis, returning a NEW classification.

    The prior determination survives in place; a later reader can still see what was
    concluded before, on what evidence, under which rule.
    """
    src = getattr(c, 'classification', c)
    prior = determination(src, axis_name)
    ev = prior.evidence + (Evidence(axis_name, source, bool(supports), amount,
                                    recorded_at=_now()),)
    return replace(src, determinations=src.determinations
                   + (_determine(axis_name, ev, rule_version),))


def with_rules(version):
    """A view of this classifier pinned to a rule version.

    A new version may classify differently. It may not change what the old one concluded —
    that is principle 4, and the reason `reproduce` exists.
    """
    return _PinnedRules(version)


@dataclass(frozen=True)
class _PinnedRules:
    version: str

    def classify(self, **kw):
        kw.setdefault('rule_version', self.version)
        return classify(**kw)


def reproduce(det):
    """Rebuild the classification a determination recorded, under its own rule version."""
    return _Reproduced(rule_version=det.rule_version,
                       determinations=(det,))


@dataclass(frozen=True)
class _Reproduced:
    rule_version: str
    determinations: tuple


# ── The sensitivity layer ───────────────────────────────────────────────────

def sensitivity(c):
    """What kind of information this classification creates.

    Domain attaches the moment any evidence bearing on a health-domain claim exists —
    including evidence AGAINST, because a stored row saying *evaluated for health
    relevance, not supported* still discloses that this transaction was health-suspicious
    enough to evaluate.
    """
    # A derived fact already carries the sensitivity of what produced it, and that is the
    # whole point of P0-3: the health context is gone by the time the figure exists, so it
    # has to have been attached upstream rather than re-derived here.
    carried = getattr(c, 'sensitivity', None)
    if isinstance(carried, Sensitivity):
        return carried

    src = getattr(c, 'classification', c)
    all_ev = [e for axis_name in AXES for e in evidence(src, axis_name)]
    if not all_ev:
        return Sensitivity(domain=None, manufactured=False)
    told = any(e.source in KNOWING_SOURCES for e in all_ev)
    return Sensitivity(domain='health', manufactured=not told)


@dataclass(frozen=True)
class DerivedFact:
    """A figure computed from classified records. Carries the sensitivity of what produced
    it, because 'spending increased 20%' contains no medical word and is still health
    information — and a `if health_context: refuse` check is useless by the time the
    sentence exists."""
    metric: str
    value: float
    sensitivity: Sensitivity
    sources: tuple = ()


@dataclass(frozen=True)
class NarratorFacts:
    """What the narrator is allowed to see. Never the underlying records.

    **Carries no sensitivity, and that is a known loss, not a contract (HAZARD_AUDIT H5).**
    `DerivedFact` arrives here with `Sensitivity(domain, manufactured)` and leaves without it:
    a figure over two manufactured health rows reaches the narrator as `category_delta:Other`,
    accurate to the dollar and unmarked (`gw 2.0/SENSITIVITY_TRACE_CASES.md`). Where the
    marking must go is ruled: to the components that ENFORCE - a refusal at the boundary, a
    check at the gate - and **never into the findings text the model reads**, because at
    `callAI()` what the model is given is what it is permitted to say (R8), so serialising
    sensitivity into the prompt would grant the model the word rather than restrict it
    (`NARRATOR_VOICE_PERMISSION_TEST.md`, ruled). Until a gate-side carrier exists, no
    findings assembler may read `DerivedFact.sensitivity` and put it in the prompt; the
    consumer-boundary fixture scans application files for exactly that read.
    """
    metric: str
    # A float, or the refusal that stands in its place. Annotating this `float` would be
    # the lie that made the bypass below easy to write in the first place.
    value: object
    includes_records: bool = False
    # How the conclusion behind `value` was reached (Q2). Beside the value, never inside
    # its strength: a rank-3 figure that overrode a contradicting EOB and a rank-3 figure
    # nothing ever contradicted are the same number and different histories.
    resolution: object = None


def category_delta(classifications, category, month=None, from_month=None):
    """Month-over-month movement in one category, as a sensitivity-carrying derived fact.

    The caller supplies the records; this module does not read the ledger.
    """
    rows = [c for c in classifications if (c.category or '').lower() == category.lower()]
    this_month = sum(c.amount for c in rows if (c.date or '').startswith(month or ''))
    prior = sum(c.amount for c in rows if (c.date or '').startswith(from_month or ''))
    contributing = [sensitivity(c) for c in rows]
    domain = 'health' if any(s.domain == 'health' for s in contributing) else None
    return DerivedFact(
        metric='category_delta:%s' % category,
        value=round(this_month - prior, 2),
        sensitivity=Sensitivity(domain=domain,
                                manufactured=any(s.manufactured for s in contributing)),
        sources=tuple(rows))


# ── The consumer helpers, and the boundary they must not step around ────────
# `narrator` and `export` are declared in `CONSUMER_STRENGTH`. These two functions build
# what those consumers receive, so they are the paths on which the declared requirement has
# to be applied — and until `EVIDENCE_MATRIX.md` Q1 they read `derived.value` directly and
# applied nothing. A declared permission is not a boundary unless EVERY path by which that
# consumer obtains a fact passes through the same check.
#
# What a refused consumer receives is the refusal itself, in the value's place, carrying
# `offered`, `reason`, `required` and `consumer` (Q1). Not omission — absence changes a
# total silently and a blank cell is a zero to a spreadsheet. Not a bare sentinel — that
# would collapse `not_evaluated`, `contradicted` and `single_weak_signal` into one word at
# the last inch, undoing what `_prefer_contradicted` exists to protect. Not an exception —
# an export that dies on one contradicted row is worse than one that marks it.
#
# Whether any of those fields is SHOWN to a person is a separate, downstream decision, and
# deliberately not made here.

def _permitted_value(derived, consumer):
    """The number if this consumer may have it, otherwise the refusal that explains why."""
    denied = refusal(derived, consumer)
    return denied if denied is not None else consume(derived, consumer)


def _fact_resolution(derived):
    """The resolution a derived fact carries to its consumers.

    A fact over ONE source carries that source's content-axis resolution - content is the
    axis knowing sources establish. A fact over several sources carries None: how the
    resolutions of several chains combine is UNSPECIFIED in Q2, marked pending in the
    fixture, and not something a fold written here should decide.
    """
    if len(derived.sources) != 1:
        return None
    return resolution(derived.sources[0], CONTENT)


def narrator_facts(derived):
    return NarratorFacts(metric=derived.metric,
                         value=_permitted_value(derived, 'narrator'),
                         includes_records=False,
                         resolution=_fact_resolution(derived))


def export_row(derived):
    return {'metric': derived.metric,
            'value': _permitted_value(derived, 'export'),
            'sensitivity': derived.sensitivity.domain,
            'resolution': _fact_resolution(derived)}


def backup_row(derived):
    # Backup is NOT in `CONSUMER_STRENGTH`, so it has never declared what it requires —
    # it borrows export's by delegating here. That is the shipped behaviour and it is left
    # exactly as found: giving backup its own entry is a decision about what a backup is
    # allowed to contain, and Q1 was not that decision.
    return export_row(derived)


# ── The policy layer ────────────────────────────────────────────────────────
# Which consumer may read which axis. Getting this table wrong is the defect the whole
# document exists to prevent, so it is data rather than scattered conditionals.
CONSUMER_AXES = {
    'lever_eligibility': (COUNTERPARTY,),
    'tax_qualifying': (CONTENT,),
}


def reads(consumer):
    return CONSUMER_AXES[consumer]


def inside_boundary(c):
    """Entered by a signal EXISTING, not by its strength.

    Global fail-closed would make every unknown transaction unavailable as a lever and
    disable the solution engine for users with no healthcare data at all. A user with no
    health signals is never inside, and §6.1 behaves exactly as it does today.
    """
    return any(axis(c, name).state in SUPPORTING_STATES for name in AXES)


def is_lever_candidate(c):
    """Protection reads the counterparty axis, and over-includes: inside the boundary is
    not offered, whatever the content axis says."""
    return not inside_boundary(c)


def qualifying_amount(c):
    """Tax reads the content axis and ONLY the content axis.

    No axis-1-only classification may establish a qualifying amount. That is the wall, and
    it is the pre-registered falsification criterion: if this function ever consults the
    counterparty axis, the two-axis model has collapsed back into one classification with
    two thresholds.
    """
    state = axis(c, CONTENT).state
    if state not in (USER_ASSERTED, IMPORTED_ATTESTED):
        return 0.00
    attested = [e.amount for e in evidence(c, CONTENT)
                if e.supports and e.amount is not None]
    # HAZARD_AUDIT H3 / R4. Two supporting readings that disagree about the amount - one EOB
    # parsed as $412 and again as $4.12 - are a parse dispute, and a parse dispute is resolved
    # by re-reading the artefact, never by which reading was appended last. Until the record
    # can hold that resolution, the figure is UNAVAILABLE: a refusal the tax consumer already
    # knows how to receive. Equal readings are not a dispute; one reading is not a dispute.
    if len(set(attested)) > 1:
        return UNAVAILABLE
    src = getattr(c, 'classification', c)
    return round(attested[0] if attested else src.amount, 2)


@dataclass(frozen=True)
class QualifyingTotal:
    attested: float
    unevaluated_count: int
    evaluated_count: int
    definitive: object
    rules: str = None


def qualifying_total(classifications, rules=None):
    """Attested, unevaluated, and no definitive figure while anything is unevaluated.

    '43 unevaluated' and '43 reviewed, none qualifying' are different claims about
    completeness. Both qualify $0.00; only one of them was looked at — which is the second
    consumer that must tell `contradicted` from `not_evaluated`.
    """
    rows = list(classifications)
    amounts = [qualifying_amount(c) for c in rows]
    unevaluated = [c for c in rows if axis(c, CONTENT).state == NOT_EVALUATED]
    # A disputed amount (R4) has no figure. Summing the others and presenting the result as
    # `attested` would omit a row silently - absence read as zero, the failure Q1 refused at
    # the consumer boundary. So a dispute anywhere makes the attested total UNAVAILABLE as
    # well as the definitive one. Whether "evaluated but disputed" deserves its own count,
    # distinct from "unevaluated", is a representation question deliberately not answered
    # here (H3 ruling): the sentinel fails closed; it does not yet say why.
    disputed = any(a is UNAVAILABLE for a in amounts)
    attested = UNAVAILABLE if disputed else round(sum(amounts), 2)
    return QualifyingTotal(
        attested=attested,
        unevaluated_count=len(unevaluated),
        evaluated_count=len(rows) - len(unevaluated),
        definitive=UNAVAILABLE if (unevaluated or disputed) else attested,
        rules=rules)


# ── Surfacing, and the no-silent-learning boundary ──────────────────────────
# A stored suspicion the user has never seen is an unsurfaced observation that persists,
# which the boundary forbids outright. Appendix A.1's Passive tier is what resolves it:
# visible where the user meets it, no prompt, no budget draw. Persistence follows the
# RENDER, not the answer — and the standard is availability, not confirmation of
# attention, the same standard already accepted for passively-surfaced settings changes.

# A.2.1's thresholds. A classification question has no goal impact by construction: it
# changes what Groundwork knows, not what the user's money does.
MATERIALITY_BUDGET_FRACTION = 0.05
MATERIALITY_GOAL_DAYS = 14


@dataclass(frozen=True)
class Marker:
    """The Passive form. Lives on the transaction row; never interrupts."""
    classification: Classification
    tier: str = 'passive'
    draws_budget: bool = False
    asks_for: str = 'fact'
    goal_impact_days: float = 0.0
    budget_fraction: float = 0.0
    surfaced: bool = True
    # The marker is about the TRANSACTION. Inferring which household member is ill is the
    # most disclosive thing this module could do, and it would be inferred rather than
    # told — so no person is named, suggested or defaulted, even where history would
    # support a guess.
    person: str = None
    suggested_person: str = None


@dataclass(frozen=True)
class ReviewOffer:
    """The one proactive form that clears the gauntlet honestly: aggregated and seasonal.

    Material because it moves a deduction, actionable because reviewing is the path, and
    perishable in A.3's strict sense — a filing deadline is a window closing by a known
    amount, not a predicted trajectory.
    """
    population: tuple
    amount: float
    season: str
    tier: str = 'proactive'
    # A new prompt-kind joins the budget its attention cost resembles; it does not mint
    # its own. An unsolicited interruption asking the user to resolve something is a
    # brake's attention cost.
    budget: str = 'brake'
    crosses_goal_boundary: bool = True


def surface(c):
    """Render the unresolved marker on the transaction row, which is what makes persisting
    it legitimate."""
    src = getattr(c, 'classification', c)
    return Marker(classification=replace(src, surfaced=True))


def is_persisted(x):
    return bool(getattr(x, 'surfaced', False))


def answer(marker, content_is_health=True, source=USER_STATED):
    """The direct question for a missing FACT — never for a commitment."""
    return record_evidence(marker.classification, CONTENT, source=source,
                           supports=bool(content_is_health))


def review_offer(classifications, season=None):
    population = [c for c in classifications
                  if inside_boundary(c) and axis(c, CONTENT).state == NOT_EVALUATED]
    return ReviewOffer(population=tuple(population),
                       amount=round(sum(c.amount for c in population), 2),
                       season=season)


def gauntlet(candidate, monthly_budget=None):
    """A.2's five gates, evaluated honestly for whichever candidate is offered.

    A single classification question fails at the first gate and will essentially always
    fail it — which is the correct outcome rather than a problem to engineer around.
    Strictness is free: a sub-threshold insight is not lost, it stays Passive.
    """
    if isinstance(candidate, ReviewOffer):
        material = bool(candidate.population) and candidate.crosses_goal_boundary
        # Bad news with a path: the population is reviewable, one row at a time.
        actionable = bool(candidate.population)
        return {'materiality': material, 'actionability': actionable,
                'novelty': True, 'budget': True, 'timing': True}

    days = getattr(candidate, 'goal_impact_days', 0.0)
    fraction = getattr(candidate, 'budget_fraction', 0.0)
    material = days >= MATERIALITY_GOAL_DAYS or fraction >= MATERIALITY_BUDGET_FRACTION
    return {'materiality': material,
            # Not bad news, so there is no §6 solution to require — and the gate exists
            # to stop bad news arriving without a path.
            'actionability': False,
            'novelty': True, 'budget': True, 'timing': True}


def can_promote(candidate, monthly_budget=None):
    return all(gauntlet(candidate, monthly_budget).values())


# ── Evidence strength: the weakest material link ────────────────────────────
# A lattice rather than a number, for the reason `classification_confidence` was refused: a
# float invites a threshold, and a threshold is an invented policy. These are the states that
# already exist, ordered by how much they establish.
#
# `not_evaluated` and `contradicted` share a floor and stay distinct - principle 2. Nothing
# supports the claim either way, and *we never looked* is not *we looked and found against it*.
STRENGTH = (NOT_EVALUATED, CONTRADICTED, SINGLE_WEAK_SIGNAL, CORROBORATED,
            IMPORTED_ATTESTED, USER_ASSERTED)

_RANK = {
    NOT_EVALUATED: 0,
    CONTRADICTED: 0,
    SINGLE_WEAK_SIGNAL: 1,
    CORROBORATED: 2,
    IMPORTED_ATTESTED: 3,
    USER_ASSERTED: 3,
}

# What each consumer requires before it may take a value. A surface absent from this table
# cannot consume anything at all, which is the enforcement: adding a consumer means stating
# what it needs, and forgetting to state it fails closed rather than open.
CONSUMER_STRENGTH = {
    # Protection over-includes, so a single weak signal is enough to withhold a lever - the
    # error is cheap in that direction and expensive in the other.
    'lever_eligibility': SINGLE_WEAK_SIGNAL,
    # A tax line is the one place being wrong has a legal consequence for the user, so it
    # takes nothing an interested party did not attest.
    'tax_qualifying': CORROBORATED,
    'narrator': CORROBORATED,
    'export': SINGLE_WEAK_SIGNAL,
}


def strength_rank(state):
    """Where a state sits in the lattice. Equal ranks are deliberate, not sloppy."""
    return _RANK[state]


def consumers():
    return tuple(CONSUMER_STRENGTH)


def required_strength(consumer):
    return CONSUMER_STRENGTH.get(consumer)


def strength_of(fact):
    """The evidentiary strength of a classification or a derived fact.

    For a classification: the **best-supported axis**, because either axis supporting the claim
    is what makes it health-domain at all.

    For a derived fact: the **weakest material source**, computed on every read rather than
    stored — so invalidating a source invalidates everything derived from it without anything
    having to remember to recompute.
    """
    src = getattr(fact, 'sources', None)
    if src is None:
        states = [axis(fact, name).state for name in AXES]
        # Best axis. `contradicted` and `not_evaluated` tie on rank, and at that tie the
        # answer must be `contradicted` — *we looked and found against it* is the finding,
        # and reporting *we never looked* instead throws away the only thing that was
        # established. Principle 2: the states share a floor and must not merge on the way
        # out either.
        return sorted(states, key=lambda st: (_RANK[st], _prefer_contradicted(st)))[-1]

    material = [x for x in src if _is_material(x)]
    if not material:
        return NOT_EVALUATED
    # Weakest source, with the same tie broken the same way — so a contradicted source in
    # the chain is named as contradicted rather than disappearing into "unevaluated".
    weakest = sorted(material,
                     key=lambda x: (_RANK[strength_of(x)],
                                    1 - _prefer_contradicted(strength_of(x))))[0]
    return strength_of(weakest)


def _prefer_contradicted(state):
    """1 for `contradicted`, 0 otherwise — the tie-break at the floor.

    Used ascending when picking the best axis (so contradicted sorts last, and is taken) and
    inverted when picking the weakest source (so it sorts first, and is taken). Same
    preference, opposite ends.
    """
    return 1 if state == CONTRADICTED else 0


def _is_material(source):
    """A source that contributes nothing cannot weaken what it did not build."""
    amount = getattr(source, 'amount', None)
    if amount is None:
        return True
    return abs(float(amount)) > 0


def derive(metric, value, sources=()):
    """Build a derived fact from named sources.

    There is no way to construct one without them: a fact with no provenance is exactly the
    thing this module exists to refuse.
    """
    rows = tuple(sources)
    contributing = [sensitivity(x) for x in rows]
    domain = 'health' if any(s.domain == 'health' for s in contributing) else None
    return DerivedFact(
        metric=metric,
        value=round(float(value), 2),
        sensitivity=Sensitivity(domain=domain,
                                manufactured=any(s.manufactured for s in contributing)),
        sources=rows)


def refusal(fact, by=None):
    """Why a consumer was refused, in the terms the decision was made in."""
    need = required_strength(by)
    if need is None:
        return {'consumer': by, 'reason': 'consumer has not declared a required strength',
                'offered': strength_of(fact)}
    have = strength_of(fact)
    if strength_rank(have) < strength_rank(need):
        return {'consumer': by, 'reason': 'evidence weaker than this consumer requires',
                'required': need, 'offered': have}
    return None


def consume(fact, by=None):
    """The only way to take a value out of a derived fact.

    Returns `UNAVAILABLE` rather than a number when the evidence is weaker than the consumer
    requires, or when the consumer never said what it requires. Two facts with identical values
    and different strengths are therefore **not interchangeable**, which is the whole point:
    the number is not the fact.
    """
    if refusal(fact, by) is not None:
        return UNAVAILABLE
    return fact.value
