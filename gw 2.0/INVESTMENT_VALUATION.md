# Item 35 — The Investments page and net worth value what they cannot price

Opened 2026-10-03 (Rob: *"yes open item 35"*). No code. This pass asks for rulings; it authorises nothing.

Named during item 29 (`INVESTMENTS_TILE.md`): the dashboard tile was built to I1–I5, but *"Investments page / net
worth share the three gaps, named."* This pass is those gaps.

## 1. What happens today (measured 2026-10-03, master, temp DB, no network)

**The portfolio.** One brokerage account holds three positions:
- **VOO:** 40 shares, priced $512.30 yesterday, basis $357.
- **VXUS:** 120 shares, never priced, basis $50.
- **NEWCO:** 15 shares, priced $30, with a cost basis recorded as 0.

| | Value | Unrealized gain |
|---|---|---|
| **Dashboard tile** (item 29, 2.0 only) | **$20,942.00**; VXUS named as unpriced | **$4,092.00 (+24.95%)**; NEWCO named as having no basis |
| **Investments page** and **Net Worth** (`_compute_portfolio_positions` summary) | **$27,902.00** | **$4,542.00 (+19.44%)** |

The same portfolio shows two different values on two screens, $6,055 apart.

1. **An unpriced holding is valued at cost** (`server.py`, *"No price yet — use avg cost as placeholder"*).
   - VXUS adds $6,055 that nobody priced.
   - Its gain is shown as $0.00, a figure nobody computed.
   - Its row says $50.46/share in gold. Nothing says the price is missing, and $50.46 is the user's cost, not a price.
2. **A lot with no basis counts as all gain.** NEWCO's $450 is reported as $450 of gain at 0%.
3. **A price has no date on the page.** `price_stale` means only *never priced*. A price cached three months ago shows
   exactly like this morning's. (The tile shows a from–to range of price dates.)
4. **Where the at-cost figure travels.** `summary.total_market_value` is the value with VXUS at cost, and it goes to
   four places:
   - **Net Worth.** `_syncPortfolioToNetWorth` copies it into the Investments field ("synced from portfolio").
   - **Net worth snapshots.** `autoSnapshotNetWorthIfDue` and the paid-off marker post totals built from that field
     to `/api/net-worth/snapshot`. Those snapshots are *persisted history*.
   - **The Historian.** `_log_investment_allocation_drift` logs expected and actual dollars from the same summary.
     These are persisted events that `get_investment_allocation_confidence` later reads as evidence.
   - **The local model.** The Investments advisor prompt (`_invLaunchAdvisorAI`) is handed *"Total portfolio value"*
     and *"Unrealized gain"* and each position's gain, including VXUS at +$0.00 (+0.0%) and NEWCO at +$450.00.
