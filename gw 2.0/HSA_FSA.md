# Item 86 — HSA and FSA balances (item 45 H5, the first slice of the health module)

**OPENED 2026-10-14 (Rob: "Health H5: HSA/FSA"). For ruling; no code, no schema, no authorisation.**

## Summary

An HSA or FSA is money the user already has, held at an outside custodian, with rules the user did not choose: a
yearly contribution limit set by the IRS, and for an FSA a date after which unspent money can be lost. Groundwork
doesn't show either account today. The account types are Checking, Savings, Credit card, Cash and Other. So an HSA
gets typed in as "Other" or left out, and nothing ever says "this money is yours to spend on care" or "this money
expires on 31 December".

This slice adds HSA and FSA as kinds of account. It shows each balance with its working, shows the year's
contributions against the limit that applies, and gives an FSA's deadline. It warns before FSA money would be lost
**only** when the user has entered their plan's real deadline and carryover rule. Without those terms it says plainly
that it can't tell whether any money is at risk. The H5 ruling (2026-10-08) is the boundary: money only, no person,
medication or diagnosis, unknown terms stay unknown, and none of H7's plan-year or deductible tracking. It works with
AI off and is master only.

## 1. What is there today (measured on master `7727072`)

- `Account.type` is free text. The app offers `checking`, `savings`, `credit_card`, `cash` and `other`
  (`static/js/app.js` `ACCOUNT_TYPES`). Investments use `investment`. There is no `hsa` or `fsa` anywhere in the code.
- `SinkingFund` is a target the user chose, with money that *"sits in the user's checking/savings"* (its docstring).
  The 2026-09-05 design (§1.3) proposed reusing it. Measured against the code, that is the wrong home: HSA and FSA
  money sits at a custodian, not in checking, and the ceiling is the IRS's, not the user's. A fund row would claim
  the money is somewhere it isn't.
- `core/health_boundary.py` (item 45 stage 1, H6) decides what counts as health through the protected list's
  category names. Every place health data can leave the app is registered in `HEALTH_SINKS`.
- `core/plan_year.py` holds insurance plan years. It has no callers, and H5 must not wire it (ruling, qualification 2).

## 2. Points for ruling

**F1. HSA and FSA are account types, not funds.** Add `hsa` ("HSA") and `fsa` ("FSA") to the account types. The
balance is the account's balance: typed in, or read from that account's imported statement like any other account.
Net worth counts it like savings. *Recommended*, for the reason in section 1: a fund row would put the money in the
wrong place.

**F2. The terms are the user's own, kept per plan year, and every one can stay unknown.** Each HSA or FSA account
has one small terms record per plan year. Changing a term keeps the old one as history, never overwrites it.
- **HSA:** coverage (self-only or family) and whether the 55+ catch-up applies. Both are asked facts with "I don't
  know" allowed. Groundwork never guesses age from anything.
- **FSA:** plan year end, then which of three applies: a grace period (to a date), a carryover (up to an amount), or
  neither. Plus the last day to submit claims, and the yearly election.

This needs a new table, so a `SCHEMA_VERSION` bump and the s51 fingerprint pin. These are the FSA's own rules, not
the insurance plan year. Deductibles and out-of-pocket stay with H7 stage 2, and `plan_year.py` stays unwired.
*Recommended.*

**F3. The IRS limit is a shipped, dated table, shown with its source.** For example, 2026 HSA: $4,400 self-only,
$7,613 family, plus $1,000 at 55+. The health FSA limit and carryover figures are to be checked against the IRS
release when this is built. Each figure says which IRS release it came from. When a year's figure isn't in the table
yet, the card says so rather than reusing last year's. The limit shown assumes a full year of eligible coverage, and
says so: partial-year rules are left out, named as left out. *Recommended.*

**F4. Contributions are counted only from what the record shows.** This year's contributions are the deposits in the
HSA or FSA account's own imported rows. If that account isn't imported, or a month is missing, the card says the
total is incomplete and which months are missing. It never treats a missing month as $0 (absence is not zero).
Payroll contributions often never appear in checking, so the HSA's own statement is the source. Typing a
contribution total is allowed and is labelled as typed. *Recommended.*

**F5. The two warnings, both facts with their working:**
- **HSA over the limit:** contributions on record against the limit for the coverage the user entered. If coverage
  is unknown, there is no warning, just a line saying the limit can't be checked without it.
- **FSA money at risk:** balance, deadline and carryover rule, all from F2. With the terms entered: *"$340 is in
  your FSA. Under the terms you entered, up to $0 carries over and the rest is lost after 31 Dec."* Without them:
  *"Groundwork can't tell whether any of this is at risk: the plan's deadline and carryover rule haven't been
  entered."* It never says "spend it" and never suggests what to buy.

The warning shows on the account's card always, and in Needs attention from 60 days before the deadline. *60 days
recommended*; you may prefer a different number.

**F6. Privacy: an HSA or FSA account's rows are health, whatever their category.** Money in an HSA is no more
sensitive than savings. But an imported HSA statement lists where the money went: a pharmacy, a doctor, a lab. Those
names disclose health even with no person attached. So every row of an `hsa` or `fsa` account goes through
`health_boundary`'s classifier as health: scrubbed from logs, model context and the AI log, and left out of exports
unless the health box is ticked. s208's sink registry adds a case to prove it. The balance and the limit figures stay
ordinary money. *Recommended*, because without it H5 would open a route around H6.

**F7. No judgement, no advice.** Groundwork shows the balance, the limit, the deadline and what the record says. It
never says "max out your HSA", "invest your HSA" or "you're behind". If the user asks how an HSA can be invested, the
help text explains how it works (teach the question) with no recommendation. That follows Rob's rulings of
2026-10-14: the user decides what financial independence is, and Groundwork never judges. *Recommended.*

## 3. Left out of this slice, on purpose

- Plan-year deductible and out-of-pocket tracking (H7 stage 2), and the health reserve (stage 3).
- Which expense an HSA or FSA paid (`HSA-paid` and `FSA-paid`, design §1.2). That is a link between a payment and an
  expense, which is the payment relation work, so it waits for its own stage.
- The tax link (HSA contributions lowering AGI, Form 8889). That belongs with the year in review (stage 4).
- HRA and limited-purpose FSA. Name them if you want them in; recommended later.
- The 1.x line (master only, as ruled).

## 4. How it would be built and proven, once authorised

One stage: the account types, the terms table with migration and pin, `core/hsa_fsa.py` (limit lookup,
contributions on record, the two warnings, all named and tested), an Accounts page card, a Needs attention entry,
and the F6 health classification. The new smoke section would check the rendered sentences, never just flags:
unknown terms produce "can't tell", a missing month makes the total incomplete, no advice wording appears, an HSA
row is scrubbed from a log line and from an export, and the table refuses a year it doesn't have. It would be gated
in its own worktree, accepted before push.

## Closing

Of all the health pieces, this is the one that can be built now. It needs no names, no medications and no insurance
plan, and it sits behind the privacy layer that is already accepted. Its only real risk is the FSA warning, and F5
keeps that warning to facts the user gave. F1, F2 and F6 are the rulings that shape the code. F3 to F5 and F7 set
what the user reads.
