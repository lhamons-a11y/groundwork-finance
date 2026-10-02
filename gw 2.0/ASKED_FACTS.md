# Asked facts: what 2.0 needs the user to tell it (item 30)

Opened 2026-10-01 (Rob: *"create a list of items from what we are adding to 2.0 that would help the agent, historian,
engines know what we would have to calculate for the user. Then we will need to visit the onboarding for groundwork
when completed."*). **No code.** This is a measurement, made against master `a191698`. The onboarding revisit comes
after this list is ruled, as its own pass.

The rule this rests on (Rob, item 26 §5): *a fact the user hasn't supplied should not become "known" just because the
computer can obtain it somewhere else.* Every input to a 2.0 calculation is one of four kinds:

| kind | meaning | who may use it |
|---|---|---|
| **Asked** | the user said it, in a question Groundwork put to them | engines, the historian, the agent, credited as *"you told us"* |
| **Ledger** | it follows from the user's own record (transactions, balances, statements) | credited as *"your record shows"* |
| **Published** | an outside source the user chose to use (EIA prices, quotes) | credited by name, never presented as the user's fact |
| **Never** | Groundwork could find it out but must not: location, behaviour, usage | nobody |

A ledger reading may **prompt** a question (*"these look like propane deliveries; is propane how you heat?"*). It never
**answers** one. That keeps the no-silent-learning rule: nothing unsurfaced persists.

---

## 1. What 2.0's calculations read (measured)

| calculation (item) | asked facts it needs | where asked today | ledger / published |
|---|---|---|---|
| Utility estimates: gas, electricity (26) | home state; that the household pays for the fuel | **state: Settings only**; paying for it: **nowhere** | bills by category; EIA STEO |
| Gasoline estimate (26) | home state | Settings only | fill-ups in *Gas / Fuel*; EIA weekly |
| Totals pass (26 follow-up) | *Follow this estimate*, per kind | Budget card | nothing |
| Dashboard attention (22) and tiles (27) | budgeted income; debts and due dates | onboarding (income; debts) | imports, payments |
| Ask for a tile (28) | the user's own words | the ask box | nothing |
| Investments tile (29) | target allocation | Investments page | holdings, prices |
| Willingness (23) | nothing new | — | reads the user's own edits |
| Break-detector (25) | nothing new | — | the ledger |
| Fund pace (25) | the fund's goal | the fund | contributions |
| Net-worth goal | amount and date | onboarding (the net-worth target), Net Worth page | balances |
| Debt plan | method (avalanche or snowball), savings % | Settings | debts |
| Pay rhythm (upcoming facts) | pay frequency | **Settings only** | deposits |

## 2. Gaps: facts a 2.0 calculation needs that nothing asks

**F1. Home state is not in onboarding.** It is asked only in Settings. A new user gets U.S. prices until they find it.

**F2. Heating fuel.** The choices are natural gas, propane, electric (furnace, baseboard or heat pump), heating oil,
wood or pellets, *heat included in my rent*, or *not sure*. A second fuel (water heater or cooking) is a follow-up.
Today the gas estimate assumes natural gas. Propane and oil also need pricing work (EIA coverage still to be measured).

**F3. How the fuel is paid.** By the bill or delivery, by an **even monthly amount** (level billing, a budget plan),
or by a **prepaid contract**. This matters for natural gas and electricity, not only propane. With level billing the
bills don't follow the weather, so the fit can't identify usage. Not measured yet: I expect the estimate then says
*needs* without naming why. Asking turns that into a plain reason.

**F4. Who pays the utilities: rent includes them, or not.** Onboarding asks *"Mortgage or rent"* as one field, so the
household's housing (own or rent) is never stated. That decides whether a utility estimate applies at all, and whether
a home value belongs in net worth.

**F5. Onboarding's "Gas ($/month)" is ambiguous.** Under *Utilities* it means natural gas. Under *Transportation*,
*Gas / Fuel* means gasoline. A propane household has nowhere honest to put its fuel. F2 fixes the label: it becomes
the user's own fuel.

**F6. An electric vehicle charged at home.** That charging is in the electricity bill, and the gasoline estimate would
see fewer fill-ups. Both estimates would read a vehicle as weather or as less driving. One yes/no question.
*Candidate: only if Rob wants it in this pass.*

**F7. Asked facts have no history.** `PATCH /api/settings` (server.py ~5988) overwrites the value and records nothing.
So the historian cannot say *"you told us Ohio in March and Arizona in August"*, and an estimate cannot be explained
from the answer that was in force at the time. Every asked fact should be recorded as a **dated statement by the
user**, with the current value as the latest. That fits historical truth and the custody rulings.

**Not gaps, on purpose:**
- Whether the home has air conditioning. The electricity fit finds cooling from the user's own bills, under the null
  model, so asking adds nothing.
- Usage habits. That would be watching.
- Location beyond the state the user picks.

## 3. What each reader would gain

- **Engines** read asked facts through one place, and each answer says where it came from (asked, ledger, published).
  An unanswered question is **unanswered**, never a default: no state is not Ohio, and no fuel is not natural gas.
- **The historian** records each answer as a dated user statement (F7). A changed answer is a new statement, never an
  overwrite.
- **The agent** (Assistant, narrator) may say *"you told us you heat with propane"* only when that statement exists. It
  may say *"your record shows deliveries"* from the ledger. It may never turn the second into the first.

## 4. Points for ruling

- **A1.** The four kinds (asked, ledger, published, never) as the rule every 2.0 input is classed under. A ledger reading
  may prompt a question, never answer it.
- **A2.** F1–F5 are added as asked facts, each stored as a dated user statement, each changeable in Settings, each
  skippable, with a skipped answer staying *unanswered*.
- **A3.** F7: asked facts get history, so the historian and the agent can credit an answer to when it was given.
- **A4.** F6, an electric vehicle at home: in or out.
- **A5.** Each question is asked in three places:
  - onboarding, optional;
  - Settings;
  - the first surface that needs it, such as the Budget card.

  Existing users never see onboarding again, so the last place is how they meet it.
- **A6.** Then the onboarding revisit, as its own pass: the order, what is skipped, and fixing the ambiguous *Gas* label.

## 5. Status

OPEN: six points for ruling (A1–A6). No code. The onboarding revisit follows once these are ruled.
