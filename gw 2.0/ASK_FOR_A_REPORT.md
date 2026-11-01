# Item 115 — Ask for a report: the person says what they want to see, and Groundwork puts it together

Opened 2026-10-31. Rob, after item 114 gave the assistant hands:

> *"Allow the user to tell the Agent what report that they would like the Agent to make and Groundwork will build it."*

> *"can already have sections prebuilt that phi can select and put the pieces together?"*

> *"could we assist phi by catalog the picker list and using terms as an index to that catalog. ie "Monthly totals of
> debt payments from June to September": Monthly totals catalog is 1-9, Monthly Debt is in Catalog 5: then pull the
> date range."*

> *"So can we use phi to fix some of the pitfalls?"*

> *"should we offer like 10 different templetes that the user could use? When they see the report they can use
> templetes that use all text and grid, text and charts, text and graphs, etc."* - P13-P15, added 2026-10-31 (Rob:
> *"yes add that"*).

**STAGES 4-7 BUILT 2026-11-01** (Rob: *"lets complete the rest of the stages"*), awaiting acceptance; section 14,
with five rulings sought (14.6). **ACCEPTED 2026-10-31.** C1-C11 ruled as recommended, one by one (section 10); MCP dropped (section 9).
Next: the C3 pairing table for ruling, and the section 6 question set, written before measuring. Stages 1-3 may
build alongside item 114's fixes; stage 4 waits for them (C7).

---

## 1. What is true today

- **Reports are a fixed catalogue** (`_REPORT_CATALOG`, `static/js/app.js`): Monthly Spending Summary, Category
  Deep-Dive, Spending vs. Budget, Annual Summary, Year-end packet, Visit report, Debt Payoff Analysis, Debt Progress,
  Income & Savings Rate, Net Worth Timeline, Distance Traveled, Import Audit. Each builds its own figures and
  `dataLines`; since item 64 (`REPORTS_WITHOUT_AI.md`) each stands on its own with AI off, and AI only teaches.
- **The assistant has hands** (item 114, `AGENT_HANDS.md`): a closed list of lookups (H2) and engines (H3); Groundwork
  writes every figure (H22); proposals need Yes (H7).
- **What item 114 measured on the M2, 8 GB, phi3.5** (section 11): 41 / 52 right outcome, **33 / 52 right lookups**,
  median 6.2 s, 45 / 52 under 20 s. The misses were routing and wrong or thin lookups - choosing, not figures.
- **The record has no way to ask for a report that is not in the catalogue.** "Monthly totals of debt payments from
  June to September" opens Debt Progress at best; the person narrows it by hand.

## 2. The idea, in one line

**A report is a stack of prebuilt sections. Each section is a shape crossed with a subject, over a period. An index of
terms picks them; phi helps only where the index cannot decide, and only by choosing from a closed list.** The model
never builds a query, a layout or a figure.

## 3. Proposed

### The catalogue

**P1. A section is shape × subject × period, with filters.** Each pairing that makes sense is one prebuilt section:
one lookup or engine from item 114's H2/H3, a fixed layout, and its settings. Groundwork draws it; the figures come
from the lookup, as today.

**Shapes** (the first number):

| # | Shape | What it draws |
|---|---|---|
| 1 | Monthly totals | one row or bar per month |
| 2 | Trend over time | a line, with the start and end figures |
| 3 | List of items | the rows themselves, capped, sortable |
| 4 | Snapshot | where it stands today |
| 5 | Comparison | this period beside that period |
| 6 | What-if | an engine run with the change stated (RG4) |

**Subjects** (the second number):

| # | Subject | Reads |
|---|---|---|
| 1 | Spending by category | `budget_vs_spent`, `category_by_month` |
| 2 | One category | `category_by_month` |
| 3 | Payees | transactions by payee |
| 4 | Income | income lines, transactions kind earning |
| 5 | Debt payments | transactions to debts, by debt |
| 6 | Debt balances | debts; the payoff engine |
| 7 | Net worth and balances | snapshots, account balances |
| 8 | Recurring charges and price steps | items 106 / 108 |
| 9 | Bills due | bills and the calendar |
| 10 | Budget headroom | `reallocation_candidates` |

