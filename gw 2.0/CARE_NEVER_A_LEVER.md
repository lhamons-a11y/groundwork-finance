# Item 89 — Care is never a lever: one rule over every conclusion, and "uncertain" as an outcome

**OPENED 2026-10-16 (Rob: "Yes, open the two gaps as item 89 for ruling"), from an outside review of item 45 that
Rob pasted. RULED 2026-10-16 (Rob: "I approve C1-C4 and U1-U5 as recommended for item 89.") and BUILD
AUTHORISED 2026-10-16 (Rob: "Build item 89."). ACCEPTED + CLOSED 2026-10-16 (Rob: "I accept merge and push").**

## Summary

Groundwork already has rules against framing health care as money to cut:
- item 46: care is never priced in months;
- item 47: the necessity floor, version 3;
- the two wrong figures fix (s221): one server list of what is never a lever.

Each of those rules was proven on the surfaces that existed when it was built. Since 2026-10-08 several new
surfaces can suggest changes to spending: possible futures (item 66), income changes (71), the monthly review and
Sunday check-in (75, 76), the W items (65), plan edits (80), and Before You Buy with the agent (73). No single test
checks every one of them. This item makes it one rule with one sweep: every surface that can suggest a change is
listed, and a test proves none of them frames care as something to cut, delay or trade away.

The second gap: today a category is either on the floor or not. A name Groundwork can't classify reliably
("Vision", "Pharmacy", an uncategorised row from a clinic) falls to "not protected", so it can be offered as a lever.
The review asks for a third outcome, *uncertain*, which is never offered as a cut. The machinery for that already
exists: `core/classification.py` has a counterparty axis and `is_lever_candidate`, which fails closed on any health
signal. It was written to tests and has never been connected. This item connects it, deterministically and with no
AI.

## 0. What the review asked that is already built

| Review suggestion | Where it stands (master `54e5062`) |
|---|---|
| H1: protected care never priced as a sacrifice; tests on rendered text | item 46, s158, ACCEPTED 2026-10-08 |
| H2: whole-word matching, no `ER` in `water` | item 47, s159, ACCEPTED 2026-10-08 |
| H5: balances only, HSA and FSA kept apart, unknown terms stay unknown | item 86, s226, ACCEPTED 2026-10-15 |
| H5: a fact-versus-conclusion line for each figure | item 86: every figure carries its working; "can't tell" without terms; contributions "on record", never "remaining" |
| H6: inventory reconciled against the code, AI log a test case, derived text scrubbed | item 45 stage 1, s208 (47 sinks, scanned against the code), ACCEPTED 2026-10-12 |
| H4: medication evidence-to-claim rules before any medication figure | still open, as ruled 2026-10-09; nothing built |
| H7: each stage gated | stages 1 and 2 (items 86, 87) each ruled, built and accepted on their own; 88 awaits ruling |
| The broader principle (what is known, calculated, unknown) | the transparency standard (item 39 U7) and "report statements must be proven" (2026-09-27) |

One deliberate difference: H6 (P1, ruled) keeps a health transaction's **category and amount** in logs and the
model's context, because they are the person's own budget, and scrubs the merchant and description. The review
suggests also testing what can be inferred from a category plus amount. That would reopen an accepted ruling, so it
is named here and not proposed.

## 1. Points for ruling — one rule over every conclusion

**C1. The invariant.** *A protected expense is counted in every accurate calculation, but no conclusion shown to
the person may present reducing, delaying or giving up that care as a way to improve their money.* Accurate reporting
stays: *"This month's health spending was $412, above the $300 budgeted."* Framing as a lever is refused: *"Reducing
health spending would move your debt-free date to March."* *Recommended.*

**C2. Every surface that can suggest a change is listed, and the list is checked against the code.** It works like
H6's sink registry: a `LEVER_SURFACES` list names each function that can put a change to spending in front of the
person. Today that is:
- `core/solution.py`'s levers 1–7, the budget pressure and the large-charge lesson;
- the Willingness Layer's flexible list;
- `core/income_change.py`, `core/futures.py`, the monthly review and the Sunday check-in;
- the W1 and W2 findings, plan edits and Before You Buy;
- the dashboard brake;
- the narrator's findings.

A scan fails the gate when a new function calls the lever machinery (`offsetting_monthly_delta`, the flexible
list, the lever set) without being listed. *Recommended.*

**C3. One sweep test over all of them.** A record is seeded where a health category is the largest and most
variable spending. That is the case most likely to be picked as a lever. Every listed surface is called through its
real route, and the rendered text is checked:
- no health category or uncertain item is named as something to cut, trim, reduce, delay or trade;
- accurate reporting of its amount is still allowed.

A mutation (a health category sneaked into the lever set) must be caught. *Recommended.*

**C4. The narrator.** With AI off, the test checks what the narrator is *given*: no finding offers care as a lever.
The voice gate's existing check on the model's words is unchanged. *Recommended.*

## 2. Points for ruling — "uncertain" as an outcome

**U1. Three outcomes.** Every category, and every uncategorised row, gets one of three outcomes:
- *protected*: on the floor (version 3), or an HSA or FSA row (item 86 F6);
- *uncertain*: a health signal exists but isn't conclusive;
- *not matched*.

*Recommended.*

