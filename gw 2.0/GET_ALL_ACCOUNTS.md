# Item 67 — Get all my accounts, with one press

Opened 2026-10-09. Rob: *"users ask is we have the account automatically have the accounts pull into Groundwork like
if we used Plaid. That takes the oh god I have to click buttons pain away."* Then: *"I do like the get all of my
accounts that could be in the header the dashboard wherever it make logic."*

**Already decided by Rob (2026-10-09):**
- No scheduled imports. The person starts every bank visit (item 57, item 65 AP9). Rob: *"Understood no need to
  schedule the imports."*
- The fetch window always closes itself when its run ends (item 57, built 3c315b8).
- Nothing leaves the computer: bank → the user's computer → Groundwork. No middleman holds a login (the difference
  from Plaid).

**Depends on item 57 being accepted.** Item 57's single-account fetch must pass Rob's real-bank run first. This item
only runs it for several accounts in turn.

## 1. What is true today (fix branch, 2026-10-09)

- Settings → *Fetch my downloads* lists each account and card that has a bank link. Each one with saved steps has its
  own **Get my latest transactions** button. One press = one account.
- Each fetch opens its own window, runs the saved steps, closes, and records one `statement_fetched` event (A11): the
  account, the outcome, why it stopped, the step it stopped on, the file's name and hash.
- The folder watcher queues each download and offers it for import, **one file at a time**. The import review asks
  which account the file belongs to, even though the fetch already knows.
- Nothing on the dashboard or the header mentions fetching.

## 2. Points for ruling

**G1. What one press does.** One press visits every account that has saved steps, **one at a time**: account A's
window opens, runs, closes; then account B's. They run in the order accounts are listed. One press starts the batch.
The list of accounts it will visit is shown as it runs, so nothing is visited without being named.

A stop stops the batch, in two cases:
- **the user presses Stop**: the open window closes, and the rest are skipped and listed as skipped;
- **a bank shows a bot check**: the batch stops at once, because carrying on would look like the pattern banks flag.

Any other stop (a step not found, a code not entered, no download) ends that account's run only, and the batch moves
to the next account.
*Recommended.*

**G2. Where the button lives.** Two places, one action:
- **(a) The header**, next to Reports: **⟳ Get my accounts**. It's always reachable, on every page. It's shown only
  when at least one account has saved steps; otherwise it isn't there at all.
- **(b) The dashboard**, as one line from the record (G3) with the same button beside it.

Settings keeps the per-account buttons for running one account alone.
*Recommended: both (a) and (b).*

**G3. The reminder, read from the record.** The dashboard line states a fact from `statement_fetched`, never a verdict:
*"Last fetched: Superior Checking 8 days ago, Harbor Card 3 days ago · Get my accounts."* It appears once the oldest
fetch is 7 days or more. The user can change the number of days or turn the line off.

It reads the record only: no timer, no pop-up, no notification. Opening the dashboard is the only time it's checked.
This is Rob's dashboard anticipation aim of 2026-09-30 (upcoming facts from the record, never from watching the user), applied to fetching.
*Recommended.*

**G4. Progress in one place.** One panel (it drops down from the header button, or opens under the dashboard line)
shows a line per account, in words:
- waiting;
- signing in;
- **your bank is asking you something: the window is in front**;
- downloaded (file name);
- stopped (why, in item 57's words);
- skipped.

The panel has a **Stop** button. When the batch ends, the panel stays until the user closes it, so the outcome is
never missed.
*Recommended.*

**G5. Codes.** When a bank asks for a code, that account's window comes to the front with its bar ("Your bank is
asking you something"). The user types the code into the bank's own page. The batch waits, using item 57's 5-minute
code wait. A code is never asked for or typed through Groundwork: it would train the habit the "read me the code"
scam relies on (discussed 2026-10-09; Rob agreed to drop scheduling for the same family of reasons).
*Recommended.*

**G6. Importing what came in.** Every file still goes through the import review; nothing reaches the record without
the user's confirmation ("no silent writing").

Two changes:
- **(a)** The review starts with the account the fetch was for already chosen. The file is matched to its
  `statement_fetched` event by content hash, not by name or guess. The user can still change the account.
- **(b)** After a batch, the files are offered in turn with a count: "1 of 3: Superior Checking".

A single combined review screen for several files is a bigger change to the import review; it isn't proposed here.
*Recommended: (a) and (b).*

**G7. Several accounts at the same bank.** Each account runs its own saved steps, with its own sign-in. A remembered
device (A7) keeps that from meaning a code each time. Sharing one sign-in across a bank's accounts, or downloading
several accounts in one visit, is not attempted: each recording describes one account's route, and guessing a second
route is what A5 forbids.
*Recommended.*

**G8. The record.** Each account's run records its own `statement_fetched` event, exactly as today, plus a `batch`
id shared by the runs from one press. "Fetched together" is then a fact in the Historian, and no single event changes
shape.
*Recommended.*

**G9. Lines and tests.** Master only. Tests:
- one window at a time;
- Stop ends the batch, and a bot check ends it at once;
- other stops move on;
- no batch starts without the press: no timer, and the dashboard line reads only;
- the reminder reads only `statement_fetched`;
- a code is never relayed;
- the review's account comes from the hash match;
- the header button is absent with no saved steps.

One real run on Rob's accounts before acceptance.
*Recommended.*

## 3. Not decided here

- **Recording the route (item 57 amendment A12)**: the sign-in page's real address, page addresses, control kinds.
  It would make each run sturdier; it's separate.
- **Assistant by voice** ("get my accounts"): Assistant's own build, calling the same start (item 57 A2).
- **A combined multi-file import review**: named in G6, not proposed.
- **Signing out of the bank before the window closes**: offered 2026-10-09, not asked for.
