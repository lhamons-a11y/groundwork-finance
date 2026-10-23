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
