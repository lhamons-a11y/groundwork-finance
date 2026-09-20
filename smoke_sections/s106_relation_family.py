"""The in-respect-of family: a STRUCTURAL regression of pass G's ruling - not a definition of the family,
and asserting nothing about composition.

`gw 2.0/RELATION_SEMANTICS.md` pass G (ruled 2026-09-16). Six kinds have identical relational semantics
after subject and object types are treated as parameters; they are represented as six registry kinds (the
correspondence precedent), never as one typed-slot kind, never with a family base, resolver, cross-pair
selector or inverse accessor. This section pins:

    every in-respect-of kind in the registry is one of the six ruled pairs; no seventh exists
    each has exactly one subject slot and one object slot (no typed-slot merge)
    the built members carry identical flags: symmetric False, reading_establishes False,
        relational_knowing True, no knowing_relation
    no bare `in_respect_of` kind; no Relation / RelationBase; no family resolver; no cross-pair
        selector; no inverse accessor; no composition helper
    A, B and the correspondence kinds are outside the family; correspondence is still seven
        per-type kinds; F, if built, is a role and not a member
    NOTHING here asserts that any member composes with another (D'.11 stays open)

and breaks the ruling three ways, each caught and restored:

    a typed-slot merge kind appears      `in_respect_of` with three subject and three object slots
    a seventh pair appears               `expense_in_respect_of_obligation` - C's refused inverse
    a family resolver appears            `resolve_in_respect_of(session, thing)` is exposed
"""

RULED_PAIRS = {
    'obligation_in_respect_of':         ('subject_obligation_id', 'object_expense_id'),
    'payment_in_respect_of':            ('subject_payment_id',    'object_expense_id'),
    'payment_in_respect_of_obligation': ('subject_payment_id',    'object_obligation_id'),
    'expense_in_respect_of_plan':       ('subject_expense_id',    'object_plan_id'),
    'obligation_in_respect_of_plan':    ('subject_obligation_id', 'object_plan_id'),
    'payment_in_respect_of_plan':       ('subject_payment_id',    'object_plan_id'),
}
FAMILY_FLAGS = {'symmetric': False, 'reading_establishes': False, 'relational_knowing': True}
FORBIDDEN_NAMES = ('in_respect_of', 'Relation', 'RelationBase', 'relation_resolver', 'resolve_relation',
                   'resolve_in_respect_of', 'in_respect_of_family', 'family_of', 'FAMILY', 'InRespectOf',
                   'inverse_of', 'related_to', 'related', 'compose', 'compose_relations', 'chain', 'traverse_family',
                   'select_pair', 'cross_pair', 'in_respect_of_kinds', 'IN_RESPECT_OF_KINDS')


def _family_members(db):
    return {k: r for k, r in db.RULED_KINDS.items() if 'in_respect_of' in k}


def _violations(db):
    out = []
    members = _family_members(db)
    for k, r in members.items():
        if k not in RULED_PAIRS:
            out.append(f'unruled in-respect-of kind: {k}')
            continue
        if len(r['subject']) != 1 or len(r['object']) != 1:
            out.append(f'{k}: typed-slot merge - {r["subject"]} / {r["object"]}')
        elif (r['subject'][0], r['object'][0]) != RULED_PAIRS[k]:
            out.append(f'{k}: wrong pair {r["subject"][0]} -> {r["object"][0]}')
        for f, v in FAMILY_FLAGS.items():
            if r.get(f) != v:
                out.append(f'{k}: {f} is {r.get(f)!r}, family says {v!r}')
        if 'knowing_relation' in r:
            out.append(f'{k}: carries a knowing_relation')
    if 'in_respect_of' in db.RULED_KINDS:
        out.append('a bare in_respect_of kind exists')
    for n in FORBIDDEN_NAMES:
        if hasattr(db, n) and n != 'in_respect_of':
            out.append(f'forbidden name on the module: {n}')
    for k in (db.PAYMENT_COUNTERACTS, db.OBLIGATION_REPLACES):
        if 'in_respect_of' in k:
            out.append(f'{k} named into the family')
    corr = [k for k in db.RULED_KINDS if k.endswith('_corresponds')]
    if len(corr) != 7 or any(not db.RULED_KINDS[k]['symmetric'] for k in corr):
        out.append(f'correspondence is no longer seven symmetric per-type kinds: {corr}')
    if 'under_plan' in db.RULED_KINDS and 'in_respect_of' in 'under_plan':
        out.append('the role kind named into the family')
    return out


