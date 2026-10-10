# Item 73 — Before You Buy, with the agent

Opened 2026-10-10. Rob: *"while we are utilizing the agent in the program how would you improve BYB with the agent.
You can offer any idea not the idea that you think I would like."* Then, on the eight ideas offered: *"open it as an
item with #1 through #8 I like this."*

**Points Y1–Y10 for ruling. No code yet.**

## 1. What is true today (measured 2026-10-10, master + the unpushed item 71 amendment)

- **Before You Buy is a form the person opens on purpose.**
  - It takes a type, a name, a monthly cost, and optionally a budget line it replaces.
  - It simulates debt-to-income before and after, the payoff date and "what's left".
  - The person chooses commit, track or walk away.
  - Decisions are logged (`byb_purchase_decision`) and read back as Pillar 5's memory, which includes estimate bias:
    how far estimates were from what the purchase really cost.
- **Most purchases never pass through it.** Nothing brings a purchase to Before You Buy unless the person starts
  there.
- **Pieces that already exist and are not connected to it:**
  - `detect_recurring_patterns`: three or more consistent charges from a merchant;
  - `large_charge_lesson`: the recent charge that moved the payoff date most;
  - item 68's bill readings (insurance, utilities);
  - item 67's balance fetch;
  - item 50's charge matching for bookings;
  - item 60's document reader with its number check;
  - item 44's read of a named price on a page the person opened;
  - the savings goals (sinking funds);
  - the EIA fuel prices.
- **The rules this must keep:**
  - AP6: the engines compute; the model explains.
  - AP7 / TM2: the person starts every outside action, and nothing is scheduled.
  - TM4 / TM5: nothing is inferred from usage or from purchases about a person's state or life.
  - TM6: no manipulative mechanics.
  - TM1: Groundwork never pays.
  - RG1–RG3: every claim has evidence.
  - The transparency standard and teach the question: options and trade-offs, never verdicts.
  - A10: everything works with AI off.

## 2. Points for ruling

**Y1. Purchases that never came through Before You Buy are brought to it, from the record.** *(idea 1)*
- When an import shows a **new repeating charge** (a subscription, a financing or lease payment, found by the
  existing recurring detection), Groundwork offers on that charge: *"New: $14.99 a month to Peacock since Sept 3.
  Here's what it does to your plan."*
- A **charge that moved the payoff date a month or more** (the existing large-charge rule) gets the same offer.
- Opening the offer shows the Before You Buy result as if it had been asked beforehand: what's left, payoff date,
  goals.
- The person can record it as a decision ("I meant to", "I'll cancel it"), which is their statement. They can also
  dismiss it, and a dismissed charge is never offered again.
- Nothing is inferred about why the purchase was made (TM5). It is offered once per charge, never as a streak or a
  count (TM6).

*Recommended. First.*

**Y2. Trials and return windows, read from the receipt.** *(idea 2)*
- The person drops or pastes a confirmation, using item 60's reader.
- Groundwork pulls out the dates it states: a free trial's end and the price after it, a return or cancel-by date.
  Every figure and date must be in the document.
- These are shown on the dashboard's upcoming list from a week before, with the receipt's own words.
- Groundwork never cancels or returns anything (TM1 in spirit: the person acts). Nothing is fetched; the receipt
  stays where the person put it (item 20's custody).

*Recommended.*

**Y3. The full cost, built from what Groundwork knows, each part with its source.** *(idea 3)*
- **A car:** the payment, plus insurance from the person's latest insurance bill reading or a figure they enter,
  fuel from the EIA price, their mpg and their typical miles, and registration as they enter it.
- **A phone on a plan:** the device payment plus the plan's change.
- **An annual charge:** shown both monthly and yearly.
- A part with no source is left out and labelled, never guessed (the item 59 rule).

*Recommended.*

**Y4. A financing offer, read and compared with the person's own debt.** *(idea 4)*
- The person pastes or opens the offer. Groundwork reads the APR, term, fees and **deferred-interest terms**,
  checking each figure against the text.
- It then shows side by side: paying cash, financing, and putting the same money on the person's existing debts
  (for example: "your Capital One balance costs 24.99%; this loan is 6.9%").
- A deferred-interest clause is shown in its own words, with what it would cost if the balance isn't cleared in
  time.

*Recommended.*

**Y5. This week, not just this month.** *(idea 5)*
- "Can it be paid now" uses the checking balance as of its last fetch (shown with its date), minus the person's
  buffer (item 68), minus the bills due before the next expected paycheck (bill readings and budget due days; the
  paycheck from item 71's per-payer schedule).
- *"After AEP ($210) and the Ford lease ($258) on the 14th, you're $638 above your buffer until the 17th."*
- When the balance is older than a day, it says so and offers *Get my accounts*; it never fetches by itself (AP7).

*Recommended.*

**Y6. The cost in the person's own goals.** *(idea 6)*
- Each active savings goal shows its date with and without the purchase: *"Denver trip fund: May → July."*
- Arithmetic only, with the goal's own contribution rule.

*Recommended.*

**Y7. After a commit, the record closes the loop.** *(idea 7)*
- The real charge is matched on the person's yes, the item 50 way. A later change in the amount is shown as a fact:
  *"you committed at $13.89; it has been $15.49 since August."*
- For a car or other purchase with ongoing costs, the estimate is shown against the real charges in its
  categories after 3 and 6 months.
- These feed estimate bias, which then rests on real charges rather than one comparison.

*Recommended.*

**Y8. "Check the price again" for a tracked item, only when the person taps it.** *(idea 8)*
- The product page the person saved is opened in Groundwork's window, and the named price is read, the item 44 way
  (confirmed, named as the site's).
- Never on a schedule, never in the background (AP7).
- Like item 44, this needs a line in Groundwork's Terms (item 44 R6) about reading a page the person opened.

*Recommended.*

**Y9. What this item will not do (from the advice given when the ideas were offered).**
- No coupon or deal hunting.
- No impulse or mood inference from timing (TM4 / TM5).
- No forced waiting period. *Save it and decide tomorrow* stays an option, never a lock (TM6).
- No "should I buy this?" answer from the AI: the engines show the trade-off, and the person decides.

*Recommended.*

**Y10. Stages and tests.** Master only. Each stage gets its own gate and Rob's acceptance:
1. Y1, plus Y6 (the goal dates Y1's result shows).
2. Y2.
3. Y3 and Y4.
4. Y5.
5. Y7.
6. Y8, with the Terms line.

Tests for each:
- the finding it should make;
- the quiet case: an existing budget line is not "new", and a dismissed charge never comes back;
- a planted figure or date not in the document, which is dropped;
- AI off;
- no verdict words;
- Y5 with a stale balance;
- Y7's match only on the yes.

*Recommended.*
