# Utility bill estimates from weather, usage and EIA prices (queue item 26)

> Status: **RULED and AUTHORISED 2026-10-01 (Rob: "I accept all seven points, build it"). U0 BUILT on both lines; the natural
> gas slice BUILT on 2.0 (§6). Electricity and gasoline to follow (U8).** Opened the same day. Rob, 2026-10-01: *"open item 26"*.
>
> **Rob's requests (2026-09-28), recorded in the queue. For every U.S. state, not one (Rob, 2026-10-01; U9):**
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

**U0: The latest-published-month fix, for every state, comes first.**
- `utility_price.py` asks EIA for only the latest month. When that month has no value yet, the price falls back to
  an estimate. This was found on Ohio's June 2026 row, but **it applies to any state**: EIA publishes state months
  on its own schedule and sometimes withholds a state's figure.
- Fix: take the latest month that **has** a value, with its period.
- A state EIA does not publish at all is shown at the U.S. average, **labelled as the U.S. average**, never presented
  as the state's.
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

**U9: Where the user is: asked, never detected.**

Rob, 2026-10-01: *"this program is not just Ohio based this will be used in all states in the united states which
means the software will have to either grab the user location or ask the user to put their state information."*

- **Measured:** the app already asks. *Settings* has a **Home state** choice (`home_state`), and the existing EIA
  lookups use it. With none set, they fall back to U.S. figures. Ohio appears in this pass only because it is the
  test machine's state.
- **Recommend: ask, never detect.**
  - Detecting location means asking an outside service where the user is, which sends their location off the
    machine.
  - That breaks the local-first promise and the call-home audit the website's trust copy rests on.
  - It also gets things wrong (VPNs, travel, a home in one state and a job in another).
  - The state the user chose is their own statement, visible and changeable.
- **Every state maps to its regions in a fixed table, shipped with the app:**
  - the **census division** for STEO's forecasts and degree days (the nine divisions, e.g. Ohio to East North
    Central);
  - the **EIA state series** for monthly actual prices;
  - the **PADD region** for weekly gasoline (e.g. Ohio to PADD 2, Midwest).
  - All 50 states and DC. STEO's exact division codes are confirmed at build, as the regional series were confirmed
    for East North Central in §1.
- **No state set:** the estimate uses the **U.S.** series, labelled as national. The row says plainly: *"Using U.S.
  averages; set your home state in Settings for your region's prices and weather."* Weather matters most here, so the
  pointer is said once, on the row, never as a prompt that speaks first.
- **The state changes:** cached prices and fits for the old region are dropped, and the estimate is re-derived. The
  user's bills, which are their own record, are not affected.

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
| Ue13 | a user in Arizona | the Mountain division's forecast and degree days, Arizona's monthly price, PADD 5's weekly gasoline |
| Ue14 | no home state set | U.S. series, labelled national, with the one-line pointer to Settings |
| Ue15 | the user changes their home state | the old region's cache and fit dropped and re-derived; the bills untouched |
| Ue16 | a state whose latest EIA month is unpublished | that state's latest published month, with its period (U0) |
| Ue17 | anything on the path | no location lookup and no IP geolocation; the state comes only from the user's own Settings choice |

---

## 4. Ruling sought: Rob

1. **U0:** the latest-published-month fix first, for every state, as its own small change on both lines, with a state
   EIA does not publish shown at the U.S. average, labelled?
2. **U1:** the degree-day fit per user, the service month a month before payment (user-changeable), and the fit used
   only when it beats the last-year baseline on held-out months?
3. **U2:** gasoline by fill-up gallons x the weekly price; Ohio or PADD 2 confirmed at build?
4. **U3:** the opted-in row **shows** the estimate without rewriting the saved amount (a), so no `budget_adjusted`
   event and the Willingness Layer is unaffected?
5. **U4 / U5 / U6:** the report line only when proven in the run and credited to EIA; reconciliation shown as fact;
   price and usage always split?
6. **U7 / U8:** U0 shared, the rest 2.0 only; build order U0, gas, electricity, gasoline?
7. **U9:** the user's state is **asked** (the existing Settings choice) and **never detected**; a fixed table maps every
   state to its census division, EIA state series and PADD region; with no state set, U.S. figures, labelled, with
   one plain pointer on the row?

---

## 5. Ruling: Rob, 2026-10-01

**All seven points accepted, and the build authorised.** Rob recorded the location model in particular:

> a fact the user hasn't supplied should not become "known" just because the computer can obtain it somewhere else.
> The state selector is transparent, reversible, and under the user's control.

**One build decision, asked and answered the same day.** U3(a) says the estimate is *"shown and used as that row's
amount for the month"*. But budget totals are read in several places, some of them shared with 1.x: the Budget page,
the dashboard's *This month*, and the solution engine.

Rob chose: **show it now, totals later.**
- This build shows the estimate and its figures, records the user's choice to follow it, and gives the report line
  and the reconciliation figure.
- **Totals keep the saved amount, and the card says so.**
- A follow-up pass routes every budget reader through one *"amount for this month"* function.
- So the report says only what is true now: *"the gas estimate on your Budget page uses that forecast"*. It does not
  say the budget *"already includes it"*.