Rob's example is **section 1.5** (monthly totals of debt payments), period June to September. Not every pairing is
a section - "what-if of payees" is not - and the catalogue says which are (section 7, C3).

**P2. The existing reports become templates.** Each of the twelve is a ready-made stack of sections: Monthly Spending
Summary is roughly 1.1 + 3.3 + 5.1; Debt Progress is 2.6 + 1.5 + 4.6. A request that matches a template needs only
its settings. Templates and today's reports stay the same page - nothing the person already uses moves.

### Reading the request

**P3. The index, before any model.** Three small vocabularies, each its own table:
- **Shape terms:** "monthly", "each month", "by month", "per month" → 1; "trend", "over time", "going up" → 2;
  "list", "show me the", "which" → 3; "how much do we owe", "where do we stand" → 4; "vs", "compared to" → 5;
  "what if", "if we paid" → 6.
- **Subject terms:** "debt payments", "paid on the cards", "loan payments" → 5; "eating out" → the person's own
  category, and so on.
- **Template terms:** "monthly review", "year end", "how is the debt going" → a template.

**P4. Names come from the record, not the index.** Debts, categories, payees and accounts are matched by code -
spelling closeness against the person's real list. Two close matches: ask, never pick (item 114 Q17). A name not in
the record is dropped and said so (the "named_debt_here" repair).

**P5. Dates are read by code.** "June to September", "last month", "this year", "since January", "Q3". A month not
yet reached this year means last year's. Phi never reads a date.

