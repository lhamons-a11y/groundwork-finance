# From stand-ins to ruled kinds — item 9

> Status: **ITEM 9 CLOSED — Rob, 2026-09-20. The §1 inventory is complete: every stand-in a ruled kind — 9A `e8fecdd` · 9B `9c53879` · 9C `cdb7cda` · 9D-i `d793472` · 9D-ii `cb8ebe4` · 9D-iii `fe15f5f` · 9D-iv `86b85d5` · 9D-v `1e646fb`; gate 1350 → 1524. What stays open is carried forward by name in *Item 9 — closed* (9D-i-F3, 7J's term read, K2's balance half, the bank line's own kind, D′.11). Below, the record as it was written.**

**The governing question:** *ten consumers exist and nothing production can call them, because
`remaining()` cannot find the entitled party, `reconciliation()` cannot find the insurer, and
`accumulator()` cannot find the plan — every one of those is a stand-in. What makes each stand-in a
ruled kind, and what proves the consumer did not move when it happened?*

The answer the record already gives, pass by pass: F and E are **accepted rulings awaiting a
build** — their passes here are builds, not re-rulings, and reopen nothing. The role catalogue is
**unruled by design** — item 5 refused to let an endpoint's existence give a role a meaning, and
every role is its own ruling: who may assert it, what it establishes, who is knowing for it. The
stance and value catalogue is the **domain question** DOMAIN_PROPOSITION §6 declined to design
(*the shape is exercised by the stand-in `eob_amount`; the catalogue is a domain question*); the
consumers now need it, so it is opened here as a catalogue of kinds with slots and knowing
relations — never of vocabulary or content semantics.

---

## 1. The inventory — every stand-in, and what it awaits

| stand-in (fixture) | used by | awaits | pass |
|---|---|---|---|
| `standin_under` + `_began` / `_ended` | 7F Tr7–Tr13, 7J Ju1–Ju3; item 5's `standin_covered_under` | **`under_plan` + `under_plan_began` / `under_plan_ended`** — F, accepted §F.8 / §F.10 | **9A** |
| `standin_entitled` + boundaries | 7F Ts1–Ts14, 7G (every station), 7H, 7I | **entitled party of** an obligation — a role, unruled; item 5's `standin_role_of_obligation`; Kn2 / D4 | **9B** |
| `standin_provider` + boundaries | 7H (the charge; direction) | **provider of** an expense — a role, unruled | **9B** |
| `standin_insurer` + boundaries | 7H (PR, plan paid), 7J | **insurer of** an expense / claim — a role, unruled; Kn3's second half | **9B** |
| `standin_plan_insurer` + boundaries | 7J (the stated accumulator; eligibility) | **insurer of** a plan — a role, unruled | **9B** |
| `standin_incurred_by` | 7J (the individual figure) | **incurred by** — a role, unruled (EXPENSE_IDENTITY: *the household member who incurred X*) | **9B** |
| `serves` (item 5's fixture); the *S serves E* link (Kn6, C3) | 7E Ms16, 7G Dg4 | **servicer of** — a role, unruled; the mediation link 7E cannot evaluate | **9B** |
| `paid_by` / `paid_to` (payment fixture) | 7G, 7H (direction) | **payer / payee of** a payment — roles, unruled (payment identity: *dated relations*) | **9B** |
| `standin_x_in_respect_of_plan` | 7J (the derived accumulator) | **`expense_in_respect_of_plan`** — E, accepted §E.8 / §E.10, with its two siblings | **9C** |
| `acknowledged` | 7G (discharge) | **the acknowledgment kind** — P-ack for a payment; §D′.4's participant question (O in a slot, or content) | **9D** |
| `balance` · `billed` · `patient_responsibility` · `plan_paid` · `deductible_applied` | 7G, 7H, 7J | **P-ack stance kinds** on O, X, P — dated positions by the party in the role | **9D** |
| `amount` · `occurred_on` | 7G, 7H, 7J | **value kinds** on a payment / expense | **9D** |
| `deductible` · `individual_deductible` · `plan_year` | 7J | **term kinds** on a plan | **9D** |
| `applied_to_deductible` · `determination` · `eligibility` | 7H, 7J | **adjudication / determination / eligibility stance kinds** | **9D** |
| `cleared` · `returned` · `denial` | 7G Dg3, Dg18; 7H Rc6 | kinds the consumers deliberately **do not read** — named so the catalogue rules them, not the consumers | **9D** |

Two things are **not** in this item: candidate generation (the matcher, the importer contract —
its own fence; it needs the kinds this item rules before it can generate candidates *for* them),
and the disposition vocabulary (blocked on the outcome / accounting-treatment question; nothing
here touches it).

---

## 2. The discipline — six things every pass keeps

1. **A build of an accepted ruling reopens nothing.** 9A and 9C implement §F.8 and §E.8 as
   accepted; a question that arises in building is recorded as a finding and put to Rob, never
   settled by the code.
2. **A role is its own ruling** (item 5, RP2). 9B rules each role on three points — who may assert
   it, what it establishes, who is knowing for it — and binds RP2's boundaries to it; nothing is
   inferred from the endpoint's existence, from a document, or from another role.
3. **The catalogue rules kinds, not content.** A kind is slots + `symmetric` + `reading_establishes`
   + `relational_knowing` (+ `knowing_relation`, `boundary`, `of`) — the registry's existing shape.
   Content stays opaque text; what a consumer parses from it (a money amount, a date) it parses as
   it does today.
4. **No consumer changes.** The proof that a pass is done is executable: **the consumer fixtures
   re-run with the ruled kind in the catalogue in place of the stand-in, and no other change** —
   "changed shape for none of them" made mechanical. The stand-in's registration is retired from
   the fixture truthfully; the catalogue argument stays (it is the convention) and now names ruled
   kinds.
5. **Registry only.** No schema, no migration, no column — every slot already exists.
6. **Relational knowing follows the role.** Where 9B rules a designated participant, the kinds that
   wait on it (the acknowledgment kind's *entitled party of the obligation*; a stance's *insurer of
   the claim*) gain a `knowing_relation` — and `derived_strength` reads the ruled class where it
   read the foundation stand-in, with no change to any consumer (7E's contract).

---

## 3. The order — 9A → 9B → 9C → 9D

**9A — F's build.** Accepted, smallest, and the first *ruled* role kind: it proves the swap
discipline (§2.4) on the simplest case before the catalogue opens. **9B — the role catalogue.**
Unlocks every gate in 7G–7J (the entitled party, the provider, the insurers, the payer / payee),
gives Kn6's mediation link a kind, and supplies the designated participants relational knowing has
waited for since RELATIONAL_KNOWING §9. **9C — E's build.** Registry entries only; sits after 9B
because 7J's fixture uses it behind the insurer roles. **9D — the stance and value catalogue.** The
widest and the least ruled; last, so that every kind in it can name the role its knowing relation
designates.

---

## Pass 9A — Build F: `under_plan` and its boundaries

### 9A.1 What is fixed — the ruling, verbatim in effect

§F.8, accepted at §F.10 with the party correction: *the asserting party holds that established
**party** P is under established plan Q at the date the assertion concerns* — an evidence boundary,
not eligibility; one ruled role kind, party subject, plan object, direction by type, no inverse, no
cardinality, no resolver (F20 mandatory), established only by a party's assertion with both
endpoints established (the household, or the insurer as a party), a card / portal / member ID /
enrollment record at most a candidate, **knowing undetermined**; RP2's `_began` / `_ended` bound to it
by the registry's boundary metadata under the existing structural guard; derives nothing about any
expense, coverage, subscriber, premium or terms. **Representation:** three registry entries, all
slots existing, no schema.

### 9A.2 The build, exactly

```text
UNDER_PLAN       = 'under_plan'         subject (subject_party_id,)  object (object_plan_id,)
                                         symmetric False · reading_establishes False · relational_knowing True · no knowing_relation
UNDER_PLAN_BEGAN = 'under_plan_began'   the same slots · boundary 'began' · of UNDER_PLAN
UNDER_PLAN_ENDED = 'under_plan_ended'   the same slots · boundary 'ended' · of UNDER_PLAN
```

The registry comment states the meaning once (F's floor, the evidence boundary, the NOT-block:
`under_plan ≠ enrolled ≠ eligible ≠ subscriber ≠ covered ≠ plan_covers_* ≠ premium_active`), and that
this is the first ruled role kind — the registry's boundary metadata, shipped empty since item 5,
carries its first two entries.

**Fixture** `tests/test_under_plan_fixture.py` over **F1–F20** and the absences: no `members` /
`plan_id` / period on any anchor; no `plan_members` / `current_plan_of` / `primary_plan` /
`is_eligible` / `is_active`; no derivation from Plan + grammar, from the card, from an expense or to
an expense; no subscriber kind; **F5** as the evidence-boundary invariant (Lakeview Health's *never eligible* is
a claim beside, and the household's claim stands); **F20 mandatory** (two plans, two claims, nothing
selected); F7 overlap unresolved; F8 no order from creation; F13 / F14 both convergence directions
(E24 from F's side; E's claim derives no membership); F15 the insurer may assert; F16 a party that is
not a Person; a reading-sourced `under_plan` a candidate (the guard: `reading_establishes False`); the
boundary guard's structural checks on the real kind (`as_of` required; a boundary of a non-role
refused).

**The swap (§2.4):** `tests/test_traversal_fixture.py` and `tests/test_accumulator_fixture.py` drop
`standin_under` and its boundaries from `STAND_INS` and set `'under_plan': db.UNDER_PLAN` in their
catalogues — **no other change**; both must pass unchanged. `tests/test_role_period_fixture.py`
retires `standin_covered_under` and its boundaries into the ruled kinds (F's own instruction) —
its *shipped registry carries no boundary entry* check retired truthfully (it now carries two, of
one role). `tests/test_plan_identity_fixture.py`'s *membership (item 5) is not built* retired
truthfully (it is built; no slot on the anchor, no `members` accessor — the absences that hold are
what it now asserts). Smoke `s117_under_plan.py` on the pattern of s100 / s106: the fixture passes;
mutations each an attempt to give the endpoint a meaning — `plan_members`, `current_plan_of`,
membership from the card, membership from an expense, an expense from membership, a period on the
anchor, `is_eligible` from the insurer's stance — all caught.

### 9A.3 What could go wrong, and where it is measured

The one place 9A can fail semantically is **the swap**: if a consumer fixture needs any change
beyond the two lines, the consumer's shape depended on the stand-in's name or on registry facts
the stand-in did not carry — and that is a finding for Rob, not a fix in the fixture. The one place
it can fail structurally is the boundary guard on a real kind: item 5's fixture exercised it only on
stand-ins.

### 9A.4 Ruling sought — a build authorisation, not a semantic ruling

> Authorise the build of `under_plan`, `under_plan_began` and `under_plan_ended` exactly as §F.8
> describes and §F.10 accepted: three registry entries, the F1–F20 fixture, the two consumer
> fixtures re-run with only the catalogue line changed, the three truthful retirements, s117, the
> gate. No consumer changes. Nothing else in F is reopened.

**What 9A leaves exactly where it found it:** the subscriber role and the rest of the catalogue
(9B) · E (9C) · the insurer's stance catalogue (9D) · every consumer · D′.11.

### 9A.5 Ruling — Rob, 2026-09-19: 9A build AUTHORISED

*Cleanly scoped: 9A is a substitution proof, not an opportunity to reinterpret F.* Held to: **(1)**
exactly the three accepted entries with the party → plan relationship and boundary metadata — no
additional role or value semantics; **(2)** F1–F20 the semantic oracle, including F5's evidence
boundary, F20's mandatory condition, F13 / F14's convergence in both directions; **(3)** the
consumer substitution is the decisive test — the 7F and 7J fixtures identical except for replacing
the stand-in with the catalogue kind; *the consumer's inputs, branching, outputs and interpretation
remain unchanged; only the identity of the relation supplied to it changes*; **(4)** the three
retirements demonstrate the old absence / stand-in machinery is actually retired rather than left
ambiguously alive; **(5)** s117 may expose coupling — if a consumer needs structural change beyond
the substitution, do not repair the fixture; that is a finding to inspect before proceeding. **One
boundary added: the registry entries are not a second semantic source.** The build establishes
*this ruled kind exists in the catalogue with the already-accepted relation / boundary definition*
and nothing new about who may assert `UNDER_PLAN`, what counts as knowing, candidate generation,
role participation, or any 9B relation — those belong to their passes. *If the consumer
substitution requires semantic changes, stop there rather than solving them inside 9A.*

#### Built — 2026-09-19 (9A)

`core/database.py`: `UNDER_PLAN`, `UNDER_PLAN_BEGAN`, `UNDER_PLAN_ENDED` — three registry entries exactly
as §F.8 accepted at §F.10: party subject, plan object, `symmetric False · reading_establishes False ·
relational_knowing True`, no `knowing_relation`; the two boundaries with `boundary began / ended · of
under_plan` — the boundary metadata's first shipped entries, the registry guard passing at import. One
comment block states F's meaning once (the floor, the evidence boundary, the NOT-block) and says
that the entry is not a second semantic source. **Nothing else** — no asserter guard, no knowing
relation, no candidate machinery, no other role.

**The oracle:** `tests/test_under_plan_fixture.py` over F1–F20 — 27 checks: F5 (Lakeview Health's *never
eligible* beside, the household's claims standing unchanged), F20 (two plans, two claims, no
selector) with F7's overlap, F13 and F14 in both directions (nothing about an expense from
membership; no membership from an expense), F15 (the insurer as a party may assert; from a reading
a candidate), F16 (a non-Person party), F17 (a plan-subject claim refused by the registry; no
inverse), the boundary guard on the real kind (`as_of` required; mismatched participants refused),
and the 9B absences (no named knowing relation, no asserter guard, no matcher, no other role kind).
One check reads the 7F consumer over the ruled kind (P2 in effect, P contested by its two endings)
— the same answers the stand-in gave.

**The substitution — the decisive test:** `tests/test_traversal_fixture.py` and
`tests/test_accumulator_fixture.py` changed by exactly the stand-in's name → the ruled kind's
(`'standin_under'` → `db.UNDER_PLAN`, and its boundaries; the three registrations dropped; the 7J
catalogue line `'under_plan': 'under_plan'`); **41/41 and 31/31, identical counts, no other
change** — the consumers' inputs, branching, outputs and interpretation unchanged; only the identity
of the relation supplied changed. `s112`'s *infer the plan from membership* mutation named the
stand-in and now names the ruled kind (a mutation, not a consumer).

**The retirements, truthfully:** (1) item 5's `standin_covered_under` and its boundaries retired
*into* `under_plan` and its boundaries — the role-period fixture now exercises RP2's grammar on the
ruled kind (28/28); (2) its *the shipped registry rules NO role kind and carries NO boundary entry*
→ *exactly one role kind and exactly its two boundary entries; the rest of the catalogue a separate
ruling* — and the same assertion in `s100_role_period` (*no boundary entry of its own*), which is
the same absence stated twice; (3) the plan fixture's *membership (item 5) is not built* → *built as
`under_plan`, a claim never a slot on the anchor; no member manufactured here* (35/35). **One more
of the same class, reported rather than hidden:** the 7F fixture's closing assertion *the registry
is as shipped — 7F ruled no role* also asserted *no boundary entries at all*; narrowed to *the only
boundary entries are under_plan's (9A)*. 7F's own claim (it ruled no role) stays true; the absence
half was item 5's, restated in 7F's fixture.

**Smoke `s117_under_plan.py`:** the fixture passes; seven mutations, each an attempt to give the
endpoint a meaning — `plan_members` · `current_plan_of` · membership from the card
(`reading_establishes` flipped) · membership from an expense (F14 reversed, firing on either
insert order) · an expense from membership (F13 / E24) · a `members` column on the anchor ·
`is_eligible` from the insurer's stance — all caught, baseline re-established after every undo.
One mutation escaped on the first run because it fired only on one insert order; the mutation was
made order-independent, the fixture and the derivation untouched.

**No coupling exposed:** the swap needed no structural change in either consumer. No schema, no
migration. Gate 1333 → 1350, 0 failed.

---

## Pass 9B — The role catalogue

**The question, applied:** *Harbor holds my mortgage but I pay a servicer; my mother paid Riverbend Hospital for
me; Lakeview Health adjudicated Kim's visit; the collection agency now says it holds the hospital bill.* Every
one of those is a **role** — a dated relation between a party and an identity — and every consumer
from 7E onward gates on one: `remaining()` on *the entitled party of O* (S(d), discharge),
`reconciliation()` on *the provider of X* (the charge, direction) and *the insurer of X* (PR),
`accumulator()` on *the insurer of P* and *incurred by*, `chain_strength()` on *S serves E* (the
mediation link it cannot evaluate), relational knowing on *the entitled party of the obligation*
(Kn2, the acknowledgment kind) and *the insurer of the claim* (Kn3). Item 5 ruled the temporal
grammar of roles and **refused to rule the catalogue**: *the catalogue and each role's semantics —
who may assert it, what it establishes, who is knowing for it — are separate rulings; an
endpoint's existence gives a role no meaning.* This pass is those rulings, one per role, on exactly
those three points, with the boundaries bound where a transition is a fact the record must hold.

### 9B.1 What is already fixed

| Ruling | Constraint on 9B |
|---|---|
| **RP2 (item 5, built)** | a role has no intrinsic period; *holds at · began at · ended at* are three sorts; boundaries bind by registry metadata under the structural guard; a boundary never rewrites, implies its opposite, resolves or creates a role; retraction ≠ ending; overlap represented, never resolved; **no role kind ruled by that slice** |
| **9A (built)** | `under_plan` — the first ruled role kind, the template: party subject, identity object, direction by type, no inverse, no cardinality, established only by a party's assertion, a reading a candidate, `relational_knowing True` |
| **The servicing ruling** | **entitlement ≠ payee ≠ discharge — three distinct facts**; *the entitled party: whose obligation / whose acknowledgment matters*; *payee: whom the household actually pays — servicing context, a transaction-level fact*; S3: Groundwork cannot turn a convincing instruction from an apparent payee into knowledge that the payee was authorised; S6: paying the entitled party directly can still leave the payment uncredited |
| **RELATIONAL_KNOWING (R2, built)** | knowing is a relation, fixed per kind, between a party and the participant the kind designates; Kn2 (*entitled party of O* — a role claim, stand-in), Kn3 (*the adjudicator of the claim* — the second half needs the role), Kn6 (*S serves O* — a consumer derivation over role claims), Kn7 (**minting ≠ knowing**: the mother (`paid_by`) and Riverbend Hospital (`paid_to`) are the first-hand parties), Kn12 (knowing ≠ true) |
| **Payment identity (Pm1, Pm5, Pm9, Pm11)** | payer and payee are **claims about p, dated relations**, never anchor columns; `minted_by` names the asserting act, never the payer; a cash payment has a payee at Rob's strength |
| **Expense identity (Ex1; §fences)** | *incurred by (the patient / consumer) · provided by — dated role claims, catalogue unruled*; relational knowing for nature claims waits on *the household member who incurred X* |
| **Insurer-claim identity (4b)** | no claim identity; *insurer of this expense* is a role — relational knowing's designated relation for adjudication; the adjudication is the insurer's dated stances about X; Ic4: two insurers, two sets of stances, nothing to mint |
| **Plan identity (Pl1, Pl3, Pl14)** | a plan's insurer is a party; two plans with one insurer are two plans; Medicare + a supplement are two insurers |
| **7F (built)** | `in_effect(party, role_kind, d)` — and its refusal: *a kind no boundary kind is `of` is not a role* (§7F.4 TR8) — **which 9B must confront (§9B.3)** |
| **Item 9 §2** | a role is its own ruling on three points; the catalogue rules kinds not content; **no consumer changes** — the substitution is the proof; registry only; relational knowing follows the role |

### 9B.2 The catalogue — seven roles, three points each

Every role: party subject (structurally a party — a household person, a minted institution, a
non-Person party), an identity object, direction fixed by type, **no inverse kind** (navigation
either way is a query, 7F), no cardinality, **established only by a party's assertion with both
endpoints established; a document, a bank line, a card, an EOB or a letter yields at most a
candidate** (`reading_establishes False`); retraction is a withdrawal, never an ending.

| kind | subject → object | sorts | who may assert | what it establishes (and which consumer reads it) | who is knowing for the role claim |
|---|---|---|---|---|---|
| **`entitled_party_of`** | party → obligation | holds · **began · ended** (R8: the debt sold — E₁ ended 5/1, E₂ began 5/1; S4 / S5: a sale transitions it, an assignment does not) | the household (Ob1's minting act names whom it owes); the entitled party itself, as a party; a servicer's or agency's letter → candidate | *whose obligation, whose acknowledgment matters*: the E-test in 7G (S(d), discharge), 7H, 7I, 7J; the designated participant Kn2 waited for (the acknowledgment kind's knowing relation, 9D) | the subject party — it holds the note (Kn12: it can be wrong) |
| **`servicer_of`** | party → obligation | holds · **began · ended** (R2 / S2: *Harbor serviced it from March to June*; the servicer changes and autopay does not) | the household (S1); the entitled party (whose authorisation it is); the servicer as a party (S3 — an assertion, not authorisation); a letter → candidate | *servicing context*: whom the household pays and why; **the mediation link Kn6 / C3 named** — `chain_strength` can evaluate *S → E* once this kind exists; **never entitlement** (S3: a servicer's own claim does not make it the entitled party — 7G's E-test unchanged) | the subject party — S3 asserts it and *is* knowing for its own assertion; knowing ≠ authorised ≠ true |
| **`provider_of`** | party → expense | holds only | the household (Ex1's minting act: *Riverbend Hospital provided it*); the provider as a party (its bill); a bill's reading → candidate | *whose charge*: 7H's `billed` (P-ack for X's charge by the provider in effect) and the direction anchor for funding events | the subject party |
| **`insurer_of`** | party → expense | holds only | the household (*Lakeview Health's EOB for the ER visit* — beside `artefact_concerns`); the insurer as a party; the EOB's reading → candidate | *whose adjudication*: 7H's PR / plan-paid stances, 7J's `applied_to_deductible` through the plan; **Kn3's second half** — knowing for the adjudication of X; **Ic4: two insurers of one X are two claims, each in effect, each knowing for its own stances** | the subject party |
| **`insurer_of_plan`** | party → plan | holds only | the household (Pl1, minting P as *the Lakeview Health plan*); the insurer as a party; the SBC's reading → candidate | *whose plan*: 7J's stated accumulator and eligibility gate; the P-ack for P's terms (9D) | the subject party |
| **`incurred_by`** | party → expense | holds only | the household (Ex1: *we took Kim to the ER*); the party itself | *whose expense*: relational knowing for nature claims (EXPENSE_IDENTITY — *the household member who incurred X*), 7J's individual figure; **never plan attribution** (E24) | the subject party — they were there (Kn8: *it was health*) |
| **`paid_by` / `paid_to`** | party → payment | holds only | the household (Pm1's minting act); the payer or payee as a party; the bank line's reading → candidate (K6: the bank knows movement, and a reading is a candidate all the same) | *who paid, whom*: 7G / 7H direction; Kn7's first-hand parties for the event; **payee ≠ entitled party ≠ discharge** (the servicing ruling, structurally: three kinds) | the subject party — the mother knows she paid; Riverbend Hospital knows it was paid; Rob was told |

**One knowing relation for all seven — `KNOWING_SUBJECT_PARTY`:** *the party knowing for a role
claim is the party in the role* — the origin of the utterance is the claim's subject party. Rob
asserting *Harbor is the entitled party* is `not_knowing` (he was told, or inferred it from the
statement); Harbor asserting it is `knowing`; a reading is a candidate and undetermined. This is R2
applied to roles with the designated participant = the subject, and it gives Kn7 for free (the
mother is knowing for `paid_by(mother, p)`, Rob is not). Kn12 stands: S3 is knowing for its own
servicing claim and may be lying; knowing says first-hand, never correct.

**Boundaries bound to two roles only** — `entitled_party_of` and `servicer_of` — because those are
the roles whose transitions are facts the record must hold (R8, S2, S4 / S5, R2 / R4). The other
five are *holds at d* stances (RP2's base sort): an expense's provider, an expense's insurer, a
plan's insurer, who incurred an expense and who paid whom **do not begin and end**; a correction is
a retraction and a new claim, not a boundary. **Binding boundaries to a role that cannot
transition would invite claims that mean nothing.** Which raises the finding.

### 9B.3 The finding — 7F's definition of a role, and what 7G–7J inherited from the stand-ins

7F ruled (§7F.4 TR8, built): *`in_effect` refuses a kind no boundary kind is `of` — a relation has
no "in effect"*. 7G, 7H and 7J inherited it through `_require_role` and `_entitled_at`. **Every
stand-in the consumer fixtures registered carried boundaries** — `standin_provider_began`,
`standin_insurer_ended`, `standin_plan_insurer_began`, … — so the consumers never met a role
without them. §9A.3 said the swap failing on more than the catalogue line is a finding, not a
fix: **here it is, before the swap.** Five of the seven ruled roles are holds-only, and the
consumers as built would refuse them by name. Three ways out, put to Rob:

- **RB-a — bind boundaries to all seven.** Registry-only, no consumer changes. Rejected by §9B.2:
  a `provider_of_ended` is a boundary that means nothing, and RP2's guard is structural — it would
  admit the claim.
- **RB-b — a role is what the registry says is a role: one metadata key, `'role': True`, on every
  role kind** (including `under_plan`, a one-key addition to 9A's entries, semantics unchanged).
  7F's refusal becomes *a kind the registry does not mark as a role is not a role*; `in_effect`
  over a holds-only role runs G over holds stances (TS already reads a holds forward and nothing
  back; N of a holds contests nothing); item 5's guard tightens to *a boundary binds only to a
  kind marked as a role* — closing "anything bounds anything" more exactly than the current *not
  itself a boundary* test. One line in `in_effect`, `_require_role` and the guard; no consumer's
  inputs, branching, outputs or interpretation change — an *eligibility* predicate of the
  registry, not a semantic one.
- **RB-c — derive "role" structurally**: subject slot `subject_party_id`, not symmetric, not a
  meta-kind, not a boundary. No metadata, but an implicit rule that `party_corresponds` and any
  future party-subject kind would fall into or out of by accident.

**Recommended: RB-b.** Explicit, one key, and it makes item 5's guard say what it meant. It is a
change to 7F's *refusal condition* — the same test with a truer predicate — not to what 7F derives;
it is recorded here as the one consumer-side change 9B needs, for Rob to rule before any swap.
**Rob, on review:** the key answers *"is this registry entry a role?"* and nothing else — it does
not answer *"how does this role behave?"*; it must acquire no consumer semantics merely because it
fixes the registry classification, which is what keeps 9B from quietly reopening 7F.

**A second finding, 7H's, exposed by Ic4:** `reconciliation()`'s governing PR is *the latest
established claim at or before d by a party in effect as insurer of X* — one series across
parties. With **two** insurers of X (Ic4, CC1), the later insurer's stance would govern by recency
across parties — the resolver 7H refused for determinations (§7H.8 item 4: G per party's series,
conflict across parties → none). **9B does not resolve this and must not**
(Rob, on review): 9B rules *which roles exist · who occupies them · the knowing relation · where
role boundaries occur*; what the governing PR is when the series crosses party boundaries is 7H's
territory, and 9B may not manufacture a party-local recency rule — or any resolver — to make its
build convenient. The role that exposes the question is ruled here; the question itself is
recorded for 7H, to be resolved against 7H's own rulings (its G-per-series treatment of
determinations is the precedent, not a decision) before the 7H fixture is substituted.

**The two questions the ruling must settle, as Rob framed them — and nothing wider:**

```text
9B-F1   Is explicit role classification ('role': True) the correct interpretation of 7F's "a role
        is a kind some boundary is of", without importing any consumer behaviour?
9B-F2   Given 7H's cross-party governing-PR series, does 9B merely expose the relevant role /
        boundary information and defer governing determination entirely to 7H?
```

Answered affirmatively, 9B proceeds without reopening 7F or 7H. The opening itself commits to
neither: the findings and the proposed shape of their resolution are recorded; the semantic
ruling precedes the build.

### 9B.4 The cases

| # | Case | What the catalogue must say | What it must never do |
|---|---|---|---|
| **Ro1 (S1)** | Riverbend Hospital keeps the bill; BillCo services it; Rob pays BillCo. | `entitled_party_of(Riverbend Hospital, O)` · `servicer_of(BillCo, O)` · `paid_to(BillCo, p)` — three kinds, three facts; 7G's E-test is Riverbend Hospital's; the payment's payee is BillCo | make BillCo the entitled party because it is paid |
| **Ro2 (S2)** | The servicer changes 5/1; autopay keeps paying the old one. | `servicer_of(Old, O)` ended 5/1, `servicer_of(New, O)` began 5/1 — 7F's answers; `paid_to(Old, p)` after 5/1 stands as a fact; discharge is E's acknowledgment either way | end the payee; redirect the payment |
| **Ro3 (S3)** | S3, never authorised, writes *pay us*. Rob does. | `servicer_of(S3, O)` asserted by S3 — established, S3 knowing, and **not** entitlement; `paid_to(S3, p)`; 7G: attached_unacknowledged, direction undetermined (S3's E-role undetermined) | let S3's claim pass the E-test; let a letter establish the role |
| **Ro4 (S4 / S5)** | Assignment (same payee, entitlement unchanged) vs sale (same payee, entitlement transitions). | the assignment: `servicer_of` only; the sale: `entitled_party_of(E₁, O)` ended · `entitled_party_of(E₂, O)` began — the household says which (C9) | infer a sale from a payee change |
| **Ro5 (S6)** | Rob pays Harbor directly, past the servicer; Harbor leaves it uncredited. | `paid_to(Harbor, p)` — payee the entitled party in effect → 7G direction −1; **still attached_unacknowledged** until Harbor acknowledges | payee = E ⇒ discharge |
| **Ro6 (S7)** | Money sent to E₁ after E₁'s role ended. | `paid_to(E₁, p)` with E₁ *not_in_effect* at `occurred_on` → 7G direction undetermined, naming p — the record says the household paid a party that no longer held it | redirect; discharge |
| **Ro7 (R8)** | E₁ ended 5/1; E₂ began 5/1; asked 5/12 and 4/12. | 7F over the ruled kind: E₁ not in effect / E₂ in effect on 5/12; on 4/12 E₁ in effect, E₂ undetermined | — |
| **Ro8 (Pm9 / Kn7)** | *My mother paid Riverbend Hospital $300 for me.* | `paid_by(mother, p)` and `paid_to(Riverbend Hospital, p)` asserted by Rob — established, Rob `not_knowing`, the mother `knowing` for `paid_by` if she asserts it; the household is not the payer by default | a household-default payer; minting = knowing |
| **Ro9 (Ex1)** | *We took Kim to the ER on Feb 14.* | `incurred_by(Kim, X)` · `provider_of(Riverbend Hospital, X)` from the minting act — holds only; no beginning, no ending | a `provider_of_began` |
| **Ro10 (Ic4 / CC1)** | Lakeview Health and Cigna both adjudicate X. | `insurer_of(Lakeview Health, X)` · `insurer_of(Cigna, X)` — two claims, both in effect, each knowing for its own stances; **7H's finding (§9B.3): the PR governs per insurer's series** | one insurer selected; the later stance governing across parties |
| **Ro11 (Pl3 / Pl14)** | Medical and dental both with Lakeview Health; Medicare + a supplement. | `insurer_of_plan(Lakeview Health, P₁)` · `insurer_of_plan(Lakeview Health, P₂)`; `insurer_of_plan(Medicare, P₃)` · `insurer_of_plan(Supp, P₄)` | the insurer as the plan; one plan for one insurer |
| **Ro12 — the party asserts its own role** | Harbor: *we hold your mortgage*; Lakeview Health: *we insure this plan*. | established, **knowing** (`KNOWING_SUBJECT_PARTY`); beside the household's claim; contest derived where they differ | the party's word outranking the household's |
| **Ro13 — a reading** | A statement's letterhead; an EOB's payer block; a bank line's payee. | a candidate for the role, never the claim | `reading_establishes` |
| **Ro14 — a stranger asserts** | Kim's cousin: *Harbor holds it*. | established, `not_knowing`; listed; the E-test is about Harbor's role, not the asserter | refuse the claim; rank asserters |
| **Ro15 — retraction** | *I was wrong — it was never Harbor.* | a retraction; the history survives; not an ending | read as `ended` |
| **Ro16 — no inverse** | `obligation_entitled_party`, `plan_insurer`, `expense_provider`. | no such kinds; navigation a query (7F) | an inverse kind |
| **Ro17 — knowing ≠ true (Kn12)** | S3's servicing claim; Harbor's mistaken entitlement claim. | knowing for their own assertions; both may be false; the resolver is fenced | knowing read as correct |
| **Ro18 — the substitution** | Every consumer fixture with the stand-ins replaced by the seven ruled kinds and the catalogue lines changed. | **no other change** — the same counts, the same answers; where a consumer refuses a holds-only role, that is §9B.3's finding, resolved by RB before the swap, never by a fixture edit | a consumer edited to fit |

### 9B.5 Testing the readings

**RB0 — roles inferred** (from a payment's payee, a document's letterhead, a plan's name, an
expense's provider being someone's usual doctor). Rejected: item 5, S3, Ro1, Ro3, Ro13.

**RB1 — one role for several facts** (payee = entitled party; servicer = entitled; insurer of X =
insurer of P). Rejected: the servicing ruling; Ro1, Ro3, Ro10 / Ro11.

**RB2 — boundaries everywhere** (RB-a). Rejected: §9B.2, §9B.3.

**RB3 — a household-default role** (the household is the payer, the incurrer, the entitled
party's counterpart). Rejected: Pm9, Kn7; Ro8.

**RB4 — the asserter's authority** (the party's own claim outranks; the household's is the truth).
Rejected: F5's shape, Ro12, Ro14 — contest derived, nothing chosen.

**RB5 — the candidate: seven ruled role kinds and one knowing relation.** `ENTITLED_PARTY_OF` (+
`_BEGAN` / `_ENDED`), `SERVICER_OF` (+ `_BEGAN` / `_ENDED`), `PROVIDER_OF`, `INSURER_OF`,
`INSURER_OF_PLAN`, `INCURRED_BY`, `PAID_BY`, `PAID_TO` — each `symmetric False ·
reading_establishes False · relational_knowing True · knowing_relation KNOWING_SUBJECT_PARTY`, the
new resolver `_designated_subject_party` beside the two existing ones; **and, on RB-b, `'role':
True` on all eight role kinds** with 7F's refusal, `_require_role` and item 5's guard reading the
key. A fixture over Ro1–Ro18; the substitution in the 7E, 7F, 7G, 7H, 7I and 7J fixtures with only
the kind names and catalogue lines changed; the payment fixture's `paid_by` / `paid_to` / `toward`
stand-ins and item 5's `serves` / `standin_role_of_obligation` retired into the ruled kinds; the
absence checks that named the roles retired truthfully; s118. **No consumer changes beyond RB-b's
predicate; nothing about the stance kinds (9D).**

### 9B.6 Ruling candidate — pass 9B, for Rob

> **A role is a party's asserted, dated standing toward an identity, and the catalogue rules
> seven: the entitled party of an obligation, the servicer of an obligation, the provider of an
> expense, the insurer of an expense, the insurer of a plan, the party who incurred an expense,
> and the payer and payee of a payment. Each has a party subject and an identity object, is
> asserted by any party under the ordinary discipline and established only by assertion — a
> document is a candidate — and is known first-hand by the party in the role and by no one else.
> Each establishes exactly what its consumers read — whose acknowledgment matters, whom the
> household pays, whose charge, whose adjudication, whose plan, whose expense, who paid whom —
> and none establishes another: the payee is not the entitled party, the servicer is not the
> entitled party, the insurer of an expense is not the insurer of its plan, and discharge is none
> of them. The entitled party and the servicer begin and end; the other five hold at a date and
> do not. A role is what the registry marks as one, and a boundary binds only to such a kind; a
> role's holds stances answer "in effect on d" without a boundary. No inverse kind, no default
> party, no rank among asserters, no inference from any document, payment, name or other role.**

**If ruled, the build is** the registry entries and the one resolver; RB-b's predicate in three
places; the Ro1–Ro18 fixture; the six consumer substitutions with no other change; the
retirements; s118; **and, before the 7H substitution, 7H's governing-PR question resolved in 7H's own terms** — not
here. No schema, no migration.

**What pass 9B leaves exactly where it found it:** the subscriber role (F10 — content or a later
kind) · the obligor role (an obligation's debtor — no consumer reads it yet) · E (9C) · every stance
kind and the acknowledgment kind's participant (9D) · D′.11.

*The line: who holds it, who services it, who provided it, who insured it, who was there and who
paid — seven things the household says, dated, and none of them says the others.*

### 9B.7 Ruling — Rob, 2026-09-19: 9B-F1 yes, 9B-F2 yes, 9B RULED as written; no code by this ruling

*Nothing needs addressing before the ruling; the sequence and the separation of concerns are
clean.* 9A (`e8fecdd`) properly closed — scope limited to the three entries; the 27/27 fixture
establishes the semantic surface rather than testing registration; s117's mutations show the
consumers depend on the substitutions; the substitutions exposed no coupling; the retirements
include the absence constraint, so the old semantic source is explicitly retired, not merely
unused; the registry is not a second ontology source; the one escaped mutation caught and
corrected before acceptance.

**9B-F1 — yes, scope exactly as written.** Explicit role classification (`'role': True`) is the
correct interpretation of 7F's *a role is a kind some boundary is of*, **provided the
classification answers only whether the registry entry denotes a role.** The important negative:
**`role: True` must not become a consumer instruction.** It says what kind of thing the entry is;
it does not say how the role behaves, whether it currently has an occupant, whether it has a
boundary, how recency is resolved, how servicing works, or anything else about consumption. F1 is
settled without reopening 7F.

**9B-F2 — yes.** 9B exposes exactly the information it owns — the roles, their occupants, the
knowing relation, the applicable role boundaries — and manufactures no governing-party resolver.
7H's cross-party governing-PR series is precisely why this belongs in 7H; a party-local
*most recent* rule introduced here would silently answer a question 7H has deliberately not
answered. The dependency stays: **9B supplies the role / boundary facts → 7H determines governing
PR under 7H's own ruling** — not *9B supplies facts + guesses governing PR*.

**The pass — accepted as opened, for build**, subject to the build remaining faithful to those
boundaries, with one negative constraint preserved in the ruling so the dependency cannot blur in
implementation: **9B does not determine governing PR, and no party-local recency resolver may be
introduced as part of 9B.** No additional finding; no code beyond the settled semantics; **9B must
not become a vehicle for solving 7H early** — the one boundary to watch when the build starts.

#### Built — 2026-09-19 (9B)

`core/database.py`: the seven role kinds exactly as §9B.7 ruled — `ENTITLED_PARTY_OF` and `SERVICER_OF`
(party → obligation) with `_BEGAN` / `_ENDED` boundaries `of` each; `PROVIDER_OF`, `INSURER_OF`,
`INCURRED_BY` (party → expense), `INSURER_OF_PLAN` (party → plan), `PAID_BY`, `PAID_TO` (party →
payment), holds-only — no boundary entry. Every role: `symmetric False · reading_establishes False ·
relational_knowing True`, one knowing relation for all seven, `KNOWING_SUBJECT_PARTY` — the third
named relation, its resolver the claim's own `subject_party_id` (R2 applied to roles; Kn12 stands: S3
is knowing and may be lying). `under_plan` names none (F). **RB-b as recommended and as ruled:**
`'role': True` on the nine role entries (`under_plan` included); the registry guard now refuses a
boundary `of` a kind the registry does not mark as a role (9B-F1) instead of inferring roleness from
boundaries; 7F's `in_effect` and the consumers' `_require_role` (7G, 7H, 7I, 7J) read the same key
and nothing else about it — a holds-only role answers from its holds stance, a relation kind is
refused by name as *not a role*. The key answers *is this entry a role?* and acquired no consumer
semantics: no behaviour key exists on any entry beyond the registry's shipped shape. **Nothing
else** — no governing-PR determination, no party-local recency, no selector, no default payer, no
inverse kind (9B-F2, the negative constraint kept).

**The oracle:** `tests/test_role_catalogue_fixture.py` over Ro1–Ro18 — 26 checks: the registry
(nine roles marked, the three points on each, the objects, boundaries bound to exactly the three
that transition, the guard refusing a boundary of a non-role, the third relation with its own
resolver); S1–S7 through 7F's `in_effect` on the ruled kinds (entitlement · servicing · payee three
kinds; the servicer change with autopay still naming the old one; S3 established and knowing and
never entitled; assignment vs sale, the new servicer nobody's entitled party; payee = E as direction
not discharge; money to the party that no longer holds it; R8's boundaries); Pm9 / Kn7 (the mother
knowing for her own `paid_by`, Rob not; no household-default payer); Ex1 (holds-only, `in_effect`
answering from the holds stance, no `_began` kind); **Ic4 / CC1 — two insurers of one expense, both
in effect, and NOTHING decided about a governing PR** (no resolver exists, `in_effect`'s source
names none); Pl3 (two plans one insurer; the plan's insurer establishes nothing about the expense's
insurers); the party asserting its own role knowing; a reading a candidate and never the claim (the
letterhead minted no role); a stranger established and not knowing, asserters not ranked;
retraction not an ending; no inverse and no selector (an obligation-subject claim refused by the
registry); knowing ≠ true; and 9B-F1 / 9B-F2 as absences with the refusal of a relation kind and of
an unruled kind.

**The substitution — the decisive test, and what it exposed:** the 7F, 7G, 7I, 7H and 7J fixtures,
item 5's, 9A's, the payment-identity and relational-knowing fixtures changed by the stand-ins'
names → the ruled kinds' and the catalogue lines (`'entitled_party': 'entitled_party_of'`,
`provider_of` / `insurer_of` / `insurer_of_plan` / `incurred_by` / `paid_to`), registrations
dropped; **41/41 · 40/40 · 30/30 · 32/32 · 31/31 · 28/28 · 27/27 · 38/38 · 23/23, identical counts,
no consumer changed.** Three things the swap needed beyond names, reported rather than absorbed:
(1) three fixtures had used a ruled *name* for a different shape — a content claim on the thing
(`subject_expense_id` / `subject_payment_id`, content `'Kim'`, `'NewBank'`): the 7F corpus's
`incurred_by`, the payment-counteracts fixture's `paid_to` / `paid_by` (A7) and the
obligation-replaces fixture's `paid_by` (B3); the registry refuses each now that the names are ruled
party → thing, and the full gate found the two the touched-fixture runs could not. Each corpus line
became the ruled role's shape (and `s112`'s *infer the plan from membership* mutation, which
mirrored the first, reads the ruled shape); the counteracts fixture's foundation map dropped
`paid_to` — knowing for a ruled role is by relation, not by the map. A fixture borrowing a ruled name
for an unruled thing is exactly what the catalogue exists to stop. (2)
The 7H and 7J fixtures' role helpers created `_began` stances for every role; on the five holds-only
roles no such kind exists, so the helpers create the holds stance — the consumers unchanged, the
fixtures' way of putting a role in the record corrected to the ruling. (3) 7J's stand-in table keeps
one non-role relation (`standin_x_in_respect_of_plan`, E's — 9C's) and drops its role key. **Not
substituted:** item 5's `serves` (party ↔ party, Kn6's link as that fixture named it) — 9B's
`servicer_of` is party → obligation, a different shape; `serves` stays a stand-in, its name carrying
no ruling, and the fixture says so.

**The retirements, truthfully:** (1) item 5's `standin_role_of_obligation` and its boundaries into
`entitled_party_of` and its boundaries; its *exactly one role kind, exactly its two boundary entries*
→ *the nine ruled role kinds, boundary entries only for under_plan, entitled_party_of and
servicer_of; serves and the obligor role not ruled* — and the same statement in `s100`; (2) 9A's
fixture's *no other role kind in the registry* retired; its *no knowing relation* made an executable
distinction rather than a comment — *under_plan names none (F: undetermined — a fact about under_plan,
not the registry) while the seven 9B roles name KNOWING_SUBJECT_PARTY* — so the preserved 9A oracle
cannot be read as asserting the final registry names no knowing relation; `under_plan`'s rule now
carrying `'role': True`;
(3) the 7G / 7I / 7H fixtures' *paid_by / paid_to not registered* narrowed to the value kinds that
are still 9D's; the payment fixture's *paid_by stays a stand-in* → *ruled as a role on the object
payment slot*; (4) the relational-knowing fixture's *two names, two resolvers* → three, and Kn7's
wording — the mother's knowing for `occurred_on` (the event's property, 9D's) still undetermined,
not manufactured from her ruled `paid_by` role; (5) the 7F fixture's closing line and `s117`'s
opening check — boundary entries of exactly `under_plan`, `entitled_party_of`, `servicer_of`; `s97`'s
opening check — three named relations.

**Smoke `s118_role_catalogue.py`:** the fixture passes; ten mutations, each an attempt to give a
role a meaning beyond its three points — payee = entitled · servicer = entitled · a reading
establishes a role · a household-default payer · the provider from the letterhead · the expense's
insurer from the plan's · boundaries on a holds-only role (RB-a) · the knowing relation resolving to
the asserter · a non-role passing `in_effect` (9B-F1) · **a governing-PR resolver appearing (9B-F2)**
— all caught, baseline re-established after every undo. Four escaped on the first run: minted claims
carried no evidence, so `in_effect` rightly never saw them (the mutations now evidence what they
mint); and three fixture gaps the escapes exposed — Ro4 never asked whether the new servicer had
become entitled, Ro11 never asked whether the plan's insurer had minted anything on the expense,
Ro13 never asked whether the letterhead had minted a claim — each closed by an assertion the case
already meant. The derivations untouched.

**Left where it belongs:** 7H's governing PR across two insurers (Ic4 / CC1) — no rule made here,
per 9B-F2. `serves` and the obligor role unruled. No schema, no migration. Gate 1350 → 1373, 0 failed.

#### Accepted — Rob, 2026-09-19 (9B): nothing to reopen

*The evidence is sufficient.* Basis as Rob stated it: gate 1350 → 1373, 0 failed; s118 23/23 catching
all ten mutations including the four fixture gaps found during the build; s117 17/17 standalone
against the final fixture closing the 9A-oracle transition; the 9A / 9B distinction executable —
`under_plan` names no knowing relation while the seven 9B roles name `KNOWING_SUBJECT_PARTY`; the
seven roles, their knowing relation and their boundaries present **without importing consumer
behaviour**; the substitutions leaving 7H's governing-PR behaviour exactly on its 7H semantics (Rc10,
Rc15, Rc16); no alternate-shape compatibility path in the registry; the three borrowed-name
corrections corpus corrections, not ontology expansion; the four escaped mutations converted into
observable tests rather than weakened; **the negative constraint held — 9B created no governing-PR
resolver.** *Most importantly, the build demonstrated the boundary we ruled: 9B exposes the
role / boundary facts that 7H needs; it does not answer the governing-PR question.* §9B complete;
the stopping point left exactly here. **9C remains unopened until its own semantic questions are
surfaced and ruled.**

---

## Pass 9C — Build E: the three plan relations

*Opened by Rob 2026-09-19 after 9B's acceptance (`909bef4`). The order he set: semantic surface →
cases / findings → ruling → build authorisation → implementation → mutation / gate evidence →
acceptance. 9C starts from E's already-accepted relations and **discovers** what the 7J
substitution exposes; the consumer paths are evidence of what E's kinds must carry, never a source
of semantics for them. No code by this opening.*

### 9C.1 What is fixed — two rulings, verbatim in effect

**E (§E.8, accepted §E.10, 2026-09-15).** *Exactly three plan relations, one per pairing, each a
party's statement that an expense, an obligation or a payment is in respect of a plan — nothing
about coverage.* `expense_in_respect_of_plan` · `obligation_in_respect_of_plan` ·
`payment_in_respect_of_plan`; both participants established; the plan the object; direction fixed
by type; **no inverse kind, `plan_covers_*` refused as a name**; no cardinality, priority, sum or
allocation; established only by a party's assertion with both endpoints established — the
household, or the insurer as a party; a reading, a group number, a bank label or an authorization
at most a candidate; **knowing undetermined**; each derives nothing — no coverage, membership,
adjudication, network, applied terms, benefit, cost, premium status, discharge or direction of
money; no *uninsured* from absence (E5); not withdrawn by the insurer's later stance (E3); no
temporal precedence (E22, permanent); **no composition** — not from membership and a date, not
from a shared person (E24, mandatory), not through an expense (E15), not through an obligation
(E18), not from a document concerning both (E6), not from the insurer's role. **E8 the
minimal-floor invariant:** denied, unpaid, cash-paid — still in respect of P. **E2 mandatory:** two
plans, neither chosen. *Not to be done* (§E.10): another case; a change to the three candidates;
opening F. §E.10 also said *implementation from E* is not to be done — item 9 is exactly the
instrument that lifts that, as it lifted F's for 9A (§2: a build of an accepted ruling reopens
nothing).

**G (§G.9, ruled 2026-09-16; the contract stated once in `core/database.py`).** Six in-respect-of
kinds have identical relational semantics after the participant types are treated as parameters;
**representation: six kinds, one per pair** — a typed-slot `in_respect_of` refused on structure; no
family base, resolver, selector, inverse accessor or composition helper; each member keeps its own
NOT-list beside its constant; the family is a shared floor, not a shared path. `s106` pins this and
already names E's three pairs (`RULED_PAIRS`) with their slots and the family flags, asserting no
`knowing_relation` on any member and *E's three accepted and unbuilt by instruction*.

**Representation, therefore, is not 9C's to choose** — E chose three kinds and G confirmed the
per-pair representation for the family. What is left to 9C is the build of exactly that.

### 9C.2 The build, exactly

```text
EXPENSE_IN_RESPECT_OF_PLAN    = 'expense_in_respect_of_plan'     subject (subject_expense_id,)     object (object_plan_id,)
OBLIGATION_IN_RESPECT_OF_PLAN = 'obligation_in_respect_of_plan'  subject (subject_obligation_id,)  object (object_plan_id,)
PAYMENT_IN_RESPECT_OF_PLAN    = 'payment_in_respect_of_plan'     subject (subject_payment_id,)     object (object_plan_id,)
    each:  symmetric False · reading_establishes False · relational_knowing True · no knowing_relation · no 'role' · no boundary
```

All slots exist; no schema, no migration. One comment block per kind beside its constant, in the
form C / D / D′ carry: E's floor once, the kind's own NOT-list (E.6's row), and the two E.6
invariants (*no in-respect-of relation licenses an inverse or a coverage relation from its
existence*; *shared person ≠ plan attribution*). The G.9 block's three *(E, accepted, unbuilt)* lines
become *(E, built 9C)*. **Nothing else** — no `plan_covers_*`, `covered_by`, `plan_of_expense`,
`which_plan`, `coverage_of`, `premium_for`; no `plan_id` on any anchor; no resolver choosing a plan;
no order guard; no candidate generator; no family abstraction; nothing from F beyond what 9A built;
no knowing relation (9B's `KNOWING_SUBJECT_PARTY` is a role's relation and E's kinds are not roles —
who is knowing for *X in respect of P* is undetermined by E and stays so).

**The fixture — one, over E1–E24, as §E.8 specified** (`tests/test_plan_relations_fixture.py`;
C / D / D′ had a fixture each because each was its own pass — E was one pass with three kinds, and
its ruling asked for one fixture): E1 the floor; **E2 mandatory** (two plans one date — two claims,
no rule names a result, no priority; the membership-and-date derivation demonstrably absent); E3
(the insurer's retroactive ending is a stance about P; the relation stands); E4 (two plans, two
claims, no netting); E5 (cash at CVS: no relation; no *uninsured* from absence); E6 (the EOB's two
`artefact_concerns` derive nothing); E7 (the authorization tied by `proposition_concerns`; X → P
Rob's to assert); **E8 the minimal-floor invariant** (denied, plan paid $0, cash-paid — the claim
stands, nothing on X or P changes; contrast E5); E9 (dispute, retraction; nothing chooses); E10
(direction by type — a plan-subject claim refused by the registry; no inverse kind; no resolver);
E11; E12 / E13 / E14 (the premium O → P; the employer's share not summed; **O′ with Lakeview Health the
obligor is the same kind — money direction is not relational meaning; O → P never yields P covers
O**); E15 (*what the plan didn't cover*: X → P + O → X does not yield O → P); E16 (COBRA: a plan is
not an obligation; `obligation_replaces` does not apply); **E17** (p → P with no O anywhere; nothing
manufactured); E18 (p → O + O → P does not yield p → P); E19 (Lakeview Health's payment to Riverbend Hospital: p′ → P by
Rob; no household party required); E20 (reimbursement: no discharge); E21 (the bank line a
candidate at most — `reading_establishes False` on all three); **E22 permanent** (December premium
for a January plan; P minted in March for a January arrangement); E23 (the vocabulary: none a
kind); **E24 mandatory** (Kim under P by 9A's ruled kind + X incurred by Kim by 9B's — **no relation
and no candidate**). And the absences E.8 listed, plus: each kind refuses the other two's subject
types by the registry; a reading-sourced claim of any of the three is a candidate.

**The swap (§2.4).** `tests/test_accumulator_fixture.py`: `standin_x_in_respect_of_plan` dropped
from `STAND_INS` (the last entry — the table becomes empty), the catalogue line
`'expense_in_respect_of_plan': db.EXPENSE_IN_RESPECT_OF_PLAN`, the two `claim(...)` sites by name —
**no other change; 31/31.** `tests/test_under_plan_fixture.py` F14: `expense_in_respect_of_plan_standin`
→ the ruled kind by name (27/27). `s117`'s two membership mutations name the ruled kind (mutations,
not consumers). `s112` unaffected (it names no E kind). The 7F, 7G, 7H, 7I fixtures name none of E's
kinds except Tr8 — **finding 9C-F1 below**.

**The retirements, foreseen:** (1) the plan fixture's **Pl7** *no kind, slot or claim ties the
premium to P* and **Pl9** *no plan ↔ expense kind* — **pre-authorised by §E.8 itself** (*retired
truthfully: the relations now exist; `plan_id`, `which_plan`, `plan_covers` still do not*); each
keeps its absences and adds the thing that now exists (*ties only by a party's asserted
`obligation_in_respect_of_plan`; none asserted here*). (2) `s106`'s *E's three accepted and unbuilt
by instruction* → *all six built; E's three by 9C* — its range check already admits six, its slot /
flag / no-`knowing_relation` checks now run over E's three for real. (3) The registry comment. (4)
**Tr8 — 9C-F1.**

### 9C.3 Findings — what the consumer paths expose, put to Rob, not resolved here

**9C-F1 — Tr8's assertion is about the unbuilt state, and the build changes its form, not only
a name.** The 7F fixture's Tr8 (E24 from the traversal side) asserts that
`reach(X, 'expense_in_respect_of_plan')` is **refused by name — "not ruled" — never a silent empty
list**. That was the right assertion while the kind was unbuilt: the substrate must not pretend an
unruled name is an empty relation. After 9C the kind is ruled and `reach` returns what it returns
for every ruled kind with no claim: an empty `endpoints` list. So Tr8 cannot be substituted by name
alone — its check must become *E24 through 7F on the ruled kind: nothing connects X to P → empty
endpoints, no candidate, no claim minted; the kind is ruled, so an empty answer is the truthful
answer, not silence*. The half of Tr8 that was about the unbuilt state retires the way item 5's
absence checks did; the half that carries E24's meaning survives on the ruled kind. **This is a
change of a consumer fixture beyond a name.** The §2.4 discipline says stop and report. Reported:
*is this a retirement of the same class as Pl7 / Pl9 (an absence check whose absence has ended,
restated truthfully), or a consumer change?* My reading: the same class — 7F's `reach` is untouched;
what changes is a fixture assertion about a name's registry status. **The question for Rob:** rule
it a retirement, so the substitution proof stays *only names and catalogue lines changed in the
consumer fixtures*, with this one assertion's restatement recorded beside the three earlier
retirements of its class.

**9C-F2 — 7J reads E's relation as the gate on which expenses enter a plan's derived accumulator;
E says the relation derives nothing about terms applied.** These are compatible, and the fixture
must show it rather than assume it: 7J's derived accumulator reads *the set of expenses a party
asserted in respect of P* (E's floor, exactly) and then reads **the plan's insurer's own
`applied_to_deductible` stances** on each — the relation selects, the stance carries the amount. E8
through 7J is the demonstration: an expense in respect of P that the insurer denied and never
adjudicated toward the deductible is *listed* by the accumulator as unadjudicated and contributes
nothing — not excluded (the relation stands), not counted (no stance), not zero (absence is not
zero). That is already 7J's behaviour on the stand-in; on the ruled kind it becomes an E-fixture
check as well (§9C.4 c2). **Not a question — a statement 9C makes demonstrably true. Recorded so
that 7J's use is never read as having extended E's floor.** (Observed, not 9C's: 7J's diagnostic
text says *the household's asserted expense_in_respect_of_plan*; E's floor admits any party,
including the insurer, and 7J's code reads any established claim regardless of asserter. A
consumer's note wording, left to 7J.)

**9C-F3 — none.** The other two kinds have no consumer today: `obligation_in_respect_of_plan` and
`payment_in_respect_of_plan` are read by nothing in item 7. Their build is registry entries and the
E fixture only; the substitution proof for them is vacuous, and the record should say so rather
than imply a swap was exercised. When 9D rules the premium / deduction stance kinds, or a consumer
is opened over them, that consumer takes the ruled kinds from the start.

### 9C.4 Cases — the consumer paths on the ruled kinds

E's own cases are ruled and are the fixture's body. 9C's additional cases are the four places a
consumer reads E's kind, each a check that the consumer's answer on the ruled kind is the answer it
gave on the stand-in — evidence the swap changed the identity of the relation and nothing else:

| # | Case | Through | What must hold |
|---|---|---|---|
| **c1 (E24 / Tr8)** | Kim under P (9A), X incurred by Kim (9B), nothing connects X to P | 7F `reach(X, EXPENSE_IN_RESPECT_OF_PLAN)` and `reach(P, …, as_object=True)` | empty endpoints; no candidate; no claim minted; **the ruled kind, not a refusal** (9C-F1) |
| **c2 (E8)** | X in respect of P; Lakeview Health's *denied* stance; plan paid $0; cash-paid | 7J `accumulator(P, d)` | X listed `unadjudicated`; contributes nothing; the relation stands — not excluded, not zero |
| **c3 (E2 / E4 / Ju11)** | one visit in respect of A and B; Lakeview Health's stance for A, Cigna's for B | 7J | A derives from Lakeview Health's stance only, B from Cigna's; no priority, no split, no sum |
| **c4 (E5)** | the cash prescription — no relation | 7J | not in P's set; no *uninsured*, no *not covered* anywhere in the report |
| **c5 (F14 from 9A)** | Y in respect of P2 by a stranger's incurrence | 9A's fixture | no membership derived — unchanged on the ruled kind |

### 9C.5 What could go wrong, and where it is measured

Semantically, in the swap (§9A.3's rule): any change the accumulator fixture needs beyond the
catalogue line and the two claim sites is a finding, not a fix — 9C-F1 is the one found on the
record before the build, and it is 7F's fixture, not 7J's. Structurally, in three places the E
fixture measures: the registry refusing each kind's wrong subject type and a plan-subject claim
(E10); `s106`'s family invariants running over six real members for the first time (a typed-slot
merge, a seventh pair, a `knowing_relation` on a member — all now measured on E's three); and the
convergence refusals **as absences with the ruled kinds present** — E24 (membership + incurred-by),
E15 (through X), E18 (through O), E6 (through a document) — where the only sound measurement is
*no proposition of the ruled kind exists that no party asserted*, taken after every convergent
fact is in the record.

Smoke `s119_plan_relations.py` on the pattern of s117 / s118: the fixture passes; mutations each an
attempt to give a plan relation a meaning above its floor — **which-plan from membership and date**
(E2 / E3 / E5) · **X → P from Kim under P + X is Kim's** (E24) · **O → P from X → P + O → X** (E15) ·
**p → P from p → O + O → P** (E18) · **an inverse `plan_covers_expense` appears** (E10) · **the
relation withdrawn on the insurer's denial** (E8 reversed) · **a typed-slot `in_respect_of_plan` merge**
(PE8 / G) · **a `which_plan` resolver over two claims** (E2) · **a knowing relation designated** (E's
undetermined manufactured) · **a temporal guard: p → P refused when p precedes P** (E22) — all caught.

### 9C.6 Ruling sought

> **(1) Rule 9C-F1:** Tr8's *refused by name* half is an absence check whose absence ends with the
> build, restated truthfully on the ruled kind (empty endpoints, no candidate, no claim) — a
> retirement of the class of Pl7 / Pl9 and item 5's, not a consumer change; 7F's `reach` untouched.
> **(2) Authorise the build** of `expense_in_respect_of_plan`, `obligation_in_respect_of_plan` and
> `payment_in_respect_of_plan` exactly as §E.8 describes, §E.10 accepted and §G.9 represents: three
> registry entries (no knowing relation, no role, no boundary), the E1–E24 fixture with the
> absences and E2 / E8 / E24 mandatory, the accumulator fixture re-run with only the catalogue
> line and the stand-in's name changed (31/31), the 9A fixture's F14 by name (27/27), the
> retirements foreseen in §9C.2 (Pl7 / Pl9 as §E.8 pre-authorised; `s106`'s wording; the registry
> comment; Tr8 per (1)), `s119`, the gate. No consumer changes. Nothing in E or G reopened; D′.11
> untouched.

**What 9C leaves exactly where it found it:** every consumer · who is knowing for a plan relation
(undetermined — a 9D-or-later question, if ever) · candidate generation · the stance / value
catalogue (9D — the premium, deduction and adjudication kinds the fixture uses as content or as
stand-ins named as such) · D′.11 · F beyond 9A · G's one-family-or-six question (answered by G:
six).

---

### 9C.7 Ruling — Rob, 2026-09-19: 9C-F1 accepted, 9C-F2 a boundary statement, 9C-F3 accepted; build AUTHORISED

*9C's surface is cleanly bounded; 9C-F1 is the only semantic question.*

**9C-F1 — accepted.** Tr8 changes from an absence-of-kind assertion to a ruled-kind behaviour
assertion. Before E is built the kind is not ruled and `reach(X, kind)` refused by name is the
correct result; after, the kind exists and is ruled, so `reach` must be allowed to answer — and with
no qualifying relation asserted the truthful result is an empty endpoints list, which creates no
candidate, infers no relation and manufactures no empty semantic claim. `reach` itself does not
change. *The old Pl7 / Pl9 absence class is retired, and its replacement is a positive emptiness
assertion on the now-ruled kind — a fixture-semantic change, not a new ontology rule.* **The
important negative: 9C does not change `reach`; it changes only what the fixture is entitled to ask
of `reach`, because E has changed the status of the named kind.**

**9C-F2 — accepted as a boundary statement,** to remain a statement rather than a finding to solve.
7J may use `expense_in_respect_of_plan` to select the expenses entering its derived accumulator;
that does not extend E's semantics. E8 is the executable boundary: *denied + unpaid + cash-paid +
in respect of P → represented as unadjudicated, not excluded and not reduced to zero.* The relation
answers whether the expense is in respect of the plan; the insurer's stance answers the
adjudication / amount question; 7J consumes both without either consumer semantics being
retroactively attributed to E.

**9C-F3 — accepted.** The obligation and payment relations have no current consumer on this
substitution surface; their build is registry / fixture construction, not an invitation to
manufacture consumers.

**Build AUTHORISED exactly as specified.** Scope: three E registry entries · the E1–E24 fixture ·
no knowing relation · no role classification · no boundary · Tr8 changed from *not ruled / refused*
to the ruled-kind empty-endpoints assertion · Pl7 / Pl9 retired as §E.8 authorised · `s106`'s
*accepted and unbuilt* wording retired · G.9's three *unbuilt* statements retired · 7J's existing
consumption preserved · **no changes to `reach`** · no reopening of E · no reopening of G · D′.11
untouched. **The central invariant for the build: E supplies the three relation kinds and their
representation. 9C may expose their existing consumer use, but it may not derive new meaning from
that use.**

---

#### Built — 2026-09-19 (9C)

`core/database.py`: `EXPENSE_IN_RESPECT_OF_PLAN`, `OBLIGATION_IN_RESPECT_OF_PLAN`,
`PAYMENT_IN_RESPECT_OF_PLAN` — three registry entries exactly as §E.8 describes, §E.10 accepted and
§G.9 represents: expense / obligation / payment subject, the plan the object, `symmetric False ·
reading_establishes False · relational_knowing True`, **no `knowing_relation`, no `'role'`, no
boundary** — knowing undetermined by E's ruling; the in-respect-of family now six members, one per
ruled pair. One comment block states E's floor once, the NOT-list, the two §E.6 invariants, and 7J's
use as §9C.7 bounded it (*the relation selects, the insurer's stance carries the amount; adds nothing
to E's floor*). The G.9 block's three *(E, accepted, unbuilt)* lines → *(E, built 9C)*. **Nothing
else** — no inverse, no `which_plan`, no `plan_id`, no resolver, no order guard, no candidate
generator, no family abstraction; **`reach` untouched** (the diff against `4f98580`: three constants,
three entries, comments; no function changed).

**The oracle:** `tests/test_plan_relations_fixture.py` — one fixture over E1–E24 as §E.8 specified,
plus c1–c5 — 33 checks: the registry (three kinds, six family members, E10's refusals by the registry
of a plan-subject claim and of each kind's wrong subject type, no `plan` column on any anchor); E1 /
E11; **E2 mandatory** (Kim under both Lakeview Health plans by 9A's ruled kind, a cleaning on 4/2 — no claim
exists until Rob asserts one; then one, no priority, the medical plan has none); E4 (two plans, both
reached, no primary / secondary key); E9 (Rob's and Kim's claims side by side; Kim's retraction
contests hers, Rob's stands); E3 (Lakeview Health's retroactive ending and reversal are stances; the relation
stands); **E8 mandatory** (denied, plan paid $0, cash-paid — the claim stands established, the
snapshot unchanged); E5 (never submitted: empty; no *uninsured* kind or helper); E6 / E21 (the EOB
concerning X6 and P derives nothing; a reading-sourced claim of the kind is a candidate); E7 (the
authorization tied by `proposition_concerns`; X7 → P not derived); E12 / E13 / E14 (the premium as
content on O → P; the employer's contribution a claim on the employer; **O′ with the insurer the
obligor is the same kind — money direction is not relational meaning; no `plan_covers_obligation`**);
E15 (X → P + O → X ⇒ nothing for O → P); E16 (a plan cannot fill `obligation_replaces`' slots); **E17**
(p → P with no obligation anywhere, none manufactured); E18 (p → O + O → P ⇒ nothing); E19 (Lakeview Health's
payment to Riverbend Hospital: p′ → P by Rob, no household party on p′); E20 (no discharge, no status column); **E22
permanent** (December's premium for the January plan; a January visit on a plan minted in March —
both accepted, no order guard); E23; **E24 mandatory** (Kim under P in effect on 3/20 + X24 incurred
by Kim — no proposition of the kind for X24 in any state, from either direction of `reach`, the
snapshot unchanged); E10 (no inverse; `reach(P, …, as_object=True)` lists every asserted expense in
every state; no resolver).

**c1–c5 — the consumer paths on the ruled kinds:** c1 (9C-F1) `reach(X24, EXPENSE_IN_RESPECT_OF_PLAN)`
answers empty and is not refused, while the stand-in's name is still refused *not ruled*; **c2
(9C-F2, E8 through 7J):** X8 — denied, $0, cash-paid, in respect of P — is *listed* as
unadjudicated and *named* in the reason, and the derived value is **undetermined**: not excluded,
not counted, not zero, and not a partial sum either — 7J's own rule (absence is not zero) applied to
an expense E's relation put in the set; X's $300 in the basis. **A correction on the record:** the
fixture's first draft expected a partial sum (300) — that was the fixture presuming what 7J does,
not 7J; corrected to 7J's ruled behaviour, no consumer touched. c3 (E2 / E4 / Ju11): P's basis
carries Lakeview Health's stances only, P2 derives from Cigna's only — no priority, split or sum. c4 (E5): the
cash prescription nowhere in the report, no *uninsured* / *not covered* key or value. c5 (F14 from
9A): no membership derived from the ruled kind.

**The substitution — the decisive test:** `tests/test_accumulator_fixture.py` changed by exactly
the stand-in's removal (`STAND_INS` is now empty — every relation and role 7J reads is ruled), the
catalogue line, and the two `claim(...)` sites' names — **31/31, no other change.** 9A's fixture F14
by name (27/27); `s117`'s two membership mutations by name (17/17). `obligation_in_respect_of_plan`
and `payment_in_respect_of_plan` have no consumer; the swap is vacuous for them (9C-F3), and their
proof is the E fixture alone.

**The retirements, truthfully:** (1) **Tr8, per 9C-F1's ruling** — *the unbuilt kind is REFUSED BY
NAME, never a silent empty list* → *on the RULED kind reach answers EMPTY: no endpoint, no candidate,
no claim; an unruled name is still refused by name* — the fixture's entitlement to ask changed,
`reach` did not (41/41); (2) the plan fixture's **Pl7 / Pl9**, as §E.8 pre-authorised — *no kind, slot
or claim ties the premium to P* → *the only kind that can is E's `obligation_in_respect_of_plan`, by
assertion; none asserted here*; *no plan ↔ expense kind* → *the one is E's, asserted never derived, no
inverse* — `plan_id`, `which_plan`, `plan_covers` still absent (35/35); (3) `s106`'s *E's three
accepted and unbuilt by instruction; 3 ≤ built ≤ 6* → *all six ruled pairs, E's three built by 9C* —
its slot / flag / no-`knowing_relation` checks now run over six real members (14/14); (4) the
registry comment; (5) three docstring lines (7F's, 7J's NOT-BUILT lists) and one 7F comment that
had been stale since 9A (*no role kind is ruled*) — words only; (6) **found by the full gate, not the
touched-fixture runs** (9B's lesson, again): three older fixtures pinned the exact set of ruled kinds
on a subject slot — obligation-replaces and obligation-identity (*the obligation-subject kinds are
exactly correspondence, replaces and in-respect-of*) and payment-identity (*payment subject slots
carry only the four ruled relation kinds*) — and E's `obligation_in_respect_of_plan` /
`payment_in_respect_of_plan` now sit on those slots; each set restated with the E kind named and
its own absences kept (no source word; no `terms` / `balance` / `toward`). Same class as 9B's
borrowed names: a fixture asserting the registry's shape as of its own pass, which a later ruled
kind legitimately changes. The first gate ran 1379 / 4 on these; the second is the count below.

**Smoke `s119_plan_relations.py`:** the fixture passes; ten mutations, each an attempt to give a
plan relation a meaning above its floor — which-plan from membership and date · X → P from a shared
person (E24) · O → P through X (E15) · p → P through O (E18) · an inverse `plan_covers_expense` ·
the relation withdrawn on the insurer's denial (E8 reversed) · a typed-slot `in_respect_of_plan`
merge (PE8 / G.9) · a `which_plan` resolver · a knowing relation designated · a temporal guard on
p → P (E22) — **all ten caught on the first run**, baseline re-established after every undo.

**Left where it belongs:** who is knowing for a plan relation (undetermined) · candidate
generation · the stance / value kinds the fixture names as 9D's (`adjudication`, `plan_paid`,
`coverage_ended`, `authorization`, `contribution`, `occurred_on`, `plan_year`, `deductible`,
`applied_to_deductible`) · D′.11 · every consumer. No schema, no migration. Gate 1373 → 1396,
0 failed.

#### Accepted — Rob, 2026-09-19 (9C)

Accepted on the record before the second gate landed, with the acceptance commit held until it was
green as he instructed; the gate then ran 1396 / 0 and produced nothing that would change the
basis. Rob's pre-acceptance checks, all clean: the Tr8 change exactly the ruled transition (the ruled
kind answers `endpoints == []` with a proposition-count assertion showing absence of a claim, not an
inferred empty one; the stand-in's name still refused); 7J at 31/31 with only the catalogue line and
two claim sites the consumer-boundary evidence, and c2's correction (an unadjudicated expense
leaving the derived value undetermined is 7J's rule, not E's decision); the `database.py` diff
exactly three constants and three entries with `reach` untouched — *9C supplies representation, not
new traversal behaviour, directly inspectable*; E's three pairs distinct, no consumer for the latter
two; the F14-style reverse case refusing `under_plan` from `in_respect_of`; the surviving *unbuilt*
references intentional or unrelated; production scope confined to `core/database.py`. On the gate's
four first-run failures: *not four new semantic problems* — three stale exact-slot-set absences with
one structural cause (E's kinds legitimately inhabit those subject slots now), corrected in the
fixtures rather than by weakening the registry, and `evidence_tie` a deliberately retained finding
fixture, not 9C's; the s104 one-off not promoted to a finding without evidence. **No reopening of E,
G or D′.11.** 9D remains unopened until its own semantic questions are surfaced and ruled.

---

## Pass 9D — The stance and value catalogue

*Opened by Rob 2026-09-19 after 9C's acceptance (`c1c52e9`). The widest and least-ruled pass, last
so that every kind in it can name the role its knowing relation designates (§3). Run as the others:
semantic surface → cases / findings → ruling → build authorisation. **9D's surface is discovered
from what the consumers read today and from the rulings that already fix these kinds' meaning; the
consumer paths are evidence of what the kinds must carry, never a source of semantics.** No code by
this opening. One question governs the rest and is put first (§9D.3, 9D-F1).*

### 9D.1 What is already fixed — per group

| Group | Kinds (stand-in names) | Fixed by | What is fixed |
|---|---|---|---|
| **(i) the acknowledgment** | `acknowledged` | ACKNOWLEDGMENT_EVIDENCE_CASES ruling (Rob, 2026-09-12); D4; **§D′.4** (a finding); 7G RG-a | **P-ack: the entitled party's stated position about a payment, as of a stated date**; *P-ack for a payment = discharge of that payment* by definition, never inferred; **one knowing party — E**; four channels (E's held statement · E's servicer of record's held statement *bounded by the household's evidence that S serves E* · E's / S's live system, dated · the user's testimony reporting one of those); *the user is not a knowing party for P-ack* (K5); weakest-link strength; **every acknowledgment is dated — frozen**; a cleared payment does not establish acknowledgment (K6); acknowledgment of a payment and statement of a balance are two propositions (K8); the return of a payment is another kind (Dg18). **§D′.4:** *which obligation E applied p to* is a hidden operand of `acknowledged(E, p)` — the catalogue must decide whether O is a participant or content; acknowledgment evidences a candidate for *p in respect of O* and never establishes it |
| **(ii) the P-ack stances** | `balance` (on O) · `billed` (on X, the provider's) · `patient_responsibility` · `plan_paid` · `applied_to_deductible` (on X, the insurer's) · `deductible_applied` (on P or (person, P), the insurer's) · `eligibility` (on (person, P), the insurer's) | the same ruling (balance); 7G TS-base / TG-base; 7H §7H.2 (*P-ack for X's charge; asserter in effect as provider of X*; *the insurer's dated claims on X, asserter in effect as insurer of X*; *a claim on X by a party not in effect in the named role is reported, never governing* — F3 / K5); 7J (Pl10 the insurer's accumulator stance; F5 the insurer's *never eligible* beside membership, deriving nothing); TS (a stance stands until the next, per party · kind · identity; conflict at one date → none); C6 / C7 | each is **the party-in-the-role's dated position** about the subject — a position, not the world; dated (frozen); governing by G per the party's series; conflict → none; never stored; the household's figure is never the position (U6, K5); *exempt* ≠ unknown ≠ zero (C6); a denial is not an adjudication (C7) |
| **(iii) value kinds** | `amount` (on a payment) · `occurred_on` (on a payment; on an expense) | PAYMENT_IDENTITY (*dated relations*, not fields); Kn7 (the mother paid — minting ≠ knowing; her knowing for `occurred_on` undetermined via the stand-in); K6 (the bank can know the household's money left); 7G / 7H / 7I (one established value or undetermined — `_one_value`; conflict → undetermined; the date read from `as_of` or content) | a value is a claim on the subject with content the figure or date; **who is first-hand for it is unruled** — the payer, the payee, the bank as artefact origin, the provider, the person who incurred it are the candidates the record names |
| **(iv) term kinds** | `deductible` · `individual_deductible` · `plan_year` (on P) | PLAN_IDENTITY §2 (*whether a service is covered = the insurer's dated stance — a term claim about P*); 7J (the governing term at d, G named; content a money amount or **`none`** — *the rule does not exist*, an answer; no claim → `unknown`; the plan year `as_of` = start, content = end; **no `met`**); Pl15; APPLICABILITY | a term is **the insurer's stance about P's rule** as of a date; the SBC read is a candidate; the household's *our deductible is $1,000* is testimony; `none` is content 7J parses, not a kind |
| **(v) the determination** | `determination` (on X) | 7H §7H.7 item 2, ruled: content **exactly one of four names** (`provider_adjustment · user_paid_cash · unpaid · pending_claim`), any other *unrecognised* and never current; `as_of` required; **any party may make it** (D12 the household; the provider; the insurer); *whether a party's role constrains its determination is the catalogue's to rule, not 7H's* — 7H reports the asserter's roles as facts and constrains nothing; superseded never overwritten; `unresolved = 0` is not `user_paid_cash`; a denial is not `pending_claim` | the kind is fixed; **who may determine, and who is knowing for a determination, is 9D's** |
| **(vi) the kinds the consumers do not read** | `cleared` · `returned` (on a payment — the bank's / E's) · `denial` (on X — the insurer's; C7) · and the names other fixtures have used as stances: `adjudication`, `coverage_ended` (Pl12 — the insurer's retroactive ending, a stance about P beside F's `under_plan_ended`), `authorization` (Pl11 — a stance about P with the service as content), `contribution` (Pl8 — a claim about the employer party) | Dg3 / Dg18 (7G reads no cleared / returned kind); Rc6 (7H reads no denial); Pl11 / Pl12 / Pl8; F5 | named so the catalogue rules them and the consumers cannot read one as another: **a return is not a non-acknowledgment; a denial is not a determination; a cleared line is not discharge; the insurer's termination stance is not the household's boundary claim** |

**Fixed across all six (§2.3, §2.6):** a kind is slots + the registry's existing keys; content stays
opaque — what a consumer parses from it (money, a date, `none`, one of four names) it parses as it
does today; no consumer changes; registry only; **relational knowing follows the role** — the kinds
that wait on 9B's designated participants gain a `knowing_relation`, and `derived_strength` reads
the ruled class where it read the foundation stand-in.

### 9D.2 What the consumers read today — the discovered shape

The stand-ins are not one shape. Read from the code, not assumed:

| kind | subject slot | party slot? | `as_of` | content | who the consumer takes as the position-holder | the consumer's gate |
|---|---|---|---|---|---|---|
| `acknowledged` | — | **`subject_party_id` = E** · object the payment | yes | — | **the subject party** (`e['party']`) for the entitled test; **the utterance origin** for strength | 7G: established · dated ≤ d · *party* entitled in effect at `as_of` · strength KNOWING (foundation `{'institution'}`) |
| `balance` | obligation | **none** | yes | money | **the utterance origin** (`asserter`) | 7G: asserter entitled in effect at `as_of` → governing series; else reported |
| `billed` · `patient_responsibility` · `plan_paid` | expense | none | yes | money | the utterance origin | 7H: asserter in effect as provider / insurer of X at `as_of` |
| `applied_to_deductible` | expense | none | yes | money or `none` | the utterance origin | 7J: asserter in effect as insurer of the plan at `as_of` |
| `deductible_applied` | plan (+ `object_party_id` the person, optionally) | none | yes | money | the utterance origin | 7J: asserter in effect as insurer of P |
| `eligibility` | **party** (the person) · object the plan | (the subject IS a party — but the person, not the holder) | yes | text | the utterance origin | 7J: listed with state and date; **no gate** (F5: deriving nothing) |
| `deductible` · `individual_deductible` · `plan_year` | plan | none | yes | money / `none` / a date | the utterance origin | 7J: **no role gate** — the latest established at or before d, any party |
| `amount` · `occurred_on` | payment / expense | none | `occurred_on`: the date in `as_of` or content | money / date | the utterance origin | `_one_value`: one established value or undetermined; **no knowing test** |
| `determination` | expense | none | yes (required) | one of four names | the utterance origin; **roles reported as facts** | 7H: established · dated · recognised; **no role gate** |

Two things this table shows that no ruling has said in one place: **(a)** the P-ack kinds already
come in two shapes — the acknowledgment carries its position-holder as a participant (`subject_party_id`
= E) while every other stance leaves the position-holder implicit in *who asserted it* and *which
role that party held at the date*; **(b)** knowing for every one of them is today the foundation
stand-in (`{'institution'}` ≈ *E*; `{'person', 'institution'}` ≈ *anyone*), which the consumers
then correct with their own role gates. The role gates are the consumers' rulings (RG-a, TG-base,
7H's, 7J's) and stay theirs; **what 9D must rule is what the kind itself says about its holder and
its knowing.**

### 9D.3 Findings — put to Rob, not resolved here

**9D-F1 — the position-holder of a stance: participant, or hidden operand? (§D′.4 generalised;
governs every other finding).** The acknowledgment ruling names the proposition *E's stated
position*; K5 says the user is not knowing for it; K8 says a balance statement is a second
proposition. So *whose position* is part of what the claim is. Today that party is (a) a slot on the
acknowledgment and (b) nowhere on any other stance — it is the asserter, gated later by a role the
consumer reads through 7F. Under K8 (a proposition's operand must be a participant or content, never
implied) the second shape carries a hidden operand exactly as §D′.4 found for O. Two shapes are
possible for the catalogue, and they differ in consumer impact:

- **Shape H (holder implied — the shipped shape for (ii)–(v)).** The stance's subject is the thing
  (O, X, P); the holder is *the asserting party*; the kind's `knowing_relation` designates **the
  party in role R on the subject at `as_of`** — `entitled_party_of` for `balance` and the
  acknowledgment, `provider_of` for `billed`, `insurer_of` for the insurer's X-stances,
  `insurer_of_plan` for the P-stances and terms — so that *knowing* = *the asserter held the role
  when the position was stated*, read through 7F's `in_effect` at the claim's date. **This is a new
  shape of knowing relation:** 9B's `KNOWING_SUBJECT_PARTY` reads a slot; this one reads a role, a
  date and (for the servicer channel, below) a second claim's strength. **No consumer changes** —
  the consumers already make this exact test; the kind's knowing would coincide with their gate.
  K5 falls out: Rob's *Harbor says $1,900* with no artefact is Rob's utterance, Rob holds no role,
  not knowing, reported and never governing — the ruled outcome. The acknowledgment's existing
  party slot becomes redundant with the asserter (or is retired for consistency — a consumer change
  to 7G's `e['party']` read, which §2.4 forbids without a ruling).
- **Shape P (holder as participant).** Every stance gains a `subject_party_id` = the holder, the
  thing in an object slot (`balance(Harbor, O)`, `billed(Riverbend Hospital, X)`, `deductible_applied(Lakeview Health, P)`);
  `knowing_relation` = `KNOWING_SUBJECT_PARTY` as 9B ruled for roles (*a party is first-hand for its
  own position* — R2), uniform and slot-read; Rob asserting *Harbor's position is $1,900* is
  testimony about Harbor's position (holder Harbor, origin Rob → not knowing) — K5 exactly, and
  representable without an artefact. **But every consumer read changes shape:** 7G's `balance`, 7H's
  three, 7J's four read the thing on the subject slot and take the asserter from the utterance; the
  role gates would move from *asserter* to *holder*. That is a consumer change on every consumer
  and a schema-free but shape-changing swap — §2.4 refuses it unless Rob rules the shape.

The servicer channel bears on both: *E's servicer of record's held statement is E's acknowledgment
at weakest-link strength, bounded by the household's evidence that S serves E.* Under H the knowing
relation must admit *the asserter holds `servicer_of` on O at `as_of`* at the strength of that
`servicer_of` claim (weakest link — the first knowing relation to compose a strength); under P the
holder is E and the asserter S, and the same weakest-link rule applies between them. **Either way
the servicer channel is a second clause of the relation, and 9D must say so or leave it
undetermined (S3 then knowing only for its own position, never for E's — Kn12 holds).**

*My reading, for Rob to reject:* H is the shape the record has been building (7G–7J were ruled on
it; §2.6's *the acknowledgment kind's entitled party of the obligation* is H's phrasing), K8's
objection is answered by naming the relation rather than adding a slot, and P is the better
ontology only if testimony-without-artefact must be representable — which K5 and ARTEFACT_ORIGIN's
channel model say it need not be. **H, with the acknowledgment's party slot retired into the
asserter as a truthful retirement, is the recommendation — but the retirement touches a 7G read
and is Rob's to authorise.**

**9D-F2 — the acknowledgment's O (§D′.4).** Under H the acknowledgment has no O; 7G supplies O from
its own argument and asks whether the asserter was E *of that O* at `as_of` — so one ack by Harbor on
p discharges p on every obligation Harbor is entitled to that p is attached to (D′3's two
obligations). Is O content, a participant (`object_obligation_id` beside the payment — the registry
has one object slot per kind today; two objects is a new shape), or absent with 7G's test as the
answer? *Reading:* absent — the acknowledgment is E's position about p; which O it discharges is
the attachment (D′'s `payment_in_respect_of_obligation`, asserted) joined with E's role, both
already in the record; naming O in the ack would let the ack establish the attachment, which D′
refused. Rob's.

**9D-F3 — value kinds: who is first-hand for a payment's amount and date, an expense's date?** The
candidates the record names: the payer and the payee (9B's `paid_by` / `paid_to` holders) for a
payment; the bank as the origin of the held line (K6 — a reading, through `artefact_origin`,
already knowing-capable); the provider (`provider_of`) and the person who incurred it
(`incurred_by`) for an expense's date; **the household as minter — never** (Kn7). A value's knowing
relation would designate *a holder of any of a set of roles on the subject* — a second new shape
(a role-set). Or: values stay foundation-mapped `{'person', 'institution'}` as today (anyone
knowing — which is what the fixtures assert now and what Kn7 called undetermined). Rob's; the
consumers read no strength for values, so either answer changes no consumer.

**9D-F4 — terms: the insurer's position, and 7J reads any party's.** If 9D rules the term kinds'
holder is `insurer_of_plan`, 7J's read (latest established, any party) is unchanged — it reports;
but the household's own *our deductible is $1,000* becomes not-knowing and still governs 7J's term.
Is that the intended reading (7J: *we do not have the deductible* is about absence, not strength),
or does 7J's term gain the role test *exactly as TG-base gained the entitled-party test* (7H's
phrase for determinations)? That is a consumer change 9D may not make; it is recorded as the
question 7J's ruling left open.

**9D-F5 — the determination: any party may make it; who is knowing?** Under H there is no role to
designate (D12: the household determines `user_paid_cash`; Riverbend Hospital `provider_adjustment`). Options:
knowing undetermined by design (no relation named, as `under_plan`); or *the asserter is first-hand
for its own determination* — which is Shape P's relation applied without a slot, and would make
every determination knowing, which says nothing. *Reading:* undetermined — a determination is a
party's reading of the situation, not a position it holds first-hand; 7H's *current* rule never
reads strength. And **the four-name vocabulary stays 7H's** (§2.3: content is opaque to the
catalogue) — 9D rules the kind, 7H recognises the names.

**9D-F6 — the unread kinds are stances with holders too.** `cleared` / `returned` on a payment: the
bank's position (holder: the artefact origin — a reading channel, not a role) or E's (`returned` as
Dg18 — E returned p unapplied: E's position, `entitled_party_of`); `denial` / `adjudication` on X:
the insurer's (`insurer_of`); `coverage_ended` on P (or on (person, P)): the insurer's
(`insurer_of_plan`) — **and its relation to `eligibility` and to F's `under_plan_ended` must be
stated**: three things that could each be read as *coverage ended* — the household's boundary claim
(F), the insurer's eligibility stance (F5), the insurer's termination stance (Pl12) — are three
kinds or two. `authorization` on P (Pl11) the insurer's; `contribution` on the employer party — not a
stance on a thing, a claim about a party, possibly not 9D's at all. 9D must at least **name** these
so no consumer reads one as another; whether it rules each fully is 9D-F8.

**9D-F7 — `as_of` required: a registry key, or the fixture's assertion?** Every P-ack is dated
(frozen). The registry has no *dated* flag; boundaries require `as_of` via their guard; the consumers
disqualify undated stances themselves. A `dated: True` key would be 9B-F1's move again
(classification, no consumer instruction). *Reading:* not needed — the consumers already refuse, and
a kind's fixture can assert *an undated stance never governs* without a key; keep the registry's
shape. Rob's.

**9D-F8 — one pass or several.** 9B ran seven roles in one pass because one knowing relation served
all seven. 9D's six groups have **four** different holder relations (a role-in-effect; a role-set;
the asserter; none) plus the servicer clause. *Proposed:* rule 9D-F1 and 9D-F2 first — they fix the
shape of every stance — then run the groups as 9D-i (the acknowledgment and `balance`, with the
servicer clause), 9D-ii (the provider's and insurer's stances on X and P, `eligibility`, terms),
9D-iii (values), 9D-iv (the determination), 9D-v (the unread kinds), each with its own cases and
build, in that order; or run one pass with six sections. Rob's.

**9D-F9 — the foundation map's remainder.** When 9D's kinds carry relations, `derived_strength`
reads the ruled class and the callers' `knowing` map serves only `artefact_origin` (ARTEFACT_ORIGIN
§4, ruled) and any kind 9D leaves unruled. The argument stays (the convention); the map entries for
ruled kinds retire from the fixtures truthfully. A statement, not a question — recorded so the
build does not appear to remove a mechanism.

### 9D.4 Cases — an index, by group; new cases only where 9D adds a question

The rulings' cases are the fixture's body and are not rewritten here: **K1–K8** (the acknowledgment
and balance — E's own statement; the servicer's; S3's; the portal; the user's report; the cleared
payment; conflicting sources by date then channel; ack ≠ balance), **D4, D′7, Dg3, Dg18** (the ack's
shape; the return), **Rc9, Rc6, Rc15, Rc16, F3 / K5** (the provider's and insurer's stances; the
denial; the household's *the EOB said*), **Pl10, Pl15, Ju3–Ju11, F5, C6, C7** (terms, the
accumulator stances, eligibility, exempt / unknown / zero), **D12, Rc5, Rc19** (determinations),
**Kn7, K6, Pm9** (values), **Pl11, Pl12, Pl8** (authorization, termination, contribution). 9D's own
cases are the position-holder cases:

| # | Case | Under H | Under P |
|---|---|---|---|
| **St1 (K1)** | Harbor's held statement: *balance $1,900 as of 3/31* — reading, origin Harbor | claim by reading → candidate; strength via `artefact_origin` = Harbor, Harbor entitled in effect 3/31 → **knowing** (C1–C3 weakest link) | the same, holder Harbor |
| **St2 (K5)** | Rob types *Harbor says the balance is $1,900*; no artefact | Rob's utterance; Rob holds no role on O → **not knowing**; reported, never governing | holder Harbor, origin Rob → not knowing; representable as testimony about Harbor's position |
| **St3 (K2)** | BillCo's statement, BillCo servicer of O by the household's `servicer_of` claim | BillCo not entitled → the **servicer clause**: knowing at the weakest link of BillCo's `servicer_of` claim (established by Rob → not_knowing? Rob asserted the servicing; is the household knowing for *S serves E*? — Kn6's question, now answerable through 9B: the household is not the subject party of `servicer_of`, so the servicing claim is not_knowing and the ack's strength is not_knowing) | the same clause between holder E and asserter S |
| **St4 (K3 / S3)** | S3's own statement of *your balance*, never authorised | S3 holds no role → not knowing (its own `servicer_of` claim is knowing for the role, Kn12 — but the balance is E's position, not S3's) | holder E asserted by S3 → not knowing |
| **St5 (7H Rc9)** | Riverbend Hospital's bill: *billed $1,200* by reading of the bill | candidate; origin Riverbend Hospital, Riverbend Hospital provider of X → knowing | the same |
| **St6 (the insurer's stance on the wrong plan — CC1)** | Cigna states *applied $150* on X, in respect of A and B; Cigna insures B only | knowing for B's series, not a holder for A — 7J's per-plan read unchanged | holder Cigna; the plan gate stays 7J's |
| **St7 (Pl12 vs F5 vs F)** | Lakeview Health: *coverage ended 6/30, as of 8/15*; the household: `under_plan_ended` 6/30; Lakeview Health: *never eligible* | three claims, three kinds (9D-F6) — none derives another; 7J lists the two stances beside membership | the same |
| **St8 (D12 vs Riverbend Hospital)** | Rob determines `user_paid_cash`; Riverbend Hospital determines `provider_adjustment` at one date | two determinations, knowing undetermined for both (9D-F5); 7H: cross-party conflict → none | holder = asserter in both; the same |
| **St9 (Kn7)** | the mother paid; she says *$300 on 3/3*; Rob says *3/4* | `amount` / `occurred_on` claims: knowing per 9D-F3's answer — the mother `paid_by` holder → knowing if the role-set includes the payer; Rob not | the same |
| **St10 (K6)** | the bank line `HARBOR 1412.00 03/05` — a reading | `amount` / `occurred_on` candidates; origin the bank → knowing for the value if the bank is in the role-set as artefact origin; **never** an acknowledgment | the same |

### 9D.5 Candidate — pending 9D-F1; two variants, the registry entries only

**Under H** (the recommendation): every stance kind keeps its shipped slots; `symmetric False ·
reading_establishes False · relational_knowing True`; `knowing_relation` a **new named relation
per holder role** — `KNOWING_HOLDER_OF_ROLE(entitled_party_of)` for `acknowledged` (subject party
retired) and `balance`; `(provider_of)` for `billed`; `(insurer_of)` for `patient_responsibility`,
`plan_paid`, `applied_to_deductible`, `denial` / `adjudication`; `(insurer_of_plan)` for
`deductible_applied`, `eligibility`, the three terms, `coverage_ended`, `authorization`; the
servicer clause on the two obligation stances; values per 9D-F3 (a role-set or the map);
`determination` with no relation; `cleared` / `returned` per 9D-F6. The resolver is one function
parameterised by the role — it reads 7F's `in_effect` at the claim's `as_of` and, for the servicer
clause, the `servicer_of` claim's `derived_strength` (weakest link). **`derived_strength` gains
that resolver in `_KNOWING_RELATIONS` and nothing else changes.**

**Under P:** every stance kind gains `subject_party_id` and moves the thing to its object slot;
`knowing_relation = KNOWING_SUBJECT_PARTY` throughout; **every consumer's read of every stance
changes** — refused by §2.4 unless Rob rules the shape and re-opens the consumers' reads.

**Under either:** no `dated` key (9D-F7, pending); content opaque; the four determination names
7H's; `none` / `exempt` 7J's parses; no consumer changes beyond what Rob rules under F1; the fixture
per group over the cases indexed in §9D.4; the swap as §2.4 — the 7G, 7H, 7I, 7J fixtures re-run
with the catalogue lines changed and the map entries for ruled kinds retired; the last stand-ins
anywhere in the consumer fixtures gone.

### 9D.6 Ruling sought — 9D-F1 first; nothing else can be ruled before it

> **(1) Rule 9D-F1** — the position-holder of a stance is implied (H: the asserter, knowing by a
> role in effect at the date) or a participant (P) — and with it **9D-F2** (the acknowledgment's O:
> absent, content, or a participant) and **the servicer clause** (a second clause of the knowing
> relation at weakest link, or undetermined). **(2) Rule 9D-F8** — one pass or five, and the order.
> Then the groups run to their own candidates on the ruled shape, each with cases, and each build
> is authorised separately. **Nothing in (1) or (2) authorises code.**

**What 9D leaves exactly where it found it:** every consumer's gates and figures (RG-a, TS, TG-base,
7H's current, 7J's three term states) · the four determination names (7H's) · `none` / `exempt`
(7J's) · candidate generation · the disposition vocabulary · U6 · the reading-level resolver
(K7: required, not designed) · D′.11 · G.

---

### 9D.3a Rob's reframing of 9D-F1, and the H test — 2026-09-19

**The ruling question, as Rob framed it:** *is the holder of these stance kinds established
relationally by the asserter's role at the stance's `as_of`, or is the holder an explicit
participant of the stance?* The distinction is not storage shape but **where the ontology says the
position-holder exists.** H keeps the consumers' existing semantics — *stance → asserter → party in
role R at `as_of`* — and makes the role / date lookup part of the meaning of the stance, not an
implementation convenience; P would require every consumer to stop asking who asserted the position
and consume a stored party instead — a semantic change §2.4 cannot smuggle in as representation.
Rob's instruction: **test the candidate against whether the record can rule H without introducing a
new consumer interpretation**; F2 stays behind F1; F8 after both; no code, no registry additions, no
consumer edits.

**The test, run per consumer gate.** H coincides with the gate for 7H's three X-stances and 7J's
two accumulator stances (asserter in role at `as_of` — exactly H's relation); introduces nothing for
the ungated kinds (terms, `eligibility`, `determination` — F4 / F5 stay open); and coincides for
7G's `balance` (asserter entitled in effect) — **with one consequence stated plainly: the
servicer's balance statement (K2 covers "a payment *or balance*") can never enter E's series under
H, because `balance` has no slot that names E apart from the asserter.** And it **fails for the
acknowledgment**:

> 7G's gate reads **the party slot** (`e['party']` = `subject_party_id`) for the entitled-party test
> and **the utterance origin** for strength. H would read the origin for both. The slot is not
> legacy — it is load-bearing. §7G.7 committed: *the servicer's statement stays listed until the
> role catalogue rules `serves` and relational knowing for the acknowledgment kind, **and the same
> two tests read the ruled answers with no change to 7G.*** That promise is coherent only if the
> acknowledgment names its holder apart from its asserter — `acknowledged(E, p)` asserted by S:
> party E passes the entitled test, origin S is knowing at weakest link through `servicer_of`. **7G
> already treats the acknowledgment as P-shaped, by anticipation.**

So the record as built is **mixed**: the acknowledgment's holder is an explicit participant; every
other stance's holder is relational. H cannot be ruled uniformly without a 7G change (retire the
slot, and make 7G's entitled test read a holder *derived* from the servicer clause); P cannot be
ruled uniformly without changing every consumer; **the mixed catalogue is the only shape that
introduces no new consumer interpretation** — and it needs a reason that is semantic, not
historical. One is available: *P-ack for a payment is discharge* (the acknowledgment ruling) — the
acknowledgment is the one stance whose holder must be nameable by a party who is not the holder,
because its ruled channels include a non-holder's held statement counting as E's position; the
other stances' channels were ruled the same way (K2 says *or balance*), but no consumer was built
to read them so, and 7G's `balance` was ruled on the asserter. Whether that reason is accepted, or
the balance is brought into line with the acknowledgment (a party slot on `balance`; 7G's stated
series reads the holder — a 7G change), is Rob's.

**A second entanglement the test exposed — F2 and the servicer clause are one question.** The
servicer clause needs the O that S serves; the acknowledgment carries no O (§D′.4). 7G has O as its
argument and could evaluate the clause; a *kind-level* knowing relation (what `derived_strength`
reads with no consumer in sight) would have to reach O through p's established
`payment_in_respect_of_obligation` claims — reading the attachment to derive a strength. That does
not establish the attachment (D′'s refusal stands) but it composes three links (the ack, the
attachment, the servicing) into one strength, and D′.11's open question is composition across
kinds. So the servicer clause cannot be ruled as a kind-level relation before F2 is, and F2's
options are now three: **O absent** (the servicer clause lives only where O is known — in 7G,
which already evaluates roles against its O; the kind's knowing relation is `KNOWING_SUBJECT_PARTY`
alone, and the servicer channel's strength is 7G's to read — a consumer-side clause, which RG-a's
wording *the asserter's entitled-party role* already half-describes); **O as content** (K8 refuses);
**O as a participant** (two objects — a new registry shape, and the ack would then establish p → O
by naming it, which D′ refused). *Reading:* O absent, and the servicer clause is not a kind-level
relation at all but the consumer's weakest-link read where O is in hand — which is where the
acknowledgment ruling placed it (*the consumer declaring the P-ack strength it requires*).

### 9D.6a Ruling sought — restated after the test

> **(1) 9D-F1, in Rob's form:** the holder of a stance is established relationally by the
> asserter's role at `as_of` (H) for `balance`, the provider's and insurer's stances on X and P,
> and the terms; **and the acknowledgment's holder is an explicit participant** (its party slot
> stays, as 7G's tests already require) — the mixed catalogue, on the semantic reason above — **or**
> Rob names the uniform shape and the consumer change it costs. **(2) 9D-F2 with the servicer
> clause, as one question:** O absent from the acknowledgment, the acknowledgment's kind-level
> knowing relation `KNOWING_SUBJECT_PARTY`, and the servicer channel's weakest-link strength a
> consumer-side read where O is in hand (recommended) — or the alternatives named. **(3) 9D-F8**
> after (1) and (2). Nothing here authorises code, a registry entry or a consumer edit.

---

### 9D.7 Ruling — Rob, 2026-09-19: 9D-F1 the mixed holder shape; 9D-F2 with the servicer clause; no code

*The test changed F1 materially, and the record has enough to rule it without inventing a consumer
interpretation. The decisive evidence is not that the catalogue historically contains two
representations — it is that the two representations answer different semantic questions.*

**9D-F1 — RULED: the stance catalogue has two holder forms.** *Ordinary stance kinds establish
their position-holder relationally from the asserter's role at `as_of`* — H, as the consumers
already read them. *`acknowledged` establishes its position-holder as an explicit participant,
because its ruled discharge semantics require the represented holder to be distinguishable from
the party who asserted the acknowledgment* — the explicit party is not a redundant copy of the
asserter's role-derived identity; it is what lets the consumer distinguish *who asserted the
acknowledgment* from *whose position the acknowledgment represents*. **This mixed shape preserves
the existing consumer interpretations; uniformising it would require a separate consumer ruling**
— uniform H would change 7G's treatment of `acknowledged`, including the K2 payment / balance
behaviour, a consumer-semantic change that cannot be adopted merely for consistency. *A real
semantic distinction, not an exception created by implementation history.*

**9D-F2 + the servicer clause — RULED as one.** The crucial fence: **the acknowledgment does not
establish its obligation merely because the servicer is the party asserting it.** The
acknowledgment has no O; that the servicer serves some O elsewhere does not permit the kind-level
relation to compose *ack → party → role / servicer → obligation* into the acknowledgment's own
attachment or evidence strength — that would collide with D′'s non-derivability boundary. So:

- `acknowledged` has **`KNOWING_SUBJECT_PARTY`** at the kind level;
- its explicit subject party is **the represented holder**;
- **O remains absent** from the acknowledgment itself;
- the servicer channel is **evidence about the holder's position at the strength already ruled
  for that channel** (weakest link);
- **where a consumer has O independently in hand, that consumer may evaluate the servicer
  statement against that O**;
- the acknowledgment kind itself **does not derive or establish O through composition.**

*This preserves the distinction between what the acknowledgment says and what a consumer may know
when it already has the relevant obligation in hand.*

**9D-F8 — after these are frozen:** it can now ask how the remaining kinds are partitioned without
solving holder / knowing / attachment semantics simultaneously. **Nothing here authorises code.**
The semantic distinction is frozen first; any 7G consumer adjustment, if one is ever required, is
opened explicitly, never smuggled in through 9D. The dependency: *F1 mixed holder semantics →
F2 / servicer attachment boundary → F8 pass structure → the remaining 9D questions.*

### 9D.8 9D-F8 — candidate partition, on the frozen shape

F1 fixed *what kind of holder* each stance has, so the partition falls out of **which holder
relation each group needs** — and one new mechanism is shared by three of them: **the
role-at-date relation** (*knowing iff the asserter held role R on the claim's subject at the
claim's `as_of`*, read through 7F's `in_effect`; the subject is on the claim, so nothing is
composed — the O, X or P is in hand). It is 9B's `KNOWING_SUBJECT_PARTY`'s sibling: that one reads
a slot, this one reads a role and a date. It should be ruled **once**, on the first group, and
applied — not re-ruled — by the next two.

| sub-pass | kinds | holder relation | what it must rule beyond the shape | consumers whose fixtures swap |
|---|---|---|---|---|
| **9D-i — the obligation stances** | `acknowledged` (F1 / F2 as ruled: party slot, `KNOWING_SUBJECT_PARTY`, no O) · `balance` (H: `entitled_party_of` at `as_of`) · `returned` (Dg18 — E's position that p was returned unapplied; the same holder) | one explicit; two role-at-date (`entitled_party_of`) | **the role-at-date relation, once**; 9D-F7 (no `dated` key — the fixture asserts *undated never governs*); the servicer channel as the consumer's read (F2); `returned` ≠ non-acknowledgment | 7G, 7I |
| **9D-ii — the provider's and insurer's stances on X** | `billed` (`provider_of`) · `patient_responsibility` · `plan_paid` · `applied_to_deductible` · `denial` · `adjudication` (`insurer_of`) | role-at-date, applied | C7 (a denial is its own kind, never a determination or an adjudication amount); `exempt` is 7J's parse of content; nothing else new | 7H, 7J |
| **9D-iii — the insurer's stances and terms on P** | `deductible_applied` · `eligibility` · `coverage_ended` · `authorization` · `deductible` · `individual_deductible` · `plan_year` (`insurer_of_plan`) | role-at-date, applied | **9D-F4** (the terms: the insurer's position, while 7J reads any party's — ruled here as *what the kind says*, with 7J's read left to 7J); **9D-F6's three "coverage ended" claims** (F's boundary · F5's `eligibility` · Pl12's `coverage_ended`) — two kinds or three; `eligibility`'s subject is the person, not the holder (the holder is the role on the *object* plan) | 7J |
| **9D-iv — values** | `amount` · `occurred_on` (payment; expense) · `cleared` (the bank's) | **9D-F3**: a role-set (`paid_by` / `paid_to` for a payment; `provider_of` / `incurred_by` for an expense) plus the artefact origin through a reading — or the foundation map as today | the second new relation shape, if a role-set is ruled; K6 (a cleared line is never an acknowledgment); Kn7 (minting ≠ knowing) | 7G, 7H, 7I, 7J |
| **9D-v — the determination** | `determination` | none — **9D-F5**: undetermined by design (recommended) | who may determine is *any party* (7H); the four names stay 7H's | 7H |
| *not 9D* | `contribution` (Pl8 — a claim about the employer party, not a stance on a thing) | — | named here so it is not mistaken for a stance; ruled when a consumer needs it | — |

**Order: i → ii → iii → iv → v.** i first because it carries the two shared rulings (the relation;
F7) and the ruled F1 / F2 shape; ii and iii apply the relation and settle their own questions (C7;
F4; F6); iv is the only other new relation shape and stands alone; v is smallest and least coupled.
Each sub-pass: its own cases (the index in §9D.4 assigns them), its own candidate, its own ruling,
its own build authorisation, its own swap, mutations and gate — 9A–9C's cadence. **Alternative:**
one pass with five sections — rejected by me only because five build authorisations keep each
group's consumer swap inspectable on its own (9B's and 9C's gates each found something the
touched-fixture runs had not).

**Ruling sought — 9D-F8:** the five sub-passes in that order, with the role-at-date relation ruled
once in 9D-i; or a different cut. Nothing here authorises code; 9D-i opens on Rob's word.

---

### 9D.9 Ruling — Rob, 2026-09-19: 9D-F8 ACCEPTED as proposed; 9D-i the next semantic slice; no code

*Not merely a topical partition: each group has a distinct semantic dependency, and the order
prevents a later group from silently changing an earlier group's holder rule.*

**9D is five separately inspectable swaps, in this order:**

1. **9D-i — obligation stances:** `acknowledged`, `balance`, `returned`. Uses the ruled
   role-at-date holder relation. Carries F7 (no `dated` registry key). Carries the ruled
   servicer-channel reading from F2. Consumers: 7G, 7I.
2. **9D-ii — provider / insurer stances on X:** `billed`, `patient_responsibility`, `plan_paid`,
   `applied_to_deductible`, `denial`, `adjudication`. Applies the same role-at-date relation.
   Settles the relevant C7 question. Consumers: 7H, 7J.
3. **9D-iii — insurer stances and terms on P:** `deductible_applied`, `eligibility`,
   `coverage_ended`, `authorization`, the three terms. Applies the already-ruled relation rather
   than introducing another holder mechanism. Settles F4 and F6. Consumer: 7J.
4. **9D-iv — values:** `amount`, `occurred_on`, `cleared`. Introduces the remaining new relation
   shape — the role-set F3 requires. Consumers: all four.
5. **9D-v — determination:** F5 only; the determination remains undetermined. Consumer: 7H.

`contribution` remains explicitly outside 9D — it is not a stance.

*The five-way split is preferable to one large 9D because each swap gets its own cases → ruling →
authorisation → consumer substitution → mutation tests → full gate; 9B and 9C are direct evidence
that touched fixtures do not exhaustively expose later registry-shape assumptions.*

**One further constraint follows from the partition: the role-at-date relation is ruled once, in
9D-i, and subsequently applied — not semantically re-ruled in ii or iii.** Those groups may test
their application and their consumer consequences; they cannot alter what the relation means.

**9D-i is the next semantic slice. No code until its cases and ruling are complete.** It opens on
Rob's word.

---

## Pass 9D-i — The obligation stances: `acknowledged` · `balance` · `returned`

*Opened by Rob 2026-09-19 with its scope fixed: the three kinds; consumers 7G and 7I; the holder
relation the already-ruled role-at-date relation from F1 / F8 — no new holder relation, no re-ruling
of F1 / F2, no `dated` registry key, the servicer channel the already-ruled consumer reading; no code
until cases → candidate → ruling → explicit build authorisation. **The slice's question, Rob's:** do
the three obligation stances actually satisfy the same role-at-date holder relation in every
consumer case, including the exceptional explicit-holder shape of `acknowledged`, without requiring
any additional semantic distinction? If the cases expose a difference it belongs here; if not, the
relation is frozen once and applied by 9D-ii / 9D-iii.*

### 9D-i.1 What is fixed

§9D.7: `acknowledged` — explicit holder (`subject_party_id` = E), `KNOWING_SUBJECT_PARTY` at the
kind level, O absent, the servicer channel evidence at its ruled strength evaluated only by a
consumer with O in hand. `balance` — H: the holder is the asserter, knowing by `entitled_party_of`
in effect on the subject obligation at the claim's `as_of`. The acknowledgment ruling (2026-09-12):
P-ack is E's stated position about a payment or balance, dated; one knowing party; K1 E's held
statement · K2 the servicer's held statement bounded by *S serves E* · K3 S3 · K4 the portal · K5
the user's report is not knowing · K6 the bank's clearance is not acknowledgment · K7 conflicts by
date then channel · K8 ack ≠ balance. 7G RG-a / TS-base / TG-base as ruled and built; Dg2 / Dg2′ /
Dg4 / Dg5 / Dg18 / Dg21 / Dg22; 7I inherits 7G at two dates. §9D.9: the role-at-date relation is
ruled once here.

### 9D-i.2 What the consumers read — three shapes under two names

| kind, as used | subject | party | object | `as_of` | content | who reads it, and how |
|---|---|---|---|---|---|---|
| `acknowledged` (7G, 7I) | — | **`subject_party_id` = E** (the holder) | the payment | yes | — | 7G: `e['party']` entitled in effect at `as_of` (7F); strength from the **utterance origin** via `derived_strength` with the foundation map `{'institution'}`; qualifies iff established ∧ dated ≤ d ∧ in effect ∧ knowing |
| `balance` (7G, 7I) | **the obligation** | none | — | yes | money | 7G: the **utterance origin** entitled in effect at `as_of` → the governing series (TG-base); strength not read |
| `balance` (7E) | **the party** (Harbor) | (the subject) | **candidates** — no obligation | yes | money | 7E: the claim's L0 class via `derived_strength` (a **reading** of Harbor's held statement → foundation `{'institution'}` → **knowing**) chained through `artefact_concerns` / `proposition_concerns` to O1 — the tie is the separate claim those cases test (Ab7) |
| `returned` | — | — | — | — | — | nobody: Dg18 — 7G reads no such kind |

**What this shows.** (a) The acknowledgment's two axes are read from two places — the *holder* from
the slot, the *strength* from the origin — exactly the split F1 ruled. (b) `balance` in 7G is H;
`balance` in 7E is a **reading-line figure whose subject is the party who states it** and whose
thing is not yet a participant — a different proposition wearing the same name (9B's borrowed-name
class; the shape is deliberate there, not stale). (c) Every strength today comes from the
foundation map: *institution ⇒ knowing* — which is how a **reading** of E's statement is knowing
(K1, Ms1) and also how an acknowledgment recorded with `party = Harbor` but *asserted by a servicer*
would today read knowing and **discharge** (the stand-in over-grants; no fixture exercises it —
Ob12 below).

### 9D-i.3 The role-at-date relation — stated once, as a candidate

> **`KNOWING_ENTITLED_PARTY_AT_AS_OF` — the asserting party held `entitled_party_of` on the claim's
> subject obligation, in effect at the claim's `as_of` (7F `in_effect`, G named).** `in_effect` →
> knowing; `not_in_effect` → not_knowing; `undetermined` or `contested` → undetermined; no `as_of` →
> undetermined (an undated position cannot be placed against a role — F7's meaning without a key).
> Nothing composed: the subject is on the claim. The servicer is **not** a clause of this relation
> (§9D.7): a servicer's balance statement is not_knowing at the kind level; a consumer with O in hand
> may read it against O — 7G does not today, and that is 7G's to open (K2's *or balance* half).

**On each evidence path** — the part 9D-i must state, because it is where the shipped strength and
the ruled relation differ (9D-i-F1): *utterance-sourced* — the origin party is the asserter; the
relation as above. *Reading-sourced* — the relational branch as built returns **undetermined for
every reading** (ruled for roles and relations: *the letterhead says Lakeview Health* is nobody's knowledge —
Ro13, CORRESPONDENCE §3). For a P-ack stance the reading **is the ruled primary channel** (K1: E's
held statement; ARTEFACT_READING_SLICE C1: *the reading conveys the artefact's origin's knowledge,
never the reader's*). So for stance kinds the relation must be evaluated on **the artefact's
established origin** as the asserting party, weakest-linked with the origin claim's strength (C3) —
the shipped foundation path's structure with the relation in place of the type test; the **state**
stays *candidate* (`_claim_states` is by evidence type; Dg2′ stands: a reading alone never
discharges). **This is one specification of the relation, not a second relation** — but it needs a
registry expression, and the one that exists is `reading_establishes`: today it gates the
strength-through-origin path (a kind with `False` short-circuits to undetermined) and does not
touch state. *Candidate:* stance kinds carry `reading_establishes: True`, meaning exactly *a reading
of this kind carries the artefact origin's knowledge for strength; it establishes no state* — and
the flag's comment is pinned to say so. Roles and relations keep `False`. **Rob rules** whether the
flag carries that meaning or a stance needs its own expression.

**Naming, for ii / iii to apply without re-ruling:** one resolver, one name per role
(`KNOWING_ENTITLED_PARTY_AT_AS_OF` here; `…PROVIDER…`, `…INSURER…`, `…PLAN_INSURER…` later) keeps
`knowing_relation` a name, as the registry's shape is; a parameterised value would be a new value
shape. The resolver is written once and takes the role from a table keyed by the name.

### 9D-i.4 Findings — put to Rob

**9D-i-F1 — the reading path (above).** The relation's behaviour on a reading-sourced stance is not
fixed by F1 / F8 and is where the swap would otherwise change a reported strength: 7E's Ms1 / Ms2
assert *knowing* for Harbor's held-statement line, 7G's Dg2 text describes E's held statement as the
knowing channel. Without the reading path stated, the ruled `balance` would report *undetermined*
for exactly the channel the acknowledgment ruling made primary. **Applies to all three kinds** —
including `acknowledged` under `KNOWING_SUBJECT_PARTY`, whose resolver 9B ruled with the reading →
undetermined behaviour for *roles* (Ro13). So the reading-path behaviour must be a property of the
**kind** (the flag), not of the resolver — which keeps 9B's relation unchanged and lets the
acknowledgment reuse it. *This is the one additional specification the cases expose, and it is not a
new holder distinction — it is which party the holder test is applied to on each path.*

**9D-i-F2 — `balance` in 7E is a different proposition.** 7E's line has the party as subject and no
obligation; the ruled `balance` has the obligation as subject. The registry will refuse 7E's shape
under the ruled name, and *correcting the corpus to the ruled shape* would put O1 on the claim and
dissolve the aboutness chain Ms1 / Ms2 exist to measure. So the truthful move is the **reverse** of
9C's: 7E's stand-in keeps its shape and **loses the borrowed name** (a fixture-registered
`statement_line_figure` or similar, foundation-mapped as today) — 7E consumes strength classes and
aboutness, not the balance kind's semantics, and its use of the name predates the catalogue. A
reading-level proposition whose thing is a candidate is the candidate-generation fence's, not 9D's.
**A swap beyond names, reported before the build; Rob rules the rename.**

**9D-i-F3 — Dg2 as ruled vs 7G as built.** §7G.3's Dg2 reads *Harbor's held statement, read; Rob
asserts that is Harbor acknowledging p; established (Rob's utterance) with strength via the
reading / origin → discharged*. Built 7G tests state and strength **per evidentiary relationship**
(`qualifies` on one relationship), and 7E's doctrine is per-relationship chains (*multiplicity is
not strength*). A claim with Rob's utterance (established, not_knowing) and the reading (candidate,
knowing) has no relationship that is both — **K1-with-acceptance does not discharge in built 7G**;
the fixture's Dg2 uses Harbor's own utterance instead. Not 9D-i's to solve — a 7G question (does
discharge read state and strength across a claim's relationships, or per relationship?) to be
opened explicitly. Recorded because 9D-i's fixture must not paper over it: Ob3 asserts what built 7G
does today.

**9D-i-F4 — `returned` takes the acknowledgment's shape.** Dg18: *E returns p unapplied* — E's
position about p, the acknowledgment's negative twin, with the same channels (a servicer may state
it). F1's reason for the explicit holder applies verbatim; so `returned`: `subject_party_id` = E,
object the payment, `KNOWING_SUBJECT_PARTY`, O absent, `reading_establishes: True` per F1. No
consumer reads it; 7G's Dg18 (station unchanged) is the swap's only test. *A return is not a
non-acknowledgment* (a later acknowledgment stands on its own series; TS per kind).

**9D-i-F5 — the answer to the slice's question.** **No — and the difference is exactly F1's, not a
new one:** `acknowledged` and `returned` carry the explicit holder and `KNOWING_SUBJECT_PARTY`;
`balance` carries the role-at-date relation. The one specification 9D-i adds (F1: the reading
path, by the kind's flag) applies to all three identically. 7G applies the role-at-date **test** to
the acknowledgment too — on the holder, against 7G's own O — and that is the consumer's gate (RG-a),
not the kind's relation; the two coincide for `balance` and are deliberately split for
`acknowledged`. **The relation can be frozen once.**

### 9D-i.5 Cases

| # | Case | Ruled outcome (kind level → 7G) | Today (foundation) |
|---|---|---|---|
| **Ob1 (K1 / Dg2)** | Harbor's own utterance: *received 3/5* (party Harbor, origin Harbor); Harbor entitled in effect | `KNOWING_SUBJECT_PARTY` → knowing; 7G: in effect ∧ knowing → **discharged** | the same |
| **Ob2 (K1 held / Dg2′)** | the parser's reading of Harbor's held statement | state candidate; strength **knowing** (F1: origin Harbor = party) → 7G: listed candidate, **not discharged** | state candidate; strength knowing |
| **Ob3 (K1 accepted — F3)** | the reading + Rob's utterance *that's Harbor acknowledging p* on one claim | two relationships: (candidate, knowing) and (established, not_knowing) → built 7G: **not discharged**; §7G.3 text says discharged — **7G's question** | the same |
| **Ob4 (K2 / Dg4)** | BillCo's utterance acknowledges p, **party = Harbor**, BillCo `servicer_of` O by Rob | origin BillCo ≠ Harbor → **not_knowing**; 7G: in effect (Harbor) ∧ not knowing → listed *acknowledged, not first-hand*, **not discharged** — the servicer channel is 7G's to evaluate with O in hand, and 7G does not today | **origin BillCo is an institution → knowing → DISCHARGED — the stand-in over-grants** |
| **Ob5 (K3 / Dg5)** | S3's utterance, party = S3 | knowing for its own (Kn12); 7G: S3 not entitled → never discharged | the same |
| **Ob6 (K5 / Dg22)** | Rob relays: party Harbor, origin Rob | not_knowing; 7G: listed, not discharged | the same |
| **Ob7 (Dg21)** | Harbor's role contested at `as_of` | `balance`: undetermined; `acknowledged`: knowing (the holder test is 7G's: contested → not discharged) | the same |
| **Ob8 (K2 balance)** | BillCo's utterance: *balance $1,900 as of 3/31* on O | role-at-date: BillCo not entitled → **not_knowing**; 7G: not in E's series (K2's balance half unreachable — recorded) | not in E's series (knowing by type, ignored by role) |
| **Ob9 (K1 balance held / Ms1)** | Harbor's held statement line *balance $1,925*, read | state candidate; strength **knowing** via the origin (F1); 7G: candidate, never governing | knowing |
| **Ob10 (K4)** | the portal figure, observed, dated; a screenshot later | a reading of a held capture → as Ob9; an observation with no artefact → nothing in the record (not 9D's) | — |
| **Ob11 (K7)** | Harbor 3/31 *$1,900*; Harbor 4/30 *$1,610* | two knowing positions; G by date (TS) — 7G's | the same |
| **Ob12 — the 2 × 2** | party ∈ {Harbor, S} × origin ∈ {Harbor, S} | (Harbor, Harbor) knowing; (Harbor, S) **not_knowing** [Ob4]; (S, S) knowing, not entitled; (S, Harbor) not_knowing (Harbor asserting S's position — testimony) | (Harbor, S) knowing; (S, Harbor) knowing — the type test cannot tell the two apart |
| **Ob13 (F7)** | an undated balance; an undated acknowledgment | undetermined; 7G disqualifies both | the same |
| **Ob14 (Dg18)** | Harbor: *returned p unapplied* (`returned`, party Harbor) | knowing; 7G reads it not at all — station unchanged; a later acknowledgment stands on its own | — |
| **Ob15 (F2)** | 7E's `balance` line with the party as subject | **refused by the registry** under the ruled name; the line keeps its shape under its own stand-in name | accepted |

### 9D-i.6 Candidate — three registry entries; one relation; one flag meaning pinned

```text
ACKNOWLEDGED = 'acknowledged'   subject (subject_party_id,)       object (object_payment_id,)
                                 symmetric False · reading_establishes True · relational_knowing True
                                 knowing_relation KNOWING_SUBJECT_PARTY · no role · no boundary
RETURNED     = 'returned'        the same slots and flags (9D-i-F4)
BALANCE      = 'balance'         subject (subject_obligation_id,)  object ()
                                 symmetric False · reading_establishes True · relational_knowing True
                                 knowing_relation KNOWING_ENTITLED_PARTY_AT_AS_OF
KNOWING_ENTITLED_PARTY_AT_AS_OF — the resolver above, in _KNOWING_RELATIONS; the reading path per
                                 reading_establishes for stance kinds (the relational branch routes a
                                 reading through the artefact's established origin when the kind's
                                 flag is True; state untouched)
```

No consumer changes. The swap: 7G's and 7I's catalogue lines; their `KNOWING` map entries for the
three kinds retired; the acknowledgment's shape unchanged (F1); **7E's line renamed** per F2 (Rob's
call); s113 / s114 / s111 by name. Mutations for `s120`: the servicer's acknowledgment discharging
(Ob4 reversed) · a reading acknowledging (state established from a reading) · the origin's type
conferring knowing (the foundation restored) · a balance by a non-entitled party governing · the
relation composing through the attachment (O reached from p) · an undated stance knowing ·
`returned` read as a non-acknowledgment · a second relation shape for the acknowledgment · the
flag made to establish state.

### 9D-i.7 Ruling sought

> **(1) 9D-i-F5:** the three kinds are as F1 assigned them — `acknowledged` and `returned` explicit
> holder + `KNOWING_SUBJECT_PARTY`; `balance` the role-at-date relation — no additional holder
> distinction; **the relation frozen as §9D-i.3 states it. (2) 9D-i-F1:** the reading path for
> stance kinds — evaluated on the artefact's established origin, weakest-linked, state untouched —
> expressed by `reading_establishes: True` with its meaning pinned (or by an expression Rob names).
> **(3) 9D-i-F2:** 7E's line keeps its shape and loses the borrowed name. **(4) 9D-i-F4:** `returned`
> takes the acknowledgment's shape. **9D-i-F3 is recorded for 7G and not ruled here.** Nothing here
> authorises code.

---

### 9D-i.8 Ruling — Rob, 2026-09-19: F5, F1, F2 (with one precision), F4 RULED; no code by this ruling

*The cases expose a clean ruling boundary.*

**F5 — the relation.** The three kinds do not share one kind-level holder representation:
`acknowledged` → explicit holder via `KNOWING_SUBJECT_PARTY`; `returned` → explicit holder via
`KNOWING_SUBJECT_PARTY`; `balance` → the role-at-date relation. *That does not contradict F8: the
role-at-date relation is one ruled relation; it is simply not the holder mechanism of every kind in
the group.* 7G's acknowledgment check against the obligation's holder is **a consumer gate, not a
second kind-level knowing relation** — it does not reopen F1.

**F1 — the reading path, frozen exactly at the boundary identified.** `reading_establishes: True`
means **the kind's relational strength may be evaluated through the artefact's established origin,
weakest-linked; it does not establish payment state, discharge, or any other state.**

```text
reading → established origin → kind's relation → strength        YES
reading → discharge                                               NEVER
```

Dg2′ preserved; `reading_establishes` a property of the stance kind, not a special branch invented
inside the resolver. *This is also why the existing relational branch's `undetermined` for
reading-sourced claims cannot simply be reused unchanged: these kinds explicitly rule that the
reading's established origin is a valid evidentiary path.*

**F2 — 7E's party-subject shape: keep the fixture shape.** The case intentionally tests a
proposition whose subject is the party, not the obligation; changing its subject to O merely to
resemble 7G would destroy what the fixture demonstrates. But the borrowed `balance` name must not
imply the fixture exercises 9D-i's ruled obligation-balance kind — **a corpus / name correction, not
an ontology correction:** preserve the party-subject proposition and its aboutness chain; remove
the borrowed-name implication. **The precision:** the replacement name is whatever the fixture's
actual proposition warrants; **no new semantic kind is invented to accommodate the test.**

**F4 — `returned`** follows the explicit-holder shape established by F1: explicit
`KNOWING_SUBJECT_PARTY`; no role-at-date relation substituted for it; reading behaviour the same
already-ruled machinery; **no new discharge semantics implied by the reading path.**

**Ob12's 2 × 2** belongs in the implementation cases — exactly the distinction the new relation is
supposed to prevent; it creates no further ruling.

**Frozen by this ruling:** (1) the mixed holder representation; (2) `reading_establishes: True` as
strength-through-established-origin only; (3) the intentional 7E party-subject fixture preserved
with the borrowed-name implication removed; (4) `returned` on the explicit-holder shape.
**9D-i-F3 stays recorded for 7G.** **No code yet beyond the explicit build authorisation that
follows these rulings.** The build, when authorised, is narrow: registry representation; the
consumer substitutions these frozen meanings require; mutation coverage for the reading / holder
distinctions; the full gate.

---

#### Built — 2026-09-19 (9D-i)

`core/database.py`: `ACKNOWLEDGED`, `BALANCE`, `RETURNED` — three registry entries exactly as §9D-i.8
froze them. **The mixed holder shape:** the acknowledgment and the return with `subject_party_id` = E
and the payment as object, `knowing_relation` **`KNOWING_SUBJECT_PARTY`** (9B's, unchanged); the
balance with the obligation as subject and **no object** (`'object': ()` — the registry's required
absence, as `utterance_retraction`), `knowing_relation` **`KNOWING_ENTITLED_PARTY_AT_AS_OF`**. All
three `reading_establishes: True`; none a role, none bounded; no `dated` key. **The role-at-date
relation, written once:** `_role_at_as_of(session, prop, claimant, role_kind)` — the claimant's
`in_effect` answer for the role on the claim's established subject at the claim's `as_of`: in effect →
knowing; not in effect, or no stance at all → not_knowing; undetermined / contested → undetermined;
no `as_of` or no subject → undetermined; nothing composed. It is three-valued and classifies the
claimant, so it is not a designated-participant resolver (those name one party and compare); it is
the fourth entry in `_KNOWING_RELATIONS`, dispatched by `_relational_strength` through
**`_ROLE_AT_AS_OF`, the table keyed by the relation's name** — 9D-ii / 9D-iii add their names and
roles there and change nothing else. **The reading path (F1):** the relational branch of
`derived_strength` now routes a reading-sourced claim of a kind with `reading_establishes: True`
through the artefact's **established origin** as the asserting party, weakest-linked with the origin
claim (C1–C3) — `_reading_origin`, factored out of the foundation path it already served, derives
nothing new; a kind with `False` still returns undetermined; **`_claim_states` untouched — a reading
is a candidate in state regardless.** The one comment block states P-ack, the two holder forms and
their reason, O's absence and the composition fence, the servicer channel as the consumer's read,
the flag's exact meaning (*reading → origin → relation → strength; never reading → discharge*), and
`returned` as the acknowledgment's twin. **Nothing else** — `reach` and every consumer untouched; no
discharge, holder or servicer helper.

**The oracle:** `tests/test_obligation_stances_fixture.py` — 22 checks over Ob1–Ob15 and the
registry, run with a foundation map that carries **no entry** for the three kinds: Ob1 (E's own
acknowledgment knowing, discharged); **Ob2** (the parser's reading of E's held statement — candidate
in state, **knowing** in strength through the origin; listed, not discharged); **Ob3, recorded not
solved** (Rob's acceptance added to the same claim — two relationships, (candidate, knowing) and
(established, not_knowing); built 7G qualifies per relationship → not discharged; 9D-i-F3 stays
7G's); **Ob4** (the servicer's acknowledgment naming E as holder — origin ≠ holder → not_knowing;
holder in effect, strength not knowing → listed, not discharged; the kind composes nothing through
BillCo's `servicer_of` or p's attachment); Ob5 (S3 knowing for its own, never entitled); Ob6 (Rob
relays → not_knowing); **Ob12 — the 2 × 2** ((E, E) knowing · (E, S) not_knowing · (S, S) knowing ·
(S, E) not_knowing — the foundation's type test called all four knowing); the balance on every
path — Ob1 (Harbor in role → knowing, governing), Ob8 (the servicer's balance → not_knowing, not in
E's series — K2's balance half recorded as a consumer question), Ob9 (E's held statement line →
candidate, knowing), Ob9′ (O5: Rob's spreadsheet with the same figure → not_knowing; relaying does not
launder), Ob11 (two positions by date, G per series 7G's), **Ob7** (the role contested at `as_of` →
undetermined, nothing manufactured), Ob13 (undated → undetermined; disqualified by 7G), a party with
no stance at all → not_knowing; Ob14 (`returned` — E's shape, knowing, station unchanged, nothing
written; its reading the same machinery); Ob15 (the party-subject line refused under `balance`,
accepted under its own stand-in name); O's absence and the balance's refusals by the registry.

**The substitution — the decisive test, and what it exposed:** the 7G, 7I and 7H fixtures changed by
their catalogue lines' meaning only (the names were already the ruled names), the two helpers naming
the ruled constants, and **their foundation-map entries for `acknowledged` / `balance` retired** —
**40/40 · 30/30 · 32/32, identical counts, no consumer changed**; 7J's helpers and map likewise
(31/31). Beyond names, three things reported rather than absorbed: **(1) `balance` as a
party-subject line (9D-i-F2, ruled)** — not one fixture but **nine** used the name for the
reading-line figure whose subject is the party and whose thing is a candidate (7A, 7C, 7D, 7E, Ab7,
proposition-correspondence, artefact-concerns, independence, obligation-identity; the shape is the
point of their cases); the ruled kind's guard refuses it (both participants established); per the
ruling the shape is kept and the borrowed name removed — one stand-in name, `statement_figure`,
across all nine, with their map entries following, **no new kind**; 7A's kind-dispute case now reads
`statement_figure` vs `payment_due`, the same dispute. Their obligation-subject `balance` claims (the
household's testimony about O) match the ruled shape and keep the name. **(2) `returned` had two
shapes:** 7G's Dg18 line was E's return with `subject_payment_id` and no holder — corrected to the
ruled shape (holder Harbor, the payment); the payment-counteracts fixture's *RETURNED ITEM 3/5* is
**the bank's** returned-item line — a bank stance of 9D-iv's class under E's name — renamed
`bank_returned_item`, its map entry following. **(3) three exact-set pins,** the class 9C found:
obligation-replaces (the obligation-subject kinds now include `balance`), the relational-knowing
fixture and the role-catalogue fixture (*three names, three resolvers* → four; *the third named
relation* kept, the count updated), `s97`'s opening check likewise. The three consumer fixtures'
*no acknowledgment / balance kind registered* narrowed to the value kinds still 9D-iv's.

**Smoke `s120_obligation_stances.py`:** the fixture passes; ten mutations, each a collapse of the
reading / holder distinction — the servicer's acknowledgment discharging (`KNOWING_SUBJECT_PARTY`
granting the servicer E's position) · the origin's type conferring knowing (the foundation restored)
· a reading establishing state (Dg2′ reversed) · a reading discharging (7G accepting a knowing
candidate) · the flag establishing state · a non-entitled balance knowing (the role ignored) · the
acknowledgment composing through the attachment (O reached from p; the servicer's role read) · an
undated stance knowing · a second relation on the acknowledgment (F1 uniformised) · `returned` read
as a non-acknowledgment — **all ten caught on the first run**, baseline re-established after every
undo.

**Left where it belongs:** 9D-i-F3 (does discharge read state and strength across a claim's
relationships, or per relationship — §7G.3's Dg2 text vs built 7G) — 7G's, to be opened
explicitly · K2's balance half (a consumer with O in hand reading the servicer's balance) · the
portal observed without an artefact · 9D-ii's and 9D-iii's roles (their names and roles go in
`_ROLE_AT_AS_OF`; the relation is not re-ruled) · values, `cleared`, the bank's stances (9D-iv) · the
determination (9D-v). No schema, no migration. Gate 1396 → 1419, 0 failed.

#### Accepted — Rob, 2026-09-19 (9D-i)

Accepted on the gate's evidence (1419 / 0, s120 23/23) and the build's fidelity to §9D-i.8: the
mixed holder representation preserved; `reading_establishes: True` as strength-through-established-
origin only, never state or discharge; the role-at-date relation added beside the three existing
resolvers rather than folded into their contract, and applied to the balance only; the 7E
party-subject line kept and renamed as corpus correction (extended to the nine fixtures sharing that
proposition, no new kind); `returned` on the explicit-holder shape and not a 7G consumer; the
pre-9D-i registry pins retired as legitimate catalogue transitions; 9D-i-F3 left recorded for 7G;
no consumer, `reach` or `_claim_states` change. **9D-ii remains unopened until Rob opens it; it
applies the relation and does not re-rule it (§9D.9).**

---

## Pass 9D-ii — The provider's and insurer's stances on X

*Opened by Rob 2026-09-19 after 9D-i's acceptance (`2511ef7`). Scope per §9D.9: `billed`,
`patient_responsibility`, `plan_paid`, `applied_to_deductible`, `denial`, `adjudication`; the
role-at-date relation **applied, not re-ruled** — two names and two roles added to `_ROLE_AT_AS_OF`
and nothing else; C7 settled; consumers 7H and 7J. No code until cases → candidate → ruling → explicit
build authorisation. The slice's question is narrower than 9D-i's: **which role on the claim's
subject (X) is each stance's holder, and does every consumer gate coincide with that** — with one
case (CC1) where the consumer selects by a role on a *different* thing.*

### 9D-ii.1 What is fixed

§9D-i.8 / §9D.9: H for every ordinary stance — the holder is the asserter, knowing iff it held role R
on the claim's subject in effect at `as_of`; `reading_establishes: True` = strength through the
artefact's established origin, never state; no `dated` key; the relation ruled once. **4b
(INSURER_CLAIM_IDENTITY §7):** adjudication is *an institutional proposition, a dated stance* about X;
patient responsibility a proposition about X; the insurer's claim has no Groundwork identity;
**recurrence of the P-ack shape establishes no common kind, resolver or family** — each kind its
own entry; *insurer of X needs its own ruling before it can become an epistemic relation* — 9B ruled
it; 9D-ii makes it the relation. **7H §7H.2 / §7H.7:** `billed` is *P-ack for X's charge, asserter in
effect as provider of X at its date*; `patient_responsibility` and `plan_paid` *the insurer's dated
claims on X, asserter in effect as insurer of X*; a claim by a party not in the role is reported,
never governing (F3 / K5: Rob's *the EOB said $412*); G per party's series; conflict at one date →
none (Rc10); **Rc6 / C7: a denial is a stance of another kind — 7H reads no denial; forced through
`unpaid` or `pending_claim` it would acquire that channel's meaning**. **7J §7J.7:**
`applied_to_deductible` — the plan's insurer's own adjudication stance on X; **CC1: under concurrency
another plan's insurer also adjudicates X, and its stance is that plan's** — each plan derives from
its insurer's stances only; content a money amount or `none` (*exempt* — C6: the rule exists and this
falls outside it, an answer, not zero and not unknown). Every consumer read is a stance on
`subject_expense_id`, asserter the utterance origin, content parsed by the consumer.

### 9D-ii.2 What the consumers read — and the one gate that is not on X

| kind | subject | `as_of` | content | 7H's gate | 7J's gate |
|---|---|---|---|---|---|
| `billed` | X | yes | money | asserter in effect as **`provider_of` X** | — |
| `patient_responsibility` · `plan_paid` | X | yes | money | asserter in effect as **`insurer_of` X** | — |
| `applied_to_deductible` | X | yes | money or `none` | — | asserter in effect as **`insurer_of_plan` P** — *the plan being computed*, not X |
| `denial` | X | yes | text | **not read** (Rc6); named in the note | — |
| `adjudication` | X | yes | text (*reversed*, *denied — not covered*) | not read | not read (the 9C fixture used the name; 9D-i's opening listed it) |

The kind-level relation reads a role **on the claim's own subject** — that is what makes it
composition-free (9D-i). For five of the six that is exactly the consumer's gate. For
`applied_to_deductible` the consumer's gate is on P: 7J asks *is the asserter the insurer of the plan
I am computing*, which under CC1 is how two insurers' stances on one X are kept to their own plans.
The kind cannot ask that — it has no P. So at the kind level `applied_to_deductible`'s holder is
**`insurer_of` X** (Lakeview Health and Cigna are both knowing for their own stance on X), and the per-plan
selection is **7J's consumer gate** — the same split 9D-i ruled for the acknowledgment (the kind's
relation vs 7G's holder test against its own O). No new relation; stated so it is not mistaken for
one.

### 9D-ii.3 Findings — put to Rob

**9D-ii-F1 — `adjudication` and `denial`: two kinds, one, or is one not 9D-ii's?** 4b calls
adjudication *the insurer's dated stance about X*; C7 / Rc6 name the denial as *a stance of another
kind* than the determination; the 9C fixture used `adjudication` with contents *reversed* and
*denied — not covered*, and 7H's fixture used `denial` with content *not covered*. Options: (a) **two
kinds** — `adjudication` the insurer's stance on the claim's outcome (content opaque: *paid*,
*reversed*, *denied*…) and `denial` its own kind, so that a consumer can refuse to read a denial as a
determination *by name* (C7's point is that a denial must not be forced into a channel; a kind of
its own is the fence); (b) **one kind** `adjudication`, a denial being its content — then C7's fence
is content-reading, which §2.3 keeps out of the catalogue and which 7H would have to parse; (c)
`denial` only, `adjudication` dropped as a name (the 9C fixture's two uses become `denial` and
`plan_paid $0` / a reversal is an `applied_to_deductible` or `plan_paid` restatement). *Reading:* (a)
— it is what Rc6 already assumes (*a denial kind*), it keeps content opaque, and `adjudication`
gives the insurer's *reversed* (E3) a home that is neither an amount nor a denial. Both `insurer_of`.
Rob's.

**9D-ii-F2 — foreseen swap findings, two classes, measured before the build.** (i) *The borrowed
line shape again* (F2's class): `patient_responsibility` as an EOB **line** — subject the insurer
party, the thing a candidate — in the expense-identity, plan-identity and obligation-in-respect-of
fixtures (`line(eob, r_eob, 'patient_responsibility', '$412 | claim #A77', aetna)`); refused under
the ruled kind; the shape kept, the borrowed name removed — a stand-in name for the EOB line figure
(7E already has `eob_amount` for exactly this proposition; reuse it — no new kind). (ii) *The
foundation's assumption made explicit* — new in this slice: 7B's In12 asserts *Lakeview Health (via the EOB)
is knowing for PR $412* and expense-identity asserts *Riverbend Hospital is knowing for `billed`* — both today
by **type** (`{'institution'}`), with **no `insurer_of` / `provider_of` claim anywhere in those
corpora**. Under the ruled relation Lakeview Health is knowing iff it held `insurer_of` X at the claim's
`as_of`; with no role in the record the answer is *not_knowing*, and In12's meaning (*an insurer's
figure is the insurer's to know*) can only be restored by putting the role in the corpus — the fact
the type test had assumed. That is a corpus correction of a new shape: not a rename, an **addition**
of the role claim the case always meant. Two fixtures (7B, expense-identity), measured; the build
reports the count. *Put to Rob as a class before the build, as 9C's pins were after.*

**9D-ii-F3 — none for the relation.** Applying `_ROLE_AT_AS_OF[KNOWING_PROVIDER_AT_AS_OF] =
PROVIDER_OF` and `[KNOWING_INSURER_AT_AS_OF] = INSURER_OF` changes nothing about what the relation
means; every 7H gate coincides with it (5 of 6 kinds); 7J's differs by design (§9D-ii.2) and is the
consumer's. The reading path is 9D-i's: the EOB read → candidate in state, knowing in strength when
its established origin is the insurer in role; Riverbend Hospital's bill read → the provider's `billed`; **the
EOB's own *billed* column → the insurer's relay of the provider's charge → `billed` by origin Lakeview Health is
not_knowing** (O5: relaying does not launder; the provider's charge is the provider's to know).

### 9D-ii.4 Cases

| # | Case | Kind level | Consumer |
|---|---|---|---|
| **Xs1 (Rc9)** | Riverbend Hospital's bill *$1,300*, read; Riverbend Hospital provider of X | `billed`: candidate, **knowing** (origin Riverbend Hospital in role) | 7H: candidate never governs; Riverbend Hospital's utterance governs |
| **Xs2 (F3 / K5)** | Rob: *the EOB said $400* — a PR claim by the household | not_knowing (Rob holds no role) | 7H: reported, never governing (Rc12) |
| **Xs3 — the EOB's billed column** | Lakeview Health's EOB, read: *billed $1,300 · plan paid $568 · PR $412* | `plan_paid`, `patient_responsibility`: knowing (Lakeview Health insurer of X); **`billed`: NOT_KNOWING** — the insurer relays the provider's charge | 7H: Lakeview Health's *billed* is not in the provider's series |
| **Xs4 (Rc10)** | two Lakeview Health PR stances at one date | both knowing | 7H: conflict → none (TS) |
| **Xs5 (CC1 / Ju11)** | Lakeview Health *applied $400*, Cigna *applied $150*, on one X in respect of A and B | **both knowing** — each holds `insurer_of` X | 7J: A from Lakeview Health's only, B from Cigna's only — the plan gate is 7J's |
| **Xs6 (C6)** | Lakeview Health *applied: none* | knowing; content opaque | 7J: exempt — not zero, not unknown |
| **Xs7 (C7 / Rc6)** | Lakeview Health: *not a covered service* | `denial`: knowing; **not a determination** — a different kind by name | 7H: not read; the determination stays whatever the parties said; the note names it |
| **Xs8 (E3)** | Lakeview Health: *reversed*, 8/15 | `adjudication` (F1): knowing | no consumer |
| **Xs9 — the provider is not the insurer** | Riverbend Hospital states *plan paid $568* | `plan_paid` by Riverbend Hospital: **not_knowing** (Riverbend Hospital is provider, not insurer) | 7H: reported, not in the insurer's series |
| **Xs10 — the 2 × 2 on X** | origin ∈ {Riverbend Hospital, Lakeview Health} × kind ∈ {`billed`, `patient_responsibility`} | (Riverbend Hospital, billed) knowing · (Lakeview Health, billed) not · (Riverbend Hospital, PR) not · (Lakeview Health, PR) knowing — the type test called all four knowing | — |
| **Xs11 (Dg21's analogue)** | Lakeview Health's `insurer_of` X contested at the stance's date | undetermined | 7H: the role answer reported; not governing |
| **Xs12 (F7)** | an undated PR stance | undetermined | 7H: disqualified |
| **Xs13 (F2-i)** | the EOB line with the insurer as subject | refused under the ruled name; accepted under `eob_amount` | — |
| **Xs14 (F2-ii)** | In12's corpus with no `insurer_of` claim | Lakeview Health not_knowing until the role is in the record | 7B: In12 restored by the role claim, not by the type |

### 9D-ii.5 Candidate — six entries; two rows in the table; nothing else

```text
BILLED · PATIENT_RESPONSIBILITY · PLAN_PAID · APPLIED_TO_DEDUCTIBLE · DENIAL · ADJUDICATION
    subject (subject_expense_id,)  object ()  symmetric False · reading_establishes True · relational_knowing True
    BILLED                       knowing_relation KNOWING_PROVIDER_AT_AS_OF
    the other five               knowing_relation KNOWING_INSURER_AT_AS_OF
_ROLE_AT_AS_OF += {KNOWING_PROVIDER_AT_AS_OF: PROVIDER_OF, KNOWING_INSURER_AT_AS_OF: INSURER_OF}
```

The resolver untouched. The swap: 7H's and 7J's catalogue lines (already the ruled names), their map
entries for the six retired, the 9C fixture's `adjudication` / `plan_paid` / `applied_to_deductible`
by constant; the two F2 classes as ruled; the consumer fixtures' *no billed / PR / plan_paid /
determination kind registered* narrowed to `determination` (9D-v). Mutations for `s121`: the
insurer's relay of the charge knowing for `billed` · the provider's *plan paid* knowing · a denial
read as a determination · a denial read as an adjudication amount · the plan gate at the kind level
(a stance not_knowing for the other plan's insurer) · the type conferring knowing · a reading
establishing state · an undated stance knowing · the relation re-ruled (a second resolver for the
insurer) · `exempt` read as zero.

### 9D-ii.6 Ruling sought

> **(1) 9D-ii-F1:** `adjudication` and `denial` two kinds (a), or (b) / (c). **(2) 9D-ii-F2:** the two
> swap classes accepted before the build — the EOB line renamed to the existing `eob_amount`
> stand-in; **the role claim added to the corpora that asserted knowing by type** (7B In12,
> expense-identity), as the fact those cases always meant. **(3)** The six entries and two table rows
> as §9D-ii.5 — the relation applied, not re-ruled; `applied_to_deductible`'s kind-level holder
> `insurer_of` X with the per-plan selection 7J's. Nothing here authorises code.

---

### 9D-ii.7 Ruling — Rob, 2026-09-19: as presented, F1 (a), both F2 classes accepted; build AUTHORISED

**Application of the already-ruled relation.** The six stances use the role-at-date relation on
**X**, without creating another relation: `billed` → `provider_of(X)`; `patient_responsibility`,
`plan_paid` → `insurer_of(X)`; `applied_to_deductible` → `insurer_of(X)`, **7J additionally
selecting the insurer of the plan being computed**; `denial` and `adjudication` per F1. For
`applied_to_deductible` the distinction is exactly 9D-i's: *the kind-level relation answers who
holds the stance on X; 7J's consumer gate answers which insurer's plan is being computed.* **The
kind cannot acquire P merely because a consumer has P.** The EOB relay case follows directly:
**origin is not a role claim** — an insurer-origin `billed` statement does not become knowing
merely because the insurer relayed the provider's charge.

**F1 — two distinct kinds.** `denial` names the denial stance; `adjudication` the adjudicative
stance, including the reversed result that otherwise has nowhere to live. Their content remains
opaque; the distinction is in **kind**, not in an interpreted content / verdict field — C7's
name-based fence preserved without manufacturing a generic interpretation of the proposition text.

**F2 — the two correction classes.** (i) The borrowed `patient_responsibility` line shape: corrected
to the existing 7E `eob_amount` stand-in — preserve the proposition actually under test rather than
force it into a ruled stance's subject shape. (ii) Type-only knowing assertions: **add the missing
role claims.** Not a semantic relaxation: under the frozen relation, *knowing = the asserter held
the required role on X at `as_of`*; a fixture that intends Lakeview Health knowing for an insurer stance must
establish Lakeview Health's `insurer_of`, and one that intends Riverbend Hospital knowing for `billed` must establish
Riverbend Hospital's `provider_of`. **The boundary: the build may add the role evidence the cases already
presuppose; it may not infer that role from the stance, origin, EOB or type.**

**Frozen:** six stance entries; the existing relation applied on X; two `_ROLE_AT_AS_OF` rows for
`provider_of` and `insurer_of`; the 7J plan-selection qualification for `applied_to_deductible`;
distinct `denial` and `adjudication` with opaque content; the borrowed-line corrections; explicit
role claims where fixtures relied on type-only knowing. No new relation, no interpretation of
content, no change to 9D-i or the relation.

**Build AUTHORISED — Rob: "Rule F1 as (a), accept both F2 classes, build 9D-ii."**

---

#### Built — 2026-09-20 (9D-ii)

`core/database.py`: `BILLED`, `PATIENT_RESPONSIBILITY`, `PLAN_PAID`, `APPLIED_TO_DEDUCTIBLE`, `DENIAL`,
`ADJUDICATION` — six registry entries, the expense the subject, no object, `reading_establishes True ·
relational_knowing True`; `billed` with `KNOWING_PROVIDER_AT_AS_OF`, the five with
`KNOWING_INSURER_AT_AS_OF`; **two rows in `_ROLE_AT_AS_OF`** (`provider_of`, `insurer_of`) and two names
on **the one resolver** — `_role_at_as_of` untouched, the relation applied, not re-ruled. `denial` and
`adjudication` two entries, no verdict key. The comment block states the application, the plan gate as
7J's (*the kind cannot acquire P because a consumer has P*), the relay (*origin is not a role claim*)
and C7's fence by kind. **The whole non-comment diff:** eight constants, six entries, two table rows,
two `_KNOWING_RELATIONS` lines. No consumer, no `reach`, no `_claim_states`, no resolver change.

**The oracle:** `tests/test_expense_stances_fixture.py` — 18 checks over Xs1–Xs14 and the registry,
with a foundation map carrying no entry for the six: Xs1 (Riverbend Hospital's `billed` knowing; its bill read →
candidate, knowing); Xs2 (Rob's *the EOB said $400* → not_knowing, reported never governing); **Xs3
(the EOB's own *billed* column → not_knowing — the insurer relays the provider's charge; its
`plan_paid` and PR knowing)**; Xs9 (Riverbend Hospital's *plan paid* → not_knowing); **Xs10 the 2 × 2 on X** (the
type test called all four knowing); Xs4 (two Lakeview Health PR stances at one date → both knowing; 7H conflict
→ none); **Xs5 (CC1: Lakeview Health and Cigna each `applied` on one X → both knowing at the kind level; 7J A
from Lakeview Health's only, B from Cigna's only)** and **Xs5′ — the ruling's sentence made executable**: Cigna
holds `insurer_of` X6 but insures no plan X6 is in respect of → knowing at the kind level, absent from
A's basis (added after the first s121 run: the plan-gate mutation escaped because no case had an
insurer outside every plan; a fixture gap, closed); Xs6 (`none` → knowing, 7J exempt, not zero);
**Xs7 (the denial its own kind, knowing, no determination current, 7H's note names it, the content
unparsed)**; Xs8 (*reversed* an `adjudication`, knowing for Lakeview Health, not for Riverbend Hospital, not a denial by
kind); Xs11 (the insurer's holds claim retracted → 7F undetermined → the relation undetermined —
**my first draft asserted `contested`; a lone retracted holds stance is *undetermined* in 7F, the
substrate was right**); Xs12 (undated → undetermined); Xs13 (the EOB line with the insurer as subject
refused under the ruled name, accepted under `eob_amount`); **Xs14 (Humana, an institution with no
`insurer_of` claim → not_knowing; the role added to the record → knowing; the role never inferred)**.

**The substitution — and the two classes measured before the build, confirmed by the substrate run
before any fixture was written:** 7H 32/32 and 7J 31/31 with their map entries for the six retired
and the helpers naming the ruled constants; the 9C fixture's three names by constant (33/33). **F2(i):**
the EOB line under `patient_responsibility` in exactly the three fixtures foreseen (expense-identity,
plan-identity, obligation-in-respect-of) → `eob_amount`, no new kind. **F2(ii):** the role claims
added where knowing had been asserted by type — 7B's In12 / In17 (Lakeview Health's `insurer_of` X), In7 b–d
(**both** Lakeview Health parties, and both Cigna parties — the cases mean *two knowing origins*, so each holds
the role), expense-identity (Riverbend Hospital's `provider_of` X) — **five role claims in two fixtures**, each
added as a claim with its own utterance, none inferred; and one further addition reported as its
own class: expense-identity's `billed` stance was **undated**, and under the frozen rule (every
P-ack dated) an undated stance's relation is undetermined — the utterance's own date supplied
(`as_of='2026-02-20'`). **Pins:** the relational-knowing and role-catalogue fixtures (four names →
six), `s97`, and 9D-i's own `s120` opening check, which had pinned the exact table `== {one row}`
— restated to the 9D-i row it owns (the class 9C's pins taught, reproduced by me a day later).

**Smoke `s121_expense_stances.py`:** the fixture passes; ten mutations — the insurer's relay of the
charge knowing for `billed` · the provider's *plan paid* knowing · a denial read as a determination ·
a denial read as an adjudication amount · **the plan gate at the kind level (P reached from X)** ·
the type conferring knowing · a reading establishing state · an undated stance knowing · the
relation re-ruled (a second resolver for the insurer) · exempt read as zero — all caught; the
plan-gate one on the second run, after Xs5′ (above).

**Left where it belongs:** 7J's plan selection (the consumer's) · the determination (9D-v) · the
insurer's stances and terms on P (9D-iii — `KNOWING_PLAN_INSURER_AT_AS_OF` is a third row, not a
third resolver) · values and the bank's stances (9D-iv). No schema, no migration. Gate 1419 →
1442, 0 failed. **A gate-time observation, not a finding:** the gate's silent stretch in `s109`
(aboutness, twenty fixture runs) grew from ~10 to ~25 minutes — `derived_strength` on a ruled stance now
runs 7F's `in_effect` per read; a cost of the ruled relation, recorded so a later slice does not mistake it
for a hang.

#### Accepted — Rob, 2026-09-20 (9D-ii)

Accepted on the gate's evidence (1442 / 0, s121 23/23) and the build's fidelity to §9D-ii.7: the
relation applied on X through two table rows with the resolver untouched; the plan gate left 7J's;
`denial` and `adjudication` two kinds with opaque content; the borrowed EOB lines renamed to the
existing stand-in; the presupposed role claims added and none inferred; the s121 plan-gate gap closed
by a real negative case rather than a count; the 9D-i pin restated to what 9D-i owns. **9D-iii remains
unopened until Rob opens it; it adds a row for `insurer_of_plan` and settles F4 and F6 — it does not
re-rule the relation (§9D.9).**

---

## Pass 9D-iii — The insurer's stances and terms on P

*Opened by Rob 2026-09-20 after 9D-ii's acceptance (`2012b2c`). Scope per §9D.9: `deductible_applied`,
`eligibility`, `coverage_ended`, `authorization`, `deductible`, `individual_deductible`, `plan_year`;
the role-at-date relation applied — a third row (`insurer_of_plan`) — not re-ruled; F4 and F6
settled; consumer 7J. No code until cases → candidate → ruling → explicit build authorisation. **What
this slice adds to the question:** the first stance whose subject is not the thing the role is on,
and the first whose shape 7J reads two ways.*

### 9D-iii.1 What is fixed

§9D-i.8 / §9D.9: H; `reading_establishes: True` = strength through the established origin, never
state; the relation ruled once, applied by name → role rows. PLAN_IDENTITY §2 / §7 (PL2): a term is
*the insurer's dated stance — a term claim about P*; the plan an impoverished anchor, terms claims
never fields (Pl2: *the family deductible has a subject that is neither Kim nor Lakeview Health*); Pl10 the
insurer's accumulator stance; Pl11 the authorization *the insurer's stance about P with the service
as content, never an expense*; Pl12 the insurer's retroactive termination *a dated stance; earlier
stances stand as history; P remains minted*; Pl15 / APPLICABILITY (`none` = the rule does not exist,
C2). **F5** (§F.2, 9A): the insurer's *never eligible* is a claim *beside* the household's membership,
deriving nothing and overriding nothing. **7J §7J.7:** the term — the governing `deductible` /
`individual_deductible` claim on P at d, content an amount or `none`, no claim → `unknown`, **no role
gate — any party's established term, latest at or before d**; the window — the governing `plan_year`
(`as_of` = start, content = end); the stated accumulator — `deductible_applied` on P (the family
figure) or on (person, P) (the individual figure), **by the plan's insurer** (asserter in effect as
`insurer_of_plan`); eligibility stances listed with the asserter's `insurer_of_plan` answer **read on
the object plan**, deriving nothing.

### 9D-iii.2 What 7J reads — two shapes and one object-side role

| kind | subject | object | `as_of` | content | 7J's gate |
|---|---|---|---|---|---|
| `deductible_applied` (family figure) | P | **none** | yes | money | asserter in effect as `insurer_of_plan` P |
| `deductible_applied` (individual figure) | P | **`object_party_id` = the person** | yes | money | the same; selected by `object_party_id ∈ person` |
| `eligibility` | **the person party** | **P** | yes | text | none (F5 — listed); the asserter's `insurer_of_plan` answer reported **on the object plan** |
| `coverage_ended` | P | none | yes | a date / text | not read (Pl12; the 9C fixture and plan-identity use it) |
| `authorization` / `authorized` | P | none | yes | the service | not read (Pl11; two names in two fixtures) |
| `deductible` · `individual_deductible` | P | none | yes | money or `none` | **no role gate** |
| `plan_year` | P | none | start | end | no role gate |

**Two things the registry's shape cannot say as-is.** (a) `deductible_applied` has an *optional*
object: the registry expresses *no object* (`()`, a required absence) or *an established object*
(`(slot,)`), never *either*. (b) `eligibility`'s role is on its **object**: the relation as stated in
§9D-i.3 and built reads *the claimant's role on the claim's subject*; for `eligibility` the subject is
the person and the role is `insurer_of_plan` on the object plan — exactly the role 7J already reads on
the object.

### 9D-iii.3 Findings — put to Rob

**9D-iii-F1 — `deductible_applied`'s optional object.** Options: **(a) two kinds** —
`deductible_applied` (subject P, no object: the family figure) and `individual_deductible_applied`
(subject P, object the person) — the exact parallel of the two term kinds 7J already keeps apart
(`deductible` / `individual_deductible`); **but 7J reads one catalogue key and filters by the object
slot** (`claims_on_plan(catalogue['deductible_applied'], person_members)`), so two kinds mean a second
catalogue key and a changed read — **a 7J consumer change**, of the smallest kind (Tr8's class: a
consumer's line changing because a kind's status changed), to be authorised explicitly if (a) is
ruled; (b) one kind with the person **required** — the family figure would have no home; (c) one kind
with the person as **content** — K8 refuses; (d) a registry key for *optional object* — §2.3's shape
refuses; (e) leave `deductible_applied` unruled in 9D-iii (a stand-in until 7J is opened) — the
catalogue then rules six of seven. *Reading:* (a), with the 7J catalogue-key change named as the one
consumer line it costs; or (e) if Rob will not open 7J for it. **Rob's.**

**9D-iii-F2 — the role on the object.** For `eligibility` the thing the stance is *about* is
(person, P) and the role that makes the insurer its holder is on P. Options: **(a) the table row
names the side** — `_ROLE_AT_AS_OF[KNOWING_PLAN_INSURER_AT_AS_OF] = (INSURER_OF_PLAN, 'object')` for
`eligibility`, `'subject'` for every other row; the resolver reads the named side — *the relation's
meaning is unchanged: the claimant held role R on the thing the stance is about, at `as_of`; which slot
that thing sits in is the kind's shape.* This touches `_role_at_as_of`'s dispatch (one parameter),
which §9D.9 forbids as *re-ruling* and permits as *application* — **Rob decides which this is.** 7J's
own read (the role on `claim.object_plan_id`) is the evidence it is application; (b) flip
`eligibility`'s slots (P subject, person object) — the role lands on the subject, but 7J reads
`subject_party_id` (a consumer change) and F5's deliberate parallel with `under_plan`'s shape is
lost; (c) `eligibility` takes no relation — undetermined, as `under_plan` — contrary to §9D.9's *the
insurer's stances take the relation*. *Reading:* (a). **Rob's.**

**9D-iii-F3 (= 9D-F6) — three "coverage ended" claims, three kinds.** The household's boundary claim
`under_plan_ended` (F — party → plan; *the household says Kim's membership ended*); the insurer's
`eligibility` stance about (person, P) (F5 — *never eligible*, *eligible from*, *ended 6/30* as content
about a person's standing under P); the insurer's `coverage_ended` stance about **P** (Pl12 — *the
arrangement ended, retroactive to 6/30*; adjudications reversed). Different holders (household vs
insurer), different subjects (party → plan; person → plan; P), different rulings behind them. *Reading:*
**three kinds; none derives another** — an insurer's `coverage_ended` on P manufactures no
`under_plan_ended` for anyone and no `eligibility` stance; a household's dispute of the termination
(plan-identity's *disputed — we paid through December*) is a second `coverage_ended` claim by a party
not in role — established, not_knowing, beside. **Rob's.**

**9D-iii-F4 (= 9D-F4) — the terms: the insurer's position; 7J reads any party's.** The kind's holder is
`insurer_of_plan`: the SBC read → candidate, knowing through the origin; the household's *our deductible
is $3,000* → not_knowing (a relay — O5). 7J's term read (*latest established, any party; strength not
read*) stays 7J's — **recorded as a 7J question** (the class of 9D-i-F3: *should the term read gate by
the insurer's role as TG-base gained the entitled-party test?*), not changed here. One consequence
is a fixture check, foreseen below (F6-iii). `plan_year` the same.

**9D-iii-F5 — `authorization`: one name.** Pl11's kind appears as `authorized` (plan-identity) and
`authorization` (the 9C fixture). The catalogue names it once — `authorization`, the noun, as `denial`
and `adjudication` are; subject P, content the service; `insurer_of_plan`; no consumer. Plan-identity's
name changes by constant.

**9D-iii-F6 — swap classes, measured before the build.** (i) *The borrowed line shape:* plan-identity's
`line(sbc, r_sbc, 'deductible', …, aetna)` — the SBC line with the insurer as subject — refused under
the ruled `deductible`; the shape kept under a stand-in (`sbc_line_figure`), no new kind. (ii) *The
presupposed role:* plan-identity asserts Lakeview Health knowing for the authorization by type with **no
`insurer_of_plan` claim in its corpus** — the role added, never inferred (9D-ii's class). (iii) *A
check whose strength clause was the foundation's:* plan-identity's Pl2 asserts the **household's**
term claim is `knowing` (map `{'person', 'institution'}` — anyone); under the ruled kind the
household is not the holder → not_knowing. The check's meaning — *a claim, dated, with a party behind
it, not a field on the anchor* — survives; its strength clause was the type test's and retires to
*established, a party behind it, not_knowing (the insurer's rule, relayed)* — Tr8's class (an
assertion made true by the stand-in that the ruling changes), reported for Rob to accept as such.

### 9D-iii.4 Cases

| # | Case | Kind level | 7J |
|---|---|---|---|
| **Ps1 (Pl10)** | Lakeview Health: *applied to deductible $700 as of 6/30* on P | `deductible_applied`: knowing (Lakeview Health insurer of P at 6/30) | the stated accumulator, G named |
| **Ps2 (Pl10 individual)** | Lakeview Health: *Kim: $300 applied* on (Kim, P) | per F1 | the individual figure |
| **Ps3 (F5)** | Lakeview Health: *Kim was never eligible* — (Kim, P) | `eligibility`: knowing **by the role on the object plan** (F2) | listed beside membership; derives nothing |
| **Ps4** | Rob: *Kim is eligible, they told me* — (Kim, P) | not_knowing (Rob not the plan's insurer) | listed, `plan_insurer` not in effect |
| **Ps5 (Pl12)** | Lakeview Health: *coverage ended 6/30, retroactive*, 8/15 — on P | `coverage_ended`: knowing | not read; P remains minted; no `under_plan_ended` manufactured (F3) |
| **Ps6 (Pl12 disputed)** | Rob: *that is wrong, we paid through December* — `coverage_ended` on P | not_knowing; established; beside | — |
| **Ps7 (Pl11)** | Lakeview Health: *prior auth, MRI* on P, 2/10 | `authorization`: knowing; minted no expense | not read |
| **Ps8 (Pl2 / F4)** | Rob: *our deductible is $3,000*; the SBC read; Lakeview Health's own statement | `deductible`: Rob not_knowing · the SBC candidate, knowing · Lakeview Health knowing | 7J reads the latest established, any party — recorded (F4) |
| **Ps9 (C2)** | Lakeview Health: *deductible: none* on H | knowing; content opaque | 7J: `none` — the rule does not exist |
| **Ps10 (CC1 on P)** | Cigna states `deductible_applied` on P (Lakeview Health's plan) | not_knowing (Cigna not insurer of P) | not the stated accumulator |
| **Ps11** | the plan year by the household: `plan_year` 1/1–12/31 | not_knowing | 7J's window still (F4) |
| **Ps12 (F7)** | an undated term | undetermined | 7J disqualifies |
| **Ps13 (the 2 × 2 on P)** | origin {Lakeview Health, Rob} × kind {`deductible_applied`, `eligibility`} | (Lakeview Health, ·) knowing · (Rob, ·) not — with `eligibility`'s role read on the object | — |
| **Ps14 (F6-i)** | the SBC line with the insurer as subject | refused under `deductible`; accepted under the stand-in | — |

### 9D-iii.5 Candidate — pending F1 and F2

```text
DEDUCTIBLE · INDIVIDUAL_DEDUCTIBLE · PLAN_YEAR · COVERAGE_ENDED · AUTHORIZATION · DEDUCTIBLE_APPLIED
    subject (subject_plan_id,)  object ()  symmetric False · reading_establishes True · relational_knowing True
    knowing_relation KNOWING_PLAN_INSURER_AT_AS_OF
INDIVIDUAL_DEDUCTIBLE_APPLIED   subject (subject_plan_id,)  object (object_party_id,)   — if F1 (a)
ELIGIBILITY                     subject (subject_party_id,) object (object_plan_id,)    knowing_relation the same name — the role on the OBJECT (F2)
_ROLE_AT_AS_OF += {KNOWING_PLAN_INSURER_AT_AS_OF: INSURER_OF_PLAN}   (+ the side, if F2 (a))
```

The swap: 7J's catalogue lines (and one new key if F1 (a)), its map entries for the seven retired;
the 9A fixture's `eligibility` and the 9C fixture's `coverage_ended` / `authorization` by constant;
F6's three classes as ruled. Mutations for `s122`: the household's term knowing · the household's
plan year governing knowing · a `coverage_ended` minting `under_plan_ended` · an `eligibility`
stance deriving membership (F5 reversed) · the other plan's insurer knowing for the stated
accumulator · the role read on the wrong side for `eligibility` · the type conferring knowing · a
reading establishing state · an undated term knowing · the relation re-ruled (a second resolver for
the plan's insurer).

### 9D-iii.6 Ruling sought

> **(1) 9D-iii-F1:** `deductible_applied` — two kinds with the one 7J catalogue-key change named, or
> unruled in this slice. **(2) 9D-iii-F2:** the role read on the object for `eligibility` — the table
> row naming the side (application), a slot flip (consumer change), or no relation. **(3) F3:** three
> kinds. **(4) F4:** the kind's holder the insurer; 7J's any-party term read recorded as 7J's question.
> **(5) F5:** `authorization`, one name. **(6) F6:** the three swap classes accepted before the
> build. Nothing here authorises code.

---

### 9D-iii.7 Ruling — Rob, 2026-09-20: F1–F6 RULED; no code authorised by this ruling

**F1 — `deductible_applied`: two kinds, parallel to `deductible` / `individual_deductible`.** The
distinction is not whether an object happens to be present but **semantic shape**: the family figure
on P has no individual object; the individual figure is on (person, P). An optional-object registry
key would collapse the two shapes into one kind and make the registry encode a distinction it does
not otherwise encode; the person as opaque content would lose the distinction 7J actually consumes.
**The person-required form is explicitly named as the consumer line.** This touches 7J's catalogue
only in the already-established two-shape classification; implementation is not authorised here.

**F2 — `eligibility`: the relation applied, not reinterpreted.** The semantic fact stands: *the
claimant held role R on the thing the stance is about, at `as_of`.* For this kind the thing the stance
is about is the **plan** while the stance's subject is the **person**; the resolver therefore needs
to know that the role is tested on the object's side. **A dispatch / application question, not a
new meaning for `insurer_of_plan`.** 7J is particularly strong evidence — it already performs the
object-plan reading — so the relation is neither flipped nor removed to preserve a simpler resolver
shape. **Ruling: retain the relation semantics; authorise the application shape in which the resolver
can specify that the role is read on the object.** *Explicitly marked: the one F item that reaches
the resolver dispatch, as §9D.9 anticipates — an application of the already-ruled relation to an
unusual stance shape, not permission to redefine what the relation means. 9D-iii does not reopen the
ontology because this is the first slice where the stance subject and the role-bearing thing
diverge.*

**F3 — coverage ended: three independent kinds, no derivation.** They differ in who / what the claim
is about and what boundary ended: the household's coverage boundary; the insurer's eligibility about
(person, P); the insurer's termination about P. A shared colloquial description does not make one
derivable from another.

**F4 — the insurer holds the terms.** *Our deductible is $3,000* is evidence relaying the insurer's
term; it does not make the household the holder. 7J's any-party term reading remains **7J's
question**, not silently settled here.

**F5 — `authorization`: one kind.** No shape distinction warrants multiplying it.

**F6 — the three swap classes retained** — borrowing the SBC line's shape; omitting the
`insurer_of_plan` role from plan-identity; treating the household's relayed term as knowing. **The
household-term case must resolve to `not_knowing`**, never a manufactured positive knowing.

| | Ruling |
|---|---|
| **F1** | two `deductible_applied` kinds, parallel to 7J's two deductible kinds; the person-required form the consumer line |
| **F2** | relation retained; the role read on the object for this shape; the resolver dispatch may carry that application distinction |
| **F3** | three independent coverage-ended kinds; no derivation |
| **F4** | the insurer holds the terms; the household's statement is relay evidence; 7J owns any-party term semantics |
| **F5** | one `authorization` kind |
| **F6** | three swap classes retained; the household-term knowing assertion retires to `not_knowing` |

**No code.** The build awaits its separate authorisation.

---

#### Built — 2026-09-20 (9D-iii)

`core/database.py`: eight registry entries — `DEDUCTIBLE`, `INDIVIDUAL_DEDUCTIBLE`, `PLAN_YEAR`,
`DEDUCTIBLE_APPLIED`, `COVERAGE_ENDED`, `AUTHORIZATION` (the plan the subject, no object);
**`INDIVIDUAL_DEDUCTIBLE_APPLIED`** (the plan the subject, the person the object — F1's second kind);
**`ELIGIBILITY`** (the person the subject, the plan the object — F5's shape kept); all
`KNOWING_PLAN_INSURER_AT_AS_OF`, `reading_establishes True`. **A third row** in `_ROLE_AT_AS_OF`
(`insurer_of_plan`), the name on the one resolver. **F2's application shape:** a second table,
`_ROLE_AT_AS_OF_SIDE = {ELIGIBILITY: 'object'}` — keyed by the **stance kind**, not the relation name
(the same relation serves `deductible_applied` on its subject); `_role_at_as_of` gains a `side`
parameter defaulting to `'subject'`, and `_relational_strength` passes it only when the table names
one. The relation's statement is unchanged — *the claimant held role R on the thing the stance is
about, at `as_of`* — the one thing the dispatch now carries is which slot that thing sits in. **The
one consumer line F1 named:** 7J's stated accumulator reads the individual figure by its own kind
(`applied_kind = catalogue['individual_deductible_applied'] if person is not None else …`), exactly
as it already reads the individual term; `ACCUMULATOR_KINDS` gains the key. **One thing beyond the
ruling, reported for Rob to accept or strike:** while writing F2's negative case (the same
`eligibility` claim read on its *subject* side must answer not_knowing) the wrong-side read came back
**knowing by id collision** — the resolver looked a *person* id up among *plan* ids and Kim's party
id matched a plan's. The resolver as built never checked that the slot's identity type matches the
role's object type; every ruled use so far matched, so nothing caught it. **A one-line type guard
added** (`_slot_type(slot) != _slot_type(role's object slot) → not_knowing`): a plan role is no role on
a person. A guard against a latent defect, not a change of meaning; every earlier stance fixture
unchanged by it (22 / 18 / 40 / 32 / 31).

**The oracle:** `tests/test_plan_stances_fixture.py` — 20 checks over Ps1–Ps14, the registry and F2's
negative, with a map carrying no entry for the eight: the registry's refusals (a `deductible_applied`
with a person — that is the individual kind; an individual one without; a plan-subject
`eligibility`; a party-subject term); **Ps8** (Rob's *our deductible is $3,000* → not_knowing, a relay;
the SBC read → candidate, knowing through its origin; Lakeview Health's own → knowing) and **Ps8 through 7J,
recorded** (the latest established term governs by date, any party — 7J's open question, read here
as it is); Ps9 (`none` → knowing; 7J: the rule does not exist); Ps11 (the household's plan year →
not_knowing; 7J's window still takes it — recorded); Ps12 (undated → undetermined; 7J disqualifies);
**Ps1 / Ps2** (the family figure and the individual figure, two kinds, each 7J's on its own axis);
Ps10 (Cigna's figure on Lakeview Health's plan → not_knowing; not the stated accumulator); **Ps3** (Lakeview Health's
*never eligible* about (Kim, P) → knowing **by the role on the object plan**; 7J lists it beside
membership, `plan_insurer` in effect, membership unchanged); Ps4 (Rob's → not_knowing); **F2's
negative** (the same claim read on its subject side → not_knowing; on its object side → knowing — the
side is the kind's); Ps3′ (the reading path on the object-read stance); **Ps5** (Lakeview Health's
`coverage_ended` on P → knowing; P remains; **no `under_plan_ended` and no `eligibility` manufactured**;
Kim still in effect by the household's claim — three kinds, none derives another); Ps6 (Rob's dispute
a second `coverage_ended`, not_knowing, beside); Ps7 (the authorization one kind; no expense minted);
**Ps13 the 2 × 2 on P**; Ps14 (the SBC line refused under `deductible`, accepted under its stand-in).

**The substitution — and F6's three classes, confirmed by the substrate run before the fixture
was written:** 7J 31/31 with the new catalogue key (F1's line), its helper minting the individual
figure by its own kind, its map entries for the seven retired, its *no term / eligibility kind
registered* absence narrowed to `occurred_on`; the 9A fixture's `eligibility` and the 9C fixture's
`coverage_ended` / `authorization` / `plan_year` / `deductible` by constant; the 9D-ii fixture's
catalogue key. **F6(i):** plan-identity's SBC line → `sbc_line_figure`, no new kind. **F6(ii):** Lakeview Health's
`insurer_of_plan` role added to plan-identity's corpus — placed **before Pl11**, not before Pl15
(*no claim of any kind touches P* is the decisive case, and my first placement broke it; the role
belongs where the case that presupposes it lives). **F6(iii):** Pl2's check — *the term is a claim,
dated, with a party behind it* — kept, its strength clause retired from `knowing` to **`not_knowing`**
as ruled: the household relays the insurer's rule. `authorized` → `AUTHORIZATION` by constant.
**Pins:** the relational-knowing and role-catalogue fixtures (six → seven names); `s97`; and two of
my own — the 9D-ii fixture had pinned the plan insurer's relation name *absent*, and `s121` the
total relation count — the exact-pin class, restated to what each slice owns.

**Smoke `s122_plan_stances.py`:** the fixture passes; ten mutations — the household's term knowing
(the relay as holder) · the household's plan year knowing · `coverage_ended` minting
`under_plan_ended` (F3) · `eligibility` deriving membership (F5 reversed) · the other plan's insurer
knowing · **the role read on the wrong side (the side table emptied — F2 dropped)** · the type
conferring knowing · a reading establishing state · an undated term knowing · **the two applied shapes
collapsed (F1 reversed)** — all ten caught on the first run.

**Left where it belongs:** 7J's any-party term read (recorded twice, Ps8 and Ps11 — 7J's question) ·
the determination (9D-v) · values and the bank's stances (9D-iv) · 9D-i-F3 (7G). No schema, no
migration. Gate 1442 → 1478, 0 failed.

#### Accepted — Rob, 2026-09-20 (9D-iii)

Accepted on the gate's evidence (1478 / 0, s122 23/23) and the build's fidelity to §9D-iii.7: the
two applied kinds by shape with the one named 7J line; F2 as application — the side carried by a
table keyed by the stance kind, the relation's statement unchanged; three coverage-ended kinds with
nothing derived between them; the insurer the holder of the terms, the household's statement a relay,
7J's any-party read left 7J's; one `authorization`; F6's three classes as ruled, the household-term
assertion at `not_knowing`. **The resolver type guard, reported beyond the ruling, is accepted with
the build** — a guard against a latent id-collision defect, not a change of the relation's meaning.
**9D-iv remains unopened until Rob opens it; it introduces the remaining new relation shape (F3's
role-set) and does not re-rule the role-at-date relation.**

---

## Pass 9D-iv — Values: `amount`, `occurred_on`, `cleared`

*Opened by Rob 2026-09-20 after 9D-iii's acceptance (`0b96733`). Scope per §9D.9: `amount` (on a
payment), `occurred_on` (on a payment; on an expense), `cleared` (the bank's stance on a payment);
**the remaining new relation shape — F3's role-set**; consumers 7G, 7H, 7I, 7J; the role-at-date
relation not re-ruled. No code until cases → candidate → ruling → explicit build authorisation. The
crux this slice exposes: **the one party the record says can know a value — the bank (K6) — holds no
ruled role.***

### 9D-iv.1 What is fixed

PAYMENT_IDENTITY: a payment's amount, date, payer and payee are *dated relations* on the minted
identity, never fields; Pm9 (the mother paid); Pm12 (a bank line about nothing paid mints nothing);
Pm10 / Pm13 (autopay lines are candidates). **Kn7 — mandatory, permanent:** *minting is not knowing*
— Rob mints his mother's payment; his claim that it occurred is not knowing; no named relation maps a
minter to an event's properties (only the about-ness kinds designate the minter). **K6:** the bank's
clearance is not acknowledgment — *the bank can know the household's money left; it cannot thereby
establish what E recorded*. O5: relaying does not launder. 9B: `paid_by` / `paid_to` (party →
payment), `provider_of` / `incurred_by` (party → expense) — holds-only roles, `KNOWING_SUBJECT_PARTY`.
**The consumers:** 7G / 7H / 7I read a payment's `amount` and `occurred_on` and 7J an expense's
`occurred_on` through `_one_value` — *one established value, or undetermined (none / unparsed /
disputed)* — **reading no strength for any value**; the date is `as_of` or content. So no consumer
gate exists for a value, and no consumer changes whatever 9D-iv rules about knowing.

### 9D-iv.2 What the fixtures hold — shapes

| kind | subject | `as_of` | content | who asserts it in the corpora | strength asserted? |
|---|---|---|---|---|---|
| `amount` | payment | **none, everywhere** | money | the household; the mother (Pm9); the bank's line by reading | no |
| `occurred_on` | payment **or** expense | the date itself (or content) | — | the household; the bank's line; the provider's bill | **Kn7 only** (Rob not_knowing; the mother undetermined) |
| `cleared` | payment (the ruled shape); **or the bank party with the thing a candidate** — the bank *line* (payment-identity, proposition-concerns) | the date | the line | the bank by reading; the bank by utterance (7G Dg3) | no |
| `bank_returned_item` (9D-i's rename) | payment | the date | the line | the bank | no |
| `date_of_service` (7E, 7B stand-in) | expense | — | a date | the household | (7E's chains) |

### 9D-iv.3 Findings — put to Rob

**9D-iv-F1 — the role-set relation, and whether a value is dated.** A value is *a fact about the
thing*, not a position as of a date: an amount does not change with time (a correction is a second
claim; `_one_value` says *disputed*), and `occurred_on`'s `as_of` **is** the value. Every `amount`
claim in every corpus is undated. So the relation for values cannot be the role-at-date relation
(undated → undetermined would make every amount undetermined — harmless to the consumers, but the
wrong answer): **the role-set relation** — *the claimant holds any of a set of roles on the claim's
subject* — read on the roles' **holds stances as established** (9B's roles are holds-only; a holds
stance stands from its `as_of`), not at a date the value does not carry. The set per subject type:
a payment → {`paid_by`, `paid_to`}; an expense → {`provider_of`, `incurred_by`}. **This is the
second new relation shape §9D.8 foresaw** — a set, undated — and it is *not* a re-ruling of the
role-at-date relation, which stays for positions. *Reading:* rule it so. **Rob's.**

**9D-iv-F2 — the bank holds no role.** K6 says the bank can know the household's money left; the
bank's statement line is where a payment's amount and date come from in practice; under the
role-set the bank is knowing only where it happens to be the payee (the mortgage to Harbor) and
**not_knowing** for a payment from the household's account to Riverbend Hospital — the party whose ledger it
is. Options: **(a) a role for the bank, ruled here in 9B's form** — `drawn_on` (party → payment: *the
payment was drawn on an account the party holds for the payer*; who may assert: the household or the
bank; what it establishes: only that; knowing: `KNOWING_SUBJECT_PARTY`) — added to the payment
role-set, and the holder of `cleared` / `bank_returned_item`; **(b) the bank not_knowing for values** —
K6's positive half unrepresentable, the bank's line a candidate at not_knowing strength until the
household asserts the figure (then knowing by `paid_by`); **(c)** defer `cleared`, `bank_returned_item`
and the bank clause to a later slice, ruling `amount` / `occurred_on` now with the role-set of 9B's
four roles. *Reading:* (a) is the only option that says what K6 says; it is a 9B-class ruling inside
9D-iv (a role, three points), which §9D.9 did not foresee — so it needs your word as such, or (c).
**Rob's.**

**9D-iv-F3 — `occurred_on`: one kind with two permitted subjects, or two kinds.** The consumers read
one catalogue key for both a payment's and an expense's date. The registry permits several subject
slots on one kind (`'subject': (payment, expense)`); G's refusal of the typed-slot merge was about a
cross product of *pairs* (three refused by accident); a value with no object rules exactly two uses.
The role-set differs by subject type, so the relation's table is keyed by (name, subject type).
Two kinds would need two catalogue keys — a consumer change in all four consumers. *Reading:* one
kind, two permitted subjects, the role-set per subject type. **Rob's.**

**9D-iv-F4 — `cleared` and `bank_returned_item` are the bank's stances** on a payment (subject the
payment; content the line / date; `as_of` the date): positions of the bank about a money movement,
never acknowledgment (K6 — 7G reads neither, Dg3). Their holder is F2's answer. The *line* shape
(`cleared` with the bank as subject and the thing a candidate — payment-identity's Pm10 / Pm12 /
Pm13, proposition-concerns) is the borrowed-name class again: refused under the ruled kind, kept
under a stand-in (`bank_line`), no new kind.

**9D-iv-F5 — Kn7, mandatory and permanent, under the ruled kind.** Its first check — *Rob minted the
payment; his claim that it occurred is not knowing* — holds under the role-set (Rob holds no role on
p9: not_knowing — the same answer, now by the relation instead of the foundation). Its second pins
*`occurred_on` not in `RULED_KINDS`* — the exact-absence class, retired. Its third (9B's rewording)
asserts *the mother's knowing for `occurred_on` cannot be derived — undetermined, not manufactured
from her `paid_by` role*; under F1 the mother **is** knowing, by `paid_by` — the payer is first-hand
for the payment's date. That is not manufacturing: it is the ruled relation answering. **A permanent
case's third clause changes; put to Rob by name.** Kn7's meaning — minting ≠ knowing — is untouched.

**9D-iv-F6 — swap classes, pre-measured.** (i) the `cleared` line shape in two fixtures → `bank_line`;
(ii) the `'amount' / 'occurred_on' not registered` pins in 7G, 7I, 7H, 7J and Kn7's; (iii) **no strength
assertion on any value outside Kn7** — the 7E / 7B `date_of_service` and `eob_amount` are stand-ins
of other shapes (a chain case; a line) and stay; map entries for `amount` / `occurred_on` / `cleared`
retire from every fixture that carries them (7G, 7I, 7H, 7J, payment-identity, D, D′, the 9D fixtures).
No presupposed-role additions foreseen: no case asserts a value knowing by type.

### 9D-iv.4 Cases

| # | Case | Kind level (F1 / F2 as read) | Consumer |
|---|---|---|---|
| **Va1 (Pm9 / Kn7)** | the mother: *$300 on July 1* — `paid_by` the mother | knowing (payer); Rob's same claim not_knowing (no role) | `_one_value`: the value; strength unread |
| **Va2** | Rob: *$1,412 on 3/5* on his own payment — `paid_by` Rob | knowing | the same |
| **Va3 (K6 / F2)** | the bank's line *HARBOR MTG 3/5 −1,412.00*, read — payee Harbor, the account at Bank B | Harbor (payee) knowing for amount / date via the reading only if Harbor is the origin — it is not; **Bank B knowing under F2(a) (`drawn_on`), not_knowing under (b)** | candidate; never acknowledgment |
| **Va4** | Rob's spreadsheet line, read (O5) | origin Rob, no role → not_knowing | candidate |
| **Va5** | Riverbend Hospital states the visit's date; Kim incurred it; Rob says a different date | Riverbend Hospital (provider) knowing; Kim (`incurred_by`) knowing; Rob not; `_one_value` → *disputed* | undetermined |
| **Va6 (Pm12)** | a bank line about nothing paid | mints nothing; no value on nothing | — |
| **Va7** | two amounts by the payer at different times | both knowing; `_one_value` → disputed | undetermined (7G: *amount disputed*) |
| **Va8 (F1)** | an `amount` with no `as_of` (every corpus) | knowing by the role-set — undated is the value's normal state | the value |
| **Va9 (F3)** | `occurred_on` on an expense vs on a payment | one kind, two subjects; the set by subject type | one catalogue key |
| **Va10 (F4)** | `cleared` by the bank's utterance (Dg3); by reading | the bank's stance; holder per F2; **7G unchanged: station unmoved** | not read |
| **Va11 (F6-i)** | the bank line with the bank as subject | refused under `cleared`; accepted under `bank_line` | — |
| **Va12 (the 2 × 2 on p)** | origin {the payer, a stranger} × kind {`amount`, `occurred_on`} | (payer, ·) knowing · (stranger, ·) not | — |

### 9D-iv.5 Candidate — pending F1–F3

```text
AMOUNT        subject (subject_payment_id,)                       object ()   knowing_relation KNOWING_ROLE_HOLDER_ON_SUBJECT
OCCURRED_ON   subject (subject_payment_id, subject_expense_id)     object ()   the same                                   (F3)
CLEARED · BANK_RETURNED_ITEM   subject (subject_payment_id,)        object ()   the same, the set {drawn_on}  (F2 a) — or deferred (F2 c)
DRAWN_ON      party -> payment, holds-only, 'role': True, KNOWING_SUBJECT_PARTY                                       (F2 a)
_ROLE_SET = {(KNOWING_ROLE_HOLDER_ON_SUBJECT, 'payment'): (PAID_BY, PAID_TO[, DRAWN_ON]), (…, 'expense'): (PROVIDER_OF, INCURRED_BY)}
    the resolver: knowing iff the claimant has an established holds stance of any role in the set on the claim's subject;
    reading path as 9D-i pinned it; no as_of read (F1); all reading_establishes True
```

Mutations for `s123`: the minter knowing (Kn7 reversed) · the type conferring knowing · the
role-set read at a date (an undated amount undetermined) · a stranger knowing · the bank knowing
without the role (F2 b reversed) / the bank not_knowing with it (a) · `cleared` moving 7G's station
(K6 reversed) · a reading establishing state · the relation composed through the attachment (the
entitled party knowing for the amount) · the two subject types' sets swapped · a second resolver.

### 9D-iv.6 Ruling sought

> **(1) F1:** the role-set relation, undated, read on the roles' established holds stances — the
> second and last new relation shape. **(2) F2:** the bank — a `drawn_on` role ruled here in 9B's
> form and added to the payment set (a), not_knowing (b), or the bank's kinds deferred (c). **(3)
> F3:** `occurred_on` one kind with two permitted subjects. **(4) F4:** `cleared` / `bank_returned_item`
> the bank's stances, the line shape renamed. **(5) F5:** Kn7's third clause — the mother knowing by
> `paid_by` — accepted as the ruled relation's answer, the permanent case's meaning intact. **(6) F6:**
> the swap classes. Nothing here authorises code.

---

### 9D-iv.7 Ruling — Rob, 2026-09-20: F1–F5 RULED; F6 RULED on its clarified text; no code by this ruling

**F1 — the role-set relation, undated.** A value is a fact about the thing, not a position; the
relation is *the claimant holds any of a set of roles on the claim's subject*, read on the roles'
**established holds stances**, not at a date the value does not carry. The set per subject type: a
payment → {`paid_by`, `paid_to`, `drawn_on`}; an expense → {`provider_of`, `incurred_by`}. The
second and last new relation shape; the role-at-date relation untouched.

**F2 (a) — `drawn_on`, a role ruled here in 9B's form.** *K6 does not merely say a bank statement
happens to contain useful information; it says the bank can know that the household's money left.
If the role-set is the mechanism for establishing first-handness, the ontology needs a role that
actually expresses that bank / payment relation.* **`drawn_on` is a role held by the bank in respect
of the payment, and belongs in the payment role-set.** Party → payment, holds-only, `'role': True`;
on 9B's three points — **who may assert:** the household, or the bank as a party (a statement line
read → a candidate); **what it establishes:** only that the payment was drawn on an account the
party holds for the payer — not the amount, not the date, not clearance, not acknowledgment (K6);
**who is knowing:** the subject party, `KNOWING_SUBJECT_PARTY` (Kn12 stands). **The holder of
`cleared` and `bank_returned_item`.** *This does not silently reinterpret the role-set relation; it
establishes the missing role K6's stated knowing case needs.* Not (b): the bank `not_knowing` would
leave K6's positive first-hand assertion unexplained. Not (c): `cleared` is not deferred merely to
avoid settling the role that accounts for the bank's knowledge.

> **A cross-slice dependency, recorded explicitly rather than pretended anticipated:** §9D.9 did not
> foresee a 9B-class role ruling inside 9D-iv. That it is necessary here is itself part of the record —
> **9D-iv has exposed a role required by an existing provenance ruling (K6).** The value provenance
> model requires `drawn_on` to account for the bank's knowledge; that is an explicit dependency of
> 9D-iv on a role, not something hidden inside its implementation.

**F3 — `occurred_on` one kind with two permitted subjects** (payment, expense); the role-set keyed by
the subject's type; one catalogue key, no consumer changes.

**F4 — `cleared` and `bank_returned_item` are the bank's stances** on a payment (subject the payment;
content the line / date; `as_of` the date), holder `drawn_on`; never acknowledgment (K6 — 7G reads
neither). The bank-line shape (the bank as subject, the thing a candidate) refused under the ruled
names and kept under a stand-in — the borrowed-name class.

**F5 — Kn7, permanent, accepted including the changed third clause.** The minter remains
`not_knowing` — now because the relation does not give the minter that status. The mother's knowing
can no longer be described as something that *cannot be derived*: under F1 she is first-hand through
`paid_by`. *The relation answers why the mother is first-hand; it does not manufacture a knowing
fact.* The named permanent change accepted: from *the mother's knowing cannot be derived* to the
formulation the role-set semantics requires.

**F6 — RULED, on its clarified text: a corpus / build-scope question, not an ontology question.
All three classes accepted as the permitted corpus corrections.** (1) *The borrowed line shape:* the
`cleared` line in the two fixtures corrected to `bank_line` — a correction of the fixture's asserted
shape, not a new ontology rule. (2) *The exact-absence pins:* the `'amount' / 'occurred_on' not
registered` pins in 7G, 7I, 7H, 7J and Kn7 restated against the now-ruled registration — those values
are registered kinds, so the old absence assertions retire. (3) *Strength / map:* no value consumer
asserts strength outside Kn7; 7E / 7B's `date_of_service` and `eob_amount` are explicitly different
stand-in shapes and remain untouched; map entries for `amount`, `occurred_on` and `cleared` retire
from the fixtures that carry them. **The scope fence: no presupposed-role additions are authorised by
F6** — it authorises only the measured corpus corrections and smuggles no role into the ontology.

| | Ruling |
|---|---|
| **F1** | the role-set relation is undated; reads established holds stances |
| **F2** | `drawn_on` is the bank role K6 requires and belongs in the payment role-set |
| **F3** | one `occurred_on` kind with two permitted subjects |
| **F4** | `cleared` / `bank_returned_item` are bank stances; the bank line a borrowed fixture shape |
| **F5** | Kn7 accepted; the minter `not_knowing`; the mother's knowing first-hand via `paid_by` |
| **F6** | three measured corpus-correction classes accepted; no presupposed-role additions |

**The cross-slice finding stands exactly as amended — 9D-iv exposed a role required by an existing
provenance ruling — and is not retroactively attributed to §9D.9.**

**No code.** The next authorisation is the explicit *build 9D-iv*.

---

#### Built — 2026-09-20 (9D-iv)

`core/database.py`: five registry entries — `AMOUNT` (a payment), **`OCCURRED_ON` with two permitted
subjects** (a payment, an expense — F3), `CLEARED`, `BANK_RETURNED_ITEM` (the bank's stances on a
payment), all `KNOWING_ROLE_HOLDER_ON_SUBJECT`, `reading_establishes True`; and **`DRAWN_ON`**, the bank's
role in 9B's exact shape (party → payment, holds-only, `'role': True`, `KNOWING_SUBJECT_PARTY`) — the
tenth role, the cross-slice dependency K6 required. **The role-set relation, written once:**
`_ROLE_SET = {'payment': (paid_by, paid_to, drawn_on), 'expense': (provider_of, incurred_by)}` keyed by
the subject's identity type; `_role_holder_on_subject(session, prop, claimant)` — knowing iff the
claimant (or its referent) holds an **established holds stance** of any role in the set on the claim's
own subject; not_knowing otherwise; undetermined with no claimant or no subject; **undated — no
`as_of` read, no `in_effect`** (a value is a fact about the thing); the eighth entry in
`_KNOWING_RELATIONS`, its own dispatch line. The role-at-date relation untouched. **The whole
non-comment diff:** six constants, five entries, the table, the resolver, one dispatch line.
`_one_value`, every consumer, `reach`, `_claim_states`: untouched.

**The oracle:** `tests/test_value_kinds_fixture.py` — 18 checks over Va1–Va12, the registry, and
`drawn_on` on 9B's three points, with a map carrying no entry for any 9D-iv kind: **who may assert**
(the household — established, not knowing, the subject party is the bank; the bank — knowing for its
own role; the statement line read — a candidate, a reading never establishes a role); **what it
establishes** (only that — no amount, date, clearance or acknowledgment claim exists or is minted by
it; the snapshot unchanged); **who is knowing** (the subject party); the registry's refusals (a
payment-subject `drawn_on`; no `drawn_on_began` / `_ended`). **Va2 / Va8** (Rob's own payment —
knowing by `paid_by` for an amount that is **undated, the value's normal state**); **Va3 (K6 / F2)**
(the bank's statement line read: amount, date and cleared **candidates in state, knowing in
strength** — the origin holds `drawn_on`; 7G's value Rob's established one, the reading listed as a
candidate, the station unmoved); Va4 (Rob's spreadsheet read → knowing — Rob is the payer; a
stranger's document → not_knowing); **Va12 the 2 × 2 on p** (the payer knowing for both, a stranger
for neither — the type test had called an institution knowing and a person not); Va7 (two amounts by
the payer → both knowing; `_one_value` → *disputed*; 7G's amount undetermined with the reason — the
relation grades who may know, the consumer never chooses); **the composition fence** (Harbor knowing
for p's amount as payee; on a payment paid to the servicer and *attached to O where Harbor is entitled*,
Harbor not_knowing — the entitled-party role is not in the set and is not reached through the
attachment); **Va1 (Kn7)** (Rob the minter not_knowing; the mother not_knowing until her `paid_by` is
in the record, then knowing — the relation answers why, manufactures nothing); Va5 / Va9 (the
expense's date: Riverbend Hospital and Kim knowing by their roles, Rob not; the same kind as a payment's date, the
set by subject type; Rob's different date → disputed); Va9 (`occurred_on` refuses an obligation
subject); **Va10** (the bank knowing through `drawn_on`; Rob's *it cleared* knowing through
`paid_by` — **the bank line is an evidence shape, never a role or a knowing source**; **7G's station
unmoved**); Va6 (a line about nothing paid: no subject, refused); Va11
(the bank line with the bank as subject refused under `cleared` / `amount`, accepted under `bank_line`).

**The substitution — F6's three classes, confirmed by the substrate run before the fixture was
written, and one interaction:** 7G 40/40, 7I 30/30, 7H 32/32, 7J 31/31 with their map entries for
`amount` / `occurred_on` / `cleared` retired, helpers by constant, the *no value kind registered*
absences retired (7G's and 7J's fixtures now say every kind they read is ruled); D and D′'s `cleared`
by constant; the three 9D stance fixtures' map entries retired. **F6(1):** the bank line under `cleared`
in payment-identity (three sites) and Ab7 → `bank_line`, no new kind; `s94`'s *bank line mints a
payment* mutation follows the rename. **F6(2):** the exact pins — 7G / 7I / 7H / 7J's absences; Kn7's
*`occurred_on` not in the registry*; the relational-knowing and role-catalogue counts (seven → eight
names); **the role-set pins** in the 9B fixture, item 5's and `s118` (*exactly nine roles* → ten, `s118`
restated to 9B's own nine as a subset); payment-identity's subject-slot set (the value kinds and the
bank's stances now sit on it). **F6(3):** no strength assertion on a value outside Kn7; `date_of_service`
and `eob_amount` untouched. **Kn7 and Va1 are intentionally different fixtures — F5's distinction made
executable, not a contradiction:** **Kn7 retains its no-presupposed-role corpus** — the mother asserts
the date, no `paid_by` claim for her exists there, and F6 authorises no presupposed-role additions —
**and therefore remains `not_knowing`**; **Va1 separately proves that an explicitly established
`paid_by` relation makes the mother's value knowing** (not_knowing before the role claim, knowing
after it). The relation answers *why* she is first-hand and manufactures nothing from her utterance.
**Kn7 must not later be "fixed" by adding `paid_by` merely to make an assertion pass** — its
not_knowing is the correct answer for the record it holds. Both rulings kept; the interaction
recorded, not resolved by adding the role. `s97`'s Kn7 mutation, which had registered a stand-in `occurred_on`
and popped it on restore, now replaces the ruled entry's relation and restores it — mutation plumbing.

**Smoke `s123_value_kinds.py`:** the fixture passes; ten mutations — the minter knowing (Kn7
reversed) · the type conferring knowing · the role-set read at a date (an undated amount undetermined)
· a stranger knowing · **the bank without its role** (`drawn_on` dropped from the set — F2 reversed) ·
`cleared` moving 7G's station (K6 reversed) · a reading establishing state · **the attachment
composing** (the entitled party in the set) · the two subject types' sets swapped · a second resolver —
all caught; two on the second run, after two fixture gaps closed: Va3 had asserted the reading's
strength but not its **state** (7G's value was the same either way), and the composition fence had
used a payment attached to nothing — a real negative case (attached to O, paid to the servicer,
Harbor entitled) put in its place.

**Left where it belongs:** the determination (9D-v) · candidate generation (the bank line's own
kind, when it has one) · 9D-i-F3 (7G). No schema, no migration. Gate 1478 → 1501, 0 failed.

#### Accepted — Rob, 2026-09-20 (9D-iv)

Accepted on the gate's evidence (1501 / 0, s123 23/23) and the build's fidelity to §9D-iv.7: the
role-set relation undated and separate from the role-at-date resolver; `drawn_on` in 9B's established
role form, no special 9D representation; F6's corrections mechanical and within scope; the exact-set
sweep by role names with both enumerations carrying the tenth role; Kn7 and Va1 recorded as
intentionally different fixtures — Kn7's `not_knowing` the correct answer for the record it holds, Va1
the proof that an established `paid_by` makes the value knowing — and the warning against "fixing"
Kn7; the bank line an evidence shape, never a role or a knowing source; the two mutation-plumbing
fixes (s94, s97) not an expansion of the ontology. **9D-v — the determination — remains unopened until
Rob opens it; it is the last slice of 9D and of item 9.**

---

## Pass 9D-v — The determination

*Opened by Rob 2026-09-20 after 9D-iv's acceptance (`21142c1`). Scope per §9D.9: `determination` —
F5 only; the determination remains undetermined; consumer 7H. The last slice of 9D and of item 9. No
code until cases → candidate → ruling → explicit build authorisation. The smallest slice: one kind, one
consumer, and its knowing already ruled — what remains is the shape, the reading path, and whether
anything the record says about who may determine belongs on the kind.*

### 9D-v.1 What is fixed

**7H §7H.7 item 2 (ruled):** kind `determination`; subject X; `as_of` **required** — the date the
determination is about; content **exactly one of four names** (`provider_adjustment · user_paid_cash ·
unpaid · pending_claim`), any other *unrecognised* and never current (C7: *one of these or not at all*);
**established = utterance-sourced and unretracted; reading-sourced → candidate (a parser determines
nothing); retracted → contested**; **who may make it: any party** under the ordinary discipline — the
household (D12), the provider, the insurer; *whether a party's role constrains its determination is
the catalogue's to rule* — 7H reports the asserter's roles as facts and constrains nothing; *current*
by G per party's series, cross-party conflict → none, superseded never overwritten; `unresolved = 0` is
not `user_paid_cash`; no determination is not `unpaid`; a denial is not `pending_claim` (Rc6 — `denial`
its own kind since 9D-ii). **9D-F5 (ruled §9D.9 / §9D-ii.7's context):** the determination's knowing is
**undetermined by design** — no relation named; a determination is a party's reading of the
situation, not a position it holds first-hand; *the asserter is first-hand for its own
determination* was rejected as saying nothing. **The four names stay 7H's** (§2.3: content is opaque
to the catalogue).

### 9D-v.2 What 7H reads

`_claim_entries(catalogue['determination'], subject_expense_id ∈ members)`; per relationship: state
by evidence type; `name` = content if in `DETERMINATION_NAMES` else *unrecognised*; the asserter's
`provider_of` / `insurer_of` answers on X **reported as facts**; qualifies iff established ∧ recognised
∧ dated ≤ d ∧ an asserter; current per party's series by latest `as_of`; two parties' currents differ
→ conflict, none current. **Strength is never read.** The shape in the 7H fixture: subject X,
content the name, `as_of`, by utterance (any party) or by reading (a candidate). No borrowed shape
anywhere; no other fixture asserts a determination.

### 9D-v.3 Findings — put to Rob

**9D-v-F1 — `reading_establishes`: False.** 7H ruled *a parser determines nothing* — a reading-sourced
determination is a candidate and never current. Under 9D-i's pin the flag governs only
strength-through-origin, and with **no knowing relation** the strength is undetermined on every path
regardless — so the flag is inert for this kind's strength. It is ruled `False` to say what 7H says
(*a reading never establishes a determination*) rather than `True` to say nothing. The state axis is
unchanged either way (`_claim_states`). *Reading:* False. **Rob's.**

**9D-v-F2 — no role on the kind; nothing about who may determine.** 7H left *whether a party's role
constrains its determination* to the catalogue. 9D-v's answer: **the kind carries no role and no
asserter constraint** — any party may determine (D12 the household; the provider; the insurer); the
roles are 7H's to report as facts. This is not an omission: a determination is not a position a
role-holder has first-hand (there is no *determiner_of* role and none is invented), which is exactly
why its knowing is undetermined by design — the parallel with `under_plan` (F: undetermined). If a
later consumer needs a role gate on determinations, that is its own ruling, not the kind's. *Reading:*
so. **Rob's.**

**9D-v-F3 — swap classes, pre-measured.** (i) 7H's fixture: the catalogue line already names the ruled
name; its `'determination' not in shipped` pin retires; its map entry retires. (ii) 7J's and the 9D-ii
fixture's map entries for `determination` retire. (iii) The payment-in-respect-of fixture pins
`not hasattr(db, 'determination')` — a **module-attribute** absence (no *helper* named determination);
the constant is `DETERMINATION`, so the pin stands and still says what it meant. (iv) `s115`'s
mutations name the kind by string — the same name. No borrowed shape; no presupposed-role addition
(there is no role). **The build's corpus touches are (i) and (ii) only.**

### 9D-v.4 Cases

| # | Case | Kind level | 7H |
|---|---|---|---|
| **De1 (D12)** | Rob: *user_paid_cash* on X, 3/20 | established; **knowing undetermined** | current for Rob's series |
| **De2** | Riverbend Hospital: *provider_adjustment* on X, 3/15 | established; undetermined | current for Riverbend Hospital's series |
| **De3 (Rc15)** | Rob and Riverbend Hospital current, different names | both undetermined | cross-party conflict → none current, both listed |
| **De4 (Rc6 / C7)** | Lakeview Health: *denied* as a determination's content | established; undetermined | **unrecognised**, never current; the denial is `denial`'s kind, not this one |
| **De5** | the EOB's *pending* read | **candidate**; undetermined (reading_establishes False) | never current |
| **De6 (Rc15)** | Rob retracts his latest; the prior stands | contested; the prior established | the prior current again |
| **De7 (F7 / 7H)** | an undated determination | accepted by the registry; undetermined | disqualified — `as_of` required by 7H |
| **De8 — the 2 × 2 collapses** | origin {Rob, Riverbend Hospital, Lakeview Health} × content {four names} | **every cell undetermined** — no relation, no role; the asserter's roles reported, constraining nothing | the series are per party |
| **De9** | a party-subject or an obligation-subject determination | refused by the registry (subject X only) | — |
| **De10 (Rc19)** | `unresolved = 0` with no determination | no claim → nothing | current None — zero is not a determination |
| **De11 (§2.3)** | content *paid in full* — not one of the four | the kind accepts any content (opaque) | unrecognised; the vocabulary is 7H's |

### 9D-v.5 Candidate

```text
DETERMINATION   subject (subject_expense_id,)  object ()
                symmetric False · reading_establishes False · relational_knowing True · no knowing_relation · no role · no boundary
```

One entry; no relation, no table row, no resolver change; `_KNOWING_RELATIONS` unchanged (eight).
The swap: 7H's pin and map entry; 7J's and 9D-ii's map entries; the 7H fixture's helper by constant;
31/31 · 32/32 unchanged otherwise. Mutations for `s124`: a knowing relation designated for the
determination (the asserter first-hand) · a reading establishing a determination · a role gate on the
kind (only the insurer may determine) · the four names enforced by the registry (content parsed) · a
denial accepted as a determination · a determination minted from `unresolved = 0` · the type
conferring knowing · an undated determination current · a `determiner_of` role appearing · a second
resolver.

### 9D-v.6 Ruling sought

> **(1) F1:** `reading_establishes False` — a reading never establishes a determination. **(2) F2:**
> no role on the kind, no asserter constraint; knowing undetermined by design, as ruled. **(3) F3:** the
> two corpus classes accepted. Nothing here authorises code. **After 9D-v's build and acceptance the
> inventory of §1 is complete — every stand-in a ruled kind — and item 9 can close; closing it is
> Rob's word, not this slice's.**

---

### 9D-v.7 Ruling — Rob, 2026-09-20: F1–F3 RULED as read; no code by this ruling

**F1 — `reading_establishes False`.** A reading never establishes a determination — a parser
determines nothing (7H). With no knowing relation the flag is inert for strength; it is ruled to say
what 7H says.

**F2 — no role on the kind, no asserter constraint.** Any party may determine; 7H reports the
asserter's roles as facts and constrains nothing; no `determiner_of` role is invented; the
determination's knowing is undetermined by design — a party's reading of the situation, not a
first-hand position (the parallel with `under_plan`). A role gate, if a consumer ever needs one, is
that consumer's own ruling, never the kind's.

**F3 — the two corpus classes accepted:** 7H's `'determination' not in shipped` pin and map entry;
7J's and the 9D-ii fixture's map entries. No borrowed shape; no presupposed-role addition (there is
no role).

**The entry:** `DETERMINATION` — subject `(subject_expense_id,)`, object `()`, `symmetric False ·
reading_establishes False · relational_knowing True`, no `knowing_relation`, no `role`, no boundary.
No relation, no table row, no resolver change.

**No code.** The build awaits its separate authorisation.

---

#### Built — 2026-09-20 (9D-v)

`core/database.py`: `DETERMINATION` — one registry entry exactly as §9D-v.7 froze it: the expense the
subject, no object, `symmetric False · reading_establishes False · relational_knowing True`, **no
`knowing_relation`, no `'role'`, no boundary** — knowing undetermined by design. No relation, no table
row, no resolver change; `_KNOWING_RELATIONS` still eight. One comment block states what a
determination is (a party's reading of the situation about X), that any party may determine with
no role on the kind and no `determiner_of` invented, that the four names are 7H's and opaque here,
that a parser determines nothing, and that with this entry **every stand-in of §1 is a ruled kind.**
**The whole non-comment diff: one constant, one entry.**

**The oracle:** `tests/test_determination_fixture.py` — 14 checks over De1–De11 and the registry, with a
map carrying no entry for the determination: the entry as frozen; no relation added, no determiner
role, the four names **not** enforced by the registry (content opaque — *anything at all* accepted);
De9 (a party- or obligation-subject determination refused); **the inventory check** (every one of §1's
stand-ins — ten roles, E's three, the stances, the terms, the values, the bank's stances, the
determination — is in `RULED_KINDS`); De1 (Rob's `user_paid_cash` established, **undetermined**; 7H
current for his series, his roles reported as facts); De2 (Riverbend Hospital's `provider_adjustment` undetermined
too — the provider is not first-hand for a reading of the situation); De3 (their currents differ → 7H
conflict, none current — the kind ranks no party); **De8 — the 2 × 2 collapses**: three asserters ×
four names, twelve cells, **every one undetermined** (the type test had graded them by institution);
De4 (*denied* as content accepted by the kind, **unrecognised** by 7H, never current — the denial is
`denial`'s kind); De5 (the EOB's *pending* read → a candidate, never current); De6 (retraction contests
the latest, the prior current again); De7 (undated — accepted by the registry, disqualified by 7H);
De10 (no determination → current None, nothing manufactured from a zero unresolved); De11 (*paid in
full* accepted by the kind, unrecognised by 7H — the vocabulary is 7H's).

**The substitution — F3's two classes, and nothing else:** every fixture green on the first substrate
run — 7H 32/32 with its `'determination' not in shipped` pin and its map entry retired and its helper
by constant; 7J's and the 9D-ii fixture's map entries retired (and 7J's `amount` / `occurred_on`
entries, missed by 9D-iv's sweep, retired with them). No borrowed shape; no presupposed role; the
payment-in-respect-of fixture's `not hasattr(db, 'determination')` stands (the constant is uppercase).

**Smoke `s124_determination.py`:** the fixture passes; ten mutations — a knowing relation designated
(the asserter first-hand) · a reading establishing a determination · a role gate on the kind (only
the insurer determines) · the four names enforced by the registry · a denial accepted as a
determination · a determination minted from `unresolved = 0` · the type conferring knowing · an
undated determination current · a `determiner_of` role appearing · a second resolver — **all ten
caught on the first run.**

**Left where it belongs:** a role gate on determinations (a consumer's own ruling, if ever) · the
four-name vocabulary (7H's) · 9D-i-F3 (7G) · D′.11. No schema, no migration. Gate 1501 → 1524,
0 failed. **With 9D-v's acceptance the §1 inventory is complete; closing item 9 is Rob's word.**

#### Accepted — Rob, 2026-09-20 (9D-v)

Accepted as built and ruled: `1e646fb`, 1524 / 0, the 23 new checks and all ten mutation checks in
s124. The implementation matches the ruling exactly — one constant, one entry; no relation, no role,
no boundary, no resolver change; `_KNOWING_RELATIONS` still eight; all twelve cells of the 2 × 2
collapse to undetermined; every §1 stand-in represented in `RULED_KINDS`. **The §1 inventory is
complete: every stand-in has been converted from an implementation candidate into a ruled kind.**

---

## Item 9 — closed

**Rob, 2026-09-20.** Four passes and five slices, each opened to a semantic surface before a line
was written, each ruled from cases, each built to exactly its ruling, each proved by the same
executable test — *the consumer fixtures re-run with the ruled kind in place of the stand-in and no
other change* — and each accepted on a green gate:

```text
9A     under_plan + began / ended                                           e8fecdd   F built as accepted
9B     entitled_party_of · servicer_of (+ bounds) · provider_of · insurer_of ·
       insurer_of_plan · incurred_by · paid_by · paid_to                    9c53879   the role catalogue; KNOWING_SUBJECT_PARTY; 'role': True
9C     expense / obligation / payment _in_respect_of_plan                    cdb7cda   E built as accepted, per G.9
9D-i   acknowledged · balance · returned                                    d793472   the mixed holder shape; the role-at-date relation, ruled once;
                                                                                      reading_establishes = strength through the origin, never state
9D-ii  billed · patient_responsibility · plan_paid · applied_to_deductible ·
       denial · adjudication                                                cb8ebe4   the relation applied on X; two kinds by name (C7)
9D-iii deductible · individual_deductible · plan_year · deductible_applied ·
       individual_deductible_applied · eligibility · coverage_ended ·
       authorization                                                        fe15f5f   applied on P; the side read on the object (application, not re-ruling)
9D-iv  amount · occurred_on · cleared · bank_returned_item · drawn_on       86b85d5   the role-set relation, undated; the bank's role K6 required
9D-v   determination                                                        1e646fb   undetermined by design; no role; the four names 7H's
```

Thirty-five ruled kinds where there were stand-ins; ten roles; eight named knowing relations —
three designated-participant, four role-at-date on one resolver, one role-set — and no generic
resolver; no consumer changed shape (the two consumer lines the record names — Tr8's assertion and
7J's second catalogue key — were each ruled before they were written). Every fixture's foundation map
now carries only what is still unruled by relation: `artefact_origin`'s own entry. Gate 1350 → 1524.

**What this closure does not close — carried forward explicitly, not resolved by the inventory's
completion:**

- **9D-i-F3** — 7G's *per-relationship* discharge (state and strength tested on one evidentiary
  relationship) versus §7G.3's Dg2 wording (*Rob asserts that is Harbor acknowledging p; established,
  strength via the reading → discharged*); K1-with-acceptance does not discharge in built 7G. **7G's,
  to be opened explicitly.**
- **7J's any-party term read** (9D-iii F4) — the kind's holder is the insurer; 7J reads the latest
  established term by any party and reads no strength. **7J's.**
- **K2's balance half in 7G** (9D-i) — the servicer's balance statement cannot enter E's series;
  a consumer with O in hand may evaluate it. **7G's.**
- **The bank line's own kind** — a reading-line proposition whose subject is the party and whose
  thing is a candidate (`statement_figure`, `eob_amount`, `sbc_line_figure`, `bank_line` stay
  fixture stand-ins); **candidate generation remains open** (the matcher, the importer contract).
- **D′.11** — composition across relation kinds — **unsettled**; every slice added evidence and
  refused a composition (the acknowledgment's O; the value's role-set; the plan gate) without a
  doctrine.

*Closing item 9 closes the inventory / ruling exercise; the questions above are carried forward by
name, not by silence.*
