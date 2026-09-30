# An Investments tile on the dashboard (queue item 29)

> Status: **OPENED 2026-09-30. No code.** Rob, 2026-09-30: *"Investments have no standing in dashboard. We should
> have those items on the dashboard."*, then *"open item 29"*.
>
> **What governs it:**
> - item 22's rulings: D1, *"no investments mean no investment tile"*; the tile is arranged by the user
>   only; nothing is learned from use;
> - item 27's standard: completeness first, a source line, and no verdict or advice wording (the BANNED
>   lexicon applies).
>
> **Out of scope:** item 28 (ask for a tile), item 24, item 26, W-D, W-E, and anything in 1.x.

---

## 1. Measured (master `d1255d4`)

| piece | what it does today | against the standard |
|---|---|---|
| `_compute_portfolio_positions` (`/api/investments/positions`) | open lots by account and ticker, split-adjusted; market value, unrealized gain and %, day change | the arithmetic exists and is shared with net worth's drift tracking. Two gaps below |
| **a ticker with no cached price** | `current_price = avg_cost`, so market value equals cost and the **gain is 0** | **absence read as zero.** A position with no price shows a fabricated $0 gain |
| **a lot with cost basis 0** (e.g. shares transferred in with no purchase price recorded) | `total_cost` is 0, so the **whole market value counts as gain** and the % is 0 | **an unknown basis read as zero,** overstating the gain |
| **price refresh** | `positions` calls `refresh_stale_prices` (a network fetch) unless `skip_refresh=true` | the dashboard should not start an outbound price fetch just by being opened. Cached prices with their **dates** are the honest input |
| `PriceCache` | `price`, `day_change`, `last_updated`, `is_manual`, `source` | the as-of date and whether a price was entered by hand are both there to state |
| realized gains | closed lots carry `realized_gain`, `closed_date`, holding period; `/realized-gains?year=` filters by year | ready to use |
| target allocation | `AppSetting.inv_target_alloc` `{asset class: %}`, set on the Investments page | optional; a fact to compare against when present |
| investment **accounts with no lots** (e.g. a 401(k) tracked only by balance in Net Worth) | not in positions at all | a tile built only from lots would **silently omit** them |

---

## 2. Findings and proposals

**I1: The tile shows only what is on record, from cached prices.**
- It never triggers a price fetch (`skip_refresh`). Refreshing stays on the Investments page, where the user asks for it.
- The value line carries its date: *"$41,943 at prices as of Sep 29"*. When prices differ in age, it gives the oldest: *"prices from Sep 22 to Sep 29"*.
- A hand-entered price is said to be one.

**I2: No price means no value claimed.**
- A position with no cached price is **named and left out** of the value and the gain: *"VTI: no price on record, not included"*.
- It is never valued at cost. The same fix is **not** made to the Investments page or net worth here (1.x, and out of scope). It is named for them.

**I3: No cost basis means no gain claimed.**
- Lots with a basis of 0 or missing are **named and left out** of the unrealized gain: *"gain not stated for 12 VTI shares: no purchase price recorded"*.
- Their value still counts in the total, because the value is known.

**I4: The content, as facts.**
- Value, as of the price date.
- Unrealized gain or loss on the lots that have both a price and a basis, in dollars and %.
- Realized gains this calendar year, from closed lots, split into short and long term where the holding period is recorded.
- Allocation against the user's target, **only if a target is set**: *"stocks 72%, target 60%"*.
- A source line: *"From your investment lots and prices on record; prices not refreshed here."*
- No *"up / down"* verdict colours beyond the sign of the number, and no advice.

**I5: Accounts with a balance but no lots.** Options:
- (a) list them as a fact: *"Also on record: 401(k) $62,400 balance (Net Worth, Sep 1), holdings not recorded, so not in gains"*;
- (b) leave them out and say only that the tile covers recorded holdings.

**Recommend (a):** leaving them out silently understates the portfolio, and saying so costs one line.

**I6: Presence and arrangement.**
- It is a seventh tile, `dashInvestmentsCard`.
- It is present by default **only when** the record holds an open lot or an investment account (D1). Otherwise it does not exist on the page, rather than showing empty.
- Pin, hide and reorder like the rest. No use is read.

**I7: Mechanism.**
- 2.0 only, through the teaching seam.
- A server read, `/api/dashboard/investments`, reuses `_compute_portfolio_positions(skip_refresh=True)` plus the I2 / I3 exclusions.
- The words go in `tiletext.js` (Node-tested) and the rendering in `tiles.js`, within s30's borrowing cap.
- No schema. app.js and index.html are untouched.

---

## 3. Cases

| # | situation | expected |
|---|---|---|
| In1 | no lots and no investment accounts | no tile at all |
| In2 | lots with prices and basis | value as of the price date, unrealized gain $ and % |
| In3 | a ticker with no cached price | named, left out of value and gain; never valued at cost |
| In4 | a lot with basis 0 | its value counted; its gain not stated; named |
| In5 | prices of different ages | the date range, or the oldest date |
| In6 | a hand-entered price | said to be hand-entered |
| In7 | closed lots this year | realized gains this year, short and long term where known |
| In8 | a target allocation is set | each class against its target, as facts; no advice |
| In9 | no target | no allocation line |
| In10 | an investment account with a balance and no lots | per I5 |
| In11 | opening the dashboard | **no price fetch** is made (structural) |
| In12 | any tile sentence | no BANNED word; the source line present |
| In13 | the user hides or moves the tile | kept as their setting; never moved by use |

---

## 4. Ruling sought: Rob

1. **I1:** cached prices with their dates, and no price fetch from the dashboard?
2. **I2 / I3:** a position with no price, or a lot with no basis, is named and left out of the figure it cannot support, never counted as zero?
3. **I4:** value, unrealized gain, realized gains this year, and allocation against a target only when one is set?
4. **I5:** list investment accounts with a balance but no holdings as a fact (a), or leave them out (b)?
5. **I6:** a seventh tile, present only when investments are on record, user-arranged like the rest?
6. **I7:** 2.0 only through the seam, no schema?
