# Item 94 — The bill that lands (item 45 H7 stage 6)

**OPENED 2026-10-17 (Rob: "Open item 94 — The bill that lands"). Depends on item 93 (bank-side record creation).
For ruling; no code, no schema, no authorisation.**

## Summary

A medical bill arrives. It might be routine, or it might be more than the household can cover without emptying the
reserve. This stage is about reading it honestly. It covers:
- what the bill states versus what is actually owed now;
- which payments went toward it;
- what insurance changed;
- any payment arrangement the provider agreed;
- what happens when it's paid with a credit card;
- a separate all-obligations date that says plainly when it can't be calculated.

The rulings it stands on:
- **Q6 (2026-10-17):** Groundwork states what the evidence does and doesn't establish. It never directs.
- **Q7 (2026-10-17):** the card-free date is card balances only.
- **Design §7:** the record says what the household can sustain, never what to offer.
- **Item 93:** a bill is the provider's statement, and payments and expenses exist only by the household's word.

Because of that last one, this item can't be built before item 93's payment and expense stages exist. Collections
are stage 7. The design ends here.

## 1. What is there to build on (master `e447509`, plus item 93 as proposed)

- **Items 86 to 92:** HSA and FSA, plan figures, the reserve with its timing choice, payoff dates that follow it,
  care-never-a-lever, the visit report and Schedule A section, and named people.
- **The 2.0 records:**
  - obligations, payments and expenses, each minted by a household statement;
  - `payment_in_respect_of` and `obligation_in_respect_of`;
  - `expense_determinations` (`unpaid`, `pending_claim`, provider adjustment, paid in cash);
  - discharge kept apart from payment (a payment may evidence discharge but never establishes it by itself).

  All ruled, all empty in production.
