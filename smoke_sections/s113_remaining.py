"""remaining: the sixth consumer - THREE FIGURES AND A DIAGNOSTIC, NEVER ONE NUMBER - and whether each way of letting
it CONFIRM or RECONCILE is caught.

`gw 2.0/CONSUMER_DERIVATIONS.md` pass 7G (ruled 2026-09-18, s 7G.8). Runs the build gate
(`tests/test_remaining_fixture.py`) and then breaks the consumer twelve ways, each an attempt to confirm or reconcile:

    attachment moves confirmed         confirmed is recomputed over every attached payment
    clearance is discharge             a payment with a 'cleared' claim is treated as discharged
    the servicer's word is E's         an acknowledgment by a party whose role is undetermined qualifies
    a relayed report is knowing        RG-b: any established acknowledgment by E in effect qualifies
    a candidate acknowledgment counts  a reading-sourced acknowledgment qualifies
    the acknowledgment date excludes   ack.as_of replaces occurred_on in the base test (Dg26 re-subtracted)
    direction is a cash-flow sign      money out of the household reduces whatever the payee
    net by matching amount             two equal-and-opposite payments net without a counteracts claim
    one balance                        stated and attached averaged into a single `balance`
    no base is zero                    a missing S becomes a base of 0
    a cheque is allocated              a payment attached to two obligations is halved on each
    it stores                          `remaining_cache` appears on the module

Same shape as s107-s112: fixture passes, every mutation is caught, the baseline is re-established after every undo,
the module is left as found.
"""
import importlib.util
import io
import contextlib
from decimal import Decimal


