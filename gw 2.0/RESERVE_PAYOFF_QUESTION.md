# Before, alongside or after the last debt balance — the payoff half

**The question, scoped before anything is touched**

> Status: **OPEN and NOT frozen.** Reviewed by Rob 2026-09-07 and revised against that review;
> several claims in the first version were stronger than the evidence supported and are
> corrected below. This document does not answer the question.
>
> **Open Question 6 has two halves and they are separate decisions.** The data half is frozen:
> *a reserve is an allocation of an existing financial state, recorded alongside the applicable
> balance; it does not modify the historical account balance and is not itself a transaction.*
> That half changed no engine code. **This is the other half** — the one design §1.4 flagged as
> landing in `core/consequence.py` and affecting every user.
>
> Reproducible: `tests/payoff_option_measurement.py`.

> ### **The audit has established the consequences of the choices. It has not established the semantics of the choices.**
>
> That is where this question genuinely stands. The measurement work is done; what remains is
> architecture and product semantics. **`core/consequence.py` should not be touched until those
> semantics are explicit enough to write the implementation requirement in testable terms.**

---

## 1. Where the decision lands mechanically

`simulate_payoff`'s monthly loop, in one shape:

```text
extra = budget − minimums
   ├── one_time_cost draws first        money that never reaches the debt
   └── the remainder goes to `order`    avalanche by rate, or snowball by balance
```

**A reserve contribution is structurally identical to `one_time_cost`**: money drawn from
`extra` that never reaches principal, differing only in that it recurs until a target is met.
So the mechanical question is one question — **does the reserve draw from `extra`, and when?**

| | means, in the loop |
|---|---|
| **before** | the reserve takes the whole of `extra` until the target is met |
| **alongside** | `extra` is split between reserve and principal every month |
| **after** | the reserve is funded from capacity that exists once the balances are gone |
| **lever** | the loop is untouched; the reserve becomes a path the user may choose |

**This is a mechanical reading, not a semantic one**, and §2 is the correction that matters most.

## 2. "After" is not yet defined semantically

The mechanical reading above — *not a change to this loop at all* — is coherent as an
implementation, and it is **not** an established product rule. At least two meanings sit under
the word:

| | |
|---|---|
| **A — temporal** | the reserve becomes relevant *after* the final debt is paid |
| **B — priority** | the reserve is an objective that sits *after* debt payoff in an ordering |

They sound equivalent and are not. Take a household with $500 of debt and $200 of monthly extra:

```text
Month 1  debt $300
Month 2  debt $100
Month 3  debt $0
Month 4  reserve $200
```

Under **A** that sequence is the rule. Under **B** it is merely what the rule happens to produce
when the reserve is empty — and the two diverge the moment it is not. **If the household already
holds $400 of reserve, A and B need not agree**, and neither is specified well enough to say
which.

The unanswered questions underneath are the same ones *before* and *alongside* are already known
to have, and the first version of this document wrongly treated *after* as exempt:

- Does the reserve have a target, and who sets it?
- Does accumulation stop when the target is reached?
- What happens when the reserve is subsequently spent?

**So the zero-impact measurement for *after* is not evidence that *after* is simple.** It is
evidence that one particular mechanical reading of it changes no measured calculation. The rule
itself is still undefined.

## 3. What each position costs — measured, with the corpus stated

### The metrics, defined

Both were quoted in the first version without definition, which is how a number becomes
dangerous:

- **One-time-cost gap** — `gap_months` from `solve_one_time_cost`: the number of months a $2,400
  one-time cost pushes out the debt-free date, relative to the payoff simulated on the same
  portfolio with no such cost. It is a delay, not a date.
- **Honest paths offered** — the length of that solver's `paths` list. **It measures
  solution-surface breadth, not solution quality.** Three mediocre paths are not better than one
  excellent one, and the count says nothing about which case obtains.

### The corpus, and what it is not evidence of

The recorded `green_light` contract is 55 states. `tests/payoff_option_measurement.py` now
reports their coverage, because *0 of 55* was doing more work in the first version than it can
bear:

```text
varies    cards per case 1-4 · rates 0.00%-28.40% · surplus −$30.15 to $1,153.93
          drivers 0-4 · both strategies · leases, PSLF, forgiveness, zero balances

ABSENT    a reserve in any state    the corpus predates it entirely — 0 of 55
ABSENT    zero / partial / full reserve, reached or depleted mid-run
ABSENT    one-time costs            0 of 55 — green_light does not take one
ABSENT    tied interest rates       0 of 55 — so ordering TIES are untested
ABSENT    a balance clearing mid-month
```

**The corpus contains no reserve at all.** It was recorded to protect `green_light` against
unintended change, not to discriminate between reserve positions. So *0 of 55* means **none of
these 55 states changed** — not *never changes anything*, and the distance between those two
readings is the point.

