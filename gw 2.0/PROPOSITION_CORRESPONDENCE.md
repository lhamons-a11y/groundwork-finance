# `proposition_corresponds` — what is a correspondence between propositions?

> Status: **Build mode, opened by Rob 2026-09-14; RULED (§7); BUILT (`ff8fcc4`); ACCEPTED and CLOSED
> (§8).** Ab7 is closed at
> `9566f23` (`PROPOSITION_ABOUTNESS.md` §8). `proposition_corresponds` was in slice 4's PARTIAL kind
> list, found **unforced** there (X8), and **pressed by a case** at Ab7 (Pa5: a re-reading's P3′
> has no about-ness of its own). This record asks what "two propositions are one referent" can
> mean, tests it against the ruled cases, finds the one place the slice-4 shape is not enough
> and one slot it forces, and ends with a ruling candidate, ruled in §7.

**Rob's question, verbatim:** *what is a correspondence between propositions?*

**Rob's fence, carried in from Ab7's closure:** *it should not be smuggled in as "about-ness
carrying"* — the need is to relate propositions produced by different readings, not to make Ab7's
claims follow a proposition around.

---

## 1. What is already ruled, and therefore constrains the answer

| Ruling | What it fixes |
|---|---|
| **Slice 4** | a correspondence claim: *two separately minted identities of one type are one referent*; both participants established, distinct, same type; established only by a party's utterance; observed matches are candidates; never merges rows, never rewrites a reference; the referent is the connected component, derived; **contested** reported, never resolved. Correspondence never crosses types |
| **Slice 4, X8** | `"$412"` (Rob) vs `"412.00"` (parser): *"those two pieces of evidence agree" is a comparison consumers derive over content under one kind + subject, not a correspondence* — **unforced** then |
| **Proposition** (`PROPOSITION.md`) | identity = the row (the minted claim-shape); *sameness beyond kind · subject · content is a correspondence claim; semantic sameness ≠ event identity*; no uniqueness on the triple |
| **Slice 1** | *same proposition, many utterances*: "said twice" is the SAME proposition row evidenced twice — row reuse at the entry path, identity not correspondence (the E3 pattern) |
| **Slice 2** | two readings of one artefact are two observation events; a **parse dispute** is *same kind + subject, different content across readings of one artefact*, computable by structure, nothing chosen |
| **Cluster B / 4 → 6** | **re-reading never corroborates**: three readings of one artefact = one source; P-subject (*artefact states X*) and P-world / testimony are **different propositions** by subject |
| **Ab7** | `proposition_concerns(P, X)` attaches to P; **a re-reading's P3′ has no about-ness of its own** (Pa5); about-ness is information about a proposition, never inserted into it — and, by Rob's closing invariant, never carried by the substrate |
| **Immutability** | rows never merge; slots never re-pointed |
| **Ab7 build** | `subject_proposition_id` exists; **no object-side proposition slot** — nothing forced one |

Two consequences before any case runs. First, the *shape* is slice 4's and not open: if there is
a proposition correspondence at all, it is a claim of its own, per type, established by an
utterance, candidates from observation, never merging. Second, since both terms of a
correspondence are of one type, **the claim needs a proposition in the second-participant
position** — an `object_proposition_id` slot, which Ab7 deliberately did not add because nothing
forced it. **This slice forces it**, if ruled. The open question is therefore not the shape but
the **meaning**: what is "one referent" for two propositions?

---

## 2. What "one referent" can mean for two propositions

A proposition is a claim-shape. Two proposition rows can be "one referent" in exactly one sense
the corpus supports:

> **They are two observations, or two recordings, of one and the same claim** — one statement
> the artefact makes (P-subject), read twice; or one assertion a party made, entered twice.

