"""The determination: built by item 9 pass 9D-v exactly as ruled (s 9D-v.7) - and whether each way of giving the
determination a holder, a gate, a vocabulary or a derivation is caught.

`gw 2.0/CATALOGUES.md` s 9D-v (2026-09-20). Runs the build gate (`tests/test_determination_fixture.py`) and then breaks
the substrate ten ways:

    a knowing relation designated          the asserter first-hand for its own determination
    a reading establishes it               a reading-sourced determination reads as established
    a role gate on the kind                only the insurer's determination is current
    the four names enforced                the registry parses content
    a denial accepted as a determination   7H's current from a denial
    minted from unresolved = 0             a zero-unresolved expense acquires user_paid_cash
    the type confers knowing               the foundation stand-in restored
    an undated determination current       7H accepts an undated claim
    a determiner_of role appears           a role kind registered for it
    a second resolver                      the determination's knowing manufactured by a generic resolver

Same shape as s117-s123: fixture passes, every mutation is caught, the baseline is re-established after every undo,
the module is left as found.
"""
import importlib.util
import io
import contextlib


def _load_fixture(BASE):
    path = BASE / 'tests' / 'test_determination_fixture.py'
    spec = importlib.util.spec_from_file_location('test_determination_fixture', path)
    fx = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fx)
    return fx


def _run_fixture(fx, db):
    fx.PASS.clear()
    fx.FAIL.clear()
    err = None
    with contextlib.redirect_stdout(io.StringIO()):
        try:
            fx.run(db)
        except Exception as e:                                # noqa: BLE001
            err = f'{type(e).__name__}: {e}'
    return len(fx.PASS), list(fx.FAIL), err


def _mutations(db):
    def relation_designated():
        rule = db.RULED_KINDS[db.DETERMINATION]
        db.RULED_KINDS[db.DETERMINATION] = dict(rule, knowing_relation=db.KNOWING_ORIGIN_OF_SUBJECT_UTTERANCE)
        orig = dict(db._KNOWING_RELATIONS)
        # the asserter first-hand for its own determination: the origin of the utterance behind the claim
        def self_origin(session, prop):
            rel = session.query(db.EvidentiaryRelationship).filter_by(proposition_id=prop.id).first()
            u = session.get(db.Utterance, rel.utterance_id) if rel is not None and rel.utterance_id else None
            return u.origin_party_id if u is not None else None
        db._KNOWING_RELATIONS[db.KNOWING_ORIGIN_OF_SUBJECT_UTTERANCE] = self_origin

        def undo():
            db.RULED_KINDS[db.DETERMINATION] = rule
            db._KNOWING_RELATIONS.clear()
            db._KNOWING_RELATIONS.update(orig)
        return undo

    def reading_establishes():
        real = db._claim_states

        def states(session, claim, retracted):
            out = real(session, claim, retracted)
            if claim.kind == db.DETERMINATION:
                out = [(db.CLAIM_ESTABLISHED if st == db.CLAIM_CANDIDATE else st, a, g) for st, a, g in out]
            return out
        db._claim_states = states
        return lambda: setattr(db, '_claim_states', real)

    def role_gate():
        real = db.reconciliation

        def gated(session, expense, d, catalogue, knowing):
            rep = real(session, expense, d, catalogue, knowing)
            det = rep['determinations']
            ins = [c for c in det['claims'] if c['roles'].get('insurer_of') == db.EFFECT_IN and c['state'] == db.CLAIM_ESTABLISHED and c['recognised'] and c['as_of']]
            if ins:
                latest = max(ins, key=lambda c: c['as_of'])
                det['current'] = {'name': latest['name'], 'asserters': [latest['asserter']], 'claims': [latest['claim']]}
                det['conflict'] = []
            elif det['current'] is not None and any(c['roles'].get('household_person') for c in det['claims'] if c['claim'] in det['current']['claims']):
                det['current'] = None
                det['reason'] = 'only the insurer may determine'
            return rep
        db.reconciliation = gated
        return lambda: setattr(db, 'reconciliation', real)

    def names_enforced():
        from sqlalchemy import event

        def guard(mapper, connection, target):
            if target.kind == db.DETERMINATION and target.content not in db.DETERMINATION_NAMES:
                raise ValueError('determination content must be one of the four names')
        event.listen(db.Proposition, 'before_insert', guard)
        return lambda: event.remove(db.Proposition, 'before_insert', guard)

    def denial_as_determination():
        real = db.reconciliation

        def with_denial(session, expense, d, catalogue, knowing):
            rep = real(session, expense, d, catalogue, knowing)
            det = rep['determinations']
            for c in det['claims']:
                if c['name'] == db.DETERMINATION_UNRECOGNISED and c['state'] == db.CLAIM_ESTABLISHED and det['current'] is None:
                    det['current'] = {'name': 'unpaid', 'asserters': [c['asserter']], 'claims': [c['claim']]}
            return rep
        db.reconciliation = with_denial
        return lambda: setattr(db, 'reconciliation', real)

    def minted_from_zero():
        real = db.reconciliation

        def zero_determines(session, expense, d, catalogue, knowing):
            rep = real(session, expense, d, catalogue, knowing)
            det = rep['determinations']
            if det['current'] is None and not det['claims'] and rep['unresolved']['value'] in (0, None):
                det['current'] = {'name': 'user_paid_cash', 'asserters': [], 'claims': []}
                det['reason'] = None
            return rep
        db.reconciliation = zero_determines
        return lambda: setattr(db, 'reconciliation', real)

    def type_confers_knowing():
        rule = db.RULED_KINDS[db.DETERMINATION]
        db.RULED_KINDS[db.DETERMINATION] = dict(rule, relational_knowing=False)
        real = db.derived_strength

        def with_map(session, relation, knowing):
            return real(session, relation, dict(knowing, **{db.DETERMINATION: {'person', 'institution'}}))
        db.derived_strength = with_map

        def undo():
            db.RULED_KINDS[db.DETERMINATION] = rule
            db.derived_strength = real
        return undo

    def undated_current():
        real = db.reconciliation

        def lenient(session, expense, d, catalogue, knowing):
            rep = real(session, expense, d, catalogue, knowing)
            det = rep['determinations']
            und = [c for c in det['claims'] if not c['as_of'] and c['state'] == db.CLAIM_ESTABLISHED and c['recognised']]
            if und:
                det['current'] = {'name': und[-1]['name'], 'asserters': [und[-1]['asserter']], 'claims': [und[-1]['claim']]}
            return rep
        db.reconciliation = lenient
        return lambda: setattr(db, 'reconciliation', real)

    def determiner_role():
        db.RULED_KINDS['determiner_of'] = {'subject': ('subject_party_id',), 'object': ('object_expense_id',), 'symmetric': False,
                                           'reading_establishes': False, 'relational_knowing': True, 'role': True, 'knowing_relation': db.KNOWING_SUBJECT_PARTY}
        return lambda: db.RULED_KINDS.pop('determiner_of', None)

    def second_resolver():
        rule = db.RULED_KINDS[db.DETERMINATION]
        db.RULED_KINDS[db.DETERMINATION] = dict(rule, knowing_relation='any_party_knowing')
        db._KNOWING_RELATIONS['any_party_knowing'] = lambda session, prop: None

        def undo():
            db.RULED_KINDS[db.DETERMINATION] = rule
            db._KNOWING_RELATIONS.pop('any_party_knowing', None)
        return undo

    return [
        ('a knowing relation designated (the asserter first-hand)', relation_designated),
        ('a reading establishes a determination', reading_establishes),
        ('a role gate on the kind (only the insurer determines)', role_gate),
        ('the four names enforced by the registry', names_enforced),
        ('a denial accepted as a determination', denial_as_determination),
        ('a determination minted from unresolved = 0', minted_from_zero),
        ('the origin\'s type confers knowing (the foundation restored)', type_confers_knowing),
        ('an undated determination current', undated_current),
        ('a determiner_of role appears', determiner_role),
        ('a second resolver for the determination', second_resolver),
    ]


