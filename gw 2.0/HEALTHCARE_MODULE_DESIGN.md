# Healthcare — cost tracking, medication prices, and the year that follows

**A design note for GW 2.0**

> Status: **Draft for decision. Nothing built.** Written 2026-09-05 against the real 2.0
> codebase. Companion to `GW_2.0_TEACHING_PLATFORM_BLUEPRINT.md`; constrained by
> `CALCULATION_PLACEMENT.md` (where the math lives) and `MODEL_PLACEMENT.md` (what the
> narrator may say). Research current as of this date; the three findings in §2 changed
> the shape of this proposal from what was first sketched.

---

## The question

Should Groundwork track healthcare costs — and if so, as what? A category, a planner, a
report, or a module with all three?

## The short answer

**Yes — but not as a third thing priced against the debt-free date.** Healthcare is measured
in *capacity*: what clearing the cards frees, and whether that freed money covers what care
costs. The payoff date is not the ruler here, and §0.1 is the reason.

That inverts the direction of every sentence in this module. The trip planner says *this
costs you two months*. Healthcare says *this is what being free of the cards lets you
absorb*. Same engine, opposite framing, and the second one is the true one for a cost nobody
chose.

It arrives with a precondition that is live today, a privacy exposure larger than anything
the product currently carries, and one assumption in the original sketch that cannot be
built as described. Those are §0, §3 and §2.3.

---

## §0 The blocking precondition: medical care is not a lever

**This is a defect in the shipped engine, today, independent of whether this module is ever
built.** `core/solution.py` protects a necessity floor from trim proposals. Measured:

| Category | `is_protected()` |
|---|---|
| `Groceries` | **True** |
| `Health Insurance` | **True** — but only because the string contains "insurance" |
| `Medications` | **False** |
| `Prescriptions` | **False** |
| `Pharmacy` | **False** |
| `Doctor` | **False** |
| `Therapy` | **False** |
| `Dental` | **False** |

A user who has named a budget category `Prescriptions` can, right now, be told that cutting
it by $85/month holds their debt-free date. The engine would be arithmetically correct and
the software would have suggested rationing medication to pay a credit card faster.

The floor fix is necessary and not sufficient. `is_protected` only removes a category from
*trim* proposals. Healthcare needs a stronger and separately-checkable rule:

> **Health spending is a cost the engine prices. It is never a lever the engine proposes
> moving.**

Concretely, that means it is excluded from `_trims`, from `_headroom`, from reallocation
candidates and from `_best_named` — not merely deprioritised in ranking. It also constrains
two levers that do not go through the floor at all:

- **Lever 7 (do-nothing, quantified)** must never render as "waiting costs nothing" about a
  deferred procedure. Waiting on a car purchase is free; waiting on care is a claim about
  medicine this software has no standing to make.
- **The honest no (Appendix C)** must never resolve by implying the care could be skipped.
  "Nothing holds the date" is the honest answer when nothing holds it. "Unless you skip the
  procedure" is not an answer this product gives.

**Open question 5 in §8 asks whether the floor fix ships now, ahead of the module.** It
should.

### §0.1 Necessary care is never priced in months

The floor stops the engine proposing a cut. A second rule stops it making an accusation.

> **Care the user cannot decline is never expressed as a delay to the debt-free date.**

"Your prescriptions cost you four months of freedom" is arithmetically true and is not
information. It is an accusation, and the thing it accuses is a person's need for medicine.
The platform already refuses this move elsewhere: Appendix D forbids attributing an outcome
to the market, because credit belongs to deliberate action and nothing else. The same logic
runs the other way — **blame belongs to a decision, and taking insulin is not one.**

There is a further reason it would be wrong even as arithmetic. Framing a necessity as the
cause of a delay implies a counterfactual in which the delay does not happen, and the only
version of that counterfactual is one where the care does not happen. §0's last rule already
forbids the engine from offering that path. Pricing care in months smuggles it back in as an
implication.

So the debt-free date is not the ruler for healthcare. **Capacity is**, and Pillar 4 already
computes it.

### §0.2 The words: healthcare cost, never medical debt

The vocabulary is doctrine here, not interface copy, because the wrong word does the same
work as the wrong sentence.

> **It is a healthcare cost. It is never medical debt.**

"Medical debt" frames getting well as a financial failure — a hole the person fell into and
should climb out of. That framing is wrong on the facts. Being healthy, physically and
mentally, is something people at every age should be doing, and in the United States doing it
costs money. **The cost is a fact about the system, not a verdict on the person**, and the
word "debt" quietly assigns the verdict.

This is the same rule as §0.1 arriving one layer lower. §0.1 stops the app *saying* care
delayed your freedom; §0.2 stops it *implying* the same thing through a noun.

Three consequences worth writing down:

- **Mental health is healthcare, and the floor must say so explicitly.** Therapy, counselling
  and psychiatric care are the categories a naive budgeting app is most likely to flag as
  optional spending, because they are recurring, discretionary-looking and easy to stop. They
  are the ones this floor exists to protect. The measured table above shows `Therapy` is
  unprotected today; the fix names mental health outright rather than hoping a substring
  match catches it.
