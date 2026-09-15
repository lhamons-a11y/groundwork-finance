# Reversal — an event identity, or a claim?

> Status: **Queue item 3, opened by Rob 2026-09-14; C RULED with three corrections applied (§8);
> `Reversal` identity rejected; no build; the payment-to-payment relation forced-but-unruled.** The transaction
> referent is closed at `5af820c` with six hard constraints for this record (`TRANSACTION_REFERENT.md`
> §8). The payment slice left reversal undecided (Pm7: *representable as a dated claim about p;
> whether it is instead its own event identity is not decided; the relation kind, if any, not
> ruled*). This record starts from constraint 6 — what Groundwork must be able to say truthfully,
> and what Person-originating act could establish it — takes the source vocabulary apart before
> testing anything, keeps the two candidates separate through every case, and ends with a ruling
> candidate, ruled in §8.

**Rob's question, verbatim:** *is reversal an event identity or a claim?*

**The six constraints, carried in** (`TRANSACTION_REFERENT.md` §8): source vocabulary decides
nothing · the two candidates stay genuinely separate · a later bank line is only a proposition ·
payment identity remains distinct · no derivation settles the ontology · the key question is
what must be sayable truthfully and what act could establish it.

---

## 1. What is already ruled, and therefore constrains the answer

| Ruling | What it fixes |
|---|---|
| **Payment identity** | a payment is an event identity minted by a Person's assertion that a payment occurred; minting establishes the identity, not the truth of any property; payer and payee are dated relations (the payer may be anyone — Pm9); *not a transaction, not discharge, not a confirmed payment*; **Pm7:** a reversal is representable as a dated claim about p, event-vs-claim not decided, relation kind not ruled |
| **Transaction referent** | a bank line is a proposition from a capture; the movement is unminted; a "REVERSAL" line is a proposition from a later capture whose meaning is this record's (Tx11); the bank's vocabulary has no ontological authority |
| **Obligation slice** | Ob4: a write-off is a *stance* about the obligation at a date, not a mint or unmint; the exposure residue stays unnamed; Ob6: *O3 settled O1* — a relation between obligations that is not correspondence and not supersession — **fenced, "ruled when the economic-transfer invariant's consumer is built"** |
| **Lifecycle §5** (economic-transfer invariant) | *whenever economic terms change, every amount whose treatment changes must have an explicit, reconstructable disposition* |
| **Slice 5** | retraction is about an **utterance** ("what U asserted no longer stands"); it never rewrites, resolves or replaces; correction = retraction + a new claim in one act |
| **Identity ≠ truth** | an identity exists as individuated by the assertion; its asserted properties are claims that can be disputed, absent or wrong |
| **Slice 4 / correspondence** | correspondence is *one referent*; two movements in opposite directions are two events, never one referent |
| **K6 / H2** | a cleared bank payment is no evidence of acknowledgment; `remaining` is a projection; the acknowledgment sequence is claims |
| **Absence is not zero** (`absence_is_not_zero`) | the absence of a line from a later capture is not a proposition |
| **1.x allocation modes** | `ExpenseFundingAllocation.mode ∈ {allocated, corrected, reversed, reinstated, eob_import}` with `occurred_on` and dual time — the shipped "reversal" is a *funding allocation* mode |

Two consequences before the cases. First, **"reversal" in the sources names at least three
different things**, and the ontology cannot be read off the word (constraint 1). Second, **the
only event identity anywhere in these cases is a payment** — if money moved again, a payment
happened; if it did not, nothing new happened and something is being *said* about the original.

---

## 2. Taking the vocabulary apart before testing

What the sources call *reversed · returned · voided · refunded · charged back · reinstated*
covers:

| What happened in the world | Source words | Ontological shape it suggests |
|---|---|---|
| **money moved again, the other way** — a refund, a chargeback settlement, a returned deposit | refund · chargeback · credit · reversal | a **second movement** — an event; if the household individuates it, a **payment identity** with payer and payee the other way round |
| **the original movement did not complete** — an ACH return, a void before settlement, an NSF bounce | returned · voided · declined · reversed | nothing new happened; a **status** of the original payment, asserted by the bank — a dated claim about p |
| **a party changed its books about the payment** — E un-applied a mis-applied payment; a funder withdrew its funding; a "reinstatement" | reversed · reinstated · corrected · adjusted | no movement; a party's **dated stance** about p (or about its own earlier stance) — a claim |
| **a write-off / charge reversal on the obligation** | reversal of charges · adjustment | not about a payment at all — Ob4's stance about the obligation; stays where the obligation slice left it |

So the question *event or claim* has a different answer per row — and that is the result, not a
failure to decide. The two candidates:

**E — reversal is an event identity of its own** (a `reversals` anchor: *something happened that
undoes X*), minted like payments and obligations.

