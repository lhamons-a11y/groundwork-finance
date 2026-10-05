"""The Willingness Layer, first build (blueprint Appendix F; `gw 2.0/WILLINGNESS_LAYER.md`, ruled 2026-09-27).

Two of F.6a's three channels, and what the solution engine may do with them:

  observed   E.2's readings of a budgeted category, each a CITATION of the edits and months it rests on:
             a cut that held (flexible), a cut the user later restored (sacred). Both rest on something the
             user DID to the budget. (Item 39, Rob 2026-10-05: the third reading - an envelope "kept through
             tight months" read as sacred - is removed. It concluded from what the user did not do, the
             nearest thing in the layer to inference from silence.) E.2a's probation: a cut that
             coincides with an income change is not classified - the correlation is shown as a fact and the
             classification is the user's to make.
  declared   what the user said, in their own words' place: protect a category, call it flexible, or release
             what they said before. Sovereign (F.6a): it beats every reading, is never mined for anything
             broader, and never decays (E.2b).
  inferred   NOT BUILT. The strategy label (F.6b) is ruled last and gated on a null model (W4).

Everything here is arithmetic over the inputs it is handed, recomputed on every call: nothing is cached and
nothing is written (ruling 2 - only what the user said is stored, and the server stores it). This module has
no database access at all; the one function that gathers its inputs lives in server.py, and a structural
test pins what that function may read (W6: never usage, never a dismissal).

The words matter as much as the arithmetic (F.4): a reading says what the record shows, never what the user
ought to do, and a declaration is never set against behaviour as a failing.
"""

from core.breaks import detect_break
from core.solution import MIN_MONTHS_OBSERVED, is_protected

# E.2a: an income change this large, beside a cut, is a correlated cause that has to be ruled out before
# the cut can be read as the user's own flexibility. A tenth is where a pay change stops being noise
# (rounding, a short month) and starts being able to explain a budget moving.
INCOME_CHANGE_SHARE = 0.10

# F.8 (BREAK_DETECTOR.md ruling 3): breaks in several categories count as one broad change when they begin
# within a month of each other and the categories carried at least this share of the spending before it.
# A quarter is where "a few envelopes moved" becomes "the household's spending moved": below it, the rest
# of the record is still the user's ordinary month, and suspending everything would hide more than it
# protects.
BROAD_SHARE = 0.25
_CONCLUDED = ('flexible', 'sacred')

STANCES = ('protect', 'flexible', 'release')

def _key(name):
    return (name or '').strip().lower()


def _month(d):
    return (d or '')[:7]


def _prev_month(m):
    y, mo = int(m[:4]), int(m[5:7])
    return f'{y - 1}-12' if mo == 1 else f'{y}-{mo - 1:02d}'


def _next_month(m):
    y, mo = int(m[:4]), int(m[5:7])
    return f'{y + 1}-01' if mo == 12 else f'{y}-{mo + 1:02d}'


def _income_correlation(cut_month, income):
    """E.2a: did income move beside this cut?

    Returns (state, fact). `state` is 'none' when both neighbouring months are recorded and neither moved
    by INCOME_CHANGE_SHARE, 'changed' when one did (the fact names it), and 'unknown' when the record does
    not hold the months needed to tell. Unknown is not 'none' - a month with no income rows is a month the
    ledger cannot speak about, not a month income stayed level (absence is not zero).
    """
    before = income.get(_prev_month(cut_month))
    after = [(m, income.get(m)) for m in (cut_month, _next_month(cut_month)) if income.get(m) is not None]
    if not before or not after:
        return 'unknown', None
    for m, amount in after:
        if abs(amount - before) / before >= INCOME_CHANGE_SHARE:
            return 'changed', {'from_month': _prev_month(cut_month), 'from': round(before, 2),
                               'month': m, 'to': round(amount, 2)}
    return 'none', None