- **Preventive care is a cost, not a luxury.** A physical, a cleaning, a screening. The app
  should never let these land in a discretionary bucket by default, and "at any age" is the
  operative phrase — this module is not for old people.
- **The floor list needs the vocabulary too.** `health`, `healthcare`, `medical`, `medication`,
  `prescription`, `pharmacy`, `doctor`, `dental`, `vision`, `therapy`, `counseling`,
  `psychiatry`, `mental health`, `clinic`, `hospital`. Over-protecting a near-miss costs
  nothing; under-protecting one costs the thing this whole section exists to prevent.

---

## §1 What the module is

Seven parts. Four are surfaces the user works in; two are documents they take away.

| Part | Shape | Reuses |
|---|---|---|
| 1.1 Care Planner | decision surface | `green_light`, `capacity_unlocked` (Pillar 4) |
| 1.2 Ledger categories | taxonomy + a field | existing categories, `is_protected` |
| 1.3 HSA / FSA | balances with a ceiling | sinking-fund machinery |
| 1.4 Card-free reserve | a fund with a derived target | sinking-fund machinery, `capacity_unlocked` |
| 1.5 Visit report | document | templated composition, PDF export |
| 1.6 Year in review | document | historian + the exclusion logic |
| 1.7 Named people | a label everything hangs off | new; see Open Question 4 |

### 1.1 The Care Planner

Not the trip planner's shape. The trip planner prices a chosen cost in months; this prices a
cost against **what the user can absorb**, which is Pillar 4's question and already has an
engine: `green_light` in `core/solution.py` says "you freed $180/mo — this fits," and
`capacity_unlocked` says what a balance you could now cover outright actually enables.

The output sentence is therefore of this shape:

> Clearing the Visa freed **$200/mo**. This year's out-of-pocket maximum is **$3,000**. That
> freed money covers it in **15 months** — or the **$1,240** already in the HSA covers it now.

Nothing in that is a delay, a cost in freedom, or a judgement. It is a statement about what
the user's own work has made possible, which is the whole of Appendix B.

The trip planner's levers are reallocation, timing, payoff order, trimming, substitution,
save-first and do-nothing. For care, three are forbidden by §0 and three different ones are
real:

- **The plan year is a timing lever, and it moves the cost itself.** Once the out-of-pocket
  maximum is met, further covered care in that plan year costs nothing. Care scheduled in
  December against a met OOP max and the same care in January against a fresh deductible are
  different prices for the identical procedure. **No general budgeting app models this**, and
  note what makes it admissible here: it changes what the care *costs*, not what the care
  *is*. It is a scheduling fact, not a suggestion to go without. This is the single strongest
  argument that healthcare deserves a planner rather than a category.
- **Funding source is a lever, and this is where the card is the adversary.** HSA dollars are
  pre-tax, cash is post-tax, a provider plan is often 0%, and a credit card is the most
  expensive of the four by a wide margin — it is the only one that turns a fixed cost into a
  compounding one. The engine may price all four. It should never present the card as a
  neutral fourth option, because §1.4 exists precisely to stop a medical bill from putting
  someone back on it.
- **The payment plan is a lever.** Providers routinely offer 0% instalment plans, and unlike
  most financing this one is frequently genuinely free. The session that built Pillar 3 found
  a case where financing beat cash by $438; that finding generalises here and is more often
  true — a 0% provider plan preserves the cash that keeps the card unused, which is worth
  more than the interest saved.

What the planner must never offer: a cheaper procedure, a different provider on clinical
grounds, or declining care.

### 1.2 Ledger categories

Healthcare is not one category. The tax report in §1.5 cannot be produced from a single
`Medical` bucket, because the IRS treats the pieces differently. Proposed taxonomy:

`Premiums` · `Deductible` · `Copay` · `Coinsurance` · `Prescriptions` · `Dental` · `Vision` ·
`Mental health` · `Medical devices` · `Medical travel`

**And one field that is not a category: reimbursement state.** Every health row carries one
of: `out-of-pocket`, `HSA-paid`, `FSA-paid`, `reimbursed`, `pending`. This is load-bearing —
§1.5 shows why getting it wrong produces a wrong tax number rather than a missing one.

`Medical travel` is worth calling out: mileage to and from care is deductible and is one of
the most commonly missed items. Groundwork already computes trip mileage for the trip
planner. That machinery transfers directly.

### 1.3 HSA and FSA

These map cleanly onto the existing sinking-fund machinery — a balance, a target, a pace,
and the question "how much is left," which is exactly what a fund row already answers. Three
things make them not-quite-funds, and each is a feature:

- **A statutory ceiling.** 2026: $4,400 self-only, $7,613 family, plus $1,000 catch-up at 55+.
  A fund has a target the user chose; an HSA has a ceiling the IRS chose, and over-contributing
  is penalised. The pace sentence has a second failure mode here — not just "behind" but
  "ahead of what you are allowed."
