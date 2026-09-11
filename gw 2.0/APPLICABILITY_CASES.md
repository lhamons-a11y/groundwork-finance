# Not applicable, not covered, unknown — five states, measured

**Gap 3, attacked with cases against the shipped modules, carrying V6's warning in.**

> Status: **Case set, 2026-09-11. No new state, no enum, no schema. The decision is Rob's.**
>
> `HEALTHCARE_GAP_TRIAGE.md` gap 3 recorded `NOT_APPLICABLE` and `NOT_COVERED` as the two
> genuinely unrepresented states, beside four that exist (`not_evaluated`, `UNRESOLVED`,
> `UNKNOWN`, `pending_claim`) and one the review had not listed (`contradicted`). The
> classification doctrine then raised the cost: *classification = unknown → fail closed* means
> anything genuinely inapplicable is refused permanently, and permanent refusals get routed
> around.
>
> **Rob's warning, carried in:** do not solve this by adding refusal states. First establish
> whether the five describe **different facts** or **different reasons for one absence.**
>
> **And V6's precedent for what to look for:** not a refusal, but an unrepresented state being
> silently converted into a represented one — *absence acquires the meaning of whatever channel
> it is forced through.*

The five, as Rob set them out:

```text
not applicable      the rule genuinely does not apply
not covered         it might apply; the evidence doesn't establish coverage
unknown             applicability itself can't currently be determined
negative            evidence establishes that it does not apply
not yet evaluated   the system hasn't reached the question
```

---

## Where each one lands today, module by module

| | `plan_year` (deductible) | `allocation` (coverage / plan) | `classification` (health) |
|---|---|---|---|
| **not applicable** | *plan has no deductible* → `deductible = 0.0` → **`met = True`** | `state(e, plan=None)` → *no plan covered this date* ✓ | — |
| **not covered** | — | **absent** — a denial has no determination status | — |
| **unknown** | `deductible is None` → `UNKNOWN` — **unreachable**, see C4/C5 | `state(e, plan=UNRESOLVED)` ✓ | — |
| **negative** | *this expense is exempt* → **counted anyway**, C6 | — | `contradicted` — a knowing source said no |
| **not yet evaluated** | (derived on read; no such state) | `'unknown'` string when no determination | `not_evaluated` ✓ |

Three modules, three vocabularies, and the same word — and the same Python value — meaning
different things in each. That table is most of the finding. The cases below are what it costs.

---

## The cases

### C1 / C2 — terms never entered, and a plan that has no deductible

```text
C1   add_plan(name='terms never entered')          deductible=0.0   applied=450   met=True
C2   add_plan(name='HMO, copays only', deductible=0.0)   deductible=0.0   applied=450   met=True
```

**Byte-identical, and both say the deductible is met.** `add_plan` defaults `deductible=0.0` and
coerces with `float()`. A plan added before its terms are known gets a deductible of zero, and
`applied >= 0.0` is true the moment anything is spent.

**This is the module's own central promise, failing.** Its docstring:

> *When the terms have not arrived, the interpretation is `UNKNOWN` — never `False`, never zero.
> Telling someone their deductible is unmet because their plan has not been entered is inventing
> a fact about their coverage.*

The docstring is worried about *unmet*. **The actual result is *met***, which is the inverse and
worse: a user with a $3,000 deductible whose terms are not yet entered is told they have satisfied
it. Under `HEALTHCARE_FAILURE_SEMANTICS.md` this is *plausible and wrong*, not detected failure —
every layer agrees, the number is coherent, and nothing anywhere can catch it.

### C4 / C5 — the `UNKNOWN` branch is unreachable

```text
C4   correct_terms(plan, deductible=None)    TypeError: float() argument must be ... not 'NoneType'
C5   add_plan(deductible=None)               TypeError: float() argument must be ... not 'NoneType'
```

`accumulators()` guards its promise with `UNKNOWN if deductible is None`. **No public path can
produce `deductible is None`.** Both mutators coerce to `float`. So the branch that defends the
docstring's promise cannot be entered by the module's own API.

