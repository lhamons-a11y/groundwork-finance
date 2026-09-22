# The bank line's own kind — candidate generation

> Status: **Queue item 14, opened by Rob 2026-09-21 from item 9's carried-forward list; no code.**
> Rob's question, verbatim: *what kind does a `bank_line` / `bank_returned_item` stand-in mint as
> evidence before anyone asserts what the line is a line of?* — with the constraint that *the
> candidate-generation question should stay sharply separated from the reader's later
> determination: the line can mint evidence of what the bank returned, while the consumer must not
> manufacture the proposition that it represents merely from context.* The opening establishes the
> existing stand-in shapes and cases first, then asks what candidate kind, if any, the record
> licenses. Cases → findings → candidate → ruling → a separate build authorisation.

**One correction against the record, before anything else.** `bank_returned_item` is not a
stand-in. 9D-i renamed it and 9D-iv F4 ruled it: *"`cleared` and `bank_returned_item` are the
bank's stances on a payment (subject the payment; content the line / date; `as_of` the date),
holder `drawn_on`; never acknowledgment (K6 — 7G reads neither). The bank-line shape (the bank as
subject, the thing a candidate) refused under the ruled names and kept under a stand-in — the
borrowed-name class."* (`CATALOGUES.md` §9D-iv F4.) The stand-in is **`bank_line`** alone. This pass
is about `bank_line`; `cleared` and `bank_returned_item` are constraints on it, not its subject.

---

## 1. What is already ruled, and therefore constrains the answer

| Ruling | What it fixes |
|---|---|
| **Transaction referent (T2, closed `5af820c`)** | *"Transaction" names no 2.0 identity. A bank line is a proposition read from a captured artefact whose origin is the bank — **the bank's statement that a movement occurred** — with the line's amount, dates, description, merchant, balance, card and check number as its content and the capture's `as_of` as its time. The movement it refers to in the world is **not minted**; where the household individuates one it does so as a payment / obligation / expense, and the line then concerns that identity by a `proposition_concerns` claim, candidate from a match, asserted by a party. Institution-side identifiers are content and correspondence evidence, never identity.* And: *"Build, if ruled: none. The answer adds no identity, no slot, **no kind** — a bank line is already a domain proposition the substrate represents."* — the kind was left unnamed, the stand-in `bank_line` standing in for it since. |
| **Payment identity (Pm2, Pm10, Pm12, Pm14)** | a bank line mints nothing; each autopay line is a candidate until asserted; a debit is a payment only when the household asserts it as one; a process cannot utter (O9) — a draft or a match is a candidate the household may assert. `s94`'s mutation *a bank line mints a payment* is caught. |
| **Reversal (item 3, ruled C)** | a later line is only a proposition; a reversal is a claim, never an identity; the payment-to-payment relation forced but unruled. Untouched here. |
| **Ab7 (K1p, ruled, built)** | *the line → p tie is `proposition_concerns(P, p)`* — a party's assertion; the matcher's pairing is a reading-sourced **candidate** concerns claim (Pa3); *the candidates state's carrier is the reading-sourced concerns claims* — `PARTICIPANT_CANDIDATES` names nothing and holds no reference. The payment identity is complete without Ab7. |
| **Proposition (slice 6)** | participants are structural, never content; a ruled kind's participants are established in the kind's slots, or `'object': ()` a required absence; **unruled kinds are constrained by the state discipline alone — the catalogue stays open** (`participant_violations`). |
| **9D-i (ruled)** | the reading path: *reading → origin → relation → strength; never reading → state*; a reading-sourced claim is a **candidate** whatever its strength. `reading_establishes: True` = strength through the artefact's established origin. |
| **9D-iv (ruled, built `86b85d5`)** | K6: *the bank knows movement*; `drawn_on` the bank's role on a payment; **the bank line is an evidence shape, never a role or a knowing source** (Va10); Va11: the line shape — *the bank as subject, the thing a candidate* — **refused** under `cleared` / `amount`, kept under `bank_line`, *no new kind*; Va6 / Pm12: a line about nothing paid mints no payment and, as a value, has no subject. |
| **9D-v (ruled)** | a kind may be *undetermined by design* — no relation named (`determination`). |
| **CORRESPONDENCE §3 (ruled)** | the knowledge *"these bytes equal those bytes"* / *"the letterhead says Lakeview Health"* is nobody's — a correspondence or origin claim read from an artefact is a candidate whose strength is not routed through the origin (`reading_establishes: False`). |
| **7A / 7C / 7D / 7E (ruled, built)** | consumers of the line shape: parse disputes group one artefact's readings by what each read (Pd4: a **kind** dispute — reading 1 kinds the line `balance`, reading 2 `payment_due`); proposition correspondence between readings of successive captures; level consistency; chain strength reads the line's strength through its origin. |
| **Candidate generation — fenced** | *the matcher, the importer contract, standing authorisation* — fenced on its own in `BUILD_QUEUE.md`, item 9 (*"it needs the kinds this item rules before it can generate candidates for them"*), and every consumer pass. **This pass rules the kind the matcher would generate; it does not open the matcher.** |

