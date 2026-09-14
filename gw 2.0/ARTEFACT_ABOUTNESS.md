# Slice 8 — what kind of thing is the crossing?

> Status: **Build mode, opened by Rob 2026-09-14; precision pass `00ec394` accepted (§8); K1 RULED
> as written and the build AUTHORISED (§9).** The obligation slice
> is accepted at `8fd7382` (`OBLIGATION_IDENTITY.md` §10); its §10.1 holds the fence, the three
> tests and the instruction this record follows: *do not start by designing `artefact_concerns`;
> ask the cases what kind of thing the crossing is.* This record does that, finds that the two
> proposals answer different questions and that a third question hides behind them, and ends
> with a ruling candidate, ruled in §9.

**Rob's question, verbatim:** *what makes an artefact's proposition about **this** obligation,
rather than merely **compatible with** an obligation?* — and the sharper form: *what kind of
thing is the crossing?*

```text
artefact
   └── reading ──► proposition        "this artefact says X"
                       ▼
                  obligation O ?      "X is about O"        ← what justifies this relationship
```

**The three tests, carried in:** identity (what actually establishes `O`) · authority (what
lets the proposition cross without the matching mechanism becoming evidence for X) · history
(is a disputed association the association's history or the proposition's). **The account
number is fenced out of all three:** a matching descriptor can be evidence *for* a
correspondence claim without becoming the claim.

---

## 1. What is already ruled, and therefore constrains the answer

| Ruling | What it fixes |
|---|---|
| **Obligation identity** (§9) | `O` exists by the household's minting assertion and by nothing else; a bill describes, never mints; the minting act ≠ the minted identity |
| **Slice 2 / 3** | a reading is what Groundwork saw of a held artefact; a value read from A has A's origin's authority (C1), derived through `artefact_origin`, one link; the reader is a channel |
| **Slice 4** | observed matches are candidates with no party; a party's utterance establishes; correspondence is between identities of *one type* — artefact ↔ obligation is cross-type and **refused** (X12), so the crossing is *not* a correspondence |
| **Slice 5** | a claim about an utterance is higher-order; **no proposition takes a proposition as subject** — nothing forced it then |
| **Slice 6** | participants are structural, never content; the read claim's obligation participant is a slot in state *not established with candidates* (Ob2 built it so) |
| **Immutability** (slice 4) | a proposition's participant slots are never re-pointed — a read claim cannot later "acquire" O |
| **C3** | origin can be mediated by asserted links, each with its own strength; weakest link over the chain; *the chain is data, not a type* |
| **U6 / RA** | the household's own statement of a value is *testimony* — a kind of its own once the household is asked; the household is not knowing for what E acknowledges (K5) |
| **Slice 3 fence** | the strength derivation runs over **one link**; longer chains are consumers' |

Two consequences before any case runs. The crossing is **not a correspondence** (cross-type)
and **not a re-pointing** (immutable slots). So whatever it is, it is either *a claim of its own*
or *a different act altogether*.

---

## 2. Three candidates for "what kind of thing the crossing is"

**K1 — a claim about the artefact: *A concerns O*.** A domain proposition — subject the
artefact, second participant an **already-established** identity — entered by a party's
utterance, with its own evidence, strength and history. **`concerns(A, O)` presupposes `O`: it
does not mint, establish, identify or otherwise create it.** Every value read from A is then
*about O* **by derivation** through the concerns claim; the read claims themselves are never
touched.

**K2 — an act of re-assertion.** The household's utterance evidences a *new* value claim — the
same content, this time with `O` established — and the reading's claim stays as it was. The
crossing is the household saying the value again, about O. Note before testing: K1 and K2 are
not two implementations of one crossing; they are **different propositions** — K1 asks *what
identity does this artefact concern?*, K2 asks *what does the household say about this
identity?*

**K3 — a resolution of the read claim's participant.** The read claim's `not established with
candidates` becomes `established`: the slot is filled once the household confirms. The crossing
is the candidate being accepted.

K3 fails before the cases: it re-points an immutable slot, and — the authority test in its
sharpest form — it makes the *reading* appear to have known which obligation it read about. The
parser asserted a value and an account string; after K3 the parser's claim carries a participant
it never asserted, and the matching mechanism has become part of the reading's evidence.
Rejected.

K1 and K2 are tested against the cases, with the three tests as columns.

---

## 3. The cases

