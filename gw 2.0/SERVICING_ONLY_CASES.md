# Entitlement ≠ payee — the servicing-only cases

> Status: **Case set, 2026-09-12. Evidence mode. No decision, no field, no change to
> `core/payment_plan.py`.** Rob opened the fence that the §7.7 doctrine test left standing:
>
> > *The cases establish that entitlement matters to disposition and collections; they do not
> > establish whether a valid discharge can be defined independently as payment to an
> > authorised payee. That deserves its own evidence.*
>
> **The unlock condition, as the fence stated it:** a servicing-only arrangement — the provider
> keeps the receivable, a billing company sends the statements. A payee who is not the
> entitled party.
>
> **What the frozen doctrine says, and what it leaves open.** Disposition follows the household
> obligation across changes in *entitlement*; funding, servicing and risk are context. The
> question here is narrower than "is payee a fifth dimension": it is **whether *to whom a payment
> validly discharges* is (a) the same fact as *who is entitled to collect*, (b) a separate fact
> the record must hold, or (c) not a fact Groundwork can hold at all — and, underneath that,
> what *discharge* rests on.**
>
> **Method.** Worked cases with amounts, adversarial by construction, each asking what a later
> observer must hold to say a true sentence about *whether this payment reduced what the
> household owes*. Measured against how payments attach today: `record_payment(plan, amount,
> on)` — **no payee**; a payment is money toward the obligation it is recorded against, and
> U1's rule already says an unattached or unconfirmed payment does not change the confirmed
> balance.
>
> **Fence.** §8's duties (what a collector owes) are not reopened. M1/M2 is not touched. The
> classification doctrine is not touched. Whether *payee* should be a field anywhere is not
> decided here — the cases establish what the fact *is* before anything decides where it lives.

---

## 0. The two dimensions, stated so the cases can pull them apart

```text
entitled party    E   whose obligation it is — who may extinguish, waive, sell, or sue on it
payee             Y   to whom the household sends money expecting it to count
discharge         D   the obligation's balance actually reduced by that money
```

The fence asks whether D can be *defined* as "Y was authorised." The cases test that.

---

## Case S1 — the baseline: provider keeps it, a billing company services it

Provider P is owed $2,100 on a 12 × $175 plan. P uses billing company S. Statements come from
S; the payment coupon says *pay S*. The household pays S $175 on Aug 3.

```text
E = P        Y = S        D = ?
```

- *What the household knows:* it paid S. The transaction row says `S BILLING SVC 175.00`.
- *What Groundwork holds today:* `record_payment(plan, 175, on='2026-08-03')` — attached to P's
  obligation by the household's act of recording it there. `paid` rises to $175, `remaining`
  falls to $1,925.
- *What establishes D:* **nothing yet.** The attachment is the household's claim that this
  money counts toward P's obligation. It became true in the world when S credited P's account
  — an event Groundwork did not see. The evidence that D happened is **P's (or S's) next
  statement showing $1,925.**
- *Sentence:* *"You paid S $175 on Aug 3 toward P's plan."* True. *"P's balance is now
  $1,925."* Not yet established — the statement establishes it.

**Forces finding 1.** Even in the baseline, *payee* and *entitled party* are two different names
on the same obligation, and the payment discharges because S acts for P — a fact the household
believes from the coupon and Groundwork cannot verify. **D is not established by Y. D is
established by E's acknowledgment.**

---

## Case S2 — the servicer changes, and autopay does not

P switches from S1 to S2 effective Sept 1. The household's autopay keeps sending $175 to S1 on
Oct 3. S1 no longer services P's account.

```text
E = P (unchanged)        Y = S1 (no longer authorised)        D = ?
```

Two worlds, indistinguishable to the household on Oct 3:

- S1 forwards the money to P (or S2). D happens, late.
- S1 returns it, or holds it, or has closed. D does not happen. The household is $175 poorer
  and $175 more behind than it believes.

- *What Groundwork holds:* `record_payment(plan, 175, on='2026-10-03')`. `remaining` falls.
  **The record now asserts a discharge that may not have occurred**, on the strength of the
  household's attachment alone.
- *What resolves it:* P's/S2's statement of Oct 20. Shows the payment → D. Does not → the
  attachment was a claim that failed.
