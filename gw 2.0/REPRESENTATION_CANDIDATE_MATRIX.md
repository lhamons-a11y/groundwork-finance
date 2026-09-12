# Representation candidate matrix — what must exist, before what it looks like

> Status: **Design mode, 2026-09-12 — revised on Rob's ontology ruling. No code, no schema
> commitment, no migration.** Mode rule:
>
> > **We are allowed to decide what information must exist. We are not yet allowed to decide
> > what the final API/schema looks like merely because a particular implementation is
> > convenient.**
>
> **Purpose:** discover whether the requirements the audit exposed want one representation or
> several related ones. Candidate locations are listed, never chosen. "Add `as_of` to
> `Evidence`", "add `document_id`", "make readings first-class rows", "replace `Evidence` with
> X" appear only as candidates.
>
> **Rob's refinement, applied:** the matrix separates **identity**, **temporal coordinates**
> and **epistemic status** explicitly, so they cannot be bundled as "evidence metadata". Two
> columns added — *invariant if absent* and *what must never be inferred from it* — because
> representation bugs become policy bugs at the consumer boundary.
>
> **Two tracks, adjacent and separate:** Track A — evidence representation. Track B — narrator
> boundary capability. **Carried separately, not here:** the 1.x discharge-scope question.

---

## 0. The minimum ontology — Rob's provisional ruling

**Four conceptual layers plus an evidentiary relationship** — not five entities. The four are a
chain; the relationship connects evidence to a proposition and is deliberately not a layer.
Independence / lineage is a **property of the source/referent relationship**, not a fifth thing.

```text
SOURCE          who / what can know or originate a claim
                (user · insurer · provider · a parser)

ARTEFACT        a particular held or asserted thing through which that source's
                position can be encountered
                (an EOB · a statement · a capture · "the Sept 1 statement", asserted)

READING         a particular interpretation / extraction of that artefact
                (a parse · a scan · a transcription — or, for an utterance, the saying itself)

PROPOSITION     the claim that can be stated from the reading
                (P-subject · P-world · P-ack · health-on-axis)

EVIDENTIARY     how strongly a proposition is supported, and by what independent
RELATIONSHIP    knowing source / channel
```

**Strength belongs to the evidentiary relationship, not to the proposition and not to the
artefact.** The same proposition can be supported by different relationships; two readings of
one artefact do not acquire strength by being two rows.

**What `Evidence` conflates today:** `Evidence(axis, source, supports, amount, recorded_at)` is
a *proposition* (axis + bit) stamped with a source *type*, with no artefact, no reading, one
time that is the import clock, and strength computed over it by counting source types. A
document is not a proposition; a reading is not a source; a row is not independence.

### The mechanical invariant — the test any candidate must pass

The representation must make this relationship **inspectable by resolution logic without
reconstructing it from timestamps, descriptions, or row order**:

```text
source S1                                    source S1 ── artefact D1 ── reading R1 ── P1
   └── artefact D1
          ├── reading R1 ── P1                source S2 ── artefact D2 ── reading R2 ── P2
          └── reading R2 ── P2

one artefact, competing readings             two potentially independent source artefacts
→ parse dispute inside one referent          → source conflict (independence still a further fact)
```

And the temporal test, alongside it:

```text
document as-of Aug 31, imported Sep 10   ≠   document as-of Sep 10, imported Sep 10
```

with import order never read as chronology.

---

## 1. Track A — the matrix, seven rows in three groups

Columns: *what must be knowable* · *current holder* (the code) · *current loss* · *candidate
locations (none chosen)* · *invariant if absent* · *must never be inferred from it* ·
*consumer*.

### Group I — identity

