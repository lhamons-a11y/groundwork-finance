# Value-level disagreement — one boolean about one proposition

**The third recurrence, attacked with cases against the shipped module, and a hypothesis tested
rather than assumed.**

> Status: **Case set, 2026-09-11. No schema, no field, no lattice change. The decision is Rob's.**
>
> Where it surfaced: `USER_KNOWLEDGE_CASES.md` U6 (four figures for one balance),
> `EVIDENCE_MATRIX.md` finding 4 (*holds for classification, absent for values*), and
> `DOCUMENT_IDENTITY_CASES.md` D3 (one document re-parsed `$412` then `$4.12`, no disagreement
> registers). Three independent surfacings, which is the bar for a case set.
>
> **The hypothesis under test, stated before the cases so it can fail:**
>
> > **Evidence carries exactly one boolean about exactly one proposition, and everything that is
> > not that proposition is invisible.**
>
> If the cases show one structural failure behind U6, finding 4, D3, `contradicted`-as-verdict and
> agreement-on-a-negative, a boundary is earned. If they split, that is recorded instead.
>
> **Fence.** Multi-source resolution, the temporal latent, consumer ranking, and the referent
> design are all adjacent to this and none of them is today's question.

---

## What `Evidence` can say

```python
Evidence(axis, source, supports, amount, recorded_at)
```

- `axis` — one of **two** fixed propositions: *this counterparty is health* or *this content is
  health*.
- `supports` — a **boolean** verdict on that proposition.
- `amount` — **scope**, not a claim. Its docstring: *set only when the evidence speaks to part of
  a charge — an EOB line inside a $150 supermarket trip.* It says how much of the transaction the
  evidence bears on. It does not say what any value *is*.

So the proposition space has size two, the verdict is one bit, and there is no slot for *what
this document says the amount is*. That is the whole shape, and the cases below are what it costs.

*(D3 in the document-identity case set passed `$412` and `$4.12` as `amount`. That was a misuse —
it recorded two scopes, not two readings of a value. The finding survives the correction and gets
sharper: there was no correct way to record it.)*

---

## The five distinctions, measured

### V1 — same proposition, opposing verdicts *(the case that works)*

`E:no → U:yes`. State `user_asserted`, rank 3, resolution `superseded, contradictions = 1`.
**The model does this well** — it is what the whole lattice was built for. Everything below is
what falls outside it.

### V5 — is `contradicted` derived from competing evidence?

One EOB says *no*. Nothing else. No competition of any kind.

```text
evidence     [(eob, no)]
state        contradicted, rank 0
resolution   none, contradictions = 0
```

**No.** `contradicted` fires with zero competing evidence. It is not a conclusion about
competition; it is **the negative verdict on the fixed proposition**, produced by
`_state_from` whenever the latest knowing evidence has `supports = False`. And `resolution()`,
correctly, reports no conflict — so the word *contradicted* means one thing in the state and
another in the projection, and the state's meaning is *a knowing source said no*, full stop.

> With one boolean, `False` is the entire negative side. There is no room for *contradicted* to
> mean *evidence competes*, because competition would need a second proposition or a second
> observation, and the state function reads only the latest.

### V3 — agreement on a negative

`U:yes → E:no → U:no`. The user claimed health, the EOB said not, the user conceded. **Two knowing
sources now agree.**

```text
state        contradicted, rank 0
qualifying   $0.00
```

Rob read this as the lattice working — separating *two sources agree* from *the positive
proposition is established* — and that reading holds. But the cases show **two layers**, and the
hypothesis explains only the first:

1. *Not health, and well-supported* cannot be **expressed**, because the only proposition is
   *health* and the only verdict is a bit. That is the hypothesis.
2. Even if it could be expressed, the lattice **ranks support for the fixed proposition**, so
   a well-supported negative would still land at the floor. That is the verdict/strength fusion —
   `is_protected`'s warning from the module docstring — and it is a second layer on the same
   root, not a separate root.

### V4 — the anchor: two readings, both *yes*, amounts differ

```text
V4a   E:yes $412   →  E:yes $4.12       state imported_attested · rank 3 · resolution none
V4b   E:yes $4.12  →  E:yes $412        state imported_attested · rank 3 · resolution none
V4c   E:yes $412   →  E:yes $412        state imported_attested · rank 3 · resolution none
```

**V4a and V4c are indistinguishable** by state, strength and resolution — two readings that
disagree by a factor of a hundred look exactly like two that agree. That was D3's finding.

**What D3 missed is worse.** `qualifying_amount()` — the figure that feeds tax — returns:

```python
attested[-1] if attested else src.amount
```

```text
V4a   qualifying   $4.12
V4b   qualifying   $412.00
```

**The tax-qualifying amount is decided by which reading was recorded last**, with no record that
another reading existed. Value disagreement is not merely invisible; it is **resolved, silently,
by list position**, and the resolution reaches a downstream consumer whose declared strength
(`tax_qualifying: corroborated`) is satisfied, because strength is about the proposition and
the proposition was never in doubt.

