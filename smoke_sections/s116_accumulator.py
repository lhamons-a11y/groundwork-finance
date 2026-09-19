"""plans_in_effect / accumulator: the last consumers - NO HOUSEHOLD-LEVEL ANSWER MANUFACTURED - and whether each way of
letting them ANSWER FOR THE HOUSEHOLD is caught.

`gw 2.0/CONSUMER_DERIVATIONS.md` pass 7J (ruled 2026-09-19, s 7J.7). Runs the build gate
(`tests/test_accumulator_fixture.py`) and then breaks the consumers eleven ways, each an attempt to answer for the
household:

    pick the earlier plan               with two plans in effect only the earliest-begun survives; `primary` appears
    eligibility from the stance         an insurer's "never eligible" removes the plan from in_effect
    the stance ends the membership      a candidate ending from the insurer's letter is treated as established
    met                                 the report gains `met: True/False`
    zero from no term                   an unknown term reads as 0 and remaining is computed
    exempt reads unknown                an exempt expense makes the derived figure undetermined
    zero for unadjudicated              an unadjudicated expense contributes 0
    the household's accumulator governs a household deductible_applied claim governs stated
    one accumulator                     stated and derived averaged into a single figure
    X -> P from membership              an expense incurred by a member enters the plan's sum without the asserted relation
    it stores                           `accumulator_cache` appears on the module

Same shape as s107-s115: fixture passes, every mutation is caught, the baseline is re-established after every undo,
the module is left as found.
"""
import importlib.util
import io
import contextlib
from decimal import Decimal


