# Slice 6 — what is a domain proposition?

> Status: **Build mode, slice 6 opened by Rob 2026-09-13 — record only, no code.** Slice 5 is
> closed at `2f127c9` (`CLAIM_ABOUT_CLAIM.md` §8). This record answers Rob's three questions
> from the inventory of domain propositions the rulings have already named, finds that the
> cases force the *shape* of a domain proposition but do not yet permit an *instance* of most of
> them — for two reasons that are each a ruling of their own — and ends with a ruling candidate.
> Nothing here is authorised to build.

**Rob's question, verbatim:** *what is a domain proposition?* — tested by three things:

1. What is its subject? A world referent — artefact, party, obligation… — not an utterance.
2. What distinguishes content from participants? Content stays opaque to derivation; a genuine
   referential operand must be structural, never smuggled into text.
3. What makes it a domain claim rather than a claim-about-a-claim? Slice 5's boundary:
   `utterance_retraction` is about an act; a domain proposition says something about the
   world, *even when its evidence is an utterance*.

**Rob's fence, verbatim:** *slice 6 rules representation of the domain propositions, not their
interpretation.* And: *P-ack is not permission to generalise the strength model.*

---

## 1. What is already ruled, and therefore constrains the answer

| Ruling | What it fixes |
|---|---|
| **Proposition** (`PROPOSITION.md`) | kind · subject (a reference into the record *or an absence*, possibly not established) · content (what disagreement is about); the eleven ruled propositions span seven subject types |
| **`SMALLEST_SCHEMA.md` §12** | referential operands are structural slots, never content; *further ruled referent types (a transaction, an obligation, a plan) arrive as their slices land*; `as_of` is the one temporal coordinate a proposition carries (*a stance as of d*) |
| **Cluster B** | two propositions per value: **P-subject** (*artefact A states X*, subject the artefact) and **P-world** (*X is true*, subject the world); resolving one never establishes the other |
| **Acknowledgment** (K1–K8) | **P-ack** = *the entitled party's stated position about a payment or balance, as of a stated date*; **one knowing party, E**; payment acknowledgment and balance statement are **two propositions** (K8); every acknowledgment is dated |
| **C1** | origin — and so the knowing party — is fixed *per proposition kind*: *the insurer adjudicated the claim*; *E only*; *the user was there* |
| **Party reference** | roles are **dated relations over parties, never parties** (*P is E, stops, is E again: still P*) |
| **Disposition doctrine** | disposition follows *the household obligation* across entitlement; entitlement transitions carry effective time · learned time · source · amount relationship |
| **Shipped-vs-target** | `Transaction`, `DebtAccount`, `HealthcareExpense`, `ExpenseObligationVersion`, `HealthPlan` are 1.x rows; *old rows decomposed only where decomposition is a fact*; no legacy-table repair |
| **Slice 5** | a claim whose subject is an utterance is higher-order; the knowing relation for it is *relational*, fenced |
| **H2 / H4** | `remaining` is an attached-payment projection, not discharge; `resolution()` untouched — both are *interpretation*, outside this slice by the fence |

---

## 2. The inventory — every ruled domain proposition, decomposed

The eleven ruled propositions, minus the three already built as kinds (`artefact_origin`,
`artefact_corresponds` / `party_corresponds`, `utterance_retraction`) and the minting assertion
(which is an utterance, not a kind), leave the **domain** inventory. Each is decomposed by Rob's
questions, plus the two columns that decide whether it can be built: *does its referent exist
in the substrate as an identity?* and *is its knowing party relational?*

