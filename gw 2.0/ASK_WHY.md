# Item 72 — Ask why: talk with the agent when something doesn't look right

Opened 2026-10-10. Rob, right after the item 71 card fired on his own data and the cause turned out to be his pay
filed under a new category:

> *"This .. what just happened is the final missing piece. When something doesn't hatch up the user should have an
> ability to talk with the agent and see why something doesn't look right or why is this reading this way and to see
> the user mis categorize something or if the user works from a company that it also may have to purchase or pay a
> bill to the user can talk with the agent to fix. Also if the user had questions on how to do things in groundwork
> it explains where and could even open that section for them."*

**C1–C10 as revised in §5: go-ahead given 2026-10-10 (Rob: "build"). STAGE 1 ACCEPTED 2026-10-10 (Rob: "i accept item 72 stage 1, build stage 2"). STAGE 2 BUILT 2026-10-10 (§8), awaiting acceptance. Stages 3–4 wait (C9).**

## 1. What happened, and why it's the model for this

The income card said Rob's income had dropped. Finding the real cause took four questions, each answered from the
ledger, not from a guess:

1. **What went into the figure?** Monthly income, from deposits filed under "Income".
2. **Which payers make it up?** City of Millbrook (every two weeks) and Harmon Packaging (weekly).
3. **Did one stop?** City of Millbrook's last "Income" deposit was June 25.
4. **Is it really gone?** No. The same deposits continue from July 9, filed under "Rob's Income", an expense-type
   category created June 26.

Then came the fix (re-file, or count that category as income), shown to Rob before anything changed. That sequence,
**the figure's inputs, then fixed checks on the record, then a proposed fix the person approves**, is what a user
needs when something doesn't add up.

## 2. What is true today (measured 2026-10-10, master 11dd614)

- **Every figure is meant to show its working** (the transparency standard, item 39 U7), but there's no way to ask
  "why does this read this way?" and have Groundwork check the record behind it.
- **There is no conversation with the agent.** The narrator explains engine findings on fixed surfaces (reports, the
  trip advisor), and *Ask for a tile* (item 28) matches words to a closed catalogue. Neither investigates or fixes.
- **Mis-filed money is invisible.** Nothing notices one payer's deposits moving between categories, credits in an
  expense-type category (or debits in an income one), or a regular deposit that stopped.
- **Work expenses paid back** have no place. A purchase the employer reimburses counts as spending, and the
  reimbursement counts as income.
- **No in-app help.** Nothing explains where a feature is or how to use it, and nothing opens a page for the person.
- **The rules this must keep:**
  - AP6: the engines compute; the model explains.
  - AP9: when Groundwork can't tell, it says so.
  - AP3 / TM4: never read the person from how they use the app.
  - AP4 / TM5: facts about other people and life events are asked, never inferred.
  - TM3: never allocate silently.
  - RG1–RG3: every claim has evidence, and the model creates no facts.
  - *Capable is not admissible*: an answer outside its contract is refused, not salvaged.
  - A10: every surface works with AI off.

## 3. Points for ruling

**C1. Where you ask.**
- A **"Why?"** on any figure, which opens the conversation already pointed at that figure.
- An **"Ask"** box in the header for anything else.

Both open one panel beside the page, and the page stays as it is underneath. *Recommended.*

**C2. The model routes; the engines answer.**
- The model only picks which check fits the question, from a closed list, through constrained output. An answer
  outside the list is refused whole.
- The check runs on the record and returns facts with the rows behind them. The model may then put the result into
  words, through the voice check (R1–R11, numbers only from the findings).
- **With AI off**, the "Why?" on a figure lists the checks that apply, and the person picks one.

So the person always gets the evidence, never a cause the model made up. *Recommended.*

**C3. The first checks, taken from today:**
- **What went into this figure:** its inputs, rows and formula. This is the transparency standard's working, made
  askable.
- **One payer, two categories:** the same payer's deposits or charges filed under different categories over time,
  with the date it changed. This is today's case.
- **Money in the wrong kind of category:** deposits in an expense-type category, or charges in an income one.
- **A regular deposit or bill that stopped:** its usual day passed with nothing on record. The check says "not on
  record yet", never zero, and asks whether it's filed elsewhere or really stopped.
- **Your own transfers counted as income or spending:** a matching amount leaving one of your accounts and arriving
  in another.
- **The same transaction imported twice.**
- **Months with no data:** a gap that a total is reading as zero.

Each check says what it found, shows the rows, and says what it can't tell (AP9). A check with a threshold passes
the shuffle test on real-shaped data before it ships. *Recommended.*

**C4. Fixes: proposed, then yours.**
- A check that finds something offers a fix as an exact list, such as *"move these 7 deposits ($16,748.80) from
  Rob's Income to Income"*, or *"make Rob's Income an income category under Income"*.
