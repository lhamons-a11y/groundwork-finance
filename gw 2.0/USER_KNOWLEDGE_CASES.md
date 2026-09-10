# What a user who knows almost nothing can still be told

**The same method, pointed at the other end. No interface is designed here.**

> Status: **Case set, 2026-09-10. Revised the same day against Rob's review**, which went back to
> this document rather than to the summary of it and found seven concrete defects, two missing
> axes, and one finding that the cases do not support. All are applied below; the retraction is
> marked where it stood.
>
> Written because of a concrete doubt, and it is the right kind of doubt to answer with cases
> rather than reassurance:
>
> > *"The fear is we may be getting too specific on this subject, where the user is unsure. I'm
> > almost hesitant to offer this. But if we are tracking finances we have to — the trick is making
> > it easier on the user while recording the information with accuracy."*
>
> Every other case set here asks what the **model** must distinguish. This one asks what a
> **person** can supply, and what Groundwork may truthfully say with that much.
>
> **No screens, no field lists, no wording.** The surface *principle* is answered in §"The rule the
> interface follows" — that is doctrine, not design, and drafting screens here would let the
> surface settle the semantics.

---

## 0. Two sources, not one — the distinction the first draft collapsed

The original ladder said U0 was *"a bill and nothing else"* and then claimed bill shock. **Bill
shock needs the reserve floor and liquid savings, and neither is on the bill.** The document was
quietly using the rest of Groundwork while claiming to use nothing.

Every rung therefore has two columns:

```text
USER-SUPPLIED        what this person hands over on this occasion
GROUNDWORK-HELD      what the application already legitimately possesses about the household
```

**This strengthens the thesis rather than weakening it.** The claim is not *a bill alone performs a
cash-flow calculation*. It is:

> **A user can supply almost nothing and still be told something true, because Groundwork is
> already reasoning from facts it legitimately holds.**

The corollary matters for a first-run user: a household with no financial history in the app has a
lower floor than one with two years of it, and the module must not pretend otherwise.

---

## U0 — a piece of paper

| | |
|---|---|
| **User-supplied** | provider name, amount, date, as printed |
| **Groundwork-held** | liquid savings, reserve floor, month's cash position |

**Establishable:** an **observed** obligation — `OBLIGATION_SEMANTICS_QUESTION.md`'s distinction
between a bill the user entered and an obligation inferred from a payment.

**May say:** bill shock (§7.1 trips when paying in full would breach the reserve floor **or when it
cannot be paid in full at all**) and the amount's effect on this month's cash — **both from the
held column**, with the bill supplying only the amount.

**May not say:** anything about instrument kind, interest, payoff, deductible progress, tax
treatment, or who holds the debt.

**And the first thing worth noticing.** The name on the bill is *the entity that sent it* — readable
off the page. It is **not** a claim about who legally holds the obligation, and under the carrier
work it does not have to be. Carrier stays `UNKNOWN`, honestly.

> **The carrier precision does not tax the user. It is what lets them not know.** Without it,
> *provider* becomes the default, and the model asserts something nobody established.

---

## U1 — "I'm paying something toward it"

| | |
|---|---|
| **User-supplied** | payments, as they happen |
| **Groundwork-held** | the obligation from U0 |

**The middle step the first draft skipped.** A payment existing is not a payment belonging to *this*
obligation. It may be intended for another bill, split, ambiguous, reversed, pending, or allocated
by the creditor differently from the user's intent. Gap 5 exists for exactly this and the case set
walked past it.

> **A payment contributes to `paid` and `remaining` only when its attachment to the obligation is
> established. An unattached or unconfirmed payment is recorded without changing the confirmed
> economic balance.**

**Unlocks, once attachment holds:** `paid` and `remaining` are **economic facts** in gap 6's split
and need no schedule at all.

**Still may not say:** ahead, behind, on track, overdue. Those are agreement-relative, and there is
no agreement yet for them to be relative to.

---

## U2 — "$175 a month for 24 months"

