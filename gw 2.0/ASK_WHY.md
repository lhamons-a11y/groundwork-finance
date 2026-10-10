# Item 72 — Ask why: talk with the agent when something doesn't look right

Opened 2026-10-10. Rob, right after the item 71 card fired on his own data and the cause turned out to be his pay
filed under a new category:

> *"This .. what just happened is the final missing piece. When something doesn't hatch up the user should have an
> ability to talk with the agent and see why something doesn't look right or why is this reading this way and to see
> the user mis categorize something or if the user works from a company that it also may have to purchase or pay a
> bill to the user can talk with the agent to fix. Also if the user had questions on how to do things in groundwork
> it explains where and could even open that section for them."*

**Points C1–C10 for ruling. No code yet.**

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
