# The disposition vocabulary — cases before the enum

**§5's invariant, attacked with worked amounts. No vocabulary is proposed here.**

> Status: **Case set, 2026-09-10.** The first of the two items `LIFECYCLE_REVIEW_TRIAGE.md` marks
> ACTIONABLE NOW. The invariant under test:
>
> > **Whenever economic terms change, every amount whose economic treatment changes must have an
> > explicit, reconstructable disposition.** (`OBLIGATION_LIFECYCLE_QUESTION.md` §5)
>
> **Method, per `ARCHITECTURE_PRINCIPLES`:** an enum drafted alongside its meaning settles the
> meaning, because concreteness wins arguments it has not earned. So every amount in every case
> below is dispositioned in prose, and the values that turn out to be **forced** are recorded at
> the end as findings rather than as a list to implement.
>
> **The candidate structure being tested** (Rob's, 2026-09-10, with my split):
>
> ```text
> disposition  =  what happened to the amount
> cause        =  why or how it happened      ← must stay orthogonal
>
> TERMINATING   the amount leaves the system      → takes no destination
> RELOCATING    the amount continues to exist     → must name its destination
> ```
>
> **Fence check applies to every case.** A destination *within one obligation* is
> model-independent — scenario A, which finding 1 showed both anchorings version identically. A
> destination *across a transition* is where M1 and M2 differ. **If a case can only be
> dispositioned by assuming an anchoring, that is the tripwire firing, and the case is recorded
> as not expressible rather than answered.**

---

## Case 1 — the same $650, three times

The figure is `OBLIGATION_SEMANTICS_QUESTION.md`'s, unchanged, because it already forced one
architectural answer and the arithmetic is deliberately identical across all three readings:

```text
gross obligation   $1,200
insurer funded       $250
user funded          $300
unaccounted          $650
```

### 1a — the $650 is a contractual adjustment

The provider charged $1,200; the network-allowed amount was $550. The $650 is the difference the
provider contracted not to bill.

| Amount | Disposition |
|---|---|
| $250 | relocating — settles part of the obligation |
| $300 | relocating — settles part of the obligation |
| $650 | **the user was never liable for it** |

The third row is the finding. This is not an amount that left the obligation; it is an amount
that was never in it. The $1,200 was a **charge**, and the obligation was $550 from the start.
Dispositioning it as *waived* or *written off* would assert the user was once liable and was
released — which is false, and is a different sentence to the user.

### 1b — the $650 is unknown

The repository's original case: it may be an unpaid balance, an unrecorded payment, a provider
write-off, or a claim still being adjudicated.

| Amount | Disposition |
|---|---|
| $650 | **none exists** |

Not *unknown-disposition*. **No disposition.** The amount's economic treatment may not have
changed at all, so it may not even be in the invariant's domain — and asserting membership is
itself a claim. The existing rule already covers this and should not be restated:

> `unreconciled` is an observation about reconciliation, not an explanation of what happened to
> the money.

### 1c — the $650 is an unpaid balance the user still owes

| Amount | Disposition |
|---|---|
| $650 | **none — nothing happened to it** |

**Forces finding 1.** The invariant's domain is *amounts whose economic treatment changed*.
An amount that simply remains owed is outside it. A `NO_CHANGE` or `OUTSTANDING` value would put
every dollar in the system inside the vocabulary and make the invariant unfalsifiable — gap 6's
stub-coherence-checker defect, in a different coat.

**And 1a / 1b / 1c have identical arithmetic and three different dispositions**, which is gap 1's
two-histories-one-balance result arriving at the amount level.

---

## Case 2 — capitalized interest, inside one obligation

$3,000 outstanding, $180 interest accrued and unpaid. Terms change; the interest is capitalized.
New principal: $2,767.

| Amount | Disposition | Destination |
|---|---|---|
| $3,000 | none — its treatment did not change | — |
| $180 | relocating | the new principal |

**The reconstruction check, which is the point of requiring a destination:**

```text
destination claims        $2,767
  undispositioned           3,000  (still there, never moved)
  relocated in                180
                          ───────
                            3,180  ✓
```

A bare `CAPITALIZED` label satisfies §5's letter and fails this check, because it does not say
**into what**. That is §0's double-count, unprevented by a vocabulary that has no destination.

---

## Case 3 — arrears rolled in, and the category error underneath it

$3,000 outstanding on a $175/month plan. The user is **$525 behind**. The plan is restructured to
$250/month.

The intuitive reading is *the arrears are capitalized into the new principal*, giving $3,525.
**That reading appears to be a category error**, and gap 6's closure is what exposes it:

| Dimension | | |
|---|---|---|
| `paid`, `remaining` | economic facts | unchanged by versioning |
| `expected_by_now`, `ahead`, `overdue` | **agreement-relative** | change with the schedule |

The $525 is `overdue` — a **position against a schedule**, not a sum of money separate from the
$3,000. It is already inside the balance. So:

| Amount | Disposition |
|---|---|
| $3,000 | none — it is the balance, and it did not move |
| $525 | **not an amount; it is a schedule-relative position** |

**Forces finding 3.** An agreement-relative quantity cannot receive a disposition, because a
disposition is a claim about money and `overdue` is a claim about a schedule. If the vocabulary
accepts one, it will double-count the same dollars under two names — the exact failure §0 draws,
arriving from a direction §0 did not anticipate.

**What genuinely can be capitalized** is a *late fee* or *interest accrued on the arrears* —
those are new amounts, and case 2 already handles them.

> **Unverified domain assertion, flagged rather than assumed.** Whether real provider or lender
> restructures ever capitalize an arrears figure as a distinct chargeable amount is not
> established here. Treated the way §8 treated the carrier claim: the case stands as written, and
> the assertion is marked for verification before anything is built on it.

---

## Case 4 — three ways to reach a zero balance

$50 of patient responsibility, and three endings with identical balance arithmetic.

### 4a — waived

The provider forgives it as a prompt-pay courtesy. The user **was** liable and **was released**.

| Amount | Disposition |
|---|---|
| $50 | terminating — released from an obligation that existed |

### 4b — written off as bad debt

The user did not pay. The provider removes it from collectible balance **on its own books**. The
account may still be sold, pursued, or reported.

| Amount | Disposition |
|---|---|
| $50 | **whose treatment changed?** |

**Forces finding 4, and it is the sharpest thing in the case set.** A bad-debt write-off is a
change in the *creditor's accounting*, not necessarily in the *user's obligation*. If the
vocabulary treats it as terminating, Groundwork tells the user the amount is gone — which may be
false, and is exactly the class of statement §6 makes the deciding criterion.

So the vocabulary needs an answer to a question nobody has asked yet:

> **Does a disposition describe what happened to the obligation, or what happened on the
> creditor's books?**

Those coincide in 4a and 4c and separate here. Not a modelling question — it determines what may
be said to the user.

### 4c — contractual adjustment

Case 1a again at a smaller figure: never liable, and outside the vocabulary.

**Three identical balance effects, three different truthful statements.** A single
`WRITTEN_OFF` collapses all three, which is why the discriminator is *was the user ever liable*
rather than *what mechanism produced it* — and that discriminator is orthogonal to cause, which
is the property Rob's test asks for.

---

## Case 5 — reversal, and whether it belongs here at all

$500 payment applied to a $3,000 obligation, then reversed for non-sufficient funds.

Gap 6 already governs this at the ledger: a reversal **names the payment it reverses**, may not
exceed it, and is distinct from an adjustment. So the question is not what happens — it is
whether a **second** mechanism should also describe it.

Two framings, and they are not equivalent:

```text
A.  the $500 receives a new disposition: REVERSED
B.  the $500's prior disposition is retracted; it has none again
```

**B is more consistent with what the repository already decided.** Gap 1 settled that a
retraction is *a state, not a removal* — the record and everything attached to it survive — and
the same shape applies one level down. Under A, two mechanisms describe one event and can
disagree; under B, the ledger stays the single authority and the vocabulary gains no member.

**Recorded as a question, not an answer**, because it turns on whether a retracted disposition is
still reconstructable as having existed — which it must be.

---

## Case 6 — partial settlement, which is not a value

$3,000 obligation. The creditor accepts $1,914 in full satisfaction; $800 is forgiven.

| Amount | Disposition | Destination |
|---|---|---|
| $1,914 | relocating — settles | the obligation |
| $800 | terminating — released | — |

The obligation's end state is *partially settled*. **Nothing received that disposition.** It is
derived from the two dispositions above it, which confirms by construction the level-mixing
objection to `Applied` / `Settled` / `Partially Settled`: those describe containers, and the
vocabulary describes contents.

---

## Case 7 — the uncleared payment

$300 sent, not yet cleared.

| Amount | Disposition |
|---|---|
| $300 | none — its treatment has not changed **yet** |

A timing state, not a disposition. Case 1c's rule, arriving from the other side: *pending* belongs
with `pending_claim` in the unknown-states vocabulary, not here.

---

## Case 8 — the tripwire, included so that it fails

$3,000 balance transferred to a collection agency. The agency's figure is **$3,300**.

| Amount | Disposition | Destination |
|---|---|---|
| $3,000 | relocating? | **M1: the same obligation, new carrier. M2: the successor.** |
| $300 | it did not exist before | — |

**Not expressible, and that is the expected result.** The destination of the $3,000 is exactly the
M1/M2 question, so any disposition written here would be advocacy for an anchoring, which
`LIFECYCLE_REVIEW_TRIAGE.md` §0 forbids. The case is kept because it demonstrates the fence
firing on contact rather than by anyone remembering it.

**It also forces finding 7.** The $300 is neither terminating nor relocating — it is **new**. And
the sum check needs it, or it cannot balance:

```text
destination claims        $3,300
  relocated in             3,000
  originated                 300
                          ───────
                             3,300
```

So the reconstruction check requires three categories on the receiving side, of which only two
are dispositions. Origination is **not** a disposition — no amount's treatment changed — but
omitting it makes the check unsatisfiable, which means it must be recorded somewhere the check
can see.

---

## What the cases force

Seven results, each produced by a case rather than chosen. **None proposes an enum member.**

1. **The invariant's domain is narrower than "every amount."** Amounts that simply remain owed
   have no disposition (1c, 7). A `NO_CHANGE` value would make the invariant unfalsifiable.
2. **Not-knowing is not a disposition** (1b). It is a statement about knowledge, and it already
   has a home in the honest-null layer.
3. **Agreement-relative quantities cannot be dispositioned** (3). `overdue` is a position against
   a schedule, not money. Accepting it double-counts the same dollars under two names.
4. **A disposition must say whose treatment changed** (4b) — the obligation's, or the creditor's
   books. Undecided, and it determines what may be said to the user.
5. **Never-liable is not a disposition at all** (1a, 4c). The amount was never in the obligation,
   so nothing happened to it. This may sit outside the vocabulary rather than inside it.
6. **Container states are derived, not values** (6). *Partially settled* is read off the
   dispositions beneath it.
7. **Relocation requires a destination, and the check requires origination too** (2, 8). Without
   the first, §5 is a declaration rather than a test; without the second, the test cannot balance.

**And one question left open on purpose** (5): whether a reversal is a new disposition or the
retraction of a prior one. Gap 1's precedent favours retraction; deciding it here would settle it
by convenience.

---

## What has not been done

No enum. No schema. No field names. No M1/M2 advocacy — case 8 is recorded as inexpressible
rather than resolved. `core/payment_plan.py` still has zero consumers.

The next legitimate step is **Rob's answer to finding 4**, since it is doctrine of the same kind
as the carrier question — *whose economic treatment does a disposition describe?* — and five of
the seven findings above are stable regardless of how it lands.
