# Pricing the other fuels: diesel, propane, heating oil (item 34)

Opened 2026-10-03 (Rob: *"Proceed"*). **No code.** Since item 30, Groundwork asks which fuel a household uses, for its
vehicle and for its heat, and says plainly when it cannot price one: *"Diesel is not priced yet"*, *"Groundwork does
not price propane yet"*. This pass measures what it would take to price them. It is carried forward from items 26 and
30; nothing here waits on the 8 GB report.

---

## 1. What EIA publishes (measured live, 2026-10-03)

| fuel | EIA series | how often | where | when |
|---|---|---|---|---|
| **diesel** (No. 2, retail) | `petroleum/pri/gnd`, `EPD2D` | weekly | U.S., each **PADD** region, and **California only** among states | all year, 455 weeks back to 2018 |
| **heating oil** (residential) | `petroleum/pri/wfr`, `EPD2F` | weekly | U.S., regions, **27 states**: CT DC DE IA IL IN KS KY MA MD ME MI MN MO NC ND NE NH NJ NY OH PA RI SD VA VT WI | **heating season only**: October to March (latest 30 March 2026) |
| **propane** (residential) | `petroleum/pri/wfr`, `EPLLPA` | weekly | U.S., regions, **38 states**: AL AR CO CT DE FL GA IA ID IL IN KS KY MA MD ME MI MN MO MS MT NC ND NE NH NJ NY OH OK PA RI SD TN TX UT VA VT WI | **heating season only** |

Compared with what is priced today:
- **Gasoline** has nine states' own weekly series; **diesel has only California's**. Everyone else uses their PADD
  region, which `STATE_PADD` already maps.
- **Heating oil and propane have no price for April to September.** EIA's season begins in early October, so
  2026-27's first weekly figure is about a week away. A summer month has **no price**, never a zero.

**Groundwork's side, already in place:**
- the facts `vehicle_fuel` (gasoline, diesel, electric, other, none), `heating_fuel` (natural gas, propane, heating
  oil, ...) and `heating_payment` (by the bill or delivery, even monthly, prepaid);
- the categories onboarding files them in (`Gas / Fuel`; `Propane`; `Heating Oil`);
- `utility_applies()`, which today says *"not priced yet"*;
- the totals pass's `month_amount`, which would carry a followed estimate into the budget like any other.

**The shape of the data differs:**
- **Diesel is bought like gasoline**: fill-ups, paid when bought. The gasoline method works as it is. Each fill-up
  divided by that week's price gives gallons; the typical month times the latest price gives the estimate.
- **Propane and heating oil are delivered.** One delivery can cover weeks or months, so a delivery is not a month's
  use. Usage has to be spread across the time between deliveries and set against the cold (heating degree days, which
  item 26 already fetches per census division). A delivery made in summer has no EIA price that week, so it cannot be
  turned into gallons from price alone.

---

## 2. Points for ruling

**F1. Diesel first, as its own slice.**
- It uses the gasoline method unchanged: fill-ups at each week's price, the median month times the latest weekly
  price, and the year-earlier comparison all from price.
- The area is California's own series for California, the household's **PADD region** everywhere else, and the U.S.
  without a state. The card says which, as gasoline's does.
- `utility_applies` prices `vehicle_fuel = diesel` instead of saying *"not priced yet"*.

*Recommended.*

