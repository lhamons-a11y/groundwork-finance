# Item 46 — Necessary care is never priced in months (H1)

Opened 2026-10-08 (Rob: *"push master h1"*). This is item 45's H1, ruled at design level 2026-10-08: *"H1 is a
correctness fix, not a health-feature dependency … The tests should verify the actual rendered conclusions, not merely
that a category is marked `protected`."* This document scopes it. **No code until Rob's go-ahead.** Master only: 1.x
builds strip the teaching layer where these sentences appear.

## 1. Every path that prices a protected category or charge in months (measured on master `dc004e3`)

Two engine functions feed six places.

**`large_charge_lesson`** (`server.py`) takes the biggest recent charges and prices the first that moved the payoff
date. It skips only transfers, income, debt and savings, so a hospital or pharmacy charge can be its subject. It feeds:
1. **The Ledger lesson** (`GET /api/transactions/lesson` → `teaching/ledger.js`): *"The St. Mary's Hospital charge … would
   have made you debt-free 2 months sooner."*
2. **The dashboard's charge item** (`server.py` ~3707, the proactive list).
3. **The monthly report's charge finding** (`server.py` ~4101 → `teaching/reports.js`): *"The CVS Pharmacy charge cost
   2 months on your debt-free date."*

**`budget_pressure`** (`core/solution.py`) prices every overspent category, protected or not. It only passes the
`protected` flag along. It feeds:

4. **The Budget page** (`teaching/budget.js`). For a protected category it says the budget is set too low, then adds
   *"That difference costs 3 months on your debt-free date and $… in interest."*
5. **The dashboard brake** (`server.py` ~3722). A protected category can be the month's brake, priced in months.
6. **The monthly report's overspend finding** (`server.py` ~4129 → `teaching/reports.js`): *"… that difference is 3
   months and $… in interest."*

**The narrator.** The report's findings (3 and 6) are also handed to the local AI (`app.js`, the causal-findings block)
as the only cause-and-effect claims it may make. Today that list can include a protected item's months, so the AI may
repeat them.

## 2. Points for go-ahead

**C1. The charge lesson never prices necessary care** (paths 1–3 at once). `large_charge_lesson` skips a charge
whose category is protected. It also skips an *uncategorised* charge whose merchant or description matches the
necessity floor (for example *CVS Pharmacy*, *St. Mary's Hospital*), because the same asymmetry as `_trims` applies:
over-protecting loses one lesson, under-protecting prices someone's surgery. The next eligible charge, if any, becomes
the lesson.

**C2. An overspent protected category is described, not priced** (paths 4–6). `budget_pressure` still returns a
protected row, because *"the budget is set $X/mo below what it costs"* is a true and useful correction. But it carries
no `months_cost` and no `interest_cost` (both `None`, with `priced: false`).
- **The Budget page and the report** keep the first sentence and drop the months-and-interest one. The *"Covering it
  would take … from …"* reallocation stays: it moves budget between envelopes, not care.
- **The dashboard brake** never selects a protected category, because a brake is a cost by definition.

**C3. The narrator gets nothing to repeat.** A protected item reaches the narrator's findings without months or
interest, and the charge path contributes nothing (C1). There is no separate rule to keep in step.

**C4. Gate, `s158`, checking what the user reads (the ruling's qualification).**
- **The rendered text:** each surface's real renderer (`budget.js`, `reports.js`, `ledger.js`, the narrator's findings
  block) is run in Node against a protected item. No output may contain a month count or interest tied to the
  debt-free date. The same renderers are also run against an unprotected item, to show they still price it.
- **The server paths:** a pharmacy or hospital charge (categorised, and uncategorised but named) is never the
  lesson. The next eligible charge is. A protected overspend is never the dashboard brake, and has no months in the
  report findings.
- **Mutations that must fail the gate:** the protected skip removed from `large_charge_lesson`; `months_cost` put back
  on a protected row; the brake allowed to pick a protected category; the Budget page's protected branch given the
  months sentence back.

**C5. Wording.** No new sentences. Each surface keeps the wording it already uses for a protected item, minus the
months clause. The Budget page's protected lead (*"has not come in under $X in N months — the budget is set $Y/mo
below what it costs"*) is already the right correction.

## 3. Not in this item

- H2, the wider floor (version 3), is a separate item. C1 and C2 use whatever `is_protected` says, so H2 later widens
  them automatically.
- 1.x is not changed.
- Nothing about health records, people or plan years: H5–H7.
