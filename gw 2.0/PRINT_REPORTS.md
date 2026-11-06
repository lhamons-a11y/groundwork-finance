# Printing: every page is a report

Rob 2026-11-05, the last item before 2.0 testing: "every page should be printable as a professional looking report that is easy to read and follow."

**ACCEPTED 2026-11-05** (Rob, once the gate passed: "I accept and push"; gate 4380/0). P-a to P-c below are kept as built.

## How you ask

- **AI on:** say or type "print this page". "Print the budget" opens the Budget and prints it.
- **AI off:** a Print button stands where the Ask box was. The microphone stays and takes the same words.
- **Ctrl+P:** gives the same report for the page in front, so it no longer prints a blank sheet.

## What prints

| Page | Report |
|---|---|
| Any page | The page redrawn on its own sheet (`static/js/print.js`). What you press is left out, what you typed is shown as text, an unfilled form is left out, and the working behind a figure stays open. |
| Ledger | Asks first: **detail** (every line showing) or **overview** (totals by category and biggest places). "Print the ledger overview" skips the question. Totals follow the Ledger's own rule for In and Out. |
| Trip Planner | An itinerary. Driving: a map and the distance each way and round trip. Flying: a ticket for each flight with its date and price. Both carry the start-to-finish list and the costs with their sources. The Your trips tab prints the saved trips. |
| Before You Buy | The cost of the item and a possible future budget (below). On the After you buy tab, or with nothing entered, the page itself. |
| Net Worth | The Report Center's Net Worth Timeline, the same code (`_rcNetWorthTimelineHTML`). With no saved months, the page itself. |
| A report in the Report Center | That report on the same sheet. Its Print buttons used to print blank, because the app-wide print rule hid the shell around them. |

## The map

Drawn on this computer from a simplified outline of the lower 48 states and a list of cities. No map service is asked. The two ends come from the geocoder the trip distance already uses (`/api/trip/route-points`): the same two place names, and nothing when they are cached.

It shows the two ends and a straight dashed line, labelled with the same road estimate the trip budget uses (straight line plus 25%). **It is not a road route** and says so. Outside the lower 48 the line and the distance are right, on open background.

## The possible future budget

`core/budget_projection.py`, not stored. Shown for today and 1, 2, 3 and 5 years.

- Everyday budget lines rise by the assumed rate, compounded yearly.
- Income stays at today's: no raise is assumed, because none is known.
- Debt minimums and set-asides stay at today's: they are amounts, not prices.
- A loan, lease or financed purchase stays fixed and stops when its term ends. A subscription or other running cost rises.

The report says, in words: this is a projection, not actual inflation; the rate is Groundwork's illustration; and it cannot account for other expenses that are not known.

**Assumed rate: 3% a year.** Rob named no rate. `ASSUMED_INFLATION_PCT` is the one place to change it.

## What it does not show

A ticket has no flight times or numbers, because Groundwork does not hold them. A booking's confirmation number is never printed (TRIP_BOOKED.md: kept out of logs, exports and the narrator).

## For Rob to look at

| # | Question | As built |
|---|---|---|
| P-a | The assumed inflation rate | 3%, named on the page as an illustration |
| P-b | The map | The two ends and a straight line, drawn offline. Real roads would mean sending the trip to a routing service. |
| P-c | The Settings and Assistant pages | They print like any other, as "every page" said. |

**Exit criterion:** printed on paper from the installed app, by a person, on each page. The PDFs checked so far came from Edge against the sample household.
