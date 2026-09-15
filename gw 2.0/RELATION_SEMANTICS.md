# Relation semantics — item 6, opened not as "design the relation family"

> Status: **Queue item 6, opened by Rob 2026-09-14. Pass A RULED (§A.6), built (`63848fa`). Pass B RULED as written (§B.7) 2026-09-15 and built — see the commit. Passes C–G open one at a time; C next, Rob opens.** Items 1–5 are
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