Not: two claims that *agree* (that is content comparison, derived — X8, Q2's reaffirmation);
not: two claims *about the same thing* (that is shared subject, structural); not: a claim and a
later claim that *replaces* it (that is retraction + a new claim, slice 5). Each of those was
ruled elsewhere and none is a correspondence.

Three candidate readings of the meaning, then, and only one survives the cases:

**M1 — same referent = same claim observed / recorded more than once.** P3 and P3′ are two
readings' outputs for one statement in the document; their *contents may differ* — that
difference is the parse dispute, now computable at line level. Correspondence says nothing about
which content is right.

**M2 — same referent = agreement.** Two propositions correspond when their kind, subject and
content match. Dies on X8 (agreement is a comparison), on Q2 (reaffirmation is derived over the
chain), and on the proposition ruling (an identical triple is still two rows, and their sameness
*beyond the triple* is what correspondence asserts — so matching content cannot be what
correspondence *is*).

**M3 — same referent = same subject.** Two propositions correspond when they are about the same
identity. Dies immediately: that is `subject_obligation_id = O1` on both — structural, already
representable, and not a claim.

M1 is tested.

---

## 3. The cases

| # | Case | Ruled in | Under M1 |
|---|---|---|---|
| **Pc1** | Pa5: reading 1 gives P3 = "balance $44,000"; reading 2 gives P3′ = "balance $4,400" for what a person can see is the same line. | Ab7 Pa5, slice 2 | the parser's position match yields a **reading-sourced candidate** `proposition_corresponds(P3′, P3)`; a party's utterance ("same line") **establishes** it. The referent {P3, P3′} is derived; **the contents differ — that is the parse dispute, now computable at line level**, and nothing is chosen. Both rows remain, each with its own reading's evidence |
| **Pc2** | Two readings agree: P3 and P3′ both "$44,000". | 4 → 6 | corresponding, contents equal — *"read twice, agreed"* — and **still one source**: readings of one referent never corroborate. Correspondence is what makes that derivation *possible*; the derivation itself (independence) is a consumer's |
| **Pc3** | P3 concerns O2 (Ab7). P3′ corresponds to P3. Is P3′ about O2? | Ab7 §8 (Rob's invariant) | **the substrate says nothing.** P3′'s participant stays candidates; no `proposition_concerns(P3′, O2)` appears; nothing is copied. A consumer *may* derive P3′'s about-ness through the correspondence — that is the consumer's rule, not the substrate's. **About-ness carrying is not what this claim does** |
| **Pc4** | X8: Rob's testimony T = "$412" (subject the world / O2) and the parser's P = "$412" (P-subject, the artefact's statement). | Cluster B, X8 | **not one claim** — different subjects by ruling (P-subject ≠ P-world); their agreement is a comparison. A household *could* assert `proposition_corresponds(T, P)`; it would be a category error the substrate represents and never treats specially (Pa7's discipline: claims can be wrong; identity ≠ truth). Whether to **refuse** it structurally is the one guard question (§4) |
| **Pc5** | Rob says "my servicer is Acme" in March and again in September; the entry path reuses the proposition row. | slice 1 | **identity, not correspondence** — the entry path recognising its own claim (E3's pattern for utterances). If two rows were nonetheless minted for one assertion, `proposition_corresponds` repairs the individuation as slice 4 did for artefacts (X1) — never a merge |
| **Pc6** | Reading 1 kinds line 3 as `balance`; reading 2 kinds it as `payment_due`. Same line. | kind is primary | corresponding across **kinds** is representable under M1 — the two readings disagree about what *kind* of statement the line makes; a dispute about kind, reported, nothing chosen. No kind-equality guard: the disagreement is real information |
| **Pc7** | Correspondence claims between concerns claims: reading 1's candidate `concerns(P3, O2)` and reading 2's candidate `concerns(P3′, O2)`. | — | representable (they are propositions); not exercised; nothing in the corpus needs it |
| **Pc8** | "No — those were two different lines after all." | slice 4 X11 | `utterance_retraction` of the correspondence utterance → the referent reads **contested**; nothing merged, so nothing to un-merge |
| **Pc9** | Transitivity: P3 ~ P3′, P3′ ~ P3″ (a third reading). | slice 4 X10 | the referent {P3, P3′, P3″} is the connected component, derived; **three readings, one source** |
| **Pc10** | The pipeline re-parses every statement monthly and wants prior about-ness to "follow". | Ab7 Pa5, Rob's fence | the pipeline may emit **candidates** (position/content matches) for `proposition_corresponds`; a party establishes; a consumer derives what follows. The substrate carries nothing across. Standing authorisation for the pipeline to establish is the importer-contract fence, unchanged |

**M1 survives every case.** What the cases fix:

- **Meaning:** *two separately minted propositions are two observations or recordings of one
  claim.* Contents may differ (Pc1); kinds may differ (Pc6); what is asserted is that the two rows
  are about one statement or one assertion — not that they agree.
- **What it enables, all as consumer derivations, none built:** the line-level parse dispute
  (Pc1); "read twice, agreed" and the one-source rule for independence (Pc2, Pc9); about-ness
  through correspondence (Pc3).
- **What it is not:** agreement (Pc4, X8); shared subject (M3); the entry path's row reuse (Pc5);
  about-ness carrying (Pc3, Pc10); replacement (slice 5).
- **The slice-4 discipline unchanged:** established by utterance; candidates from readings;
  never merges; contested reported; per type.

---

## 4. The one open guard question — and the slot it forces

**The slot.** A correspondence has two participants of one type; `subject_proposition_id`
exists (Ab7), `object_proposition_id` does not. This slice forces the object-side slot **for
this kind only** — the registry keeps it to `proposition_corresponds`; Ab7's *first and only*
becomes *the only ruled kind with a proposition subject, and `proposition_corresponds` the only
one with a proposition object*. Slice 5's non-kinds gain nothing.

**The guard.** Slice 4's `party_corresponds` had a ruled invariant to enforce (never crosses
foundations). Is there one here? Two candidates, stated so Rob can rule:

- **(g1) Established participants of one type must agree.** If P has `subject_obligation_id =
  O1` established and Q has `= O2` established, "P and Q are one claim" is incoherent — one claim
  cannot be about two obligations. Refusing it parallels the same-foundation guard and Ab7's
  one-source rule: the structural participants already say the two are not one. Pc4 (T about O2
  vs P-subject about artefact A) would **not** be caught by g1 — different slot types, no conflict
  — so g1 does not encode the P-subject ≠ P-world doctrine; it only refuses the flatly
  contradictory case.
- **(g2) No guard beyond slice 4's** (type, distinct, existence). Claims can be wrong; the
  consumer reports incoherence as it reports Pa7's level inconsistency.

The record leans **g1**, with its scope stated exactly so it cannot grow: **g1 does not judge
whether two propositions are semantically about the same thing. It prevents correspondence from
identifying one referent when the propositions' already-established same-type structural
participants explicitly disagree** — because then the "one claim" would have two established
structural subjects, a contradiction in the identity structure itself, not merely a false claim.
**g1 inspects established participants only** — never candidates, `proposition_concerns`,
content, kind, evidence, reading position, authority or semantic similarity; those stay outside
the guard, and a future "these don't seem equivalent" validator is exactly what g1 is not. Pc4
remains representable-but-wrong under g1, which is the honest position for a doctrine (P-subject
≠ P-world) the substrate cannot see in the rows.

---

## 5. Not decided here — fences and findings

- **Line-level parse-dispute derivation; independence over corresponding propositions (4 → 6);
  about-ness through correspondence** — all consumers of this claim; none built.
- **The pipeline's standing authorisation** to establish (monthly re-parse) — the importer-contract
  fence, unchanged; candidates only.
- **Relational knowing** — the household for what it can see are the same line; the origin party
  plausibly; `undetermined`.
- **Retraction propagation** — none; a contested referent is reported.
- **`utterance_corresponds`** — still unforced (E3 is identity); untouched.

---

## 6. Ruling candidate — for Rob

> **A correspondence between propositions asserts that two separately minted propositions are
> two observations or recordings of one claim — one statement an artefact makes, read more
> than once, or one assertion a party made, entered more than once. It is slice 4's kind shape,
> a fifth type: both participants established, distinct propositions; established only by a
> party's utterance; a position or content match observed by a reading may produce a candidate
> for the claim — the observation is not itself the claim, and candidate generation is outside
> this slice; the referent is the connected component, derived;
> never merged, never re-pointed; contested when its establishing utterance is disputed. Their
> contents and kinds may differ — that difference is the parse dispute, made computable and
> never resolved. It is not agreement, which is a comparison; not shared subject, which is
> structural; not the entry path's reuse of one proposition row, which is identity; not
> replacement, which is retraction; and not about-ness carrying — the substrate copies nothing
> across corresponding propositions, and what a consumer derives through the correspondence is
> the consumer's rule. It forces one additive slot, `object_proposition_id`, used by this kind
> alone; and it refuses a correspondence between propositions whose already-established
> same-type structural participants explicitly disagree — inspecting established participants
> only, never content, kind, evidence or similarity — since one claim cannot have two
> established structural subjects. Its knowing relation is relational and its strength
> `undetermined`.**

**If ruled**, implementation follows slice 4's shape: the additive object-side slot; the registry
entry; `referent()` extended to propositions; the g1 guard; a fixture over Pc1–Pc10 asserting
what is *not* carried or derived; no data step. **Outside it:** every consumer derivation named
in §5 · the pipeline's authorisation · `utterance_corresponds`.

*The line: two readings can be of one line; saying so decides nothing about what the line says.*

---

## 7. Ruling — Rob, 2026-09-14. Ruled as written; g1 ruled narrowly; the build authorised.

*The proposition-correspondence problem is not a new correspondence shape — slice 4 answered
that; what was missing was what the referent means when the thing individuated is itself a
proposition.* **M1 ruled; M2 and M3 rejected.** The decisive sentence: *two separately minted
propositions are two observations or recordings of one claim* — surviving the cases without
importing agreement, truth, subject identity or replacement. Pc1 proves correspondence cannot
mean semantic equality: the correspondence establishes that two proposition identities are
intended as representations of one claim; the disagreement remains information. **Pc3 keeps
correspondence relational rather than transmissive** — a consumer may reason *P3 ~ P3′ and P3
concerns O2, therefore for this purpose P3′ may be treated as concerning O2*; the substrate
mutates nothing, manufactures no `proposition_concerns`, transfers no evidence.

**g1 — ruled, narrowly**, as an *established-same-type-participant incompatibility guard*: it
does not judge semantic sameness; it prevents identifying one referent when the already-
established same-type structural participants explicitly disagree (a contradiction in the
identity structure, not merely a false claim). **g1 inspects established participants only** —
not candidates, `proposition_concerns`, content, kind, evidence, reading position, authority or
semantic similarity. Pc4 is a category error the ontology cannot recognise in the rows and is
not g1's business.

**`object_proposition_id` — forced**, for `proposition_corresponds` alone. The proposition-
participant taxonomy stays explicit and asymmetric, and is not to be generalised:

| Kind | Proposition participant |
|---|---|
| `proposition_concerns` | subject |
| `proposition_corresponds` | object (and subject) |
| slice-5 non-kinds | neither |

**Wording adopted:** *a position or content match observed by a reading **may** produce a
candidate for the claim; the observation is not itself the claim* — candidate generation stays
outside this slice.

**What the slice accomplishes:**

```text
READING ──observes/matches──► candidate
   ▼
PROPOSITION ──concerns────► IDENTITY
            └─corresponds─► PROPOSITION
```

Neither relation changes the thing on the left. `proposition_concerns` says what a proposition
concerns; `proposition_corresponds` says which proposition identities represent one claim;
neither says what the claim is true of, which content is correct, or what should be derived.

**Recorded:** M1 ruled · M2, M3 rejected · g1 ruled narrowly · `object_proposition_id` forced ·
consumer derivations not part of the ruling · about-ness propagation explicitly not part of the
ruling · `proposition_corresponds` ready for minimal implementation. No further semantic question
opened before building. **Build it.**

---

## 8. Slice accepted and closed — Rob, 2026-09-14. `2256ef7` ruling · `ff8fcc4` build · 941 green.

*Stronger than "941 tests pass": the implementation carries the ruling unusually faithfully.*

1. **The asymmetry is preserved deliberately** — no generic "proposition can point at
   proposition" mechanism: `proposition_concerns` → subject only; `proposition_corresponds` →
   subject + object; slice-5 non-kinds → neither.
2. **The reverse-order fixture repair was important** — it establishes the actual invariant,
   *correspondence is relational, not transmissive, regardless of which proposition already has
   the about-ness claim*; and the mutation attempts to implement precisely the forbidden
   architecture rather than merely corrupting a value.
3. **g1 stayed appropriately stupid** — *the most important engineering detail*: established
   same-type participant A ≠ B, and nothing more. Different content, different kind, different
   reading, candidates, about-ness, authority, similarity — all irrelevant. The moment g1 became a
   semantic equivalence checker, correspondence would have changed from a claim that can itself
   be wrong into a validator that decides truth. `g1_overreaches` protects against exactly that.
4. **Pc1 is the crucial test** — two readings, one line, different content, correspondence
   established, and *nothing chooses between the contents*. If future code ever "helpfully"
   reconciles $44,000 and $4,400, this fixture should break it.
5. **The migration is exactly the size it should be** — one self-FK, one index, no data step.
6. **The smoke mutations are pointed at architectural failure modes** — observation → assertion ·
   relation → transmission · relation → merge · guard → semantic judge · unruled kind → ontology
   slot.

**Recorded as an invariant of the whole relation, not merely a Pc3 test:**

> **No state belonging to either proposition is transmissively copied to the other by
> correspondence.**

Today demonstrated through about-ness; if another proposition-level relation appears, it is not
to be assumed to carry either. No expansion, no new tests now — the ruling says what it says.

**Verdict:** ruling accepted · implementation accepted · gate accepted · migration appropriately
minimal · mutation coverage meaningful including the previously missing reverse direction ·
scope clean · **no consumer rule smuggled into the substrate.** The correspondence says *these two
proposition identities have been asserted to be two recordings or observations of one claim* —
and then it stops. Exactly where it should.
