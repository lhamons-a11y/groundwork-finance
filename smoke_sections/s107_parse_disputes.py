"""parse_disputes: the first consumer - a read-only derivation over the observations of one artefact that
reports disagreement and never resolves it - and whether each way of letting it choose, grow or resolve is
caught.

`gw 2.0/CONSUMER_DERIVATIONS.md` pass 7A (ruled 2026-09-16). Runs the build gate
(`tests/test_parse_disputes_fixture.py`) and then breaks the consumer eight ways, each an attempt to make
it choose or grow:

    the latest reading wins         the derivation adds a `chosen` content - the newest reading's - to each group
    a threshold appears             `similarity_threshold` is exposed on the module (the structural oracle becomes a calibration)
    agreement raises strength       `sources` counts readings instead of standing at one
    the candidate is upgraded       a candidate group is reported as established
    it establishes correspondence   `establish_correspondence(session, a, b)` is exposed (the consumer as a second mechanism)
    the answer is cached            `dispute_cache` appears on the module
    two artefacts are folded        `conflicts_between_artefacts` appears - the parse dispute as a general conflict engine
    omission read as zero           the derivation drops `omissions` and reports absent lines as agreed

Same shape as s103-s106: fixture passes, every mutation is caught, the baseline is re-established after
every undo, the module is left as found.
"""
import importlib.util
import io
import contextlib


def _load_fixture(BASE):
    path = BASE / 'tests' / 'test_parse_disputes_fixture.py'
    spec = importlib.util.spec_from_file_location('test_parse_disputes_fixture', path)
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
    original = db.parse_disputes

    def _wrap(post):
        def mutated(session, artefact):
            return post(original(session, artefact))
        mutated.__doc__ = original.__doc__
        return mutated

    def latest_wins():
        def post(out):
            for g in out['groups']:
                latest = max(g['propositions'], key=lambda p: p[3])
                g['chosen'] = latest[2]
            return out
        db.parse_disputes = _wrap(post)
        return lambda: setattr(db, 'parse_disputes', original)

    def threshold_appears():
        db.similarity_threshold = 0.9
        return lambda: delattr(db, 'similarity_threshold')

    def agreement_raises_strength():
        def post(out):
            out['sources'] = out['observations']
            return out
        db.parse_disputes = _wrap(post)
        return lambda: setattr(db, 'parse_disputes', original)

    def candidate_upgraded():
        def post(out):
            for g in out['groups']:
                if g['state'] == db.GROUP_CANDIDATE:
                    g['state'] = db.GROUP_ESTABLISHED
            return out
        db.parse_disputes = _wrap(post)
        return lambda: setattr(db, 'parse_disputes', original)

    def establishes_correspondence():
        db.establish_correspondence = lambda session, a, b: None
        return lambda: delattr(db, 'establish_correspondence')

    def answer_cached():
        db.dispute_cache = {}
        return lambda: delattr(db, 'dispute_cache')

    def artefacts_folded():
        db.conflicts_between_artefacts = lambda session, a, b: []
        return lambda: delattr(db, 'conflicts_between_artefacts')

    def omission_as_zero():
        def post(out):
            out['omissions'] = []
            return out
        db.parse_disputes = _wrap(post)
        return lambda: setattr(db, 'parse_disputes', original)

    return [
        ('the latest reading wins', latest_wins),
        ('a similarity threshold appears', threshold_appears),
        ('agreement raises strength - sources counts readings', agreement_raises_strength),
        ('the candidate is upgraded to established', candidate_upgraded),
        ('the consumer establishes correspondence itself', establishes_correspondence),
        ('the answer is cached', answer_cached),
        ('two artefacts are folded into one dispute engine', artefacts_folded),
        ('omission is read as zero', omission_as_zero),
    ]


def run(ctx):
    check, BASE = ctx.check, ctx.BASE

    try:
        from core import database as db
        import core.classification as cl
    except Exception as e:                                    # noqa: BLE001
        check(f'core imports ({type(e).__name__}: {e})', False)
        return
    check('core/database.py carries parse_disputes beside referent(), read-only, with no chooser, threshold, cache or establishing helper; resolution() names it and does not read past it',
          callable(getattr(db, 'parse_disputes', None))
          and not any(hasattr(db, n) for n in ('resolve_dispute', 'latest_reading', 'majority', 'similarity_threshold',
                                               'establish_correspondence', 'dispute_cache', 'conflicts_between_artefacts'))
          and 'parse_disputes' in (cl.resolution.__doc__ or ''))

    try:
        fx = _load_fixture(BASE)
    except Exception as e:                                    # noqa: BLE001
        check(f'the parse-disputes fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, db)
    check('the parse-disputes fixture passes in full',
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
