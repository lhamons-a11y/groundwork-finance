# What a user who knows almost nothing can still be told

**The same method, pointed at the other end. No interface is designed here.**

> Status: **Case set, 2026-09-10.** Written because of a concrete doubt, Rob's, and it is the right
> kind of doubt to answer with cases rather than with reassurance:
>
> > *"The fear is we may be getting too specific on this subject, where the user is unsure. I'm
> > almost hesitant to offer this. But if we are tracking finances we have to — the trick is making
> > it easier on the user while recording the information with accuracy."*
>
> Every other case set here asks what the **model** must distinguish. This one asks what a
> **person** can actually supply, and what Groundwork may truthfully say with that much. The test
> is not whether the model is expressive; it is whether value degrades **gracefully** as knowledge
> runs out.
>
> **No screens, no field lists, no wording.** Naming what may be said is not the same as drafting
> it, and drafting it here would let the surface settle the semantics — the mistake the whole
> gap-8 review exists to catch.

---

## The ladder

Each rung adds exactly one thing a real person might have, starting from the least informed user
who could plausibly open the module at all.

---

### U0 — a piece of paper and nothing else

**Has:** a bill. A provider name, an amount, a date.

**Establishable:** an **observed** obligation — the distinction
`OBLIGATION_SEMANTICS_QUESTION.md` already drew between a bill the user entered and an obligation
inferred from a payment. Amount, date, and *the name printed on the bill*.

**May say:**

- bill shock — §7.1 trips when paying in full would take liquid savings below the reserve floor,
  **or when it cannot be paid in full at all**. Both work on an amount and a balance. Nothing else
  is needed.
- the amount's effect on cash flow this month.

**May not say:** anything about instrument kind, interest, payoff date, deductible progress, tax
treatment, or who holds the debt.

**And the thing worth noticing first.** The name on the bill is *the entity that sent it* — a fact
the user can read off the page. It is **not** a claim about who legally holds the obligation, and
under the carrier work it does not have to be. Carrier stays `UNKNOWN`, honestly, and the record is
still complete for what it claims.

> **The carrier precision does not tax the user. It is what lets them not know.** Without it,
> "provider" would be the default, and the model would be asserting something nobody established.

---

### U1 — "I'm paying something toward it"

**Adds:** payments, recorded as they happen. No agreed schedule.

**Unlocks — and this is gap 6's split doing real work:** `paid` and `remaining` are **economic
facts** and need no schedule at all. So:

> *"You have paid $850 of $4,000. $2,741 remains."*

**Still may not say:** ahead, behind, on track, overdue. Those are **agreement-relative**, and with
no agreement there is nothing for them to be relative to. Not a limitation to be worked around —
saying them would require inventing a schedule the user never agreed to.

Most of what a person actually wants at this stage is on the permitted side of that line.

---

### U2 — "$175 a month for 24 months"

**Adds:** the schedule. Instrument kind still unknown.

**Unlocks:** `expected_by_now`, `ahead`, `overdue` — the full payment-state vector, with adherence
expressed as one distance under two names.

**And here the exercise found something.** With a schedule and no instrument kind, the system can
compute adherence, and adherence language is the most reassuring language it has:

```text
"You're on track."          ← true about the schedule
                            ← possibly catastrophic about the obligation
```

If the balance is a deferred-interest promotional balance, a user who is perfectly on track by the
schedule may still owe retroactive interest on the **original principal** at a date the schedule
does not contain. *On track* is then true and misleading at once, which is the worst combination a
teaching system can produce.

> **Finding: adherence language must be gated on instrument kind being established, not merely on a
> schedule existing.** The permission ladder already forbids climbing from *calculate* to
> *conclude* without evidence; this names a specific rung where the climb is tempting because the
> arithmetic is impeccable.

A projection is still allowed, provided it is a projection **of the balance** and not a claim about
the obligation ending:

```text
allowed:   at $175/month the balance reaches zero in 18 months
forbidden: in 18 months you will owe nothing
```

---

### U3 — the instrument-kind question, which is the hard one

`PAYMENT_AGREEMENT_DECISIONS.md` §0 makes kind `NOT NULL`, no default, never computed, because a 0%
provider plan and a deferred-interest promo are **byte-identical as a schedule**. This is the one
place in the whole design that puts a question to a person who may genuinely not know the answer.

Three sub-cases, and only one of them is actually hard:

