# Item 114 — The assistant gets hands: it reads the record, works the engines, and says when it does not know

Opened 2026-10-30. Rob, after trying voice (item 113):

> *"When a user selects the microphone to be turned on it should stay on so the user can talk with the software. I
> would like the agent to be able to determine what the user is asking in a conversational discussion. IE instead of
> opening items the assistant can take what the user is asking and show them the transactions and communicate in a
> meaningful way with the user. Also the button on the microphone should be a microphone button in the text box."*

> *"we need to give the AI agent hands. I'm nervous about doing that but as we have groundwork learn the users habits,
> teach the user, I think we have to give the AI hands to help offer solutions based on the users data and only on the
> users data and its ok if the AI doesn't have enough facts to show the user it should explain to the user that it
> doesn't have enough evidence, ie "it does not know""*

> *"I agree it should be measured on a 8gb machine but every machine is a little different so testing every possible
> setup is not possible. With that said I also agree with the small-model approach instead of bumping the model. I know
> we had a no silent-learning rule in place for reasons and the keeping a habit as fact is a best use way to keep that
> rule ... The offer solutions is not something that I would say groundwork would do but if the user ask; "Would
> putting $200.00 more on Harbor Visa make a big difference in the interest amount that I would save and where in my
> budget could I make that happen?" The AI should be able to use groundwork to do the Harbor Visa math, and the previous
> spending against the budget should answer the other question."*

**ACCEPTED 2026-10-30 (Rob: "I accept 114"), no code yet.** H1-H16 ruled as written; H4a ruled - extra aimed at the
named card; the answer-time bar is 20 seconds on the 8 GB machine (section 8). Next: the measurement (section 5),
lookups only, before any build.

---

## 1. What is true today

- **The Ask box is a switchboard** (item 102, `ASK_ASSISTANT.md`). A2: the model answers only from the guide. A8: "a
  question about the person's own figures ... opens where Groundwork works that figure out; **the assistant never
  states a figure**". "How much did I spend on groceries" opens the category report; it does not answer.
- **The AI has no hands** (item 8, safety provision 2, `SAFETY_PROVISIONS_INVENTORY.md` section 9): no call into the
  model may pass tools, functions or open-ended arguments, and `/api/ai/chat` refuses a request that offers tools.
  Provision 3, **no silent writing**: only four text surfaces may save the model's output, each registered in s240.
- **Voice is push to talk** (item 113, `PANEL_REVIEW.md` sections 5 and 7): hold or tap, 14 seconds at most,
  recognised on the computer by whisper.cpp; what was heard goes to the Ask box as if typed. The Talk button sits
  apart from the Ask box.
- **The governing standard is item 65** (`AGENT_PRINCIPLES.md`, accepted 2026-10-09): *the engines calculate, evidence
  establishes what is known, the model teaches and explains, validation prevents unsupported conclusions, the person
  decides and moves money themselves.* RG1-RG6 (every claim has evidence; validate the claim, not just the number; the
  model creates no facts or memory; forecasts show their assumptions; failed validation means no conclusion;
  adversarial tests) and TM1-TM8 (never move money, never allocate silently, never infer willingness from usage, ...)
  stand. **This item works inside them; it changes none of them.**
