# Slice 5 — what is a claim about a claim?

> Status: **Build mode, slice 5 opened by Rob 2026-09-13; RULED (§7); BUILT (`2f127c9`); CLOSED
> (§8).** Slice 4 is
> accepted at `780c5f1` (`CORRESPONDENCE.md` §9). This record tests the four named candidates —
> correction · retraction · contradiction · reaffirmation — against the Case-B history and the
> rulings that already touch it, answers Rob's five questions for each, finds one substrate
> limitation, and ends with a ruling candidate, ruled in §7.

```text
ordinary proposition → subject may be an utterance
claim-about-claim ≠ mechanism
represent the assertion → do not resolve its consequence
```

**Rob's question, verbatim:** *what proposition kind represents a party's assertion about an
utterance or proposition?* The `subject_utterance_id` mechanism has existed since slice 1
(Case B in the substrate fixture); what is not ruled is **what claim that pointer means**.

**Rob's fence, verbatim, carried in:** *Slice 5 rules representation, not resolution.* If the
cases establish `U2 corrects U1 · U3 retracts U2 · U4 reaffirms U3`, slice 5 may make those
claims representable. It must not decide which claim governs, rewrite the earlier proposition,
collapse history, or make `multiple` / `contested` disappear.

---

## 1. What is already ruled, and therefore constrains the answer

| Ruling | What it fixes |
|---|---|
| **Utterance identity, Case B** | Friday's *"…but I was wrong Monday"* is a **second event about the first**; *the retraction/correction relation is a claim like any other, with origin and strength, pointing at an event that still exists*; a false correspondence — or a party's own correction — never retroactively means the utterance did not exist |
| **Utterance identity, the ABOUT list** | *later contradiction / retraction — a further claim taking the utterance as subject (RA4, Case B)*; strength is derived, never carried |
| **Proposition ruling** | *Monday's assertion was wrong* has subject **an utterance** — one of the seven subject types; the seven kinds' meanings were not ruled |
| **Q2 / `resolution()` contract** | `resolution = kind · resolver · contradictions · post`, **derived on read from the chain, never stored**; kinds `none · superseded · reaffirmation · self_reversal` are *names of derived states over a chain of stances*, not claims |
| **R-ASSERT** | RA4: the household later says the portal showed $1,295 — *a testimony conflict; the source-history kinds are already correct*; **RETRACT reaches everything derived from it**; retract reaches testimony only, never a held artefact |
| **Slice 1 / the relationship** | *no `supports` flag: a negative claim is a proposition with negative content evidenced here* — contradiction of a value is an ordinary domain proposition |
| **Gap 1** | state, not removal: a reversed determination is superseded, never deleted |
| **Slice 3 `multiple`, slice 4 `contested`** | both detect *that a claim exists about an establishing utterance*; neither derives *what it says*; the resolver is fenced — twice |
| **Minting assertion** | unminting not opened; an institution sits under the claim that minted it |

---

## 2. The four candidates, against the cases

Each named candidate is asked Rob's five questions. The cases are the ruled ones; the
question for each candidate is whether any case **forces** it as a kind — or whether it is
already representable as something the substrate has, or is a *derived* state the resolver
names.

### 2.1 Retraction — *"I was wrong Monday"*

| Case | What happens | What must be representable |
|---|---|---|
| **B** (slice 1 fixture) | Rob, March: "my servicer is Acme" (U1). Sept: "I was wrong in March" (U3) | a proposition whose subject is U1, evidenced by U3; U1 remains with its evidence |
| **O8** | "from Lakeview Health" (U_a); later "no — that was from the hospital" (U_b) | a proposition about U_a **and** a new origin claim naming Riverbend Hospital — both evidenced by U_b |
| **X11** | "b1 and b2 are the same" (U_same); "no — b2 was the corrected one" (U_no) | a proposition about U_same; the correspondence claim remains; the referent reads *contested* |
| **RA-retract** | the household withdraws "the statement dated Sept 1 says $1,925" | a proposition about the asserting utterance; **the asserted artefact stays** (never removal); what was derived from the testimony is *reached* by the retraction — a consumer's derivation |
| **S3, later** | "S3 was never my servicer" | a proposition about the utterance that asserted the servicer role; S3 the *party* keeps its provenance (minting ruling) |
| **H10** (new, from slice 3) | "I was wrong — 'Lakeview Health Health Inc' isn't a separate company" | a proposition about the minting utterance; the institution sits under a claim now said to be wrong; **unminting is not derived** (fenced) |

