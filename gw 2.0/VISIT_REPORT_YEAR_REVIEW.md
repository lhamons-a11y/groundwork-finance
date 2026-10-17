# Item 91 — The visit report and the year in review (item 45 H7 stage 4)

**OPENED 2026-10-16 (Rob: "open stage 4"). For ruling; no code, no schema, no authorisation.**

## Summary

The design (`HEALTHCARE_MODULE_DESIGN.md` §1.5–1.6) has two documents here:
- **A visit report:** a cost receipt to take to an appointment, so a price question can be asked from facts.
- **A year in review:** an itemised health total for the person's tax preparer. Of all the health tax figures, it is
  the one Groundwork is placed to produce.

Both are possible now, but smaller than designed.
- **The visit report** as designed is per person and lists medications with what was paid. Named people are stage 5,
  and medication claims wait on H4, which is still open. So this stage builds it per provider, without a person or
  medications.
- **The year in review** can do most of its job already. Payments from an HSA or FSA are known (item 86), refunds
  back into health categories are on record, and the 7.5% floor needs one figure only the person has, their AGI.
  What Groundwork can't see, a reimbursement that never came back as a credit, is said plainly.

Design question Q3, whether the visit report ever leaves the machine, is answered in Q3 below: only when you print
or save it. Both documents are templated, with no AI and no clinical or causal sentence ever. Neither is tax advice.
Master only.

## 1. What is there today (measured on master `3b521a1`)

- **Item 65 W9's year-end packet** (`server.py` `_year_end`, Reports) totals the year by category, income, interest,
  donations and realized gains. It names missing months and accounts, and leaves health spending out unless the
  health box is ticked (H6 P3). It is printable and saveable as PDF and CSV. It has no health section of its own.
- **Item 86:** HSA and FSA accounts. Every row in them is health, and each one is known to be paid from that
  account. HSA contributions are on record.
- **Item 87:** the current plan, its deductible and out-of-pocket maximum, and the insurer's figures as typed, with
  dates.
- **Item 88:** the reserve.
- **H6:** the export and print paths are registered sinks, and health text is scrubbed from logs and the model.
- **Not there:** named people (stage 5), medication claims (H4, open), a "reimbursed" mark on a payment (the design's
  §1.2 field), bills not yet paid (stage 6), and medical trips (no trip is marked medical).

## 2. Points for ruling — the visit report

**Q3. It leaves the computer only when you print it or save it.** Groundwork never sends it anywhere. Print and save
go through the same registered H6 paths as the year-end packet (s208 lists them). *Recommended.*

**V1. Per provider, not per person, for now.** You pick the provider from the health payees on your record. You
pick from exact names that appear on your record, never a fuzzy guess. The report shows:
- what you have paid that provider, each payment with its date and account;
- the plan year's figures from item 87 (deductible and out-of-pocket maximum, met so far, as of the date you
  entered);
- HSA and FSA balances (item 86) and the reserve (item 88).

It leaves out a person (stage 5), medications (H4), and anything pending or unbilled (stage 6). The report says
which of those are missing and why. *Recommended.*

**V2. What a payment shows, and what it doesn't.** "You paid $220 on Mar 4 and $220 on Aug 19" is the claim. "A
visit costs $220" or "your next visit will cost $220" is not: a payment establishes the payment (the H4 rule, ruled
2026-10-09). *Recommended.*

**V3. Templated, with no AI, ever.** Every sentence is fixed text with your figures in it. No clinical sentence, no
causal sentence, nothing suggesting what to ask about care. The design §1.5 rule is enforced by a list of forbidden
words checked by the gate. *Recommended.*

**V4. Nothing stored.** Which names belong to a provider is picked each time and not saved, so no grouping of your
health payees sits in the database. *Recommended*; the other choice is to remember your pick, which would be stored
as health data under H6.

## 3. Points for ruling — the year in review

**Y1. It is a "Health care, for Schedule A" section of the year-end packet**, shown only when the health box is
ticked, and printed or saved the same way. It is not a separate document. *Recommended.*

**Y2. What counts, and what is set aside, each line shown with its reason:**
- **Counted:** payments in health categories from ordinary accounts, less refunds and credits back into health
  categories, each listed with its date.
- **Set aside, with the reason:**
  - payments from an HSA or FSA: already tax-advantaged;
  - insurance premiums: they count only if paid with after-tax money, which Groundwork can't see, so they are
    listed for the preparer to decide.

*Recommended.*

**Y3. What Groundwork can't see is said.** *"If any of these was reimbursed by insurance or a plan in a way that
didn't come back into a health category, it doesn't count, and Groundwork can't tell."* No "reimbursed" field is
added in this stage. *Recommended.*

**Y4. The 7.5% floor, only with your AGI.** You type the year's adjusted gross income (an asked fact, labelled as
yours). With it, the report shows the floor (7.5% of AGI) and whether the counted total is above it *on these
numbers*, and by how much. Without it, the report says whether the total clears the floor can't be known. It never
says "you can deduct". It adds that itemising only helps when itemised deductions beat the standard deduction, and
the preparer decides. *Recommended.*

**Y5. HSA figures for Form 8889, as supporting detail:** contributions on record (item 86) and payments out of the
HSA, with the note that the custodian's forms (5498-SA, 1099-SA) are the authoritative ones. *Recommended.*

**Y6. Completeness from the packet.** Months and accounts with nothing imported are named, as the packet already
does. The health total is marked incomplete when they exist, never treated as zero. *Recommended.*

**Y7. Medical mileage is left out**, and the report says so: no trip is marked medical yet. That can be its own
item. *Recommended.*

## 4. Left out, on purpose

- **Medications (H4), named people (stage 5), pending bills (stage 6) and collections (stage 7).**
- **Filling in any tax form:** the design rules it out (§1.6, "a report, not a filled-in form").
- **A "reimbursed" mark on payments.**
- **The 1.x line.**

## 5. How it would be built and proven, once authorised

1. `core/health_documents.py`: the visit report's figures and the Schedule A section, with every sentence a fixed
   template.
2. The provider picker.
3. The packet section on the health tick.
4. One asked fact, AGI by year, stored like the household's other asked facts.

A new smoke section checks:
- nothing leaves except through the registered print and save paths;
- the forbidden-word list catches every sentence;
- HSA and FSA rows are set aside with their reason;
- a refund lowers the total;
- with no AGI it says it can't tell;
- with AGI the floor is shown as a fact on these numbers;
- missing months mark the total incomplete;
- no medication or person appears.

## Closing

Both documents turn the record into something a person can carry into a room, without letting the record claim more
than it holds. Q3 and V1 set the visit report's limits. Y2 to Y4 decide whether the year in review is honest, and
each says what Groundwork can't see instead of guessing.
