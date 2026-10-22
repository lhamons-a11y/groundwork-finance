# Item 107 — The same charge paid from two accounts in the same month

Opened 2026-10-21. Rob:

> *"Netflix $17.99 from Checking Account and Netflix $17.99 from Harbor Visa in the same month ... the user may know
> this because they are funding one for another person but I think those things we should alert the user."*

**No code.** D1-D12 for ruling.

---

## 1. What is true today (measured 2026-10-21 on master `52275e6`)

- **Recurring charges are grouped by payee, across every account.**
  - `detect_recurring_patterns` (`server.py:2170-2206`) reads debits for 6 months and groups them by the exact
    `Transaction.merchant` string, with no account in the key (`server.py:2184-2186`).
  - A payee with 3+ charges, each within 5% of their average, is a pattern. One whose name is an active budget item
    is skipped (`server.py:2188-2194`).
  - So when two accounts pay Netflix under the same payee string, the two merge into one pattern with twice the
    count, and nothing says two accounts pay it.
  - When the two banks spell it differently (`NETFLIX.COM` and `Netflix`), they are two unrelated patterns, and
    nothing connects them.
- **Lever 4 adds them together without saying so.** `trim_candidates` (`server.py:2287-2330`) divides every charge
  for the payee by the months it spans. Two accounts at $17.99 give one line, *Netflix $31.30 a month*, with no
  account named.
- **Before You Buy's "new recurring" offer loses it.** `new_recurring` (`core/byb_offer.py:30-62`) also groups by
  payee only, then needs a monthly or weekly gap between charges. Measured with the function itself:
  - $17.99 on the 15th of July to October from one account: offered, *every month, $17.99*;
  - the same, plus $17.99 on the 28th from a second account: **nothing offered**. The gaps of 13 and 18 days are
    neither monthly nor weekly (`core/byb_offer.py:22-23, 50-57`).
- **Price changes read the wrong schedule.** `rhythm` (`core/price_change.py:39-48`), given both accounts' dates
  together, reads charges on the 9th and the 22nd as *"every two weeks"*, and charges on the 3rd and the 28th as no
  schedule at all. Each account alone reads *monthly*.
- **Ask why's duplicate check looks inside one account only.** `check_duplicates` (`core/ask_why.py:276-287`) groups
  by account, date, amount, direction and description. Its card says *"Suspected, not confirmed: two identical real
  charges look exactly like this"*, and its `cannot` line says it can't tell an import twice from a real second
  charge (`core/ask_why.py:48-51`). Two accounts paying one payee, on different days, are never in one group.
  `check_own_transfers` (`:290-305`) pairs a deposit with a debit, never two debits.
- **What the person said about a recurring charge has no account in it.**
  - The feedback route (`server.py:6252-6273`) logs `recurring_pattern_confirm` / `recurring_pattern_reject` to the
    Historian with `{'merchant': ...}` and the average only (`core/database.py:498-499`).
  - Confirmed recurring bills are kept in the setting `recurring_items_json`, read at `server.py:3270, 3320, 4215,
    4393` and `static/js/app.js:14522`. None of these carry an account.
- **Payee matching that already exists.**
  - `_norm_payee` (`server.py:3256-3257`) keeps letters and digits, lower-cased.
  - `_price_line` (`server.py:3263-3266`) treats two names as one payee when either contains the other and both are
    4+ characters. So *netflixcom* and *netflix* match.
  - The Ledger's own key is merchant, else description, trimmed and lower-cased (`static/js/app.js:5036`,
    `core/new_vendor.py:20-22`).
- **What a card payment looks like.**
  - A payment from checking to a card is a debit on checking. `_isSpend` (`static/js/app.js:252-264`) leaves out
    Transfer-typed categories.
  - The sample household files card payments under the first of *Loan Payment / Credit Card Payment / Debt Payment
    / Transfer* that exists (`core/sample_household.py:123, 135`).
  - A store card is where a name can collide: a $17.99 *Target* purchase on a Target card, and *TARGET CARD PMT*
    $17.99 from checking, share the payee *target*.
- **Each row also carries** `card_last4` and `pending` (`core/database.py:111, 115`). So two cards on one account,
  and a pending line, can be told apart.