| | | |
|---|---|---|
| **U3a** | has the agreement | readable — deferred interest is disclosed |
| **U3b** | has a statement | readable — a promotional balance and an *if paid in full by* date appear on it |
| **U3c** | has neither | genuinely unknown |

**The shape of the ask matters more than the ask.** In 3a and 3b, Groundwork is not asking the user
to *know*; it is asking them to *look*. That is a user-verifiable external action following from an
established fact — which is exactly the rule gap 14 says should be generalised out of §0.3 and
currently is not.

**For 3c, kind stays unknown and the system fails closed**, which means it may not project a payoff
as though the balance were 0%. What it may still do is name what to look for:

> *"If this is a promotional balance there will be a date on the paperwork that matters. It is
> worth finding."*

That names an action the user can verify and asserts nothing about their instrument.

---

### U4 — "I think I paid $500 in March, but I'm not sure"

**Adds:** an unconfirmed payment.

The states already exist and gap 5 records that only the vocabulary is missing: a confirmed payment
is `cleared + attached + user_confirmed`; this one is attached and **not** user-confirmed.

**Unlocks:** the payment is recorded as what it is. `remaining` is reported with the unconfirmed
amount visible as unconfirmed, rather than silently included or silently dropped.

**This is the rung where the precision most obviously serves the person.** They are permitted to be
unsure, and the number stays honest, because the model has somewhere to put *I think so*. A system
that only accepts confirmed payments would force them to assert something they do not know.

---

### U5 — a letter from a company they do not recognise

**Adds:** a second document — a different name, and an amount that does not match the original.

**Establishable:** a second record, with **both figures kept**. §8.1 already requires the original
creditor and original amount alongside the agency's, *"because the gap between them is sometimes
the whole story."*

**May say:** §8.2a's premise, which a hospital-bill figure does not carry — *this is what you would
pay if you agree that you owe this, and Groundwork has no way to know whether you do.*

**And one honest cost, recorded rather than smoothed over.** Groundwork may not conclude *on its
own* that the debt was transferred: §10 forbids payment state from establishing a change in who
bears an obligation. A human looking at the same two letters would conclude it instantly.

The relief is that the user is not a forbidden source — they are a **knowing** one. If they say the
letter states the account was purchased, that is evidence, and the transition is dated, sourced and
reconstructable from it. **The prohibition binds Groundwork's inference, not the user's testimony.**

---

## Findings

1. **Value degrades gracefully, and the floor is not zero.** U0 — one bill, nothing else — already
   supports bill shock and cash-flow effect, which are the two things most likely to matter on the
   day someone opens a medical bill.
2. **The demanding fields are the ones whose absence is safest to admit.** Adherence, interest
   consequence and payoff all require real knowledge, and all are places where being wrong is
   expensive. The correlation runs the right way.
3. **The precision reduces the demand on the user rather than raising it.** Carrier being explicit
   is what makes *I don't know who holds this* recordable. Not-knowing not being a disposition is
   what stops the model demanding one. Unconfirmed payments have a home. **A model that collapses
   these is the model that makes the user decide before anything can be recorded.**
4. **The usability risk is concentrated in exactly one field.** Instrument kind is both hard to
   supply and gates a class of statements. Everything else on the ladder degrades smoothly. One
   design problem is a much better position than a pervasive one.
5. **New: adherence language must be gated on instrument kind, not on schedule presence.** *On
   track* is arithmetically true and materially false for a deferred-interest balance, and nothing
   currently prevents the sentence.
6. **The hard ask is "look", not "know".** In two of three sub-cases the answer is on paper the
   user already has. That is a different kind of request, and gap 14's ungeneralised rule is what
   governs it.

---

## The answer to the question that prompted this

Not *almost nothing until four fields are filled in*. The floor is a single bill, and it buys the
alarm that matters most on the worst day.

**But the doubt was not misplaced**, and it should not be filed as answered. It correctly located a
real constraint — it just belongs to **one field** rather than to the design. The remaining risk is
not that the model is too precise; it is that the precision could leak into the interface as
questions no one can answer. Nothing here forces that, and nothing here prevents it either:

> **The distinctions the model must hold are not the questions the interface may ask.**

That sentence is a surface decision, unmade, and it should be made deliberately rather than
discovered in a form.

---

## What has not been done

No screens, no fields, no copy, no ordering, no defaults. No claim about which of these rungs the
module should require before it will record anything — that is the same decision, and it is not
made here.
