# The payment as a 2.0 identity — what is it, and what makes something correspond to it?

> Status: **Build mode, opened by Rob 2026-09-14 — record only, no code.** Slice 8 is closed at
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

Two consequences before any case runs. First, **the payment is what three different parties
make statements about**: the bank (money moved), the entitled party (money received / applied),
the household (I paid this, toward that). S6 is *bank says yes, E says no* about one event;
K6 is *bank's statement is not E's*. Three statements about one referent is exactly the
condition that forces an identity (the same argument that forced the obligation). Second,
**every fact in the rulings is a claim about the payment, made by the party knowing for it** —
cleared (bank) · payee (bank, household) · toward which obligation (household) · acknowledged /
applied (E) · amount as sent vs as applied (bank vs E) · reversed (bank or E). None of them is
the payment.

---

## 2. Four readings of "the payment as an identity"

**Reading A — an event minted by the household's individuating assertion.** *"I paid Harbor
$1,412 on March 3"*, *"my mother paid Riverbend Hospital $300 for me"*: an utterance, origin a Person, mints
the payment — an **event** identity where the obligation was a continuant, but minted the same
way. The anchor is structure + a pointer to the minting utterance. Payer, payee, amount, date,
method, purpose, clearance, acknowledgment and reversal are claims about it.

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
| **Pm2** | The bank feed shows `HARBOR MTG  3/3  −1,412.00`. | slice 6; K6 | mints nothing. What the feed *states* is the bank's claim (a debit occurred) — a value read from the bank's artefact, with the payment as a participant **not established, with candidates**; if Rob has asserted p, the line is a candidate *for* p; if not, it is a candidate for a payment Rob has not yet said he made. Rob's "yes, that's my March payment" is the crossing — **and the bank statement lists many lines, so the tie is proposition-level about-ness (Ab7), forced a second time** (§5) |
| **Pm3** | Harbor's statement: "payment received 3/5, $1,412, applied." | K-cases, D4 | **D4 becomes representable:** `acknowledged(E = Harbor, p, as of 3/5)` — subject the party whose stance it is, object the payment, content the position, `as_of` the date; E's statement is an artefact whose reading evidences it (the line-item tie again Ab7; Rob's "Harbor confirmed it" as testimony is representable now). **Discharge is this claim, by definition — and whether it moves anything downstream is not derived** (H2) |
| **Pm4** | S6 — Rob paid Harbor directly; Harbor never credited it. | S6 | p exists (Rob minted it); the bank's claim *debited* stands; E's acknowledgment is **absent** — or present as *not received*. Bank-says-yes / E-says-nothing about one referent, representable, **nothing chosen**; the projection that would move `remaining` is a consumer and is fenced |
| **Pm5** | S3 — Rob paid the never-authorised servicer. | S3 | p exists; payee = S3 (a claim); toward O1 (Rob's intent, a claim); E's acknowledgment never comes. **A real payment, no discharge** — the three facts held apart by structure: entitled party (a role on O1), payee (a claim on p), discharge (E's claim on p) |
| **Pm6** | K8's $25: the bank shows $1,412 sent; Harbor applies $1,387 after a fee. | K8, U6 | two claims about p by two origins — and probably two **kinds** (*amount sent* · *amount applied*); if one kind, a conflict; nothing chosen; the catalogue is not ruled here |
| **Pm7** | Reversal / chargeback (`ExpenseFundingAllocation.mode = reversed`, `occurred_on`). | allocation | representable as **a dated claim about p** by the bank or E (*reversed as of d*); whether a reversal is instead its own event identity (a second payment, negative) related to p is **not decided** — the household or the bank's statement says which, and the relation kind is not ruled |
| **Pm8** | Rob paid $700 and $712 the same day; the bank shows one $1,412 debit. | correspondence | two payments minted (Rob's two assertions) *or* one — Rob says which; `payment_corresponds` if he later says the two were one; never merged; the bank line's candidate points at whichever he asserts |
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
  is a state read off claims, not the identity; and the fourth claim, E's, was the missing party.
- **The payer is a relation** (Pm9), like the obligor.
- **Minted only by the household's assertion** (Pm2, Pm10, Pm14): never by a bank line, a draft, a
  ledger row, or E's statement — those yield candidates.

---

## 4. What makes something correspond to the payment

Four different things, three ruled mechanisms and one blocked:

1. **Another payment identity** (Pm8): `payment_corresponds` — slice 4's shape, fourth type.
2. **A party**: dated role claims — *paid_by(P, p)*, *paid_to(P, p)* (the payee fact of the
   servicing ruling, now a claim about p rather than "on the row").
3. **An obligation**: *toward(p, O)* — the household's claim about what the payment was for,
   with object the obligation (Pm1, Pm5, Pm13). Not identity of either; a claim, retractable.
4. **An artefact — the bank's statement, E's statement, a receipt.** `artefact_concerns(A, p)`
   where A is the payment's own record (a receipt; a confirmation email; a single-transaction
   artefact) — the slice-8 kind, gaining `object_payment_id` as its ruled growth path says. But
   where A is a **statement listing many payments** (Pm2, Pm3 — the common case), the tie between
   *this line* and *this payment* is the **proposition-level about-ness Ab7 forced** — forced
   again here, and more sharply: bank statements are line-item documents by nature. **Blocked;
   its own ruling; not designed here.** Whether the 1.x `transactions` row could be treated as a
   single-line *artefact* (making the tie artefact-level) is the *transaction referent's* question
   (slice 6 §4), also not this slice's.

What does **not** make something correspond: a matching amount and date (a candidate), a
merchant string (a candidate), a draft (a candidate), a cleared flag (the bank's claim about
movement, nothing about identity).

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

> **A payment is an event identity minted by the household's individuating assertion that a
> payment was made — an utterance whose origin is a Person. The anchor is structure plus a
> pointer to the minting utterance and nothing else: no payer, payee, amount, date, method,
> purpose, clearance, acknowledgment or reversal lives on it. Every such property is a claim
> about the payment, made by the party knowing for it — the bank for movement, the entitled
> party for acknowledgment (D4, which this identity makes representable: discharge is that claim,
> by definition, and nothing downstream is derived from it here), the household for what it was
> toward and to whom it was meant — and payer and payee are dated role relations, not anchor
> columns. A payment is not a transaction (it may have none; a debit may be no payment), not a
> discharge (it exists before, without or despite E's acknowledgment), and not a "confirmed
> payment" (cleared · attached · confirmed are three claims from two of the four parties; the
> fourth was E's). It is never minted by a bank line, a ledger row, a draft or E's statement —
> those yield candidates. Something corresponds to it as another payment (`payment_corresponds`),
> as a party (a role claim), as an obligation (a *toward* claim), or as an artefact — its own
> record by `artefact_concerns`; a line in a statement by the proposition-level about-ness that is
> now forced twice and remains its own ruling. `DebtLedgerEntry` and `CheckingTransactionLink` are
> household assertions with the payment identity missing from the middle, decomposable only
> where their asserting party is a fact, which today it is not.**

If ruled, the build is the obligation slice's shape exactly: `payments(id · minted_by_id →
utterances · created_at)` with the minting-utterance guard · additive `subject_payment_id` /
`object_payment_id` slots · `payment_corresponds` in the registry and `referent()` ·
`artefact_concerns` gaining `object_payment_id` as its ruled growth path · fixture over Pm1–Pm14
with stand-in kinds and the not-derived consequences asserted (D4 representable; no `remaining`;
no discharge derivation; Pm2/Pm3 line ties asserted *not representable*; Pm12 asserted as *no
payment*; Pm14 as *no mint*) · mutations (a bank line mints; a draft mints; a payee/amount column
appears; E's acknowledgment moves something; a cleared flag establishes acknowledgment;
correspondence merges) · migration: `create_all` + two additive columns, **no data step**. **Not
in it:** Ab7 · the transaction referent · reversal's shape · the catalogue · any consumer ·
`DebtLedgerEntry` / allocation decomposition.

*The line: a bank can say money left; a creditor can say money arrived; only the household can
say it paid.*
