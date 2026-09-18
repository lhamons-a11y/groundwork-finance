"""chain_strength: the fifth consumer - a CLASS, not a quantity - and whether each way of letting it QUANTIFY
or CHOOSE is caught.

`gw 2.0/CONSUMER_DERIVATIONS.md` pass 7E (ruled 2026-09-17). Runs the build gate
(`tests/test_chain_strength_fixture.py`) and then breaks the consumer thirteen ways, each an attempt to quantify
or choose:

    a score                          every chain gains a numeric `score` (0.9 x 0.8 ...)
    paths are counted                an about entry gains `count`, and enough chains make the entry knowing
    the strongest chain answers      an about entry gains a per-identity `class` - the best of its chains
    chains ordered by class          chains sorted knowing-first instead of structural order
    undetermined reads not_knowing   a chain through correspondence is graded not_knowing
    a candidate chain carries        unchained entries become about entries with L0's class
    correspondence graded knowing    the correspondence link is given the asserter's class and the chain recomputed
    the servicer link is built       an unruled role claim becomes a link on the chain
    the chain replaces L0            the value's own class becomes the chain's
    grounds aggregated               two grounds on one link collapse to one chain with the strongest
    identities aggregated            entries for one identity merge into one with a summary class
    a chain enumerated twice         the same ground sequence reported twice through equivalent traversals
    it stores                        `chain_cache` appears on the module

Same shape as s107-s110: fixture passes, every mutation is caught, the baseline is re-established after every
undo, the module is left as found.
"""
import importlib.util
import io
import contextlib