- **FSA money expires.** Use-it-or-lose-it, at plan year end. This is the cleanest proactive
  candidate in the entire product: material (real dollars), actionable (there is a lever —
  spend it), novel (it happens once a year), and **perishable**, which Appendix A's contention
  rules already handle via the position-fact/perishability clause. "You have $340 in FSA that
  expires in 31 days" is a brake worth interrupting for. It is also the rare case where the
  honest answer is genuinely urgent.
- **HSA contributions lower AGI**, which lowers the 7.5% floor in §1.5. The two documents are
  coupled, and showing that coupling is real teaching rather than trivia.

### 1.4 The card-free reserve, and what capacity is for

> The credit card is always to be paid off, and there should be enough money that it is never
> needed again. Credit cards are the enemy of financial freedom.

That is the module's organising principle, and it turns out healthcare can state it more
precisely than any other part of the app.

**The target is not a round number.** "Three to six months of expenses" is the usual advice
and it is a number somebody invented — exactly the kind of milestone `capacity_unlocked`
already refuses to celebrate. Healthcare supplies a real one: **the plan's out-of-pocket
maximum is, by definition, the most a covered year can cost.** A reserve of that size means a
bad medical year cannot put the card back to work. It is computable, it comes from the user's
own plan document, and it is the exact threshold at which the card stops being necessary.

So the module carries one fund with a derived target — the OOP max, or the family OOP max
where that applies — and it is not a savings goal in the ordinary sense. It is the number
that makes the sentence "I will never need that card again" true rather than hopeful.

**And then the capacity is for living.** Money freed by clearing balances flows in a fixed
order, and naming the order is the teaching:

1. **The card is cleared.** Nothing outranks this.
2. **The reserve is filled to the OOP max.** Now a medical year cannot undo step 1.
3. **What is left over is the life the work was for** — the trip planner, the gift budget, the
   sinking funds. Same freed number, now spendable without consequence.

Step 3 is why this module belongs in a product that also plans holidays. The freed $200/mo
that absorbs a deductible in a bad year funds a trip in a good one, and it is the same $200.
`green_light` already says "this fits" about a purchase; it should say it about a trip, and
the reason it can is that steps 1 and 2 are done.

**The tension worth naming, because the engine currently has an opinion.** Avalanche puts
every spare dollar against the highest APR, and with an empty reserve that is how a
$1,400 emergency-room bill lands on the card and erases a year of progress. Optimal payoff
and never-needing-the-card are not the same objective, and the engine today only models the
first. Whether the reserve is built *before*, *alongside*, or *after* the last balance is a
real allocation question with no obvious answer, and it is Open Question 6.

### 1.5 The visit report

A cost receipt to take to an appointment. **It is not a health record.** It carries no
symptoms, no conditions, no diagnosis, and it never suggests what to ask about clinically.

What it carries: plan-year spending to date, deductible and OOP-max progress, what this
provider has charged before, current medications with what the user has actually paid for
them, and what is still pending or unbilled.

Its purpose is narrow and honest: it lets a patient ask price questions from a position of
fact instead of guessing. "You have charged $220 for this visit type twice this year" is a
question a person can ask. It is the same move Appendix B makes everywhere else — proof, not
persuasion.

**MODEL_PLACEMENT constrains this hard.** That study measured inference-smuggling at 37–70%
across every model tested, *rising with model size*. A narrator that invents a causal claim
about a trip is a bug; one that invents a causal claim about a person's health is something
worse. **This document is templated. The narrator may phrase a sentence it is handed; it may
not generate a clinical or causal claim, ever.**

### 1.6 The year in review

The tax document, and the one with the most ways to be quietly wrong.

- **IRC §213(a):** unreimbursed medical expenses are deductible only to the extent they exceed
  **7.5% of AGI**, and only as an itemised deduction on Schedule A — so it only helps if total
  itemised deductions beat the standard deduction.
- **The exclusion is the whole risk.** Anything reimbursed by insurance, or paid from an HSA,
  FSA or HRA, must be excluded. A naive "total health spending this year" report would
  double-count HSA-paid expenses that were *already* tax-advantaged, hand the user a number
  that is too high, and contribute to a wrong filing. This is why reimbursement state in §1.2
  is a field on every row and not an afterthought.
- **Form 8889** reports HSA contributions and distributions; the deduction flows to Schedule 1
  and reduces AGI without itemising.
- **The honest no applies.** If the qualifying total does not clear the floor, the report says
  so plainly — "this does not reach the 7.5% floor on this year's numbers" — rather than
  presenting a number that implies a deduction the user cannot take.

**Not tax advice.** It produces a documented total, shows every exclusion it made and why,
and says the preparer decides. The value is the documentation, which is the part people
actually lack in April.

### 1.7 Named people

Health belongs to a person, and a household is not one person. Every medication, bill, device
link and plan-year state hangs off a **named person** the user creates — not an account, not
a login: a label inside the one household record.

That choice has consequences worth stating rather than discovering.

- **The visit report is per person.** You see one doctor about one patient, and a report
  carrying a spouse's prescriptions into that room is wrong in a way that is hard to undo.
