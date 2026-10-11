# Item 59 — The trip budget uses real prices, or says it has none

**ACCEPTED + CLOSED 2026-10-10** (Rob 2026-10-10: "i accept all").

Opened 2026-10-09. Rob: *"can we add that web search capability?"*, then, on the way set out below, *"Lets approach
it that way"*. **P1–P8 RULED as recommended (Rob 2026-10-09: "I accept item 59, 60, 62")**: P1 on both lines; P2 on condition GSA's files and terms allow it. **BUILT 2026-10-10 on master** (Rob: "build all items that have been ruled on"): **P2's condition checked first** - GSA publishes each fiscal year's rates as one public spreadsheet (FY 2027: 641 rows, effective October 1, 2026, 36 KB, no key), and its website policy says its material is free of copyright and may be copied and distributed; works of federal employees are public domain. `core/per_diem.py` reads GSA's file with the standard library, ships it (core/data/gsa_per_diem.json), looks a destination up by city (a DOT market's first city leads; a name in two states asks which; an unlisted place says so - GSA's standard rate is per county, which a city name cannot tell) and season, and refreshes once a year from gsa.gov. **P1:** the AI budget, "live prices", the web-search tool and saving `aiResult` are gone; an old saved one is labelled; the sourced budget is still saved for the trip history. **P3:** "Look up hotels (Google Hotels)" opens the trip's destination, dates and guests in Groundwork's window (checked: Google fills them from search text; its check-in parameters are ignored); reading the clicked price (P3's optional half) BUILT 2026-10-11 (Rob: "build 58 and 59"): `hotels_window.py`, item 44's shape - on a real click of a "Visit site for ..." button on Google Hotels, the row's three prices are read only if the page shows its "Stay total with taxes + fees" heading and "N nights with taxes + fees", and the total agrees with the nightly price with taxes times the nights (within a dollar a night); one line back, "hotel <total> <nights>"; offered with Use / Not this one, named as Google's with taxes and fees and that the hotel's checkout may differ; measured on a real Google Hotels page (KAYAK's row: $87 / $100 / $301, 3 nights -> $301). The hotels window is now titled Google Hotels (it said "Bank website - www.google.com"). s196. **P4/P5:** the $140 / $45 / $50 defaults are gone; each line says its source; activities are the person's own figure; the total counts only sourced lines. s186. **1.x P1:** separate commit on lts/1.x.

## 1. What is true today (measured 2026-10-09, master and lts/1.x)

- **"Generate my trip budget →" shows invented prices as live ones, on both lines.**
  - `generateTripBudget()` asks the local model: *"You are a travel budget assistant. **Always search for real
    current prices.** Return only valid JSON"*. It passes a `web_search` tool, which is a leftover from cloud AI.
  - The local engine has no search, and ignores the tool. The hotel, dining, activity and transport figures it
    returns are the model's own.
  - The call skips the voice check (`skipGate`, "prices come from a live web search", which is no longer true).
  - The page labels the result **"✦ AI · live prices"** and saves it to the trip record (`/api/trip/budget`,
    `aiResult`).
- **What already works without a model:** DOT average fares (item 41), EIA fuel prices (items 26 and 34), and
  Google Flights in Groundwork's window with the clicked fare read and confirmed (items 42–44). All are sourced,
  named, and downloaded as whole public tables, never with anything about the user's trip.
- **Why not a web search:**
  - It sends the destination and dates to a search company (a third party).
  - It needs a paid key, which no user has; that's why item 40 replaced SerpApi.
  - The small local model would turn arbitrary pages into figures nothing can check.

## 2. Points for ruling

**P1. Stop showing and saving invented prices (both lines).** The model call, the "live prices" label, the
`web_search` tool and the saved `aiResult` all go. On 1.x this is a wrong saved figure, so it falls under the 1.x rule
(item 32 L1). Trip records already saved with an `aiResult` keep it, labelled *"estimated by the AI model in an
earlier version, not a price"*, never shown as live.
*Recommended.*

**P2. Lodging and meals from the U.S. government's per-diem rates (GSA).**
- GSA publishes lodging rates (by month) and meals-and-incidentals rates for every U.S. city and county, free, as
  whole tables.
- Groundwork ships the table and refreshes it once a year, the way the DOT fare table works.
- The trip line reads like *"Lodging: GSA rate for Denver, October, $173 a night (the federal travel rate, not a
  quote)"*.
- Outside the U.S., or for a place GSA doesn't list: *"No published rate for this destination; enter yours."*
- **Before building:** confirm GSA's downloadable file format and terms. This point is ruled on condition that they
  allow it.

*Recommended.*

**P3. The real hotel price: Google Hotels in Groundwork's window.** It opens filled in with the destination, dates
and guests, like Google Flights (item 42). Optionally, the price the user clicks is read and confirmed before use,
like item 44: named as Google's, with taxes and fees possibly extra.
*Recommended.*

**P4. Fuel stays EIA (items 26 and 34). Activities are the user's own,** or the budget leaves them out and says so.
No guessed activity price.
*Recommended.*

**P5. Every line shows its source** (the transparency standard): GSA, DOT, EIA, Google (confirmed), or *"you
entered"*. A line with no source isn't in the total.
*Recommended.*

**P6. The model's role, if any:** none in the price lines. It may narrate the finished budget through the voice
check (R8: every figure must be one of the sourced ones).
*Recommended.*

**P7. Lines.** P1 on both lines. P2–P6 master only.
*Recommended.*

**P8. Tests.**
- No path asks the model for a price or labels anything "live".
- A saved `aiResult` is shown as an old estimate.
- The GSA lookup, by city and month.
- A missing rate is said, not guessed.
- The Google Hotels address is built.
- R8 holds on the narration.

*Recommended.*
