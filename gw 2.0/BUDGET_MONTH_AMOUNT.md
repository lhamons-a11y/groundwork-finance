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

## 4. Status

OPEN: seven points for ruling (M1–M7). No code until ruled.
