"""level_consistency: the fourth consumer - a REPORT, not a verdict - and whether each way of letting it
DECIDE is caught.

`gw 2.0/CONSUMER_DERIVATIONS.md` pass 7D (ruled 2026-09-16). Runs the build gate
(`tests/test_level_consistency_fixture.py`) and then breaks the consumer twelve ways, each an attempt to decide:

    prefer the artefact level        inconsistent lines are dropped from the report
    prefer the line level            the artefact's established set is replaced by the lines' identities
    prefer recency                   the newest claim's identity replaces the artefact set
    the majority flips the set       when most lines disagree, the artefact set becomes the lines' identity
    refuse the outlier at write      a listener refuses a proposition_concerns outside the artefact's set
    a candidate raises a conflict    candidate identities are treated as established line identities
    an empty level reads consistent  no_level_basis becomes consistent
    contested manufactures           unresolved becomes inconsistent
    the five states collapse         no_level_basis / unresolved / no_line_basis become a Boolean consistent=False
    a cross-type conflict            an obligation line is inconsistent because the artefact concerns an expense
    a recommended retraction         the report gains `recommend_retraction`
    it stores                        `consistency_cache` appears on the module

Same shape as s107-s109: fixture passes, every mutation is caught, the baseline is re-established after
every undo, the module is left as found.
"""
import importlib.util
import io
import contextlib


