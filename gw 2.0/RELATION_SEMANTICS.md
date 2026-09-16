# Relation semantics — item 6, opened not as "design the relation family"

> Status: **Queue item 6, opened by Rob 2026-09-14. Pass A RULED (§A.6), built (`63848fa`). Pass B RULED (§B.7), built (`c0215a6`), ACCEPTED (§B.8). Pass C RULED (§C.9), built, smoke-reviewed and CLOSED. Pass D RULED (§D.9), built (`ef04ddb`), ACCEPTED (§D.10). Pass D′ OPENED 2026-09-15 by Rob as a semantic pressure test — shared-X convergence refused on every row (§D′.2), `toward` interrogated and rejected as the kind (§D′.3), a finding on the acknowledgment shape (§D′.4), candidate `payment_in_respect_of_obligation` (§D′.8); RULED (§D′.9), build AUTHORISED (§D′.10), built (`cf107e8`), assessed (§D′.11). Pass E OPENED 2026-09-15 by Rob — the coverage magnet interrogated (§E.2), three pairings each forced by its own case (§E.3), candidate three kinds `expense_ / obligation_ / payment_in_respect_of_plan` (§E.8), tightened (§E.9), ACCEPTED as written at `54a24a3` (§E.10), unbuilt by instruction. Pass F OPENED 2026-09-15 by Rob as the recorded order's next move — the meaning of covered-under ruled before the relation (§F.2), a party ↔ plan role with RP2's boundary kinds bound for the first time (§F.3–F.4), candidate `under_plan` + `_began` / `_ended` (§F.8), tightened after Rob's review (§F.9: the structural floor, F5 as an evidence boundary, the name, F20), no code; awaiting Rob's ruling. G remains; D′.11 stays an open constraint.** Items 1–5 are
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

---

## Pass B — Obligation ↔ Obligation

**The question, applied:** when a household member says *the new loan replaced the Harbor
mortgage*, *they rolled my hospital bill into a payment plan*, *the consolidation loan paid off
the three cards*, or *NewCo took over my loan*, what is being claimed, who can establish it, and
what follows? Rob's framing carried from §2: *one ending and another beginning · one continuing
with changed terms · a refinancing · a transfer of servicing · merely a new dated stance* — none
collapsed because an institution says "restructured"; **first determine whether there is an
obligation-to-obligation relation at all.**

### B.1 What is already fixed

| Ruling | Constraint on pass B |
|---|---|
| **Obligation identity** (§9) | *an obligation is a continuant minted by the household's individuating assertion*; creditor, amount, kind, terms, account number, entitlement, obligor, servicer, balance are **information about the continuant**; the identity **survives assignment, sale, write-off, recourse and restructure because none of those touches the anchor**; the minting act is not the minted identity |
| **Ob6** | restructure is *either* the same O with new terms (terms claims with `as_of`) *or* a new O that settled the old (O3 minted by the household + a relation between O3 and O1, kind not ruled) — **the household says which (C9); both must be representable** |
| **M1 / M2 — closed** (`CARRIES_DOCTRINE_TEST.md` §6) | the obligation is the continuant; *both cases are expressible as continuity of the obligation across change*; **no hidden identity/successor problem**; agreement identity (M2's object) *not needed by any case* — nothing forecloses it, nothing requires it |
| **Servicing** (S1–S7, frozen) | assignment, sale, a new servicer, a new account number, a recourse return: **one obligation, dated role claims** — *NewCo is E of O1 as of d*, *S services O1 as of d*; **payment state may evidence but never establish a change of carrier** (§10) |
| **Role period** (RP2) | `began` / `ended` are boundary kinds **bound to role kinds**; a boundary never rewrites, implies its opposite, resolves or establishes continuous effect — an obligation is not a role, so RP2 supplies pass B nothing |
| **Economic-transfer invariant** (§5) | *whenever economic terms change, every amount whose treatment changes must have an explicit, reconstructable disposition*; the anchoring decides only **where** it is represented — under the identity ruling, *a claim on whichever the household asserted*; **the disposition is not this pass's** (OBLIGATION_IDENTITY §7: ruled when the invariant's consumer is built) |
| **Disposition vocabulary** (case 3, case 6) | arrears are **not an amount** but a schedule-relative position; partial settlement is not a value — nothing here gives a relation an amount to carry |
| **Discharge** (S1) | *established by the entitled party's acknowledgment, not by the payee* — and not by anything else |
| **Correspondence** (Ob7) | `obligation_corresponds` = **one obligation minted twice**; a new obligation is never one referent with the old; a matching creditor or account number is a *candidate* for correspondence, and the household says whether it is Ob7 or Ob6 |
| **Pass A** | the precedent: one kind, two established participants, directional, no inverse, no cardinality, party-asserted, **no amount**, derives nothing; source words are content, not kinds |
| **`toward(p, O)`** | a **stand-in** (D′, unruled) — usable in a case as what the payoff payment is *claimed toward*, never as something this pass rules |
| **K8** | a referential operand is a participant: *O3 replaced (O1)* with O1 in content is the hidden-operand mistake |
| **Prohibitions 1–12** | §1 |

### B.2 The five phenomena, first — is there a relation at all?

Rob's five, taken one at a time against what is already ruled, *before* any case is written:

| Phenomenon | What it is, under the rulings | Obligation ↔ obligation? |
|---|---|---|
| **one continuing with changed terms** | terms claims about **one O**, `as_of` the effective date, the earlier terms remaining (Ob6 first arm) | **no** — one participant |
| **a transfer of servicing** (and assignment, sale, recourse) | dated **role claims** about one O (S2, S4/S5, S7); a new account number is a descriptor in content | **no** — one participant; an institution's "your new account" mints nothing |
| **merely a new dated stance** | a claim about one O at d — E's balance, a write-off, the household's *I consider this closed* | **no** — one participant |
| **one ending and another beginning** | *two independent facts*: the ending of O1 is a claim about O1 (E's acknowledgment of discharge; the household's stance); the beginning of O3 is the household's minting assertion — **neither establishes the other**; a third thing may be asserted *between* them, and only that third thing is two-participant | **only if asserted** — and then it is the row below |
| **a refinancing** (consolidation, rollover, balance transfer, a plan replacing a bill) | O3 minted by the household; a **payment** from the new lender to the old (payer may be anyone, Pm9; *toward O1* as a stand-in); E's acknowledgment of O1's discharge (D4/D5); and the household's assertion that **O3 was taken on in place of O1** — the last is a claim whose referential operands are two obligations | **yes — one relation**, and it is exactly the third thing in the row above |

**So: four of the five are not obligation-to-obligation at all, and the fifth is one claim.** The
relation exists because the household says something that has two obligations as its
operands — *this one was incurred in substitution for that one* — and K8 forbids recording it as a
claim about the new obligation with the old in content. It does **not** exist because a
restructure "creates a successor" (M2, closed), because RP2 can now say `ended` (roles only), or
because an institution's product has a name. Everything the relation might be tempted to say
*about either obligation* — ended, discharged, closed, carried, netted — is either a claim of a
different shape on one obligation or item 7's.

### B.3 The cases

