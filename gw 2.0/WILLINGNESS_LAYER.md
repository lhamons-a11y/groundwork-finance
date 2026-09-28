# The Willingness Layer: the build pass

> Status: **RULED 2026-09-27 (Rob, §6): all eight recommendations accepted. First build AUTHORISED
> 2026-09-28 (Rob: *"Run it when the gate is available"*) and BUILT (§7); awaiting the gate and Rob's
> acceptance.** Opened the same day. Queue item 23. Rob, 2026-09-27: *"lets build the
> teaching layer"*, then *"the unbuilt teaching pieces"*, then *"I feel we need that before the
> dashboard"*. So this pass comes before the dashboard build (item 22, ruled, not authorised).
>
> The design is **Appendix F** of the blueprint (F.1–F.8), with **E.2 / E.2a / E.2b** for the
> category classifications it reads and corrects. F.3 (where it lives) was settled 2026-09-03.
> That is the *what*. This pass is the *build*: what gets built first, from which existing evidence,
> where it shows, and what may be stored. The design is not reopened. Where the code and the
> design disagree, the finding says so and asks for a ruling.

---

## 1. What is fixed

1. **Appendix F as written.**
   - The three planes: what is true, what would help, and what the user is willing to do.
   - "Nothing at all" is a first-class answer.
   - Willingness is evidenced three ways (F.6a), each with its own standard:
     - **observed**: must cite its receipt;
     - **inferred**: must predict behaviour it was not fitted to;
     - **declared**: sovereign.
   - F.6b: a strategy, not a motive. `unclassified` is the resting state and must stay common.
   - F.4: willingness is never a stick.
2. **E.2 / E.2a / E.2b as written.**
   - Flexible or sacred, learned from proof.
   - Probation for correlated causes.
   - An override is persistent and never decays.
   - A contradiction-check never silently flips the user's word.
3. **No silent learning** (2026-08-17): an observation not surfaced to the person may not become
   persistent memory. No engagement signals, no learned ranking, no inference from silence.
4. **The dashboard rule** (2026-09-27): *usage never creates, ranks, or implies* anything. Evidence
   about the user's finances does.
5. **Absence is not zero, teach the question, local-only AI.**
6. **SCHEMA_VERSION + the s51 pin** for any `migrate.py` change, proven on an upgraded database.

---

## 2. What exists today (measured 2026-09-27, master `9e3f776`)

| piece | where | state |
|---|---|---|
| the deliberate budget edit | `budget_adjusted` Historian event, `server.py` `update_budget_item` (old amount → new amount, `budget_item_id`, name) | **built**, logged since 1.1; the only *observed* source E.2 names |
| the category ledger | transactions by category and month | built |
| the necessity floor (E.1) | `core/solution.py` `NECESSITY_FLOOR`, `is_protected` | built, versioned (`'2'`) |
| naming without asserting | `solution.py` levers 1 and 4 name a category as a **receipt** ("budgeted $400, never needed more than $310"), ordered by size only | built |
| the three withheld ranking rules | `solution._rank_key`: E.3 rules 2, 4, 5 (flexible-by-proof, demonstrated tolerance, spread vs. concentrate) **absent deliberately**: *"each needs willingness"* | **the gap this layer fills** |
| the generic monthly lever | `solution.py`: *"which envelope it comes from is the user's to choose, and naming one needs willingness this engine does not have"* | waiting on this layer |
| overrides (E.2b) | none: no table, no setting, no route | **not built** |
| in-context declaration (F.3) | none | **not built** |
| the working picture (F.3) | none | **not built** |
| strategy inference (F.6b) | none | **not built** |
| contradiction-check (E.2b) | budget settled (the brake budget, 2026-09-03); nothing else | **not built** |

Two measurements matter more than the table:

- **There is no assistant destination.** F.3 places the working picture "with the assistant" and
  depends on the assistant being a **first-class destination**. It says outright: *"If it becomes a
  secondary pane, the correction channel goes with it."* Groundwork has twelve views (`index.html`:
  dashboard, ledger, budget, debt, BYB, investments, net worth, trophy, trip, gifts, settings,
  reports). **None of them is an assistant.** The only AI conversations are threads inside report
  cards (`_rcAIThread`). So F.3's home does not exist yet (W3).