| # | Case | Identity — what establishes `O`? | Authority — what crosses, and what is *not* evidence for X? | History — whose history? |
|---|---|---|---|---|
| **Ab1** | A Harbor statement A (origin Harbor). The parser reads five values (balance, payment due, rate, escrow, last payment). Rob: "that's my mortgage statement." | O already minted (Ob1). **K1:** one claim `concerns(A, O)`, evidenced by Rob; five values about O by derivation. **K2:** Rob re-asserts five values with O established | **K1:** the values keep **Harbor's** authority (read from A, origin Harbor); the *association* is **Rob's assertion** — whether Rob is *knowing* for that relational claim is a separate question, `undetermined` in this slice. **K2:** the five re-asserted values have **Rob's** authority — the household is not knowing for what Harbor states (K5) — so the crossing *downgrades* E's statement into testimony, and the reading's E-strength claims stay unattached | **K1:** one association, one history. **K2:** five histories, all tangled with the values |
| **Ab2** | A bill from Riverbend Hospital; no obligation exists. Rob: "that's the ER visit — I owe Riverbend Hospital for it." | **one utterance performs two distinct semantic jobs**: it mints `O` (the obligation anchor points at it) and it evidences `concerns(bill, O)` (a proposition whose second participant is the now-established `O`) — the institution pattern (O1). **The utterance is neither the identity nor the concerns relation**; no new kind of act is involved, only one act evidencing two things. Under K2 the same utterance would mint O *and* re-assert the bill's amount as Rob's own claim | as Ab1 | as Ab1 |
| **Ab3** | The parser notices "4471" in A and "4471" in O's minting utterance. | **nothing** — the match establishes no referent | a **reading-sourced `concerns(A, O)` candidate** — no party behind it (slice 4 §3); the household's answer establishes it. **The match is evidence for the *concerns* claim and for nothing else** — it never touches the balance claim's evidence. Under K2 the match has no home at all: there is no proposition for it to be a candidate *for* except the values, which is exactly the authority failure | the candidate's history is the association's |
| **Ab4** | Later: "no — that statement was for the HELOC, not the mortgage." | O2 exists (or is minted) | **K1:** `utterance_retraction` of the concerns utterance + a new `concerns(A, O2)`; **A's readings and their values are untouched — A still says $1,925.** **K2:** retract the five re-assertions, assert five new ones — and the *value* claims are what get retracted, though nobody disputed the value | **K1: the association's history, cleanly its own.** K2: the value's history, though the value was never in question |
| **Ab5** | Two readings of A disagree: $1,925 vs $1,295. | — | a **parse dispute** (slice 2), inside A; the association is not in question | **the proposition's history**, cleanly its own — K1 keeps the two histories apart by structure; under K2 the household's re-assertion would have picked one reading's value to re-assert, silently resolving the dispute |
| **Ab6** | Rob, without any statement: "the mortgage balance is about $178k." | O exists | **this is K2 — and it is legitimate: testimony.** A value claim about O with Rob's authority (U6: a kind once he is asked). But it *identifies no artefact*, crosses nothing, and is not what Ab1's Rob did. **K2 answers a different question** — *what does the household say?* — not *what is A about?* | its own |
| **Ab7** | A combined credit-union statement lists the mortgage *and* the HELOC. Rob: "that's my credit-union statement." | both O1 and O2 exist | **K1:** `concerns(A, O1)` and `concerns(A, O2)` — both true. But now a value read from A is about *which*? The artefact-level relation cannot say. **The case forces a relation between a particular proposition and an identity, not merely between the artefact and an identity** — one that neither K1 (artefact-level) nor K2 (Rob re-asserting each value, losing E's authority as in Ab1) supplies. **Forced, not built:** it reopens slice 5's finding (*no proposition takes a proposition as subject — nothing forced it then*) on this evidence, and its form is not designed here | that proposition-level association's history is its own — a third history |
| **Ab8** | An EOB from Lakeview Health concerns an *insurance claim* (a referent with no identity yet). | **cannot be established — the claim has no identity** (slice 6 §4); the EOB's values stay about a not-established participant | the same kind, a different object type — `concerns(artefact, identity)` recurs per identity; nothing to build until the claim is minted | — |
| **Ab9** | "My March Harbor statement — I don't have it" (asserted artefact 9, Ob/X5) — "it's for the mortgage." | O exists; artefact 9 is asserted, unheld | `concerns(9, O)` — **about-ness needs no custody**; the same utterance may assert the artefact, point at O, and relate them | its own |
| **Ab10** | S3's letter ("we service your mortgage; pay us") — the debt is real, the servicer claim false. | O exists | **`concerns(letter, O)` is true even though the letter's content is wrong**: about-ness is not endorsement. What the letter *says* (S3 services O) is a value claim with S3's authority, later retracted by Rob (Ob10); the association stands | two histories, separate — the association is never disputed, the claim is |

---

## 4. What the cases decide

**The crossing is K1 — a claim of its own: *this artefact concerns this identity*.** It passes
all three tests, and passes them *by structure*:

- **Identity:** `O` is established only by the household's minting assertion; `concerns(A, O)`
  **presupposes** an already-established `O` and does not mint, establish, identify or create it
  (Ab2 shows one utterance can do both jobs — mint, and evidence the concerns claim — without
  the utterance being either the identity or the relation). The match establishes nothing
  (Ab3).
- **Authority:** the value keeps its source's authority (Harbor's, via `artefact_origin`); the
  association is the household's *assertion* — whether the household is *knowing* for it is
  the relational-knowing question, `undetermined` here. The match is a candidate *for the
  concerns claim* and for nothing else — it has no path to the value's evidence (Ab3). Under K2
  the crossing itself downgrades E's statement into household testimony (Ab1), which is the
  laundering path run backwards: not manufacturing authority, destroying it.