5. **Opening a page fetches prices.**
   - `/api/investments/positions` runs `refresh_stale_prices` unless `skip_refresh=true`. That is a call to
     `query1.finance.yahoo.com` per held ticker older than 30 minutes (`price_engine.py`). Only the ticker symbol is
     sent (`SAFETY_PROVISIONS_INVENTORY.md`).
   - The Investments page and the Net Worth page both call it on open. The dashboard tile does not (item 29's I1).
6. **Both lines.** The Investments page, `_compute_portfolio_positions`, `price_engine.py`, the Net Worth sync and the
   snapshots are shared code on `lts/1.x` and master. The tile is 2.0 only.

## 2. Points for ruling

**V1. One valuation, at its source.**
- Apply item 29's rules inside `_compute_portfolio_positions` itself, so the page, Net Worth, the snapshots, the drift
  log, the narration and the tile all read one figure:
  - a holding with no price has **no** market value and **no** gain (`None`, not cost and not zero);
  - a lot with no basis counts in value and is left out of the gain.
- The summary reports the priced value, the gain on lots with a basis, and the holdings it left out, by name.
- The tile then stops re-deriving these at lot level and reads the summary, so there is one rule in one place.

*Recommended.*

**V2. What net worth says when a holding has no price.** Leaving VXUS out understates net worth. Counting it at cost
asserts a value nobody has. Neither number is true on its own.
- (a) Net worth is stated from what is priced, and the unpriced holding is named beside it: *"$X, plus VXUS
  (120 shares) with no price on record — set a price on the Investments page."*
- (b) Count it at cost, labelled as at cost.
- (c) Withhold net worth until every holding is priced.

*Recommended: (a).* (b) is today's behaviour with a label: the total still adds a figure that is not a value. (c)
blocks the whole screen for one ticker.

**V3. A lot with no basis.**
- Its value counts, because the price is known.
- The gain leaves it out, and the row says *"no cost basis on record — gain not shown"*.
- It is never shown as 100% gain or 0%.

*Recommended.*

**V4. Every price carries its date.**
- Each row shows *"price as of <date>"*, or *manual, <date>*.
- The page total shows the range of dates its prices come from, as the tile does.
- There is no "stale" threshold and no verdict, only the date.

*Recommended.* A threshold would be a heuristic with no null model behind it.

**V5. Whether opening a page should fetch prices.**
- Today, opening the Investments or Net Worth page sends each held ticker to Yahoo.
- (a) Keep the fetch on opening the Investments page, and stop it on the Net Worth page (Net Worth reads cached prices,
  like the dashboard).
- (b) Fetch only when the user presses *Refresh prices*, on both pages.
- (c) Keep both as they are.

*Recommended: (a).* The Investments page is where prices are maintained, so a fetch there is expected. Net Worth
should not reach out because the user opened it. This is Rob's call: it sets how much Groundwork calls out unasked.

**V6. Downstream of V1, each says what it left out.**
- **The Net Worth sync** carries the priced value and the named exclusions (V2).
- **Snapshots** record the value V2 states, with the exclusions in the snapshot's note.
- **The drift log** logs nothing for an allocation that has an unpriced holding: the drift would be computed against
  a total missing that holding. It does not log a partial drift as if it were whole.
- **The advisor prompt** receives the V1 figures and the named exclusions, never a gain nobody computed. This is the
  same rule as the report-statement rule: proven in the same run, or not said.

*Recommended.*

**V7. History already recorded is left as recorded.**
- Past net worth snapshots and drift events may include at-cost values. They are append-only history, and nothing can
  tell an inflated entry from a true one after the fact.
- Nothing is rewritten. The Net Worth chart's first snapshot after the fix carries a note that valuation changed on
  that date, so a step in the line is explained rather than read as a loss.

*Recommended.*

**V8. Lines.**
- This is a correctness fix to shared code: a figure the user reads is wrong today on 1.x as well.
- Build `lts/1.x` first, then merge to master, with a gate on each.
- The tile's change in V1 is master only.

*Recommended.*

## 3. Cases (for the build, if ruled)

| # | Case | Expected |
|---|---|---|
| Iv1 | The §1 portfolio | Page, Net Worth and tile all say $20,942.00 and $4,092.00. VXUS and NEWCO are named. |
| Iv2 | Every holding priced and with a basis | Today's figures, unchanged |
| Iv3 | Nothing priced | No value, no gain; every holding named. Net Worth states the rest and names them. Never $0, never cost. |
| Iv4 | Only basis-0 lots | The value is shown. The gain is not shown, and the card says why. |
| Iv5 | A manual price | Valued; the row says *manual* with its date |
| Iv6 | A price from three months ago | Valued; the row shows its date; no verdict |
| Iv7 | The Net Worth page opens (V5 (a)) | No network call; cached prices only |
| Iv8 | A refresh with targets set and VXUS unpriced | No drift event logged (V6) |
| Iv9 | The advisor prompt | No line carries a gain for VXUS or NEWCO. The exclusions are listed. |
| Iv10 | A snapshot after the fix | The value per V2; the exclusions in the note; older snapshots untouched |
| Iv11 | 1.x | Iv1–Iv10 that apply to 1.x, on `lts/1.x` |

## 4. Status

OPENED 2026-10-03. Ruling sought on V1–V8. No build authorised.
