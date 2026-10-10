# Item 69 — An Automation page in the Assistant group

Opened 2026-10-10. Rob, with a screenshot of Settings → Accounts (an account's edit view open: required minimum
balance, bank website, reconcile running balance):

> *"yes put save login on the bill line, also this being the the settings page is getting too much. Lets move this
> into assistant tab since this is part of it we can make the page automation, then in that page we can have accounts
> page in the settings (yes it will be duplicate) but without the amount to make it more focused and we can make the
> edit a simple double click and the account setting slides down."*

**P1–P8 RULED 2026-10-10 (Rob: "approve P1–P8 as recommended"). BUILT 2026-10-10 (Rob: "build item 69"):** a static Assistant group in the sidebar (the teaching layer adds Working picture to it), the Automation view, Settings' card replaced by one line; `/bank-logins?all=1` lists every account and standalone card with where it stands and no amounts; rows open on a double-click, their ▸ or Enter, one at a time, Esc closes, the slide off for reduced motion; bills with website, login, show me once, read, paid from and the way to pay; the Budget card links to the setup; s180. Awaiting the gate and acceptance.

**Already done on Rob's word (2026-10-10):** Save login on each bill's own line (item 68, 636c574).

**What this item is:** where the automation lives and how it's laid out. It changes no rule: everything the agent does
and never does (items 57, 65, 67, 68) stays as ruled. No code until Rob says "build item 69".

**Amended 2026-10-10 (Rob: "we need to use tabs for accounts and for bills. Then I would like to see a better slide
down animation than a double click"):** Accounts and Bills on two tabs; P4 now opens a row on a single click on the row,
its arrow, or Enter - the height eases open and the arrow turns (no motion for reduced motion) - instead of a
double-click. A closed row's settings can't be reached by Tab.

## 1. What is true today (fix branch, aa83843)

- **Settings carries all of it**, in one card, *Fetch my downloads*: the vault explanation (item 57 A3), every bank
  account and card with a link (save login, show me once, record again, delete steps, remember this computer, the
  last fetches), the "last fetched" reminder's days (item 67 G3), and, folded, *Bills from their own website*
  (item 68 B1). It sits among backup, the AI log, household facts and the rest.
- **Settings → Accounts** lists every account with its balance; the pencil opens its editor in place (Rob's
  screenshot): name, type, institution, required minimum balance, bank website, reconcile running balance.
- **The sidebar's Assistant group** holds *Working picture*.
- **The Budget page** carries the bills card (item 68 B3, B6, B7): what was read, confirmed, can I pay this, paid?.
- **The header** has ⟳ Get my accounts; the dashboard has the "last fetched" line (item 67).

## 2. Points for ruling

**P1. An Automation page in the sidebar's Assistant group.** Everything in *Fetch my downloads* moves there: logins,
saved steps, remembered computer, last fetches, the reminder's days, and bills' websites and logins. It **moves, it
isn't copied**: Settings keeps one line in its place, *"Logins and automatic downloads are in Assistant →
Automation"*, with a link.
*Recommended.*

**P2. The page's top: what automation does, and one button.** The vault explanation (A3's words, unchanged), then
⟳ Get my accounts with each account's last fetch, the reminder's days, and Stop while a run is going (the same panel
as the header's).
*Recommended.*

**P3. Accounts, without amounts (Rob: "yes it will be duplicate").** Every bank account and standalone card, by
name, with no balances: the page is about getting the data, not what it says. Each row shows where it stands in
words: *"website · login saved · steps saved · remembered computer"*, or what it still needs (*"needs a website"*).
It lists the same accounts as Settings → Accounts, read from the same records; nothing is stored twice.
*Recommended.*

**P4. Double-click opens a row's settings, sliding down in place** (Rob). One row open at a time. Inside: the bank
website (the same field and save as Settings → Accounts, so the two can't disagree), Save login / Forget, Show me
once / Record the steps again / Delete steps, Remember this computer, and the last three fetches.
- **Not double-click alone:** a double-click can't be done from a keyboard or a screen reader, and many people never
  try one. Each row also opens with a single click on a small ▸ at its end, and with Enter when it has focus. A
  double-click anywhere on the row does the same.
- Esc, or the ▸ again, closes it.
*Recommended.*

**P5. Bills, the same way.** Below the accounts: every bill line in the budget, by name, no amounts, with its state
in words (*"website · login saved · where the amount and due date are, saved"*). A double-click (or ▸ / Enter)
slides down its website, Save login, Show me once (with the two marking buttons) and Read my bill. Which account pays
it lives here too ("Paid from"), so the Budget card only shows the money.
*Recommended.*

**P6. The Budget page keeps the money; the Automation page keeps the setup.** The Budget bills card keeps what was
read, the yes, use for this month, can I pay this, paid? and Take me to pay this. Where it now asks for setup (no
website yet, no way to pay recorded), it links to that bill on the Automation page, opened.
*Recommended.*

**P7. Settings → Accounts is unchanged**, balances and reconcile included. Its bank website field stays (it's the
same field P4 shows).
*Recommended.*

**P8. Tests.** The Settings card gone, its one-line link in place; the page in the Assistant group; no balance or
amount anywhere on the Automation page; one row open at a time; ▸ and Enter open a row as a double-click does; the
website saved from either place reads the same in both; every route the card used still answers; AI off changes
nothing. Master only.
*Recommended.*

## 3. Not decided here

- **Moving anything else out of Settings** (backup, the AI log, household facts): not proposed; Rob said "this".
- **Anything the agent does** (items 57, 65, 67, 68): unchanged.