- **The tax report is the household total.** §213 lets a taxpayer deduct what they paid for a
  spouse and dependents, so the total is the correct default and the per-person split is
  supporting detail rather than the headline.
- **Names are labels, not access control.** Anyone who opens Groundwork sees every person's
  data. For most households that is right, and a barrier between spouses would be friction
  pretending to be privacy. For some households it is not right at all, and this design does
  not solve that. It should be said plainly in the interface rather than left to be
  discovered.
- **A person is also where a device would attach**, if §2.3 ever resolves. That is the only
  reason the profile needs to exist before the device question is answered.

This partly answers Open Question 4 and sharpens the rest of it. The question was never
"whose data is this" — a label answers that. It is "who may see it," and a shared ledger
answers that for everyone at once.

---

## §2 Data sources: what exists, what doesn't

Three findings, all of which changed this design.

### 2.1 Medication pricing — there is no free patient-price API

| Source | What it is | Verdict |
|---|---|---|
| **GoodRx API v2** | `Price Compare` + `Coupon` endpoints; lowest cash/coupon price by drug or NDC, with pharmacy detail | **Real, but partnership-gated** — apply, review, then a call. A commercial dependency, and every query sends a drug name outbound. |
| **NADAC** (CMS) | Free, weekly, ~1.5M NDCs | **Wrong number.** It is what *pharmacies pay wholesale*, explicitly not the patient price. Presenting it as a price would be fabrication. |
| **RxNorm** (NIH) | Free, no auth; name ↔ RxCUI ↔ NDC, brand/generic equivalence | **Right tool, wrong job** — use it for naming, normalisation and matching, never for price. |
| **Cost Plus Drugs** | Publishes transparent prices | No official public API; scraping is fragile and a terms risk. |

So the honest position: **a comprehensive "cheapest price near you" feature cannot be built
without a commercial partner.** That leaves three options.

- **A. GoodRx partnership.** Real prices, at the cost of a commercial dependency and a
  standing outbound flow of medication names.
- **B. The user's own record.** What *you* paid, at *your* pharmacy, over time. No API, no
  partner, no data leaving the machine.
- **C. B by default, A opt-in per query.**

**Recommended: B first, and possibly only B.** It answers the question people actually have —
"am I paying more than I was, and is this pharmacy dearer than that one" — from evidence the
user already owns. That is Appendix B's proof-not-persuasion applied exactly: the record
beats the estimate. It also ships with zero new privacy surface, which §3 argues is the
binding constraint. A is a later, separable decision.

Note the phrasing constraint either way: **the price of the same prescription is a fact; a
suggestion to change pharmacies is advice, and a suggestion to change or stop a medication is
not something this product will ever say.**

### 2.2 Claims data — the right source, at a real integration cost

**CMS Blue Button 2.0** is a FHIR R4 API conforming to the CARIN Blue Button IG, serving
`ExplanationOfBenefit`, `Patient` and `Coverage` for 60M+ Medicare beneficiaries. Access is
patient-directed: OAuth 2.0 authorisation-code with mandatory PKCE, authorised by the
beneficiary at Medicare.gov. There is an open sandbox with synthetic data; production
credentials are free but require CMS approval.

This is the correct source for what care actually cost — an EOB carries the service, the
date, the provider and the amounts. And its consent model is exactly Groundwork's ethos:
patient-directed, standards-based, revocable.

Two limits. It is **Medicare only**. The CMS Interoperability and Patient Access rule pushes
the same CARIN-shaped API to Medicare Advantage, Medicaid, CHIP and exchange plans, but
commercial employer coverage is largely outside it — so a working-age user with employer
insurance may have no endpoint at all, and those that exist require per-payer registration.

**Therefore: stage it late, and design Phase 1 so it does not depend on it.** The Phase 1
substitute is PDF EOB import, which reuses the extraction machinery already built for debt
statements (`/api/debt/pdf-extract`).

### 2.3 Devices — this cannot be built as described

The original sketch was "let users add their credentials to Apple Health or Google Health."
Three problems, in increasing order of importance.

1. **There is no server-side HealthKit API.** Apple Health data is accessible only on-device,
   through a framework that requires an app running on the user's iPhone. A Windows desktop
   application cannot read Apple Health at all, with credentials or otherwise. Android's
   Health Connect is the same: on-device, local storage.
2. **Credentials are the wrong model everywhere.** These are OAuth flows. Groundwork should
   never accept a health-account password — and would refuse to, on the same grounds it
   refuses to handle any other credential.
3. **The question nobody has asked: what would this data do?** Step counts and heart rate do
   not price anything. The financially meaningful health feed is claims, prescriptions and
   receipts — §2.1 and §2.2 — not fitness telemetry. Google's cloud-side **Google Health API**
   (the former Fitbit Web API) *is* reachable via OAuth, so Fitbit-class data is technically
   available; that still does not make it useful to a cost tracker.

**Recommendation: defer device integration entirely** until someone can name a financial
question it answers. If one emerges — a chronic condition whose spending correlates with a
tracked measure, say — it arrives as a companion mobile app, which is a different product
decision than an integration.

---

