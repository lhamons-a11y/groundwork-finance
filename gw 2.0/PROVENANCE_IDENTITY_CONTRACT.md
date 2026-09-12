# Provenance identity — the minimum contract, and whether source lineage is already defined

> Status: **Design mode, 2026-09-12. No code, no object model, no fields.** Rob opened the
> primitive question by *not* choosing an object model: the thing to rule is the minimum
> **identity contract** any eventual schema must satisfy. His primitive:
>
> ```text
> Provenance identity
> ├── source lineage
> ├── artefact identity
> └── reading identity
>
> source ──produced/owns──► artefact ──has──► reading ──supports──► proposition
> ```
>
> with source lineage and artefact identity **kept as different dimensions**, three
> mechanically testable questions, and one hard invariant:
>
> | question | must answer |
> |---|---|
> | is this the same artefact? | yes / no |
> | is this the same reading of that artefact? | yes / no |
> | do these observations have independent provenance? | yes / no / **not established** |
>
> > **A reading is never an independent source merely because it has a different
> > capture/source type, and two artefacts are never independent merely because they have
> > different artefact instances.**
>
> None of the three answers may be reconstructed from `USER_STATED`, `IMPORTED_EOB`, row count,
> or insertion order. Outside the primitive, deliberately: evidence time · P-ack · supersession
> · resolution kind · unresolved representation · strength · proposition identity. No generic
> "Evidence ID".
>
> **The question this document answers:**
>
> > **Can the minimum semantics of *source origin / lineage* be defined from the existing
> > rulings and cases, or does that require another case pass?**
>
> The four things to keep distinct, from Rob's framing: **capture channel** (how Groundwork
> obtained it) · **source origin** (the party responsible for the evidence) · **artefact** ·
> **reading**. K5 proved capture channel ≠ source origin. What the cases say beyond that is
> traced below, clause by clause.

---

## 1. What the record already fixes about origin — traced

Each clause names the ruling it comes from. Nothing here is proposed; it is collected.

**C1 — Origin is *the party whose knowledge the reading ultimately conveys*, and it is fixed
per proposition kind.**
- Health: `KNOWING_SOURCES = {USER_STATED, IMPORTED_EOB}` for the stated reason that *"each has
  first-hand knowledge of the health proposition — the user was there; the insurer adjudicated
  the claim"* (`ACKNOWLEDGMENT_EVIDENCE_CASES.md` §0, reading the code's own comment). Two
  parties: the user, the insurer.
- P-ack: *"one knowing party, four channels"* — E, reached by E's statement, the servicer of
  record, a live system, or the user's report (ruled). The user is **not** knowing for P-ack:
  *"the user does not independently know what E acknowledges"* (K5).
- So the set of knowing origins is a property of the **proposition kind**, and the same party
  can be an origin for one proposition and a mere channel for another: the user *originates*
  *"it was health"* and *relays* *"the statement says $1,925"*.

**C2 — Capture channel is how the reading reached Groundwork, and it never determines origin.**
- K5: `USER_STATED` carrying *"I saw the EOB say $412"* has origin **insurer**, channel
  *user utterance*. The built `distinct = {e.source}` reads channel as origin — the shipped
  defect (`REPRESENTATION_CANDIDATE_MATRIX.md` row 7).
- Captured-portal ruling: capture changes reproducibility and *"does not create a new
  knowledge channel"* — and a fortiori not a new origin.
- R-ASSERT: an utterance about a document is testimony **about an artefact**; the artefact's
  origin is the source's, the utterance's channel is the user's.

**C3 — Origin can be *mediated*, and each mediation link is an asserted relationship with its
own strength; the chain's strength is weakest-link.**
- K2: the servicer's statement is E's acknowledgment *"bounded by the household's evidence that
  the servicer actually serves E"* — origin E, mediated by S, the link asserted by the
  household. Ruled: *"the weakest-link mechanism transfers."*
- K3: S3's statement has the **same claimed chain** and the link is false — indistinguishable
  at the moment of recording; corrected by *conflict* with E's own statement, never by rank.
- C2 (captured portal): the chain runs *capture states X* → *the portal displayed X* (asserted:
  faithful) → *S's position* → *P's position* — *"one link longer than K2."*
- So a lineage is **origin + a chain of asserted links + the channel at Groundwork's end**, and
  the chain is data, not a type.

**C4 — Independence is between *origins*, for a given proposition, and it is three-valued.**
- `DOCUMENT_IDENTITY_CASES.md`: *"source instance ≠ source independence. Two EOBs from one
  insurer, for one claim, are two artefacts and **not** independent evidence… whether two
  artefacts are independent is a further fact about their provenance, and the record must be
  able to hold *unknown* there too."* Distinct artefacts: necessary for some independence,
  never sufficient — Rob's invariant, second half.
