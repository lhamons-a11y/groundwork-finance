# Item 45 — The health review: where the module stands, and the smallest first piece

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