- **Needs attention is a closed list.** It has six kinds (`static/js/teaching/attention.js:17-19`), and *"a new kind
  is a ruled addition, never something code invents"* (`:9-12`). Each item shows a fact, a source line, an action
  and Dismiss (`static/js/teaching/dashboard.js:155-196`).
- **Speaking first is governed.** Appendix A's gauntlet is built in `core/proactive.py`. Materiality is 5% of the
  monthly budget, or two weeks on the payoff date (`core/proactive.py:48-49, 66-72`). $17.99 against a $5,000 budget is
  0.36%, so a typical subscription can never be promoted to an interruption.
- **The Morgans show none today.**
  - StreamBox $15.49 and TuneFlow $10.99 are on the Cashback Visa only (`core/sample_household.py:137-138`).
  - Everyday Checking pays the Visa $600 a month under the card-payment category (`:135`).
  - s249 pins the working picture's Streaming Video readings (`smoke_sections/s249_sample_household.py:103-104`).

## 2. What it would do

Groundwork would say, in fixed words with the rows behind them:

- **the fact:** the same payee, at the same amount, was paid from two of the person's accounts in the same month,
  more than once;
- **a source line;**
- **what it can't tell:** whether both are meant.

The fact is said on the Dashboard's Needs attention and as an Ask why check. It never calls the charge a mistake or
a duplicate, and never guesses why. The person can answer once, *"Both are meant"*, *"One of these should stop"* or
*"These aren't the same"*. The answer is kept as their own statement, added to and never overwritten, and that pair
is not raised again. Groundwork cancels nothing and moves nothing, and no total changes.

## 3. Points for ruling

**D1. The same payee.** Two rows are the same payee when their Ledger keys (merchant, else description), reduced to
letters and digits, are equal, or one contains the other and both are 4+ characters. This is the test `_price_line`
already uses, so *NETFLIX.COM* and *Netflix* match. The amount (D2) keeps *Amazon* and *Amazon Prime* apart in most
cases. Where it doesn't, the person's *"These aren't the same"* (D8) settles it for good.
- (a) contains, as above. *Recommended.*
- (b) equal keys only. Fewer false matches, but it misses the two-banks-two-spellings case, which is the common one.

**D2. The same amount.** The two charges are within 5% of each other. That is the house rule for *"the same
subscription, not shopping"* (`core/byb_offer.py:21`), and it allows for a tax line or currency rounding. If the
service changed price between the two accounts' charges (say $15.49 against $17.99), the two are outside 5% and
nothing is said. The `cannot` line names this. *Recommended.*

**D3. Different accounts, and never a card payment.** The two rows are on two different accounts, and **neither
row**:
- is in a Transfer-typed category (the `_isTransferCat` / `core/checkin._transfer_ids` test);
- is in a debt or card-payment category (Credit Card Payment, Loan Payment, Debt Payment, or one under them);
- is a deposit or refund;
- is still pending (item 93 B9).

So checking paying the Visa never pairs with a charge on the Visa, even when the store card shares the store's
name. *Recommended.*

**D4. The same month, and how many months before it is said.** The charge is on both accounts in the same calendar
month, the months the person sees on every page. The current month counts as soon as both charges are on record.
It is said from the **second** such month within the last three.

Why not the first: moving a subscription from one account to another, the most ordinary change there is, produces
exactly one month with both. That month is the last charge on the old account and the first on the new one.
"Within the last three" allows for a charge that posts on the 31st one month and the 1st the next.
- (a) the first month. Said a month sooner, but said at every card switch.
- (b) two months within the last three. *Recommended.*
- (c) three months. Quieter, but $31 more paid before anyone sees it.

A single month stays visible in Ask why (D6 b), as a single month, and nowhere else.

**D5. Each account's own charges.** The pattern is read per account, not from both accounts' charges together, so
the D1-D4 test never feeds §1's merged readings. This item doesn't change `detect_recurring_patterns`, Lever 4, the
BYB offer or `rhythm` (see §4). *Recommended.*

