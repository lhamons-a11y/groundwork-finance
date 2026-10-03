# Budget amount for the month: one reader, the totals follow-up pass (item 26 follow-up)

Opened 2026-10-01. **No code.** This is the follow-up Rob chose on U3(a) (`UTILITY_ESTIMATES.md` §5: *"show it now,
totals later"*). Today a followed estimate is shown beside the saved amount, and the totals keep the saved amount and
say so. This pass decides how a followed estimate becomes *"that row's amount for the month"* everywhere a budget total
is read. Only after that may the report say the budget *"includes"* it.

---

## 1. What was measured (master `8e7087c`)

**Server readers of `BudgetItem.amount`**

| where | what it does with the amount | is it a total for *this month*? |
|---|---|---|
| `bootstrap()` (server.py ~6031) | sends `{id, name, amount, cat}` to the client as `expenses` | **the source of every client total** |
| `get_budget_items()` (~2579) | the Budget page list; also what `_syncBudgetItemsToDb` diffs against | the list, and the write-back's baseline |
| `get_budget_variance_for_category` (~1322) | budget vs the last 6 months' actuals | no: it judges history against the saved amount |
| `reallocation_candidates` (~1494) | finds under-used rows to move money from | no: it is history |
| `_willingness_inputs` (~1587) | reads edits over 12 months | no: it reads what the *user* set, by design |
| `debt_capacity()` (~3952) | sums expenses to find room for debt payments | **yes** |
| `merge_category` (~6326) | moves rows between categories | no: it is structure |
| `export_to_file()` (~7914) | writes the user's budget out | no: the export is the user's own figures |
| create_app diagnostic (~438) | counts rows | no |

**Client readers.** `S.expenses` is used 60 times in `app.js`. It is built in one place, `restoreFromBootstrap`
(app.js ~1479). About twenty places add up `e.amount`: the Budget page totals, projections (~7916, ~8015, ~8989), the
surplus (~13234), monthly spend (~18384, ~18682), the solution engine's inputs (~20483), and the per-category
`budgeted` maps (~913, ~2437, ~22493, ~23126). No teaching module reads `S.expenses`. The dashboard's *This month* tile compares spending with budgeted **income** (`tiles.js` `_effectiveIncome`), so it is not one of these readers.

**What writes back (the decisive finding).** The client saves amounts in two ways:
- `_syncBudgetItemsToDb('expense', S.expenses)`, with 7 callers. It upserts **every row in the list**, not only the
  one edited.
- The Build-Your-Budget sandbox commit (~20922). It PATCHes any row whose sandbox amount moved.

So if the estimate were swapped into `amount` where the list loads, editing *any* row would save the estimate as the
user's own Gas amount. That is **silent writing**, which the settled safety rule forbids
(`assistant_safety_crossing_test_discipline`). The obvious one-line change is the wrong one.

---

## 2. Points for ruling

**M1. Two figures per row, never one overwritten.** Each row carries `amount` (what the user saved, the only thing
any write path sends) and `month_amount` (what this month's totals use). `month_amount` equals `amount` unless the user
follows an estimate for that row's kind and the estimate has a figure. Nothing writes `month_amount`. *Recommended.*

**M2. One function, `budget_month_amount(session, item, month)`, in `core/`.** Every this-month total on the server
reads it. On the client, `restoreFromBootstrap` carries `month_amount` from the server, and the ~20 summing sites read
`e.month_amount ?? e.amount` through one helper, `_rowMonth(e)`. Writes keep sending `amount`. The server decides,
and the client never recomputes. *Recommended.*

**M3. Which readers change.** This month's totals change: the Budget page totals,
projections, surplus, monthly spend, `debt_capacity`, and the solution engine's inputs. History does **not** change:
variance, reallocation, willingness, merge and export keep the saved amount, because they judge or show what the user
set. *Recommended.* (Each unchanged reader gets a test that it is still unchanged.)

**M4. The row says which figure is in use.** A row using an estimate shows both figures: *"$124 this month, from the
gas estimate · you saved $120"*. Turning off *Follow this estimate* returns the row to the saved amount at once.
Nothing is lost, because nothing was written. *Recommended.*

**M5. When there is no figure.** If the estimate says *needs* (EIA is missing a month, or there are too few bills or
fill-ups), `month_amount` is the saved amount, and the row says why: absence is not zero. *Recommended.*

**M6. The report wording follows the code.** Only once M1–M3 are built and tested may the report say *"your budget
includes it"*. The test is that the sentence appears only when the same run's total really contains the estimate
(`report_statements_must_be_proven`). *Recommended.*

**M7. 2.0 only.** The estimates exist only on master. On 1.x the row has no `month_amount`, and `_rowMonth` returns
`amount`. `app.js` is shared, so the helper ships on both lines, but on 1.x it does nothing.
*Recommended: helper on both, `month_amount` only from 2.0's bootstrap.*

---

## 3. What the tests would have to show

- With an estimate followed, every write path (the list sync, a row edit, the sandbox commit) sends the **saved**
  amount. **This is the crossing test for no-silent-writing.**
- The this-month totals contain the estimate. The history readers do not.
- Turning off *Follow* restores every total, with no write.
- *Needs* falls back to the saved amount, and the row says so.
- The *"includes"* sentence appears only when the total really contains the estimate.
- 1.x: no row has `month_amount`, and the totals are unchanged.

## 4. Ruling and build (Rob, 2026-10-02)

*"I accept M1-M7 as recommended, build it."* That includes the helper staying in app.js (M7).

**What was built:**
- **`core/budget_month.py`** (pure):
  - `bill_month(this_month, lag)` gives the service month whose bill is paid this month;
  - `pick_estimate()` chooses the estimate for **that** bill: lag 0 is this month's estimate, lag 1 is last month's
    (`previous`, now computed for electricity too), lag 2 is not covered. It returns none, with the reason, for a
    *needs* or for an estimate the household's answers rule out;
  - `month_amount()` gives the followed estimate's figure, or the saved amount.
- **`server.budget_month_amounts()`** is the one function (M2):
  - it gives every expense row `month_amount`, `month_source`, `month_why`, `month_from` and `month_for`;
  - it uses `fetch=False`, so totals never wait on EIA and use what the estimate cards last fetched.
- **Readers of it:** bootstrap; `GET /api/budget/month-amounts`; `debt_capacity` (M3); and the estimate route's
  `budget_uses` (M6), so the words are proven from the same request.
- **The client:**
  - `_rowMonth(e)` is the one helper;
  - 15 this-month readers use it: the Budget totals, shortfall, realism, what's left, the scheduler, trip room, lean
    mode, the debt suggestion and advisor, retirement and withdrawal monthly spend, the BYB what's left, the top-over
    category, the consequence sentence, and the row's own bar and figure;
  - history readers keep the saved amount: the behavioural profile, high leverage, reports of any month, the sandbox
    copy, the sandbox commit and the bloom save (M3).
- **M4/M5:** the 2.0 layer adds the row note, for example *"$48.21 this month, from the natural gas estimate · you
  saved $120.00"*, or the reason the saved amount is in use. Following or un-following refreshes the figures at once,
  with no write.
- **M6:** the card line becomes, for example, *"This month's budget uses the estimate for the bill paid this month
  (for September 2026's use), $48.21, in place of your saved Gas budget of $120.00."* The report statement says
  *"this month's budget includes the estimate built on it"* **only** when `budget_uses.in_totals` is true in that
  same request.
- **The earlier wording checks** in s136, s137 and s138 (*"still sets the totals"*, from 2026-10-01) were updated to
  the ruled behaviour.

**The crossing test for no-silent-writing** (s141):
- every write path sends the saved amount (the whole-list save, the sandbox copy and commit, every API payload);
- a mutation that makes the whole-list save send this month's figure is caught;
- at run time, after following, un-following and every read, the saved amounts are as set, and no `budget_adjusted`
  event was logged.

**Found in the browser, and now guarded:** an edit left a bare `async` on its own line in app.js. That is valid syntax
(`node --check` passed it), but at run time it stopped app.js part-way, so everything after it never existed. No
gate check executed app.js, so the gate could not see it. **s64**, on both lines, now runs app.js and every teaching
module top to bottom in the page's own order. A bare-`async` mutation proves it catches the failure. s66 checks the
shared helper (M7).

**Seen in the browser** (2.0, seeded, live EIA):
- unfollowed, the gas row is $120 (saved) and the card offers to follow;
- after ticking *Follow this estimate*, the row note, the card line and *What's left* (Expenses $904.80 to $848.61)
  all show $48.21 for September's bill at a one-month lag;
- the database still holds Gas $120, Electric $110 and Gas / Fuel $160;
- no console errors.

**Gates:** lts/1.x **895 / 0** (`b74f7da`); master **2237 / 0** (`9fb63f2`).

## 5. Status

BUILT on both lines (the helper on both; the month figures from 2.0's server) and gated. Awaiting Rob's acceptance.
Item 26's last open piece.
