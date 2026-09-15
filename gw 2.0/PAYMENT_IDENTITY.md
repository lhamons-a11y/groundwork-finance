# The payment as a 2.0 identity — what is it, and what makes something correspond to it?

> Status: **Build mode, opened by Rob 2026-09-14 — record only, no code. Precision pass applied on Rob's
> review (2026-09-14); Reading A stands; ready for ruling — not yet ruled, not yet authorised.** Slice 8 is closed at
> `06bd42d` (`ARTEFACT_ABOUTNESS.md` §10). The payment was found missing at slice 6 (D4: *E
> acknowledges payment p* has no `p`) and confirmed missing at the obligation slice (the
> obligation alone does not unblock D4). This record tests four readings of the payment's
> identity against the servicing, acknowledgment, lifecycle and allocation rulings, answers the
> correspondence half, evaluates the 1.x rows only afterwards, finds what the identity unblocks
> and what it immediately runs into, and ends with a ruling candidate. Nothing here is authorised
> to build.

**Rob's question, verbatim:** *what is a payment as a 2.0 identity?* — with the obligation
slice's negative criterion carried over: not *which existing table represents the payment*, but
*what is the payment as an identity, and what makes something correspond to it*; the 1.x rows
evaluated afterwards, as possible records of it.

**The acceptance test carried in from slice 6:** once an identity is proposed, the domain
propositions that need it — D4 (*E acknowledges payment p, as of d*), and the servicing ruling's
three facts as they touch a payment — must satisfy the domain-proposition contract without
reopening its definition: subject structural, participants not content, identity before instance.

---

## 1. What is already ruled, and therefore constrains the answer

| Ruling | What it fixes |
|---|---|
| **Servicing** (S1–S7, frozen) | **three facts**: entitled party · **payee (a transaction-level fact)** · **discharge (an acknowledgment fact)**; *a payment may evidence discharge; it never establishes it merely by destination*; S6: paying E directly can leave it uncredited; S3: a payment to a never-authorised payee is a real payment and no discharge; S7: the June payment in the recourse return |
| **Acknowledgment** (K1–K8) | **P-ack for a payment = discharge of that payment**, by definition; **K6: a cleared bank payment is no evidence of acknowledgment**; K8: payment acknowledgment and balance statement are two propositions; every acknowledgment is dated; the $25 discrepancy is U6's |
| **H2** (audit, remediated) | `remaining` is an **attached-payment projection, not discharge**; the ruled sequence: *attached → attached/unacknowledged → E acknowledges → discharge → confirmed remaining changes*; `record_payment()` moving `remaining` on attachment alone is too strong |
| **Lifecycle §10** | *payment state may become evidence about a change in who bears the obligation; it may never independently establish that change*; non-payment precipitates, never constitutes |
| **"What confirms a payment"** (`OBLIGATION_SEMANTICS_QUESTION.md`, 2026-09-06) | *a confirmed payment is a cleared transaction, attached to the obligation, confirmed by the user* — and *this defines a payment, not an obligation*. Read now, after the evidence rulings: it defines a **state of** a payment (confirmed), from the household's and the bank's side, **one party short** (`SHIPPED_VS_TARGET.md`: the booleans are the acknowledgment sequence minus E). It does not say what the payment *is* |
| **Slice 6** | D4's payment has no identity; **a `transactions` row is the bank's statement, not the event**; `DebtLedgerEntry` and `transactions` are *records*, neither the event E acknowledges |
| **Obligation slice** | an identity is a continuant minted by the household's individuating assertion; anchor = pointer to the minting utterance and nothing else; the minting act ≠ the minted identity; Ob5: *no payment referent exists, so payment state cannot be consulted — by construction* |
| **Slice 8** | about-ness is a claim presupposing an identity; a statement listing many items needs **proposition-level about-ness (Ab7)** — forced, not built |
| **Party reference** | roles are dated relations over parties; a party is a household `Person` or a minted party |
| **Slice 4 / immutability** | correspondence per type, never merges; references never re-pointed |

