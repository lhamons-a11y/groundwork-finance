# Identity mechanism comparison — candidates against the contract's tests

> Status: **Design mode, 2026-09-12. No code, no schema. Ends in a ruling candidate, not an
> implementation.** The question, ruled open in `PROVENANCE_IDENTITY_CONTRACT.md` §5:
>
> > **What identity mechanism makes origin, artefact, and reading comparable while preserving
> > the distinction between them?**
>
> **The tests every candidate is run against** (from the ruling): **T-A** readings of one
> artefact ≠ independent sources · **T-B** two artefacts with one origin ≠ independent
> provenance — *non-negotiable* · **T-C** one artefact with two readings distinguishable from
> two artefacts with one reading each, without order or enum · **T-D** stable identity across
> time — same real artefact through a different arrival and a different reading is *one*
> artefact; a different real artefact from the same origin is *two* artefacts, one origin.
>
> **Rejected as identity itself:** source enum · import event · row position · reading content
> alone · filename alone · timestamp alone · number of observations. Attributes a mechanism
> may *use*; never sufficient.
>
> **Method.** Three things need identity — artefact, reading, origin. For each, the candidate
> mechanisms that exist in the code or the rulings, and for each candidate: what makes two
> things *same*, what makes them *different*, how *unknown* is expressed, and which tests it
> passes. Lineage and independence are then checked as *derivations* over the three, since the
> ruling says lineage is not an identity object.

---

## 1. Artefact identity — *which particular thing was observed?*

Must be comparable across arrivals (T-D), must not be the file, the source type, or a reading.

