# -*- coding: utf-8 -*-
"""The resolution-projection fixture — written BEFORE the projection it specifies.

`gw 2.0/RESOLVED_CONFLICT_CASES.md`, Q2 — CLOSED as design, implementation pending. The contract:

    resolution = kind · resolver · contradictions · post
    all four derived from the evidence chain at read time, never stored;
    travelling beside the current value and strength, and never becoming evidence.

**Provenance model this fixture assumes (HAZARD_AUDIT H4, 2026-09-12).** Every `E` event in
the histories below is treated as the EOB SOURCE stating its stance - a distinct source event.
That is correct for distinct documents and for testimony, and it is the only thing the record
can currently express: `Evidence.source` is a type with no referent, so two readings of ONE
EOB are byte-identical to two EOBs here. The 5,460 histories therefore demonstrate the
projection's behaviour under a model in which readings and sources are indistinguishable.
They do NOT establish that behaviour for a future model containing document identity and
readings, where two readings of one artefact are a parse dispute and not a source reversal
(`gw 2.0/ASSERTED_REFERENT_CASES.md` RA4, `REPARSE_CLUSTER_B_TEST.md` D3b). When a referent
exists, this fixture is re-pointed, not cited.

Q1 proved a refused value cannot bypass the consumer boundary. This fixture has to prove the
other half of the same shape for Q2:

    When a resolution projection exists, every consumer permitted to receive the current value
    receives the resolution with it, and no consumer can manufacture a resolution from the
    current value alone.

The dangerous case is the ordinary, permitted rank-3 result. A consumer holding

    value = 1250.00
    strength = rank 3

cannot tell `never contradicted` from `contradicted → resolved`, even though the model can.
That is the defect found twice already - sensitivity dying at rendering, the refusal never
reaching the consumer - and this fixture exists so it is not found a third time after the
projection is built.

**The oracle is embedded.** The derivation below is the one checked against every history of
length 1-6 (5,460 of them) in `RESOLVED_CONFLICT_CASES.md`, so an implementation is measured
against a definition that has already survived enumeration rather than against a handful of
expected rows. `--exhaustive` re-runs that enumeration against the implementation.

**Names are provisional.** `resolution(c, axis)` on a classification, and a `resolution` field
on what `narrator_facts` and `export_row` return, are what this fixture looks for. If the
implementation chooses different names the fixture changes, not the contract.

Run:  python tests/test_resolution_projection_fixture.py [--exhaustive]
"""
import itertools
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS, FAIL, PENDING = [], [], []


def check(name, condition):
    if condition is None:
        PENDING.append(name)
        print(f'  ....  {name}')
    elif condition:
        PASS.append(name)
        print(f'  OK    {name}')
    else:
        FAIL.append(name)
        print(f'  FAIL  {name}')


NEUTRAL = {'amount': 950.00, 'merchant': 'ACME HARDWARE', 'mcc': '5251',
           'category': 'Home', 'category_set_by': 'importer', 'date': '2026-03-09'}


# ── The oracle: the enumerated definition ───────────────────────────────────
def oracle(knowing):
    """knowing: [(source, supports), ...] in recorded order. Returns the four fields.

    resolver  = the first event after the last disagreement - the one that made the current
                conclusion current. NOT the last event (that definition was wrong on 42% of
                histories).
    kind      = partitions on the resolver's most recent prior stance: none / superseded /
                reaffirmation / self_reversal. One prior stance or none, so never two kinds.
    post      = every event after the resolver. All agree with current, by construction.
    """
    if not knowing:
        return {'kind': 'none', 'resolver': None, 'contradictions': 0, 'post': ()}
    cur = knowing[-1][1]
    dis = [i for i, (_, s) in enumerate(knowing) if s != cur]
    if not dis:
        return {'kind': 'none', 'resolver': None, 'contradictions': 0, 'post': ()}
    ri = dis[-1] + 1
    resolver = knowing[ri][0]
    prior = [s for src, s in knowing[:ri] if src == resolver]
    kind = ('superseded' if not prior
            else 'reaffirmation' if prior[-1] == cur
            else 'self_reversal')
    return {'kind': kind, 'resolver': resolver, 'contradictions': len(dis),
            'post': tuple(src for src, _ in knowing[ri + 1:])}


def history(m, *steps):
    c = m.classify(**NEUTRAL)
    for src, sup in steps:
        c = m.record_evidence(c, m.CONTENT, source=src, supports=sup)
    return c