- **Item 18:** the EOB as a document line, stage 2 done in fixtures; stage 3 (reading a held PDF's lines) not
  authorised.
- **Item 68:** bills on the Budget page (readings, due dates); never pays (TM1).
- **The payoff engine:** card-free dates; minimums untouched; the reserve schedule (item 90).

## 2. Points for ruling

**L1. The bill is the provider's statement, brought in by you.** A bill enters as a statement *from* a provider,
typed from the paper or, later, read from a held document (item 18, stage 3). It records the amount due, the dates,
the service dates and the provider's account number. The file itself is kept only on your word (item 20). A bill
creates an obligation only when you confirm *"this bill is mine to pay"* (item 93 B4). It never creates one by
arriving. *Recommended.*

**L2. "Amount owed now" is worked out and shown with its parts, never assumed to be the bill's figure.** It is:
- the provider's latest stated amount, as of that bill's date;
- less payments you've said were toward it since then (item 93 B3);
- with adjustments only as the provider or insurer stated them (a newer bill, an EOB).

When two statements disagree, both are shown with their dates. The newer one is the provider's current position;
the disagreement is named, not resolved. Under Q6: *"The bill doesn't show whether the $300 paid on Sep 2 was
applied."* *Recommended.*

**L3. Insurance changes come only from the insurer's or provider's own statement.** Groundwork never estimates what
insurance will pay. While you've marked a claim as pending (`pending_claim`), the bill is shown as *"may change: the
insurer's claim is pending (as you said)"*, and it is left out of any "can be paid in full" judgement (L6). *Recommended.*

**L4. A payment arrangement is what the provider agreed, as you report it.** You record the terms you were given:
monthly amount, first payment, number of payments. They are kept as the provider's terms, reported by you, and feed
the Budget (as a bill, item 68) and the all-obligations date (L9). Groundwork never states or implies that a
provider *will* accept an arrangement. It shows only what one that was agreed means for your plan. *Recommended.*

**L5. A bill paid by credit card is counted once.** Paying a medical bill with a card is one payment toward the
medical obligation, and it adds to the card's balance. Once the provider's statement (or your word) shows the bill
paid, the medical obligation's remaining amount drops, and the money now owed is card debt, counted once in the
card-free date (Q7). The link between the card charge and the bill is your statement (item 93 B3/B4), never
inferred from a card charge to a hospital. Until you link them, a note says: *"A $900 card charge to St. Mary's on
Oct 3 may be this bill; Groundwork counts both until you say."* *Recommended.*

**L6. The alarm is about the reserve, not the bill's size (design §7.1).** A bill raises a Needs attention item
when either:
- paying it in full would take liquid savings below the health reserve (item 88) or the stability floor (C.5); or
- it can't be paid in full from what's on record.

There is no dollar threshold. It's a new ruled attention kind (`bill_due`), with its due date and the figures
behind it, said as facts: *"Paying this $4,000 bill in full would leave $1,200 in savings, below your $2,000
reserve."* *Recommended.*

**L7. Facts about the world, only where the record establishes they apply (design §7.2, under Q6).** When you've
said the provider is a non-profit hospital (a field on the provider, never guessed), Groundwork may state the cited
federal facts:
- a published financial assistance policy is required (IRC §501(r));
- you have at least 240 days to apply;
- there are limits on collection steps for 120 days.

Beside them, *"The bill doesn't show whether financial assistance was applied."* It never says "you should apply"
or "call them", and never implies an outcome. For other provider types these facts aren't stated. *Recommended.*

**L8. What your record can sustain, never what to offer (design §7.3).** From your leanest month on record, after
the stability floor and the reserve, Groundwork shows three durations with their monthly amounts and marks which
your record sustains. With fewer months than `MIN_MONTHS_OBSERVED` it says the record is too thin to name a figure.
The words are always about your capacity (*"your record sustains $150 a month"*), never *"offer $150"*.
*Recommended.*

**L9. The all-obligations date, separate from the card-free date (the open part of Q7).**
- **What it covers:** every obligation on record: card balances, loans, and medical bills with an agreed
  arrangement.
- **What it uses:** each obligation's own schedule, through the same engine.
- **Labelled:** *"all obligations on record"*.

When any included obligation can't be dated (a bill with no arrangement, a pending claim, a disagreement), Groundwork
shows no date. It says *"The all-obligations date can't be calculated reliably: 2 obligations have no schedule"*,
names them, and still shows the card-free date (card balances only). *Recommended.*

**L10. Privacy and wording.**
- Bills, providers and arrangements are health data under H6. They are scrubbed, kept out of the model and the AI
  log, and appear in exports only on the health tick.
- Every sentence is templated, with no AI.
- Collections (stage 7) are out.
- Groundwork never contacts anyone.

*Recommended.*

## 3. Depends on, and left out

- **Item 93 must be ruled and its payment and expense stages built first** (B3, B4, B6, B8). L1, L2, L4 and L5 rest
  on them.
- **Reading a held bill or EOB:** item 18, stage 3, not authorised. Typing comes first.
- **Collections:** stage 7, last.
- **The 1.x line.**

## Closing

Design §7 called this the part that strains the platform's rules hardest. Q6, Q7 and item 93 settle most of the
strain before any code exists:
- Groundwork states the evidence and never directs;
- the card-free date is card balances only;
- a bill is the provider's word until you take it on.

What's left is arithmetic with its working shown, and a plain "can't tell" wherever the record runs out.

**RULED 2026-10-19 (Rob): "I accept item 94 as written" - L1-L10 as written.**

**BUILT 2026-10-19 (Rob: "Build item 94, the bill that lands, as ruled"); master only. SCHEMA 20261019-medical-bills; s243.**
- `core/medical_bills.py`: every sentence templated; no log, no model, no network. Three tables: `medical_providers`
  (the non-profit answer is the household's word), `medical_bill_accounts` (the obligation minted only by "mine to
  pay"; claim and arrangement kept as dated history), `medical_bill_statements` (provider bills and insurer EOBs as
  typed, kept, never edited).
- A payment toward a bill is item 93's payment plus `payment_in_respect_of_obligation`, each the answering person's
  utterance; a card charge is linked the same way, so it is one payment toward the bill (L5).
- L6 `bill_due` joins the ruled attention kinds, from 30 days before the due date.
- L8's working, as built: the leanest of the last twelve complete months (money in by the one income definition,
  money out less transfers), less the reserve's monthly fill when the person chose before/alongside.
- L9, as built: the later of the card-free date and each agreed arrangement's last payment; none when any owed
  obligation has no arrangement, a pending claim or disagreeing statements, and those are named.
- L10: providers' names and account numbers join the H6 scrubber's markers. Bills are in no export today, so none
  carries them without the health tick.
- Not built here (as ruled): reading a held bill or EOB (item 18 stage 3), collections (stage 7).
- Checked in a browser: the Settings card with a non-profit provider, and the dashboard's Needs attention item.
