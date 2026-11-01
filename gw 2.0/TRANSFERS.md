# Item 111 — Money moving between your own accounts: find the cause, fix it once

Opened 2026-10-22. Rob, on the review pack's fourth issue (the Ledger offering *Add to budget* for transfers and loan
payments):

> *"Ledger has always struggled with transfers. Possible rewrite?"*

On a one-line stopgap:

> *"I would rather find the cause and fix it instead of a stop gap because a temp fix always becomes the fix until
> it breaks again."*

**No code** except the read-only measurement script (`scripts/transfer_measure.py`). X1-X10 for ruling.

---

## 1. What is true today (measured 2026-10-22 on master `809b2cc`)

**Four causes.** Each one makes a different page wrong.

**Cause 1: "transfer" is a category label, not a fact about money.**
- A row is a transfer only if it is filed under Transfer (`_isTransferCat`, `app.js:274`; `core/checkin._transfer_ids`).
- Nothing pairs the two sides of a move: checking out and savings in, or checking out and the card's *payment thank
  you* in. An own-account move filed under anything else counts as spending on one side, and possibly as income on the
  other.

**Cause 2: a card or loan payment is filed as spending.**
- The importer's auto-category files a card or loan payment under **Debt** (`clientAutoCategory`, `app.js:7079`). Debt
  is an ordinary expense category.
- The page's one spending test, `_isSpend` (`app.js:267`), leaves out only Transfer.
- Run with Apple's JavaScriptCore on the shipped functions:

  | Bank line | Filed as | Counted as spending |
  |---|---|---|
  | `HARBOR CREDIT CRD AUTOPAY` | Debt | **yes** |
  | `CAPITAL ONE MOBILE PYMT` | Debt | **yes** |
  | `DISCOVER E-PAYMENT` | Debt | **yes** |
  | `SALLIE MAE LOAN PMT` | Debt | **yes** |

- The purchases on the card are counted as spending too. So **a card payment is counted twice**: once as the
  purchases, and again as the payment.

**Cause 3: the categoriser files three different things as Transfer** (`app.js:7082-7085`):
- **refunds** (`AMAZON.COM REFUND`). The purchase still counts, and the refund never reduces it;
- **cash withdrawals** (`ATM WITHDRAWAL`). The cash disappears from spending;
- **Venmo, Zelle, Cash App and PayPal**, even when the money goes to another person, not to the person's own account.

**Cause 4: at least nine places each decide "is this spending?", and they disagree.**
- **The page:**
  - `_isSpend` / `_isEarn`;
  - three hand-written checks: `app.js:8917` (not Income or Transfer), `app.js:13909` (not Income, Transfer or Debt)
    and `app.js:16599` (Debt, Transfer or *Payment* is a debt payment).