**D6. Where it is said.**
- **(a) Needs attention:** a seventh kind, `two_accounts`, ruled here as the closed list requires. It is passive
  under Appendix A: it is on the Dashboard the person opens, not an interruption. The action is *Show the
  charges*, which opens the Ledger filtered to that payee, both accounts.
- **(b) Ask why:** a check `two_accounts` in `CHECKS`, with `establishes` and `cannot` lines. It is reachable from
  *Why?* on a spending figure or a category, and offered to the model's routing list with AI on (item 72 stage 3).
  It lists single months too, marked *one month*.
- **(c) The Ledger:** under each of the paired rows, a small line, *"Also paid from Cashback Visa this month"*.
- **(d) A proactive card:** not proposed. See §5.

(a) + (b) *Recommended*. (c) is optional: it is the most visible place, but it is one more line on every paired
row.

**D7. The words.** Fixed words, the same with AI on or off:

> **StreamBox**: $15.49 from Everyday Checking on Oct 3 and $15.49 from Cashback Visa on Oct 9. Both accounts paid
> it in September too.
>
> *From your Ledger: the same payee at the same amount, from two of your accounts, in the same month. Groundwork
> can't tell whether both are meant.*

- It doesn't use *duplicate*, *double*, *twice by mistake*, *wasted*, *should* or *forgot*, or say why it happened.
  That keeps show-don't-scold (blueprint §3 #5) and keeps Groundwork from naming a cause it can't see (§3, the
  pattern paragraph).
- The heading is the payee. The kind's label in Needs attention is *"Paid from two accounts"*.
- No monthly or yearly "cost of the second one" is shown. That figure would assume one is unwanted.

*Recommended.*

**D8. The person's answer.** Three buttons, beside Dismiss:
- **Both are meant**, with a hint underneath: *"e.g. one is for someone else"*.
- **One of these should stop.**
- **These aren't the same.**

**How it is kept:**
- Appended to a setting `two_accounts_said_json` as `{key, payee, accounts: [id, id], amount, answer, at}`. A later
  answer is added after the first, never written over it, and the newest one counts.
- Listed in Settings with *Undo*. Undo adds a withdrawal; it removes nothing.
- Logged in the Historian as `two_accounts_answered`, with the payee key and the two account ids. It carries no
  description text, as `household_statements` doesn't.

**What happens next:**
- **Both are meant**, or **these aren't the same:** never said again for that payee and that pair of accounts. A
  third account paying it is a new pair, and is said once.
- **One of these should stop:** the item leaves Needs attention. Groundwork doesn't cancel anything; the person
  does.
  - (a) If both accounts still pay it two months after the answer, it is said **once more**, with the person's
    own words: *"You said one of these should stop. Both paid it in December."* Then never again. *Recommended.*
  - (b) Never again.
- **Dismiss** is *not now*. It hides the pair for 60 days, the A.4 cooldown. The fingerprint is the payee and the
  pair, not the month, so a new month doesn't bring it straight back.

*Recommended*, with (a).

**D9. What the answer feeds: nothing else.** *"Both are meant (one is for someone else)"* doesn't create a person, a
care-for statement, a reimbursement or a split. Facts about other people are asked, never inferred (AP4 / TM5), and
this answer doesn't say who. No answer changes:
- the budget, a total or a category;
- `recurring_items_json`;
- the recurring detection, Lever 4, BYB or price changes.

*Recommended.*

**D10. AI off changes nothing.**
- The finding, the words and the answers are the engine's and fixed. The narrator doesn't rephrase Needs attention
  items, so there's nothing to add with AI on.
- With AI on, the only difference is that the Ask box can route a question (*"am I paying for StreamBox twice?"*)
  to the `two_accounts` check.
- Nothing about it is sent anywhere.

*Recommended.*

**D11. The Morgans show one.** The sample is for review, and the item can't be reviewed on a household that never
triggers it. StreamBox $15.49 is added to Everyday Checking on the 3rd of the last two months, beside the Visa's
charge on the 9th. Then Needs attention shows the D7 item on first look.
- **The cost:** Streaming Video spending rises by $15.49 in those two months. That touches the Morgans' streaming
  budget ($27) and their *"trim by $7"* statement (`core/sample_household.py:199, 238-242`), and may move s249's
  working-picture readings (`smoke_sections/s249_sample_household.py:103-104`). It is measured at build, and s249's
  expectations change only if they move, with the change named.
