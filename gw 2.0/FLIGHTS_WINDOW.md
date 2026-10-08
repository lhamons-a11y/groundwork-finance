# Item 42 — Google Flights in Groundwork's window, already filled in

**ACCEPTED and CLOSED 2026-10-07 (Rob: "I accept item 42").** Also on 1.x (lts `3871d77`), by Rob's ruling, in the user's browser.

Asked 2026-10-07 by Rob: *"In 2.0 the google flight link should open in the groundwork app web browser and it should
have the airport that the user entered already in the google flight search."* Master only.

## 1. What was wrong

- **The search never got filled in.** The link from item 40 put the trip in Google's `?q=` search text. Google
  ignores that and opens its Flights front page on the user's own local airport. On 2026-10-07 it showed "Dayton",
  with nothing about the trip.
- **Google fills a search in only from its encoded form, `tfs=`.** That is a small protobuf of the legs, passengers,
  cabin and trip type, base64. `/travel/flights/search?tfs=…` opened "Chicago ORD → Denver DEN, round trip,
  2 travelers, Nov 1 – Nov 8" with fares listed, and the one-way form opened "One way · Chicago ORD → Denver DEN ·
  Sun, Nov 1".
- **Google does not document `tfs=`.** If it stops being read, Google shows its front page, which is where the old
  link went anyway.

## 2. What was built

- **W1. `core/airfare.google_flights_url()`** builds the `tfs=` search from both airport codes, the dates and the
  number of travelers. It produces two legs for a round trip, one leg one way, 1–9 adults, economy. A bad code, the
  same airport twice or a malformed date builds nothing.
- **W2. `POST /api/trip/flights-window`** builds the address on the server from the form's fields. The page cannot
  name any other address to open.
- **W3. It opens in the bank window's separate, private process** (`bank_window.py`, `BANK_BROWSER.md`).
  - The process is given only the address, the same single stdin line as for a bank, so the s126 crossing rules
    hold unchanged.
  - It keeps no sign-in (`private_mode`). Groundwork reads nothing from the page.
  - Its title comes from the address alone: "Google Flights".
  - A new search replaces the window on screen.
  - **Open in my browser** is the escape hatch (F10). It is offered beside the result, and automatically when the
    window engine is unavailable.
- **W4. The button needs both airport codes and a departure date**, and says so. With only cities picked, the DOT
  average still shows (item 41), but the search cannot be filled in from a city name. Round trip unticked sends no
  return date.
- **Gate:** `s153_flights_window.py`. It decodes the address back into legs, travelers and trip type, stands in for
  the window process, and runs the button in Node. `s151` was trimmed to the fare box.

## 2a. Continue to the airline (found by Rob 2026-10-08)

- **The fault:** *"when I am clicking continue in google flights another window is opening and i am getting a 404
  error"*.
- **The cause, measured.** Google's *Continue* posts a form (fields `u`, `w`) to `/travel/clk/f` with
  `target=_blank`. pywebview hands every new window to the system browser by its address alone, so the browser
  requested `/travel/clk/f` with no form, and Google answered 404.
- **The fix, measured before and after.** In the Google Flights window only, the new-window request is left
  unhandled. WebView2 then opens the window itself, in the same private process, carrying the form.
  - Proved with a local form server: handed over, the server saw a bare address; left unhandled, it received the
    POST and both fields.
  - Then in the real window: Continue opened United's own page at *Traveler Info*, ORD → DEN, 1–8 Nov, 2 adults.
- **Banks are unaffected.** A bank window keeps pywebview's handling (`BANK_BROWSER.md` is unchanged), and s126's
  crossing rules all hold.
- **Gate:** s153 W5.

## 3. Not changed

- **Downloads are on in that process**, as they are for a bank (F1, F6). A file saved from Google Flights would land
  in the watched Downloads folder like any other file and go through the same review. Groundwork imports nothing
  without the user.
- **1.x** got the same encoded search by Rob's ruling ("bring the filled-in search to 1.x too"), opened in the user's
  browser: 1.x has no in-app window.
