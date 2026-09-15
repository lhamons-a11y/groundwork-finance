# Relation semantics — item 6, opened not as "design the relation family"

> Status: **Queue item 6, opened by Rob 2026-09-14. Pass A RULED as written (§A.6) and its representation authorised 2026-09-15; built — see the commit. Passes B–G open one at a time.** Items 1–5 are
> closed at `1deb727`. Rob's reframing, verbatim: *I would not open it as "design the relation
> family." That name is already a potential trap. The previous slices have deliberately established
> identities without allowing relations to acquire meaning by accumulation. Item 6 should therefore
> be the relation-semantics pass: determine which relationships actually exist, one at a time, and
> only then decide whether any share a family-level substrate.* This record carries the governing
> question, the discipline, the order and the stopping rule, and then runs **pass A** — the first
> relation — to a ruling candidate. Passes B–G follow one at a time, each after the previous
> ruling. **The highest-risk mistake is no longer missing a table: it is discovering a convenient
> generic relation abstraction and then unconsciously making the ontology conform to it.**

**The governing question, verbatim:** *when one established identity is said to stand in a
relationship to another established identity, what exactly is being claimed, who can establish
it, and what — if anything — can be derived from it?*

---

## 1. The discipline — shortcuts prohibited for every pass

1. Relation name ≠ relation semantics.
2. Correspondence ≠ arbitrary relationship.
3. About-ness ≠ relationship.
4. A bank / institution label cannot establish a household relation merely by appearing in content.
5. A relation cannot mint either endpoint.
6. A relation cannot merge either endpoint.
7. A relation cannot silently become a status.
8. A relation cannot imply an inverse unless that inverse is separately ruled.
9. A relation cannot imply cardinality unless ruled.
10. A relation cannot create temporal continuity merely because RP2 now exists.
11. A relation cannot create a consumer derivation.
12. **No family-level resolver until the individual relations establish that they actually share
    semantics** — the most important.

**The stopping rule for the family decision (G):** *if two relations differ in what establishes
them, what they mean, their directionality, their participants, or what they permit downstream,
they are not one semantic family merely because their database representation looks similar.*

---

## 2. The order, and the pressure each pass inherits

| Pass | Relation | Where the pressure already exists in the record | Rob's framing, carried |
|---|---|---|---|
| **A** | **Payment ↔ Payment** | REVERSAL.md §5/§8: *there must eventually be a claim relating certain payments when one is asserted to economically undo some or all of another* — forced-but-unruled; not correspondence, not `proposition_concerns`, not derived from "REVERSAL" | *what is the relation being claimed, and what are its semantics? Do not let "reversal" become a Payment status* |
| **B** | **Obligation ↔ Obligation** | OBLIGATION_IDENTITY Ob6: *the same O with new terms* or *a new O that settled the old* — the household says which; the relation kind not ruled | *one ending and another beginning · one continuing with changed terms · a refinancing · a transfer of servicing · merely a new dated stance* — none collapsed because an institution says "restructured"; **first determine whether there is an obligation-to-obligation relation at all** |
| **C** | **Obligation ↔ Expense** | EXPENSE_IDENTITY Ex4: *"That's the ER visit — I owe Riverbend Hospital for it"* — one act mints O and ties the bill to X; `arises_from` asserted absent | Ex5 disproves *every expense has an obligation*; the mortgage disproves *every obligation arose from an expense*; **what does "arises from" mean, who asserts it, directionality, multiplicity — and it must not imply payment, discharge, amount owed or necessity** |
| **D** | **Payment ↔ Expense** | PAYMENT_IDENTITY / EXPENSE_IDENTITY: different identities; the relation family fenced | *payment = money movement for expense* is the enormous temptation; the relation cannot manufacture either identity, cannot prove purpose from a bank description, cannot silently become one-to-one; cases must include **1→1, 1 expense→n payments, 1 payment→n expenses, payment with no established expense, expense with no payment, disputed attribution** |
| **D′** | **Payment ↔ Obligation** (*toward*) | PAYMENT_IDENTITY Pm1/Pm5/Pm13 already use `toward(p, O)` as a **stand-in** claim — a relation used before it is ruled | not in Rob's list; recorded here so it is not ruled by accumulation — to be placed after D, tested against D's semantics |
| **E** | **Plan ↔ Expense / Obligation / Payment** | PLAN_IDENTITY §5 fences; Pl7 (premium), Pl9 (which plan covered X) | **a very hard fence around the word "coverage"**: Plan's existence answers none of *who is covered · when · whether an expense is covered · whether the insurer owes a benefit · whether it paid · whether an obligation is covered*; **Plan must not become a semantic magnet** |
| **F** | **Covered-under / membership** | ROLE_PERIOD R10; PLAN_IDENTITY §8 | **its own semantic ruling**, never an automatic consequence of Plan + RP2: *Plan identity → meaning of covered-under → party / Plan relation → temporal boundary kinds → later consumers*, not *Plan exists + temporal grammar exists → membership exists* |
| **G** | **Family decision** | — | only after A–F: a common implementation abstraction, or merely proposition-shaped relationships that happen to look alike |