---

## 2. The stand-in as it exists — the shapes in the record today

The line stand-ins in the fixtures are **one shape with four (five) names and two subject slots**:

| stand-in | document | subject | object | content | `as_of` | strength today | sites |
|---|---|---|---|---|---|---|---|
| `bank_line` | the bank statement / feed capture | the **bank** (party) | `CANDIDATES` (Pm2, Pm10, Ab7) — `NONE` for Pm12's transfer | `HARBOR MTG 3/3 -1,412.00` | the **line's** date (3/3) | the fixture's foundation map `{'institution'}` | payment identity ×3, Ab7, Va11, `s94` |
| `statement_figure` (`payment_due`, `minimum`) | the creditor's statement | the **creditor** (party) | `CANDIDATES` | `$44,000` · `rate 6.1%` | the artefact's `as_of` | map `{'institution'}` | 7A, 7C, 7D, 7E, concerns, correspondence, independence, obligation identity (~40 sites) |
| `eob_amount` | the EOB | the **insurer** (party) — **or the artefact** (`subject_artefact_id`: artefact-reading, relational-knowing Kn5 / Kn8, retraction) | `CANDIDATES` / `NONE` | `$412 \| claim #A77` | — | map `{'institution'}` | slice 3, 7B, 7E, expense / plan identity, 9D-ii Xs13 |
| `sbc_line_figure` | the SBC | the **insurer** (party) | `CANDIDATES` | `$3,000 individual / $6,000 family` | — | map `{'institution'}` | plan identity, 9D-iii |

Three things the table shows that no ruling has said:

1. **The strength of every line is by foundation** — the fixtures' `KNOWING` maps, `{'institution'}`
   per stand-in. That is the mechanism 9D retired for every ruled kind (*the map entry unused*),
   surviving only on the stand-ins. 9D-iv said the bank line is *never a knowing source*; it is
   nonetheless scored, by type, wherever a fixture reads its strength (7E's L1 is *knowing*).
2. **The subject slot is unruled** — the party in most fixtures, the artefact in the slice-3-era
   ones — and the object state is *candidates* or *none* by the case's later knowledge (Pm12 is
   `NONE` because the fixture knows the transfer is no payment; at reading time nothing knows that).
3. **The bank line is not the same question as its three siblings.** The bank line's referent —
   the movement — **is never an identity** (T2). The statement's, the EOB's and the SBC's lines are
   the creditor's / insurer's positions about identities that exist or will (O, X, P) — *stances
   before their subject is tied* — the shape 9D refused under the ruled stance names (Va11, Xs13,
   9D-iii's SBC line). Two different questions: *a kind for a statement about a non-identity*, and
   *what a stance is before its subject is named*. This pass is the first. The second is named in
   §4 F1 and not ruled here.

---

## 3. The cases

The bank's March statement, held (`h-bank-mar`, origin the bank, established by Rob's utterance),
read by `feed-import/1`. `p1` minted by Rob (*I paid the mortgage on March 3*). Nothing else asserted.