1. **Subject:** the utterance — the act — never the domain proposition. *Monday's assertion was
   wrong* is about what Monday *did*; "the servicer is not Acme" would be a domain claim with
   negative content and the world as subject. The cases never need the second form to carry
   the first's meaning.
2. **Second participant:** **none**. What replaces the retracted assertion, if anything, is a
   *separate domain proposition* evidenced by the same utterance (O8: the Riverbend Hospital origin claim) —
   one act, two propositions, slice 1's rule. Putting the replacement inside the retraction
   would hide a referential operand in content (the A ruling of `SMALLEST_SCHEMA.md` §12).
3. **Content:** the party's stance on the utterance's assertion — opaque; *"wrong"*, *"I no
   longer stand by it"*, a reason. The kind carries the meaning: *the claimant holds that what
   U asserted does not stand.* Content never carries the replacement.
4. **Forced?** **Yes** — by B, O8, X11, RA-retract, S3 and H10, all the same shape. This is the
   one kind the cases force.
5. **Who establishes:** any party's utterance, the ordinary discipline. In every ruled case the
   claimant is the **origin party of the subject utterance** (self-retraction). A third party
   saying "your March assertion was wrong" is not in the corpus — K3's E does not say that; E
   asserts the domain fact and the *conflict* is derived. So the kind's knowing relation is
   forced only for the self case, and that case exposes a limitation (§3).

### 2.2 Correction — *"I was wrong, it was the hospital"*

O8 and Case B are the cases, and both decompose without remainder: **correction = a retraction
+ a new domain proposition evidenced by the same utterance.** Whether a replacement exists is
*structural* — another proposition under the same utterance — not a kind. A `correction` kind
would either duplicate `retraction` with a flag, or carry the replacement as an operand (the
hidden-operand mistake). **Not forced.** Slice 1's and slice 4's fixtures used the label
`'correction'` for an unruled kind; when the ruled kind exists they point at it — retirement in
place, at build.

### 2.3 Contradiction — *"X is false"*

| Case | Shape |
|---|---|
| **Q2** `E:n U:y U:n E:n` | four domain utterances, alternating content; *self_reversal* is the resolver's **derived** name for the last prior stance being the opposite |
| **K3** | E's statement conflicts with S3's letter — two parties' domain claims; corrected *by conflict, never by rank*; the conflict is computed |
| **V-cases / D3** | $412 vs $4.12 — a parse dispute, *computable by structure and nothing is chosen* |
| **RA4** | $1,925 then $1,295 from the same source — a testimony conflict; source-history kinds already correct |

Contradiction is **derived**: two propositions of one kind and subject with differing content,
or a party's stance reversing across its own utterances. Storing it as a claim would store the
resolver's output as evidence — the `resolution()` lesson (*derived on read, never stored*)
and the `[-1]` family in one. When a party *says* "that's false" about a value, that is a
**domain proposition with negative content** (slice 1: no `supports` flag) — subject the world,
not the utterance. When a party says "*your assertion* was wrong", that is §2.1's kind by a
non-origin party — the same kind, a different claimant; not a separate name. **Not forced.**

### 2.4 Reaffirmation — *"I stand by it"*

Q2's *reaffirmation* is *the party asserting the same stance again* — **a second utterance
evidencing the same proposition** (slice 1: *same proposition, many utterances*; the tie ruling:
*count is history*). The resolver derives the name. The higher-order form — "my March
assertion was right" — appears in no ruled case; RA5's two members, Q2's `U:y … U:y`, the tie
ruling's "said twice, agreed" are all second assertions, not claims about the first. **Not
forced.** If a case ever needs "U1 stands" as a claim about U1, it is the same shape as §2.1
with opposite content, and it would be ruled then — not named now because the word is handy.

### 2.5 What the four reduce to

```text
retraction       FORCED     one kind: a party asserts that what utterance U asserted does not stand
correction       = retraction + a new domain proposition under the same utterance  (structural)
contradiction    DERIVED    two claims of one kind + subject, differing content; or a reversed stance
reaffirmation    DERIVED    the same proposition evidenced by a later utterance
```

One kind, not four. The other three names live where Q2 put them: in the **derived**
vocabulary of a resolver that reads the chain — and that resolver is not this slice.

---

## 3. A limitation found: the knowing relation is relational here