**And the fixture cannot see it.** `test_plan_year_fixture.py` asserts `UNKNOWN` only through
`year_summary` when **no plan is on file** — a different situation from *a plan is on file and
its terms are not*. The first is handled; the second is the common real state (*I know I'm on the
Lakeview Health PPO; I haven't found the deductible*), and it reads as *met*. This is gap 4's shape:
the fixture exercises a state the production path cannot reach, and the state the production
path does reach is untested.

### C6 — an expense that is exempt from the deductible

A preventive visit, exempt by law, flagged in the expense dict. `accumulators()` sums every
expense in the period:

```text
applied = 700.00      (the $250 preventive visit counted: True)
```

**Expense-level negative is unrepresentable.** There is no way to say *this expense does not count
toward the deductible*. That is a different fact from C2's *this plan has no deductible* — the
rule exists and this case falls outside it, versus the rule does not exist — and both currently
land as *counted*.

### C7 — the insurer says "not a covered service"

The determination statuses that settle an expense's evidentiary question:

```text
provider_adjustment · user_paid_cash · unpaid        (+ pending_claim, which settles nothing)
```

**A denial has to be recorded as one of these, or not at all.** `unpaid` says nobody paid — true,
and it implies someone might. `pending_claim` says nobody yet knows who bears the cost — false;
the insurer has said. Forced through either channel, a denial acquires that channel's meaning:
*still open* or *still undecided*, when it is neither.

### C8 — what `None` means

```text
plan_year        terms['deductible'] = None    →  UNKNOWN            unknown
allocation       state(e, plan=None)           →  no plan covered    not applicable
classification   Evidence.amount = None        →  whole charge       scope
```

**One value, three modules, three meanings** — and two of them are opposite: `None` is *we don't
know* in one file and *there isn't one* in the file next to it. Each module is coherent on its
own. Together they cannot be read.

### C9 — the precedent that gets it right

`allocation.state()`:

> *`plan` defaults to `UNRESOLVED` rather than `None` because the two are different answers:
> nobody has told us which plan covered this date, versus no plan covered it. Only a caller
> holding the household record can tell them apart, which is why this asks rather than derives.*

**Unknown and not-applicable, distinguished, in one place, with the reason stated.** Two things
worth noticing: it distinguishes them by *sentinel versus `None`*, which is the convention C8
shows is not shared; and it puts the distinction on the **caller**, because the module cannot
derive it. That second point is the important one — *no plan covered this date* is a fact about
the household's coverage that the allocation engine has no way to establish from inside.

---

## Are they five facts, or five reasons for one absence?

Rob's question, and the cases answer it: **neither.** They are points on two axes that the
current vocabularies flatten into one.

```text
                          what is true of the RULE              what is true of OUR KNOWLEDGE

not applicable            the rule does not exist here          —              (C2: HMO has no deductible)
negative / not covered    the rule exists; this falls outside   established    (C6, C7)
applies                   the rule exists; this falls inside    established
unknown                   —                                     cannot determine  (C1: terms not entered)
not yet evaluated         —                                     never asked      (allocation's 'unknown' string)
```

**Three are facts about the rule** — it does not exist here, it exists and this is outside it, it
exists and this is inside it. **Two are facts about our knowledge** — we cannot determine which,
or we have not asked. And *not covered* is not a sixth state: it is *negative*, about one specific
rule (coverage), and the reason it looked like a separate state is the value-disagreement finding
— the proposition space is fixed, so negatives about different propositions have nowhere to go.

**The collapse the cases found is between the two axes.** C1 (knowledge: cannot determine) and C2
(rule: does not exist) are one representation. Neither is *met*, and both read as *met*. That is
V6's mechanism exactly: two absences, forced through the only channel — a numeric deductible —
and acquiring that channel's meaning, which happens to be the positive one.

> **The boundary:** applicability is a fact about the rule; determinability is a fact about our
> knowledge; **they are orthogonal, and a state vocabulary that puts them on one axis will
> always have a cell where an absence reads as a fact.**

Which is why adding `NOT_APPLICABLE` and `NOT_COVERED` as two more peers of `UNKNOWN` would not
fix C1/C2. It would give them names while leaving `add_plan` defaulting to `0.0`.

---

## What the fail-closed rule does to this

`classification = unknown → fail closed` is correct **on the knowledge axis** — cannot-determine
should refuse. Applied to the **rule axis** it is wrong in both directions: *the rule does not
exist here* is not a refusal, it is an answer (*your plan has no deductible*), and refusing it
permanently is what gets routed around. And *met* for an unentered deductible is fail-**open**
wearing a number.

So the two axes need different defaults, and today neither has the right one:

```text
knowledge axis     cannot determine  →  refuse, with the reason        (today: reads as met)
rule axis          does not exist    →  answer, and say so             (today: reads as met)
```

---

## Requirements, as sentences they permit — not fields

| Distinction | Permits |
|---|---|
| rule absent ≠ knowledge absent | *your plan has no deductible* versus *we don't have your deductible yet* |
| expense-level negative | *this visit doesn't count toward your deductible* |
| coverage negative | *your insurer has said this is not a covered service* — not *still pending* |
| not-yet-asked ≠ cannot-determine | *we haven't looked at this* versus *we looked and can't tell* |
| one meaning for absence across modules | any sentence at all that spans two of them |

And one that must never be permitted, which today is the default: *you have met your deductible*
for a deductible nobody entered.

---

## What has not been done

No state added. No change to `add_plan`, `correct_terms`, `accumulators`, or the determination
vocabulary. The `0.0` default is left exactly as found — **it is a present defect with a teaching
consequence** and the fix is not obvious, because the right default depends on which axis the
absence is on, and the API currently cannot say. Recorded, not repaired.

**What is Rob's:** whether the two axes become explicit in the vocabularies, and — the one that
decides the shape — whether *applicability* is something a module can derive or, as
`allocation.state()` already concluded for plan attribution, something only the caller holding
the household record can assert.

**Next, per the sequence:** gap 2, the historical-vs-current invariant, which C4's `as_of`
machinery already serves and which U7 gave an instance.
