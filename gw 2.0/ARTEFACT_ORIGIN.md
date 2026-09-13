# Slice 3 — what proposition establishes an artefact's origin?

> Status: **Build mode, slice 3 opened by Rob 2026-09-13 — record only, no code.** Slice 2 is
> accepted at `9cdb4e6` (`ARTEFACT_READING_SLICE.md` §9). This record answers one question by
> testing three readings of it against the cases already ruled, finds the dependency the answer
> forces, and ends with a ruling candidate. Nothing here is authorised to build.

**Rob's question, verbatim:** *what proposition establishes an artefact's origin?*

Rob's framing when he fenced it out of slice 2: *what proposition establishes an artefact's
origin, and what evidence is sufficient to establish it? — not another schema question
disguised as implementation.* And the reason it was fenced: the reading's strength is
`undetermined` without it, and *the need for a value downstream is not evidence that the
proposition kind is already ruled.* So the kind must be earned here, from the cases, or the
reading's strength stays `undetermined` and that is the honest result.

---

## 1. What is already ruled, and therefore constrains the answer

Six rulings bear on this question directly. None answers it; together they leave little room.

| Ruling | What it fixes |
|---|---|
| **C1** (`PROVENANCE_IDENTITY_CONTRACT.md`) | origin is *the party whose knowledge the reading ultimately conveys*; the same party can originate one proposition and merely relay another |
| **C2** | the capture channel never determines origin — a user's utterance carrying "I saw the EOB say $412" has origin *insurer*; the reader of an artefact is a channel (slice 2 ruling, point 1) |
| **C3** | origin can be *mediated* by asserted links, weakest-link; *the chain is data, not a type* |
| **Frozen primitive** (`IDENTITY_MECHANISM_COMPARISON.md`) | an artefact *may carry an origin reference, when established* — Rob's correction: cardinality and semantics left **neutral**; an artefact may involve an issuer, a preparer, a provider, a transmitting intermediary, an asserting user, or several |
| **`SMALLEST_SCHEMA.md` §2** | origin is **derived, not stored** — established by a proposition (subject: the artefact; second participant: a party), never a column; the four states are *read off the origin propositions* |
| **Institution encounter** (`INSTITUTION_ENCOUNTER.md`) | *an artefact that describes an institution is an artefact whose origin is not established — with candidates when the description matches parties on file*; description never mints or matches; **an institution comes to exist as a party by one event only: the household's individuating assertion**, a claim with strength, not a declaration |

Two consequences before any case is run:

- **The origin proposition's second participant is a party**, and for every non-household
  artefact that party is an institution — which exists only once the household's assertion has
  minted it. *The origin question cannot be answered for an EOB without the institution branch
  existing.* That is a dependency, found here, not a plan (§5).
- **"Established" cannot mean "true."** The household's assertion is a claim with strength
  (S3: real party, false relation; a forged letterhead: real claim, false origin). Established
  means *asserted by a party's utterance at a derivable strength* — the same sense in which a
  proposition's subject is established: a reference exists, not a fact is settled.

---

## 2. Three readings of "the proposition that establishes origin"

**Reading A — one kind: *this artefact is a statement by P*.** Subject: the artefact
(established). Second participant: the party *whose statement the artefact is* — C1's party,
the one whose knowledge the artefact's readings convey. Maker, capturer, transmitter and
recipient are not this proposition; they are mediation links (C3) of other kinds, later.

**Reading B — several role-typed kinds: *issued by · prepared by · captured by · transmitted
by · received from*.** Rob's cardinality correction taken as a catalogue: each participant an
artefact "may involve" gets a kind, and "origin" is whichever of them a consumer asks for.

**Reading C — origin is a property of readings, not artefacts.** Each reading carries whose
knowledge it conveys; the artefact has no origin of its own.

C fails immediately: it is C2's collapse with the sign flipped (the reader's row now carries the
origin), it makes two readings of one artefact able to disagree about the artefact's origin,
and it repeats the shipped defect `Evidence.source` — origin-by-row. Rejected without a case.