| # | Case | What must be sayable | What must not follow |
|---|---|---|---|
| **B1 (Ob6, first arm)** | Harbor modifies the mortgage: new rate, new payment; Rob: *same mortgage, new terms*. | terms claims on **O1** with `as_of` the effective date; the earlier terms remain | no O3; the modification agreement (an artefact from Harbor) mints nothing; no relation — one participant |
| **B2 (Ob6, second arm)** | Riverbend Hospital closes the $3,000 plan and opens a new one at $250/month; Rob: *they closed the old plan and started a new one*. | Rob mints **O3**; **O3 replaces O1** — a claim with two obligation participants, asserted by Rob | O1 acquires no `closed` / `replaced` status; O1's discharge is not derived from the relation; the household's choice of the second arm is not second-guessed by the substrate |
| **B3** | Refinance with a different lender: NewBank pays Harbor $178,412; Harbor sends a paid-in-full letter; Rob: *the NewBank loan replaced the Harbor mortgage*. | **four separate things**: O3 minted (Rob); a payment p — payer NewBank, payee Harbor, *toward O1* (stand-in), asserted by Rob; Harbor's letter → a reading → E's acknowledgment claims about O1; **O3 replaces O1** (Rob) | the payment does not establish the relation; the relation does not establish the discharge; the letter mints nothing; the relation is not `toward`, not acknowledgment, not correspondence |
| **B4** | Consolidation: one personal loan pays off three cards. | three claims: **O4 replaces O1 · O4 replaces O2 · O4 replaces O3** | no cardinality; nothing sums the three; "consolidation" is not a kind |
| **B5** | Partial: the consolidation loan covers $5,000 of an $8,000 card; the card stays open. | **O4 replaces O1** — the relation's scope is *some or all*, as the party's assertion | the relation carries **no amount**; "$3,000 remains on O1" is a consumer's (item 7); O1 continues, un-statused |
| **B6** | Split: the hospital separates one bill into a facility plan and a physician plan. | two claims: **O2 replaces O1 · O3 replaces O1** | many-to-many with B4; nothing apportions O1 between them |
| **B7 (case 3)** | $525 behind on the old plan; the new plan is $250/month. | B1 or B2, **the household says which**; the $525 is a schedule-relative position under the old terms, reconstructable (8.1-a) | the relation does not carry *$525 rolled in*; the invariant's disposition (8.1-b) is a **separate claim of a different shape**, fenced to the invariant's consumer — not a field on this kind |
| **B8 (S2 / S4 / S5 / S7)** | Harbor sells the mortgage to NewCo; NewCo issues a new account number and a welcome letter: *your new NewCo loan*. | **one O1**; *NewCo is E of O1 as of d* (D7); the account number is content | **no relation** — one participant; NewCo's word mints nothing and relates nothing; if the household nonetheless mints O2 for "the NewCo loan", that is **Ob7** — `obligation_corresponds` on the household's say-so — not this kind |
| **B9** | NewBank's statement shows a first payment on a loan whose amount equals Harbor's payoff; the matcher pairs them; the closing disclosure reads `PAYOFF — HARBOR ****4471`. | a **reading-sourced candidate** *O3 replaces O1* (if O3 exists); a proposition concerning nothing established (if it does not) | the matcher establishes nothing; `PAYOFF` establishes nothing; no obligation is minted from a statement |
| **B10** | Direction: could *O1 replaces O3* be asserted for B3? | the claim is directional — **the replacing obligation is the subject**; asserting the reverse asserts something else | **direction is not derived from minting order or dates** — O1 may be minted in Groundwork *after* O3 (Ob9-style late recording); a party asserts which replaced which |
| **B11** | Chain: O3 replaced O1 (2020); O5 replaced O3 (2024). | two claims, same kind, different pairs | **no transitivity**: *O5 replaces O1* is not derived; O1's standing is not computed |
| **B12** | Rob: *the new loan replaced the mortgage*; Kim: *no — it replaced the HELOC*. | two claims: O3 replaces O1 (Rob); O3 replaces O2 (Kim) — **contested, derived** | nothing chooses; no "current successor" |
| **B13** | Rob later: *I was wrong — the loan didn't pay off that card.* | `utterance_retraction` of the utterance behind the relation claim; a new relation claim if he has one | O1, O4 untouched; the relation claim's history survives; retraction ≠ the card being "restored" |
| **B14** | Rob pays off the card and closes it. No second obligation. | a dated claim about O1 — E's acknowledgment of discharge, or Rob's *closed* stance | **not a relation** — pass B does not reach for it; an ending needs no successor, and no successor is manufactured for it (the A12 shape) |
| **B15** | O3 replaces O1 is asserted; the payoff was $40 short and Harbor keeps billing O1. | Harbor's D5 balance claims on O1 stand beside the relation; both are true as asserted | the relation **does not derive O1's ending** — this is the structural reason, not a stylistic one (A7's role in pass A): a status derived from the relation would contradict E's acknowledged balance |
| **B16** | NewBank (an institution) asserts, in its own words, that the proceeds paid off the Harbor loan. | NewBank **may assert** the relation as a party; from a reading it is a candidate; the household may assert it | knowing for the relation is **not ruled** — `undetermined`; the participant whose relationship would constitute knowing (the obligor of the subject obligation? E of the object?) has no ruled role kind |
| **B17** | *Refinance* vs *consolidation* vs *restructure* vs *rollover* vs *modification* vs *balance transfer* vs *payment plan*. | the product, who initiated, why, and the terms are claims about O3 (its kind, its creditor, its terms) or content | **not kinds**: they do not differ in what is claimed *of the relation*, who can establish it, its direction or its participants — the stopping rule inside one pass (A14's shape); *modification* is B1, not this kind at all |
| **B18** | A hospital bill becomes a payment plan: is the plan a new obligation replacing the bill's, or terms on the same one? | **the household says which** (Ob6 / C9); if a new O, B2 | the substrate never infers the arm from the creditor being the same; pass C (obligation ↔ expense, Ex4) is not reached for — what the *expense* is to either obligation is C's |

### B.4 Testing the readings

**PB0 — no obligation-to-obligation relation; everything is one-participant claims.** Tested
honestly first, because Rob's framing asks it. It holds for four of the five phenomena (§B.2) and
fails on the fifth by K8: *O3 was incurred in place of O1* has two referential operands, and
recording it as a claim about O3 with O1 in content makes B4, B6 and B12 indistinguishable or
unstatable. Ob6's second arm — *both must be representable* — is not representable under PB0.

**PB1 — one ruled kind with two obligation participants**, meaning exactly *the asserting party
holds that the subject obligation was incurred in substitution for some or all of the object
obligation*. Every case is representable; every "must not follow" is a non-derivation the
substrate already refuses; B1, B8, B14 are correctly *outside* it.

**PB2 — a claim about the new obligation with the old in content.** Rejected by K8, as in PA2.

**PB3 — one generic `obligation_relation` with the relation named in content** (`refinance`,
`consolidation`, `restructure`…). Rejected: prohibitions 1 and 4; the generic abstraction
arriving first.

**PB4 — several kinds by context** (`obligation_refinances`, `obligation_consolidates`,
`obligation_rolls_into`, `obligation_transfers_balance`…). Tested by the stopping rule inside
the pass (B17): the contexts differ in **product, initiator and reason** — claims about O3 or
content — not in what is claimed of the relation, who may establish it, its direction or its
participants. One kind survives.

**PB5 — correspondence.** Rejected by ruling: a new obligation is never one referent with the
old. B8 is the important boundary — the *same* obligation under a new account number is Ob7
(`obligation_corresponds`), and the household, not the matcher, says whether a new number is a
new obligation.

**PB6 — derive it** (O1's balance reaches zero as O3 appears with a matching amount ⇒ replaced).
Rejected: prohibitions 4 and 11; §10 — *payment state may evidence but never establish*; B15
shows the heuristic is false; the matcher yields candidates only (B9).

**PB7 — succession as identity** (O1 ends, O3 begins, the edge carries the disposition — M2's
shape re-entering as a relation). Rejected: M1/M2 is closed; the obligation is the continuant; a
relation cannot end an identity (prohibitions 5–7); the disposition lives on claims, not on an
edge (§5, as the identity ruling placed it). B15 is the case that makes this structural.

**PB8 — an `ended` boundary on the obligation via RP2.** Rejected: RP2's boundary kinds are
bound to *role* kinds; an obligation is not a role; and the ending of an obligation is E's
acknowledgment or the household's stance about O1 — never a consequence of a relation to O3
(prohibition 10).

### B.5 What the relation is — and is not

| The claim | *the subject obligation was incurred in substitution for some or all of the object obligation*, as the asserting party holds |
|---|---|
| **participants** | subject: the replacing obligation · object: the replaced obligation — both **established** obligations; no other slot |
| **direction** | directional; **not symmetric**; **no inverse kind** — *O1 was replaced by O3* is the same claim read backwards |
| **cardinality** | none ruled: many-to-many (B4, B6) |
| **who establishes** | any party's assertion — the household, the new lender; a reading yields **candidates only**; no label (`PAYOFF`, `REFINANCE`, *your new account*) establishes |
| **knowing** | `relational_knowing` **True with no designated relation → `undetermined`** — the designated participant (obligor of the subject? entitled party of the object?) is a role kind not ruled |
| **content** | opaque — the party's wording, the product, the reason, the portion; never read by a derivation |
| **`as_of`** | permitted (the date the stance is about); each obligation's terms and boundaries are its own claims |
| **derives** | **nothing**: no ending, discharge, closed or replaced status on the object (B15); no beginning on the subject (it was minted, not begun); no disposition of any amount across the pair (B7 — the invariant's consumer); no remaining (B5); no transitivity (B11); no apportionment (B6); no temporal continuity; no inference of the Ob6 arm |
| **what it is not** | not terms (B1); not a role claim (B8); not correspondence (B8, Ob7); not `toward` (B3's payment); not acknowledgment (B3's letter); not an RP2 boundary (PB8); not a successor identity (PB7) |
| **relation to Ob6** | the *second arm's* relation, now ruled; the first arm needs no relation; **the household's choice between the arms is a fact the substrate records, never infers** |
| **name** | a working name is needed for a kind; **not** a source word (*refinance*, *restructure*, *consolidate*, *supersede* — the last is artefact vocabulary): `obligation_replaces` — the name carries no semantics beyond this table |

### B.6 Ruling candidate — pass B, for Rob

> **There is exactly one obligation-to-obligation relation, and it is needed for exactly one of
> the five phenomena. Changed terms are claims on one obligation; a transfer of servicing,
> assignment, sale or recourse is a dated role claim on one obligation; a new dated stance is a
> claim on one obligation; an ending and a beginning are two independent facts about two
> obligations that establish nothing about each other. The relation is the household's — or any
> party's — assertion that one obligation was incurred in substitution for some or all of
> another: one ruled kind, `obligation_replaces`, meaning exactly that the asserting party holds
> the subject obligation was incurred in substitution for some or all of the object obligation.
> Both participants are established obligations; the claim is directional and never symmetric;
> no inverse kind exists; no cardinality is implied — one obligation may replace several and be
> replaced by several. It is established only by a party's assertion; a reading, a matcher, a
> payoff line or an institution's product name yields at most a candidate. Knowing for it is
> undetermined until a role designates the relevant participant. It derives nothing: no ending,
> discharge or status on the replaced obligation, no beginning on the replacing one, no
> disposition of any amount across the pair, no remaining, no transitivity across a chain, no
> apportionment among several, no temporal continuity, and no inference of which Ob6 arm the
> household meant. Refinance, consolidation, rollover, balance transfer, restructure and payment
> plan are content or claims about the replacing obligation, never kinds; modification is the
> first arm and no relation at all. Where no second obligation is individuated there is no
> relation — a paid-off, closed, written-off or transferred obligation remains one obligation
> under dated claims. The disposition the economic-transfer invariant requires is a claim of its
> own shape, fenced to that invariant's consumer, and is not carried by this kind. Nothing is
> merged and nothing is minted by the claim.**

**If ruled, the representation is one registry entry** — `OBLIGATION_REPLACES: subject
(subject_obligation_id) · object (object_obligation_id) · symmetric False · reading_establishes
False · relational_knowing True, no knowing_relation` — the obligation slots already exist, the
generalised reflexive guard already covers it; a fixture over B1–B18 and the absences (no
`closed` / `replaced` column or accessor, no discharge derived, no disposition field, no
transitivity, no inverse kind, no Ob6-arm inference); **no schema, no migration**; and **nothing
at family level** — pass C opens only after this is ruled.

**What pass B leaves exactly where it found it:** the invariant's disposition claim (8.1-b) ·
discharge and `remaining` (item 7) · agreement identity (M2's object — still unforced) · the
write-off's unnamed residue · the role catalogue (obligor, E, servicer as ruled kinds) · pass C's
question of what the *expense* is to either obligation (B18) · D′ (`toward`, still a stand-in in
B3).

*The line: the new loan is a loan; that it took the old one's place is what someone said about
the two of them — and whether the old one is really gone is what its creditor says.*

### B.7 Ruling — Rob, 2026-09-15: PB1 / `obligation_replaces` accepted as written

*No semantic defect warrants another case before the ruling.*

**"In substitution for" survives — the right level of abstraction.** It says **why the subject
obligation exists in relation to the old obligation**, not what happened afterward to the old
obligation. O2 can be incurred in substitution for O1 while O1 remains outstanding · while O1 is
later discharged · while O1 is disputed, partially paid or never actually discharged · even if the
economic amount differs. So substitution does **not** require *O2 replaces O1 → O1 ended*, and it
must not acquire that implication downstream. Pinned explicitly, in the record and the fixture:
**"in substitution for" is not itself a temporal or lifecycle assertion** — B15 carries it.

**The economic-transfer claim stays out — the place to resist expanding the pass.** Two
propositions that are easy to collapse are kept separate: *O2 was incurred in substitution for O1*
and *some economic position associated with O1 was transferred / reallocated into O2*. They are not
the same claim. The second has its own unresolved questions — what exactly is transferred (an
amount, an obligation position, a funding allocation, something else) · who can assert it · its
operands · its cardinality · whether it survives partial payoff · whether it implies anything about
O1's balance — and none of them is `obligation_replaces`'s to answer merely because refinance is a
common context. **8.1-b is retained exactly as a fence, not treated as an implementation hole.**
The invariant: **`obligation_replaces` does not explain where money went.** A good absence.

**Knowing: not forced.** An important demonstration that the relational-knowing ruling is working.
For `payment_counteracts` the candidate participant was relatively obvious; here both candidates
show a problem — *obligor of the subject* is plausible in some refinances but not necessarily the
party establishing the claim; *E / obligor of the object* is plausible but not semantically forced.
*The party that incurred O2 knows O2 replaced O1* would quietly turn **participation / agency in
the obligation into an epistemic rule** that has not been established; *the party responsible for
O1 knows O2 replaced it* would manufacture knowledge from the object's role. Neither follows from
the relation. `relational_knowing = True` with no `knowing_relation` → `undetermined` is exactly the
correct stopping point.

**The more important result of pass B is §B.2.** The pass did not start from *what relations
might obligations have?* — it started from the phenomena and discovered that most of them **are not
relations**, which is exactly what the item 6 fence was meant to accomplish:

| Phenomenon | Ontological result |
|---|---|
| changed terms | claims about one O |
| servicing / assignment / sale / recourse | role claims about one O |
| new dated stance | claim about one O |
| end + beginning | independent boundary claims |
| refinance / consolidation / substitution | **O → O relation** |

`obligation_replaces` is a **narrow residue**, not a turning of every lifecycle phenomenon into an
O ↔ O relation. **Preserve that reasoning at implementation** — otherwise a future engineer will
look at RP2 and say *obligations have beginnings and endings, therefore they need succession
relations*; the cases already show why that does not follow.

**B15 is especially important.** O2 incurred in substitution for O1 · the payoff $40 short · Harbor
continues billing O1: the relation cannot manufacture an `ended`, `settled` or `discharged`
interpretation. *O2 replaces O1* · *O1 still has an acknowledged balance* · *O1 has not been
discharged* stand simultaneously. It blocks the shortcut **replacement → termination**, which
would otherwise be incredibly easy for a consumer to encode.

**Wording kept:** *some or all of the object obligation* — it means the relation encodes no amount
and presumes no complete replacement; not tightened to *the object obligation* or *the entire
object obligation*. No *financially*, *legally*, *fully*, *substantially*, *formally* — each would
introduce semantics that belong somewhere else.

**The semantic contract, frozen:**

> **`obligation_replaces`: the asserting party holds that the subject obligation was incurred in
> substitution for some or all of the object obligation.**

subject = established Obligation · object = established Obligation · directional · not symmetric ·
no inverse · no cardinality · any party may assert · reading / matcher / source vocabulary cannot
establish it · content opaque · `as_of` may date the assertion · no amount semantics · no transfer
semantics · no discharge / settlement semantics · no lifecycle implication · no status derivation ·
no transitivity · no temporal continuity · no automatic party / role mirroring · relational knowing
**undetermined** · no consumer yet.

**Representation authorised, for this relation only:**

```text
OBLIGATION_REPLACES
    subject: subject_obligation_id
    object:  object_obligation_id
    symmetric: false
    reading_establishes: false
    relational_knowing: true
    knowing_relation: none
```

No schema work · no economic-transfer relation · no resolver · no inverse accessor · no obligation
status · no family substrate. **Pass B: RULED / CLOSED on build.** The next semantic question is
**C**, not a reopening of the unresolved money-tracing claim.

#### Built — 2026-09-15

One registry entry exactly as authorised; the obligation slots already existed and the generalised
reflexive guard already covered the kind (its comment now names it). Fixture
`tests/test_obligation_replaces_fixture.py` (39 checks, B1–B18 and the absences: no
`closed` / `replaced` / `discharged` column or accessor, no discharge or disposition helper, no
inverse, no transitivity, no apportionment, no successor chain, no Ob6-arm inference, no boundary
kind bound to the relation, no relation table). Smoke `s102_obligation_replaces.py`, eight
mutations caught: the PAYOFF label establishes · the relation becomes an obligation status · the
inverse is manufactured · transitivity slips in · discharge is derived · a disposition helper
explains the money · **the Ob6 arm is inferred (a terms claim mints a successor)** · the kind turns
symmetric. Retired in place, truthfully: the obligation fixture's Ob6 check *"the relation between
O3 and O1 is NOT built — no kind for it exists"* → *ruled elsewhere as `obligation_replaces` and not
asserted here; the obligation slots carry only correspondence and replaces*. No schema, no
migration, no family abstraction. Gate 986 → 997, 0 failed.

### B.8 Build accepted and pass B closed — Rob, 2026-09-15. `c0215a6`, 997 green, clean tree.

*Faithful to the ruling; the smoke section attacks ways the semantic boundary could leak rather
than checking that the happy-path row can be inserted.*

**The ontology was not quietly widened — the strongest check is the absence surface:** no
`Relation` / `RelationBase` · no resolver · no inverse · no successor chain · no status · no
discharge · no disposition helper · no source-specific relation kinds · no schema change. The
registry is exactly the authorised contract, and the fixture records that knowing, disposition and
the consumers remain unbuilt rather than accidentally absent.

**B15 is the right adversarial test** — not merely *replacement doesn't imply `closed`* but the
stronger fact: **the replacement relation and a contradictory-looking balance position coexist
without the relation resolving either one.** Much harder for a future consumer to misread.

**B8 protects the identity / correspondence boundary:** sale + new account number does not become
replacement because the record looks new; the changed creditor is a role claim; a second obligation
exists only when the household mints one; *the same mortgage* is then `obligation_corresponds`.

**B18 may be the most valuable regression in the fixture:** *same bill, now on a plan* → terms
claim; *a new plan* → potentially a new obligation + replaces — and **the substrate does not decide
which arm the words imply; the household's individuation does.** The software does not get to
manufacture the user's identity decision from vocabulary.

**The eight mutations attack eight genuinely different failure modes** (label → assertion ·
relation → status · direction → inverse · chain → transitivity · relation → discharge · relation →
money disposition · terms → automatic successor · directional → symmetric), the baseline is
required green before mutation results count, and the module is restored and re-checked.

**One thing not to change — recorded so it is not "improved" later:** do **not** add a test that
`obligation_replaces` validates the subject was created later than the object. B10 demonstrates
the opposite: minting order does not establish direction; the replacing obligation may have an
identity created *before* the obligation it is later asserted to replace. Preserving that keeps
`created_at` from becoming accidental temporal ontology.

**Three things left fenced exactly where they are, and not a reason to reopen B:** knowing (no
designated epistemic role yet) · economic disposition / transfer (a separate relation, still
unruled) · discharge / remaining / status (consumer territory, not a property of replacement).

**The boundary for C, as Rob stated it:** *C should determine what it means for an Obligation to
stand in relation to an Expense — starting from Ex4's `arises_from` — without importing
`obligation_replaces`, payment tracing, plan semantics, or discharge into it.* Opened when Rob
opens it.

---

## Pass C — Obligation ↔ Expense

**The question, applied:** when a household member says *that's the ER visit — I owe Riverbend Hospital for
it*, *the CareCredit balance is for Kim's surgery*, or *the Riverbend Hospital statement covers the visit and
the follow-up*, what is being claimed, who can establish it, and what follows? Rob's framing
carried from §2 and §B.8: begin with Ex4's `arises_from`, **but do not assume that because Ex4
says an obligation arises from an expense, `arises_from` is already the correct semantic kind —
that is the candidate to interrogate, not the answer**; and import nothing from
`obligation_replaces`, payment tracing, plan semantics or discharge.

*Tightened 2026-09-15 after Rob's review (§C.8) — C is the first pass where the endpoint types
carry the direction, so the record must not establish by implication what the wording leaves
open.*

### C.1 What is already fixed

| Ruling | Constraint on pass C |
|---|---|
| **Expense identity** (X3, §8) | an event identity for an incurrence the household individuates; minted by the household's individuating assertion; *other parties may assert claims about it but do not thereby mint it*; date, provider, patient, nature, necessity, category and **every monetary amount** — billed · allowed · plan-paid · patient responsibility · household-paid — are claims about X |
| **Obligation identity** (§9) | a continuant minted by the household's individuating assertion; creditor, amount, kind, terms, balance are claims about O; **a bill mints nothing** (Ob2) |
| **Ex4** | *"that's the ER visit — I owe Riverbend Hospital for it"*: one act mints O and ties the bill to X; *O arises from X* is **a claim the §7.7 consumers need — its kind not ruled**; the expense fixture asserts it absent |
| **Ex5 / Ex6** | an expense with no obligation; an obligation with no expense — **neither endpoint requires the other** |
| **Ex7** | one visit, three bills: one X with three obligations — or three expenses; individuation is the household's; `expense_corresponds` repairs |
| **§7.7 classification** (frozen; consumers) | *classification describes the obligation by its financial terms and, where applicable, the nature of the underlying expense*; three facts consumed by different behaviours — instrument kind (C1/C2/C6) · **care necessity (C3, read off the underlying expense)** · terms (C4/C5); never a party; `Unknown` terminal; **not an ontology, no master label** |
| **Insurer's claim** (4b) | no identity; *patient responsibility $412* is **the insurer's dated stance about X** — a claim about the expense, not an obligation and not a relation; what the household calls "the claim" is the expense |
| **Payment identity / D′** | `toward(p, O)` a stand-in; a payment *for* X (Ex8) noted beside it — **pass D's**, not this pass's |
| **Plan identity §5** | Plan's existence answers nothing about coverage — **pass E/F's**; "covered" is not this pass's word |
| **About-ness** | `artefact_concerns(bill, X)`, `artefact_concerns(bill, O)`, `proposition_concerns(P, X)` — a document or a line concerns an identity; **neither O nor X is a document or a proposition** |
| **Correspondence** | within one type only; O and X are never one referent |
| **Role period** (RP2) | boundary kinds bound to *role* kinds; neither an obligation nor an expense is a role; X's occurrence is not a boundary of O |
| **Passes A / B** | the precedent: one kind, two established participants, party-asserted, no amount, derives nothing; source words are content; **direction was semantic in both because both participants were the same type** — to be re-tested here, not carried |
| **K8** | a referential operand is a participant: *I owe Riverbend Hospital for (the ER visit)* with X in content is the hidden-operand mistake |
| **Prohibitions 1–12** | §1 |

### C.2 Is there a relation at all — the pressure, one source at a time

| Where the pressure comes from | What it is, under the rulings | Obligation ↔ expense? |
|---|---|---|
| **Ex4, the household's sentence** — *I owe Riverbend Hospital for the ER visit* | a statement with **two referential operands** of different types: an obligation and an expense | **yes — if it is to be recorded at all**, K8 makes it a two-participant claim |
| **§7.7 C3** — care necessity read off the underlying expense | a *consumer's* need to reach X from O; it presupposes the tie, it does not define it | needs the relation to exist; **rules nothing about it** (prohibition 11) |
| **the EOB's patient responsibility** (Ex3, 4b) | the insurer's dated stance about X with an amount — *a claim about the expense*; O is minted only by the household (Ob2) | **no** — one participant (X); PR > 0 mints no O and relates none |
| **the bill concerns X; the bill concerns O** | two about-ness claims on one artefact | **no** — about-ness ≠ relation (prohibition 3); a document concerning two things does not relate them |
| **one utterance mints O and mentions X** (Ex4) | provenance — the minting act and the relation claim share an utterance | **no** — a relation is never derived from shared provenance; the utterance evidences two distinct claims |
| **Ex5 / Ex6** | an expense nobody owes for; a debt for nothing incurred | **no** — no second participant; the relation is optional at both ends |
| **a financing obligation for a service** — the CareCredit balance *for Kim's surgery* | the household's statement, two operands; the creditor is not the provider | the **same** claim as Ex4's, with a different instrument — a claim about O, not a different relation (C.4, PC5) |

**So: there is exactly one obligation-to-expense relation, and it is — once more — the fifth
thing: a party's statement whose referential operands are two identities.** It is not manufactured
by a bill, an EOB, a shared utterance, a patient-responsibility figure or a consumer's need.

### C.3 Interrogating `arises_from` — three defects, separately

Ex4's phrase was a placeholder for a claim the consumers need. Taken as *semantics*, its ordinary
relational reading carries three implications, each rejected on its own ground:

| Implication | What it would assert | Why it fails |
|---|---|---|
| **causal origin** | *O exists because X caused it* | stronger than Ex4 establishes — the household said what the debt is *for*, not why it exists; Groundwork cannot establish why an obligation exists, and a causal kind would be satisfiable only by inference, the shape §10 forbade for carrier transitions |
| **temporal origin** | *X precedes O* | **contradicted by a case, not merely a concern**: C7 — the pre-service deposit — has O minted before X is incurred; C7′ has the bill fourteen months after. The claim carries no order; the phrase does. B10's lesson in a new place: **the phrase must not supply a temporal ontology, and `created_at` on either anchor is not consulted** |
| **lifecycle origin** | *X begins O / O begins when X occurs* | prohibited by RP2 and prohibition 10: boundary kinds bind to role kinds; X's date of service is X's claim and is nobody's boundary; O has no beginning in the ontology beyond its minting |

**Conclusion (Rob's wording):** *`arises_from` is rejected because its ordinary relational
reading carries causal, temporal, or lifecycle-origin implications that are not established by
the household assertion and are contradicted or prohibited by the case set.* Not because the
phrase merely *sounds* causal. **C7 is the decisive anti-`arises_from` case** and is a permanent
regression. And it mis-reads the household: *I owe Riverbend Hospital for it* is not an origin story; it says
**what the debt is in respect of** — the whole of the claim. `arises_from` is rejected as the
semantic kind (PC2) and kept as what it was: Ex4's placeholder, now discharged.

### C.4 The cases

| # | Case | What must be sayable | What must not follow |
|---|---|---|---|
| **C1 (Ex4)** | Riverbend Hospital's bill for $412 arrives. Rob: *that's the ER visit — I owe Riverbend Hospital for it.* | **three things from one act**: the bill concerns X (`artefact_concerns`); O minted (Ob2); **O in respect of X** — a claim with two established participants, asserted by Rob | the relation is not derived from the shared utterance, from the bill concerning both, or from the EOB's $412; O's amount is O's claim |
| **C2 (Ex5)** | Kim's wellness visit: billed $250, plan paid $250, patient responsibility $0. | X; Lakeview Health's PR stance on X | **no O and no relation**; PR = $0 (or > $0) mints nothing |
| **C3 (Ex6)** | The mortgage. | O; its claims | **no X and no relation**; nothing manufactures an incurrence for a debt |
| **C4 (Ex7) — one expense, several obligations** | One surgery; Rob mints the Riverbend Hospital obligation, the radiologist's, the lab's — and the CareCredit balance he financed part of it with. | **four claims**: O1 in respect of X · O2 in respect of X · O3 in respect of X · O4 in respect of X | no cardinality is *ruled*, and the case shows why none could be: the four are not merged, not duplicates (the substrate derives no correspondence candidate from a shared expense — candidate generation stays fenced), no single creditor is inferred, nothing allocates X among them, nothing sums them to "what the surgery cost" |
| **C5 — one obligation, several expenses** | One Riverbend Hospital account statement, one balance; Rob: *that balance is the ER visit and the follow-up.* Rob mints one O. | **two claims**: O in respect of X1 · O in respect of X2 | **no allocation, no percentage, no amount split, no priority, no requirement that anything adds up, no determination that X1 and X2 jointly produced O**; "how much of the balance is the follow-up" is a consumer's — and *in respect of* asserts **no exclusivity**: being in respect of X1 says nothing against being in respect of X2 (§C.6) |
| **C6 — the relation is not a reconciliation operator** | Lakeview Health's EOB: patient responsibility $412 (a stance on X). Riverbend Hospital's statement: balance $450 (a stance on O). Riverbend Hospital's billed charge: $1,300 (a stance on X). | all three stances stand; the relation stands beside them | **three temptations, all absent**: *O's amount = X's amount* (billed, allowed or any other) · *O's amount = X's patient responsibility* · *O's amount = a residual derived from X's figures* (billed − plan-paid, allowed − plan-paid…); O's balance ≠ X's PR is not an error the substrate sees and not a permission to compute a "corresponding obligation amount"; the four determinations are item 7 |
| **C7** | *I owe Riverbend Hospital a $500 deposit for the surgery* — O minted from the pre-service estimate; the surgery happens next month; Rob individuates X afterwards and says the deposit was for it. | O minted first; X minted later; **O in respect of X** asserted then, `as_of` permitted | **no temporal order** — the relation does not require X to precede O; `created_at` on either anchor is not consulted; *arises from* would misdescribe this. **PERMANENT** |
| **C7′** | A radiology bill arrives fourteen months after the visit. | O minted; O in respect of X | no timing semantics; no "late" |
| **C8** | The CareCredit balance is for Kim's surgery (Synchrony is E; Riverbend Hospital provided). | **O in respect of X**, asserted by Rob; instrument kind *deferred-interest card* is a claim on O; provider Riverbend Hospital is a role claim on X | **no creditor / provider mirroring** — E of O need not be the provider of X (A7's role in this pass); the instrument does not change what O is in respect of |
| **C9 (pass B)** | The consolidation loan O5 replaces the CareCredit O4 (`obligation_replaces`). | O5 replaces O4 is one claim; O4 in respect of X is another | **no transitivity across kinds**: *O5 in respect of X* is not derived; Rob may assert it |
| **C10** | The EOB's reading yields *patient responsibility $412* with X as a candidates participant; Rob: *Lakeview Health's EOB for the ER visit* (`artefact_concerns`). No O yet. Later Rob mints O. | the P-world stance on X; the EOB concerns X; O minted by Rob | the EOB **mints no O and asserts no relation**; if a matcher pairs Riverbend Hospital's account number to the visit, that is a **reading-sourced candidate** for the relation, never the claim |
| **C11** | Riverbend Hospital's bill concerns X (Rob) and concerns O (Rob). | two `artefact_concerns` claims | **the relation is not derived** from a document concerning both — a statement can concern several identities without relating them |
| **C12** | Direction: is *X in respect of O* a different claim? | the participants are of different types: subject the obligation, object the expense, **fixed by type**; there is no second claim to read | **direction is not semantic here** — unlike A and B, where two same-type participants made *which is which* the meaning; the phrase *arises from* / *gave rise to* suggests a direction (cause, order) the claim does not carry. See C20 for what this does *not* license |
| **C13** | Rob: *the Riverbend Hospital balance is for the ER visit*; Kim: *no — it's for my follow-up.* | two claims: O in respect of X (Rob); O in respect of X′ (Kim) — **contested, derived** | nothing chooses; no "current attribution" |
| **C14 (Ex11)** | Rob later: *that bill wasn't for the ER — it was the follow-up on the 20th.* | `utterance_retraction` of the utterance behind the relation claim; a new relation claim to X′ | O, X, X′ untouched; the history survives |
| **C15** | Rob pays Riverbend Hospital $412 (a payment *toward* O — stand-in); Lakeview Health's plan "covered" the rest. | a payment claim toward O; a coverage stance about X by Lakeview Health | **the relation says nothing about payment, discharge or coverage**: paying O does not make X "paid" (pass D); *O in respect of X* does not make X covered or O's amount the patient responsibility (passes E/F) |
| **C16** | *Bill for* · *charge for* · *responsibility for* · *balance for* · *financed* · *arising from* · *on account of*. | content | **not kinds** — they differ in instrument, who billed, and phrasing: claims about O, or content; the stopping rule inside the pass (A14 / B17) |
| **C17 — endpoint, not projection** | Rob: *the ER visit was necessary care* (a nature claim on X); *it was on Feb 14* (a date claim on X); *Riverbend Hospital provided it* (a role claim on X). Lever protection (C3) wants to know whether O is protected. | the claims on X; O in respect of X; **a consumer may traverse the relation to reach X** | **two different statements, only the first legitimate**: (1) given O and a ruled *O in respect of X*, a consumer can identify X as an expense O is asserted to be in respect of — *by whom, and beside any competing assertion*; (2) the relation tells us the nature, necessity, date, provider or amount of O — **never**. *O in respect of X* does **not** make O medical, necessary, incurred on X's date, owed to X's provider, or equal to X's amount. Expense facts do not silently become obligation facts through the edge. C3's reading is item 7's, and it reads X, not O |
| **C18 — the semantic floor** | *The $450 Riverbend Hospital obligation is in respect of the February 14 ER expense.* | exactly that: O is asserted as being in respect of X | the relation has **no mechanism for choosing among interpretations**: it does not establish why $450 exists, that Riverbend Hospital's bill is correct, that Lakeview Health's $412 is correct, that all $450 is attributable to X, that O is legally enforceable because of X, that O is *the* payment obligation for X, or that O is the final responsibility for X. Any of those is a further claim by a party, or a consumer's reading |
| **C19 — provider standing** | Riverbend Hospital's statement: *for services 02/14*. Riverbend Hospital (a party) asserts *this balance is in respect of the visit*. | Riverbend Hospital **may assert the relation** — a claim with its own evidence; from a reading it is a candidate | **the standing rule**: *any party may assert the relation, provided both endpoints are already established; the party's ability to assert the relation establishes neither endpoint nor any property of either endpoint* — not X's identity, not O's, not Riverbend Hospital as creditor, not the amount, not the correctness of the bill. "Provider may assert" never becomes "provider establishes the debt" |
| **C20 — no inverse kind** | Could a kind with subject X and object O exist — *expense has obligation* · *expense generates* · *expense is owed*? | no: there is no reverse *claim* here (C12), so a kind with the slots swapped would be **a second relation needing its own ruling**, not this one read backwards | **no inverse kind** is manufactured; and none of the three named would be this claim in another order — each asserts something else (cause, entitlement, existence) |
| **C21 — traversal is not derivation** | A consumer wants "the underlying expense" of O for C3. | a **query over the established directed relation** — filter by `subject_obligation_id`, get every asserted X with its asserter, contested or not — is graph navigation and needs no accessor; it may run in either direction (from X to its obligations likewise) without that being an inverse kind | **a named accessor that presents as a fact** — `underlying_expense(O)` returning *one* X, choosing among several, silent about who asserted it — is a resolver and a derivation, and is not built; *the relation establishes no additional fact about the endpoint it reaches* |

### C.5 Testing the readings

**PC0 — no relation; O ↔ X is reached by inference** (the bill concerns both; the same utterance
minted O and mentioned X; the EOB's patient responsibility; matching amounts). Rejected:
prohibitions 3, 4, 11; Ob2 (nothing but the household mints O); C8 has no document concerning
both; C11 shows a document may concern two things without relating them; and K8 — Ex4's sentence
has two operands and PC0 cannot record it.

**PC1 — one ruled kind with an obligation subject and an expense object**, meaning exactly *the
asserting party holds that the subject obligation is in respect of the object expense* — with
the semantic floor of §C.6 and nothing above it. Every case is representable; every "must not
follow" is a non-derivation the substrate already refuses; C2, C3 and C11 are correctly *outside*
it.

**PC2 — `arises_from` as the ruled semantics** (O exists because of, and after, X). Rejected in
C.3 on three separate grounds; C7 is the counterexample.

**PC3 — a claim about O with X in content** (*O is for the ER visit*). Rejected by K8; C4, C5,
C13 become indistinguishable or unstatable; nothing can reach X from O for any consumer.

**PC4 — one generic `obligation_expense_relation` with the relation named in content.**
Rejected: prohibitions 1 and 4.

**PC5 — several kinds by context** (`obligation_bills_for`, `obligation_finances`,
`obligation_responsibility_for`…). Tested by the stopping rule inside the pass (C16): the
contexts differ in **instrument, who billed and phrasing** — claims about O, or content — not in
what is claimed of the relation, who may establish it, its participants or what follows. One
kind survives; C8 is the same claim as C1 with a different creditor.

**PC6 — about-ness** (treat O as something that "concerns" X). Rejected by ruling: `concerns`
takes a document or a proposition as its subject; an obligation is neither; and C11 shows the
about-ness claims exist *alongside* the relation without producing it.

**PC7 — fold it into the amount** (O minted from PR; O's amount = X's PR; the relation carries
a share). Rejected: Ob2; C6's three temptations; C5's allocation; the four determinations are
item 7; the relation carries no amount.

**PC8 — a classification of O** (*healthcare obligation* = an obligation carrying its expense).
Rejected by §7.7: nature is *read off the underlying expense*, not stored on the obligation;
instrument kind is the fact on O; the relation is what makes "the underlying expense" reachable
and is not itself a classification (C17).

### C.6 What the relation is — and is not

**The semantic floor, first.** The relation means only: **O is asserted as being in respect of
X.** It has no mechanism for choosing among the readings the phrase could be stretched to, and it
does **not** mean any of: *X caused O* · *X preceded O* · *X generated O* · *O is incurred because
of X* · *O is legally owed because of X* · *O is billed for X* (a claim about O, or content) · *O is
allocated to X* · *O is the payment obligation for X* · *O is the coverage responsibility for X* ·
*O's amount equals X's amount, X's patient responsibility, or any residual of X's figures* · *O is
exclusively in respect of X*. Each of those is a further claim by a party, a consumer's reading,
or another pass's relation. The floor is the relation; nothing above it is.

**"In whole or in part" — dropped.** Rob's challenge: the phrase opens an allocation door by
implying there *is* a part. It was borrowed from A and B, where *some or all* qualified a verb
(*counteracts*, *incurred in substitution for*) that would otherwise read as complete. *In
respect of* is not a verb of completeness and carries no exclusivity, so the qualifier added a
quantitative flavour without fencing anything the floor does not already fence. Multiplicity (C4,
C5) is carried by the absence of cardinality; the absence of a share is stated in the floor.

| The claim | *the subject obligation is in respect of the object expense*, as the asserting party holds — and nothing above the floor |
|---|---|
| **participants** | subject: the obligation · object: the expense — both **established**; no other slot |
| **direction** | **fixed by participant type, not by meaning** — there is no reverse claim to distinguish (C12); `symmetric` is false in the registry only because the slots differ in type; the kind carries **no directional semantics**; **no inverse kind** (C20); navigation in either direction is a query, not a relation (C21) |
| **cardinality** | none ruled — and C4 / C5 show none could be: many-to-many, no share, no exclusivity |
| **who establishes** | any party's assertion, **both endpoints already established** — the household, the provider (C19); the assertion establishes neither endpoint nor any property of either; a reading yields **candidates only**; no figure (the EOB's PR) and no label establishes |
| **knowing** | `relational_knowing` **True with no designated relation → `undetermined`** — the obligor of O? the party who incurred X? E of O? none is forced by the relation (B's restraint, again) |
| **content** | opaque — the party's wording, the portion, the instrument; never read by a derivation |
| **`as_of`** | permitted (the date the stance is about); O's and X's dates are their own claims |
| **derives** | **nothing**: no amount, share or reconciliation on either side (C5, C6); no temporal order (C7); no beginning or ending of O; no occurrence of X; no discharge, payment or "paid" (C15); no coverage (C15); no nature, necessity, date, provider or amount projected onto O (C17); no creditor / provider mirroring (C8); no transitivity across `obligation_replaces` (C9); no correspondence candidate between obligations sharing an expense (C4); no minting of either endpoint; no single "underlying expense" (C21) |
| **what it is not** | not the minting (C1); not about-ness (C11); not correspondence; not the insurer's stance on X (C10); not `toward` (C15); not a classification (C17); not cause, order or lifecycle (C.3); not a reconciliation operator (C6); not an inverse of anything (C20) |
| **relation to §7.7** | the edge through which a consumer *reaches* X from O; what it reads there — nature, necessity — it reads **of X**, and item 7 decides what it may then say of O; the relation grants it nothing |
| **name** | a working name is needed for a kind; **not** `arises_from` (C.3), not a source word (*bill*, *charge*, *responsibility*, *finance*): `obligation_in_respect_of` — the name carries no semantics beyond this table. (`obligation_owed_for` rejected: *owed* hints a status; `obligation_for` rejected: too bare to fence.) |

**For G — recorded now, in Rob's sharper terms.** The stopping-rule dimension C exposes is not
"directionality" as a registry flag but **participant typing and participant-role semantics**:
*does the relation's semantics distinguish endpoint roles independently of slot order?* In A and
B the slots are the same type and the kind's meaning is what tells the two payments (or
obligations) apart; in C the endpoint kinds themselves distinguish the roles and the relation
adds no role semantics. G must compare **what makes the participants semantically different**,
not registry flags — and three relations, two of which share a property the third lacks, is early
evidence *against* a common family.

### C.7 Ruling candidate — pass C, for Rob

> **There is exactly one obligation-to-expense relation, and it is a party's statement of what
> an obligation is in respect of — not why it exists, not when it began, not what it costs, and
> not what happened to it. `arises_from` is rejected as the semantic kind because its ordinary
> relational reading carries causal, temporal or lifecycle-origin implications that the
> household's assertion does not establish and the cases contradict or prohibit. The relation is
> one ruled kind, `obligation_in_respect_of`, meaning exactly that the asserting party holds the
> subject obligation is in respect of the object expense — and nothing above that floor: not
> caused by, preceded by, generated by, billed for, allocated to, legally owed because of, the
> payment obligation for, the coverage responsibility for, equal in amount to, or exclusively in
> respect of. Both participants are established identities — the obligation the subject, the
> expense the object, a direction fixed by participant type and carrying no meaning; no reverse
> claim and no inverse kind exist, and a query in either direction is navigation, not a relation;
> no cardinality is implied — an obligation may be in respect of several expenses and an expense
> the subject of several obligations, with no share, allocation, sum, merge or single creditor
> following. It is established only by a party's assertion, both endpoints already established
> — the household's, or the provider's — and the assertion establishes neither endpoint nor any
> property of either; a reading, a matcher, a bill concerning both identities, a shared minting
> utterance or an insurer's patient-responsibility figure yields at most a candidate. Knowing
> for it is undetermined until a role designates the relevant participant. It derives nothing:
> no amount or reconciliation on either side, no temporal order, no beginning or ending of the
> obligation, no occurrence of the expense, no discharge, payment or coverage, no nature,
> necessity, date, provider or amount projected from the expense onto the obligation, no
> requirement that the obligation's creditor be the expense's provider, no transitivity across
> `obligation_replaces`, and no single "underlying expense" — a consumer may traverse the
> established relation to its asserted endpoints, by whom and beside any competing assertion,
> and the relation establishes no further fact about what it reaches. Bill, charge,
> responsibility, balance, financing and their phrasings are content or claims about the
> obligation, never kinds. Where either endpoint is absent there is no relation. Nothing is
> minted, merged, classified or reconciled by the claim.**

**If ruled, the representation is one registry entry** — `OBLIGATION_IN_RESPECT_OF: subject
(subject_obligation_id) · object (object_expense_id) · symmetric False · reading_establishes
False · relational_knowing True, no knowing_relation` — both slots already exist; a fixture over
C1–C21 and the absences (no amount, share or reconciliation; no nature / date / provider /
amount projected onto O; no `underlying_expense` resolver; no inverse kind; no transitivity; no
correspondence candidate from a shared expense; no derivation from about-ness or shared
provenance; no minting from PR); C7 permanent; the expense fixture's *"O ↔ X NOT built"* check
retired truthfully; **no schema, no migration**; and **nothing at family level** — pass D opens
only after this is ruled.

**What pass C leaves exactly where it found it:** payment ↔ expense (D) · `toward` (D′) ·
coverage (E/F) · the four determinations and every reconciliation (item 7) · C3's reading of
necessity through the relation (item 7) · the role catalogue (obligor, incurred-by, provider,
E) · the classification catalogue · the insurer's stances as P-ack-shaped claims · candidate
generation.

*The line: the visit is what happened; the debt is what is owed; that the debt is for the visit
is what someone said about the two of them — and why, when, how much, and how it divides are not
in it.*

### C.8 Rob's review, 2026-09-15 — tightened before ruling

Rob's seven required tightenings and three worth-having are applied above: the three
`arises_from` defects separated and independently justified, with C7 named decisive (§C.3) · the
semantic floor defined and a case for it (C18, §C.6) · C6 made a three-way reconciliation test ·
C17 split into endpoint retrieval vs projection, with the five negatives · one expense → several
obligations (C4, now including the financing obligation) · one obligation → several expenses
(C5) · C12 recorded for G as participant typing and role semantics · provider standing (C19) ·
no inverse (C20) · traversal vs derivation (C21).

**Two places the record departs from the review's wording, deliberately:**

1. **"A consumer can identify X as *the* expense the obligation is in respect of."** The singular
   hides a resolver. C13 and C5 give one O several asserted expenses, by different parties,
   possibly contested. What a consumer can identify is *every X asserted, by whom, beside any
   competing assertion* — never "the" X. C17 and C21 are worded that way, and
   `underlying_expense(O)` returning one value is named as the thing not built.
2. **"No `expenses_for_obligation()` unless justified as a query."** The distinction the review
   draws — navigation vs derivation — is right, and C21 pins it; but the fence is drawn on the
   *shape of the answer*, not on the existence of a function: a query returning every asserted
   endpoint with its evidence is the same thing every fixture already does with a filter and is
   neither built nor forbidden; a function that returns *one* endpoint, or hides the asserter, is
   a derivation and is refused. This keeps the fence from being read as "no reading the
   relation".

**"In whole or in part" dropped** on Rob's challenge — the reasoning is in §C.6. The candidate
sentence changes accordingly; the floor now carries what the qualifier was trying to.

### C.9 Ruling — Rob, 2026-09-15: PC1 / `obligation_in_respect_of` accepted as written

*Both pushbacks agreed; the rewrite improved the pass rather than merely satisfying the review.*

**The correction on "the" is exactly right.** The reviewer's wording had introduced the very
resolver discipline the passes exist to prevent. With C5 / C13 the valid result is not `O → X` as
though X were *the* underlying expense; it is

```text
O
├── asserted in_respect_of → X1   [Party A]
├── asserted in_respect_of → X2   [Party B]
└── asserted in_respect_of → X3   [Party C]
```

each assertion retaining its provenance and any contest. **The relation gives a directed
assertion between established endpoints; a consumer can enumerate those established assertions;
it cannot collapse them into a singular semantic answer.** Query / navigation (every established
endpoint with provenance) vs derivation (select or manufacture one "underlying expense") is the
right architectural boundary — **C21 accepted as written on that basis.**

**Dropping "in whole or in part" was right.** In A *counteracts some/all* and in B *substitution
for some/all* have semantic work to do; *in respect of* needs no completeness qualifier, and the
phrase would have created an apparent quantitative dimension without defining one. C4 / C5 plus
the semantic floor do the cleaner job — multiple obligations may point at one expense; one
obligation may be asserted against multiple expenses; no allocation, no share, no exclusivity, no
cardinality rule — **stronger than encoding multiplicity into the wording.**

**The candidate survives the important attacks — the boundaries now explicit:** identity (neither
endpoint minted) · evidence (readings produce candidates, never the relation) · semantics (not
caused by / preceded by / began / generated / legally owed because of / amount-equivalent /
payment toward / covered by) · multiplicity (no 1:1, 1:n or n:1 decided) · quantification (no
allocation, percentage, residual, sum or reconciliation) · direction (typed Obligation → Expense;
a reverse relation would be separately ruled, never implied) · provenance (the asserting party
stays part of the assertion; provider assertion acquires no special ontological authority) ·
traversal (enumerating established endpoints ≠ deriving a privileged endpoint or fact) ·
downstream (no balance, status, discharge, payment tracing, plan meaning, lifecycle or
expense-property projection). *A very clean relation floor.*

**The G observation accepted — and not turned into a conclusion yet.** *Participant typing and
participant-role semantics* is retained as the G comparison dimension:

| Relation | Endpoint structure | What distinguishes the roles |
|---|---|---|
| `payment_counteracts` | Payment → Payment | semantic role of each same-typed participant |
| `obligation_replaces` | Obligation → Obligation | semantic role of each same-typed participant |
| `obligation_in_respect_of` | Obligation → Expense | the endpoint types themselves |

Evidence that an eventual family substrate may have to accommodate genuinely different semantic
structures; **not yet** evidence that a shared substrate is impossible. G inspects it, not solves
it prematurely.

**C7 is permanent, and protects a general invariant:** *relation semantics must not derive
temporal order from the relation's linguistic direction or from identity creation order* —
connected to the B10 fence without importing B's relation. Exactly the regression a later
"helpful" implementation would introduce on seeing `obligation_in_respect_of(expense)` and
deciding the expense must precede the obligation.

**The semantic contract, frozen:**

> **`obligation_in_respect_of`: the asserting party holds that the subject obligation is in
> respect of the object expense.**

subject = established Obligation · object = established Expense · directional · not symmetric ·
established by party assertion · reading / matching / EOB / bill labels produce candidates only ·
no inverse · no cardinality · no allocation or quantitative semantics · no temporal / lifecycle
semantics · no balance reconciliation · no property projection · no status / discharge / payment /
plan derivation · relational knowing **undetermined** unless a separately ruled epistemic relation
designates the relevant participant · traversal may enumerate established assertions / endpoints
but may not select a privileged endpoint.

**Representation authorised — the same build discipline as A / B:** one registry entry on the
existing obligation / expense slots, fixture coverage for the C cases and absences, no family
abstraction.

```text
OBLIGATION_IN_RESPECT_OF
    subject: subject_obligation_id
    object:  object_expense_id
    symmetric: false
    reading_establishes: false
    relational_knowing: true
    knowing_relation: none
```

**Pass C: RULED / CLOSED on build. No pass D yet — C earns its own closure first.**

#### Built — 2026-09-15

One registry entry exactly as authorised; both slots pre-existed; no guard change (the reflexive
guard does not apply to a cross-typed kind — the type discipline in `participant_violations`
already refuses the slots swapped, which is C12 / C20 made executable). Fixture
`tests/test_obligation_in_respect_of_fixture.py` (43 checks, C1–C21 and the absences: no
`underlying_expense` / `expense_of_obligation` / `obligations_of_expense` resolver, no
reconciliation or residual helper, no allocation or share column, no nature / date / provider /
amount projected onto O — as claim, column or attribute — no inverse or expense-subject kind, no
order guard, no `arises` kind, no correspondence candidate from a shared expense, no relation
table; C7 permanent). Smoke `s103_obligation_in_respect_of.py`, **nine** mutations caught: the
matcher's pairing acquires a party's assertion · expense facts project onto O · a resolver selects
the underlying expense · the relation reconciles amounts · **the phrase supplies temporal order
(a C7 guard)** · the inverse kind is manufactured · **patient responsibility mints the obligation**
(escaped first — the fixture had no obligation count around C6's $412 stance; closed, as A's
label-establishes escape was) · about-ness derives the relation · the kind turns symmetric.
Retired in place, truthfully: the expense fixture's Ex4 *"O ↔ X NOT built"* → *ruled elsewhere,
`arises_from` rejected, not asserted here*; the obligation and obligation-replaces fixtures'
"obligation-subject kinds are exactly {corresponds, replaces}" → plus `obligation_in_respect_of`.
No schema, no migration, no family abstraction. Gate 997 → 1009, 0 failed.

#### Smoke review — Rob, 2026-09-15: no semantic defect; two test-quality fixes; C stays closed

*An adversarial smoke review, not a plausibility check.* **The C7 mutation is especially valuable:
it proves the permanent temporal invariant is executable, not merely documented** — the realistic
future mistake `O in_respect_of X → X must have existed first → created_at ordering guard`, killed
by the fixture; and the raw-SQL mutations (`aboutness_derives`, `pr_mints`) are appropriate: they
test whether an implementation could manufacture a relation or an identity *structurally*, not
whether a normal API would accept it. The registry mutation attacks the contract, not an
implementation detail; C12 / C20 keep cross-type direction from being "symmetry false because the
registry says so" — reversing the endpoint types would be a different proposition kind.

Applied: **(1) C19's obligation count decoupled** — it read `n_obl + 1` inherited from C10, i.e.
*"since C10 exactly B450 was created"*, which is not what C19 tests and would break on any
legitimate addition between them; the counts are now captured immediately before Riverbend Hospital's
assertion, so the check says exactly *the assertion minted nothing*. **(2) C21's helper comment
strengthened** — *test-only enumeration of proposition rows + their evidence; deliberately not a
database / model accessor or semantic resolver* — so it is never read as a canonical traversal
API. **(3) The baseline is re-established after every mutation's undo**, not only at the end — a
mutation whose undo leaves global state the fixture happens not to observe is attributed to the
mutation that left it. (s86–s102 check only the final state; not changed unasked.) **Not changed:
the C7 mutation.** Gate 1009 → 1018, 0 failed.

**The mutation surface, as Rob read it:** evidence → assertion · expense facts → obligation facts ·
relation → resolver · relation → reconciliation · relation → temporal ontology · relation →
inverse · determination → identity · about-ness → relation · typed direction → symmetry.

**C: CLOSED.** *The next semantic work is D, but it should begin from its own pressure source
rather than treating `in_respect_of` as evidence for whatever D turns out to be.* Opened when Rob
opens it.

---

## Pass D — Payment ↔ Expense

**The question, applied:** when a household member says *that CVS charge was Kim's prescription*,
*I paid $30 at the desk for the ER visit*, *the HSA reimbursed me for it*, or *one cheque covered
both visits*, what is being claimed, who can establish it, and what follows? Rob's framing carried
from §2 and §C.9: ***payment = money movement for expense* is the enormous temptation** — the
relation cannot manufacture either identity, cannot prove purpose from a bank description, cannot
silently become one-to-one; the cases must include **1→1 · one expense → several payments · one
payment → several expenses · a payment with no established expense · an expense with no payment ·
disputed attribution**; and D **begins from its own pressure sources**, not from
`obligation_in_respect_of` — whatever D turns out to be, C is not evidence for it.

*Tightened 2026-09-15 after Rob's review (§D.8) — the payment-specific ambiguity of "in respect
of", cardinality vs allocation, payer / payee semantics, and composition with pass A.*

### D.1 What is already fixed

| Ruling | Constraint on pass D |
|---|---|
| **Payment identity** (A, §10) | an event identity minted by a Person's individuating assertion; payer, payee, amount, date, method, cleared, attached, confirmed, acknowledged, reversed, *toward* are **claims** about p by their knowing parties; **payment ≠ transaction** (Pm11 cash; Pm12 a debit that is no payment); **payment ≠ discharge**; the payer may be anyone (Pm9); a bank line, a draft, a ledger row yield candidates |
| **Expense identity** (X3, §8) | an event identity for an incurrence the household individuates; billed · allowed · plan-paid · patient responsibility · **household-paid** are claims about X; **expense ≠ movement** (it may have none, or several); Ex5 an expense nobody paid for; Ex8 *Kim's prescription* — a card line, no bill, no EOB, **no obligation** |
| **Transaction referent** (Tx8) | a bank line is the bank's statement about a movement; the movement is unminted; the line *concerns* X once the household says so (`proposition_concerns`) — a proposition about a movement, not a payment↔expense relation |
| **Rob's constraint** (reversal, carried to expense) | *a source's category for a movement does not establish the identity of the thing being categorised* — `CVS PHARMACY · Medical` mints neither p nor X and proves no purpose |
| **`toward(p, O)`** (D′) | a stand-in — the household's claim about what a payment was for, *object an obligation*; **not this pass's**; placed after D, tested against D's semantics; it does not establish discharge |
| **Acknowledgment / H2** | discharge is E's claim on a payment; `remaining` is an attached-payment projection, not discharge; *cleared · attached · user-confirmed* are three claims by two parties — **one party short** of the sequence |
| **1.x `ExpenseFundingAllocation`** (SHIPPED_VS_TARGET) | `expense_id · funder · amount · mode · cleared · attached · user_confirmed · duplicate_of · occurred_on` — *a household assertion of who funded what*, the acknowledgment stations as booleans, correspondence as a column, evidence time fused; **the fused row the target decomposes — the shape not to inherit** |
| **The four determinations** (`provider_adjustment · user_paid_cash · unpaid · pending_claim`) | *current determinations superseded rather than overwritten* — reconciliation stances about amounts of an expense; **consumers of the identities, item 7**; `unpaid` and `pending_claim` must not collapse |
| **Pass A** | `payment_counteracts` — two payments; a refund is another payment; **no netting** |
| **Pass C** | `obligation_in_respect_of` — an obligation and an expense; **no transitivity across kinds** (C9); its floor is C's result on C's cases — **not imported here** |
| **About-ness** | a receipt (`artefact_concerns`) or a statement line (`proposition_concerns`) concerns p and/or X — a document or proposition concerning two identities does not relate them |
| **Correspondence** | within one type; p and X are never one referent |
| **K8** | *I paid CVS for (Kim's prescription)* with X in content is the hidden-operand mistake |
| **Prohibitions 1–12** | §1 |

### D.2 Is there a relation at all — D's own pressure sources, one at a time

| Where the pressure comes from | What it is, under the rulings | Payment ↔ expense? |
|---|---|---|
| **Ex8 — the card purchase** — *that CVS charge was Kim's prescription* | Rob individuates X (the prescription) and p (the payment); **no obligation exists or is wanted**; his sentence has **two referential operands** of different types | **yes — if it is to be recorded at all**: K8 makes it a two-participant claim, and no chain through an obligation can stand in for it because there is no obligation |
| **1.x `ExpenseFundingAllocation`** — *who funded what* | a household assertion tying a funding event to an expense, fused with amount, mode, three station booleans and a duplicate pointer | **yes, one part of it**: the *attached* assertion is a relation claim; **everything else on the row is a claim about p** (amount, occurred, cleared — the bank's; confirmed — the household's), a correspondence (`duplicate_of` → `payment_corresponds`), or a counteraction (`mode = reversed` → pass A). The row is pressure for the relation and a warning about its shape |
| **the determinations** — `user_paid_cash` | a reconciliation stance: *this amount of X was paid by the user* — a consumer's reading over p, X and whatever relates them | **no** — item 7; it presupposes the relation, rules nothing about it (prohibition 11) |
| **the bank line** — `CVS PHARMACY 24.99 · Medical` | the bank's proposition about a movement; may concern X (Tx8) and, once p exists, concern p (Ab7) | **no** — about-ness; a category proves no purpose; a line mints neither |
| **the chain** — p *toward* O (D′), O in respect of X (C) | two claims of two kinds | **no** — no transitivity across kinds; the household may say *I paid for the ER visit* and mean the bill, and that is a claim it makes, not one the substrate derives |
| **the EOB's *plan paid $568*** | the insurer's dated stance about X (Ex3, 4b) — an amount claim on X | **no** — not a payment identity (unminted) and not a relation; if Rob individuates *Lakeview Health paid Riverbend Hospital $568* as a payment, that is a new p and the relation is his to assert |
| **Ex5 / Pm11-with-no-expense / Pm12** | an expense nobody paid for; a payment the household never tied to an incurrence; a debit that is no payment | **no** — no second participant; the relation is optional at both ends |

**So: there is exactly one payment-to-expense relation, and it is — the fourth time — a party's
statement whose referential operands are two identities: *this payment was in respect of that
expense*.** It is forced by Ex8 on its own, where nothing else in the ontology can carry the
sentence; the 1.x row shows the temptation to make it carry amount, station and direction; the
bank line, the determinations, the chain and the EOB manufacture nothing.

### D.3 The temptation, interrogated — *payment = money movement for expense*

Three collapses hide in the phrase, each rejected on its own ground:

| Collapse | What it would assert | Why it fails |
|---|---|---|
| **movement = payment** | the bank line is the payment | ruled already (Pm11 / Pm12): a payment may have no movement, a movement may be no payment; the line is evidence, never the identity |
| **payment = funding of the expense** | the relation means *p paid (some of) the cost of X* — money flowed *from* the household *to* the provider *for* X | **contradicted by three independent cases, for three different reasons**: D9 (reimbursement — money flows *to* the household), D18 (the insurer's payment — a payment can exist with **no household participant as payer or payee**), D19 (a third party — **payer and incurrer can be different people**). Together they refuse the silent chain *payment → payer → expense's incurrer → payment funds expense*. **The relation carries no payer / payee semantics; those remain separately asserted claims about the payment** — a consumer may join them to the relation, and may not turn them into its meaning. A "funds" reading would need a different kind for each money direction — and D9's reimbursement is the same sentence, *that was for the ER visit* |
| **one movement, one expense** | the relation is 1:1 | contradicted by D3 (copay + bill payment for one visit) and D4 / D17 (one swipe for two prescriptions, or a prescription and shampoo nobody individuates) |

What survives is the household's sentence, which says none of those things: **the payment was in
respect of the expense** — its purpose, as asserted, not its direction, its sufficiency or its
uniqueness. *(That this is the same floor pass C reached is a result of D's cases, not an
import from C — and is recorded for G in §D.6.)*

### D.4 The cases

| # | Case | What must be sayable | What must not follow |
|---|---|---|---|
| **D1 (Ex8) — 1 → 1** | Rob: *the CVS charge on 3/2 was Kim's prescription.* Rob individuates X and p — one utterance, or two. | X minted; p minted (payer Rob, payee CVS, $24.99, 3/2 — claims on p); **p in respect of X** — a claim with two established participants; the bank line concerns p and concerns X (about-ness) | no obligation is minted or implied; X acquires no *paid* status; p's amount is not X's cost; the merchant string proves nothing |
| **D2** | The feed: `CVS PHARMACY 24.99 · Medical`. Nothing minted yet. | a proposition from a capture with candidates (a payment Rob has not asserted; an expense he has not individuated) | it mints neither p nor X and relates nothing; **purpose is not proven from the description**; once p and X exist, a matcher's pairing is a **reading-sourced candidate** for the relation |
| **D3 — 1 expense → n payments** | The ER visit: $30 copay at the desk (p1, cash — no bank line); $382 paid on the bill in April (p2); a third payment p3 Rob later says was also for it. | **three claims**: p1 in respect of X · p2 in respect of X · p3 in respect of X | **cardinality is not allocation**: no sum; no *fully paid*; nothing compares $412 to $30 + $382; **no implication that any of them is a duplicate (`payment_corresponds` is a separate claim), a replacement, a counteraction (pass A) or "partial" unless another claim says so**; `user_paid_cash` is item 7's |
| **D4 — 1 payment → n expenses** | One CVS swipe, $61.48: Kim's prescription (X1) and Rob's (X2). | **two claims**: p in respect of X1 · p in respect of X2 | **the relation does not say how p relates to each**: no allocation, no split, no percentage, no order of satisfaction (*the first expense gets paid first*), no *remainder*; **several assertions of this kind are never an implicit allocation** — *how much of $61.48 was Kim's* is a consumer's question, and X's own amount claims are where the pharmacy's figures live |
| **D5 — payment, no expense** | Rob paid the plumber $200 in cash and never individuated the job as an expense; Rob gave his brother $500. | p minted with payee and amount; **no X and no relation** | nothing manufactures an incurrence for a payment — *every payment is for something* is false in the ontology |
| **D6 — expense, no payment** | Ex5's wellness visit; Riverbend Hospital's bill still unpaid. | X; its stances | **no p and no relation**; *unpaid* is a determination (item 7), never derived from an absent relation — absence of a relation is absence of evidence |
| **D7 — disputed attribution** | Rob: *the $84 was for the cushion* (X1); Kim: *no — the brace* (X2). | two claims: p in respect of X1 (Rob); p in respect of X2 (Kim) — **contested, derived** | nothing chooses; no current attribution |
| **D8 — the chain** | p2 *toward* O (stand-in); O in respect of X (C). And separately: Rob says *I paid for the ER visit* (p2 in respect of X). | three claims of three kinds, each asserted | **no transitivity in either direction**: p2 in respect of X is not derived from toward + in-respect-of; p2 toward O is not derived from the two in-respect-ofs; **discharge of O is untouched** — E's acknowledgment, never a relation's consequence |
| **D9 — reimbursement** | The HSA administrator pays Rob $412; Rob: *that was the reimbursement for the ER visit.* | p minted by Rob (payer the administrator, payee Rob — Pm9); **p in respect of X**, the same kind | the relation carries **no direction of money** — payer / payee are p's claims; *reimbursement* is content; X acquires no *reimbursed* status and no net cost; nothing offsets p against D3's payments (netting is item 7 and, for payments, pass A's fence) |
| **D10 — amounts** | Copay $30 (p1's claim); X's patient responsibility $412 (Lakeview Health's stance); X's billed $1,300. | the claims on p and on X; the relation beside them | **the relation carries no amount and reconciles nothing**: no *p's amount = X's cost / PR / residual*, no *remaining on X*; the determinations are item 7 |
| **D11 — the 1.x row** | `ExpenseFundingAllocation(expense_id=X, funder=user, amount=30, mode=allocated, cleared=1, attached=1, user_confirmed=1, occurred_on=…, duplicate_of=…)`. | decomposes without remainder: **p** (minted by the household's assertion) · *paid_by* (funder — a role claim on p) · amount / occurred (claims on p) · cleared (the bank's claim on p) · **attached = the relation, p in respect of X** · user_confirmed = the household's confirmation of its own assertion (provenance, not a field) · `duplicate_of` → `payment_corresponds` · `mode = reversed` → pass A · `eob_import` → a reading | **not inherited**: an amount on the relation; station booleans on the edge; a mode; a pointer for correspondence. Decomposition blocked, as before, on the asserting party (no `Person` rows) — a data question, not a reason to weaken the kind |
| **D12 — the determinations** | Rob marks the visit *user_paid_cash*. | a reconciliation stance — a consumer's reading over X, its amount claims, p and the relation; representable later as a dated claim on X if item 7 rules it | **not this kind, not derived from it**: *paid* is not a status the relation confers; `unpaid` / `pending_claim` stay uncollapsed |
| **D13 — direction** | Is *X in respect of p* a different claim? | subject the payment, object the expense — **fixed by type**; no reverse claim to read | **no inverse kind** (`expense_paid_by`, `expense_funded_by` would be second relations, not this one backwards); navigation either way is a query, never an accessor that selects |
| **D14 (Pm13)** | Rob later: *that charge wasn't the prescription — it was the brace.* | `utterance_retraction` of the utterance behind the relation claim; a new claim to X′ | p, X, X′ untouched; the history survives |
| **D15 (pass A) — composition refused both ways** | CVS refunds the prescription: p2 counteracts p1; p1 in respect of X. And the mirror: Rob asserts only p2 in respect of X and p2 counteracts p1. | p2 counteracts p1 (A); p1 in respect of X; **p2 in respect of X is Rob's to assert** (a refund is *for* the prescription too, if he says so) | **no composition across independently ruled relations, in either direction**: *counteracts + in-respect-of* does not derive the counteracting payment's relation to X, and *in-respect-of + counteracts* does not derive the counteracted payment's; X acquires no *refunded*; nothing nets (A's fence, item 7) |
| **D16 — vocabulary** | *paid for* · *funded* · *covered* · *reimbursed* · *copay* · *out-of-pocket* · *attached* · *allocated*. | content, or claims on p (its payer, its payee, its kind) | **not kinds**: they differ in money direction, station and label — claims about p — not in what is claimed of the relation, who may establish it, its participants or what follows; *covered* is pass E/F's word |
| **D17 — the mixed basket** | One swipe $61.48: Kim's prescription (X1) and shampoo, which nobody individuates. | p in respect of X1 | the relation says nothing about the rest of p; no *unallocated remainder*; no expense is manufactured for the shampoo |
| **D18 — the insurer's payment** | The EOB says *plan paid $568*. Rob: *Lakeview Health paid Riverbend Hospital $568 for the ER visit.* | the EOB's stance on X (Ex3) is one thing; **p′ minted by Rob** (payer Lakeview Health, payee Riverbend Hospital) is another; p′ in respect of X, asserted by Rob | the EOB line mints no payment; the stance on X and the payment identity are not one thing and neither derives the other; **neither payer nor payee is the household** — the relation requires no household party anywhere on p |
| **D19 (Pm9)** | Rob's mother paid CVS for Kim's prescription. | p (payer the mother — a minted party); p in respect of X | **no payer / incurrer mirroring**: the payer of p need not be the person who incurred X, nor the household (A7 / C8's role in this pass) |
| **D20 — about-ness** | The CVS receipt (artefact, origin CVS) concerns p and concerns X. CVS's receipt line *Rx #4471 — $24.99*. | two `artefact_concerns` claims; CVS **may assert the relation as a party**; from a reading it is a candidate | **the relation is not derived** from a document concerning both; *any party may assert, both endpoints already established; the assertion establishes neither endpoint nor any property of either* (C19's rule, restated for D) |
| **D21 — timing** | The $500 surgery deposit paid in April (p); the surgery in May (X); Rob: *the deposit was for the surgery.* Also: a payment in 2027 for a 2026 visit. | p in respect of X, `as_of` permitted | **no temporal order** — p before X or long after; `created_at` not consulted. D reproduces C7's result independently, so the invariant is not an artefact of obligation semantics and is stated generally, to survive D′: ***a relation's direction and participant types do not establish temporal precedence between its endpoints.*** **PERMANENT** |
| **D22 — the semantic floor, payment-specific** | *I made this payment in respect of Kim's prescription.* | exactly that — the asserted subject / object relationship | **"in respect of" ≠ "made for"**: it does not establish, merely by the relation, that the payer is Kim · the payer is the incurrer · the payee is CVS or the provider (S1: a billing company) · the payment funded CVS · the payment was made *because of* the prescription · the payment discharged an obligation · the amount corresponds to the prescription · this is the only payment for the expense · X is paid, or nothing remains · the expense was covered; each is a further claim or a consumer's reading |

### D.5 Testing the readings

**PD0 — no relation; p ↔ X is reached by inference** (the chain through an obligation; the bank
line concerning X; matching amounts and merchants; the receipt concerning both). Rejected: **Ex8
has no obligation to chain through**; prohibitions 3, 4, 11; D2 (a description proves no purpose);
D20 (a document concerns two things without relating them); and K8 — Rob's sentence has two
operands.

**PD1 — one ruled kind with a payment subject and an expense object**, meaning exactly *the
asserting party holds that the subject payment was in respect of the object expense* — with the
floor of §D.6 and nothing above it. Every case is representable; every "must not follow" is a
non-derivation the substrate already refuses; D5, D6, D12 are correctly *outside* it.

**PD2 — the 1.x allocation shape** (the relation carries amount, mode, cleared, attached,
confirmed). Rejected: prohibition 7 and the no-amount precedent of A–C; the row fuses three
parties' claims about p onto an edge (D11); *attached* is the whole of the relation and the rest
is p's.

**PD3 — a claim about p with X in content** (*p was for Kim's prescription*). Rejected by K8; D4,
D7 become indistinguishable or unstatable.

**PD4 — one generic `payment_expense_relation` with the relation named in content.** Rejected:
prohibitions 1 and 4.

**PD5 — several kinds by money direction or station** (`payment_funds`, `payment_reimburses`,
`payment_copay`, `payment_attached`…). Tested by the stopping rule inside the pass (D9, D16): they
differ in **payer / payee direction, station and label** — claims about p, or content — not in
what is claimed of the relation, who may establish it, its participants or what follows. One kind
survives. **D9 is where this bites**: the reimbursement is the same sentence with the money the
other way, and the money's direction is already p's payer / payee claims.

**PD6 — reduce it to about-ness** (`proposition_concerns(line, X)` is enough). Rejected: the line
is a proposition; p is an identity that may have no line at all (D3's cash copay); C11's shape
again (D20).

**PD7 — derive it across the chain** (toward + in-respect-of ⇒ p in respect of X, or the reverse).
Rejected: D8; no transitivity across kinds; discharge would ride along.

**PD8 — an expense status** (*paid*, *reimbursed*, *funded*). Rejected: prohibition 7; D6, D9,
D12; the determinations are item 7.

### D.6 What the relation is — and is not

**The semantic floor.** The relation means only: **p is asserted as having been in respect of
X.** It does **not** mean any of: *p funded X* · *p paid (some of) the cost of X* · *money moved
from the household to the provider* · *p's amount equals or contributes to X's cost, patient
responsibility or any residual* · *X is paid, partly paid, reimbursed or covered* · *p discharged
an obligation* · *p was allocated to X* · *p preceded or followed X* · *the payer incurred X* ·
*the payee provided X* · *p is exclusively in respect of X*. Each is a further claim by a party,
a consumer's reading, or another pass's relation. **"In respect of" identifies the asserted
subject / object relationship; it does not describe the economic purpose, direction, funding
mechanism or legal effect of the payment.** The relation carries **no payer / payee semantics**;
payer and payee remain separately asserted claims about the payment — a consumer may join them to
the relation (as it may join X's nature claims in C17), and may not make them its meaning.

| The claim | *the subject payment was in respect of the object expense*, as the asserting party holds — and nothing above the floor |
|---|---|
| **participants** | subject: the payment · object: the expense — both **established**; no other slot; **no household party required anywhere on p** (D18) |
| **direction** | **fixed by participant type, not by meaning** — no reverse claim (D13); `symmetric` false only because the slots differ in type; **no inverse kind**; navigation either way is a query |
| **cardinality** | none ruled — and D3 / D4 / D17 show none could be: many-to-many, no share, no exclusivity, no remainder |
| **who establishes** | any party's assertion, **both endpoints already established** — the household, the pharmacy (D20), the insurer if it ever asserts; establishes neither endpoint nor any property; a reading, a matcher, a merchant string, a category, a receipt concerning both yields **candidates only** |
| **knowing** | `relational_knowing` **True with no designated relation → `undetermined`** — the payer of p? the payee? the incurrer of X? none forced (A's and C's restraint) |
| **content** | opaque — the party's wording (*copay*, *reimbursement*, *the whole swipe*); never read by a derivation |
| **`as_of`** | permitted; p's date and X's date of service are their own claims |
| **derives** | **nothing**: no amount, share, sum, allocation, order of satisfaction or reconciliation (D3, D4, D10); no duplicate / replacement / partial reading of several payments (D3); no *paid* / *reimbursed* / *covered* on X (D6, D9); no discharge on any obligation (D8); no payer / payee semantics or direction of money (D9, D18); no temporal order (D21); no payer / incurrer or payee / provider mirroring (D19, D22); no composition with `toward` or `obligation_in_respect_of` (D8) or `payment_counteracts` (D15, both directions); no manufactured expense for an untied payment or the rest of a swipe (D5, D17); no determination (D12) |
| **what it is not** | not the movement (D2); not `toward` (D′); not about-ness (D20); not correspondence; not the 1.x allocation row (D11); not a determination (D12); not funding (D.3) |
| **name** | a working name is needed for a kind; not a source word (*funds*, *pays for*, *allocated*, *attached*): `payment_in_respect_of` — chosen because **D's own cases arrived at the same floor as C's**; the name records that result and carries no semantics beyond this table |

**For G — same semantic floor, not the same relation.** C and D were opened from different
pressure (Ex4 / §7.7 vs Ex8 / the 1.x allocation row) and **currently exhibit the same relational
semantic floor under substitution of the subject participant type**: *a party's statement that
the subject is in respect of the object expense*, the same establisher rule, direction fixed by
type, no cardinality, nothing derived. The relational shape is parallel; **the subject identities
have different ontology and different downstream possibilities** (a payment has payer, payee,
cleared, counteraction; an obligation has entitlement, terms, replacement, discharge). On the
stopping rule's dimensions they differ only in participants — which is **evidence for later
family inspection, not a ruling that they belong to one semantic family**, standing beside C.12's
evidence *against* a family with A / B. **G inspects both; D concludes neither.** The name
`payment_in_respect_of` describes the candidate — the same linguistic relation phrase with a
different typed subject — and asserts no family.

### D.7 Ruling candidate — pass D, for Rob

> **There is exactly one payment-to-expense relation, and it is a party's statement of what a
> payment was in respect of — not what it funded, not which way the money went, not how much of
> the expense it met, and not what it did to any obligation. *Payment = money movement for
> expense* collapses three things the cases keep apart: the movement is the bank's statement and
> not the payment; funding is a direction of money that reimbursement, an insurer's payment and a
> third party's payment all contradict; and one-to-one is contradicted by a copay beside a bill
> payment and by one swipe for two prescriptions. The relation is one ruled kind,
> `payment_in_respect_of`, meaning exactly that the asserting party holds the subject payment was
> in respect of the object expense — and nothing above that floor. Both participants are
> established identities — the payment the subject, the expense the object, a direction fixed by
> type and carrying no meaning; no reverse claim and no inverse kind; no cardinality — a payment
> may be in respect of several expenses and an expense the object of several payments, with no
> share, sum, remainder, allocation or exclusivity following, and no expense manufactured for
> what a payment was not tied to. It is established only by a party's assertion with both
> endpoints already established — the household's, the payee's, or any party's — and the
> assertion establishes neither endpoint nor any property of either; no household party is
> required on the payment; a bank line, a merchant string, a category, a matcher, a receipt
> concerning both identities or an insurer's paid figure yields at most a candidate. Knowing for
> it is undetermined until a role designates the relevant participant. It derives nothing: no
> amount or reconciliation, no paid, reimbursed or covered status on the expense, no discharge on
> any obligation, no direction of money, no temporal order, no requirement that the payer
> incurred the expense or the payee provided it, no transitivity with toward,
> obligation_in_respect_of or payment_counteracts, and no determination. The 1.x allocation row
> decomposes into a payment, claims about it, a correspondence, a counteraction and this relation
> — its amount, mode and station booleans are not inherited onto the edge. Paid-for, funded,
> covered, reimbursed, copay, out-of-pocket, attached and allocated are content or claims about
> the payment, never kinds. Where either endpoint is absent there is no relation, and the absence
> of a relation is absence of evidence, never "unpaid". Nothing is minted, merged, reconciled or
> statused by the claim.**

**If ruled, the representation is one registry entry** — `PAYMENT_IN_RESPECT_OF: subject
(subject_payment_id) · object (object_expense_id) · symmetric False · reading_establishes False ·
relational_knowing True, no knowing_relation` — both slots already exist; a fixture over D1–D22
and the absences (no amount, share, sum or remainder; no paid / reimbursed / covered; no funding
direction; no `expense_paid_by` inverse; no `payments_for_expense` resolver; no order guard; no
transitivity; no manufactured expense; no determination; no allocation row shape); D21 permanent;
the payment fixture's stand-in note and the expense fixture's Ex8 check updated truthfully;
**no schema, no migration**; and **nothing at family level** — D′ opens only after this is ruled.

**What pass D leaves exactly where it found it:** `toward(p, O)` — D′, **to determine
independently whether *toward* means what the fixtures have assumed, not to take D as its semantic
foundation**; in particular D establishes neither *p in respect of X + O in respect of X ⇒ p toward
O* nor its reverse (D8) · discharge and `remaining` · netting (A's fence, item 7) · the four
determinations and every reconciliation (item 7) · coverage (E/F) · the role catalogue (payer,
payee, incurrer, provider) · candidate generation and the importer contract · `ExpenseFundingAllocation`
decomposition (blocked on Person rows).

*The line: the money moved; the visit happened; that the money was for the visit is what someone
said about the two of them — and which way it went, how much it met, and whether anything is now
paid are not in it.*

### D.8 Rob's review, 2026-09-15 — tightened before ruling

Rob's four checks, applied where the record did not already pin the boundary: **(1)** the
economic-purpose / funding fence stated on the floor in his words — *"in respect of" identifies
the asserted subject / object relationship; it does not describe the economic purpose, direction,
funding mechanism or legal effect of the payment* — and D22 rewritten as the payment-specific
ambiguity test (*in respect of* ≠ *made for*, with the things it does not establish);
**(2)** D3 / D4 now say *cardinality is not allocation* explicitly — several payments for one
expense imply no duplicate, replacement, counteraction or "partial"; one payment for several
expenses implies no allocation, split, percentage or order of satisfaction, and several assertions
are never an implicit allocation; **(3)** *"the relation carries none of it"* tightened to *carries
no payer / payee semantics; those remain separately asserted claims about the payment* — a
consumer may join them, may not make them the relation's meaning (the C17 traversal / projection
fence, mirrored); **(4)** D15 now refuses composition with `payment_counteracts` **in both
directions** (the record had one).

Also applied: D9 / D18 / D19 recorded as **three independent reasons** against *funds the
expense* — money to the household · no household participant on the payment · payer ≠ incurrer —
refusing the silent chain *payment → payer → incurrer → funds*; D21's invariant stated generally
so it survives D′ — *a relation's direction and participant types do not establish temporal
precedence between its endpoints* — now supported independently by C and D; the G note reworded
to *same relational semantic floor under substitution of subject participant type — evidence for
inspection, not a family ruling*; the D′ boundary stated — D establishes neither *p in respect of
X + O in respect of X ⇒ p toward O* nor its reverse. **Name retained** (`payment_in_respect_of`
describes the candidate; it asserts no family).

### D.9 Ruling — Rob, 2026-09-15: PD1 / `payment_in_respect_of` accepted as written; pass D closed

*The revision addresses the remaining semantic pressure without expanding the slice.*

- **The floor is sufficiently narrow.** It identifies only the asserted relationship between an
  established Payment and an established Expense; the explicit exclusion of economic purpose,
  funding mechanism, legal effect, payer / payee meaning and amount semantics prevents *in respect
  of* from becoming a disguised funding relation.
- **D3 / D4 properly separate cardinality from allocation** — several payments to one expense, one
  payment to several expenses, without the relation specifying how money is divided, prioritised
  or allocated.
- **D9 / D18 / D19 are usefully independent** — three different illicit chains, not variants of
  *payer isn't necessarily the incurrer*; **D18 in particular prevents the household from being
  smuggled into the payment merely because the payment economically benefits the household.**
- **The payer / payee clarification is correct** — separately asserted Payment claims a consumer
  may join: *relational navigation is not semantic projection.*
- **D21 is a proper general invariant** — participant typing plus direction establishes neither
  temporal precedence nor lifecycle ordering; it survives D′ instead of being a D-specific rule.
- **The `payment_counteracts` boundary is symmetric** — neither endpoint inherits meaning from the
  other relation; an obvious composition shortcut closed.
- **The G observation is appropriately restrained** — *same relational semantic floor under
  substitution of subject participant type* is evidence to inspect later, not a family ruling.
- **The D′ fence is where it belongs** — D does not provide `toward`, and no composition from
  *p ↔ X* plus *O ↔ X* may manufacture *p → O*.

**The semantic contract, frozen:**

> **`payment_in_respect_of`: the asserting party holds that the subject Payment stands in respect
> of the object Expense.**

subject = established Payment · object = established Expense · directional · not symmetric ·
established only by a party assertion · reading / matcher / label → candidate only · no
cardinality · no allocation or split semantics · no payer / payee semantics · no funding /
reimbursement semantics · no amount reconciliation · no temporal precedence · no lifecycle /
discharge implication · no property projection · no composition with `payment_counteracts` · no
inverse · no consumer derivation · relational knowing **undetermined** absent a designated
epistemic relation. **Nothing in D changes the identity rulings for Payment or Expense** — the
relation connects two already-established identities; it mints neither.

**Representation authorised — the B / C shape:** one registry entry; the existing Payment /
Expense immutable slots only; a fixture over the D cases and the explicit absence surface;
mutation smoke tests; no schema migration and no generic relation abstraction; **no D′
implementation bundled into this build.**

```text
PAYMENT_IN_RESPECT_OF
    subject: subject_payment_id
    object:  object_expense_id
    symmetric: false
    reading_establishes: false
    relational_knowing: true
    knowing_relation: none
```

**Carried forward, not changed now:** D′ is a **fresh semantic question** even though `toward`
already appears in the payment fixtures — a clean *Payment → Expense* relation makes the
temptation to infer *Payment → Obligation* stronger, which is precisely why D′ deserves its own
pressure test. **Pass D: RULED / CLOSED on build.**

#### Built — 2026-09-15

One registry entry exactly as authorised; both slots pre-existed; no guard change (the type
discipline already refuses the slots swapped — D13 executable for free, as C12 was). Fixture
`tests/test_payment_in_respect_of_fixture.py` (45 checks, D1–D22 and the absences: no
`payments_for_expense` / `expense_of_payment` resolver; no allocation, split, share, remainder or
order-of-satisfaction column or helper; no reconciliation or funding helper; no *paid* /
*reimbursed* / *covered* / *funded* claim or attribute on X; no `expense_paid_by` inverse; no order
guard; no determination kind or helper; no `funder` / `mode` / `cleared` / `attached` /
`user_confirmed` / `duplicate_of` on the proposition — the 1.x table untouched; `toward` still a
stand-in; D21 permanent). Smoke `s104_payment_in_respect_of.py`, **ten** mutations caught, the
baseline re-established after every undo: the matcher's pairing acquires an assertion · the
expense gets a `paid` status · the relation allocates · reconciles · names a funder · **the phrase
supplies order (a D21 guard)** · the inverse kind · **the chain composes through the obligation
(toward + obligation_in_respect_of ⇒ p ↔ X)** · **`payment_counteracts` composes into the
relation** · the kind turns symmetric. Retired in place, truthfully: the payment fixture's
"only payment_corresponds and payment_counteracts are ruled on the payment slots" → plus
`payment_in_respect_of`, `toward` still a stand-in. No schema, no migration, no family
abstraction. Gate 1018 → 1041, 0 failed.

### D.10 Build accepted and pass D closed — Rob, 2026-09-15. `ef04ddb`, 1041 green, clean tree.

*The implementation stayed narrower than the semantic temptation.* One new registered relation, no
new schema semantics · the existing slot discipline does the work, no redundant guard · the fixture
tests the **absence** of tempting interpretations, not merely the presence of the relation · the
obligation composition and the `payment_counteracts` composition are **explicitly executable** —
the composition surface is concrete, not documented · the EOB's *plan paid* does not manufacture a
payment · Lakeview Health → Riverbend Hospital establishes the relation **without inventing a household party** · the
proposition stays deliberately non-denormalised — no `funder`, `mode`, `cleared`, `attached`,
`confirmed`, `duplicate_of` or `source` sneaking semantic payload in · the payment fixture's
retirement is truthful (three ruled kinds; `paid_by` / `toward` still stand-ins) · **most
importantly, D′ remains outside the build** — that *p → O* becomes tempting once *p → X* is clean
is exactly why it must be a separate semantic question rather than an implementation consequence.

**D — accepted.** Build conforms to the ruled B / C-shaped relation and its explicit composition
surface. **D′ remains unopened and carries forward as a distinct semantic question.** `ef04ddb` is a
legitimate stopping point.

---

## Pass D′ — Payment ↔ Obligation: shared-X convergence, and the `toward` stand-in

**Rob's question, verbatim (2026-09-15):** *What, if anything, permits a payment's relation to X and
an obligation's relation to X to establish a payment-to-obligation relation, and what evidence
boundary prevents shared-X convergence from manufacturing obligation identity?*

Opened as a **semantic pressure test, not as "how do we derive `payment_in_respect_of` from
`obligation_in_respect_of`"**. D established `p → X`; C established `O → X`; the tempting inference
is *p → X + O → X ⇒ p → O* — **not a logical consequence merely because both propositions share
the same X.** The central trap, in Rob's words: *"a payment is in respect of an obligation because
the payment and obligation are both in respect of the same entity"* — which would collapse
about-ness / subject identity into relation identity. Two propositions can legitimately converge
on X without one thereby becoming a relation to the other:

```text
p ──in_respect_of──> X
O ──in_respect_of──> X          ≠          p ──in_respect_of──> O
```

And the pass carries §2's original D′ item — `toward(p, O)` **used as a stand-in in the payment
fixtures since Pm1 / Pm5 / Pm13, a relation used before it is ruled** — because once convergence is
refused, the only remaining source of *p → O* is a direct assertion, and that assertion's kind has
never been ruled. Neither D's clean *p → X* nor the fixtures' `toward` is D′'s foundation.

### D′.1 What is already fixed

| Ruling | Constraint on pass D′ |
|---|---|
| **Pass D** (§D.9) | `payment_in_respect_of(p, X)` — the asserted relationship, no funding / direction / amount / status; **no composition with toward or `obligation_in_respect_of`** (D8): *p ↔ X + O ↔ X ⇒ p → O* is refused, and its reverse; **D′ is a fresh question** |
| **Pass C** (§C.9) | `obligation_in_respect_of(O, X)` — no composition; several obligations may be in respect of one X (C4) |
| **Payment identity** (Pm1, Pm5, Pm13) | *toward O1* is **a claim about what the payment was for**, retractable, **does not establish discharge**; the payer may be anyone (Pm9); **S3**: a payment to the never-authorised servicer is a real payment *toward O1* by Rob's intent, no discharge; **S6**: a payment to E directly, uncredited — *toward O1*, no discharge |
| **Acknowledgment** (K1–K8, D4) | **P-ack for a payment = discharge of that payment, by definition** — *E's stated position about a payment*, subject E, object p, `as_of`; **K6**: a cleared bank payment is no evidence of acknowledgment; **K8**: acknowledgment and balance are two propositions; E only |
| **H2** | the ruled sequence *attached → attached/unacknowledged → E acknowledges → discharge → confirmed remaining changes*; `remaining` is an attached-payment **projection**, not discharge; moving it on attachment alone is too strong |
| **Servicing** (S1–S7) | payee ≠ entitlement; *a payment to Y may evidence D; it never establishes D* |
| **Obligation identity** (Ex6, Ob1) | **the mortgage has no expense** — an obligation with no X exists, and payments toward it exist (Pm1) |
| **1.x rows** | `DebtLedgerEntry` — attached-payment records, H2's projection input; `ExpenseFundingAllocation.attached` — the household's tie of a funding event to an expense (D11), **not** to an obligation |
| **Passes A / B** | `payment_counteracts`, `obligation_replaces` — no composition across kinds |
| **Prohibitions 1–12**; **K8**; **D21 / C7** (*a relation's direction and participant types do not establish temporal precedence between its endpoints*) | §1; hidden operand; permanent |

### D′.2 The convergence question — the case table, answered

Rob's rows, each run against the rulings, with two rows added (the insurer's payment; an obligation
with no X):

| Case | p → X | O → X | p → O | Why |
|---|---:|---:|---:|---|
| **D′-a** payment and obligation genuinely connected — the $382 Rob paid on Riverbend Hospital's bill for the ER visit | yes | yes | **not from the two arrows** — only if Rob (or a party) asserts *p toward O* | the connection is real *because Rob says so*; the arrows say only that both concern X |
| **D′-b** multiple obligations for X — Riverbend Hospital's O1, the radiologist's O2 (C4) | yes | yes, yes | **no** — any rule producing *p → O1* or *p → O2* **manufactures identity the premises do not contain** | the first pressure point: with two O's the derivation cannot even name its result |
| **D′-c** payment before the obligation exists — the deposit (D21) paid before Riverbend Hospital's balance obligation is minted | yes | later yes | **no** — order adds nothing; Riverbend Hospital may later *credit* the deposit (E's stance), Rob may later assert *toward* | temporal precedence is neither for nor against (D21 / C7) |
| **D′-d** payment satisfies something other than the obligation — **Lakeview Health pays Riverbend Hospital $568** (D18) for the ER visit; Rob's O is the $412 patient responsibility | yes | yes | **no — and a derivation would be *false***: Lakeview Health's payment is not toward Rob's obligation; Rob owes $412 regardless | the decisive counterexample: convergence produces a *wrong* p → O, not merely an unlicensed one |
| **D′-e** X merely the common economic subject — the HSA reimbursement (D9); the $30 copay paid at the desk before any bill existed (D3) | yes | yes | **no** — the reimbursement is not toward the bill; the copay was never toward O (O is for the remainder) | shared subject, no relation |
| **D′-f** explicit evidence identifies the obligation — Rob: *that was toward the mortgage*; Harbor's statement: *applied to loan 4471* | yes / — | yes / — | **potentially yes — from the assertion, never from the convergence**: Rob's utterance establishes; Harbor's line is a reading → a candidate; Harbor as a party may assert | the distinction Rob named: **shared semantic target** vs **identified obligation relationship** |
| **D′-g** an obligation with no X — the mortgage (Ex6); Rob: *I paid Harbor $1,412 toward the mortgage* (Pm1) | — | — | **yes, asserted** — and there is no X to converge on | the relation is needed where convergence is impossible: D′'s Ex8 |

**Answer to the question: nothing.** Shared-X convergence never establishes *p → O* — in D′-b it
cannot name its result, in D′-d its result is false, in D′-e it is unwanted, and in D′-g the
relation exists with no X at all. **The evidence boundary is the one every pass has drawn: a
relation between two identities exists when a party asserts it with both as operands, and a
reading yields at most a candidate.** Convergence is not a party and not a reading; it is two
claims by possibly different parties about possibly different things that happen to share a
referent.

**The four things Rob separated, and where each lives:**

| | What it is | Where it lives |
|---|---|---|
| **1. common referent** | p and O both concern X | two claims of two kinds (D, C); *nothing more* |
| **2. economic relationship** | p actually bears on the economic obligation — reduces it, was credited, discharged some of it | **E's acknowledgment** (K-cases, D4) and item 7's `remaining` — E's stance about p, never a relation the household or the substrate makes |
| **3. identity relationship** | evidence identifies *which* obligation p concerns | **a party's assertion with p and O as operands** — the relation D′ rules; a statement line naming the account is a candidate |
| **4. derived relationship** | the system infers p → O from other propositions | **refused** — prohibitions 8, 11, 12; D8; D′-b / D′-d |

None is silently interchangeable with another. In particular **2 ≠ 3**: E acknowledging p (2) is
not E asserting *p is in respect of O* (3) — the acknowledgment kind has subject E and object p,
and *which* obligation E applied it to is **not a participant of that claim** (§D′.4, a finding).

### D′.3 The `toward` stand-in, interrogated

Once convergence is refused, *p → O* comes only from an assertion — and the assertion's kind has
been `toward` in every fixture since Pm1, unruled. Taken as *semantics*, *toward* carries two
things the household's sentence may or may not mean:

| Implication | What it would assert | Why it fails as the kind |
|---|---|---|
| **direction of money** | money went *to* the creditor, reducing O | **D′11**: Harbor refunds an escrow overage — a payment (payer Harbor, payee Rob) *in respect of the mortgage*; the household's sentence is the same shape with the money the other way; D9's lesson on D′'s own case |
| **intent to reduce / discharge** | p was meant to pay O down | intent is the household's **content**, not the relation; S3 / S6 already separate intent from effect (*toward O1*, no discharge); the effect is E's acknowledgment (2 above) and `remaining` (item 7) — and a payment E *rejects* (returned, unapplied) was still asserted in respect of O |

What survives, on D′'s own cases, is the floor the pass expected to have to fight for: **p is
asserted as being in respect of O.** Not funded, not reduced, not applied, not discharged. That
D′ lands on the same floor as C and D — a third time, with the third participant pairing — is a
result for G (§D′.6); it is not why the floor was chosen.

### D′.4 A finding — the acknowledgment shape has a hidden operand

`acknowledged(E, p, as_of)` — the payment fixture's stand-in for D4 — has subject E and object p.
*Which obligation E applied p to* is nowhere in it: it rides on *E is E of O* (a role) and on
content (*applied to loan 4471*). Under K8 that is a hidden operand **when the acknowledgment is
read as establishing p → O** — which is exactly the derivation D′ refuses. The finding is
recorded, not fixed: the acknowledgment kind is a stand-in from the catalogue (item 7 territory);
D′ says only that **acknowledgment evidences a candidate for *p in respect of O* and never
establishes it**, and that when the catalogue rules acknowledgment it must decide whether O is a
participant or content. Nothing here changes D4's shape.

### D′.5 The cases

| # | Case | What must be sayable | What must not follow |
|---|---|---|---|
| **D′1 (Pm1, Ex6)** | *I paid Harbor $1,412 on 3/3 toward the mortgage.* No expense exists. | p minted; **p in respect of O1** — a claim with two established participants, asserted by Rob | no X is manufactured; no discharge; no `remaining` moved (H2); the claim needs no convergence |
| **D′2 (D′-a)** | The $382 on Riverbend Hospital's bill: p in respect of X (D); O in respect of X (C); Rob: *and it was toward the bill.* | three claims, three kinds | **p in respect of O is not derived from the first two** — it exists because Rob asserted it (D8's fence, now from D′'s side) |
| **D′3 (D′-b)** | X with O1 (Riverbend Hospital) and O2 (radiologist); p in respect of X. | p → X; O1 → X; O2 → X | **no p → O1 and no p → O2** — a rule producing either manufactures identity; Rob asserts *toward O1* or nothing |
| **D′4 (D′-c, D21)** | The deposit paid in April; the balance obligation minted in June; Riverbend Hospital's June statement credits the deposit. | p in respect of X; later O; Riverbend Hospital's *credited $500* — E's stance about p; Rob may assert p in respect of O | no p → O from order, from convergence, or from the credit; the credit is evidence (2), the assertion is (3). **PERMANENT** with D21 |
| **D′5 (D′-d)** | Lakeview Health pays Riverbend Hospital $568 (p′); p′ in respect of X; O (Rob's $412) in respect of X. | the two claims | **p′ in respect of O is not derived — and would be false**; nothing about O changes; Rob still owes $412 |
| **D′6 (D′-e)** | The HSA reimbursement; the $30 desk copay. | each in respect of X | neither is in respect of O; convergence with O → X produces nothing |
| **D′7 (D′-f)** | Harbor's statement: *payment received 3/5, $1,412, applied to loan 4471.* | a reading → **a candidate** for *p in respect of O1*; E's acknowledgment claim (D4) separately; Harbor **may assert the relation as a party** | the line establishes nothing; *applied* does not derive the relation; the acknowledgment does not derive it (§D′.4) |
| **D′8 (S3)** | Rob paid the never-authorised servicer $1,412 *toward the mortgage*. | p; payee S3 (a claim on p); **p in respect of O1** (Rob's intent as content) | no discharge; no entitlement of S3; E's acknowledgment never comes and the relation stands |
| **D′9 (S6)** | Rob paid Harbor directly; Harbor never credited it. | p in respect of O1; the bank's *cleared*; E's acknowledgment absent | the relation does not establish discharge; `remaining` is not moved; bank-says-yes / E-says-nothing stands unchosen |
| **D′10 — E rejects** | Harbor returns the payment as unapplied (a dated claim on p, REVERSAL C). | p in respect of O1 stands beside *returned as of d* | the relation is not withdrawn by E's rejection; no status on p or O |
| **D′11 — money the other way** | Harbor refunds a $210 escrow overage (payer Harbor, payee Rob): *that refund was on the mortgage.* | p″ minted; **p″ in respect of O1** — the same kind | the relation carries no direction of money; *toward* would misdescribe it; O1 acquires nothing |
| **D′12 — no cardinality, no allocation** | One cheque to Riverbend Hospital for two payment plans (O1, O2); twelve autopay payments toward one mortgage. | p → O1 · p → O2; p1..p12 → O1 | no allocation, split or order of satisfaction; no sum, no *paid down*, no `remaining` (H2 / item 7); cardinality is not allocation (D3 / D4's rule) |
| **D′13 (Pm13)** | *That March payment wasn't for the mortgage — it was the HELOC.* | `utterance_retraction`; a new claim to O2 | p, O1, O2 untouched |
| **D′14 — dispute** | Rob: toward the mortgage; Kim: toward the HELOC. | two claims — contested, derived | nothing chooses |
| **D′15 — composition, both neighbours** | O3 replaces O1 (B); p in respect of O1. And: p2 counteracts p1 (A); p1 in respect of O1. | the claims as asserted | **p in respect of O3 is not derived** (the refinance payment is Rob's to assert); **p2 in respect of O1 is not derived** (either direction, D15's rule) |
| **D′16 — vocabulary** | *toward* · *against* · *on* · *applied to* · *attached* · *for the bill* · *paid down*. | content; *attached* is the household's station name in H2's sequence — which this relation **is** | **not kinds**; *applied* is E's word (2); *paid down* is item 7's |
| **D′17 — the semantic floor** | *The $1,412 payment was in respect of the mortgage.* | exactly that | it does not establish that p was applied · credited · discharged anything · equalled the instalment · was on time · cleared · went to the entitled party · reduced `remaining` · was the only payment that month |
| **D′18 — direction fixed by type; no inverse** | Is *O in respect of p* a claim? | subject the payment, object the obligation, by type; no reverse claim | **no inverse kind** (`obligation_paid_by`, `obligation_receives`); navigation either way is a query; a resolver choosing *the* obligation for a payment is refused (D′3) |

### D′.6 Testing the readings

**PD′0 — derive p → O from convergence** (shared X; order; matching amounts; E's credit). Rejected
on every row of §D′.2: D′3 cannot name its result, D′5's result is false, D′6's is unwanted, D′1
has no X to converge on; prohibitions 8, 11, 12; D8 from D's side.

**PD′1 — one ruled kind with a payment subject and an obligation object**, meaning exactly *the
asserting party holds that the subject payment was in respect of the object obligation*, with the
floor of §D′.7. Every case representable; every "must not follow" a non-derivation the substrate
already refuses; D′5, D′6 correctly outside it.

**PD′2 — `toward` as the ruled semantics** (money to the creditor, intended to reduce it).
Rejected in §D′.3: D′11 refutes the direction; S3 / S6 / D′10 separate intent from effect; the
effect is E's (2) and item 7's.

**PD′3 — a claim about p with O in content** (*p was for the mortgage*). Rejected by K8; D′3, D′12,
D′14 unstatable.

**PD′4 — extend `payment_in_respect_of`'s object to obligations** (one kind, two typed object
slots, as `artefact_concerns` has). **Rejected here — not on the merits, on jurisdiction**: one
kind serving two object types *is* a decision that D and D′ share semantics, which is **G's**
(prohibition 12). D′ records that D and D′ share subject type and floor and differ in object type
— the mirror of C / D — and leaves the representation question to G. A distinct kind is the
conservative representation until then.

**PD′5 — fold it into acknowledgment** (E's *applied* = p → O). Rejected: different subject (E,
not p), different establisher (E only), a discharge consequence the relation must not carry, and
the hidden operand (§D′.4).

**PD′6 — several kinds by direction or station** (`payment_toward`, `payment_refund_on`,
`payment_attached`, `payment_applied`). Stopping rule inside the pass (D′11, D′16): direction is
p's payer / payee claims; *attached* / *applied* are stations of two different parties — the
household's assertion *is* attached, E's is acknowledgment. One kind survives.

**PD′7 — the 1.x `DebtLedgerEntry` shape** (an attached row with an amount that moves
`remaining`). Rejected: H2 — attachment alone moving `remaining` is the audit's finding; the row
is the projection's input, decomposable into p + this relation + claims on p.

**PD′8 — an obligation status** (*paid down*, *current*). Prohibition 7; item 7.

### D′.7 What the relation is — and is not

**The semantic floor.** The relation means only: **p is asserted as being in respect of O.** It
does not mean: *p was applied to O* (E's) · *p discharged some of O* (E's, by definition) · *p
reduced `remaining`* (item 7) · *money moved to O's creditor* (p's payee) · *p was intended to pay
O down* (content) · *p reached the entitled party* (S3 / S6) · *p was on time, in full, or the
instalment* · *p is the only payment in respect of O* · *O is the only obligation p is in respect
of*. It carries no payer / payee semantics and no station: **the household's assertion of this
relation is H2's "attached"; E's acknowledgment is a different claim by a different party.**

| The claim | *the subject payment was in respect of the object obligation*, as the asserting party holds — and nothing above the floor |
|---|---|
| **participants** | subject: the payment · object: the obligation — both **established**; no other slot; no X required anywhere (D′1) |
| **direction** | **fixed by participant type, not by meaning**; no reverse claim; **no inverse kind**; navigation either way a query; no resolver selecting *the* obligation (D′3) |
| **cardinality** | none ruled; cardinality is not allocation (D′12) |
| **who establishes** | any party's assertion, both endpoints established — the household (Pm1), the creditor (D′7), a servicer; a statement line, a matcher, E's credit or acknowledgment yields **candidates only** |
| **knowing** | `relational_knowing` **True with no designated relation → `undetermined`** — the payer of p? E of O? the obligor? none forced |
| **content** | opaque — *toward*, *against*, the instalment, the intent |
| **`as_of`** | permitted |
| **derives** | **nothing**: no discharge, application, credit or acknowledgment (D′8–D′10); no `remaining` (H2); no direction of money (D′11); no temporal order (D′4); no allocation or sum (D′12); no composition with `obligation_replaces` or `payment_counteracts` (D′15) or with D + C (D′2, D′3, D′5); no manufactured expense; no status on p or O |
| **what it is not** | not convergence (§D′.2); not acknowledgment (§D′.4, PD′5); not the ledger row (PD′7); not `payment_in_respect_of` with a wider object (PD′4 — G's) |
| **name** | a working name is needed; **not** `toward` (§D′.3), not *applied* / *attached* / *against*: **`payment_in_respect_of_obligation`** — distinct from D's kind by object type; the name records the mirror of C / D and asserts no family. *(If G rules that D and D′ are one kind with typed object slots, the name changes there, not here.)* |

**For G — the pattern is now complete on both axes.** C and D: same floor, same object type,
**different subject type**. D and D′: same floor, same subject type, **different object type**.
A and B: same-typed participants where the kind's meaning distinguishes the roles. Three floors
that read identically under participant substitution, and two that do not; whether the first
three are one semantic family or three that happen to share a phrase is exactly the stopping
rule's question — **inspected here, decided in G.**

### D′.8 Ruling candidate — pass D′, for Rob

> **Shared-X convergence establishes nothing. A payment's relation to an expense and an
> obligation's relation to the same expense are two claims of two kinds by possibly different
> parties, and no rule may produce a payment-to-obligation relation from them: with several
> obligations it cannot name its result, with an insurer's payment its result is false, with a
> reimbursement or a desk copay its result is unwanted, and with a mortgage there is no expense to
> converge on. The evidence boundary is the one every pass has drawn — a party's assertion with
> both identities as operands establishes; a reading, a statement line, a matcher, the creditor's
> credit or the creditor's acknowledgment yields at most a candidate; and convergence is neither a
> party nor a reading. Common referent, economic relationship, identity relationship and derived
> relationship are four different things: the first is two claims, the second is the entitled
> party's acknowledgment and item 7's remaining, the third is the relation ruled here, and the
> fourth is refused. That relation is one ruled kind, `payment_in_respect_of_obligation`, meaning
> exactly that the asserting party holds the subject payment was in respect of the object
> obligation — and nothing above that floor: not applied, credited, discharged, reduced, intended,
> on time, in full, exclusive, or moved in any direction. `toward` is rejected as the kind: it
> asserts a direction of money a creditor's refund contradicts and an intent-to-reduce that is
> content. Both participants are established; the payment the subject, the obligation the object,
> a direction fixed by type; no inverse kind; no cardinality and no allocation; established only
> by a party's assertion; knowing undetermined; deriving no discharge, no remaining, no status, no
> temporal order, no composition with any other ruled relation. The household's assertion of it is
> the "attached" station of the ruled acknowledgment sequence; the entitled party's acknowledgment
> is a different claim, whose own shape — whether the obligation is its participant or its content
> — is recorded as an open question for the catalogue and not decided here. Whether this kind and
> `payment_in_respect_of` are one kind with typed object slots is G's question; a distinct kind is
> the representation until G rules.**

**If ruled, the representation is one registry entry** — `PAYMENT_IN_RESPECT_OF_OBLIGATION:
subject (subject_payment_id) · object (object_obligation_id) · symmetric False ·
reading_establishes False · relational_knowing True, no knowing_relation` — both slots exist; a
fixture over D′1–D′18 and the absences (no convergence-derived row in any of D′2 / D′3 / D′5 / D′6;
no resolver choosing an obligation for a payment; no discharge, application or `remaining` from
the relation; no direction of money; no order guard; no composition with A / B / C / D; no
`obligation_paid_by` inverse); D′4 permanent beside D21; **the payment fixture's `toward` stand-in
retired truthfully into the ruled kind** (the one place a fixture changes shape — the stand-in was
this relation under an unruled name); `acknowledged` **stays a stand-in**, with §D′.4's finding
noted beside it; **no schema, no migration, nothing at family level**.

**What pass D′ leaves exactly where it found it:** acknowledgment's own shape (§D′.4 — the
catalogue's) · discharge and `remaining` (item 7) · the four determinations · `DebtLedgerEntry`
decomposition (blocked on Person rows) · the importer contract / standing authorisation (Pm10) ·
coverage (E / F) · the role catalogue (payer, payee, E, obligor) · G.

*The line: the payment was made; the debt is owed; that the one was for the other is what someone
said about the two of them — and that both were about the same visit is not that.*

### D′.9 Ruling — Rob, 2026-09-15: D′ closed at the semantic level

*The pass did not merely say "convergence is insufficient"; it demonstrated why no derivation
rule can safely cross that boundary.* The Lakeview Health example is decisive: *Lakeview Health's payment in respect
of X* and *O in respect of X* converge on exactly the same X, and *Lakeview Health's payment → Rob's
obligation* is **false** — not an epistemic weakness but a semantically unsound inference.

**The identity boundary, now crisp:**

```text
C/D:   claims establish common referent
E:     evidence can establish economic relationship
D′:    an assertion can identify the particular obligation
       convergence cannot manufacture that identity
```

*Convergence is neither a party nor a reading* — stronger than "not enough evidence": it says why
convergence has **no authority** to establish the relation.

**Rejecting `toward` is justified** — an important correction to what could otherwise become
accidental ontology: repeated use as the fixture stand-in does not make it the kind. The
separation: *p is in respect of O* — not *toward* O, not *reduced* O, not *applied to* O, not
*caused O's balance to change*; those are consequences, content or separate evidence, never
silently packed into the relation. The same floor surviving a third participant pairing is
evidence for G, not a reason to decide G early.

**The acknowledgment finding stays beside the ruling, unfixed** — if `acknowledged(E, p)` is used
as though it meant *E applied p to O*, O is a hidden operand; exactly the K8 participant / content
question that belongs in the catalogue, not patched locally. *Finding recorded; no implementation
change.*

**PD′4 is an especially important fence** — otherwise *does the relation exist?* becomes *what is
the ontology of its object slot?* `payment_in_respect_of_obligation` is a candidate, not a
decision; and G now has a coherent question:

```text
A/B  → same participant types, role semantics differ
C/D  → subject type changes
D/D′ → object type changes
```

**Disposition, verbatim:** *No convergence rule exists. Shared reference to X cannot establish
payment → obligation. A payment-to-obligation relation requires an assertion / evidence that
identifies the obligation; a reading may yield that assertion as a candidate, but convergence
itself has no evidentiary authority. `toward` is rejected as the semantic kind. The
acknowledgment participant / content issue is recorded for D4 and remains unfixed. Object-type
jurisdiction is deferred to G.*

**Implementation consequence, as specified — if / when the build is authorised:** one registry
entry; the payment fixture's `toward` stand-in becomes the ruled relation; `acknowledged` remains
a stand-in with its finding preserved beside it. **No E.** D′ closed at the semantic level; G has
a well-defined family question rather than a collection of unresolved local choices.

### D′.10 Build authorised — Rob, 2026-09-15: one safety improvement, four fixture protections

*Not reopening the semantic ruling; making sure the implementation cannot accidentally turn the
existence of the relation into a new inference engine.*

1. **The registry entry carries an explicit non-derivability boundary** — stated where the kind
   is defined, not in a document six months away from the join someone will otherwise write:
   *`payment_in_respect_of_obligation(p, O)` is assertable from evidence identifying both p and O;
   it is not derivable merely from `payment_in_respect_of(p, X)` + `obligation_in_respect_of(O, X)`,
   nor from any composition whose only shared operand is X.*
2. **The fixture proves non-selection, not just non-existence** — for every convergence case
   (D′2 / D′3 / D′5 / D′6): zero relation row, zero selected obligation, zero resolver choice. The
   dangerous implementation is not `insert(relation)`; it is `candidate = find_obligation_for_payment(…)`
   followed by a later derivation.
3. **The multiple-obligation case is mandatory** (D′3): *p → O1* absent, *p → O2* absent, and
   `selected_obligation(p) == none` — **the point is not that the system didn't happen to choose the
   wrong one; it must have no authority to choose one.**
4. **The Lakeview Health counterexample is a named permanent fixture** (D′5) — stronger than the generic
   ambiguity case: a known real-world interpretation makes the inferred relation *false*, not merely
   unknowable; it protects against *"we can safely infer it because usually the payment is related
   to the obligation."*
5. **Assertion is not a new evidence mechanism** — no `payment.obligation`, no
   `resolve_payment_obligation(payment)`; the relation stays boring — *p → O* — and the evidence /
   provenance machinery explains why the proposition exists. No smart resolver.
6. **The `toward` migration carries a migration-shape assertion** — every fixture use of `toward`
   that represented the D′ semantic case becomes the ruled kind; no unrelated use is silently
   reclassified (`toward` is broader / different; a global rename would be dangerous).

**Not waiting for G** — that would make the build hostage to a future family decision. The
jurisdiction fence preserved: *D′ authorises the distinct relation as the current ruled semantic
kind; G may determine whether it belongs to a broader relation-family representation; G must not
retroactively supply the semantics D′ refused to derive.* **Authorised: `payment_in_respect_of_obligation`
now, with the registry clause and the stronger convergence / non-selection fixtures. No E, no
schema, no family abstraction, no resolver, no new acknowledgment semantics.** G will decide
representation over already-tested relations rather than inferring what D′ meant from behaviour.

#### Built — 2026-09-15

`core/database.py`: `PAYMENT_IN_RESPECT_OF_OBLIGATION` with the **NON-DERIVABILITY** clause in the
constant's contract block (the smoke section asserts the clause is present beside the kind), and
the registry entry; both slots pre-existed; no guard change. Fixture
`tests/test_payment_in_respect_of_obligation_fixture.py` (41 checks, D′1–D′18): every convergence
case asserts `nothing_selected()` — no selector, resolver, convergence join or `Payment.obligation`
/ `Obligation.payments` accessor — beside the absent row; D′3 mandatory (two obligations, neither
chosen, no candidate list); **D′5 named PERMANENT** (Lakeview Health's payment and Rob's obligation converge
on X; the derived relation would be false; O untouched); D′4 permanent with D21; D′7 shows the
statement line as a candidate and the `acknowledged` stand-in deriving nothing (O is not its
participant — the §D′.4 finding beside it, unfixed); D′1 the mortgage with zero expenses; D′15 the
convergence join never made even after O1 is asserted in respect of X. Smoke
`s105_payment_in_respect_of_obligation.py`, **twelve** mutations caught, baseline re-established
after every undo: the label establishes · **CONVERGENCE DERIVES — the obvious join, both
directions** · a selector · a `Payment.obligation` accessor · **E's acknowledgment derives** ·
discharge derived · remaining moves · a D′4 order guard · the inverse kind · `obligation_replaces`
composes · **`toward` comes back as a kind** · the kind turns symmetric — **plus a static
migration-shape scan**: no fixture or smoke section uses `toward` as a proposition kind (prop /
kind= / kind==; comment lines skipped), prose uses untouched. **The `toward` stand-in retired into
the ruled kind in exactly its five D′-semantic uses** — payment fixture Pm1 and Pm5 (S3),
obligation_in_respect_of C15, obligation_replaces B3, payment_in_respect_of D8, and s104's chain
mutation — each check's wording updated to *toward rejected, never a kind*; the payment fixture's
slot check now names four ruled kinds and keeps `paid_by` as a stand-in. `acknowledged` untouched.
No schema, no migration, no family abstraction. Gate 1041 → 1069, 0 failed.

### D′.11 What D′ fixed, and what it did not — Rob, 2026-09-15 (the distinction to preserve)

*D′ fixed the concrete flaw and strengthened the architecture against recurrence. It has not
demonstrated that Groundwork needs a new general composition doctrine — and that is good news.*

| Concern | Status |
|---|---|
| shared-X convergence could manufacture *payment → obligation* | **fixed** |
| a resolver could secretly choose an obligation | **fixed / fenced** |
| a convenience accessor could reintroduce the inference | **fixed / fenced** |
| `toward` could accidentally become permanent ontology | **fixed for the D′ migration** |
| acknowledgment could silently establish the obligation relationship | **caught / fenced; D4 remains open** |
| object-type / family abstraction decided prematurely | **fenced; correctly deferred to G** |
| valid vs invalid relation composition lacks an established general doctrine | **not yet resolved** |
| evidence → candidate → proposition boundaries in general | **partially addressed; broader question remains** |
| identity semantics across the whole system | **not fully resolved** |
| lifecycle / evidence interaction | **not addressed by D′** |

**What changed:** before D′ one specific dangerous inference existed; now there is a semantic
ruling that it is invalid, a registry contract saying so, fixtures with the counterexamples, a
mandatory multiple-obligation test, the Lakeview Health counterexample, no resolver or accessor for it to
re-enter through, smoke mutations that try to introduce it, and migration protection around the
old terminology — *a real architectural repair, not documentation.*

**What did not change:** the general question *how does Groundwork know which compositions are
legitimate?* D′ answered one instance — *convergence is not enough to establish identity* — not
the class. **No giant composition doctrine is to be created because the pattern was noticed**;
the next step is to determine, from the A / B / C / D / D′ rulings as they stand, whether they
already provide the necessary rules — *find the hotspot → pressure-test it → determine whether
it is an actual gap → fix only the part that is actually unsupported.*

**One observation for that determination, recorded so it is not re-found:** the refusal of
composition across kinds appears in every pass as a *local* fence — A4 (no transitivity along a
chain), B11, C9, D8 / D15, D′15 and §D′.2 — while §1's twelve prohibitions state it nowhere in
general: prohibition 8 (no implied inverse) and 11 (no consumer derivation) are adjacent, not it.
The general rule exists today **only by accumulation** — the same shape §1 forbids for relation
*meaning*, here for a *prohibition*. Whether that is a doctrine gap or a one-line lift into §1 is
the question, not a conclusion.

---

## Pass E — Plan ↔ Expense · Obligation · Payment

**The question, applied:** when a household member says *the ER visit was on Kim's Lakeview Health plan*,
*the $412 a month is the premium for it*, or *that payroll deduction is the plan*, what is being
claimed, who can establish it, and what follows? Rob's framing carried from §2: **a very hard fence
around the word "coverage"** — Plan's existence answers none of *who is covered · when · whether an
expense is covered · whether the insurer owes a benefit · whether it paid · whether an obligation is
covered*; **Plan must not become a semantic magnet.** PLAN_IDENTITY §8's rule carried: *do not let
the existence of `Plan` pre-answer the meaning of "covered under"* — that is F's. And D′'s
invariant, now generalised in §D′.11's terms and applied here: convergence through a shared
identity establishes nothing.

Three pairings, each run from its own pressure — the plan-pressure was named in PLAN_IDENTITY §2
before any of them: **Pl9** (*which plan covered the ER visit?* — a relation claim or a consumer
derivation), **Pl7** (the premium — *"for P"* is a relation claim), and payment as the pairing
nobody named because the premium obligation was assumed to sit between them.

*Tightened 2026-09-15 after Rob's review (§E.9) — the five statements the record and fixture must
make demonstrably true: "in respect of" ≠ "covered by" · membership + person + date ≠ plan
attribution · shared person ≠ plan attribution · in-respect-of ≠ inverse / coverage · each pairing
independently necessary.*

### E.1 What is already fixed

| Ruling | Constraint on pass E |
|---|---|
| **Plan identity** (PL2, §7) | *a coverage arrangement the household individuates — its being covered under an insurer's product, not the product*; anchor impoverished; **"coverage arrangement" acquires no ontology by implication** — no ruled coverage relation, contract, enrollment, benefit or agreement object; identity ≠ currency (Pl5); identity ≠ truth (Pl12) |
| **The collapsing words** (PLAN_IDENTITY §2) | coverage ① = the plan · ② *who is under it, when* = a dated relation person ↔ plan, **F's** · ③ *whether a service is covered* = **the insurer's dated stance** (a term claim about P, or an adjudication about X — 4b) · benefit ② = adjudication · authorization = the insurer's stance about P with the service as content · responsibility = about X · premium = an Obligation and Payments, *"for P"* a relation claim · accumulator = the insurer's stance / a consumer derivation |
| **Pl9** | *which plan covered X*: **either a relation claim X ↔ P or a consumer derivation from membership-period claims and X's date claim** — the 1.x row's derivation is a consumer; **never a `plan_id` on X** |
| **Pl7 / Pl8** | the premium is never the plan; the employer's contribution is a claim about the employer party; the household's obligation is its share |
| **Pl11** | an authorization is never an expense and never a plan; tied to X later by `proposition_concerns` if a party ties it |
| **Pl12** | the insurer's retroactive termination is a dated stance; earlier stances stand as history; P remains minted |
| **4b** | adjudication is the insurer's dated stance about X; *what the household calls the claim is the expense*; the P-ack shape recurs and establishes no family |
| **Expense identity** | Ex8 — an incurrence with no plan involved at all; the 1.x row has *deliberately no `plan_id`* |
| **Passes C / D / D′** | `obligation_in_respect_of(O, X)`, `payment_in_respect_of(p, X)`, `payment_in_respect_of_obligation(p, O)` — three "in respect of" floors; **no composition across kinds; convergence through a shared operand establishes nothing** (§D′.2; A4, B11, C9, D8, D15, D′15) |
| **F, unopened** | membership — *Kim under P from d* — is F's own ruling; E may not use it, imply it, or derive from it |
| **About-ness** | `artefact_concerns(EOB, X)` and `artefact_concerns(EOB, P)` — a document concerning both relates neither |
| **K8**; **prohibitions 1–12**; **D21 / C7** (no temporal precedence from direction or type) | hidden operand; §1; permanent |

### E.2 The magnet, interrogated — what "under the plan" would smuggle

*The ER visit was under the Lakeview Health plan* is the household's sentence for all three pairings. Taken as
semantics, *under* carries four things, each already placed elsewhere and each refused as the kind:

| Implication | What it would assert | Where it actually lives |
|---|---|---|
| **covered** (coverage ③) | the service is covered — the insurer owes a benefit | **the insurer's dated stance** about P's terms or about X (adjudication, 4b); **E8**: a claim submitted under P and *denied* is still under P |
| **member** (coverage ②) | Kim was under P when X occurred | **F's** relation, unruled; **E3**: an expense adjudicated under P after the insurer retroactively ended coverage was still submitted under P |
| **terms applied** | P's deductible / coinsurance governed X's amounts | a **consumer derivation** over term claims and adjudications (item 7); the relation is the edge it traverses, not the arithmetic |
| **benefit paid** | the plan paid on X | the insurer's stance on X (Ex3 *plan paid*), or a payment identity the household mints (D18) — never the relation |

What survives, on E's own cases, is the floor: **the subject is asserted as being in respect of the
plan** — the arrangement it is asserted to relate to — nothing about whether that arrangement
covered it, admitted the person, governed the amounts or paid. That the floor is the one C, D and D′
reached is a result of E's cases and is recorded for G (§E.7).

**And the second magnet — the derivation.** Pl9's other reading, *derive which plan from
membership and the date*, is the 1.x approach and is item 7's to do as a **consumer**. It must not
manufacture the relation: *Kim under P during T* (F) + *X incurred by Kim on d ∈ T* ⇒ *X under P* is
convergence through Kim, the D′ invariant's shape exactly — and E2 (two plans on one date) shows it
cannot name its result, E3 (retroactive termination) shows its result is wrong, E5 (cash-pay) shows
its result is unwanted.

### E.3 Is there a relation at all — three pairings, each from its own pressure

| Pairing | Where the pressure comes from | Is anything else able to carry it? | Relation? |
|---|---|---|---|
| **expense ↔ plan** | Pl9's sentence — *the ER visit was on Kim's plan*: two operands | **no**: the derivation from membership + date cannot name its result with two plans on one date (E2 — Pl3 medical and dental with Lakeview Health, Pl14 Medicare + supplement), gives the wrong answer under retroactive termination (E3 — Pl12), and gives an unwanted answer for a cash-pay prescription (E5); the EOB concerning both X and P is about-ness (E6); the authorization is a stance about P (E7) | **yes — one kind**, asserted |
| **obligation ↔ plan** | Pl7's sentence — *the $412 a month is the premium for the plan*: two operands | **no**: a *premium* kind on O would put the plan in content (K8); a *cost* on P is a property the anchor refuses; the employer's share is a claim about the employer (E13); the insurer's own duty to the household (E14) is an obligation with the household as entitled party and needs the same tie | **yes — one kind**, asserted |
| **payment ↔ plan** | the payroll deduction where **no premium obligation was ever minted** (E17 — the household never individuated "we owe the premium"; it just comes out): two operands, no O to chain through | **no**: the D′-shaped chain *p in respect of O + O in respect of P* is unavailable (no O) and, where O exists, is refused as composition (E18); the bank line `AETNA PREMIUM` is a candidate (E21); the insurer's benefit payment and reimbursement need the same tie (E19, E20) | **yes — one kind**, asserted |

**So: three relations, each forced by a case nothing else in the ontology can carry — the Ex8 shape
three times** — and none forced by "the plan should know its expenses / cost / payments", which
is the magnet talking.

### E.4 The cases

| # | Case | What must be sayable | What must not follow |
|---|---|---|---|
| **E1 (Pl9)** | Rob: *the ER visit was on Kim's Lakeview Health plan.* | **X in respect of P** — two established participants, asserted by Rob | X acquires no *covered* / *in network* / *adjudicated*; Kim's membership is not established (F); P's terms are not applied; the plan is not said to have paid |
| **E2 (Pl3 / Pl14) — two plans, one date** | Medical and dental both with Lakeview Health; a dental cleaning on 4/2. Medicare + a supplement; one visit. | X in respect of P_dental (Rob); X in respect of P_medicare · X in respect of P_supp | **the membership-and-date derivation cannot name its result** — no rule produces either; **F's membership + X's date + incurred-by does not derive the relation** (convergence through Kim); no *primary / secondary* — that is content or the insurers' stances |
| **E3 (Pl12)** | X on 7/15 adjudicated under P; on 8/15 Lakeview Health says coverage ended 6/30 retroactively; adjudications reversed. | X in respect of P stands (it went under P); Lakeview Health's *ended 6/30 as of 8/15* is a stance about P; the reversals are stances about X | the relation is **not withdrawn** by the insurer's later stance; a derivation from membership would say "no plan" — wrong; *covered* was never in the relation, so nothing about it changes |
| **E4 (Pl14) — coordination** | One visit, two plans; each insurer adjudicates. | X in respect of P1 · X in respect of P2 | no cardinality; no priority; no netting of the two adjudications (item 7) |
| **E5 (Ex8)** | Kim's prescription bought cash at CVS; never submitted. | X; no plan | **no relation**; absence of a relation derives no *uninsured*, *not covered*, *out of network* |
| **E6** | The EOB concerns X (Rob) and concerns P (Rob); Group 12345 on it. | two `artefact_concerns`; the group number a correspondence candidate (Pl16) | **the relation is not derived** from a document concerning both (C11's shape); *plan paid $568* is the insurer's stance on X |
| **E7 (Pl11)** | Prior authorization for an MRI, 2/10 — a stance about P with the MRI as content. The MRI happens 3/1; Rob mints X; a party ties the authorization to X (`proposition_concerns`). | the stance about P; the about-ness tie; **X in respect of P is Rob's to assert** | not derived from the authorization; an authorization is never an expense, a plan or this relation |
| **E8 — denied, unpaid, cash-paid: the minimal-floor invariant** | Lakeview Health denies the claim for X: *not covered*; the plan pays nothing; Rob pays Riverbend Hospital in cash (p in respect of X, D). | X in respect of P (it was submitted under P); Lakeview Health's *denied* stance on X; *plan paid $0*; the cash payment | **`expense_in_respect_of_plan(X, P)` remains true when the plan denied the claim, paid nothing, and the expense was cash-paid** — so the relation is an association with the arrangement, not "covered by"; nothing on X or P changes; the structural reason the floor carries no coverage (B15 / D′5's role in E). *Contrast E5: never submitted → no relation at all* |
| **E9 — dispute; retraction** | Rob: *on Kim's plan*; Kim: *no — Rob's marketplace plan*. Later Rob retracts. | two claims, contested; `utterance_retraction` + a new claim | nothing chooses; X, P1, P2 untouched |
| **E10 — direction; no inverse** | Is *P in respect of X* a claim? Could `plan_covers_expense` exist? | subject the expense, object the plan, **fixed by type**; no reverse claim | **no inverse kind — and the obvious inverse name is the magnet word**; navigation either way is a query; no resolver choosing *the* plan for an expense (E2) |
| **E11 — the floor** | *The ER visit was in respect of the Lakeview Health plan.* | exactly that | establishes nothing about coverage, membership, adjudication, benefit, responsibility, network, terms or the plan year |
| **E12 (Pl7)** | *We owe $412 a month — the premium for the plan.* | O minted; **O in respect of P**; *premium* is a claim on O (its kind) or content | P acquires no *cost*; O acquires no *premium* status; "the plan costs $412" is a consumer's sentence |
| **E13 (Pl8)** | The employer pays 70% of the premium. | the employer's contribution is a claim about the employer party; the household's O is its share; O in respect of P | no total is derived; the employer's share is not a household obligation; nothing sums |
| **E14 — the insurer owes the household** | An out-of-network claim: Lakeview Health owes Rob $340 under the plan. Rob mints O′ (obligor Lakeview Health, entitled party the household). | **O′ in respect of P** — the same kind as E12's premium | *this particular obligation is in respect of this particular plan* — **never** *the plan covers this obligation*: *O → P* does not imply *P covers O* (the entire pass keeps coverage apart from in-respect-of); the relation carries **no direction of money** (D9's lesson) — *household owes insurer* (E12) and *insurer owes household* (E14) are both obligations in respect of P, and who owes whom is O's role claims; PL3 (the plan as a pair of obligations) stays rejected — O′ is one obligation the household individuated, not the plan's structure |
| **E15 — the magnet's favourite: "what the plan didn't cover"** | Riverbend Hospital's bill O ($412 patient responsibility) for X; Rob: *that's what the plan didn't cover.* | O in respect of X (C); *what the plan didn't cover* is content, or the insurer's PR stance on X; **O in respect of P is assertable** if Rob asserts it — and derives nothing | **not derived**: *X in respect of P + O in respect of X ⇒ O in respect of P* is convergence through X — refused (§D′.2); *didn't cover* is coverage ③ and lives with the insurer |
| **E16 (Pl13) — COBRA** | The household now pays the whole premium; same P or new P is the household's (Pl13); O_new minted. | O_new in respect of P (or P′); if P′ replaces nothing — plans are not obligations, `obligation_replaces` does not apply to plans | no composition with `obligation_replaces` (O_new replaces O? the household's, and it says nothing about P) |
| **E17 — the deduction with no obligation minted** | $412 comes out of every paycheque; the household never individuated "we owe the premium"; Rob: *that deduction is the plan.* | p minted (payer the household via the employer — a claim); **p in respect of P** — no O anywhere | no obligation is manufactured; no chain is needed or available |
| **E18 — with the obligation** | O (the premium) in respect of P; p in respect of O (D′). | the two claims | **p in respect of P is not derived** — composition through O refused; Rob may assert it |
| **E19 (D18)** | *Lakeview Health paid Riverbend Hospital $568 under the plan.* Rob mints p′ (payer Lakeview Health, payee Riverbend Hospital). | p′ in respect of X (D); **p′ in respect of P** (Rob) | not derived from the EOB's *plan paid* (a stance on X) nor from X in respect of P; no household party required on p′ |
| **E20 — reimbursement** | Lakeview Health pays Rob $340 (payer Lakeview Health, payee Rob). | p in respect of P; p in respect of O′ (E14) if Rob says so | no direction of money; no discharge of O′ (E's acknowledgment) |
| **E21 — the bank line** | `AETNA PREMIUM 412.00` — the feed. | a proposition with candidates; once p and P exist, a reading-sourced candidate | the label establishes nothing; *PREMIUM* proves no purpose |
| **E22 — timing** | The first premium paid in December for a plan starting January 1 — or P minted in March, retroactively, for a January arrangement. | p in respect of P, `as_of` permitted | **no temporal precedence** — *a relation's direction and participant types do not establish temporal precedence between its endpoints* (D21, C7, D′4). **PERMANENT** |
| **E24 — shared person ≠ plan attribution (MANDATORY)** | Kim is a member of P (an F-shaped stand-in claim); X is Kim's expense (*incurred by Kim*); **no evidence whatsoever connects X to P** — no submission, no EOB, no assertion. | the membership claim; the incurred-by claim; X | **no relation and no candidate from the substrate**: *person → plan* + *person → expense* ⇒ *expense → plan* is convergence through Kim — structurally D′'s mistake; membership must not become a universal carrier of plan attribution; whether a candidate generator may ever use membership is the fenced candidate-generation question, and this record licenses nothing |
| **E23 — vocabulary** | *under* · *on* · *covered by* · *through* · *premium* · *benefit* · *claim* · *in network*. | content, or claims on the subject, or the insurer's stances | **not kinds**; *covered by* is the magnet and is refused as a kind name and as semantics |

### E.5 Testing the readings

**PE0 — no relation: derive the plan** from membership + date (Pl9's second reading), from
about-ness (the EOB concerns both), from the insurer's role (*Lakeview Health is P's insurer and adjudicated
X*), or through O. Rejected: E2 cannot name its result, E3's result is wrong, E5's is unwanted;
prohibitions 3, 4, 11; §D′.2; E17 has no O; and K8 — the household's sentence has two operands.

**PE1 — three ruled kinds**, one per pairing, each with the floor *the asserting party holds that
the subject is in respect of the object plan*. Every case is representable; every "must not
follow" is a non-derivation the substrate already refuses; E5 and E15's derivation are correctly
outside.

**PE2 — *under* / *covered under* as the ruled semantics.** Rejected in §E.2: coverage ③ is the
insurer's, membership is F's, terms-applied is item 7's, paid is a stance or a payment; E8 (denied
yet under P) and E3 (terminated yet under P) are the counterexamples.

**PE3 — a claim about X (or O, or p) with P in content** (*X was on the Lakeview Health plan*). Rejected by
K8; E2, E4, E9 unstatable.

**PE4 — one generic `plan_relation` with the pairing named in content.** Prohibitions 1 and 4.

**PE5 — several kinds by context** (`expense_claimed_under`, `obligation_premium_for`,
`payment_premium_for`, `payment_benefit_under`, `payment_reimbursed_under`…). Stopping rule inside
the pass (E23): the contexts differ in **which side the money is on, and what the insurer said** —
claims on the subject, or the insurer's stances — not in what is claimed of the relation, who may
establish it, or what follows. Within each pairing, one kind survives.

**PE6 — fold it into about-ness** (the EOB concerns P; enough). Rejected: X is an identity with,
possibly, no document at all (E5's cash-pay has none; E1's visit may have none yet); C11's shape.

**PE7 — plan as subject: `plan_covers_expense`, `plan_costs`, `plan_paid`.** Rejected on two
grounds: direction is type-fixed and carries no meaning, so a plan-subject kind would be the same
claim with the magnet's name; and each name asserts exactly what the floor refuses.

**PE8 — one kind `in_respect_of_plan` with three typed subject slots** (as `artefact_concerns`
has typed object slots). **Rejected on jurisdiction, as PD′4 was**: one kind serving three subject
types *is* a decision that the three pairings share semantics — G's (prohibition 12). Three
distinct kinds are the representation until G rules.

### E.6 What the relations are — and are not

**The semantic floor, shared by the three on E's own cases.** Each means only: **the subject is
asserted as being in respect of the plan.** None means: *covered* · *a member at the time* ·
*submitted* · *adjudicated* · *in network* · *terms applied* · *the plan paid* · *the plan owes* ·
*the plan's cost* · *premium* (a claim on the obligation or payment) · *primary / secondary* ·
*the only plan* · *the only expense / obligation / payment for the plan*. Each of those is the
insurer's stance, F's relation, a claim on the subject, or item 7's derivation.

| | `expense_in_respect_of_plan` | `obligation_in_respect_of_plan` | `payment_in_respect_of_plan` |
|---|---|---|---|
| **participants** | subject the expense · object the plan | subject the obligation · object the plan | subject the payment · object the plan |
| **forced by** | E2 / E3 / E5 (derivation fails three ways) | E12 / E14 (nothing else carries *for P*) | E17 (no obligation to chain through) |
| **direction** | fixed by type, no meaning; no reverse claim; **no inverse kind — `plan_covers_*` is the magnet as a name** | same | same |
| **cardinality** | none; E4 — no priority | none; E13 — no sum | none; no allocation |
| **who establishes** | any party, both endpoints established — the household; the insurer (as a party); a reading, a group number, a label → candidates | same | same; **no household party required on p** (E19) |
| **knowing** | `relational_knowing` True, no designated relation → `undetermined` | same | same |
| **derives** | **nothing** — no coverage, membership, adjudication, network, terms, benefit; no *uninsured* from absence (E5); not withdrawn by the insurer's later stance (E3); no composition with C / D / D′ (E15, E18, E19); no temporal order (E22) | **nothing** — no cost on P, no premium status, no total (E13), no direction of money (E14), no composition (E15, E16) | **nothing** — no premium status, no discharge (E20), no direction of money, no composition (E18, E19), no manufactured obligation (E17) |
| **what it is not** | not Pl9's derivation (item 7); not about-ness (E6); not the authorization (E7); not `plan_id` | not the plan's structure (PL3 rejected); not the employer's contribution | not the premium obligation; not the insurer's *plan paid* stance |
| **content** | opaque — *under*, *primary*, *claim #* | opaque — *premium*, *COBRA* | opaque — *deduction*, *benefit*, *reimbursement* |
| **`as_of`** | permitted | permitted | permitted |

**Two invariants, stated as D′ stated its own:**

> **No `in_respect_of` relation in E licenses an inverse or coverage relation merely from its
> existence.** *expense → plan* does not yield *plan → expense*, *obligation → plan* does not
> yield *plan → obligation*, *payment → plan* certainly does not yield *plan → payment*; and
> none of the three yields *P covers …*. A mechanical inverse would not be the same claim in
> another order — it would have changed the semantics (E10, E14).

> **Shared person ≠ plan attribution.** *Kim under P* + *X is Kim's* ⇒ *X in respect of P* is
> refused (E24), as *Kim under P during T* + *X on d ∈ T* was (E2 / E3 / E5). Membership is F's
> relation and is never a carrier of plan attribution for expenses, obligations or payments.

**The general invariant this is becoming — recorded for G and for §D′.11's composition question,
not enacted as a doctrine:** *a relation must not be manufactured merely because its operands can
be connected through a shared person, entity, date, or other contextual fact.* D′ established it
for identity (convergence through X); E establishes it for plan attribution (convergence through
Kim, through X, through O, through a document). Every instance so far is the same shape.

### E.7 For G — the shape is now fully populated

| Kind | Subject | Object |
|---|---|---|
| `obligation_in_respect_of` (C) | obligation | expense |
| `payment_in_respect_of` (D) | payment | expense |
| `payment_in_respect_of_obligation` (D′) | payment | obligation |
| `expense_in_respect_of_plan` (E) | expense | plan |
| `obligation_in_respect_of_plan` (E) | obligation | plan |
| `payment_in_respect_of_plan` (E) | payment | plan |

Six "in respect of" floors, reached separately, each from a case nothing else could carry; subject
∈ {obligation, payment, expense}, object ∈ {expense, obligation, plan}; the same establisher rule,
type-fixed direction, no cardinality, nothing derived — beside A and B, whose same-typed
participants are distinguished by the kind's own role semantics. **Whether six kinds are one
relation with typed slots, three, or six is exactly the stopping rule's question — inspected in
every pass, decided in G.** E records the evidence; it neither generalises the kind (PE8) nor
lets the count decide.

### E.8 Ruling candidate — pass E, for Rob

> **There are exactly three plan relations, one per pairing, and each is a party's statement that
> an expense, an obligation or a payment is in respect of a plan — nothing about coverage.
> "Under the plan" is rejected as the semantics of any of them: it would assert that the service
> is covered (the insurer's stance — a denied claim was still under the plan), that the person was
> a member (F's relation — an expense adjudicated under a plan whose coverage the insurer later
> ended retroactively was still under it), that the plan's terms governed the amounts (a
> consumer's arithmetic) and that the plan paid (a stance, or a payment identity). Each relation
> is forced by a case nothing else carries: two plans on one date, where a derivation from
> membership and date cannot name its result; a premium the household owes, where "for the plan"
> has two operands; a payroll deduction the household never individuated an obligation for. Each
> is one ruled kind — `expense_in_respect_of_plan`, `obligation_in_respect_of_plan`,
> `payment_in_respect_of_plan` — meaning exactly that the asserting party holds the subject is in
> respect of the object plan. Both participants are established, the plan the object, a direction
> fixed by type; no inverse kind — and `plan_covers_*` is refused as a name because it is the
> magnet; no cardinality, priority, sum or allocation; established only by a party's assertion
> with both endpoints established — the household, or the insurer as a party; a reading, a group
> number, a bank label or an authorization yields at most a candidate; knowing undetermined. Each
> derives nothing: no coverage, membership, adjudication, network, applied terms, benefit, cost,
> premium status, discharge or direction of money; no "uninsured" from an absent relation; no
> withdrawal by the insurer's later stance; no temporal precedence; and no composition — not
> from membership and a date, not from a shared person, not through an expense, not through an
> obligation, not from a document concerning both, not from the insurer's role. None of the three
> licenses an inverse or a coverage relation merely from its existence; an obligation in respect
> of a plan is never "covered by" it, whichever way the money runs. An expense in respect of a
> plan remains so when the plan denied the claim, paid nothing, and the household paid cash. The plan is the object of six "in
> respect of" kinds' worth of evidence for G and decides none of it; whether the three are one
> kind with typed subject slots is G's question, and three distinct kinds are the representation
> until G rules. Nothing is minted, merged, covered or paid by any of the three.**

**If ruled, the representation is three registry entries** — `EXPENSE_IN_RESPECT_OF_PLAN: subject
(subject_expense_id) · object (object_plan_id)`; `OBLIGATION_IN_RESPECT_OF_PLAN: subject
(subject_obligation_id) · object (object_plan_id)`; `PAYMENT_IN_RESPECT_OF_PLAN: subject
(subject_payment_id) · object (object_plan_id)`; each `symmetric False · reading_establishes False ·
relational_knowing True, no knowing_relation` — all slots exist; a fixture over E1–E23 with the
absences (no `plan_covers_*` / `covered_by` / `plan_of_expense` / `which_plan` / `coverage_of`; no
membership derivation; no `plan_id`; no premium or cost on P; no composition through X, O or Kim; no
resolver choosing a plan; no order guard); **E8 the minimal-floor invariant** (denied, unpaid,
cash-paid — still in respect of P) and E3 as the coverage counterexamples, **E2 and E24 mandatory**
(two plans, neither chosen; shared person, nothing attributed), E22 permanent; **the plan fixture's Pl7 / Pl9 absence checks retired
truthfully** (the relations now exist; `plan_id`, `which_plan`, `plan_covers` still do not); **no
schema, no migration, no family abstraction, nothing from F.**

**What pass E leaves exactly where it found it:** membership / covered-under (F) · coverage
determination, accumulators, *which plan covered X* as a derivation, deductible met (item 7) ·
the term and adjudication catalogues · the resolver over the insurer's successive stances ·
`HealthPlan` / `TermVersion` decomposition · G.

*The line: the plan is the arrangement; the visit, the premium and the deduction are what
someone said were in respect of it — and whether it covered anything is what the insurer says.*

### E.9 Rob's review, 2026-09-15 — tightened before ruling

*E is to be scrutinised harder than D′, because "coverage" carries several concepts that are easy
to collapse.* Rob's five statements, and where each is now made demonstrably true:

| | Statement | Where |
|---|---|---|
| 1 | *"in respect of" ≠ "covered by"* | §E.2; **E8 strengthened** — the relation remains true when the plan denied the claim, paid nothing, and the expense was cash-paid; E5 by contrast (never submitted → no relation) |
| 2 | *membership + person + date ≠ plan attribution* | §E.2's second magnet; E2 (cannot name), E3 (wrong), E5 (unwanted); the fixture must make the derivation's absence explicit |
| 3 | *shared person ≠ plan attribution* | **E24 added, mandatory** — Kim under P, X is Kim's, no evidence connecting X to P → nothing; *person → plan + person → expense ⇒ expense → plan* is D′'s mistake in E's clothing; membership is never a universal carrier of attribution |
| 4 | *in-respect-of ≠ inverse / coverage relation* | the §E.6 invariant, in D′'s form — *no `in_respect_of` relation in E licenses an inverse or coverage relation merely from its existence*; E10; **E14 sharpened** — *O → P* never implies *P covers O*, and money direction does not determine the relation (E12 and E14 are both obligations in respect of P) |
| 5 | *each pairing independently necessary* | §E.3 — the Ex8 method: *what proposition still needs to exist when every tempting chain is removed?* E2, E12 / E14, **E17** (the deduction with no obligation to smuggle through) |

**Not changed, on Rob's instruction:** the three relations are **not collapsed** — subject ∈
{expense, obligation, payment}, object plan; one polymorphic relation vs three, and the six-way
question, belong to G. *Don't let the fact that the pattern is becoming obvious cause a premature
abstraction.*

**The larger reason for the scrutiny, recorded:** *D′ proved Groundwork must not manufacture
identity from convergence; E tests whether it will manufacture plan association from membership /
convergence.* With both doors closed the general invariant accumulates without a composition
doctrine — *a relation must not be manufactured merely because its operands can be connected
through a shared person, entity, date, or other contextual fact* — and that is among the most
important things to preserve going into G.

### E.10 Ruling — Rob, 2026-09-15: E ACCEPTED as written at `54a24a3`; no build from E

*The tightening addressed the two places where E was most vulnerable, and did so without quietly
turning the pressure-test findings into a new derivation doctrine. `54a24a3` closes the actual
semantic questions raised by the pass rather than documenting that the implementation happens to
behave correctly.*

**What is settled:**

1. **The floor is genuinely weaker than coverage.** E8 is the critical test — submitted under P,
   denied, paid nothing, cash-paid, and `expense_in_respect_of_plan(X, P)` can still be true: an
   attribution / association claim, not a disguised `covered_by`. **E5 is the necessary lower
   boundary** — never submitted means no basis for the relation; without it *in respect of* could
   have become "somehow associated with a plan".
2. **The membership trap is explicitly closed.** E24 — *member → plan + person → expense ≠
   expense → plan* — and the result is not "the implementation happens not to derive it": the
   fixture requires **no relation and no candidate**. Fencing the candidate-generator question
   separately is correct: E must not answer a future question about candidates because it needs to
   establish that this substrate cannot establish the relation.
3. **Shared-person convergence is demonstrably rejected** — the plan-domain analogue of D′. The
   pattern is becoming clear: *A → X, B → X, therefore A → B* is not a relation rule. E24 shows it
   with a person as the shared node; D′ with an expense. Useful pressure without prematurely
   turning the observation into a universal composition rule.
4. **Inverse semantics are properly fenced** — the §E.6 invariant; and E14 makes money direction
   concrete: *household owes insurer* and *insurer owes household* are the same relational kind
   despite opposite monetary direction, so "obligation to plan" can never become a synonym for
   "plan owes / charges / covers obligation".
5. **The three E relations have earned their existence independently** — each has an Ex8-shaped
   case where it remains meaningful without the other two. G is not being asked to rescue an
   under-specified E; G can genuinely answer *one relational family, or three distinct relations?*

**Two statements the acceptance keeps apart:**

> **Established by E:** these three subject / object relationships are semantically warranted by
> independently constructed cases.
>
> **Not established by E:** that they constitute one relation family, compose with one another,
> or share a generic typed relation mechanism. — G's.

Nor does E establish *membership + person + date → expense_in_respect_of_plan*, or
*expense_in_respect_of_plan → plan_covers_expense*, or *expense_in_respect_of_plan +
obligation_in_respect_of → obligation_in_respect_of_plan* — precisely the things E demonstrated
are not licensed.

**Carried forward, not reopened:** *what exactly is the identity of P?* The plan is an object
distinct from insurer, person, expense, obligation and document; G / document-identity work can
determine the structural implications. E's job was to establish that when P is known, the three
relations have legitimate floors and that contextual convergence cannot manufacture them — done.

**Disposition — E: ACCEPTED.** Not to be done: another case; a change to the three candidates;
opening F; **implementation from E.** The handoff:

```text
E establishes:
    expense    → plan
    obligation → plan
    payment    → plan

E rejects:
    membership / date / person convergence
    shared-person attribution
    inverse-from-existence
    coverage-from-in-respect-of
    money-direction as relational meaning

E does not decide:
    whether the three relations are one family
    whether / how they compose
    typed-slot architecture
    candidate-generation doctrine

                 ↓
                 G
```

*A properly bounded pass; G owns the structural question.*

### E.11 The boundary, stated — Rob, 2026-09-15 (the stopping point)

*Semantically clean rather than merely implementation-clean.* Four things kept visibly separate:

```text
E:      what does expense / obligation / payment → plan mean?          CLOSED (accepted, unbuilt)
F:      what does covered-under mean?                                  NOT OPEN
D′.11:  what, if anything, permits composition across relation kinds?  OPEN QUESTION
G:      what structural family / representation should the ruled
        relations have?                                                NOT OPEN
```

**The failure mode this prevents:** using G's eventual representation to retroactively justify
D′.11's composition semantics. *That several relations eventually look like members of an
`in_respect_of` family cannot itself establish that they compose; conversely, that they currently
have separate registry identities does not establish that they must remain structurally
unrelated.*

**Why D′.11 has become more significant:** E independently reproduced the same kind of boundary.
D′ showed *payment → expense + obligation → expense ≠ payment → obligation*; E shows *person →
plan + person → expense ≠ expense → plan* — while also establishing the legitimate direct
relations *expense / obligation / payment → plan*. The record is accumulating examples of both
legitimate relations and illegitimate convergence **without a general composition doctrine** —
exactly where the system should be before the next semantic question is opened: evidence that
composition matters, no premature generalisation of the answer.

**And 1069 green does not settle D′.11.** The tests demonstrate the rulings already encoded; they
do not turn the cross-kind composition question into a closed doctrine.

**The tree is left exactly here:** E accepted · nothing built · F unopened · G unopened · D′.11
carried as an explicit unresolved semantic question. *"G owns the structural question" identifies
where that question belongs once the ordered work reaches it; it is not authorisation to open G.*

**The architectural guard, now explicit (Rob):** *representation cannot become evidence for
semantics after the fact.* Nothing is to be opened opportunistically; the next move follows the
recorded order, with D′.11 available as a *constraint* rather than silently becoming doctrine. A
productive stop: the known semantic surface is settled, the unresolved boundary is named, and
there is no implementation artefact capable of accidentally answering it.

---

## Pass F — Covered-under / membership

**The question, applied — the recorded order's next move, not an opportunistic one:** what does
*covered under* mean? When a household member says *Kim's on my work plan*, *the baby was added
from her birth date*, *Lakeview Health says Kim was never eligible*, what is being claimed, who can establish
it, and what follows? Rob's framing carried from §2: **its own semantic ruling, never an automatic
consequence of Plan + RP2** —

```text
Plan identity → meaning of covered-under → party / Plan relation → temporal boundary kinds → later consumers
```

**not** *Plan exists + temporal grammar exists → membership exists.* ROLE_PERIOD R10 carried: `Plan`
supplies the endpoint and the `as_of` machinery and **no meaning**; PLAN_IDENTITY §8 carried: *do
not let the existence of `Plan` pre-answer the meaning of "covered under"*; E24 carried from the
other side: F's relation is never a carrier of plan attribution for an expense.

The order inside the pass follows the arrow: §F.2 the meaning, §F.3 the relation, §F.4 the
boundary kinds, §F.5 what consumers are left.

*Tightened 2026-09-15 after Rob's review (§F.9): the floor made structural — "P is under Q at the
date the assertion concerns" — in place of the elastic "one of the persons the arrangement is
for"; F5 restated as an evidence boundary, not objective eligibility; the name `under_plan`; F20
the two-plan non-selection case.*

### F.1 What is already fixed

| Ruling | Constraint on pass F |
|---|---|
| **Plan identity** (PL2) | *a coverage arrangement the household individuates*; **membership is not smuggled onto the anchor** — not a field on `Plan`, `Person` or the expense (§8); Pl6: *Kim under P₁ from d* is a dated relation person ↔ plan, *item 5's shape with a non-party endpoint*; Pl15: a plan with no claims — **no members known is the absence of claims** |
| **The collapsing words** (PLAN_IDENTITY §2) | coverage ② = *who is under it, when* = **this pass**; coverage ③ = whether a service is covered = the insurer's stance; benefit, authorization, responsibility, premium, accumulator — placed elsewhere |
| **Role period** (RP2, ruled and built) | a role has no intrinsic period; *holds at d · begins at d · ends at d* are three sorts of proposition; boundary kinds are bound to a ruled role kind by registry metadata (`boundary`, `of`) under a **structural** guard — same participants, a role not a boundary, never symmetric, a reading never establishes, `as_of` required; a boundary never rewrites, implies its opposite, resolves, establishes continuous effect or creates a role; retraction ≠ ending; overlap represented, never resolved; *in effect on d* is a derivation (R9, item 7). **No role kind is ruled; the registry carries no boundary metadata** — `standin_covered_under` in the fixture *is not "covered under"* |
| **R10 / R11 / R3 / R5 / R7** | the endpoint and grammar for *Kim is covered under the work plan* exist; the card line is P-subject (reading → candidate); T4 / T8 — Lakeview Health's *ended 6/30* learned 8/15; Lakeview Health vs household on the ending = a dispute, derived; overlap detectable, never resolved |
| **Party reference** | roles are dated relations over parties, never parties; a party is a household `Person` or a minted party (a dependent who is not a Groundwork Person is minted under the household's utterance, as the mother was in Pm9) |
| **Pass E** (accepted) | `expense / obligation / payment → plan` are attribution claims; **shared person ≠ plan attribution** (E24) — *Kim under P + X is Kim's ⇒ X under P* is refused; E's relations say nothing about who is a member |
| **4b** | *eligible*, *enrolled*, *member since*, *terminated* are the insurer's dated stances and identifiers — content, evidence, propositions; the insurer mints nothing |
| **Correspondence; about-ness; K8; prohibitions 1–12; D21 / C7** | never one referent; a card concerning Kim and P relates neither; hidden operand; §1; no temporal precedence from direction or type |

### F.2 The meaning — interrogated before the relation

*Kim is covered under the work plan.* Four senses hide in the sentence; three are already placed
and refused as the meaning:

| Sense | What it would assert | Where it lives |
|---|---|---|
| **covered** (③) | services rendered to Kim are covered — the insurer owes benefits | **the insurer's dated stances** about P's terms or about an X; **F5**: Lakeview Health's *never eligible* and its denials leave the household's *Kim is under P* standing as a claim |
| **enrolled** | the insurer's records list Kim | **the insurer's stance / record** — *member since 01/01/2026* is P-subject content (R11); a party's assertion, including the insurer's as a party, establishes; the record does not |
| **the subscriber** | the plan is Kim's — her employment carries it | a **different role**: who holds the arrangement (and owes the premium — E12's obligor) is not who is under it; **F10**: Rob is the subscriber, Kim a dependent, both are under P |
| **premiums paid / in good standing** | the arrangement is current for Kim | E12's obligation and its payments; *current* is a status (prohibition 7) |

What survives is narrower than any of those and is the relation itself, not an interpretation of
it: **the asserting party holds that the person is under the plan at the date the assertion
concerns.** *Under* here names the asserted relationship between this particular person and this
particular plan — independent of what the insurer believes about eligibility or coverage — and
nothing more: not that anything is covered, not that the insurer agrees, not that the premium is
paid, not that the person is the subscriber, not that the person is beneficiary, dependent,
enrolled, eligible, or merely named in a document. ("One of the persons the arrangement is for",
the first draft's phrase, was elastic enough to cover several of those roles; it is withdrawn.) **Plan's existence contributes the endpoint only** (R10): a plan
with no such claims has no known members (Pl15), and a claim of this kind about a plan says nothing
about the plan's terms, period or product.

### F.3 The relation — a role, party ↔ plan

**Is there a relation at all?** *Kim is on the work plan* has two referential operands — a party
and a plan — and nothing else in the ontology can carry it: not a field on `Plan` (§8), not a field
on `Person`, not E's relations (an expense under P is not a person under P; E24 refuses the
inference both ways), not the insurer's record (4b), not `Plan`'s existence (R10). K8 makes it a
two-participant claim. **It is a role in RP2's sense** — a dated relation over a party — and so
the first *ruled* role kind.

| The claim | **the asserting party holds that established person P is under established plan Q at the date the assertion concerns** |
|---|---|
| **participants** | subject: the person — structurally a **party**: a household Person's party, or a minted party standing for an individual the household names (F16, the ex-spouse who is not a Groundwork Person; Pm9's shape) · object: the plan — both **established**; the household party as such is not under anything: persons are (F11) |
| **direction** | fixed by type — party subject, plan object — RP2's role shape; no reverse claim; **no inverse kind** (`plan_covers_party`, `plan_members` — the magnet as a name, as in E10); **no resolver selecting *the* plan for a person** (F20) |
| **cardinality** | none: a party under several plans (R7 overlap, Pl14); a plan with several parties (F10); none is exclusive |
| **who establishes** | any party's assertion, both endpoints established — the household (R1); **the insurer as a party** (its enrollment statement, asserted); a card, a portal, a member ID → **candidates only** (R11) |
| **temporal sort** | the role claim is **holds at d** (R1: nothing about since when); *began* / *ended* are §F.4's kinds |
| **knowing** | `relational_knowing` True with no designated relation → `undetermined` — the party itself? the insurer? the subscriber? none forced |
| **content** | opaque — *dependent*, *spouse*, *via my employer*, the member ID |

### F.4 The boundary kinds — RP2 applied to a ruled role for the first time

*Kim's been on the work plan since January 1* · *Lakeview Health's letter: coverage ended June 30.* With a
ruled role kind, RP2's machinery is finally bound to something real: **two boundary kinds**, each a
proposition in its own right with `as_of` the date it is about and its own provenance and
`created_at`, registered with `boundary = began / ended` and `of = the role kind` — the structural
guard already built (`_registry_problems`, `_boundary_violations`) doing exactly what it was
authorised to do and no more. The ruled temporal grammar, now with a subject:

| | Kind | Meaning | Does **not** |
|---|---|---|---|
| holds at d | `under_plan` | the person is under the plan, as of d | imply a beginning or an ending |
| begins at d | `under_plan_began` | the party came under the plan on d, as asserted | rewrite a prior *holds*; imply an ending; create the role (a *began* with no *holds* is a claim like any other — R12's mirror) |
| ends at d | `under_plan_ended` | the party ceased to be under the plan on d, as asserted | imply the beginning; resolve a dispute (R5); establish that nothing was covered after d (③ is the insurer's); withdraw earlier claims (T4 / T8) |

**Retraction ≠ ending, pinned again on the real kind:** retracting *Kim was covered beginning
January 1* is about the assertion; Lakeview Health's *coverage ended June 30* is a boundary claim, not a
retraction. And **a period is never written** — *from March to June* is two boundary claims (R2);
*was Kim under P on 5/12?* is a derivation (R9, item 7).

### F.5 The cases

| # | Case | What must be sayable | What must not follow |
|---|---|---|---|
| **F1 (R1)** | January: *Kim is on the work plan.* Nothing about since when. | **Kim `under_plan` P**, as of the stance date — a role claim with two established participants | no beginning is implied; no ending; P's terms are not applied to Kim; nothing is covered by it |
| **F2 (R2 / R11)** | *Kim's been on it since January 1.* The card: *Member since 01/01/2026.* | `under_plan_began`, `as_of` 2026-01-01, asserted by Rob; the card line is P-subject → a candidate for the same claim | the card establishes nothing; the insurer's *member since* is its stance; the beginning implies no ending |
| **F3 (R3, T4 / T8)** | August 15: Lakeview Health's letter — coverage ended June 30. | `under_plan_ended`, `as_of` 2026-06-30, recorded 8/15; the *began* and *holds* claims stand; a reader asking what the record held on 7/1 sees them | **no row rewritten**; nothing about ③ follows — whether July's visit was covered is the insurer's adjudication, not this boundary's consequence |
| **F4 (R5)** | Lakeview Health: ended 6/30; the household: it ran through December. | two `ended` claims (or an `ended` and a later `holds`), different parties | a **dispute, derived**; nothing chosen; no "current membership" |
| **F5 — the meaning invariant, stated as an evidence boundary** | Lakeview Health: *Kim was never eligible* — rescinds, denies every claim, refunds nothing. Rob: *she was on my plan all year.* | Rob's `under_plan` claims stand as his assertions; Lakeview Health's *never eligible* is its own stance about Kim and P — a competing claim, contest derived | **an assertion that Kim is under P does not cease to be an assertion of the `under_plan` relation merely because another party asserts that Kim was ineligible** — an epistemic / evidence boundary, **not** a declaration that the relation is true regardless of eligibility, and not a system-level truth overriding contradictory evidence; the proposition / evidence discipline holds both claims and chooses neither (E8's role in F); nothing is unminted |
| **F6 (R6)** | *I was wrong — Kim was never on the work plan; that was the dental.* | `utterance_retraction` of the utterance behind the claim; a new claim about the dental plan | **not an ending**; the history that it was believed survives; P and Kim untouched |
| **F7 (R7 / Pl14)** | Kim under P₁ from 1/1; under P₂ from 7/1; no ending on P₁. Medicare + a supplement. | two `began` claims, two plans | **overlap represented, never resolved**; not tied by which row was written first; no *primary* |
| **F8 — the newborn** | The baby, born 4/3, is added; the insurer backdates to the birth. Rob enters it 5/2. | a new party (a Person, or minted); `covered_under_began` `as_of` 2026-04-03, `created_at` 5/2 | no temporal precedence from creation order (D21 / C7 — the party may be minted after the date it came under P); nothing derives *eligible since birth* |
| **F9 — COBRA (Pl13)** | The household leaves the employer; COBRA continues the same product. Same P or new P is the household's. | if the same P: the role continues — no claim needed, or a *holds* stance; if a new P′: `under_plan` P′ from d, `under_plan_ended` P as asserted | the substrate infers neither arm; *continuation* is the insurer's word; E16's obligation change says nothing about membership |
| **F10 — subscriber ≠ under** | Rob's employment carries the plan; Rob, Kim and the children are under it. | four `under_plan` claims; *subscriber* is content, or a later role kind; the premium is Rob's obligation (E12) | **the subscriber role is not this kind** and is not derived from it; being under P does not make anyone the subscriber; the obligor of the premium is not thereby "more covered" |
| **F11 — persons, not the household** | *We're all on the Lakeview Health plan.* | one `under_plan` claim per person the household names; the household party (Rob's) is under P as Rob, not as "the household" | no household-level membership; no claim is manufactured for a person nobody named |
| **F12 (Pl15)** | *We have a plan* — no members entered. | P with no `under_plan` claims | **no members known is the absence of claims** — not *no members*, not *Rob by default* |
| **F13 (E24 from F's side)** | Kim under P during T; X is Kim's, incurred on d ∈ T. | the role claim; X | **nothing about X follows** — no `expense_in_respect_of_plan`, no candidate from the substrate; F is never a carrier of plan attribution |
| **F14 — the reverse** | X is asserted in respect of P (E1); nobody has said who is under P. | E's claim | **no membership is derived** from an expense being under P — *X under P + X is Kim's ⇒ Kim under P* is convergence through X, refused as D′ refused it |
| **F15 — the insurer asserts** | Lakeview Health's enrollment confirmation, as a party: *Kim enrolled effective 1/1.* | Lakeview Health **may assert** `under_plan_began` as a party; from a reading it is a candidate | knowing undetermined; the insurer's assertion does not outrank the household's (contest is derived) and does not establish ③ |
| **F16 — the ex-spouse** | Rob's ex-spouse remains on the plan by court order; not a Groundwork Person. | a minted party (Pm9's shape); `under_plan` P | no Person is manufactured; the subject slot takes any established party |
| **F17 — direction; inverse; resolver** | *P has Kim*? `plan_members(P)`? *the* plan Kim is under? | subject party, object plan — by type; a query either way | **no inverse kind, no `members_of` / `current_plan_of` accessor that selects** — with F7's overlap a selector would manufacture a choice (D′3's rule) |
| **F18 — vocabulary** | *on the plan* · *under* · *enrolled* · *eligible* · *member* · *dependent* · *subscriber* · *active* · *terminated*. | content, or the insurer's stances, or a later role kind | **not kinds**; *active* / *terminated* are statuses (prohibition 7) — *terminated* becomes an `ended` claim only when a party asserts the ending |
| **F19 — the floor** | *Kim is under the Lakeview Health plan as of March.* | exactly that | establishes nothing about coverage of any service, enrollment in the insurer's records, the subscriber, the premium, the plan's terms, a beginning, an ending, or any expense of Kim's |
| **F20 — two plans, one person, one period (MANDATORY)** | Kim is asserted under P₁ and under P₂ for the same period — the employer plan and Rob's marketplace plan both list her; or Medicare and a supplement. Nothing about Kim's person, employment, dates or the insurers selects one as *the* plan. | **two separately asserted `under_plan` claims** — if both are actually asserted | **no resolver selects one** (`current_plan_of(Kim)`, `plan_of_person`, `primary_plan`) — with two plans a selector would manufacture a choice the assertions do not contain (D′3's rule; E2's pressure from the person's side); no *primary / secondary* (the insurers' stances or content); no exclusivity; F7's temporal overlap is the same case seen through the boundaries |

### F.6 Testing the readings

**PF0 — membership from Plan + RP2** (*the plan exists and the temporal grammar exists, therefore
membership exists*) — Rob's named trap. Rejected: R10 and PLAN_IDENTITY §8 by ruling; F12 (a plan
with nobody under it); the grammar binds to a *ruled* role kind and there was none — F rules one.

**PF0′ — membership from the insurer's record, the card, or the portal.** Rejected: 4b, R11 —
readings yield candidates; the insurer as a *party* may assert (F15).

**PF1 — one ruled role kind, party subject / plan object, with two bound boundary kinds**, meaning
exactly *the subject party is one of the persons the object plan is for, as the asserting party
holds, at the date the stance is about*. Every case representable; every "must not follow" a
non-derivation the substrate refuses; F12, F13, F14 correctly outside.

**PF2 — *covered under* as coverage ③** (Kim's services are covered). Rejected in §F.2; F5 is the
counterexample (never eligible, nothing covered, still under P as asserted).

**PF3 — membership as an attribute** (`members` on `Plan`; `plan_id` on `Person`; a membership
table with a period). Rejected: PL2 §8, RP1 (a period never written), the anchor discipline; F7's
overlap and F4's dispute are unrepresentable as attributes.

**PF4 — several kinds by the insurer's vocabulary** (`enrolled_in`, `eligible_under`, `member_of`,
`dependent_of`, `subscriber_of`). Stopping rule inside the pass (F18): *enrolled / eligible / member*
differ in **whose stance** — the insurer's — not in what is claimed; *subscriber* is a **different
role** (F10) and is left to the catalogue, not folded in; *dependent* is content. One kind.

**PF5 — a claim about Kim with P in content** (*Kim is on the Lakeview Health plan*). Rejected by K8; F7 and
F4 unstatable.

**PF6 — fold it into E** (Kim's expenses under P ⇒ Kim under P; or the reverse). Rejected: F13 /
F14 — convergence through X or through Kim, both directions, as E24 and D′ refused.

**PF7 — the household as the subject.** Rejected: F11 — persons are under plans; the household party
is Rob's party and Rob is under P as a person.

### F.7 What the relation is — and is not; what consumers are left

**The semantic floor.**

```text
under_plan(P, Q)

means:   the asserting party holds that established person P
         is under established plan Q at the date the assertion concerns.

and from that relation alone, NOT:
         enrolled(P, Q)                       eligible(P, Q)
         subscriber(P, Q)                     covered(X, Q)
         expense_in_respect_of_plan(X, Q)     obligation_in_respect_of_plan(O, Q)
         payment_in_respect_of_plan(M, Q)     active_plan(P, Q)
         paid_premium(P, Q)                   plan_covers(P, Q)
         P is under no other plan             Q's terms apply to P
```

Nor does it derive either endpoint, cardinality, temporal continuity, or any consumer conclusion.
The boundary kinds mean only that the role began / ended on the date asserted, as asserted, and
imply neither the opposite boundary nor anything about ③. **The name is non-authoritative** —
`under_plan` is authoritative because of this ruling, as `payment_counteracts` is, not because of
the English word.

| | `under_plan` | `under_plan_began` | `under_plan_ended` |
|---|---|---|---|
| **slots** | `subject_party_id` · `object_plan_id` | same | same |
| **registry** | `symmetric False · reading_establishes False · relational_knowing True`, no `knowing_relation` | same + `boundary: 'began' · of: 'under_plan'` | same + `boundary: 'ended' · of: 'under_plan'` |
| **`as_of`** | permitted (the date the stance is about) | **required** (the guard) | **required** |
| **derives** | nothing (§F.2) | no ending; no prior rewrite; no role | no beginning; no resolution; no ③; no withdrawal |

**Name — `under_plan` (Rob, §F.9).** The item has carried *covered-under* through R10, PLAN_IDENTITY
§2 / §8 and BUILD_QUEUE as the name of coverage ② — and that is exactly why the ruled kind is not
called that: `covered` already has a separately established meaning in this domain, and the kind
would carry the lexical magnet F spent the pass dismantling (E10 refused `plan_covers_*` on the same
ground). The semantics table does the work; the boundary kinds follow the role's name.

**Consumers left where they are (item 7):** *in effect on d* (R9) · *who is covered today* ·
eligibility · overlap policy · *which plan covered X* (Pl9's derivation) · coverage determination
for any service · the subscriber role · the catalogue of the insurer's stances.

**For G.** F is the first **role** kind ruled — a dated relation over a party with bound boundary
kinds — and it is not "in respect of": its subject is a party, its meaning is membership of an
arrangement, its temporal grammar is RP2's. Beside A / B (same-typed, role-semantic direction) and
the six "in respect of" kinds (typed direction, attribution floors), it is a third shape. Recorded;
not compared further here.

### F.8 Ruling candidate — pass F, for Rob

> **Covered-under is a role, and its ruled kind is `under_plan`: the asserting party holds that
> established person P is under established plan Q at the date the assertion concerns — the
> asserted relationship between this person and this plan, independent of what the insurer
> believes about eligibility or coverage. It is not the insurer's agreement, not enrollment in the
> insurer's records, not eligibility, not the subscriber's role, not a paid premium, not an active
> status, and not coverage of any service; and an assertion that a person is under a plan does not
> cease to be one because another party asserts the person was ineligible — an evidence boundary,
> not a declaration of eligibility, with contest derived and nothing chosen. It is one ruled role
> kind with a person subject — structurally a party, so that an individual the household names
> without being a Groundwork Person can be under a plan — and a plan object, direction fixed by
> type, no inverse kind, no cardinality (a person under several plans at once, two separately
> asserted claims and no resolver selecting one; a plan for several persons; overlap represented
> and never resolved), established only by a party's assertion with both endpoints established —
> the household, or the insurer as a party — while a card, a portal, a member ID or an enrollment
> record yields at most a candidate; knowing undetermined. It is the first ruled role kind, and
> RP2's temporal grammar binds to it: two boundary kinds, `_began` and `_ended`, each a proposition
> with its own provenance and learned-at time, `as_of` the date asserted about, bound by the
> registry's structural metadata and its existing guard; a beginning implies no ending, an ending
> implies no beginning and rewrites nothing, retraction is not an ending, a period is never
> written, and "in effect on d" is a derivation. It derives nothing about any expense — a person
> under a plan attributes nothing of theirs to it, and an expense under a plan makes nobody a member
> — and nothing about coverage, the subscriber, the premium or the plan's terms. Membership is not
> an attribute of the plan, the person or the expense; a plan with no such claims has no known
> members, which is not no members. Plan's existence supplied the endpoint; this ruling supplies
> the meaning; nothing was manufactured from the two existing together.**

**If ruled, the representation is three registry entries** — the role and its two boundary kinds,
all slots existing, the boundary metadata exactly as RP2 authorised, **no schema, no migration**; a
fixture over F1–F20 and the absences (no `members` / `plan_id` / period on any anchor; no
`plan_members` / `current_plan_of` / `primary_plan` / `is_eligible` / `is_active` accessor; no
derivation from Plan + grammar, from the card, from an expense, or to an expense; no subscriber
kind; F5 as the evidence-boundary invariant; **F20 mandatory** — two plans, two claims, nothing
selected; F7 overlap unresolved; F8 no order from creation; F13 / F14 both convergence directions);
**the role-period fixture's `standin_covered_under` and its boundaries retired into `under_plan` and its boundaries**
(the one stand-in that was this relation under an unruled name — the other stand-ins, over
obligations, stay stand-ins); the plan fixture's *membership is not built* check retired
truthfully; **nothing at family level, no consumer.**

**What pass F leaves exactly where it found it:** the subscriber role and the rest of the role
catalogue · the insurer's stance catalogue · every consumer (R9, eligibility, overlap policy, *which
plan covered X*) · E's build · D′.11 · G.

*The line: the plan is the arrangement; who it is for is what the household says, dated; whether
it covered anything is what the insurer says — and neither is the other.*

### F.9 Rob's review, 2026-09-15 — tightened before ruling

*F is not allowed to inherit the meaning of "covered" from ordinary insurance language.* The central
separation — Plan identity ≠ the relation ≠ the insurer's coverage stance ≠ the enrollment record ≠
the subscriber role ≠ premium / payment status — is sound; F5 tests the floor under hostile facts;
F13 / F14 are the right convergence tests; Plan + RP2 correctly manufactures nothing.

**Applied:**

1. **The floor made structural.** *"One of the persons the arrangement is for"* was elastic enough
   to encompass beneficiary, dependent, subscriber, enrolled, eligible, covered, or merely named in
   a document — distinctions F itself had shown matter. Replaced by the asserted relationship
   itself: **the asserting party holds that established person P is under established plan Q at the
   date the assertion concerns.** The relation, not the insurer's interpretation, is the object of
   the assertion; *enrolled / eligible / subscriber / covered(X) / the three in-respect-of-plan
   relations / active / paid / plan_covers* remain deliberately separate claims (§F.7's block).
2. **F5 restated as an evidence boundary.** Not *the relation is true regardless of eligibility* —
   stronger than the pass needs and contrary to the proposition / evidence discipline — but *an
   assertion that Kim is under P does not cease to be an assertion of the `under_plan` relation
   merely because another party asserts that Kim was ineligible.* Never a system-level truth
   overriding contradictory evidence.
3. **The name is `under_plan`.** `covered_under` carries exactly the lexical magnet the pass
   dismantled; *covered* already has a separately established meaning. The name is
   non-authoritative — the ruling is.
4. **F20 added, mandatory** — the two-plan non-selection case: Kim asserted under P₁ and P₂ for the
   same period; two separately asserted relations; nothing about her person, employment, dates or
   insurers selects one; no resolver. The F analogue of D′3 and of E2 from the person's side.

**One departure from the review's wording, deliberate:** the subject is written as a **party** in
the registry, not restricted to a Groundwork `Person` — F16's ex-spouse, under the plan by court
order and not a household member, is a minted party (Pm9's shape) and must be able to be under P.
"Person" in the ruling means *an individual the household names*, which the party foundation
represents; it does not mean the `Person` table.

**Still no code** — F's job is to settle what `under_plan` means, not to prove it belongs in any
implementation family. G inherits six `in_respect_of` relations plus one role relation, and may not
alter any of their meanings.
