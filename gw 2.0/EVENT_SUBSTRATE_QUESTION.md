# The event substrate — extend `HistorianEntry`, or replace it?

**An open decision with a migration attached**

> Status: **Closed 2026-09-06; experiment run and criterion MET 2026-09-07.** `HistorianEntry`
> is kept and extended, structure stays in link tables with foreign keys, and new references
> follow the existing per-entity convention. The pre-registered criterion has now been
> tested rather than predicted: `tests/substrate_experiment.py`, 0 relationships in
> `context_json`, no read path needing it, one new nullable foreign key.
> Originally written as an open architecture decision; the codebase turned out to have answered
> most of it already. Written 2026-09-06, pulled out of the healthcare
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

## Largely answered by the code — structure versus event

The preference is to put things in the historian wherever that is safe and logical. The
codebase already shows where that line falls, in one function, seven lines apart
(`create_debt_ledger_entry`):

```python
session.add(CheckingTransactionLink(        # the STRUCTURE - real foreign keys
    checking_transaction_id=linked_txn_id,
    debt_ledger_entry_id=entry.id,
    user_confirmed_at=datetime.utcnow()))
...
log_historian_event(                        # the EVENT - what happened
    session, 'charge_observation', ...,
    context={'merchant': ..., 'entry_id': entry.id})
```

> **Structure goes in a table with foreign keys. Events go in the historian.**

So a healthcare payment is recorded in the historian *as an event*, and its *attachment to an
obligation* lives in a link table — which is not a new pattern, only the existing one pointed at
a new object. **That answers the pre-registered failure criterion at zero**: if relationships
live in link tables, none of them need to be inside `context_json`, and the historian is never
asked to carry what it cannot enforce.

### A JSON file is not the alternative

For financial relationships a file on disk is **worse** than `context_json`, not better — it
sits outside the transaction, outside backup and restore consistency, cannot be joined, and
carries no integrity at all. The precedent in this codebase is `voice_miss_log.jsonl`, and the
code's own docstring places it there *"not `historian_entries`"* precisely because it is
append-only telemetry that nothing references. **That is the right use for a JSON file: things
nothing depends on.** A payment attachment is the opposite of that.

### The latent defect this uncovered, in shipped code

`entry_id` is already written into `context_json` in three places with **no foreign key**, and
debt ledger entries are deletable. Delete one and the historian keeps a `charge_observation`
pointing at a row that no longer exists.

Nothing dereferences those references today — they are written for forensics and never read —
so this is latent rather than broken. **Healthcare would be the first consumer to dereference
them**, for a figure that reaches a tax report, which is exactly what converts a harmless smell
into a wrong number.

### What is left of the question

Only one piece, and it is much smaller than the original framing. A historian event about a
healthcare obligation still needs to *say which obligation*, and `historian_entries` has foreign
keys only for `debt_account_id` and `category_id`. So:

> **Does `historian_entries` gain one foreign key per referable entity, or a single polymorphic
> pair (`entity_type`, `entity_id`)?**

**Decided 2026-09-06: one foreign key per entity, following the existing convention.** The table
already does this for `debt_account_id` and `category_id`, the pattern works, and it is kept.

The trade is worth recording so it reads as a decision rather than a default. Per-entity keys
mean **column sprawl** — a nullable column per referable type, most of them null on most rows —
and a small migration each time a new entity becomes referable. A polymorphic pair avoids both
and gives up **referential integrity**, which is precisely the failure already visible in
`entry_id`: a reference the database cannot enforce, pointing at rows that can be deleted.

Sprawl is the price of enforceability, and this project has consistently paid it. **The substrate
question is closed. `HistorianEntry` is kept and extended; nothing is replaced.**

### On the latent `entry_id` references

Left alone. They are harmless while nothing dereferences them, and rewriting working code to fix
a defect that has never fired is not warranted. **The trigger is clear, though:** the first
consumer that dereferences one of those references needs a real foreign key at that point, not a
blob lookup. Healthcare's tax path would be exactly that consumer.

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

**Provisionally met at zero**, on the structure-versus-event split above: relationships live in
link tables with foreign keys, so none needs to be in the blob. The criterion stays written down
because the slice has not been built yet, and a criterion that is retired the moment it looks
satisfied was never a criterion.