Two consequences before any case runs. First, **the same payment can be the object of claims
from different knowing parties** — the bank (money moved), the entitled party (money received /
applied), the household (I paid this, toward that). S6 is *bank says yes, E says no* about one
event; K6 is *bank's statement is not E's*. Several parties' statements about one referent is
exactly the condition that forces an identity (the same argument that forced the obligation).
The **payer** may be a separate party again (Pm9), but payerhood is a relation asserted about
the payment, not a further epistemic source. Second,
**every fact in the rulings is a claim about the payment, made by the party knowing for it** —
cleared (bank) · payee (bank, household) · toward which obligation (household) · acknowledged /
applied (E) · amount as sent vs as applied (bank vs E) · reversed (bank or E). None of them is
the payment.

---

## 2. Four readings of "the payment as an identity"

**Reading A — an event identity, minted by an individuating assertion originating from a
Person.** *"I paid Harbor $1,412 on March 3"*, *"my mother paid Riverbend Hospital $300 for me"*: the payment
is an **event** identity (where the obligation was a continuant); an utterance whose origin is a
Person mints that identity — **the asserting utterance is the minting act, not the payment**,
exactly as the obligation ruling put it. **Minting establishes the identity, not the truth of
any property asserted about the event.** The anchor is structure + a pointer to the minting
utterance. Payer, payee, amount, date, method, purpose, clearance, acknowledgment and reversal
are claims about it.

**Reading B — the payment is the bank transaction.** The `transactions` row (or the feed line)
*is* the payment; a payment exists when the bank shows a debit.

**Reading C — the payment exists when E acknowledges it.** No acknowledgment, no payment; the
P-ack is constitutive.

**Reading D — a 1.x row is the payment** (`DebtLedgerEntry` with `entry_type='payment'`;
`ExpenseFundingAllocation`). Evaluated in §6, afterwards.

