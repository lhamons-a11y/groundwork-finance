# Item 45 — The health review: where the module stands, and the smallest first piece

**RULED 2026-10-08 at design level (Rob: "approve H1–H7 as recommended, with one clarification to H7"; confirmed:
"yes that's my ruling").** See section 6. **Nothing is authorised for implementation.** No code, schema change,
migration or 1.x change follows from this ruling. Each piece of work is its own item, with its own scope, review and
authorisation.

Opened 2026-10-08 (Rob: *"what is there to build for health?"* → *"open the health review item"*). The module was held
on 2026-10-04. This item reopens it as a **review only: no code**. It reconciles the draft with its challengers, checks
§0 against today's code, maps the record layer, and proposes a first slice. It asks for rulings and authorises nothing.

## 1. What exists (measured 2026-10-08, master `c32a083`)

**Shipped, both lines**
- Health care is a set of spending categories. Imports sort into them automatically.
- Health categories are on the *necessity floor* (`core/solution.py` `NECESSITY_FLOOR`, version 2 since 2026-09-06).
  So the engine never offers them as money to move or cut. That is design §9 Q5, already done.

**The record layer, on master, built to tests written first**

None of it is wired to a screen, and five of these modules have no callers at all:

| Module | What it holds | Called by |
|---|---|---|
| `core/plan_year.py` | insurance plans and plan years, terms as versioned history | nothing |
| `core/allocation.py` | health obligations, funding and reconciliation | nothing |
| `core/payment_plan.py` | one coherent payment state from a ledger | nothing |
| `core/reserve.py` | the health reserve, as an allocation of a balance, not a transaction | nothing |
| `core/person.py` | who an expense belongs to (identity, not a name) | nothing |
| `core/classification.py` | health-domain sensitivity classification | `core/database.py` |

The triage's standing caveat still holds: every guarantee these modules make is made in isolation.

**The design and its challengers**

| Document | Verdict it reached |
|---|---|
| `HEALTHCARE_MODULE_DESIGN.md` (draft, 2026-09-05) | seven parts; nine open questions (§9); *"UNDER REVIEW — do not implement from this document alone"* |
| `HEALTHCARE_CRITIQUE_SURVIVAL.md` | 8 criticisms: 6 survive; 2 land (the reimbursement guard is not carried over; out-of-pocket language does not exist) |
| `HEALTHCARE_GAP_TRIAGE.md` | 15 gaps. One live defect, quarantined and repaired (`efbb271`): unentered terms read *unknown*, not *met*. 1, 4, 6 and 8 are new; 2, 3, 5, 7, 9, 11 and 12 partial; 10 and 13 addressed; 15 closed as design |
| `HEALTHCARE_FAILURE_SEMANTICS.md` | what the model may return, record, show and say when it can't be trusted; three cases left open |
| `INSURER_CLAIM_IDENTITY.md` | **ruled 2026-09-14 (4b)**: the insurer's claim has no Groundwork identity |
| `HEALTH_TRUST_BOUNDARY.md` | 5 of 6 release-blocking conditions hold: no enforcement point; the narrator log and app log are replicas the sensitivity layer cannot see (F3, F4); blast radius undeterminable (F5) |

## 2. §0 against today's code — two live findings

§0 is the design's precondition: *health spending is a cost the engine prices, never a lever it proposes moving*. §0.1
adds: *care the user cannot decline is never expressed as a delay to the debt-free date*.

**Finding A — necessary care is priced in months, on master today.** The floor keeps health out of the *levers*
(`_headroom`, `_trims`, and so `_best_named` and reallocation). But four surfaces still price a health category or
charge on the debt-free date:
1. **Budget page** (`teaching/budget.js`, from `budget_pressure`). For a protected category over budget it says the
   budget is set below what it costs, then: *"That difference costs **3 months** on your debt-free date."*
2. **Monthly report** (`teaching/reports.js`). The same sentence: *"… that difference is **3 months** and $… in
   interest."*
3. **Dashboard** (`server.py`, the *brake* item from `budget_pressure`). An overspent protected category can be raised
   as the month's brake, priced in months.
4. **Ledger lesson** (`large_charge_lesson`). It skips only transfers, income, debt and savings. A large recent
   hospital or pharmacy charge can be its subject: *"The St. Mary's Hospital charge cost **2 months** on your debt-free
   date."*

