# The onboarding revisit (item 30, A6)

Opened 2026-10-02 (Rob: *"yes open item 30"*, after item 31 was accepted). **No code.** Item 30's ten points are
ruled (`ASKED_FACTS.md` §5). A6 said the onboarding revisit is its own pass, after item 31. This is that pass. It
measures what onboarding asks today, against current master (`6b8ae63`, with the in-app engine), and puts the
changes to Rob.

The rules it applies, all already settled:
- **Asked, ledger, published, never** (A1). A ledger reading may prompt a question, never answer it.
- **No data goes unused** (A7). Every question has a named reader, and each answer shows its effect where the user
  meets it.
- **Unanswered stays unanswered.** Skipping is never a default: no state is not Ohio, and no fuel is not natural gas.
- **Each answer is a dated statement** (A2, A3), changeable in Settings and asked again on the first page that needs
  it (A5).
- **AI off loads nothing** (A9), and the AI choice is the first asked fact.

---

## 1. What onboarding asks today, and who reads each answer (measured)

| # | screen (`index.html`) | asks | stored as | read by | verdict |
|---|---|---|---|---|---|
| 0 | `obStepAICapability` | the machine check, then *Turn on local AI* / *Continue with AI off* (item 31) | `ai_enabled` | the engine (load at launch, A9) | **keep: first, as ruled** |
| 1 | `obStepIntent` | *"What brought you here today?"* (5 choices) | `onboarding_intent` | **only the next screen's subtitle**; nothing after | **F8: unused** |
| 2 | `obStep0` | import, set up by hand, or restore | nothing (it routes the flow) | the flow | keep |
| 3 | `obStep1` | names, *sharing finances?*, take-home income (one or two) | `household_mode` and names; income budget rows | the whole app (household, plans, dashboard) | keep |
| 4 | `obStep2` | fixed bills: mortgage or rent, Electric, **Gas**, water, internet, phone, trash, groceries, dining, **Gas / Fuel**, car lease | expense budget rows (`Gas` → category `Gas`) | budgets, totals; item 26 reads `Gas`, `Electric`, `Gas / Fuel` | keep, but **F5**: *Gas* means natural gas to item 26, and a propane household has no honest field |
| 4b | `obStep2`, import view (`obExpImport`) | the category averages it found, editable | expense budget rows | as above | keep |
| 5 | `obStep3` | every card or loan: balance, rate, minimum | debt accounts | the debt pages, plans, attention | keep |
| 6 | `obStep4` | *"When you have money beyond your immediate needs, what would you most like it to accomplish?"* plus avalanche or snowball | `surplus_goal`; `debt_method` | `debt_method`: the debt plan. **`surplus_goal`: nothing** | **F8: half unused** |
| 7 | `obStep5` | net-worth target and date (optional) | `nw_goals_json` | the Net Worth page | keep |
| 8 | `obStep6` | the summary (*"Here's where you're starting from"*) | nothing | — | the natural place to show each answer's effect (A7) |

**Never asked in onboarding, though 2.0 reads them** (from `ASKED_FACTS.md` §2, and measured again):

| fact | read by | asked today |
|---|---|---|
| home state (F1) | item 26's estimates (2.0), and the Budget page's EIA benchmarks (**both lines**, `_home_state()`) | Settings only |
| heating fuel (F2) | item 26 (today it assumes natural gas) | nowhere |
| how the fuel is paid (F3) | item 26 (even monthly or prepaid bills defeat the fit) | nowhere |
| own or rent, and whether utilities are included (F4) | item 26 (no bill, no estimate); net worth (a home's value) | nowhere: *"Mortgage or rent"* is one field |
| pay frequency | cash flow and payday views (`app.js` ~10093, ~25275) | Settings only |

## 2. Points for ruling

**O1. The order.** Each question comes just before the first screen that uses its answer:
1. *Local AI* (unchanged, first).
2. *How do you want to start?*
3. *Who is this for* (names, household) and *what comes in* (income), adding **"Is it the same each month, or does
   it vary? How often are you paid?"** (pay frequency already has readers).
4. **Where you live:** the home state.
5. **Your home:** own or rent, and whether rent includes the utilities.
6. **Heating:** the fuel (natural gas, propane, electric, heating oil, wood or pellets, heat included in rent, not
   sure), and for a delivered or billed fuel, how it is paid (by the bill or delivery, an even monthly amount, a
   prepaid contract). Skipped when step 5 says utilities are included.
7. *What regularly goes out*: the bills, now **labelled from steps 5 and 6** (O4).
8. *Debts.*
9. *Your priority for extra money*, with a reader (O3).
10. *Net-worth target.*
11. *The summary*, showing what each answer turned on (O7).

*Recommended.*

**O2. "What brought you here today?" is removed** (F8). Its only effect is one subtitle, and it would steer the
narrator if passed on (A8 keeps it out). The welcome copy becomes the neutral default. Recorded answers stay in the
database; nothing reads them. *Recommended.* (The alternative, replacing it with a question an engine reads, is
covered by the pay-pattern question in O1 step 3.)

**O3. The priority question gets its reader.** The summary card states the user's own choice and its arithmetic,
with no verdict. For example: *"You said emergency savings come first. At about $X a month of room, a one-month
cushion of $Y takes about N months."* The same applies for paying debt faster (from the debts they entered and the
chosen method), a future goal, investing, and *not sure*, which gets no line. This is the "user's own priority" the
d21 tester note asked for: Groundwork shows the user's choice, never its own. The answer is a dated statement and
goes into the narration block as the user's choice (A8). *Recommended.*