Nothing is built during the passes. Each pass ends in a ruling candidate; a ruling may authorise
a representation for that relation alone; G decides whether anything is shared.

---

## Pass A — Payment ↔ Payment

**The question, applied:** when a household member says *the $300 that came back on 6/9 undid
the $300 I paid Riverbend Hospital on 6/2*, what is being claimed, who can establish it, and what follows?

### A.1 What is already fixed

| Ruling | Constraint on pass A |
|---|---|
| **Payment identity** | a payment is an event identity minted by a Person's assertion that a payment occurred; amount, date, payer, payee, cleared, acknowledged, *toward* are claims about it; the payer may be anyone (Pm9) |
| **Reversal (C)** | money moving back is **another payment**; "reversal" is a claim; where no second payment is individuated it is a party's dated claim about the existing payment or a party's treatment of it (Rv3, Rv5, Rv6) — **not a relation case**; the relation is needed only where **two payments exist** (Rv1, Rv2, Rv7, Rv8); a bank line is evidence for either shape and manufactures neither (Rv9); netting is a consumer's (Rv7); retraction ≠ reversal (Rv11) |
| **Rob's correction 1 on REVERSAL** | *"the later returns to the earlier's payer some or all of what it paid"* **over-specified**; the relations are directional and contextual; no registry kind created merely because four cases show something will be needed |
| **Correspondence** | two events are never one referent — the relation is not `payment_corresponds` |
| **About-ness** | neither payment is a document the other concerns — not `proposition_concerns` / `artefact_concerns` |
| **Domain proposition (K8 / hidden operand)** | a referential operand is an operand: *p1 was refunded (by p2)* with p2 in content makes two claims about different pairs structurally indistinguishable — **both payments must be participants** |
| **Relational knowing** | knowing is derived from a kind-designated relation to a kind-designated participant; a kind with `relational_knowing` and no designated relation derives `undetermined` |
| **Prohibitions 1–12** | above |

### A.2 The cases