That is exactly the sentence §0.1 forbids. These surfaces are 2.0's teaching layer. 1.x strips it, so this is master
only.

**Finding B — the floor misses common health names.** Built-in categories are covered, except *Long-term Care*. But
many names a user might type are not:
- **Medicines:** *Medicine, Meds, Rx, Insulin*.
- **Visits:** *Urgent Care, Physician, Pediatrician, Surgery, Ambulance, OB/GYN, Labs*.
- **Eyes and ears:** *Hearing Aids, Glasses, Contacts, Optometrist*.
- **Teeth:** *Orthodontist*.

Each could still be offered as money to cut. (*ER* is protected only by accident: it matches inside "water".)

## 3. What has changed since the draft (2026-09-05 → today)

- **Cloud AI is gone** (item 21). Design §3 rule 3 (refuse the cloud model for health content) has nothing left to
  refuse. All narration is local or templated.
- **The feedback path is not carried into 2.0** (trust boundary §7), and the forum asks for plain words, no files
  (item 37). F2 leaves 2.0. F3 (the narrator miss-log) and F4 (the app log) do not.
- **Transparency** (item 39 U7). Every figure shows its working; assumptions are named. A health figure is held to it.
- **The no-silent-learning edges** (U7). Conclusions about the person are never drawn from usage. That bears directly
  on any *"you tend to …"* about care.
- **AI-off** (A9/A10). Every health surface must work with the model off.
- **The Assistant is parked to ~2029-30.** Design §9 Q1 (*Groundwork or Assistant?*) now has a practical answer: the
  record layer is already in Groundwork's `core/`.
- **Websites read inside Groundwork** (item 44). The one page read is the flights fare. Nothing health-related may
  ever use that path.

## 4. Points for ruling

