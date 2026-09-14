# The obligation as a 2.0 identity — what is it, and what makes something correspond to it?

> Status: **Build mode, opened by Rob 2026-09-14; §8 ACCEPTED and the representational build
> AUTHORISED, exactly as fenced (§9).** Slice 6 is accepted
> at `88abc97` (`DOMAIN_PROPOSITION.md` §8): *identity precedes proposition instances*, and the
> obligation is the first referent to rule. This record tests four readings of the obligation's
> identity against the cases the disposition, servicing, acknowledgment and lifecycle records
> already ruled, answers the second half of the question (correspondence), evaluates the 1.x
> rows only afterwards, finds two blockers, and ends with a ruling candidate, ruled in §9.

**Rob's question, verbatim:** *what is the obligation as a 2.0 identity, and what makes
something correspond to that identity?*

**Rob's negative criterion, verbatim:** *do not start by asking "which existing table
represents the obligation?" … Only after that can the 1.x rows be evaluated as possible records
of it.* §6 honours the order.

**The acceptance test carried in from slice 6:** once an identity is proposed, the domain
propositions that need it (D4 P-ack payment · D5 P-ack balance · D7 *P is E of X*) must satisfy
the domain-proposition contract *without reopening the definition*: subject structural,
participants not content, identity before instance.

---

## 1. What is already ruled, and therefore constrains the answer

| Ruling | What it fixes |
|---|---|
| **Disposition doctrine** (`CARRIES_DOCTRINE_TEST.md`, frozen) | *disposition follows the household obligation, across changes in entitlement*; the **obligation-centred** model survived write-off (4b) and recourse (§9–10); the ledger-centred model failed twice; **the obligation is the continuant** |
| **§7.7 classification** (frozen) | classification describes the obligation *by its financial terms and, where applicable, the nature of the underlying expense — not by the party entitled to collect it*; instrument kind is **a fact about the obligation**, stored, never computed; `Unknown` is a terminal state |
| **Servicing** (S1–S7, frozen) | **three facts**: entitled party · payee · discharge; assignment vs sale (S4/S5) change who is entitled *on the same obligation*; S6: paying E directly can leave it uncredited; S7: recourse returns the obligation to E |
| **Acknowledgment** (K1–K8) | P-ack is *E's stated position about a payment or balance* — **of an obligation**; E only |
| **Lifecycle §10** (Rob, 2026-09-09) | *who carries an obligation* is **not one fact** — funding · servicing · economic risk are three layers; *a single `carrier` field cannot represent all three*; **payment state may evidence but never establish a change of carrier**; **a discovered transition preserves effective_on and recorded_at** |
| **Lifecycle §5** | the economic-transfer invariant: whenever economic terms change, every amount whose treatment changes has an explicit, reconstructable disposition — *regardless of M1 or M2* |
| **M1 / M2** (`OBLIGATION_LIFECYCLE_QUESTION.md`, held) | M1: the obligation is the durable entity, carrier/instrument/terms versioned facts *about* it; M2: instrument kind is part of an *agreement's* identity, a change ends it and begins a successor; **M3 — mixing — refused**; the decision was held behind §7.7, which has since been ruled |
| **Party reference** | **roles are dated relations over parties, never parties**; *P is E, stops, is E again: still P* |
| **Institution encounter / minting** | encounter mints nothing; an identity Groundwork has no sovereign declaration for comes to exist by **one event: the household's individuating assertion**, a claim with strength; the anchor = structure + a pointer to the minting claim; descriptors are the utterance's content |
| **Correspondence** (slice 4) | separately minted identities of one type are asserted corresponding by a party; observed matches (ids, descriptions) are candidates; never merges |
| **Slice 6** | a `transactions` row is the bank's *statement*, not the event; a 1.x row is not presumed to be the thing |

Two things follow before any case runs. First, **the identity question is M1/M2 asked at the
identity level** — and the doctrine has since answered the part that matters here: the thing
disposition follows across entitlement changes *is* the continuant, so whatever the 2.0
identity is, it survives a change of entitled party, servicer, funder and risk-bearer. Second,
**every party-relation of the obligation is a dated relation, not identity** — the party ruling
said it of roles generally, §10 said it of carriage specifically. Neither settles *what mints*
the identity, which is the question.

