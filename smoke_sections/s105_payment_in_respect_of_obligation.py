"""payment_in_respect_of_obligation: the one ruled relation between a payment and an obligation - a party's
assertion that the subject payment was in respect of the object obligation, and nothing above that floor -
and THE D' INVARIANT: it is not derivable from payment_in_respect_of(p, X) + obligation_in_respect_of(O, X),
nor from any composition whose only shared operand is X, nor from E's acknowledgment; convergence is neither
a party nor a reading. Whether each way of letting it is caught.

`gw 2.0/RELATION_SEMANTICS.md` pass D' (ruled 2026-09-15). Runs the build gate
(`tests/test_payment_in_respect_of_obligation_fixture.py`), then a static scan, then breaks the slice twelve ways:

    the label establishes           the matcher's pairing acquires a party's assertion
    CONVERGENCE DERIVES             p->X + O->X inserts p->O (the obvious join)
    a selector appears              `find_obligation_for_payment(payment)` is exposed
    an accessor appears             `Payment.obligation` is exposed
    acknowledgment derives          E's acknowledgment of p inserts p->O for E's obligations
    discharge is derived            `discharged_by(obligation)` is exposed
    remaining moves                 `remaining_on(obligation)` is exposed
    the phrase supplies order       a guard refuses the relation when the obligation was minted after the payment (D'4)
    the inverse is manufactured     the registry gains an obligation -> payment kind
    replaces composes               obligation_replaces(O3, O1) + p->O1 inserts p->O3
    toward comes back               the registry gains `toward`
    the kind turns symmetric        the registry entry flips symmetric True

Static scan (the migration-shape assertion): no fixture or smoke section still uses `toward` as a
proposition KIND on a payment -> obligation pair - the D' stand-in is retired INTO the ruled kind everywhere;
prose, view strings and docstring uses of the word are not propositions and are untouched.

Same shape as s103 / s104: fixture passes, every mutation is caught, the baseline is re-established after
every undo, the module is left as found.
"""
import importlib.util
import io
import re
import contextlib

# The stand-in used as a proposition KIND - prop(...) with the word as its first argument, or a kind= /
# kind== comparison against it. Anything else containing the word (docstrings, view text, check names,
# comment lines) is not a kind; comment lines are skipped so the scanner never matches its own description.
_TOWARD_AS_KIND = re.compile(r"""(prop\(\s*['"]toward['"]|kind\s*=\s*['"]toward['"]|kind\s*==\s*['"]toward['"])""")


def _load_fixture(BASE):
    path = BASE / 'tests' / 'test_payment_in_respect_of_obligation_fixture.py'
    spec = importlib.util.spec_from_file_location('test_payment_in_respect_of_obligation_fixture', path)
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