- **History:** the association's history is its own (Ab4); the value's is its own (Ab5); a
  wrong artefact can still concern the right obligation (Ab10). K2 tangles the two at every
  turn.

**K2 is not the crossing — and not a weaker implementation of it. It represents a different
proposition.** K1 asks *what identity does this artefact concern?*; K2 asks *what does the
household say about this identity?* Ab6 is the evidence that the second question already has a
legitimate, separate representation: ordinary testimony — a value claim about O evidenced by
the household's utterance, with the household's strength. The two proposals were answering
different questions, as Rob suspected — and both have answers: K1 for about-ness, ordinary
testimony for the household's own statement.

**A third question hides behind them (Ab7):** *which of an artefact's subjects does this
particular read proposition concern?* When A concerns exactly one identity the derivation is
unambiguous; when A concerns several, **the cases force a relation between a particular
proposition and an identity, not merely between the artefact and an identity.** Combined
statements are common enough that this is a real case, not a hypothetical. **Recorded as
forced, not built, and not designed here**: it reopens slice 5's finding on evidence, which is
the only way it should be reopened.

---

## 5. What K1 is, precisely — and what it is not

`artefact_concerns(A, X)`: subject the artefact; second participant an **already-established
identity** — the obligation now, and each further identity once it is minted (Ab8); the claim
presupposes the identity and never creates it. **Asserted** — entered into the record — by a
party's utterance under the ordinary proposition discipline; reading-sourced claims are
candidates (Ab3). **Assertion is not authority:** whether the asserting party is *knowing* for
this relational claim (the household for its own artefacts and obligations; the origin party for
its own statements) is a separate question, and **relational knowing remains `undetermined` in
this slice**, joining retraction, P-ack, health, D5/D7. Content: the basis, shown to a person.
Not symmetric, not reflexive (cross-type by construction).

> **Anti-collapse invariant.** `artefact_concerns(A, O)` never changes the subject,
> participants, authority, evidence or history of any proposition derived from a reading of A.
> The association is a claim beside those propositions, never an edit to them. *(A semantic
> invariant, not an implementation proposal.)*

**Not endorsement** (Ab10). **Not custody** (Ab9). **Not correspondence** (cross-type; and the
artefact and the obligation are not "one referent"). **Not a rewrite** of any read claim (the
read claims keep `not established with candidates` forever; *about O* is a derivation over
them, by a consumer, through the concerns claim). **Not the per-value association** (Ab7).

**A consequence, not decided:** a consumer that wants to say how strongly a value is *about O*
may need to combine the provenance of the value (through `artefact_origin`) with the strength of
the concerns claim. That is a future consumer derivation; the precise multi-link derivation
stays outside this slice, as slice 3 left it.

---

## 6. Not decided here — fences and findings

- **Proposition-level about-ness (Ab7)** — forced; not built; not designed; a reopening of
  slice 5's finding and nothing more.
