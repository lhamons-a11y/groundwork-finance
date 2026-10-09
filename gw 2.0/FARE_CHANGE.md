# Item 51 — Has the average fare gone up or down?

Opened 2026-10-08 (Rob: *"we should acknowledge if the average price was less or more than last average. It will let
the user know if prices have increased."*; *"yes open item 51"*). **RULED 2026-10-08 (Rob: "approve F1–F8 as recommended"):** F1 (a), the same quarter a
year earlier. **BUILT 2026-10-08 (Rob: "build item 51"): `core/airfare.py` keeps the same quarter a year earlier (`compare`; 2025 Q1 shipped beside 2026 Q1, 302 → 567 KB; `refresh()` and the release step download it beside a newer quarter) and `lookup()` returns `change`; `airfareChangeLine` in `app.js`; `s163`; `s152` D3 counts the two extra whole-table queries. Awaiting acceptance.** Master only, as item 41 is (`DOT_AIRFARE.md`).

## 1. What is true today (measured 2026-10-08)

- **The app can't answer it yet.** The shipped table (`core/data/dot_airfare.json`, 302 KB) holds one quarter,
  2026 Q1. `refresh()` replaces that quarter when DOT publishes a newer one. No earlier average is kept, so nothing can be
  compared.
- **DOT publishes every past quarter** on the same free, no-key service (`yj5y-b2ir` city pairs, `tfrh-tu9e` airport
  pairs). Fetching an earlier quarter is the same whole-table download. Nothing about the user's trip is sent.
- **Season moves the average as much as price does.** Measured on DOT's own rows, passenger-weighted over the 5,619
  routes listed in all four quarters of 2025:

  | 2025 | Q1 | Q2 | Q3 | Q4 |
  |---|---|---|---|---|
  | Average one-way fare | $215.74 | $206.51 | $195.88 | $216.51 |

  Within one year the averages span $225 to $217, a 10.5% swing with no change in prices from one year to the next.
- **The two candidate comparisons for 2026 Q1**, on routes listed in both quarters:

  | Compared with | Routes in both | Today's routes missing there | Median route change | Routes up | Weighted average |
  |---|---|---|---|---|---|
  | The quarter before (2025 Q4) | 6,054 | 259 | +5.6% | 77% | $215.82 → $231.39 (+7.2%) |
  | The same quarter a year earlier (2025 Q1) | 5,826 | 487 | +5.6% | 71% | $216.24 → $231.53 (+7.1%) |

  This time the two agree. They won't when the season turns: going from Q3 to Q4 in 2025 would have read +10.5%, with the
  year-over-year change unknown.
- **One route's change varies widely.** Against a year earlier, half of routes moved more than 8.1% either way, and one
  in ten moved more than 19.8%. DOT's figures come from a 10% sample of tickets, so a quieter route's average carries
  more chance in it.

## 2. What it would do

The DOT average fare note in the trip planner gains one line, with its working (the transparency standard). For
example:

> $287.40 average one-way, 2026 Q1. That's $14.20 (5.2%) more than the same quarter a year earlier, 2025 Q1
> ($273.20). Both figures are in each quarter's own dollars, not adjusted for inflation.

## 3. Points for ruling

**F1. What "last average" is compared with.**
(a) The same quarter a year earlier. Like is compared with like, so a change is about price, not season.
(b) The quarter before. This is more recent, but up to a 10.5% swing in it is only the season (§1), so "prices went
up" would sometimes be false.
(c) Both, each labelled.
*Recommended: (a).* (b) would state something the math does not show, which breaks *report statements must be
proven*.

**F2. The wording.** The dollar and percent difference, both quarters and both averages, with "more", "less" or "the
same" decided only by the sign. No adjectives ("sharply", "only"), no advice ("book now"), and no band that calls a
small change "about the same". A $0.40 difference is stated as $0.40.
*Recommended.*

**F3. Like for like, or nothing.** Both figures use the same basis. When today's figure is airport-pair, the earlier
one must be the same airport pair, otherwise both fall back to the city pair. When the route isn't listed in the
earlier quarter, the line says *"DOT has no average for this route in 2025 Q1, so there's nothing to compare it
with,"* and never estimates one.
*Recommended.*

**F4. Inflation, named, not adjusted.** The comparison is in each quarter's own dollars, and the line says so. No CPI
adjustment, since that would be a second source and a second assumption.
*Recommended.*

**F5. Storage.** The table carries a `compare` block: the year-ago quarter's city-pair and airport-pair fares. The
release step (`python -m core.airfare`) and the weekly `refresh()` download it beside the newest quarter. If that
second download fails, the newest quarter is still used and the line says nothing about change. The table is expected to
grow from about 302 KB to about 600 KB.
*Recommended.*

**F6. Per leg, one-way.** The comparison is of DOT's one-way average, the figure DOT publishes. It isn't multiplied
into the trip total, so the line can't be read as "your trip costs $X more".
*Recommended.*

**F7. The sample is named.** The line sits under the existing note, which already says "a 10% sample of real tickets
(about N passengers a day)". It also shows the earlier quarter's passengers a day, so a quiet route reads as quiet. No
threshold hides a change (see F2).
*Recommended.*

**F8. Master only, gated.** One new section: the comparison through the real lookup route on a fixture table, the
wording rendered from `app.js`, F3's no-earlier-route and mixed-basis cases, F5's failed second download, and no
verdict words. Item 41's s-section checks keep passing.
*Recommended.*

## 4. Not decided here

- A longer trend (four or eight quarters, a chart). That is its own item, if wanted.
- Comparing the user's own typed or read fare with the DOT average. That compares a booking with a sample, which is a
  different statement.