def _toward_as_kind_uses(BASE):
    hits = []
    for folder in ('tests', 'smoke_sections'):
        for f in sorted((BASE / folder).glob('*.py')):
            for n, line in enumerate(f.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
                if line.lstrip().startswith('#'):
                    continue
                if _TOWARD_AS_KIND.search(line):
                    hits.append(f'{folder}/{f.name}:{n}')
    return hits


def _mutations(db):
    from sqlalchemy import event
    P, E = db.Proposition.__table__, db.EvidentiaryRelationship.__table__
    PAY, O = db.Payment.__table__, db.Obligation.__table__

    def label_establishes():
        def manufacture(mapper, connection, target):
            if target.reading_id is None:
                return
            p = connection.execute(P.select().where(P.c.id == target.proposition_id)).first()
            if p is not None and p.kind == db.PAYMENT_IN_RESPECT_OF_OBLIGATION:
                u = connection.execute(db.Utterance.__table__.select().limit(1)).first()
                connection.execute(E.insert().values(proposition_id=p.id, utterance_id=u.id))
        event.listen(db.EvidentiaryRelationship, 'after_insert', manufacture)
        return lambda: event.remove(db.EvidentiaryRelationship, 'after_insert', manufacture)

    def convergence_derives():
        # The obvious join, written by someone six months from now: p->X and O->X share X, so p->O.
        def join(mapper, connection, target):
            if target.kind == db.PAYMENT_IN_RESPECT_OF and target.subject_payment_id and target.object_expense_id:
                for r in connection.execute(P.select().where(P.c.kind == db.OBLIGATION_IN_RESPECT_OF,
                                                              P.c.object_expense_id == target.object_expense_id)).fetchall():
                    connection.execute(P.insert().values(
                        kind=db.PAYMENT_IN_RESPECT_OF_OBLIGATION, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                        subject_payment_id=target.subject_payment_id, object_obligation_id=r.subject_obligation_id))
            elif target.kind == db.OBLIGATION_IN_RESPECT_OF and target.subject_obligation_id and target.object_expense_id:
                for r in connection.execute(P.select().where(P.c.kind == db.PAYMENT_IN_RESPECT_OF,
                                                              P.c.object_expense_id == target.object_expense_id)).fetchall():
                    connection.execute(P.insert().values(
                        kind=db.PAYMENT_IN_RESPECT_OF_OBLIGATION, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                        subject_payment_id=r.subject_payment_id, object_obligation_id=target.subject_obligation_id))
        event.listen(db.Proposition, 'after_insert', join)
        return lambda: event.remove(db.Proposition, 'after_insert', join)

    def selector_appears():
        db.find_obligation_for_payment = lambda session, payment: None
        return lambda: delattr(db, 'find_obligation_for_payment')

    def accessor_appears():
        db.Payment.obligation = None
        return lambda: delattr(db.Payment, 'obligation')

    def acknowledgment_derives():
        def derive(mapper, connection, target):
            if target.kind != 'acknowledged' or not target.subject_party_id or not target.object_payment_id:
                return
            for r in connection.execute(P.select().where(P.c.kind == 'entitled_party',
                                                          P.c.subject_party_id == target.subject_party_id)).fetchall():
                connection.execute(P.insert().values(
                    kind=db.PAYMENT_IN_RESPECT_OF_OBLIGATION, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                    subject_payment_id=target.object_payment_id, object_obligation_id=r.object_obligation_id))
        event.listen(db.Proposition, 'after_insert', derive)
        return lambda: event.remove(db.Proposition, 'after_insert', derive)

    def discharge_derived():
        db.discharged_by = lambda session, obligation: []
        return lambda: delattr(db, 'discharged_by')

    def remaining_moves():
        db.remaining_on = lambda session, obligation: 0
        return lambda: delattr(db, 'remaining_on')

    def phrase_supplies_order():
        def refuse_out_of_order(mapper, connection, target):
            if target.kind != db.PAYMENT_IN_RESPECT_OF_OBLIGATION or not target.subject_payment_id or not target.object_obligation_id:
                return
            p = connection.execute(PAY.select().where(PAY.c.id == target.subject_payment_id)).first()
            o = connection.execute(O.select().where(O.c.id == target.object_obligation_id)).first()
            if p is not None and o is not None and o.created_at >= p.created_at:   # 'must precede' is strict: a tie is not precedence (same-tick mints; cf. s104)
                raise ValueError('an obligation must exist before a payment in respect of it')
        event.listen(db.Proposition, 'before_insert', refuse_out_of_order)
        return lambda: event.remove(db.Proposition, 'before_insert', refuse_out_of_order)

    def inverse_manufactured():
        db.RULED_KINDS['obligation_paid_by'] = {'subject': ('subject_obligation_id',), 'object': ('object_payment_id',),
                                               'symmetric': False, 'reading_establishes': False, 'relational_knowing': True}
        return lambda: db.RULED_KINDS.pop('obligation_paid_by', None)

    def replaces_composes():
        def compose(mapper, connection, target):
            if target.kind != db.OBLIGATION_REPLACES or not target.subject_obligation_id or not target.object_obligation_id:
                return
            for r in connection.execute(P.select().where(P.c.kind == db.PAYMENT_IN_RESPECT_OF_OBLIGATION,
                                                          P.c.object_obligation_id == target.object_obligation_id)).fetchall():
                connection.execute(P.insert().values(
                    kind=db.PAYMENT_IN_RESPECT_OF_OBLIGATION, subject_state=db.PARTICIPANT_ESTABLISHED, object_state=db.PARTICIPANT_ESTABLISHED,
                    subject_payment_id=r.subject_payment_id, object_obligation_id=target.subject_obligation_id))
        event.listen(db.Proposition, 'after_insert', compose)
        return lambda: event.remove(db.Proposition, 'after_insert', compose)

    def toward_comes_back():
        db.RULED_KINDS['toward'] = {'subject': ('subject_payment_id',), 'object': ('object_obligation_id',),
                                    'symmetric': False, 'reading_establishes': False, 'relational_knowing': True}
        return lambda: db.RULED_KINDS.pop('toward', None)

    def kind_turns_symmetric():
        rule = db.RULED_KINDS[db.PAYMENT_IN_RESPECT_OF_OBLIGATION]
        db.RULED_KINDS[db.PAYMENT_IN_RESPECT_OF_OBLIGATION] = dict(rule, symmetric=True)
        return lambda: db.RULED_KINDS.__setitem__(db.PAYMENT_IN_RESPECT_OF_OBLIGATION, rule)

    return [
        ("the matcher's pairing acquires a party's assertion", label_establishes),
        ('CONVERGENCE DERIVES - p->X + O->X inserts p->O', convergence_derives),
        ('a selector chooses an obligation for a payment', selector_appears),
        ('a payment.obligation accessor appears', accessor_appears),
        ("E's acknowledgment derives the relation", acknowledgment_derives),
        ('discharge is derived', discharge_derived),
        ('remaining moves', remaining_moves),
        ("the phrase supplies temporal order (D'4)", phrase_supplies_order),
        ('the inverse kind is manufactured', inverse_manufactured),
        ('obligation_replaces composes into the relation', replaces_composes),
        ('toward comes back as a kind', toward_comes_back),
        ('the kind turns symmetric', kind_turns_symmetric),
    ]


def run(ctx):
    check, BASE = ctx.check, ctx.BASE

    try:
        from core import database as db
    except Exception as e:                                    # noqa: BLE001
        check(f'core/database.py imports ({type(e).__name__}: {e})', False)
        return
    check('core/database.py carries payment_in_respect_of_obligation exactly as authorised, the non-derivability clause beside it, and nothing at family level',
          hasattr(db, 'PAYMENT_IN_RESPECT_OF_OBLIGATION')
          and db.RULED_KINDS[db.PAYMENT_IN_RESPECT_OF_OBLIGATION] == {'subject': ('subject_payment_id',), 'object': ('object_obligation_id',),
                                                                       'symmetric': False, 'reading_establishes': False, 'relational_knowing': True}
          and 'toward' not in db.RULED_KINDS
          and db.RULED_KINDS[db.PAYMENT_IN_RESPECT_OF]['object'] == ('object_expense_id',)
          and 'NON-DERIVABILITY' in (BASE / 'core' / 'database.py').read_text(encoding='utf-8', errors='replace')
          and not any(hasattr(db, n) for n in ('Relation', 'RelationBase', 'relation_resolver', 'find_obligation_for_payment',
                                               'discharged_by', 'remaining_on', 'obligation_paid_by'))
          and not hasattr(db.Payment, 'obligation'))

    hits = _toward_as_kind_uses(BASE)
    check('migration shape: no fixture or smoke section still uses toward as a proposition kind - the stand-in is retired into the ruled kind everywhere, and nothing else was reclassified',
          not hits)
    for h in hits[:8]:
        print(f'        toward-as-kind at: {h}')

    try:
        fx = _load_fixture(BASE)
    except Exception as e:                                    # noqa: BLE001
        check(f'the payment-in-respect-of-obligation fixture loads ({type(e).__name__}: {e})', False)
        return

    passed, failures, err = _run_fixture(fx, db)
    check('the payment-in-respect-of-obligation fixture passes in full',
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