## §3 Privacy: the exposure this creates

Groundwork's positioning is that the user is not the product, and the outbound-network audit
backs that claim today. Health data is where that claim is hardest to keep and most costly to
break.

**A medication list is a diagnosis in disguise.** From a list of prescriptions one can infer
HIV status, cancer treatment, psychiatric conditions, pregnancy and fertility treatment. It
is the most sensitive data the application would ever hold, and more sensitive than anything
currently in it.

HIPAA does not apply — Groundwork is not a covered entity and this is the user's own record.
That is a legal fact and not an ethical permission.

Proposed rules, written to be checkable the way the rest of the doctrine is:

1. **Health data never leaves the machine by default.** Not in telemetry, not in crash logs,
   not in an update check.
2. **Every outbound price query is per-query, explicit, and names exactly what is being sent.**
   Never batched, never background, never on a timer.
3. **The cloud model is refused for health content, even when the user has selected the cloud
   provider.** Health narration is local-only (phi3.5) or templated. This is a real rule with a
   real test: `ai_provider == 'cloud'` plus health context must return a refusal, not a
   completion.
4. **Health rows are excluded from exports unless explicitly included**, and the export says so.
5. **No silent learning, sharpened.** The existing boundary — an unsurfaced observation may
   never persist — applies with no exceptions here.
6. **Backups carry health data.** The backup folder is user-settable and may be a USB drive or
   a synced folder. Whatever this module ships, it should say that plainly at least once.

---

## §4 Where the calculations live

Per `CALCULATION_PLACEMENT.md`: anything backing a claim is Python, named, and tested.

- `core/health.py` — plan-year state: deductible met, OOP-max progress, reset date, and the
  eligibility flags per category. This is the module that makes the timing lever in §1.1 real.
- `core/health_tax.py` — the §213 total and, more importantly, the exclusion logic. This is
  the highest-risk code in the module and deserves to be alone in a file with its own tests.
- HSA/FSA state can live in `core/health.py` unless it grows; the ceiling and the expiry are
  small.
- **`core/solution.py` gains the reserve, and that is where the real work is.** The output in
  §1.1 is `green_light` and `capacity_unlocked` answering a new question — not "what does this
  cost you" but "what does your freed money now cover." Both functions already exist and both
  already carry the reserve discipline (C.5's stability floor is one month of recorded
  expenses); §1.4 replaces that invented floor with a derived one.
- **`core/consequence.py` changes only if Open Question 6 says so.** Nothing in this module
  needs a new payoff simulation — a medical cost is not priced in months (§0.1), so Pillar 1
  is not asked a new question here. But "build the reserve before the last balance is clear"
  *is* a change to how payoff is allocated, and that lands in the engine and affects every
  user. Which is why it is a question and not a decision in this document.

---

## §5 The rules, collected

Written as a list because this codebase tests its doctrine rather than describing it.

1. Never propose reducing a health category — not ranked low, excluded.
2. Never count health spending as headroom or name it as a reallocation source.
3. Never suggest changing, substituting or stopping a medication. Only the price of the same
   prescription.
4. Never state a price that was not observed in the user's record or returned by a named
   source, with the source shown.
5. Never let a model generate a causal or clinical claim about health. Templated only.
6. Never send health data to a cloud model or a third party without a per-event, explicit yes.
7. Never imply a tax outcome. Produce a total, show the exclusions, name the preparer.
8. Never treat declining care as a path, including inside an honest no.
9. Never express necessary care as a delay to the debt-free date. Healthcare is measured in
   capacity, not in months lost (§0.1).
10. Never present a credit card as a neutral way to pay for care. It is the outcome §1.4
    exists to prevent.
11. Never state that a provider will accept an offer, or assert §501(r) protections for a
    provider they do not cover. State the policy, condition it on provider type, stop.
12. Never name a payment figure the record cannot support. Below the observed-months floor,
    say the record is too thin — this number leaves the building.
13. Never let the urgent tier (§7.4) carry anything without an external deadline. One bypass
    per bill, ever, and materiality, actionability and novelty still apply.
14. Never call it medical debt — anywhere, in any surface, in any export. It is a healthcare
    cost, and the noun is doctrine (§0.2). Nor may layout say it: a healthcare cost listed
    among the credit cards has been called a debt without the word.
15. Never treat mental health as discretionary. Therapy, counselling and psychiatric care are
    on the necessity floor by name, not by substring luck.
16. Never show a serene payoff date for a deferred-interest balance. The promotional end date
    and the retroactive principal are the number that matters; the payoff date without them
    is the most dangerous figure this app could display (§7.7).
17. Never classify a lender's balance as a healthcare cost, however medical the purchase.
    Provider carries it at 0% — healthcare cost. A lender carries it — credit card.
18. Never ask again after a standing no. "The plan is fine" is a preference, not a cooldown:
    it does not expire, reset on a balance change, or return next year.
19. Never infer that preference from silence. A user who dismisses twice has dismissed twice;
    only a user who said "stop asking" has said it.

---

## §6 Staging