- *Sentence the record must be able to say on Oct 21:* *"You paid S1 $175 on Oct 3. P's
  statement of Oct 20 shows no payment received. This payment is attached but not
  acknowledged."*

**Forces finding 2.** Y can change while E does not, and the change can defeat D. **Payee and
entitlement are independent.** And **forces finding 3:** the sentence needs a state the
payment model does not have — *attached, unacknowledged* — which is U1's "unconfirmed payment"
and `USER_KNOWLEDGE_CASES.md` finding 8's *two remaining values*, arriving with the mechanism
that produces it: a payee who stopped being one.

---

## Case S3 — the payee who was never authorised

A letter arrives on P's letterhead style from "S3 Patient Services", with a portal link and a
balance of $1,925. The household pays S3 $175. S3 is not P's servicer.

```text
E = P        Y = S3 (never authorised)        D = no
```

- *What Groundwork holds:* the same `record_payment` as S1. Indistinguishable from S1 at the
  moment of recording.
- *What the household could have known:* nothing from the letter alone. The only party who
  can say S3 is not authorised is P.
- *What resolves it:* P's statement. Still $1,925 (or $2,100 less genuine payments).

**Forces finding 4.** *Authorised payee* is **not a fact Groundwork can establish.** It can
record the household's belief (they paid S3 expecting it to count) and it can record E's
acknowledgment or its absence. It cannot verify authorisation, and a rule that defined D as
"payment to an authorised payee" would require Groundwork to **manufacture authorisation from a
letter** — the S3 letter would qualify, since the record has no way to know it should not.
This is rule 1's shape (*payment state may evidence, never establish, a change in who bears the
obligation*) applied to the payee: **a payment to Y may evidence D; it never establishes D.**

---

## Case S4 / S5 — assignment versus sale: same payee, different entitlement

P places the $1,925 with agency A.

```text
S4  assignment for collection    E = P     Y = A     A acts for P; P still owns the debt
S5  sale                         E = A     Y = A     A bought it; P has no further claim
```

The household experiences S4 and S5 **identically**: letters from A, pay A. §8 treats them
differently — the duties A owes differ, and §8.1's *original creditor and original amount* pair
exists because the gap between P's figure and A's is *sometimes the whole story.*

- *Payment to A, $175, under S4:* D on P's obligation, once P acknowledges (via A's statement,
  acting for P). Under S5: D on A's obligation, once A acknowledges. **Same payment, same payee,
  different obligation discharged.**
- *What distinguishes them in the record:* only an entitlement transition (S5) or its absence
  (S4) — which is the frozen doctrine's mandatory dimension, dated and sourced. The payee is
  the same in both and tells the record nothing.

**Forces finding 5.** Y does not determine E — the same payee can stand on either side of an
entitlement transition. With S2 (E fixed, Y changes) this completes the independence in both
directions.

---

## Case S6 — paying the entitled party directly, past the servicer

S1's world: P is entitled, S services. The household mails $175 to P directly, ignoring the
coupon.

```text
E = P        Y = P        D = ?
```

P may accept and credit it; P may return it with *please pay S*; P may accept it and S's
statement may take a cycle to reflect it. **Even a payment to the entitled party itself does
not establish D** — it is still established by acknowledgment, and the acknowledgment comes
through the servicing channel P chose.

**Forces finding 6, the sharpest one.** If payment *to E* does not establish D, then D cannot
be defined by the payee under *any* choice of payee. **Discharge is not a payee fact at all.**
It is an **acknowledgment fact** — established by a statement from a source the record ranks
as knowing for this obligation — and the payee is context on the payment, not a condition of
discharge.

---

## Case S7 — the recourse return, and money sent to the party that no longer holds it

`CARRIES_DOCTRINE_TEST.md`'s R, one step further: the account returned from vendor V to P in
March; the household learns in September; in June it paid V $175.

```text
E = P (since March)        Y = V (was E; no longer)        D = ?
```

- June's payment went to a party that was entitled three months earlier and is not now. V may
  forward it, or not. Same two worlds as S2.
- *What the record must be able to say after September:* *"Your June payment went to V. Since
  March the obligation has been P's; we learned that in September. P's statement will show
  whether the June payment reached it."*