def knowing_of(m, c):
    return [(e.source, e.supports) for e in m.evidence(c, m.CONTENT)
            if e.source in m.KNOWING_SOURCES]


def same(a, b):
    return (a.get('kind'), a.get('resolver'), a.get('contradictions'),
            tuple(a.get('post') or ())) == (b['kind'], b['resolver'], b['contradictions'],
                                             b['post'])


def run(m, exhaustive=False):
    U, E = m.USER_STATED, m.IMPORTED_EOB
    Y, N = True, False

    # Rob's table, with the third row's `post` corrected: the reaffirming U:y IS the resolver.
    TABLE = [
        ('U:y                 never contradicted',          [(U, Y)],
         dict(kind='none',          resolver=None, contradictions=0, post=())),
        ('E:n U:y             superseded',                  [(E, N), (U, Y)],
         dict(kind='superseded',    resolver=U,    contradictions=1, post=())),
        ('U:y E:n U:y         reaffirmation, post empty',   [(U, Y), (E, N), (U, Y)],
         dict(kind='reaffirmation', resolver=U,    contradictions=1, post=())),
        ('U:y E:n U:n         EOB resolved, user conceded', [(U, Y), (E, N), (U, N)],
         dict(kind='superseded',    resolver=E,    contradictions=1, post=(U,))),
        ('E:n U:y U:n         user reversed',               [(E, N), (U, Y), (U, N)],
         dict(kind='self_reversal', resolver=U,    contradictions=1, post=())),
        ('E:n U:y U:n E:n     user reversed, EOB agreed after', [(E, N), (U, Y), (U, N), (E, N)],
         dict(kind='self_reversal', resolver=U,    contradictions=1, post=(E,))),
        ('U:y U:n E:n U:y     flip-flop is a reversal',     [(U, Y), (U, N), (E, N), (U, Y)],
         dict(kind='self_reversal', resolver=U,    contradictions=2, post=())),
    ]

    print('\n0. The oracle agrees with the table (a check on the fixture itself)\n')
    for label, steps, expected in TABLE:
        got = oracle(knowing_of(m, history(m, *steps)))
        check(f'oracle: {label}', got == expected)

    print('\n1. The projection exists on a classification and matches the oracle\n')
    for label, steps, expected in TABLE:
        c = history(m, *steps)
        got = m.resolution(c, m.CONTENT)
        check(f'resolution(): {label}', same(got, expected))

    print('\n2. The projection is derived from the chain, not from the current value\n')
    h1 = history(m, (U, Y))
    h2 = history(m, (E, N), (U, Y))
    f1 = m.derive('balance', 1250.00, sources=(h1,))
    f2 = m.derive('balance', 1250.00, sources=(h2,))
    check('two histories with identical value and strength',
          f1.value == f2.value and m.strength_of(f1) == m.strength_of(f2))
    check('...have different resolutions, so the projection reads the chain',
          not same(m.resolution(h1, m.CONTENT), oracle(knowing_of(m, h2))))
    # If someone "derives" a resolution from (value, strength), it will be constant across
    # these two. The assertion above is what catches it.

    print('\n3. Every permitted consumer receives the resolution with the value\n')
    n1, n2 = m.narrator_facts(f1), m.narrator_facts(f2)
    check('narrator receives the number for both (rank 3, permitted)',
          n1.value == 1250.00 and n2.value == 1250.00)
    check('narrator receives a resolution beside it',
          hasattr(n1, 'resolution') and hasattr(n2, 'resolution'))
    check('narrator can tell never-contradicted from contradicted-then-resolved',
          getattr(n1, 'resolution', None) != getattr(n2, 'resolution', None))
    check('narrator\'s resolution for H2 is the chain\'s, not a summary of the value',
          same(getattr(n2, 'resolution', None) or {}, oracle(knowing_of(m, h2))))

    x1, x2 = m.export_row(f1), m.export_row(f2)
    check('export receives the number for both',
          x1.get('value') == 1250.00 and x2.get('value') == 1250.00)
    check('export receives a resolution beside it',
          'resolution' in x1 and 'resolution' in x2)
    check('export can tell never-contradicted from contradicted-then-resolved',
          x1.get('resolution') != x2.get('resolution'))
    check('backup inherits export\'s resolution as it inherits its value',
          m.backup_row(f2) == x2)

    print('\n4. The resolution is not evidence\n')
    # Contradiction count and kind must never move strength. H2 (superseded, 1 contradiction)
    # and H1 (none) are both rank 3; a projection that "penalises" a resolved conflict has
    # turned history into a confidence score, which Q2 forbids.
    check('a resolved conflict leaves strength exactly where the evidence puts it',
          m.strength_of(f2) == m.strength_of(f1))
    r1 = m.resolution(h1, m.CONTENT)
    r2 = m.resolution(h2, m.CONTENT)
    check('resolution carries no strength field of its own',
          'strength' not in (r1 or {}) and 'strength' not in (r2 or {}))

    print('\n5. Refused consumers receive the refusal, and the resolution does not leak the value\n')
    weak = m.record_evidence(m.classify(**NEUTRAL), m.COUNTERPARTY,
                             source=m.MERCHANT_MATCH, supports=True)
    wf = m.derive('balance', 1250.00, sources=(weak,))
    nw = m.narrator_facts(wf)
    check('a refused narrator still gets the refusal in the value slot (Q1 holds)',
          isinstance(nw.value, dict) and 'offered' in nw.value)
    res = getattr(nw, 'resolution', None)
    check('the resolution beside a refusal does not carry the value',
          res is None or 1250.00 not in (res.values() if isinstance(res, dict) else ()))

    print('\n6. Multi-source facts\n')
    both = m.derive('balance', 2500.00, sources=(h1, h2))
    check('a fact over several sources: resolution semantics are UNSPECIFIED here',
          None)

    if exhaustive:
        print('\n7. Every history to length 6 - the implementation against the oracle\n')
        U_, E_ = m.USER_STATED, m.IMPORTED_EOB
        EVENTS = [(U_, True), (U_, False), (E_, True), (E_, False)]
        bad, total = 0, 0
        for n in range(1, 7):
            for steps in itertools.product(EVENTS, repeat=n):
                c = history(m, *steps)
                total += 1
                if not same(m.resolution(c, m.CONTENT), oracle(knowing_of(m, c))):
                    bad += 1
        check(f'implementation matches the oracle on all {total} histories'
              + (f' ({bad} mismatches)' if bad else ''), bad == 0)