---

## 6. The build (2026-10-01)

| piece | where | what it does |
|---|---|---|
| **U0, both lines** | `utility_price.py` (`lts/1.x` `d9ce860`, gate 830 / 0; merged to master) | Asks EIA for six months and uses the newest **with a value**. Live: Ohio natural gas **$19.86, May 2026** (June and July unpublished); Arizona its own July; Ohio electricity 19.45¢. A state with nothing published is the U.S. figure, labelled `U.S.`, naming the state asked for. `s53`, 9 checks, no network |
| **U9, every state** | `core/utility_estimate.py` `STATE_DIVISION`, `STATE_PADD` | All 50 states and DC, to their census division and PADD. **All nine STEO division codes were confirmed against EIA** (NEC MAC ENC WNC SAC ESC WSC MTN PAC: degree days and residential gas price). No state set means the U.S. series, labelled *United States* |
| **the outlook** | `server._steo` | EIA's Short-Term Energy Outlook, cached a week (it publishes monthly; a call takes ~10 s, and the first load in the page took about 39 s for two series). Fetched only by `gas_estimate`, behind the Budget page's route; **never by the dashboard** |
| **the bills** | `server._gas_bills` | Debits in the *Gas* category, summed by the month paid and moved to their **service month** (`lag`, default 1, the user's setting). A month without a bill is absent, never zero |
| **U1, the fit** | `utility_estimate.choose` | `bill = F + B*price + S*(price*HDD)` by least squares. **It earns its place three ways, each scored leave-one-out over every bill:** it beats the baseline; it beats a plain average by at least a quarter; and its heating slope is positive. Otherwise the baseline (*last year's same month x the price change*), labelled with the reason. With no year-ago bill either, it says what it needs |
| **the null model** | run in `s136` on **every gate** | Bills that follow weather x price: the fit chosen 396 / 400 (20% noise: 362 / 400). **Pure noise: 1 / 400. Flat bills with no heating: 2 / 400.** The first version, which only had to beat the baseline, chose the fit on 295 / 400 noise worlds, which is why the average test was added |
| **U6, the split** | `utility_estimate.split_vs_last_year` | Against the **same month last year**: the fit splits into price (last year's usage x the price change) and usage (the usage change x this year's price). The baseline says the whole difference is price, because it assumes last year's usage. *Found building:* the first version compared month to month and called the season "price" |
| **U3, following it** | `POST /api/budget/utility-estimate/optin` | The user's choice and their lag (0–2 months). **No budget amount is written and no `budget_adjusted` event is logged**, so the Willingness Layer never reads an estimate as the user's edit |
| **the card** | `static/js/teaching/utility.js`, `utilitytext.js` (Node-tested) | On the Budget page, only when there is a Gas row or gas bills. It shows the region, the estimate and how it was made, how close past estimates came, the split, EIA's forecast line, *"your saved Gas budget of $X still sets the budget totals"*, *Follow this estimate*, and *bills pay for* |
| **U4, the report** | `utility.js` wraps `_rcRenderMonthlyReport` | Only when the user follows the estimate, and only the sentence the estimate proves, credited to EIA |

**Found building, fixed and pinned:**
- **A missing month must not be zero.** The first server read used `hdds.get(month, 0.0)`, so a month without EIA's degree days would have claimed no heating. And a month without a price crashed the estimate. Both now return *"needs EIA's outlook figures for that month"*.

**Tests: `smoke_sections/s136_utility_estimate.py`, 25 checks.**
- U9: 51 of 51; the region and series ids; the national fallback; the service-month lag.
- **The null model**, plus *too few bills*, a fitted estimate's figures, *no estimate*, and missing EIA figures.
- U6: both splits, with the sum checked.
- **The route end to end**, with EIA and the bills stood in.
- **U3a:** the saved amount untouched and no `budget_adjusted` event; opt-in validation.
- **I1:** `_steo` called only by `gas_estimate`; nothing on the dashboard calls it.
- **U17:** no geolocation or IP-location anywhere.
- The words in Node: the fit, the baseline and its reason, the split, EIA's statement exactly, *"still sets the budget totals"* and never *"budget already includes"*, the national pointer, no statement when the forecast is unchanged.

**Seen in the page** (throwaway database: Ohio, 21 months of gas bills, a $120 Gas row, **live EIA**):
- *"Using EIA's outlook for East North Central (your home state, OH)."*
- The weather fit was chosen: *about 4.0 MCF at EIA's forecast $14.54/MCF plus about $39.73 fixed, about $90.65*, within about $8.16 on held-out months.
- *"Against October 2025 ($76.46): -$3.02 from price and +$11.55 from usage."*
- EIA's forecast line, and *"Your saved Gas budget of $120.00 still sets the budget totals."*
- Ticking *Follow this estimate* put EIA's line into the monthly report.

**Still to come (U8):** electricity (adds cooling degree days), gasoline (fill-up gallons x EIA's weekly price, by PADD), and the follow-up pass that makes every budget total use the estimate for a followed row.

