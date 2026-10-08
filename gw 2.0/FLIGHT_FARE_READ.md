# Item 44 — Reading the chosen fare from Google Flights

Opened 2026-10-08 (Rob: *"is it possible for the agent to grab to final cost from the airlines page and put that in
the cost so the customer doesn't have to paste anything"*; *"yes open item 44"*). No code.

**RULED 2026-10-08 (Rob: "I accept R0 (a) and R1-R8").** Google's price is read on the user's Continue click, named as
Google's, confirmed before use, flights window only. BUILT 2026-10-08 (Rob: "yes build item 44"): flights_window.py, s156, gate 2503 / 0. Tested live: Continue on Economy delivered $774.30, the fare clicked, and United's page still opened. The gap between Google's price and the
airline's final total (section 1) is still unmeasured.

## 1. What is true today (measured 2026-10-08)

- **The flights window never reads a page.** Google Flights opens in Groundwork's own window (item 42), which runs in
  the bank window's separate, private process (`bank_window.py`). That process inherits the bank ruling
  (`BANK_BROWSER.md` F1): Groundwork *"receives no page state, performs no interaction"*. s126 enforces it: a page
  read (`evaluate_js`, `js_api`, a DOM read) anywhere in `bank_window.py` fails the gate.
- **The user types the fare.** They pick flights in that window and type the total into *Flight total for all
  travelers*. It replaces the DOT average in the trip budget.
- **Airline pages cannot be read reliably.** Each airline lays out its checkout differently and changes it often.
  United's, reached by *Continue* on 2026-10-08, opens at *Traveler Info*, with the fare beside a passenger form. The
  airline's final price can also move with seats and bags chosen there.
- **Google's booking page carries the chosen fare in a fixed form.** Each booking option's button says, in its
  accessibility label, for example: *"Continue to book with United, Basic Economy for 690 US dollars"*.
  - It is the same wording for any airline, and labels change far less often than layout.
  - **The figure is the total for all travelers, for the whole trip.** The same United round trip was $345 for one
    adult and $690 for two (measured 2026-10-08).
  - The trip it covers (airports, dates, travelers, round trip or one way) is the one Groundwork built into the search
    address (item 42), so Groundwork already knows it.

- **Google's figure is not always the airline's final cost** (Rob, 2026-10-08: *"the airline page ha the additonal
  taxes that google doesn't show"*). Google's booking page says its prices *"include required taxes + fees"* and
  that *"Optional charges and bag fees may apply"*. The airline's checkout can still show a higher total. Not yet
  measured: how large the gap is, and whether it is the airline's taxes, its fees, or optional extras such as seats
  and bags. On 2026-10-08 United's checkout showed *Fare $508.24* for the $690 trip, with its total further down the
  page and not read. The difference is unknown.

## 2. Points for ruling

**R0. What the figure is called, given the gap.** Before R1-R8:
- **(a) Google's price, named as Google's** (*recommended*). The prompt reads: *"Google Flights showed $690.00 for this
  trip (2 travelers, round trip). The airline's checkout may add taxes or fees. Use $690.00, or enter the airline's
  total?"* The trip budget labels the line *"from Google Flights"*, never *"final"*, so it reads as an assumption
  under the transparency standard. The fare box stays editable for the airline's own total.
- **(b) Read the airline's own final total instead.** That needs one reader per airline checkout, each laid out
  differently and changed often, and the total often appears only after passenger details are typed. It is not
  reliable enough to put into a budget (see section 1).
- **(c) No read; keep typing the airline's total**, as now.

Measure the gap before ruling (a): the same itinerary's Google price against the airline's final checkout total, for
a few airlines. *(Rob holds the observed example; the amounts would go here.)*



**R1. The exception, and its edges.** The Google Flights window may read **one figure**: the price in the label of the
*Continue* button the user clicks, on a page at `https://www.google.com/travel/flights/booking`.
- Nothing else on the page is read or kept.
- A bank window gains nothing. s126's crossing rules stay as they are for every window except this one.
- The flights window keeps everything else: private, no sign-in kept, no automation, no clicks made for the user.

*Recommended.* It is the narrowest read that removes the typing.

**R2. Read on the user's click, not by watching.**
- The figure is read only when the user clicks *Continue*. That click is the user choosing that fare.
- Browsing, hovering and comparing are not observed, and nothing about the page is recorded before or after.

*Recommended.* Under the no-silent-learning rule, a usage observation never persists. This reads a figure the user
chose, at the moment they chose it.

**R3. The channel back is one number.**
- The window process sends one line to Groundwork: `fare <amount>`, digits and a decimal point only.
- The amount must be over $0 and at most $100,000, and is checked again on Groundwork's side.
- The label is parsed only by the fixed pattern *"for N US dollars"*. Another currency or another wording means no
  figure.

*Recommended.* It is the same shape as the window's fixed status lines today. Nothing from the page can travel in it
except a number.

**R4. The user confirms before anything is used.**
- The trip planner shows: *"Google Flights showed $690.00 for this trip (2 travelers, round trip). Use it?"*
- Only *Use it* fills the fare box. *No thanks* discards the figure. Nothing is written without that choice
  ("no silent writing").

*Recommended.*

**R5. When it cannot be read, nothing is filled.**
- A changed label, another currency, a page that is not Google's booking page, or a click on something other than
  *Continue* gives no figure, and the fare box stays as it is.
- Failing closed under *capable is not admissible*: a guessed price is worse than an empty box.

*Recommended.*

**R6. Said plainly on screen.**
- The note under the button changes from *"Groundwork reads nothing from it"* to *"Groundwork reads one thing from it:
  the price on the Continue button you click, which it asks you to confirm."*
- The Terms and the privacy wording (item 37) say the same before it ships.

*Recommended.* The current note would become untrue.

**R7. Where the read lives.**
- The read is set up only in the Google Flights branch of the window process: a click listener on the page, and one
  function the page may call with the label.
- s126 is widened so this is allowed only when the window is Google Flights. New mutations must fail the gate:
  - the read reaching a bank window;
  - anything but a number crossing back;
  - a read without a click.

*Recommended.*

**R8. Master only.** It is a new feature (L1).

## 3. Not decided here

- **Recording the chosen fare in the historian, and "prefers direct" / "cheapest".** Raised 2026-10-07 and left
  unruled. This item only fills the fare box once the user confirms.
- **Reading airline pages.** Ruled out above as unreliable. A later item could revisit it.