| candidate | same when | different when | unknown | T-C | T-D | rejected-basis? |
|---|---|---|---|---|---|---|
| **A1 — content hash of held bytes** (`PdfExtractCache.source_hash`, shipped) | identical bytes | any byte differs | no bytes held (asserted referents) — **no identity at all** | ✓ for held | **✗** — the same real statement as a downloaded PDF, a phone scan, and a portal capture are three byte-strings → three artefacts; and *"the March EOB"* asserted has no hash | filename no; but **identity = bytes** conflates artefact with file — the captured-portal ruling's *artefact ≠ file* |
| **A2 — the issuer's own identifier** (statement no., claim no., EOB id) | the issuer's id matches | differs | absent for captures, utterances, many letters; issuers reuse ids | ✓ when present | ✓ when present — the strongest cross-arrival evidence there is | no — but availability is the source's gift, not Groundwork's |
| **A3 — individuating description** (issuer · date · kind — RA1) | descriptions match *and the match is unique in the candidate set* | descriptions differ | ambiguous when two candidates match (RA2 — **non-monotonic**) | ✓ | partial — two arrivals with the same description *may* be one artefact; the description cannot say | no — but *same description = same artefact* is a listed must-never-infer |
| **A4 — assigned artefact identity, with A1/A2/A3 as *correspondence evidence*** — an identity Groundwork mints on first encounter; later arrivals are linked to it by a **correspondence claim** (hash equality · issuer id · description match · the user confirming *"yes, that's the one"*), each claim carrying its own strength | linked by an established correspondence | no correspondence asserted | **expressible**: a new arrival with no established correspondence is a new artefact *or* an unlinked one — *not established* (D7's default) | ✓ | ✓ — the only candidate that makes *same real artefact, different arrival* representable, because the correspondence is a claim, not a computation | none — identity is minted, not derived; the rejected bases become **evidence for correspondence** at graded strength |

**Finding A.** A1–A3 each fail T-D in a different way and for the same reason: they make
identity a **function of an attribute** — bytes, an issuer's string, a description — and every
attribute either changes across arrivals (A1), is sometimes absent (A2), or is non-unique (A3).
**A4 passes T-D by refusing to compute identity from any attribute.** It mints an identity and
treats every "this is the same artefact" as an **asserted correspondence with a strength** —
which is exactly the R-ASSERT ruling's *asserted → held upgrade stays fenced: the system must
not silently turn "the Sept 1 statement" into a held statement merely because a later artefact
matches the description*, and C9's *confirm, don't infer*. Under A4, A1 is strong
correspondence evidence (byte-identical), A2 is strong where present, A3 is weak and
candidate-relative, and a user's confirmation is an assertion like any other. **Held vs
asserted** becomes a property of the artefact identity (does Groundwork hold bytes of it?),
not a different kind of identity.

---

## 2. Reading identity — *which observation of that artefact produced this proposition?*

Must be owned by its artefact (ruled), must not be the artefact, must never count as a source.

| candidate | same when | different when | T-A | T-C | rejected-basis? |
|---|---|---|---|---|---|
| **R1 — content-derived** (a hash of the extracted values; `PdfExtractCache.extracted_json` is one such, and it is why a re-parse *cannot coexist* there) | identical extraction | any value differs | ✓ (readings are under an artefact) | **✗ partially** — two identical parses collapse to one reading, hiding that two observations occurred; and when does *when read / by what* live? | **reading content alone — rejected** |
| **R2 — the observation event** (artefact · reader or process · when read), an identity per act of reading | the same act | different acts, even if they yield identical values | ✓ | ✓ — two readings of D1 are two events under D1; R1 of D1 and R2 of D2 are events under different artefacts | none — timestamp is an *attribute* of the event, not its identity; two readings at one instant by two readers are two events |

**Finding R.** R2 is the only candidate consistent with the ontology ruling (*a reading is an
observation/interpretation of that thing*): identity of an *act*, owned by the artefact it is
an act upon. R1 is the shipped store's shape and the D3 limitation in one. Under R2, a
re-parse that yields the same values is still a second reading — which is right: it is a
second observation, not a second source (T-A), and the record can say *read twice, agreed*.

---

## 3. Origin identity — *whose knowledge does this proposition convey?*

Must be comparable (same · different · unknown), fixed per proposition kind, never the channel.

| candidate | same when | different when | unknown | T-B | rejected-basis? |
|---|---|---|---|---|---|
| **O1 — the capture enum** (`USER_STATED`, `IMPORTED_EOB`) — the shipped mechanism | same enum | different enum | cannot express | **✗ — the defect.** Two EOBs from one insurer: same enum ⇒ same origin (right by accident); the user relaying the EOB vs the EOB: different enums ⇒ different origins (wrong) | **source enum — rejected** |
| **O2 — a name string** (`PdfExtractCache.issuer`, `DebtAccount.name`) | string equality | inequality | absent string — but *absent* and *different* both read as "not equal" | ✓ when spelled consistently; ✗ on *"Lakeview Health"* vs *"AETNA INC"*; and unknown collapses into different | not listed, but identity by spelling is filename-alone's cousin |
| **O3 — a role per proposition kind** (*the user* · *the insurer* · *the provider* · *E of obligation X*) | same role instance | different | a role with no instance | partial — passes for one insurer; **fails under concurrent coverage**: two insurers are one role and two origins, so role without instance cannot say *different* | no |
| **O4 — a party reference**: an identity for each party the household deals with — household members (`Person`, exists), the entitled party of an obligation (exists as doctrine; entitlement over time is ruled), insurers and providers (no entity today; `issuer` strings), a servicer (the servicer of record, asserted) — with origin recorded on the artefact as *which party*, and the per-proposition knowing sets stated over parties | same party | different party | **a party reference may be absent — *origin not established*** — and absent is distinct from different | ✓ — E's statement and S's statement both trace to party E (through S's asserted agency); two EOBs from party *Lakeview Health* have one origin; the user's report of the EOB has origin *Lakeview Health*, channel *user* | none |

**Finding O.** O1 is rejected by the ruling. O2 and O3 each fail one live case (spelling;
concurrent coverage). **O4 is the only candidate that expresses all three values** — same,
different, and *not established* as a distinct state — and it is the one the contract's C3
(mediation chain) needs, because a chain is a sequence of *parties* with asserted links
between them, and a chain's links cannot be stated over strings or roles. It requires one
thing the record does not have: an identity for non-household parties. Whether that is a
table, a reference, or a value is the schema; that it must be *comparable and absent-able* is
the contract.

---

## 4. Lineage and independence — derivations, not identities

With A4, R2 and O4 the ruling's two derived questions are computable without touching order,
enum, or counts:

```text
lineage(reading)      = origin(artefact(reading)) · [asserted links: party → … → artefact] · channel
independent(r1, r2, P) =
    origin(r1) and origin(r2) both established, both knowing-for P, and different   → yes
    origin(r1) = origin(r2)                                                          → no
    either origin not established, or any link in either chain unasserted          → not established
```

Run against the four tests and the contract's rows:

| test | A4 + R2 + O4 |
|---|---|
| T-A | R1, R2 are events under one artefact identity → one origin → not independent ✓ |
| T-B | D1, D2 are two minted identities; `origin(D1) = origin(D2)` is a party comparison, not an enum → not independent ✓ — **`distinct = {e.source}` cannot be reproduced under this mechanism** |
| T-C | one artefact with two reading events vs two artefacts with one each — structurally different, no order or enum consulted ✓ |
| T-D | a re-import: a new reading event; whether under the *same* artefact identity depends on an asserted correspondence (hash match → strong; user confirms → asserted; nothing → a new identity, linkable later) ✓ — and a second statement from the same insurer: a new identity, same origin party ✓ |
| K5 (user relays the EOB) | reading event, channel *user*, artefact = the EOB (asserted correspondence to a held or described EOB), origin = the insurer → not independent of the EOB's own reading ✓ |
| K3 (S3, never authorised) | artefact from party S3, asserted link S3 → E — the link is a claim with a strength; if E's statement conflicts, the conflict surfaces; the link is not *ranked* away ✓ (K3's ruling) |
| RA6 (below individuation) | no correspondence can be asserted, no origin party named → artefact identity *not minted* or minted-unlinked; origin not established ✓ |

**No rejected basis is load-bearing anywhere in the derivation.** Bytes, issuer ids,
descriptions, timestamps, and counts appear only as correspondence evidence or event
attributes.

---

## 5. What the comparison establishes, and what it does not

**Establishes:**
1. **Artefact identity must be minted, not derived** (A4). Every attribute-derived identity
   fails T-D; the ruled *confirm, don't infer* rule is what A4 is.
2. **Correspondence is a claim with a strength**, and held/asserted is a property of the
   artefact, not two identity kinds.
3. **Reading identity is the observation event**, owned by its artefact (R2); content-derived
   reading identity is the D3 limitation.
4. **Origin identity requires a comparable, absent-able party reference** (O4); enum, string
   and role each fail a live case.
5. **Under A4 + R2 + O4, independence is a party comparison over established chains** and
   T-B's kill of `distinct = {e.source}` is structural, not a rule someone remembers.

**Does not establish — and must not be read as deciding:**
- whether the party reference is a `Party` table, a reference into existing tables (`Person`,
  the obligation's entitlement), or a value; whether insurers/providers become rows;
- whether artefact identities are integers, UUIDs, or composite; whether readings persist as
  rows or are reconstructed;
- how a correspondence claim is stored, or its strength scale (the evidentiary relationship's);
- whether `PdfExtractCache` becomes the artefact store or is migrated into one;
- anything about evidence time, P-ack, supersession, unresolved, or strength — outside the
  primitive by ruling.

---

## 6. Ruling candidate — for Rob

> **Identity is minted and owned: an artefact identity Groundwork assigns on first encounter,
> owning its reading identities (one per act of observation), and carrying an origin as a
> comparable party reference that may be absent. Every "this arrival is that artefact" is an
> asserted correspondence with a strength, never a computation from bytes, description, or
> file; held vs asserted is a property of the artefact, not a second identity kind. Lineage
> and independence are derived over these three and consult no enum, order, or count.**

If ruled, the next question is the first that touches a table: **what the party reference
is** — because it is the one identity the record lacks entirely.
