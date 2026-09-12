# Narrator sensitivity ↔ voice permission — the test, run on the two CVS rows

> Status: **Doctrine test, 2026-09-12. No decision. No field on `NarratorFacts`, no gate rule,
> no change to `callAI()`.** Joint constraint 3 of three, opened on one case: **the two CVS
> pharmacy transactions the importer filed under *Other*** (`SENSITIVITY_TRACE_CASES.md`) —
> both marked health by merchant and MCC, both `manufactured`, folded into
> `category_delta:Other = 180.0`, `corroborated`, and handed to the narrator as a float with a
> category name that is not a health word.
>
> **Rob's question:**
>
> > **What information is allowed to control narrator voice, and where is that permission
> > enforced?**
>
> **Structure, his — four cells, representation tested separately from permission:**
>
> ```text
>                  representation          permission
> classifier       what does it know?      may it affect voice?
> narrator         what does it infer?     may that inference affect voice?
> ```
>
> **§11's two referents kept together as one issue:** the classifier's `manufactured` flag and
> the narrator's own inference from strings. The question is whether *either* is authorised to
> change what the narrator is permitted to say.
>
> **Fences.** *Sensitive* ⇒ *restricted voice* is not assumed; sensitivity can be a fact and
> permission a policy. The initial fence from constraint 3's opening: **a narrator must not
> become the enforcement boundary for a voice rule that can be determined upstream.** And the
> result the opening preserves as possible:
>
> ```text
> sensitivity fact  → carried downstream
> voice permission  → decided elsewhere
> ```
>
> rather than *sensitivity fact → narrator restriction*, because otherwise the narrator becomes
> another policy engine.

---

## 0. The pipeline as built — what "voice" and "enforced" mean today

Measured, not assumed, because the permission column has to be answered against enforcement
points that exist.

```text
DerivedFact ──_permitted_value(·,'narrator')──► NarratorFacts ──(assembled into text)──► findings
                    refuses on STRENGTH only         metric · value ·                  = the user
                                                     includes_records · resolution      message
                                                     NO sensitivity
findings ──► model ──► text ──► _voiceGateCheck(text, findings) ──► pass / retry ×2 / refuse
                                   R1–R9 wordlists, and
                                   R8: every figure in text must appear in findings
                                   reads TEXT ONLY — no sensitivity input
                        ──► on any rejection: _logVoiceMiss(surface, model, rules, text)  (F3)
```

Three facts this fixes for the cells:

1. **The findings text is both what the model knows and what it is permitted to say.** R8 is
   *the cardinal rule* (its own comment): a figure is voiceable iff it was given. There is no
   rule by which a given figure is *not* voiceable. For numbers, **representation is
   permission** — by construction, at the choke point, today.
2. **Enforcement is downstream of the model and outside it** — a deterministic check on output
   in the browser, plus a strength refusal upstream. The model is not the enforcer of anything;
   the system prompt (`_GW_VOICE`) *asks*, and the gate *checks*. Rob's fence is already the
   built shape.
3. **Nothing reads `Sensitivity` anywhere on this path.** Not the boundary, not the assembler,
   not the gate. The classifier's flag is rendered on the transaction row (the Passive tier —
   `CLASSIFICATION_QUESTION.md` resolution 1b — which is what lets it persist at all) and goes
   nowhere else.

---

## 1. The four cells

### Classifier — representation: what does it know?

`Classification(domain=health, manufactured=True)` on each CVS row: merchant and MCC say
pharmacy; nobody said health. Its own docstring ranks `manufactured` as *the most sensitive
thing the system holds* — a suspicion about a person that nobody asserted. Folded upward:
`DerivedFact(category_delta:Other, 180.0, strength=corroborated, domain=health,
manufactured=True)`. And the suspicion is **already user-visible**, on the row, as a Passive
marker — so it is surfaced, which is why it may persist.