**H1. Fix Finding A now, ahead of any module.** Necessary care is never priced in months:
- **Budget page and report:** a protected category over budget keeps its first sentence (*"the budget is set $X/mo
  below what it costs"*) and loses the months-and-interest one. The correction stays a correction to the number.
- **Dashboard:** a protected category is never the brake.
- **Ledger lesson:** skips charges in protected categories.
- **Gate:** a check asserting no surface prices a protected category or charge in months, with mutations.

Master only (1.x has no teaching layer).

*Recommended.* It is live, it is the sentence §0.1 exists to stop, and it does not depend on the module.

**H2. Widen the floor (version 3).** Add the names in Finding B and *long-term care*, then bump
`NECESSITY_FLOOR_VERSION` to `'3'`. Matching stays loose on purpose: over-protecting costs one unavailable lever;
under-protecting proposes cutting someone's insulin.

Master only. 1.x builds strip the whole teaching layer (`static/js/teaching/`, including `paths.js`, where the levers
are shown), so a 1.x user is never shown a proposed cut (checked 2026-10-08).

*Recommended.*

**H3. Design Q1: Groundwork, not the Assistant.** The record layer already lives in `core/`, and the Assistant is parked
for years. Per-account visibility stays a Groundwork concept. *Recommended.*

**H4. Design Q2: medication pricing is the user's own record only.** There is no free patient-price source, and a
commercial feed would be a new outbound path for the most sensitive data the app could hold. Prices are what the user
entered or imported. *Recommended.*

**H5. The first slice: HSA and FSA balances.** These are design §1.3, reusing the sinking-fund machinery.
- **What it holds:** each account's balance, the year's contribution limit, and for an FSA the use-it-or-lose-it date.
  It is shown as a fact with its working, and it warns before money would be forfeited.
- **What it leaves out:** no person, no medication, no plan terms. It is money in accounts, as sensitive as a savings
  balance and no more. So it does not wait on the trust-boundary enforcement point.
- **AI:** works with AI off. Master only.

*Recommended* as the first piece of the module itself. It is useful alone, and the least sensitive.

**H6. Nothing that names a person, a medication or a diagnosis is built before the trust-boundary enforcement point.**
That means F1 (one place every outbound or persisted path passes) and F3/F4 (logs that cannot carry health content).
Design §3's rules 4 and 6 come with it: exports exclude health rows unless included, and the backup statement. This
fences the design's §1.5–1.7 (visit report, year in review, named people), §7 (the bill that lands) and §8
(collections). *Recommended.*

**H7. The order after H5, each its own item and ruling:**
1. the trust-boundary enforcement point (H6);
2. plan year and deductible tracking (wiring `plan_year.py`, under the failure semantics);
3. the reserve (needs design Q9);
4. the visit report and year in review (needs Q3);
5. named people (needs Q4 and Q8);
6. the bill that lands (needs Q6 and Q7);
7. collections last, with *underbuild* a live answer (critique 6).

*Recommended* as the sequence. Each step still needs its own go-ahead.

## 5. Open, and deliberately not asked yet

- **Design §9:** Q3 (does the visit report leave the machine?), Q4 (whose health, in a joint account?), Q6 (does the
  app say *"call them"*?), Q7 (card-free date or all-obligations date?), Q8 (are names enough?) and Q9 (reserve
  before, alongside or after the last balance; it changes `core/consequence.py` for every user). Each waits for the
  slice that needs it.
- **Triage gaps:**
  - *do first:* 4 (inference amplification), 1 (two valid histories, one present state), 6 (compound partial
    payments), 2 (historical vs current truth);
  - *larger, waiting on entities that do not exist yet:* 8 (agreement versioning) and the schema half of 7.
- **Failure semantics:** three cases left open there.
- **The closing criticism, which stands:** *"The biggest danger is not getting healthcare wrong. It is becoming the
  first place Groundwork violates its own philosophy."*

## 6. Ruling — Rob, 2026-10-08

Item 45 stays review-only. The rulings settle H1–H7 **at the design level**. They do not authorise implementation,
schema changes, migrations, or changes to 1.x.

| Point | Ruling | Boundary, as ruled |
|---|---|---|
| H1 — fix the live violations | **Approved** | Fix the four teaching-layer surfaces that price protected health spending in months towards debt freedom. Add regression gates covering the Budget page, the monthly report, the dashboard and the Ledger. |
| H2 — protected categories, version 3 | **Approved** | Expand the list to the identified health terms and built-in categories. Test aliases, capitalisation, partial matches and false positives. A match inside an unrelated word, such as `ER` inside `water`, must not count as a valid classification. |
| H3 — health belongs in Groundwork | **Approved** | Health records, calculations and explanations belong in Groundwork. The Assistant must not become a separate health-data store or a route around Groundwork's rules. |
| H4 — medication prices | **Approved** | Only prices supported by the user's own records. No invented prices, no population averages presented as personal costs, no inferred medication expenses. Missing information stays missing. |
| H5 — first slice: HSA / FSA balances | **Approved** | Money only. No person, medication, diagnosis or other named health record. An FSA forfeiture warning must be grounded in the user's actual plan-year and forfeiture rules. Unknown terms stay explicitly unknown. |
| H6 — privacy enforcement before named health data | **Approved** | No named people, medications or diagnoses until the enforcement point covers logs, exports and backups, with release-gating tests. It applies to every relevant persistence and disclosure path, not just the main database. |
| H7 — the sequence | **Approved, with a gate between stages** | The order stands. Each stage is a separate item with its own review, authorisation and passing gates. Finishing one stage authorises nothing for the next. |

**Two qualifications, as ruled.**

1. **H1 is a correctness fix, not a health-feature dependency.**
   - The engine must not frame necessary care as money available to sacrifice for a debt-free date. The fix does not
     wait for the health module, the privacy enforcement point or the wider protected-category work.
   - Its tests check the rendered conclusions the user reads, not merely that a category is marked `protected`. A
     flag that fails to change the user-facing conclusion does not satisfy the rule.
2. **H5 must not quietly implement H7's plan-year tracking.**
   - The HSA / FSA slice records the money and explains what is known.
   - A forfeiture warning needs reliable plan-year, deadline and forfeiture information. Without it, Groundwork says
     it cannot determine whether money is at risk, rather than manufacture a warning.

**H7's sequence, as ruled:**
1. the privacy enforcement point;
2. plan-year and deductible tracking;
3. the health reserve;
4. the visit report and year in review;
5. named people;
6. the bill that lands;
7. collections, last.

Each item establishes its own scope and unresolved decisions before code is authorised. Named people stays behind H6's
completed privacy gate.

**What this item keeps apart.**
- **Findings confirmed against the code:** section 2 (Findings A and B), measured on master `c32a083`.
- **Design decisions approved here:** H1–H7, with the boundaries above.
- **Work authorised:** none. Each piece, starting with H1, needs its own item and go-ahead.

## 7. Open design questions recorded 2026-10-09 (no code, no authorisation)

Recorded after a review of the 2026-10-08 ruling. That review found the ruling already separated design approval from
authorisation (§6), already kept H1 and H2 apart, and already ruled H5's unknown-terms case and H7's gates. It also
found two requirements not yet written down precisely enough to stop a later build from meeting the wording and
missing the intent.

**Verified against the repository** (not a narrative summary):
- `dc004e3`: the design-level ruling.
- Item 46 (H1): `cc37853`, accepted, gate 2532 / 0.
- Item 47 (H2): `e9d6d95`, accepted at `e6178be`, gate 2566 / 0.
- `8fafb95` (this review) contained this document **and one `BUILD_QUEUE.md` row**. Rob was told, and said to push it as
  is.

**H4 — Evidence scope for medication-cost claims (open).** Before designing this slice, define which claims each type
of user record can support. A recorded pharmacy payment establishes the recorded payment (for example, $25 paid on a
date). It does not establish:
- the medication's regular price;
- the next refill's cost;
- the out-of-pocket cost after an insurance or plan change.

Each displayed claim must be supported by evidence sufficient for that specific claim, with the source and relevant
date of each amount preserved. No claim may be extended beyond what its evidence establishes. This is the existing
per-figure discipline (R8; item 60 I3), not a new mechanism.

**H6 — Privacy enforcement inventory (open).** Before declaring the privacy enforcement point complete, establish an
inventory of the relevant data **flows and sinks**: logs, exports, backups, diagnostics, model context, and the AI log
introduced by item 62. For each applicable path, define:
1. what data can reach it, including **derived** health-sensitive information, not only explicitly named health
   records (a record without a name can still disclose through an associated transaction or an inference);
2. what may be retained, exported or disclosed;
3. what enforcement prevents prohibited data from crossing the boundary;
4. which test demonstrates that enforcement works.

Establish the inventory's completeness criteria before treating the gate as satisfied. This does not require every
conceivable path to be built or investigated now. The completeness criteria must be **verifiable**, not a statement in a document:
- the design specifies how the inventory is reconciled against the actual code paths and relevant dependencies, so a
  new logging or export path cannot silently escape it;
- item 62's AI log is an explicit **test case**, not only a mention.

Recording this requirement does not satisfy it. H4 and H6 each need their own design work and acceptance gate when
their slices are opened.

**Status:** open design questions only. No code, schema change, migration or implementation authorisation follows from
this section. Each is taken up when its slice is opened.

**Decision, 2026-10-09:**
- **H6:** the requirements above are accepted as design requirements, and **the gate remains open**. H6 is complete
  only after its design is approved, its implementation is separately authorised, and its acceptance tests pass. The
  tests must cover the inventory, the reconciliation method, each path's boundary and enforcement, and item 62's AI
  log as a regression case.
- **H4:** remains an open design question.

Item 57's work is separate and does not affect either.

## 8. Q6 and Q7 ruled — Rob, 2026-10-17

**Q6 — Approved.** Groundwork states what the available evidence does and does not establish. It does not direct
the user to call someone, and it does not suggest an action as the default. It may name the party a question relates
to only when the records establish that relationship.
Example: *"The bill doesn't show whether financial assistance was applied."*

**Q7 — Approved.** The card-free date is the projected date when the included credit-card balances reach zero. It is
labelled **"card balances only"** and follows the user's existing reserve choice and payoff rules (item 90). The
definition is not reopened for another design pass.

**Still open, for stage 6 (item 94):** a separate all-obligations date: what it includes, what evidence supports it,
and what Groundwork says when it can't be calculated reliably.

**Sequence, as ruled:**
- Item 93 (bank-side record creation, the general import model) is opened ahead of stage 6.
- Item 94 (the bill that lands) depends on item 93.
- No implementation until each design is reviewed and separately authorised.
