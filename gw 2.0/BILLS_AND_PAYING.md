# Item 68 — Your bills, read from the source, checked against your buffer (and whether Groundwork pays)

Opened 2026-10-10. Rob: *"now the users will want this program to also pay their bills for them. They will want to
check their account, verify money is their with a preset buffer that the user set. ie always leave $2000.00 in my
checking and pay my utilities using my checking account."* Then: *"our agent can do this."* Then:

> *"what if groundwork ask the user hey your aep is coming up and according to your checking balance that was
> downloaded (date of transcript import into groundwork) you can pay this bill Would you like Groundwork to pay this
> for you .. Now the user told groundwork to do this and groundwork told the facts that it has and that are known,
> What could happen is the agent could login into two areas and get the utility bill, an email address that the
> utility company sends the bill get the balance and put that into the budget or have the agent log into the utility
> account and look at the balance and bring that into the budget into groundwork."*

And: *"if the transaction more than 24 hour old that should be a notice to the user that a transaction has not been
downloaded in the past 24 hours."* Then: *"yes open it as an item."*

**B1–B9 RULED 2026-10-10 (Rob: "approve B1–B9 as recommended"):** B3 (a), the bill shown beside the budget line;
**B8 (b): TM1 stands.** Groundwork takes the person to their bank's bill pay at that payee and stops; the person enters
the amount and presses Pay. (c) is to be revisited once B6 and B7 have run on real accounts. **BUILT 2026-10-10 (Rob: "build item 68") in three
stages:** 1 the bill read from its own website (bill_site / bill:<id> vault login / 'read' steps marking the label
beside each figure, every number masked / parse_amount, parse_due / bill_pending until the yes / the BillReading table,
SCHEMA_VERSION 20261010-bill-readings / the Budget page's card / "use the bill's amount for this month" derived in
budget_month_amounts; s177); 2 core/bill_check.py - can I pay this? against the person's floor with the 24-hour notice,
and paid? (s178); 3 "Take me to pay this" - the way to the bank's payment screen recorded once (pay:<id>), followed with
the bank account's login and device, the window held at the payment with the bill's facts on its bar; the
never-press-a-payment guard in clean_step, press() and the click step, checked in Node against the same names (s179).
Awaiting the full gate, a real run on Rob's AEP account and bank, and acceptance.

**Already decided (not reopened here):**
- The person starts every outside action; nothing is scheduled or unattended (item 65 AP7, TM2; Rob 2026-10-09).
- Groundwork never reads email or text messages (item 65 AP8). A bill that arrives by email reaches Groundwork as a
  PDF the person saves, through the existing import.
- Logins live in the operating system's vault; no third party sees anything (item 57).
- Every figure shows its working (transparency standard); every claim has evidence and fails closed (item 65
  RG1–RG6).

**What is NOT decided, and is this item's hardest point:** item 65 TM1 says *"Never pay bills or move money ... even as
a one-time convenience and even with a confirmation step."* B8 asks Rob whether to keep, narrow, or reverse it. Nothing
else in this item depends on the answer; B8 can't be built before B1–B6 exist, because a payment needs the bill they
read and the check they make.

## 1. What is true today (master 0057f88)

- **Utility bills in the budget are planned amounts or estimates.** A budget line (`BudgetItem`) carries a name, a
  category and a monthly amount; item 26 estimates gas and electricity from EIA prices; item 56 adds municipal
  utilities. No line carries the company's website, a due date, or what the bill actually says this month.
- **The bank agent (item 57, 67) signs in only to banks and cards.** Its logins and steps are keyed `account:<id>` /
  `card:<id>`; a utility company has neither.
- **The agent can already read a named figure off a page** and hand it back for confirmation: item 44's fare read
  (Google's total, named as Google's, confirmed before use).
- **Balances come from downloaded files.** A checking balance is as old as its last download; the file shows no
  pending charges or holds. Item 67's dashboard line says when each account was last fetched (after the person's
  number of days, 7 by default).
- **Nothing in Groundwork can pay.** No route, no agent step, no page action moves money (TM1).

## 2. Points for ruling

**B1. A bill's own website.** A budget line for a bill (a utility, phone, internet, insurance) can carry the company's
website, with the same https check and the same "Groundwork doesn't check this belongs to the company" wording as a
bank link. Its login goes to the vault under `bill:<id>`, and "Remember this computer" works as for a bank.
*Recommended.*

**B2. Show me once, for a bill: the agent learns where the amount and the due date are.** The person records the
route to the bill page, as for a bank download (item 57 A5, A13 pop-ups included). Then, still recording, they click
the amount due and the due date on the page, and Groundwork asks "Is this the amount due?" / "Is this the due date?".
What's saved is where those figures are (the label next to them), never the figures themselves.
*Recommended.*

**B3. Reading the bill: a fact from its source, confirmed before use.** On a run, the agent follows the steps and
reads the two figures. Groundwork shows them with their source and time: *"AEP: $142.37 due Oct 24 - read from
aep.com today at 9:14."* Nothing is used until the person confirms. A figure that won't read as an amount or a date is
named and left out, never guessed (AP9, RG5).
Where it goes, once confirmed:
- (a) **Beside the budget line**, as that month's bill: "Electric: planned $120, the bill says $142.37". The planned
  amount isn't rewritten; the person can choose "use the bill's amount for this month".
- (b) Replace the month's planned amount automatically.
*Recommended: (a).* (b) would let a read figure silently change a plan (TM3).
A confirmed reading is kept as a record (the line, the amount, the due date, when and where it was read), so the
budget can say where its number came from. That is a new table: a SCHEMA_VERSION bump and the s51 pin.