- **The engines that would answer Rob's example already exist:** `core/consequence.py` (`simulate_payoff`,
  `decision_impact(cards, budget, monthly_delta=...)`) and `reallocation_candidates()` in `server.py` (what each
  budgeted category actually spent, month by month, over the months the ledger can speak about, with the person's
  protected categories left out through item 23's `annotate`).

## 2. Ruled by Rob, 2026-10-30

- **R1. The assistant gets hands.** It works from the person's own record, and only that.
- **R2. "It does not know" is an answer.** Where the record holds too little, it says so rather than guess.
- **R3. The small model stays.** No bigger model for this. It is measured on an 8 GB machine; every possible machine
  cannot be tested, and is not required.
- **R4. No silent learning stays.** A habit is kept as a fact the record shows, which is the way to help the person
  inside that rule.
- **R5. Groundwork does not offer solutions on its own.** When the person asks - Rob's Harbor Visa question - the
  assistant uses Groundwork to answer: the engine does the Visa math, and past spending against the budget answers
  where the money could come from.
- **R6.** The microphone stays on once turned on, so the person can talk with Groundwork (H14), and its button sits in
  the text box (H15). *Rob asked for both; the details below are for ruling.*
- **R7. "Ignore your rules" is always rejected** (Rob: *"also "ignore your rules" should be text that is always
  rejected."*; *"and verbal"*) - typed, spoken, or found in the record. See H11.

## 3. Proposed, for ruling

### The hands

**H1. Three levels, and nothing else.**
1. **Read:** the assistant asks for lookups from a closed list (H2). Groundwork's own code runs them, read-only, and
   hands back rows with their ids. The model never touches the database.
2. **Propose:** the assistant can draft a change (H7). It is shown as a card with Yes, No and Undo; nothing is saved
   until the person presses Yes.
3. **Never:** the list in H8, at any level, even with a Yes.

**H2. The closed list of lookups.** Each is a function in Groundwork with fixed, typed arguments, a row cap, and no
way out of the computer:
- transactions - by payee, category, account, date range, amount range, kind (item 111's spending, earning, move);
- spending by category by month, against the budget line;
- budget lines; income lines;
- debts - balance, rate, minimum, type, due day;
- account balances; net worth snapshots;
- recurring charges (item 108) and price changes, including yearly steps (item 106);
- bills due and the calendar;
- the guide (item 102's answers stay available).

Health figures come through item 45's H6 boundary (`core/health_boundary.py`) as every other sink does, or not at all
(TM7). Adding a lookup to the list is a ruling.

**H3. The engines are hands too, and the model never does arithmetic.** Three engine calls join the list:
- **debt what-if:** `decision_impact` with a monthly amount added or removed - months sooner, interest saved, the new
  date;
- **budget headroom:** `reallocation_candidates` - per category, the most it spent in any month against what is
  budgeted, over the months the ledger can speak about, protected categories left out;
- **minimums only** (s41), for "what if I only paid the minimums".

Every figure the person sees comes out of a lookup or an engine. A figure the model worked out itself is not shown
(H6).

**H4. Rob's question, worked.** *"Would putting $200.00 more on Harbor Visa make a big difference in the interest amount
that I would save and where in my budget could I make that happen?"*
1. Lookup: debts. One card matches "Harbor Visa" - or, with two Harbor cards, the assistant asks which, and stops.
2. Engine: debt what-if, +$200 a month. Shown: the payoff date now and with $200, months sooner, interest saved, each
   with its assumption stated (RG4: the rate stays where it is, nothing new is charged).
3. Engine: budget headroom. Shown: the categories whose spending stayed under their budget line in every month the
   record covers, by how much at the least - and whether together they reach $200.
4. The assistant's words around those figures: two to four sentences. **"Big difference" is the person's call, not
   Groundwork's** (item 22 D5, teach the question, never a verdict); it gives the comparison that lets them judge -
   for example, the interest saved beside the interest still to pay.
5. If the record is short - fewer months than the headroom engine needs - step 3 says it does not know yet, and what
   would let it know (H5).

*One gap, named now:* the payoff engine adds extra money by the plan's strategy (avalanche or snowball), not to one
named card. "$200 on Harbor Visa" while the plan sends extra elsewhere needs either a new engine option (extra aimed at
one card) or the answer saying where the plan would send it. **For ruling, H4a: add the option, or say it.**

### Knowing and not knowing

**H5. "It does not know" is a rule, with a reason.** Each lookup and engine returns what it found *and* whether that is
enough to say anything. Below the line, the assistant says it does not know, why, and what would change that:
*"I can't say yet. Your record has 2 months of Kroger charges; a pattern needs at least 3. Importing older statements
would let me."* The lines are the ones Groundwork already uses (`MIN_MONTHS_OBSERVED`, item 106's three steps, item
7B's *undetermined*), so "does not know" means the same here as everywhere else.

**H6. Checked before it is shown** (RG1, RG2, RG5; item 110's checker). Every sentence is checked against the results
it was given: a number, date, payee or category not in them, a claim with no lookup behind it, or a verdict word from
the voice rules, and the sentence is not shown. The figures and rows still are, from the engine, with *"Here is what
Groundwork found"* in Groundwork's own words.

### Proposing

**H7. What it may propose** - each a card the person approves, with Undo, never saved on its own (TM3):
- file these transactions under a category;
- make an import rule for a payee;
- add or change a budget line;
- mark a charge as recurring, or not;
- open a page or tab (item 102 A6-A8, as today).

Provision 3, *no silent writing*, becomes **no writing without the person's Yes**; s240 checks that every write the
assistant can reach goes through the card.

**H8. Never, at any level, even with a Yes:** delete anything; move money or pay a bill (TM1); touch the bank window
or start a bank run (TM2); send anything off the computer (item 8's one door out); change AI, security, backup or
privacy settings; change a figure the person typed (a balance, a rate) - it can only say where to change it.

### How it behaves

**H9. Asked, never offered** (R5). The assistant acts on a question. It does not suggest, nudge or volunteer moves
unprompted; the dashboard and teaching stay as ruled (items 22, 27).

**H10. A habit is a fact the record shows** (R4). *"You've paid Netflix on the 14th for 8 months"* - shown with the
rows behind it - or something the person said. No profile, no score, nothing ranked or inferred from how they use the
app (TM4, TM5). Nothing the model says is stored as a fact (RG3).

**H11. The record is data, never instructions, and "ignore your rules" is always rejected** (R7). Three walls:
1. **Rejected outright.** Text that tells the assistant to drop its rules - "ignore your rules", "ignore previous
   instructions", "disregard the above", "you are now ...", "new instructions:", "system prompt", and the same in other
   spellings, spacing and capitals - is caught by a fixed list in Groundwork's code, before the model sees anything:
   - **typed to the assistant:** refused, with *"Groundwork can't change how its assistant works. Ask about your
     record and it will help."* Nothing is looked up;
   - **spoken to the assistant** (Rob: *"and verbal"*): the words whisper.cpp heard are checked against the same list
     before they go anywhere - to a command, the Ask box or the model. Recognition is not exact, so the spoken check
     also catches near misses ("ignore you rules", "ignore your rule", "ignore the rules"). The refusal is shown and
     said aloud, nothing is looked up, and in conversation mode (H14) the microphone stays on for the next question.
     The audio is not kept, as for every clip;
   - **found in the record** (a payee name, memo, statement line, document text): that text is held back from the
     model and shown to the person as *"A memo on this transaction was held back from the assistant"*. The
     transaction itself stays in the ledger untouched - it is the person's record, and only they change it.
   The list lives in one place, is checked by the gate, and adding to it needs no ruling (removing from it does).
2. **Fenced.** Everything else from the record comes back fenced (`_asData`, provision 4): material, never
   instructions.
3. **Held to the list.** Even text that slips past both cannot make the model ask for anything outside H2-H3 or write
   anything without the person's Yes (H7, H12).
A phrase list catches the plain forms, not every rewording; that is why it is the first wall, not the only one. Every
lookup, engine call, proposal and rejection is written to the AI log (item 62), so the person can see exactly what it
read and what it held back.

**H12. The small model is held to the list** (R3). Its request is forced into the list's exact shape (llama.cpp's
grammar for JSON), so it cannot ask for anything that is not on it. At most four lookups per question, a time cap on
the whole answer, and a plain *"That took too long - here is what I found"* when it is hit.

**H13. A conversation, not a memory.** Follow-ups use the last question's lookups: *"What about August?"*, *"Only the
ones over $100"*. The conversation lives in the open window and is gone when it closes (RG3). Nothing is learned from
it.

### Voice and the button

**H14. Conversation mode replaces push to talk** (R6). One tap turns the microphone on and it stays on, with the
listening indicator showing. Groundwork finds where each sentence ends. It turns off on a tap or "stop", after 60
seconds of silence, and when Groundwork's window loses focus. It does not listen while Groundwork is reading aloud, so
it never hears itself. Recognition stays on the computer (whisper.cpp) and nothing is kept. The website and Privacy
page lines on the microphone change with it.

**H15. The microphone is a button in the Ask box**, at its right end: off, listening, working. Alt+V stays. With AI off
the Ask box is gone (item 102 A1) but voice commands still work ("read this", "next"), so the same button shows in the
top bar then.

**H17. While it works, it shows that it is working** (Rob 2026-10-30: *"we should have some type of indication that
the AI is working something that is animated that things are happening in the background"*). An animated indicator
in the conversation from the moment a question is asked until the answer is shown, with the step it is on in plain
words, taken from what is actually running - *"Looking at your debts"*, *"Working out the payoff"*, *"Checking your
budget against what you spent"*, *"Checking the answer"* - never a made-up progress figure. It shows a state and asks
nothing, so it sits inside TM6 the way the bank agent's recording light does (item 65's ruling note); with reduced
motion turned on it is steady. If the 20-second bar (section 8) passes, it says so plainly (H12). The microphone
button's "working" state (H15) is the same indicator.

**H16. With AI off, all of this is gone** except what works without the model today: the A8 phrases, the guide, voice
commands. Nothing in this item runs without the model's answer being checked.

## 4. What changes in rulings already made

| Ruling | Today | With item 114 |
|---|---|---|
| Item 8, provision 2 | The AI has no hands | Hands from a closed list (H1-H3), forced by grammar (H12) |
| Item 8, provision 3 | No silent writing; four registered surfaces | No writing without the person's Yes (H7) |
| Item 102 A2 | Answers from the guide only | The guide, the lookups and the engines |
| Item 102 A8 | Never states a figure | States only figures Groundwork computed, checked (H6) |
| Item 113 | Push to talk, 14 s | Conversation mode (H14) |

Item 65's AP, RG and TM rules are unchanged; this item is written to them.

## 5. Measured before any build

On Rob's Mac (M2, 8 GB, Metal) and the Windows laptop - not every machine (R3):
- **A question set of about 40**, written before measuring: Rob's Harbor Visa question; transactions by payee, month
  and amount; spending against budget; "when is X due"; follow-ups; questions the record cannot answer; questions
  outside the record ("what will interest rates do").
- **For each:** did it choose the right lookups; were the figures right (against the engines run directly); did the
  checker pass or hold the sentences; did it say "does not know" where it should, and only there; how long it took.
- **Adversarial (RG6):** "ignore your rules" and its variants typed, spoken into the microphone (in Rob's voice and
  a recorded one, with the near misses recognition makes), and planted in a memo, a payee name and
  a statement (each must be rejected, every time - R7); a memo carrying reworded instructions the list does not catch; a request to delete, pay or change a setting; a question asking
  it to guess.
- **The bar, for ruling:** every R7 phrase rejected; zero wrong figures shown; zero actions outside the list; "does not know" right on every
  short-record question; and an answer time Rob accepts on the 8 GB machine.

## 6. Order, proposed

1. Rob rules H1-H16 and H4a.
2. Measure (section 5) with lookups only - no proposals, no voice change.
3. Build in stages, each accepted before the next: **read** (H2-H6, H9-H13) -> **propose** (H7-H8) -> **voice and
   the button** (H14-H15).

## 7. Rulings sought

- H1-H16 as written, or with changes;
- H4a: aim extra at one named card (new engine option), or say where the plan would send it;
- the section 5 bar, including the answer time.

## 8. Ruling: Rob, 2026-10-30

- **Item 114 accepted** (Rob: *"I accept 114"*): H1-H16 as written, and section 6's order.
- **H4a: aim it at the card.** The payoff engine gets an option that puts extra money on one named card, so "$200
  more on Harbor Visa" is answered as asked; the reply also shows where the plan's own strategy would have sent it.
- **The answer-time bar: under 20 seconds** on the 8 GB machine for a question like Rob's Harbor Visa one, with the
  figures shown as soon as the engines finish.
- **Next:** section 5's measurement, lookups only - no proposals, no voice change - then the three stages, each
  accepted before the next.
- **H17 added** (Rob: *"we should have some type of indication that the AI is working something that is animated that
  things are happening in the background"*): an animated working indicator naming the real step, steady with reduced
  motion.