**U2. Where "uncertain" comes from: `core/classification.py`'s counterparty axis, as written.** Its merchant terms
are narrow on purpose (`healthcare`, never bare `health`, so OhioHealth and a health club aren't swept in).
`inside_boundary` is entered by a signal *existing*, not by its strength. A category name that partly matches a
health term without meeting the floor's whole-word rule (for example "Vision", "Pharmacy & Household") is uncertain
too. No AI classifier and no new list: this connects what was built and tested. *Recommended.*

**U3. Uncertain is never a lever and never priced in months.** It is treated exactly like protected on every C2
surface. Accurate reporting still applies. *Recommended.*

**U4. Your answer settles it.** Groundwork may ask, once, beside the category: *"Is 'Vision' health care?"* The
answer is recorded as yours, with its date:
- *Yes* makes it protected;
- *No* makes it not matched.

Groundwork never decides by itself and never learns silently (the no-silent-learning boundary). Leaving the question
unanswered keeps it uncertain, which means protected from cuts. *Recommended.*

**U5. An uncertain reading is itself health information, so it is never stored.** It is worked out when a surface
needs it, and never written to the database, a log, an export or the model's context. That is the concern
`classification.py`'s own notes raise: a guessed health signal on an ordinary row can be the most sensitive thing
the system holds. Only your U4 answer is stored, under H6 like any health category. *Recommended.*

## 3. Left out, on purpose

- **Testing what a category plus an amount reveals in logs:** it reopens H6 P1 (see section 0). Name it as its own
  item if you want it reopened.
- **Medication claims (H4):** still open.
- **The tax axis of `classification.py` (`qualifying_amount`):** that belongs with the year in review (stage 4).
- **The 1.x line:** master only. 1.x has the floor but not these surfaces.

## 4. How it would be built and proven, once authorised

1. `LEVER_SURFACES` and its scan.
2. The sweep section.
3. Connecting `classification.py` behind `is_protected`'s callers, so `is_protected` becomes one consumer of
   classification, as that module's notes already plan.
4. The U4 question and its stored answer. That is a small table, so a `SCHEMA_VERSION` bump and pin.

The gate must also show that a user with no health signals sees exactly what they see today: the module's own rule
that "§6.1 behaves exactly as it does today".

It does not depend on item 88, and either can be built first.

## Closing

Most of the review was already answered by what has been built since it was written. What it found that is real is
reach, not rules: the rules exist, but the proof covers the surfaces of 2026-10-08, and an unclear name falls the
wrong way. C2 and C3 make the proof cover every surface and keep it current as surfaces are added. U1 to U5 make an
unclear name fall the safe way, using a module that was written for exactly this and never connected.


## Built 2026-10-16 (s228; SCHEMA 20261016-care-answers)

- **C1 / U3:** `core/care_status.py` `never_lever` (protected or uncertain) replaces the floor-only test at every
  lever decision:
  - `solution.py`'s `_flexible_named`, `_headroom`, `_trims` and `_overspend`. An uncertain overspend is described
    and never priced.
  - `willingness.py`'s readings and `income_change.py`'s `budget_follows`.
  - `server.py`'s `not_levers`, the one list the page reads.
  - The large-charge lesson, where an uncategorised row now uses `classification.py`'s row-level test.

  `is_protected` remains only where it labels the floor.
- **C2:** `LEVER_SURFACES` (21 functions, each with how C1 holds there) is reconciled by an AST scan in s228. A
  function that calls the lever machinery without being listed fails the gate, and so does a listed one that no
  longer calls it.
- **C3:** s228 seeds an uncertain category as the biggest, most flexible overspend. It checks the engine helpers and
  the real routes: not-levers, Budget pressure, the Ledger lesson, Before You Buy offers, the dashboard brake and the
  debt teaching. A mutation that lets the category back into the lever set is caught.
- **C4:** the narrator's findings (`/api/debt/teaching`) carry no months for it.
- **U1 / U2:** three outcomes. Category-level signals are `classification.py`'s strong counterparty signals
  (health merchant terms, health card codes) and its health category terms on a name the floor doesn't take.
  - **Measured on Rob's record** (104 categories, 1,492 payments): a supermarket with a pharmacy counter would have
    made Shopping uncertain from 41 rows, so that weak signal works on single rows only, as the module describes it.
    The strong signals flag three categories, all false positives each settled by one "No": Goodwill under card code
    8043 in Charitable Donations, and a recycler under 8011 in Home Maintenance and HomeServices.
  - **Found in the app:** a clinic payment auto-filed under **Other** asked "Is Other health care?". Catch-all
    categories are now judged row by row only, like uncategorised payments.
- **U4:** "Is this health care?" sits at the top of Settings → Categories, with the reason and Yes / No buttons.
  Until the person answers, the category is never offered as a cut. Answers are kept, newest current, and listed
  under "Your answers about health care" with a Change button. (The first draft said answers could be changed
  without a way to change them; found in the app, fixed.) An answer never takes a category off the floor.
- **U5:** `care_answers` holds only category, answer and date. The uncertain reading and its reason are worked out
  on read, held in memory and never logged. s228 also proves that with no health signals `never_lever` equals the
  floor exactly, as before item 89.
- **Pins:** s158's charge-guard pin follows the new line.
