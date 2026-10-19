# Item 101 — Medical collections (item 45 H7 stage 7)

**RULED 2026-10-19 by Rob, in his words:** *"lets treat that as a debt but don't keep that in the debt payoff lets keep
that in medical and when a payment is make they can link that to the collections, and we can keep a running balance on
that collections. We don't need to worry about interest because they would add any fees to the balance anyway. I would
add to save our self a note that If they feel that this bill is not correct or no longer valid that they should consult
legal advice."*

The stage the health review left last, with "underbuild" a live answer. Ruled as a small, plain build.

## The rulings (C1-C6)

**C1. A debt, kept on the Health page.** A medical bill sent to collections is a debt the household owes, recorded on
the Health page under Bills. It is not a Debt Payoff card and does not enter the card-free date (Q7: card balances
only). It does enter the all-obligations date (item 94 L9) like any medical obligation: datable only with an agreed
arrangement.

**C2. It starts from the household's word.** "This bill went to collections with X" is the household's statement
(item 93): the collector, its account number, the date and the balance the collector states. The collection carries
the bill's obligation (minted then if the bill wasn't yet said to be theirs). From then on the original bill shows
"sent to collections" and its amount is counted only under the collection - never twice.

**C3. Payments link to the collection.** Exactly as a bill (item 94 L2/L5): each payment is the household's statement,
a card payment included.

**C4. A running balance, from the collector's own statements.** Each statement the collector sends sets the balance as
of its date; each payment linked after it lowers it. Shown line by line, oldest first, with the balance after each.

**C5. No interest, no fees invented.** Groundwork computes no interest and adds no fee. Whatever the collector adds
arrives in its next stated balance (C4).

**C6. One note, on every collection** (Rob's ruling, and the one place Groundwork names a step):
*"If you believe this debt isn't correct, or is no longer valid, consider getting legal advice before you pay or
agree to anything."* Nothing else is directed; Groundwork never contacts anyone (item 94 L10).

## Status

Ruled and BUILT 2026-10-19 (SCHEMA 20261019-collections, s245). A collection is a bill account whose issuer is the
collector (`medical_collections` links it to the bill it came from), so statements, payments, the arrangement, the alarm
(item 94 L6) and the dates (L9) work as a bill's. The two accounts share the bill's obligation - one debt that changed
hands, as the 2.0 records hold it (obligation_replaces is for a second obligation, which this is not) - and its
payments are split by the hand-off date: before it the bill's, from it the collection's. Collectors get no
non-profit question or claim box (those are about the hospital and the insurer). Checked in a browser: the collector
adding $25 between statements shows as the next stated balance, with the legal note beneath.