**F2. Propane and heating oil follow, as their own slice, under the null-model rule.**
- Each delivery (a debit in the fuel's own category) is divided by that week's residential price for the household's
  state, or its region where the state has no series. That gives gallons.
- Gallons are spread over the days since the previous delivery and fitted against heating degree days.
- **Before it ships, the fit is simulated against trend-free data** and must beat a plain average, as item 26's gas fit
  had to (`null_model_before_shipping_a_heuristic`).
- With fewer than three priced delivery intervals, it says what it needs.

*Recommended.*

**F3. Out of season is said, never filled in.**
- From April to September there is no current propane or heating-oil price.
- The card says *"EIA publishes these prices October to March; the latest is from 30 March 2026"* and shows last
  season's figures **as last season's**. It never presents them as this month's price, and it never shows a zero.
- A delivery with no price that week (a summer fill) is not converted to gallons, and the card counts it as such.

*Recommended.*

**F4. How it is paid still decides** (item 30's `heating_payment`). Even-monthly and prepaid customers get no fit:
their payments do not follow the cold, exactly as for natural gas today. *Recommended.*

**F5. The budget, like the others.** A followed diesel, propane or heating-oil estimate becomes this month's figure
through the totals pass (`budget_month_amounts`: a new kind per fuel, read from the fuel's category). The saved amount
is never written. *Recommended.*

**F6. 2.0 only, like item 26's estimates.** 1.x keeps its benchmark line. *Recommended.*

**F7. Order:**
1. F1 (diesel), built and accepted;
2. then F2–F4 (the delivered fuels), measured and simulated first.

Each is its own build authorisation. *Recommended.*

## 3. Ruling (Rob, 2026-10-03)

**F1–F7 ruled as written.** EIA's own pages agree with the measurement: on-highway diesel is weekly for the U.S., the
PADD regions and California, and residential heating oil and propane are collected October to March only.

**The build-level guard on F2** (it defines what *"tested against random data first"* must prove, without changing the
ruling):
- **Three priced deliveries is the minimum to attempt the model, not a guarantee that it is accepted.**
- The pre-release tests must show, on constructed data where the underlying consumption relationship is known, that
  the weather model beats the appropriate non-weather (null) model.
- If it cannot, Groundwork returns *insufficient evidence* rather than forcing the fit, and stays unknown.

In Rob's words: *having enough rows to calculate something is not the same as having enough evidence to justify
saying it.*

**F3, restated:**
- never substitute zero;
- never pretend a summer delivery has an EIA price that week;
- last season's price is shown only as last season's;
- current-season estimation stays blocked while the current price evidence does not exist.

**F4:** no consumption fit where the payments do not represent the consumption, unless a future pass finds a real
consumption signal.

**F5:** the existing totals path, with no second budgeting mechanism.

**F6:** no 1.x implementation.

**F7:** diesel, then its acceptance, then the delivered-fuel pass, then its own acceptance.

## 4. F1, diesel: authorised and built (Rob, 2026-10-03: *"Yes I authorize the diesel build"*)

- **`core/utility_estimate.py`:**
  - `diesel_area()`: California's own series (`SCA`), else the PADD region, else the U.S.;
  - `EIA_PRODUCT`: gasoline `EPMR`, diesel `EPD2D`.
- **`server.py`:**
  - `_eia_weekly_gas()` takes the product, and its cache keeps diesel apart from gasoline;
  - `gasoline_estimate()` prices diesel when the household said `vehicle_fuel = diesel`, and returns `fuel`. It keeps
    its id, so the opt-in and the budget totals (`budget_month_amounts`, whose words say *"the diesel estimate"*) carry
    over unchanged;
  - `utility_applies()` no longer says diesel is *"not priced yet"*.
- **The words:**
  - the card reads *"Using EIA's weekly diesel price for the Midwest (PADD 2) (EIA publishes no weekly series for
    OH)"*;
  - its title is *Diesel estimate*;
  - the report statement is EIA's diesel price, credited, and never says *gasoline*;
  - the onboarding summary says diesel is estimated from fill-ups.
- **The registry** (`core/household.py`): `vehicle_fuel`'s consumers include `gasoline_estimate` for diesel.
- **Tests:**
  - **s142** (12 checks): the areas, gasoline unchanged, a diesel household priced from R20/EPD2D, unanswered fuel
    still gasoline, the fetch still behind the Budget page only, the cache split, the words in Node, the title;
  - s140's vehicle check and s138's stand-in were updated for the extended signature.
- **Live EIA, through Groundwork's own fetch:** Midwest diesel **$6.526/gal**, California $8.181, U.S. $6.382 (week of
  28 September 2026). Ohio gasoline is unchanged at $4.263.
- **In the browser** (seeded, live): a diesel household's card read *"... about 26.2 gallons in a typical month ... At
  EIA's latest weekly price, $6.53/gal (week of Sep 28), that is about $148.59 a month. The same gallons a year
  earlier, at $3.25/gal, came to about $84.95: +$63.64, all from price."* No console errors.
- **Gate:** master **2269 / 0** (`87873c1`). 2.0 only (F6).

## 5. Acceptance (Rob, 2026-10-03)

*"Yes I accept the diesel slice"*. F1 is ACCEPTED as built (master `87873c1`).

## 7. The F2 guard's simulation (Rob: *"Yes run the simulation"*, 2026-10-03)

**Measurement only, no product code.** The script is `delivered_fuel_sim.py`. It uses **constructed households where
the true consumption is known**:
- **Use:** base plus k × degree days, with day-to-day noise (±30%) and month-to-month behaviour (±20%: occupancy,
  thermostat, time away).
- **Each home's weather** differs from its census division's by ±15%. Groundwork sees **only the division's monthly
  degree days**, as from EIA STEO.
- **Price:** each home's dealer price differs from EIA's state average by -15% to +20%.
- **Deliveries:** *will-call* fills (to 80% of the tank when it falls to 25%), plus a late-August top-up. Heating homes
  have a 500-gallon tank; water-heater and cooking homes have 120 gallons.
- **Pricing:** only deliveries in October to March have an EIA price, so only those intervals can be converted.

**The models** are chosen as item 26's gas fit is, by leave-one-out error: *weather* (gallons = b × days + k × degree
days) against *no-weather* (one daily rate). Each is judged on an average January's **true** use. There are three
household kinds:
- *heating* (k 0.10–0.20 gal per degree day);
- *weak* (k 0.02–0.05: supplemental heat);
- *weather-free* (k = 0: the null case).

