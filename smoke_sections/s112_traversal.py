"""reach / in_effect: the traversal consumers - ONE HOP, EVERY ENDPOINT, NOTHING CHOSEN - and whether each way
of letting them CHOOSE or EXTEND is caught.

`gw 2.0/CONSUMER_DERIVATIONS.md` pass 7F (ruled 2026-09-18, TS s 7F.8). Runs the build gate
(`tests/test_traversal_fixture.py`) and then breaks the consumers twelve ways, each an attempt to choose or extend:

    pick the newest endpoint          only the highest claim id survives
    pick the household's              endpoints asserted by others are dropped
    compose the second hop            an obligation's expenses gain the payments in respect of those expenses (via)
    project onto the subject          the endpoint's nature claim is reported as the subject's
    infer the plan from membership    an expense reaches a plan through the person who incurred it
    resolve the overlap               with two identities in effect only the earliest-begun survives
    the earlier ending governs        contested becomes not_in_effect (the governing set wins)
    absence reads not in effect       undetermined becomes not_in_effect
    a retraction is an ending         a contested stance is read as an ended stance
    a reading's stance counts         candidate stances are treated as established
    a period is materialised          the report gains `period: (began, ended)`
    it stores                         `in_effect_cache` appears on the module

Same shape as s107-s111: fixture passes, every mutation is caught, the baseline is re-established after every
undo, the module is left as found.
"""
import importlib.util
import io
import contextlib


