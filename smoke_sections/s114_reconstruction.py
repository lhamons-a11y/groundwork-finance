"""reconstruction: the seventh consumer - THE CHECK, NOT THE VOCABULARY - and whether each way of letting it EXPLAIN
is caught.

`gw 2.0/CONSUMER_DERIVATIONS.md` pass 7I (ruled 2026-09-19, s 7I.8). Runs the build gate
(`tests/test_reconstruction_fixture.py`) and then breaks the consumer ten ways, each an attempt to explain:

    a negative gap is waived            the report gains `disposition: waived` when unaccounted < 0
    a positive gap is a fee             the report gains `originated` when unaccounted > 0
    the relation's content is scope     a dollar figure in the relation's content adjusts `after`
    not restated carries forward        a context with no post-transition P-ack is counted at its carried-forward figure
    replaced reads zero                 a predecessor with an established successor is counted at 0 on the after side
    the payoff's direction inferred     a payment whose payee is the entitled party reduces regardless of payer
    overdue enters                      an `overdue` claim on a predecessor is subtracted from `before`
    the chain folds                     successors of successors join the group
    other predecessors dropped          the group is O and its successors only
    it stores                           `reconstruction_cache` appears on the module

Same shape as s107-s113: fixture passes, every mutation is caught, the baseline is re-established after every undo,
the module is left as found.
"""
import importlib.util
import io
import contextlib
from decimal import Decimal