def _reading(category, edits, spend, ledger_months, income):
    """One budgeted category's observed reading, with the receipts it rests on."""
    cuts = [e for e in edits if e['new'] < e['old']]
    base = {'category': category, 'source': 'observed'}

    if cuts:
        cut = cuts[-1]
        later = [e for e in edits if (e['date'], e['id']) > (cut['date'], cut['id'])]
        restore = next((e for e in later if e['new'] >= cut['old']), None)
        if restore:
            return {**base, 'stance': 'sacred', 'reason': 'restored',
                    'receipt': {'cut': cut, 'restore': restore}}

        cut_month = _month(cut['date'])
        after = sorted(m for m in ledger_months if m > cut_month)
        seen = [m for m in after if (category, m) in spend]
        if len(seen) < MIN_MONTHS_OBSERVED:
            return {**base, 'stance': 'unclassified', 'reason': 'too_soon',
                    'receipt': {'cut': cut, 'months_seen': len(seen)}}
        worst = max(spend.get((category, m), 0.0) for m in after)
        if worst > cut['new']:
            # A cut that did not hold is an answer too ("not this, not now", F.6), and not a verdict of
            # any kind - so it is not classified either way.
            return {**base, 'stance': 'unclassified', 'reason': 'did_not_hold',
                    'receipt': {'cut': cut, 'months': after}}
        state, fact = _income_correlation(cut_month, income)
        if state == 'changed':
            return {**base, 'stance': 'unclassified', 'reason': 'probation',
                    'receipt': {'cut': cut, 'months': seen, 'worst': round(worst, 2), 'income': fact}}
        if state == 'unknown':
            return {**base, 'stance': 'unclassified', 'reason': 'income_unrecorded',
                    'receipt': {'cut': cut, 'months': seen}}
        return {**base, 'stance': 'flexible', 'reason': 'cut_held',
                'receipt': {'cut': cut, 'months': seen, 'worst': round(worst, 2)}}

    # No edit, no reading: an envelope the user never cut is not read as one they keep (item 39).
    return {**base, 'stance': 'unclassified', 'reason': 'no_evidence', 'receipt': None}


def _months_apart(a, b):
    return abs((int(a[:4]) - int(b[:4])) * 12 + int(a[5:7]) - int(b[5:7]))


def _concluded(r):
    return r['stance'] in _CONCLUDED or r['reason'] == 'probation'


