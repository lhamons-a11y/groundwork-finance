# The plan — does it have a Groundwork identity, and what assertion could mint it?

> Status: **Queue item 4c — RULED (§7, PL2); BUILT (`dcac27e`); ACCEPTED and CLOSED (§8).** 4b closed at
> `ea8f9d4` with the insurer's claim dissolved: no identity, nothing can mint one, the household's
> "claim" is the expense and the insurer's is its record. Rob's warning on opening 4c, verbatim:
> *likely the more dangerous of the two, because "plan," "coverage," "benefit," "authorization,"
> and "responsibility" are extremely easy to collapse into one financial object … approach it with
> the same identity-first discipline rather than assuming a plan is an identity merely because
> insurers have plan IDs.* Built to §5 and nothing beyond it.

**Stopping question:** *does a plan have a Groundwork identity, and if so, what assertion is
capable of minting it?*

**Adversarial question:** *can the insurer's product — its plan name, plan ID, group number,
member ID — mint the plan identity?* Derived from identity authority, not from "the insurer
issues the plan."

**The second adversarial question, which 4b did not have to face:** *if the insurer cannot mint
it, is there anything left for the household to individuate that is not already a party, a role,
an obligation, or a claim?* 4b answered "no" for the insurer's claim, because the expense was
already there to be the referent. 4c has no such stand-in, so the answer must be earned by cases.

---

## 1. What is already ruled, and therefore constrains the answer

| Ruling | What it fixes |
|---|---|
| **Identity authority** | two minting acts only: Groundwork's encounter of an *artefact*; a *Person's* individuating assertion. Institutions mint nothing; their identifiers are correspondence evidence; description never mints; encounter mints only the artefact |
| **4b** | the insurer's records, identifiers and dated stances are content, evidence and propositions; *what the household individuates* is the test for a referent; an institution's product / bookkeeping vocabulary decides nothing |
| **Expense X3** | an identity the household individuates, minted by a Person's assertion, **anchor impoverished** — everything descriptive is a claim; mis-individuation is correspondence (X1), never unminting; granularity is the household's (Ex7) |
| **Obligation ruling** | *what one party owes another, as the household individuates it*; a standing identity, not an event; discharge and balance are claims / consumers |
| **Party ruling** | parties are agents (persons, institutions); roles are **dated relations over parties** — item 5, unruled; the household party is anchored to a Person, the institution party is the minted identity |
| **P-ack / 4b §4 pinned** | an institution's dated stance about an established identity is a proposition shape; recurrence of shape establishes no family, resolver or consumer |
| **APPLICABILITY_CASES** (1.x) | *a plan whose terms were never entered* ≠ *a plan with no deductible*; *no plan covered this date* ≠ *nobody has told us which plan* — absence of a claim is not a zero |
| **Legacy map (SHIPPED_VS_TARGET)** | 1.x `HealthPlan` + `TermVersion` treats *the plan* as a subject type with household-asserted, dated terms; `HealthcareExpense` has *deliberately no `plan_id`* — coverage derived from the date of service. **Precedent, not a ruling**: legacy vocabulary never decides |
| **Source-category constraint** | a source's category / vocabulary never mints or establishes the nature of what it names |

---

## 2. The words that collapse — separated before the cases

The trap is a single "plan" object carrying coverage, benefits, authorizations, responsibility
and premiums. Each word names something already placed, or placeable, without the others:

| Word | What it turns out to name | Where it lives |
|---|---|---|
| **plan** (this record's question) | the household's *arrangement* — its being covered under an insurer's product | **open — §3–§4** |
| **product** | the insurer's catalogue entry — *Lakeview Health Choice POS II* — its name, plan ID, group number | **content**; correspondence evidence; never identity (4b, party ruling) |
| **coverage** ①  | *the arrangement* | = plan |
| **coverage** ② | *who is under it, when* — Kim, from 2026-01-01 | a **dated relation** person ↔ plan — **item 5's shape**, unruled |
| **coverage** ③ | *whether a service is covered* | the insurer's **dated stance** (a term claim about the plan, or an adjudication about X — 4b) |
| **benefit** ① | the terms — deductible, copay, out-of-pocket maximum, coinsurance | **propositions about the plan**, dated / with effective period claims; asserted by the household or read from the SBC |
| **benefit** ② | what the insurer paid on X | **adjudication** — 4b, closed |
| **authorization** | the insurer's dated stance that a *prospective* service will be covered | a **proposition** — no expense exists yet; tied to X later by `proposition_concerns` if a party ties it |
| **responsibility** | what the household owes on X | **proposition about X** — 4b, closed; the obligation, if any, is O |
| **premium** | what the household owes the insurer (or the employer via payroll) for the arrangement | an **Obligation** and **Payments** — already identities; *"for plan P"* is a relation claim, **item 6** |
| **accumulator** | *$1,800 of $3,000 met as of 3/1* | the insurer's **dated stance**; also a **consumer derivation** over adjudications — fenced |
| **plan year** | the insurer's period vocabulary | **content**; what the household individuates across a renewal is the household's (§3 Pl4) |

None of these needs the others on a row. Whatever the plan is, it is not the row they collapse onto.

---

## 3. The cases

| # | Case | Under PL1 (no identity — party + role + claims) | Under PL2 (household-minted arrangement identity) |
|---|---|---|---|
| **Pl1** | An insurance card arrives: *Lakeview Health · Group 12345 · Member W2288 · Kim*. | artefact; identifiers content | same — artefact; identifiers content and correspondence evidence for later documents; nothing minted by encounter but the card |
| **Pl2** | The SBC says deductible $3,000 individual / $6,000 family; 80% after deductible. | P-subject claims; **subject?** — the insurer party? Lakeview Health has many products; Kim's coverage role? the *family* deductible is not about Kim | P-subject claims from the reading; P-world *P's deductible is $3,000* when a party asserts it; **P is the subject** |
| **Pl3** | The household has **medical and dental both with Lakeview Health**, overlapping periods. | two coverage roles person ↔ Lakeview Health, distinguished **only by their terms** — identity by content, which the ontology forbids | two plans, **individuated by the household's assertion**; the insurer's two product names are content |
| **Pl4** | January 1: same product name, deductible rises to $3,500. | a new term proposition; whether the "plan" is the same is not representable — there is no plan | the household decides: **same P with a new dated term claim**, or a new P. The insurer's *plan year* decides nothing; mis-individuation is `plan_corresponds` (X1 pattern) |
| **Pl5** | Open enrollment: the household switches from Lakeview Health to Cigna. | Lakeview Health role ends (a dated claim), Cigna role begins | new P₂; *P₁'s coverage ended 12/31* is a dated claim about P₁; P₁ persists as an identity — **identity ≠ currency** |
| **Pl6** | Kim is on the employer plan; Rob is on a marketplace plan. | two roles over two persons and two insurers | two plans; **membership** — Kim under P₁ from d — is a dated relation person ↔ plan: **item 5's shape with a non-party endpoint** — *not a field on P*, unruled |
| **Pl7** | The premium: $412 monthly via payroll. | Obligation / Payment to the employer or insurer; nothing ties it to a plan | same identities; *"for P"* is a relation claim obligation ↔ plan — **item 6**; the premium is never the plan |
| **Pl8** | The employer pays 70% of the premium. | a claim about the employer party's contribution | same; the employer is a party; the household's obligation is its share; the employer's contribution is a claim, not a household obligation |
| **Pl9** | *"Which plan covered the ER visit?"* | derived from the role in effect on X's date claim | either a **relation claim X ↔ P** (item 6) or a **consumer derivation** from membership-period claims and X's date claim — the 1.x row's derivation is a consumer; **never a `plan_id` on X** |
| **Pl10** | The portal: *deductible met $1,800 of $3,000 as of 3/1*. | insurer's stance — subject the role? | the insurer's **dated stance about P** (or about Kim under P); a consumer may derive the same figure from adjudications; disagreement is a **derived dispute**, never a stored status |
| **Pl11** | Prior authorization approved for an MRI, 2/10. | insurer's stance, subject unclear — no X exists | the insurer's dated stance **about P** with the service as content — **no expense exists** (nothing incurred); when the MRI happens and the household mints X, a party may tie them by `proposition_concerns(auth, X)`. An authorization is never an expense and never a plan |
| **Pl12** | Lakeview Health terminates coverage **retroactively** to 6/30, notified 8/15; adjudications reversed. | dated claims | the insurer's dated stance *covered until 6/30, as of 8/15*; earlier stances stand as history (Ic2); the household may dispute; **P remains minted — identity ≠ truth** |
| **Pl13** | COBRA: same product, the household now pays the whole premium. | a new role? a continued one? — undecidable without a referent | the household individuates: same P (terms unchanged, the obligation changes) or new P; *continuation* is the insurer's word and decides nothing |
| **Pl14** | Medicare Part B plus a supplement. | two roles, two insurers | two plans, two insurers; coordination is their stances on X (Ic4) |
| **Pl15** | The household records *"we have a plan"* before any document arrives — no terms known. | **nothing to record** — no role can be distinguished, no term to hold | **P minted with no claims** — the anchor carries nothing; *terms never entered* is the **absence of term claims**, not `deductible = 0` (APPLICABILITY C1/C2 finally representable) |
| **Pl16** | The importer reads a second EOB with the same Group 12345. | correspondence between readings | Group 12345 is **evidence for a correspondence candidate** between the EOB propositions and, if a party says so, for `artefact_concerns(EOB, P)`; the number never establishes anything |

---

## 4. Testing the readings

### PL1 — no identity: the plan dissolves into the insurer party, a dated coverage role, term propositions and identifiers

The strongest form is not a deferral: it says *the plan is a relation*, and the ontology already
has roles as dated relations over parties. It fails on three cases:

- **Pl3** — two arrangements, one insurer, one household, overlapping periods: the two roles can
  be told apart **only by their content**, which makes content identity. The ontology forbids
  exactly this (identifiers, categories, vocabulary are never identity).
- **Pl2 / Pl10** — the *family* deductible and the accumulator are about something that is neither
  Kim (a person) nor Lakeview Health (the insurer, which has many products): **the propositions have no
  subject** under PL1.
- **Pl15** — a plan with no terms yet has **nothing to be a role of**; PL1 cannot record that the
  household has an arrangement until it has content — the APPLICABILITY defect reproduced at the
  ontology level.

And the relation PL1 leans on is **not a role over parties**: one endpoint of "Kim is covered
under P" is P, which under PL1 does not exist. So PL1 does not park 4c on item 5; it makes item 5
unable to express membership at all.

### PL3 — the plan is an obligation (or a pair of them: the insurer's duty to cover, the household's duty to pay)

Rejected. The obligation ruling individuates *what one party owes another*; the premium is an
obligation and already an identity (Pl7); the insurer's duty to cover is conditional and standing
— nothing is owed until an adjudication says so, and then it is the insurer's stance on X (4b).
Fusing the two obligations into a "contract" object is precisely the single financial object Rob
warned against.

### PL4 — the plan is a party (an institution sub-unit), or is minted by the insurer's product ID

Rejected by identity authority. A plan cannot utter; it is not an agent; parties are minted by a
Person's individuating assertion (institutions) or anchored to a Person. Letting the insurer's
product catalogue mint would let an institution's assertion mint — the exception 4b refused.

### PL2 — a household-minted arrangement identity

Every case has a representation, and the boundary holds at each:

- **the minting act establishes only the identity** — insurer, product name, plan / group /
  member identifiers, terms, effective period, members, premium, whether it covered any expense
  are **claims** (Pl2, Pl4, Pl5, Pl12);
- **the referent is the household's arrangement, not the insurer's product** — two households
  on *Lakeview Health Choice POS II* have two plans; the product name is content (Pl1, Pl16). This is 4b's
  sentence again: *what the household individuates is its arrangement; what the insurer
  individuates is its product*;
- **granularity is the household's** — one P across a renewal or two (Pl4, Pl13); wrong
  individuation is `plan_corresponds`, symmetric, party-established, never merging;
- **nothing collapses onto the anchor** — membership is a dated relation with a non-party
  endpoint (item 5, unruled); premium and "which plan covered X" are relation claims (item 6) or
  consumers; authorization and accumulator are dated stances; responsibility is 4b;
- **identity ≠ truth, identity ≠ currency** — a terminated, disputed or never-effective plan
  stays minted (Pl5, Pl12);
- **absence of claims is representable** (Pl15) — the substrate distinguishes *no terms entered*
  from *deductible 0* by having no term proposition, which the 1.x engine could not.

### The parallel and the asymmetry with 4b

```text
insurer's claim   ── record of ──►  X   (household-individuated; ALREADY minted)      → dissolves
insurer's product ── offered to ──►  P   (household-individuated arrangement; NOT yet a thing) → survives
```

4b dissolved because the world referent was already an identity. 4c does not, because the
household's arrangement has no other identity to stand in for it — and the cases (Pl3, Pl15,
the family-level subjects) show the household refers to it independently of its content.