| # | Case | What the record says today | The question it forces |
|---|---|---|---|
| **Bl1** | line 7 reads `HARBOR MTG 3/3 -1,412.00` | a `bank_line` proposition, subject the bank, object candidates, content the line, `as_of` 3/3, evidenced by the reading; a candidate; strength *knowing* by the map | **what kind is minted, with what participants, and where its strength comes from** |
| **Bl2** | Rob: *line 7 is my March mortgage payment* | `proposition_concerns(P7, p1)` established by Rob's utterance, knowing (Ab7); P7 unchanged; no payment minted | the tie is Ab7 as ruled — but **who mints `cleared(p1)`**, the bank's stance on the payment 9D-iv ruled (subject p1, holder `drawn_on`)? The line does not become it (Va11); the reading may evidence it as a candidate only once p1 is named |
| **Bl3 (Pm12)** | line 12 reads `TRANSFER TO SAVINGS -2,000.00`; Rob never ties it | today the fixture mints it with object `NONE` — *about nothing paid* | at reading time nothing knows it is about nothing paid; the honest generation-time state is the same as Bl1's. *About nothing* is the **absence of any tie**, not a state the reader may set |
| **Bl4 (Pm10)** | twelve autopay lines a year | twelve candidates; the importer contract (fenced) decides how they are asserted | the kind is the same twelve times; **nothing here opens the contract** |
| **Bl5 (Tx5 / K5)** | Rob types *my bank shows -1,412 on 3/3* | — | an **utterance** evidencing the bank's statement: subject the bank, claimant Rob → not_knowing. Distinct from Tx5's *$40 cash* — Rob's own payment claim, not a bank line at all |
| **Bl6 (O5)** | Rob's spreadsheet, read, has a row `HARBOR MTG 3/3 -1,412.00` | — | a line whose artefact's origin is **Rob**: a statement *by Rob* that a movement occurred — knowing for what Rob states of his own money, and **nothing about clearing**: `cleared(p1)` is the bank's by `drawn_on`, a separate proposition. Relaying launders nothing because the line is never the stance |
| **Bl7 (7C)** | two captures of the same feed read line 7 twice | two propositions, a correspondence candidate between them; the importer's to establish | unchanged by any reading below |
| **Bl8 (Tx11 / item 3)** | a later line `REVERSAL -(-48.20)` | a new line, a proposition; the reversal a claim | unchanged |
| **Bl9 (Pd4)** | reading 1 kinds line 7 `balance`, reading 2 `payment_due` | a **kind** dispute (7A) | on a **bank** statement there is one kind for every line; kind disputes on it vanish, content disputes remain. On a creditor's statement the kind dispute is §4 F1's question, not this pass's |
| **Bl10 (Va11)** | the line under `cleared` / `amount` | refused (the thing a candidate) | stays refused: the line is not a stance on a payment |
| **Bl11 (the null model)** | every existing `bank_line` site | Pm2 / Pm10 / Pm12 / Va11 / Ab7 / `s94` | the outcomes unchanged under a rename; the pins that read the object state (Pm2, Pm12) and the map are the class that moves |

---

## 4. Findings — put to Rob, not resolved

**F1 — scope: the bank line, or the line class.** The three sibling stand-ins are stances before
their subject is tied — a different question (§2, point 3): whether a reading mints the ruled stance
kind with its subject named by the matcher as a candidate (the shape 7G-F3 / 7J-F4 / 7J-F4-F1
already rely on — Dc3, Te5, Sb3: *the reading of Harbor's statement* evidencing `balance(O)` as a
candidate), or a generic line kind whose tie to O is Ab7. *Reading:* rule the **bank line only**
here — its referent is not an identity, so it cannot be a stance-before-the-tie — and **name the
sibling question** (*a stance before its subject is named*) as its own pass. **Rob's.**

**F2 — the kind: the bank's statement that a movement occurred.** T2 already says what the line
*is*; it declined to name the kind because the answer "adds no kind — a bank line is already a
domain proposition the substrate represents". It is represented **as a stand-in**, unruled,
scored by the retired mechanism. *Reading:* one ruled kind — working name **`movement`** (source
vocabulary decides nothing; *transaction* is refused by T2, *bank_line* names the evidence shape, not
the statement) — **subject the party whose statement it is** (the bank; for Bl6, Rob), content the
line, `as_of` per F5. The bank's stances on a *payment* (`cleared`, `bank_returned_item`) remain what
9D-iv ruled and are never minted from a line (Va11 stays). **Rob's.**

