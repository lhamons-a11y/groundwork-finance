# The role period — what is the temporal shape of a dated relation?

> Status: **Queue item 5 — RULED RP2 (§7); BUILT (`1321170`, no schema); ACCEPTED and CLOSED (§8).** Item 4 is closed at
> `6eb0623`. The party ruling fixed *roles are dated relations over parties, never parties*; the
> domain-proposition record found that *a period-bearing claim is not representable* and fenced
> the question — *whether a period is two coordinates on the proposition or two propositions
> (begins / ends) is a ruling the cases have not forced.* This record forces it, narrowly: the
> **temporal shape** of a role, and nothing else. Rob's framing for item 5: *its own narrow
> treatment — not introduced as infrastructure for something else*; and the rule carried from 4c:
> ***do not let the existence of `Plan` pre-answer the meaning of "covered under."***

**Stopping question:** *how does a role — a dated relation between a party and an identity —
carry its period, without the period becoming a mutable field, a piece of content, or a
derivation the substrate performs?*

**What this record does not decide:** which roles exist (the catalogue — *serves*, *entitled
party of*, *obligor on*, *provider of*, *insurer of*, *covered under* — is the domain's and each
needs its own semantics ruled); who is knowing for a role claim; what "in effect on d" answers
when stances conflict or overlap (item 7 / overlap policy); the restructure relation (item 6).

---

## 1. What is already ruled, and therefore constrains the answer

| Ruling | What it fixes |
|---|---|
| **Party ruling** | *roles are dated relations over parties, never parties*; *P is E, stops, is E again: still P* — the relation changed, the party did not |
| **Domain proposition D6 / D7** | the counterparty is a participant, the role name is the **kind**, nothing is content; *P is E of X at d* is a stance at **d**; *"S served P from March to June" is not one claim's content — a temporal operand is an operand*; a role kind that cannot carry its period would be ruled twice (**this record is that ruling**) |
| **Proposition shape** | immutable rows; the ruled temporal coordinate is **`as_of`** — *a stance as of d*, a column because it individuates the claim; `created_at` is row time, never event time; content opaque |
| **HISTORICAL_TRUTH T4 / T8** | *was true, and stopped being true earlier than we recorded* must be representable with **the effective boundary, the recorded time, and the prior belief preserved**; `as_of` must reproduce the record's view of periods, not only of terms; the current answer never depends on write order; overlap is a detectable state, never a silent tie broken by position |
| **OBLIGATION_LIFECYCLE rule 2** | *a discovered transition preserves both when the change became effective and when Groundwork learned of it* — period-close **may not collapse effective-at into learned-at** |
| **DECISION_DEPENDENCY_MAP 7** | period-close is decided by whether *ended earlier* has **different provenance and history semantics** from a correction of terms — not by API verbs; and 7 does not decide overlap policy (8) |
| **`utterance_retraction`** | a party withdraws its own utterance — *I was wrong* — distinct from *the world changed* |
| **Slice 5 / Ab7** | "X is false" is a domain negative; agreement and dispute are **derived**; no truth kinds |
| **Expense / plan rulings** | absence of a claim is absence, never a zero and never an inferred nonexistence (Pl15) |
| **Relational knowing** | roles are asserted; knowing is derived from them; the role-designated relations (*entitled party of O*, *insurer of X*) stay `undetermined` until the roles are ruled — **the period shape does not rule them** |
| **4c, carried** | the existence of `Plan` gives *covered under* an endpoint, not a meaning |

Two consequences before the cases. First, the T8 criterion already answers the provenance
question: *the beginning* and *the ending* of a relation are learned at different times, from
different sources, with different authority — the household enrolled in January and learned in
August from the insurer's letter that coverage ended in June. **Two facts with different
provenance are two claims** in this ontology; one row that fuses them is the `HealthPlan`
period defect at a new address. Second, the ruled coordinate `as_of` is *the date the stance is
about*, and every temporal thing the record already holds is a stance at a date. The question is
therefore whether a period needs anything the stance shape lacks.

---

## 2. The three things a role claim can say about time

Listening to how people speak about relations:

