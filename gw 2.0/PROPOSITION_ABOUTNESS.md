# Ab7 — what is proposition-level about-ness?

> Status: **Build mode, opened by Rob 2026-09-14; two wording refinements on his review; K1p RULED as
> written and the build AUTHORISED (§7).** The payment slice is
> closed at `6390804` (`PAYMENT_IDENTITY.md` §11) with the constraint that *the payment identity
> is complete without Ab7*. Ab7 was found at slice 8 (`ARTEFACT_ABOUTNESS.md` Ab7), forced a
> second time by the payment slice (Pm2, Pm3), and is a **reopening of slice 5's finding** —
> *no proposition takes a proposition as subject; nothing forced it then* — on this evidence
> only. This record asks what kind of thing the proposition-level crossing is, tests the
> candidates against the ruled cases under the three tests, and ends with a ruling candidate, ruled in §7.

**Rob's question, verbatim:** *what is proposition-level about-ness?*

**The problem, as Rob stated it at the payment closure:** *a document contains a proposition
about a particular thing, but document-level `artefact_concerns` cannot establish which
proposition is about which identity.* Two independent demonstrations:

```text
combined statement  ──► section / item      (slice 8, Ab7: mortgage and HELOC on one statement)
bank statement      ──► individual line      (payment slice, Pm2/Pm3: thirty debits, one is p)
```

```text
artefact A ──concerns──► O1, O2          (slice 8: asserted, artefact-level)
   └── reading ──► P3  "balance $44,000"  ──?──► O1 or O2      ← what justifies this
```

**The three tests, carried in:** identity · authority · history. **The account number, section
heading and any other descriptor are fenced out of all three**: a match nominates a candidate;
it does not establish.

---

## 1. What is already ruled, and therefore constrains the answer

| Ruling | What it fixes |
|---|---|
| **Slice 5** | claims about an utterance are higher-order; *no proposition takes another proposition as subject — nothing forced it then*; truth, contradiction and reaffirmation claims about a proposition are **not kinds** ("X is false" is a domain negative; agreement is derived) |
| **Slice 8** (ruled, built) | the artefact-level crossing is a claim of its own, `artefact_concerns(A, X)`, presupposing X; asserted by a party's utterance, matching evidence a candidate for it only; **anti-collapse:** it never changes the subject, participants, authority, evidence or history of any proposition derived from a reading of A; the read propositions' identity participant stays *not established with candidates*; **K3 rejected** — filling the read claim's slot makes the reading appear to have known which identity, and the match becomes the reading's evidence |
| **Slice 8, Ab7 as recorded** | *the cases force a relation between a particular proposition and an identity, not merely between the artefact and an identity* — forced, not designed |
| **Immutability** (slice 4) | a proposition's participant slots are never re-pointed |
| **Slice 6** | participants are structural, never content; the identity participant of a read claim is a slot in the candidates state |
| **Proposition** (`PROPOSITION.md`) | `PARTICIPANT_CANDIDATES` — *candidates live in correspondence, not here*: the state names nothing and never holds a placeholder reference |
| **Slice 4** | `proposition_corresponds` in the PARTIAL list, **unforced** — X8 (two contents, one value) was a comparison, not a correspondence |
| **Slice 2 / 4 → 6** | two readings of one artefact are two observation events; a parse dispute is computable by structure; readings of one referent are never independent |
| **Payment slice** | the line → `p` tie is Ab7; **the payment identity is complete without Ab7**; Ab7 must not become part of any identity |
| **Minting doctrine** | one source of truth: a fact must not be representable two ways that can drift (the reason the institution was not built before the utterance) |

Two consequences before any case runs. The crossing is **not a re-pointing** (immutable slots;
K3), **not a re-assertion** (slice 8's K2: it downgrades the source's authority and answers a
different question), and **not a correspondence** (a proposition and an identity are not one
referent). So, exactly as at artefact level, it is *a claim of its own* or nothing — and the
only open question is **what its subject is**.

---

## 2. Three candidates for "what kind of thing the proposition-level crossing is"

**K1p — a claim whose subject is the proposition: *this proposition concerns this identity*.**
`proposition_concerns(P, X)`: subject the read proposition (a new referent type for a subject —
the slice-5 reopening), second participant an already-minted identity. Asserted by a party's
utterance ("the $44,000 line is the HELOC"); a section heading or account number seen by the
parser yields a reading-sourced candidate. P is never touched.

