# Party reference — the relational shape

> Status: **Design mode, 2026-09-12. The first record allowed to touch schema — as a
> representation question only. No migration, no code, no decision on institution
> correspondence, external ids, or whether `Person` is extended.** Rob's question:
>
> > **How should Groundwork represent one usable party reference that can refer to either a
> > household-declared `Person` or a Groundwork-minted institution, while preserving the fact
> > that these identities have different epistemic foundations?**
>
> **The constraint:** *one reference is not one ontology.* Rejected on sight: a bare `party_id`
> under which `Person 42` and `Institution 42` are indistinguishable at the semantic layer. Also
> rejected: forcing every consumer to know `Person`-or-institution before it can say
> `origin_party = ?`, `role.subject = ?`, `correspondence.party = ?` — the whole reason for one
> reference is to give relationships a common target.
>
> **The hard review invariant, written before scoring** (the schema analogue of the artefact
> ruling):
>
> > **A party reference is a referential mechanism, not evidence of party identity.** A foreign
> > key establishes *this relation points to Party X*. It must not silently establish *Party X
> > is the same as the entity described by Y* — that still requires correspondence evidence.
>
> **The fourth test, added to T-A…T-D:**
>
> > **T-E — reference integrity.** Can every relationship that requires a party target refer to
> > exactly one party through a stable database-level reference, without requiring consumers
> > to reconstruct identity from type, role, name, or external identifier?
>
> **Evidence admitted:** the existing schema and its constraints. Candidates are tested against
> the actual relationships — origin · role · mediation · correspondence · lineage ·
> independence — and the nasty cases, not invented features.

---

## 0. What the schema already says — constraints as evidence

Four facts from `core/database.py`, each bearing on a candidate:

1. **The project has already rejected polymorphic `(entity_type, entity_id)` pairs, with the
   reason written down.** `HistorianEntry`: *"One foreign key per referable entity… Sprawl is
   the price of enforceability, and this project has consistently paid it: a polymorphic
   (entity_type, entity_id) pair avoids the nullable columns and gives up referential
   integrity, which is precisely the defect already visible in the `entry_id` values written
   into `context_json` with nothing to enforce them."* And the substrate rule
   (`EVENT_SUBSTRATE_QUESTION.md`): every structural relationship in a foreign key or a link
   table. **Candidate A is contrary to a reasoned, standing convention. Candidate D *is* the
   convention.**
