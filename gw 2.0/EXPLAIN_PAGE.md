# Item 103 — Explain this page

**RULED 2026-10-19 by Rob:** *"this feature is what people think ai in software is suppose to be. Is their a way to add
explain this page to me? and the search feature reads the page and explains what the page is calculating in simple
words and what the numbers mean."* The design was approved: *"yes feel free to add that to 103 also push."*

## What it does (E1-E5)

**E1. One panel, two ways in.** "Explain" in the top bar, or the Ask box: "explain this page", "what does this page
mean", "what am I looking at", "what do these numbers mean"; "explain my budget" / "explain my debts" opens that page
first. Like the Ask box it is AI help, shown only while AI is on. "Explain the avalanche method" is still a question
for the guide.

**E2. What the page works out - always right.** First, Groundwork's own fixed words for the page and the tab on screen
(every page; each tab of Budget, Debt Payoff, Health and Before You Buy), e.g. *"What's left" is income less all of
them - the room in the plan, not money in an account.*

**E3. What your figures mean - from the screen only.** With AI on, the figures on screen go to the model, each read
with its own label ("Left to save or spend · $2,279.41"). A line crosses only if every word in it is Groundwork's own
(its page, its code, your category names) and every number is a figure: a line in anyone else's words - a bank's
description - is left out (item 8, H5: trim the input, never admit it). A figure with no label in front is left out.
Groundwork's short labels are said in full ("$120.00 min" → "minimum payment $120.00"). It is fenced as data,
declared by kind, and the model is told: three sentences, one line each, its own label, never connect, compare or
compute figures, no advice, no judging.

**E4. Checked before it is shown.** Every number in the answer must be a whole figure on the page ("$4,200" counts as
"$4,200.00"; a stray "2" from "2026" doesn't count). Otherwise only the fixed words show, saying why. A shown answer says:
*"it can mix up which figure is which, and the page itself is always right."*

**E5. Health and the Ledger get the fixed words only** (health stays out of the AI; the Ledger is the bank's wording),
as do Settings and the Assistant (no figures). Nothing is saved or changed.

## Measured (Rob's M2, the shipped Phi-3.5 on Metal, 3-6 s an answer)

- **Net Worth:** correct every run ("Liabilities ... amount to $4,200.00, fully accounting for the negative net
  worth").
- **Budget:** correct on two runs. On a third it called the $600.00 Food budget "expenses" - a misreading the number
  check cannot catch, which is why every answer carries the "can mix up" line.
- **Debt Payoff:** misread "min" as interest until the short labels were said in full; correct on the run after (one run).
- **Dashboard:** garbled "October 2026" into a word; the number check caught it and only the fixed words showed.

## Amended 2026-10-20: figures that know what they are (E3-E5 above are replaced by these)

**RULED by Rob:** *"So could we have meta data that the user can see but is attached behind the values that tells the
agent where in the historian and database where these values are located and then the result is only reading the same
way that the report is."* And: *"say someone see Restaurants $500.00 they don't think that is right it should show the
transactions that is in the category and break down each transaction in a grid like a spreadsheet."*

**A1. Every figure carries its key.** Where a page draws a figure it is tagged (`data-fig`), with whose it is
(`data-fig-of`: a budget line, a card). One list, `FIGS`, says for each key what it is called, how it is worked out,
and the record it is kept in - the table, the saved app state, the Historian entries (`historian_entries`,
`debt_balance_history`) where its changes are recorded. Hovering a figure shows that. Stage one: Budget (header, What's
Left, every line and group), Debt Payoff (the date, time left, owed, interest, DTI, the suggestion, each card's balance,
rate, minimum and payoff month), Net Worth (net worth, assets, liabilities, card and loan debt, the change) and the
Dashboard's debt card. The Dashboard's month tiles are the teaching layer's and stay untagged (app.js never reaches into
it); untagged pages give the fixed words only.

**A2. Explain reads only tagged figures**, each numbered with its name, value and meaning - never the page's text (the
Groundwork-words filter and the label spelling are gone with it). The model writes one line per figure, starting with
its number. A line is kept only when every number in it is that figure's own; a wrong pairing, a garbled value, a
missing figure or a summary line is dropped. What is shown is the figure's own name and value - Groundwork's - with the
AI's sentence under it, and "Where these figures come from" lists every figure with its record.

**A3. The transactions behind a spent figure.** A "spent" figure on Budget (a line, or a group with its subcategories)
is underlined; clicking it - or "See the transactions" in Explain, or "explain restaurants" / "why is food so high" in
the Ask box - opens a grid: date (and posted date), where (the merchant, and what the bank says), account, category,
amount, then the count and total, and whether that total is the page's figure. The figure and the grid read one list
(`_catTxnsInMonth` / `_budgetTxnsForCat`), so they cannot disagree. Tapping a row opens it in the Ledger to change it.

**Measured (Phi-3.5 on Metal, three runs per page, 2.5-7 s):** every run on all four pages showed an explanation; every
line shown had the right figure. The model's habit of garbling some values ("Jan 2dict", "-$4,20thy") only ever cost
that one line. Budget, three runs: "Left to save or spend (planned): $2,279.41 - the amount left for saving or additional
spending after accounting for your planned expenses, debt payments, and savings contributions."

## Status

Ruled and built 2026-10-19; amended and built 2026-10-20 (s248; s240 registers the model surface, s25 reads its per-page declarations).