| # | Case | What must be sayable | What must not follow |
|---|---|---|---|
| **A1 (Rv1)** | Chargeback: Rob paid Riverbend Hospital $300 on 6/2 (p1); the network moved $300 back on 6/9 (p2); Rob: *that undid the charge*. | **p2 counteracts p1** — a claim with two payment participants, asserted by Rob | p1 acquires no `reversed` flag; nothing computes a net; p1 is not discharged, mutated or merged |
| **A2 (Rv2)** | Refund: the pharmacy credits $84 for the returned cushion; the pharmacy's statement says *refund for order 5512*. | the pharmacy (an institution) **may assert** the relation; the household may assert it; each is a claim with its evidence | the pharmacy's word "refund" establishes nothing by appearing in content; knowing for the relation is **not ruled** — `undetermined` |
| **A3 (Rv7)** | Partial: $120 of the $300 comes back. | the same relation, p2 = $120 (p2's own amount claim) | the relation carries no amount; "$180 remains" is a consumer's (item 7); "partial" is not a kind |
| **A4 (Rv8)** | The chargeback is itself reversed: $300 goes back to Riverbend Hospital on 7/15 (p3). | **p3 counteracts p2** — the same kind, applied to a different pair | **no transitivity**: p3 counteracts p1 is not derived; p1's standing is not computed |
| **A5** | One refund cheque of $130 covers two purchases (p1 $84, p4 $46). | **two claims**: p5 counteracts p1; p5 counteracts p4 | no cardinality: a counteracting payment may counteract several |
| **A6** | Two partial refunds of one purchase: $120 on 6/9 (p2), $180 on 6/20 (p6). | two claims: p2 counteracts p1; p6 counteracts p1 | nothing sums them; "fully refunded" is a consumer's |
| **A7** | The refund lands on **Kim's** card, not Rob's (the card was replaced). | p2's payee is Kim (a claim on p2); **p2 counteracts p1** still | the relation does **not** require p2's payee = p1's payer — the over-specified wording is dead for a structural reason, not only a stylistic one |
| **A8 (Rv9)** | The bank line reads `REFUND MERCY 300.00`; the matcher pairs it with p1. | if no p2 is minted: a proposition from a capture concerning nothing established; if p2 is minted: a **reading-sourced candidate** *p2 counteracts p1* | the matcher establishes nothing; the word establishes nothing; no payment is minted from the line |
| **A9** | Rob: *the $84 was for the cushion* (p1); Kim: *no, it was for the brace* (p4). | two claims: p2 counteracts p1 (Rob); p2 counteracts p4 (Kim) — **contested, derived** | nothing chooses; no "current attribution" |
| **A10** | Rob later: *I was wrong — the $84 wasn't for the cushion.* | `utterance_retraction` of the utterance behind the relation claim; a new relation claim if he has one | p1, p2 untouched; the relation claim's history survives |
| **A11** | Goodwill: Riverbend Hospital credits $350 against a $300 charge. | p2 counteracts p1 | the relation validates no amounts; "over-refunded" is a consumer's reading |
| **A12 (Rv3)** | The ACH bounces — one failed payment, no second movement individuated. | a dated claim about p (*returned 3/5*), **not a relation** | pass A does not reach for it; nothing forces a second payment |
| **A13** | The direction: could *p1 counteracts p2* be asserted for Rv1? | the claim is directional — the counteracting payment is the subject; asserting the reverse is asserting something else | **direction is not derived from dates**: a party asserts which counteracts which |
| **A14** | *Refund* vs *chargeback* vs *return* vs *dispute credit*. | who initiated, and why, are claims about p2 (its payer, its cause) or content | **not kinds**: they do not differ in what is claimed *of the relation*, who can establish it, its direction or its participants — the stopping rule applied within one pass |

### A.3 Testing the readings

**PA1 — one ruled kind with two payment participants**, meaning exactly *the asserting party holds
that the subject payment economically counteracts some or all of the object payment*. Every case
is representable; every "must not follow" is a non-derivation the substrate already refuses.

**PA2 — a claim about p1 with p2 in content** (*p1 was refunded on 6/9 by that $300 credit*).
Rejected by ruled doctrine: the hidden-operand mistake (K8); A5, A6, A9 become indistinguishable
or unstatable; `proposition_concerns` cannot reach p2.

**PA3 — one generic kind `payment_relation` with the relation named in content** (`refund`,
`chargeback`, `partial`…). Rejected: prohibition 1 (name ≠ semantics) and 4 (the bank's label in
content becomes the relation); per-kind slot, direction and knowing rules become impossible; it
is the "convenient generic abstraction" arriving first.

**PA4 — several kinds by context** (`payment_refunds`, `payment_chargeback`, …). Tested by the
stopping rule inside the pass (A14): the contexts differ in **who initiated and why** — claims
about p2 — not in what is claimed of the relation, who may establish it, its direction or its
participants. Several kinds would encode the initiator into the relation, which prohibition 1
forbids and A7 shows is not even a stable property. One kind survives; the context is content or
separate claims.

**PA5 — correspondence, or about-ness.** Rejected by ruling: two events, never one referent; no
document.

**PA6 — derive it** (same amount, same counterparty, opposite direction ⇒ related). Rejected:
prohibitions 4 and 11; A7 and A11 show the heuristic is false; the matcher yields reading-sourced
candidates only (A8).

### A.4 What the relation is — and is not

| The claim | *the subject payment economically counteracts some or all of the object payment*, as the asserting party holds |
|---|---|
| **participants** | subject: the counteracting payment · object: the counteracted payment — both **established** payments; no other slot |
| **direction** | directional; **not symmetric**; **no inverse kind** — *p1 was counteracted by p2* is the same claim read backwards |
| **cardinality** | none ruled: many-to-many (A5, A6) |
| **who establishes** | any party's assertion — the household, the issuer of the counteracting payment; a reading yields **candidates only**; no label establishes |
| **knowing** | `relational_knowing` **True with no designated relation → `undetermined`** — the designated participant would be *the payer of the subject payment*, a role kind not ruled (item 6-F territory and the catalogue's) |
| **content** | opaque — the party's wording, the portion, the reason; never read by a derivation |
| **`as_of`** | permitted (the date the stance is about); the payments carry their own dates as claims |
| **derives** | **nothing**: no net, no effective amount, no discharge, no `reversed` status, no transitivity (A4), no amount validation (A11), no party mirroring (A7), no temporal continuity |
| **relation to reversal (C)** | the *later payment + relation* leg of REVERSAL §8; the *claim about p* legs (Rv3, Rv5, Rv6) are untouched and are not this kind |
| **name** | a working name is needed for a kind; **not** a source word (*reversal*, *refund*, *return*): `payment_counteracts` — the name carries no semantics beyond this table |

### A.5 Ruling candidate — pass A, for Rob

> **The payment-to-payment relation is one ruled kind, `payment_counteracts`, meaning exactly:
> the asserting party holds that the subject payment economically counteracts some or all of
> the object payment. Both participants are established payments; the claim is directional and
> never symmetric; no inverse kind exists; no cardinality is implied — a payment may counteract
> several and be counteracted by several. It is established only by a party's assertion; a
> reading, a matcher or a bank's label yields at most a candidate. Knowing for it is
> undetermined until a role designates the payer of the counteracting payment. It derives
> nothing: no net or remaining amount, no discharge, no status on either payment, no
> transitivity across a chain, no validation of amounts, no requirement that the counteracting
> payment's payee be the counteracted payment's payer, and no temporal continuity. Refund,
> chargeback, return, partial and goodwill are content or separate claims about the
> counteracting payment, never kinds. Where no second payment is individuated there is no
> relation — a failed, returned, unapplied or voided payment remains a dated claim about the
> one payment. Nothing is merged and nothing is minted by the claim.**

**If ruled, the representation is one registry entry** — `PAYMENT_COUNTERACTS: subject
(subject_payment_id) · object (object_payment_id) · symmetric False · reading_establishes False ·
relational_knowing True, no knowing_relation` — a fixture over A1–A14 and the absences (no
`reversed` column or accessor, no netting, no transitivity, no inverse kind), **no schema, no
migration**; and **nothing at family level** — pass B opens only after this is ruled.

*The line: the second payment is a payment; that it undid the first is what someone said about
the two of them — and the ledger's arithmetic waits for item 7.*

### A.6 Ruling — Rob, 2026-09-15: PA1 / `payment_counteracts` accepted as written

*No remaining semantic defect requires another case. A7 makes the candidate substantially stronger
than the earlier reversal wording — the replacement-card case makes the payer-based formulation
structurally wrong.*

**The operative definition is sound:** `payment_counteracts` means the asserting party holds that
the subject payment economically counteracts some or all of the object payment. The important
parts are the boundaries: both endpoints are Payment identities and the relation cannot
manufacture either · subject / object are semantically meaningful — the counteracting payment is
the subject · directional, not symmetric, no manufactured inverse · no cardinality · no
payer / payee mirroring (A7) · **the relation carries no amount — "some or all" is the semantic
scope of the assertion, not a numeric field or calculation** · refund / chargeback / return /
goodwill are not relation kinds — they describe the payment or the circumstances asserted around
it · a matcher discovers a candidate and cannot establish · a bank's `REFUND` label cannot
establish · no transitivity · no payment status · no netting or remaining (item 7) · no temporal
semantics from RP2 · retraction remains retraction · **no relation where there is no second
Payment identity** — the reversal ruling preserved for bounced / void / unapplied cases.

**One particularly important acceptance:** `relational_knowing = True` with no
`knowing_relation`, so knowing remains `undetermined` — the relation is semantically ruled, but
the participant whose relationship would constitute knowing (the payer of the subject payment)
has not been given role semantics; pass A does not reach forward and invent them.

**Representation authorised, for this relation only:**

```text
PAYMENT_COUNTERACTS
    subject: subject_payment_id
    object:  object_payment_id
    symmetric: false
    reading_establishes: false
    relational_knowing: true
    knowing_relation: none
```

No schema change · no migration · no family abstraction. The distinction preserved:
**Payment** → identity · **payment facts** → amount / date / payer / payee as propositions ·
**`payment_counteracts`** → an assertion relating two established Payments · **item 7** →
whatever consumers can legitimately derive. The implementation may not introduce a generic
relation base, a relation resolver, an inverse accessor, a counteracted status, a netting helper,
or any item 7 consumer.

**Pass A: RULED / CLOSED on build.** Then — and only then — pass B: Obligation ↔ Obligation.