What it knows, then: *a health inference the household never made, at the highest sensitivity
rank, corroborated by two rows, inside a category the household labelled Other.* Every word of
that is true and every word of it is lost at `NarratorFacts`.

### Classifier — permission: may the flag affect voice?

Run the three places it could:

- **At the boundary, as a refusal.** `_permitted_value` could refuse a manufactured health
  fact to the narrator the way it refuses a weak one — Q1's shape, with `reason` carried. Then
  the narrator never receives `category_delta:Other` at all. **Cost, and it is the case's own
  cost:** the figure *Other spending is up $180* is accurate and non-disclosive — limb 3
  (available inference) fails on it; nobody can learn health from it. Withholding it *because
  of* a suspicion the household never made is the classifier's suspicion **steering** what the
  household sees. A refusal that travels with its reason (Q1) is not silent — the household can
  see *refused: manufactured health suspicion* — and since the marker is already on the row,
  that discloses nothing new. A refusal that does **not** travel — the figure just absent — is
  the hidden belief that steers, the harm the self-changing-settings decision named. So: **the
  flag may affect voice by visible refusal; it may never affect voice by omission.**
- **In the findings text, as a fact given to the model.** `domain: health (manufactured)`
  beside the figure. Under fact 1 above this is not a restriction — **it is a grant.** The model
  now holds *health* as a given, R8 has no objection (no figure), R3 catches *suggests* but not
  *your health spending rose*, and the narrator says the word. Carrying the flag *into the
  model's text* authorises the model to voice the suspicion as a fact, by the gate's own logic.
  **This is the collapse the opening was written to prevent, and it is one line of assembler
  code away.**
- **Beside the findings, as metadata the gate reads.** The gate could hold a rule of R8's
  shape for claims — *every health claim in the output must be an asserted fact in the
  findings* — and refuse an output that says *health* when the only health fact given was
  manufactured. The model never sees the flag; the gate does. **The flag affects voice by
  making an output refusable, not by making a fact sayable.**

So the case answers the cell with an asymmetry: **the classifier's flag may control voice
only through a refusal or a check, both of which are visible and outside the model; the one
path by which it would "affect voice" invisibly — being handed to the model as text — is the
one that turns representation into permission.**

### Narrator — representation: what does it infer?

Only what the strings it is given invite. In the two-CVS case: **nothing.** The findings say
`category_delta:Other 180.0`; *Other* is not a health word; the model cannot infer health and
does not. The same case set's two other rows are the referent-2 illustration and are in scope
by Rob's instruction:

- `category_delta:Prescriptions` — the model infers health from the string. **And the record
  agrees**: *Prescriptions* is a user-set category, which the classifier reads as content
  evidence — user-asserted health. The inference happens to match an asserted fact.
- memo *wheelchair ramp lumber* — the model would infer health from the string. **The record
  does not agree**: both axes `not_evaluated`; the purchase may be for a neighbour or a stage
  set. The inference manufactures a suspicion the record refused to.

What the narrator infers is therefore **a function of the findings string and nothing else**,
and — the point — **it cannot tell which of the two cases it is in.** It does not hold the
record (`includes_records = False`, asserted). *Prescriptions* and *wheelchair* look the same
from inside the model: a word that means health.

### Narrator — permission: may its inference affect voice?

Today: **yes, unblocked**, wherever a string invites it. R3 catches inference *verbs*; R8
catches invented *figures*; nothing catches an invented *claim*. *Your pharmacy spending rose*
passes every rule if no number is wrong and no listed word appears. So the narrator's
inference from strings is, today, an unenforced source of voiced claims — and the
`wheelchair` row shows it can voice a suspicion the record deliberately does not hold.

May it? The cell is answered by the representation cell above: since the narrator cannot
distinguish an inference that matches an asserted fact from one that manufactures a suspicion,
**its inference can never be authorised as the source of a voiced claim.** Not because inference
is forbidden in general, but because the only party that can tell *Prescriptions* from
*wheelchair* is the record, and the record is upstream. The authorisation, if any, has to be
*the claim is asserted in the findings* — R8's shape, for claims — which is exactly a rule that
can be determined upstream of the model and checked downstream of it, and so by Rob's fence
must not be left to the model.