---

## 5. What a build would be — if ruled, and not before

Named so the boundary is visible, not so it is started:

- `Plan(plans: id · minted_by_id → utterances NOT NULL · created_at)` — the expense anchor's
  shape exactly; `_minting_violations` (Person origin); no name, no insurer, no terms, no period,
  no member, no product ID, no status;
- `plan_corresponds` — symmetric, `reading_establishes False`, `relational_knowing False`;
- `subject_plan_id` / `object_plan_id` slots; `proposition_concerns` and `artefact_concerns`
  object slot gains `object_plan_id`; `_CORRESPONDENCE_OF['Plan']`;
- fixture: minting, Person-origin refusal, term claim about P with the SBC as artefact origin,
  Pl3 two plans one insurer, Pl4 same-P-new-term vs new-P, Pl15 plan with no claims, `plan_id`
  absent from expenses, membership / plan↔expense / plan↔obligation kinds **absent** from the
  registry, correspondence never merges;
- migration: a table, two columns, two indexes; no data step.

**Not in it, whatever the ruling:** membership (item 5) · plan ↔ expense, plan ↔ obligation,
plan ↔ payment (item 6) · accumulators, *which plan covered X*, *deductible met*, coverage
status (item 7) · the term / authorization kind catalogue (the domain's) · the resolver over the
insurer's successive stances · legacy `HealthPlan` / `TermVersion` decomposition.

---

## 6. Ruling candidate — for Rob

> **A plan is a Groundwork identity for a coverage arrangement that the household individuates
> — its being covered under an insurer's product, not the insurer's product — minted by a
> Person's individuating assertion. The insurer's assertion mints nothing: its product name and
> plan, group and member identifiers are content and correspondence evidence, and the card, SBC
> and portal are artefacts whose encounter mints only the artefact. The minting act establishes
> only the identity; the insurer, the product, the terms, the effective period, who is covered
> and when, the premium, and whether it covered any expense remain claims. Coverage of a person
> under a plan is a dated relation with the plan as an endpoint (item 5); the premium is an
> obligation and payments, tied to the plan only by a relation claim (item 6); which plan
> covered an expense is a relation claim or a consumer derivation, never a field on the expense;
> a term is a proposition about the plan; an authorization is the insurer's dated stance about
> a prospective service, tied to an expense only when one exists and a party ties them; an
> accumulator is the insurer's dated stance or a consumer's derivation; responsibility is a
> proposition about the expense. A plan the household has mis-individuated is corrected by
> correspondence, never by unminting; a plan whose terms are unknown has no term claims, not
> zero terms; a terminated, disputed or superseded plan remains minted. Nothing collapses onto
> the anchor.**

**If ruled: the build is the anchor, its correspondence kind and its slots, as §5 — and the
absences.** **Outside it:** items 5, 6, 7 · the catalogues · the resolver · legacy.

*The line: the insurer sells a product; the household has a plan. Groundwork holds the plan the
household individuates, and everything the insurer says about it as what the insurer said.*

---

## 7. Ruling — Rob, 2026-09-14: PL2 as written / build authorised

*This pass earned the distinction rather than assuming it: Pl3, Pl2/Pl10 and Pl15 are enough to
kill PL1 structurally, not merely because PL2 is more convenient.*

> **A plan is a Groundwork identity for a coverage arrangement that the household individuates —
> its being covered under an insurer's product, not the insurer's product — minted by a Person's
> individuating assertion.**

The rest of the candidate is consequence / boundary material, confirmed: insurer product and
identifiers remain content / evidence, not identity · terms, period, insurer, members, premium
remain claims · membership is not smuggled onto the anchor · authorization is not confused with
an incurred expense · premium remains an Obligation / Payment · responsibility remains about the
Expense · coverage of X remains a relation / consumer question · absent terms mean no term claim,
not zero · termination / dispute does not destroy the identity · correspondence corrects mistaken
individuation without merging plans.

**The decisive point — Pl15 is the strongest case in the record.** *"We have a plan"* with no
terms, document, identifier or other descriptive information still gives the household something
it can individuate. That demonstrates the identity is not secretly manufactured out of the plan's
content: the arrangement can exist as an identity before Groundwork knows anything substantive
about it — **identity first → claims afterward** — and the APPLICABILITY distinction becomes
clean: *unknown* is represented by absent claims, never fabricated zeros or inferred nonexistence.

**Two boundaries preserved tightly (Rob):**

1. **"Coverage arrangement" acquires no ontology by implication.** It is the referent of `Plan`;
   it does not establish that there is already a ruled `coverage` relation, contract, enrollment
   object, benefit object, or legal agreement.
2. **"The household decides: same P with a new dated term claim, or a new P"** is an
   *individuation choice*, not a semantic licence for arbitrary duplicate plans. If two assertions
   purport to individuate the same arrangement differently, correspondence is the mechanism for
   saying so later. **Nothing about `created_at`, product ID, plan year, or changing terms decides
   identity.**

**Build authorised — exactly §5:** (1) `Plan` anchor with only `id`, `minted_by_id`,
`created_at` · (2) Person-origin minting guard · (3) `plan_corresponds` · (4) plan proposition /
concern slots · (5) plan in the correspondence machinery · (6) the fixture and absence /
regression cases specified · (7) additive migration only · (8) no data migration. **Fences
preserved:** no item 5 membership · no item 6 plan ↔ payment / obligation / expense relations ·
no item 7 coverage / accumulator / status consumers · no term catalogue · no resolver · no legacy
decomposition. 4b §4 retained: recurrence of the P-ack shape authorises no shared relation kind
or generic resolver.

**Disposition: 4c — PLAN IDENTITY: RULED / BUILD AUTHORISED.** The resulting symmetry:

```text
Expense   household individuates the incurrence
Plan      household individuates the coverage arrangement
Insurer   supplies products and assertions about both
```

*Neither bank vocabulary nor insurer vocabulary gets to mint the household's referents.* Build
the slice, then stop again at the exact §5 boundary.

---

## 8. Slice accepted and closed — Rob, 2026-09-14. `dcac27e`, 967 green, clean tree.

*No further pass on the plan slice: another test pass would mostly re-litigate settled
boundaries.*

- **The anchor is correctly impoverished** — `Plan(id, minted_by_id, created_at)` is exactly PL2's
  result; the strongest evidence is Pl15: the identity exists before the system knows terms,
  insurer, members, dates or economics. That prevents "plan" becoming a disguised
  insurance-record table.
- **Identity authority is cleanly separated from informational authority** — the insurer can say
  *you are enrolled in Lakeview Health Choice POS II, Group 12345* without thereby creating a `Plan`; its
  statement produces propositions and evidence, never the household referent.
- **Pl3 and Pl4 do important work** — two Lakeview Health arrangements can be two plans despite identical
  visible terms; a renewal can be the same plan with new dated claims; and the test refuses to let
  `created_at`, product ID, group number, plan year or changing terms decide it. *Identity before
  description, in executable form.*
- **Correspondence remains correspondence** — `P ↔ P_new`: both identities survive; the later
  assertion establishes correspondence; neither row is canonicalised; neither minting pointer
  changes; `referent()` gives the connected component. The same immutability doctrine as the
  other identity types, not a special exception for plans.
- **The slice fence held** — no membership, enrollment, plan ↔ expense / obligation / payment,
  coverage determination, accumulator state, current-plan resolution, term catalogue,
  authorization identity or legacy decomposition; the fixture asserts several of the absences.
  The first escaped mutation was met by strengthening the test, not weakening the mutation —
  the fixture is an adversarial boundary, not a green-count generator.

**Recorded, not opened as a defect — the pressure point waiting for item 5:** *plan identity is
not membership identity.* "Kim is covered under P during period T" must be handled without making
membership an attribute of `Plan`, `Person` or the expense. And *coverage* is now explicitly
overloaded: the coverage arrangement is what `Plan` identifies · who is covered and when is a
future relation · whether a particular expense is covered is another future question · insurer
payment / adjudication is another proposition. That separation is strong enough that item 5 can
address the middle one without reopening 4c.

**Rule carried into item 5:** ***do not let the existence of `Plan` pre-answer the meaning of
"covered under."*** The relation now has a real endpoint to attach to; its semantics must still be
independently earned.

**4c — PLAN IDENTITY: ACCEPTED / CLOSED.** Item 4 is complete. Next: item 5, the role period.
