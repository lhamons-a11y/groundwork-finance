# Hazard audit — concrete implementation against frozen semantics

> Status: **Audit, opened 2026-09-12. Mode: HAZARD AUDIT — no new case doctrine, no map
> extension, no code changes until the audit identifies the smallest safe repair boundary.**
> Evidence mode closed at `e7103d1` with seven fences lifted. Several places are now known
> where shipped behaviour contradicts semantics that are *frozen*, not proposed. This document
> audits each against the concrete code and its consumers.
>
> **Rob's audit rule, applied per hazard:**
>
> ```text
> frozen rule → actual implementation → actual consumers → specific contradiction
>             → blast radius → minimum safe repair boundary → implementation decision
> ```
>
> **Discipline:** audit first, repair second. **Never repair a mechanism merely because one
> consumer is wrong until its other consumers have been classified.** The evidence work proved
> `resolution()` correct for one half of its domain; that is the pattern to expect elsewhere.
>
> **Order, Rob's — semantically-wrong first, missing-representation last:**
>
> 1. `plan_at()` / overlap
> 2. `record_payment()` / `remaining`
> 3. dated resolvers — `knowing[-1]`, `attested[-1]`
> 4. `resolution()`
> 5. the narrator authorisation boundary
>
> Representation design is **not** this mode. *What must the system mean* is largely settled;
> *how to encode it* is the mode after this one, once it is known which code paths must survive.

---

## H1 — `plan_at()` / overlap

### Frozen rule

From `PERIOD_CLOSE_OVERLAP_TEST.md` §5 and `CONCURRENT_COVERAGE_CASES.md` ruling:

- **B (competing claims, governance unknown):** the overlapped range attributes to *neither*;
  `deductible_met = UNKNOWN`; both claimants named; **never resolved by position.**
- **C (both govern):** attribution is **determinate and multi-valued** — each plan's share, each
  plan the knowing party for its own. Not unresolved. Priority may be unresolved *within* C.
- **CC4:** period overlap does not determine applicability; **applicability is evaluated per
  expense, first.** Where it excludes a plan the state is A.
- **CC5 / A:** sequential periods are one plan per date.
- The year-level `UNKNOWN` conflates B, C and sequential periods — a consumer hazard.
- **Not decided:** `plan_at()`'s return shape — a consumer/build decision.

### Actual implementation — `core/plan_year.py`

```python
def plan_at(when, as_of=None):                      # L191
    for p in plans(as_of):
        if (p.effective_from or '') <= (when or '') <= (p.effective_to or '9999-12-31'):
            return p                                # first match, insertion order
    return None

def plan_of(expense_key, expenses, as_of=None):     # L204 — thin wrapper: plan_at(row['date'])

def accumulators(expenses, plan, as_of=None):       # L234
    applied = sum(e['amount'] for e in expenses if _in_period(plan, e['date']))
    # the FULL amount of every expense whose date falls in the plan's period

def year_summary(expenses, year, as_of=None):       # L258
    periods = [accumulators(rows, p) for p in plans(as_of) if any expense in p's period]
    unattributed = sum(e['amount'] for e in rows if plan_at(e['date'], as_of) is None)
    met = periods[0]['deductible_met'] if len(periods) == 1 and unattributed == 0 else UNKNOWN
```

Three facts about the implementation that the rulings did not have in view:

