# Yearly price steps: a bill that goes up at the same time each year (item 106)

Opened 2026-10-21 (Rob: *"if say insurance or internet increased in price that budget would pick up on that increase
and as we have more data Groundwork can see what percentages that the utility has increased and if those increases
happen at a certain time of year and then the projection could identify that and show the user ... ie February 2027
municipality bill has increased 3.2% year after year. This is your projected bill. It can ask the user is your
municipality bill now $XXX.XX? If the user says yes then groundwork now can predict that price moving forward in budget
and that will also allow groundwork to predict the following year rate increase."*). **No code.** Y1-Y11 for ruling.

---

## 1. What exists (measured against master `1c2d346`)

- **A price step is already found** (item 65 W2, `core/price_change.py`, s211). When a steady recurring charge moves to
  a new level, the Budget page's *Price changes* list says so, *"Netflix: $23.23 through April, $25.09 since May"*,
  and one tap updates the budget line, with Undo. Only the **latest** step is found (`step()` walks back from the
  newest charge and stops at the first).
- **Its thresholds were set for "did the price change", not "how much each year".** A step must be at least 3% and 50
  cents, from 3+ steady charges to 2+ at the new level. A 2.5% yearly increase is never seen. A charge paid once a year
  (many insurance policies) never has 3 charges before and 2 after within the 12 it reads, so it is never seen either.
- **Usage bills are deliberately left out.** W2's null model found seasonal utilities read as a "step" on 18-30% of
  trend-free years. The fix was: a price only steps from a steady charge (W2 fix 1). So a municipal, water, electric or
  gas bill is never a price change today. **Rob's own example is the case W2 ruled out.**
- **A budget row can already follow a figure without its saved amount being rewritten** (`BUDGET_MONTH_AMOUNT.md` M1,
  `core/budget_month.py`): `amount` is what the household saved, `month_amount` is what this month's totals use. Item
  26's utility estimates use this today.
- **Item 26 already separates use from price** for electricity and gas (a degree-day fit per household, EIA prices).
  It has no water, sewer or trash rate.
- **How much history a household has** decides everything below. On the live ledger in October W2 read 13 months, so
  at most **one** yearly step per payee is visible today. A Quicken import (`quicken_import.py`) can bring older years.

---

## 2. Proposed

**One sentence:** Groundwork keeps a yearly record of each bill's price steps from the ledger. When the steps fall in
the same month year after year, it shows the expected new amount before that month. When the first bill of that month
lands, it asks *"Is your municipal bill now $XXX.XX?"* The answer is the household's, and it becomes the new budget
amount and the next year's starting point.

### Y1. Every step, by year, from the ledger
A payee's whole history is read for **every** price step, not only the latest: when (the month of the first charge at
the new level), from what, to what, and by what percent. Derived on every read, never stored (no silent learning). The
records behind each step stay listed, as in W2. *Recommended.*

### Y2. A yearly pattern
A pattern is **2 or more steps in different years whose months are within one month of each other**, and no step in
between. The yearly figure is the **median** of those steps' percents, so one large jump doesn't move it.
- With one step, it is stated as a fact (*"went up 3.2% in February 2026"*) and nothing is projected.
- With 2 steps the words say *"the last two Februaries"*. *"Each year"* is said only from 3.
- Steps that disagree a lot (the highest more than twice the lowest) are shown as a range, or not projected. The null
  model (section 4) sets that line.

*Recommended: 2 to project, 3 to say "each year".*

### Y3. A lower floor inside a yearly pattern
W2's 3% floor misses ordinary yearly increases (2-3% is common for insurance, internet and municipal rates). For a
**steady** charge whose normal swing is near zero, a step of **1% and 50 cents** is clear evidence. The lower floor
applies only when looking for a yearly pattern, and only after the null model passes it. W2's *Price changes* list
keeps its own rule. *Recommended.*

### Y4. Bills paid once a year
A yearly charge (an insurance premium, a membership) is compared **charge to charge**: each year's charge against the
last. W2's 3-before, 2-after rule cannot apply to something charged once a year. *Recommended.*

### Y5. Usage bills (municipal, water, sewer, electric, gas)
The hard case, and Rob's example. The amount follows use as well as the rate, so a February bill 3.2% higher than last
February's may be a rate change or a colder month. Three ways, for ruling:
- **(a)** Compare the same month across years and say only that: *"February's bill: $X in 2026, $Y in 2025 (+3.2%)."*
  No rate claim, no projection. Honest but weak.
- **(b)** Where item 26 has a fit for the household (gas, electric), take the year-over-year change in **price after
  use is accounted for**: the bill against what the fit says that month's use should cost. Projection allowed only if
  the null model passes on seasonal series.
