# The dashboard — your summary, and what needs attention

> Status: **RULED 2026-09-27 (Rob, §6). No code; the build is not yet authorised.** Opened the same day. Rob's question:
>
> > **Should the dashboard become more dynamic: showing the summary items the user normally looks
> > at, and the items Groundwork sees as needing the user's attention?**
>
> Queue item 22. Where the proposal meets a settled rule, the rule governs and the proposal is
> reshaped (§3), never the other way round.

---

## 1. What is fixed

1. **No silent learning** (Rob, 2026-08-17, settled): *an observation not surfaced to the person
   cannot become persistent memory.* It forbids engagement and dwell signals, learned ranking of
   what to surface, and inference from silence. **"What the user normally looks at", measured by
   watching what they open, is exactly that**, so it is not available as a mechanism.
2. **Appendix A, when the app may speak first** (`core/proactive.py`, `/api/proactive/*`,
   `teaching/proactive.js`): the gauntlet; at most one thing per session and two brakes a week;
   a dismissal cooldown; the **Speaking up** dial (Normal / Fewer / Off, `proactive_dial`).
3. **Absence is not zero:** every dashboard verdict passes a completeness test first. The
   *$7,053 shortfall* that was a surplus came from exactly this surface (`_computeCurrentPriority`).
4. **Teach the question** (Rob, 2026-09-24 / 26): the user decides and the data is truth; a
   surface teaches the mechanism and the question to ask; estimates are labelled, facts carry
   their source, unknowns stay unknown; never a verdict.
5. **Proof, not persuasion** (Appendix B): every claim is a fact from the user's own record.

---

## 2. The surface today — measured 2026-09-27 (`renderDashboard`, `app.js:2194`)

The dashboard is not a blank slate. It already draws, top to bottom:

| section | what it is | kind |
|---|---|---|
| `_renderRecordStatus` | the *check-engine light*: *"Financial Record: up to date"*, or a band naming which conclusions are **gated** by missing data (`_computeClaimConfidence`) | a **completeness fact** |
| `_renderWhatChanged` | *What changed since last month*, confidence-gated | summary |
| `_renderCurrentPriority` | *Current priority* / *Where you stand*: one ranked stability verdict | a **verdict** (the $7,053 site) |
| `_renderHealthCard`, pace bar | month health, income pace | summary |
| `_renderDashHeroCard` | stage-aware hero (debt / building) | summary |
| `_renderDashSpendingDonut` | spending by category | summary |
| `_renderDashUpcoming` | **debt payments due within 7 days, not yet paid this month** | an **attention fact** |
| `_renderDashSeasonalAlert` | seasonal spending alert (B6d) | an **alert** |
| achievements strip, check-in streak, next achievement | recognition | summary |
| Sunday card (Sundays), Getting started / Week 1 checklist | periodic / onboarding | summary |
| the proactive insight (`teaching/proactive.js`) | Appendix A's one gated voice | **the app speaking first** |

Three things follow:

- **Attention already exists, scattered.** Upcoming unpaid payments, gated conclusions and a
  seasonal alert each live in their own card, under their own rules.
- **Nothing is user-arranged.** Every section is fixed by code, apart from sections that hide
  themselves.
- **Two kinds of "alert" are mixed:** facts (*a payment is due Thursday and unpaid*) and
  insights (*you could close this gap by…*). Appendix A governs only the second.

---

## 3. Findings

**D1 — "What the user normally looks at" comes from their record and their choice, never from
watching them.** Two sources, both honest:

- **the user arranges it.** Pin, hide and reorder summary tiles, stored as their own setting. A
  visible choice, reversible, theirs;
- **defaults come from what the record contains.** Debts on file mean a payoff tile; savings goals
  mean a funds tile; no investments mean no investment tile. Reading the data is not observing the
  person.

**Refused:** view counts, dwell time, click frequency, "you usually open X", and any ranking that
reorders by use, including a *"pin this?"* suggestion computed from accumulated views. That counting
is the silent accumulation rule 1 forbids, whether or not the suggestion is later shown.

**D2 — *Needs attention* is facts, and only facts.** An attention item is a **dated fact from the
record, with its source and a way to resolve it**: never advice, never a verdict. Candidates, each
already computed somewhere or cheaply derivable:

| candidate | source | resolves by |
|---|---|---|
| a payment due within N days and not yet paid this month | `_renderDashUpcoming` today | paying / marking paid |
| an account not imported for N weeks | last transaction date per account | importing |
| a conclusion gated by missing data | `_computeClaimConfidence` (the check-engine light) | the named missing input |
| a statement balance that does not match the ledger | reconciliation | reconciling |
| an import offer or a Downloads file waiting (H2) | the auto-import queue | answering it |

**The list is closed:** a new kind of attention item is a ruled addition, never something code
invents. That keeps *Needs attention* from sliding into the nagging Appendix A exists to prevent.