**K2p — sub-artefacts: each line or section is an artefact of its own,** part of the statement,
and `artefact_concerns` then works at line level with no new subject type.

**K3p — resolution of the read proposition's participant,** the household's confirmation
filling the slot. Already rejected at artefact level (slice 8 K3); nothing changes at line
level. Rejected without a case.

**K2p fails on a category error already named.** A line is not *encountered*; it is *produced
by a reading* — the parser's segmentation. Two readings of one statement may segment
differently (the $412 / $4.12 dispute is a line-level dispute), so line-artefacts would differ
per reading: a reading's output placed in the artefact layer, which is the `transactions`-row
error of slice 6 §4 (*the record describing the thing becomes the thing*) with the parser as
the minter. It would also make a process create world objects, which O9 forbids. Rejected.

K1p is tested.

---

## 3. The cases

| # | Case | Identity — what establishes X? | Authority — what crosses; what is *not* evidence for the value? | History — whose? |
|---|---|---|---|---|
| **Pa1** | The credit-union statement concerns O1 (mortgage) and O2 (HELOC). Line 3 reads "balance $44,000". Rob: "that line is the HELOC." | O2 already minted; the claim presupposes it | **K1p:** `proposition_concerns(P3, O2)` evidenced by Rob's utterance. P3 keeps the credit union's authority (read from A, origin CU); the association is Rob's assertion — knowing for it is relational, `undetermined`. P3's own participant stays *candidates*; nothing is filled | the association's; P3's value history is separate |
| **Pa2** | A bank statement of thirty lines; no artefact-level concerns claim at all (a bank account is not a ruled identity). Line 7: "HARBOR MTG −1,412.00". Rob: "that's my March payment." | p minted by Rob (Pm1); presupposed | `proposition_concerns(P7, p)`. **Proposition-level about-ness works with no artefact-level claim above it** — the two levels are independent; the bank's line keeps the bank's authority; the tie is Rob's | its own |
| **Pa3** | The parser sees the heading "Acct …4471" over lines 1–5 and "Acct …9902" over 6–9. | nothing — a match establishes no referent | five **reading-sourced `proposition_concerns` candidates** naming O1 and four naming O2 — no party behind them; `undetermined`; **they are what the candidates state has always pointed at**: `PARTICIPANT_CANDIDATES` finally has a concrete carrier — the reading-sourced concerns claims about that proposition. The heading never touches the values' evidence | the candidates' history is the association's |
| **Pa4** | Later: "no — line 3 was the mortgage, not the HELOC." | O1 exists | `utterance_retraction` of the line-3 utterance + `proposition_concerns(P3, O1)`; **P3 is byte-identical before and after**; the credit union still says $44,000 | **the association's, cleanly**; nothing about the value moved |
| **Pa5** | A second reading of the statement gives P3′ = "$4,400" for the same line. | — | a **parse dispute** (slice 2) between P3 and P3′. **Rob's about-ness on P3 does not reach P3′**: about-ness attaches to a proposition, and a re-reading produces new propositions. P3′ has no about-ness unless asserted — or unless *P3 and P3′ are one line* is claimed, which is `proposition_corresponds`, **unforced until now and now pressed** (§5). Not decided here | P3′'s absence of about-ness is honest, not a defect |
| **Pa6** | Rob, without the statement: "the HELOC balance is about $44k." | O2 exists | **testimony** (slice 8 Ab6) — a value claim about O2 with Rob's strength; identifies no line, crosses nothing; a different question | its own |
| **Pa7** | A concerns {O1, O2}; Rob says line 3 concerns O3 (the car loan). | O3 exists | representable — both claims stand; **the inconsistency between levels is a consumer's to report, never a guard's to refuse and never a resolver's to settle**; nothing chosen | each claim's own |
| **Pa8** | A single-obligation statement (concerns O1 only); no line-level claims. | O1 exists | **no proposition-level claim is required**: a consumer that wants "which identity is this line about" has the artefact-level claim and nothing contradicting it. Proposition-level about-ness is *needed* only where the artefact concerns several identities or none (Pa1, Pa2); it is never required — and how a consumer combines the two levels is the consumer's rule, not derived here | — |
| **Pa9** | With a proposition-subject slot in existence: "P3 is false", "P3 agrees with P3′", "I stand by P3". | — | **none of these becomes a kind** — slice 5's substance holds: "P3 is false" is a domain negative about O2; agreement and reaffirmation are derived. The slot is *narrowly* opened: the only ruled kind with a proposition subject is `proposition_concerns`; the registry says so and the fixture asserts it | — |
| **Pa10** | Rob's own testimony T = "HELOC balance $44k" (object O2 established). Someone asserts `proposition_concerns(T, O1)`. | — | **refused.** Two representations of apparently related information exist by design: P's participant slot is **structural participation**; `proposition_concerns(P, X)` is **a claim about what P is about**. The one-source rule says they may not both establish the same semantic fact — so **once a proposition's participant of the relevant identity type is established, its about-ness is already structurally established, and `proposition_concerns` may not provide a competing source for that same about-ness.** (Not because the proposition "knows" what it is about — because its structural participant establishes it.) `participant = O2` with `proposition_concerns(P, O1)` is never two competing established facts. To say T was about O1 after all is a retraction of T's utterance and a new testimony — Case B, not an about-ness override | — |

