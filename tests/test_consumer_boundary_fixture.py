# -*- coding: utf-8 -*-
"""The consumer-boundary fixture — is `consume()` the only way in?

`gw 2.0/EVIDENCE_MATRIX.md` finding 9. Gap 4 closed with the enforcement stated as:

    consume() is the only way to take a value; every consumer declares the strength it
    requires; a consumer absent from the table is refused outright.

`consume`'s own docstring makes the same claim: *"The only way to take a value out of a derived
fact."* This fixture asks whether that is **structural or conventional**, using gap 6's method —
which asserted the ABSENCE of a `paid()` accessor so that a future convenience method could not
reintroduce the drift. The analogous assertion was never written here, and this file is it.

Three levels, weakest first:

    1. the declared refusals still fire                    regression guard
    2. no function in the module hands out a raw value     the module's own bypass
    3. no application file reads .value on a derived fact  the guard for the first consumer

**Level 2 is the one that matters**, and it is not hypothetical. `narrator` and `export` are both
declared in `CONSUMER_STRENGTH` with a required strength — and `narrator_facts` and `export_row`
both read `derived.value` directly, so the requirement declared for exactly those two consumers is
never consulted on the path those two consumers use.

**Level 3 excludes tests and smoke sections deliberately.** A fixture inspecting internals is doing
its job; an application surface doing it is the defect. `core/classification.py` has no consumers
outside its own fixtures today, so level 3 passes now and exists to fail later.

Run:  python tests/test_consumer_boundary_fixture.py
"""
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS, FAIL, PENDING = [], [], []


def check(name, condition):
    if condition is None:
        PENDING.append(name)
        print(f'  ....  {name}')
    elif condition:
        PASS.append(name)
        print(f'  OK    {name}')
    else:
        FAIL.append(name)
        print(f'  FAIL  {name}')


# Genuinely neutral, and it took a second attempt to find one. A supermarket or a
# discount store is NOT neutral here and correctly so - MIXED_RETAIL_TERMS gives it one
# weak counterparty signal for the pharmacy counter inside it, which is the state the
# fail-closed zone was written for. A hardware store has no such counter.
NEUTRAL = {'amount': 950.00, 'merchant': 'ACME HARDWARE', 'mcc': '5251',
           'category': 'Home', 'category_set_by': 'importer', 'date': '2026-03-09'}

MODULE = ROOT / 'core' / 'classification.py'

# Files that may legitimately read a raw value: the module that defines the boundary, and
# the fixtures that verify it. Everything else is an application surface.
SCAN_SKIP = ('core/classification.py', 'tests/', 'smoke_sections/', 'vendor/', 'build/',
             'dist/', 'installer/', 'installer_output/', '.claude/')


def _raw_value_readers(module_path):
    """Functions that read `.value` off a parameter, other than `consume`.

    Deliberately narrow: only a read of `<param>.value` counts, so `refusal` returning a
    strength and `gauntlet(...).values()` do not.
    """
    tree = ast.parse(module_path.read_text(encoding='utf-8'))
    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name == 'consume':
            continue
        params = {a.arg for a in node.args.args}
        for sub in ast.walk(node):
            if (isinstance(sub, ast.Attribute) and sub.attr == 'value'
                    and isinstance(sub.value, ast.Name) and sub.value.id in params
                    and isinstance(sub.ctx, ast.Load)):
                offenders.append((node.name, sub.lineno))
    return offenders


# Attributes an application surface may not read directly off a derived fact. `.value` is
# the number (Q1: consume() is the only path). `.sensitivity` is the domain and the
# `manufactured` flag - and an application surface reading it is the one way sensitivity
# reaches the model's findings text, which the voice ruling forbids (HAZARD_AUDIT H5): the
# marking travels to the boundary and the gate, never into the prompt.
GUARDED_ATTRS = ('value', 'sensitivity')


def _application_readers():
    """Application files that import the module and read a guarded attribute off something."""
    out = []
    for path in ROOT.rglob('*.py'):
        rel = path.relative_to(ROOT).as_posix()
        if any(rel.startswith(s) or f'/{s}' in f'/{rel}' for s in SCAN_SKIP):
            continue
        try:
            text = path.read_text(encoding='utf-8')
        except OSError:
            continue
        if 'core.classification' not in text and 'from core import classification' not in text:
            continue
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for sub in ast.walk(tree):
            if (isinstance(sub, ast.Attribute) and sub.attr in GUARDED_ATTRS
                    and isinstance(sub.ctx, ast.Load)):
                out.append((rel, sub.lineno, sub.attr))
    return out