---

## 2. Result

|  | representation | permission |
|---|---|---|
| **classifier** | health · manufactured · corroborated; folded into *Other*; visible on the row; **lost at `NarratorFacts`** | may control voice **only by visible refusal (boundary) or by check (gate)** — never by silent omission, and never by being handed to the model as text, which under R8's logic is a grant |
| **narrator** | infers only from strings; in this case nothing; **cannot tell an asserted health word from a manufactured one** | its inference is **never an authorised source** of a voiced claim; today nothing enforces that beyond wordlists |

**Rob's question, answered from the case.**

> **What information is allowed to control narrator voice:** what is *asserted in the findings*
> — the principle R8 already enforces for figures, which the case shows is the same principle
> for claims. A manufactured health fact is not asserted; a narrator's inference from a string
> is not in the findings at all. Both referents fall under one rule, which is why they were
> right to keep together: **the question for either is *is this claim asserted in the record?*,
> and neither source can answer it for itself.**

> **Where that permission is enforced:** upstream of the model (the boundary, with a visible
> refusal) and downstream of it (the gate, with a check against the findings) — **never inside
> it.** Rob's fence is the pipeline's existing shape; the case shows the one way to violate it
> is not by adding a rule to the model but by adding a fact to its text.

**The result the opening hoped to preserve is achievable, with one condition.**

```text
sensitivity fact  → carried downstream        yes — to the BOUNDARY and the GATE
voice permission  → decided elsewhere         yes — by refusal and by check
```

The condition: **`NarratorFacts.Sensitivity`, if it exists, has two possible readers with
opposite consequences — the gate (a check) and the findings assembler (a grant) — and 9 = yes
says nothing about which.** *Carried downstream* and *the model reads it* are different
decisions. The one that turns representation into permission is the assembler's, not the
field's. So the §9 decision is safe under either answer **provided the field is never
serialised into the model's text** — and that provision is the whole of where representation
and permission would otherwise meet.

**What this does to the map's arrows.** `9 ──X──► 11 (policy)` holds — carrying the flag
grants nothing *if the gate reads it*. But the X has a stated exception the map did not have:
carrying the flag **into the findings text** is a grant, by construction. The locus constraint
sharpens: it is not *boundary vs narrator*; it is *boundary or gate vs findings text*, and the
model is never a locus at all.

---

## 3. What the test does not prove

1. **11's policy.** Whether a manufactured suspicion may be voiced *at all* — as a refusal's
   reason, as a hedged aggregate, never. The case shows which paths are visible and which are
   grants; it does not choose. `CLASSIFICATION_QUESTION.md` already settled the *proactive*
   path (Passive on the row; the only proactive form is an aggregated seasonal review offer,
   drawing the brake budget); the *narration* path is what remains, and it is Rob's.