- **The Historian already holds usage events.**
  - `session_start` is logged at bootstrap.
  - `session_end` and `budget_reviewed` are sent by the client through `/api/historian/engagement`.
  - `proactive_shown` and `proactive_dismissed` are logged too.
  - `get_engagement_streak` reads the first two for the check-in streak, which the user sees.
  - All of them sit in the same table the Willingness Layer reads. **Keeping them out is a
    requirement of construction, not a hope** (W6).

---

## 3. Findings and proposals

**W1: Build order follows the burden of proof, cheapest honest channel first.**

| slice | channel | builds | depends on |
|---|---|---|---|
| **W-A** | observed | E.2's three readings per category, each citing its receipts: *cut and it stuck* (flexible), *cut, then restored* (sacred), *held through a tight month* (sacred until shown otherwise). E.2a probation: a shift that coincides with an income change stays `unclassified` | `budget_adjusted` + the category ledger: exists |
| **W-B** | declared | the E.2b override (*protect* / *flexible* / *release*), persistent, never decaying. Set where a claim is shown (W3) or in answer to a proposal (in context, F.3) | storage: a schema change (W5) |
| **W-C** | consumption | the solution engine reads W-A and W-B: E.3 rule 2 (flexible-by-proof) enters `_rank_key`; a declared-protected category is never a lever; the generic monthly lever may name a category **only** when it is observed-flexible or declared-flexible, citing which | W-A, W-B |
| **W-D** | correction | the contradiction-check (a declaration against durable contrary behaviour). **Passive by default** in the working picture; promotes only through the gauntlet, from the brake budget (settled) | W-A, W-B, W3 |
| **W-E** | inferred | F.6b's strategy label with the out-of-sample prediction test | W-A with months of data, and a null model (W4) |

Recommendation: **build W-A, W-B, W-C and W3 as the first build; W-D second; W-E last and
separately.** W-C is where the user gets something new: a path that names *their* flexible
category because *they* showed or said it is. Without W-C the layer is a record nobody acts on.

**W2: Observed readings are computed, not stored.** An E.2 reading is arithmetic over the record,
recomputed on every read. That leaves nothing for the no-silent-learning rule to catch and nothing
to decay. F.6b speaks of a label that is *"cached, never remembered"*. Recommendation: **no cache in
this build.** Add one only if a measured cost demands it, as a ruled change with the recompute
proven equal.

**W3: The home. F.3's dependency is live now, not hypothetical.** Options:

| | what | cost |
|---|---|---|
| **H-a** | build the assistant destination **now**, as a new view whose first pane is the record ("what Groundwork has concluded"). The conversation pane joins it later (local narration, item 10). Settings gets F.3's one-line pointer | a new view; honours F.3 exactly: same home, distinct view; the home exists before the conversation does |
| H-b | put the working picture inside Budget, where the categories are | contradicts F.3's placement: a demotion, which F.3 says is a Willingness Layer decision |
| H-c | build the engine only, with no surface | the E.2b correction channel has nowhere to live; declarations cannot be made or disputed; F.3's "nothing editable that isn't first a claim with a receipt" cannot be checked |

