# Item 50 — "I booked it": recording a booking without counting it twice

Opened 2026-10-08 (Rob: *"when the user selects the flight and got the final price they should have a button that said
I booked it. Then it would [record] whatever the user selected as how they are going to pay for it with the airline
name and the credit card confirmation if it see's it and put that in the logger"*; *"yes open item 50"*). **RULED 2026-10-08 (Rob: "approve B1–B8 as recommended"), including B3's tolerances (±$1.00, 7 days, the airline named, the chosen card or account).** **BUILT 2026-10-08 (Rob: "build item 50"): `TripBooking` (`trip_bookings`, SCHEMA_VERSION `20261008-trip-bookings`, fingerprint pinned, fixture saved), `core/trip_booking.py` (the B3 rule), the booking routes under `/api/trip/` (accounts, list, create, edit or cancel, candidates, match), the *I booked it* form, the bookings list and *Find the charge* in `app.js`, the flight line from the booking (B7), `s162` end to end.** **ACCEPTED and CLOSED (Rob, 2026-10-08: "I accept items 50 and 51"), gate 2601 / 0.** Master only.

## 1. What is true today (measured 2026-10-08)

- **Debit cards buy airline tickets.** Delta, American, Southwest and United all accept them for ticket purchases
  ([The Points Guy](https://thepointsguy.com/news/cashless-airlines/),
  [WalletHub](https://wallethub.com/edu/cc/book-flight-without-credit-card/25851)). PayPal can restrict which linked
  cards an airline takes. A booking can therefore be paid from a credit card *or* a checking account.
- **A card charge can already be recorded** as a `DebtLedgerEntry` (`charge`, amount, date, merchant). Recording one
  does **not** change the card's balance, which comes from statements.
- **A checking transaction can already be linked** to a debt ledger entry (`CheckingTransactionLink`), with the user's
  confirmation (`user_confirmed_at`), *"so nothing gets double-entered"*.
- **The real charge arrives later by import:** the bank's CSV/QFX for a checking account, or the card's statement or
  CSV for a card.
- **The trip planner knows** the airline (from Google's Continue label, item 44), the fare (item 44, or typed, item 48),
  the dates, the travelers, and, if chosen, the card (item 49).
- **Item 44's exception covers one figure only:** the Continue button's price, on Google's page. Nothing on an
  airline's page is read.

## 2. What it would do

After the user has chosen a fare, an **I booked it** button opens a short confirmation:
- the airline;
- the exact amount (pre-filled from the fare box, editable, to the cent);
- **paid with**: the user's credit cards *and* checking accounts;
- the date;
- an optional confirmation number, typed by the user.

Saving records **a booking**, tied to the trip. When the real charge is imported, Groundwork offers to match it to the
booking. It is not counted a second time.

## 3. Points for ruling

**B1. The confirmation number is typed, never read.**
- Groundwork does not read the airline's confirmation page. That would be a second page read, beyond item 44's one
  figure.
- The field is optional.
- A confirmation code with the traveler's last name is enough to change or cancel the booking, so it is stored like
  the rest of the financial record and never placed in a log, an export summary or the narrator's input.

*Recommended.*

**B2. A booking is a planned record, not a transaction.**
- It does not enter the Ledger's spending, a budget total or a card balance.
- It is shown on the trip as *Booked: Delta, $612.48 on Visa, Nov 1 — waiting for the charge*.
- The money is counted once, when the real charge arrives.

*Recommended.* A transaction written now and imported later would be counted twice, the very failure
`CheckingTransactionLink` exists to stop.

**B3. Matching the real charge, with the user's say.** When an import brings a charge on the chosen card or account,
within ±$1.00 of the booked amount, dated within 7 days of the booking, from a merchant naming the airline, Groundwork
asks: *"Is this your Delta booking for Nov 1?"*
- **Yes** links the two. The booking shows *charged*.
- **No** leaves both as they are.

Nothing links without the user's yes. *Recommended.* The tolerances are for ruling. A foreign-currency fare or a
split payment may not match, and then the user can link it by hand.

**B4. Paid with: credit cards and checking accounts.** The list is the user's active credit cards (as in item 49) and
their checking accounts, so a debit-card purchase is covered. *"Other / not listed"* records the booking with no
account, and it is never matched automatically. *Recommended.*

**B5. The booking is recorded; nothing is learned from it.**
- The button is an explicit act, so recording the booking is not silent writing.
- But a pattern across bookings, such as *"usually flies Delta"*, *"prefers direct"* or *"uses the Visa"*, is a
  conclusion drawn from usage, which item 39 U7 rules out.
- Groundwork records each booking as the user entered it and derives nothing about the person from them.

*Recommended.* (The same line as the 2026-10-07 discussion of direct versus cheapest flights.)

**B6. Changing or cancelling.**
- A booking can be edited, or marked *cancelled*, with a refund expected.
- A cancelled booking is kept and shown as cancelled, never silently deleted.
- A refund is matched like a charge (B3), as a credit.

*Recommended.*

**B7. The record's lifetime and the trip's cost.**
- While waiting for the charge, the trip's flight line shows the booked amount, labelled *booked*.
- Once the charge is matched, it shows the charged amount, labelled *charged*. That is the figure the user actually
  paid, and the one item 39's transparency standard prefers.
- If the two differ (fees, currency), both are shown.

*Recommended.*

**B8. Schema.**
- A new `trip_booking` table: trip, airline, amount, account or card, date, optional confirmation, status
  (`booked`, `charged`, `cancelled`), and the linked transaction or ledger entry.
- That needs a `SCHEMA_VERSION` bump and the s51 fingerprint pin (`SCHEMA_VERSION gates migrations`).
- Master only. Gate: render-level checks, plus the double-count mutation (an imported charge counted alongside an
  unmatched booking).

*Recommended.*

## 4. Not decided here

- Hotels and car rentals: the same shape could follow, but car rentals are stricter about debit cards. That would be
  its own item.
- Reading an airline's confirmation email: out of scope. Groundwork does not read the user's email.