**C — reversal is a claim** — a dated proposition about an existing payment by the party knowing
for it (the bank for movement, E for application, a funder for funding); and, where money
actually moved again, **that movement is a second payment identity**, related to the first by a
claim — never a third kind of thing.

Kept apart through the cases; neither implemented as the other.

---

## 3. The cases

| # | Case | What must be sayable truthfully | Under E | Under C |
|---|---|---|---|---|
| **Rv1** | Rob disputes a $300 card charge to Riverbend Hospital; the network moves $300 back on 6/9. | *you paid Riverbend Hospital $300 on 6/2; $300 came back to you on 6/9; the second undid the first* | a `reversal` identity "undoing p1" — but money **moved**: the reversal *is* a movement, and the ontology already has an identity for that: a payment. E duplicates payment for one case | **p2** — a payment the household mints ("Riverbend Hospital's $300 came back"), `paid_by` Riverbend Hospital / the network, `paid_to` Rob; p1 untouched; and a **relation claim** *p2 undoes p1*, asserted by Rob or by the party that issued it. Two events, one relation, nothing collapsed |
| **Rv2** | Rob returns the wheelchair cushion; the pharmacy refunds $84 to the card. | *you were refunded $84 for the 5/12 purchase* | as Rv1 | p2 minted by Rob; the pharmacy is knowing it issued it (payer); relation claim to p1 if asserted; the bank's "REFUND" line concerns p2 — evidence, not the relation |
| **Rv3** | Rob's $1,412 ACH to Harbor bounces: the bank shows the debit on 3/3 and `RETURNED ITEM` on 3/5. | *you initiated $1,412 on 3/3; the bank says it was returned on 3/5; Harbor has not acknowledged it* | a reversal identity for the return — but the household individuates **one failed payment**, not two events; E would mint an event nobody asserted | **p** (minted by Rob's "I paid Harbor 3/3"); the bank's two lines are two propositions concerning p — *debited 3/3* and *returned 3/5* — dated stances by the bank about p's movement; no acknowledgment from Harbor. Whether the household also individuates the return as a second payment is **the household's**; nothing forces it |
| **Rv4** | A pending charge appears in Monday's capture and is gone from Tuesday's; nothing says "voided". | *the bank showed a pending charge on Monday; it no longer shows it; we do not know why* | nothing to mint — no line says anything happened | **absence is not a claim**: no proposition arises from the line's disappearance; if Rob says "it was voided", that is Rob's dated stance about p (identity ≠ truth: p exists as individuated; "did not occur" is a claim). Consumers must not infer a void from absence |
| **Rv5** | Harbor applied the 3/3 payment to the wrong loan, then "reversed the application" and re-applied it. | *Harbor said applied on 3/5; on 4/1 Harbor said not applied to that loan; on 4/2 applied to the right one* | a reversal identity for a bookkeeping act — no money moved; E mints an event out of E's ledger | three dated **D4-shaped claims** by Harbor about p (and about which obligation) — history; the resolver over them is fenced; nothing chosen |
| **Rv6** | The HSA "reversed" its $250 funding, then "reinstated" it (1.x modes). | *the funder withdrew its funding as of d1 and restored it as of d2, learned on r1 / r2* | two reversal identities for two ledger acts | two dated stances by the funder with effective and learned time — **exactly the shipped `occurred_on` + dual-time shape**, as claims. If money actually moved (a clawback), that is a payment; the 1.x row cannot say which |
| **Rv7** | A partial refund: $120 of the $300. | *$120 of the $300 came back* | one reversal identity with an amount — a second kind of money event | **p2 = $120**, a payment; the relation claim to p1; **netting is a consumer's** (item 7); nothing here computes $180 |
| **Rv8** | The chargeback is itself reversed — the merchant wins the dispute; $300 goes back to Riverbend Hospital. | *…and on 7/15 the $300 went back to Riverbend Hospital* | a reversal of a reversal — recursion in an identity table | **p3**, a payment; relation claim to p2; the same two shapes, no new ontology |
| **Rv9** | A bank line reads `REVERSAL −(−48.20)`; the household says nothing. | *the bank reports a $48.20 credit it calls a reversal* | E would be tempted to mint from the word — **constraint 1 and 3 broken at once** | a proposition from a capture, concerning nothing established; candidates from the reference number; **no identity, no status inferred**; it waits for a party |
| **Rv10** | "Reversal of late charges" on the mortgage statement. | *Harbor removed the late charges as of d* | — | **not about a payment**: Ob4's stance about the obligation's terms; stays with the obligation slice; the word "reversal" bought it nothing |
| **Rv11** | Rob: "I never made that payment" vs Rob: "that payment was reversed." | two different truths | — | the first is `utterance_retraction` of the minting utterance (about the *act*; p remains); the second is a dated stance about p (about the *world*). Distinct, both representable, neither unmints |