### The measurements

| Position | Recorded states changed | Gap | Paths |
|---|---|---|---|
| **after** | 0 of 55 | 4 months | 3 |
| **alongside** | 15 of 55 | 7 months | 4 |
| **before** | 23 of 55 | 9 months | **1** |

Under *before* the solver drops to a single path: §6.4's honest-no would fire far more often,
because a reserve consuming the lever pool removes most of what Pillar 3 has to offer. That is a
real consequence — and by the definition above it is a statement about breadth, not quality.

## 4. Ordering versus baseline — observed, not proven

The key-level diff separates two events a changed/unchanged comparison flattens:

```text
ALTERED    an existing value is different
EXTENDED   a list grew, and everything already there is unchanged
```

| Position | Altered | Extended | of 15 |
|---|---|---|---|
| **after** | 0 | 0 | 15 |
| **lever** | 0 | 1 | 15 |
| **alongside** | 12 | 0 | 15 |
| **before** | 12 | 0 | 15 |

**In the measured portfolio, *before* is the only measured position that changes ordering.** Its
`simulate_payoff` diff includes `first_cleared_name` — a *different card clears first* — where
*alongside*'s does not: the same card clears, later, which is a baseline change.

That is an **observed result on one portfolio, not a mathematical invariant.** The corpus
contains no tied interest rates, which is exactly where an ordering claim would be most fragile.

*before* also uniquely moves `solve_one_time_cost.honest_no` and `solve_monthly_cost.reason`:
the solver stops offering and starts declining.

## 5. The lever — non-invasive, which is not the same as orthogonal

**The lever produces 0 altered and 1 extended**: `solution.solve_one_time_cost.paths`, every
existing path unchanged and one appended.

The precise claim is that **the lever is non-invasive to the existing payoff calculation** — it
does not alter the currently measured payoff outputs. *Orthogonal* was too strong, because the
reserve lever plainly can affect what the user chooses, their future available cash, subsequent
simulations, capacity, emergency spending and future debt creation. None of those are
represented in the payoff function, so the measurement is **silent** about them rather than
supportive.

Its footprint is a **floor, not a ceiling**: measured with the path offered by
`solve_one_time_cost` alone. Every further surface that offers it adds one more **extended**
calculation — and none become **altered**.

### The lever's own unspecified architecture

It fits the product's philosophy — *here are the consequences, here are the levers, you choose*
rather than *I have determined your reserve outranks your debt*. But that fit is a claim about
control, and control is exactly what is unspecified:

- Who decides **when** the lever is offered, and on what evidence?
- What reserve amount does it model — user-entered, or engine-calculated?
- Is the **target** itself a user decision?
- What happens when the user chooses it: is opportunity cost shown against payoff?
- Does choosing it establish a preference, and does that preference later become a constraint?

**And the lever is not automatically neutral because it is user-selected.** If Groundwork offers
A, B and C and not D, the architecture has already judged what counts as a legitimate option.
Under a lever, **the solution engine's eligibility rules become the new policy boundary** — a
smaller surface than changing everyone's payoff, but not no surface.

## 6. "Alongside" is semantically incomplete, not merely expensive

It requires a split of `extra` between reserve and principal, and there is no uninvented source
for it:

```text
reserve_contribution = f(reserve_balance, reserve_target, debt_balance,
                         interest_rate, risk, user_choice, …)
```

50/50 is an arbitrary financial policy. So is 20/80. Deriving the ratio from risk introduces a
**risk model** — precisely one of the things this architecture is built not to pretend it has.
§1.4 already rejected an invented number for the *target*; accepting one for the *rate* is the
same defect relocated.

So *alongside* is not currently an implementable position. It is a position with a missing
function at its centre, and until that function has a principled source, its 12-of-15 cost is
the cost of something not yet fully specified.

## 7. The abstraction this exposed — `extra_above_minimums`

The most consequential engineering finding here, and it belongs to no position.

`extra_above_minimums` shows as unchanged under every perturbation **only because the audit
injects the reserve draw inside `simulate_payoff`** — after the abstraction boundary rather than
at it. A real implementation redefines the pool, so it moves too, and being the pool definition
it moves **first**.

The name encodes today's model:

```text
income → minimums → extra_above_minimums → principal
```

with a docstring calling it *"the money that actually reduces principal."* Once the reserve is a
real allocation that sentence stops being true, because some of that money is deliberately going
elsewhere. That is **a model-level refactor, not a docstring change**:

```text
income → minimums → discretionary_capacity
                        ├── one_time_cost
                        ├── reserve
                        └── debt_acceleration
```

A more internally truthful model — and worth noting that it makes *lever* and *after* easier to
express as well as *before* and *alongside*, so it is not a cost attributable to any one
position.

## 8. Blast radius — wider than parity, and the LTS question

