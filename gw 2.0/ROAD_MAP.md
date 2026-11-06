# The road map: exact miles for a drive

Rob 2026-11-05: "if the road routing can get the user a more exact price on the trip that is something worth discussing", then a local open engine "that also goes out and downloads updates", then, on the trial's numbers, "Yes, build it".

## What it is

An optional download on Settings, Data. With it, a drive's miles come from the actual road route, worked out on this computer by Valhalla on a map of the main U.S. roads. Without it, or for a trip it can't route, the straight line plus 25% stays, and the Trip Planner says which one the figure is (transparency standard).

Place names are still looked up with OpenStreetMap, as before. Routing sends nothing.

## What was measured (2026-11-05, against the public OSRM server on the full map)

| Set | Today's estimate | Main-roads map | Wider map |
|---|---|---|---|
| 40 city trips (my choice, 14 hard): typical error | 8.3% | 0.3% | 0.3% |
| Over 10% off | 16 | 1 | 1 |
| 20 small-town trips, held out: typical error | 9.9% | 1.0% | 0.2% |
| Over 10% off | 9 | 3 | 2 |
| 30 parks, suburbs, rural roads: typical error | not measured | 0.7% | 0.2% |
| Over 10% off | not measured | 3 | 1 |
| Download | none | 343 MB | 543 MB |
| On disk (one file) | none | 801 MB | 1.2 GB |

The reference is two engines agreeing on OpenStreetMap's data, not an odometer. Largest round-trip fuel difference on the doorstep set: $4.99 (28 mpg, $3.40).

Three things tried and not shipped:
- **Retuning 25% to 17%.** Helped on the trips it was tuned on, and did worse on the held-out towns.
- **Adding the gap to the nearest main road.** Removed some worst cases, and made the typical trip slightly worse (1.1% against 0.7%).
- **The wider map.** Rob chose main roads on the numbers above.

## As built, and why

| Choice | As built | Why |
|---|---|---|
| Hosted | `groundworkfinance.app/static/download/road-map/` | The GitHub repository is private, so its release files can't be downloaded by users. The site is already an allowed host and already serves the installers. |
| Asked of the internet | Nothing until "Get the road map" is pressed, and the size is shown before it downloads. | No silent writing, no surprise. |
| Updates | With a map installed and "Keep the map current" on (the default), the planner asks at most every 30 days and downloads a newer map by itself. The box turns it off. | Rob asked that it download updates. No schedule: only when the planner is opened. |
| Replacing a map | Fingerprint, then a real route (Columbus to Cincinnati, 95 to 125 miles), then swap. Anything failing leaves the old map as it was. | |
| Memory | The router opens for one route and closes. Measured: 243 MB while routing, 52 MB after. | The narrator already holds 3.7 GB on an 8 GB machine. |
| Saved trips | Keep their figures until reopened and updated (TRIP_SAVED.md). | A map arriving doesn't change a figure the person saved. |
| A route shorter than the straight line | Not believed. The estimate stands. | Can't be true. |
| Ferries | Not used. Cape May to Lewes is the drive around, and the planner says it doesn't take ferries. | Fuel on a ferry isn't a mileage figure. |
| Intel Macs | No engine exists, so the app runs and the estimate stays. | |

## The licence (ODbL). My reading, not legal advice

- **Credit.** Apps with a routing engine or geocoder must credit OpenStreetMap, with a link to `openstreetmap.org/copyright`, and a printed map must print that address. Done on the Settings card, the Trip Planner, the printed itinerary (estimate too: the geocoder always needed it), the Help guide, and `THIRD_PARTY_NOTICES.md`.
- **Share-alike.** The map file is treated as a derived database. It is published under the ODbL, with `README.txt` and `build_road_map.py` beside it as the method.
- **The app's own licence.** Nothing found says a program using such a database takes on the ODbL. The sources don't state this outright. **Rob decides whether to have a lawyer read this before release.**

## For Rob

1. **Publish** (Rob publishes, never Claude): the `road-map` folder goes in `Website/static/download/`, with the Privacy page's new line. Until then, "Get the road map" says it can't be reached and the estimate stays.
2. **Confirm the host will serve a 343 MB file**, and range requests if possible. A download that can't resume starts again.
3. **Each refresh** is `python scripts/build_road_map.py`, over an hour on this computer, then publish. Nothing forces a schedule.

**Exit criterion:** a person presses "Get the road map" in the installed app against the published file, sees road miles on a real trip, and prints it.