**Phase 1 — no network, no partner, no new privacy surface.** Categories and reimbursement
state; HSA/FSA as funds with a ceiling; the FSA expiry brake; medication prices from the
user's own record; both documents built from local data. The necessity-floor fix ships here
or earlier.

*This phase delivers most of the user value with none of the exposure.* That is deliberate,
and it is the argument for building it first rather than last.

**Phase 2 — the plan year and the bill that lands.** PDF EOB import on the existing
extraction machinery, the plan-year state machine, and the Care Planner with its three levers.
§7's sequence belongs here too and needs nothing from the network: the alarm is derived from
balances the app already holds, the sustainable payment comes from the historian, and the
agreed plan writes to structures that already exist once a budget item can carry a term.

**Phase 3 — gated, optional.** Blue Button 2.0 for Medicare users, behind its own consent.
GoodRx if the partnership is pursued.

**Phase 4 — deferred pending a reason.** Devices.

---

## §7 The bill that lands

A hospital bill arrives for $4,000. The user cannot cover it, or covering it empties the
reserve §1.4 exists to protect. This is the sequence that follows, and it is the part of the
module that strains the platform's rules hardest. Each strain is named below with what it
costs to allow it.

### 7.1 The alarm, and why the threshold is not a number

"$4,000" is not the trigger. A $4,000 bill against $40,000 of liquid savings is an expense; a
$900 bill against $600 is an emergency. **The trigger is the relationship to the reserve, not
the size of the bill**, and every term in it already exists:

> A bill trips the alarm when paying it in full would take liquid savings below the §1.4
> reserve floor — or when it cannot be paid in full at all.

That derives from the user's own plan and their own balances. No invented threshold, no
"large bill" constant to argue about, and it scales with a household instead of against it.

### 7.2 The strain: this is the first time the app tells someone to do something

Everything else in this platform shows a consequence and stops. Here the useful sentence is
"call the billing department, and here is what to offer." That is an instruction, and the
no-prescription rule exists for good reason.

**The adjustment is a distinction, not an exception.** The rule forbids claims about the
user's life that the app cannot verify — "cut your dining" assumes dining is flexible for this
person, and inventing that is the fabrication R8 exists to stop. A hospital's billing
obligations are not a claim about the user at all. They are a checkable fact about the world:

- **IRC §501(r)(4) requires** every non-profit hospital to maintain a written, published
  Financial Assistance Policy covering all emergency and medically necessary care, free to
  download, with the application form and a plain-language summary.
- A patient has **at least 240 days** to apply.
- The hospital is **barred from lawsuits, wage garnishment and credit reporting for at least
  120 days**, and must make a reasonable effort to determine eligibility before pursuing
  collections.
- Once a patient qualifies, they **cannot be charged more than the "amounts generally billed"**
  to insured patients.

So the sentence splits into three parts with three different warrants, and the split is what
keeps it honest:

| Part | Warrant | Example |
|---|---|---|
| What is available | federal law, cited | "Non-profit hospitals must have a financial assistance policy. You have at least 240 days to apply." |
| What the record shows | the user's own history | "Your leanest month in the last 14 left $210 after everything." |
| The arithmetic between them | derived, shown | "$150/month clears this in 27 months and stays inside that." |

**The app never says "you should call."** It says what exists, what the record can sustain,
and what the two make possible. The user decides, which is where every other lever in this
platform leaves them.

**Two things it must never do.** It must not assert those protections for a for-profit or
government provider, where §501(r) does not apply the same way — so provider type is a field,
and the fact is conditional on it. And it must never state or imply that the provider will
accept an offer. What the law guarantees is a policy and a process, not a number.

### 7.3 The strain: the offered amount is a number the app invented

The original sketch was "take what the historian shows is left over each month and divide."
The divisor is the danger. This project has already been burned twice by a heuristic that
looked obvious and turned out to be a coin flip against trend-free data, and a fabricated
payment figure would be worse than either — it is a number a person repeats out loud to a
hospital.

**The adjustment: derive it, and refuse when the record cannot.**

- **Use the leanest month, not the average.** A payment plan has to survive the worst month on
  record, not the typical one — an average-month payment fails in the month the car breaks,
  and failing a medical payment plan is how the bill reaches collections after all.
- **Apply the existing floors.** C.5's stability floor and §1.4's reserve floor both already
  constrain what may be proposed; the payment may not push either below its line.
- **Require enough record to speak.** Below `MIN_MONTHS_OBSERVED` there is no leanest month
  worth the name. Appendix C.7 already covers this: say the record is too thin to name a
  figure rather than naming one anyway. **An honest null is worth more than a number here**,
  because this number leaves the building.
- **Offer the curve, not a point.** Payment and term are two unknowns in one equation. Show
  three durations with their payments, mark which the record sustains, and let the person
  choose. That is E.4's "show the paths with their costs" applied to a negotiation.

### 7.4 The strain: the alarm must not be silenced by the frequency budget

Appendix A caps interruptions — one per session, two brakes a week. A bill that will reach
collections is not a spending observation, and suppressing it because a card was already shown
this session would be the gauntlet defeating its own purpose.