def _load_fixture(BASE):
    path = BASE / 'tests' / 'test_reconstruction_fixture.py'
    spec = importlib.util.spec_from_file_location('test_reconstruction_fixture', path)
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
    original = db.reconstruction

    def _swap(post):
        def mutated(session, obligation, at, d, catalogue, knowing):
            return post(original(session, obligation, at, d, catalogue, knowing), session, obligation, at, d, catalogue, knowing)
        mutated.__doc__ = original.__doc__
        db.reconstruction = mutated
        return lambda: setattr(db, 'reconstruction', original)

    def _retotal(out):
        aft = [t['confirmed'] for t in out['after']['terms'] if t['eligible']]
        bef = [t['confirmed'] for t in out['before']['terms']]
        if all(v is not None for v in aft) and all(v is not None for v in bef) and all(t['eligible'] for t in out['after']['terms']):
            out['after']['value'], out['after']['reason'] = sum(aft, Decimal(0)), None
            out['before']['value'], out['before']['reason'] = sum(bef, Decimal(0)), None
            out['unaccounted'] = {'value': out['after']['value'] - out['before']['value'], 'reason': None}

    def negative_is_waived():
        def post(out, *_):
            if out['unaccounted']['value'] is not None and out['unaccounted']['value'] < 0:
                out['disposition'] = 'waived'
            return out
        return _swap(post)

    def positive_is_fee():
        def post(out, *_):
            if out['unaccounted']['value'] is not None and out['unaccounted']['value'] > 0:
                out['originated'] = out['unaccounted']['value']
            return out
        return _swap(post)

    def content_is_scope():
        def post(out, session, *_):
            import re
            for claim_id, _, _, state in out['group']['relations']:
                c = session.get(db.Proposition, claim_id)
                m = re.search(r'\$([\d,]+)', c.content or '')
                if m and state == db.CLAIM_ESTABLISHED and out['after']['value'] is not None:
                    out['after']['value'] += Decimal(m.group(1).replace(',', ''))
                    out['unaccounted']['value'] = out['after']['value'] - out['before']['value']
            return out
        return _swap(post)

    def not_restated_carries():
        def post(out, *_):
            for t in out['after']['terms']:
                if not t['eligible'] and t['confirmed'] is not None:
                    t['eligible'], t['reason'] = True, None
            _retotal(out)
            return out
        return _swap(post)

    def replaced_reads_zero():
        def post(out, *_):
            if out['group']['successors']:
                for t in out['after']['terms']:
                    if t['side'] == 'predecessor':
                        t['eligible'], t['confirmed'], t['reason'] = True, Decimal(0), None
            _retotal(out)
            return out
        return _swap(post)

    def payoff_direction_inferred():
        def post(out, session, obligation, at, d, catalogue, knowing):
            resolved = []
            for u in list(out['unresolved_payments']):
                r = db.remaining(session, session.get(db.Obligation, u['obligation']), d, catalogue, knowing)
                pm = next(x for x in r['payments'] if x['payment'] == u['payment'])
                if pm['amount']['value'] is not None and pm['direction']['payees']:
                    resolved.append((u['obligation'], pm['amount']['value']))
                    out['unresolved_payments'].remove(u)
            for o_id, amt in resolved:
                for t in out['after']['terms']:
                    if t['obligation'] == o_id and t['confirmed'] is not None:
                        t['confirmed'] -= amt
                        if t['stated'] is not None:
                            t['eligible'], t['reason'] = True, None
            _retotal(out)
            return out
        return _swap(post)

    def overdue_enters():
        def post(out, session, *_):
            for t in out['before']['terms']:
                od = session.query(db.Proposition).filter_by(kind='overdue', subject_obligation_id=t['obligation']).first()
                if od is not None and t['confirmed'] is not None:
                    t['confirmed'] -= db._money(od.content)
            _retotal(out)
            return out
        return _swap(post)

    def chain_folds():
        def post(out, session, obligation, at, d, catalogue, knowing):
            for n_id in list(out['group']['successors']):
                n = session.get(db.Obligation, n_id)
                for e in db.reach(session, n, db.OBLIGATION_REPLACES, as_object=True)['endpoints']:
                    if e['state'] == db.CLAIM_ESTABLISHED and e['id'] not in out['group']['successors']:
                        out['group']['successors'].append(e['id'])
                        r = db.remaining(session, session.get(db.Obligation, e['id']), d, catalogue, knowing)
                        S = r['stated']['governing']
                        out['after']['terms'].append({'obligation': e['id'], 'side': 'successor', 'eligible': S is not None and S['as_of'] >= at,
                                                      'stated': S, 'confirmed': r['figures']['confirmed']['value'], 'reason': None})
            _retotal(out)
            return out
        return _swap(post)

    def other_predecessors_dropped():
        def post(out, session, obligation, *_):
            out['group']['predecessors'] = [obligation.id]
            out['before']['terms'] = [t for t in out['before']['terms'] if t['obligation'] == obligation.id]
            out['after']['terms'] = [t for t in out['after']['terms'] if t['side'] == 'successor' or t['obligation'] == obligation.id]
            _retotal(out)
            return out
        return _swap(post)

    def it_stores():
        db.reconstruction_cache = {}
        return lambda: delattr(db, 'reconstruction_cache')

    return [
        ('a negative gap is waived', negative_is_waived),
        ('a positive gap is a fee (originated)', positive_is_fee),
        ("the relation's content supplies scope", content_is_scope),
        ('a not-restated context carries forward as its answer', not_restated_carries),
        ('a replaced predecessor reads zero', replaced_reads_zero),
        ("the payoff's direction is inferred from its payee", payoff_direction_inferred),
        ('overdue enters as money', overdue_enters),
        ('the chain folds', chain_folds),
        ("a consolidation's other predecessors are dropped", other_predecessors_dropped),
        ('the answer is stored', it_stores),
    ]


def run(ctx):
    check, BASE = ctx.check, ctx.BASE

    try:
        from core import database as db
    except Exception as e:                                    # noqa: BLE001
        check(f'core imports ({type(e).__name__}: {e})', False)
        return
    check('core/database.py carries reconstruction beside remaining, read-only, reading no disposition, with no disposition / waived / apportion / family / cache helper',
          callable(getattr(db, 'reconstruction', None)) and 'no disposition kind is ruled' in db.DISPOSITION_NOTE
          and not any(hasattr(db, n) for n in ('disposition', 'disposition_of', 'waived', 'written_off', 'apportion', 'close_obligation',
                                                'transition_group', 'family_of', 'reconstruction_cache')))

    try:
        fx = _load_fixture(BASE)
    except Exception as e:                                    # noqa: BLE001
        check(f'the reconstruction fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, db)
    check('the reconstruction fixture passes in full',
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
