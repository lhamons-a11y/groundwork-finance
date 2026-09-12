# The Person → Party anchor — when it comes into existence

> Status: **Design mode, 2026-09-12. A migration question, and only this one. No code, no
> migration written.** Rob's question, with the party shape (B) ruled upstream:
>
> > **When and how do existing authoritative `Person` rows acquire their required 1:1 `Party`
> > anchors?**
>
> Candidates: **(1)** backfill every existing `Person` in one migration · **(2)** create the
> anchor lazily when a person first participates in a party-bearing relation · **(3)** a staged
> variant. The record may inspect actual data and migration conventions.
>
> **The fault line Rob named:** if every `Person` has exactly one party anchor *by
> construction*, lazy creation permits a transient state — a person without its party — that
> the ontology says should not exist.
>
> **Not reopened:** party semantics · correspondence · external identifiers · institution
> identity · the Party shape. Upstream.

---

## 0. The data and the conventions — inspected

**There are no `Person` rows in production.** `people` exists (created by `create_all`), but
no route in `server.py` creates one — the twelve textual matches for *people*/*Person* there
are unrelated words — and `core/person.py` is pure with no callers (`database.py` L627:
*"person… pure and have no callers"*). `Person` rows are written in exactly one place: the
substrate experiment (`tests/substrate_experiment.py` `_sync_person`), a test double that
mirrors the pure registry into a temporary database. So the *existing rows* the question
names are, today, **zero in every production database and some in throwaway test databases.**

**The migration convention** (`migrate.py`): a `SCHEMA_VERSION` gate skips everything when
current; `init_db()` → `create_all` covers fresh installs; `_add_missing_columns` and
`_ensure_indexes` are idempotent by nature; **data-rewriting steps are flagged** in
`app_settings` via `_migration_done` / `_mark_migration_done` so they run once — *"they risk
clobbering a value the user has since deliberately set."* A backfill would be a flagged,
data-writing step.

**The creation paths that would have to mint the anchor:** `core/person.py:add_person` (pure
registry, `Person(id=r._next_id, …)`); the substrate's `_sync_person` (persisted, explicit
ids); and whatever persisted path 2.0 eventually wires — none exists yet.

**A constraint the database cannot express.** `parties.person_id UNIQUE` enforces *at most one
party per person*. *At least one* — that every `Person` has an anchor — is a cross-table
existence constraint SQLite cannot check. So "by construction" is not free: it is the creation
path plus a guard, the same way the sole-mutator and absence guards hold what a constraint
cannot.

---

## 1. Candidate (2), lazy creation — tested first, because it is the fault line

Under lazy creation a `Person` exists from declaration and its party row appears on the first
party-bearing relation — the first `origin`, `role`, `mediation` or `correspondence` that names
it.

**What that state is.** Between declaration and first use, the person has a sovereign identity
and **no reference-layer identity.** The ruling: *a household party is created with its
`Person` and linked to it structurally — the declaration's own identity seen from the reference
layer.* The anchor is not a thing the person *acquires when needed*; it **is** the person, at
the layer relationships point to. A person without it is a person who cannot yet be an origin,
hold a role, or be corresponded — not because no relation has been asserted, but because the
target does not exist. **The transient state is the ontology's forbidden state**, and it is
forbidden for a reason with teeth: the fixed point that terminates the correspondence regress
is *`Person` is not evidence-derived* — and a party identity that comes into existence
*because a relation needed it* is an identity whose existence depends on a consumer. That is
the consumer-boundary lesson (a declared permission is not a boundary unless every path is
subject to it) transposed to identity: an identity that exists on demand is an identity whose
absence is a live state.

**Two concrete consequences, either of which rejects it:**
- *Read-side:* "does this person have a party?" becomes a meaningful question with a *no*
  answer, and every consumer has to handle it — the four party states would acquire a fifth,
  *person exists, party not yet minted*, which is neither *not established* (the person is
  established) nor *no party* (there is one; it just hasn't been created). A state the doctrine
  has no name for, arriving from implementation.
- *Write-side:* the first relation to name a person becomes the thing that creates identity.
  Which relation, on which path, in which transaction — every party-bearing table would carry
  the minting responsibility, and a relation written through a path that forgot would point at
  nothing. The sole-mutator problem, multiplied by the number of relations.

**Verdict: semantically impermissible**, not merely inconvenient. Rejected.

---

## 2. Candidate (1), backfill — correct, and today empty

A flagged migration step, on the convention: *for every `Person` row without a party row,
create one* — idempotent, once, recorded in `app_settings`. **In production it does nothing**,
because there are no rows. It must exist anyway, for three reasons:
- a database that *does* have people rows without anchors is the forbidden state, and the
  migration is the only path by which such a database becomes conformant — test databases
  today, any 1.x → 2.0 upgrade path later;
- "by construction" has to hold for databases that predate the construction, or the invariant
  is a property of new installs only;
- it is the audit query as well: after it runs, `people LEFT JOIN parties … WHERE party IS
  NULL` must be empty, and that query is the guard the constraint cannot be.

**Verdict: required, and its emptiness in production is a fact worth recording** — this is the
rare migration with no data risk, which is why it can be written to the flagged convention
without a dry-run path.

---

## 3. Candidate (3), staged — nothing to stage

Staging exists to bound risk over a large or heterogeneous population. The population is
zero in production and small and disposable in tests. **Rejected as unmotivated**; if a
future upgrade path finds a populated `people` table, the backfill step of §2 *is* the stage.

---

## 4. What "by construction" therefore means — the actual answer

The question was *when* the anchor comes into existence. The cases give a two-part answer,
because the constraint has two halves the database can only enforce one of:

> **Going forward: the party row is created in the same unit of work as the `Person`, on every
> creation path — never afterwards, never on demand. Existing rows: a flagged, idempotent
> backfill creates the missing anchors once; today it finds none in production. At most one is
> the database's (`UNIQUE`); at least one is the creation path's, and a guard asserts it.**

Concretely for the paths that exist:
- `core/person.py:add_person` — the pure registry gains the anchor as part of `add_person`,
  or the registry's `Person` *is* its own anchor in the pure model (the pure module has no
  separate reference layer today; how it models the party row is the pure-module analogue of
  the schema, decided when the schema is written).
- `tests/substrate_experiment.py:_sync_person` — writes `Person(id=…)` rows and must write the
  anchor in the same session, or the experiment itself manufactures the forbidden state in
  every run.
- the eventual 2.0 persisted creation route — the same unit of work, by rule.
- **the guard:** a fixture assertion of the absence kind — *no `Person` without a party* —
  runnable against any database, and the migration's audit query. Not a constraint; a test,
  like the sole-mutator guard, until the day the store can express it.

---

## 5. What this record does not decide

The `parties` table's columns beyond `person_id`; whether the pure `core/person.py` grows a
party concept or the persisted layer alone does; the transaction mechanism (SQLAlchemy session
boundary vs explicit); the `SCHEMA_VERSION` string; institution minting paths (none exist, and
that is the *next* creation path, not this one); anything about correspondence or state.

---

## 6. Ruling candidate — for Rob

> **The anchor exists from the moment the `Person` does. It is created in the same unit of
> work as the `Person` on every creation path, and never lazily — a person without a party is
> the ontology's forbidden state, and an identity that appears because a consumer needed it is
> an identity whose absence is a live state. Existing rows are anchored by a flagged,
> idempotent backfill that today finds none in production. The at-most-one half of the 1:1 is
> a database constraint; the at-least-one half is the creation path plus a guard.**

If ruled, the design mode has reached its first table-changing decision with its shape,
timing and guard all settled, and **the next question is whether to write it** — which is a
build-selection question, not a design one.

---

## 7. Ruling — Rob, 2026-09-12. §6 ruled as written. The design chain reaches its first build boundary.

*The data inspection collapsed the migration question into a creation invariant.* With zero
`Person` rows in production there is no meaningful choice between migration strategies; the
migration is still required because the schema must be safe for databases that may contain
rows, but today's production backfill is empty.

**Lazy creation fails semantically, not just operationally.** The sentence that carries it:
*an identity that appears because a consumer needed it is an identity whose absence is a live
state* — the consumer-boundary principle in a new place. The party reference exists because
the person exists; it cannot exist because some later relationship required a target.

```text
Person exists  ──same unit of work──►  Party anchor exists  ──►  relationships may reference Party

never:   Person exists  ──…some consumer eventually needs Party…──►  Party gets created
```

**The SQLite limitation is a constraint boundary, not permission to weaken the invariant:**

```text
UNIQUE(person_id)        →  at most one
creation path + guard    →  at least one
```

The project's existing approach: when the storage engine cannot express a semantic invariant,
the application path owns it and a test guards it.

### The design work is over for this branch

```text
1. artefact identity              ruled
2. reading identity               ruled
3. origin / party semantics       ruled
4. party reference shape          ruled
5. Person → Party anchor timing   ruled
```

**The next decision is no longer philosophical:** *do we implement the settled shape, and what
is the smallest build that does so without opening downstream questions?*

**The build, if authorised, is deliberately boring:**

- the `Party` anchor structure
- the `Person` creation path
- the substrate's `_sync_person`
- the idempotent audit / backfill
- the guard — no `Person` without a party
- tests
- schema / version wiring as the existing convention requires

**And nothing institution-specific.** Implementation must not "finish the job" by adding
institution correspondence, issuer normalisation, external ids, or provenance consumers. Those
are not consequences to be guessed; they are subsequent questions.

---

## 8. Slice accepted — Rob, 2026-09-12. `dadb823`, 860 green, clean tree, no downstream ontology implemented.

**The orphan discovery strengthened the invariant.** Not *every `Person` should eventually have
a `Party`* but:

> **The `Person` and its anchor have the same lifecycle boundary.**

So the delete path belongs inside the slice; otherwise the forward forbidden state is
implemented while its inverse is permitted:

```text
Person exists, Party absent       ← creation violation
Person absent, Party exists       ← deletion violation
```

The lifecycle is symmetric:

```text
Person lifecycle
    ├── create ──same unit──────► Party anchor
    └── delete ──same lifecycle─► Party anchor removed

Party
    └── person_id UNIQUE FK  →  one Person ↔ one Party
        the missing cross-table half guarded by  people_without_party() == empty
```

**The mutation fixture is appropriately adversarial** — it removes the mechanism that
guarantees creation and corrupts the supposedly idempotent remediation, and restores the
module afterwards: the right pattern for architecture fixtures — prove the guard has teeth
without leaving the repository modified by the proof.

**The migration is remediation, not a second creation mechanism:** it repairs legacy state and
then the construction invariant takes over.

**Recording two invariants as *not exercisable* rather than manufacturing placeholder tests**
preserves the distinction between *green because tested* and *green because the forbidden
machinery doesn't exist yet.*

### The next question — the institution side

An institution, unlike `Person`, has no existing sovereign declaration to anchor. Its creation
path is therefore **not assumed to copy the `Person` solution.** The next record establishes
**what encountering an institution means** before deciding how an institution row gets minted.
