"""independence: the second consumer - a three-valued derivation between origins, for one proposition, that
counts nothing, defaults nothing, scores nothing and stores nothing - and whether each way of letting it
count, default, score or store is caught.

`gw 2.0/CONSUMER_DERIVATIONS.md` pass 7B (ruled 2026-09-16). Runs the build gate
(`tests/test_independence_fixture.py`) and then breaks the consumer twelve ways:

    rows are counted                each ground becomes its own origin (different row => independent)
    parties are counted             a reading's origin becomes its READER, not the artefact's origin (channel as origin)
    processes are counted           a process reader becomes an origin
    unknown defaults to independent an unestablished chain is reported established
    unknown defaults to not         a candidate correspondence is read as established (the pair collapses)
    a score appears                 the answer gains `corroboration` = number of independent pairs + 1
    not-knowing origins pair        an origin not knowing for the proposition takes part in pairs
    it stores                       `independence_cache` appears on the module
    it establishes                  `establish_independence(session, a, b)` appears on the module
    multiplicity becomes evidence   an origin with multiplicity > 1 gains a `support` figure and a self-pair marked independent
    unresolved grounds collapse     every origin-None entry is merged into one entry with summed multiplicity
    it mutates a row in place       the derivation UPDATEs a proposition's content (no count changes) before returning

Same shape as s103-s107: fixture passes, every mutation is caught, the baseline is re-established after
every undo, the module is left as found.
"""
import importlib.util
import io
import contextlib


