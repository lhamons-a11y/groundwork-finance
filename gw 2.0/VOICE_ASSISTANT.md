# Item 116 — Voice as a serious feature: Groundwork you can talk to, and that talks back

Opened 2026-10-31. Rob, after Groundwork got its own voice:

> *"what am i missing with the voice assistant to make this feature more powerful. People are getting use to using
> voice controls in their software now. So this should be a serious feature."*

> *"I love these add them , anything else missing?"* - V1-V8 and the smaller items (section 3), approved as proposed.

**APPROVED 2026-10-31 as proposed** (section 3). Built in stages, one at a time, accepted between (section 5).
Section 4 approved the same day: *"I approve v13-v18 ... also I approve all section 4 to build."*

The rule under all of it, unchanged (`PANEL_REVIEW.md`, Rob 2026-10-24): *"Sending the data to someone though is kinda
of a deal breaker for me."* Everything heard and everything said stays on this computer. Nothing is kept.

---

## 1. What is true today (2026-10-31)

- **Listening** (item 113): the mic in the Ask box (or Alt+V) starts conversation mode. Each thing said, ended by a
  pause, is recognised here by whisper.cpp base.en (`core/voice.py`) with a fixed hint of Groundwork's words. Off after
  "stop", a minute of quiet, or leaving the window. It does not listen while Groundwork is speaking.
- **The microphone's yes is kept** (Rob 2026-10-31): the window answers its next request from the record; Settings can
  forget it (s272). The red light and the timing are what keep it from always listening.
- **Speaking**: Groundwork's own voice, Kokoro af_heart, made here (`core/speak.py`, s273). Figures said as a person
  says them - "450 dollars", "interest rate of 24.99 percent". The computer's voices are the fallback.