**E fails wherever it is tried**: where money moved it duplicates the payment identity (Rv1, Rv2,
Rv7, Rv8); where it did not, it mints an event nobody asserted from a party's bookkeeping or the
bank's vocabulary (Rv3, Rv5, Rv6, Rv9) — constraints 1, 3 and 4 broken. **C survives every case
with the two shapes it already has** — a payment identity, and a dated claim about a payment —
plus **one relation claim** (Rv1, Rv2, Rv7, Rv8) that the record does not yet have as a ruled kind.

---

## 4. What the cases fix

- **Reversal is a claim, never an identity of its own.** There is no `reversals` anchor, no
  `reversed` column, no reversal accessor. The only event identity in play is **a payment**.
- **Where money moved again, that is a second payment** — minted by the household when it
  individuates it, payer and payee the other way (Rv1, Rv2, Rv7, Rv8). The first payment is not
  mutated, collapsed or discharged by it (constraint 4).
- **Where no second payment is individuated, "reversal" is a party's dated claim about the
  existing payment *or about a party's treatment of that payment*** — the bank's that it was
  returned or voided (Rv3, Rv4: about the movement); E's that an application to an obligation
  was reversed (Rv5: about E's *treatment*, with the obligation as a participant); a funder's
  that funding was withdrawn or restored (Rv6: about the funder's treatment) — with `as_of` and
  the utterance's or capture's recorded time. **These are distinct predicates with potentially
  different designated participants and knowing relations; they are not one universal
  `payment_status`.** The shipped `mode` + `occurred_on` + dual time is this shape, as claims.
- **A bank line is evidence for either shape and manufactures neither** (Rv9); **absence of a
  line is not a claim** (Rv4).
- **Which shape applies is decided by a party's assertion, never by a derivation** (constraint
  5): the household individuates a second payment or does not; the bank asserts a status or does
  not. `payment_state()`, `remaining` and discharge consume these claims later; they do not
  create them.
- **Retraction ≠ reversal** (Rv11): about the act vs about the world.
- **The obligation-side "reversal of charges" is Ob4's stance**, not a payment matter (Rv10).

---

## 5. The one thing C needs that the record lacks — the event-relation claim

Rv1, Rv2, Rv7 and Rv8 say truthfully *the second movement undid the first*. That is a
proposition with **two payment participants** asserting an economic relation between two events.
It is:

- **not correspondence** — two events, never one referent (slice 4's meaning is sharp);
- **not about-ness** — neither payment is a document the other concerns;
- **not derived from a line's vocabulary** (constraint 1) — "REFUND" on the bank's line is
  evidence for the claim, never the claim;
- **the same family as Ob6's *O3 settled O1*** — a relation between two identities of one type
  asserting that the later stands in an economic relation to the earlier, which the obligation
  slice fenced until *the economic-transfer invariant's consumer is built*.

Two queue items now press the family (this one and item 6, restructure). **What the cases
establish is exactly this and no more: there must eventually be a claim relating certain
payments when one payment is asserted to economically undo some or all of another.** They do
**not** establish the relation's final ontology or name: *refund*, *chargeback*, *partial refund*
and *chargeback reversal* (Rv8: `p3` undoes `p2` which undid `p1`) are directional and contextual,
and *"the later returns to the earlier's payer some or all of what it paid"* — the first draft's
wording — already over-specifies one economic relation across cases that may not all share it.
*Reverses*, *refunds*, *returns* are source words besides (constraint 1). **Forced-but-unruled:
the naming and the family treatment (with item 6) are deferred, and no registry kind is created
merely because four cases show something will be needed.** Until it is ruled, Rv1's two payments
are representable and their relation is not — honestly, as the obligation slice left Ob6.

---

## 6. The constraints, checked

| Constraint | Held by |
|---|---|
| 1 — source vocabulary decides nothing | §2 takes the words apart; Rv9, Rv10; the relation kind is not named after any of them |
| 2 — candidates kept separate | E and C tested side by side in every row; E is never "implemented as" C |
| 3 — a later line is only a proposition | Rv9; Rv3's two lines are stances about p; Rv4's absence is nothing |
| 4 — payment identity distinct | Rv1/Rv7/Rv8: p1 untouched by p2; no discharge; no collapse |
| 5 — no derivation settles the ontology | §4: which shape applies is a party's assertion; netting, `remaining`, `payment_state()` are item 7 |
| 6 — what must be sayable, and by whose act | the middle column of §3; the minting Person for a second payment; the bank / E / funder for a status |

---

## 7. Ruling candidate — for Rob

> **Reversal is a claim, never an event identity of its own. What the sources call reversed,
> returned, voided, refunded, charged back or reinstated is one of two things the record already
> has. Where money moved again, that movement is a second payment identity — minted by a
> Person's assertion when the household individuates it, its payer and payee the other way —
> and the first payment is neither mutated, collapsed nor discharged by it. Where money did not
> move again — where no second payment is individuated — "reversal" is a party's dated claim
> about the existing payment or about a party's treatment of that payment: the bank's that it
> was returned or voided, the entitled party's that an application to an obligation was
> reversed, a funder's that funding was withdrawn or restored — distinct predicates, each with
> its own time and participants, never one universal status and never a change to the payment. A bank line naming a reversal is a proposition from a later capture: evidence
> for either shape, manufacturing neither; the disappearance of a line from a later capture is
> not a claim at all. Which shape applies is decided by a party's assertion and never by a
> derivation — netting, remaining and discharge consume these claims and do not create them.
> Retraction is about the act and reversal about the world; a reversal of charges on an
> obligation is the obligation slice's stance, not a payment matter. The one thing the cases
> force that the record lacks is a claim relating certain payments when one is asserted to
> economically undo some or all of another — a claim between two identities, not a
> correspondence, not named after any source word, of the same family as *O3 settled O1*; its
> ontology and name are not established by these cases and remain forced-but-unruled, deferred
> to the family treatment.**

**Build, if ruled as doctrine alone: none** — no anchor, no column, no kind; the executable trace
is an absence the fixtures can assert (no `reversals` table, no `reversed` or `status` column on
`payments`, no reversal accessor), and the shipped `mode = reversed` stays where it is as a
funder's dated stance in 1.x terms. **If Rob also rules the event-relation kind for payments
now:** one registry kind with two payment slots (existing), asserted by utterance, reading-
sourced candidates, relational knowing `undetermined`, no schema, a fixture over Rv1–Rv11 with
Rv3/Rv5/Rv6 asserted as stances and Rv9/Rv4 as nothing. **Outside it under either:** netting ·
`payment_state()` · discharge · the resolver over E's stances · the restructure relation's own
cases · any legacy `mode` decomposition.

*The line: money can go back; that is another payment. A party can say a payment failed or was
undone; that is a claim about it. **"Reversal" does not identify a distinct Groundwork event
kind.***

---

## 8. Ruling — Rob, 2026-09-14. C accepted; `Reversal` identity rejected; no build.

*The record has demonstrated why, rather than merely asserted it.* The central distinction —
**money moving back is another payment; "reversal" is the claim about the relationship or
disposition of that payment** — gives a clean ontology without a special `Reversal` object.
The eleven cases do real work: Rv1/2/7/8 defeat a reversal-event identity because Payment already
is the adequate event identity; Rv3/5/6 defeat *every "reversal" names something that happened*;
Rv4 protects absence-is-not-zero; Rv9 stops bank vocabulary manufacturing ontology; Rv10 keeps
obligation semantics out; Rv11 makes act/world crisp. **Rv3's negative result especially:** a
bounced ACH needs no invented "return event" — one household-individuated payment and claims
about what happened to it.

**Three corrections applied before freezing:**
1. **§5/§7 compressed two claims.** *"The later returns to the earlier's payer some or all of what
   it paid"* over-specified one economic relation across cases (refund · chargeback · partial ·
   chargeback reversal · ACH return · application reversal) that do not all share it; Rv8 shows
   the relations are directional and contextual. What is established: *there must eventually be a
   claim relating certain payments when one is asserted to economically undo some or all of
   another* — not its final ontology or name. **Fence preserved; no registry kind created merely
   because four cases show something will be needed.**
2. **The subject of the "dated stance" made explicit:** *where no second payment is individuated,
   "reversal" is a party's dated claim about the existing payment **or about a party's treatment
   of that payment*** — Rv5 is about application to an obligation, Rv6 about funding treatment:
   distinct predicates with potentially different designated participants and knowing relations,
   **not one universal `payment_status`** for later consumers to reach for.
3. **The final line narrowed** from a claim about how banks and people may speak to the
   ontological point: **"Reversal" does not identify a distinct Groundwork event kind.**

**The doctrine as ruled:** reversal is not an identity; everything the cases establish is
representable with existing primitives —

```text
payment identity          when money actually moves and the household individuates that movement
claim                     when a party asserts that an existing payment failed, was returned,
                          was applied / unapplied, or otherwise had some treatment
later payment + relation  when money actually moves back and someone asserts the economic
                          relationship between the two payments   ← relation forced-but-unruled
```

*A strong result because it leaves the ontology less populated than the source vocabulary
suggests, rather than translating every bank noun into an object.*

**Verdict:** C accepted · `Reversal` identity rejected · **no build** · payment-to-payment
economic relation recorded as forced-but-unruled, naming and family treatment (with item 6)
deferred.
