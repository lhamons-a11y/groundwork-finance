# Item 48 — A fare or hotel total the user chose or typed is used to the cent

**ACCEPTED and CLOSED (Rob, 2026-10-08: "I accept items 47, 48 and 49"), gate 2566 / 0.** Opened and built 2026-10-08. Rob: *"when travel grabs the total from the airline web page it rounds the value up it
should grab the exact total since a good chance the user ordered it."* Master only.

## What was wrong

- **The trip budget rounded totals to whole dollars.** It applied `Math.round(_tripQuoteData.flightTotal)` to every
  fare (typed, pasted from a quote, or read from Google Flights by item 44), and did the same to a hotel quote's total.
  So a typed $612.48 became $612.
- **Google's own figure is whole dollars.** Item 44 reads the Continue button, which Google labels *"for 690 US
  dollars"*.
- **Groundwork does not read the airline's page.** It was ruled out in item 44, because every checkout differs.

So the exact total, with cents, is the one the user types from the airline's checkout into the fare box.

## What was built

- **`tripExactTotal()`** keeps a total the user chose or typed to the cent. That covers the flight total and the hotel
  quote total.
- **The planner's own estimates are still rounded,** because they were never exact: fuel, dining, activities, and a
  per-night guess.
- **Gate:** `s160`.
