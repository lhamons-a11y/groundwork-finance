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

**No data goes unused (Rob, 2026-10-01):** *"Having the user first enter data that will already get the program
moving in what the user will feel like a custom setting and also goes with the belief that no data goes unused."* This
works in both directions:
- **Every question earns its place.** It feeds a named calculation. A question nothing reads is not asked.
- **Every answer is used where the user can see it.** The answer changes something they meet soon after, so the setup
  feels like it was made for them.

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

**F8. Two onboarding answers are stored and never used.** This breaks *no data goes unused* today.
- *"What brought you here today?"* is saved as `onboarding_intent` (app.js ~12612). Its only effect is the subtitle on
  the next screen. Nothing reads it afterwards.
- *"When you have money beyond your immediate needs, what would you most like it to accomplish?"* is saved as
  `surplus_goal` (app.js ~13170) and put in `S.surplusGoal`. Nothing reads either one, and the answer isn't restored
  on startup.

The revisit must either give each a reader the user can see (for example, the first dashboard tiles or the debt plan's
order), or stop asking it.

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
- **A7.** *No data goes unused* as the test for every question: a question with no named reader is not asked, and
  each answer shows its effect where the user meets it. F8's two questions are fixed or removed in the revisit.
- **A8.** *The household facts block for narration* (discussed 2026-10-02, proposed, not yet put to Rob as a ruling):
  - the current asked facts are given to the narrator as one small block, each labelled asked / ledger / published,
    with the date it was given;
  - it goes in the prompt's stable prefix, so the runtime reuses it and the in-app engine can process it at launch;
  - history goes in only when the question is about a change;
  - `onboarding_intent` is never put in, because it would steer every answer toward that motive;
  - the user's stated priority may go in, as their choice, never as advice.

  Why: the model reads input in batches, but each token it writes is a full read of its 2.2 GB of weights from RAM. A
  fact given as input replaces text and round trips it would otherwise have to write. Fewer trips and shorter answers,
  with a small block.
- **A9.** *AI off means nothing AI-related loads* (Rob agreed, 2026-10-02). The engine checks the user's AI setting
  **before** loading the model. Today [`launch.py`](../launch.py) (~404) starts the Ollama runtime on every launch
  without checking `ai_enabled`. That costs little now, because Ollama loads the model only on first use, but the
  in-app engine (MODEL_PLACEMENT ruling 4, not built) loads 2.2 GB at launch. Test: with AI off, the process never
  loads the model and its memory stays at the no-AI level.
- **A10.** *Every surface is complete with AI off* (Rob agreed, 2026-10-02). The program is still good with AI off:
  each page gives the plain-figures fallback, never an empty box or an error. Items 22-29 are worked out from data
  already. The older AI surfaces (trip planning, categorising, the narrator panels) have not been checked. Test: one
  gate pass with `ai_enabled=false` that visits each AI surface and requires a useful non-AI answer.

  Rob's stance, recorded with it (2026-10-02): users know how their own machine runs. Those who want AI know it needs
  RAM and a decent processor or GPU. Those who don't care switch it off in onboarding and still get *"freeware that
  doesn't suck"*, on little RAM. So the onboarding machine check and the AI on/off choice are the first asked fact
  (A7: that answer decides what loads).
- **A6.** Then the onboarding revisit, as its own pass: the order, what is skipped, and fixing the ambiguous *Gas* label.

## 5. Ruling: Rob, 2026-10-02

**All ten points accepted as written** (*"I accept A8, all ten points as written"*). This is a ruling, not a build
authorisation.

Already settled before this ruling, and still in force: unanswered stays unanswered; a ledger reading prompts a
question and never answers it; no data goes unused.

**Next:** the onboarding revisit, opened as its own pass (A6). The build pieces each need their own go-ahead:
- the asked-fact store with history (A2, A3);
- the questions in Settings and on the first page that needs each one (A5);
- the AI-off checks (A9, A10);
- the narration facts block (A8, which waits on the in-app engine).

## 6. Status

RULED 2026-10-02 (A1–A10). No code authorised. Item 31 (replacing Ollama, `ENGINE_REPLACEMENT.md`) goes first, by Rob's choice. The onboarding revisit follows it.
