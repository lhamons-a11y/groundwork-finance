# Relational knowing — what does it mean for a party to know a proposition, and what does that relation establish?

> Status: **Build mode, queue item 1, opened by Rob 2026-09-14 — a doctrine record, no code. Two
> doctrinal repairs applied on Rob's review (§8a); the candidate is READY FOR RULING — not yet ruled,
> not yet authorised.** Nine
> ruled kinds carry `relational_knowing = True` and derive `undetermined`; the shipped health
> classifier carries a foundation-keyed set (`KNOWING_SOURCES = {USER_STATED, IMPORTED_EOB}`);
> slice 1's `derived_strength` takes a caller-supplied map `{kind: {person, institution}}`. This
> record derives the competing readings of *knowing* from the rulings and the code, tests them,
> says exactly what the relation establishes and what it does not, projects the result onto the
> waiting kinds to see which become derivable and which honestly stay `undetermined`, and ends
> with a ruling candidate **and a readiness judgement** — whether the ontology is ready to
> freeze. Nothing here is authorised to build.

**Rob's question, verbatim:** *what does it mean for a party to know a proposition, and what
exactly does that relation establish?*

**Rob's warning, verbatim:** *a sloppy definition here could retroactively change the meaning of
nine already-closed slices.* So §6 is the retroactivity check: what, if anything, the ruling
changes in the record of any closed slice. The intended answer is *nothing representational*.

