# Representation candidate matrix — what must exist, before what it looks like

> Status: **Design mode, opened 2026-09-12. Mode: REPRESENTATION & REMEDIATION DESIGN — no
> code, no schema commitment, no migration.** First deliverable of the mode, on Rob's rule:
>
> > **We are allowed to decide what information must exist. We are not yet allowed to decide
> > what the final API/schema looks like merely because a particular implementation is
> > convenient.**
>
> **Purpose:** discover whether the six requirements the audit exposed want **one**
> representation or **several related** ones. Candidate locations are listed, never chosen.
> "Add `as_of` to `Evidence`", "add `document_id`", "make readings first-class rows", "replace
> `Evidence` with X" are all **candidates**, and appear below only as such.
>
> **Two tracks, adjacent and separate:** Track A — evidence representation (rows 1–6).
> Track B — narrator boundary capability (a separate table; it asks *may this cross into
> model-visible findings?* and does not presume the same object).
>
> **Carried separately, not here:** the 1.x discharge-scope question. It may affect
> remediation later; it does not shape the 2.0 evidence model.

---

## 0. The ontology, and the two tests any representation must pass

Rob's minimum unit question: before fields, settle what the units are.

```text
source        a party or process that can know something        (user · insurer · provider · a parser)
artefact      a thing that can be held and re-read               (an EOB · a statement · a capture)
reading       one observation of an artefact, or one utterance   (a parse · a scan · "the user said")
proposition   what a reading lets the record say                 (P-subject · P-world · P-ack · health-on-axis)
```

What `Evidence` conflates today: `Evidence(axis, source, supports, amount, recorded_at)` is
**a proposition (axis + bit) stamped with a source *type*, with no artefact, no reading, and
one time that is the import clock.** A document is not a proposition; a reading is not a
source; strength belongs to the evidentiary relationship, not to the document.

**Test 1 — same referent vs different referents**, mechanically distinguishable:

```text
D1 → R1: $412        D1 → R1: $412
D2 → R2: $4.12       D1 → R2: $4.12
source conflict      parse dispute inside one referent
```

**Test 2 — evidence time vs import time**, without treating import order as chronology:

```text
document as-of Aug 31, imported Sep 10      ≠      document as-of Sep 10, imported Sep 10
```

Every candidate below is scored against both.

---

## 1. Track A — the matrix

