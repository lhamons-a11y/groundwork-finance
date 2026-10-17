# Item 92 — Named people (item 45 H7 stage 5)

**OPENED 2026-10-16 (Rob: "open stage 5"). RULED + BUILD AUTHORISED 2026-10-16 (Rob: "I approve N1-N8 as recommended. Build item 92.").**

## Summary

Health belongs to a person, and a household isn't one person. Until now every health figure in Groundwork has been the
household's. This stage lets you name the people in the household and say, payment by payment, whom care was for.
With that:
- the visit report can be about one person;
- a family plan's per-person deductible can be shown;
- the year in review can show the per-person split under the household total.

H6, the privacy gate this stage was waiting for, is built and accepted (item 45 stage 1).

The two design questions are mostly answered by rules already made:
- **Q4 (whose health, in a joint account?)** is answered by your 2026-08-13 ruling that *a joint account has no
  author*. A payment belongs to nobody in particular until you say whom it was for, and Groundwork never guesses
  from the card or account.
- **Q8 (are names enough?)** Yes. A person is a name you choose. The identity is the record, not the name, so
  renaming changes no figure.

Names are labels, not locks: anyone who opens Groundwork sees everyone, and the app says so where you add a person.
Medications stay out (H4 is still open).

## 1. What is there today (measured on branch `visit-report`, `2ab9124`)

- **`core/person.py`**, specified by `tests/test_person_identity_fixture.py` (no callers):
  - the person's id is identity, the name is presentation;
  - a reassignment is a correction with a reason, source and date, superseding and never overwriting;
  - an imported "patient" name must be mapped explicitly, never matched by name;
  - a person with history is deactivated, never destroyed;
  - the household total is the tax figure, and the per-person split is supporting detail.
- **Tables** `people`, `person_assignments` (against `healthcare_expenses`) and `person_enrolments` exist, empty.
- **Household mode** (Settings) holds two names, `household_user1` and `household_user2`, for greetings and the
  Sunday check-in. They are not linked to anything health-related.
- **Items 86 to 91:** the HSA and FSA, plan and readings, reserve, care-never-a-lever, the visit report per provider,
  and the Schedule A section.

## 2. Points for ruling

**N1 (Q8). A person is a name you choose, and nothing more.** No birth date, no ID number, no relationship
required. Renaming touches no figure. A person with history can be made inactive but not deleted; one with no
history can be deleted. *Recommended.*

**N2 (Q4). Whom care was for is said payment by payment, never inferred.** A health payment has no person until you
say. "Household" means not said, and a payment without a person is never split between people. Groundwork never
infers the person from the card, the account or an imported "patient" name. A joint account has no author.
*Recommended.*

**N3. Names are labels, not access control.** Everyone who opens Groundwork sees every person's data. Where you add
a person, the app says so plainly: *"Anyone who opens Groundwork on this computer can see everything here, including
each person's health spending."* Who may see which account is the per-account visibility item noted 2026-08-13, its
own piece of work, not this stage. *Recommended.*

**N4. Saying whom care was for.** A health payment (in the Ledger and in the visit report) gets *"Who was this
for?"*, with your people and "Household". Changing an answer is a correction: dated, with the earlier answer kept,
never overwritten (`person.py`).
- After an answer, Groundwork may offer: *"Mark the other 4 payments to MILLBROOK MAPLE CLINIC as for Sam too?"*, only on
  your yes.
- Nothing is assigned by itself.

*Recommended.*

**N5. What people unlock in this stage:**
- **(a) The visit report for one person:** the provider's payments for that person. Payments marked "Household" are
  listed apart and named as not said.
- **(b) Per-person figures in a family plan:** item 87's readings can be entered per person (the insurer shows them
  per member), with the same rule as P1: typed, dated, never summed from spending.
- **(c) The year in review:** keeps the household total as the figure, with the per-person split under it as detail
  (design §1.7), so moving a payment between people never changes the total.

*Recommended.*

**N6. Household mode's names are offered, not copied.** If household mode has two names, the people screen offers:
*"Add Rob and Sam as people?"*. They are added only on your yes, and the two settings are left as they are.
*Recommended.*

**N7. Privacy under H6: names stay on health surfaces.** A person's name appears:
- on the health screens;
- in the visit report;
- in the health-ticked export and packet.

It never appears in the AI's context or the AI log, and never in an untickable export. Names are *not* added to the
log scrubber. A first name scrubbed everywhere would damage ordinary text, for example "Rob's Income", so they are
kept off those paths instead, and the test proves no path carries one. Assignment reasons are already scrubbed (H6).
*Recommended.*

**N8. How a payment gets a person, in the record's own terms.** The person is attached to a health expense
(`healthcare_expenses`), not to the bank row. Saying whom a payment was for is the household's statement that this
payment was for that expense. That is the expense identity rule ruled in September: the household's assertion mints
it, and a payment never mints one by itself. So an expense is created only when you say whom a payment was for, and
never for an unassigned row. The build measures the existing link between a payment and an expense first and uses
it. If none fits, it stops and brings that back to you rather than inventing one. *Recommended.*

## 3. Left out, on purpose