This rung was the largest defect in the first draft, and it fails in two independent ways.

### U2a — sufficiency: that sentence is not a schedule

`$175 × 24` does not establish a start date, a first due date, a cadence, whether the first period
is partial, whether a residual final payment exists, or whether the schedule has begun. So:

```text
permitted:   a balance projection — at $175/month the balance reaches zero in N months
NOT permitted:  expected_by_now, and therefore not ahead or overdue
```

> **Finding: an amount and a duration permit a projection. `expected_by_now`, `ahead` and `overdue`
> require a schedule with enough temporal semantics to identify what was expected by the evaluation
> date.**

Without that stated, someone eventually writes `expected = 175 * elapsed_months` and a rough
intention silently becomes an authoritative obligation. Note that gap 6 took the schedule as
**caller-supplied scalars** precisely so it would not have to answer this — and the case set then
imported the scalars as though they were a schedule.

### U2b — authority: who said $175?

The user hoping to pay $175 a month and an agreement requiring $175 a month are different facts,
and `overdue` depends entirely on which one it is. *You were required to pay this and did not* is
not something a user's intention can establish about themselves.

> **A schedule supports projection at a lower evidentiary level than it supports adherence.**

Which is `consume()`'s shape exactly: the consumer declares the strength it needs, and *adherence*
declares a higher one than *projection*. The machinery is already built.

### And the sentence that is true and dangerous at once

With a schedule established, adherence is computable, and adherence language is the most reassuring
language the system has:

```text
"You're on track."          ← true about the schedule
                            ← possibly catastrophic about the obligation
```

A user perfectly on track by the schedule may still owe retroactive interest on the **original
principal** at a date the schedule does not contain.

> **Adherence language must be gated on instrument kind being established *and* on the schedule
> being authoritative — not on a schedule merely existing.**

---

## U3 — instrument kind, and what it does not establish

`PAYMENT_AGREEMENT_DECISIONS.md` §0 makes kind `NOT NULL`, no default, never computed, because a 0%
provider plan and a deferred-interest promo are byte-identical as a schedule.

**The first draft treated kind as the hard field. It is the hard *gate*.** Knowing *"this is
CareCredit"* establishes almost none of what the consequence needs:

```text
kind established
      ↓          ← does NOT follow
promotional principal · cliff date · post-promo APR · whether deferred interest
applies to the original principal · whether later purchases carry their own promos
      ↓
consequence calculable
```

> **Instrument kind determines which additional evidence is required. It does not supply that
> evidence.**

Otherwise the architecture drifts toward `kind == deferred_interest → therefore calculate`, which
is the whole failure in one line.

### Three sub-cases, one of them hard

| | | |
|---|---|---|
| **U3a** | has the agreement | readable — deferred interest is disclosed |
| **U3b** | has a statement | readable — a promotional balance and an *if paid in full by* date appear on it |
| **U3c** | has neither | genuinely unknown |

In 3a and 3b Groundwork asks the user to **look**, not to **know** — a user-verifiable external
action following from an established fact, which is gap 14's rule, still ungeneralised.

### The capability cap, because "fails closed" is not specific enough

Unknown kind must suppress the claims that depend on it and **only** those:

| | Unknown instrument kind |
|---|---|
| observed balance | permitted |
| confirmed payments, `paid`, `remaining` | permitted |
| cash-flow effect, bill shock | permitted |
| schedule adherence | permitted **only** if U2a and U2b hold, and gated per above |
| deferred-interest consequence | **refused** |
| definitive payoff claim | **refused** |

> **Unknown instrument kind suppresses only claims whose correctness depends on instrument-specific
> semantics. It does not suppress independent economic facts.**

---

## U4 — "I think I paid $500 in March"

The states exist; gap 5 records that only the vocabulary is missing. A confirmed payment is
`cleared + attached + user_confirmed`; this one is not user-confirmed.