**Must not collapse into knowing** (Rob's list): reading / observation · assertion / utterance ·
evidence · proposition correspondence · about-ness · strength · truth · participant
establishment. §2 takes each in turn.

---

## 1. What is already ruled, and therefore constrains the answer

| Ruling | What it fixes about knowing |
|---|---|
| **C1** (`PROVENANCE_IDENTITY_CONTRACT.md`) | origin is *the party whose knowledge the reading ultimately conveys*, **fixed per proposition kind**; the shipped reason: *"each has first-hand knowledge of the health proposition — the user was there; the insurer adjudicated the claim"*; **the same party can be an origin for one proposition and a mere channel for another** — the user *originates* "it was health" and *relays* "the statement says $1,925" |
| **K5** | *the user does not independently know what E acknowledges* — the household is not knowing for P-ack |
| **Acknowledgment ruling** | P-ack has **one knowing party, E, reached by four channels**; the health `KNOWING_SOURCES` set, ranks and tie **do not transfer** — *the weakest-link mechanism transfers* |
| **C2** | capture channel never determines origin; the reader is a channel (slice 2); a reading's authority is its artefact's origin's (slice 3) |
| **C3** | origin can be **mediated** by asserted links, each with its own strength; the chain's strength is **weakest-link**; *the chain is data, not a type* |
| **C4** | independence is between **origins**, per proposition, three-valued; never from type, channel, count |
| **Q2 / `resolution()`** | *source type ≠ source instance*; `IMPORTED_EOB` is a kind not a document; resolution derived on read, never stored |
| **Slice 1** | strength = origin foundation × kind, **derived on read, never stored**; the knowing map is caller-supplied *because the catalogue is not ruled*; absence of a rule → `undetermined` |
| **Slice 3, O5** | Rob's spreadsheet: origin Rob; Rob not knowing for the insurer's figure → the relayed value derives `not_knowing`; "it was health" from the same sheet derives `knowing` — **C1 through a document** |
| **Slice 5** | the retraction's knowing party is *the subject utterance's own origin* — **relational to the subject, not a foundation**; P-ack's *E of this obligation* likewise; strength left `undetermined` rather than expanding the map |
| **Slice 6 §5** | *every* domain kind's knowing party is relational: *the insurer of this claim* · *E of this obligation* · *the household for its own relations*; `{'institution'}` for a health value means *any* institution — a Harbor statement saying "health: yes" would derive knowing through Harbor |
| **Party ruling** | NO PARTY is positive: a process *contributes nothing to independence*; a process cannot utter (O9) |
| **Payment slice** | the bank knows movement; E knows acknowledgment; the household knows intent and identification; **the minting party is not thereby the knowing party for every property** — Pm9's mother pays, Rob asserts |
| **Ab7, correspondence** | about-ness and correspondence are asserted relations with their own (relational) knowing parties; neither transmits anything |

Two consequences before the readings. First, **knowing is already, by ruling, relative to the
proposition's kind and to some participant of it** — the insurer *of this claim*, E *of this
obligation*, the origin *of this utterance*. Second, knowing has only ever been *used* for one
thing: **classifying the strength of an evidentiary relationship** (`knowing` / `not_knowing` /
`undetermined`). Nothing else in the record consumes it.

---

## 2. What knowing is not — each separation already ruled

| Not this | Why — the ruling that separates it |
|---|---|
| **reading / observation** | a reading is what Groundwork saw; the *reader* is a channel (C2, slice 2). Knowing belongs to the artefact's origin, never to whoever read it. O4: Rob reads Lakeview Health's portal; Lakeview Health knows |
| **assertion / utterance** | an utterance is what a party *said*; saying does not make the party knowing (K5: the user asserts what E acknowledged and is not knowing). Every utterance has an origin; only some origins are knowing for what they assert |
| **evidence** | an evidentiary relationship says *this proposition is evidenced by this utterance / reading*. Knowing is a property *of the origin behind that source relative to the proposition* — it grades the relationship; it is not the relationship |
| **correspondence** | asserts one referent for two identities; transmits nothing (slice 4, `proposition_corresponds` §8). Whether the asserting party is knowing for *that* is its own relational question |
| **about-ness** | asserts what a proposition concerns; the asserting party's knowing for the about-ness claim is separate from anyone's knowing for the value (Ab7: the value keeps Harbor's authority; the association is Rob's assertion) |
| **strength** | strength is the *output*: `knowing(kind, origin) × chain` → knowing / not_knowing / undetermined. Knowing is one input; conflating them makes strength a stored property (the `strength_of` lesson) |
| **truth** | a knowing party can be wrong (S3: E's own statements can be false; identity ≠ truth). Knowing says *first-hand*, never *correct* |
| **participant establishment** | whether a proposition's participant is established is structural (slice 6); knowing is about the party behind the evidence, not the referent's state |

---

## 3. Readings of "a party knows a proposition"

**R1 — knowing is a foundation property.** Persons are knowing for some kinds, institutions for
others. This is slice 1's `{kind: {person, institution}}` and the shipped `KNOWING_SOURCES`
(source *types*). Kills itself on Kn10 (any institution knowing for health) and on Q2 (*source
type ≠ source instance*). It was always a stand-in; slice 1 said so.

**R2 — knowing is a relation derived from the party's ruled relation to the participant the
kind designates.** Not *some* relation to *any* participant: **the kind names one epistemically
relevant relation to one designated participant**, and only standing in *that* relation to
*that* participant confers knowing —

```text
PROPOSITION KIND → designated epistemic relation → designated participant → party
```

never `party relates to P somehow → party knows P`. Per kind, the catalogue names which
relation and which participant: for a retraction,
*being the origin of the subject utterance*; for P-ack, *being the entitled party of the object
obligation*; for a health value read from an EOB, *being the origin of the artefact that
adjudicated the claim*; for a payment's movement, *being the bank the payment went through*; for
a payment's occurrence, *being the payer* (Kn7). The relation is read off **structure already
in the record** (utterance origins, artefact origins, minting utterances) and off **role claims**
(entitled party, obligated on, paid by) where those are ruled. Never stored.

**R3 — knowing is itself an asserted claim** (*"P knows about X"*, a proposition kind). Fails on
the record's own discipline: what would be *asserted* is the **role** (P is entitled to O; P paid
p) — those are already claims — and knowing would then be a stored restatement of a derivation
over them, the thing the `resolution()` / `strength_of` lesson forbids. R3 collapses into R2 plus
a redundant table.

**R4 — knowing is strength.** Rejected in §2.

R2 is tested.

---

## 4. The cases

| # | Case | Ruled in | Under R2 — who is knowing, by what relation, and what it establishes |
|---|---|---|---|
| **Kn1** | Rob retracts his own March assertion (U1). | slice 5 | Rob is knowing for `utterance_retraction(U1)` **because he is the origin of U1** — a structural relation already in the record (`U1.origin_party_id`). A third party's "your March claim was wrong" is *not knowing* by this relation (it may be knowing for the domain fact by another). **Derivable today** |
| **Kn2** | Harbor acknowledges Rob's payment p (D4 / P-ack). | K-cases | Harbor is knowing **because Harbor is the entitled party of the obligation p is toward** — a **role claim** (`entitled_party(Harbor, O)`, stand-in kind, unruled). Rob is not (K5). **Derivable only once the entitled-party kind is ruled**; until then `undetermined`, honestly |
| **Kn3** | A health value read from Lakeview Health's EOB. | C1, slice 3 | Lakeview Health is knowing **because Lakeview Health is the origin of the artefact** (built) **and the adjudicator of the claim** — the second half needs the *claim* identity (queue item 4). With origin alone: knowing for *what the EOB states* (P-subject), not yet for *the claim's true value* (P-world) — which is exactly Cluster B's two propositions. **Partly derivable now, correctly scoped** |
| **Kn4** | Rob says "that statement is my mortgage" (`artefact_concerns`); "line 3 is the HELOC" (`proposition_concerns`); "those two parses are one line" (`proposition_corresponds`). | slices 8, Ab7, corr | For the two **concerns** kinds Rob is knowing **because he is the origin of the utterance that minted the identity concerned** (`O.minted_by.origin`) — the household member who declared the obligation knows which documents are about it. Structural, built. For **`proposition_corresponds`** no epistemic relation is established by the corpus: *being able to see a held artefact* would be a general shortcut the record does not support (held is custody, not knowledge — the capture ruling). **Stays `undetermined`**: correspondence must not acquire an epistemology merely because a flag needs a value |
| **Kn5** | K5: Rob says "the EOB says $412". | C1, C2 | Rob is the **origin** of the utterance and **not knowing** for the value: he has no ruled relation to the claim's adjudication. His utterance is testimony *about* an artefact; the value's knowing party is the artefact's origin. **R2 gives K5 for free** — no special case |
| **Kn6** | K2: the servicer S states E's acknowledgment. | C3 | S is not E; S's statement conveys E's knowledge **through an asserted link** (*S services O*, a role claim). Knowing is E's; the chain S → E is weakest-link over the link's strength. **A consumer derivation over role claims; not this slice's** |
| **Kn7** | Pm9: "my mother paid Riverbend Hospital $300 for me." | payment slice | Rob **minted** p and is **not knowing** that it occurred — he was told. The mother (`paid_by`) and Riverbend Hospital (`paid_to`) are the first-hand parties. **Minting ≠ knowing** — the sharpest case: identity comes from the household's assertion, knowledge of the event's properties from the participants |
| **Kn8** | Rob's spreadsheet: "it was health" and "$412 (Lakeview Health EOB)" on one sheet. | O5 | Rob is knowing for the first (he was there — a relation to the *expense event*, a referent not yet minted; today approximated by "the household for its own transactions") and not for the second (relayed). **C1's own example; R2 states why** |
| **Kn9** | A parser's reading; Groundwork's export. | O9, party state 4 | a process is **never** knowing: it has no party, hence no relation to any participant. Reading-sourced claims derive through the artefact's origin, never through the reader |
| **Kn10** | A Harbor bank statement's reading yields "health: yes" for a debit. | slice 6 §5 | Harbor is the artefact's origin and **not knowing** for health: Harbor adjudicated nothing. Under R1 (`{'institution'}`) this derived *knowing* — the case that kills R1. Under R2: no ruled relation between Harbor and the claim → `not_knowing` |
| **Kn11** | Two knowing parties for one kind (health: the user *and* the insurer; Q2's tie). | Q2, tie ruling | R2 allows several relations per kind; two parties both knowing is the ruled tie, resolved by recency on the evidence's own axis (Q2, chosen and not reopened). Knowing does not rank them |
| **Kn12** | E itself is wrong (S3's letter; a mis-applied payment). | S3, identity ≠ truth | E is knowing and wrong. Knowing establishes *first-handness*, never correctness; the conflict with other evidence is the resolver's, fenced |

**R2 survives every case, and gives K5, O5, Kn7 and Kn10 without special-casing.** What the cases
fix:

- **Knowing is a relation, fixed per kind, between a party and the participant the kind
  designates, in the relation the kind designates** — *origin of the subject utterance* · *origin
  of the artefact* · *entitled party of the object obligation* · *payer / payee of the object
  payment* · *origin of the minting utterance of the identity concerned*. A party's other
  relations to the proposition's other participants confer nothing. It is **read off structure** (origins, minting) and **off
  role claims** (roles are dated relations, ruled but not yet built as kinds). **Never stored,
  never asserted directly** — roles are asserted; knowing is derived from them.
- **Minting ≠ knowing** (Kn7 — **a mandatory permanent regression case**: it forecloses
  `minted_by → knowing` and protects *identity provenance ≠ event knowledge ≠ proposition truth*).
  **Origin of an utterance ≠ knowing for its content** (Kn5).
  **Origin of an artefact ≠ knowing for every kind read from it** (Kn10). **A process is never
  knowing** (Kn9).
- **Several parties may be knowing for one kind** (Kn11); knowing does not rank them.
- **Knowing is never correctness** (Kn12).

---

## 5. What the relation establishes — and what it does not

**Establishes:** exactly one thing — **the strength class of an evidentiary relationship** whose
source (utterance, or reading via its artefact's origin) originates from that party, for that
proposition's kind. The three values have exact conditions:

```text
the kind's relation is ruled  AND  the designated participant is established
     AND  the party stands in that relation                          → knowing
     AND  the party does not stand in that relation                  → not_knowing
the kind's relation is not ruled                                     → undetermined
the designated participant is not established                        → undetermined
```

**`not_knowing` means "this party is not the party the ruled relation identifies"** — it does
*not* mean "we established that this party does not know." The record has no way to establish
the latter and never claims it (Kn10: Harbor is not the adjudicator, so `not_knowing`; nothing is
said about what Harbor knows). Over a mediated chain, weakest-link (C3) — a later consumer
derivation.

**Does not establish:** truth (Kn12) · participant establishment (structural) · resolution among
competing claims (Q2's resolver; fenced) · independence (C4 is between *origins*; knowing feeds
it, it is not it) · discharge, entitlement, disposition or any domain consequence · a ranking
among knowing parties (Kn11) · anything about-ness or correspondence carries (nothing).

---

## 6. The retroactivity check — what R2 changes in the nine closed slices

| | Under R1 (today) | Under R2 | Representation changed? |
|---|---|---|---|
| `derived_strength`'s `knowing` argument | `{kind: {person, institution}}`, caller-supplied | per kind, **a relation** between claimant and a named participant — supplied by the same caller path, or carried in `RULED_KINDS` as `knowing_relation` for the ruled kinds | **no column, no table, no kind.** One function's input shape; the *catalogue stays caller-supplied for unruled kinds* exactly as slice 1 said |
| kinds flagged `relational_knowing = True` | `undetermined` always | derivable **where the relation's participant is structurally present** — Kn1 (retraction: subject utterance's origin) now; Kn4's minting-origin relation now; P-ack / D5 / D7 / payment acknowledgment **only once the role kinds are ruled**; health's adjudicator only once the claim identity exists | the flag becomes *"knowing is relational for this kind; the relation is …"* — a narrowing, not a reversal; kinds whose relation needs an unruled role stay `undetermined` **and that is the honest output the slices already promised** |
| the fixtures' adversarial `KNOWING[...]` entries (*"supplied — and must not score"*) | pass because the flag short-circuits | must **still** not score: a foundation entry is not a relation. Kept exactly (Rob, slice 8 §10) | none — they become the test that R1 can no longer sneak in |
| `artefact_origin`, `artefact_corresponds`, `party_corresponds`, `obligation_` / `payment_corresponds` (flag False today) | foundation map | the same map is *wrong* for them too (any institution?) — but their knowing parties (recipient household; the origin party itself; the minting party) are R2 relations of the same shape; **re-flagged**, not re-ruled | none representational; the registry flag flips to relational with its relation named — stated as the retroactive tightening it is |
| the shipped classifier's `KNOWING_SOURCES` | source **types** | untouched (1.x; SHIPPED_VS_TARGET's fused `Evidence`) — a consumer of the old model, not repaired here | none |

**So R2 changes no row, no column, no kind, no fixture semantics.** It changes what
`derived_strength` is *given*, and lets four flagged kinds derive where they could not — while the
five that need role kinds or identities keep the `undetermined` they were built to give. That is
the retroactivity answer Rob asked for: **nothing closed reopens; several closed slices simply
stop waiting.**

---

## 7. Readiness — is the ontology ready to freeze?

**The definition is ready.** §4's twelve cases fix it without a new primitive: knowing is a
derived relation over structure and role claims, per kind, establishing strength class only.

**The projection is half ready.** Of the kinds waiting:

| Kind | Relation (R2) | Its participant | Derivable if ruled now? |
|---|---|---|---|
| `utterance_retraction` | origin of the subject utterance | built | **yes** |
| `artefact_concerns`, `proposition_concerns` | origin of the minting utterance of the identity concerned | built (minting) | **yes** |
| `proposition_corresponds` | none established — *held* is custody, not knowledge | — | **no — stays `undetermined`**; no epistemic shortcut is manufactured to make the flag derivable |
| `artefact_origin` | the recipient household (which household? the one whose Person asserted — the origin of the origin claim itself); the origin party itself | built | **yes** |
| `artefact_`, `party_`, `obligation_`, `payment_corresponds` | the origin of the minting utterances of both identities — a candidate relation of the same shape as the concerns kinds; **Rob decides whether it is established by the corpus or stays `undetermined` like `proposition_corresponds`** | built | conditional |
| P-ack / D4 (payment acknowledgment), D5, D7 | entitled party of the object obligation | **role kind unruled** (`entitled_party` is a stand-in) | **no** — `undetermined` until the role kinds are ruled |
| health value (P-world) | adjudicator of the claim | **claim identity unminted** | **no** |
| payment movement / occurrence | the bank of the payment; the payer | role kinds unruled | **no** |

**Recommendation:** freeze the **definition** (§8) now — it is what the nine slices were waiting
for, and it forecloses R1 for good — and authorise only the **mechanism** that lets a kind carry
its relation and lets `derived_strength` evaluate it (no schema), projecting it onto the kinds
whose participants are built. **Do not rule the role kinds here** to make P-ack derivable; that
is the domain catalogue, and Rob's ordering puts identities and roles later. Those kinds stay
`undetermined`, as built.

---

## 8. Ruling candidate — for Rob

> **A party knows a proposition when it stands, in the record, in the epistemic relation the
> proposition's kind designates, to the participant the kind designates — the origin of the
> subject utterance, the origin of the artefact, the entitled party of the object obligation,
> the payer or payee of the object payment, the origin of the utterance that minted the identity
> concerned. No other relation to any other participant confers knowing. Knowing is derived on
> read from that structure and from ruled role claims; it is never stored, never a foundation,
> and never asserted directly — roles are asserted, knowing follows from them. It establishes
> exactly one thing, the strength class of an evidentiary relationship whose source originates
> from that party, for that kind: *knowing* when the kind's relation is ruled, its designated
> participant is established, and the party stands in the relation; *not knowing* when the
> relation is ruled and the participant established but the party does not stand in it —
> meaning only that this is not the party the ruled relation identifies, never that the party
> has been shown not to know; *undetermined* when the kind's relation is unruled or its
> designated participant is not established; over a mediated chain, weakest-link. It
> establishes nothing else: not truth, not participant establishment, not resolution, not
> independence, not any domain consequence, and no ranking among several knowing parties.
> Minting an identity does not make the minter knowing for the event's properties; originating
> an utterance does not make the origin knowing for its content; originating an artefact does
> not make the origin knowing for every kind read from it; a process is never knowing; holding
> an artefact is custody, not knowledge. The foundation-keyed map is withdrawn as a definition
> and survives only as the caller's stand-in for unruled kinds. Nothing in any closed slice
> changes representation; kinds whose designated relation depends on an unruled role or an
> unminted identity remain undetermined, as built — and no relation is manufactured to make a
> flag derivable.**

### 8a. The two doctrinal repairs, on Rob's review (2026-09-14)

1. **"One of the proposition's participants" → the kind-designated participant and relation.**
   The earlier wording could be read as *Rob relates to P somehow → Rob knows P*; the cases
   describe `kind → designated relation → designated participant → party`. Applied in R2, §4's
   summary and §8.
2. **The `not_knowing` / `undetermined` boundary made explicit** (§5): ruled relation +
   established participant + party not in the relation → `not_knowing`; unruled relation →
   `undetermined`; participant not established → `undetermined`. `not_knowing` is *"not the party
   the ruled relation identifies,"* never *"shown not to know."*

And, on Rob's third point: **`proposition_corresponds` stays `undetermined`** — *held* is custody,
not knowledge, and no epistemic shortcut is encoded to give the flag a value. Kn7 is marked a
mandatory permanent regression case.

**If ruled**, the build is mechanism only: a per-kind `knowing_relation` in `RULED_KINDS` for the
kinds whose designated participants are built, evaluated by `derived_strength` in place of the
foundation lookup for those kinds; the fixtures' adversarial foundation entries kept and shown
not to score; a fixture over Kn1–Kn12 with Kn7 permanent (Kn2, Kn3-world, Kn6, Kn7-payer asserted
*undetermined — role kind or identity unruled*; `proposition_corresponds` asserted *undetermined —
no established relation*); no schema, no migration. **Outside it:** the role kinds · the claim identity ·
the chain derivation · the resolver · independence · the shipped classifier.

*The line: a party knows a claim by where it stands to the thing the claim is about — not by
what kind of party it is, not by having said it, and not by being right.*