**B4. Bills in Get my accounts.** One press (item 67) visits the banks first, then the bills with saved steps, one at a
time; each window closes; each reading waits for confirmation in the same panel. The Ledger-style single button on a
bill's line reads just that bill.
*Recommended.*

**B5. Never from email.** Settled by AP8; recorded here so the item is complete. A bill PDF the person saves is
imported as statements are today, and its amount and due date are offered for the same confirmation as B3.
*Recommended (restates a settled rule).*

**B6. "Can I pay this?" - the check against your buffer, with the 24-hour notice.**
- The person sets a buffer per account, in their words: *"Always leave $2,000 in checking."* It's their statement,
  kept as one (it never changes on its own).
- For each confirmed bill coming up, Groundwork works out: the account's balance from its last download, minus
  confirmed bills due before it, minus this bill, against the buffer. It shows the working and the answer as a fact:
  *"Fits: checking would be $3,707.63, $1,707.63 above your $2,000."* or *"Would leave $1,636, $120 below your
  $2,000."*
- **The 24-hour notice (Rob).** If that account was last downloaded more than 24 hours ago, the notice comes first:
  *"Checking was last downloaded Oct 8, 2 days ago. Transactions since then aren't counted."* with **Get my latest
  transactions** beside it. Under 24 hours, the date is still shown.
- It always names what it can't see: pending charges, holds and checks not yet in the download.
- No verdict words ("safe", "you can afford it"); the facts and the working only.
*Recommended.*

**B7. Paid? - checking autopay and payments after the fact.** After each fetch, Groundwork looks for each confirmed
bill's payment in the account's transactions (the payee, the amount, near the due date) and says what it found:
*"AEP $142.37 paid Oct 22 from checking; checking stayed above your $2,000 (lowest $2,097 on Oct 22)."* or *"AEP
$142.37 due Oct 24: no payment seen yet (checking last downloaded Oct 23)."* A match is shown with the transaction it
rests on; a near-match is asked about, never assumed (AP2).
*Recommended.* This gives a person on their bank's autopay most of what "pay my bills for me" means: the payment
happens through the bank's own protected system, and Groundwork watches that it did, for the right amount, without
breaking the buffer.

**B8. Whether Groundwork pays - reopening TM1. Rob's ruling; the options are not equal.**
- **(a) Keep TM1.** Groundwork reads, checks and confirms (B1–B7); the person pays through their bank's bill pay or
  autopay.
- **(b) Take the person to the payment, and stop.** On "Pay this", the agent opens the bank's bill pay (by steps the
  person recorded) at that payee, and stops before anything is entered. The bar shows the bill's amount and due date
  and the buffer check; the person types the amount and presses Pay. TM1 holds: Groundwork moves no money.
- **(c) Groundwork pays, on the person's word each time.** TM1 is rewritten to allow it, with every one of these as a
  hard rule:
  1. **Asked every time, with the facts and their dates** (Rob's wording): *"AEP $142.37 is due Oct 24. Your checking
     showed $3,850 on Oct 10 (downloaded). Pay it from checking? Groundwork will check your live balance first and
     won't go below your $2,000."* Never on a schedule, never a standing instruction (TM2).
  2. **A live balance first.** Just before paying, the agent reads the available balance from the bank's own page.
     If it can't read it, or paying would go below the buffer, it stops and says why. A downloaded balance never
     decides a payment.
  3. **Only a payee already set up at the bank.** The agent never adds or edits a payee or an account number.
  4. **Only the confirmed bill's amount**, never more, and never above a per-payment cap the person sets.
  5. **The bank's confirmation is the proof.** Its confirmation number is read and recorded (Historian), and the
     payment is checked again on the next fetch (B7).
  6. **Anything unexpected stops it before Pay**: a different page, a changed amount, a pop-up asking to agree, a
     bot check, a second "are you sure" it didn't record.
  7. **Told before turned on.** The person is told plainly that a payment they approve is one they authorised, and
     that their bank may treat it that way if something goes wrong; Terms updated; off until turned on per account.
  8. **Its own real-bank tests** and Rob's acceptance, separately from B1–B7.

  Why the options aren't equal (said on 2026-10-10 and kept here): the balance a file shows is behind the bank's; a
  payment the person told software to make may not be covered as unauthorised; payment pages are where banks' bot
  checks are strictest; a wrong payment is hard to undo; and paying removes the decision Groundwork exists to teach.
  (c)'s safeguards answer the first and most of the second; they can't remove the rest.

*Recommended: (b) now, which gives the person one press to the right page with the facts in front of them, and
revisit (c) once B6 and B7 have run on real accounts.* Rob decides.

**B9. Lines and tests.** Master only.
- Reading: a figure read is the page's (a fabricated or changed amount refused; a stale reading named); nothing used
  unconfirmed (RG1, RG3).
- The check: the 24-hour notice at 24 h + 1 min, not at 23 h; pending charges named; the working shown; no verdict
  words; a buffer the person never set is never assumed (AP9).
- Paid?: a match shows its transaction; a near-match is asked; none is "not seen yet" with the download date (RG5).
- Crossings: no route reads email; nothing starts without a press; and, unless B8 (c) is ruled, **no agent step ever
  presses a control named like Pay / Submit payment / Send / Transfer / Confirm payment** - a mutation test plants one.
- One real run on Rob's AEP account and his bank before acceptance.
*Recommended.*

## 3. Not decided here

- **Paying anything that isn't a bill** (transfers between accounts, savings moves, card payments): not proposed.
- **Due dates for cards and loans** from their own sites: the same mechanism could read them; its own item if wanted.
- **Item 57 A12, recording the route**: still unruled; B2 would use it if ruled.