**The first draft said `remaining` is shown "with the unconfirmed amount visible", which is
hand-waving over a real arithmetic choice.** There are two legitimate values:

```text
confirmed remaining                  $4,000 − confirmed
remaining if the $500 is accepted    $4,000 − confirmed − 500
```

**Reporting one number silently decides whether the unconfirmed payment is economically
effective.** That is the hidden collapse this whole review method exists to find.

> **Both values are named, and the unconfirmed amount never alters the confirmed ledger state.**

**This is the rung where precision most obviously serves the person.** They are permitted to be
unsure, and the number stays honest, because the model has somewhere to put *I think so*.

---

## U5 — a letter from a company they do not recognise

**Two errors in the first draft, and the first is the larger.**

### A second document is not a second view of the same obligation

It could be the same debt transferred, a separate debt, an administrative duplicate, a spouse's or
guarantor's account, a disputed account, or a collection attempt against the wrong person.

> **Creating a second record must not create a relationship between the two.** The relationship is
> its own fact, with its own states — *same obligation · different obligation · possibly the same ·
> unresolved* — and **unresolved is the default**, not an error.

Both figures are kept regardless: §8.1 already requires the original creditor and original amount
alongside the agency's, *"because the gap between them is sometimes the whole story."* That
requirement does not depend on the relationship being settled — which is why keeping the figures is
safe and asserting the link is not.

**May say:** §8.2a's premise, which a hospital-bill figure does not carry — *this is what you would
pay if you agree that you owe this, and Groundwork has no way to know whether you do.*

### User testimony is evidence, not an upgrade path

The first draft said the user "is not a forbidden source — they are a knowing one." Directionally
right, and too loose. If the user says the letter states the account was purchased, that
establishes:

```text
the user reports that the letter says X       ← established
the letter says X                             ← NOT established
```

> **User statements establish user-stated facts. They may not silently become document-observed or
> externally-established facts.**

Which keeps faith with gap 15's open case: `user_stated` and `imported_eob` are deliberately equal
in rank, and inventing a promotion here would be inventing the hierarchy that case exists to
refuse. §10's prohibition still binds Groundwork's *inference*; it never bound the user's testimony,
and testimony still does not become observation.

---

## U6 — contradiction *(new; the ladder had no room for it)*

```text
the bill says            $4,000
the user says            $3,500
a statement says         $3,700
payment history implies  $3,176
```

**This is not a rung. It is a different axis.** The user has *more* information than U0 and can
support *fewer* conclusions about the current balance.

**And the machinery already exists** — the case set simply failed to exercise it. `CONTRADICTED`
sits at the **floor** of the strength lattice beside `NOT_EVALUATED`, the weakest-link rule drags
any derived fact down to its weakest material source, and `consume()` refuses a consumer whose
declared requirement is not met. Four conflicting figures do not produce a best guess; they produce
a `contradicted` strength that most consumers cannot take.

> **Information quantity and evidentiary certainty are independent axes. More documents can permit
> fewer conclusions.**

What survives is the honest report: four figures, their sources, their dates, and no fifth number
manufactured to reconcile them.

---

## U7 — staleness *(new)*

A statement from March, read in September.

```text
"the statement showed $4,000 on 12 March"     ← still true, permanently
"you owe $4,000 today"                        ← not established, and was never established
```

Age does not make a document false. It makes it **insufficient for a class of current claims**, and
the two must not be conflated — a stale record that is discarded loses a fact that remains true.

The precedent exists: the reserve work already has a stale target that **reports with its age
rather than freezing or vanishing**. Three things stay separate:

| | |
|---|---|
| historical observation | what a document showed, on its date |
| current state | what is true now |
| current applicability | whether that observation still supports a claim about now |

**And this is gap 2 with a concrete instance.** Gap 2 is still PARTIAL — the `as_of` machinery is
thorough and the invariant is unstated. *A historical conclusion is an immutable representation of
the knowledge available then; a current conclusion may be superseded by later evidence.* U7 is that
invariant meeting a user.