| # | requirement | what must be knowable | current holder | current loss | candidate locations | **invariant if absent** | **must never be inferred** | consumer |
|---|---|---|---|---|---|---|---|---|
| **1** | **referent identity** | which artefact this evidence belongs to; held (bytes) vs asserted (individuating description); for asserted, that identity is relative to the candidate set and can degrade (RA2) | `PdfExtractCache.source_hash` — content-hash identity for held PDFs, shipped, **unlinked to evidence**; `Evidence.source` is a *type*; `ExpenseDetermination.evidence` is a `String(80)` label | two artefacts ≡ one read twice; retraction cannot find derived facts; D3b reported as a source reversal | (a) evidence → artefact record keyed by hash, `PdfExtractCache` as the store · (b) artefact owns readings, evidence hangs off readings · (c) referent field on evidence only · (d) description record for asserted referents with candidate-set evaluation | **source-history and parse disputes collapse** into one shape | **same description = same artefact** (RA2); **held = verified** (captured-portal) | Cluster B; H4; R-ASSERT |
| **3** | **reading identity** | which interpretation / extraction of that artefact produced this value; when read; by what (parser version · person); that readings of one referent are one source | `PdfExtractCache.extracted_json` — **one reading per hash**; a second parse cannot coexist; `Evidence` rows are readings with no referent | `attested[-1]` decides tax by scan order; corroboration counts readings as sources; a parse dispute cannot be *represented* | (a) reading record beneath an artefact · (b) reading id + artefact id on evidence · (c) version `PdfExtractCache` by (hash, parser) | **re-reads can masquerade as corroboration** | **row count = independent evidence**; **latest reading = correct reading** | H4; Cluster B; R4 |
| **7** | **independence identity** *(added)* | which evidence paths are genuinely independent knowing sources for corroboration and ranking; lineage sufficient to answer *how many independent knowing sources support this?* | `_state_from`: `distinct = {e.source for e in supporting}` — **independence by source *type***; nothing for the P-ack chain (E → servicer → capture → user report) | `USER_STATED` reporting the EOB + `IMPORTED_EOB` = two independent sources (K5's inflation, shipped in the pure module); three readings of D1 = corroborated; a capture of S's portal = a source | (a) lineage on the reading (*derived from artefact X, which is source S's*) so independence is computed by walking to distinct sources · (b) an explicit *independent-of* relation between artefacts (DI: source instance ≠ independence; two EOBs from one insurer are not independent) · (c) independence declared per channel for P-ack (one knowing party, four channels — ruled) | **strength can be inflated** by custody, capture, report or re-read | **capture / user report / re-read = new knowing source**; **distinct source type = independent** | corroboration; `strength_of`; acknowledgment (one knowing party); tie |

### Group II — temporal coordinates

| # | requirement | what must be knowable | current holder | current loss | candidate locations | **invariant if absent** | **must never be inferred** | consumer |
|---|---|---|---|---|---|---|---|---|
| **2** | **evidence time** | when the proposition was true / stated *according to the evidence itself*: utterance → when said; document → its as-of; capture → render time (and the portal's stated as-of where they differ — fenced); import time kept **beside** it | `Evidence.recorded_at` = import clock; `payment_plan.Entry.on` = effective (correct); `ExpenseObligationVersion.effective_seq / recorded_seq` — the dual pattern, shipped for amounts; `Plan.effective_from/to` | a document's own date is unrepresentable; `knowing[-1]`/`resolution()` valid only by construction; P-ack undated; same-party ties untellable from history | (a) as-of on the artefact, readings inherit · (b) as-of per evidence item · (c) generalise `effective_seq / recorded_seq` to evidence · (d) two coordinates — artefact as-of *and* reading time — because a re-read on Oct 1 of an Aug 31 statement has both | **chronology becomes import-order-dependent** | **`recorded_at` = evidence date**; **later-imported = later-stated** | H3 (R2/R3); acknowledgment; tie; Cluster C |

### Group III — epistemic status

| # | requirement | what must be knowable | current holder | current loss | candidate locations | **invariant if absent** | **must never be inferred** | consumer |
|---|---|---|---|---|---|---|---|---|
| **4** | **P-ack** | what the entitled party said about this payment / balance, and as of when; which channel (E's artefact · servicer-of-record · live system · user report); the named payment it concerns; *attached-unacknowledged* before it | **nothing.** `Entry` has no acknowledgment; `Evidence` has two health axes; 1.x `debt_pdf_reconcile` computes `{implied, stated, diff}` once and discards | discharge unrepresentable; `remaining` asserts confirmation; the four figures cannot say which is E's | (a) a proposition kind over the family, evidenced by readings of E's artefacts — **downstream of rows 1–3, 7** · (b) an acknowledgment entry kind in the ledger referencing evidence · (c) both: ledger holds *that*, evidence holds *why* | **payment attachment is read as discharge** | **cleared payment = acknowledged** (K6); **stated balance = acknowledged payment** (K8); **household confirmation = E acknowledgment** (1.x `is_auto_confirm`) | discharge; `remaining` (strength fenced) |
| **5** | **resolution provenance** | whether a disagreement is between sources or between readings of one artefact; ordering on row 2's axis; a supersession relation where a document claims one (T4) | `resolution()` derives kind · resolver · contradictions · post from `(source type, bit)` in position order; `ExpenseObligationVersion.supersedes_id` — shipped pattern | D3b's wrong row; positional ordering; supersession unrepresentable | **nothing of its own if rows 1, 2, 3, 7 exist** — derived on read, `resolution()`'s own principle · plus (a) a supersession relation between artefacts on the `supersedes_id` pattern | **the resolver assigns a wrong causal story** it cannot detect | **a later row = a source changed its stance**; **supersession = arrival order** (T4 vs T3) | narrator / export / backup; the reading-level kind (deferred) |
| **6** | **unresolved state** | that no single conclusion is established, *which fact* is unresolved, and *between what* — with no manufactured winner | four consumer-local sentinels: `plan_year.UNKNOWN` · `allocation.UNRESOLVED` · `classification.UNAVAILABLE` · `payment_plan.REFUSED`; Q1's refusal-as-value carries `offered · reason · required · consumer` | none says *what* or *between what*; `year_summary.UNKNOWN` carries three truths; `plan_at` and `attested[-1]` manufacture | (a) keep local terminals — *unresolved is a state, not a rank* (ruled) · (b) Q1's refusal shape carrying candidates · (c) the unresolved **condition** in the family (two claimants; priority sub-fact), terminals reading it | **the consumer is forced to choose** | **`UNKNOWN` = both equally true**; **`UNKNOWN` = neither applies**; **one sentinel = one situation** (CC5) | every consumer |

---

## 2. What the matrix says — one representation, or several?

**Group I + row 2 + row 5 are one family**, and row 7 is what makes the family *worth
having*. Referent, reading, and independence are three questions about the same
artefact → reading lineage; evidence time attaches to the artefact (as-of) and the reading
(when read); resolution provenance is **derived** from the four and needs nothing stored.
The mechanical invariant in §0 is passed or failed by any candidate for rows 1, 3, 7 *together*
— none of the three can pass it alone: a referent without readings cannot show competing
readings; readings without a referent cannot show they are of one thing; both without
independence cannot say whether D1 and D2 are two knowing sources or one insurer printing
twice. **This family wants one representation.**

**Row 4 is downstream, by Rob's ruling and by the matrix.** P-ack is a proposition kind whose
subject is E, evidenced by readings of E's artefacts, ranked by row 7's independence (one
knowing party, four channels). It consumes the family and adds a ledger link. Candidate (c) —
*ledger holds that, evidence holds why* — is the one that keeps `payment_plan` from inventing
evidence semantics. Not chosen; noted as the candidate that respects the chain:

```text
artefact → reading → proposition → P-ack assertion → evidentiary relationship → discharge → projection
```

**Row 6 splits.** The *condition* (what is unresolved, between what) is a derived fact over
the family — *two readings of D1 disagree*, *two plans claim August*, *priority between A and
B*. The *terminal* stays consumer-local, as the tie ruling requires and as the four existing
sentinels already do. The matrix does not propose converging them.

**So: one evidence family, one downstream proposition kind, and consumer-local terminals.**

```text
EVIDENCE FAMILY     artefact   identity (held/asserted) · as-of · supersedes · lineage to source
                    reading    of artefact · when · by what · yields
                    evidence   a reading's claim on a proposition; or an utterance
                    ─ independence     derived by lineage, never by row count or source type
                    ─ resolution       derived on read
                    ─ unresolved       derived condition

DOWNSTREAM          P-ack: a proposition kind over the family + a ledger link

LOCAL TERMINALS     UNKNOWN · UNRESOLVED · UNAVAILABLE · REFUSED — consumer-owned, kept
```

---

## 3. What already exists, in the wrong place — findings, not proposals

- **`PdfExtractCache` is an artefact-and-reading store.** Content-hash identity, issuer, one
  parse; shipped for debt statements; unknown to the evidence model. It has rows 1 and 3's
  shape and D3's limitation — **one reading per hash**. Whether it becomes the store or is
  precedent for one is a choice; that it exists is a fact.
- **`ExpenseObligationVersion` carries `effective_seq / recorded_seq / supersedes_id`.** Rows 2
  and 5's pattern, shipped for amounts. Reuse as a pattern is a candidate; as a table, not
  proposed.
- **`ExpenseDetermination.evidence` is a `String(80)`.** Where the persisted side loses the
  referent today.
- **`_state_from`'s `distinct = {e.source …}`** is row 7's current holder and is *wrong by
  type*: it counts source kinds, not knowing sources. Independence has never been represented;
  it has been approximated by an enum.

---

## 4. Track B — narrator boundary capability *(separate; no shared object presumed)*

| requirement | what must be knowable | current holder | current loss | candidate locations | invariant if absent | must never be inferred | consumer |
|---|---|---|---|---|---|---|---|
| **may this cross into model-visible findings?** | per item a surface passes: its *kind*; for 2.0 facts, sensitivity domain and whether the classification was manufactured | `Sensitivity(domain, manufactured)` on `Classification` / `DerivedFact`, **dropped at `NarratorFacts`**; nothing on 1.x findings | H5: safe by construction, unenforced; 2.0: the two-CVS figure reaches the narrator unmarked | (a) **the declaration at `callAI`** — ruled and authorised · (b) a sensitivity carrier *beside* `NarratorFacts` for the gate's reader, never in findings text · (c) `_permitted_value` refusing on `manufactured` with Q1's reason — deferred, needs the settled gate rule | **the model becomes the enforcement locus** by default | **given to the model = permitted to say** (R8's logic applied to claims); **not a health word = not health** (the two-CVS case) | `callAI` (live); the 2.0 narrator; the gate |

Track B needs nothing from Track A: the declaration is a property of the call; the 2.0
carrier needs a field that exists and is lost at one projection. Adjacent, not merged.

---

## 5. Design boundary at this point — Rob's

**Decided:** source, artefact, reading, proposition are conceptually distinguishable ·
evidence time is not import time · reading multiplicity cannot equal source independence ·
strength is a relationship, not an artefact property · P-ack is downstream of
proposition/evidence identity · discharge is downstream of P-ack · 1.x discharge scope is
outside this exercise · narrator authorisation is a separate boundary problem.

**Not decided:** whether these become classes, tables, value objects, linked records, or
something else · whether `Evidence` survives · whether readings are persistent · exact
identity keys · exact temporal fields · strength representation · resolution algorithm /
state names · migration strategy.

---

## 6. Ruling — Rob, 2026-09-12. Artefact owns its readings.

**The ontology:**

```text
Source
  └── Artefact
        ├── Reading 1
        │     └── Proposition(s)
        └── Reading 2
              └── Proposition(s)
```

with **lineage running through the whole chain**, not the reading owning the artefact
reference. The reason is mechanical: *the referent is the thing that existed independently of
our interpretation of it; a reading is an observation of that thing; therefore two readings must
be able to point to the same referent without becoming two sources.* That gives the two
invariants actually needed, kept separate:

```text
same artefact + different reading   ≠   different artefact + different reading
different artefact                  ≠   independent source
```

Two documents from one insurer may be two artefacts and one evidentiary source. A household
statement about an EOB and the EOB itself may be two representations of one underlying fact and
must not become independent merely because their `source` enums differ.

**Lineage lives on the relationship, conceptually:**

```text
source ── produced / holds ──► artefact ── read-as ──► reading ── asserts ──► proposition
```

Not `reading → "some source enum"` — that recreates K5. The lineage needed for independence
answers *what real-world origin does this evidence trace back to?*, not *what ingestion
mechanism produced this row?* So these stay distinguishable — different capture channels,
potentially one underlying referent — and the representation must permit that relationship to
be **discovered**, never assumed either way:

```text
USER_STATED    └── "I saw the EOB saying $412"
IMPORTED_EOB   └── EOB.pdf saying $412
```

**The seven rows, regrouped:**

```text
IDENTITY     1 referent identity · 2 reading identity · 3 independence / lineage
TEMPORAL     4 evidence time · 5 P-ack evidence date
EPISTEMIC    6 resolution provenance · 7 unresolved state
```

The evidentiary relationship stays outside the hierarchy: it connects these to a proposition; it
is not another identity layer.

**One hard invariant, added to the design:**

> **No independence claim may be derived solely from capture / source type.**

That catches the shipped K5 defect exactly.

**Correction to "five units":** four conceptual layers plus an evidentiary relationship.
Independence/lineage is a property of the source/referent relationship, not necessarily a fifth
entity — otherwise a useful decomposition becomes a premature schema.

**Recorded as the representation decision:**

> **Artefact owns readings; readings identify their artefact through lineage; source
> independence is represented independently of capture/source type; propositions are
> downstream assertions of readings; evidentiary relationships connect evidence to
> propositions. No schema or API shape is implied by this ontology.**

**Deliberately not decided:** table/object names · whether `source` becomes an entity · whether
artefact IDs are generated or externally supplied · whether readings are immutable · whether a
proposition belongs to one or many readings · how supersession is encoded · how P-ack is
represented · how an unresolved state is encoded · the API shape. Implementation choices,
downstream of the ontology.

**What build mode now inherits:** it must preserve who/what produced the evidence, what
artefact it came from, which reading produced the proposition, and whether two pieces of
evidence have independent provenance — with none of those answerable by list position or enum
identity.

---

## 7. Next, in this mode — Rob's

The ontology is ruled (§6). What remains in this mode is downstream of it and Rob's to open:
the remediation authorisation (the H1–H5 contracts, guards and refusals, and the `callAI`
declaration — none of which need the representation), and the implementation choices the
ruling lists as not decided.