- **Multi-link strength** — a future consumer derivation; not specified here.
- **Relational knowing** — one more kind waiting; unchanged.
- **Who is knowing for about-ness** — anyone may *assert* it under the ordinary discipline;
  which asserters are *knowing* is the relational-knowing question, fenced with it.
- **The insurance claim / plan / payment identities** (Ab8) — outside this slice; nothing here
  decides them.
- **Candidate generation** — outside the substrate and this slice; no rule is stated here.

---

## 7. Ruling candidate — for Rob

> **The crossing is a claim of its own: *this artefact concerns this identity* — a domain
> proposition whose subject is the artefact and whose second participant is an
> already-established identity (the obligation now; each further identity as it is ruled) — it
> presupposes that identity and does not mint, establish or identify it. It is asserted by a
> party's utterance under the ordinary discipline; whether that party is knowing for the
> relational claim is a separate question, and its strength is `undetermined` until relational
> knowing is ruled. An observed match — account number, name, date — is a reading-sourced
> candidate for the concerns claim and for nothing else, and never touches the evidence of
> anything the artefact says. The values read from the artefact keep their source's authority
> and are about the identity by derivation through the concerns claim, never by rewriting
> their own participants. The association's history is its own — disputed, retracted or
> replaced without touching what the artefact says — and the artefact's readings' history is
> its own. About-ness is not endorsement and needs no custody. Re-assertion is not the crossing:
> it is the household's testimony about the identity, a different question with its own
> ordinary representation, answering a different question. `artefact_concerns(A, O)` never
> changes the subject, participants, authority, evidence or history of any proposition derived
> from a reading of A. Where an artefact concerns several identities, the cases force a
> relation between a particular proposition and an identity — forced by the combined-statement
> case, not built here, and reopening slice 5's finding only.**

If ruled, the build is one kind: `ARTEFACT_CONCERNS` in the registry (subject artefact; object
the identity slots ruled so far — obligation; `reading_establishes` false; relational knowing)
· fixture over Ab1–Ab10 with Ab7 asserted *not representable* and Ab8 *not establishable* ·
mutations (the match establishes; the read claim's participant is filled; retracting the
association retracts the value; re-assertion is treated as the crossing; a value acquires O
without a concerns claim) · no migration. **Not in it:** per-proposition about-ness · the
two-link derivation · any consumer of "about O" · candidate generation · the other identities.

*The line: a statement can be about your debt without you having said a word about the debt;
but nothing is about your debt until you say which debt it is about.*

---

## 8. Review — Rob, 2026-09-14. Precision pass accepted; ready for ruling. No further wording pass.

*The improvement is not cosmetic: several places where a future implementation could have
mistaken an epistemic statement for an ontological one are gone.* Three changes materially
strengthen the record:

- **"Presupposes"** cleanly prevents `concerns` from becoming a backdoor identity-minting
  mechanism.
- **Assertion ≠ knowing** prevents *a party asserted this* from silently becoming *the party
  knows this*.
- **The anti-collapse invariant** gives the future implementation a hard semantic boundary:
  the association can explain *which identity*, but cannot rewrite what the artefact said or
  how we know it.

The Ab7 correction identifies the actual forced fact without prematurely deciding that the
answer must be a particular slot or relation shape.

**The conceptual structure, as Rob now reads it:**

```text
            ┌── reading ──► proposition ──► "A says X"
artefact A ─┤
            └── concerns ──► identity O ──► "A is about O"

party ──asserts──────────► concerns(A, O)
party ──may/may not know─► concerns(A, O)      ← still fenced

concerns(A, O) does not rewrite: proposition subject · participants · authority · evidence · history
```

*A considerably stronger slice 8 than the original draft, without being broader.* No further
edits to this record; the next step is the ruling.

---

## 9. Ruling — Rob, 2026-09-14. K1 ruled as written (§7); the slice 8 build authorised.

The candidate stands verbatim. The build is the one listed under §7 and nothing more: the
single `artefact_concerns` kind in the registry (subject the artefact; second participant the
identities ruled so far — the obligation; reading-sourced claims candidates only; relational
knowing, strength `undetermined`) · fixture over Ab1–Ab10 with Ab7 asserted *not representable*
and Ab8 *not establishable* · the five mutations · no migration. Out, as fenced: proposition-
level about-ness · multi-link strength · any consumer of "about O" · candidate generation · the
other identities.