**What the cases fix about K1p's meaning:**

- **Subject: the proposition** — the first and only ruled kind with a proposition subject
  (Pa9). Slice 5's finding is *reopened and narrowed, not reversed*: it said no case forced a
  proposition subject; Ab7 and Pm2/Pm3 do; truth, contradiction and reaffirmation claims about
  propositions remain non-kinds.
- **Presupposes the identity** (Pa1, Pa2); never establishes it (Pa3). **A match observed by a
  reading produces a candidate for a `proposition_concerns` claim; it is not itself that claim**
  — `reading observes heading → candidate → possible proposition_concerns(P, O2) → only an
  assertion establishes the claim`.
- **Anti-collapse, extended** (Pa1, Pa4): `proposition_concerns(P, X)` never changes P's
  subject, participants, authority, evidence or history. P's identity participant stays
  *candidates* forever; **the candidates are the reading-sourced concerns claims about P** —
  `PARTICIPANT_CANDIDATES` gains the carrier the proposition ruling said it would have
  ("candidates live in correspondence, not here").
- **Independent of the artefact level** (Pa2, Pa8): needed where the artefact concerns several
  identities or none; never required; consistency between levels is reported by consumers, never
  enforced or resolved (Pa7).
- **Attaches only to a proposition with no established participant of that type** (Pa10) — a
  guard: once the structural participant is established, about-ness is structurally
  established, and the claim may not compete with it.
- **Does not survive a re-reading** (Pa5): a new reading's propositions have no about-ness of
  their own; carrying it across is a correspondence or policy question, not decided.

---

## 4. The three tests, answered

| Test | Answer |
|---|---|
| **Identity** | X is established only by minting; the concerns claim presupposes X and points at it; a heading, account number, section or position establishes nothing (Pa3) |
| **Authority** | the value keeps its source's authority through `artefact_origin`; the association is a party's assertion, relational knowing `undetermined`; the match is a reading-sourced candidate *for the concerns claim* and never evidence for the value (Pa1, Pa3) |
| **History** | the association's history is its own (Pa4); the value's is its own (Pa5); they cannot tangle because the claim is beside P, never in it |

---

## 5. Findings — and what they do not decide

- **`proposition_corresponds` is now pressed by a case (Pa5)** — *this reading's P3 and that
  reading's P3′ are one line* — where X8 did not press it. It is **not ruled here**: the case is
  recorded as the first genuine pressure; its shape, if forced, is slice 4's (per type, never
  merges, candidate then asserted). A pipeline carrying prior about-ness forward as *candidates*
  on a re-parse is a policy matter outside the substrate.
- **The candidates state has a carrier.** No new state, no new column: the reading-sourced
  `proposition_concerns` claims *are* the candidates. Consumers that show candidates read them
  there.
- **Relational knowing** — one more kind waiting (the household for its own lines; the artefact's
  origin plausibly — Harbor can say which account a line is for). Unchanged; `undetermined`.
- **Consistency between levels** — Pa7's report is a consumer derivation; not built.
- **The multi-link strength derivation** — a value's strength *about X* through a line-level
  claim is the same future consumer derivation slice 8 left, with one more link. Not specified.

