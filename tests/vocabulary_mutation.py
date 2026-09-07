# -*- coding: utf-8 -*-
"""Question 5, applied to a term: can the repository tell two meanings apart?

`gw 2.0/ARCHITECTURE_PRINCIPLES.md`, the semantic audit:

> Could two reasonable engineers interpret the term differently and both produce passing tests?

Detectable rather than merely worth pondering, and this is the instrument. It is **principle 7
aimed at vocabulary**: a suite that cannot distinguish two meanings is not evidence about which
one the system holds.

**The term under test: `extra_above_minimums`.**

Two operational readings, neither selected here:

    A — DESTINATION    "the money that actually reduces principal"   (its docstring)
    B — AVAILABILITY   "what is uncommitted once every minimum is paid"

They are not the same claim. A is about where the money *goes*; B is about whether it is
*spoken for*. Today they compute the same number only because nothing but a one-time cost draws
on the pool — and the moment a reserve does, they diverge.

**The experiment is deliberately adversarial and fixes nothing.** If the suite cannot tell the
readings apart, the correct output is that finding, not a repaired test: choosing a meaning in
order to make a test pass is precisely the semantic contamination the audit exists to avoid.

`core/consequence.py` is restored byte-for-byte afterwards and the hash is verified. This is an
observability experiment, not a production change.

Run:  python tests/vocabulary_mutation.py
"""
import hashlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / 'core' / 'consequence.py'

ORIGINAL_BODY = """    data = _prepare(cards)
    if not data:
        return None
    total_min = sum(c.minimum for c in data)
    if float(budget) < total_min:
        return None
    return round(float(budget) - total_min, 2)"""

# Reading A, implemented faithfully and numerically identical TODAY. The pool is what reaches
# principal, so anything committed elsewhere is netted out — and nothing is committed elsewhere
# yet, so the arithmetic does not move. An engineer who read the docstring and implemented it
# would write something with this shape.
READING_A_SILENT = """    data = _prepare(cards)
    if not data:
        return None
    total_min = sum(c.minimum for c in data)
    if float(budget) < total_min:
        return None
    committed_elsewhere = 0.0          # nothing draws on the pool yet
    return round(float(budget) - total_min - committed_elsewhere, 2)"""

# The same reading, once something IS committed elsewhere — a reserve, a standing hold. This is
# not a different reading; it is reading A on a day when its distinguishing case exists.
READING_A_ACTIVE = """    data = _prepare(cards)
    if not data:
        return None
    total_min = sum(c.minimum for c in data)
    if float(budget) < total_min:
        return None
    committed_elsewhere = 100.0        # a standing hold that never reaches principal
    return round(float(budget) - total_min - committed_elsewhere, 2)"""


def _hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_suite():
    """Full suite. Returns (passed, failed, failing check names)."""
    proc = subprocess.run([sys.executable, str(ROOT / 'smoke_test.py')],
                          cwd=str(ROOT), capture_output=True, text=True, timeout=1800)
    out = proc.stdout
    m = re.search(r'(\d+) passed, (\d+) failed', out)
    passed, failed = (int(m.group(1)), int(m.group(2))) if m else (0, -1)
    names = re.findall(r'^\s*FAIL\s+(.*)$', out, re.M)
    return passed, failed, names


def _apply(body):
    src = TARGET.read_text(encoding='utf-8')
    assert ORIGINAL_BODY in src, 'extra_above_minimums body not found - has it changed?'
    TARGET.write_text(src.replace(ORIGINAL_BODY, body), encoding='utf-8')


def main():
    baseline_hash = _hash(TARGET)
    print(__doc__.split('Run:')[0].strip().splitlines()[0])
    print('=' * 74)
    print('term under test: extra_above_minimums')
    print('  reading A  destination   "the money that actually reduces principal"')
    print('  reading B  availability  "what is uncommitted once every minimum is paid"')
    print()

    print('Where each reading is already visible in the repository:')
    print('  docstring   asserts A  ("the money that actually reduces principal")')
    print('  signature   enforces B  (cards, budget) - it cannot net out a one-time cost,')
    print('                          and a one-time cost already draws on this pool')
    print('  consumer    requires B  save_first_plan divides the price by the WHOLE pool')
    print('  assertion   pins B      s45: pool == 775 - (200 + 75), an arithmetic identity')
    print()

    results = {}
    try:
        passed, failed, names = _run_suite()
        results['baseline'] = (passed, failed, names)
        print('baseline                       %d passed, %d failed' % (passed, failed))
        if failed:
            print('  baseline is not clean - stop')
            return 1

        for label, body in (('reading A, silent case', READING_A_SILENT),
                            ('reading A, active case', READING_A_ACTIVE)):
            _apply(body)
            try:
                passed, failed, names = _run_suite()
            finally:
                TARGET.write_text(
                    TARGET.read_text(encoding='utf-8').replace(body, ORIGINAL_BODY),
                    encoding='utf-8')
            results[label] = (passed, failed, names)
            print('%-30s %d passed, %d failed' % (label, passed, failed))
            for n in names[:8]:
                print('        FAILED  %s' % n.strip())
    finally:
        restored = _hash(TARGET)
        print()
        print('core/consequence.py restored byte-for-byte: %s'
              % ('yes' if restored == baseline_hash else 'NO - INVESTIGATE'))
        if restored != baseline_hash:
            return 1

    # ── The finding ─────────────────────────────────────────────────────────
    silent = results['reading A, silent case'][1]
    active = results['reading A, active case'][1]
    print()
    if silent == 0:
        print('FINDING: the suite does NOT distinguish the two readings.')
        print('  An implementation meaning "the money that reaches principal" passes every')
        print('  check, because the readings agree numerically while nothing else draws on')
        print('  the pool. The repository does not assert which meaning it holds - it asserts')
        print('  an arithmetic identity that both readings satisfy today.')
    else:
        print('FINDING: the suite distinguishes the readings even when they agree numerically.')

    print()
    if active:
        print('When the distinguishing case exists (something IS committed elsewhere), %d'
              % active)
        print('checks fail. Worth reading their names before calling that detection: a check')
        print('that pins an arithmetic identity fails for ANY change, including a correct one,')
        print('and that is not the same as asserting a meaning.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