2. **Correspondence-as-assertion already exists for `Person`.** `PersonAlias`: *"`patient =
   "ROB L."` is a string a billing system chose; it becomes identity only when a person says
   so. John and John Jr. are why a near-match may never be a match."* The household-declared
   branch already has exactly the artefact ruling's shape — an external string is evidence for
   a correspondence the household asserts; it is never the identity. Whatever shape is chosen
   must leave this untouched.
3. **Dated relations over parties already exist.** `PersonAssignment` (mode · seq · reason ·
   source · recorded_at, superseding rather than overwriting) and `PersonEnrolment`
   (effective_on) are the role pattern the ruling requires — *a relation, dated, over a party
   and a thing*. The role rule is already the schema's habit for persons.
4. **There is no institution entity.** Institutions are strings: `Account.institution`,
   `PdfExtractCache.issuer`, `DebtAccount.name`. The minted branch has nowhere to be minted.
   And — worth stating — the engine sets no `PRAGMA foreign_keys=ON`, so SQLite's FK
   enforcement is nominal today; T-E is about the *shape* being enforceable, and enforcement
   is a wiring condition beside it.

---

## 1. A finding that precedes the candidates — the four states are not nullability

Every candidate below has to encode *established A · established B · not established · no
party*. A nullable reference gives two values: pointing, or null. **No candidate can encode the
four states in the reference column alone**, and trying to is the `PARTY_ID = NULL` collapse
the ruling names. So, independent of A–D:

> **Wherever a relation carries a party reference that may be unestablished, the relation
> carries a separate *party state* beside it — `established · not_established · no_party` —
> and the reference is populated iff the state is *established*.** *No party* is a positive
> value of the state, never a null. *Not established* may carry candidates in a separate
> candidate relation; it never carries a placeholder party.

This is not a kind tag: it says nothing about *what kind* of party, only *whether one is
established*. Consumers read the state to know whether to read the reference; they never read
a kind to decide what the party is.

---

## 2. The candidates, against the relationships and the nasty cases

The relationships that need a party target, and how many targets each carries:

```text
origin           artefact → party                            1 target
role             party → obligation/plan, dated               1 target (+ the thing)
mediation        party → party, asserted, dated               2 targets
correspondence   party ~ party, asserted, with strength       2 targets
lineage          derived: walks origin + mediation             0 stored
independence     derived: compares origins                    0 stored
```

### A — polymorphic `(party_kind, party_id)`

| | |
|---|---|
| T-E | **fails.** No FK can target two tables; integrity is procedural. The project's own recorded reason for rejecting the pattern (§0.1). |
| one reference ≠ one ontology | `party_kind` preserves the distinction — **as a tag consumers switch on**, which is source-enum thinking one level up. The two foundations become two *values* of one field rather than two *anchors*. |
| nasty cases | all *representable*: any (kind, id) can be written — which is the problem; nothing prevents `(INSTITUTION, 42)` pointing at nothing. |
| verdict | **rejected** — on the schema's own evidence and on the ontology constraint. |

### D — separate foreign-key columns, exactly one populated

| | |
|---|---|
| T-E | **passes per column**: `person_id → people.id`, `institution_id → institutions.id`, a CHECK that exactly one is non-null (SQLite supports CHECK). Enforceable. |
| one reference ≠ one ontology | **over-preserved.** The two foundations are structurally distinct at every relation site — but there is no common target: nothing can FK to "a party". The common concept is a CHECK plus a convention, i.e. procedural. |
| relationships | origin: 2 columns. role: 2. **mediation and correspondence: 4 columns each** (two ends × two kinds), with CHECKs on both ends. Correspondence between a Person and an institution is structurally impossible — **correct** by the ruling, and D gets it for free. |
| nasty cases | P→A→P: role rows over `(person_id=P)`… wait — **P is the provider, an institution**; the entitled party is `(institution_id=P)`; fine. EOB1/2→A, EOB3→B: fine. "Lakeview Health"≠"AETNA INC": two institution rows unless corresponded: fine. Not established / no party: §1's state column, both FKs null: fine. |
| cost | every relation table carries the party abstraction twice; adding a third foundation (there is none, and none is foreseen) would touch every relation. The project's convention accepted this sprawl for referable *entities*; here the sprawl is for two *foundations of one concept*, which is the case the convention did not anticipate. |
| verdict | **passes every test; fails the requirement's purpose** — there is no usable common reference. Runner-up. |

### C — a reference/association object over the two domains

| | |
|---|---|
| shape | `party_references(id, person_id → people, institution_id → institutions)`; relations FK to `party_references.id`. |
| the crucial question | *is the reference merely a handle, or has it become a third identity?* **It depends on one constraint.** If `person_id` and `institution_id` are each UNIQUE (at most one reference row per person, per institution), a reference row is 1:1 with its anchor and is exactly **B's party row under another name.** If they are not unique, two reference rows can denote one person, and "are these two references the same party?" is a new correspondence question about a thing that is not an identity — **Rob's third-identity trap, precisely.** |
| verdict | **collapses into B with uniqueness; fails without it.** Not a distinct candidate. |

### B — a common `Party` identity, with the two foundations as *anchors*, not subtypes

| | |
|---|---|
| shape | `parties(id)` — the reference. **Household branch:** a party row is created *with* its `Person`, 1:1, `parties.person_id → people.id UNIQUE NOT NULL` for that branch; the link is **structural, carries no source, no strength, no supersession, and is never a claim** — it is the declaration's own identity seen from the reference layer. **Institution branch:** the party row *is* the minted identity; `institutions(party_id → parties.id UNIQUE)` holds what Groundwork knows about it (name as first seen, and later correspondence evidence — outside this record). A CHECK: each party row has exactly one anchor. |
| the dangerous question — *does `Party` turn `Person` into a correspondence-established identity?* | **No, and here is the demonstration rather than the assertion.** Correspondence is a relation with a source and a strength that can be asserted, contested, superseded. The person-branch link has **none of those properties by construction**: it is created in the same transaction as the `Person`, it cannot be re-pointed (UNIQUE, NOT NULL on the branch), and no table exists in which *party 7 corresponds to person 42* could be stated as a claim. A thing that cannot be asserted, weighed, or withdrawn is not evidence; it is structure. The Person's party identity is therefore *derived from the declaration by construction* — the fixed point, encoded. |
| one reference ≠ one ontology | **preserved structurally.** Which foundation a party has is answered by *which anchor table it joins to*, not by a kind consumers switch on. A `kind` column may exist **only as an integrity aid** (to write the exactly-one-anchor CHECK); consumers of relations never need it — `origin_party = 7` is complete, and *who 7 is* is a join, not a branch. |
| T-E | **passes.** Every relation carries one FK to `parties.id`. Mediation and correspondence carry two. Enforceable. |
| relationships | origin: 1 column. role: 1. mediation: 2. correspondence: 2, **and correspondence between a Person-anchored party and an institution-anchored party must be refused** — a CHECK or a guard on the correspondence relation, since B does not get this for free the way D does. Recorded as the one place B needs a rule D needs none. |
| nasty cases | P→A entitled / not / entitled: three dated role rows, `party=P`, one party ✓. EOB1, EOB2 → A: `artefact.origin_party = A` twice, one party ✓ (DI). EOB3 → B: a different party ✓ (CC1). "Lakeview Health" ≠ "AETNA INC": two minted party rows; equal **only** if a correspondence claim is asserted — and correspondence **never merges rows**; it is a relation with strength, and lineage walks it ✓. Not established: state `not_established`, reference null, candidates elsewhere ✓. No party: state `no_party`, reference null ✓ — and a manufactured classification can never acquire a party by pointing at the artefact it sits on, because origin is on the *artefact*, and the manufactured flag's origin state is `no_party` on its own derived fact. |
| the hard invariant | an FK to `parties.id` says *points to 7*. Whether 7 is the same as the thing on a letterhead is a row in the correspondence relation with an origin and a strength. Separate by construction ✓. |
| verdict | **passes**, with one added rule (no cross-foundation correspondence) and one demonstrated property (the person branch is structure, not claim). |

---

## 3. What the comparison establishes

1. **A is rejected on the schema's own recorded reasoning; C is B or a trap; D passes every test
   and fails the purpose.** B is the shape that gives relationships one target while keeping
   two foundations as *anchors*.
2. **The four states live beside the reference, never in it** (§1), under every candidate.
3. **B's person branch is demonstrably not a correspondence** — it has none of the properties
   that make something a claim — which is what the ruling required to be shown, not said.
4. **B needs one rule D gets structurally:** correspondence never crosses foundations.
5. **The departure from the one-FK-per-entity convention is justified by the convention's own
   reason.** The convention exists for enforceability. B keeps a single enforceable FK; D would
   spread two-to-four columns across every relation to encode one concept. The convention's
   *form* changes for parties; its *reason* is honoured.

---

## 4. What this record does not decide

Institution correspondence (how *"Lakeview Health" ~ "AETNA INC"* is asserted, stored, weighed);
where external identifiers live; whether `Person` gains columns or `parties` is populated
retroactively for existing persons and how; the candidate relation for *not established*; the
`institutions` table's contents beyond an anchor; FK enforcement (`PRAGMA foreign_keys`) — a
wiring condition; any migration; and whether `Account.institution`, `PdfExtractCache.issuer`
or `DebtAccount.name` are ever read as correspondence evidence.

---

## 5. Ruling candidate — for Rob

> **One `parties` reference, anchored not subtyped: a household party is created with its
> `Person` and linked to it structurally (1:1, immutable, no source, no strength — never a
> claim); an institution party is the minted identity itself. Relations reference `parties`
> with one enforceable foreign key; which foundation a party has is a join to its anchor,
> never a kind consumers switch on. Every relation whose party may be unestablished carries a
> party state — established · not established · no party — beside the reference, and the
> reference is populated iff established. Correspondence is a separate relation with strength
> that never merges rows and never crosses foundations.**

If ruled, the next question is the first that changes a table: **whether existing `Person`
rows acquire party rows by migration or on first reference** — and that is a migration
question, not this one.

---

## 6. Ruling — Rob, 2026-09-12. B ruled. §5 frozen, with one invariant promoted.

*B does not win because one table is cleaner. It wins because the schema can encode the
semantic distinction without turning the distinction itself into a consumer-visible identity
mechanism.*

**The decisive point:** the household branch is created with its `Person`, 1:1, UNIQUE NOT
NULL, with no correspondence between party and person that could itself become a claim. *The
fixed point in relational form.* The common `Party` reference is not claiming how the party
became known; it is the stable target relationships point to — which is the invariant: *a
party reference is a referential mechanism, not evidence of party identity.*

```text
Person
  │ household declaration
  ↓