**D3 — Teaching insights stay under Appendix A, unchanged.** *"You could close this gap by…"* is the
app speaking first. It keeps the gauntlet, the caps, the cooldown and the dial, and it is **not**
moved into *Needs attention*. The two areas differ in kind, not only in layout.

**D4 — Every attention item passes a completeness test first (absence is not zero).** *"Account not
imported for 5 weeks"* is a fact. *"You spent nothing on groceries"* inferred from a missing import
is not. An item whose inputs are incomplete says what is missing, or does not appear.

**D5 — Every attention item teaches the question, not a verdict.** A statement mismatch says what
differs and what to check, not *"your bank is wrong"*. A due payment says the amount and date, with
the balance it comes from.

**D6 — Consolidation, not addition.** The redesign **gathers** what exists (check-engine light,
upcoming payments, seasonal alert) into *Needs attention*, and the summary cards into *Your
summary*, rather than adding a fourteenth section. **`Current priority` is the open question:** it
is a ranked verdict, not a fact, so it belongs in neither area as it stands (§5 Q5).

---

## 4. Cases

| # | situation | expected |
|---|---|---|
| Da1 | a new user with debts but no savings goals | defaults: a payoff tile, no funds tile, from the record |
| Da2 | the user pins *Net worth*, hides the donut | stored as their setting; shown exactly so after restart |
| Da3 | the user opens *Debt* daily for a month | **nothing changes** on the dashboard: no view is counted |
| Da4 | a payment due in 3 days, unpaid | one attention item: amount, date, source; resolves when paid |
| Da5 | an account last imported 6 weeks ago | one attention item naming the account and the date |
| Da6 | income rows missing for a month | the item names what is missing, never a shortfall verdict |
| Da7 | a teaching insight qualifies | shown under Appendix A's caps, never listed in *Needs attention* |
| Da8 | *Speaking up* set to Off | insights silent; **facts still listed** (Q2 decides) |
| Da9 | the user dismisses a still-true attention item | per Q3 |
| Da10 | a code path emits an attention kind not on the ruled list | refused by construction (a crossing test) |

---

## 5. Ruling sought — Rob

1. **D1:** summary tiles arranged by the user, with defaults from what the record contains, and no
   use-based arrangement or suggestion of any kind?
2. **D2 / D3:** *Needs attention* holds facts only, from a closed ruled list, while teaching
   insights stay under Appendix A. **Do attention facts sit outside Appendix A's caps and the
   *Speaking up* dial, since they are facts rather than the app's voice?**
3. **Dismissing a still-true fact:** allowed, and for how long (until it changes, or a set time)?
   And does the dismissal persist, as the user's own visible choice?
4. **The starting list:** which of D2's five candidates, and what N (days / weeks) for each?
5. **`Current priority`:** keep it as its own verdict card, fold it into *Your summary*, or retire it
   in favour of attention facts plus the proactive voice?
6. **Scope:** 2.0 only (the teaching seam), or both lines? The dashboard is shared code today.

---

## 6. Ruling — Rob, 2026-09-27

**The overarching rule, recorded exactly:**

> **Usage never creates, ranks, or implies an attention item. An attention item requires evidence
> about the user's finances.**

**The 17 August no-silent-learning rule is not reopened.** The dashboard is dynamic from the
user's **financial state**, never from their navigation.

| # | ruling |
|---|---|
| **1** | **User-controlled pin / hide / reorder.** Usage is **not counted, not stored, and not used** to rearrange the dashboard. Initial contents may be derived from **current financial records**, never from behavioural history |
| **2** | **Attention facts are separate from *Speaking up*.** A due payment stays visible when advice is silenced: **fact visibility ≠ unsolicited advice**. Recommendations stay under Appendix A's caps and the dial |
| **3** | **A dismissal persists until the underlying fact changes.** The dismissal is a user action and may be stored; **no arbitrary timeout and no engagement-based resurfacing** |
| **4** | **Exactly three to start:** an unpaid payment due within **7 days**; an account not imported for **3 weeks**; a conclusion **blocked by missing data**. Statement mismatches and waiting downloads are **deferred** until their completeness semantics are separately established |
| **5** | **`Current priority` retired as a separate ranked card.** Its factual content belongs in *Needs attention*; any recommendation drawn from those facts stays under the speaking-up rules |
| **6** | **2.0 only, through the teaching seam.** The 1.x dashboard is unchanged |

**What the build would have to show, by construction and by test:** no usage signal is read,
stored or computed anywhere on the dashboard's path. Every attention item is one of the three
ruled kinds, with its source and the fact its dismissal is tied to. Completeness is tested
before any item appears (absence is not zero). The LTS bundle carries none of it (the seam's
existing check). **Not authorised yet:** the build itself.