- (a) StreamBox, as above. It reads as Rob's own example. *Recommended.*
- (b) A new small payee on both accounts (a cloud-storage plan in a category the picture doesn't read). It leaves
  the streaming story alone, but is less recognisable.
- (c) None.

**D12. Line and tests.** Master only. A new smoke section (s251) checks:
- **planted cases:**
  - Rob's example (two spellings, two accounts, two months) is said;
  - one month only is not said on the Dashboard, and is listed in Ask why as *one month*;
  - a card switch (last old charge and first new charge in one month) is not said;
  - checking paying the card, including the store-card name collision, is never paired;
  - a Transfer-category or pending row is never paired;
  - amounts 6% apart are not paired;
  - two cards on one account are not paired (until §4 says otherwise);
- **the answers:** each one is appended, never overwritten; the pair is not asked again; *should stop* comes back
  once after two months and then never; Undo adds a withdrawal; Dismiss holds 60 days; the Historian event carries
  no description text;
- **nothing else moves:** spending totals, budget figures, `recurring_items_json`, `detect_recurring_patterns`,
  Lever 4 and BYB are the same before and after an answer;
- **the words:** the fixed words carry none of D7's barred words; Needs attention's `build()` takes the new kind
  and still refuses an unknown one (s131);
- **AI off:** the item and the check appear with no model;
- **the Morgans:** they show exactly one item, StreamBox, and s249 still passes;
- **a null model** before it ships, as item 65 W2 and item 106 had: shuffle the account on real-shaped recurring
  charges and measure how often D1-D4 fire on a household that pays each payee from one account. It should be zero
  or near it. A rate above that changes D1 or D4 before any build.

*Recommended.*

## 4. Not decided here

- **Two cards on one account** (a couple's two debit cards, told apart by `card_last4`). Rob's words are "different
  accounts". This is held, not proposed: the same pattern on two cards is plausible, but it isn't what was asked.
- **Charges paid once a year.** Two yearly charges in one month never reach D4's second month. A yearly version
  would need its own threshold.
- **Different plans at different prices** (a family plan on one account, an individual plan on the other) are
  outside D2's 5%, and not said.
- **The merged readings in §1.** `detect_recurring_patterns`, Lever 4's monthly figure, the BYB offer losing the
  charge, and `rhythm` reading two accounts as *every two weeks* are all real, and all separate from this item. Each
  would read better per account. That is its own item, with its own null model, and nothing here depends on it.
- **Paid outside the Ledger** (cash, Venmo, an account nobody imports). Groundwork can't see it, and the `cannot`
  line doesn't pretend to.
- **"For someone else" meeting the people record.** Asking who, or tying it to item 72 C5 or the care-for
  statements, is not proposed (D9).

## 5. Guardrail check (blueprint §3, Appendix A)

- **No conflict with §3:**
  - **#1 math-true or silent:** every figure is a row on record;
  - **#5 show, don't scold:** D7 says what was seen and never that it is a mistake;
  - **#6 real signals:** it is triggered by charges, never by usage;
  - **#7 local:** nothing is sent;
  - **#8 proof:** the rows are shown.
- **Rob's word "alert" against Appendix A.** A proactive card for a $15-$20 charge fails A.2 #1 (materiality, 5% of
  the monthly budget) in almost every household. So under the gauntlet it would never interrupt. D6 doesn't ask to
  change that. Needs attention is how Groundwork already alerts without interrupting, and *strictness is free*
  (A.1): nothing is hidden by staying passive.
- **If Rob wants it to interrupt as well**, that is its own point:
  - it would join the brake budget, as a clarification (A.3, *"a new prompt-kind joins the budget its attention
    cost resembles"*);
  - it would need either a materiality exception for this kind, which is the first one the blueprint would have,
    or a rule that it interrupts only when the pair is material.
  - This is flagged here, not recommended.
- **A.4's dismissal rule** is kept by D8's 60-day Dismiss.
- **No silent learning:** the answer is a statement the person made, kept where they can see and undo it, and it
  feeds nothing else (D9).