- **(c)** For water, sewer, trash and municipal bills, which item 26 does not model: the **rate** comes only from the
  household's word or the biller's statement (item 68). The ledger may prompt the question (*"Your February bill was
  3.2% higher than last February's. Did your rate go up?"*). It never answers it (`ASKED_FACTS.md`).

*Recommended: (b) for gas and electric, (c) for everything item 26 does not cover, (a) as the fallback wording.*

### Y6. The projection on the budget row
In the month before the expected step, the budget row shows the figure **beside** the saved amount: *"Projected from
February 2027: $XXX.XX (+3.2%, the median of February 2025 and 2026)."* It is a figure the row can follow (M1). The
totals use it only if the household chooses to follow it; otherwise they keep the saved amount and say so. *Recommended,
the same as item 26 U3(a).*

### Y7. The question
When the first bill in the expected month lands, Groundwork asks once: *"Is your municipal bill now $XXX.XX?"*
- **Yes:** the budget row's saved amount becomes $XXX.XX, shown first and with Undo. That is the only write, and the
  answer is recorded as *"you told us"*, dated.
- **No, it's $___:** that figure is used, and recorded the same way.
- **Not sure / not now:** nothing changes, and the question is not asked again for that month.

One bill is enough to ask, where W2 needs two to *say* a price changed: here the household confirms, the ledger only
prompts. *Recommended.*

### Y8. Next year's prediction
Each year's step comes from the household's answer where there is one, otherwise from the ledger. The answer wins for
that year. The median is worked out again on every read, so each confirmed year sharpens the next projection.
*Recommended.*

### Y9. Words
Facts with their years, never a verdict or a promise. *"Has gone up about 3.2% each February (2025: +3.1%, 2026:
+3.3%)"*, never *"will go up"* or *"expect"*. Decreases are said the same way. Every figure is tagged with its key
(item 103), so Explain and the hover show the charges behind it. *Recommended.*

### Y10. Where it shows
- The budget row (Y6) and the question (Y7).
- The Budget page's *Price changes* list gains a *Yearly* note beside a payee with a pattern.
- The Sunday check-in (item 76) names it the week the expected month begins.
- The calendar (W3) marks the expected month.

*Recommended.*

### Y11. Line
2.0 only. Nothing new stored except the household's answers. *Recommended.*

---

## 3. Cases

| # | the record | what Groundwork says |
|---|---|---|
| Yp1 | Internet $56.55 to Mar 2025, $58.81 from Apr 2025, $61.16 from Apr 2026 | "Has gone up about 4% each April (2025: +4.0%, 2026: +4.0%)." In March 2027: projected $63.61; the first April bill asks "Is your internet bill now $63.61?" |
| Yp2 | One step only, Feb 2026 +3.2% | "Went up 3.2% in February 2026." No projection. |
| Yp3 | Steps in Feb 2025 and Sep 2026 | Two price changes, no yearly pattern (months too far apart). |
| Yp4 | Insurance paid yearly: $1,140 (2024), $1,041 (2025), $1,083 (2026), each in June | Charge to charge (Y4): +5.0%, +4.0%; "the last two Junes", projected about $1,132 in June 2027. |
| Yp5 | Municipal bill, no item 26 fit, Feb 2026 bill 3.2% over Feb 2025 | Y5(c): "February's bill was 3.2% higher than last February's. Did your rate go up?" No projection unless the household says so. |
| Yp6 | Electric, item 26 fit, price after use +6% each January for 2 years | Y5(b): projected, if the null model passed. |
| Yp7 | Steps +2% and +9% | Range "2-9%", or no projection (Y2, set by the null model). |
| Yp8 | Household answers "No, it's $76.91" | $76.91 is the saved amount; that year's step is worked out from it (Y8). |
| Yp9 | Household answers "Not sure" | Nothing changes; asked again only next year. |
| Yp10 | A price drop each January | Said the same way: "has gone down about 2% each January". |
| Yp11 | 13 months of history | At most one step per payee: Yp2's wording only. Said plainly in the list: "A yearly pattern needs two years of history." |

---

## 4. Null model, before anything ships

Like W2's (`scripts/w2_null_model.py`), seeded, 4,000 series per row:
- steady charges with **randomly timed** steps (the false-pattern rate);
- seasonal usage bills with no rate change (for Y5(b));
- true yearly steps of 1-8% with ±1 month jitter and 2-5 years of history (the found rate);
- yearly-paid charges (Y4).

**The bar, proposed:** no more than 2% false yearly patterns on any series without one; yearly steps of 2% or more found
at least 95% of the time with 2+ years of history. The same run sets Y2's "steps disagree" line and Y3's floor.

**Then the live ledger, read-only:** how many payees have 2+ years, how many show a yearly pattern, and what they are.
Expected to be few until 2027 unless older history is imported.

---

## 5. Ruling sought: Rob

1. **Y1-Y2:** every step by year from the ledger; a pattern is 2+ steps within a month of each other in different
   years; projected from 2, *"each year"* only from 3; the median?
2. **Y3-Y4:** a 1% / 50-cent floor inside a yearly pattern for steady charges; yearly-paid charges compared charge to
   charge?
3. **Y5:** usage bills as (b) for gas and electric, (c) ask for the rate on everything else, (a) as the fallback words?
4. **Y6-Y7:** the projection shown beside the saved amount and followed only by choice; the question on the first bill
   of the expected month, the answer the only write, with Undo?
5. **Y8-Y11:** answers win over the ledger for their year; facts-only words; the four places it shows; 2.0 only?
6. **Order:** the null model and the live read first, then the build?