---

## Findings

1. **The floor is not zero, and it is not the bill either.** U0 supports bill shock and cash-flow
   effect from the **held** column, with the bill supplying an amount. A household with no history
   in the app has a lower floor, and the module must not pretend otherwise.
2. **The demanding fields are the ones whose absence is safest to admit.** Adherence, interest
   consequence and payoff all need real knowledge, and all are places where being wrong is
   expensive. The correlation runs the right way.
3. **The precision reduces the demand on the user rather than raising it.** Carrier being explicit
   makes *I don't know who holds this* recordable. Not-knowing not being a disposition stops the
   model demanding one. Unconfirmed payments have a home. Unresolved relationships have a home.
   **A model that collapses these is the model that makes the user decide before anything can be
   recorded.**
4. ~~**The usability risk is concentrated in exactly one field.**~~ **Retracted — the cases do not
   support it.** Instrument kind is the most visible instance, not the only one. The pattern is:

   > **User-facing risk arises wherever the model requires a distinction the user cannot directly
   > establish.**

   Instances already in this document: instrument kind (U3), legal ownership (U0), payment
   attachment (U1), schedule authority (U2b), obligation identity (U5), which figure is true (U6),
   and whether an old figure still applies (U7). Seven, not one — and stating it as a *pattern*
   gives a test for the next one rather than a list to remember.
5. **Adherence language must be gated on instrument kind *and* schedule authority**, not on a
   schedule existing. *On track* is arithmetically true and materially false for a
   deferred-interest balance, and nothing currently prevents the sentence.
6. **The hard ask is "look", not "know"** — in two of three sub-cases the answer is on paper the
   user already holds. Gap 14's ungeneralised rule governs it.
7. **Instrument kind selects which further evidence is required; it does not supply it.** The gate
   is not the answer.
8. **An unconfirmed payment has two remaining values, and both must be named.** One number silently
   decides a semantic question.
9. **A second record creates no relationship.** *Unresolved* is the correct default, not a failure
   state.

---

## The rule the interface follows

*(Rob, 2026-09-10 — doctrine, and it answers the question the first draft left open.)*

> **The interface may ask for evidence. It may not ask for conclusions the user cannot reasonably
> know.**

Three classes:

| | |
|---|---|
| **Ask directly** | what the user can reasonably know: the amount printed on the bill, a date, a payment they made, whether an agreement says $175/month, whether a document names a promotional expiration |
| **Ask them to inspect** | where the evidence exists but the knowledge does not — U3a and U3b |
| **Never ask** | who legally owns the debt; whether two accounts are the same obligation; whether an economic transfer occurred when the evidence does not establish it; what an ambiguous document legally means |

> **`Unknown` must be an acceptable terminal state.** The interface may not turn the model's need
> for precision into the user's obligation to manufacture it.

The earlier formulation — *the distinctions the model must hold are not the questions the interface
may ask* — stands as the description. This is the operative rule.

---

## What this document turned out to be, and what should replace it

A knowledge **ladder** was the wrong shape, and U6 and U7 are where it broke. The ladder assumes:

```text
more information  →  more capability
```

The cases show three quantities moving independently:

```text
more information   ≠   more certainty   ≠   more permissible conclusions
```

A user with one bill establishes one solid fact. A user with five conflicting documents may
establish **less** about the current obligation than that. And a user who does not know who owns the
debt must not be made to guess because a schema wants a `carrier`.

So the successor is a **matrix**, not a longer ladder, over four dimensions the ladder treated as
one:

```text
what evidence exists  ·  who can establish it  ·  how certain it is  ·  what claims it permits
```

**That is the next review** — before any interface work, and it needs neither the carrier doctrine
nor the disposition scope. Recorded here rather than begun, because a matrix drafted in the same
pass as the cases that motivated it would settle its own columns.

---

## What has not been done

No screens, no fields, no copy, no ordering, no defaults. No claim about which rung the module must
require before it will record anything. No matrix.