> **Met in fact, 2026-09-07, and the caution was worth keeping.** The prediction was right —
> zero — but the first version of the experiment measured it wrongly and would have reported a
> pass it had not earned. Being right about the answer is not the same as having tested it.
> See *The experiment was run* below.

The rule behind it, worth keeping regardless of how the experiment lands:

> **JSON may carry explanatory context. Relationships required to preserve financial integrity
> may not exist only inside JSON.**

Because once they do, the database cannot enforce them — and a `context_json` holding
`{"transaction_id": 1827, "person_id": 4, "plan_id": 9}` survives transaction 1827 being
deleted, person 4 being merged and plan 9 being corrected, leaving historical-looking JSON
pointing into a world that no longer exists.

## The fixture that decides it

`tests/test_lifecycle_fixture.py`, written before any model. If the
historian can carry fact → event → relationship → calculation → rule version → correction →
reversal → historical reconstruction without becoming an untyped JSON dump, it is extended. If
it cannot, that is demonstrated in code rather than argued in a document.

### The experiment was run — criterion MET, 2026-09-07

`tests/substrate_experiment.py`. Every operation in the lifecycle fixture round-trips through
a candidate schema, and the criterion is **measured, not inspected**:

| | |
|---|---|
| Structural relationships in `context_json` | **0** of 9 — eight foreign keys and one link table |
| Read paths parsing JSON to enforce an invariant | **none** |
| New columns on `historian_entries` | **one**, `healthcare_expense_id`, nullable |

**The measurement that counts is the second phase**, which runs the whole fixture with
`context_json` **never written at all**. An earlier version of this experiment wiped JSON
after the first run and re-ran — and reported a pass it had not earned, because the second run
created new rows and wrote fresh JSON it was then free to depend on. Wiping proves nothing;
never writing does.

**And the experiment proves it can fail.** Two deliberate breakages — the event→expense
relationship moved out of its foreign key into JSON, and an allocation amount moved out of its
column into JSON — are both caught. A criterion that cannot go red measures nothing, and this
one had to be rebuilt once before it could.

### What the experiment settled that the document had not

**The historian is not the authority for the money.** Structure lives in versioned,
append-only tables — obligation versions, funding allocations, determinations, each row
pointing at the one it supersedes — and the historian records that the event happened, keeping
the audit and learning role it already has. State is folded from the typed tables, so
`superseded, never overwritten` is true *in the database* rather than only in the model.

That is the structure-versus-event split from `create_debt_ledger_entry`, unchanged, pointed
at a new object. The reason it matters here: had the amounts gone into historian rows, they
would have landed either in `context_json` (failing the criterion outright) or in
`actual_value` — the variance-shaped column whose name would then lie about half the rows,
forever.

**A mutable current-state row would not have worked.** `expense_funding_allocations` is a
version chain rather than a row that gets updated, because a correction that overwrites cannot
answer what the figure was in March, and a tax figure has to be reproducible after the rules
change under it.

**Shipped 2026-09-07.** The tables landed in `core/database.py` (design §6.3 step 2), the
experiment now imports them rather than mirroring them, and the migration is verified against
a pre-change database. So this file can no longer drift from what it claims to test: a change
to the shipped shape that breaks the criterion fails here.

### Extended to the whole schema, same day

The criterion was originally answered for one slice — the reimbursement allocation, which
`EVENT_SUBSTRATE_QUESTION` recommended precisely because it is small and runs end to end. It
now covers every module that has tables:

| Module | Round-trips | Passes with `context_json` never written | Proven able to fail |
|---|---|---|---|
| `allocation` | yes | yes | relationship into JSON · amount into JSON |
| `person` | yes | yes | a reassignment persisting without its `source` |
| `plan_year` | yes | yes | a correction persisting without what it corrected |

The last column is the one that matters. A store that quietly answered from its in-memory
registry would pass every other check while persisting nothing, so each round-trip is broken
at a single column and required to notice. Reads rebuild the registry **from the tables**,
which is what makes a field the schema cannot carry show up as a wrong answer rather than a
silent absence.

`core/classification.py` has no tables and is deliberately the one left out: its output is a
derived sensitive classification, and where that persists is a privacy decision — see
`CLASSIFICATION_QUESTION.md`, where an unsurfaced suspicion may not persist at all.