def _load_fixture(BASE):
    path = BASE / 'tests' / 'test_remaining_fixture.py'
    spec = importlib.util.spec_from_file_location('test_remaining_fixture', path)
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
    original = db.remaining

    def _swap(post):
        def mutated(session, obligation, d, catalogue, knowing):
            return post(original(session, obligation, d, catalogue, knowing), session, obligation, d, catalogue, knowing)
        mutated.__doc__ = original.__doc__
        db.remaining = mutated
        return lambda: setattr(db, 'remaining', original)

    def _recompute(out, predicate, occurred_key='occurred_on'):
        """Rebuild confirmed over the payments `predicate` admits (a mutation's notion of discharge)."""
        S = out['stated']['governing']
        f = out['figures']['confirmed']
        if S is None:
            return
        total, basis = S['value'], []
        for pm in out['payments']:
            if pm['attachment']['state'] != db.CLAIM_ESTABLISHED or pm['netted'] or not predicate(pm):
                continue
            when = pm[occurred_key]['value'] if occurred_key == 'occurred_on' else (pm['discharge'] or {}).get('as_of')
            if when is None or when <= S['as_of'] or when > out['d']:
                continue
            if pm['amount']['value'] is None or pm['direction']['sign'] is None:
                continue
            basis.append((pm['payment'], pm['direction']['sign'], pm['amount']['value']))
            total += pm['direction']['sign'] * pm['amount']['value']
        f['value'], f['basis'] = total, basis
        out['figures']['remaining']['value'] = total

    def attachment_moves_confirmed():
        return _swap(lambda out, *_: (_recompute(out, lambda pm: True), out)[1])

    def clearance_is_discharge():
        def post(out, session, *_):
            cleared = {c.subject_payment_id for c in session.query(db.Proposition).filter_by(kind='cleared').all()}
            for pm in out['payments']:
                if pm['payment'] in cleared and pm['attachment']['state'] == db.CLAIM_ESTABLISHED:
                    pm['station'] = db.STATION_DISCHARGED
            _recompute(out, lambda pm: pm['station'] == db.STATION_DISCHARGED)
            return out
        return _swap(post)

    def servicer_is_e():
        def post(out, *_):
            for pm in out['payments']:
                if pm['attachment']['state'] == db.CLAIM_ESTABLISHED and any(
                        a['state'] == db.CLAIM_ESTABLISHED and a['strength'] == db.STRENGTH_KNOWING and a['as_of'] <= out['d'] for a in pm['acknowledgments']):
                    pm['station'] = db.STATION_DISCHARGED
            _recompute(out, lambda pm: pm['station'] == db.STATION_DISCHARGED)
            return out
        return _swap(post)

    def relayed_is_knowing():
        def post(out, *_):
            for pm in out['payments']:
                if pm['attachment']['state'] == db.CLAIM_ESTABLISHED and any(
                        a['state'] == db.CLAIM_ESTABLISHED and a['entitled'] == db.EFFECT_IN and a['as_of'] <= out['d'] for a in pm['acknowledgments']):
                    pm['station'] = db.STATION_DISCHARGED
            _recompute(out, lambda pm: pm['station'] == db.STATION_DISCHARGED)
            return out
        return _swap(post)

    def candidate_counts():
        def post(out, *_):
            for pm in out['payments']:
                if pm['attachment']['state'] == db.CLAIM_ESTABLISHED and any(
                        a['state'] == db.CLAIM_CANDIDATE and a['entitled'] == db.EFFECT_IN for a in pm['acknowledgments']):
                    pm['station'] = db.STATION_DISCHARGED
            _recompute(out, lambda pm: pm['station'] == db.STATION_DISCHARGED)
            return out
        return _swap(post)

    def ack_date_excludes():
        return _swap(lambda out, *_: (_recompute(out, lambda pm: pm['station'] == db.STATION_DISCHARGED, occurred_key='discharge'), out)[1])

    def cash_flow_sign():
        def post(out, session, *_):
            persons = {p.party.id for p in session.query(db.Person).all()}
            for pm in out['payments']:
                if pm['direction']['sign'] is None and pm['direction']['payers'] and pm['direction']['payees']:
                    pm['direction']['sign'] = -1 if any(x in persons for x in pm['direction']['payers']) else 1
            S = out['stated']['governing']
            if S is not None:
                for name, disch in (('attached', False), ('confirmed', True)):
                    total, basis = S['value'], []
                    ok = True
                    for pm in out['payments']:
                        if pm['attachment']['state'] != db.CLAIM_ESTABLISHED or pm['netted'] or (disch and pm['station'] != db.STATION_DISCHARGED):
                            continue
                        when = pm['occurred_on']['value']
                        if when is None or when <= S['as_of'] or when > out['d']:
                            continue
                        if pm['amount']['value'] is None or pm['direction']['sign'] is None:
                            ok = False
                            break
                        basis.append((pm['payment'], pm['direction']['sign'], pm['amount']['value']))
                        total += pm['direction']['sign'] * pm['amount']['value']
                    if ok:
                        out['figures'][name]['value'], out['figures'][name]['basis'], out['figures'][name]['reason'] = total, basis, None
                        out['figures'][name].pop('undetermined', None)
                out['figures']['remaining']['value'] = out['figures']['confirmed']['value']
            return out
        return _swap(post)

    def net_by_amount():
        def post(out, *_):
            seen = {}
            for pm in out['payments']:
                key = pm['amount']['value']
                if key in seen and seen[key]['direction']['sign'] and pm['direction']['sign'] == -seen[key]['direction']['sign']:
                    pm['netted'] = {'as': 'counteraction', 'claim': None}
                    seen[key]['netted'] = {'as': 'counteracted', 'claim': None}
                else:
                    seen[key] = pm
            for name, disch in (('attached', False), ('confirmed', True)):
                f = out['figures'][name]
                if f['value'] is not None:
                    for pid, sign, amt in list(f['basis']):
                        pm = next(x for x in out['payments'] if x['payment'] == pid)
                        if pm['netted'] and pm['netted']['claim'] is None:
                            f['value'] -= sign * amt
                            f['basis'].remove((pid, sign, amt))
            out['figures']['remaining']['value'] = out['figures']['confirmed']['value']
            return out
        return _swap(post)

    def one_balance():
        def post(out, *_):
            S = out['stated']['governing']
            a = out['figures']['attached']['value']
            if S is not None and a is not None:
                out['balance'] = (S['value'] + a) / 2
            return out
        return _swap(post)

    def no_base_is_zero():
        def post(out, *_):
            if out['stated']['governing'] is None and not out['stated']['conflict']:
                fake = {'claim': None, 'asserter': None, 'as_of': '0000-00-00', 'value': Decimal(0)}
                out['stated']['governing'] = fake
                out['stated']['reason'] = None
                for name, disch in (('attached', False), ('confirmed', True)):
                    f = out['figures'][name]
                    total = Decimal(0)
                    for pm in out['payments']:
                        if pm['attachment']['state'] == db.CLAIM_ESTABLISHED and not pm['netted'] and (not disch or pm['station'] == db.STATION_DISCHARGED) \
                                and pm['amount']['value'] is not None and pm['direction']['sign'] is not None:
                            total += pm['direction']['sign'] * pm['amount']['value']
                    f['value'], f['reason'] = total, None
                out['figures']['remaining']['value'] = out['figures']['confirmed']['value']
            return out
        return _swap(post)

    def cheque_allocated():
        def post(out, session, obligation, *_):
            for pm in out['payments']:
                n = session.query(db.Proposition).filter_by(kind=db.PAYMENT_IN_RESPECT_OF_OBLIGATION, subject_payment_id=pm['payment']).count()
                if n > 1 and pm['amount']['value'] is not None:
                    pm['amount']['value'] = pm['amount']['value'] / n
            for name in ('attached', 'confirmed'):
                f = out['figures'][name]
                if f['value'] is not None:
                    S = out['stated']['governing']
                    f['basis'] = [(pid, sign, next(x for x in out['payments'] if x['payment'] == pid)['amount']['value']) for pid, sign, _ in f['basis']]
                    f['value'] = S['value'] + sum(sign * amt for _, sign, amt in f['basis'])
            out['figures']['remaining']['value'] = out['figures']['confirmed']['value']
            return out
        return _swap(post)

    def it_stores():
        db.remaining_cache = {}
        return lambda: delattr(db, 'remaining_cache')

    # ── 7G-F3 (s 7G-F3.8): the discharge test on the CLAIM - the four ways it could have collapsed ──
    def any_knowing_origin_alone():
        # a knowing candidate alone discharges (Dc2 reversed): the claim need not be established
        def post(out, *_):
            for pm in out['payments']:
                if pm['attachment']['state'] == db.CLAIM_ESTABLISHED and any(
                        a['strength'] == db.STRENGTH_KNOWING and a['entitled'] == db.EFFECT_IN and a['as_of'] and a['as_of'] <= out['d'] for a in pm['acknowledgments']):
                    pm['station'] = db.STATION_DISCHARGED
            _recompute(out, lambda pm: pm['station'] == db.STATION_DISCHARGED)
            return out
        return _swap(post)

    def acceptance_lifted():
        # an establishing utterance is lifted to knowing by sitting beside any second relationship (Dc4 reversed)
        def post(out, *_):
            for pm in out['payments']:
                for a in pm['acknowledgments']:
                    if len(a['origins']) >= 2 and a['state'] == db.CLAIM_ESTABLISHED:
                        a['strength'] = db.STRENGTH_KNOWING
                        if a['entitled'] == db.EFFECT_IN and a['as_of'] and a['as_of'] <= out['d'] and pm['attachment']['state'] == db.CLAIM_ESTABLISHED:
                            pm['station'] = db.STATION_DISCHARGED
            _recompute(out, lambda pm: pm['station'] == db.STATION_DISCHARGED)
            return out
        return _swap(post)

    def servicer_reading_knowing():
        # a reading of the servicer's statement counts as E's knowing origin (Dc7 reversed)
        def post(out, *_):
            for pm in out['payments']:
                for a in pm['acknowledgments']:
                    if a['state'] == db.CLAIM_ESTABLISHED and any(o['ground'] and session_reading_origin(out, o) for o in a['origins']):
                        a['strength'] = db.STRENGTH_KNOWING
                        if a['entitled'] == db.EFFECT_IN and a['as_of'] and a['as_of'] <= out['d'] and pm['attachment']['state'] == db.CLAIM_ESTABLISHED:
                            pm['station'] = db.STATION_DISCHARGED
            _recompute(out, lambda pm: pm['station'] == db.STATION_DISCHARGED)
            return out

        def session_reading_origin(out, o):
            return o['asserter'] is None            # a reading-sourced relationship, whoever the origin is
        return _swap(post)

    def retracted_acceptance_discharges():
        # a retracted acceptance still discharges (Dc6 reversed): contested read as established
        def post(out, *_):
            for pm in out['payments']:
                for a in pm['acknowledgments']:
                    if a['state'] == db.CLAIM_CONTESTED and a['strength'] == db.STRENGTH_KNOWING and a['entitled'] == db.EFFECT_IN and a['as_of'] and a['as_of'] <= out['d']:
                        a['state'] = db.CLAIM_ESTABLISHED
                        if pm['attachment']['state'] == db.CLAIM_ESTABLISHED:
                            pm['station'] = db.STATION_DISCHARGED
            _recompute(out, lambda pm: pm['station'] == db.STATION_DISCHARGED)
            return out
        return _swap(post)

    return [
        ('a knowing candidate alone discharges (7G-F3, Dc2 reversed)', any_knowing_origin_alone),
        ('an establishing utterance lifted to knowing by a second relationship (7G-F3, Dc4 reversed)', acceptance_lifted),
        ("a reading of the servicer's statement counts as E's knowing origin (7G-F3, Dc7 reversed)", servicer_reading_knowing),
        ('a retracted acceptance still discharges (7G-F3, Dc6 reversed)', retracted_acceptance_discharges),
        ('attachment moves confirmed', attachment_moves_confirmed),
        ('clearance is discharge', clearance_is_discharge),
        ("the servicer's word is E's (role test dropped)", servicer_is_e),
        ('a relayed report is knowing (RG-b)', relayed_is_knowing),
        ('a candidate acknowledgment counts', candidate_counts),
        ('the acknowledgment date replaces occurred_on in the base test', ack_date_excludes),
        ('direction is a cash-flow sign', cash_flow_sign),
        ('net by matching amount without a counteracts claim', net_by_amount),
        ('stated and attached averaged into one balance', one_balance),
        ('no base is zero', no_base_is_zero),
        ('a cheque is allocated across obligations', cheque_allocated),
        ('the answer is stored', it_stores),
    ]


def run(ctx):
    check, BASE = ctx.check, ctx.BASE

    try:
        from core import database as db
    except Exception as e:                                    # noqa: BLE001
        check(f'core imports ({type(e).__name__}: {e})', False)
        return
    check('core/database.py carries remaining beside in_effect, read-only, four stations, with no paid / discharged / allocate / net / reconcile / cache helper',
          callable(getattr(db, 'remaining', None))
          and (db.STATION_ATTACHED_CANDIDATE, db.STATION_ATTACHED_CONTESTED, db.STATION_ATTACHED_UNACKNOWLEDGED, db.STATION_DISCHARGED)
          == ('attached_candidate', 'attached_contested', 'attached_unacknowledged', 'discharged')
          and not any(hasattr(db, n) for n in ('paid', 'is_discharged', 'allocate', 'net_payments', 'reconcile', 'resolve_figures',
                                                'remaining_cache', 'attached_remaining', 'floor_remaining')))

    try:
        fx = _load_fixture(BASE)
    except Exception as e:                                    # noqa: BLE001
        check(f'the remaining fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, db)
    check('the remaining fixture passes in full',
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