def describe():
    print('\nThe fixture, as a specification:\n')
    print('  resolution(c, axis) -> {kind, resolver, contradictions, post}, derived on read')
    print('    resolver  = the first event after the last disagreement')
    print('    kind      = none | superseded | reaffirmation | self_reversal,')
    print('                by the resolver\'s most recent prior stance')
    print('    post      = events after the resolver (all agree, by construction)')
    print('  narrator_facts() and export_row() carry `resolution` beside the value')
    print('  two facts with equal value and strength may have different resolutions')
    print('  a resolution never changes strength and carries none of its own')
    print('  a refused consumer\'s resolution does not leak the refused value')


def main():
    exhaustive = '--exhaustive' in sys.argv
    print('=' * 74)
    print('THE RESOLUTION-PROJECTION FIXTURE')
    print('=' * 74)
    try:
        from core import classification as model
        model.record_evidence
    except (ImportError, AttributeError):
        print('\nNo classifier.')
        return 1

    if not hasattr(model, 'resolution'):
        print('\nNo projection yet - core/classification.py has no resolution().')
        print('This file is the specification it has to satisfy.')
        describe()
        # Section 0 still runs: the fixture checks its own oracle against the table.
        U, E = model.USER_STATED, model.IMPORTED_EOB
        print('\n0. The oracle agrees with the table (a check on the fixture itself)\n')
        for label, steps, expected in [
            ('U:y E:n U:y   reaffirmation, post EMPTY', [(U, True), (E, False), (U, True)],
             dict(kind='reaffirmation', resolver=U, contradictions=1, post=())),
            ('U:y E:n U:n   EOB resolved, user in post', [(U, True), (E, False), (U, False)],
             dict(kind='superseded', resolver=E, contradictions=1, post=(U,))),
        ]:
            got = oracle(knowing_of(model, history(model, *steps)))
            check(f'oracle: {label}', got == expected)
        print(f'\n{len(PASS)} passed, {len(FAIL)} failed - every projection assertion is pending')
        return 1

    run(model, exhaustive=exhaustive)
    print(f'\n{len(PASS)} passed, {len(FAIL)} failed, {len(PENDING)} pending')
    return 1 if (FAIL or PENDING) else 0


if __name__ == '__main__':
    sys.exit(main())
