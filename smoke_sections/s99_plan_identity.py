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

    # ── DOCUMENT_LINE_KIND.md s11 (stage 1, the SBC): the four crossings the ruled line kind opens ──
    def line_becomes_the_term():
        # the L1 crossing: a document line read from the insurer's own SBC mints the ruled term on the plan
        def on_line(mapper, connection, target):
            if target.kind != db.DOCUMENT_LINE:
                return
            pl = connection.execute(PL.select().limit(1)).first()
            if pl is None:
                return
            connection.execute(P.insert().values(kind=db.DEDUCTIBLE, subject_state=db.PARTICIPANT_ESTABLISHED,
                                                 object_state=db.PARTICIPANT_NONE, subject_plan_id=pl.id,
                                                 content=target.content, as_of=target.as_of))
        event.listen(db.Proposition, 'after_insert', on_line)
        return lambda: event.remove(db.Proposition, 'after_insert', on_line)

    def tie_from_artefact_concerns():
        # the matcher smuggled in: the line gains a concerns claim from the artefact's own concerns
        def on_ev(mapper, connection, target):
            if target.reading_id is None:
                return
            p = connection.execute(P.select().where(P.c.id == target.proposition_id)).first()
            if p is None or p.kind != db.DOCUMENT_LINE:
                return
            ac = connection.execute(P.select().where(P.c.kind == db.ARTEFACT_CONCERNS)).first()
            if ac is None or ac.object_plan_id is None:
                return
            connection.execute(P.insert().values(kind=db.PROPOSITION_CONCERNS, subject_state=db.PARTICIPANT_ESTABLISHED,
                                                 object_state=db.PARTICIPANT_ESTABLISHED, subject_proposition_id=p.id,
                                                 object_plan_id=ac.object_plan_id))
        event.listen(db.EvidentiaryRelationship, 'after_insert', on_ev)
        return lambda: event.remove(db.EvidentiaryRelationship, 'after_insert', on_ev)

    def map_restored_for_the_kind():
        # F4 reversed: the kind reads the foundation map again, so an institution's type confers knowing
        saved = db.RULED_KINDS[db.DOCUMENT_LINE]
        db.RULED_KINDS[db.DOCUMENT_LINE] = dict(saved, relational_knowing=False, knowing_relation=None)
        real = db.derived_strength

        def with_map(session, relation, knowing):
            return real(session, relation, dict(knowing, **{db.DOCUMENT_LINE: {'institution'}}))
        db.derived_strength = with_map

        def undo():
            db.RULED_KINDS[db.DOCUMENT_LINE] = saved
            db.derived_strength = real
        return undo

    def candidates_object_permitted():
        # F7 reversed: the required absence relaxed, so the line may name a candidate plan again
        saved = db.RULED_KINDS[db.DOCUMENT_LINE]
        db.RULED_KINDS[db.DOCUMENT_LINE] = dict(saved, object=('object_plan_id',))
        return lambda: db.RULED_KINDS.__setitem__(db.DOCUMENT_LINE, saved)

    return [
        ('a document line mints the ruled term (DOCUMENT_LINE_KIND s11, L1 crossed)', line_becomes_the_term),
        ("the line's tie manufactured from the artefact's concerns (the matcher smuggled in)", tie_from_artefact_concerns),
        ('the foundation map restored for the ruled line kind (F4 reversed)', map_restored_for_the_kind),
        ('a candidates object permitted on the ruled line kind (F7 reversed)', candidates_object_permitted),
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