B fails on slice 6 directly (*the row is the bank's statement, not the event*) and on the
cases: a cash payment, a payment made by a relative, a money order — no row, real payment
(Pm9, Pm11); a transfer between the household's own accounts — a row, no payment (Pm12); and
S3 — the bank's debit is real *and* the payment reached a party not entitled: the bank's
statement cannot carry *toward what* or *to whom it was meant*. B also makes the bank a minting
authority for the household's acts.

C fails on the servicing and acknowledgment rulings by name: *attached but unacknowledged* is a
**state** of a payment (H2's sequence), which requires the payment to exist before E speaks; S6's
uncredited payment is the case the three-facts ruling was written for. C would make the
uncredited payment not exist — precisely the collapse the rulings forbid.

A is tested.

---

## 3. The cases

| # | Case | Ruled in | Under A |
|---|---|---|---|
| **Pm1** | Rob: "I paid Harbor $1,412 on March 3 for the mortgage." | minting | one utterance mints payment **p**; the same act evidences claims about p: amount ($1,412), occurred (March 3), payee (Harbor), **toward O1** (a claim with object the obligation); "$1,412" and "March 3" are **content / `as_of`**, never identity |
| **Pm2** | The bank feed shows `HARBOR MTG  3/3  −1,412.00`. | slice 6; K6 | mints nothing. What the feed *states* is the bank's claim that a debit occurred — a value read from the bank's artefact **with no payment referent established by the line itself** (structurally, the read claim's payment participant is in the *not established with candidates* state and names nothing); if Rob has asserted p, the line is a candidate *for* p; if not, it is a candidate for a payment Rob has not yet said he made. Rob's "yes, that's my March payment" is the crossing — **and the bank statement lists many lines, so the tie is proposition-level about-ness (Ab7), forced a second time** (§5) |
| **Pm3** | Harbor's statement: "payment received 3/5, $1,412, applied." | K-cases, D4 | **D4 becomes representable:** `acknowledged(E = Harbor, p, as of 3/5)` — subject the party whose stance it is, object the payment, content the position, `as_of` the date; E's statement is an artefact whose reading evidences it (the line-item tie again Ab7; Rob's "Harbor confirmed it" as testimony is representable now). **Discharge is this claim, by definition — and whether it moves anything downstream is not derived** (H2) |
| **Pm4** | S6 — Rob paid Harbor directly; Harbor never credited it. | S6 | p exists (Rob minted it); the bank's claim *debited* stands; E's acknowledgment is **absent** — or present as *not received*. Bank-says-yes / E-says-nothing about one referent, representable, **nothing chosen**; the projection that would move `remaining` is a consumer and is fenced |
| **Pm5** | S3 — Rob paid the never-authorised servicer. | S3 | p exists; payee = S3 (a claim); toward O1 (Rob's intent, a claim); E's acknowledgment never comes. **A real payment, no discharge** — the three facts held apart by structure: entitled party (a role on O1), payee (a claim on p), discharge (E's claim on p) |
| **Pm6** | K8's $25: the bank shows $1,412 sent; Harbor applies $1,387 after a fee. | K8, U6 | two claims about p by two origins — and probably two **kinds** (*amount sent* · *amount applied*); if one kind, a conflict; nothing chosen; the catalogue is not ruled here |
| **Pm7** | Reversal / chargeback (`ExpenseFundingAllocation.mode = reversed`, `occurred_on`). | allocation | representable as **a dated claim about p** by the bank or E (*reversed as of d*); whether a reversal is instead its own event identity (a second payment, negative) related to p is **not decided** — the household or the bank's statement says which, and the relation kind is not ruled |
| **Pm8** | Rob paid $700 and $712 the same day; the bank shows one $1,412 debit. | slice 4 (X1), slice 8 | Two distinct situations, kept apart. **(a) Two real payments, one bank debit** (the bank batched them): two identities; the single line *concerns both* — an about-ness matter (Ab7 at line level), **not** payment ↔ payment correspondence. **(b) Rob later says "those two were actually one payment":** two identities were minted by two assertions; slice 4 already ruled this shape — *separately minted identities later established as one referent* (X1: one EOB uploaded twice) — as `payment_corresponds`: the referent is derived, **the two identities are never merged or re-pointed**, and nothing about them is unminted. Retraction of one minting utterance ("I never made the second one") is a different case — Pm13 — not this one |
| **Pm9** | "My mother paid Riverbend Hospital $300 for me." | party reference | p minted by Rob's assertion; **payer = a role relation** (*paid_by(mother, p)*), not an anchor column; the mother is a non-household party — a *minted* party under Rob's utterance. *(Finding: the minted foundation covers non-household individuals; `party_foundation()`'s label `'institution'` is a misnomer for them — a naming matter, not this slice's.)* |
| **Pm10** | Autopay: twelve mortgage payments a year, no fresh utterance for each. | importer contract (fenced) | each bank line is a **candidate** until asserted; the identity rule is unchanged. That twelve confirmations a year is heavy is a **policy / standing-authorisation** question — the same fence slice 4 left (*how a standing household authorisation lets a pipeline act on its own candidates*) — not a reason to let the bank mint |
| **Pm11** | Rob paid the plumber in cash. | — | p minted; no bank line will ever correspond; amount and payee are Rob's claims at Rob's strength. **A payment with no transaction** — the case that kills B on its own |
| **Pm12** | A $2,000 debit: Rob moving money to his own savings. | — | a bank line, **no payment**: nothing is *paid toward* anything; a debit is a payment only when the household asserts it as one. **A transaction with no payment** — the other half of *payment ≠ transaction* |
| **Pm13** | "That March payment wasn't for the mortgage — it was the HELOC." / "I never made that payment." | Case B, Ob12 | the first: retract the *toward* claim, assert a new one; p unchanged. The second: `utterance_retraction` of the minting utterance; **p remains** (never removal; unminting fenced) |
| **Pm14** | Groundwork's `generate_recurring_payment_drafts` proposes next month's payment. | O9 | a **draft is not a payment** and cannot mint one: a process cannot utter (O9); a draft is a candidate the UI shows and the household may assert — the same shape as Pm10 |

**A survives every case.** The identity is the minting act and nothing else. Every property a
schema would put on the row — payer, payee, amount, date, method, cleared, attached, confirmed,
acknowledged, reversed, toward — is a claim about the payment, by its knowing party, and each
case needs at least one of them to be absent, disputed or wrong while the payment stays what it
is.

**What the cases fix about A's meaning:**

- **Payment ≠ transaction** (Pm11, Pm12): a payment may have no transaction; a transaction may be
  no payment. The bank's line is the bank's statement about a payment — evidence, never the
  payment, never its minter.
- **Payment ≠ discharge** (Pm3, Pm4, Pm5): discharge is E's claim about the payment; the payment
  exists before, without, or despite it.
- **Payment ≠ confirmed payment** (the 2026-09-06 answer): *cleared · attached · user-confirmed*
  are three claims — the bank's, the household's, the household's — about a payment; *confirmed*
  is a state read off claims, not the identity; and the entitled party's claim — acknowledgment —
  was the one that answer did not have.
- **Payer and payee are relations** (Pm9, Pm5), like the obligor — and **payee does not establish
  entitlement, and `toward(p, O)` does not establish discharge** (S3: the payee was never
  entitled; S6: the intended obligation was never credited). Entitlement is a role on the
  obligation; discharge is E's claim on the payment; neither is read off the other.
- **Minted only by an individuating assertion originating from a Person** (Pm2, Pm10, Pm14):
  never by a bank line, a draft, a ledger row, or E's statement — those yield candidates.
  ("The household" throughout this record means that: the Person foundation, not the household
  as payer — Pm9.)
- **Identity is not truth.** The minting assertion may be false ("I paid Harbor" when he did
  not); p still exists, as *the payment event individuated by that assertion*, and its asserted
  properties are claims that can be disputed, absent or later retracted (Pm4, Pm5, Pm6, Pm13).
  This is why p can exist with no transaction, no acknowledgment, a disputed amount, a disputed
  payee, and survive a challenge to the assertion that minted it.

---

## 4. What may refer to, relate to, or concern the payment

These are **different relation families**, not four kinds of correspondence — slice 4's
discipline (*correspondence per type, never merges*) is preserved by keeping them apart:

| Referent / participant | Relation | Status |
|---|---|---|
| another **payment** | `payment_corresponds` — slice 4's shape, a fourth type; separately minted identities later established as one referent; never merged (Pm8 b) | ruled shape |
| a **party** | `paid_by(P, p)` · `paid_to(P, p)` — dated role claims (the payee fact of the servicing ruling, now a claim about p rather than "on the row"); **payee does not establish entitlement** | role claims, catalogue unruled |
| an **obligation** | `toward(p, O)` — the household's claim about what the payment was for (Pm1, Pm5, Pm13); not identity of either; retractable; **does not establish discharge** | a domain claim, catalogue unruled |
| an **artefact** that is the payment's own record — a receipt, a confirmation, a single-transaction artefact | `artefact_concerns(A, p)` — the slice-8 kind, gaining a payment object slot as its ruled growth path says | ruled kind, slot not yet added |
| a **line in a statement** listing many payments (Pm2, Pm3 — the common case) | the tie between *this proposition* and *this payment* — **proposition-level about-ness (Ab7)**, forced a second time and more sharply: bank statements are line-item documents by nature | **unresolved; its own ruling; not designed here** |

Whether the 1.x `transactions` row could be treated as a single-line *artefact* (making the
line tie artefact-level) is the *transaction referent's* question (slice 6 §4), not this one's.

> **Invariant — a candidate is not a correspondence.** Evidence may nominate a candidate
> without making the referent known. A matching amount and date, a merchant string, an account
> number, a draft, a cleared flag: each generates a candidate; none mints, establishes or
> identifies. *Similarity generates a candidate; it does not establish identity.*

---

## 5. What the identity unblocks — and what it immediately runs into

| | With `p` minted | Status |
|---|---|---|
| **D4** — *E acknowledges p as of d* | subject E, **object p**, content, `as_of` | ✓ representable — slice 6's blocked row clears |
| the servicing ruling's **three facts** for a payment | entitled party: a role on O · payee: a claim on p · discharge: E's claim on p | ✓ representable as three separate claims — the ruling's separation is now structural |
| H2's sequence *attached → unacknowledged → acknowledged* | *toward(p, O)* by the household · absence of E's claim · E's claim | ✓ each station representable; **the sequence's consequence (`remaining`) is not derived** |
| the bank's statement of movement, per line | a value claim with p as a not-established participant | ✓ representable; **tying the line to p: Ab7** |
| discharge → `remaining` | — | ✗ a consumer; fenced (H2) |
| reversal as event vs claim | — | not decided |

So the payment identity does real work at once (D4; the three facts; the acknowledgment
stations) — and the first thing a consumer would want after that, *which bank line is this
payment*, is the proposition-level about-ness question. **Ab7 is now forced by two slices, from
two directions** (a combined statement's sections; a bank statement's lines). That is the
strongest signal yet that it is the next reopening — but it is reopened by Rob, on that
evidence, not here.

---

## 6. The 1.x rows, evaluated afterwards as records of it

| Row | What it is, against A | Record of the identity? |
|---|---|---|
| **`transactions`** | the bank's statement, per line — its own unruled referent question (slice 6) | **no** — a statement *about* payments (and about non-payments, Pm12) |
| **`DebtLedgerEntry` (`entry_type = 'payment'`)** | created by the household (`record_payment`) — *this money went toward this debt*, with `linked_checking_transaction_id` | **yes-shaped** — a household assertion fusing *mint p* + *toward(p, O)* + *concerns(bank line, p)* + amount/date claims onto one row; decomposable only where the asserting party is a fact |
| **`ExpenseFundingAllocation`** (`funder · amount · mode · cleared · attached · user_confirmed · occurred_on · duplicate_of`) | funding events against a healthcare expense: **claims about a payment** by three stations (bank: cleared; household: attached, confirmed) with the effective/recorded dual time and a reversal mode | claims, not the identity; `duplicate_of` is **correspondence by pointer** (the slice-4 B shape) — the part not to inherit; `mode = reversed` is Pm7's undecided shape, shipped as a mode |
| **`CheckingTransactionLink`** / `user_confirmed_at` | *this transaction is attached to this obligation, confirmed by the user* | a household assertion tying a bank line to an obligation — **the about-ness crossing, shipped without the identity in the middle** (line → obligation, skipping the payment) |
| **`HistorianEntry` payment drafts** | Groundwork's proposals | candidates (Pm14); never records of a payment |

**Blocker, unchanged:** production has zero `Person` rows; the asserting party of every ledger
entry and allocation is not a fact; *decomposed only where decomposition is a fact* forbids
minting payments from them. No synthetic migration.

---

## 7. Not decided here — fences and findings

- **Proposition-level about-ness (Ab7)** — now forced twice; the tie between a statement line
  and a payment; reopened by Rob on this evidence; not designed.
- **The transaction referent** — what a `transactions` row is in 2.0 (a P-subject of an
  unrepresented reading; or a single-line artefact); slice 6 §4's question, not this one's.
- **Reversal** — a claim about p, or an event of its own related to p; not decided; the relation
  kind, if any, not ruled.
- **The kind catalogue** for payment claims (amount sent vs applied; occurred vs posted vs
  applied dates; payee; method) — domain questions; shapes named, values not.
- **Discharge → `remaining`; the acknowledgment sequence's consequences** — H2's consumer, fenced.
- **Standing authorisation / autopay volume** — the importer-contract fence; policy, not identity.
- **Relational knowing** — the bank for movement, E for acknowledgment, the household for
  intent and identification: one more family waiting; `undetermined` until ruled.
- **`party_foundation()`'s `'institution'` label** for minted non-household individuals (Pm9) —
  a naming finding; not touched here.
- **Unminting** (Pm13) — fenced as before.

---

## 8. Ruling candidate — for Rob

*(Rob's tightening of the first draft, 2026-09-14, adopted verbatim: event vs utterance
explicit; identity vs truth explicit; correspondence vs ordinary relations explicit.)*

> **A payment is an event identity. An individuating assertion originating from a Person mints
> that identity; the asserting utterance is the minting act, not the payment. Minting
> establishes the identity, not the truth of any property asserted about the event. The
> payment anchor is structure plus a pointer to the minting utterance and nothing else: payer,
> payee, amount, date, method, purpose, clearance, attachment, acknowledgment, discharge and
> reversal are not identity properties. They are claims about the payment, made by the party
> knowing for that claim. Payer and payee are dated relations; `toward(p, O)` is a household
> claim about the obligation for which the payment was intended; acknowledgment by the entitled
> party is the discharge claim and does not establish the payment's existence.**
>
> **A payment is not a transaction: a payment may have no transaction, and a transaction may
> be no payment. It is not discharge: it exists before, without, or despite acknowledgment. It
> is not a confirmed payment: cleared, attached and user-confirmed are claims about an existing
> payment, not the identity itself. A bank line, ledger row, draft or entitled-party statement
> can produce a candidate but cannot mint the payment.**
>
> **Relations to a payment remain typed: another payment may correspond to it; a party may
> stand in a payer/payee relation to it; an obligation may be the object of a `toward` claim;
> and an artefact may concern it. A candidate match does not establish correspondence. A
> statement line requires proposition-level about-ness to establish its relation to the
> payment, which remains a separate ruling. No relation merges or re-points payment
> identities.**

**If ruled**, implementation follows the obligation identity's shape; the exact schema,
registry changes, fixtures, migration mechanics and consumer treatment are implementation work
after the ruling, authorised separately. Expected shape, for orientation only: a `payments`
anchor of the obligation's form; additive payment slots; `payment_corresponds`; a payment
object slot on `artefact_concerns`; a fixture over Pm1–Pm14 asserting what is *not* derived; no
data step. **Outside it under any authorisation:** Ab7 · the transaction referent · reversal's
shape · the catalogue · any consumer · `DebtLedgerEntry` / allocation decomposition.

*The line: a bank can say money left; a creditor can say money arrived; only the household's
assertion mints the payment — whoever paid.*

---

## 9. Pre-ruling consistency check — the intended shape against §8's exclusions (2026-09-14)

Rob's six points, checked against the obligation implementation the payment would copy
(`core/database.py` at `e45ccc0`), before anything is ruled or built:

| Exclusion | Where the obligation shape already holds it | Carried into a payment build as |
|---|---|---|
| `minted_by_id` = the minting act's utterance, whose origin is the asserting Person — **not the payer** | `Obligation.minted_by_id → utterances`; the utterance's `origin_party_id` is the asserting party; nothing on the anchor names an obligor — the obligor is `obligated_on`, a role claim (Ob8) | payer = `paid_by`, a role claim; the anchor never names one — asserted by the fixture's descriptor scan (Pm9) |
| the pointer identifies the **act**, not the identity | `id` is the identity; `minted_by_id` is **not unique** — one act mints several (fixture: *"one act may mint two identities — minted_by is a pointer, not a unique key"*) | same check, verbatim |
| `created_at` is **not** the occurred date | substrate `created_at` columns are row-creation defaults only; no substrate code reads any `created_at` as evidence time (the only `created_at` indexes are 1.x historian) — `Artefact` keeps `encountered_at` and `as_of` apart for the same reason | the occurred date is a claim with `as_of` (Pm1); the docstring says `created_at` is when the row was written; the fixture asserts the anchor has exactly `id · minted_by_id · created_at` and that no claim reads `created_at` |
| `subject_/object_payment_id` are **generic participation**, not payer/payee/toward shortcuts | the slots carry no semantics; `RULED_KINDS` constrains only ruled kinds; `obligation_corresponds` is the only ruled kind on the obligation slots | same; `paid_by` / `paid_to` / `toward` remain stand-in kinds, unruled, using the generic slots |
| no accessor infers **confirmed / cleared / discharged / paid** from `p`'s existence | no such function exists in the substrate (checked: none of `is_paid · paid · confirmed · discharged · cleared · remaining · is_confirmed · is_cleared`); the obligation fixture asserts none of `disposition · discharge · remaining · entitlement_of · obligation_state` | the same absence list, extended with the payment's own vocabulary |
| correspondence stays correspondence — **no resolver substitutes identities** | `referent()` is read-only (its only `.add` calls are Python-set adds); `_refuse_repoint` forbids re-pointing every referential slot including the obligation's; the fixtures assert no `merge_* · canonical_id · duplicate_of · referent_id` in the substrate (`ExpenseFundingAllocation.duplicate_of` and `expense_merge_links` are 1.x, noted in §6 as the shape **not** inherited); s90 catches *position resolves a contested referent* | `payment_corresponds` joins `referent()` unchanged; the X1 pattern (Pm8 b) derives a referent and merges nothing |

Nothing in the intended shape encodes anything §8 excludes. Ready for the ruling.