- **Apply** changes exactly those rows. **Undo** puts them back.
- Each fix is recorded in the Historian with what changed (AP10).
- The model can't apply anything, and nothing changes without the tap (TM3, RG3). *Recommended.*

**C5. Work expenses paid back, and payments to an employer: told, never guessed.**
- The person says it: *"I buy things for work and get paid back"* (AP4, TM5). Groundwork never infers it from
  purchases.
- After that, a purchase can be marked *"my employer pays this back"*. When the reimbursement arrives, the person
  matches it (like item 50's bookings), and neither one counts as spending or income.
- The same works the other way, for something the person pays their employer for.
- This needs a new record, so it's its own build stage with a schema bump.

*Recommended.*

**C6. How-to help: from a catalogue, with "Open it for me".**
- A shipped catalogue describes each feature: what it does, where it is, and the steps.
- A question is matched to an entry, the same closed matching as item 28 (by keywords with AI off, by the model with
  AI on). The answer is the entry as written.
- **"Open it for me"** goes to that page and section on the tap.
- A question with no entry gets an honest *"Groundwork doesn't have an answer for that yet"*.

*Recommended.*

**C7. Nothing learned from the conversation.**
- Questions aren't used to infer anything about the person (AP3, no silent learning).
- When AI is used, the exchange is in the AI log (item 62), as every AI call is.
- A fix that was applied is in the Historian.
- Questions nothing could answer are kept in a list the person can see and clear, as their words only, read by
  nothing else (the item 28 K4 pattern).

*Recommended.*

**C8. What it won't do.**
- It gives no advice and no verdicts. It answers what the record shows, and how to use Groundwork.
- It doesn't move money (TM1) and doesn't change anything without the tap.
- It doesn't answer from general knowledge or research (TM8, R11).

*Recommended.*

**C9. Built in stages, master only:**
1. The checks of C3, "Why?" on figures with the AI-off menu, and C4's fixes.
2. C6's help catalogue and "Open it for me".
3. The model's routing (C2) through constrained output, and the "Ask" box.
4. C5's work reimbursements.

Each stage gets its own gate and acceptance. *Recommended.*

**C10. Tests:**
- Each check finds its planted case and stays quiet on clean data. Today's "Rob's Income" pattern is one fixture.
- A check with a threshold passes the shuffle test.
- A fix changes exactly its listed rows, and Undo restores them.
- A routing answer outside the closed list is refused.
- Every check is reachable with AI off.
- The voice check runs on every model sentence.
- No answer contains a figure that isn't in its check's findings.

*Recommended.*

## 4. Not decided here

- **Which figures get "Why?" first.** The proposal is the dashboard tiles, budget totals, the income card and the
  debt plan; the rest follow.
- **Talking to the agent by voice.** Not proposed.
- **The agent fixing things on a bank's or employer's website** (item 57's window). Not proposed here. C4's fixes are
  inside Groundwork only.


## 5. Revised recommendations after review (2026-10-10)

Rob passed in a review of C1–C10 and asked for push-back where it is valid. Most of the review is adopted. Three
points are adopted only in part, with the reason given. **These replace the recommendations in §3 for ruling.**

**C1 (revised).**
- Stage 1 puts **"Why?" only on figures and findings** whose calculation or records Groundwork can check.
- The **Ask box** arrives in stage 2, for how-to questions only. Those match a written guide, the same low-risk
  matching as item 28.
- Money questions in the Ask box wait for stage 3, once the AI's check-picking has passed its gate.
- *Partly adopted:* the review deferred the whole box. That holds back how-to help, which carries no AI judgment.

**C2 (revised).**
- The AI picks only from the registered checks, with validated inputs.
- It never writes a query, invents a check, or changes data.
- When its pick is ambiguous or invalid, Groundwork asks the person to choose.
- With AI off, the same checks are available through the ordinary interface.

**C3 (revised): evidence before explanation.**
- Each check is defined in writing before it is built:
  - what it can establish;
  - what it cannot;
  - its comparison period;
  - what happens when data is missing.
- A check reports what the ledger shows ("these 7 deposits are filed under an expense-type category"). It never
  reports a cause ("you mis-filed them").
- Added to the checks:
  - the figure's time period, the records it includes and the records it leaves out;
  - duplicates, kept as *suspected* until the person confirms them;
  - incomplete imports and stale accounts;
  - changed (not only stopped) deposits and bills.
- When the evidence conflicts, or no check explains the figure, Groundwork says so plainly.

**C4 (revised): preview, approve, verify.**
- The preview shows:
  - each record;
  - its current and proposed category;
  - the total;
  - the figure that was asked about, before and after;
  - the named totals it feeds that Groundwork can recompute.
- It says plainly that **other figures may change too**. *Partly adopted:* the review asked for "any known
  downstream effects". A list that looks complete but isn't would mislead.
- **Added (not in the review):** when the import's own category rule would file the next deposit the same way, the
  preview offers to change that rule too, as a separate tick box. Otherwise the problem comes back on the next
  import.
- Approval covers exactly the change shown. If the records have changed since the preview, the preview refreshes
  instead of applying.
- After applying, Groundwork confirms the records really changed and records the result in the Historian.
- **Undo** reverts only the rows still as the fix left them. Rows edited since are listed and left alone.

**C5 (revised): deferred to stage 4, unchanged in spirit.**
- The person tells Groundwork about it; it is never inferred.
- A reimbursement is matched only on evidence.
- Partial repayments and unmatched cases are handled.
- Nothing is double-counted.
- Not every employer deposit is a reimbursement, and not every work purchase is repaid.

**C6 (adopted).**
- The guide covers features that exist, and "Open it for me" only navigates.
- A guide entry whose page or section doesn't exist fails the gate.
- With no entry, Groundwork says it has no answer, rather than inventing steps.

**C7 (adopted, made exact).**
- What is said in the conversation answers the question in front of it. It never becomes a stored fact,
  preference, willingness statement or Historian entry about the person.
- The financial record changes only through a fix the person approved, which is recorded in the Historian as a
  change to the record, not a trait of the person.
- The AI log (item 62) records AI calls as calls, not as facts about the person.

**C8 (revised): explain the options, never choose.**
- This is the existing rule, *teach the question*. Groundwork explains the ways a finding can be fixed, what each
  one changes, and what stays uncertain, conditionally and without picking one.
- *Partly adopted:* the options come from the check's own fixed list of fixes, never from the AI. The AI
  explaining why an option "could help" would be an invented cause again.
- No decisions for the person, no "you must", no pressure. A fix is always a separate approved action.

**C9 (adopted).**
- Four stages, each with its own gate and Rob's acceptance. A stage starts only after the one before is accepted,
  not merely built.
- Stage 1 must:
  - work with AI off;
  - show its checks are correct;
  - handle incomplete data safely;
  - make every fix reversible;
  - hold back any finding that fails.
- Stage 3 must also meet RG1–RG6.

**C10 (adopted, with failure cases). The tests must show both that real problems are found and that unsupported
explanations are refused:**
- a known mis-filing (today's "Rob's Income" case), and correct filing that must stay quiet;
- one employer in two legitimate categories;
- real repeated payments that look like duplicates;
- missing months, partial imports and stale accounts;
- transfers, refunds and reversals;
- ambiguous questions, unsupported causes, and questions no check fits;
- the AI picking a check that doesn't exist;
- **instructions planted in an imported transaction description**: bank text is data, never instructions;
- a stale preview, a failed write, and an Undo that meets later edits;
- AI off, AI unavailable, and an AI answer that fails validation.


## 6. Stage 1, built (2026-10-10)

- **The checks** (`core/ask_why.py`). Each has its *what it shows* and *what it can't tell* in writing, shown with every
  finding:
  - **what went into your monthly income:** the period (complete months), what is counted, and what is left out, per
    month;
  - **one payer, filed under two categories:** a clean switch from one category to another at a date, deposits and
    charges never mixed. A payer filed two ways back and forth stays quiet;
  - **deposits in a spending category, or charges in an income category:** a spending category is shown only when most
    of its money is deposits, so refunds stay quiet;
  - **a regular deposit that has not come in:** weekly, every two weeks or monthly. When the account's records end
    before the next payday, it says the deposit may simply not be on record yet; otherwise it asks whether the deposit
    is filed elsewhere or stopped;
  - **the same transaction on record twice:** always *suspected*, with no fix that deletes;
  - **money between your own accounts counted as income;**
  - **months with no records, and accounts whose records stop.**

  When nothing explains the figure, the panel says so. Findings state what the record shows, never a cause (s189
  holds a list of cause and verdict words they may not use).
- **Where:** *Why does it say this?* on the income card (the income figure, deposits only), and *Check my records* on
  the Assistant page (all checks). The panel opens beside the page. **Not yet:** "Why?" on other figures; they follow
  once stage 1 is accepted.
- **Fixes (C4).**
  - Each finding offers its ways to change it as choices.
  - The preview shows each row with its current and proposed category, the total, your monthly income before and
    after for the months touched, what it feeds, and that other figures may change.
  - A tick box adds an import rule **for deposits only (or charges only)**, placed first, so the next import files
    the same way without catching the same name's other direction. Import rules gained a `direction`, which the
    import screen honours and the rules list shows.
  - Apply refuses a preview the records have moved on from (409, with a fresh preview). It reads back what the
    database holds, records `record_fix` in the Historian with each row's from and to, and changes nothing if the
    write didn't take.
  - Undo reverts only the rows still as the fix left them, lists any edited since, removes the rule it added, and
    runs once.
- **No model** in this stage: AI off changes nothing. Bank text is shown escaped, as data.
- **Not built in stage 1:**
  - *changed* (not stopped) pay, which waits for item 71's amendment D3–D6;
  - retyping a category, since the income figure counts only "Income" until item 71's D1 is ruled;
  - stages 2–4.
- **On Rob's data** (a copy, 2026-10-10), the income figure shows:
  - City of Millbrook's 7 deposits since 2026-07-09 in "Rob's Income" ($16,748.80);
  - the same category holding the City of Millbrook utility charges;
  - stale card accounts.

  *Check my records* also finds Auto Finance A's charges moving from Debt to Car Lease Payment, and Menards' from Transfer
  to Rent / Mortgage.
- **Tests:** s189, 25 checks, covering the found cases and the quiet ones (C10).

## 7. Amendment C11: a question outside Groundwork gets one plain answer (Rob, 2026-10-10)

Rob: *"if a user tries to ask a question that does not fall in the parameters that groundwork has inside of the
program it should default to that question is outside of Groundwork understanding. or something like that"*

**C11.** When a question matches no check and no how-to guide entry, the answer is always the same fixed sentence,
written by the engine, never by the model:

> *"That question is outside what Groundwork understands. It can check your records and show how to use Groundwork."*

- **No attempt from general knowledge.** The model never answers anything itself (TM8, R11). A partial match is not
  stretched to fit; it becomes this answer.
- **The default applies everywhere a question can be typed:** the how-to Ask box (stage 2), money questions (stage 3),
  and any later surface.
- **It is not an error.** The question is kept in the person's own list of unanswered questions (C7), visible and
  deletable, read by nothing else.
- **Tests:** an off-topic question (weather, a stock tip, medical, legal), a question phrased like a check but naming
  no figure Groundwork has, and an instruction planted in the question all get exactly this sentence.

Stage 1 takes no typed questions, so C11 is built with stage 2.


## 8. Stage 2, built (2026-10-10)

- **The guide is the existing Help & FAQ list** (`HELP_FAQ`, behind the ? button), not a second copy.
  - It now holds 54 answers: the 44 it had and 10 new ones. The new ones cover getting accounts from the bank, a
    bill's balance, import rules, finding out why a number looks wrong, undoing a fix, the Your pay card, "Make this
    my budget", turning AI on or off, the AI log, and bringing in an itinerary.
  - Each answer carries the words it matches on, where *Open it for me* goes (a page, a Settings tab, an element),
    and the on-screen labels it names.
- **Corrected as out of date:**
  - importing (it is in the Ledger, *↑ Import*, not Settings);
  - "the app does not connect to my bank" (Groundwork now visits banks itself, when asked);
  - the Trip Planner (federal travel rates, Google Hotels and the government's average airfares; no AI prices, and
    no oil-change check);
  - the monthly report (the summary works with AI off);
  - "how the AI knows my patterns" (the engines compute; the model explains);
  - PSLF (the real checkbox wording);
  - commission mode (the real Settings path).
- **C1:** the *Ask how to…* box sits in the top bar, beside ?. The answer opens in a panel. **No model:** matching
  is by keywords on this computer.
- **C2 (stage 2's share):** when two answers fit about equally, both are offered to choose from, never a guess.
- **C6:** *Open it for me* goes to the page, the Settings tab and the spot, and outlines it briefly. It presses
  nothing and writes nothing.
- **C11:**
  - A question with no clear match gets the fixed sentence: *"That question is outside what Groundwork understands.
    It can check your records and show how to use Groundwork."*
  - A question that names a wrong or missing figure also gets a *Check my records* button.
  - A partial match isn't stretched to fit, and words typed into the box are only words.
- **C7:** unanswered questions are kept as typed (up to 300 characters, the last 100) in the person's own list,
  which they can see and delete one at a time or all at once. Only the three `/api/help/unanswered` routes touch it.
- **Tests:** s193 runs the matcher in Node on:
  - 12 real how-to questions;
  - 9 that must not match: weather, a stock tip, a medical question, a legal question, "ignore previous
    instructions…", a joke, "how do I import a car", a capital city, and an empty question;
  - one ambiguous question.

  It also checks that every *Open it for me* target and every named label exists in the app.
- **Seen in the page** on a copy of the real data:
  - the import-rules answer, and *Open it for me* landing on Settings → Automation → Import rules;
  - the stock-tip question getting the fixed sentence;
  - the ambiguous AI question offering both answers.