---

## 2. Four readings of "the obligation as an identity"

**Reading A — minted by the household's individuating assertion.** *"I have a mortgage with
Harbor"*, *"I owe Riverbend Hospital for the ER visit"*: an utterance, origin a Person, mints the obligation
exactly as it mints an institution. The anchor is structure + a pointer to the minting
utterance. Everything else — creditor, amount, kind, terms, who is entitled, who services — is
a claim about it.

**Reading B — minted by encounter.** A bill or statement arrives; an obligation row is created
from it (issuer, account number, amount). The document is the identity's basis.

**Reading C — derived, no identity.** "The obligation" is whatever the statements, P-acks and
payments cohere around; consumers cluster claims by account number and creditor and call the
cluster an obligation.

**Reading D — a 1.x row is the obligation.** `DebtAccount`, or `ExpenseObligationVersion`'s
chain, *is* the identity, and 2.0 references it.

B fails on the institution ruling transposed without change: *encounter mints nothing; an
artefact describing an obligation establishes an artefact and a description; description never
mints*. Two identical statements would mint two obligations; a statement about an obligation
the household never had (S3's letter) would mint one — a false assertion given an identity by
arrival. And it puts the *creditor's* act where the *household's* belongs, which is the
disposition doctrine's ledger-centred failure in a new form.

C fails on the doctrine directly: disposition needs a continuant across entitlement changes,
and a cluster keyed by creditor or account number *dissolves* at exactly those changes (S4/S5:
new creditor, new account number, same obligation). The carries test already killed the
ledger-centred model for this reason; a clustering is the ledger-centred model without a
ledger. It also cannot represent Ob9 (an obligation whose creditor is not yet known).

D is Rob's negative criterion, and is evaluated in §6 *after* the identity is proposed, as
records of it.

A is tested.

---

## 3. The cases

| # | Case | Ruled in | Under A |
|---|---|---|---|
| **Ob1** | Rob: "I have a mortgage with Harbor — account ending 4471, about $180k." | minting ruling | one utterance; mints obligation **O1** (anchor under the utterance); the same utterance evidences claims *about* O1: instrument kind (mortgage), entitled party (Harbor, D7 at d), a balance testimony; "4471" and "$180k" are **content** — correspondence evidence, never identity |
| **Ob2** | A bill arrives from Riverbend Hospital Hospital (artefact, origin Riverbend Hospital). | institution encounter | mints nothing; propositions read from it have the obligation as a participant **not established, with candidates** (account number matches?); Rob: "that's the ER visit" → mints **O2** and asserts the bill concerns it (§4) |
| **Ob3** | S4/S5 — Harbor assigns (or sells) the mortgage to NewCo. | servicing, doctrine | O1 unchanged; a new D7 claim *NewCo is E of O1 as of d*, with `as_of` = effective date, the utterance's `recorded_at` = when learned — **the §10 dating requirement is met by the substrate's existing two coordinates**; the old D7 remains (history, not removal); disposition follows O1 |
| **Ob4** | Write-off (4b). | doctrine | O1 unchanged. What changed is a stance of E's about O1 at d — a claim, not a mint or unmint. *(The residue the doctrine left unnamed stays unnamed here.)* |
| **Ob5** | S7 — recourse: provider → financing party → provider. | §10 | three dated D7 claims on one O; **payment state never establishes the return leg** — a missed payment is evidence a consumer may weigh, never a transition the substrate records; under M2 this loop would be three agreements for one debt |
| **Ob6** | Restructure — new terms. | §5, the reconstruction test | either *the same O with new terms* (terms claims with `as_of`) or *a new O that settled the old* (O3 minted by the household's assertion + a relation between O3 and O1 — kind not ruled here); **the household says which** (C9); both must be representable; the economic-transfer invariant's disposition is then a claim on whichever the household asserted |
| **Ob7** | Rob asserts "my Harbor mortgage" in March and "the 4471 loan" in June, not realising. | correspondence | two obligations minted; account-number match → **candidate**; Rob: "same loan" → `obligation_corresponds`; never merged; the referent contains both |
| **Ob8** | A joint obligation — Rob and a household member both owe. | party ruling; *a joint account has no author* | the obligor is **a dated relation** (*P is obligated on O*), two claims; not an anchor column — an anchor column would make "whose" part of identity and break on assumption / release of one obligor |
| **Ob9** | "I owe someone for that ambulance — the letter didn't say who." | party state 3 | **O minted with no entitled party established**: D7 absent, or with candidates; identity without a creditor is legitimate because the creditor is a relation — reading C cannot represent this at all |
| **Ob10** | S3 — a letter from a party claiming to be the servicer. | S3 | O exists (Rob owes P); S3's letter is an artefact with origin S3; *S3 services O* is a claim the household may make and later retract (`utterance_retraction`); O is untouched by the false relation |
| **Ob11** | The balance is disputed (U6: four figures). | U6, K8 | balances are D5 claims at dates by parties; **amount is never identity**; the dispute is representable as competing claims and nothing is chosen |
| **Ob12** | Rob: "I never had that loan — I was confusing it with my brother's." | Case B, minting | `utterance_retraction` of the minting utterance; O remains (never removal), under a claim now said not to stand; **unminting is not derived** (the same fence as the institution's, H10) |

**A survives every case; the identity is the minting act and nothing else.** Every property a
schema would be tempted to put on the row — creditor, account number, amount, kind, obligor,
servicer, status, terms — is a claim *about* the obligation, and each case above needs at
least one of them to change while the obligation stays what it is.

---

## 4. The second half — what makes something correspond to the obligation

Three different things "correspond" to an obligation, and they are three different mechanisms
already ruled:

1. **Another obligation identity** (Ob7): `obligation_corresponds` — slice 4's kind shape
   extended to a third type; candidates from account numbers and creditor names; established
   by a party's utterance; never merged.
2. **A party** (Ob1, Ob3, Ob5, Ob8, Ob9): **dated role relations** — *P is E of O as of d*
   (D7), *S services O as of d*, *P is obligated on O as of d* — each a domain proposition with
   subject a party, object the obligation, `as_of` the effective date. Not identity; §10's three
   layers are three kinds, not one field. (The role *period* remains the slice-6 fence: one
   `as_of` per claim; a period is a later ruling.)
3. **An artefact** (Ob2, Ob10) — the statement, the bill, the collection letter: **the case the
   inventory did not name.** A statement's readings yield D5 claims whose object is the
   obligation — but a reading cannot establish *which* obligation (it reads an account number:
   a candidate). So: the D5 read from the statement carries `object_state = not_established_
   with_candidates`; the household's assertion establishes the link. **What form does that
   assertion take?** Two candidates, and the record does not choose:
   - **(i) a proposition per artefact** — *artefact A concerns obligation O* (subject artefact,
     object obligation; established by the household; candidates from descriptors) — one claim
     covers every value read from A, and consumers derive that A's D5s are about O;
   - **(ii) re-asserting each read claim** — the household's utterance evidences a new D5 with
     the obligation established, leaving the reading's claim as it was.
   (i) is one claim where (ii) is many, and (i) matches how a person actually behaves ("that's
   my Harbor statement"); but (i) is an *about-ness* kind not in the inventory, and (ii) needs
   nothing new. **A ruling of its own** — it recurs for every referent (a statement concerns a
   plan; an EOB concerns a claim) and should be ruled once.

What does **not** make something correspond: an account number alone (description never
matches), a payment to a payee (S6: paying E directly does not even establish discharge, let
alone identity), a creditor's name on a document (candidate), or Groundwork's own inference from
a recurring payment pattern (a candidate that must be *surfaced* — the no-silent-learning rule —
never a mint).

---

## 5. What the identity satisfies — the slice-6 acceptance test

| Domain proposition | With the obligation minted | Contract |
|---|---|---|
| **D5** P-ack balance — *E states balance b on O as of d* | subject E (party), **object O**, content b, `as_of` d | subject structural ✓ · participant not content ✓ · identity before instance ✓ |
| **D7** *P is E of O at d* | subject P, **object O**, content the role, `as_of` d | ✓ — and Ob3/Ob5 show the history is a sequence of these, never an overwrite |
| **D4** P-ack payment — *E acknowledges payment p* | subject E, **object p** — **the payment has no identity yet** | ✗ — blocked on the *payment* referent (§7); the obligation alone does not unblock D4 |
| instrument kind — *O is a mortgage* | subject O, content the kind | ✓ — a claim, absent = `Unknown`, exactly the classification ruling's terminal state; **not** a column on the anchor |

Three of four; the fourth names the next referent.

---

## 6. The 1.x rows, evaluated afterwards as records of it

Now, and only now, the negative criterion's other half:

| Row | What it is, against A | Record of the identity? |
|---|---|---|
| **`DebtAccount`** (name · balance · debt_type · linked_account · paid_off_at) | created by the household in the UI — **a household assertion with descriptors**: the closest shipped thing to a minting utterance plus its content claims (name, kind, balance) fused onto one row | **yes-shaped** — decomposable into *one minting utterance + one obligation + kind / balance / name claims* **where the asserting party is a fact** (see the blocker below) |
| **`ExpenseObligationVersion`** (effective_seq · recorded_seq · supersedes_id) | versions of an obligation's amount/terms with dual time — **claims about an obligation at effective/recorded dates**, the §10 dating shape already | claims, not the identity; the identity they version is `HealthcareExpense`'s obligation, unminted |
| **`DebtLedgerEntry`** | attached-payment records (H2) | **the payment referent's** territory, not the obligation's |
| **`HealthcareExpense`** | the household's record of an expense event, from which an obligation arises | a *different* referent — the expense/claim (D3) — of which the patient-responsibility obligation is one consequence; **not** the obligation |
| **`ExpenseFundingAllocation`** | funding events with `attached / cleared / user_confirmed` | claims about payments — the acknowledgment sequence one party short (shipped-vs-target) |

**Blocker for any decomposition:** a minting utterance needs an origin party, and **production
has zero `Person` rows** (`PERSON_PARTY_ANCHOR.md`: no route creates one). The asserting party of
every `DebtAccount` is *not a fact* today — so *old rows decomposed only where decomposition is a
fact* forbids minting obligations from them until the household has declared its members. This
is not a defect of the ruling; it is the fixed point doing its job.

---

## 7. Not decided here — fences and findings

- **The payment referent** — D4 is blocked on it; `DebtLedgerEntry` and `transactions` are
  both *records* (H2's projection input; the bank's statement), neither the event E
  acknowledges. Its own question, next in line if P-ack is to be built.
- **Artefact ↔ obligation about-ness** (§4.3, (i) vs (ii)) — a ruling of its own; recurs per
  referent.
- **The role period** — slice 6's fence stands; D7 claims are stances at dates.
- **Restructure relation** (Ob6) — *O3 settled O1*: a kind between obligations that is not
  correspondence (they are not one referent) and not supersession of artefacts; ruled when the
  economic-transfer invariant's consumer is built.
- **Agreement identity (M2's object)** — not needed by any case here; the obligation is the
  continuant and terms are claims. If a case ever forces an *agreement* as a minted identity
  beneath the obligation, it is a later question; nothing here forecloses it, and nothing here
  requires it.
- **Unminting** (Ob12) — fenced as for institutions.
- **Relational knowing** — D5/D7's knowing party is *E of this O* / *the household*; the
  obligation identity makes the predicate *statable* (`E of O`) but its form is still the fenced
  question; D5/D7 derive `undetermined` until it is ruled.
- **The kind catalogue for obligation claims** (instrument kind values, role kinds, balance
  kinds) — domain questions; the record names the shapes, not the values.

---

## 8. Ruling candidate — for Rob

> **The obligation is a Groundwork-minted identity that comes to exist by one event: the
> household's individuating assertion that it owes — an utterance whose origin is a Person.
> The anchor is structure plus a pointer to the minting utterance and nothing else: no
> creditor, amount, kind, obligor, servicer, status or account number lives on it. Every such
> property is a claim about the obligation — instrument kind, balance and terms as dated
> stances; entitled party, servicer, funder, risk-bearer and obligor as dated role relations
> over parties (§10's three layers are three kinds, not one field); a discovered transition is
> a new claim with `as_of` the effective date and the utterance's `recorded_at` the learned
> date, the earlier claim remaining. The identity survives assignment, sale, write-off,
> recourse and restructure because none of those touches the anchor; it exists without a known
> creditor; it is never minted by a bill, a statement, a payment or an inference — those yield
> candidates. Something corresponds to it in one of three ruled ways: another obligation, by
> `obligation_corresponds`; a party, by a dated role claim; an artefact, by an assertion whose
> form — one about-ness claim per artefact, or a re-asserted value claim — is a ruling of its
> own. A 1.x `DebtAccount` is a household assertion with descriptors and is decomposable into
> the identity only where its asserting party is a fact, which today it is not. The payment is
> a separate referent, and D4 waits on it.**

If ruled, the build is the institution slice's shape exactly: `obligations(id · minted_by_id →
utterances · created_at)` with the one-anchor guard · additive `subject_obligation_id` /
`object_obligation_id` slots · `obligation_corresponds` in the registry and `referent()` ·
fixture over Ob1–Ob12 with D5/D7 as stand-in kinds and the not-derived consequences asserted
(no unminting; disposition not derived; payment state not consulted; no column beyond the
anchor) · mutations (a bill mints; a creditor/amount/kind column appears; a role rewrites the
anchor; a missed payment records a transition; retraction unmints) · migration: `create_all`
+ two additive columns, **no data step**. **Not in it:** the payment referent · about-ness
form · role period · restructure relation · any consumer · any `DebtAccount` decomposition.

*The line: a bill can describe a debt; only the household can say it owes one.*

---

## 9. Ruling — Rob, 2026-09-14. §8 accepted; the representational build authorised, exactly as fenced.

*A does not merely win the case comparison; it preserves the distinctions slice 6 established
without creating a new hidden ontology.* The cleanest formulation:

> **An obligation is a continuant minted by the household's individuating assertion.**

Everything else — creditor · amount · kind · obligor · servicer · terms · account number ·
entitlement · disposition · balance — is *information about that continuant*. That is why the
obligation survives changes to those things without a magical continuity algorithm. **S4/S5 is
decisive:** if creditor or account number can change while the obligation persists, they cannot
constitute its identity.

**B** would let an institution create a new world object merely by issuing another statement —
the evidence artefact partly responsible for ontology; the transactions category error again:
*the record describing the thing becomes the thing.* The bill establishes a proposition about
the obligation; it does not manufacture it. **C** has the wrong ontological direction, not
merely inconvenience: an obligation can exist before its creditor is known, so creditor-derived
identity is impossible independently of the transition cases. **D** was rightly evaluated last —
what it is · how it is minted · what corresponds · *then* whether a 1.x row instantiates it —
otherwise the existing schema dictates the ontology; `DebtAccount` is yes-shaped, which does not
mean "therefore it is the obligation".

**The correspondence section exposes the next real question.** Three supported directions —
obligation ↔ obligation · party ↔ obligation through dated role propositions · artefact →
obligation through a still-unruled about-ness relation — and the last is correctly not chosen
between (an explicit *concerns* proposition vs re-assertion through every reading). Its
recurrence across claim / statement / plan / obligation is strong evidence it deserves **its own
slice** rather than being hidden inside whatever consumes it.

**The Person blocker is exactly the fixed point wanted.** There is no legitimate way to retrofit
`DebtAccount.asserted_by = ???` from today's data; *"we know it was the household"* is not
enough to manufacture a person identity. **The ontology is settled before the migration data
is** — the implementation may not invent historical facts to populate the new model.

**One subtle point, preserved explicitly in the ruling: the minting act is not the minted
identity.** The obligation is not the utterance. The utterance mints the obligation and supplies
its anchor; the obligation thereafter exists as the continuant to which later propositions
refer. This matters for retraction, correspondence, restructuring, disposition and historical
truth — otherwise *minted by assertion* can sound as if the assertion remained the identity.

**Authorised — the representational projection of the ruling, exactly as fenced:** obligation
anchor · additive identity slots · `obligation_corresponds` · fixture · mutation tests. **Not:**
data migration · payment identity · artefact-about-ness decision · role-period decision ·
restructure relation · interpretation or consumer. **And the absence of `Person` production
rows must not tempt a synthetic migration** — a downstream data question, not a reason to
weaken the identity ruling.

*A bill can describe a debt; only the household can say it owes one* — essentially the whole
ontology in one sentence.