Party ────────────────► Institution
  │                        │
  │ common reference       │ minted identity
  │                        │
  └──────── relationships ─┘
             │
      role / correspondence /
      mediation / provenance
```

**Why A is genuinely out:** the `HistorianEntry` reasoning is unusually valuable evidence
because it is not architectural taste — the project already identified the exact defect.
Adopting A would deliberately reintroduce a known defect at a more fundamental layer, and
`party_kind` would recreate identity-as-categorical-label, the thing several records just
eliminated.

**Why C is worse than it first appears:** `PartyReference 7 → Person 42` and
`PartyReference 8 → Person 42` — if 7 and 8 are distinct identities, two parties were
invented for one household-declared person; if the same, a correspondence mechanism between
two supposed party identities is now needed. The third identity layer. C is B with uniqueness
or an unnecessary correspondence problem without it.

**D is the honest runner-up:** direct referential integrity to each concrete identity is a
real virtue. It fails the thing the abstraction exists for — every relation has to understand
the ontology, so the common party concept lives in application convention rather than
relational structure. B gives `origin.party_id · role.party_id · correspondence.party_id ·
lineage.party_id` one enforceable target: T-E exactly.

**Promoted from explanatory prose to an invariant:**

> **Correspondence never crosses foundations.** A `Person` and an institution may
> participate in a *relation* ("a partner's account is with Lakeview Health" is a relation involving two
> parties); they may never be collapsed by *correspondence*. An institution's external
> identifier cannot establish correspondence to a `Person` because the same string appears
> somewhere.

**Party state is explicit; NULL follows from it, never the reverse:**

```text
party_state = ESTABLISHED       reference = Party X
party_state = NOT_ESTABLISHED   reference = NULL
party_state = NO_PARTY          reference = NULL
```

`NOT_ESTABLISHED` and `NO_PARTY` are not inferred from NULL. This is exactly the distinction
that disappears if someone later "simplifies" to a nullable foreign key.

**Not to be reopened:** party semantics · correspondence · external identifiers · institution
identity · the Party shape. Upstream now.

**The next question — a migration question, and only this:**

> **When and how do existing authoritative `Person` rows acquire their required 1:1 `Party`
> anchors?**

Candidates: backfill in one migration · lazy creation on first participation in a party-
bearing relation · a staged variant. May inspect actual data and migration conventions.
**The likely fault line:** if every `Person` has exactly one party anchor *by construction*,
lazy creation permits a transient state — a person without its party — that the ontology says
should not exist.
