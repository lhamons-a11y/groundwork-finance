# Coming back to a saved trip

Rob 2026-11-05: if someone says they are saving or using money for a trip, should Groundwork keep the trip so they can pull it up and revisit it as it gets closer? It mostly did already (TRIP_FUNDING_COACH.md, item 61). This finishes it inside "Your trips", which has its own tab on the Trip Planner (Rob, same day), with no new page. Rob: "Yes, add them."

## What changed

1. **The trip's costs on its card.** Each line and where its figure came from, not only the total.
2. **Open in the planner.** What was typed is now kept with the trip (`trips.planner_json`): places, dates, travelers, car, flight details, a quote or itinerary in use. Opening it puts that back and works the trip out at today's prices.
   - The saved trip does not change until "Update this trip" is pressed. The page shows saved against today's figure first.
   - The name stays on an update, because a flight booking finds its trip by name (TRIP_BOOKED.md). A different destination is a new trip, and the page says so.
   - A trip's fund follows a changed departure date. Sources are left alone: when they add up to more than the new total, the card says so.
   - A finished trip is never changed. Its button is "Start a new trip from this one".
   - A trip saved before this has no details, so only its name and dates come back, and the page says so.
3. **Saying it.** "I'm saving for this trip", "I'm using money for a trip", "we're going on a trip" and similar offer the button. They save nothing: only the tap makes a trip one the person is going on (T1, TM5). "Your trips" is a page to the voice like any other: it and "my trips" open the tab; "trips", "trip planner" and "plan a trip" open the planner.
4. **Printing.** Each tab prints what it shows: Plan a trip the itinerary, Your trips the saved trips.

A confirmation number is never kept in the saved details, at any depth (B1).

**Exit criterion:** a real trip saved, closed, reopened and updated by a person in the installed app. Checked so far in the dev server against the sample household, and by s289.
