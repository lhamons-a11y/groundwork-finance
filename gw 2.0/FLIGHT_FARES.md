# Item 40 — Flight prices that need a key nobody has

**ACCEPTED and CLOSED 2026-10-07 (Rob: "I accept item 40")** at lts `e266a78` / master `6957bcf`.

Reported 2026-10-07 by Rob: *"When users are using travel and click the flights they are getting an api key missing."*
Fix approved the same day. On which lines it goes: *"if the users can't get a price to budget then this is a potential
data loss"*, so L1 admits it to 1.x. It is built on `lts/1.x` first and merged forward.

## 1. What happened

- **Travel → Fly → "Search live flight prices"** called SerpApi's Google Flights service through
  `/api/trip/flight-price` (`flight_price.py`, built `34a4f96`). That needs a SerpApi key, which the user was told to
  add as `FLIGHTS_API_KEY` in `config.json`. Groundwork ships no key, and a user has no reason or way to get one.
  Every click answered *"No flights API key configured yet — add FLIGHTS_API_KEY to config.json"*.
- **No user ever got a live price.** The module's own notes say it was never run against a real key.
- **With no price, the flight cost was a fixed $220 per person** marked *"AI will refine"*. The user could still type a
  fare, but only through the *paste a quote* box, which needs the model.

## 2. What was ruled out

- **Ship Groundwork's own key.** SerpApi's free tier is 100 searches a month for the whole key, not per user, so a
  shared key runs out or becomes a paid bill on every search. Each search would also send the user's route and dates
  to a third party under Groundwork's account.
- **Ask the user for their own key in Settings.** That still sends their route to a third party, and few people will
  sign up for a developer service to plan a trip.

## 3. What was built

- **F1. The keyed search is gone.** `flight_price.py`, the route, `_get_flights_api_key`, and the module's
  PyInstaller entries are removed. The `flight_price_cache` table is kept, unwritten, so there is no schema change and
  no `SCHEMA_VERSION` bump.
- **F2. "Look up fares on Google Flights"** opens a Google Flights search for the form's airports, dates and number of
  travelers in the user's own browser (`openExternal`). Groundwork itself sends nothing. It needs both 3-letter codes
  and a departure date; with no return date it searches one way.
- **F3. "Flight total for all travelers ($)"** is a plain number box. What is typed there becomes the trip's flight
  total. It fills the same `_tripQuoteData.flightTotal` the budget already reads, so the budget math is unchanged.
  A pasted quote's flight total fills the box too, clearing the quote empties it, and clearing the box keeps a
  pasted lodging total. It works with AI off.
- **Gate:** `s151_flight_fares.py`. It runs the three functions in Node and checks that nothing in a shipped file
  still names the keyed search.

## 4. Not changed, still open

- **The $220 per person fallback**, and its *"AI will refine"* text, when no fare is entered. Cloud AI is removed, so
  nothing refines it, and under the transparency standard (item 39 U7) a figure that cannot show its working is not
  shown. Raised 2026-10-07; ruled the same day and built on master as item 41 (`DOT_AIRFARE.md`): the DOT
  average fare for the route replaces it. 1.x keeps the $220.