**F3 — the knowing relation: the subject party, not the foundation.** The line's strength today is
*institution → knowing* by map. The record's own relation for a stance whose holder is an explicit
participant is `KNOWING_SUBJECT_PARTY` (`acknowledged` / `returned`: *the asserter is the holder*).
For a `movement` claim: the reading path → the artefact's established origin = the subject party →
knowing (weakest-linked with the origin claim, as everywhere); Rob's utterance relaying the bank's
line (Bl5) → not_knowing (K5); Rob's spreadsheet row (Bl6) → subject Rob, origin Rob → knowing *for
Rob's statement of a movement*, which is not `cleared`. `reading_establishes: True`. No foundation
map entry anywhere. *Reading:* `KNOWING_SUBJECT_PARTY`; the alternative — undetermined by design
(9D-v's shape) — would make the bank not knowing for its own ledger, which K6 refused. **Rob's.**

**F4 — the object: a required absence, or the candidates state.** A ruled kind's object is
established in a permitted slot or `()` — the registry has no ruled kind whose object is *by
design* `not_established_with_candidates`. Ab7 ruled that the candidates state's carrier is the
reading-sourced concerns claims, and that the state itself names nothing. Bl3 shows the reader
cannot honestly distinguish *candidates* from *none* at generation. *Reading:* **`'object': ()`** — a
`movement` claim has no object participant; what it concerns is Ab7's claim or nothing, and *about
nothing paid* is the absence of a tie, never a state the reader sets. Pm2's and Pm12's pins on the
object state restate to the required absence. The alternative — admit a candidates-object kind to
the registry — is a substrate change for a state whose carrier already exists elsewhere. **Rob's.**

**F5 — `as_of`: the line's date, or the capture's.** T2 says *the capture's `as_of` as its time*;
every fixture uses the line's own date (3/3). A movement has a date the bank states (posted /
transaction) and the capture has a time. *Reading:* `as_of` **the movement's date as the bank states
it** — it is the claim's date the way a balance's `as_of` is the statement's date; the capture's
time is the artefact's `as_of`, already held on the artefact. T2's phrase corrected, not
contradicted: the artefact carries the capture's time; the claim carries the movement's. **Rob's.**

**F6 — what the reading may mint besides the line.** Two outputs exist in the record: the line
(this pass) and, since 7G-F3, a reading-sourced **domain candidate whose subject the reader named**
(`acknowledged(Harbor, p)` from the statement — Dc3; `balance(O)` — Sb3; `deductible(P)` — Te5).
The second is candidate generation in the matcher's sense (Pa3's analogue at the claim level) and
is *fenced*; this pass does not rule when the matcher may name p. It records only that **the line is
never the domain claim** (Bl2: `cleared(p1)` is a separate proposition, evidenced by the same
reading once p1 is named, or by the bank's own utterance) — the separation Rob's framing requires.
**Stated, not ruled.**

**F7 — the build's corpus class, pre-measured.** `bank_line` appears at eight sites (payment identity
×3, Ab7, Va11, `s94`, two `KNOWING` maps). Under F2–F5 the swap is a rename plus: the map entries
retired; Pm2 / Pm12's object-state pins restated; Va11's *not in `RULED_KINDS`* pin retired (the
exact-absence class); `s94`'s mutation follows the name. The sibling stand-ins (~60 sites) are
**untouched** — F1. No consumer reads `bank_line` by name; 7A / 7C / 7D / 7E read whatever kind the
readings yield. The null model: every bank-line outcome unchanged before any case is added.

---

## 5. Candidate — pending the ruling

> One ruled kind, working name `movement`: **the statement by a party that a movement of money
> occurred on its account** — subject the party whose statement it is (`subject_party_id`), object a
> required absence (`()`), content the line as read (amount, description, identifiers — content,
> never identity), `as_of` the movement's date as stated; `reading_establishes: True`;
> `relational_knowing: True` with `KNOWING_SUBJECT_PARTY` — knowing iff the asserting party (the
> artefact's established origin on the reading path; the utterance's origin otherwise) is the
> subject party. It mints no identity; it is never a role, never a stance on a payment, never a
> knowing source for one; what it concerns is Ab7's claim, and *about nothing* is the absence of a
> tie. `cleared` / `bank_returned_item` untouched; `bank_line` retired for it at its eight sites;
> the three sibling stand-ins untouched and their question named.

**Fixture additions, if ruled:** Bl1 (the kind, the participants, knowing through the origin), Bl2
(the tie Ab7; `cleared` a separate proposition — the line never becomes it), Bl3 (generation-time
object the same for a transfer as for a payment; *about nothing* the absence of a tie), Bl5 (Rob's
relay not_knowing), Bl6 (Rob's spreadsheet row knowing for Rob's statement, nothing about clearing),
Bl10 (Va11 holds), Bl11 (the null model). **Mutations for `s94` / `s123`:** a movement line minting a
payment (exists, renamed) · a movement line accepted as `cleared` (the line becoming the stance) ·
the bank knowing by foundation with the subject party absent · Rob's relay knowing · the object set
to a payment by the reader (the match manufacturing the tie) · the line's `as_of` the capture's.

---

## 6. Ruling sought