`derived_strength` takes `knowing = {kind: {foundation, …}}` — a kind is knowing for
*persons* or *institutions*. For §2.1's kind the knowing party is **the origin party of the
subject utterance**: whoever made the assertion is first-hand about withdrawing it. That is a
*relation between the claimant and the subject*, not a foundation. The same is true of a kind
already ruled and not yet built: **P-ack's knowing party is *the entitled party of this
obligation*** — also relational. The foundation-keyed map was a slice-1 simplification adequate
for the health kinds and the artefact/correspondence kinds, and this is the first ruled kind it
cannot express.

Two ways to proceed; the candidate takes the second:

- **(a)** extend the knowing relation so an entry may be a predicate over (claimant,
  proposition) — a mechanism, small, but a mechanism added to represent one kind;
- **(b)** leave the strength of this kind **`undetermined`** in slice 5, record the limitation,
  and let the first *consumer* of higher-order claims (the resolver) force the relational form
  when it is opened. Fail-closed; nothing invented; consistent with the fence.

Under (b) the self-retraction case is representable, attributable, and unscored — which is
what *represent, do not resolve* means in practice.

---

## 4. Claims about propositions — not this slice

Rob's question allows *an utterance or proposition*. The cases never need a **proposition** as
subject: "X is false" is a domain claim with negative content; "P is disputed" is derived; "P
and Q are one claim" is `proposition_corresponds` (fenced, unforced). No `subject_proposition_id`
slot is added. If a case ever forces one, it is an additive slot like the others.

---

## 5. What the slice must not do — restated mechanically

- **No verdict.** No function returns "U1 is retracted" as a state of U1, or removes U1 from
  any derivation. `multiple` and `contested` stay exactly as built — they may later be
  *narrowed* to the ruled kind (today any claim about an establishing utterance triggers them,
  which is over-broad), but narrowing is a change to slice 3/4 behaviour and is not done here.
- **No rewrite.** U1, its evidence, its propositions, the asserted artefact under it, the
  institution minted by it — all remain. The immutability guard already enforces this.
- **No chain.** "U3 retracts U2 which retracts U1" is three claims; what governs is not
  derived.
- **No reach.** *RETRACT reaches everything derived from it* is a **consumer** property: the
  things derived from U1 are derived by consumers, and it is they who must look for claims
  about U1. The substrate makes the claims findable; it does not propagate them.

---

## 6. Ruling candidate — for Rob

> **One proposition kind represents a party's assertion about an utterance: *what this
> utterance asserted does not stand* — subject the utterance (the act, never the domain
> proposition), no second participant (a replacement is a separate domain proposition under the
> same utterance), content the claimant's stance, opaque. It is established by any party's
> utterance under the ordinary discipline; in every ruled case the claimant is the subject
> utterance's own origin. Correction is that kind plus a new claim in the same act;
> contradiction and reaffirmation are derived states over ordinary claims and are not kinds.
> Its strength is `undetermined` in this slice: the knowing relation for it is relational
> (the subject's origin), which the foundation-keyed relation cannot express — recorded, and
> left to the first consumer. No claim takes a proposition as subject. Nothing is resolved:
> the earlier utterance, its evidence and everything under it remain, and `multiple` /
> `contested` are unchanged.**

Kind name: Rob's. The record has avoided *retraction* as the identifier because it names an
act (something a party does) where the proposition names a stance (something a party holds
about an act); `utterance_does_not_stand` is literal but long, `assertion_withdrawn` reads as
the act. Whatever is chosen must not be read as a verdict on U1.

If ruled, slice 5's build contents are: the kind · its `RULED_KINDS` entry (subject: utterance;
object: none — the first registry entry with a *required absence* of a second participant) ·
fixture over B, O8, X11, RA-retract, S3-later, H10 with the *not-derived* consequences asserted
(U1 present; origin/referent states unchanged; artefact/institution present; `multiple` and
`contested` unchanged) · the slice-1/4 fixtures' `'correction'` label retired onto the kind ·
mutations (a verdict function appears; the earlier claim is removed or re-pointed; a second
participant is smuggled in; the replacement is read out of content; strength is scored from
the foundation) · no migration. **Not in it:** the resolver · narrowing `contested` · reach
· a proposition subject slot · the other three names.

*The line: a party may say its earlier word does not stand; the record keeps both words and
decides nothing.*

---

## 7. Ruling — Rob, 2026-09-13. The one-kind result, with one terminology correction; build authorised.

**The key distinction:** *the proposition is about the utterance, not about the truth of the
proposition the utterance contained.* That keeps the higher-order layer from becoming a hidden
resolver.

**The kind is named `utterance_retraction`.** Its literal proposition: **"The assertion made by
utterance U no longer stands."**