Recommendation: **H-a.** Its **empty state is designed first** (F.3: *"the design centre, not an
edge case"*). It says Groundwork has not earned conclusions about the user yet, and it has **no
controls**. A control appears only beside a claim Groundwork has made, with the receipt. That is
the testable form of "not a settings screen".

**W4: Null-model the inferred channel before it ships** (memory rule, twice now: the obvious
threshold was a coin flip). W-E does not enter a build until:
- its prediction test has been run against trend-free synthetic ledgers;
- it has been shown to return `unclassified` for nearly all of them.

F.6b's own acceptance test stands: *if nearly everyone gets a label, delete the layer.*

**W5: Storage is only the user's own acts.** What is stored:
- an override: category, *protect* or *flexible*, when it was set, and the claim it disputed;
- an in-context declaration: the words attach to the proposal they answered.

Nothing inferred is stored (W2). This needs a table or a setting:

| option | what it needs |
|---|---|
| a new table (`willingness_declarations`) | a SCHEMA_VERSION bump and the s51 pin, proven on a v1.1.0 upgrade |
| an `AppSetting` JSON key | no migration |

Recommendation: **a table.** Declarations are a history the user can read back ("you set dining
protected on 3 March"), so they carry their date and the claim they answered. A settings key is the
settings-screen shape F.3 refuses. A release, if allowed, is a new row, not a delete, so the
record of what the user said stays point-in-time (E.2b: *overrides take effect prospectively*).

**W6: The read boundary, stated as a crossing test.** The Willingness Layer may read only:
- `budget_adjusted`;
- the ledger (transactions, categories, budget items);
- income rows, for E.2a;
- its own declarations.

It may **never** read:
- `session_start`, `session_end`, `budget_reviewed`, or any engagement event;
- `proactive_shown` or `proactive_dismissed`. **Dismissing a suggestion is not an answer about
  willingness** (A.4 already uses dismissals for the gauntlet's backoff; this layer must not
  reuse them as evidence about the person);
- anything counted from navigation.

A structural test pins the allowed set, as H1's reader pin did. A new source is a ruled addition.

**W7: F.4 in text.**
- No sentence may pair a declaration with a failure ("you said…, but…" as a verdict).
- A missed intention is renegotiated neutrally (F.4's own wording).
- The contradiction-check asks *which do you mean*, not *why didn't you*.
- A lexicon test over the layer's strings, like s52's.

**W8: Scope.**
- The **engine** (`core/willingness.py`) sits beside `core/solution.py`, which both lines carry.
- The **surface** (H-a) and the **solution engine's use of it** are 2.0 only.
- On 1.x the solution engine must keep today's behaviour exactly. Either the willingness input is
  absent there, or the engine is master-only.

  Recommendation: **master only**, engine and all. 1.x gains nothing from an engine with no
  surface, and a shared engine adds a place to diverge.

**W9: What follows this pass, by name.**
- **The break-detector (F.8)** is its own pass after W-A exists. It re-derives the willingness
  model, and until W-A exists there is nothing to re-derive.
- **Layer 4** (`ASSISTANT_SCOPE.md`) surfaces in the working picture, so it follows H-a.
- **Streamed narration** (item 10) waits on item 11's CPU measurement, as before. It is the
  conversation pane's voice when H-a gets one.

**Noticed in passing, not in scope:** `app.js:934` computes an `engagementLevel` ("engaged",
"occasional", "passive") from the count of recent transactions.
- It is derived from the record, not from watching, and it is not stored.
- But it labels a *person* from how *sparse their record* is, which is the absence-is-not-zero
  shape.
- Nothing in the Willingness Layer may read it. Whether it should exist at all is a separate
  question.

---

## 4. Cases

| # | situation | expected |
|---|---|---|
| Wl1 | a new user, no budget edits | working picture: the empty state, no controls; solution paths exactly as today |
| Wl2 | dining cut 450 → 350 in March, spending stayed ≤ 350 for three months | observed *flexible*, citing the `budget_adjusted` event and the three months |
| Wl3 | dining cut in March, raised back in May | observed *sacred*, citing both edits |
| Wl4 | dining rose in the same month income rose | `unclassified` (E.2a probation); the correlation shown as a fact, never narrated as cause |
| Wl5 | the user marks dining *protected* beside Wl2's claim | declaration stored with its date and the claim it disputed; dining never a lever; the reading and the declaration both visible |
| Wl6 | Wl5, then dining trimmed for three months | contradiction-check, passive: *"you set dining protected; the last three months trimmed it: which do you mean?"* The declaration is not flipped |
| Wl7 | a shortfall, dining observed-flexible | the named lever may say *dining*, citing the receipt; ranked by E.3 rule 2 |
| Wl8 | the user opens Budget every day for a month | **nothing changes**: `budget_reviewed` is never read |
| Wl9 | the user dismisses a proactive brake twice | the gauntlet's backoff applies (A.4); the Willingness Layer reads nothing from it |
| Wl10 | a category on the necessity floor | never proposed, whatever is observed or declared *flexible* (E.1); a *flexible* declaration there is shown with the floor's reason |
| Wl11 | the user declares "not changing anything right now" | F.2: accepted, no guilt; the truth still shown; paths still offered as receipts, none ranked as the user's |
| Wl12 | an upgraded v1.1.0 database | migrates; the declarations table empty; nothing inferred appears |
| Wl13 | the LTS bundle | carries none of it |

---

## 5. Ruling sought: Rob

1. **W1, order:** W-A, W-B, W-C and the home first; the contradiction-check second; strategy
   inference last, as its own pass?
2. **W2:** observed readings computed on every read, no cache?
3. **W3, the home:** H-a, the assistant destination built now with the record as its first pane,
   the empty state designed first, and a pointer from Settings?
4. **W4:** strategy inference gated on a null-model run, with F.6b's "delete if everyone gets a
   label" as its acceptance test?
5. **W5, storage:** a declarations table (schema bump and pin), with releases as new rows?
6. **W6:** the read boundary as listed, including **dismissals are not willingness**?
7. **W8, scope:** master only, engine and surface; 1.x unchanged?
8. **Then:** the break-detector as the next pass, and the dashboard build after this layer?

---

## 6. Ruling: Rob, 2026-09-27

**All eight accepted as stated.** The distinction the ruling draws, recorded:

> Groundwork can be an active financial coach **without learning the user's behaviour from the
> Historian.** The Willingness Layer's coaching signal is what the user has actually said they are
> willing to do, and what their record shows, never what their clicks suggest.
>
> **Financial evidence** tells Groundwork what is happening. **The user's stated willingness** tells
> it what kinds of solutions it may responsibly present. **The coaching layer** explains the
> connection. **The user** still makes the decision.

| # | ruling |
|---|---|
| **1** | **Build order as W1:** record evidence (W-A), the user's statements (W-B), the solution engine's use of them (W-C) and the home first; the contradiction-check (W-D) after; strategy inference (W-E) last, earning its place by test |
| **2** | **Derived readings are recalculated, never persisted.** Only what the user said is stored |
| **3** | **H-a: the home is built now,** its empty state genuinely empty until Groundwork has something it can substantiate. It gives the coaching layer somewhere to exist **without prematurely inventing a conversational assistant**: the conversation pane is not part of this build |
| **4** | **W4's kill condition:** if the strategy labels collapse into near-universal labels on trend-free data, they are not earning their existence, and W-E is not built |
| **5** | **Storage: the user's statements get their own history.** A changed mind is a new statement, never a rewrite. The schema bump and s51 pin follow |
| **6** | **The layer never reads usage, dismissals included:** *a dismissal says "I dismissed this", not "I am unwilling to do this"* |
| **7** | **2.0 only;** 1.x is not disturbed |
| **8** | **The break-detector is the next pass; the dashboard build follows,** on a foundation that presents actual coaching situations |

**Separated out, not part of this ruling:** the `engaged / occasional / passive` label
(`app.js:934`) becomes its own semantic question, opened later and not here: *what does Groundwork
actually know when it labels someone "engaged", "occasional" or "passive", and is that label useful
enough to exist?* A sparse record can mean many things, and "passive" is not one Groundwork can see.

**Not authorised yet:** the build itself. *(Authorised 2026-09-28: §7.)*

---

## 7. The first build: W-A, W-B, W-C and the home (2026-09-28)

Rob, 2026-09-28: *"Run it when the gate is available"*. That authorised the first build ruled in §6.1. Built on
master only (ruling 7); 1.x untouched.

| piece | where | what it does |
|---|---|---|
| **W-A** observed | `core/willingness.py` `observed_readings` | E.2's readings per budgeted category, each a citation: **a cut that held** three recorded months (flexible); **a cut later restored** to at least its old amount (sacred); **kept through two tight months**, where spending passed recorded income (sacred until shown otherwise). E.2a: a cut beside a ≥10% income move is `unclassified` with the move shown as a fact (`probation`); income not on record around the cut is `income_unrecorded`, never level. Also `too_soon`, `did_not_hold` and `no_evidence`, which conclude nothing. The necessity floor gets no reading. Pure: no database access, no cache |
| **W-B** declared | `WillingnessDeclaration` (`willingness_declarations`), `POST /api/willingness/declarations` | protect / flexible / release, with what it answered. **Append-only**: no route edits or deletes; a changed mind and a release are new rows. F.3 enforced by the server: a statement answers **a claim** (a concluding reading, or the user's own earlier statement) or **a proposal whose text names the category**, and anything else is refused |
| **W-C** consumed | `server.reallocation_candidates` / `trim_candidates` → `willingness.annotate`; `core/solution.py` `_willing_key`, `_flexible_named` | the user's word beats every reading. A protected category is **never a candidate** (lever 1 or lever 4). **E.3 rule 2**: flexible candidates are offered first, then unclassified, then what the record says is kept, and size within each. With no willingness the order is exactly as before. The generic monthly lever names a category **only** when it is flexible, and says whether that came from the record or the user's word. The floor holds against a *flexible* statement. Rules 4 and 5 stay absent: they need W-E |
| **the home** (H-a) | `static/js/teaching/willingness.js` | a view of its own, **Assistant → Working picture**, plus the Settings pointer, both created from the teaching layer (app.js and index.html untouched). **The empty state has no controls.** Each claim shows its receipt with one control that disputes it. Each statement shows its date, what it answered, and *Release* / change. There is a full history, oldest first. The page says it never learns from pages opened or suggestions dismissed |
| in context | `static/js/teaching/paths.js` | a reallocation or trim path that names a category carries **"never X"**, which answers that proposal where it stands. A flexible candidate's path says *"your record shows X has moved before"* or *"you marked X flexible"* |
| schema | `migrate.py` `SCHEMA_VERSION = '20260928-willingness-declarations'` | the bump creates the table on upgraded databases (via `init_db`'s `create_all`). **The bump carries no migrate.py code, so the s51 fingerprint cannot see it**, and s129 proves the upgrade instead (below) |

**Tests: `smoke_sections/s129_willingness.py`, 45 checks.**
- **Engine cases** Wl1–Wl5, Wl7 and Wl10, each E.2 / E.2a reading, and the ordering.
- **Route cases, end to end on the real database:**
  - the gatherer reads the edit and complete months only;
  - an unclaimed category is refused (409);
  - a proposal must name the category;
  - "never X" is stored with what it answered;
  - the protected category leaves the solution engine's candidates;
  - a changed mind and a release are new rows;
  - no PUT / PATCH / DELETE route exists.
- **The W6 read boundary, pinned structurally:**
  - the gatherer reads exactly one event kind, `budget_adjusted`;
  - no usage name appears on the layer's path;
  - the engine imports no storage.
  - Mutations are caught: a dismissal read as willingness, a page visit counted, a second event kind, and the engine given database access.
- **F.4 over what the user reads,** with a scolding-line mutation.
- **The empty state offers no controls.**
- **The seam:** app.js and index.html know nothing of the layer.
- **Wl12:** a database stored at the previous version gains the table on start.

Standalone: 45 / 0. The neighbouring sections standalone: s45 solution engine 288 / 0, s51 pin 6 / 0, s30 seam
12 / 0.

**Seen in the page** on a throwaway database, seeded (built-in browser, `localhost` dev server, never the real
database):
- A seeded Dining cut (450 → 350, held four recorded months, income level) showed as flexible with its
  receipt and one control, *Protect it*.
- Protecting it moved it under *What you have told Groundwork*, with the reading quoted once.
- *"never Hobbies"* on a path phrase stored a proposal-answer for a category with no reading.
- *Release* added a row, and the history reads oldest-to-newest in reverse.
- No console errors.
- On an empty database the page showed *"Groundwork has not drawn any conclusions about you yet"* with
  **zero controls**.

**Named, not built here:**
- W-D, the contradiction-check (second, per ruling 1).
- W-E, strategy inference (last, gated on the null model, ruling 4).
- F.2's explicit *"not changing anything right now"* statement. Wl11's behaviour already holds by default: with nothing said, no path is ranked as the user's.
- The conversation pane (ruling 3).
- The break-detector: the next pass (ruling 8).

**Found while building, for Rob:**
- **s51's blind spot has a second shape.** A new **model table** needs a SCHEMA_VERSION bump just as a new column does, because `create_all` runs only when the stored version differs. But it changes no migrate.py code, so the fingerprint cannot catch a forgotten bump. This build bumped and proved the upgrade in s129. The general guard, fingerprinting the models' table set in s51 on both lines, is a separate change and is not made here.
- **Readings attach an edit to the budget item's category as it stands now,** because budget items key category by name. Renaming a category re-files its past edits under the new name. That is honest for a rename; a split or merge is not modelled.
