# Utility bill estimates from weather, usage and EIA prices (queue item 26)

> Status: **OPENED 2026-10-01. No code.** Rob, 2026-10-01: *"open item 26"*.
>
> **Rob's requests (2026-09-28), recorded in the queue:**
> - estimate natural gas from weather, usage and price, and set it in the budget;
> - the same for electricity;
> - gasoline from fill-ups, leaving the cheapest station to GasBuddy.
>
> And his framing: *"the eia is forecasting that the cost of gas will increase next month and the budget is already
> accounting for this"*. It is the truth from the U.S. government, not shame.
>
> **What governs it:**
> - report statements proven in the same run;
> - the user decides, so nothing is written silently;
> - absence is not zero;
> - the null-model rule (simulate a heuristic against trend-free data before trusting it);
> - item 29's I1: the dashboard fetches nothing;
> - capable is not admissible.

---

## 1. Measured (2026-10-01, live, read-only, with Rob's EIA key)

**EIA's Short-Term Energy Outlook (STEO) has every input, from one source and the same key.** No NOAA account is
needed.

| need | STEO series (East North Central = Ohio's census division) | sample |
|---|---|---|
| residential natural gas price, history and **forecast** | `NGRCU_ENC` ($/MCF) | through **Dec 2027** (9.35 Dec 2027) |
| residential electricity price | `ESRCU_ENC` (¢/kWh) | Aug 2026 19.34, Sep 2026 19.82 |
| heating degree days | `ZWHD_ENC` | Aug 2026 11.1, Sep 2026 89.0; Dec 2027 1,025.8 |
| cooling degree days | `ZWCD_ENC` | (0 in winter months, as expected) |
| U.S. regular gasoline | `MGRARUS` (¢/gal) | through Dec 2027 |

- **Each call took 9–11 seconds.** STEO publishes monthly, so results are cached for the month.
- **Fetching happens only where the user is working with the budget**, never from the dashboard (I1).
- **Regional, not state:** STEO is by census division. Ohio maps to *East North Central*. The monthly *actual*
  state price stays the `utility_price.py` source, with its Ohio lag fix (U0).
- **The ledger:** utility bills already have their own categories, *Electric* and *Gas*, under *Utilities* (the
  seeded child categories). Fuel purchases go under the app's *Gas / Fuel* category.

---

## 2. Findings and proposals

**U0: The Ohio natural-gas fix comes first.**
- `utility_price.py` asks EIA for only the latest month, and Ohio's latest has no value yet, so natural gas falls
  back to an estimate.
- Fix: take the latest month that **has** a value.
- This is shared code: lts/1.x first, then master, with a gate on each line.

**U1: The model, per utility (the degree-day method).**

```
natural gas:  bill = F + (B + S x HDD) x price
electricity:  bill = F + (B + Sh x HDD + Sc x CDD) x price
```

- F, B and S are fitted by regression on **the user's own bills**: transactions in the Gas or Electric category.
- **Each bill is matched to its service month.** Rob: gas is billed a month behind. Proposed default: the service
  month is the month before the payment. It is a setting the user can change, shown on the row.
- **Minimum:** about 8–12 bills spanning heating and non-heating months.
- **The fit must earn its place before it is used** (null-model rule). On the user's own history it must beat the
  simple baseline, *last year's same month x the price change*, when scored on months it was not fitted to.
- If it doesn't, or the history is too short, the baseline is used and labelled as such. With no year-ago bill
  either, there is no estimate, and the row says what it needs.

**U2: Gasoline, without weather.**
- Each fill-up (a debit in *Gas / Fuel*) divided by EIA's weekly price that week gives gallons. The monthly gallons
  are the median of the last 6 complete months.
- The estimate is gallons x the latest weekly price, or STEO's next-month forecast when one is shown.
- Weekly *history* needs a new fetch (`gas_price.py` keeps only the latest week).
- Whether EIA publishes a weekly Ohio series or only the Midwest (PADD 2) one is confirmed at build. Otherwise PADD 2.
- Finding the cheapest station is out of scope (Rob: let GasBuddy do it).

**U3: The budget, as the user's choice, and the conflict it creates.**
- The user opts a row in: *"Estimate this from weather and EIA."* It is visible, reversible and labelled.
- **Conflict found:** if the estimate **rewrote** `BudgetItem.amount`, every monthly change would log a
  `budget_adjusted` event. The Willingness Layer reads exactly those events as **the user's own cuts and restores**
  (W-A). An automatic estimate would be read as willingness, which breaks item 23's read boundary.

  Options:

  | | what | effect |
  |---|---|---|
  | **(a)** | the opted-in row keeps the user's saved amount untouched. The month's **estimate is shown and used as that row's amount for the month**, computed and not stored, with its figures | no `budget_adjusted` event; W-A unaffected; the user's own number survives opting out |
  | (b) | write the amount, under a new event kind (`budget_estimated`) that W-A never reads | a second write path to keep out of the Willingness Layer forever |

  **Recommend (a):** it is a derived value, recomputed each read, like every other reading since item 23.

**U4: The report statement, proven in the same run.**
- *"EIA forecasts natural gas at $Y/MCF for November in your region, up from $X in October; your Gas row follows the
  estimate, so November's budget is $144, based on about 9 MCF, your usage last November."*
- It is stated **only** when the row is opted in **and** the amount shown was computed from that forecast in the
  same run. Otherwise it is blocked.
- A forecast is always credited to EIA as a forecast, never as Groundwork's prediction.

**U5: Reconciliation.**
- When the real bill lands (a month later, by which time EIA's actual price is published), the row shows **estimate
  against actual**, and the next fit uses the real figures.
- The record of how close the estimates have been is shown as a fact: *"the last 6 estimates were within $12 on
  average."* It is never a score of the user.

**U6: Price and usage stay separate in every sentence.**
- A rise is split into the part from price and the part from usage.
- A higher bill from price is never read as using more.
- No shame wording (the BANNED lexicon applies).

**U7: Scope.**
- U0 is shared (1.x first).
- **Everything else is 2.0 only**, through the teaching seam: the estimate, the opt-in, the report line and the
  reconciliation.
- The 1.x Budget page keeps today's benchmark line.

**U8: Build order.**
1. U0.
2. Natural gas: STEO fetch and cache, the fit with its baseline test, the opt-in row (U3a), the report line.
3. Electricity: the same, plus CDD.
4. Gasoline: weekly history.

---

## 3. Cases

| # | situation | expected |
|---|---|---|
| Ue1 | Ohio's latest NG month has no value | the latest month **with** a value, with its period (U0) |
| Ue2 | 12 gas bills across a year, fit beats the baseline on held-out months | the fitted estimate, labelled with F, B and S and the forecast HDD and price |
| Ue3 | 12 bills, fit does **not** beat the baseline | the baseline estimate, labelled as such |
| Ue4 | 4 bills | baseline if a year-ago bill exists; otherwise the row says what it needs |
| Ue5 | the user opts the Gas row in | that month's amount shown is the estimate; the saved amount is untouched; **no `budget_adjusted` event** |
| Ue6 | opting out | the user's saved amount returns exactly |
| Ue7 | EIA forecasts a rise and the row is opted in | the report line, proven in the run, credited to EIA |
| Ue8 | the row is not opted in | the forecast is stated as a fact, with *"your saved amount is $120; the estimate is $144"* and a one-click accept, which is the user's own edit |
| Ue9 | the bill lands | estimate against actual; the next fit uses it |
| Ue10 | a rise caused by price alone | split, and said to be price, not usage |
| Ue11 | the dashboard opens | no STEO or EIA fetch |
| Ue12 | fill-ups for 6 months | median monthly gallons x the latest weekly price, with its region |

---

## 4. Ruling sought: Rob

1. **U0:** the Ohio fix first, as its own small change on both lines?
2. **U1:** the degree-day fit per user, the service month a month before payment (user-changeable), and the fit used
   only when it beats the last-year baseline on held-out months?
3. **U2:** gasoline by fill-up gallons x the weekly price; Ohio or PADD 2 confirmed at build?
4. **U3:** the opted-in row **shows** the estimate without rewriting the saved amount (a), so no `budget_adjusted`
   event and the Willingness Layer is unaffected?
5. **U4 / U5 / U6:** the report line only when proven in the run and credited to EIA; reconciliation shown as fact;
   price and usage always split?
6. **U7 / U8:** U0 shared, the rest 2.0 only; build order U0, gas, electricity, gasoline?