**Confirms findings 2, 3 and 6** on the doctrine's own case, and adds one requirement to the
sentence: the payee context on a payment has to be readable **against the entitlement history
at the payment's effective date** — *V was E when you paid V* is a different sentence from *V
was not E when you paid V* — which the frozen doctrine's dual-dated transitions already permit.
Nothing new is needed to say it; the payee on the transaction row and the entitlement history
on the obligation are enough.

---

## What the cases force

Seven results, none proposing a field.

1. **Discharge is established by the entitled party's acknowledgment, not by the payee** (S1,
   S6). Payment to *any* party — servicer, agency, or the entitled party itself — is the
   household's expectation of discharge. The statement is the evidence of it.
2. **Payee and entitlement are independent in both directions** (S2: E fixed, Y changes;
   S4/S5: Y fixed, E differs).
3. **The payment model needs an *attached, unacknowledged* state** (S2, S7) — U1's unconfirmed
   payment, now with the mechanism that produces it. Today `record_payment` moves `remaining`
   on attachment alone, which asserts a discharge the record has no evidence for.
4. **"Authorised payee" is not a fact Groundwork can hold** (S3). It can hold *whom the
   household paid* and *whether E acknowledged it*; authorisation is the inference between
   them, and it is E's to make.
5. **A payment to Y may evidence D; it never establishes D** (S3, S7) — rule 1's shape,
   applied to payments.
6. **Payee is the servicing dimension** — *whom to pay* — and the doctrine test's placement of
   servicing as *context* survives: it is context on the obligation and a fact on the
   transaction row (the merchant string already holds it). **Not a fifth dimension of
   entitlement, and not a condition of discharge.**
7. **The sentence about a misdirected payment needs the payee read against the entitlement
   history at the payment's date** (S7) — and the frozen doctrine's dual dating already
   permits it.

---

## The fence, answered by the cases — not ruled

> *Can a valid discharge be defined independently as payment to an authorised payee?*

**No, and not because payee is unimportant — because discharge is not a payee fact.** Under
every choice of payee, including the entitled party, discharge is established by acknowledgment
from the entitled party through the channel it uses. *Authorised payee* is exactly the fact the
household cannot verify and Groundwork cannot establish; defining discharge on it would make
the S3 letter sufficient.

**So *entitlement ≠ payee* holds, and it holds more cleanly than the fence expected:** they are
independent dimensions (finding 2), only one of them is mandatory to disposition (entitlement —
the frozen doctrine), and **neither of them defines discharge** (finding 1). The distinction the
fence protected turns out to be three facts, not two:

```text
entitled party      mandatory   frozen doctrine — whose obligation it is
payee               context     servicing — whom the household sends money to; on the row already
discharge           evidence    acknowledged by the entitled party, or attached-unacknowledged
```

---

## What the cases do not establish

1. **Whether payee should be a field on the obligation.** The cases show it is *context* and
   that the transaction row already carries it. Whether servicing history deserves its own
   record (*S1 until Sept, then S2*) is a question about the servicing dimension, not about
   discharge, and it is not opened here.
2. **What "acknowledgment" requires.** A statement from E; a statement from E's servicer; a
   portal balance; the household's report of a statement (*the user reports the letter says X*
   is not *the letter says X* — `USER_KNOWLEDGE_CASES.md`). That is source ranking for balance
   evidence, and it belongs to the evidence layer, where `IMPORTED_EOB`/`USER_STATED` already
   rank knowing sources for health. Not designed here.
3. **How `record_payment` should change.** Finding 3 says the state *attached, unacknowledged*
   must exist and must not move the confirmed balance. Whether that is a flag on `Entry`, a
   second ledger, or a projection over statements is design.
4. **Anything about §8's duties.** S4/S5 differ in what A owes; that is §8's, untouched.

---

## Decision remaining — Rob's

Whether to lift the fence on the cases' terms: *entitlement ≠ payee* confirmed as independent
dimensions; payee placed as the servicing dimension (context); and **discharge placed as an
acknowledgment fact rather than a payee fact** — which is the part the fence did not
anticipate and is the part that needs his word, because it reaches the payment model's
`remaining`.
