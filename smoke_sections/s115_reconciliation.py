"""reconciliation: the eighth consumer - EQUATES NOTHING, DETERMINES NOTHING - and whether each way of letting it SETTLE
is caught.

`gw 2.0/CONSUMER_DERIVATIONS.md` pass 7H (ruled 2026-09-19, s 7H.8). Runs the build gate
(`tests/test_reconciliation_fixture.py`) and then breaks the consumer ten ways, each an attempt to settle:

    the PR becomes the balance          the obligation's stated position is replaced by the patient responsibility
    a verdict                           the comparison gains `matches: True/False`
    zero is user_paid_cash              unresolved 0 with no claim yields a current determination
    a denial is unpaid                  a denial claim on the expense yields current `unpaid`
    pending_claim is unpaid             the two names collapse to one
    the balances are summed             several obligations are summed against the PR
    the PR is apportioned               the PR is split across several obligations and each compared
    the household's figure governs      a PR claim by a household person governs
    a payment to the provider counts    a payment to the provider with no membership ground enters the funding view
    it stores                           `reconciliation_cache` appears on the module

Same shape as s107-s114: fixture passes, every mutation is caught, the baseline is re-established after every undo,
the module is left as found.
"""
import importlib.util
import io
import contextlib
from decimal import Decimal