def _load_fixture(BASE):
    path = BASE / 'tests' / 'test_chain_strength_fixture.py'
    spec = importlib.util.spec_from_file_location('test_chain_strength_fixture', path)
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
    original = db.chain_strength
    ORDER = {db.STRENGTH_UNDETERMINED: 0, db.STRENGTH_NOT_KNOWING: 1, db.STRENGTH_KNOWING: 2}
    SCORE = {db.STRENGTH_KNOWING: 0.9, db.STRENGTH_NOT_KNOWING: 0.4, db.STRENGTH_UNDETERMINED: 0.5}

    def _wrap(post):
        def mutated(session, proposition, knowing):
            return post(original(session, proposition, knowing), session, proposition, knowing)
        mutated.__doc__ = original.__doc__
        return mutated

    def _swap(post):
        db.chain_strength = _wrap(post)
        return lambda: setattr(db, 'chain_strength', original)

    def _regrade(chain):
        chain['class'] = db._weakest(*(l['class'] for l in chain['links']))

    def a_score():
        def post(out, *_):
            for a in out['about']:
                for c in a['chains']:
                    c['score'] = 1.0
                    for l in c['links']:
                        c['score'] *= SCORE[l['class']]
            return out
        return _swap(post)

    def paths_counted():
        def post(out, *_):
            for a in out['about']:
                a['count'] = len(a['chains'])
                if a['count'] >= 3:
                    for c in a['chains']:
                        c['class'] = db.STRENGTH_KNOWING
            return out
        return _swap(post)

    def strongest_answers():
        def post(out, *_):
            for a in out['about']:
                if a['chains']:
                    a['class'] = max((c['class'] for c in a['chains']), key=ORDER.get)
            return out
        return _swap(post)

    def ordered_by_class():
        def post(out, *_):
            for a in out['about']:
                a['chains'].sort(key=lambda c: -ORDER[c['class']])
            return out
        return _swap(post)

    def undetermined_reads_not_knowing():
        def post(out, *_):
            for a in out['about']:
                for c in a['chains']:
                    if c['class'] == db.STRENGTH_UNDETERMINED:
                        c['class'] = db.STRENGTH_NOT_KNOWING
            return out
        return _swap(post)

    def candidate_carries():
        def post(out, *_):
            for t, i, cond, reason in list(out['unchained']):
                out['about'].append({'type': t, 'id': i, 'provenance': db.ABOUT_DERIVED, 'path': db.ABOUT_PATH_CORRESPONDENCE,
                                     'chains': [{'evidence': e['relationship'], 'trace': [], 'class': e['class'],
                                                 'links': [{'kind': db.CHAIN_LINK_EVIDENCE, 'claim': None, 'ground': e['relationship'], 'class': e['class']}]}
                                                for e in out['evidence']]})
            out['unchained'] = []
            if out['about']:
                out['note'] = None
            return out
        return _swap(post)

    def correspondence_knowing():
        def post(out, *_):
            for a in out['about']:
                for c in a['chains']:
                    for l in c['links']:
                        if l['kind'] == db.PROPOSITION_CORRESPONDS:
                            l['class'] = db.STRENGTH_KNOWING
                    _regrade(c)
            return out
        return _swap(post)

    def servicer_link_built():
        def post(out, session, proposition, knowing):
            role = (session.query(db.Proposition).filter(db.Proposition.kind == 'services')
                    .filter(db.Proposition.object_obligation_id == proposition.subject_obligation_id).first()
                    if proposition.subject_obligation_id is not None else None)
            if role is not None:
                for a in out['about']:
                    for c in a['chains']:
                        c['links'].append({'kind': 'services', 'claim': role.id, 'ground': None, 'class': db.STRENGTH_KNOWING})
            return out
        return _swap(post)

    def chain_replaces_l0():
        def post(out, *_):
            by_rel = {}
            for a in out['about']:
                for c in a['chains']:
                    by_rel.setdefault(c['evidence'], []).append(c['class'])
            for e in out['evidence']:
                if e['relationship'] in by_rel:
                    e['class'] = min(by_rel[e['relationship']], key=ORDER.get)
                    for a in out['about']:
                        for c in a['chains']:
                            if c['evidence'] == e['relationship']:
                                c['links'][0]['class'] = e['class']
            return out
        return _swap(post)

    def grounds_aggregated():
        def post(out, *_):
            for a in out['about']:
                seen = {}
                for c in a['chains']:
                    key = (c['evidence'], tuple(l['claim'] for l in c['links']))
                    if key in seen:
                        best = seen[key]
                        if ORDER[c['class']] > ORDER[best['class']]:
                            best['links'] = c['links']
                            best['class'] = c['class']
                    else:
                        seen[key] = c
                a['chains'] = list(seen.values())
            return out
        return _swap(post)

    def identities_aggregated():
        def post(out, *_):
            merged = {}
            for a in out['about']:
                m = merged.setdefault((a['type'], a['id']), {'type': a['type'], 'id': a['id'], 'provenance': a['provenance'],
                                                             'path': a['path'], 'chains': []})
                m['chains'].extend(a['chains'])
            for m in merged.values():
                if m['chains']:
                    m['class'] = max((c['class'] for c in m['chains']), key=ORDER.get)
            out['about'] = list(merged.values())
            return out
        return _swap(post)

    def enumerated_twice():
        def post(out, *_):
            for a in out['about']:
                if a['path'] == db.ABOUT_PATH_CORRESPONDENCE:
                    a['chains'] = a['chains'] + [dict(c) for c in a['chains']]
            return out
        return _swap(post)

    def it_stores():
        db.chain_cache = {}
        return lambda: delattr(db, 'chain_cache')

    return [
        ('a numeric score on every chain', a_score),
        ('paths are counted and enough of them make knowing', paths_counted),
        ('the strongest chain answers for the identity', strongest_answers),
        ('chains ordered by class', ordered_by_class),
        ('undetermined reads as not_knowing', undetermined_reads_not_knowing),
        ('a candidate chain carries a class', candidate_carries),
        ('the correspondence link is graded knowing', correspondence_knowing),
        ('the servicer link is built from an unruled role claim', servicer_link_built),
        ("the chain's class replaces the value's own", chain_replaces_l0),
        ('grounds on one link aggregated to the strongest', grounds_aggregated),
        ('entries for one identity aggregated with a summary class', identities_aggregated),
        ('the same chain enumerated twice through equivalent traversals', enumerated_twice),
        ('the answer is stored', it_stores),
    ]


def run(ctx):
    check, BASE = ctx.check, ctx.BASE

    try:
        from core import database as db
    except Exception as e:                                    # noqa: BLE001
        check(f'core imports ({type(e).__name__}: {e})', False)
        return
    check('core/database.py carries chain_strength beside level_consistency, read-only, on the substrate\'s three classes, with no score / rank / cache / aggregate / corroboration helper',
          callable(getattr(db, 'chain_strength', None))
          and (db.STRENGTH_KNOWING, db.STRENGTH_NOT_KNOWING, db.STRENGTH_UNDETERMINED) == ('knowing', 'not_knowing', 'undetermined')
          and not any(hasattr(db, n) for n in ('chain_cache', 'strength_score', 'rank_chains', 'best_chain', 'aggregate_strength',
                                                'identity_strength', 'corroboration', 'link_strength', 'strength_of')))

    try:
        fx = _load_fixture(BASE)
    except Exception as e:                                    # noqa: BLE001
        check(f'the chain-strength fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, db)
    check('the chain-strength fixture passes in full',
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
