# Item 49 — Paying for a trip by card: what it would take, and what it would cost

Opened 2026-10-08 (Rob: *"since we are teaching and learning we should offer how are you looking to pay for this trip
we should offer the available credit option and if they select that it should bring in a drop down menu to allow the
user to select a … credit card. Then we can show the user available payment options that the user could do with their
current payments how much the user has left in their monthly finances and a good percentage for the user to save. We
are not saying don't do this but if you do this then here is what you need to do to pay this off and how much it will
cost over the time that it will take you to pay it off."*). **ACCEPTED and CLOSED (Rob, 2026-10-08: "I accept items 47, 48 and 49"), gate 2566 / 0.** **RULED 2026-10-08 (Rob: "approve R1–R7 as recommended").** R5 is the user's own savings rate from the record, or a rate they pick, labelled as theirs: no outside guideline, no percentage called good. **BUILT 2026-10-08 (Rob: "build item 49")**: `core/trip_card.py` (the rows, the plan at current payments, the assumptions), `GET /api/trip/cards` and `GET /api/trip/card-plan`, the third option and its renderer in `app.js`, `s161` end to end; the teaching layer's save line now applies to *Save for it* only. Master only: a new
teaching feature.

## 1. What exists (measured 2026-10-08)

- **"How will you pay?"** offers *Pay now* (this month's surplus after debt payments) and *Save for it* (that surplus
  until the total is reached, with a ready-by date) (`_renderFundingDetail`).
- **The record holds, for each debt:** balance, APR, minimum payment, type (`credit`, mortgage, …), and *credit
  limit*. The limit is optional, so available credit (limit minus balance) is known only when the user entered a
  limit.
- **The engine already prices a one-time cost** against the whole payoff plan (`decision_impact`, Pillar 1). That is
  how the trip planner has said what a trip costs in months.
- **The monthly surplus after debt payments** is already on the page (*"Monthly surplus · after debt payment"*).

## 2. What it would show

A third option, **Put it on a card**. Choosing it opens a list of the user's credit cards, each shown as: *name ·
balance · APR · available credit* (or *"limit not entered"*). With a card chosen, three sections follow.

**A. Whether it fits:** *"The trip is $2,140.00. Visa has $3,600.00 of available credit"*, or *"$1,400.00 —
$740.00 short"*, or *"Visa's limit isn't entered, so Groundwork can't tell whether it fits."*

**B. Ways to pay it off.** Each line is computed by the engine, at the card's APR, from the record. *(The figures below
are illustrative only, for a $2,140 trip at 22% APR. The engine computes the real ones.)*

| If you pay off the trip in… | Each month | Interest | Fits your surplus? |
|---|---|---|---|
| this statement (in full by the due date) | $2,140.00 once | see R4 | $X left this month |
| 3 months | $630.84/mo | $47.32 | yes, $310/mo left |
| 6 months | $321.73/mo | $68.43 | yes |
| 12 months | $167.39/mo | $146.86 | yes |
| at your current payments only | — | $412.00 over 31 months | — |

The last row is *"at your current payments"*: the card's balance with the trip added, paid at what the plan pays now.
It says how much longer the card, and the debt-free date, take, and the interest that adds.

**C. Your month:**
- what is left after debt payments today, and after the chosen payoff;
- the savings line (R5).

**The tone, as Rob put it:** *"We are not saying don't do this."* Every sentence is conditional (*"if you put it on
Visa and pay $630.84 a month, it's paid off in March and costs $47.32 in interest"*). There is no verdict and no
recommendation of which row to pick.

## 3. Points for ruling

**R1. The option and the list.**
- *Put it on a card* sits beside *Pay now* and *Save for it*.
- The list holds active debts of type `credit`. Loans, mortgages and leases are not places to put a trip.
- Available credit is shown only when a limit is entered; otherwise it says so.

*Recommended.*

**R2. The payoff rows** are 3, 6 and 12 months, plus *at your current payments*. Each is computed by the engine from
the card's APR, balance and the trip total, and shows its working: APR, months, payment and interest, per the
transparency standard. *Recommended.* (Other periods are a small change.)

**R3. Fitting the surplus.** Each row says whether its monthly payment fits the surplus after debt payments, as a
fact: *"$310/mo left"*, or *"$187/mo more than your surplus"*. It is never *"you can afford"* or *"you can't"*.
*Recommended.*

**R4. Interest assumptions are named, not hidden.** Two facts aren't in the record.
- **The grace period:** most cards charge no interest on a purchase paid in full by the statement due date, but the
  record doesn't say whether this card does. The *this statement* row says: *"No interest if your card has a grace
  period and you pay $2,140.00 in full by the due date — check your card's terms."*
- **A 0% or promotional rate:** if the user knows the card has one, they can say so. Otherwise the card's recorded
  APR is used, and named as the assumption.

*Recommended.* (Under item 39 U7, an assumption is shown as an assumption.)

**R5. "A good percentage to save."** This is the one point where the request reaches for a norm, and Groundwork's
rules don't allow a verdict about what is *good*. The recommended shape:
- **When the record shows a savings habit,** use the user's own rate: *"You've put 8% of income into savings the
  last 6 months; after this trip's payment that would be 3%."*
- **When it doesn't,** the user picks the rate to plan with (*5 / 10 / 15 / 20%*), and the line says it is their
  pick: *"At the 10% you chose: $X/mo, leaving $Y."*
- No percentage is ever called good, right or recommended.

*Recommended.* (The alternative, a published guideline such as *"many planners suggest 10–20%"*, names an outside
norm. It would be stated as the source's claim, never Groundwork's. That is your call.)

**R6. Nothing is saved unless the user saves the trip.**
- Choosing a card writes nothing, and nothing about the choice persists or is learned from it (no-silent-learning).
- Saving the trip budget keeps the chosen funding with it.

*Recommended.*

**R7. Works with AI off** (A10): every figure is the engine's, and the AI only narrates if it is on. Master only.
Gate: render-level checks, the same discipline as item 46. *Recommended.*

## 4. Not decided here

- Moving the trip to a different card, or comparing two cards side by side (a later step if wanted).
- Balance transfers, cash advances and loans: out of scope.
