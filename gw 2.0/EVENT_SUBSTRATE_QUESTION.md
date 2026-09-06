# The event substrate — extend `HistorianEntry`, or replace it?

**An open decision with a migration attached**

> Status: **Question, not a proposal.** Written 2026-09-06, pulled out of the healthcare
> reviews because it is not a healthcare decision. It touches shipped code, real user data, and
> the LTS line, and it should not be settled inside a document about medical bills.
>
> Raised by `ARCHITECTURE_REVIEW_LIFECYCLE.md` §A1.
>
> **`OBLIGATION_SEMANTICS_QUESTION.md` is upstream of this one.** What events should be
> recorded depends on what is being recorded — whether an unpaid bill is an accounting object
> at all. Answer that first; this question changes shape depending on the answer.

---

## Why this is not a greenfield question

Both review passes proposed building a fact/event/relationship/conclusion model. **Groundwork
already has an event log, and it is already load-bearing.**

`HistorianEntry` is read in fourteen places, and in several of them it *is* the source of truth
rather than a record of one:

- **The proactive frequency ledger.** `_proactive_state` reads `proactive_shown` and
  `proactive_dismissed` rows to decide what may interrupt. There is no other store; the
  historian is the authority, deliberately, so the budget survives a restart.
- **Pillar 5's decision memory** reads estimate-vs-actual variance from it — the table it
  replaced could not carry that.
- **The engagement streak** counts distinct `session_start` days.

So the honest question is not *what should the event model look like*. It is **whether the one
already carrying weight can carry more, or whether it has to be replaced** — and that is a
migration on a shipping product.

## Why its current shape does not fit

Three specific mismatches, all structural rather than cosmetic.

**It is variance-shaped.** The columns are `expected_value`, `actual_value`, `variance_pct`,
`variance_amount`. That schema was designed for *expected versus actual* learning events, which
is what Phase H1 needed. A general fact or relationship has no expected value, and forcing one
into these columns means either nulls everywhere or overloading them with meanings the column
names contradict.

**It is debt-shaped.** The only foreign keys are `debt_account_id` and `category_id`. There is
no reference to a transaction, a person, an expense, a plan, an obligation or a provider — so it
**structurally cannot point at** most of the entities the healthcare model needs. Everything
else has to go into the blob.

**Its provenance is an untyped blob.** `context_json` is `Text`. No schema, no version, no
validation. It already holds the proactive ledger's `key`/`budget`/`category`, and it works —
but nothing prevents two writers disagreeing about the shape, and nothing can query it.

And what a fact/event model needs and this has none of: a **source** (who asserted this), a
**rule version** (what the conclusion was computed under, per `ARCHITECTURE_REVIEW_LIFECYCLE`
C1), and **relationships between events** — reverses, supersedes, corrects, funds, satisfies.

## What a `HistorianEntry` is — the question to settle first

Extending it is straightforward. Extending it **without deciding what its authority is** is how
the substrate problem gets buried rather than solved. It could be:

| | |
|---|---|
| **A — audit log** | something happened |
| **B — event store** | the authoritative record from which current state is reconstructed |
| **C — learning history** | a record of what Groundwork observed |
| **D — all three** | which is the architecture problem, not a description |

**The code says A + C by design, B by accident.** Its docstring calls it a structured,
queryable event log for adaptive features and compliance reporting — audit plus learning. Then
`_proactive_state` reconstructs live state from it: it queries `proactive_shown` and
`proactive_dismissed` rows and derives session counts, weekly budgets and cooldowns, with no
other store behind them. That is option B, in one feature, added later, without the shape being
revisited.

Which makes the answer cheaper than it looks: **B is currently true of exactly one feature.**
Small enough to move if the decision goes the other way — and worth confirming before anything
is designed around it.

## The three options

**Extend in place.** Add columns and foreign keys to `historian_entries`, keep the variance
columns as legacy, and let new event kinds use the new fields. Cheapest, no data movement, and
existing readers keep working untouched. The cost is a table with two schemas in it, where the
column names lie about half the rows, forever.

**A new table beside it.** Leave the historian doing what it does and build a typed event store
for the new work. No migration, no risk to shipped readers — and two event logs, which is the
condition where "where is the truth" stops having one answer. That is the failure mode this
whole review exists to prevent, arriving through the back door.

**Replace it.** One typed event store, historian rows migrated. Correct, and the most expensive:
fourteen read sites, real user data, and an LTS line whose whole promise is stability.

## What has to be true before choosing

- **How many historian rows exist in real installs**, and how many are the variance-shaped kinds
  versus the newer blob-shaped kinds. If the variance shape is a small legacy tail, replacement
  is cheaper than it sounds.
- **Whether the proactive ledger's read path can tolerate a schema change**, since it is the one
  place where a historian read directly gates user-visible behaviour.
- **Whether the primitives get provenance too** (`ARCHITECTURE_REVIEW_LIFECYCLE` §A2). If
  `Transaction` stays mutable and provenance-free, a typed event store above it still cannot
  answer the reconstruction question end to end, and the scope of this decision changes
  completely.

## The recommendation, held loosely

**Do not decide this from a document.** The reviews' own lesson is that models specified without
being built are wrong in ways the document cannot show.

Build the thinnest slice that exercises all four layers — facts, events, relationships, a
conclusion — and let contact settle the substrate. The natural candidate is **the reimbursement
allocation**: small, local to one entity, already proven unrepresentable as a status field, and
it runs end to end because the tax number depends on it. If it survives $1,000 with three
funders, a late correction, a reversal and a rule-version change, the model generalises and the
substrate question answers itself. If it does not, that is known in a week rather than after a
migration.

**And it should be built somewhere other than healthcare.** If healthcare is the part of this
product that matters most, it is the worst possible place to learn what the event model should
have been.

## The pre-registered failure criterion

Declared before the experiment, because a substrate that half-works exerts a strong pull to be
kept, and the argument then gets relitigated on attachment rather than evidence. This project
already applies the discipline one level down — state what would falsify a check before you can
be fond of it.

> **The historian fails the experiment if carrying the fixture requires more than two structural
> relationships to live inside `context_json`, or if any read path must parse JSON to enforce an
> invariant.**

The rule behind it, worth keeping regardless of how the experiment lands:

> **JSON may carry explanatory context. Relationships required to preserve financial integrity
> may not exist only inside JSON.**

Because once they do, the database cannot enforce them — and a `context_json` holding
`{"transaction_id": 1827, "person_id": 4, "plan_id": 9}` survives transaction 1827 being
deleted, person 4 being merged and plan 9 being corrected, leaving historical-looking JSON
pointing into a world that no longer exists.

## The fixture that decides it

`tests/test_lifecycle_fixture.py`, written before any model and currently failing. If the
historian can carry fact → event → relationship → calculation → rule version → correction →
reversal → historical reconstruction without becoming an untyped JSON dump, it is extended. If
it cannot, that is demonstrated in code rather than argued in a document.