> **(1) F1:** the bank line only, the sibling question named. **(2) F2:** one ruled kind, the
> party's statement that a movement occurred; the name. **(3) F3:** `KNOWING_SUBJECT_PARTY`, no
> foundation map. **(4) F4:** the object a required absence. **(5) F5:** `as_of` the movement's
> date as stated. **(6) F6** as stated — the matcher not opened. **(7) F7** as read. Nothing here
> authorises code.

---

## 7. Ruling — Rob, 2026-09-21. F2's candidate ruled; F1–F7 accepted; the matcher boundary explicit; no code

*The correction materially sharpens the pass: `bank_returned_item` is already ruled and is not part
of this question. The only stand-in under examination is `bank_line`.*

**F2 — ruled as the candidate: one ruled kind — the party's statement that a movement occurred,
with the party as subject.** The working name `movement` if that is the record's chosen vocabulary;
*the semantics matter more than the label.*

**F1 — accepted:** the bank line only; the sibling question (*a stance before its subject is tied*)
named, not ruled. **F3 — accepted.** `KNOWING_SUBJECT_PARTY` is the appropriate strength source: the
bank is knowing for its own ledger statement; a foundation-map inference here would recreate the
mechanism 9D retired; K6's alternative (undetermined by design) remains refused. **F4 — accepted.**
The absent object / tie is genuinely absent; the reader does not manufacture an *about nothing paid*
state; the movement's eventual relation to a payment is a separate determination. **F5 — accepted.**
`as_of` is the movement date stated by the bank line — T2's loose *capture's `as_of`* corrected
without changing the underlying temporal fact. **F6 — accepted.** The bank line is not the domain
proposition `cleared(p1)`; it supplies evidence that a movement occurred; a separate proposition
establishes what happened to a particular payment. *The matcher therefore remains fenced and cannot
be smuggled into candidate generation.* **F7 — accepted as scope.** The eight `bank_line` sites are
the corpus; the roughly sixty sibling sites remain untouched.

**The key semantic distinction, recorded.** The bank line has a different status from the other
line shapes despite their representational similarity: **`bank_line` mints evidence about an
occurrence, not a stance about an already-identified domain object.** The movement itself need not
be minted as an identity merely to represent the bank's statement. The line establishes the bank's
proposition about an occurrence; later reasoning may establish whether that occurrence corresponds
to a payment, return, fee, etc. *That later tie cannot be manufactured by the line-kind rule.*

**No code is authorised by this ruling.** The build awaits its separate authorisation.

---

## 8. Built — 2026-09-21

`core/database.py`: **`MOVEMENT = 'movement'`** and one registry entry — `subject ('subject_party_id',)`,
`object ()`, `reading_establishes True`, `relational_knowing True`, `knowing_relation
KNOWING_SUBJECT_PARTY`; not a role; a comment block carrying the ruling (the occurrence / stance
distinction, the object's absence, `as_of` the movement's date, the matcher fenced). **No resolver, no
relation, no consumer, no migration:** the existing designated-subject-party resolver answers, and no
consumer reads the kind (7A / 7C / 7D / 7E read whatever kinds the readings yield).

**The null model, twice.** The registration alone against the unchanged corpus: 9D-iv 18/18,
payment identity 38/38, Ab7 32/32, 9B 26/26, relational knowing 23/23, 9D-i 22/22, 9C 33/33 — zero
change. Then **the corpus swap at the eight `bank_line` sites (F7)** — `bank_line` → `MOVEMENT`; the
object `CANDIDATES` → `NONE` at Pm2 / Pm10 / Ab7 (Pm12 already `NONE`) — the required absence (F4);
the two `KNOWING` map entries retired (F3); Pm2's object-state pin restated to the absence; Va11's
*`bank_line` not in `RULED_KINDS`* pin (the exact-absence class) restated to *the ruled kind refuses a
candidates object too*; `s94`'s mutation follows the name — 18/18, 38/38, 32/32 again: **every
bank-line outcome unchanged** (mints nothing, names nothing, refused under the stances; Ab7's P7
tie and its knowing strength unchanged — now by the relation, not the map). No `bank_line` remains.