**O4. The bills screen follows the answers:**
- *Gas* becomes the user's own fuel: **Natural gas**, **Propane**, **Heating oil**, or no heating line when heat is
  included or electric.
- *Electric* stays.
- Under Transportation, *Gas / Fuel* is labelled **Gasoline** (the category keeps its name, so item 26 still reads
  it).
- *Mortgage or rent* splits by step 5's answer: **Mortgage** or **Rent**.
- Propane and heating oil rows get their own categories. Item 26 makes **no** natural-gas estimate from them. Their
  own estimates wait for the heating-fuel pricing work (`ASKED_FACTS.md` F2, EIA coverage still to be measured).

*Recommended.*

**O4, Rob's wording (2026-10-02):** *"Should we specify the gas field better as heating fuel (for home fuel usage),
petro for vehicle fuel."* Adopted into O4, pending the ruling:
- **Home: "Home heating fuel: <the fuel from step 6>"**, for example *Home heating fuel: propane*. The label alone
  can't tell item 26 which fuel to price, so the step-6 answer fills it in. There is no field when heat is included
  in the rent or is electric.
- **Vehicle: "Vehicle fuel (gasoline or diesel)"**, not *petrol*, which is the British word. Item 26 prices regular
  gasoline only, so a diesel driver would be priced wrong. EIA's weekly diesel series makes a diesel estimate a later
  small slice, with one question (*gasoline, diesel, or electric*). Electric links to the home-charging question
  (F6).
- **Labels change; category names do not, in this pass.** `Gas` and `Gas / Fuel` keep their names, because existing
  history is filed under them and item 26 reads them by name. Renaming categories rewrites the ledger, which is its
  own migration. Propane and heating oil get new categories, so they never feed a natural-gas estimate.

**O5. Where the answers live: dated statements (A2, A3), built here.**
- A new table, `asked_fact` (key, value, said_at, where: onboarding, Settings or a page). The current value stays in
  `AppSetting`, so nothing that reads settings today changes.
- A changed answer is a new row, never an overwrite.
- **This is a new table, which is exactly item 24's gap:** the schema pin cannot see a forgotten bump for a table.
  So this build bumps `SCHEMA_VERSION` explicitly, adds the s51 pin, and proves the upgrade through
  `run_migration_if_needed` on an upgraded database, as item 23 did. Item 24's general guard stays its own pass.

*Recommended: the table, with the explicit bump and the upgrade test.*

**O6. Skipping.**
- Every new question has *Skip for now*.
- A skipped answer is **unanswered**: no row, no default.
- The summary lists what was skipped and where to answer it later.
- An estimate that needs a skipped answer says what it needs (item 26 already does).

*Recommended.*

**O7. The summary shows each answer's effect, so A7 is visible and testable:**
- *Ohio · natural gas → a gas estimate on your Budget page.*
- *Rent includes utilities → no utility estimates.*
- *AI off → nothing loaded.*

Behind it sits a registry, in code, of **every onboarding question and its named reader**. A test fails if a question
has no reader, or if a reader names a question onboarding no longer asks. *Recommended.*

**O8. Existing users** (A5). Onboarding is never shown again, so:
- the same questions appear in a **Settings → Your home** card (state, home, fuel, how paid);
- they also appear **inline on the first card that needs them**. The Budget page's utility card asks *"Which state?
  What heats your home?"* when it has no answer, rather than showing a U.S. figure silently.
- A ledger reading may **prompt** there (*"payments to Suburban Propane look like deliveries; is propane how you
  heat?"*). It never answers.

*Recommended.*

**O9. Which line.**
- `app.js` is shared, but the readers are not. Home state has a reader on both lines (the EIA benchmarks), so 1.x
  asks it too.
- Own or rent, fuel, and how it is paid have readers only in 2.0 (item 26), so they are **2.0 only**. They are asked
  from the teaching layer, which 1.x strips at build. Asking them on 1.x would break A7.
- The intent removal (O2) and the pay-frequency question apply to both lines. Each has a reader on both, and the
  removal is shared code.

*Recommended.*

**O10. Not in this pass:**
- the narration facts block (A8, its own build on the engine);
- heating-fuel pricing (propane and oil estimates);
- item 24's general guard;
- the onboarding's look and copy beyond the changed questions.

*Recommended.*

## 3. Status

OPEN: ten points for ruling (O1–O10). No code until ruled and authorised.