| # | requirement | information required | current holder | current loss | candidate locations *(none chosen)* | consumer needing it |
|---|---|---|---|---|---|---|
| **1** | **referent identity** — which artefact this evidence is *of* | an individuating identity per artefact: for held, the bytes (content hash); for asserted, an individuating description (issuer · date · kind); plus *held vs asserted* | **`PdfExtractCache.source_hash`** — a content-hash identity for held PDFs, shipped, **unlinked to any evidence**; `Evidence.source` is a *type* (`IMPORTED_EOB`); `ExpenseDetermination.evidence` is a `String(80)` label | two artefacts ≡ one artefact read twice (D1/D2); independent confirmation unreachable; retraction cannot find derived facts (D6); `resolution()` reports a reversal that did not happen (D3b) | (a) a reference on each evidence item to an artefact record keyed by content hash, with `PdfExtractCache` as the existing artefact store · (b) an artefact entity that *owns* its readings, evidence hanging off readings · (c) a referent field on `Evidence` only, no artefact entity · (d) for asserted referents, a description record with candidate-set evaluation (RA2's non-monotonicity) | Cluster B (4 ↔ 5); H4; R-ASSERT; captured-portal |
| **2** | **evidence time** — the evidence's own temporal coordinate | per evidence *kind*: utterance → when said; document → its as-of; capture → render time (and the portal's stated as-of, where they differ — fenced); *and* import time kept beside it, never in its place | `Evidence.recorded_at` = **import clock** (`_now()` at append); `Entry.on` in payment_plan = effective (correct); **`ExpenseObligationVersion.effective_seq` + `recorded_seq`** — the dual pattern, shipped for amounts; `Plan.effective_from/to` | a document's own date is unrepresentable; `knowing[-1]` and `resolution()` are valid only by construction (H3); P-ack cannot be dated (K7); ties between same-party documents cannot be told from history (T3) | (a) an as-of on the artefact (a document has one date; all its readings inherit it) · (b) an as-of on each evidence item · (c) the `effective_seq / recorded_seq` pair generalised from obligation versions to evidence · (d) time on the reading (when read) *and* on the artefact (as-of) — two coordinates, because a re-read of an Aug 31 statement on Oct 1 has both | H3 (R2/R3); acknowledgment (dated P-ack); tie (recency axis); Cluster C (late discovery) |
| **3** | **reading identity** — so multiple readings of one artefact are one source | per reading: which artefact, when read, by what (parser version / person), what it yielded; and the rule that readings of one referent never corroborate | **`PdfExtractCache.extracted_json`** — exactly one reading per hash, shipped; **a re-parse overwrites or is refused, so the second reading of D3 cannot even be stored**; `Evidence` rows are readings without a referent | `attested[-1]` decides tax by scan order (R4); corroboration counts readings as sources (D1/D2, `distinct = {e.source}`); no parse dispute can be *represented*, only resolved by position | (a) a reading record beneath an artefact, evidence items pointing at readings · (b) a reading id on `Evidence` with the artefact id · (c) treat `PdfExtractCache` as the reading store and version it (hash + parser version) | H4 (reading-vs-source); Cluster B (parse dispute); R4; R-ASSERT (asserted referents have *no* readings — RA4) |
| **4** | **P-acknowledgment evidence** — the entitled party's stated position about a payment or balance, as of a date | a proposition kind whose subject is E; the payment it concerns (a named payment — the ledger's `Entry`); the stated balance; the as-of (row 2); the channel (E's statement · servicer-of-record · live system · user report — row 1's held/asserted plus an agency link); *attached-unacknowledged* as the state before it | **nothing.** `payment_plan.Entry` has no acknowledgment; `Evidence` has two health axes only; 1.x `debt_pdf_reconcile` computes `{implied, stated, diff}` once and discards it | discharge unrepresentable (H2); `remaining` asserts confirmation; the four-figures case cannot say which figure is E's | (a) P-ack as a proposition kind in the evidence model, evidenced by readings of E's artefacts (row 1–3) — *downstream of identity/time, per Rob* · (b) an acknowledgment entry kind in the payment ledger, referencing evidence · (c) both — the ledger holds *that* a payment is acknowledged and points at the evidence that says so | discharge; `remaining` (its required strength fenced); K8's balance-vs-computed diagnostic |
| **5** | **resolution provenance** — enough to tell source-history conflict from parse dispute | for each knowing event: *distinct source stance* or *reading of artefact X*; ordering on row 2's axis; a supersession relation where a document claims one (T4) | `resolution()` derives `kind · resolver · contradictions · post` from `(source type, bit)` in position order; **`ExpenseObligationVersion.supersedes_id`** — a supersession pointer, shipped, for amounts | one wrong row: D3b reported as `self_reversal by imported_eob`; positional ordering (H3); supersession claims unrepresentable (T4) | **nothing new** if rows 1–3 exist — provenance is *derived on read* from referent + reading + time, which is `resolution()`'s own principle (never stored); plus (a) a supersession relation between artefacts, on the `supersedes_id` pattern | narrator / export / backup (presentation); the reading-level kind (deferred) |
| **6** | **unresolved state** — where evidence cannot establish one conclusion | per consumer: the *fact* that is unresolved, its candidates, and no manufactured winner | **four consumer-local sentinels already exist:** `plan_year.UNKNOWN` · `allocation.UNRESOLVED` · `classification.UNAVAILABLE` · `payment_plan.REFUSED`; Q1's refusal-as-value carries `offered · reason · required · consumer` | none of the four says *what* is unresolved or *between what*; `year_summary.UNKNOWN` carries three truths (CC5); `plan_at` and `attested[-1]` manufacture instead of refusing | (a) keep consumer-local sentinels — the tie ruling says *unresolved is a state, not a rank, and each consumer fails closed its own way* · (b) a shared refusal shape (Q1's) carrying the candidates · (c) an unresolved *fact* in the evidence model (the two claimants, the priority sub-fact) with consumer-local terminals reading it | every consumer; H1 (refusal); R4; T3/T5; CC3 |

---

## 2. What the matrix says — one representation, or several?

**Rows 1, 2, 3, 5 are one family.** Referent, evidence time, reading identity, and resolution
provenance all attach to the **artefact → reading** pair, and row 5 needs nothing of its own
if the other three exist — it is derived, which is how `resolution()` already works. Both tests
in §0 are passed or failed *together* by any candidate for rows 1–3: Test 1 needs referent +
reading; Test 2 needs the artefact's as-of beside the import clock. **This family wants one
representation.**

**Row 4 is downstream, by Rob's rule and by the matrix.** P-ack is a *proposition kind* — its
subject is E — and it is evidenced by readings of E's artefacts. It needs rows 1–3 to be
well-formed (which statement, as of when, held or reported) and adds a proposition and a
ledger link. **It should not shape the family; it should consume it.** Candidate (c) — ledger
holds *that*, evidence holds *why* — keeps the payment module from inventing evidence
semantics, which the acknowledgment ruling's chain requires.

