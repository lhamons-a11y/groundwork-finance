"""Relational knowing: a derived classification of an evidentiary relationship by the kind-designated
relation to the kind-designated participant - and whether each way of broadening it is caught.

`gw 2.0/RELATIONAL_KNOWING.md` s9 (ruled 2026-09-14). Runs the mechanism gate
(`tests/test_relational_knowing_fixture.py`) and then breaks it five ways:

    a generic resolver             any relation to any participant confers knowing (a graph traversal)
    minting confers knowing        a value kind is given the minter relation - minted_by -> knowing (Kn7)
    the foundation map scores      a relational kind falls back to the caller's foundation stand-in
    the boundary collapses         not_knowing is reported as undetermined
    custody as knowledge           proposition_corresponds is given a "household holds the artefact" relation

Same shape as s86-s96: fixture passes, every mutation is caught, the module is left as found.
"""
import importlib.util
import io
import contextlib


def _load_fixture(BASE):
    path = BASE / 'tests' / 'test_relational_knowing_fixture.py'
    spec = importlib.util.spec_from_file_location('test_relational_knowing_fixture', path)
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


def _swap(db, name, replacement):
    orig = getattr(db, name)
    setattr(db, name, replacement)
    return lambda: setattr(db, name, orig)


def _mutations(db):

    def generic_resolver():
        orig = db._relational_strength

        def traversal(session, prop, claimant, relation_name):
            # "find any party related to any participant; if the claimant is one of them, knowing"
            related = set()
            for col in ('subject_utterance_id', 'object_utterance_id'):
                uid = getattr(prop, col, None)
                if uid is not None:
                    u = session.get(db.Utterance, uid)
                    if u is not None:
                        related.add(u.origin_party_id)
            for col, model in (('subject_obligation_id', db.Obligation), ('object_obligation_id', db.Obligation),
                               ('subject_payment_id', db.Payment), ('object_payment_id', db.Payment)):
                iid = getattr(prop, col, None)
                if iid is not None:
                    ident = session.get(model, iid)
                    if ident is not None:
                        u = session.get(db.Utterance, ident.minted_by_id)
                        if u is not None:
                            related.add(u.origin_party_id)
            for col in ('subject_party_id', 'object_party_id'):
                pid = getattr(prop, col, None)
                if pid is not None:
                    related.add(pid)
            if related:
                return db.STRENGTH_KNOWING if claimant in related else db.STRENGTH_NOT_KNOWING
            return orig(session, prop, claimant, relation_name)
        return _swap(db, '_relational_strength', traversal)

    def minting_confers_knowing():
        db.RULED_KINDS['occurred_on'] = {'subject': ('subject_payment_id',), 'object': (), 'symmetric': False,
                                         'reading_establishes': False, 'relational_knowing': True,
                                         'knowing_relation': 'minter_of_subject_payment'}
        orig = dict(db._KNOWING_RELATIONS)

        def minter_of_subject(session, prop):
            pm = session.get(db.Payment, prop.subject_payment_id) if prop.subject_payment_id else None
            if pm is None:
                return None
            u = session.get(db.Utterance, pm.minted_by_id)
            return u.origin_party_id if u else None
        db._KNOWING_RELATIONS['minter_of_subject_payment'] = minter_of_subject

        def restore():
            db.RULED_KINDS.pop('occurred_on', None)
            db._KNOWING_RELATIONS.clear()
            db._KNOWING_RELATIONS.update(orig)
        return restore

    def foundation_map_scores():
        orig = db._relational_strength

        def fallback(session, prop, claimant, relation_name):
            out = orig(session, prop, claimant, relation_name)
            if out == db.STRENGTH_UNDETERMINED or relation_name is None:
                # "no relation? use the foundation map like any other kind"
                party = session.get(db.Party, claimant) if claimant else None
                if party is not None:
                    return db.STRENGTH_KNOWING
            return out
        return _swap(db, '_relational_strength', fallback)

    def boundary_collapses():
        orig = db._relational_strength

        def collapsed(session, prop, claimant, relation_name):
            out = orig(session, prop, claimant, relation_name)
            return db.STRENGTH_UNDETERMINED if out == db.STRENGTH_NOT_KNOWING else out
        return _swap(db, '_relational_strength', collapsed)

    def custody_as_knowledge():
        saved = dict(db.RULED_KINDS[db.PROPOSITION_CORRESPONDS])
        orig = dict(db._KNOWING_RELATIONS)

        def holder_of_the_artefact(session, prop):
            # "the household holds the artefact both readings came from, so any household member knows"
            p = session.get(db.Proposition, prop.subject_proposition_id) if prop.subject_proposition_id else None
            if p is None:
                return None
            rel = (session.query(db.EvidentiaryRelationship).filter_by(proposition_id=p.id)
                   .filter(db.EvidentiaryRelationship.reading_id.isnot(None)).first())
            if rel is None:
                return None
            # return the first Person party as "the household"
            hp = session.query(db.Party).filter(db.Party.person_id.isnot(None)).first()
            return hp.id if hp else None
        db._KNOWING_RELATIONS['holder_of_the_artefact'] = holder_of_the_artefact
        db.RULED_KINDS[db.PROPOSITION_CORRESPONDS]['knowing_relation'] = 'holder_of_the_artefact'

        def restore():
            db.RULED_KINDS[db.PROPOSITION_CORRESPONDS].clear()
            db.RULED_KINDS[db.PROPOSITION_CORRESPONDS].update(saved)
            db._KNOWING_RELATIONS.clear()
            db._KNOWING_RELATIONS.update(orig)
        return restore

    return [
        ('a generic resolver - any relation to any participant confers knowing', generic_resolver),
        ('minting confers knowing for an event property (Kn7)', minting_confers_knowing),
        ('the foundation map scores a relational kind', foundation_map_scores),
        ('not_knowing collapses into undetermined', boundary_collapses),
        ('custody is treated as knowledge for proposition_corresponds', custody_as_knowledge),
    ]


def run(ctx):
    check, BASE = ctx.check, ctx.BASE

    try:
        from core import database as db
    except Exception as e:                                    # noqa: BLE001
        check(f'core/database.py imports ({type(e).__name__}: {e})', False)
        return
    check('core/database.py carries named knowing relations, a finite resolver table, and no generic resolver',
          hasattr(db, '_KNOWING_RELATIONS') and hasattr(db, '_relational_strength')
          and set(db._KNOWING_RELATIONS) == {db.KNOWING_ORIGIN_OF_SUBJECT_UTTERANCE, db.KNOWING_MINTER_OF_OBJECT_IDENTITY}
          and db.RULED_KINDS[db.PROPOSITION_CORRESPONDS].get('knowing_relation') is None
          and not any(hasattr(db, n) for n in ('find_related_party', 'knowing_party_for')))

    try:
        fx = _load_fixture(BASE)
    except Exception as e:                                    # noqa: BLE001
        check(f'the relational-knowing fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, db)
    check('the relational-knowing fixture passes in full',
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