- `4 → 6` (ruled): *"multiple readings of one referent cannot constitute independent
  corroboration"* — Rob's invariant, first half.
- K7: *"two channels agreeing are not corroboration — there is one knowing party for P-ack."*
- U5/D7: a second letter creates **no relationship**; *unresolved* is the default. An artefact
  whose chain to any origin is unasserted has independence **not established** against
  everything.
- So: **same origin → not independent; distinct origins, both knowing for the proposition, both
  chains established → independent; any chain unestablished → not established.** Never *yes*
  from artefact count, reading count, row count, or channel type.

**C5 — What a lineage must be comparable on, and what it need not be.**
The three questions require *same / different / unknown* for artefacts, for readings, and for
origins. They do **not** require origins to be entities with attributes, artefacts to have
generated ids, or readings to be persistent rows. Comparability is the contract; identity
mechanism is the schema. (Rob's not-decided list: *whether `source` becomes an entity*.)

---

## 2. The contract, stated once

> **Provenance identity is a lineage: an origin (the party whose knowledge the reading
> conveys, fixed per proposition kind), a chain of asserted links from that origin to the
> artefact Groundwork encountered, the reading of that artefact, and the channel by which it
> arrived. Two lineages are independent for a proposition iff their origins are distinct,
> both knowing for that proposition, and both chains established; not independent iff their
> origins coincide; and not established while any chain is unasserted. No part of this may be
> derived from capture type, artefact count, reading count, or record position.**

Run against the tests:

```text
D1 → R1: $412 · D1 → R2: $4.12      same artefact, different readings   → parse dispute; NOT independent (4→6)
D1 → R1: $412 · D2 → R2: $4.12      different artefacts                 → conflict POSSIBLE; independent
                                                                          only if origins distinct (DI)
E's statement · S's statement       different artefacts, one origin      → not independent (K7, C3)
E's statement · user reports it     different channels, one origin       → not independent (K5)
user "it was health" · the EOB      two origins, both knowing            → independent (health tie's reason)
a letter with no chain to anyone    origin unasserted                    → not established (U5/D7)
```

Every row is a ruled case; the contract adds no new answer to any of them.

---

## 3. The answer: defined from the record — with one part fenced, not missing

**Yes, the minimum semantics of source origin/lineage are already fixed by the existing rulings
(C1–C4).** No new case pass is needed to state the contract, and no existing case contradicts
it. What the cases do *not* fix, and where the line is:

**Fenced, and correctly so — reader independence for P-subject (RA5).** For propositions
about the *world* (health, P-world, P-ack), readings of one artefact never multiply sources —
that is the invariant. But P-subject's subject is the artefact itself, and there a second
*reader* is how a parse dispute gets resolved (the Cluster B ruling: *re-reading resolves what
A says*). Two household members independently reading one statement are two observations of
the artefact's content. Whether that is *corroboration of P-subject* was fenced at RA5 (*same
subject only*), and this contract leaves it fenced: **the independence clause above is stated
for propositions about the world; it does not decide independence of readers with respect to
what a document says.** That is the one place a case would be needed — and only if P-subject
corroboration ever matters to a consumer.

**Not determined, by design — the identity mechanism.** The contract requires origins,
artefacts and readings to be *comparable*; it does not say how. Whether origin is a party
entity, a string, or a reference; whether artefact identity is a content hash or an assigned
id; whether readings persist — all downstream, exactly as Rob's not-decided list has them.

**Not determined — and worth naming so it is not smuggled in:** the contract's *asserted
link* (servicer-of-record serves E; the capture is faithful; the user's report is of *that*
statement) is an evidentiary relationship with a strength. That strength is the evidentiary
relationship's, outside the primitive by Rob's ruling. The primitive holds *that a link is
asserted*; it does not hold *how well*.

---

## 4. What the contract changes about the matrix, without redrawing it

Row 7's *current holder* — `distinct = {e.source}` — is now precisely describable: it computes
independence from **channel type**, which C2 forbids, and it has no notion of a chain (C3) or of
per-proposition knowing sets beyond the health enum (C1). Any candidate for rows 1, 3 and 7
is scored against §2's contract, not against the code it replaces.

---

## 5. Decision remaining — Rob's

Whether §2 is the contract — the minimum identity/lineage semantics every eventual schema must
satisfy — with reader-independence for P-subject explicitly left fenced, and the identity
mechanism explicitly left to the next question. If so, the next question is the one Rob
named as the last before fields: **what identity mechanism makes origin, artefact and reading
comparable** — and that is the first question in this mode whose answer is a representation.
