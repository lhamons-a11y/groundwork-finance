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

    # ── 7J-F4-F1 (s 7J-F4-F1.8): the holder's series at the claim level - the ways it could collapse ──
    # The mutation site is the shared helper `_holder_series` (7G's balance, 7H's three stances, 7J's stated
    # accumulator all read through it); each mutation post-processes the per-claim entries it returns.
    _series_original = db._holder_series

    def _swap_series(post):
        def mutated(session, entries, knowing, role_of, d, role_key):
            out = _series_original(session, entries, knowing, role_of, d, role_key)
            for c in out:
                post(c, session, knowing, role_of, d, role_key)
            return out
        db._holder_series = mutated
        return lambda: setattr(db, '_holder_series', _series_original)

    def _requalify(c, d):
        c['qualifies'] = c['state'] == db.CLAIM_ESTABLISHED and bool(c['as_of']) and c['as_of'] <= d and c['strength'] == db.STRENGTH_KNOWING and c['value'] is not None

    def series_candidate_alone_governs():
        # a knowing candidate (the document read, unaccepted) qualifies without an established relationship
        def post(c, session, knowing, role_of, d, role_key):
            if c['strength'] == db.STRENGTH_KNOWING and bool(c['as_of']) and c['as_of'] <= d and c['value'] is not None:
                c['qualifies'] = True
        return _swap_series(post)

    def series_multiplicity_lifts():
        # an established claim with two origins qualifies whatever their class (Rob's spreadsheet, read and accepted)
        def post(c, session, knowing, role_of, d, role_key):
            if c['state'] == db.CLAIM_ESTABLISHED and len(c['origins']) >= 2 and bool(c['as_of']) and c['as_of'] <= d and c['value'] is not None:
                c['qualifies'] = True
        return _swap_series(post)

    def series_institution_document_governs():
        # any institution's document, read and accepted, enters the holder's series (K2 by the back door)
        def post(c, session, knowing, role_of, d, role_key):
            for o in c['origins']:
                rel = session.get(db.EvidentiaryRelationship, o['ground'])
                if rel.reading_id is not None and o['party'] is not None and db.party_foundation(session.get(db.Party, o['party'])) == 'institution':
                    c['strength'] = db.STRENGTH_KNOWING
                    _requalify(c, d)
        return _swap_series(post)

    def series_dated_by_acceptance():
        # the position takes the establishing utterance's date, not the claim's as_of
        def post(c, session, knowing, role_of, d, role_key):
            dates = []
            for o in c['origins']:
                rel = session.get(db.EvidentiaryRelationship, o['ground'])
                if rel.utterance is not None and rel.utterance.asserted_at:
                    dates.append(rel.utterance.asserted_at[:10])
            if dates and any(session.get(db.EvidentiaryRelationship, o['ground']).reading_id is not None for o in c['origins']):
                c['as_of'] = max(dates)
                _requalify(c, d)
        return _swap_series(post)

    def series_role_at_d():
        # role-at-date collapsed: the origin's role read at d instead of at the claim's as_of
        def post(c, session, knowing, role_of, d, role_key):
            if c['asserter'] is not None and c['as_of']:
                answer, _ = role_of(c['asserter'], d)
                c[role_key] = answer
                c['strength'] = (db.STRENGTH_KNOWING if answer == db.EFFECT_IN else db.STRENGTH_NOT_KNOWING if answer == db.EFFECT_NOT else db.STRENGTH_UNDETERMINED)
                _requalify(c, d)
        return _swap_series(post)

    def series_establishing_party_asserts():
        # the governing entry's asserter is the party that established the claim, not the knowing origin (F6 reversed)
        def post(c, session, knowing, role_of, d, role_key):
            est = [o for o in c['origins'] if o['state'] == db.CLAIM_ESTABLISHED and o['asserter'] is not None]
            if est and c['asserter'] != est[0]['asserter']:
                c['asserter'] = est[0]['asserter']
        return _swap_series(post)

    _series_mutations = [
        ('a knowing candidate alone governs the series (7J-F4-F1)', series_candidate_alone_governs),
        ('multiplicity lifts the relay into the series (7J-F4-F1, Sb10 reversed)', series_multiplicity_lifts),
        ("an institution's document enters by the back door (7J-F4-F1, K2 - Sb8 reversed)", series_institution_document_governs),
        ("the position dated by the acceptance (7J-F4-F1, Sb11 reversed)", series_dated_by_acceptance),
        ('the role read at d, not at as_of (7J-F4-F1, role-at-date collapsed)', series_role_at_d),
        ('the establishing party reported as the governing asserter (7J-F4-F1, F6 reversed)', series_establishing_party_asserts),
    ]

    # ── 7G-K2-F7 (s 7G-K2-F7.8): THE CROSSING TEST. K2's balance half is closed under L - the servicer's
    # balance is listed and never admitted - and F7 adds the servicer answer to the report only. These three
    # mutations are the ways that reported field could silently become semantic input.
    def servicer_qualifies():
        # L crossed: the servicer answer qualifies a claim, so the servicer's balance governs
        def post(out, *_):
            for c in out['stated']['claims']:
                if not c['qualifies'] and c.get('servicer') == db.EFFECT_IN and c['as_of'] and c['as_of'] <= out['d'] and c['value'] is not None:
                    c['qualifies'] = True
            q = [c for c in out['stated']['claims'] if c['qualifies'] and c['as_of'] <= out['d']]
            if q:
                b = max(c['as_of'] for c in q)
                at = [c for c in q if c['as_of'] == b]
                if len({c['value'] for c in at}) == 1:
                    out['stated'] = dict(out['stated'], governing={'claim': at[0]['claim'], 'asserter': at[0]['asserter'], 'as_of': b, 'value': at[0]['value']}, reason=None)
                    for name, disch in (('attached', False), ('confirmed', True)):
                        f, total = out['figures'][name], at[0]['value']
                        for pm in out['payments']:
                            if pm['attachment']['state'] == db.CLAIM_ESTABLISHED and not pm['netted'] and (not disch or pm['station'] == db.STATION_DISCHARGED)                                     and pm['amount']['value'] is not None and pm['direction']['sign'] is not None and pm['occurred_on']['value'] and pm['occurred_on']['value'] > b:
                                total += pm['direction']['sign'] * pm['amount']['value']
                        f['value'], f['reason'] = total, None
                    out['figures']['remaining']['value'] = out['figures']['confirmed']['value']
            return out
        return _swap(post)

    def servicer_substituted():
        # the servicer answer substituted for the entitled one
        def post(out, *_):
            for c in out['stated']['claims']:
                if c.get('servicer') is not None:
                    c['entitled'] = c['servicer']
                for o in c['origins']:
                    if o.get('servicer') is not None:
                        o['entitled'] = o['servicer']
            return out
        return _swap(post)

    def servicer_as_label():
        # a label instead of the four-valued answer: an absence reads as a negative
        def post(out, *_):
            for c in out['stated']['claims']:
                if 'servicer' in c:
                    c['servicer'] = 'your servicer' if c['servicer'] == db.EFFECT_IN else 'a stranger'
            return out
        return _swap(post)

    return _series_mutations + [
        ('the servicer answer qualifies a claim (7G-K2-F7, L crossed)', servicer_qualifies),
        ('the servicer answer substituted for the entitled one (7G-K2-F7)', servicer_substituted),
        ('the servicer answer reported as a label (7G-K2-F7, Reading B)', servicer_as_label),
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