- Subject: `utterance` · Second participant: none · Content: the claimant's stance toward that
  utterance's assertion · Evidence: an ordinary party utterance · Replacement: not part of the
  retraction; a new domain proposition may be evidenced by the same utterance · Truth /
  conflict / repetition: not encoded here — resolver-derived concepts.

```text
U1: "The EOB is from Lakeview Health."          U2: "I was wrong. It was from Riverbend Hospital."
U2 produces two propositions:   utterance_retraction(U1)   ·   artefact_origin(EOB, Riverbend Hospital)
```

Correction is an *interpretation* of those two propositions occurring in one act, not a kind.
`"That is false"` produces a domain proposition, not `contradiction(U1)`; `"I still stand by
that"` produces a later assertion, not `reaffirmation(U1)` — both derived.

**One tightening — "opaque" must not mean an arbitrary payload.** The substrate preserves the
proposition as a *normal* proposition under the ordinary evidence/strength discipline. What it
must not preserve is a semantic verdict — `retracted = true`, `contradicted = true`,
`reaffirmed = true` — resolver vocabulary. The chain is

```text
party → utterance U2 → utterance_retraction(U1) → a resolver later interprets the relationship
```

never `party → U2 → "U1 is retracted"`, which has already performed the resolution.

*Applied in the build as:* `content` stays what every proposition's content is — text the
derivations never read — and the kind carries the whole meaning; a retraction with empty
content is a complete retraction (so no meaning can migrate into content); and no column,
accessor or function anywhere yields a verdict on U1.

**The limitation is real and remains a fence.** *Does the origin of U2 know the status of U1's
assertion?* is relational — `origin(U2) → knows_about → U1` — not `Person → knowing`. The
strength system is **not** expanded in slice 5; `undetermined` is the correct result until a
ruled consumer requires the relational form. *Represent the claim now; don't invent the
machinery needed to interpret it.*

**The ruling, as Rob stated it:**

> One higher-order proposition kind is forced: `utterance_retraction` — a proposition whose
> subject is an utterance and whose content asserts that the assertion made by that utterance
> no longer stands. It has no second participant; any replacement or contrary domain
> proposition is a separate proposition, potentially evidenced by the same utterance.
> `correction` decomposes into retraction plus a new domain proposition; `contradiction` and
> `reaffirmation` are derived relationships, not stored kinds. No proposition takes another
> proposition as subject. The claim is established through the ordinary party/utterance
> discipline. Its knowing relation is currently relational to the subject utterance rather
> than foundation-keyed, so strength remains `undetermined` until that relational form is
> separately ruled. Resolver interpretation is fenced: this slice represents claims about
> assertions; it does not decide whether an assertion is retracted, contradicted, reaffirmed,
> replaced, or otherwise resolved.

**The invariant, explicit:**

```text
A higher-order claim can say that an utterance's assertion no longer stands.
It cannot itself rewrite, resolve, or replace that utterance.
```

**Authorised at exactly this line:** the single `utterance_retraction` kind on the existing
`subject_utterance_id` mechanism · fixture coverage for the forced cases · **no** resolver ·
**no** `subject_proposition_id` · **no** relational-knowing expansion · **no** change to the
existing `multiple` / `contested` derivations unless a separate ruling requires them.

---

## 8. Slice closed — Rob, 2026-09-13. `2f127c9`, 898 green, clean tree.

Cleanly closed. **Slice 6 is opened — not as "how do we model health / roles / obligations?"
(that jumps from the sequence into implementation) but as the common substrate question
underneath those instances: *what is a domain proposition?*** Three things to test without
designing any particular domain: its subject (a world referent, not an utterance) · what
distinguishes content from participants (a genuine referential operand is structural, never
smuggled into text) · what makes it a domain claim rather than a claim-about-a-claim (slice 5
gives the boundary: `utterance_retraction` is about an act; slice 6 needs propositions that
say something about the world, even when the evidence is an utterance).

**Fence, held especially hard:** *slice 6 rules representation of the domain propositions, not
their interpretation.* If a case says an EOB acknowledges something: establish what proposition
was asserted, its subject/participants, and who can establish it — not what the
acknowledgement means for an obligation, balance, health state or downstream derivation.

**P-ack is not permission to generalise the strength model.** It is a concrete case that may
force the substrate to represent *who knows a claim in relation to this particular thing*; if
the cases do not force a generalisation, it stays fenced exactly as slice 5 left it.

Record: `DOMAIN_PROPOSITION.md`.