2. **That the gate should gain a claim-provenance rule.** The case establishes the *shape* of
   the only enforceable authorisation — asserted-in-findings — not that R8's mechanism is the
   place for it, nor what "asserted" means for a claim as opposed to a figure (a user-set
   category name is asserted; is an importer's category?). That reaches the classification
   axes and is fenced.
3. **Anything about F3.** The miss-log stores rejected text verbatim; whether it must carry
   sensitivity is constraint-3-adjacent and was closed as a foreclosure in the case pass. Not
   reopened.
4. **That silent omission never happens today.** It cannot — nothing reads the flag. The harm
   is reachable only once a boundary refusal on sensitivity exists *without* Q1's reason
   travelling. Recorded as the wiring condition for that refusal, not as a present defect.

---

## 4. Decision remaining — Rob's

11's policy for the narration path, now with the enforcement geometry fixed by the case:
visible refusal upstream, check downstream, never text to the model. And 9, which the case
neither requires nor forbids — it requires only that if the field exists, the findings
assembler is not among its readers.

---

## 5. Ruling — Rob, 2026-09-12. Constraint 3 closed.

**11, for the narration path, ruled conservatively — and the reason matters more than the
rule, because the rule is not "health-sensitive things cannot be narrated":**

> **A claim may be voiced only when the claim is asserted by the findings record. A
> manufactured classification is not an asserted claim, and narrator inference from strings is
> never an authorisation to make one.**

Applied to the case (referents as the case records them):

| row | what the record holds | voiceable as a health claim? |
|---|---|---|
| `category_delta:Prescriptions` | user-set category → **asserted** content evidence | potentially — subject to the existing gates |
| the two CVS rows under *Other* | classifier-marked health, **manufactured** | **no** — manufactured provenance cannot satisfy the authorisation requirement |
| memo *wheelchair ramp lumber* | **nothing** — both axes `not_evaluated`; only the narrator would infer | **no** — an inference from a string is not in the record and authorises nothing |

**This is not a general prohibition on mentioning the transaction.** It is a prohibition on
the narrator *upgrading* an inference or a manufactured fact into an asserted health claim.

**Why this and not "never voice manufactured":** provenance is doing the work. The rule is not
`manufactured = forbidden` as a universal semantic law; it is **manufactured provenance cannot
satisfy the authorisation requirement for an asserted claim.** That leaves room for a future
policy to decide whether a manufactured fact may participate in some *other* form of narration
— an explicitly non-claiming statement — without silently granting it the status of a finding.

**Enforcement geometry, preserved exactly as the test found it:**

```text
classifier
   │
   ├── sensitivity / provenance ──► boundary
   │                                └── visible refusal, if policy requires
   │
   └──────────────────────────────► findings
                                    │
                                    ▼
                                 callAI()
                                    │
                                    ▼
                                  model
                                    │
                                    ▼
                               voice gate
                                    │
                                    └── verifies output against findings
```

Nothing about sensitivity is serialised into the model as an instruction or a fact whose
presence authorises speech.

**The `callAI()` finding, weighted as Rob reads it — more significant than it first looks:**
the findings assembler is *currently the implicit authorisation boundary.* Anything it puts
into the model's text has, under R8, effectively been admitted for narration. So if
`NarratorFacts.Sensitivity` ever exists, the dangerous implementation is not *the model sees a
flag*; it is

```text
Sensitivity → findings text → model
```

because that silently converts representation into authorisation.

**§9 left unchanged.** The constraint is not *sensitivity must not travel downstream*; it is:

> **Sensitivity may travel to components that enforce policy, but may not be converted into
> model-visible content merely because it exists.**

So the sharper arrow stands — `9 ──X──► 11 (policy)` — with the caveat that **findings text is
an authorisation-bearing boundary, not a neutral transport layer.**

**Fenced, deliberately:**

- the exact 11 policy beyond this narration rule;
- whether the check becomes R8, a sibling gate, or another validation — the doctrine says
  *assertion status is required for voice authorisation*; where the check lives is
  implementation architecture;
- what "asserted" means for an imported classification such as `Prescriptions` — stays in
  classification/evidence semantics, **not to be solved by making the narrator smarter**;
- F3.

**Constraint 3, recorded:**

```text
3  narrator sensitivity ↔ voice permission

   voice authorisation   → asserted findings
   manufactured facts    → cannot authorise a voiced claim
   narrator inference    → never authorisation

   enforcement           → upstream boundary or downstream gate
   model                 → never an enforcement locus

   9 → 11 policy: no — sensitivity may travel, provided it never becomes
   model-visible authorisation merely by being serialised into findings
```

**The pattern across all three joint constraints (Rob's):** *don't make one semantic dimension
impersonate another merely because the data happens to travel through the same object.*
§7.7: entitlement is not classification, though one event touches both. Time: an observed
claim is not a resolved period, though one operation closes both. Voice: a carried fact is not
an authorised claim, though one text carries both.