1. **`accumulators` is multi-valued already, and wrongly so.** It sums the *full* amount of
   every expense in the plan's period, per plan, independently. Under C it therefore attributes
   the whole $600 to A **and** the whole $600 to B — a double count — where the truth is $400
   to A and $150 to B. Under B it does the same. `plan_at` invents a winner; `accumulators`
   invents *two* whole winners. The C ruling's *each plan's share* is not representable:
   an expense carries `amount` and `date` only, and the share is evidence (each plan's EOB)
   the module does not hold.
2. **`year_summary`'s `unattributed` is the only internal caller of `plan_at`**, and it uses it
   for exactly one thing: *is there **no** plan for this date?* — a question `[0]` answers
   correctly, because `None` is position-independent. The overlap resolution inside `plan_at`
   is never consulted by `year_summary`.
3. **The module answers a period question and is read as an applicability question.** An
   expense is `{amount, date}`; nothing in `plan_year` can know that a dental expense is
   outside a medical plan's rule. CC4's hazard is therefore **not in this module** — it is in
   any caller that asks `plan_of` before consulting the applicability axis (which lives with
   `core/allocation.py` / `core/classification.py`). The contract *"the plan in force on a
   date"* is accurate; the hazard is a caller treating *in force* as *governs this expense*.

### Actual consumers

| consumer | what it reads | classification |
|---|---|---|
| `core/plan_year.plan_of` | `plan_at` | internal wrapper; inherits `[0]` |
| `core/plan_year.year_summary` L281 | `plan_at(...) is None` | **safe** — asks only *no plan?*, position-independent |
| `core/allocation.state(e, plan=UNRESOLVED)` | takes `plan` from the caller — *"reports the plan it was told"* | **future consumer**; single `plan` parameter presumes A; not wired |
| `core/database.py` L627 | — | *"NOTHING READS THESE TABLES YET… plan_year… pure and have no callers"* |
| `server.py`, `static/js/app.js` | — | **no reference** |
| `tests/test_plan_year_fixture.py` L89, L112 | `plan_at(...) is a`, `plan_of('x1') is a` | pins **single-object identity** on the happy path (A only) |
| `smoke_sections/s85_plan_year.py` | mutates `year_summary`, `accumulators` | **does not mutate `plan_at`** |
| `tests/substrate_experiment.py` `PlanYearStore._READS` | `plan_at`, `plan_of` in the read set | test double mirroring the API |

**Shipped consumers on the default path: none.** The module is pure and uncalled in production.

### Specific contradiction

| state | frozen | `plan_at` | `accumulators` |
|---|---|---|---|
| A | one plan | correct | correct |
| B | neither; UNKNOWN; never by position | **first inserted wins** | **both plans count the full amount** |
| C | both, each its share | **first inserted only** | **both plans count the full amount** (share unrepresentable) |
| CC4 | applicability first | not this module's to know — **caller** hazard | same |
| CC5 | one plan per date | correct | correct |
| year-level | three truths | — | one `UNKNOWN` for all three |

And one thing the audit adds: **the `[0]` behaviour is unpinned in both directions.** No test
asserts it (the fixture's `is a` cases have one plan per date) and no mutation catches a
change to it (s85 mutates `year_summary` and `accumulators` only). It is a live semantic
hazard that the suite is silent about.

### Blast radius

- **Today, shipped:** zero. No production caller. The hazard is *reachable* only through the
  module's own API and the year-level `UNKNOWN`'s uninformativeness.
- **On first wiring:** every consumer that calls `plan_of` for an expense inherits B's invented
  winner and C's dropped plan; every consumer that calls `accumulators` under B or C inherits a
  double count. The named first consumer, `allocation.state`, takes one `plan` and so can only
  receive A's answer — **it cannot be wired under B or C without the return shape being
  decided.**
- **Downstream doctrine:** period close (ruled: represent-and-report, three provenances)
  requires the record to *hold* the overlap state during REPORT — which is precisely the
  state `plan_at` currently resolves away. **Period-close work is blocked behind this hazard**,
  as Rob said.
- **Tests:** two identity assertions in the fixture and `PlanYearStore._READS` in the
  substrate experiment change if the return shape changes. s85 is unaffected until a
  mutation for `plan_at` is added.

### Minimum safe repair boundary

The boundary is the module's API plus its fixture, and it is smaller than "fix overlap":

1. **`plan_at` must stop resolving B and C by position.** That is the frozen rule and it is
   independent of the return shape: the *minimum* change is that `plan_at` **refuses** when more
   than one plan's period contains the date — fail-closed, single-valued contract preserved
   for A and CC5, and no shape decided. Anything richer (a tuple, a set, an ambiguity object)
   is the fenced consumer decision and is **not** in the minimum boundary.
2. **`year_summary` needs no change for its own use of `plan_at`** — `is None` survives a
   refusal only if the refusal is not `None`; that is the one coupling to check in the repair.
3. **`accumulators` is out of the minimum boundary.** Its double count under B/C is real and
   cannot be repaired without the per-plan share, which is evidence the module cannot hold —
   a representation question, next mode. It should be **guarded, not fixed**: the same
   refusal condition (more than one plan contains an expense's date) marks the result as
   not computable, rather than returning a double-counted `applied`.
4. **The contract must say *period*, not *governs*.** `plan_at`'s docstring — *"the plan in
   force on a date"* — is right; the caller-side hazard (CC4) is prevented by documenting that
   applicability is the caller's question and is asked first. A documentation change, in the
   boundary because it is the only place CC4 can be prevented from inside this module.
5. **Add the missing guard:** a mutation in s85 that restores first-match under overlap must
   be caught. Today it would not be.
6. **Out of the boundary:** the year-level `UNKNOWN` split (three states — a consumer
   decision on what the summary returns), the per-plan share, `plan_at`'s eventual shape,
   `allocation.state`'s signature, period close itself.

### Implementation decision — Rob's

Whether the minimum boundary above is the repair: **refuse on overlap in `plan_at`, guard
`accumulators` on the same condition, document the period/applicability contract, add the
mutation** — or whether the return shape should be decided now so that `plan_at` can *report*
B and C instead of refusing them. The first keeps the shape fenced and unblocks nothing
downstream except correctness; the second unblocks period close and `allocation.state` at
the cost of making the consumer decision now, in build mode rather than this one.

**No code is changed by this section.**

### H1 ruling — Rob, 2026-09-12. Minimum repair boundary accepted. Return shape NOT decided.

> *Do not decide the return shape in Hazard Audit. That is exactly the kind of decision this
> mode is supposed to prevent us from smuggling in under the label of "repair."*

1. **`plan_at()` — refuse on genuine period overlap.** Single-valued contract kept: one
   applicable period → that plan; none → `None`; more than one contains the date →
   **refuse / fail closed.** Refusal is not a new semantic answer; it is the API saying the
   existing single-plan representation cannot faithfully represent what the evidence
   establishes. Preserves A and CC5; prevents B/C being silently collapsed.
2. **`accumulators` — guard, don't repair the accounting.** The full expense against both
   plans is demonstrably wrong under C, and `$400/$150` is not something this module is
   entitled to invent. *If an expense falls within multiple governing periods, `accumulators`
   must not produce a normal per-plan applied amount.* Guard; manufacture no share. The
   allocation question stays separate from the period question.
3. **`year_summary` — don't touch it because `plan_at()` changes.** Its use asks *is there any
   plan?*, not *which governs?*; `[0]` does not contaminate it. Verify the refusal
   sentinel/exception does not break that contract; do not redesign.
4. **CC4 — contract, not logic.** `plan_at()` answers period membership; it cannot evaluate
   medical-vs-dental applicability. *The caller must establish applicability before treating
   a plan as governing an expense.* Made explicit, or a correct primitive becomes a semantic
   trap.
5. **Add the s85 mutation.** Protects frozen behaviour against regression; expands no doctrine.

**Explicitly not decided now:** `plan_at()` return shape · B's representation · C's
representation · per-plan allocation/share · `allocation.state()` signature · year-level
`UNKNOWN` decomposition · period-close representation. Consumer/build-selection decisions.
**The argument "period close is blocked, so decide the shape now" is rejected** — that is how
a blocked consumer starts dictating an API before the other consumers are audited.

**Audit observation kept:** zero shipped blast radius means this is not an emergency repair;
the boundary can be made correct before the first consumer is wired.

> **H1 minimum repair accepted: fail closed on multi-period `plan_at()`; guard `accumulators`
> on the same condition; clarify the period-vs-applicability contract; add the overlap
> mutation. Do not decide representation or consumer shape in Hazard Audit.**

**H1 is not implemented yet.** H2–H5 are audited first, because a later hazard may expose a
shared mechanism whose repair boundary should be coordinated.

---

*H2 – H5 follow, each on the same rule, once H1 is ruled or Rob directs the audit to proceed
in parallel.*
