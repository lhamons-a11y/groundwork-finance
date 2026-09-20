# From stand-ins to ruled kinds — item 9

> Status: **Queue item 9, opened by Rob 2026-09-19 after item 7 closed 7A–7J.** Every consumer from
> 7F onward runs on kinds a fixture registers and removes; this item turns them into ruled kinds —
> F's `under_plan` (accepted, unbuilt), the role catalogue (unruled), E's three plan relations
> (accepted, unbuilt) and the stance / value catalogue (a domain question the record deferred) —
> **without changing any consumer's shape.** Four passes in that order (§3). **9A built and accepted
> (`e8fecdd`); 9B ruled (§9B.7), built (`9c53879`) and ACCEPTED (Rob, 2026-09-19); **9C opened
> (§9C) — E's three plan relations; one finding (9C-F1, Tr8's refusal-by-name) and a build
> authorisation sought; no code.**

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
