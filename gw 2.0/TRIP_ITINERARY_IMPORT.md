# Item 60 — Bring in a whole itinerary and see the trip's budget

Opened 2026-10-09. Rob: *"figure out a way to import from expedia and other travel groups plans that the agent can
break apart and show the travel budget."* **No code yet:** I1–I7 need a ruling, and the build needs its own
go-ahead.

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