- **The server and engines:**
  - `core/checkin._transfer_ids`;
  - `NOT_SPENDING_WORDS` (`server.py:4010`, for the solution engine's levers);
  - `_LESSON_EXCLUDED_CATEGORIES` (`server.py:6883`);
  - `NOT_PRICES` (`core/price_change.py:28`, for price changes and the Calendar's one rule);
  - `EVERYDAY` (`core/first_import.py:19`);
  - item 107's `payment_category_ids`.
- **And one with none at all:** `detect_recurring_patterns`. That is why the Ledger offers to budget *Transfer to
  savings* and *Cashback Visa payment*.

**The sample household hides it.** The Morgans file their card and loan payments under Transfer by hand
(`core/sample_household.py:123`), so their pages never show the double count. Measured with
`scripts/transfer_measure.py`:

- **The Morgans as loaded:** 6 own-account pairs, all filed Transfer; spending unchanged. Nothing shows.
- **The same household filed as a real import would file it** (card and loan payments as Debt, the card's *payment
  thank you* present, one refund):

  | | Count | Total |
  |---|---|---|
  | Debt-filed payments, counted as spending | 18 | $6,258.78 |
  | Card payments counted on top of the card's own purchases | 6 | $3,600.00 |
  | Refund not netted | 1 | $42.18 |

  **Spending reads $1,199.00 a month too high**, about 35%, every month from May to September; $1,079.83 in October.

**Rob's own ledger is not on this computer.** The database here is the sample. The script reads a database read-only
and prints counts and totals only, no names. Run on Rob's machine, its output goes into this section before any
ruling is built:

```
python3 scripts/transfer_measure.py
```

## 2. What it would do

- Every row gets **one kind**, worked out in **one place** and read everywhere: spending, income, a move between the
  person's own accounts, a debt payment, interest and fees, a refund, or cash taken out.
- A move between the person's own accounts is found by **pairing its two sides**, and the person confirms the pairing
  once.
- The category the person filed stays theirs, and stays as filed.
- Spending, income, the budget, the levers, recurring charges, price changes, the Calendar and the Ledger all read the
  same answer.

## 3. Points for ruling

**X1. One definition, in one place.**
- A single function on the server, `core/money_kind.py`, gives each row its kind:

  | Kind | What it is |
  |---|---|
  | `spending` | a purchase or bill |
  | `income` | money in from outside |
  | `own_move` | between the person's own accounts |
  | `debt_payment` | paying a card or loan |
  | `interest_fees` | the cost of debt |
  | `refund` | money back on a purchase |
  | `cash_out` | cash taken out |
  | `unknown` | can't be told |

- The page reads the kinds from the server, and doesn't decide them itself.
- All nine places in §1 are replaced by it, and s257 fails if a new one appears.

*Recommended.*

**X2. A move is a pair.**
- **What pairs:** money leaving one of the person's accounts and the same amount arriving in another of their accounts
  within three days. Both rows are then `own_move`.
- **The card case:** a card payment leaving checking pairs with the card's *payment thank you*.
- **When only one side is in Groundwork** (the other account isn't imported), the row is said as such, never guessed:
  - a payment to a debt on record is `debt_payment`, by the existing *attach as debt payment* link
    (`CheckingTransactionLink`);
  - anything else stays as filed, and Ask why's *own transfers* check can show it.

*Recommended.*

**X3. A pair is confirmed once.**
- Each new pairing is shown once: *"$600.00 left Everyday Checking on Oct 22 and $600.00 reached Cashback Visa on Oct
  23. Is this money moving between your accounts?"*
- A yes can become a standing statement for that pair of accounts and that payee, with item 93's standing-statement
  pattern: listed, withdrawable, never assumed.
- Until confirmed, a found pair is counted as `own_move` and marked *found, not yet confirmed*.
  - (a) counted while waiting. *Recommended*: counting it as spending is the error being fixed.
  - (b) counted as filed until confirmed.

**X4. Paying a card is not spending; the purchases were.**
- A card payment is `debt_payment`, and never counted in spending. The purchases on the card are.
- A loan payment is `debt_payment` too: an outflow on the budget's debt line, not spending.
- Interest and fees are `interest_fees`. They are the cost of debt, and stay counted where the cost of debt is shown.

*Recommended.*

**X5. A refund reduces spending in its own category.**
- A refund is `refund`. It nets against the category of the purchase it reverses: the same merchant's category, or,
  if there isn't one, the category it was filed in.
- It is no longer filed under Transfer by the categoriser.

*Recommended.*

**X6. Cash taken out.**
- (a) `cash_out`: shown as *"cash taken out: $X; what it was spent on isn't on record"*. It is counted neither as
  spending nor as a move, and the person can file any of it. *Recommended*: honest, never a guess.
- (b) Counted as spending, in a *Cash* category.

**X7. Venmo, Zelle, Cash App and PayPal.**
- These are `spending` (or `income` when money comes in) unless the other side pairs with one of the person's own
  accounts under X2.
- Paying a friend is spending. Moving money to your own PayPal balance is a move.

*Recommended.*

**X8. The category stays the person's.**
- The kind sits beside the category and never overwrites it. The Transfer category stays.
- Nothing is re-filed without the person: existing rows get their kind on read, and no migration rewrites a category.

*Recommended.*

**X9. The Morgans are filed like a real import.** Card and loan payments go under Debt, with the card's *payment thank
you* and one refund, so the sample shows X1-X5 working rather than hiding the problem. s249 is updated as far as
measured. *Recommended.*

**X10. Built in stages, master only, measured first.**
1. Rob's ledger measured with the script (§1).
2. `money_kind` and the pairing (X1, X2, X4-X7), with every reader switched to them, and a null model: on a household
   with no own-account moves, every page's figures are unchanged.
3. The confirmation (X3), and the Morgans (X9).

Tests (s257):
- each kind on planted rows;
- a pair found and the double count gone;
- one side only;
- a refund netted;
- cash said as cash;
- a friend paid by Zelle is spending;
- the category untouched;
- no second definition anywhere;
- every page's spending equal to one total.

*Recommended.*

## 4. Not decided here

- **Investment contributions and 401(k) deductions.** Money to a brokerage the person owns is an `own_move` under X2
  when both sides are in Groundwork. A payroll deduction never reaches the ledger. That is its own point if asked.
- **Splitting one transaction** (a paycheck with a reimbursement inside it). Item 72 stage 4 named this as separate
  work. It is still separate.
- **Joint and shared accounts between two households.**

---

## 5. Ruled (2026-10-26)

Rob: *"build item 111"*. Read as X1-X10 accepted as recommended, with **X3 (a)** (a found pair is counted as a move
while it waits) and **X6 (a)** (cash said as cash, counted as neither). If that reading is wrong, each choice is one
place in `core/money_kind.py`.

Rob 2026-10-29: *"I accept item 111"* - the reading above, X3 (a) and X6 (a) included, stands.

## 6. Stage 1: Rob's ledger, measured (2026-10-26, on the Windows laptop)

`python scripts/transfer_measure.py` on this computer's own database (1,706 transactions, 2026-01-05 to 2026-10-23,
8 accounts):

- **7 own-account pairs**, $5,434.89. Six were card payments into a credit account, filed Debt on both sides; one was
  a move to savings, filed Transfer. Today the leaving side of the six counts as spending ($1,084.89).
- **142 debits filed under Debt**, $17,559.45, all counted as spending today.
- **160 rows filed Transfer**: 1 refund ($10.88), 1 cash withdrawal ($42.20), 14 Venmo / Zelle / Cash App / PayPal
  ($385.29), 3 "transfer to/from" or savings ($12,702.15). 146 Transfer debits have no arriving side in the ledger.
- **Spending reads $1,600 to $3,000 a month too high**: March $6,701.35 against $5,068.65, April $7,758.76 against
  $5,146.61, September $7,829.97 against $5,692.31.

## 7. Built (stages 2 and 3)

**One kind per row, in one place.** `core/money_kind.py`:

- `classify()` gives every row one of the eight kinds, with the category it counts in (a refund's is the same
  payee's purchase category, X5) and its pair.
- `kinds(session)` reads the record; `spending_of()` is the one spending total.
- The server sends each row's kind with `/api/transactions`, and `/api/transactions/kinds` answers for every row.
- The page reads them: `_kind`, `_isSpend`, `_isEarn`, `_spendAmt`, `_spendCat`. It re-asks after any change to a
  transaction or a debt, because one row can pair or unpair another.

**What was replaced, all reading money_kind now:**

- the page's `_isTransferCat`, and the three hand-written checks (budget prefill, onboarding analysis, *debt paid
  this month*);
- every spending sum and per-category total on the page (25 uses), each now through `_spendAmt`, so refunds net
  everywhere;
- `core/checkin._transfer_ids`, `NOT_SPENDING_WORDS`, `_LESSON_EXCLUDED_CATEGORIES`, `NOT_PRICES` (price changes,
  the Calendar's recurring rule, yearly steps), `EVERYDAY`'s not-spending words, `two_accounts.payment_category_ids`;
- `detect_recurring_patterns` (no transfer or card payment is offered as a bill to budget);
- the year-end summary and the heavy-months reader;
- found while building, a tenth: `_debt_payment_txn_ids` (BYB offers and the lesson). It now also counts a payment
  linked through a Debt Payoff entry, and a payment *in the bank's words for one* to a payee naming a debt. A purchase
  at a store whose card is on record is no longer read as a payment.

**The null model (X10), measured before it was trusted.** The first pairing rule let a store credit on a card pair with
an unrelated purchase of the same amount on checking, because "it reached a card" counted as evidence. Now:

- a pair needs evidence beyond the amount: a side filed as a move or payment, or the bank's own words for one;
- its arriving side must be filed as a move or payment, or not filed at all.

On 300 simulated households with purchases, store credits and paychecks but no moves, it finds 0 pairs, and spending
is unchanged in every one. On Rob's ledger it still finds the same 7 pairs.

**The check-in (S3 amended).** Card and loan payments are not spending (X4), but the budget holds their line, so the
month is compared like for like: *left = budget - spending - debt payments*. The check-in carries `debt_paid`.

**What moved is said for what it is.** The check-in and the Monthly Report used to say *"$X moved between your own
accounts"* of every debit that wasn't spending. Now that figure also holds card payments, cash and interest, so each
part is named: *"$600.00 paid to cards and loans, $300.00 moved between your own accounts and $60.00 taken out as
cash - not spending."* The check-in's month reads *"$S spent and $D paid to cards and loans, $T of the $B budgeted"*.

**X3.**
- Needs attention takes a ninth kind, `own_move`, in the server's fixed words, with three answers: *Yes*, *Yes, every
  time between these two* (a standing statement for that pair of accounts and that payee) and *No, it isn't* (the
  pair ends, and both rows count as filed).
- Answers are appended to `own_moves_said_json`, never written over. The settings route can't write it.
- Settings lists the standing statements, each with Undo (`teaching/ownmoves.js`).
- The Ledger names each row that isn't spending or income, and marks a found pair *found, not yet confirmed*.

**X5 in the categoriser.** `bank_importer.auto_category` and `clientAutoCategory` no longer file refunds under
Transfer. A refund is filed by its merchant (`AMAZON REFUND` -> Shopping), and s166's table follows.

**X9.**
- The Morgans' card and loan payments are filed under Debt, with the card's *PAYMENT THANK YOU* on the Visa and one
  ParcelMart refund.
- On load they show 12 found pairs: 6 card payments and 6 moves to savings. One *every time* answer on the card
  clears all six card-payment cards (checked in the app).

**Rob's ledger after the build** (read-only, a copy):

| | Count |
|---|---|
| spending | 1,285 |
| debt_payment | 158 |
| own_move | 136 |
| income | 63 |
| refund | 38 |
| cash_out | 17 |
| interest_fees | 9 |

| Month | Spending today | Spending by kind |
|---|---|---|
| March | $6,701.35 | $4,676.14 |
| April | $7,758.76 | $5,019.36 |
| September | $7,829.97 | $5,560.87 |
| October | $6,578.30 | $5,011.89 |

Income moves by $15-$614 a month. A credit filed under a spending category is now a refund in that category, where
the page used to count it as income (X5's "the category it was filed in").

**Tests.** `smoke_sections/s257_money_kind.py`, 23 checks:
- each kind on planted rows;
- a pair found and the double count gone;
- one side only;
- a refund netted;
- cash said as cash;
- a friend paid by Zelle;
- Zelle to the person's own account;
- the category untouched;
- the null model;
- no second definition anywhere (a scan of `server.py`, `core/` and `app.js`);
- every row's kind on the route;
- the X3 question, its answers and its standing statements;
- one spending total from the server, the check-in and the page's own sum (in Node);
- the Morgans' filing.

s131 (the ninth kind and its endpoints) and s166 (refunds by merchant) were updated.

## 8. Accepted (2026-10-29)

Rob: *"I accept item 111"*. Built at `374c623` (gate 3987/0), accepted as built. **Item 111 CLOSED.**

## 9. Reopened (2026-11-01)

Rob, after an outside review: *"the issue that I would focus on this review is with item 111 still. I think we may
have a few issues that I would like to look over before I put it to rest."* Every case the review named was replayed
against `core/money_kind.py` on master `3977fc1` (a scratch script, synthetic rows in s257's shape). No code has
changed. **Item 111 is open again for X11-X20 below.**

### 9.1 What the replay found

| Case | Today | What it is |
|---|---|---|
| $100 *OHIO EDISON AUTOPAY* (filed Utilities) and an unrelated, unfiled $100 deposit to savings two days later | both `own_move`; spending $100 → $0 | **defect** (X11) |
| $142.17 *STATE FARM PAYMENT* (filed Insurance) and a $142.17 deposit filed Transfer the next day | both `own_move` | **defect** (X11) |
| control: $100 *KROGER #12* and the same unfiled deposit | spending stays; no pair | as intended |
| Kroger refund on Sept 4; Kroger purchases Sept 1 (Groceries) and Sept 21 (Shopping) | refund nets against Shopping | **defect** (X12) |
| unmatched *TARGET REFUND* filed Transfer | `refund`, category *Other* | for ruling (X13) |
| *KROGER REFUND* filed under Income | `income` | for ruling (X14) |
| *ZELLE TO SAM* filed under Debt | `debt_payment` | for ruling (X15) |
| two $0 rows filed Transfer on two accounts | paired, a $0 question in Needs attention | small (X16) |
| one $300 transfer, two $300 deposits on two accounts | the nearer, then the lower row id; the other never named | for ruling (X17) |

**Why the tests passed.**
- The null model (s257 X10) compares only debits.
- Every generated row is called *STORE n*, so no household has a payment word in it. The path behind X11 is never
  exercised.
- The store credits are generated, but the spending total they now change is never compared.

**Where the cause sits.**
- *X11:* `_evidence` accepts the bank's payment words on **either** side. So a bill the person filed as spending
  pairs with any same-amount deposit that is unfiled or filed as a move.
- *X12:* `bought` (the refund's category) is built over the whole history, newest purchase winning, with no date
  limit.

### 9.2 Readers that still decide for themselves

X1 said every reader reads the one kind. These still decide by category, in `server.py` unless named:

| Reader | What it does | Reading |
|---|---|---|
| `_willingness_inputs` | spending by category and month, leaving out only Transfer-type categories | debt payments and cash counted as spending - **probably wrong** |
| `reallocation_candidates` | raw debits summed by category | a non-spending category can feed the pool - **probably wrong** |
| `_futures_inputs` | the spending record leaves out only Transfer-type categories; the budget side separates debt lines | history and plan may count debt payments differently - **probably wrong**, needs a test |
| `_bills_ctx` (the reserve's leanest month) | money out less Transfer categories | debt payments and cash *are* money out, so this is defensible as cash flow. Only the unfiled side of a found pair still counts - narrow |
| `_price_changes`, `_yearly_steps` | leave out non-spending categories by name (`not_a_price`), not by the row's kind | a linked debt payment filed under a spending category could read as a recurring charge - **needs a test** |
| `_first_import_findings` | yearly renewals by category, beside a `money_kind.kinds` read | **needs a test** |
| `_category_months` | one category's raw debits by month | **needs a test** |
| `core/ask_why.py` | `check_own_transfers` pairs an income deposit with any same-amount debit within two days, with no other sign needed; two checks find Transfer by the exact name *transfer* | a **second definition**. It only offers a fix the person taps, so it writes nothing |

s257's "no second definition anywhere" scan looks for five names, so it does not see `ask_why`'s.
`scripts/transfer_measure.py` still pairs on amount and date alone. It was the pre-build measurement and is not a
check of the build.

### 9.3 Points for ruling

**X11. The bank's word "payment" is not enough on the leaving side.**
- A pair needs one of these:
  - either side **filed** as a move or payment;
  - the bank's **move** words (*transfer*, *xfer*, *savings*) on either side;
  - the bank's **payment** words on the **arriving** side (*payment thank you*);
  - the arriving account is a card or loan.
- A leaving side the person filed as spending pairs only when the money reached a card or loan.
- **Before building:** re-measure Rob's ledger. §6 found 7 pairs, and each one must still be found.

*Recommended.*

**X12. A refund nets against a purchase that came before it.**
- The same payee's latest spending purchase **on or before** the refund's date.
- None before it: X5's second half (X13).

*Recommended.*

**X13. A refund with no purchase, filed under a category that isn't spending.**
- X5 says "else the one it was filed in". Read literally, that nets a refund against Transfer or Debt.
- (a) *Other*, as built, with X5's words amended to "else the one it was filed in, when that is a spending category;
  else *Other*".
- (b) the filed category, literally.

*(a) recommended.*

**X14. A credit filed under Income that the bank calls a refund.**
- (a) Income, as filed - X8, the category is the person's. As built.
- (b) A refund - the bank's own word wins.

Imports file rows too, so the filing may not be the person's choice. No recommendation.

**X15. Venmo / Zelle / Cash App / PayPal filed under Debt.**
- (a) `debt_payment`, as filed - paying back a friend can be a debt. As built.
- (b) Spending, by X7.

*(a) recommended.*

**X16. A $0 row never pairs.** *Recommended.*

**X17. More than one row could be the other side.**
- (a) The nearest date, then the lower row id, as built. The other candidate is never named.
- (b) The same rule, and the question in Needs attention names the other candidate, so a *no* moves to it knowingly.

Debits are also paired oldest first, so an earlier debit can take a later one's deposit. Name this in the question
rather than solve it.

*(b) recommended.*

**X18. s257 widened.**
- The null model's households get bills in the bank's payment words (utility and insurance autopays) beside
  unrelated deposits of the same amounts.
- Credits are compared in the spending total.
- Each row of §9.1 becomes an adversarial check.
- The X1 scan also catches `ask_why`'s exact-name test.

*Recommended.*

**X19. Every reader in §9.2 reads the kind.**
- Each one says which figure it means:
  - **spending:** the `spending` kind less refunds;
  - **money out:** every debit, with each kind named.
- Then it reads `money_kind`, never a category.
- The four marked *needs a test* get one first, so the change is measured, not assumed.

*Recommended.*

**X20. Ask why's *own transfers* check.**
- (a) It uses `find_pairs`, so it finds exactly what the Ledger counts, and its fix becomes the X3 question.
- (b) It stays a separate finder of evidence, with its rule named in its own words.

*(a) recommended.*

### 9.4 Not here

The review's findings on item 115 (report sections ignoring their periods, required settings not enforced on the
server, the net-worth fallback, R19 against G4) are item 115's, and are not reopened here.
