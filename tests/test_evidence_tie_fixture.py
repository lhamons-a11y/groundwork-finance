# -*- coding: utf-8 -*-
"""The equal-rank tie fixture — can two knowing sources disagree without an invented winner?

`gw 2.0/EVIDENCE_MATRIX.md` findings 1 and 2, and gap 15's third open case.

`USER_STATED` and `IMPORTED_EOB` are both in `KNOWING_SOURCES` and both sit at rank 3 in
`_RANK`. That equality is deliberate — gap 15 recorded that asserting *manual wins* would be
**inventing a hierarchy the model does not have**, and left the answer as: keep an explicit tie
state.

`_state_from` then resolves knowing evidence with:

    latest = knowing[-1]

So the tie that was deliberately not broken at rank 3 **is broken further down by list
position**. The winner gap 15 refused to invent arrives anyway, by accident.

Two separable claims, and this fixture keeps them apart because they have different fixes:

    ORDER INDEPENDENCE   two knowing sources disagreeing must not resolve on which was
                         appended second - there is no fact of the matter in the order
    TEMPORAL ORDER       `knowing[-1]` is described as *the latest*. It is the last element
                         of a list. Evidence carries `recorded_at` and it is never consulted

**The second is latent today and will not stay that way.** `record_evidence` always appends in
call order, so position and time coincide through the only public mutator. They diverge the
moment evidence is assembled any other way — a merge, a re-import, or the late-arriving
discovery §10 of `OBLIGATION_LIFECYCLE_QUESTION.md` makes mandatory, where `effective_on` is in
the past and `recorded_at` is now.

**What is NOT asserted here:** any particular tie state, name or shape. That would be inventing
the mechanism this fixture exists to demand. The assertions are properties.

Run:  python tests/test_evidence_tie_fixture.py
"""
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


def run(m):
    base = m.classify(**NEUTRAL)

    def content_state(c):
        return m.axis(c, m.CONTENT).state

    print('\n1. The asymmetry that already holds — controls\n')

    said_yes = m.record_evidence(base, m.CONTENT, source=m.USER_STATED, supports=True)
    check('a user statement establishes content',
          content_state(said_yes) == m.USER_ASSERTED)

    then_weak = m.record_evidence(said_yes, m.CONTENT, source=m.MERCHANT_MATCH, supports=False)
    check('a non-knowing signal may not overturn a knowing one',
          content_state(then_weak) == m.USER_ASSERTED)

    changed_mind = m.record_evidence(said_yes, m.CONTENT, source=m.USER_STATED, supports=False)
    check('the same knowing source may correct itself',
          content_state(changed_mind) == m.CONTRADICTED)

    print('\n2. Two knowing sources disagreeing\n')

    user_then_eob = m.record_evidence(said_yes, m.CONTENT,
                                      source=m.IMPORTED_EOB, supports=False)
    eob_first = m.record_evidence(base, m.CONTENT, source=m.IMPORTED_EOB, supports=False)
    eob_then_user = m.record_evidence(eob_first, m.CONTENT,
                                      source=m.USER_STATED, supports=True)

    print(f'        user then EOB  -> {content_state(user_then_eob)}')
    print(f'        EOB then user  -> {content_state(eob_then_user)}')

    check('the same disagreement resolves the same way in either order',
          content_state(user_then_eob) == content_state(eob_then_user))

    # The sharper half. In one of the two orders the disagreement leaves no trace at all:
    # the result is identical to a user statement that was never contradicted by anything.
    check('a disagreement between equal-rank sources is still visible afterwards',
          content_state(eob_then_user) != content_state(said_yes))

    check('neither source wins merely by being recorded second',
          not (content_state(user_then_eob) == m.CONTRADICTED
               and content_state(eob_then_user) == m.USER_ASSERTED))

    print('\n3. "Latest" should mean latest, not last in the list\n')

    # Assembled directly, because `record_evidence` stamps `recorded_at` itself and so can
    # never produce this ordering. A merge or a backfilled import can.
    out_of_order = (
        m.Evidence(m.CONTENT, m.USER_STATED, True, recorded_at='2026-03-01T00:00:00'),
        m.Evidence(m.CONTENT, m.IMPORTED_EOB, False, recorded_at='2025-07-04T00:00:00'),
    )
    in_order = tuple(reversed(out_of_order))

    print(f'        list order = time order      -> {m._state_from(in_order)}')
    print(f'        list order != time order     -> {m._state_from(out_of_order)}')

    check('with list order matching time order, the later statement wins',
          m._state_from(in_order) == m.USER_ASSERTED)
    check('with list order NOT matching time order, the later statement still wins',
          m._state_from(out_of_order) == m.USER_ASSERTED)


def describe():
    print('\nThe fixture, as a specification:\n')
    print('  * two knowing sources at equal rank must resolve identically in either order')
    print('  * a disagreement must remain visible after it is resolved - a conflict that')
    print('    reads as though it never happened is worse than an unresolved one')
    print('  * neither source may win by being recorded second')
    print('  * "latest" must be by recorded_at, not by list position')
    print('\n  No tie state is named here on purpose. Naming one would settle by')
    print('  convenience the question gap 15 deliberately left open.')


def main():
    print('=' * 74)
    print('THE EQUAL-RANK TIE FIXTURE')
    print('=' * 74)
    try:
        from core import classification as model
        model._state_from
    except (ImportError, AttributeError):
        print('\nNo classifier yet.')
        describe()
        return 1

    run(model)
    print(f'\n{len(PASS)} passed, {len(FAIL)} failed, {len(PENDING)} pending')
    if FAIL:
        print('\nThe failures are the finding, not a broken fixture:')
        print('  EVIDENCE_MATRIX.md finding 1 - the deliberate tie at rank 3 is broken')
        print('  by list position, and gap 15\'s explicit tie state is unimplemented.')
    return 1 if (FAIL or PENDING) else 0


if __name__ == '__main__':
    sys.exit(main())
