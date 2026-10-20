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

## Status

Ruled and built 2026-10-19 (s248; s240 registers the new model surface).