def breaks(categories, edits, spend, ledger_months, income, debits):
    """F.8's evidence boundaries: {'local': {category key: break}, 'broad': break or None}.

    A category's series is its spending in the months the ledger holds AND the category appears in. A month
    it is absent from is a gap, never a zero (absence is not zero), so a gap cannot make a break.

    A category break that begins within a month of the user's own budget edit to that category - the month
    before (people often spend less first and update the budget after), the month of it, or the month after -
    is **explained by that edit**. It is the behaviour the reading is about, not an unexplained
    discontinuity (E.2b: a break is what the model cannot explain), so it is no boundary for that category.
    Without this rule a cut that held would suspend its own reading.

    Broad (ruling 3): a break in recorded income, which is load-bearing by definition, or unexplained
    category breaks beginning within a month of each other whose categories carried at least BROAD_SHARE
    of spending before them. Broad reaches every reading; local reaches its own category.
    """
    months = sorted(ledger_months)
    local = {}
    for name in {c for c in categories if c}:
        series = [(m, spend[(name, m)]) for m in months if (name, m) in spend]
        b = detect_break(series)
        if not b:
            continue
        own = [_month(e['date']) for e in edits if _key(e['category']) == _key(name)]
        if any(b['month'] in (_prev_month(m), m, _next_month(m)) for m in own):
            continue
        local[_key(name)] = {**b, 'category': name, 'scope': 'category'}

    broad = None
    inc = detect_break(sorted(income.items()))
    if inc:
        broad = {**inc, 'scope': 'income'}
    else:
        # The largest set of local breaks starting within a month of each other.
        for anchor in sorted(local.values(), key=lambda b: b['month']):
            group = [b for b in local.values() if _months_apart(b['month'], anchor['month']) <= 1]
            first = min(b['month'] for b in group)
            prior = [debits[m] for m in months if m < first and m in debits]
            total = sorted(prior)[len(prior) // 2] if prior else 0.0
            share = sum(b['before'] for b in group) / total if total else 0.0
            if len(group) >= 2 and share >= BROAD_SHARE:
                broad = {'scope': 'together', 'month': first,
                         'categories': sorted(b['category'] for b in group),
                         'share': round(share, 3), 'parts': sorted(group, key=lambda b: b['category'])}
                break
    return {'local': local, 'broad': broad}


def _boundary_for(name, found):
    """The latest break reaching this category: its own, or a broad one."""
    reach = [b for b in (found['local'].get(_key(name)), found['broad']) if b]
    return max(reach, key=lambda b: b['month']) if reach else None


def observed_readings(categories, edits, spend, ledger_months, income, debits):
    """E.2's reading for each budgeted category not on the necessity floor.

    `categories`     the budgeted expense categories, by name
    `edits`          the user's budget edits: [{id, date 'YYYY-MM-DD', category, old, new}], oldest first
    `spend`          {(category, 'YYYY-MM'): debits} for months the ledger holds
    `ledger_months`  the complete months the ledger holds any spending in (the current month excluded)
    `income`         {'YYYY-MM': income} - only months with income on record appear
    `debits`         {'YYYY-MM': all debits}

    A floor category gets no reading: E.1 already keeps it out of every lever, and a reading there would
    be a claim with nothing to decide.
    """
    found = breaks(categories, edits, spend, ledger_months, income, debits)
    out = []
    for name in sorted({c for c in categories if c}, key=_key):
        if is_protected(name):
            continue
        mine = sorted((e for e in edits if _key(e['category']) == _key(name)), key=lambda e: (e['date'], e['id']))
        whole = _reading(name, mine, spend, ledger_months, income)
        b = _boundary_for(name, found)
        if not b:
            out.append(whole)
            continue
        # F.8 ruling 1: only evidence from the break on may support the current reading. Nothing is erased
        # - the edits and months before it stay in the record, and a set-aside reading keeps them as its
        # receipt - they are simply not admissible for behaviour after the break.
        since = b['month']
        bounded = _reading(name, [e for e in mine if _month(e['date']) >= since], spend,
                           {m for m in ledger_months if m >= since}, income)
        if _concluded(bounded):
            out.append({**bounded, 'boundary': b})
        elif _concluded(whole):
            out.append({'category': name, 'source': 'observed', 'stance': 'unclassified', 'reason': 'break',
                        'receipt': {'break': b, 'set_aside': whole}})
        else:
            out.append({**bounded, 'boundary': b})
    return out


def current_declarations(declarations):
    """The user's word as it stands now: the latest statement per category, releases removed.

    `declarations` is the whole history, oldest first. Nothing in it is ever rewritten - a changed mind is a
    newer row (ruling 5) - so "as it stands" is simply the last word said about each category.
    """
    last = {}
    for d in sorted(declarations, key=lambda d: (d['said_at'], d['id'])):
        last[_key(d['category'])] = d
    return {k: d for k, d in last.items() if d['stance'] != 'release'}


def effective(readings, declarations):
    """What the solution engine may use, per category key: {stance, source, reading?, declaration?}.

    The declared word beats every reading (E.2b); a reading stands where nothing was said. Stances out:
    'protected' (never a lever), 'flexible', 'sacred', 'unclassified'.
    """
    out = {}
    for r in readings:
        out[_key(r['category'])] = {'stance': r['stance'], 'source': 'observed', 'reading': r}
    for k, d in current_declarations(declarations).items():
        prior = out.get(k, {}).get('reading')
        out[k] = {'stance': 'protected' if d['stance'] == 'protect' else 'flexible',
                  'source': 'declared', 'declaration': d, 'reading': prior}
    return out


def annotate(candidates, eff, field='name'):
    """Attach the willingness a lever's candidates carry, and drop what the user protected.

    The server calls this on the raw material for levers 1 and 4 before the solution engine sees it, so the
    engine never has to know where willingness came from - only what it says.
    """
    out = []
    for c in candidates or []:
        w = eff.get(_key(c.get(field)))
        if w and w['stance'] == 'protected':
            continue
        if w:
            c = {**c, 'willingness': {'stance': w['stance'], 'source': w['source'],
                                      **({'reason': w['reading']['reason']}
                                         if w.get('reading') and w['source'] == 'observed' else {})}}
        out.append(c)
    return out


def claim_for(category, readings, declarations):
    """Is there something Groundwork has claimed about this category, that a statement could dispute?

    F.3: nothing is editable that is not first a claim with a receipt. A reading that concluded something
    (flexible, sacred, or E.2a's correlation shown as a fact) is a claim; so is a statement the user made
    earlier, which they may always change or release. 'too_soon', 'did_not_hold', 'income_unrecorded' and
    'no_evidence' concluded nothing, and there is nothing there to dispute.
    """
    k = _key(category)
    for r in readings:
        if _key(r['category']) == k and (_concluded(r) or r['reason'] == 'break'):
            return r
    if k in current_declarations(declarations):
        return {'category': category, 'source': 'declared'}
    return None
