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

**ACCEPTED 2026-10-31, no code yet.** C1-C11 ruled as recommended, one by one (section 10); MCP dropped (section 9).
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

The index leans on the same routing item 114 still misses. In order:
1. Requests to act decided by Groundwork before the model (section 11, fix 1).
2. Pages and the guide (fix 2), wrong lookups (fix 3).
3. The 60-73 s stalls, measured with other apps closed and on the Windows laptop (fix 6).
4. H19 / H20c, if goals become a subject.

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
