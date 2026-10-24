# The simulated user panel: what it found, what is fixed, what needs a ruling (item 112)

Opened 2026-10-24 (Rob: *"here are the results from the simulated review and issues that was detected"*, then *"start
on the High ones then move through the rest of the list"*). The review: ten made-up households run through 24 months
of the real server (`groundwork-panel-sim-files.zip`: harness, personas, 90 journal entries, 25 issues).

**What the panel liked:** no one was ever shamed (all ten); interest as dollars a month; honest fund pace and "did not
hold" readings; the Health module (bills owed only when you say so); every figure saying where it came from;
privacy that can be checked.

---

## 1. Fixed (2026-10-24), held by s260

| # | What | Commit |
|---|---|---|
| I-01, I-04 | Debt payments are budgeted wherever they are spent: one rule (`_debt_month_plan` / `_debtMonthPlan`: the payoff plan, never below the minimums; the minimums with no plan) in the check-in, Before You Buy, the income futures, the Budget page; a debt payment is never offered as a purchase or priced as the month's biggest charge | 347cc79 |
| I-03, I-06 | A payoff that can't be dated is said, never a 500: below the minimums by $X (with "Use my minimums"), or never clearing (including the 30-year cap). Found on the way: the budget typed on Debt Payoff never reached the server's `monthly_budget`; it is saved as it is typed | 83b1f1b |
| I-05 | A debt the record brings to $0 is asked about ("Is it paid off?"), dated when it reached $0; $0 counts as a real balance in the Trophy Room | fd421a6 |
| I-02 | Each trophy held to its own description (10%, half, a real crossing, three rises in a row, all three of Groundwork laid) | 523a296 |
| I-07 | AI on only when chosen; an install that had it on by the old default keeps it, written once | 523a296 |
| I-08 | The schema pin reads the same on Python 3.12, 3.13 and 3.15; re-pinned without a version bump | 523a296 |
| I-16 | One "freed minimums" figure, against the minimums on record | 523a296 |
| I-17 | Payments on record short of the plan for three full months: Debt Payoff says so, with the date at that pace | 523a296 |
| I-22 | "Whose pay" asked only of a household of two | 523a296 |
| I-18 | Facts, not advice: the Budget's grades and to-do lines, the 15-20% savings target and its colour grade, "Consider checking" | f3865b3 |
| I-19, I-20, I-21 | The said-history count; no price dated after today; trophies earned together in one toast, at most three toasts | f3865b3 |

**Already fixed before the review reached us:** I-09 (parity, passing), I-10 (item 109), I-15 (item 110 V1), I-24
(`unique_path`), I-25 (3608760).

---

## 2. For ruling (no code)

**P1 (I-11). Pay with no rhythm is asked about, and read by the week.** Ray's Uber pay was "unknown" for 24 months, so
every income feature skipped him. Proposed: a payer with deposits several times a week and no schedule goes to the
same "ask" path weekly contractors get; and variable pay is read as a weekly-earnings view - a typical week, a low
week and a high week, from the last 13 weeks - never as a monthly figure it doesn't have. *Recommended.*

**P2 (I-12). No brake on spending a fund was saving for, and "I had to" describes rather than prices.** The brake
priced a $2,900 hotel as "8 months on your debt-free date" while a fund the app tracked had saved for that trip, and a
$900 brake repair at "2 months". Proposed:
- (a) a charge that matches an active fund (its name, or within 10% of its balance) is shown as "paid from your
  Honeymoon fund", never priced;
- (b) the person can mark a charge "had to" (car, home, health): described ("a $900 repair"), not priced.

*Recommended, both. (b) is the person's statement, kept like every other.*

**P3 (I-13). A fund notices what it paid for.** After the roof and the house closing were paid, the funds still said
"18 months to go". Proposed:
- When a large charge is within 10% of a fund's balance or target, Groundwork asks "Is this what you were saving
  for?". A yes spends it from the fund and closes or reduces the fund.
- A deposit over the target is shown as over, never quietly capped: today `min(target, current + amount)` drops the
  extra from the record.

*Recommended.*

**P4 (I-14). In Household mode, who changed what.** Darnell cut Restaurants and Keisha put it back; the working
picture read "restored: something you keep". Proposed:
- Each budget edit records which partner made it, when Household mode is on.
- When one partner reverses the other's edit, Groundwork asks "Is this a shared decision?" instead of concluding.
- Until it is answered, the reading is "undecided", never "sacred".

*Recommended (it fits item 92's named people).*

**P5 (I-23). Accessibility, then a real audit.** Proposed now:
- Words on every colour state ("$13.67 over", not only a red bar).
- Caption text raised to WCAG AA contrast.
- A one-line text summary under each chart.

Then a session with screen-reader users (NVDA, JAWS, VoiceOver), which Rob would need to arrange. The panel was
clear that screenshots are not a test. *Recommended.*

**P6. A simple mode and larger text.** Harold: *"A simple mode with only the pages I use."* Proposed:
- A Settings choice that shows only Dashboard, Ledger, Budget, Debt Payoff and Settings. Every page stays one click
  away under "More".
- A text-size setting (100 / 115 / 130%).

*Recommended as its own item; the page list is Rob's call.*

**P7. Outside help, and a printable summary.** Proposed:
- (a) A plain "Outside help" page: NFCC, 211, the CFPB, and legal aid by state, reached from the ? help. Item 104 has
  these numbers for the crisis words already; this makes them findable without a crisis.
- (b) "Print this session": the check-in's facts and the month's figures on one page, for a counsellor or a partner.

*Recommended, both.*

---

## 3. Ruling sought: Rob

1. **P1-P4:** build as proposed, in the order P2 (smallest), P3, P1, P4?
2. **P5:** the three page changes now, and will you arrange a screen-reader session?
3. **P6:** its own item - which pages make the simple list?
4. **P7:** (a) and (b), or one of them?

---

## 4. Ruling: Rob, 2026-10-24

**P1, P2, P3, P4, P5 and P7 accepted as written** (Rob: *"i accept p1-p5 and p7 as written"*). Build order as
proposed: P2, P3, P5's three page changes, P1, P7, P4 last. The screen-reader session (P5) is Rob's to arrange.

**P6 held** (Rob: *"I like this approach. I want to sit on this"*). Rob wants text size app-wide, not per page - *"so
we can fix css style issues in the html"*. The approach he liked, for when he picks it up:
- **Measured:** 2,339 hard-coded pixel font sizes (index.html 458, app.js 1,765, teaching 116), none relative, about
  15 sizes from 9px to 28px, about 250 at 9-10px. A text-size setting can't reach any of them today.
- **Proposed:**
  - A type scale of about six named sizes in rem, every hard-coded size replaced by the nearest one, and an 11px
    floor (which also serves P5).
  - One Text size setting (100 / 115 / 130%) that changes the root size.
  - Every page screenshotted at all three sizes, and fixed-height places (top bar, Ask pill, badges) fixed.
- **Rejected:** browser zoom - quick, but it leaves every hard-coded size and enlarges spacing with the text.
- **Undecided:** whether the "simple mode" (fewer pages) stays in P6.

## 5. P6, held: two additions (Rob, 2026-10-24)

**P6b. Read aloud.** Rob: *"The LLM or assistant can also read the area that the cursor is nearby out loud."*
- **What it reads:** after a short pause (about 0.7 s), the text or figure under the cursor - and, with the keyboard,
  the one in focus. A figure is read with its item 103 tag ("Debt payments: $450 a month, your payoff plan").
- **Whose words:** Groundwork's own fixed words, not the model's. The text on the page and the figure tags are
  already checked; a model wording what is spoken could misread a figure aloud.
- **The voice:** the computer's own speech, and only voices installed on the machine (some Windows "Natural" voices
  are online).
- **Settings:** off by default, beside Text size, with slower / normal / faster. Esc stops it.
- **Not a screen reader:** it must stay off when one is in use, or everything is spoken twice. It doesn't replace
  P5's session.

**P6c. "Would you like this explained further?"** Rob: *"after the reading of the section the ai should ask would you
like this explain further, then it reads that section of explain."*
- After a section is read, Groundwork asks, in its fixed words, whether to explain it further.
- On yes (spoken, Enter or a click), it reads that section's Explain (item 103): the fixed words for what it works
  out and, with AI on, the checked lines on what the figures mean.
- With AI off, the fixed words only. The question never depends on AI being on.

**Open for P6:**
- (a) Read on hover automatically, on a key, or both (proposed: both, the key as the default).
- (b) Whether simple mode stays in P6.

**Proposed as its own item (113): voice commands.** Rob: *"this causes another add on ... we have to add voice
commands now."*
- **On-device recognition only:** whisper.cpp, the same family and graphics paths as the engine (llama.cpp), about
  75-150 MB. The browser engine's built-in recognition sends audio to Google, Microsoft or Apple, which would break
  the local-only promise.
- **Push to talk, never always listening.** An indicator shows while listening. The audio is turned into words and
  never kept.
- **A closed command set:**
  - answers: yes, no, stop, repeat, slower, faster, read this, read the page, next, back;
  - navigation, through the Ask box's existing commands (item 102 A6-A8);
  - anything else goes to the Ask box, as if typed.
- **Off by default.** The operating system asks for the microphone the first time.
- **Before it is built:**
  - the website and privacy copy need a line on the microphone;
  - a test that no audio leaves the machine;
  - measurements on Rob's Mac and the Windows laptop, including how well it hears money ("four hundred fifty
    dollars").

### Item 113 (proposed): on the computer only, and which open engine

**Rob, 2026-10-24:** *"Sending the data to someone though is kinda of a deal breaker for me."* So this is a hard rule,
not a preference:
- **Voice never leaves the computer.** The audio, the words recognised and the speech read aloud all stay on the
  machine. Nothing is sent, nothing is kept.
- **The browser engine's own speech recognition is never used.** It sends audio to Google, Microsoft or Apple, so the
  page disables it rather than merely not calling it.
- **Read-aloud uses voices installed on the machine only** (no online "Natural" voices).
- **The gate holds it:** a test that recognition and read-aloud make no network request, and that the browser's
  recognition is absent from the code.

**The open engines (all run on the computer; licences checked again at build):**

| | Licence | Size | Fits | Weak at |
|---|---|---|---|---|
| whisper.cpp (Whisper) | MIT | 75-150 MB, English tiny/base | spoken questions; the same family and graphics paths as the engine (llama.cpp) | heavier; short clips, not streaming |
| Vosk (Kaldi) | Apache 2.0 | about 50 MB, small English | commands: streams, and can be held to a fixed phrase list | open-ended speech |
| Moonshine | MIT | about 30-60 MB | short commands, fast on small machines | newer, English only |
| Sherpa-ONNX | Apache 2.0 | varies | streaming, many models | more to package |

**Proposed:**
- **Measure two before choosing:** Vosk held to the command list, and whisper.cpp for spoken questions. Measure on
  Rob's Mac and the Windows laptop: words right (money especially - "four hundred fifty dollars", "$1,650"), the time
  to an answer, the memory used and the size added.
- **Possibly ship both:** Vosk always on hand for commands, Whisper only when someone speaks a question.

## 6. Built: P1-P5, P7 (2026-10-24), s261

| | What | Commit |
|---|---|---|
| P2 | A charge a fund saved for (within 10% of its balance or target, or sharing a word with its name) is never priced; "I had to" (car, home, health, other) on the brake and the Ledger lesson, with Undo | a9ccf7a |
| P3 | "Is this what you were saving for?" on a recent charge near a fund's balance: yes spends it, and closes a fund with under a tenth of its target left; no is kept; Undo. Deposits are never capped at the target | a9ccf7a |
| P5 | Over and near the budget said in words beside the colour; the spending donut and both net-worth charts carry a text summary. Contrast was already AA (item 77) | a9ccf7a |
| P1 | Pay with no schedule, landing several times a week, read by the week: a typical, low and high week over 13 (empty weeks count as $0), as facts; counted toward monthly income | 0b64d85 |
| P4 | Budget edits record who made them in Household mode; one partner's cut and the other's restore read undecided, and "Is this a shared decision?" is asked | 0b64d85 |
| P7 | Outside help (NFCC, 211, CFPB, lawhelp.org) from the ? help; "Print a summary" and the check-in's "Print this" | 0b64d85 |

Full suite on Rob's Mac: 3,950 passed, 0 failed. Checked in a browser: the Budget rows' words and the Outside help page.

**Still owed:**
- ~~The CFPB number and the two addresses~~ - confirmed by Rob 2026-10-24: consumerfinance.gov, (855) 411-2372,
  lawhelp.org.
- A fund row that is over its target saying "over" in words (the server already reports it).
- Words for the colour-only states beyond the Budget rows.
- Rob's screen-reader session (P5).

**Item 113, where it can be tested (Rob, 2026-10-24):** *"my mac does not have a microphone so it will be only tested
on the windows machine."*
- Recognition (Vosk and whisper.cpp) is measured on the Windows laptop only.
- The Mac build can still be checked without a microphone, using recorded audio files: the same model, the same
  words, so the Mac's recognition is compared with Windows', and how it behaves with no microphone is tested.
- Nobody speaking into a Mac is a gap to say plainly at release, unless a USB or Bluetooth microphone is used later.
- Read-aloud (P6) needs only speakers, so it is tested on both.

### Item 113, measured on Rob's Mac (2026-10-24, recorded audio, no microphone)

Thirty phrases (18 commands, 6 with money, 6 questions) spoken by four macOS voices (Samantha, Reed, Flo, Grandpa)
into 16 kHz files with `say`, then run through each engine on this Mac. Nothing left the computer.

| Engine | Commands | Money amounts | Questions | Peak memory | Time vs audio | Size added |
|---|---|---|---|---|---|---|
| Vosk small, held to the command list | 69/72 | - | - | 165 MB | about 1% | ~80 MB |
| Vosk small, free speech | 49/72 | 18/24 | 12/24 | 239 MB | 21% | (same) |
| whisper.cpp base.en | 57/72 | 24/24 | 20/24 | 338 MB | 6% | ~152 MB |
| **whisper.cpp base.en + a word hint** | **68/72** | **24/24** | **23/24** | 338 MB | 6% | ~152 MB |

- **Scoring:**
  - a money phrase counts when the dollar amount matches ("$450" or "four hundred fifty");
  - commands must match exactly (Vosk's "[unk]" for a breath is stripped);
  - questions are right at 20% word error or less.
- **The hint is one line of expected words** (debt, payoff, budget, ledger, Kroger, the commands). Without it,
  Whisper heard "debt" as "that", "death", "test" and "dad's".
- **Misses left with the hint:** "back" as "But" or "Bye", one "show my debts" as "show my test", one "do I pay" for
  "am I paying".

**Proposed:**
- One engine, whisper.cpp base.en with the hint. Vosk would add a second engine and ~80 MB for one command in 72.
- "Go back" rather than "back".
- Groundwork says what it heard before acting ("Showing your debts"), with Undo, so a mishearing is visible.
- The Windows laptop's microphone with real voices is the real test, before any build.

**Item 113 ruled (Rob, 2026-10-24):** *"i accept your recommendations"*:
- whisper.cpp base.en with the word hint, one engine;
- "go back" for "back";
- Groundwork says what it heard before acting, with Undo;
- the Windows laptop's microphone with real voices as the real test;
- on this computer only, push to talk, off by default (the hard rule above).