**Row 6 may want no shared representation at all.** The tie ruling: *unresolved is a state,
not a rank; each consumer fails closed in its own direction.* The code already has four
consumer-local sentinels, and the audit's repairs (H1's refusal, R4's `UNAVAILABLE`) add
refusals, not a shared state. What is missing is not a common object but **the unresolved
*fact*** — *two plans claim August*, *two readings of D1 disagree*, *priority between A and B*
— which lives in the evidence family (rows 1–3, 5) as a derived condition, and which each
consumer maps to its own terminal. So row 6 splits: the *condition* belongs to the family;
the *terminal* stays consumer-local.

**So: two representations and a set of local terminals, not one and not six.**

```text
EVIDENCE FAMILY      artefact (identity · held/asserted · as-of · supersedes)
                     reading  (of artefact · when · by what · yields)
                     evidence (a reading's claim on a proposition; or an utterance)
                     ─ resolution provenance derived on read
                     ─ unresolved conditions derived on read

DOWNSTREAM           P-ack as a proposition kind over the family + a ledger link

LOCAL TERMINALS      UNKNOWN · UNRESOLVED · UNAVAILABLE · REFUSED — kept, consumer-owned
```

---

## 3. What already exists, in the wrong place — findings, not proposals

- **`PdfExtractCache` is an artefact-and-reading store.** Content-hash identity, issuer, one
  parse. Shipped for debt statements in 1.x, unknown to the evidence model. It has exactly the
  shape rows 1 and 3 need and exactly the limitation D3 exposes: **one reading per hash** — a
  second parse cannot coexist with the first. Whether it *becomes* the artefact store or is a
  precedent for one is a design choice; that it exists is a fact the matrix would be dishonest
  to omit.
- **`ExpenseObligationVersion` already carries `effective_seq / recorded_seq / supersedes_id`.**
  Dual time and supersession, shipped, for amounts. The pattern rows 2 and 5 need is in the
  schema for a neighbouring entity. Reuse as a *pattern* is a candidate; reuse as a *table* is
  not proposed.
- **`ExpenseDetermination.evidence` is a `String(80)`.** The persisted determination's link to
  its evidence is a label. Whatever row 1 becomes, this column is where the persisted side
  currently loses the referent.

---

## 4. Track B — narrator boundary capability *(separate table, separate object not presumed)*

| requirement | information required | current holder | current loss | candidate locations | consumer |
|---|---|---|---|---|---|
| **may this cross into model-visible findings?** | for each item a surface would pass: its *kind* (category · total · annotation · description · …) and, for 2.0 facts, its sensitivity domain and whether the underlying classification was manufactured | `Sensitivity(domain, manufactured)` on `Classification` and `DerivedFact` — preserved through derivation, **dropped at `NarratorFacts`**; nothing on the 1.x findings at all | H5: safe by construction of inputs, unenforced; 2.0: the two-CVS figure reaches the narrator unmarked | (a) the **declaration at `callAI`** — ruled and authorised: kinds declared per gated call, fail closed on undeclared / free text; (b) a sensitivity carrier *beside* `NarratorFacts` for the gate's reader, never in the findings text (the ruled collapse) · (c) `_permitted_value` refusing on `manufactured` with Q1's reason — **deferred, needs the settled gate rule** | `callAI` (live); the 2.0 narrator (unwired); the gate |

**Track B does not require Track A's object.** The declaration needs no evidence
representation at all — it is a property of the *call*. The 2.0 carrier needs `Sensitivity`,
which already exists on the fact and is lost only at one projection. Neither needs referent or
time. **Adjacent; not merged** — Rob's correction holds in the matrix.

---

## 5. What this matrix does not decide

- Which candidate in any row. Every cell lists alternatives; none is preferred.
- Whether the evidence family is one table, three, or a pure-module dataclass set; whether
  `Evidence` is extended or replaced.
- `plan_at()`'s return shape · payment projection semantics · supersession *trust* · the
  claim-level narration policy · the 1.x discharge scope. All fenced, all untouched.
- Whether the four local terminals should ever converge. The matrix says they need not.

---

## 6. Next, in this mode — Rob's

The matrix's answer to the mode's question is **two representations and local terminals**.
The next design question it hands back, without answering: **for the evidence family, does
the artefact own its readings, or does the reading own its artefact reference?** That is the
first choice that makes Test 1 cheap or expensive, and it is the one the candidates in rows 1
and 3 actually differ on.