**The oracle — the 9D-iv fixture (18 → 26), §7:** **Bl1** the registry as ruled, and line 7 read → a
movement claim, subject the bank, `as_of` 3/3 (the movement's date, not the capture's 3/31), a
candidate in state, **knowing** in strength because the artefact's origin *is* the subject party;
no payment minted; nothing named. **Bl2 (F6)** Rob's tie is Ab7's claim, established by his
utterance; the movement claim byte-identical; `cleared(p)` the bank's separate stance — none added
by the tie, none with the line as subject. **Bl3 (F4 / Pm12)** the transfer to savings the same shape
as the mortgage line; *about nothing paid* the absence of any tie. **Bl5 (K5)** Rob relaying the
bank's line as an utterance → not_knowing, by the relation. **Bl6 (O5)** a row of Rob's own
spreadsheet → knowing for *Rob's* statement of a movement, and nothing about clearing — `cleared`
stays the bank's by `drawn_on`. **Bl10 (Va11 holds)** a movement with a payment object, or a
candidates object, refused; `bank_returned_item` keeps the payment as subject. **Bl11 (the null
model, F6)** across every line no payment minted and the one tie in the record is Rob's utterance —
no reader, match or rule manufactured one.

**Smoke `s123` (23 → 33), five mutations, all caught first run:** the line becomes the stance
(movement admits a payment object) · the bank knowing by foundation (the map restored) · the relay
knowing (K5 reversed) · **the reader manufactures the tie** (a reading-sourced concerns claim inserted
from the line — the matcher smuggled in) · `as_of` the capture's. **`s94` (9/9):** *a bank line mints
a payment* renamed to the kind, still caught.

**F7 corrected — an inventory finding, not a semantic expansion (Rob, 2026-09-21).** The first
full gate returned 1504 / 10: five sections (s101, s104, s109, s110, s98), each its *fixture passes in
full* plus its baseline, nothing else. The cause: the record's fixtures had **already been using the
name `movement`** as a fifth stand-in for the bank-line shape — party subject, `CANDIDATES` object,
bank-line content, the subject already the artefact's origin — at seven sites the opening's grep
never searched (payment-counteracts A8 `REFUND MERCY 300.00`; payment-in-respect-of D2 `CVS PHARMACY
24.99`; expense identity ×2 `MERCY HOSPITAL 412.00 | bank category`, `CVS PHARMACY 38.20`; aboutness
P7 and level-consistency L7 `HARBOR MTG -1,412.00`; plus a chain-strength map entry and `s98`'s
mutation keyed on the name). The ruled kind's required absence refused their candidates object.
**Ruled:** *the corpus is the bank-line SHAPE, not the four names*; the seven sites are in; the kind
name stands (a different name would solve an inventory error by changing the ontology); no sibling
stand-in is pulled in by resemblance; the map entry and the mutation are auxiliary occurrences
updated with the transition, not new semantic cases. **Done, after the failure set was complete:**
the object → `NONE` at the seven sites (two `line()` helpers gained an `object_state` parameter
defaulting to the sibling stand-ins' shape; the sibling calls unchanged); the map entry retired; the
mutation keyed on the constant; one pin restated (expense identity's *still names nothing*: the
absence). Fixture counts unchanged — 25 / 45 / 34 / 27 / 32 / 37 — **every outcome preserved**, the
strength identical because the subject was already the origin; s98 9/9, s101 9/9, s104 23/23,
s110 27/27 standalone. The corpus: **fifteen sites, one shape.**

**Untouched, by name:** `cleared` / `bank_returned_item` (9D-iv); the three sibling line stand-ins
(`statement_figure`, `eob_amount`, `sbc_line_figure`, ~60 sites) — *a stance before its subject is
tied*, the named sibling question; the matcher / the importer contract (fenced); K2's balance half;
D′.11. Gate 1580 → 1504 / 10 (the inventory error) → 1590, 0 failed.

---

## 9. Accepted and closed — Rob, 2026-09-21

Accepted as built and ruled: `51094d4`, 1590 / 0 on the second full gate. *The evidence is complete
and internally consistent:* the fifteen bank-line-shape sites are accounted for, with no remaining
`bank_line` or unruled `'movement'` test / section strings; the seven substitutions stayed within the
existing authorisation — no new semantic case or pass was introduced; **the first-gate failure set
established the cause before the swap**, and §8 records that discovery / handling order; standalone
coverage remains green, including `s123` 33/33 and `s94` 9/9; the tree is clean; the explicitly
protected neighbouring semantics remain untouched — the sibling stand-ins, the matcher,
`cleared`, `bank_returned_item`, K2's balance half and D′.11; the required workflow was followed:
note → queue (item 14 BUILT) → commit → push. *So this is not merely a green gate after a convenient
substitution; the inventory correction is now evidenced, bounded, recorded, and independently
green.* **The bank line's own kind: built, accepted, closed.**