def run(m):
    print('\n1. The declared refusals still fire\n')

    neutral = m.classify(**NEUTRAL)
    weak = m.record_evidence(neutral, m.COUNTERPARTY, source=m.MERCHANT_MATCH, supports=True)
    weak_fact = m.derive('balance', 1250.00, sources=(weak,))

    against = m.record_evidence(neutral, m.CONTENT, source=m.USER_STATED, supports=False)
    contradicted_fact = m.derive('balance', 1250.00, sources=(against,))

    check('a single weak signal is single_weak_signal',
          m.strength_of(weak_fact) == m.SINGLE_WEAK_SIGNAL)
    check('a knowing source saying no is contradicted, at the floor',
          m.strength_of(contradicted_fact) == m.CONTRADICTED)
    check('an undeclared consumer takes nothing at all',
          m.consume(weak_fact, 'a_surface_nobody_declared') is m.UNAVAILABLE)
    check('narrator is refused a fact weaker than corroborated',
          m.consume(weak_fact, 'narrator') is m.UNAVAILABLE)
    check('export is refused a contradicted fact',
          m.consume(contradicted_fact, 'export') is m.UNAVAILABLE)

    print('\n2. No function in the module hands out a raw value\n')

    offenders = _raw_value_readers(MODULE)
    if offenders:
        print('        raw `.value` reads outside consume():')
        for fn, line in offenders:
            print(f'          core/classification.py:{line}  {fn}()')
    check('consume() is the only function that reads a fact\'s value', not offenders)

    # The behavioural half. The AST scan says whether the bypass exists in the source; these
    # say what the consumers whose requirement is at stake actually receive.
    #
    # `!= the number` is too weak an assertion to leave alone: anything at all would satisfy
    # it, including a None that a later reader would render as blank. Q1 says the value slot
    # holds THE REFUSAL, carrying all four fields, so that is what is asserted.
    FIELDS = {'consumer', 'reason', 'required', 'offered'}

    narrated = m.narrator_facts(weak_fact)
    check('narrator_facts does not emit a value narrator may not consume',
          narrated.value != weak_fact.value)
    check('what narrator receives instead is the refusal, carrying all four fields',
          isinstance(narrated.value, dict) and FIELDS <= set(narrated.value))
    check('the refusal names which strength was offered, not merely that one was refused',
          isinstance(narrated.value, dict)
          and narrated.value.get('offered') == m.SINGLE_WEAK_SIGNAL
          and narrated.value.get('required') == m.CORROBORATED)

    exported = m.export_row(contradicted_fact)
    check('export_row does not emit a value export may not consume',
          exported.get('value') != contradicted_fact.value)
    check('export receives the refusal in the value slot, and the row still exists',
          isinstance(exported.get('value'), dict)
          and FIELDS <= set(exported['value'])
          and 'metric' in exported)
    check('a refused export cell is not blank, None or zero',
          exported.get('value') not in (None, 0, 0.0, ''))
    check('contradicted is distinguishable from not_evaluated at the boundary',
          exported['value'].get('offered') == m.CONTRADICTED)

    check('backup_row inherits whatever export_row decides',
          m.backup_row(contradicted_fact) == exported)

    # The other half of the invariant, and the one a refusal-shaped bug would sail past:
    # a fact the consumer MAY have must still arrive as the number.
    strong = m.record_evidence(weak, m.COUNTERPARTY, source=m.MCC, supports=True)
    strong_fact = m.derive('balance', 1250.00, sources=(strong,))
    check('two distinct supporting sources corroborate',
          m.strength_of(strong_fact) == m.CORROBORATED)
    check('a permitted consumer still receives the number',
          m.narrator_facts(strong_fact).value == 1250.00
          and m.export_row(strong_fact)['value'] == 1250.00)

    print('\n3. No application file reads a value or a sensitivity off a derived fact\n')

    readers = _application_readers()
    if readers:
        print('        application reads of guarded attributes in files importing the module:')
        for rel, line, attr in readers:
            print(f'          {rel}:{line}  .{attr}')
    check('no application surface bypasses the boundary (nothing consumes the module yet)',
          not any(attr == 'value' for _, _, attr in readers))
    check('no application surface reads sensitivity toward the findings text',
          not any(attr == 'sensitivity' for _, _, attr in readers))


def describe():
    print('\nThe fixture, as a specification:\n')
    print('  consume(fact, by) is the ONLY path from a derived fact to its number.')
    print('  Every other function that hands a value to a consumer must go through it,')
    print('  including the module\'s own narrator_facts() and export_row(), because')
    print('  `narrator` and `export` are declared consumers with declared requirements.')
    print('\n  A rule a consumer can forget is not an invariant, it is a convention —')
    print('  and gap 6 settled that the way to keep one is to assert the absence of')
    print('  the shortcut, not to trust that nobody takes it.')


def main():
    print('=' * 74)
    print('THE CONSUMER-BOUNDARY FIXTURE')
    print('=' * 74)
    try:
        from core import classification as model
        model.consume
    except (ImportError, AttributeError):
        print('\nNo consumer boundary yet.')
        describe()
        return 1

    run(model)
    print(f'\n{len(PASS)} passed, {len(FAIL)} failed, {len(PENDING)} pending')
    if FAIL:
        print('\nThe failures are the finding, not a broken fixture:')
        print('  EVIDENCE_MATRIX.md finding 9 — consume() is the only way in by')
        print('  convention, not by construction — with two live instances inside')
        print('  the module itself.')
    return 1 if (FAIL or PENDING) else 0


if __name__ == '__main__':
    sys.exit(main())