| # | Proposition, as ruled | Subject (referent type) | Second participant | Content | `as_of` | Knowing party | Referent in substrate? | Knowing relational? |
|---|---|---|---|---|---|---|---|---|
| **D1** | *transaction t is health on axis X* | a **transaction** | — | the axis value (yes / no / unknown) | — | user · the insurer *of this claim* | **no** — a 1.x row (`transactions`), status unruled (§4) | **yes** — not any institution: the adjudicating insurer |
| **D2** | **P-subject** — *artefact A states patient-responsibility = $412* | an **artefact** | — | the stated value | the document's date is the artefact's, not the claim's | whoever read A (a reading) — and strength then follows A's origin (slice 3) | **yes** | via origin — already derived (slice 3) |
| **D3** | **P-world** — *patient-responsibility for this claim = $412* | **the claim** — a world event | — | the value | — | nobody (§8.2a) — or the insurer, derivable through D2 | **no** — the insurance claim has no identity anywhere; `HealthcareExpense` is 1.x and is *the household's record of* it, not it | **yes** |
| **D4** | **P-ack (payment)** — *E acknowledges payment p, as of d* | the **party E** (whose stance) | **the payment p** | the position (received · applied · not received) | **d** | **E only** | party yes; **payment no** — a 1.x row (`debt_ledger_entries` / transaction) or an event with no identity | **yes** — E *of this obligation* |
| **D5** | **P-ack (balance)** — *E states balance b on obligation X, as of d* | the **party E** | **the obligation X** | the balance | **d** | **E only** | party yes; **obligation no** — 1.x rows (`DebtAccount`, `ExpenseObligationVersion`); the *household obligation* of the doctrine has no 2.0 identity | **yes** |
| **D6** | *S serves P* (servicer of record) | a **party S** | a **party P** | the role (serves) | the date the stance is about; the *period* is not one date (§3.2) | the household (asserted); S or P themselves | **yes** (both parties) | **yes** — the household for its own relations; S and P for theirs |
| **D7** | *P is E of obligation X at d* | a **party P** | the **obligation X** | the role (entitled) | **d** | the household; E's own documents | obligation **no** | **yes** |
| **D8** | *B supersedes A* | an **artefact B** | an **artefact A** | — (the kind is the content) | the supersession's date, if stated | the issuer of B (B's origin) | **yes** | via origin |
| **D9** | *the classification of row r is manufactured* | a **classification** — a process's output | — | manufactured | — | **no party** — a process | **no** — a classification is not a substrate identity; and a process cannot utter (O9) | n/a |

Two propositions are fully representable today: **D2** (P-subject) and **D8** (supersession
between artefacts) — and D6 nearly (both parties exist; its temporal shape is the problem,
§3.2). The fixtures have been exercising D2 since slice 2 under the stand-in kind
`eob_amount`. Everything else waits on a referent that does not exist as a 2.0 identity.

---

## 3. Rob's three questions, answered from the inventory

### 3.1 Subject: a world referent — five types appear, and one never does

Artefact (D2, D8) · party (D4–D7, as the party *whose stance or role* it is) · transaction
(D1) · obligation / payment (D4, D5, D7) · the world event itself (D3). **Never an utterance**:
that is the slice-5 boundary, and it is structural — a domain kind's registry entry never
permits `subject_utterance_id`. It is also not "a classification" (D9): a process's output is
not a thing in the record a claim can be about; D9 is the manufactured *flag* (decision 9) and
lives where the sensitivity ruling put it, not here.

### 3.2 Content vs participants — the test the inventory forces

> **If a disagreement about it would be a disagreement about *which thing*, it is a
> participant and gets a slot. If it would be a disagreement about *what is said of the
> thing*, it is content.**

Applied:

- **P-ack's payment / obligation** (D4, D5): two acknowledgments "of the $175 payment" and "of
  the $175 payment of March 3" differ in *which* — a participant. Content = the position.
  Putting the payment in content makes two P-acks about different payments structurally
  indistinguishable — the hidden-operand mistake at the exact place the acknowledgment ruling
  said matters most (K8: payment ack and balance statement are two propositions; they need two
  *subjects*, not two strings).
- **The health axis** (D1): the axis is part of the **kind** (the two-axis space is two kinds);
  the value is content. The $412 vs $4.12 re-parse *registering no disagreement* (both say
  health) is correct under this split — the amount is D2, a different proposition.