The payoff math exists twice: `core/consequence.py` and `_simulatePayoffStrategy` in
`static/js/app.js:12517`, held to agreement *to the month* by `tests/test_consequence_parity.py`
— 32 checks, passing today.

**Correcting the first version's wording:** *before* and *alongside* are **not merely internal
engine changes — they are product behaviour changes, because they modify the payoff model.** (The
earlier phrasing said they were "not engine changes", which read literally is the opposite of
what this document establishes.) The affected layers:

| Layer | What is at stake |
|---|---|
| Calculation parity | Python ↔ JS, both must move together |
| Behavioural contracts | `green_light` contract, solution engine |
| Product behaviour | what the user actually sees |
| Persistence | what gets recorded |
| Historical semantics | what the historian believes happened |

### The LTS question, which was missing entirely

Changing payoff semantics on a shipped LTS line does not only change code. **It changes
historical interpretation.** An existing user could see their debt-free date move from June 2027
to August 2027 **with no underlying transaction having changed.**

So before `core/consequence.py` is modified there is a prior question:

> **Is this a correction of an existing model, or a new product behaviour?**

If it is a correction, changing LTS is right. If it is new behaviour, it may belong in 2.0
rather than retroactively altering what existing users were told. That question is upstream of
the position itself.

## 9. The requirement, and the limits of the instrument

> **The reserve/payoff treatment must be resolved relative to the final debt balance before
> `core/consequence.py` is modified. Once the position is chosen, audit the existing consequence
> calculations against that rule and identify every calculation whose ordering or baseline
> changes.** *(Rob, 2026-09-07)*

`tests/payoff_option_measurement.py` performs that audit and names the calculations. **It is not
the whole implementation checklist**, and treating it as one would make the measurement tool the
new authority:

> The audit generates the **calculation-impact** checklist. Implementation still requires a
> repository-wide **semantic** audit.

It measures observed calculation impact. It cannot discover dead code, UI assumptions,
persistence and serialization assumptions, undocumented invariants, migrations, import/export
behaviour, event semantics, user-facing copy or error handling.

### Three measurement caveats

Distinct from §11's decision caveats, and printed by the tool itself:

1. `extra_above_minimums` shows unchanged only because of where the perturbation injects — §7.
2. `budget_pressure` and `capacity_unlocked` are unchanged **for this portfolio**, which is not
   the same as unable to change.
3. The lever footprint is a **floor** — more surfaces offering the path add more *extended*.

## 10. How this instrument must not be used

**It enumerates consequences. It does not rank positions.** *(Rob, 2026-09-07.)*

The position with the smallest diff is not thereby the right one. Choose the position whose
**semantics** are correct, then use the audit to establish what implementation consequences
follow. Selecting by diff size inverts that and lets the tooling make a judgement it cannot
see — *after* and *lever* are cheap precisely because the engine models months and the question
is about exposure, which is the thing not on the table.

**Corrected wording, because the first version overreached:** *after* and *lever* **produce no
altered existing calculations in the measured model; lever additionally extends the solution
surface.** They do not "cost nothing" — *after* plausibly needs reserve state handling, UI,
persistence, teaching behaviour, a transition when debt reaches zero, depletion handling and new
tests, none of which this instrument can see.

## 11. What remains unresolved

Three **decision** caveats the measurement cannot settle — distinct from §9's measurement
caveats:

- Whether a household with an empty reserve and one card left is better served by clearing the
  card or filling the reserve. That is **exposure**, and the engine measures months.
- *alongside*'s split ratio — §6.
- Whether this belongs in the engine at all — §5.

And the open questions this review surfaced, none of which the audit can answer:

1. What does *after* mean semantically — temporal or priority? (§2)
2. Who owns the reserve target: user, engine, suggestion, inference, or none?
3. What is the lifecycle of a reserve **after it is spent**?
4. If *alongside*, what determines the allocation ratio?
5. If *lever*, who determines when it is offered and with what parameters?
6. Is changing payoff behaviour in LTS a **correction** or a **new capability**? (§8)
7. Does `extra_above_minimums` become a general discretionary-capacity abstraction? (§7)
8. How much of the 55-state measurement generalises beyond the tested portfolio? (§3)

### Declared out of scope, deliberately

**The reserve's lifecycle as fluctuating state** — what happens when a household spends $1,500
of a $2,000 reserve — is not part of Q6. Q6 is about the *creation* of reserve capacity relative
to the final debt balance. Whether Groundwork rebuilds automatically, offers rebuilding as a
lever, treats depletion as a financial event, or remembers the target across it, is a separate
design question. Named here so its absence is a decision rather than an oversight.

## 12. Not decided here

Deliberately. The measurements are inputs; a document that slid from *here is what each costs*
to *therefore choose this* would be making a risk judgement that is not its to make, and
dressing it as arithmetic.
