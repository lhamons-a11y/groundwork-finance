# Architecture principles

**Derived, not designed**

> Status: **Doctrine.** Written 2026-09-06 from the healthcare reviews, but none of it is
> healthcare-specific — every principle here was reached by finding the same defect in an
> unrelated subsystem for the second or third time.
>
> Each carries its worked instance. A principle with a scar is more useful than one without,
> because the scar is what makes it recognisable the next time.

---

## 1. Separate what establishes truth from what interprets it, and from what acts on it

```text
facts / determinations  →  interpretation  →  policy
```

> **Facts establish reality; interpretation and policy consume that reality without becoming
> its owner.**

**Two distinct ways to violate it**, and naming both is what stops a design satisfying the rule
halfway:

- **Interpretation/policy fusion** — policy starts deciding what the facts *mean*.
  `is_protected(category_name)` takes evidence (a name), classifies it (never named, never
  returned), and emits a policy verdict: three layers in one expression, the middle one existing
  only inside an `any()`.
- **Fact/interpretation fusion** — an interpretive result is treated as though it were itself a
  fact. This is the harder one to see, because the result looks like data. A stored
  `is_healthcare = true`, or a persisted `protected` boolean, is a *conclusion* wearing a
  fact's clothes — and once stored it stops carrying the reasoning that produced it.

**Third independent appearance:** `MODEL_PLACEMENT.md`'s *the application owns truth, the model
interprets it*; the lifecycle review's *`health.py` is a policy evaluator over facts*; and
*reconciliation establishes reality, tax rules interpret established reality*. Arrived at
separately each time, which is what makes it the project's central instinct rather than a
preference.

## 2. States must represent reality, not the needs of their current consumer

> Do not collapse distinct states merely because the current consumer produces the same result
> from them. Preserve the distinction at the factual layer; let consumers collapse it only when
> their own rules permit.

Otherwise **the first consumer becomes an accidental schema designer for every future one.**

**Instances:** `unpaid` and `pending_claim` yield the same tax figure today and are not the same
reality — one says nobody paid, the other says nobody yet knows who bears it, and their
transitions differ. `reimbursed = true` is the same error one level down, unable to represent
one expense with three funders.

## 3. Never manufacture a value or classification from an unresolved state

> Never manufacture a value or classification from an unresolved state merely because a consumer
> requires one. **Preserve the uncertainty until evidence establishes otherwise** — and record
> that as a determination, superseded rather than overwritten when better evidence arrives.

Distinct from principle 2, and the distinction is worth keeping sharp:

```text
Known A  ≠  Known B          →  state preservation   (principle 2)
Unknown  ≠  A,  ≠ B          →  epistemic honesty    (this one)
```

Absence is not zero, not the average, and not whatever makes the arithmetic close.

**Instances, both real:** an unreconciled $650 is `$300` if you assume it was never paid and
`$950` if you assume the user paid it — **both are guesses**, and the honest output names the
confirmed amount, the unresolved amount, and *no definitive total at all*. And the dashboard
once reported a **$7,053 shortfall that was actually a surplus**, because blank income months
were read as zeroes.

Those two scars are worth holding together, because they are **superficially opposite outcomes
from one conceptual failure** — one invents a number where none existed, the other invents a
zero. Both manufacture a value the evidence did not supply.

The rule that follows: **completeness is tested before anything is judged.**

## 4. Any interpretation that can change the meaning of a user-visible conclusion must be version-identifiable

Not only the necessity floor. Tax classifications, adherence calculations, consequence
interpretations, solution eligibility — and narrator transformations where they materially alter
interpretation.

**The consumer does not get to decide versioning is unnecessary because today it cannot
distinguish two versions.** That is principle 2 applied to rules instead of states.

**Instance:** `is_protected('Prescriptions')` returned `False` on the morning of 2026-09-06 and
`True` that afternoon. Nothing was stored, so nothing was corrupted — what was lost was the
ability to explain any prior judgement. `NECESSITY_FLOOR_VERSION` is the mitigation, and it is
deliberately thin: it says *this answer came from floor rule version 2*, not *the reasoning was
recorded*.

**Corollary — an absence has provenance too.** A solver returning `candidates = [A, B]` is also
saying *C, D and E did not survive*. If a rule caused that exclusion, the exclusion carries the
rule's version. This matters more as the solution engine gets more sophisticated, because the
interesting answer is increasingly what was ruled out.

## 5. Test coverage cannot substitute for semantic inventory

> A test suite proves the invariants it contains. It cannot prove the important invariants have
> all been identified.

Nearly a truism as stated. **The value is in the questions**, and two of them do most of the
work:

1. What does this function actually **know**? (its real inputs, not its parameter list)
2. What does it silently **infer**?
3. What does it **decide**?
4. **What disappears from the output because of that decision?**
5. **Can yesterday's conclusion still be explained after today's rule changes?**

Question 4 found the two solver payloads that also needed the rule version. Question 5 found the
unversioned floor. Neither is a question a test suite asks of itself.

**The instance, with times attached.** A defect was introduced at 09:00 in a commit carrying
three mutation-proven checks, and found at 16:00 by running these questions against the same
code. The checks were not wrong and were not weak — **they enforced the invariant that had been
chosen, and the specification of what to test was incomplete.** That is a different class of
risk from *implementation ≠ specification*, and no amount of rigour inside the chosen invariant
would ever have surfaced it.

---

## The workflow this implies

Not a process to administer. A sequence worth preserving because it produced the above:

```text
inventory  →  identify the semantic boundary  →  identify historical consequences
           →  formulate the invariant  →  implement  →  mutation-test the invariant
```

Rather than: *write code → write tests → declare green.*

**The division of labour is the point.** The inventory finds the missing invariant; mutation
testing proves the invariant cannot quietly regress. Neither does the other's job, and a suite
that has only ever done the second will report green while the first has never been attempted.

## What "green" cannot tell you

That the invariants are complete. 692 passing checks demonstrated something narrower and still
worth having: existing behaviour survived the change, the new invariant is enforceable, removal
of it is detected, and the payload surfaces were **found rather than assumed to be one**.

That is a good result. It is not evidence that the specification is finished, and treating it as
such is how the 09:00 commit happened.