def _load_fixture(BASE):
    path = BASE / 'tests' / 'test_traversal_fixture.py'
    spec = importlib.util.spec_from_file_location('test_traversal_fixture', path)
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
    reach0, in_effect0, stance0 = db.reach, db.in_effect, db._stance_answer

    def _swap_reach(post):
        def mutated(session, thing, kind, as_object=False):
            return post(reach0(session, thing, kind, as_object), session, thing, kind, as_object)
        mutated.__doc__ = reach0.__doc__
        db.reach = mutated
        return lambda: setattr(db, 'reach', reach0)

    def _swap_effect(post):
        def mutated(session, party, role_kind, d):
            return post(in_effect0(session, party, role_kind, d), session, party, role_kind, d)
        mutated.__doc__ = in_effect0.__doc__
        db.in_effect = mutated
        return lambda: setattr(db, 'in_effect', in_effect0)

    def pick_newest():
        def post(out, *_):
            if out['endpoints']:
                newest = max(out['endpoints'], key=lambda e: e['claim'])
                out['endpoints'] = [newest]
            return out
        return _swap_reach(post)

    def pick_household():
        def post(out, session, *_):
            persons = {p.party.id for p in session.query(db.Person).all()}
            out['endpoints'] = [e for e in out['endpoints'] if e['asserter'] in persons or e['asserter'] is None]
            return out
        return _swap_reach(post)

    def compose_second_hop():
        def post(out, session, thing, kind, as_object):
            if kind == db.OBLIGATION_IN_RESPECT_OF and not as_object:
                for e in list(out['endpoints']):
                    if e['type'] == 'expense':
                        x = session.get(db.Expense, e['id'])
                        for pe in reach0(session, x, db.PAYMENT_IN_RESPECT_OF, as_object=True)['endpoints']:
                            out['endpoints'].append(dict(pe, via=e['id']))
            return out
        return _swap_reach(post)

    def project_onto_subject():
        def post(out, session, thing, kind, as_object):
            for e in out['endpoints']:
                if e['type'] == 'expense':
                    nat = session.query(db.Proposition).filter_by(kind='nature', subject_expense_id=e['id']).first()
                    if nat is not None:
                        out['nature'] = nat.content
            return out
        return _swap_reach(post)

    def infer_plan():
        def post(out, session, thing, kind, as_object):
            if type(thing).__name__ == 'Expense':
                inc = session.query(db.Proposition).filter_by(kind='incurred_by', subject_expense_id=thing.id).first()
                if inc is not None:
                    kim = next((p.party for p in session.query(db.Person).all() if p.display_name == inc.content), None)
                    if kim is not None:
                        for m in reach0(session, kim, db.UNDER_PLAN)['endpoints']:
                            out['endpoints'].append(dict(m, claim=None))
            return out
        return _swap_reach(post)

    def resolve_overlap():
        def post(out, *_):
            if len(out['in_effect']) > 1:
                first = min(out['in_effect'], key=lambda i: min(st['as_of'] for st in out['identities'][i]['governing']))
                for i in out['in_effect']:
                    if i != first:
                        out['identities'][i]['answer'] = db.EFFECT_NOT
                out['in_effect'] = [first]
            return out
        return _swap_effect(post)

    def earlier_ending_governs():
        def post(out, *_):
            for v in out['identities'].values():
                if v['answer'] == db.EFFECT_CONTESTED and v['governing']:
                    v['answer'] = db.EFFECT_NOT if v['governing'][0]['sort'] == 'ended' else db.EFFECT_IN
            out['in_effect'] = [i for i, v in out['identities'].items() if v['answer'] == db.EFFECT_IN]
            return out
        return _swap_effect(post)

    def absence_not_in_effect():
        def post(out, *_):
            for v in out['identities'].values():
                if v['answer'] == db.EFFECT_UNDETERMINED:
                    v['answer'] = db.EFFECT_NOT
            return out
        return _swap_effect(post)

    def retraction_is_ending():
        def mutated(established, d):
            return stance0(established, d)
        def post(out, session, party, role_kind, d):
            for ident, v in out['identities'].items():
                est = [dict(st) for st in v['stances'] if st['state'] == db.CLAIM_ESTABLISHED and st['as_of']]
                for st in v['stances']:
                    if st['state'] == db.CLAIM_CONTESTED:
                        est.append(dict(st, sort='ended', state=db.CLAIM_ESTABLISHED))
                v['answer'], v['governing'], v['next'] = stance0(est, d)
            out['in_effect'] = [i for i, v in out['identities'].items() if v['answer'] == db.EFFECT_IN]
            return out
        return _swap_effect(post)

    def reading_stance_counts():
        def post(out, session, party, role_kind, d):
            for ident, v in out['identities'].items():
                est = [dict(st) for st in v['stances'] if st['state'] in (db.CLAIM_ESTABLISHED, db.CLAIM_CANDIDATE) and st['as_of']]
                v['answer'], v['governing'], v['next'] = stance0(est, d)
            out['in_effect'] = [i for i, v in out['identities'].items() if v['answer'] == db.EFFECT_IN]
            return out
        return _swap_effect(post)

    def period_materialised():
        def post(out, *_):
            for v in out['identities'].values():
                begs = [st['as_of'] for st in v['stances'] if st['sort'] == 'began']
                ends = [st['as_of'] for st in v['stances'] if st['sort'] == 'ended']
                v['period'] = (min(begs) if begs else None, max(ends) if ends else None)
            return out
        return _swap_effect(post)

    def it_stores():
        db.in_effect_cache = {}
        return lambda: delattr(db, 'in_effect_cache')

    return [
        ('pick the newest endpoint', pick_newest),
        ("pick the household's endpoints", pick_household),
        ('compose the second hop (via)', compose_second_hop),
        ("project the endpoint's nature onto the subject", project_onto_subject),
        ('infer the plan from membership', infer_plan),
        ('resolve the overlap', resolve_overlap),
        ('the earlier ending governs a contest', earlier_ending_governs),
        ('absence reads not in effect', absence_not_in_effect),
        ('a retraction is an ending', retraction_is_ending),
        ("a reading's stance counts", reading_stance_counts),
        ('a period is materialised', period_materialised),
        ('the answer is stored', it_stores),
    ]


def run(ctx):
    check, BASE = ctx.check, ctx.BASE

    try:
        from core import database as db
    except Exception as e:                                    # noqa: BLE001
        check(f'core imports ({type(e).__name__}: {e})', False)
        return
    check('core/database.py carries reach and in_effect beside chain_strength, read-only, four dated answers, with no selector / inverse / period / cache helper',
          callable(getattr(db, 'reach', None)) and callable(getattr(db, 'in_effect', None))
          and (db.EFFECT_IN, db.EFFECT_NOT, db.EFFECT_UNDETERMINED, db.EFFECT_CONTESTED) == ('in_effect', 'not_in_effect', 'undetermined', 'contested')
          and not any(hasattr(db, n) for n in ('current_plan_of', 'primary_plan', 'obligation_paid_by', 'plan_covers', 'period_of',
                                                'in_effect_cache', 'reach_cache', 'traverse', 'compose', 'resolve_overlap')))

    try:
        fx = _load_fixture(BASE)
    except Exception as e:                                    # noqa: BLE001
        check(f'the traversal fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, db)
    check('the traversal fixture passes in full',
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