**P6. Each request goes through four steps, in order:**
1. **The index finds one shape and one subject** (or a template). Groundwork builds it. No model call.
2. **It finds one but not the other.** Groundwork asks one question with buttons ("Debt payments as: monthly totals
   · a list · a trend?"), or hands phi only the 3-4 candidates (P8).
3. **It finds nothing.** Phi gets the request and the short catalogue (P8), or Groundwork offers the templates.
4. **Every miss is logged** (item 114's 1E miss log): the request, what the index found, what was asked, what the
   person picked.

Requests to act ("email me this every month", "delete these") are read by Groundwork before any of this, as item 114
section 11 fix 1 rules; this item adds no action.

### Phi's helpers

**P7. Phi answers small closed questions, never builds.** Four helpers, each one question, each with "can't tell":

| Helper | Phi is asked | Code then |
|---|---|---|
| H-a Two meanings | "Is 'payments on the Visa' A) bill payments, B) debt payments, C) can't tell?" | C asks the person |
| H-b Unknown words | "Which of these categories / subjects is 'takeout'? or none" - the person's list shown | checks it is on the list |
| H-c Except and versus | fills `exclude: [ ]`, `compare: [period, period]` | checks every name and period |
| H-d Index suggestions | reads the miss log when idle; suggests "'takeout' → Restaurants" | nothing enters the index until a person says Yes |

**P8. The answers are forced by grammar.** llama-cpp-python's GBNF grammars (the same runtime `core/engine.py`
loads phi3.5 with) let a call allow only the listed answers. Phi cannot write anything else. Code checks the answer
against the record anyway - grammar first, check second.

**P9. H-d writes nothing on its own.** A suggested term is a proposal (item 114 H7): shown, Yes / No, Undo. This keeps
provision 3, no silent writing, and R4, no silent learning.

### What the person sees

**P10. The report arrives as a list of sections the person can change.** Each section shows what it is ("Monthly
totals · Debt payments · June-September 2026"), with its settings as dropdowns. Add, remove, reorder, change - no AI
needed. A wrong pick costs one click.

**P11. A saved report is its list of sections**, stored as data, not words. "Run my debt payments report" runs it
again with the period moved on, no model call. Saving is the person's Yes.

**P12. AI off loses nothing but the reading of free words.** The section list, templates and saved reports all work
with AI off (item 64, A10). With AI off, step 3 offers the templates; H-a falls back to the button question.

### How it looks

**P13. Layout styles, kept apart from content templates.** A content template (P2) says *what* is in a report; a
style says *how* it is shown. Any report - a template, one built by hand, one asked for - can be shown in any style,
so twelve reports do not become sixty. Six to start, more only when a person asks for one:

| Style | What it looks like | For |
|---|---|---|
| Text and grid | summary sentences and tables | exact figures; screen readers |
| Text and charts | each section's sentences beside its chart | the default on screen |
| Charts first | charts and headline figures as tiles, short text under | a quick look |
| Text only | sentences, no tables or charts | read aloud - conversation mode and the microphone (item 114 H14, H15) |
| Print / PDF | paged, tables, charts safe in black and white | the year-end packet, the accountant |
| Compact summary | one card per section: the headline figure and what changed | a phone; the Sunday check-in |

**P14. The section's shape picks the chart, not the style.** Monthly totals draw bars; a trend draws a line; a
comparison draws bars side by side; a snapshot draws a figure tile; a list is always a table. "Text and charts" means
*show the visuals*; each section draws its own kind, so no style puts a trend line on a single figure.

**P15. The person picks the style, and can change it.**
- One control on the finished report switches style; one section can be set apart ("this one as a table").
- Style terms join the index (P3): "as a table", "with charts", "for printing", "read it to me". Code reads them;
  phi is not asked.
- A saved report keeps the style the person saved it with. Groundwork never picks a style from what the person opens
  most - that would be learning without asking (R4).
- The "text" in every style is Groundwork's own summary sentences (item 64); the AI's teaching part sits under them
  when AI is on. Every style works with AI off.

## 4. What this does not change

- **H22:** every figure from a lookup or engine. Sections are drawn by Groundwork.
- **Provision 2, no tools to the model:** phi gets a multiple-choice prompt and a grammar, not tools or open
  arguments. **Ruled (C6): a GBNF-limited choice is not a tool under provision 2; provision 2 stands unchanged.**
- **Provision 3 / R4:** no new text surface saves model output; H-d goes through Yes.
- **Health:** health sections go through item 45's H6 boundary, or are not in the catalogue (TM7). None proposed.
- **Item 22 D5:** a section shows; it does not judge. No "good month".
- **Item 64 and R4, in every style (P13-P15):** the words are Groundwork's summary sentences, AI only teaches on
  top, and the style is the person's choice, never learned from what they open.

## 5. Before this builds: item 114's open misses

The index leans on the same routing as item 114. **Corrected 2026-10-31:** this section was first written from
section 11's first run; its fixes were already built and measured again the same day (`AGENT_HANDS.md` section 11,
*The fixes, measured again*): `read_request` decides requests to act, changes, the guide, pages and outside the
record before the model; 58 / 60 right outcomes; 60 / 60 under 20 s, slowest 10.5 s; H19 and H20c built (section
13). What is still open:
1. Q05, Q07, Q10 - a lookup that works but is not the best one, and "since we cut that budget" read as not enough.
2. The Windows laptop run of the question set (Rob's machine).
3. A real microphone try on the Mac and Windows (H14, H15).

C7 holds: stage 4 waits for item 1; items 2 and 3 are Rob's runs and do not block it.

## 6. Measured before any build

**The question set:** 25 report requests in Rob's own words, written before measuring (the item 114 way), each with
the expected sections and settings. At least: five that should match by index alone, five templates, five with a
two-meaning word, five with unknown words, three with "except" or "versus", two requests to act.

**Scored separately:**

| What | Bar (proposed) |
|---|---|
| Index alone: right sections, or right question asked | most of the set; the share is the finding |
| Index alone: wrong section built | 0 - a doubt asks |
| Dates read right | every one |
| H-a: right choice, or "can't tell" when it truly is | measured, no bar yet |
| H-b: right category or "none" | measured, no bar yet |
| H-c: right exclude / compare, names real | measured |
| H-d: suggestions Rob would accept | measured, from a planted miss log |
| Time, index-only requests | under 1 s |
| Time, requests that reach phi | under 20 s (item 114's bar) |
| Any figure the model wrote, shown | 0 |
| Style terms read right ("as a table", "for printing") | every one |
| Every style against every section: screen, print, light, dark, a phone | checked by hand, each a pass or a fix |

On the M2, 8 GB, phi3.5 Q4 - the same machine as item 114 section 11.

## 7. Order, proposed

1. **C1-C3:** the catalogue tables (shapes, subjects, which pairings exist) and the twelve reports as templates -
   data only, no reading yet.
2. **The section list page** (P10, P11): build a report by hand from sections. Useful with AI off, on its own.
3. **The six styles** (P13-P15): the style control, per-section override, saved with the report; checked against
   every section (section 6).
4. **The index and the date reader** (P3-P6), steps 1, 2 and 4, with the style terms.
5. **Measure** (section 6), index alone.
6. **Phi's helpers** H-a, H-b, H-c with grammars (P7, P8); measure each.
7. **H-d** suggestions through Yes (P9), last.

Each stage is useful without the next: stage 2 alone gives a report builder; stage 3 gives it its looks; stage 4
alone gives most requests.

## 8. Rulings sought (ruled 2026-10-31, section 10)

- **C1.** The six shapes and ten subjects as the starting catalogue, or changed.
- **C2.** The twelve reports become templates of sections, their pages unchanged.
- **C3.** Which shape × subject pairings are sections (a table to follow, from C1).
- **C4.** Adding a term to the index is a ruling for Rob's own vocabulary (P3); a term the person accepts through H-d
  is that person's own, kept on their computer only.
- **C5.** Phi's four helpers, each with "can't tell".
- **C6.** A grammar-limited choice is not a tool under provision 2.
- **C7.** Section 5 first: item 114's routing fixes before stage 3.
- **C8.** The section 6 question set and bars.
- **C9.** The six styles (P13), or a changed list; more only when a person asks.
- **C10.** The default style: text and charts on screen, print / PDF when printing.
- **C11.** One section may be set to a different style from the rest of its report (P15).

## 9. Dropped: attaching outside agents (MCP)

Rob asked whether, if the built-in model cannot carry this, Groundwork should let people attach their own agents
through the Model Context Protocol. **Ruled 2026-10-31: dropped. Groundwork does not attach outside agents.** This item
is built so phi is enough. The reasons, kept for the record: outside agents do their own arithmetic, so H22 cannot
hold for them; a cloud agent takes the record off the computer; R7 and H8 refusals would become the other agent's.

**Security, the strongest reason** (Rob, 2026-10-31: *"i think that would produce security issues"*):
- **Planted text reaches a model Groundwork does not guard.** Item 114 section 11 held back 5 / 5 planted memos and
  payees because Groundwork's own gate reads them first. An outside agent reading the same rows through MCP has no
  such gate: a memo written to instruct a model ("ignore earlier instructions and ...") goes straight to it.
- **The record leaves the computer.** Most agents people would attach run in the cloud; every lookup would send
  transactions, balances and debts to another company's servers - against local-first, and against the health
  boundary (TM7).
- **A door other programs can open.** An MCP server is something listening on the computer. Unless it is locked down
  with care, any program there, malware included, could ask it for the whole financial record. Groundwork has no such
  door today, and that is a strength.
- **No say over what the agent does next.** R7, H8 and Yes / No / Undo live inside Groundwork. An outside agent could
  take what it read and act elsewhere - email, a browser, a bank's website.
- **Figures nobody checked**, shown beside Groundwork's name (H22 cannot hold).
- **Tools Groundwork cannot review.** People would install third-party MCP servers and agents; their code is outside
  anything Groundwork can test or vouch for.

Reopening it would need a ruling that answers each of these first.

## 10. Ruling: Rob, 2026-10-31

Rob: *"lets rule in section 4-9"*, then ruled one by one:

| | Ruling |
|---|---|
| C1 | **Accepted:** six shapes, ten subjects (P1) |
| C2 | **Accepted:** the twelve reports become content templates, their pages unchanged |
| C3 | **Accepted:** the pairings that are sections come from a table, written next, for ruling |
| C4 | **Accepted, two kinds:** built-in terms change only by Rob's ruling; a term a person accepts through H-d is theirs alone, kept on their computer |
| C5 | **Accepted:** all four helpers, each with "can't tell", each measured on its own |
| C6 | **Accepted:** a grammar-limited choice is not a tool; provision 2 unchanged |
| C7 | **Accepted:** item 114's misses before stage 4; stages 1-3 may build alongside |
| C8 | **Accepted:** 25 requests in Rob's words, written before measuring, section 6 bars |
| C9 | **Accepted:** the six styles; more only when a person asks |
| C10 | **Accepted:** text and charts on screen; print / PDF when printing |
| C11 | **Accepted:** one section may differ in style from its report, saved by the person's choice |
| Section 9 | **MCP dropped** - Groundwork does not attach outside agents |

## 11. C3: which pairings are sections (proposed 2026-10-31, for ruling)

Rows are subjects, columns shapes. **✓** a section; **-** not one (it would say nothing the others do not, or the
record cannot speak to it). Each ✓ names what it reads.

| Subject | 1 Monthly totals | 2 Trend | 3 List | 4 Snapshot | 5 Comparison | 6 What-if |
|---|---|---|---|---|---|---|
| 1 Spending by category | ✓ every category, each month | ✓ all spending, a line | ✓ categories ranked, for the period | ✓ `budget_vs_spent`, one month | ✓ two periods, by category | - |
| 2 One category | ✓ `category_by_month` | ✓ its line, with the budget line | ✓ its transactions | ✓ this month against its line | ✓ two periods | - |
| 3 Payees | ✓ one payee, each month | - (the same as 1) | ✓ top payees, for the period | - | ✓ two periods, by payee | - |
| 4 Income | ✓ each month | ✓ a line | ✓ paychecks and other income | ✓ income lines against what came in | ✓ two periods | - |
| 5 Debt payments | ✓ each month, by debt | ✓ a line | ✓ the payments | - | ✓ two periods | - |
| 6 Debt balances | - | ✓ where the record holds snapshots | ✓ each debt: balance, rate, minimum | ✓ owed today, payoff date | ✓ then and now | ✓ `debt_whatif`, `minimums_only` |
| 7 Net worth and balances | ✓ month-end net worth | ✓ a line | ✓ each account | ✓ today, set aside and available | ✓ then and now | - |
| 8 Recurring and price steps | - | ✓ a charge's price over time (`price_changes`) | ✓ `recurring` | ✓ the monthly total of what recurs | - | - |
| 9 Bills due | - | - | ✓ the next 30 days | ✓ what is due, in all | - | - |
| 10 Budget headroom | - | - | - | ✓ `reallocation_candidates` | - | ✓ "find $X" against it |

**40 sections.** Proposed order of building, so the first batch is useful at once:
- **Batch A (14):** what the twelve templates and Rob's example need - 1.1, 1.3, 1.4, 2.1, 2.2, 3.3, 4.1, 5.1, 6.3,
  6.4, 6.6, 7.1, 7.2, 10.4.
- **Batch B:** the rest of the lists and snapshots.
- **Batch C:** the comparisons (they need H-c's two periods for free words; by hand they work at once).

**Ruled 2026-10-31 (Rob: *"Accept, all 40 at once build after 3:30pm est"*):** the table as written, all 40 sections
built together rather than in batches, the build starting after 3:30 pm Eastern that day.

**Two corrections to section 11, said openly (2026-10-31, while building):**
- **The table ticks 39, not 40.** Payees has three sections (1, 3, 5), and "40" was a miscount when the table was
  written. All 39 are built, as ruled ("the table as written"). A 40th would be a new pairing, for Rob to name.
- **Section ids are shape.subject**, Rob's own order (*"Monthly totals catalog is 1-9, Monthly Debt is in Catalog
  5"*): 1.5 is monthly totals of debt payments, as P1 says. The batch list above wrote subject.shape; with all 40 at
  once the batches are moot.

## 12. Stages 1-3 built (2026-10-31)

Rob: *"after the gates are done lets build this final piece"*; C3 *"Accept, all 40 at once build after 3:30pm est"*.

- **Stage 1, the catalogue** (`core/report_sections.py`): six shapes, ten subjects, the 39 sections, each run from
  item 114's lookups and the record's own rows - every figure Groundwork's (H22), no model call. A period is read by
  `core/periods.py` (P5); one it cannot read is said, not guessed. A section the record cannot speak to says *"Groundwork
  doesn't know yet"* and what would let it (on the sample: yearly price steps need 13 months). **Ten templates**: the
  twelve reports less the visit report (health, TM7 - no health sections) and the import audit (about imports, not
  money); those two stay their own pages. Every report page is unchanged (C2).
- **Stage 2, the section list page** (Reports → *Build your own* → **Build a report**; `/api/reports/builder/catalog`,
  `/run`, `/saved`): each section is *Show* (shape) and *Of* (subject) - only the pairings the table ticks - with the
  period in the person's words and the settings it needs (category, payee, compared with, amount, a debt). Add, move
  up and down, remove; *Start from…* a template or a saved report. **Save…** keeps the sections and the chosen style
  (P11), only on the person's press; Delete removes it.
- **Stage 3, the six styles** (P13-P15): text and grid, text and charts (the default), charts first, text only,
  print / PDF, compact. A section may carry its own (C11). The shape picks the chart (P14): bars, a line (with the
  budget line where there is one), side-by-side bars, figure tiles; a list is always a table. **⎙ Print** redraws in
  the print style and prints only the report.
- **Checked in the app** (a throwaway database, the sample household): Rob's example - *"Debt payments, June 2026 to
  September 2026: $4,796.00 in all"*, $1,199.00 each month, as bars; Debt Progress as a template ($39,940.00 owed in
  May, $36,790.00 now, debt-free August 2030 on the plan, its assumptions stated); each style drawing differently from
  the same sections; a report saved with its style.
- **The gate:** s269 (12 checks), s268 (11). Item 114's Q05, Q07 and Q10 closed first (AGENT_HANDS.md section 16).

**Next, stage 4:** the index (P3-P6) - the Ask box reading "monthly totals of debt payments from June to September"
into section 1.5 and its period, with no model call; then the section 6 question set, written by Rob before measuring.

## 13. The 25 requests (C8), written 2026-10-31

Rob's 25, verbatim, are in `tests/report_requests.json`, each with the sections, settings and outcome proposed for it.
They were checked against the 39 sections on the sample household before measuring. 13 build as the catalogue
stands, four should ask, six say what Groundwork cannot do yet, two are refused as requests to act. Four gaps showed:

| Gap | What | Requests | Proposed |
|---|---|---|---|
| G1 | No section narrows to one account | R03, R12 | an *account* setting on the spending sections |
| G2 | Debt payments cannot narrow to one debt | R04, R20, R22 | the *debt* setting (today only on 6.6) on 1.5, 2.5, 3.5, 5.5 |
| G3 | Transfers are not a subject | R14 | stays out: says so (transfers are left out of spending on purpose) |
| G4 | "lately", "between paydays" are not periods | R12, R17, R19 | ask the period; never guess (P5) |

Also seen: "the last six months" reads as the six full months before this one (April-September). On the sample,
April is before the record, so the section shows May-September without saying April is missing. A section title
echoes the category as typed ("groceries, each month"), not the record's name.

**Ruled 2026-10-31.** Rob: *"Accept all four."*

- **G1, built:** an optional *account* on the spending, category, payee and income sections (not the snapshots: the
  budget and income lines are the household's). The name is matched like a debt's ("the Visa" is Cashback Visa); a
  name the record lacks is said, with the accounts it has. List of items with an account shows the charges row by row.
- **G2, built:** an optional *debt* on the debt-payment sections. A payment belongs to a debt when it is linked to it
  on Debt Payoff, or when its payee carries a distinctive word of that debt's name and of no other ("Riverside Auto
  Finance" is the Riverside Auto loan). On the sample: $600.00, $389.00 and $210.00 a month, the $1,199.00 together.
- **G3:** transfers stay out of the catalogue; Groundwork says they are left out of spending on purpose.
- **G4:** "lately" and "between paydays" are asked, never guessed - R12 and R17 now ask the period.
- Titles now carry the record's own names ("Groceries, each month"; "…, on Cashback Visa"; "…, to Riverside Auto loan").
- s269: five more checks. The expectations in `tests/report_requests.json` are updated to match: 14 build, 2 build and
  say, 5 ask, 2 say what the record cannot tell (transfers, pay-stub deductions), 2 refused as requests to act.

**Periods, ruled 2026-10-31.** Rob: *"depends on whether the user is measuring full calendar months or a rolling
30-day/date-to-date window, and whether the current month is complete."* Built in `core/periods.py`:

| Said | Read as |
|---|---|
| "the last six months" | the six most recent complete calendar months. This month counts once complete - on its last day; before that it is left out and the section says *"October 2026 is left out: it is not over yet."* |
| "the last six months to date", "… up to today" | date to date: the day after the same date six months back, to today |
| "the last 30 days", "the past 2 weeks" | date to date, ending today |
| "June 15 to September 15", "since June 15" | date to date, the days named; across the new year when the end comes first |

A date-to-date section counts only its days, says them ("15 June 2026 to 15 September 2026"), and says which month
counts from or up to which day. Where the record starts after the period does, the section says when it starts. "Today
is the last day" is the calendar's word on complete: a statement for that day may not be imported yet.
s268 and s269: three more checks; s268's "the last 3 months" on 31 October is now August-October. One help entry: what
"the last six months" means.

## 14. Stages 4-7 built (2026-11-01)

Rob: *"lets complete the rest of the stages"*.

### 14.1 Stage 4: the index (P3-P6)

`core/report_index.py`, `read(reader, text)`. Build a report has an Ask box above the sections:
- **Read in order, by code, no model.** First a request to act ("email", "schedule", "every Friday"), then the style
  ("as a table", "for printing", "out loud"), then things the record has no subject for (transfers, pay-stub
  deductions), the period (`core/periods.py`, P5), the record's own names (P4), and the template, shape and subject
  terms (P3).
- **"Except" and "versus" are read by code too** (H-c's first half). Two debts make two sections. Two subjects make two
  monthly sections. Two periods make a comparison.
- **What it can't decide becomes one question with buttons** (step 2). Each button is the sections it would build. This
  covers:
  - a word with two meanings ("payments", "paying out", "the car");
  - two close names (P4);
  - a period like "lately" (G4);
  - a shape the subject has no section for;
  - a word nothing read ("the dog").

  **That last one is new.** The first build dropped such a word and showed all spending instead (section 14.3).
- **A name the record lacks** ("at Walmart") is dropped and said (P4).
- **When nothing is found** (step 3), it offers the templates.
- **A request to act** is never done. It says so and builds what it can show (R24, R25).
- **New spending setting: `exclude`,** the names left out, each the record's own. A name that is not in that section
  leaves nothing out, and the section says so (R21).
- **Every request it could not build alone is kept** (P6.4): the words, what the index found, what it asked, and what
  the person picked. The list is kept on this computer under *Requests Groundwork asked about*, shown there, and
  cleared by the person, the item 72 pattern. Requests it built alone are not kept.

### 14.2 Stage 5: measured, index alone (section 6)

`scripts/report_requests_measure.py`, on the sample household, built fresh. Results are in
`tests/report_requests_results/`.

| Set | Right | Wrong section built | Slowest |
|---|---|---|---|
| Rob's 25 (`tests/report_requests.json`) | 25 / 25 | 0 | 33 ms |
| 25 held out, **first run** | 20 / 25 | **2** | 32 ms |
| 25 held out, after the fixes | 25 / 25 | 0 | 32 ms |

**Said openly: Rob's 25 were in view while the index was written, so 25 / 25 there flatters it.** That is why I wrote
a second set of 25 rewordings (`tests/report_requests_heldout.json`). I wrote all 25 before running any of them, and
the first run is kept as it came out (`20261101-0100-index-first-run.json`).

Its misses:
- **Built wrong:**
  - "spend at Walmart" built all spending without saying Walmart is not in the record.
  - "Text me the budget every Monday" built categories ranked instead of the budget.
- **Asked instead of building:**
  - "top payees"
  - "what bills are coming up"
- **The scorer's error, not the index's:** one miss (H19) came from the scorer comparing a list with a word.

Every period was read right, and the four style terms too. The bar for index-only requests is under 1 s; all ran in
milliseconds.

### 14.3 Stage 6: phi's helpers (P7, P8)

`engine.pick_label`: one of a list of labels under a GBNF grammar, with the record's names quoted and escaped, then
checked again in code. I wrote 16 cases before any model run (`tests/report_helper_cases.json`). They ran on the M2,
8 GB, phi3.5 Q4, with Groundwork closed.

**The first run was 2 / 16** (`20261101-0104-m2-helpers-first-run.json`). Three of the causes were Groundwork's:
- **Silently ignored words.** "What did the dog cost us", "the wifi", "workouts" and "tunes" never reached H-b. The
  index read "cost" as spending and dropped the word it did not know, so it built all spending: a wrong section, in
  silence. **Fixed:** a word nothing reads is now asked about, with the categories as buttons and "All spending" last.
- **"made" was read as income** ("the payments I made"). It now needs "how much did we make".
- **The scorer** counted a helper's stated reading as a wrong outcome.

After the fixes:

| Helper | Phi's answer right | What it showed |
|---|---|---|
| H-a two meanings | 2 / 2 where the words decide; **0 / 3 "can't tell"** where they truly don't | It always picks one |
| H-b unknown words | 5 / 6 ("dog" Pet Food / Supplies, "wifi" Internet, "workouts" Gym / Fitness, "tunes" Streaming Music, "landlord" Rent / Mortgage) | "kids' piano lessons" read as Gifts; "can't tell" was right |
| H-c except / versus | 4 / 4, including "can't tell" for "the unicorn rides" | |

Every helper answered in about 1 s or less, against the 20 s bar. No helper wrote a figure; each answer is a name from
the list.

**What the measurement decided, per helper (C5):**
- **H-a and H-b only advise.** Phi does not say "can't tell" when it should, so its pick is shown first, marked
  *(likely)*, and the person chooses.
- **H-c builds on its pick and says it** ("Read "the stuff for the dog" as Pet Food / Supplies"). The name it leaves out
  is in the section's title.

This is a ruling for Rob (14.6).

### 14.4 Stage 7: H-d (P9)

*Suggest words Groundwork could learn* is under the kept list, AI on only. Phi reads the kept requests' unread words
and picks one of the record's categories or payees. Each suggestion is shown with Yes / No. On Yes, code checks that
the name is the record's, then keeps the word as the person's own, on this computer (C4); Forget removes it. An
accepted word is read before the built-in vocabulary, with no model.

Measured from six planted misses (4.9 s for all six). Five suggestions, each one for Rob to say whether he would
accept:

| Word | Suggested |
|---|---|
| dog | Pet Food / Supplies |
| wifi | Internet |
| workouts | Gym / Fitness |
| date nights | Restaurants |
| tunes | Streaming Music |

The first version also suggested "kids piano lessons" as GiftNook. The person had answered "All spending" for that
request, and now a request answered like that is skipped.

**One departure from P7:** H-d runs when the person presses the button, not "when idle". Groundwork starts no model
work the person did not ask for.

### 14.5 Also in this change

- **The backup reminder counted 7 days for 8** in the week the clocks go back. It subtracted two local times; it now
  compares real time. This was found because the gate ran at 01:15 on 1 November, just after DST ended.
- **A help entry:** "Can I just ask for a report?"
- **The gate:** s276 (20 checks); 4118 passed, 0 failed.

### 14.6 Rulings sought

| | Question | Recommended |
|---|---|---|
| D1 | **The built-in vocabulary** (`STYLE_TERMS`, `SHAPE_TERMS`, `SUBJECT_TERMS`, `TEMPLATE_TERMS`, `TWO_MEANINGS`, `NOT_SUBJECTS` in `core/report_index.py`). C4 says built-in terms change only by Rob's ruling, and these are mine. | Accept as the starting list |
| D2 | **H-a and H-b only advise** (measured: no "can't tell" where it was right). Or let them build on their pick, said, one click to change. | Advise only |
| D3 | **H-d on the person's press,** not when idle | On press |
| D4 | **Requests it had to ask about are kept** on this computer, shown and cleared by the person (P6.4). Item 114's R19 keeps the assistant's own questions nowhere; this follows item 72's list instead. | Keep, as built |
| D5 | **The expectations** in the held-out set and the helper cases are mine, written before running. Confirm them, or correct any. | Rob to read |

**Not done here:** the Windows laptop run, and a microphone try with "read it to me" (section 5, items 2 and 3, Rob's
runs).
