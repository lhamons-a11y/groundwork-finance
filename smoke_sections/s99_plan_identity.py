"""Plan identity: an identity for a coverage arrangement the household individuates - not the insurer's
product; terms, period, members, premium are claims; nothing collapses onto the anchor - and whether each
way of letting it is caught.

`gw 2.0/PLAN_IDENTITY.md` s7 (ruled 2026-09-14). Runs the build gate
(`tests/test_plan_identity_fixture.py`) and then breaks the slice six ways:

    the product mints               the insurer's enrollment line (a group number) creates a plan
    terms become structure          the anchor grows a `deductible` attribute
    the insurer mints               the Person requirement on the minting utterance is dropped
    a number establishes            a shared group number manufactures a party's correspondence assertion
    correspondence merges           establishing plan_corresponds deletes the second row
    membership slips in             a person <-> plan relation kind enters the registry (item 5)

Same shape as s86-s98: fixture passes, every mutation is caught, the module is left as found.
"""
import importlib.util
import io
import contextlib


def _load_fixture(BASE):
    path = BASE / 'tests' / 'test_plan_identity_fixture.py'
    spec = importlib.util.spec_from_file_location('test_plan_identity_fixture', path)
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
    from sqlalchemy import event
    P, E, PL = db.Proposition.__table__, db.EvidentiaryRelationship.__table__, db.Plan.__table__

    def product_mints():
        def on_line(mapper, connection, target):
            if target.kind == 'identifiers' and target.content and 'Group' in target.content:
                u = connection.execute(db.Utterance.__table__.select().limit(1)).first()
                if u is not None:
                    connection.execute(PL.insert().values(minted_by_id=u.id))
        event.listen(db.Proposition, 'after_insert', on_line)
        return lambda: event.remove(db.Proposition, 'after_insert', on_line)

    def terms_become_structure():
        db.Plan.deductible = None
        return lambda: delattr(db.Plan, 'deductible')

    def insurer_mints():
        orig = db._minting_violations

        def existence_only(target, connection, noun):
            return [v for v in orig(target, connection, noun) if 'Person' not in v]
        db._minting_violations = existence_only
        return lambda: setattr(db, '_minting_violations', orig)

    def number_establishes():
        def manufacture(mapper, connection, target):
            if target.reading_id is None:
                return
            p = connection.execute(P.select().where(P.c.id == target.proposition_id)).first()
            if p is not None and p.kind == db.PROPOSITION_CORRESPONDS and p.content and 'group' in p.content:
                u = connection.execute(db.Utterance.__table__.select().limit(1)).first()
                connection.execute(E.insert().values(proposition_id=p.id, utterance_id=u.id))
        event.listen(db.EvidentiaryRelationship, 'after_insert', manufacture)
        return lambda: event.remove(db.EvidentiaryRelationship, 'after_insert', manufacture)

    def correspondence_merges():
        def merge(mapper, connection, target):
            if target.utterance_id is None:
                return
            p = connection.execute(P.select().where(P.c.id == target.proposition_id)).first()
            if p is not None and p.kind == db.PLAN_CORRESPONDS:
                connection.execute(PL.delete().where(PL.c.id == p.subject_plan_id))
        event.listen(db.EvidentiaryRelationship, 'after_insert', merge)
        return lambda: event.remove(db.EvidentiaryRelationship, 'after_insert', merge)

    def membership_slips_in():
        db.RULED_KINDS['covered_under'] = {'subject': ('subject_party_id',), 'object': ('object_plan_id',),
                                           'symmetric': False, 'reading_establishes': False, 'relational_knowing': True}
        return lambda: db.RULED_KINDS.pop('covered_under', None)

    return [
        ('the insurer\'s enrollment line mints a plan', product_mints),
        ('terms become anchor structure', terms_become_structure),
        ('an institution-origin utterance mints a plan', insurer_mints),
        ('a shared group number manufactures a party\'s correspondence assertion', number_establishes),
        ('establishing a correspondence merges the two plans', correspondence_merges),
        ('a person <-> plan membership kind slips into the registry', membership_slips_in),
    ]


def run(ctx):
    check, BASE = ctx.check, ctx.BASE

    try:
        from core import database as db
    except Exception as e:                                    # noqa: BLE001
        check(f'core/database.py imports ({type(e).__name__}: {e})', False)
        return
    check('core/database.py carries the plan anchor, its slots, plan_corresponds and the concerns slots',
          all(hasattr(db, n) for n in ('Plan', 'PLAN_CORRESPONDS', 'plans_without_minting_utterance'))
          and 'subject_plan_id' in db.Proposition.SUBJECT_SLOTS and 'Plan' in db._CORRESPONDENCE_OF
          and {c.name for c in db.Plan.__table__.columns} == {'id', 'minted_by_id', 'created_at'}
          and 'object_plan_id' in db.RULED_KINDS[db.ARTEFACT_CONCERNS]['object']
          and 'object_plan_id' in db.RULED_KINDS[db.PROPOSITION_CONCERNS]['object'])

    try:
        fx = _load_fixture(BASE)
    except Exception as e:                                    # noqa: BLE001
        check(f'the plan-identity fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, db)
    check('the plan-identity fixture passes in full',
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

    restored, restored_failures, restored_err = _run_fixture(fx, db)
    check('the module is left exactly as it was found',
          restored == passed and not restored_failures and not restored_err)