A and B are tested below. The discriminating question is what the *neutral cardinality*
correction was protecting: was it protecting *several kinds of relation to an artefact* (B), or
*the possibility that the one origin relation is absent, mediated, or multi-valued* (A)?

---

## 3. The cases

Each case is already ruled somewhere; the origin question is asked of it fresh.

| # | Case | Ruled in | Under A | Under B |
|---|---|---|---|---|
| **O1** | A mailed EOB. Rob says "this is from Lakeview Health, my insurer." | O-encounter, minting | one proposition `origin(A = EOB, P = Lakeview Health)`, evidenced by Rob's utterance; Lakeview Health minted or corresponded by the same act; **established** | `issued_by(EOB, Lakeview Health)` + `received_from(EOB, Lakeview Health)`? Two kinds for one act, or Rob picks one; "origin" = which? |
| **O2** | The parser reads the EOB's letterhead: "Lakeview Health." | O-encounter | a **reading-sourced** origin proposition; the artefact describing itself; **candidate only**, never establishing — the reading's own strength would derive from the origin it establishes (circular) | same, per kind |
| **O3** | S3's letter: "we are your servicer; pay us." Rob: "this is from S3." | S3, K3 | `origin(letter, S3)` **established** — a real party sent it; *S3 is my servicer* is a different proposition (a role, dated) and is false; origin is not contaminated | same, plus the temptation to fold "servicer" into `issued_by` |
| **O4** | Rob screenshots Lakeview Health's portal. | captured-portal, C3 | `origin(capture, Lakeview Health)` — *whose statement* the capture is; Rob is the **capturer**, a mediation link (*faithful capture*, C3), not the origin; readings convey Lakeview Health's knowledge (C2) | `captured_by(capture, Rob)` + `issued_by(capture, Lakeview Health)`; a consumer asking "origin" must know to skip `captured_by` — the collapse is one wrong join away |
| **O5** | Rob's own spreadsheet of medical bills. | K-cases (user-stated) | `origin(sheet, Rob)` — Rob's statement; readings convey Rob's knowledge; knowing for "it was health", not for "what Lakeview Health acknowledged" — C1 exactly, through a document | `prepared_by(sheet, Rob)` = `issued_by(sheet, Rob)`: the kinds coincide, which suggests they were never two |
| **O6** | Lakeview Health's EOB names "Riverbend Hospital Hospital, NPI …". | O-encounter | origin of the EOB is Lakeview Health. The Riverbend Hospital mention is **content** — a candidate for the origin of a *different* artefact (a Riverbend Hospital bill), never establishing it | same |
| **O7** | Two identical letterheads, nobody has asserted anything. | O-encounter | two artefacts, each with reading-sourced candidates only; **not established, with candidates — indefinitely** | same |
| **O8** | Rob: "from Lakeview Health." Later: "no — that was from the hospital." | Case B, tie ruling | two utterance-sourced origin propositions naming different parties, plus a Case-B claim about the first utterance; **nothing chosen** — derivation reports *competing*; resolution over the correction is the resolver's question, fenced | same, per kind |
| **O9** | Groundwork's own year-end export. | manufactured flag, party state 4 | origin = **no party** (a process) — and **no utterance can assert it**: `utterances.origin_party_id` is NOT NULL by ruling. The substrate cannot currently say "this artefact originates from a process." A finding, not solved here (§6) | same problem |
| **O10** | "My March Harbor statement — I don't have it." | R-ASSERT | an **asserted** artefact; the same utterance that asserts it exists also evidences `origin(stmt, Harbor)`; **established without being held** — origin does not require custody | same |
| **O11** | A settlement letter signed by both the hospital and the collector. | — (new) | one artefact, two origin propositions, both established — **determinate multi-valued**, the concurrent-coverage shape (state C), not a conflict; nothing chosen because nothing needs choosing | `issued_by` twice — same |