- **Commands**: pages, tabs, the report builder, Import, Get my accounts, a Ledger search ("show me my Kroger
  transactions"); lead-ins "Groundwork", "let's", "I want" (s271). A command said aloud is answered aloud ("Sure,
  opening the Budget for you"); typed, only the toast.
- **Questions**: with AI on, the assistant answers and the answer is read back. With AI off, a question about the
  person's figures opens the page that shows them, silently.
- **Changes**: a change is made only by pressing Yes on its card (H7). A spoken yes never makes a change.

## 2. What a serious voice feature needs that this lacks

Measured against what people now expect from voice in their software: start it without the hands, interrupt it,
ask follow-ups, act on the page, know what can be said, and recognise *their* words - their payees, accounts and
categories - not only Groundwork's.

## 3. Approved (Rob 2026-10-31: "I love these add them")

| # | What | As approved |
|---|---|---|
| V1 | **The person's own words in the recogniser** | whisper's hint is built from the record each time voice starts: payees, account names, categories, people, budget lines - with Groundwork's words. Read from the record on this computer; nothing new is kept. |
| V2 | **Interrupt it** | while Groundwork speaks it listens for a short list only - stop, quiet, next, repeat, slower, faster, no - and stops speaking to hear it. Echo cancellation is on; Groundwork's own words are not taken for the person's. |
| V3 | **Hands-free start** | "Groundwork, ..." starts a command with no tap, **only while Groundwork's window is in front, with the red light showing**, and only once turned on in Settings (off by default). It uses the listening Groundwork already has - a pause-ended clip, recognised here - acting only on what begins with "Groundwork"; everything else is let go unrecognised as a command and kept nowhere. Leaving the window turns it off, as conversation mode does now. |
| V4 | **Every reply aloud, and follow-ups** | with AI on or off, a spoken question gets a spoken reply - with AI off, the fixed sentence that says where the figure is shown, then the page. Follow-ups carry the last subject: "and last month?", "what about Walmart?", "the other one". The context lives in memory for the conversation only. |
| V5 | **Changes by voice, read back, made by the button** | "add a 40 dollar grocery purchase at Kroger today", "move 100 dollars from Groceries to Dining": Groundwork fills the card and **reads it back with its figures** ("Add 40 dollars, Groceries, Kroger, today?"). The change is made by pressing Yes, as H7 says; a spoken yes still never makes it. Groundwork never pays. |
| V6 | **Control the page** | open a tab, sort, filter ("only this month", "just Groceries"), clear the search, scroll, read the next card, go back - what the page's own controls do, nothing they don't. |
| V7 | **Learnable and responsive** | "What can I say?" answered aloud, and a short list beside the mic; a soft sound when listening starts and stops; "One moment" said when an answer takes more than a second; a one-minute spoken tour the first time voice is turned on. |
| V8 | **Measured like a product** | a recorded set of real commands - Windows microphones, several accents, a noisy room - run by the gate: commands that did what was meant, and the time to the first word spoken. Exit criterion for "serious": each number written down with what it was measured on, and none of them guessed. |
| V9 | **Voice and speed** | a choice of Groundwork's voices in Settings (the ones shipped in `voices-v1.0.bin`), and slower / normal / faster as now. |
| V10 | **The microphone** | choose which microphone, and a "test my microphone" check that says what it heard. |
| V11 | **Spanish** | Spanish commands and reading. Needs a multilingual whisper model (base, not base.en) and Kokoro's Spanish voices; measured for size and accuracy before it ships. |
| V12 | **Voice first, for people who can't see the screen well** | a mode where every page change, toast and card is said, worked out with screen readers so nothing is said twice (`PANEL_REVIEW.md` P6b). |

## 4. Also missing - approved 2026-10-31 (Rob: "I approve v13-v18")

| # | What | Why |
|---|---|---|
| V13 | **Spoken figures in, not only out** | "set Groceries to four hundred fifty" - words to numbers, read back before the card's Yes (V5). Whisper writes most figures as digits, not all. |
| V14 | **Dictation into a field** | a memo, a note, a goal's name - said into the field in focus, shown before it is kept. |
| V15 | **"What's coming up?" said aloud** | the week ahead from the record's upcoming facts - bills due, a trip, a paycheck - only when asked (the anticipation aim: from the record, never watching). The Sunday check-in read aloud. |
| V16 | **Say a name right** | the person corrects how Groundwork says a payee ("say Meijer like my-er"); kept in the record, shown in Settings, removable - never learned silently. |
| V17 | **Step-by-step by voice** | a guided job spoken one step at a time - reconcile an account, import a statement, set up a bill - with "next" and "go back". |
| V18 | **Voice on Mac and Linux** | the kept microphone answer is Windows-only today (WebView2); the other windows ask each time. |

**Why V18 is needed at all** (Rob: *"if the assistant worked in Windows and the code is the same why would it work
differently on a Mac?"*). The engines and Groundwork's code are the same everywhere. The window is not: each system
lends its own browser to draw it - WebView2 on Windows, WKWebView on the Mac, WebKitGTK on Linux - and the microphone
question belongs to that browser, each with its own hook. pywebview answers none of them; the Windows fix answers
WebView2's `PermissionRequested`. Read in pywebview 6.2.1 (2026-10-31): the Mac window has no media-capture handler,
so WKWebView asks each time; the Linux window turns media on but handles no permission request, so WebKitGTK's
default applies - possibly a refusal. V18 answers each from the same kept yes. Untested: needs a Mac and a Linux
machine with a microphone (as item 33 Q6).

## 4a. Measured (V8, first cut, 2026-10-31 - synthetic voices, not yet real people)

`scripts/voice_measure.py`: 30 commands said by six voices - Kokoro af_heart, am_michael, bf_emma, bm_george (American
and British) and Windows' David and Zira - clean and with noise at about 15 dB, recognised by Groundwork's whisper.cpp
base.en with and without the household's words in the hint, then routed by the Ask bar's own code from `app.js`.

| | did what was meant |
|---|---|
| first run, 720 commands | 677 (94%) |
| the same recognitions after the router took whisper's punctuation ("Groundwork. Open my budget."), quotes, singular "transaction", "do" for "due", "calendars", "net work" | 698 (97%) |
| the short words said over Groundwork's voice (84), full hint | 76 |
| the same with only the short words as the hint (V2, `SHORT_HINT`) | 82 |
| with the household's words in the hint (V1) / without, 360 each | 339 / 338 - no measurable gain on these payees, which whisper already hears; the hint is for names like "Meijer", which this set does not carry |

Time to Groundwork's first spoken reply ("Sure, opening the Budget for you."): 0.6 to 0.9 seconds to make. Recognising a
command: 1.0 to 1.3 seconds. What still fails is mishearing, not routing - mostly the British male voice ("Stomp!" for
"Stop") and "my Kroger" heard as "microger". **Not the exit criterion:** that needs real people on real microphones.

## 5. Stages - one at a time, accepted between

| Stage | Items | Rulings needed first |
|---|---|---|
| 1 | V1 own words, V2 interrupt, V4 replies + follow-ups, V7 learnable, V8 the measured set (first cut) | none |
| 2 | V6 page control, V5 changes read back | none beyond section 3 |
| 3 | V3 hands-free start | none beyond section 3; its CPU while listening is measured and stated |
| 4 | V9 voices, V10 microphone, V12 voice first | none |
| 5 | V11 Spanish | measured size and accuracy, then Rob |
| 6 | V13 spoken figures in, V14 dictation, V15 what's coming up, V16 say a name right, V17 step by step | none beyond section 4 |
| 7 | V18 Mac and Linux | built from pywebview's hooks; proven only on the hardware |

Each stage: a smoke section, the gate, and a run on the Windows laptop with a real microphone.