- **The role** (D6, D7): the counterparty is a participant; the role name is the kind; nothing
  is content. And the **period** is the finding: *roles are dated relations*, but a relation has
  an effective period and a proposition carries one `as_of`. *P is E, stops, is E again* is three
  stances at three dates — representable as three claims — but "S served P from March to June"
  is not one claim's content (a temporal operand is an operand). **A period-bearing claim is
  not representable in this slice**; whether a period is two coordinates on the proposition or
  two propositions (begins / ends) is a ruling the cases have not forced. Fenced.
- **`as_of`** (D4, D5, D7): the ruled temporal coordinate — *a stance as of d* — is a column,
  and every P-ack is dated by ruling. Present, sufficient for the stance kinds.

### 3.3 Domain vs claim-about-a-claim — the evidence path is not the subject

"The EOB says $412" said by Rob is a **domain** proposition (D2, subject the artefact)
*evidenced by an utterance* — slice 2's X7 already holds the two apart. `utterance_retraction`
is about the act. The test is the subject's type, never the source's type: a domain claim may
be evidenced by an utterance or a reading; a higher-order claim is about an utterance whatever
evidences it. **P-world vs P-subject** are both domain (Cluster B): the world and the artefact
are both world referents; neither is an act.

---

## 4. The finding that stops most instances: domain referents are not yet identities

Six of nine inventory rows need a referent the substrate does not have: a **transaction**, an
**obligation**, a **payment**, an **insurance claim**. Each exists in 1.x as a row — and that is
precisely the problem, because *what the row is* is unruled, and in at least one case the
obvious answer is a category error:

- **A `transactions` row is the bank's statement that a transaction occurred** — a value read
  from a feed or a statement: in this ontology a **P-subject** (D2-shaped: *the feed states a
  debit of $X on d*) whose artefact (the feed / statement) and reading are unrepresented. The
  purchase — the world event D1 is *about* — is the referent of that statement, not the row.
  A `subject_transaction_id` slot pointing at the row would make the bank's statement stand in
  for the world event — `Evidence.source`'s category error in a new place, and the Cluster B
  ruling (P-subject ≠ P-world) violated at the substrate's own front door.
- **The obligation** of the disposition doctrine (*the household obligation, across
  entitlement*) has **no 2.0 identity**; `DebtAccount` and `ExpenseObligationVersion` are 1.x
  records with their own identity bases. Which of them, if either, *is* the obligation — or
  whether the obligation is minted like an institution, under the household's assertion — is
  decision 2's territory (M1/M2, schema), explicitly held behind §7.7.