- **Medications (H4), the bill that lands (stage 6) and collections (stage 7).**
- **Per-account visibility:** its own item.
- **Enrolment dates:** who was on which plan when (`person_enrolments`). Not needed for anything in N5, so not used
  yet.
- **The 1.x line:** master only.

## 4. How it would be built and proven, once authorised

1. A storage layer keeping `person.py`'s rules over its tables.
2. The N8 link, measured first.
3. The people screen, with the N3 notice and the N6 offer.
4. "Who was this for?" on health payments, with the N4 offer.
5. The N5 extensions to items 87, 90 and 91.

A new smoke section checks:
- a payment has no person until assigned;
- a reassignment keeps the old one;
- nothing is inferred from card, account or name;
- moving a payment between people leaves the household total unchanged;
- a person with history can't be deleted;
- a name never reaches the AI's context, the AI log or an untickable export;
- the N3 notice is shown.

## Closing

This is the stage the privacy gate was built for. The rules that make it safe already exist, in `person.py`, the
expense identity ruling and "a joint account has no author". This item connects them. The one decision with
consequences beyond health is N3: Groundwork doesn't hide one person's data from another in this stage, and says so
where it matters.

## N8 measured 2026-10-16 - no existing link fits; brought back as N8 says

- The 1.x layer: `person_assignments` points at `healthcare_expenses` (id, incurred_on). Neither it nor
  `expense_funding_allocations` has any reference to a bank row.
- The 2.0 layer: `expenses` and `payments` are each minted by a Person's utterance. `incurred_by` (party → expense) is
  the ruled way to say whom care was for, and `payment_in_respect_of` (payment → expense) is ruled. A Person row
  carries its Party anchor. But **a bank row → payment link does not exist**: "A bank line ... can produce a candidate
  but cannot mint it", and a statement line's about-ness (Ab7) is a separate, unruled question.
- So N4's "Who was this for?" on a bank row has no faithful place to land. The options are put to Rob before any code.

### N8 decided — Rob, 2026-10-17

The 2.0 path was explored first (Rob's first pick). Its household side is ruled (expense, payment, `incurred_by`,
`payment_in_respect_of`, `proposition_concerns`). Its bank side is not: the bank as a party, the statement as a held
artefact (item 20's store, not authorised) and the importer contract are all fenced. So Rob chose **"tag now, absorb
later"**:
- **The tag.** "Whom this payment was for" is stored as dated, kept versions on the ledger row (`care_for`), named
  for what it is: a 1.x record of the household's answer, not an expense identity.
- **The absorption.** When the bank side is ruled, each tag becomes the household's statement in the 2.0 records:
  an expense minted by that answer, `incurred_by(person, expense)`, and the bank line concerning the payment. The
  tag's date and answer carry over unchanged. That migration is owed by whichever item rules the bank side.


## Built 2026-10-17 (s232; SCHEMA 20261017-named-people)

- **N1 / N3:** a **People** card at the top of the health section in Settings → Accounts.
  - Add, rename (inline: the app's window ignores the browser's own prompt, caught by the gate) and remove.
  - A person with payments or readings is made inactive, never deleted. One without is removed with their party
    anchor. A person named in any 2.0 record counts as having history.
  - The notice: *"Anyone who opens Groundwork on this computer can see everything here, including each person's
    health spending. Names are labels, not locks."*
- **N2 / N4 / N8:** "Who was this for?" appears in the Ledger's edit panel on health payments only, offering your
  people or "Household (not said)".
  - The answer is a tag on the ledger row (`care_for`, kept, newest current). A change is a correction and the
    earlier answer stays. The same answer again writes nothing.
  - Nothing is inferred: s232 proves one answer touches only its own payment, even with the same payee, card and
    account.
  - The offer *"Mark the other payment to MILLBROOK MAPLE CLINIC as for Sam too?"* acts only on its Yes.
  - No expense or payment is minted; that waits on the bank side (N8 decided).
- **N5:**
  - **(a)** the visit report has a "For" choice. One person's payments are shown, and the rest are listed apart as
    not said.
  - **(b)** a family plan's reading can be one person's (`health_plan_readings.person_id`), shown as *"Sam: $600.00
    toward the deductible as of … (from your insurer)."*. The old "not tracked yet" note now says the amounts can be
    entered.
  - **(c)** the Schedule A section shows "By person" under the household total. s232 proves moving a payment
    between people never changes the total.
- **N6:** household mode's names are offered (*"Add them as people?"*), only those not already people, and never
  copied.
- **N7:**
  - Names appear only on health screens and in the health-ticked packet.
  - No function that reaches the model or the AI log reads a name (AST-checked).
  - Names are not in the log scrubber ("S232 Robert's Income" stays whole).
- **Verified in the running app (dev database):**
  - adding Sam showed the notice;
  - choosing Sam on a MILLBROOK MAPLE CLINIC payment brought the offer for the other one, applied on Yes;
  - the visit report for Sam read "2 payments to MILLBROOK MAPLE CLINIC for Sam, $440.00 in all…".
- **Fixed in the app:** "the other 1 payment" now reads "the other payment".
