# From stand-ins to ruled kinds — item 9

> Status: **Queue item 9, opened by Rob 2026-09-19 after item 7 closed 7A–7J.** Every consumer from
> 7F onward runs on kinds a fixture registers and removes; this item turns them into ruled kinds —
> F's `under_plan` (accepted, unbuilt), the role catalogue (unruled), E's three plan relations
> (accepted, unbuilt) and the stance / value catalogue (a domain question the record deferred) —
> **without changing any consumer's shape.** Four passes in that order (§3). **Pass 9A — F's build —
> opened and run to a candidate (§9A); no code.**

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