- **The payment** (D4) is either a transaction row (the same problem) or a `debt_ledger_entries`
  row (an attached-payment record, H2's projection input) — neither is the *event* E
  acknowledges.
- **The insurance claim** (D3) exists nowhere as an identity; `HealthcareExpense` is the
  household's record of an expense, and *the claim* is the insurer's object.

So the honest result is: **the shape of a domain proposition is forced; the first domain slot
is not.** Adding any of these slots is a ruling about *that referent's identity* — what mints
it, what it corresponds to, whether a 1.x row is it or is a statement about it — and it is a
ruling of the same weight as the institution's was. This record does not make it.

**A note on order, not a decision.** If Rob opens a referent question next, the inventory
suggests the **obligation** first: D4, D5, D7, the disposition doctrine, H2's `remaining`, the
acknowledgment chain (P-ack → discharge → remaining) and the E-role all hang on it, and it is
the one whose 1.x rows are least likely to *be* it. The transaction is the tempting first (it
has the most rows) and the most dangerous (its rows are statements).

---

## 5. Relational knowing — three kinds now wait on it; the cases still do not force its form

Every domain kind in the inventory has a **relational** knowing party: *the insurer of this
claim* (D1, D3), *E of this obligation* (D4, D5, D7), *the household for its own relations*
(D6). The foundation-keyed map (`{kind: {person, institution}}`) was a slice-1 simplification
adequate for kinds whose knowing party is a *foundation* — and the inventory shows there are
none among the domain kinds: `{'institution'}` for a health value means *any* institution,
and a reading of a Harbor statement asserting "health: yes" would derive `knowing` through
Harbor's institution foundation. The slice-3 fixtures' `knowing` results (O1, O5) demonstrate
the *mechanism* — strength derived through origin, one link — under a coarse caller-supplied
map for an unruled stand-in kind; they are not ruled strengths.

Rob's fence holds: this is a *case* (three now — retraction, P-ack, health), not permission.
Candidate: any domain kind ruled in this or a later slice carries `relational_knowing: True`
until the relational form is ruled — `undetermined`, exactly as slice 5 — and **the relational
knowing question is now a question in its own right**, with three kinds waiting, to be opened
by Rob when a consumer forces it. What that ruling would have to say is at least: knowing is a
predicate over (claimant, proposition) — *is the claimant the origin of the subject utterance /
the entitled party of the subject obligation / the adjudicating insurer of the subject claim* —
which is why it cannot be ruled before the obligation and claim referents exist.

---

## 6. What could be built now — and why the candidate builds almost none of it

| Representable today | Would need | Built? |
|---|---|---|
| **D2 P-subject** — value kinds with an artefact subject | a **domain value catalogue** (`patient_responsibility` · `statement_balance` · `amount_due` …) — designing the health / debt domains, which Rob excluded from this question | **no** — the shape is exercised by the stand-in `eob_amount`; the catalogue is a domain question |
| **D8 supersession** — *B supersedes A* | nothing new: `subject_artefact_id` + `object_artefact_id`, a ruled kind entry, `reading_establishes` — the *issuer of B* is knowing, and the issuer is B's origin, so a **reading of B** can establish it (the one kind so far where a document may vouch — for *its own* supersession claim, T4) | **candidate: yes** — one kind, forced by the tie ruling, both referents exist; but its consumer (recency on the evidence's own axis) is fenced, so it would be represent-only |
| **D6 role, undated** | the kind, two party slots, `as_of` — and the period question (§3.2) unruled | **no** — a role kind that cannot carry its period would be ruled twice |
| the **domain / higher-order discipline** | nothing: per-kind slot contracts already exclude utterance subjects for domain kinds; a `layer` flag would be a taxonomy the cases do not need | **no** |

The candidate build is therefore **one kind or none**: `artefact_supersedes`, if Rob wants the
tie ruling's T4 representable before its consumer exists; otherwise slice 6 is a ruling
without code — which the sequence allows (*the later ten are mostly tests of generality, not
reasons to expand the ontology*).

---

## 7. Ruling candidate — for Rob

> **A domain proposition is a proposition whose subject is a world referent — an artefact, a
> party, an obligation, a transaction, a claim — never an utterance; the evidence path (an
> utterance or a reading) does not decide the layer, the subject's type does. Every
> referential operand — the counterparty of a role, the payment or obligation a stance is
> about — is a participant slot, never content; content is what is said of the thing; the one
> temporal coordinate is `as_of`, and a period-bearing claim is not yet representable. The
> shape is forced by the inventory; instances are not: six of nine ruled domain propositions
> need a referent (transaction · obligation · payment · claim) that has no 2.0 identity, and
> each such referent is a ruling of its own — a 1.x row is not presumed to be it, and a
> `transactions` row in particular is the bank's statement, not the purchase. Every domain
> kind's knowing party is relational; the relational form remains fenced, three kinds now
> waiting on it, and any domain kind ruled before it derives `undetermined`. Nothing in this
> slice interprets a domain proposition: no acknowledgment reaches an obligation, no health
> value reaches a plan, no role reaches entitlement.**

**Build, if authorised — either:** (a) `artefact_supersedes` only — the one ruled domain kind
both of whose referents exist, represent-only, its consumer fenced; or (b) **no code** — the
ruling stands as the definition the referent slices will be checked against. The record
recommends **(b)**, with the obligation referent as the next question, because a kind built
before any consumer can read it proves nothing the registry entry does not already state.

**Not in this slice under either:** any domain slot · the value catalogue · the role period ·
relational knowing · P-ack, health, role, P-world instances · any consumer.

*The line: a domain proposition says something about a thing in the world; the record must
first be able to point at the thing.*