def _mutations(db):
    def typed_slot_merge():
        db.RULED_KINDS['in_respect_of'] = {
            'subject': ('subject_obligation_id', 'subject_payment_id', 'subject_expense_id'),
            'object': ('object_expense_id', 'object_obligation_id', 'object_plan_id'),
            'symmetric': False, 'reading_establishes': False, 'relational_knowing': True}
        return lambda: db.RULED_KINDS.pop('in_respect_of', None)

    def seventh_pair():
        db.RULED_KINDS['expense_in_respect_of_obligation'] = {
            'subject': ('subject_expense_id',), 'object': ('object_obligation_id',),
            'symmetric': False, 'reading_establishes': False, 'relational_knowing': True}
        return lambda: db.RULED_KINDS.pop('expense_in_respect_of_obligation', None)

    def family_resolver():
        db.resolve_in_respect_of = lambda session, thing: None
        return lambda: delattr(db, 'resolve_in_respect_of')

    return [
        ('a typed-slot merge kind appears', typed_slot_merge),
        ("a seventh pair appears (C's refused inverse)", seventh_pair),
        ('a family resolver appears', family_resolver),
    ]


def run(ctx):
    check = ctx.check
    try:
        from core import database as db
    except Exception as e:                                    # noqa: BLE001
        check(f'core/database.py imports ({type(e).__name__}: {e})', False)
        return

    members = _family_members(db)
    built = sorted(members)
    check('every in-respect-of kind in the registry is one of the six ruled pairs, with its ruled slots; no seventh pair exists',
          set(built) <= set(RULED_PAIRS) and all((members[k]['subject'][0], members[k]['object'][0]) == RULED_PAIRS[k] for k in built))
    check('the family is represented per pair - each member has exactly one subject slot and one object slot; no typed-slot merge; no bare in_respect_of kind',
          all(len(members[k]['subject']) == 1 and len(members[k]['object']) == 1 for k in built)
          and 'in_respect_of' not in db.RULED_KINDS)
    check('the built members carry identical flags - symmetric False, reading never establishes, relational_knowing True, no knowing_relation',
          all(all(members[k].get(f) == v for f, v in FAMILY_FLAGS.items()) and 'knowing_relation' not in members[k] for k in built))
    check('the family contract is stated once beside the kinds (a comment, not a constant), and no family base, resolver, selector, inverse accessor or composition helper exists',
          'THE IN-RESPECT-OF FAMILY' in (ctx.BASE / 'core' / 'database.py').read_text(encoding='utf-8', errors='replace')
          and not any(hasattr(db, n) for n in FORBIDDEN_NAMES if n != 'in_respect_of'))
    check('A and B are outside the family (two singletons sharing a shape); correspondence is still seven symmetric per-type kinds; a role kind is never a member',
          'in_respect_of' not in db.PAYMENT_COUNTERACTS and 'in_respect_of' not in db.OBLIGATION_REPLACES
          and len([k for k in db.RULED_KINDS if k.endswith('_corresponds')]) == 7
          and all(db.RULED_KINDS[k]['symmetric'] for k in db.RULED_KINDS if k.endswith('_corresponds')))
    # E's three were built by item 9 pass 9C (2026-09-19); the family is complete - six members, one per ruled pair
    check(f'built members today: {built} - all six ruled pairs; E\'s three built by 9C exactly as accepted',
          len(built) == 6 and set(built) == set(RULED_PAIRS))
    check('the section asserts nothing about composition - no composition helper exists and none is checked for presence',
          not any(hasattr(db, n) for n in ('compose', 'compose_relations', 'chain', 'traverse_family', 'transitive_closure')))

    baseline = _violations(db)
    check('baseline: no structural violation of the G ruling', not baseline)
    for v in baseline[:6]:
        print(f'        violation: {v}')
    if baseline:
        check('mutation detection is meaningful (baseline clean)', False)
        return

    for name, make in _mutations(db):
        undo = make()
        try:
            mutated = _violations(db)
        finally:
            undo()
        check('caught: ' + name, bool(mutated))
        check('restored after: ' + name, not _violations(db))