def _load_fixture(BASE):
    path = BASE / 'tests' / 'test_reconciliation_fixture.py'
    spec = importlib.util.spec_from_file_location('test_reconciliation_fixture', path)
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
    original = db.reconciliation

    def _swap(post):
        def mutated(session, expense, d, catalogue, knowing):
            return post(original(session, expense, d, catalogue, knowing), session, expense, d, catalogue, knowing)
        mutated.__doc__ = original.__doc__
        db.reconciliation = mutated
        return lambda: setattr(db, 'reconciliation', original)

    def pr_becomes_balance():
        def post(out, *_):
            PR = out['stances']['patient_responsibility']['governing']
            if PR is not None:
                for o in out['obligations']:
                    if o['stated'] is not None:
                        o['stated'] = dict(o['stated'], value=PR['value'])
                        o['confirmed'] = PR['value']
                if out['comparison']['difference'] is not None:
                    out['comparison']['stated'] = dict(out['comparison']['stated'], value=PR['value'])
                    out['comparison']['difference'] = Decimal(0)
            return out
        return _swap(post)

    def a_verdict():
        def post(out, *_):
            if out['comparison']['difference'] is not None:
                out['comparison']['matches'] = out['comparison']['difference'] == 0
            return out
        return _swap(post)

    def zero_is_paid():
        def post(out, *_):
            if out['unresolved']['value'] == 0 and out['determinations']['current'] is None:
                out['determinations']['current'] = {'name': 'user_paid_cash', 'asserters': [], 'claims': []}
                out['determinations']['reason'] = None
            return out
        return _swap(post)

    def denial_is_unpaid():
        def post(out, session, expense, *_):
            if out['determinations']['current'] is None and session.query(db.Proposition).filter_by(kind='denial', subject_expense_id=expense.id).count():
                out['determinations']['current'] = {'name': 'unpaid', 'asserters': [], 'claims': []}
                out['determinations']['reason'] = None
            return out
        return _swap(post)

    def pending_is_unpaid():
        def post(out, *_):
            cur = out['determinations']['current']
            if cur is not None and cur['name'] == 'pending_claim':
                cur['name'] = 'unpaid'
            for c in out['determinations']['claims']:
                if c['name'] == 'pending_claim':
                    c['name'] = 'unpaid'
            return out
        return _swap(post)

    def balances_summed():
        def post(out, *_):
            PR = out['stances']['patient_responsibility']['governing']
            if len(out['obligations']) > 1 and PR is not None and all(o['stated'] is not None for o in out['obligations']):
                total = sum(o['stated']['value'] for o in out['obligations'])
                out['comparison'] = {'obligation': None, 'stated': {'value': total}, 'patient_responsibility': PR, 'difference': total - PR['value'], 'reason': None}
            return out
        return _swap(post)

    def pr_apportioned():
        def post(out, *_):
            PR = out['stances']['patient_responsibility']['governing']
            if len(out['obligations']) > 1 and PR is not None:
                each = PR['value'] / len(out['obligations'])
                out['comparison']['apportioned'] = [(o['obligation'], each) for o in out['obligations']]
            return out
        return _swap(post)

    def household_governs():
        def post(out, session, *_):
            persons = {p.party.id for p in session.query(db.Person).all()}
            st = out['stances']['patient_responsibility']
            hh = [c for c in st['claims'] if c['asserter'] in persons and c['state'] == db.CLAIM_ESTABLISHED and c['value'] is not None]
            if hh:
                c = max(hh, key=lambda x: x['as_of'])
                st['governing'] = {'claim': c['claim'], 'asserter': c['asserter'], 'as_of': c['as_of'], 'value': c['value']}
                if out['comparison']['stated'] is not None and len(out['obligations']) == 1 and not out['obligations'][0]['other_expenses']:
                    out['comparison']['patient_responsibility'] = st['governing']
                    out['comparison']['difference'] = out['comparison']['stated']['value'] - c['value']
                    out['comparison']['reason'] = None
            return out
        return _swap(post)

    def provider_payment_counts():
        def post(out, session, expense, d, catalogue, knowing):
            role = catalogue['provider_of']
            members = {pm['payment'] for pm in out['payments']} | {p for _, p in out['candidate_payments']} | {p for _, p in out['contested_payments']}
            for pt in session.query(db.Proposition).filter_by(kind=catalogue['paid_to']).all():
                if pt.object_payment_id in members or pt.subject_party_id is None:
                    continue
                if db._entitled_at(session, pt.subject_party_id, role, expense.id, pt.as_of)[0] != db.EFFECT_IN:
                    continue
                amt = session.query(db.Proposition).filter_by(kind=catalogue['payment_amount'], subject_payment_id=pt.object_payment_id).first()
                if amt is None or db._money(amt.content) is None:
                    continue
                out['payments'].append({'payment': pt.object_payment_id, 'grounds': [], 'amount': {'value': db._money(amt.content), 'reason': None},
                                        'occurred_on': {'value': pt.as_of, 'reason': None}, 'direction': {'sign': -1, 'reason': None, 'payers': [], 'payees': [pt.subject_party_id]},
                                        'attached_to': []})
                if out['unresolved']['value'] is not None:
                    out['unresolved']['value'] -= db._money(amt.content)
                    out['unresolved']['terms'].append((pt.object_payment_id, -1, db._money(amt.content)))
            return out
        return _swap(post)

    def it_stores():
        db.reconciliation_cache = {}
        return lambda: delattr(db, 'reconciliation_cache')

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

    return _series_mutations + [
        ('the patient responsibility becomes the balance', pr_becomes_balance),
        ('a verdict (matches)', a_verdict),
        ('zero is user_paid_cash', zero_is_paid),
        ('a denial is unpaid', denial_is_unpaid),
        ('pending_claim is unpaid', pending_is_unpaid),
        ('the balances are summed against the PR', balances_summed),
        ('the PR is apportioned across obligations', pr_apportioned),
        ("the household's PR figure governs", household_governs),
        ('a payment to the provider without membership counts', provider_payment_counts),
        ('the answer is stored', it_stores),
    ]


def run(ctx):
    check, BASE = ctx.check, ctx.BASE

    try:
        from core import database as db
    except Exception as e:                                    # noqa: BLE001
        check(f'core imports ({type(e).__name__}: {e})', False)
        return
    check('core/database.py carries reconciliation beside reconstruction, read-only, four closed determination names, with no matches / reconcile / determine / classify / cache helper',
          callable(getattr(db, 'reconciliation', None)) and db.DETERMINATION_NAMES == ('provider_adjustment', 'user_paid_cash', 'unpaid', 'pending_claim')
          and not any(hasattr(db, n) for n in ('matches', 'reconcile', 'corresponding_amount', 'infer_determination', 'mark_paid', 'deductible',
                                                'apportion', 'reconciliation_cache', 'DETERMINATION_MAP')))

    try:
        fx = _load_fixture(BASE)
    except Exception as e:                                    # noqa: BLE001
        check(f'the reconciliation fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, db)
    check('the reconciliation fixture passes in full',
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