def _load_fixture(BASE):
    path = BASE / 'tests' / 'test_accumulator_fixture.py'
    spec = importlib.util.spec_from_file_location('test_accumulator_fixture', path)
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
    pie0, acc0 = db.plans_in_effect, db.accumulator

    def _swap_pie(post):
        def mutated(session, person, d, catalogue, knowing):
            return post(pie0(session, person, d, catalogue, knowing), session, person, d, catalogue, knowing)
        mutated.__doc__ = pie0.__doc__
        db.plans_in_effect = mutated
        return lambda: setattr(db, 'plans_in_effect', pie0)

    def _swap_acc(post):
        def mutated(session, plan, d, catalogue, knowing, person=None):
            return post(acc0(session, plan, d, catalogue, knowing, person=person), session, plan, d, catalogue, knowing, person)
        mutated.__doc__ = acc0.__doc__
        db.accumulator = mutated
        return lambda: setattr(db, 'accumulator', acc0)

    def _consequences(out):
        S = out['stated']['governing']
        dv = out['derived']['value']
        out['dispute'] = {'value': S['value'] - dv, 'reason': None} if (S is not None and dv is not None) else {'value': None, 'reason': 'x'}
        if out['term']['state'] == db.TERM_AMOUNT and dv is not None:
            out['remaining'] = {'value': out['term']['value'] - dv, 'reason': None}

    def pick_earlier():
        def post(out, *_):
            if len(out['in_effect']) > 1:
                first = min(out['in_effect'], key=lambda p: min(st['as_of'] for st in out['plans'][p]['governing']))
                out['in_effect'], out['overlap'], out['primary'] = [first], [], first
            return out
        return _swap_pie(post)

    def eligibility_from_stance():
        def post(out, *_):
            for pid, v in out['plans'].items():
                if any(e['state'] == db.CLAIM_ESTABLISHED and 'never' in (e['content'] or '') for e in v['eligibility']):
                    v['answer'] = db.EFFECT_NOT
            out['in_effect'] = [p for p, v in out['plans'].items() if v['answer'] == db.EFFECT_IN]
            out['overlap'] = out['in_effect'] if len(out['in_effect']) > 1 else []
            return out
        return _swap_pie(post)

    def stance_ends_membership():
        def post(out, *_):
            for pid, v in out['plans'].items():
                cand = [st for st in v['stances'] if st['state'] == db.CLAIM_CANDIDATE and st['sort'] == 'ended' and st['as_of'] <= out['d']]
                if cand and v['answer'] == db.EFFECT_IN:
                    v['answer'] = db.EFFECT_NOT
            out['in_effect'] = [p for p, v in out['plans'].items() if v['answer'] == db.EFFECT_IN]
            out['overlap'] = out['in_effect'] if len(out['in_effect']) > 1 else []
            return out
        return _swap_pie(post)

    def met():
        def post(out, *_):
            out['met'] = out['remaining']['value'] is not None and out['remaining']['value'] <= 0
            return out
        return _swap_acc(post)

    def zero_from_no_term():
        def post(out, *_):
            if out['term']['state'] == db.TERM_UNKNOWN:
                out['term'] = dict(out['term'], state=db.TERM_AMOUNT, value=Decimal(0), reason=None)
                _consequences(out)
            return out
        return _swap_acc(post)

    def exempt_reads_unknown():
        def post(out, *_):
            if out['derived']['exempt'] and out['derived']['value'] is not None:
                out['derived']['undetermined'] = [(x, 'exempt read as unknown') for x, _ in out['derived']['exempt']]
                out['derived']['value'], out['derived']['reason'] = None, 'undetermined: exempt'
                out['dispute'] = {'value': None, 'reason': 'x'}
                out['remaining'] = {'value': None, 'reason': 'x'}
            return out
        return _swap_acc(post)

    def zero_for_unadjudicated():
        def post(out, *_):
            if out['derived']['unadjudicated'] and out['window']['start'] is not None:
                others = [r for r in out['derived']['undetermined'] if r[0] not in out['derived']['unadjudicated']]
                if not others:
                    out['derived']['value'] = sum((a for _, a, _ in out['derived']['basis']), Decimal(0))
                    out['derived']['reason'], out['derived']['undetermined'] = None, []
                    _consequences(out)
            return out
        return _swap_acc(post)

    def household_governs():
        def post(out, session, *_):
            persons = {p.party.id for p in session.query(db.Person).all()}
            hh = [c for c in out['stated']['claims'] if c['asserter'] in persons and c['state'] == db.CLAIM_ESTABLISHED and c['value'] is not None and c['as_of'] <= out['d']]
            if hh:
                c = max(hh, key=lambda x: x['as_of'])
                out['stated']['governing'] = {'claim': c['claim'], 'asserter': c['asserter'], 'as_of': c['as_of'], 'value': c['value']}
                out['stated']['reason'] = None
                _consequences(out)
            return out
        return _swap_acc(post)

    def one_accumulator():
        def post(out, *_):
            S = out['stated']['governing']
            if S is not None and out['derived']['value'] is not None:
                one = (S['value'] + out['derived']['value']) / 2
                out['derived']['value'] = one
                out['stated']['governing'] = dict(S, value=one)
                _consequences(out)
            return out
        return _swap_acc(post)

    def x_to_p_from_membership():
        def post(out, session, plan, d, catalogue, knowing, person):
            members = {e['id'] for e in db.reach(session, plan, catalogue['under_plan'], as_object=True)['endpoints'] if e['state'] == db.CLAIM_ESTABLISHED}
            members |= {c.subject_party_id for c in session.query(db.Proposition).filter(db.Proposition.kind == catalogue['under_plan'] + '_began', db.Proposition.object_plan_id == plan.id).all()}
            known = {x for x, _, _ in out['derived']['basis']} | {x for x, _ in out['derived']['exempt']} | set(out['derived']['unadjudicated']) | {x for x, _ in out['derived']['outside_window']}
            added = Decimal(0)
            for m in members:
                for e in db.reach(session, session.get(db.Party, m), catalogue['incurred_by'])['endpoints']:
                    if e['state'] != db.CLAIM_ESTABLISHED or e['id'] in known:
                        continue
                    adj = session.query(db.Proposition).filter_by(kind=catalogue['applied_to_deductible'], subject_expense_id=e['id']).first()
                    if adj is not None and db._money(adj.content) is not None:
                        out['derived']['basis'].append((e['id'], db._money(adj.content), adj.id))
                        added += db._money(adj.content)
                        known.add(e['id'])
            if added and out['derived']['value'] is not None:
                out['derived']['value'] += added
                _consequences(out)
            return out
        return _swap_acc(post)

    def it_stores():
        db.accumulator_cache = {}
        return lambda: delattr(db, 'accumulator_cache')

    return [
        ('pick the earlier plan (a primary)', pick_earlier),
        ('eligibility from the insurer\'s stance', eligibility_from_stance),
        ('the insurer\'s candidate ending ends the membership', stance_ends_membership),
        ('met', met),
        ('zero from no term', zero_from_no_term),
        ('exempt reads unknown', exempt_reads_unknown),
        ('zero for an unadjudicated expense', zero_for_unadjudicated),
        ('the household\'s accumulator governs', household_governs),
        ('stated and derived averaged into one accumulator', one_accumulator),
        ('an expense enters the plan from membership', x_to_p_from_membership),
        ('the answer is stored', it_stores),
    ]


def run(ctx):
    check, BASE = ctx.check, ctx.BASE

    try:
        from core import database as db
    except Exception as e:                                    # noqa: BLE001
        check(f'core imports ({type(e).__name__}: {e})', False)
        return
    check('core/database.py carries plans_in_effect and accumulator beside reconciliation, read-only, the term on three named states, with no plan_at / primary / eligible / covered / met / cache helper',
          callable(getattr(db, 'plans_in_effect', None)) and callable(getattr(db, 'accumulator', None))
          and (db.TERM_AMOUNT, db.TERM_NONE, db.TERM_UNKNOWN) == ('amount', 'none', 'unknown')
          and not any(hasattr(db, n) for n in ('plan_at', 'primary_plan', 'is_eligible', 'is_covered', 'deductible_met', 'met', 'accumulator_cache',
                                                'resolve_overlap', 'household_accumulator', 'plan_for_expense')))

    try:
        fx = _load_fixture(BASE)
    except Exception as e:                                    # noqa: BLE001
        check(f'the accumulator fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, db)
    check('the accumulator fixture passes in full',
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