---

## 6. Ruling candidate — for Rob

> **Proposition-level about-ness is a claim of its own: *this proposition concerns this
> identity* — a domain proposition whose subject is a proposition and whose second participant
> is an already-minted identity. It presupposes the identity and does not establish it. It is
> asserted by a party's utterance under the ordinary discipline; whether that party is knowing
> for the relational claim is a separate question, and its strength is `undetermined` until
> relational knowing is ruled. A match observed by a reading — a section heading, an account
> number, a position — produces a candidate for a `proposition_concerns` claim; it is not itself
> that claim, and it is evidence for nothing else; those candidates are what the *not
> established with candidates* state has always referred to. The claim never changes the
> subject, participants, authority, evidence or history of the proposition it is about, whose
> own identity participant remains unestablished: **about-ness is information about a
> proposition, not information inserted into the proposition.** Once a proposition's participant
> of the relevant identity type is established, its about-ness is already structurally
> established, and `proposition_concerns` may not provide a competing source for it. It is independent of
> artefact-level about-ness — needed where an artefact concerns several identities or none,
> never required, with consistency between the levels reported by consumers and never enforced
> or resolved. This is the first and only ruled kind with a proposition subject: slice 5's
> finding is reopened on this evidence and narrowed, not reversed — truth, contradiction and
> reaffirmation claims about a proposition remain non-kinds. A re-reading's propositions carry
> no about-ness of their own; carrying it across readings is a correspondence question
> (`proposition_corresponds`, now pressed by a case and not ruled) or a policy question.**

**If ruled**, implementation follows slice 8's shape: one additive proposition-subject slot; one
registry kind whose object is the identity slots ruled so far; the one-source guard; a fixture
over Pa1–Pa10 asserting what is *not* derived; no data step. The exact mechanics are
implementation work after the ruling. **Outside it under any authorisation:** `proposition_
corresponds` · consistency derivation · multi-link strength · candidate generation · any
consumer · the transaction referent.

*The line: a document can be about your debts; a line in it is about one of them only when
someone says which — and saying which changes nothing about what the line says.*

---

## 7. Ruling — Rob, 2026-09-14. K1p ruled as written; the Ab7 build authorised.

*Ab7 is not a special property of documents or lines. It is a new proposition whose subject
happens to be another proposition* — the right abstraction. Two wording refinements applied
before ruling (above): Pa10 phrased over the **structural participant**, not a proposition's
self-knowledge; and *a match observed by a reading produces a candidate for a
`proposition_concerns` claim; it is not itself that claim.*

**The three-level separation, each arrow a different claim, neither concerns claim changing P:**

```text
Artefact ──artefact_concerns──► Identity
   └── reading → Proposition ──proposition_concerns──► Identity
```

**Pa2 establishes something bigger than the payment case:** proposition-level about-ness exists
without an artefact-level claim; the two are *independent claims consumers may combine later —
the substrate does not*, not a layer that inherits. **Pa5** is architecturally correct: history
does not jump from one proposition identity to another because a pipeline thinks they came from
the same line; `proposition_corresponds` is the clean question that leaves — **pressed, not
decided**, and not smuggled in.

**"First and only" is preserved exactly as scoped:** not *propositions may generally be subjects
of propositions* but *one domain relation has been forced whose subject happens to be a
proposition* — a narrow reopening of slice 5, not an ontology expansion.

| Boundary | Result |
|---|---|
| identity | presupposes an already-minted identity |
| truth | does not alter P or establish P's truth |
| authority | the concerns claim has its own asserting origin |
| evidence | a match is candidate evidence, never the value's evidence |
| history | concerns history stays separate from P's |
| immutability | never fills or re-points P's participant |
| artefact level | independent; neither level requires the other |
| re-reading | does not automatically carry forward |
| candidates | finally has a legitimate carrier |
| proposition subject | narrowly permitted for this one ruled kind |
| correspondence | a separate, currently unruled question |

**The invariant that captures why K3 fails, why history stays separate, why authority does not
migrate, and why Ab7 coexists with the proposition model without corrupting it:**

> **About-ness is information about a proposition, not information inserted into the
> proposition.**

Ruled; build authorised at §6's shape; then stop. `proposition_corresponds` stays where it is.
