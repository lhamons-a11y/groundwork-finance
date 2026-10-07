# Item 41 — The DOT average fare replaces the $220 guess

**ACCEPTED and CLOSED 2026-10-07 (Rob: "I accept item 41")** at `81e2588`, gate 2425 / 0.

Opened and ruled 2026-10-07 from the flight-fare follow-up to item 40 (`FLIGHT_FARES.md`). Master only: a new
feature, not a fix that L1 admits to 1.x, so 1.1 keeps its $220 fallback.

## 1. Rulings (Rob, 2026-10-07)

- *"yes replace the $220 with the DOT average … when users select the to and from flight that should show them the
  average cost of the flight … then have a link to google flights … the same as the cost of gas."*
- **A:** the user picks the From and To city from DOT's own list. **Ship the table** with the app.
- *"lets add a round trip button so the search grabs the 1st trip then reverse the trip search grab that price then add
  those cost together."*
- *"I would like the search to grab the latest data and not dependent on the user to always update to the latest
  version."*

## 2. The source

The **U.S. DOT Domestic Airline Fares Consumer Report** is public domain and published quarterly on
data.transportation.gov. It needs no key.
- **Table 6** (`yj5y-b2ir`) has every contiguous-state city-pair market averaging 10+ passengers a day: 6,313 markets
  across 317 cities in 2026 Q1.
- **Table 1a** (`tfrh-tu9e`) is by airport pair, only where one end is a city with more than one airport: 2,080 pairs
  in 2026 Q1.
- **The fare** is the *average one-way fare* fare-paying passengers actually paid, from DB1B's 10% ticket sample, using
  *"directional components of domestic itineraries"* (the report's data-source note). First class is included; free
  tickets are not.
- **DOT markets have no direction.** Chicago–Denver and Denver–Chicago are one row. The round trip Rob asked for (the
  outbound fare plus the reversed search) therefore adds the same average twice. Both legs are shown, so the working is
  visible.
- **Not covered:** Alaska, Hawaii and international routes, and routes under 10 passengers a day.

## 3. What was built

- **`core/airfare.py` + `core/data/dot_airfare.json`.** The table ships with the app, about 290 KB, inside the bundled
  `core/` folder. A lookup reads that table on the computer, so the user's route never leaves it.
- **Keeping current without a release.** When the Travel page opens, `POST /api/trip/airfare-refresh` asks DOT for its
  latest quarter, at most once a week. If that quarter is newer, it downloads that quarter's two whole tables into the
  data folder, and they are used straight away. The requests carry only the quarter, never a city, airport or route.
  A failed, partial or malformed download is refused, and the current table stays in use.
- **Release step:** `python -m core.airfare` writes DOT's newest quarter into the shipped table.
- **The Fly form:**
  - *Flying from* / *Flying to* pick from DOT's city list.
  - Airport codes are now optional. When both are given and DOT lists the pair, the airport-pair average is used.
  - A **Round trip** box, ticked by default, sets the number of legs.
  - The note under the form reads, for example: *"The average cost of this flight is $217.27 one way, Chicago, IL (ORD)
    → Denver, CO (DEN), and $217.27 back … Round trip: ($217.27 + $217.27) × 2 travelers = $869.08."* It names the
    source, the quarter, what the figure is, and that it is not a fare you can book.
- **The budget's flight line:** a fare the user typed in, then the DOT average × legs × travelers. With no DOT figure,
  flights are **left out of the total and the line says so**. The $220 guess is gone.
- **Google Flights link:** airport codes when both are given, otherwise the two cities. One way when Round trip is
  unticked.
- **Gate:** `s152_dot_airfare.py`, with DOT's API stood in for so the gate never touches the network. `s151` was updated
  for the city-aware link.

## 4. Not changed

- The trip total's *"AI will refine this"* label, and the trip planner's other built-in defaults: $140 a night,
  $45 a day dining, $50 a day activities, a 10% buffer, and the 400-mile placeholder. Each is an assumption under the
  transparency standard. They were not part of this ruling.
