"""aboutness: the third consumer - four things make a proposition about an identity (structural, asserted,
derived through the artefact level, derived through established correspondence) and nothing else; candidates
never reach, contested stops, paths are not counted, conflicts are reported not resolved - and whether each
way of letting it CARRY is caught.

`gw 2.0/CONSUMER_DERIVATIONS.md` pass 7C (ruled 2026-09-16). Runs the build gate
(`tests/test_aboutness_fixture.py`) and then breaks the consumer ten ways, each an attempt to carry:

    copy the claim                 a derived (correspondence) about-ness is written back as a proposition_concerns row
    set the participant            an asserted about-ness sets the proposition's object slot
    follow a candidate             a candidate correspondence or candidate artefact claim is promoted to derived
    follow a relation              P about O + O in respect of X => P about X (composition, D'.11)
    match content                  a proposition whose content names an obligation's minting text is about it
    rank derived over asserted     the conflict is dropped and the asserted identity removed when a derivation disagrees
    candidate unsettles            an established result becomes undetermined because a candidate names another identity
    paths become support           a derived entry gains `support` = number of paths
    the derivation knows           a derived entry gains `strength` = knowing
    it stores                      `aboutness_cache` appears on the module

Same shape as s107 / s108: fixture passes, every mutation is caught, the baseline is re-established after
every undo, the module is left as found.
"""
import importlib.util
import io
import contextlib


def _load_fixture(BASE):
    path = BASE / 'tests' / 'test_aboutness_fixture.py'
    spec = importlib.util.spec_from_file_location('test_aboutness_fixture', path)
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
    original = db.aboutness

    def _wrap(post):
        def mutated(session, proposition):
            return post(original(session, proposition), session, proposition)
        mutated.__doc__ = original.__doc__
        return mutated

    def copy_the_claim():
        def post(out, session, proposition):
            for d in out['derived']:
                if any(p['path'] == db.ABOUT_PATH_CORRESPONDENCE for p in d['paths']) and d['type'] == 'obligation':
                    pr = db.Proposition(kind=db.PROPOSITION_CONCERNS, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                                        subject_proposition_id=proposition.id, object_obligation_id=d['id'])
                    session.add(pr)
                    session.commit()
            return out
        db.aboutness = _wrap(post)
        return lambda: setattr(db, 'aboutness', original)

    def set_the_participant():
        def post(out, session, proposition):
            for t, i, _, _ in out['asserted']:
                if t == 'obligation' and proposition.object_state == db.PARTICIPANT_CANDIDATES:
                    session.execute(db.Proposition.__table__.update().where(db.Proposition.__table__.c.id == proposition.id)
                                    .values(object_state=db.PARTICIPANT_ESTABLISHED, object_obligation_id=i))
                    session.commit()
                    session.expire_all()
            return out
        db.aboutness = _wrap(post)
        return lambda: setattr(db, 'aboutness', original)

    def follow_a_candidate():
        def post(out, session, proposition):
            for t, i, src, ref in out['candidates']:
                if src in ('candidate correspondence', 'candidate artefact concerns'):
                    out['derived'].append({'type': t, 'id': i, 'paths': [{'path': db.ABOUT_PATH_CORRESPONDENCE, 'links': [('candidate', ref)]}]})
            if out['derived'] and out['note']:
                out['note'] = None
            return out
        db.aboutness = _wrap(post)
        return lambda: setattr(db, 'aboutness', original)

    def follow_a_relation():
        def post(out, session, proposition):
            ids = [i for t, i, _, _ in out['asserted'] if t == 'obligation'] + [d['id'] for d in out['derived'] if d['type'] == 'obligation']
            for oid in ids:
                for r in session.query(db.Proposition).filter_by(kind=db.OBLIGATION_IN_RESPECT_OF, subject_obligation_id=oid).all():
                    out['derived'].append({'type': 'expense', 'id': r.object_expense_id, 'paths': [{'path': 'relation', 'links': [('obligation_in_respect_of', r.id)]}]})
            return out
        db.aboutness = _wrap(post)
        return lambda: setattr(db, 'aboutness', original)

    def match_content():
        def post(out, session, proposition):
            if out['note'] == 'no about-ness established':
                o = session.query(db.Obligation).first()
                if o is not None:
                    out['derived'].append({'type': 'obligation', 'id': o.id, 'paths': [{'path': 'content', 'links': []}]})
                    out['note'] = None
            return out
        db.aboutness = _wrap(post)
        return lambda: setattr(db, 'aboutness', original)

    def rank_derived_over_asserted():
        def post(out, session, proposition):
            if out['conflicts']:
                out['conflicts'] = []
                out['asserted'] = []
            return out
        db.aboutness = _wrap(post)
        return lambda: setattr(db, 'aboutness', original)

    def candidate_unsettles():
        def post(out, session, proposition):
            asserted_ids = {(t, i) for t, i, _, _ in out['asserted']}
            for t, i, src, ref in out['candidates']:
                if src == 'candidate correspondence' and asserted_ids and (t, i) not in asserted_ids:
                    out['undetermined'] += [(at, ai, 'candidate disagrees', ref) for at, ai in asserted_ids]
                    out['asserted'] = []
            return out
        db.aboutness = _wrap(post)
        return lambda: setattr(db, 'aboutness', original)

    def paths_become_support():
        def post(out, session, proposition):
            for d in out['derived']:
                d['support'] = len(d['paths'])
            return out
        db.aboutness = _wrap(post)
        return lambda: setattr(db, 'aboutness', original)

    def derivation_knows():
        def post(out, session, proposition):
            for d in out['derived']:
                d['strength'] = db.STRENGTH_KNOWING
            return out
        db.aboutness = _wrap(post)
        return lambda: setattr(db, 'aboutness', original)

    def it_stores():
        db.aboutness_cache = {}
        return lambda: delattr(db, 'aboutness_cache')

    return [
        ('the derived about-ness is copied back as a concerns claim', copy_the_claim),
        ("the assertion sets the proposition's participant", set_the_participant),
        ('a candidate link is followed as if established', follow_a_candidate),
        ('a ruled relation is followed (P about O, O in respect of X => P about X)', follow_a_relation),
        ('content is matched to an identity', match_content),
        ('derived ranks over asserted - the conflict is dropped', rank_derived_over_asserted),
        ('a candidate unsettles an established result', candidate_unsettles),
        ('paths become support', paths_become_support),
        ('the derivation acquires knowing', derivation_knows),
        ('the answer is stored', it_stores),
    ]


def run(ctx):
    check, BASE = ctx.check, ctx.BASE

    try:
        from core import database as db
    except Exception as e:                                    # noqa: BLE001
        check(f'core imports ({type(e).__name__}: {e})', False)
        return
    check('core/database.py carries aboutness beside independence and parse_disputes, read-only, over four identity types, with no carrier / ranker / matcher / cache',
          callable(getattr(db, 'aboutness', None)) and set(db.ABOUT_IDENTITY_TYPES) == {'obligation', 'payment', 'expense', 'plan'}
          and not any(hasattr(db, n) for n in ('carry_aboutness', 'copy_concerns', 'rank_aboutness', 'match_heading', 'aboutness_cache', 'resolve_levels')))

    try:
        fx = _load_fixture(BASE)
    except Exception as e:                                    # noqa: BLE001
        check(f'the aboutness fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, db)
    check('the aboutness fixture passes in full',
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