**Where A and B differ:** O1, O4, O5. In each, B either produces two kinds for one event (O1),
forces the consumer to know which role-kind "counts" as origin (O4 — the collapse the slice-2
ruling forbids, moved from the schema to a join), or produces kinds that coincide (O5). B is
Rob's cardinality correction read as a *catalogue*; the cases show the correction was
protecting the *state* of one relation — absent (O7), candidates (O2), mediated (O4),
multi-valued (O11) — not a plurality of relations. **A survives every case; B survives them
with an extra decision the consumer must get right every time.**

**What the cases fix about A's meaning:**

- The origin party is *whose statement the artefact is* — the party whose knowledge its
  readings convey (C1). Not who made the file (O4), not who received it (O1), not who is named
  in it (O6). Those are links or content.
- **Established by an utterance, never by a reading of the artefact itself** (O2: self-
  description is circular; O7: description never matches) **nor by a reading of another
  artefact** (O6: correspondence evidence, candidates). *Only a party's assertion establishes
  an artefact's origin.*
- Established ≠ held (O10). Established ≠ true (O3, forgery). Established ≠ unique (O11).
- Origin state is **read off the origin propositions**: no utterance-sourced claim → *not
  established*; reading-sourced claims only → *not established, with candidates*; one or more
  utterance-sourced claims naming parties → *established* (multi-valued if several agree on
  distinct parties for one joint statement — O11); utterance-sourced claims that *compete* →
  *not established, competing* (O8) — reported, never resolved by position. **No fifth state on
  the artefact**: *competing* is a derived reading of the claims, as *governing plan UNKNOWN*
  was.

---

## 4. What "sufficient evidence" means — the strength of the origin claim

