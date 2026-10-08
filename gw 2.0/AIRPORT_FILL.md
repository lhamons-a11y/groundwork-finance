# Item 43 — Picking a city fills its airport

**ACCEPTED and CLOSED 2026-10-07 (Rob: "I accept item 43")**, gate 2454 / 0.

Asked 2026-10-07 by Rob. Master only. What he asked for:
- *"when someone enters the city in the trip planner and select fly the airport code should appear … if their is two
  different airports for that city then the user should be asked which airport? Then that airport code will appear."*
- *"the DOT flight average should appear near the google flight area. That way the user can see if they are taking a
  trip to that area at a good time depending on google flight prices."*

## 1. Where the airports come from

Each DOT city's airports ship in the DOT table (`core/data/dot_airfare.json`, key `airports`). They are built at
release by `python -m core.airfare` from two public BTS sources:
- **BTS's airport list** (`L_AIRPORT`) gives each airport code its city, as *"City, ST: Airport name"*. It is matched
  to DOT's city names. A DOT city named for several cities, such as *"Dallas/Fort Worth, TX"* or
  *"Gulfport/Biloxi, MS"*, matches any of them. DOT's own airport-pair table adds the airports it names for each city.
- **BTS T-100 passenger counts** (data.bts.gov `r495-tyji`, the last 12 months) decide which airports are offered:
  - an airport needs at least 2,000 domestic boardings a year, and at least 3% of the city's busiest airport;
  - this drops business-jet fields beside a big airport (Denver's Centennial, Chicago Executive) and keeps real
    second airports (Midway, Love Field, Mesa Gateway);
  - a military-only field (an AAF or AFB without "International", "Regional" or "Municipal" in its name) is dropped;
    joint-use airports such as *"Charleston AFB/International"* are kept.

**The result for 2026 Q1:** 311 of DOT's 317 cities have their airports, busiest first. 13 offer a choice: Chicago,
Washington, New York, Los Angeles, San Francisco, Boston, Dallas, Houston, Miami, Tampa, Phoenix, Cleveland and
Columbus OH.

**No airport is filled in for six cities:** Belleville IL, Hot Springs AR, Killeen TX, Quad Cities, Steamboat Springs
and Valparaiso FL. Their airports are named for another town, or are military-joint fields under a base name, so the
user types the code.

A DOT refresh between releases keeps the shipped airports. They change far more slowly than fares.

## 2. What the user sees

- **A city with one airport fills its code in** as soon as the city is picked.
- **A city with several asks "Which airport?"**, with a button for each, for example *ORD · Chicago O'Hare
  International*, *MDW · Chicago Midway International*. The code picked is filled in.
- **A code the user typed themselves is never replaced** by a city pick.
- **The DOT average now sits directly under the Google Flights button.** It ends *"… compare it with the fares Google
  Flights shows for your dates."* It states the average and leaves the comparison to the user, with no judgement of
  whether a fare is good.

## 3a. The trip's own cities (found by Rob 2026-10-08)

Rob tested it: *"I put in the destination and home city I hit fly the airport code did not go into the airport code."*
- **What was wrong.** The trip form has two pairs of city boxes: *Destination* and *Home city* at the top, and *Flying
  from* / *Flying to* inside the Fly section. Only the second pair filled airports, and nothing connected the two, so
  a user who filled the top of the form and chose Fly got nothing.
- **The fix.** Choosing Fly, editing either top box while Fly is chosen, or the city list arriving carries Home city
  into *Flying from* and Destination into *Flying to*, and their airports fill in as above.
  - The match is to DOT's own city list: the city with or without its state, common names (NYC, Washington DC,
    Saint Louis), and a city inside a two-city name (Dallas → Dallas/Fort Worth, St. Paul → Minneapolis/St. Paul).
  - Only an unambiguous match is used. "Columbus" with no state is three DOT cities, and "Disney World" is none, so
    nothing is guessed. The Fly section says the name did not match one city and asks the user to pick it.
  - A *Flying from* / *Flying to* city the user chose themselves is never replaced. Nothing is carried for a drive.
- **Gate:** s154 A5.

## 3. Gate

`s154_airport_fill.py`:
- the matching rule, on a small fixture: business-jet fields, military fields, joint use, two-city names;
- the shipped coverage;
- the refresh keeping the airports;
- the note's place on the page;
- the fill-in and the question, run in Node.

`s152` was updated, because the city list now carries airports.
