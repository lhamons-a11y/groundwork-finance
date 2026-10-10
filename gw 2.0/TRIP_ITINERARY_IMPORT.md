# Item 60 — Bring in a whole itinerary and see the trip's budget

Opened 2026-10-09. Rob: *"figure out a way to import from expedia and other travel groups plans that the agent can
break apart and show the travel budget."* **I1–I7 RULED as recommended (Rob 2026-10-09: "I accept item 59, 60, 62"). BUILT 2026-10-10 on master** (Rob: "build all items that have been ruled on"); see §3.

## 1. What is true today (measured 2026-10-09, master)

- **One quote at a time.** *Paste a quote or describe the trip* (`_readTripQuote`, Phase 5D) reads a single pasted
  lodging or flight quote, or a plain description, into strict JSON through the local model.
- **The numbers are checked.** Every dollar figure the model returns must appear in the pasted text (the same
  number-provenance check as the PDF statement reader), or it's nulled. Nothing fills the form until the user
  confirms.
- **What it can't take:**
  - a whole itinerary: flight plus hotel plus car plus activities, each with its own price, taxes and fees;
  - a PDF or a saved confirmation email.
- **Bookings exist (item 50).** *I booked it* records a booking per airline, and the trip's flight line follows it.
- **Groundwork never reads the user's email** (item 50, and *local only*). The user brings the itinerary.

## 2. Points for ruling

**I1. How the itinerary comes in.** The user pastes the confirmation text, drops a PDF (Expedia, Booking.com,
airline and hotel confirmations all offer one), or drops a saved email file (`.eml`).
- The file is read on the computer, by the existing PDF text reader.
- Nothing is fetched, and no account is connected.

*Recommended.*

**I2. Broken into parts.** The reader returns a list of components. Each is one of flight, lodging, car, activity,
transfer, insurance or fees, with:
- its dates;
- its price, taxes and fees as printed;
- whether it says paid, deposit or due later.

The model extracts; it never computes.
*Recommended.*

**I3. Every figure must be in the document.** It's the existing number check, applied per component. A figure the
document doesn't contain is dropped and said. The total is Groundwork's sum of the kept components, shown beside
the document's own printed total. If they differ, both are shown, never reconciled by guessing.
*Recommended.*

**I4. Confirm before anything is used.** The parts are shown as a list with checkboxes and an edit box per figure.
On a yes they become the trip's lines, each sourced *"from your Expedia itinerary"*. Paid parts can be recorded as
bookings (item 50), so their real charges match later.
*Recommended.*

**I5. Known formats first.** For the most common senders, a format reader that finds the fields without the model is
tried first: Expedia, Booking.com, and the big airlines and hotel chains. It's faster, and it works with AI off (A10).
The model handles everything else.
*Recommended.*

**I6. Privacy.** The document stays where the user put it. Groundwork keeps the extracted parts, never the file (item
20's custody rule). Confirmation numbers are handled as in item 50 B1: typed or extracted, kept out of logs, exports
and the narrator.
*Recommended.*

**I7. Lines and tests.** Master only. Tests:
- a sample itinerary of each known format;
- a model-read one with a planted figure that's not in the document, which must be dropped;
- totals that disagree are shown both ways;
- nothing is saved without confirmation;
- AI off works for the known formats.

*Recommended.*


## 3. Built (2026-10-10, master)

- **I1.** *Read as a whole itinerary* (pasted text), *Choose an itinerary file* (PDF, `.eml`, `.txt`, `.html`), or a
  file dropped on the card. `core/itinerary.py` reads it on the computer: PDF text by `pdf_statement.extract_text`,
  email by the standard library. Nothing is fetched.
- **I2.** Parts are flight, lodging, car, activity, transfer, insurance or fees, each with dates (a year is required,
  never assumed), its printed lines (price, taxes and fees, total), and paid / deposit / due later / not stated.
  A part with several lines and no printed total is summed by Groundwork and says *added up by Groundwork*.
- **I3.** Every figure is checked against the document with the statement reader's number check. A failed figure
  is dropped and named; so is a printed total the document lacks. The parts' sum is shown beside the document's
  total; when they differ, both are shown and the person is asked to check. A model answer that isn't the asked
  shape is refused whole.
- **I4.** A ticked list with an amount box per part; *Use the ticked parts for this trip* is the only way in. Used
  parts become the trip's lines: flights, lodging and activities on their own lines, and car, transfers, insurance
  and fees on a new **Other** line, each sourced *from your Expedia itinerary*. Empty trip dates are filled from
  the parts. A paid flight can also be recorded as a booking (item 50) when the destination is filled in; its
  booked-on date is the day it is recorded, which the person can correct on the booking.
- **I5.** Without a model: Expedia (its price summary), Booking.com, an airline receipt (18 named airlines), and a
  hotel folio (13 named chains). Anything else goes to the local model, and with AI off says so plainly.
  **Caution:** the four readers are written against representative layouts in `tests/itineraries.py`, not real
  confirmations. Each needs one real document before it is trusted; a layout they don't match falls through to the
  model (or, AI off, to the plain message), never to a wrong figure, because every figure is still checked.
- **I6.** Confirmation, itinerary, booking, reservation and reference numbers are taken out of the text before the
  model or the AI log can see it. Only a flight's number travels with its part, to the booking. The file is never
  written; the read and check routes write nothing. The used parts (without numbers) are saved with the trip budget.
- **I7.** s187: 16 checks. Each known format; a planted figure dropped; disagreeing totals shown both ways; nothing
  saved by reading; AI off reads the known formats; the lines' sources; the parts run in Node.