This is `[-1]` as a conflict-resolution strategy for the **third time** in the module:
`knowing[-1]` for the state (the equal-rank tie), the last-event resolver (the 42% bug, fixed),
and now `attested[-1]` for the amount. **Wherever the model has no way to represent a
disagreement, position decides it.** That is a pattern, and it is now named.

### V2 — different propositions whose values happen to conflict

*Patient responsibility is $50* and *the billed amount is $400* are different propositions and do
not conflict. *Patient responsibility is $50* and *patient responsibility is $75* are the same
proposition and do.

**Neither can be recorded as evidence at all.** There is no proposition slot; there are two axes.
`amount` is scope. So the record cannot say what a value is *about*, and therefore cannot say
whether two values that differ are a disagreement or two facts.

### U6 — four figures for one balance

```python
derive('balance', 4000.00, ...)    imported_attested
derive('balance', 3500.00, ...)    imported_attested
derive('balance', 3700.00, ...)    imported_attested
derive('balance', 3650.00, ...)    imported_attested
```

Four derived facts. Each rank 3. **No relation between them**, and no way to say whether they are
four observations of one proposition (*the current balance*) or four different propositions
(*billed · believed · stated on a date · computed from payments*) that superficially share a name.
Every consumer receives each one as a permitted, well-supported figure.

---

## The hypothesis, tested

| Surfacing | Explained by *one boolean, one proposition*? |
|---|---|
| D3 / V4 — two readings differ, nothing registers | **yes** — amounts are scope, not claims |
| U6 — four figures, no relation | **yes** — *balance is X* is not an evidence proposition |
| finding 4 — absent for values | **yes** — same |
| V5 — `contradicted` without competition | **yes** — `False` is the whole negative side |
| V3 — agreement on a negative at the floor | **yes for invisibility; a second layer for rank** |
| V2 — different propositions inexpressible | **yes**, directly |

**What correctly does not reduce to it:** age (its own boundary, latent), and referent (its own
case set). The hypothesis explains the five and stops at the two that already have homes, which
is the right shape for a boundary — it should not swallow neighbours.

> **The boundary earned:** the evidence model's proposition space has size two and its verdict is
> one bit. **Every claim that is not *this transaction is health-related on axis X* is
> inexpressible as evidence** — and wherever a disagreement cannot be expressed, the module
> resolves it by position.

And the second layer, kept separate because it survives the first being fixed: **the strength
lattice ranks support for a proposition, not the strength of a verdict.** A well-supported
negative is the weakest thing the lattice can say. Whether that is right for the boundary question
(*is this inside the health zone?*) and wrong for a value question (*what does the document say?*)
is exactly `is_protected`'s fusion, and it is a separate decision from the proposition space.

---

## What the boundary implies, as requirements and not fields

1. **Evidence must be able to say what proposition it bears on and what it claims.** Not a
   fixed pair with a bit. *This document says the patient responsibility is $412* is a claim
   about a proposition with a value, and today it has no representation.
2. **Two claims about one proposition with different values are a disagreement**, and a
   disagreement must be *representable* before it can be *resolved* — by anything other than
   `[-1]`.
3. **Two claims about different propositions are not a disagreement**, whatever their values,
   and the record must be able to say so.
4. **`contradicted` should mean what `resolution()` means by it** — competition exists — or be
   renamed for what it is, a negative verdict. Two meanings under one word is how the next probe
   gets written against the wrong one.
5. **Separately:** the lattice's rank is support-for-P. If a well-supported negative needs to
   rank as well-supported, that is a change to what strength *is*, and it must not be smuggled in
   with the proposition change.

**And the sentence each unlocks**, since that is the test:

| Requirement | Permits |
|---|---|
| propositions with values | *this document says $412; that one says $4.12* |
| representable disagreement | *two readings of your EOB disagree about the amount* |
| different propositions | *your bill and your statement are not disagreeing — they measure different things* |
| `contradicted` disambiguated | *someone said no* versus *sources disagree* |
| verdict strength | *it is well established that this was not medical* |

---

## What has not been done

No field on `Evidence`. No proposition type. No change to `_state_from`, `qualifying_amount`, or
the lattice. `attested[-1]` is left exactly as found — it is a shipped behaviour with a tax
consequence, and the fix is not obvious once the disagreement is representable, because *which
reading is right* is a parse dispute (document identity) and not something position or recency
should answer. Recorded, not repaired.

**What is Rob's:** whether the proposition space opens at all, and if so whether the lattice's
meaning of strength changes with it or stays as support-for-the-boundary-question with a separate
notion for verdict strength. Those are two decisions and the second must not ride on the first.

**Next, per the sequence and without re-ranking:** gap 3 — `NOT_APPLICABLE` / `NOT_COVERED`.