Rob's second half: *what evidence is sufficient to establish it?* The cases answer: **one
utterance suffices to establish; strength is a separate derivation.** Establishing is
referential (a party is named by a party's claim); how much to trust it is `derived_strength`
over the origin proposition — origin foundation × kind — and that needs **the origin kind's
knowing relation**, the first catalogue entry this slice would rule:

| Origin of the origin claim | Knowing for *this artefact is a statement by P*? | Why |
|---|---|---|
| the recipient household (Person) | **yes** — first-hand for *where I got this* | O1, O3, O10; S3 shows the claim can still be *wrong*, which is what strength ≠ truth means |
| P itself (institution, via its live system or statement — *"yes, we sent this"*) | **yes** | the four-channel shape of P-ack, applied to authorship |
| a third party (another institution's document naming P) | **no** — candidate | O6 |
| a process reading of the artefact | **no** — candidate | O2 |

And the consequence Rob fenced slice 2 for: **a reading's strength becomes derivable.**

```text
reading-sourced relation, proposition kind k
    artefact origin   = the established origin party P (derived, §3)
    origin_kind       = P's foundation (person | institution) — a join to the anchor
    strength          = weakest link of
                          knowing(k, origin_kind)                 — is P knowing for k?
                          derived_strength(origin claim)          — how well is P established as origin?
    not established / candidates / competing   → undetermined
```

Weakest-link is C3's rule, applied to the shortest possible chain (one link). The captured-
portal chain (*capture is faithful* → *portal displayed X*) is a second link and stays fenced;
this slice derives over the origin link only, and says so.

*Danger test on the derivation:* O5 — Rob's spreadsheet says "$412 Lakeview Health EOB". Origin = Rob
(established, knowing for origin). Kind `eob_amount`, knowing relation `{institution}` → Rob is
**not knowing** → `not_knowing`. Correct: K5 through a document. The derivation does not let a
household-made artefact launder a relayed value into a first-hand one.

---

## 5. The dependency the answer forces — the institution anchor

O1 cannot be represented without Lakeview Health as a party, and Lakeview Health exists only under the household's
minting utterance (`MINTING_ASSERTION.md`: *the institution anchor = structure + a pointer to
the claim that minted it*). The build sequence already put the institution anchor at slice 3
(`SHIPPED_VS_TARGET.md` §6); this record confirms it is the same slice as the origin
proposition, not a slice before it, because:

- an origin proposition whose object is an institution needs `parties.minted_by_id` to exist
  (`SMALLEST_SCHEMA.md` §1: the one additive column on `parties`);
- the minting utterance and the origin assertion are, in O1, **one act**: "this is from Lakeview Health,
  my insurer" mints Lakeview Health (if new) and evidences `origin(EOB, Lakeview Health)`. One utterance, two
  propositions — slice 1's *same act → one utterance, many propositions*, exactly;
- building the anchor without the origin kind would leave a minted institution that nothing
  can be *from* — an identity with no claim able to reach it.

What the anchor is, restated from the rulings (no new design): `parties.minted_by_id`
(nullable → `utterances`); **exactly one anchor per party** — `person_id` xor `minted_by_id` —
a guard, since the CHECK cannot be added; foundation is still a join, never a kind column;
the minting utterance's origin is a Person (the fixed point one step out); descriptors
(name, plan number, address) are the utterance's **content** and become correspondence
evidence later — **no name column on the institution party.** A party with neither anchor is
the forbidden state; a party with both is the collapse of the two foundations.

---

## 6. Not decided here — fences, and one finding

- **O9 — process-originated artefacts.** The substrate cannot say *this artefact originates
  from no party*: an origin proposition with `object_state = none` must be evidenced by
  something, and a process cannot utter. Not solved by relaxing `origin_party_id` (that would
  let a process assert anything). Recorded as the first place the substrate is *found* unable to
  represent a ruled state; the manufactured-artefact question (export/backup, decision 10) is
  where it will be answered. **Do not build around it.**
- **The mediation chain** — capture faithfulness (O4), servicer agency (K2/K3), transmission —
  each an asserted link of its own kind. Fenced; the derivation in §4 runs over one link.
- **Resolution over competing origin claims** (O8) — the resolver over Case-B corrections is
  the same fenced question as `resolution()`'s reading-level kind. *Competing* is reported.
- **Correspondence** — "these two letterheads are one institution"; "arrival B is artefact 17".
  Slice 4. The O7 candidates are *found* by description match and *asserted* by correspondence;
  neither happens here.
- **The kind name.** `artefact_origin` is used above as a label; the ruling names it.
- **The knowing relation** stays caller-supplied in code; §4's table is the *ruled content* the
  first caller passes for this kind — the kind catalogue as a whole is still not settled.
- **Unminting** an institution asserted in error — not opened (MINTING_ASSERTION's fence
  stands).

---

## 7. Ruling candidate — for Rob

> **One proposition kind establishes an artefact's origin: *this artefact is a statement by
> P* — subject the artefact, second participant the party whose knowledge the artefact's
> readings convey. It is established only when asserted by a party's utterance; a reading of
> the artefact itself, or of any other artefact, yields a candidate and never establishes.
> Established means referentially asserted, not true, not held, not unique: an origin may be
> absent, carry candidates, be multi-valued for a joint statement, or be competing — each a
> state read off the origin propositions, never a column on the artefact and never resolved
> by position. Maker, capturer, transmitter and recipient are not origin; they are mediation
> links of their own kinds, fenced. The household is knowing for an artefact's origin (it
> knows where it got it), as is the origin party itself; a third party's document and a
> parser are not. With an established origin, a reading's strength is derivable: weakest link
> of the origin party's knowingness for the proposition kind and the origin claim's own
> strength. The kind's object is a party, so the institution anchor — `parties.minted_by`,
> one anchor per party, foundation by join — is this slice's dependency, built with it, since
> in the common case one utterance both mints the institution and asserts the origin.**

If ruled, slice 3's build contents are: the `artefact_origin` kind (the first ruled catalogue
entry) · `parties.minted_by_id` + the one-anchor guard · `artefact_origin(session, artefact)`
deriving the state · `derived_strength` extended over one link for reading-sourced relations ·
fixture over O1–O11 (O9 asserted as *not representable*) · mutations (origin read from a
reading; reader consulted; anchor doubled; position chosen among competing claims) · gate.
**Not in it:** correspondence · descriptor columns · the chain · unminting · any consumer.

*The line the slice must hold: a document can say where it is from; only a party can say
where a document is from.*