| Utterance | What it says about time |
|---|---|
| *"Harbor services our mortgage"* | the relation **holds at d** — d the date of the stance; nothing about when it began |
| *"Kim's been on the work plan since January 1"* | the relation **began at d** |
| *"The PPO ended June 30 — we thought it ran all year"* | the relation **ended at d**, learned later |
| *"Harbor serviced it from March to June"* | **two** boundary statements in one breath |
| *"Who was the entitled party when I paid in May?"* | a **question over stances** — a derivation |
| *"I was wrong, Harbor never serviced it"* | not a temporal statement — a **retraction** |

Three temporal sorts, and nothing else: **holds at**, **begins at**, **ends at**. A period is
never spoken as a primitive; it is spoken as two boundaries, or asked about.

---

## 3. The cases

| # | Case | Requirement it carries |
|---|---|---|
| **R1** | January: *Kim is on the work plan.* Nothing about since when. | a role stance with no boundary — **holds at d** — must be representable on its own |
| **R2** | *Harbor serviced the mortgage from March to June.* | one utterance, two boundaries; the period is what the two boundaries bound |
| **R3 (T4/T8)** | Jan–Dec on file. August 15: Lakeview Health's letter — coverage ended June 30. | effective boundary 6/30 · recorded 8/15 · prior belief (*running all year*) reproducible for a reader asking what the record held on 7/1 · **no row rewritten** |
| **R4** | *P is E, stops, is E again.* | three transitions; still P; no "current E" written anywhere |
| **R5** | Lakeview Health says coverage ended 6/30; the household says it ran through December. | two claims about the ending, different parties, different dates — a **dispute, derived**; nothing chosen |
| **R6** | *I was wrong — Harbor never serviced it.* | a **retraction** of the utterance behind the beginning; not an ending; the history that it was believed survives |
| **R7 (overlap)** | Kim's membership under P₁ begins 1/1; under P₂ begins 7/1; no ending recorded for P₁. | **detectable** by a consumer as two holding relations in August; never resolved by the substrate; never tied by which row was written first |
| **R8** | The debt is sold: E₁ ceases to be the entitled party 5/1; E₂ becomes it 5/1. | two roles' boundaries on one obligation; O continues; *sold* is another claim (item 6 territory) |
| **R9** | *Who was the entitled party when I paid on 5/12?* | a **derivation** over holds / begins / ends stances — computable from the record, **not computed by it** (item 7) |
| **R10** | *Kim is covered under the work plan* — entered after `Plan` exists. | the role's **endpoint** is P; its **meaning** (who may assert it; what it establishes for adjudication or knowing) is **not** given by P's existence — the catalogue entry is ruled separately |
| **R11** | The insurer's card: *Member since 01/01/2026*. | the artefact's line is a P-subject claim (the insurer's statement); a *begins at 1/1* claim about Kim ↔ P exists only when a party asserts it — reading never establishes a role |
| **R12** | An ending entered with no beginning on file. | representable: an ending is a claim like any other; the "period" it closes is a derivation's problem, not a referential requirement |

---

## 4. Testing the readings

### RP1 — one claim, two temporal coordinates (`effective_from` / `effective_to` on the proposition)

*"S served P from March to June"* as one row. It fails on the constraints it was meant to serve:

- **R3 fuses two provenances into one row.** The beginning (household, January) and the ending
  (insurer, August) have different sources, dates and authority; one row carries one evidence
  set per claim. To record the ending, RP1 must write a *second* full-period row (Jan–Jun 30)
  beside the first (Jan–Dec) — two claims about one relation, differing in a coordinate, with
  the beginning duplicated. The record then holds the ending only as a *difference between two
  rows*, which a reader must diff to find. That is the DECISION_DEPENDENCY_MAP criterion failed:
  *ended earlier* is not given its own provenance.
- **R1 has nothing to put in the coordinates** — *holds at d* is a stance, not a period; RP1
  needs NULLs, and a NULL `effective_to` is the ambiguity the substrate refuses (*no end yet* /
  *end unknown* / *end not asserted*).
- **R5's dispute becomes a dispute over whole periods** rather than over the ending, hiding what
  is actually contested.
- It adds two columns that every non-role kind never uses, and makes the **period** — a derived
  thing — structural.

### RP3 — point stances only (*holds at d*); boundaries never stated; the period derived

Minimal, and already representable. But it cannot say what people say:

- **R3's "ended June 30"** becomes *does not hold on 6/30* — a point, not a boundary; the
  reader must infer the transition from the neighbouring *holds* stance, which is a **policy**
  (latest-stance-governs, interpolation) the substrate must not own.
- **R2** cannot be stated at all without inventing sample points.
- Negation must live somewhere — in content (*forbidden for roles: nothing is content*) or as a
  negative kind (*forbidden by slice 5: no truth kinds*).

### RP2 — boundary stances: *holds at d*, *begins at d*, *ends at d*, each a proposition with `as_of` = d

Every case has a representation, and each constraint is met by machinery that already exists:

- **R1** — a *holds at* stance: the kind, the party subject, the identity object, `as_of`. This is
  D7's ruled shape, unchanged.
- **R2** — one utterance evidences two claims (*begins at 3/1*, *ends at 6/30*) — the pattern
  already used when one utterance mints an expense and evidences four claims about it.
- **R3** — *ends at 6/30* is a claim with its own evidence (Lakeview Health's letter, via the household's
  assertion or the artefact's reading as candidate), `as_of` = 6/30 (**effective**),
  `created_at` = 8/15 (**learned**), the *begins at 1/1* row untouched (**prior belief
  preserved**): a reader asking what the record held on 7/1 filters by `created_at` and finds a
  beginning and no ending. Nothing rewritten; effective-at never collapsed into learned-at.
- **R4** — begins · ends · begins: three claims, three dates; P unchanged.
- **R5** — two *ends at* claims (6/30 by Lakeview Health; 12/31 by the household): the dispute is derived
  from two same-kind, same-participant claims with different `as_of` — nothing chosen.
- **R6** — `utterance_retraction` of the utterance behind *begins at* — already ruled, distinct
  from an ending; the beginning's history survives.
- **R7** — two *begins at* with no *ends at* for one party under two plans: a consumer sees both
  holding in August. **The substrate represents the state; it neither refuses nor resolves it**
  — overlap policy (8) stays open, as the dependency map showed it may.
- **R8** — *E₁ ends at 5/1*, *E₂ begins at 5/1* — two claims on O; nothing on the obligation
  anchor; the sale is another claim.
- **R9** — computable: order the stances for (party, kind, identity) by `as_of`; answer for d.
  **Not computed here.**
- **R10** — the shape gives *covered under* an `as_of`, a party subject and a plan object. It
  gives it **no meaning**: whether the insurer's or the household's assertion establishes it,
  what it licenses for adjudication, whether it is knowing-designated — each is the catalogue
  entry's own ruling. `Plan` supplies the endpoint; nothing more.
- **R11** — the card line is P-subject; a *begins at* about Kim ↔ P is established only by a
  party; `reading_establishes` stays False for role kinds.
- **R12** — an ending without a beginning is a claim; the derivation, not the substrate, notices
  the gap.

**Where the sort lives.** Three temporal sorts, two ways to carry them:

- **(a) as kinds** — `serves` · `serves_begins` · `serves_ends`, with the registry linking the
  boundary kinds to their role (`'boundary': 'begins' | 'ends'`, `'of': 'serves'`), and
  requiring `as_of` on boundary kinds. No schema; the catalogue grows by two entries per ruled
  role; consumers find boundaries through the registry, generically.
- **(b) as a column** — a nullable `boundary` ∈ {`begins`, `ends`} on every proposition, NULL
  meaning *holds at*. One column, mostly NULL; NULL carrying meaning is what the substrate has
  refused everywhere else (the four-state readings; the two-slot reader).

**(a) is the smaller and the more consistent**: the sort is part of *what is claimed* — *that it
began* is a different claim from *that it holds* — and what is claimed is the kind. It is also
what the domain-proposition record already said: *the role name is the kind; nothing is content*.
The linking metadata makes the pairing structural rather than a naming convention.

### The result, stated against the fenced question

*Whether a period is two coordinates on the proposition or two propositions* — **two
propositions, and not even a new sort of proposition: a beginning and an ending are dated
stances like every other dated stance the substrate holds.** The period is what a reader derives
between them. Nothing new is needed to represent it; what was missing was the ruling that a
period is never written.

---

## 5. What a build would be — if ruled, and not before

Named so the boundary is visible:

- **no anchor, no column, no migration**;
- the `RULED_KINDS` registry admits two optional entries — `boundary` (`'begins'` | `'ends'`) and
  `of` (the role kind it bounds) — with a guard: a boundary kind requires `as_of`, and its slots
  must equal its role's slots;
- **no role kind is ruled by this slice** — the fixture uses stand-in kinds (`serves`,
  `serves_begins`, `serves_ends` over party ↔ party; `stands_in_covered_under` over party ↔ plan,
  named as a stand-in) to exercise R1–R12: holds-at alone; one utterance two boundaries; the
  T4/T8 replay by `created_at` with the prior belief reproducible; three transitions; the
  disputed ending as two claims; retraction ≠ ending; overlap represented and not resolved; the
  ending without a beginning; `reading_establishes` False; **the absence of any period column, any
  `in_effect_on` / `current_role` / `period_of` accessor, and any ruled real role kind**;
- the existing per-kind guards apply unchanged (slot discipline, immutability, one-source
  about-ness).

**Not in it, whatever the ruling:** the role catalogue (*serves*, *entitled party of*, *obligor
on*, *provider of*, *insurer of*, **covered under**) and each role's semantics · knowing for
role claims · the "in effect on d" derivation · overlap policy (refuse vs report) · the resolver
over disputed boundaries · the restructure relation · legacy `PersonEnrolment` /
`PersonAssignment` / `HealthPlan` period decomposition.

---

## 6. Ruling candidate — for Rob

> **A role's period is never written. A role — a dated relation between a party and an identity
> — is carried by dated stances of three sorts, each a proposition whose `as_of` is the date it
> is about: that the relation *holds at* d, that it *began at* d, that it *ended at* d. The
> sort is part of what is claimed and therefore lives in the kind: a role's beginning and
> ending are kinds bound to the role kind in the registry, not coordinates on a claim and not
> content. A beginning and an ending have their own provenance, their own evidence and their own
> recording time, so a transition discovered late is a new dated claim recorded now about a
> boundary then — the prior belief survives untouched and effective-at is never collapsed into
> learned-at. A withdrawn beginning is a retraction, not an ending. Two claims about one
> boundary are a dispute, derived; two relations holding at once are a state the record shows
> and neither refuses nor resolves; which relation held on a date is a derivation over the
> stances and is not performed by the substrate. Absence of an ending is absence, not
> "ongoing" and not "unknown." This rules the temporal shape of every role and the semantics of
> none: no role kind is ruled here, and the existence of an endpoint — a party, an obligation,
> a plan — gives a role no meaning.**

**If ruled: the build is the registry's two boundary entries with their guard, and a fixture on
stand-in kinds — no schema.** **Outside it:** the catalogue and every role's semantics · knowing
· "in effect on d" · overlap policy · the resolver · item 6 · legacy.

*The line: a relation is not a line on a calendar; it is what people said about when it held,
began and ended — and the calendar is drawn from that, never written into it.*

---

## 7. Ruling — Rob, 2026-09-14: RP2 / build authorised

*A good stopping point because the record has separated the temporal semantics from the
particular role catalogue. `effective_from` / `effective_to` on a future role table must not
creep back in.*

**The decisive distinction:** *a role has no stored period; its temporal history is represented
by propositions about when that role began or ended.* Holds-at is a question / derivation, not a
stored interval; began-at and ended-at are separate claims about boundaries; `as_of` says when the
asserted fact is about, the utterance / recording time says when we learned it; a late discovery
does not rewrite history; absence of an ending remains absence; overlap remains representable; a
disputed ending remains multiple claims — **the ontology must not manufacture a continuous
interval from two point claims merely because humans commonly read one that way.**

**RP1 stays dead** — stronger than "NULL is awkward": it makes a derived temporal interpretation
look like intrinsic structure of the claim. Household says began January 1; insurer says ended
June 30; household learns of it in August — distinct assertions with different provenance and
potentially different epistemic status, not one proposition with two coordinates.

**RP3 stays dead** — point stances leave an unspoken interpolation rule (*covered on 1/1* and
*covered on 3/1* license nothing about 2/1), silent consumer logic the substrate must not
smuggle; and "ended" cannot be reconstructed from a later negative stance without deciding what
the negative means temporally.

**The constraint on the registry (accepted with the build):** `boundary = began / ended` and
`of = the role kind it bounds` are acceptable, **provided the guard enforces the relationship
between the boundary kind and its role kind** — the registry must not become *anything can be a
beginning of anything*, or the ambiguity has moved rather than been solved. The guard establishes
**structural validity only** — *this boundary kind is permitted to bound this role kind* — and
never that the role actually began or ended, never resolves disputes, infers a period, or
decides overlap.

**R10 correctly fenced:** *Kim is covered under the work plan* gets the endpoint and the `as_of`
machinery without item 5 deciding what "covered under" means. Item 5 establishes the temporal
grammar; it does not establish membership, enrollment, coverage, knowing for the role, overlap
resolution, effective-status consumers, plan membership, or plan / expense relationships. The
later role ruling decides meaning first, then uses the ruled temporal machinery.

**Retraction vs ending, pinned:** retracting *Kim was covered beginning January 1* is about the
assertion and does not mean *Kim's coverage ended on [some date]*; an insurer's *coverage ended
June 30* is a boundary claim, not a retraction of earlier coverage propositions. This prevents a
large class of lifecycle bugs.

**The ruling, as pinned by Rob:**

> **A role has no intrinsic period. Temporal boundaries are propositions in their own right: a
> ruled beginning or ending kind, bound to the role kind it temporally qualifies, with `as_of`
> identifying the date asserted about. Boundary claims preserve their own provenance and
> learned-at time. A beginning or ending does not rewrite prior claims, imply the opposite
> boundary, resolve disputes, establish continuous effect, or itself create a role.**

**Build authorised — appropriately tiny:** no schema change · the two registry metadata fields
with their guard · a fixture of the structural discipline on stand-in role kinds · no actual role
kind · no membership semantics · no temporal consumer · no resolver · no overlap policy · no
item 6 relation work. **Item 5 — ROLE PERIOD: RP2 ACCEPTED / RULED.** Stop at that boundary;
then item 6 addresses the relation families accumulating behind the identity rulings.

---

## 8. Slice accepted and closed — Rob, 2026-09-14. `1321170`, 977 green, clean tree.

*The implementation matches the RP2 ruling unusually tightly; no semantic leak warrants reopening.*

- **No intrinsic period** — no `effective_from/to`, interval, period table or equivalent state.
- **Boundary = proposition** — `began` and `ended` are distinct kinds with their own provenance
  and `created_at`; **`as_of` does the right job** — the date the boundary is about, not a
  substitute for learned-at.
- **Binding is structural, not semantic** — a boundary kind must identify a ruled role kind, use
  the same participants, and be exactly `began` / `ended`; the import-time check is a good
  additional integrity measure.
- **No role creation · no historical rewriting (R3: the 6/30 ending learned 8/15 does not alter
  what could truthfully be replayed as of 7/1) · no inference of the opposite boundary · no
  resolution (two endings remain two claims; two beginnings remain representable) · no
  interpolation (*holds at d* stays a future derivation) · retraction remains retraction (R6) ·
  reading remains non-establishing (R11) · no role semantics smuggled (the stand-ins are the right
  mechanism; `standin_covered_under` rules nothing) · knowing remains undetermined · legacy periods
  untouched · the mutation suite is meaningful** — the two escaped mutations were caught by
  strengthening the fixture, not weakening the implementation.
- **The strongest part, architecturally:** `boundary_kinds_of(role_kind)` reads the registry rather
  than discovering boundaries by naming convention — the temporal grammar is discoverable without
  the registry becoming a temporal engine.

**Fence recorded explicitly (Rob):** the registry's `boundary` / `of` metadata does **not** mean a
role kind has temporal semantics merely because somebody registers it that way. It says only:
*if this is a ruled role kind, these ruled proposition kinds are its beginning / ending boundary
kinds.* It does not establish the role, establish a boundary claim, calculate a period, or answer
whether the role holds at a date.

**Item 5 — ROLE PERIOD: CLOSED.** RP2 implemented exactly within its authorised scope: no schema
change · no role catalogue · no membership / enrollment semantics · no `in_effect_on` · no
overlap resolver · no knowing rule · no item 6 relation family · no consumer derivation.
967 → 977 is the expected increment; the tree is clean.