def run(ctx):
    check, BASE = ctx.check, ctx.BASE

    try:
        from core import database as db
    except Exception as e:                                    # noqa: BLE001
        check(f'core imports ({type(e).__name__}: {e})', False)
        return
    check('core/database.py carries the determination exactly as ruled - the expense the subject, no object, reading_establishes False, relational knowing with no relation, no role, no boundary; the named relations still eight; no determiner role or helper; the guard passing; every s 1 stand-in a ruled kind',
          db.RULED_KINDS[db.DETERMINATION] == {'subject': ('subject_expense_id',), 'object': (), 'symmetric': False, 'reading_establishes': False, 'relational_knowing': True}
          and len(db._KNOWING_RELATIONS) == 8 and 'determiner_of' not in db.RULED_KINDS
          and db.registry_violations() == []
          and not any(hasattr(db, n) for n in ('determiner_of', 'may_determine', 'determine', 'current_determination', 'resolve_determination')))

    try:
        fx = _load_fixture(BASE)
    except Exception as e:                                    # noqa: BLE001
        check(f'the determination fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, db)
    check('the determination fixture passes in full',
          not failures and not err and passed > 0)
    if failures or err:
        for f in failures[:6]:
            print(f'        failing: {f}')
        if err:
            print(f'        raised: {err}')
        check('mutation detection is meaningful (baseline green)', False)
        return

    for name, make in _mutations(db):
        undo = make()
        try:
            _, mutated, mutated_err = _run_fixture(fx, db)
        finally:
            undo()
        check('caught: ' + name, bool(mutated) or bool(mutated_err))
        after, after_failures, after_err = _run_fixture(fx, db)
        check('restored after: ' + name,
              after == passed and not after_failures and not after_err)

    restored, restored_failures, restored_err = _run_fixture(fx, db)
    check('the module is left exactly as it was found',
          restored == passed and not restored_failures and not restored_err)