**The adjustment is a narrow tier with a checkable definition**, because "urgent" is a door
every product eventually props open:

> An event may bypass the **frequency budget** — and only the frequency budget — when it has a
> deadline that is not ours, and a consequence that compounds if the deadline passes.

A bill with a due date qualifies. A spending pattern never does. A trophy never does. Note
what the tier does *not* get: it still passes materiality, actionability and novelty, and it
is capped at one bypass per distinct bill, ever, so a single bill cannot become a nag.

**The dial still silences it, and that needs no exception.** A.1 already says turning
interruptions down hides nothing, because every insight remains on the page it belongs to. An
alarm the user has switched off still sits on the bill, which is where they will look.

### 7.5 Recording what was agreed

The user offers $150. The hospital says $175, or $125, or yes. That outcome is recorded — the
offer, the agreement, the term — and three rules apply immediately.

- It is **the historian's**, not a model's. A recorded outcome is a fact about what happened.
- **No rate below the threshold.** The same rule BYB's memory follows: a count is a receipt at
  any size, a *rate* needs enough decisions to be one. "Two of your three offers were accepted"
  is a pattern invented from noise.
- **Never a prediction.** "Hospitals accept about 80% of offers" is exactly the inference from
  engagement data that the blueprint's §9 forbids, and it would be worse here — it would set an expectation
  before a phone call that the app has no standing to set.

### 7.6 The strain: the app writes to the budget

An agreed plan is $175/month for 24 months, and it belongs in the budget for exactly 24
months. Two problems, one shallow and one deep.

**Shallow: budget items have no term.** They are ongoing. This needs an end month, which is a
schema addition rather than a design question.

**Deep: what is an agreed plan, and what is it called?** It is a fixed obligation, with a term,
at 0%. Recorded as an ordinary expense it is invisible to the payoff engine and the date the
app shows is wrong. Given to the engine it is priced correctly, and the engine's own ranking
puts a 0% obligation last without being told to.

**So: the engine sees it; the interface never calls it debt.** These are separable and keeping
them separate is the whole of §0.2. Internally it is a term obligation at 0%, flagged
protected, which buys a true date and correct ordering for free while §0 keeps it off the
lever list — never trimmed, never headroom, never a reallocation source. On screen it is a
**Healthcare Cost**, it lives on the healthcare page, and it appears in the payoff view under
its own heading rather than mixed in among the cards.

That last part matters more than it looks. A label can say "Healthcare Cost" while the page
around it says *debt* by placement — a plan listed between a Visa and a store card has been
called a debt without a word being used. Its own section, with the cards' section left alone,
is what makes the vocabulary rule real rather than cosmetic.

**And the date needs a decision, which is Open Question 7.** Adding the obligation moves the
payoff date later. §0.1 governs how that may be said — *"your plan now carries $175/mo it did
not"* is a fact; *"your hospital stay cost you six months of freedom"* is the accusation this
document exists to rule out. But there is a further question underneath, and it follows from
the framing that credit cards are the adversary: perhaps the headline figure should be the
**card-free date**, with a second, quieter figure for when every obligation clears. Then a
healthcare cost never moves the number that measures the fight against the cards, because it
was never part of that fight.

### 7.7 The end date, and where extra money goes

Two things follow from treating a healthcare cost the way a car loan is treated, and one
important thing does not.

**It shows its own end date, and the date is exact.** A true provider plan carries no
interest, so the arithmetic is balance ÷ payment and nothing else: *"$175/month — paid off
March 2028."* That is not a projection and does not need a confidence qualifier, which makes
it rarer than almost any other date in this app.

It is also the right number psychologically, and for a reason §0.1 already argued. "This cost
you six months of freedom" is a verdict; **"this ends in March 2028" is a horizon.** Same
obligation, same arithmetic, opposite thing done to the person reading it.

**Extra money can go to either, and the two answers buy different things.** As the cards come
down, a user with room to send more should be offered the choice — and the honest presentation
is not a recommendation but the pair of consequences, because they are not the same *kind* of
consequence:

| Extra $200 goes to | What it buys |
|---|---|
| The Visa (22%) | **$310 saved in interest.** Money that would otherwise be gone. |
| The healthcare cost (0%) | **Four months earlier, and $175/mo freed four months sooner.** No money saved — none was being lost. |

That distinction is the teaching, and it must not be blurred. At 0% an extra payment saves
nothing, because nothing was being taken; it buys an earlier end and earlier capacity. Both
are legitimate reasons to choose it, and neither is the interest saving that the card offers.

The app shows both and picks neither — E.4's rule, that the paths are shown with their costs
and the choice is the user's. The doctrine that credit cards are the adversary does not need
to be argued in a sentence here; at 22% against 0% the interest column argues it. And the
existing floors still apply: money sent to either may not take the reserve below §1.4's line.

**The offer has three answers, and the third one is permanent.**

Offering to send more is the app asking a question, and a question asked twice after a clear
answer is a nag. So:

1. **Yes** — send this much, to this obligation.
2. **Not now.** An ordinary dismissal, which A.4 already handles: sixty days of quiet, and
   twice in a category drops the category to passive for good.