**Results: weather must beat no-weather by 25%, with k > 0.**

| priced intervals | heating accepted | error when accepted | no-weather's error | **weather-free falsely accepted** |
|---|---|---|---|---|
| 3 | 48% | 8.0% | 40% | 3.9% |
| 4 | 93% | 7.5% | 43% | 5.9% |
| 5 | 98% | 7.5% | 42% | 4.6% |
| 6 | 100% | 7.1% | 41% | 3.9% |
| 8 | 100% | 6.8% | 41% | 2.1% |

**What it shows:**
- **Where the weather drives use, the weather model is about 5–6 times more accurate than no weather** (about 7–8%
  against about 41%).
- **At three intervals it declines about half the time.** The guard is working: three is the minimum to *attempt*,
  not a guarantee.

**The null case was not good enough as is.** 4–6% of weather-free homes got a weather model, and those were worse off:
their January error went from 2–3% (no weather) to a median of 8–9%, 15–19% at the 90th percentile.
- **A statistical-clarity test** (k at least 3 × its standard error) **barely helped**: 4.8% → 3.8% at four intervals.
- **A plausibility floor did:** *the weather must explain at least 30% of a year's use.*

| at 4 / 5 / 6 intervals | heating accepted (error) | weather-free falsely accepted | weak accepted |
|---|---|---|---|
| no floor | 93.0 / 98.2 / 100% (7.8 / 6.8 / 7.1%) | 5.3 / 4.0 / 3.4% | 79 / 86 / 94% |
| **floor 30%** | **92.8 / 97.8 / 100%** (8.2 / 7.6 / 7.4%) | **0.1 / 0.0 / 0.0%** | 69 / 76 / 81% |
| floor 50% | 91.2 / 96.8 / 99.2% | 0.1 / 0 / 0% | 25 / 27 / 29% (too strict) |

**The rule the simulation supports**, for F2's build:
- attempt the fit from **3** priced intervals (F2's minimum);
- **accept** it only if its leave-one-out error beats no-weather's by **25%**, **k > 0**, and the **weather explains at
  least 30% of a year's use**;
- otherwise: **insufficient evidence**, with no estimate.

**Limits, said plainly:**
- This is constructed data. Real delivery records can break its central assumption: **each delivery refills the tank
  to the same level**. A household that orders a fixed amount (*"100 gallons"*) when money is short, or a keep-full
  plan with partial fills, makes *delivered* differ from *used*. The fit cannot tell, so it would still pass or fail
  on the evidence alone.
- The first real delivery histories should be checked against this before the method is trusted further.
- Even-monthly and prepaid payers are excluded by F4.

## 8. Status

F1 ACCEPTED. The F2 simulation is done (s7): the method works where the weather drives use, and the null case needs
the 30% floor. F2–F4 await their build authorisation.