def _load_fixture(BASE):
    path = BASE / 'tests' / 'test_independence_fixture.py'
    spec = importlib.util.spec_from_file_location('test_independence_fixture', path)
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
    original = db.independence

    def _wrap(post):
        def mutated(session, proposition, knowing):
            return post(original(session, proposition, knowing), session)
        mutated.__doc__ = original.__doc__
        return mutated

    def rows_counted():
        def post(out, session):
            split = []
            for o in out['origins']:
                for g in o['grounds']:
                    split.append(dict(o, grounds=[g], multiplicity=1, origin=(o['origin'], g[0]) if o['origin'] is not None else None))
            out['origins'] = split
            ks = [o for o in split if o['origin'] is not None and o['knowing'] == db.STRENGTH_KNOWING and o['state'] == db.CHAIN_ESTABLISHED]
            out['pairs'] = [(a['origin'], b['origin'], db.INDEPENDENT) for i, a in enumerate(ks) for b in ks[i + 1:]]
            out['note'] = None if len(ks) > 1 else out['note']
            return out
        db.independence = _wrap(post)
        return lambda: setattr(db, 'independence', original)

    def readers_as_origins():
        def post(out, session):
            for o in out['origins']:
                for g in o['grounds']:
                    if g[1] == 'reading':
                        rd = session.get(db.Reading, g[2])
                        if rd.reader_party_id is not None:
                            o['origin'] = rd.reader_party_id
            # re-pair
            ks = {}
            for o in out['origins']:
                if o['origin'] is not None and o['knowing'] == db.STRENGTH_KNOWING:
                    ks.setdefault(o['origin'], o)
            ks = list(ks.values())
            out['pairs'] = [(a['origin'], b['origin'], db.INDEPENDENT) for i, a in enumerate(ks) for b in ks[i + 1:]]
            return out
        db.independence = _wrap(post)
        return lambda: setattr(db, 'independence', original)

    def processes_counted():
        def post(out, session):
            for i, proc in enumerate(out['readers']):
                out['origins'].append({'origin': ('process', proc, i), 'state': db.CHAIN_ESTABLISHED, 'knowing': db.STRENGTH_KNOWING,
                                       'grounds': [], 'multiplicity': 0, 'correspondence_candidates': []})
            ks = [o for o in out['origins'] if o['origin'] is not None and o['knowing'] == db.STRENGTH_KNOWING]
            out['pairs'] = [(a['origin'], b['origin'], db.INDEPENDENT) for i, a in enumerate(ks) for b in ks[i + 1:]]
            return out
        db.independence = _wrap(post)
        return lambda: setattr(db, 'independence', original)

    def unknown_defaults_independent():
        def post(out, session):
            for o in out['origins']:
                if o['state'] in (db.CHAIN_UNESTABLISHED, db.CHAIN_CANDIDATE, db.CHAIN_CONTESTED):
                    o['state'] = db.CHAIN_ESTABLISHED
            out['pairs'] = [(a, b, db.INDEPENDENT if v == db.INDEPENDENCE_UNDETERMINED else v) for a, b, v in out['pairs']]
            return out
        db.independence = _wrap(post)
        return lambda: setattr(db, 'independence', original)

    def candidate_collapses():
        def post(out, session):
            merged = {}
            for o in out['origins']:
                key = o['origin']
                for c in o['correspondence_candidates']:
                    if c in merged:
                        key = c
                m = merged.setdefault(key, dict(o, grounds=[], multiplicity=0))
                m['grounds'] += o['grounds']
                m['multiplicity'] += o['multiplicity']
            out['origins'] = list(merged.values())
            out['pairs'] = [p for p in out['pairs'] if p[2] != db.INDEPENDENCE_UNDETERMINED]
            return out
        db.independence = _wrap(post)
        return lambda: setattr(db, 'independence', original)

    def score_appears():
        def post(out, session):
            out['corroboration'] = 1 + sum(1 for _, _, v in out['pairs'] if v == db.INDEPENDENT)
            return out
        db.independence = _wrap(post)
        return lambda: setattr(db, 'independence', original)

    def not_knowing_pairs():
        def post(out, session):
            ks = [o for o in out['origins'] if o['origin'] is not None and o['state'] == db.CHAIN_ESTABLISHED]
            out['pairs'] = [(a['origin'], b['origin'], db.INDEPENDENT) for i, a in enumerate(ks) for b in ks[i + 1:]]
            out['note'] = None if len(ks) > 1 else out['note']
            return out
        db.independence = _wrap(post)
        return lambda: setattr(db, 'independence', original)

    def it_stores():
        db.independence_cache = {}
        return lambda: delattr(db, 'independence_cache')

    def multiplicity_is_evidence():
        def post(out, session):
            for o in out['origins']:
                if o['multiplicity'] > 1:
                    o['support'] = o['multiplicity']
                    if o['origin'] is not None:
                        out['pairs'].append((o['origin'], o['origin'], db.INDEPENDENT))
            return out
        db.independence = _wrap(post)
        return lambda: setattr(db, 'independence', original)

    def unresolved_collapse():
        def post(out, session):
            nones = [o for o in out['origins'] if o['origin'] is None]
            if len(nones) > 1:
                merged = dict(nones[0], grounds=[g for o in nones for g in o['grounds']], multiplicity=sum(o['multiplicity'] for o in nones))
                out['origins'] = [o for o in out['origins'] if o['origin'] is not None] + [merged]
            return out
        db.independence = _wrap(post)
        return lambda: setattr(db, 'independence', original)

    def mutates_in_place():
        from sqlalchemy import update

        def mutated(session, proposition, knowing):
            session.execute(update(db.Proposition).where(db.Proposition.id == proposition.id)
                            .values(content=(proposition.content or '') + ' '))
            session.commit()
            return original(session, proposition, knowing)
        mutated.__doc__ = original.__doc__
        db.independence = mutated
        return lambda: setattr(db, 'independence', original)

    def it_establishes():
        db.establish_independence = lambda session, a, b: None
        return lambda: delattr(db, 'establish_independence')

    return [
        ('rows are counted - every ground its own origin', rows_counted),
        ("a reading's origin becomes its reader - channel as origin", readers_as_origins),
        ('processes are counted as origins', processes_counted),
        ('unknown defaults to independent', unknown_defaults_independent),
        ('a candidate correspondence collapses the pair', candidate_collapses),
        ('a corroboration score appears', score_appears),
        ('not-knowing origins take part in pairs', not_knowing_pairs),
        ('the answer is stored', it_stores),
        ('the consumer establishes independence', it_establishes),
        ('multiplicity becomes evidence', multiplicity_is_evidence),
        ('unresolved grounds collapse into one origin None', unresolved_collapse),
        ('the derivation mutates a row in place', mutates_in_place),
    ]


def run(ctx):
    check, BASE = ctx.check, ctx.BASE

    try:
        from core import database as db
        import core.classification as cl
        import inspect
    except Exception as e:                                    # noqa: BLE001
        check(f'core imports ({type(e).__name__}: {e})', False)
        return
    src = inspect.getsource(cl)
    check('core/database.py carries independence beside parse_disputes, read-only, three-valued, with no score / count / cache / establishing helper; the 1.x channel-type count is named, not repaired',
          callable(getattr(db, 'independence', None))
          and {db.INDEPENDENT, db.NOT_INDEPENDENT, db.INDEPENDENCE_UNDETERMINED} == {'independent', 'not_independent', 'undetermined'}
          and not any(hasattr(db, n) for n in ('corroboration', 'n_sources', 'independence_cache', 'establish_independence', 'is_independent'))
          and 'distinct = {e.source for e in supporting}' in src and 'CHANNEL TYPES' in src)

    try:
        fx = _load_fixture(BASE)
    except Exception as e:                                    # noqa: BLE001
        check(f'the independence fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, db)
    check('the independence fixture passes in full',
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