def _load_fixture(BASE):
    path = BASE / 'tests' / 'test_level_consistency_fixture.py'
    spec = importlib.util.spec_from_file_location('test_level_consistency_fixture', path)
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
    original = db.level_consistency

    def _wrap(post):
        def mutated(session, artefact):
            return post(original(session, artefact), session, artefact)
        mutated.__doc__ = original.__doc__
        return mutated

    def _recount(t):
        t['counts'] = {}
        for l in t['lines']:
            t['counts'][l['classification']] = t['counts'].get(l['classification'], 0) + 1
        t['inconsistencies'] = [l for l in t['lines'] if l['classification'] == db.LEVEL_INCONSISTENT]

    def prefer_artefact():
        def post(out, session, artefact):
            for t in out['types'].values():
                t['lines'] = [l for l in t['lines'] if l['classification'] != db.LEVEL_INCONSISTENT]
                _recount(t)
            return out
        db.level_consistency = _wrap(post)
        return lambda: setattr(db, 'level_consistency', original)

    def prefer_lines():
        def post(out, session, artefact):
            for t in out['types'].values():
                ids = {i for l in t['lines'] for i, _ in l['identities']}
                if ids:
                    t['established'] = {i: [('lines', None)] for i in ids}
                    for l in t['lines']:
                        if l['classification'] == db.LEVEL_INCONSISTENT:
                            l['classification'] = db.LEVEL_CONSISTENT
                            l['against'] = []
                    _recount(t)
            return out
        db.level_consistency = _wrap(post)
        return lambda: setattr(db, 'level_consistency', original)

    def prefer_recency():
        def post(out, session, artefact):
            for t in out['types'].values():
                if t['lines']:
                    newest = t['lines'][-1]
                    if newest['identities']:
                        t['established'] = {newest['identities'][0][0]: [('newest', None)]}
                        for l in t['lines']:
                            if l['identities']:
                                l['classification'] = db.LEVEL_CONSISTENT if l['identities'][0][0] in t['established'] else db.LEVEL_INCONSISTENT
                        _recount(t)
            return out
        db.level_consistency = _wrap(post)
        return lambda: setattr(db, 'level_consistency', original)

    def majority_flips():
        def post(out, session, artefact):
            for t in out['types'].values():
                inc = [l for l in t['lines'] if l['classification'] == db.LEVEL_INCONSISTENT]
                if len(inc) > len(t['lines']) / 2:
                    t['established'] = {inc[0]['identities'][0][0]: [('majority', None)]}
                    for l in t['lines']:
                        if l['identities']:
                            l['classification'] = db.LEVEL_CONSISTENT if l['identities'][0][0] in t['established'] else db.LEVEL_INCONSISTENT
                    _recount(t)
            return out
        db.level_consistency = _wrap(post)
        return lambda: setattr(db, 'level_consistency', original)

    def refuse_at_write():
        from sqlalchemy import event
        P = db.Proposition.__table__

        def refuse(mapper, connection, target):
            if target.kind != db.PROPOSITION_CONCERNS or not target.subject_proposition_id or not target.object_obligation_id:
                return
            reading_ids = [r.reading_id for r in connection.execute(
                db.EvidentiaryRelationship.__table__.select().where(db.EvidentiaryRelationship.__table__.c.proposition_id == target.subject_proposition_id)).fetchall() if r.reading_id]
            if not reading_ids:
                return
            arts = {r.artefact_id for r in connection.execute(db.Reading.__table__.select().where(db.Reading.__table__.c.id.in_(reading_ids))).fetchall()}
            allowed = {r.object_obligation_id for r in connection.execute(
                P.select().where(P.c.kind == db.ARTEFACT_CONCERNS, P.c.subject_artefact_id.in_(sorted(arts)))).fetchall() if r.object_obligation_id}
            if allowed and target.object_obligation_id not in allowed:
                raise ValueError('a line may not concern an identity its artefact does not')
        event.listen(db.Proposition, 'before_insert', refuse)
        return lambda: event.remove(db.Proposition, 'before_insert', refuse)

    def candidate_conflicts():
        def post(out, session, artefact):
            for t in out['types'].values():
                est = set(t['established'])
                for l in t['lines']:
                    if l['classification'] == db.LEVEL_NO_LINE_BASIS and l['candidates'] and est and not set(l['candidates']) <= est:
                        l['classification'] = db.LEVEL_INCONSISTENT
                        l['against'] = sorted(est)
                _recount(t)
            return out
        db.level_consistency = _wrap(post)
        return lambda: setattr(db, 'level_consistency', original)

    def empty_reads_consistent():
        def post(out, session, artefact):
            for t in out['types'].values():
                for l in t['lines']:
                    if l['classification'] == db.LEVEL_NO_LEVEL_BASIS:
                        l['classification'] = db.LEVEL_CONSISTENT
                _recount(t)
            return out
        db.level_consistency = _wrap(post)
        return lambda: setattr(db, 'level_consistency', original)

    def contested_manufactures():
        def post(out, session, artefact):
            for t in out['types'].values():
                for l in t['lines']:
                    if l['classification'] == db.LEVEL_UNRESOLVED:
                        l['classification'] = db.LEVEL_INCONSISTENT
                        l['against'] = sorted(t['established'])
                _recount(t)
            return out
        db.level_consistency = _wrap(post)
        return lambda: setattr(db, 'level_consistency', original)

    def states_collapse():
        def post(out, session, artefact):
            for t in out['types'].values():
                for l in t['lines']:
                    if l['classification'] in (db.LEVEL_NO_LEVEL_BASIS, db.LEVEL_UNRESOLVED, db.LEVEL_NO_LINE_BASIS):
                        l['classification'] = db.LEVEL_INCONSISTENT
                _recount(t)
            return out
        db.level_consistency = _wrap(post)
        return lambda: setattr(db, 'level_consistency', original)

    def cross_type():
        def post(out, session, artefact):
            other = {typ: set(t['established']) for typ, t in out['types'].items()}
            for typ, t in out['types'].items():
                if any(other[o] for o in other if o != typ):
                    for l in t['lines']:
                        if l['classification'] == db.LEVEL_CONSISTENT:
                            l['classification'] = db.LEVEL_INCONSISTENT
                    _recount(t)
            return out
        db.level_consistency = _wrap(post)
        return lambda: setattr(db, 'level_consistency', original)

    def recommended_retraction():
        def post(out, session, artefact):
            out['recommendation'] = 'retract the artefact claim' if any(t['inconsistencies'] for t in out['types'].values()) else None
            return out
        db.level_consistency = _wrap(post)
        return lambda: setattr(db, 'level_consistency', original)

    def it_stores():
        db.consistency_cache = {}
        return lambda: delattr(db, 'consistency_cache')

    return [
        ('prefer the artefact level - inconsistent lines dropped', prefer_artefact),
        ('prefer the line level - the artefact set replaced', prefer_lines),
        ('prefer recency', prefer_recency),
        ('the majority flips the artefact set', majority_flips),
        ('refuse the outlier at write', refuse_at_write),
        ('a candidate raises a conflict', candidate_conflicts),
        ('an empty level reads consistent', empty_reads_consistent),
        ('a contested basis manufactures an inconsistency', contested_manufactures),
        ('the five states collapse to a Boolean', states_collapse),
        ('a cross-type conflict', cross_type),
        ('a recommended retraction appears', recommended_retraction),
        ('the answer is stored', it_stores),
    ]


def run(ctx):
    check, BASE = ctx.check, ctx.BASE

    try:
        from core import database as db
    except Exception as e:                                    # noqa: BLE001
        check(f'core imports ({type(e).__name__}: {e})', False)
        return
    check('core/database.py carries level_consistency beside aboutness, read-only, five named states, with no decider / status / cache / recommendation',
          callable(getattr(db, 'level_consistency', None))
          and (db.LEVEL_CONSISTENT, db.LEVEL_INCONSISTENT, db.LEVEL_NO_LINE_BASIS, db.LEVEL_NO_LEVEL_BASIS, db.LEVEL_UNRESOLVED)
          == ('consistent', 'inconsistent', 'no_line_basis', 'no_level_basis', 'unresolved')
          and not any(hasattr(db, n) for n in ('resolve_levels', 'prefer_level', 'majority_level', 'recommend_retraction', 'consistency_cache', 'is_consistent')))

    try:
        fx = _load_fixture(BASE)
    except Exception as e:                                    # noqa: BLE001
        check(f'the level-consistency fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, db)
    check('the level-consistency fixture passes in full',
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
