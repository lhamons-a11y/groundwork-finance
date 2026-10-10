# Item 64 — Reports that stand on their own without AI; AI adds the teaching

Opened 2026-10-09. Rob: *"if the software is running on a computer that the ai is running too slow can turn it off
and still have a great experience. In fact we should off pre built reports for no AI usage and show graphs and data
that help summarize what the ser would want to see in that report. Where an AI report will also offer the same data
but can focus on things that can help inform the user and teaches the user. which is the ultimate goal."*

**N1–N7 RULED as recommended 2026-10-10 (Rob: "I accept item 62 and 64").** No code yet: the build needs its own go-ahead.

## 1. What is true today (measured 2026-10-09, master)

- **With AI off, a report's narrative slot shows an error-shaped panel.** `_rcRenderAIFallback` shows *"Written
  analysis unavailable — here's what was computed"* over the raw `dataLines` in a monospace block, with *"Try written
  analysis again"*. It reads as a failure, not a report.
- **The AI-off monthly report text breaks the no-verdict rule.** `_rcMonthlyFallbackText` writes *"was a solid month"*,
  *"was a tight month"*, *"These are the areas worth reviewing if you want to find room"*, *"every dollar applied now
  saves money in interest"* and *"Start next month by identifying one category to trim"*. No AI is involved, so the
  voice check never sees it.
- **The reports already compute what a report needs.** The catalogue's reports each build their figures and
  `dataLines`: monthly, category deep-dive, annual, budget vs. actual, debt payoff and progress, net worth, income and
  savings, distance travelled, the advisors. Several already draw charts.
- **A10 (2026-10-02): every surface works with AI off.** Today the reports "work", but as a fallback, not as a design.

## 2. Points for ruling

**N1. Every report has a designed AI-off form.** In place of the fallback panel, each report shows its *summary*:
- the two or three charts that answer its question (spending by category, the month against the budget, the debt
  balance over time, the net worth line);
- the key figures as plain statements of fact, each with its working (the transparency standard);
- *what changed* since the last period, as signed differences.

The data comes from the same computation the AI would be given.
*Recommended.*

**N2. The words follow the same rules as the AI's.** Every sentence in an AI-off summary passes the voice check's rules
(no verdicts, no advice, no commands), checked in the gate against the shipped text. The monthly fallback's *"solid /
tight month"* and *"trim"* wording is rewritten as facts: *"You kept $867.82 of $4,280.00 income in September."*
*Recommended.*

**N3. With AI on, the same summary, plus teaching.** The AI report shows the same charts and figures, so nothing is
lost either way. Its narrative focuses on *informing and teaching*: what a figure means, which question it raises,
the mechanism behind it (*teach the question*). It doesn't retell what the charts already show. Once item 58 is
built, research entries attach where they apply.
*Recommended.*

**N4. Turning AI off is presented as a good choice, not a downgrade.** Settings → AI says plainly that with AI off,
every report shows its full summary. Where AI is slow (the engine can time a first answer), it offers: *"AI is
running slowly on this computer. Reports work fully without it. Turn it off?"* It's the user's choice, never
switched on their behalf.
*Recommended.*

**N5. First reports.** Monthly, budget vs. actual, debt payoff and progress, category deep-dive and net worth. The rest
follow in the same shape.
*Recommended.*

**N6. A10 kept by test.** For each report: AI off renders charts and figures with no "unavailable" panel, and its
text passes the voice rules. A mutation that puts a verdict word in a summary fails.
*Recommended.*

**N7. Lines.** Master only. The monthly fallback's verdict wording is on 1.x too; whether that's fixed there is your
call under the 1.x rule (it's wording, not a saved figure).
*Recommended.*
