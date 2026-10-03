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

## 4. Status

RULED 2026-10-03. No code until a build is authorised. F1 (diesel) is first.