3. **No. The plan is fine. Not a penny more.** A *standing* answer, stored against that
   obligation, honoured until the user themselves changes it. Not a cooldown — an end to the
   question. It does not expire, it does not reset when the balance changes, and it does not
   return next January.

The third answer is a preference, not a dismissal, and the distinction matters more than it
looks. **Inferring from repeated dismissals that someone wants to be left alone would be
learning from silence, which the platform forbids. Recording an explicit "don't ask again" is
honouring something the user actually said**, which the platform requires. Same silence,
opposite provenance — one is inferred, the other is stated.

And A.1 still holds: switching the question off hides nothing. The option to pay extra remains
on the healthcare page for anyone who goes looking for it. What ends is the asking.

There is a reason to want this beyond quiet. A payment plan someone can meet every month
without thinking about it is doing its job, and a person who has decided that $175/month is
what they can live with should not be re-litigated every time their balance falls.
"Fine as it is" is a legitimate financial position and the app should be able to hear it.

**What must not follow: the same treatment for a medical credit card.**

A provider payment plan and a medical credit card look alike on a statement and are not the
same instrument. Deferred-interest promotional financing — CareCredit and its relatives — is
the common form, and its mechanics are the reason this subsection exists:

- Interest **accrues from the purchase date**, not from the end of the promotion.
- If the balance is not paid **in full** by the promotional end date, that interest is charged
  **retroactively on the entire original purchase**, at a standard APR around 30%.
- Retroactively on the *original* amount — not the remaining balance. **Paying off 90% and
  missing the date by a month is very nearly as expensive as having paid nothing.**

So a serene *"paid off March 2028"* on one of these would be the most dangerous number this
application has ever displayed. It would be arithmetically defensible and would hide a cliff.

**The classification rule, therefore:**

> An obligation is a **healthcare cost** when the provider carries it at no interest. It is a
> **credit card** when a lender carries it, whatever the marketing calls it, and however
> medical the purchase was.

A deferred-interest plan is the adversary, is grouped with the cards, and is subject to
everything §0.2 does *not* protect — because §0.2 protects care from being called a failure,
not lenders from being called lenders. It also qualifies for §7.4's urgent tier on the
definition already written: an external deadline whose consequence compounds if it passes.
Few things in personal finance fit that sentence better.

The engine therefore needs three obligation types, not two: a card, a provider plan at 0% with
a term, and a promotional balance with a **cliff date and a retroactive principal**. The third
is new work and the reason it is worth doing is that it is the one people are quietly hurt by.

---

## §8 Open questions — yours to answer

Named rather than assumed, and none of them defaulted.

1. **Groundwork or Assistant?** The historian/assistant split puts the long record on one side
   and the working surfaces on the other. Healthcare has both: a planner that belongs in
   Groundwork and a multi-year record that looks a lot like the Assistant's territory.

2. **Does medication pricing ship at all?** §2.1 says it is either a commercial partnership or
   the user's own record. If the answer is "own record only," the feature is smaller and more
   honest than the original sketch — worth confirming that is acceptable rather than assuming
   it.

3. **Does the visit report leave the machine?** Printing is clearly fine. Emailing it to a
   provider is a different decision with a different privacy answer.

4. **Whose health is it, in a joint account?** This is the sharpest one. A joint account has no
   author, and visibility belongs per-account — but a spouse's medication list inside a shared
   ledger is a materially different problem from a shared grocery total, and the existing
   per-account visibility model may not be enough.

5. **Does the necessity-floor fix ship now?** It is a live defect in shipped code, it is a
   handful of lines, and it does not depend on any of the above.

6. **Does the app say "call them"?** §7.2 argues the sentence is admissible because a
   hospital's obligations are a fact about the world rather than a claim about the user's
   life, and that the three parts must stay visibly separate. It is still the first time this
   product tells someone to pick up a phone. If that line should not be crossed at all, the
   feature degrades to stating the law and the leanest month and letting the user draw the
   conclusion — which is weaker, and might be right.

7. **Card-free date, or all-obligations date?** *Mostly settled: it is never called debt
   (§0.2), the engine prices it, it gets its own section rather than a line among the cards,
   and it carries its own exact end date (§7.7).* What is left is the headline figure. If credit cards are the adversary, the number that
   measures that fight is the card-free date — and a healthcare cost should not move it. A
   second figure covers when everything clears. Two numbers is one more than this app shows
   today, and that is the cost of the split.

8. **Are names enough?** §1.7 makes a person a label, not an account, so everyone with the app
   open sees everyone's medications. That is right for most households and wrong for some, and
   the design does not currently distinguish them.

9. **Reserve before, alongside, or after the last balance?** Avalanche says every spare dollar
   goes to the highest APR, and with an empty reserve that is how one emergency-room bill
   lands back on the card and erases a year. "Pay it off" and "never need it again" are two
   objectives and the engine models only the first. This is the one open question that changes
   `core/consequence.py`'s behaviour rather than adding to it, and it affects every user, not
   only those who use this module.
