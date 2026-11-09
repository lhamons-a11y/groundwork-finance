# The 2.0 release walk (2026-11-08)

Rob: *"lets do a full application walk clicking every button and entering data and testing everything adding data
etc. I think that will be a full test for the release."* Before that, the same day: *"lets also go over the onboarding
again. To make sure it's not broken other places."*

## 1. What was done

**Every first-launch path, walked by hand** on an empty Groundwork: the terms, the AI check (on and off), the sample
household and "Start with my own", "Bring in my spending history" (a 76-line checking CSV), "Set things up by hand"
(income, home, bills, a card, a goal), and "Restore from a backup".

**Every page, every control, by machine** (`scripts/release_walk/crawl.mjs`), five passes:

| Pass | Household | Controls pressed |
|---|---|---|
| Press everything | the sample, fresh for each page | 301 |
| Press everything | an empty install | 216 |
| Enter data in every form and save it | one sample household, kept throughout | 511 |
| Press everything again on what pass 3 entered | the same household | 699 |
| Press everything on the pages changed by the fixes, with data entry | the sample | 218 |
| **Total** | | **1,945** |

Recorded per press: uncaught errors, console errors, unhandled promise rejections, every API answer of 400 or more.
**Result: no exception, no console error, no server error on any page.** Every 4xx was the server's right answer to an
empty or incomplete form ("a name, please", "the backup password needs at least 10 characters", "set up backup
protection first" - item 81 B1, "which bank holds Cashback Visa?" and "who is answering?", both asked by the page).

**Data that must survive a reload** (`scenarios.mjs`): a transaction added, edited and deleted; an account; a card with
its balance, rate and due day; a budget line; a holding; the home state; a trip worked out ($591 to Columbus: fuel,
two GSA nights, meals), kept and listed under Your trips; Before You Buy at $100, $1,200 and $9,000 a month, with and
without a saved debt plan; the engine's "$200 more" and "$591 trip" answers. All held.

## 2. Found and fixed

| # | What was wrong | Where |
|---|---|---|
| 1 | **"Restore from a backup" never worked.** The upload was the one raw fetch without the session token, so every restore was refused as "Unauthorized" and shown as "protected on another computer". | `app.js` handleRestoreUpload |
| 2 | **First launch's "Bring in my spending history" was a dead end**: the import window needs an account, accounts are made in Settings, Settings is behind the welcome. The window now names the first account when there are none. Settings' "accounts are created automatically" corrected. | `app.js` _fillImportAccounts, `index.html` |
| 3 | **The snapshot after a first import never showed**: the welcome decided before the rows were loaded and saw none. | `app.js` confirmImport / _obAfterImport |
| 4 | **Income was blank right after the snapshot reported it**, with Next locked. It starts from the detected figure, says so, and is never put over a typed one. | `app.js` _obPrefillIncomeFromImport |
| 5 | **"You're starting debt-free"** for a person who skipped the debts step (over an import full of car-loan payments), and for anyone owing under $500. | `app.js` _obRenderPlanSummary |
| 6 | **"High confidence in spending patterns"** over 11% categorized spending, on top of a dashboard saying it couldn't be assessed; "Largest spending: Other". | `app.js` _renderFinancialSnapshot |
| 7 | **The import preview cut the amounts off** (the category list pushed them out of the window). | `app.js` import preview |
| 8 | **The "What if you paid extra?" slider snapped back to $0** on every new amount: the engine's answer re-rendered the Advisor, which reset it. | `app.js` loadDebtAdvisor |
| 9 | **A $1,500 debt budget nobody chose** dated payoff on Debt Payoff and the dashboard ("debt-free in 3 months" for a $3,200 card) while Budget counted the $95 minimum. With no saved plan it is now the minimums everywhere (panel I-01) - the Debt page, and the payoff engine behind Before You Buy, trips and the assistant. A saved $0 stays $0. Saving Settings with the field empty no longer saves a $0 plan. | `app.js` boot, _getMonthlyBudget, saveSettings; `server.py` _consequence_inputs, bootstrap |
| 10 | **Before You Buy said "unable to cover your current minimum debt payments" beside $3,071 left each month.** The engine prices a cost inside the debt plan; its "no date" means the plan can't carry it, not that the minimums go unpaid. It now says which: the plan carries it (its date), only what's left does ("Not in your debt plan", and the date unchanged if paid from what's left), or neither (the minimums warning, now true). The what's-left alternative is offered for a small cost the plan carries as for a large one, so a bigger purchase never reads better than a smaller one. | `app.js` _bybFunding and the comparison; `teaching/byb.js` |
| 11 | **A dev server shared the installed app's vault entries** (both "Groundwork - account:1"): the demo-bank video run was one click from overwriting a real saved bank login. `GROUNDWORK_VAULT_SERVICE`, set by `dev_server.py` to "Groundwork dev", read by `bank_vault` and the bank window process; unset, "Groundwork" as before. | `core/bank_vault.py`, `bank_agent_window.py`, `dev_server.py` |

| 12 | **Net worth grew by the 401(k) and IRA on every visit to the Net Worth page, and was saved that way** (present since 1.0). Investments are stored as one combined figure (brokerage + 401(k) + IRA); the page put that combined figure into the brokerage field, then added the 401(k) and IRA again. On the sample: $113,066.33, $154,565.33, $196,064.33 on three visits; now $30,068.33 every time. The monthly snapshots recorded the inflated assets too. | `app.js` renderNetWorth |
| 13 | **A loan held to a credit card's minimum formula.** The Budget page showed "↓ min $171.27" beside a fixed $389 car loan; its debt editor refused to save a payment below that estimate (the sample's $210 student loan was "below the minimum" of $257.81 - and a card's real statement minimum below Groundwork's estimate was refused the same way); debt history stored the formula as a loan's minimum, so freed-minimums read the loan's minimum as rising; the Debt Payoff report printed "(min $171.27)". A loan's minimum is now its payment, and a card's statement minimum is saved with a note. | `app.js` _budgetMinDecay, _budgetSaveDebtBloom, _budgetSaveDebtSnapshot, _freedMinimums, the report |

Held by **s294** (18 checks), beside the full gate.

## 2a. The math audit

`scripts/release_walk/math_collect.mjs` takes the raw records and every figure a page shows; `math_check.py`
recomputes each from the raw records alone, with its own payoff simulation (interest at APR/12, every minimum, the
rest by strategy, freed minimums rolling on), sums and ratios, sharing no code with Groundwork. **41 of 41 agree** on
the sample household: the debt-free date and total interest, $200 more a month (9 months, $1,013), a $591 trip
(1 month, $282), interest a month and a week, debt-to-income, the Budget page's income, planned and projected out
and left, this month's and last week's spending, five categories against their ledger lines, every account's
activity, each holding's value and gain, the portfolio, and net worth. Two conventions, stated: whole-dollar interest
on the Debt page, and a week's interest as a month x 12 / 365 x 7.

## 3. Found, not changed (for ruling)

- **No Internet rule in the importer.** Comcast, Xfinity, Spectrum and plain "internet" land in Other; a first import
  of real payees can read as mostly uncategorized. The categorizer's coverage has its own history (item 84).
- **Closing Groundwork right after the first import skips the rest of the welcome** (income, debts, goal); it does not
  come back.
- **Two "at minimums" dates.** The welcome's debt step uses V11's minimums-only (each card's minimum falling with its
  balance): "Jul 2042". Debt Payoff with no plan saved uses a steady sum of today's minimums: "June 2031". Both follow
  their rules; side by side they read as a contradiction.
- **"Clear the sample" asks the AI question again** although it promises the AI setting stays (it does stay; the
  welcome cannot tell "never chosen" from "chose off").
- **OFX `&amp;`** (already noted in DEMO_BANK.md): kept literally by the reader.
- **The Budget page's header OUT / LEFT is the month projected at this pace**, unlabelled; the section below it
  labels "planned" and "projected at this rate" correctly.
- **Net worth already inflated on 1.x computers (fix 12)** - RULED 2026-11-08 (Rob: "Yes put the note in"). The fix
  stops it growing but cannot know the true brokerage figure. An upgrade from 1.x now leaves a note
  (`nw_check_note`); the Net Worth page asks once to check Investments (brokerage) against the statement - only with a
  401(k) or IRA and a brokerage figure entered, with the holdings' value and "Use it" when there are holdings - until
  "I've checked it". Snapshots saved before the update are named as possibly higher. Tried on a 1.1.1-versioned copy
  of the sample: shown, "Use it" gave $30,068.33, gone after "I've checked it" and a reload; never on a 2.0 database.
  s294 W10.

## 4. Not covered by this walk

The bank, airline and hotel windows (they open real sites - the demo bank is item 117's own run); the local AI model
answering (AI on was chosen, the engine not exercised); voice and the microphone; the print dialog; the packaged app's
Downloads watcher and installer; macOS and Linux. Release checklist items R1-R8 (RELEASE_2_0.md) are unchanged.

## 5. Running it again

`scripts/release_walk/README.md`.
