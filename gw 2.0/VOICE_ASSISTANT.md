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

## 4b. V11 Spanish - measured, not built (2026-11-01). Rob's to rule.

Speaking needs nothing new: the shipped voices file already holds Spanish voices (ef_dora, em_alex). Listening does:
base.en hears English only. Measured with whisper.cpp's multilingual `base` (141 MB, the same size as base.en):

| | result |
|---|---|
| Spanish, 11 commands x Dora and Alex x clean and noise (44) | 28 heard exactly (64%); mean word error 23.8%; 1.1 s each |
| what misses | an English store name ("Kroger" heard as "crojero"), one-word commands ("Para" as "Parque", "Repite" as "Repita"), "Muéstrame" split into "Muestra me" - harmless to a router |
| English, 50 commands, routed by the Ask bar | base.en 50/50; multilingual base 50/50 |

So swapping base.en for the multilingual base would cost English nothing measured here, at no extra size, and would
hear Spanish. **What it would not do on its own:** every command, page name, reply and fixed sentence is English. A
Spanish Groundwork is a Spanish command layer and Spanish fixed words throughout - the real work. The questions for Rob:
(a) swap to the multilingual model now (English unchanged, Spanish heard but only questions to the assistant work), or
(b) the full Spanish layer as its own item, or (c) neither yet.

**Every language Groundwork's voice speaks (Rob 2026-11-01: "lets do all of them"), measured the same way:** the same
11 commands in each, said by Kokoro's voices (two where it has two; French has one), clean and with noise, heard by the
multilingual base. "Named right" is whisper telling the language from the voice alone, told nothing (for Rob's
question: can Groundwork pick up the person's language?). Japanese and Chinese are scored by character.

| language | named right | heard exactly | mean error | note |
|---|---|---|---|---|
| English | 44/44 | 31/44 | 10.3% (word) | control; routing was 97% (4a) |
| Spanish | 40/44 | 29/44 | 21.5% (word) | |
| French | 19/22 | 10/22 | 47.3% (word) | one voice only |
| Italian | 34/44 | 24/44 | 26.8% (word) | |
| Portuguese (Brazil) | 32/44 | 15/44 | 60.5% (word) | |
| Hindi | 23/44 | 0/44 | 114.8% (word) | |
| Japanese | 17/44 | 0/44 | 489.9% (char) | the voice cannot read kanji: espeak says "Chinese letter" for each |
| Mandarin | 33/44 | 0/44 | 98.9% (char) | |

**What this does and does not say.** It is whisper hearing *Groundwork's own voice*: where the voice is weak (Japanese
plainly; Hindi and Mandarin likely, and a script mismatch - simplified against traditional, Devanagari against Urdu -
scores as all wrong) the listening is judged on bad input. It is not a measure of real people. What it does say:
naming the language works for English and Spanish and is unreliable on one short command elsewhere - so an offer to
switch should wait for several things said, not one. Spanish, Italian and French are the ones near usable with these
two engines; Portuguese is weaker; Hindi, Japanese and Mandarin are not ready with them (Japanese needs its own
pronunciation tool before Groundwork can speak it at all). A larger multilingual whisper ("small", about 465 MB)
hears other languages far better than base - a size Rob would weigh. Real speakers decide all of it.

## 4c. V19 Only voices it knows - BUILT 2026-11-01, awaiting acceptance

Rob 2026-11-01, after the microphone kept picking up the television: *"lets have it recognize your voice.. Since we
are dealing with people finance and health information."* Background sound was handled first (an adaptive room level
and a minimum length of sound, s281); a television's speech is speech, so only knowing the voice keeps it out.

**As built** (`core/voiceprint.py`, routes in `server.py`, Settings in `access.js`, s282):
- **The model**: WeSpeaker ResNet34-LM trained on VoxCeleb, 26.5 MB, **CC BY 4.0** (commercial use with credit;
  credited in `THIRD_PARTY_NOTICES.md`), run by the ONNX Runtime Groundwork's voice already ships. Pinned by SHA-256,
  fetched by `scripts/fetch_voiceprint_model.py`, placed by all three installers and the Mac/Linux specs. Kaldi's
  80-band filterbank is computed in NumPy, as WeSpeaker computes it, with the silence trimmed first.
- **Enrolling**: Settings -> Reading & Voice -> *Only voices it knows* -> *Teach it my voice*. Five everyday sentences,
  one at a time, each ended by a pause. The server makes the voiceprint (256 numbers, not a recording) and keeps it in
  the record under its own setting; *Only voices it knows* turns on. A reading that does not sound like the others is
  refused and nothing is kept. Each person in the household can add their own, by name; enrolling again under the
  same name replaces it. *Forget* deletes it; with none left the setting turns off.
- **The gate**: with it on, each clip is scored against the voices it knows before whisper runs. Below the bar the clip
  is let go - no words recognised, no toast, nothing kept. A clip it cannot score is no one it knows (fail closed).
  **Anyone may say "stop" while Groundwork reads** - stopping can only hide; "next", "repeat" and the rest are gated.
- **Never sent to the page**: `/api/settings` leaves the voiceprints out and PATCH cannot write them; the page sees
  names and dates only. **Never learned from listening** (the no-silent-learning rule): only enrolling changes it.
- **Test my microphone** says whose voice it heard, with the score and the bar ("Scored 0.71; it needs 0.45").
- **Said plainly in Settings**: it keeps other voices from using Groundwork; it is **not a lock** - a recording of the
  person's voice could pass it, and it does nothing about someone reading the screen.

**Measured** (`scripts/voiceprint_measure.py`, 2026-11-01): 30 synthetic voices - every English Kokoro voice and
Windows' David and Zira - each enrolled in turn, then V8's 30 commands said by it and by the 29 others, clean, with
noise at 15 dB, and with a 60 Hz hum at 10 dB. 2,690 same-voice and 78,010 other-voice clips.

| bar | the enrolled voice refused | another voice taken |
|---|---|---|
| 0.35 | 4.2% | 3.0% |
| 0.40 | 7.6% | 1.7% |
| **0.45 (as built)** | **11.0%** | **0.87%** |
| 0.55 | 25% | 0.17% |

- Equal error rate 3.6%. A voiceprint takes 40 ms for a 3 s clip (143 ms at most).
- **Trimming the silence is what makes it work**: without it the equal error rate was 29%.
- **Short commands are the weak point**: under a second of speech ("Stop", "Next"), the enrolled voice's median score is
  0.50 against 0.67-0.75 for longer commands - most of the 11% refused are one-word commands.
- Enrolment's agreement bar (0.65): every voice's own readings agreed at 0.794 or more; with one reading swapped for
  another voice's, 4,344 of 4,350 were caught.
- The null model: noise, hum and silence alone scored at most 0.11.
- An error in the first run, caught: "Microsoft Mark" is not installed, so Windows kept speaking as Zira - the "two
  voices" scored 0.909. Only installed voices are used now.

**Not the exit criterion**: Kokoro's voices are one model's styles and may sit closer together, or further apart, than
people do. The bar is settled only on real people - Rob, and someone else - on the Windows laptop's microphone, with a
television on.

**Rob's to rule** (built as recommended, each one constant or line to change):

| # | Question | As built |
|---|---|---|
| K-a | The bar | 0.45: about 1 in 9 commands from the enrolled voice refused (mostly one word), under 1 in 100 from other voices taken. Lower is friendlier, higher is stricter. |
| K-b | "Stop" from anyone while it reads | allowed - stopping only hides. Gate it too, or allow "pause" only? |
| K-c | What a refused clip shows | nothing - the television would otherwise toast every sentence. The enrolled person finds out from Test my microphone. |
| K-d | Turned on by enrolling | yes - that is why someone enrols. |

## 4d. V20 Several commands in one ask - BUILT 2026-11-01, awaiting acceptance

Rob 2026-11-01: *"Groundwork to open the ledger, and then show me all of Chiefs Supermarket transactions" ... "It should
be able to understand a multiple ask."* The ask is split at "and then", "then", "after that", "and also", "and" and
commas - **only where every part is itself a command Groundwork knows** (a page, an action, a Ledger search, what's
coming up); otherwise it stays one ask, so "my Kroger and Walmart transactions" is still one search and a question is
still a question. Up to four parts, done in the order said, each given a moment for its page to open; a spoken ask
hears one reply naming them all ("Sure, opening the Ledger for you. Then, OK, showing your Chiefs Supermarket
transactions in the Ledger."). Typed asks get the same. A leftover "to" ("Groundwork to open ...") is dropped. s283.

**"Go"** (Rob: *"Groundwork go get my accounts ... go should work for anything like go to Budget"*): "go", "go and" or "go
ahead and" in front of anything is a lead-in - "go budget", "go show me my Kroger transactions", "go build a report".
"Go to ..." reads as it did, "go back to the budget" goes there, and "go back", "go ahead" and "go" alone stay their own
words. s283 M10.

**Several stores in one search** (Rob: *"it fails on asking for two stores"*): "my Kroger and Walmart transactions",
"Kroger, Walmart and Aldi" - each store searched, when each is in the record and the whole phrase is not ("Barnes and
Noble" stays one name). The Ledger search takes "kroger or walmart", typed too.

**A store said as it sounds** (Rob: *"meyer is meijer"*): a name that matches nothing is taken as the record's store it
sounds like - compared by sound (ij/y, ph/f, ck/k, double letters, a plural s), against the store's whole name and its
first words, same first letter, one sound different at most (two in a long name) - and the toast says what was heard.
Measured on Rob's 295 stores: Meyer and Meijers -> Meijer, Chiefs Supermarket -> Chief Supermarket 2 Millbrook, Aldis,
Wallmart found; 40 everyday words that are not stores ("dinner", "milk", "rent") taken for none - the first cut took
"dinner" for Disney+ and missed "Chiefs" entirely, and was tightened before it shipped.

**In a list, a name that is no store** is named as not found and the rest are shown (whisper wrote "my Meijer and
Walmart" as "admire and walmart": Walmart shown, "nothing in your record is called 'admire'").

**"When I say admire, I mean Meijer"** (Rob: *"Yes, add that"*): what Groundwork hears, taken the person's way from then
on - whole words only, spoken words only (typed words are already the person's). Said back with an Undo, kept in
Settings -> Reading & Voice -> *Words it hears your way*, each with Remove; never learned without being told (the
no-silent-learning rule, as V16 for how names are said).

## 4e. V21 Groundwork's voice learns from the person, and can be taught - RULED 2026-11-01, BUILT

Rob 2026-11-01: *"the voice assistant should be able to learn from the user and I think we will need to have a way that
the user can teach the voice assistant. Lets make that the call."* It came from whisper hearing "Meijer" as "admire"
every time - even in "I mean Meijer", so the word meant could not be said.

**How it stays inside the no-silent-learning rule** (*an observation not surfaced to the person cannot become
persistent memory*): nothing is kept until it is said. The counting lives in the window's memory only; when a word is
learned, Groundwork says so then - *"I noticed that when I hear admire, you mean Meijer. I will take it that way from now
on"* - with an Undo, and it is listed in Settings with Remove. A one-time notice alone was considered and set aside: it
says learning happens, not what was learned.

- **Taught**: Settings -> Reading & Voice -> *Words it hears your way*: *Teach it a word* (say it; Groundwork shows what
  it heard; type what was said), the typed form *When I say [ ] I mean [ ]*, or saying "when I say admire, I mean
  Meijer". Saying it with the same word twice ("I mean admire") is answered, not dropped.
- **Learned**: a spoken search word that finds nothing, then - within a minute, said or typed - one store looked for
  instead. **The third time**, the word is taken as that store.
- **Measured before it was built** (null model on Rob's stores and how often he shops at each, 20,000 sessions): with no
  link between the two searches, learning after one pairing was wrong in 48% of sessions, after two 0.04%, after three
  none. The hard case is habit - a store not found, then the usual one: with the same usual store 80% of the time, two
  was wrong in 2.3% of sessions and three in 0.08%. Hence three.
- The voiceprint (4c) is unchanged: it is never adapted from listening, only by enrolling again.
- **Settings has its own tab, Reading & Voice** (Rob: *"in settings I would like a tab all voice and reading assistance
  should get moved to"*): text size, read aloud, Groundwork's voice, voice first, voice commands, start by saying
  Groundwork, the microphone, words it hears your way, only voices it knows. "Accessibility" was offered; Reading & Voice
  was chosen because voice commands are not only an accessibility feature, and the section already had that name.

## 4f. V22 The country's supermarket chains - BUILT 2026-11-01

Rob 2026-11-01: *"here is a website to grab all of the major national Grocery Stores that is in the United States"*
(Wikipedia, *List of supermarket chains in the United States*). Asked what Groundwork should do with it, he chose all
three: say every name right, hear the names right, know they are grocery stores.

- **The list**: `core/data/grocery_chains.json`, built by `scripts/build_grocery_chains.py` from the page's raw text
  (revision 1375454291, 2026-09-17) - 353 names: 332 grocery, 10 mixed (Walmart, Target, Costco, Amazon, Sam's Club,
  BJ's, the dollar stores), 11 parent companies and cooperatives. Wholesalers and defunct chains are left out. It ships
  with the app; Groundwork never fetches it. Credited (CC BY-SA 4.0) in THIRD_PARTY_NOTICES.md.
- **Said right**: every name was run through Groundwork's voice and its phonemes read; 45 it says wrong are respelled
  (Fred Meyer was "Fred MAY-er", IGA "igga", Lidl "LID-ul", Ingles "ing-LEZ", Gelson's and Gerrity's a soft g,
  Stater Bros. "Brose", and the Spanish, Japanese, Korean and Vietnamese names read as English). The store's own words
  alone are respelled too ("GELSON'S #12"). The person's own "say X like Y" still wins. Rob is to listen to these.
- **Heard right**: the sound-alike matching (4d) tries the person's own stores first, then the chains - "wegmen's" is
  Wegmans before a first visit. Measured: 16 mishearings found (Wegmans, Hy-Vee, Lidl, Schnucks, Trader Joe's, Fred
  Meyer...), and of 76 everyday words none taken for a different store.
- **Known as grocery**: right after the importer's own Groceries rule, on the server (`bank_importer.auto_category`)
  and the page (`clientAutoCategory`) alike, a bank line naming a grocery chain - or saying "supermarket" /
  "supermercado" - is Groceries. Before this, "food" filed Food Lion, Cub Foods, Harps and Food 4 Less as Restaurants.
  Never moved: 62 chains named by an everyday word or phrase (Giant, Lucky, Tops, Seasons, Market Street, City
  Market - "LUCKY DRAGON" is not a supermarket, "123 MARKET STREET" is an address), the mixed stores (their own rules
  stand), and the precise rules before it (Meijer Express is fuel, Walgreens is Prescriptions).
- **Measured on Rob's record** (1,751 transactions): the rules now file 66 differently - Chief Supermarket 2 Millbrook (65,
  $2,574.08: Other -> Groceries; saved today under the parent Food) and one Jim's Thriftway. Only new imports are
  filed by the rules; nothing saved moves, and the category review offers any move only on a Yes. s284.

## 4g. V23 The other major stores, with how they are said - BUILT 2026-11-04

Rob 2026-11-04: *"lets grab all of the Department stores, pharmacies, all major shopping stores in the United States with
phenetic spelling to train Whisper. Also feel free to add anything else that you can think of maybe gas stations etc."*

- **The list**: `core/data/us_stores.json`, written by hand - 585 rows in 31 groups: department, discount, warehouse,
  major supermarkets, pharmacies, home improvement, electronics, clothing, shoes, jewelry, sporting, craft, furniture,
  pet, beauty, books and toys, office and shipping, auto parts, tires and service, farm stores, gas and convenience, fast
  food, coffee, casual dining, online, phone and internet, streaming, rides and delivery, travel, banks and cards,
  insurance. Each row: name, phonetic spelling, what is heard instead. Closed chains stay (Rite Aid, JOANN, Party City):
  their names are still in people's records. A store on the V22 list keeps its kind and gains its heard forms.
- **whisper is not trained by a list.** The model file is fixed. What can be done is to nudge it with the prompt, and to
  correct what it writes afterwards. Both were measured (`scripts/store_names_measure.py`: "Show me my <store>
  transactions" said from the phonetic spelling by Kokoro af_heart and am_michael, whose forms were merged, then scored
  on bm_george, which was held out):

  | bm_george, 585 names | reached the store |
  |---|---|
  | whisper wrote the name itself | 397 |
  | with the V22 supermarket list only | 406 |
  | with the hand-written heard forms | 501 |
  | with the forms measured on the other two voices too | 524 |

  **The prompt**: of the 52 names that fit its 800 characters, exact went from 33 to 43; of the 533 that did not fit, from
  370 to 364. It helps what it holds and costs the rest a little, and it would push out the person's own words (V1), so
  no store goes into it. Pharmacies would stay out regardless (H6).
- **Corrected, not rewritten**: `_askSoundsLike` tries the person's own stores first, then the heard forms ("coals" is
  Kohl's, a first letter the sound comparison can never reach), then the V22 list, then the other stores by whole name
  only. One sound can be two stores (QuikTrip, Kwik Trip): the one in the record wins. It runs only when what was heard
  matches nothing in the record, and the toast says what was heard.
- **Null model**: with every name in the sound comparison, "hotel" came back Hooters, "pets" Peet's Coffee, "school"
  Scheels. Hence whole name only and 7 letters or more for these rows; of 125 everyday words none is taken for a store
  (s285 N4). Measured forms that are everyday words ("golf" for Gulf, "belt" for Belk) were left out by hand.
- **Hearing only**: no row decides a category (only kind `grocery` does), and the phonetic spelling is not served to the
  page and does not change how Groundwork's voice says a name. s285.
- **Not the exit criterion**: these are synthetic voices; real people on real microphones will mishear differently.

## 4h. V24 Understanding how people talk - BUILT 2026-11-05

Rob 2026-11-05: *"Let's push everything that makes the voice addition stronger and feel more natural talking and
understanding of the user asks."* What was failing was not hearing but understanding: whisper wrote the words, and the
Ask bar only knew them in a few set shapes.

**Measured first** (`scripts/voice_natural_measure.py`, phrases in `scripts/voice_natural_asks.json`, written by hand, run
through the Ask bar's own code as a spoken ask with AI off):

| | before | after |
|---|---|---|
| the build set, fixed against (165) | 80 | 165 |
| held out: only its total was looked at while fixing (75) | 23 | 74 |
| real questions and passing remarks left for the assistant (87, 18 of them added before the fix) | 2 of the first 69 wrongly taken | 87 |

**Said aloud** (Kokoro's voice into Groundwork's whisper, then the router; before the last small fixes for "due" heard as
"do" and "budgets"):

| | af_heart before / after | bm_george before / after |
|---|---|---|
| build (165) | 80 / 162 | 78 / 159 |
| held out (75) | 24 / 67 | 23 / 66 |
| not commands left alone (87) | 81 / 87 | 81 / 87 |

What still misses is mostly mishearing ("Yeah, I open the budget", "from Shep"), which is what V21's teaching and V23's forms
are for.

- **Said any ordinary way**: "where's my budget", "check my debts", "pull my budget up", "would you mind opening the
  calendar", "the budget page please". A loose form opens a page only if what is left is exactly a page's name, so "check my
  math" and "take me out to dinner" stay questions.
- **A store, however it is put**: "show me Kroger", "everything from Costco", "my Costco purchases from this month". Only
  if it is in the record or sounds like a known store: "show me the money" searches nothing.
- **Answered, AI off** (Rob's to rule, below): "what did I spend at Kroger", "how much last month", "when did I last go to
  Costco" hear the record's own sum, worked out in the page from the same charges the Ledger then shows.
- **People put themselves right**: "open the budget, no wait, the ledger", "show me Kroger, I mean Walmart", then "no, I
  meant Walmart", "Walmart instead". Only when what came before was a command and what comes after names something real.
- **Pausing to think**: "show me my ... Kroger transactions" is one ask. What stops on a word that cannot end a sentence
  waits 2.6 seconds for the rest, and is asked as it stands if nothing comes, so nothing is lost. What sounds like
  someone struggling never waits (care first, item 104).
- **What's coming, as it's said**: "anything due this week", "do I have any bills due", then "and next week?". "Next week"
  used to answer with this week's dates and call them this week; it now looks up the week after.
- **The small words**: "never mind", "forget it", "thanks Groundwork", "hello Groundwork", "what do you do". To cut in: "hold
  on", "wait", "one more time", "what did you say", "too fast". To end it: "I'm done", "all done". "Groundwork, stop." and
  "okay stop please" were not understood as stop; they are now.
- **"Say that again" works on a reply.** It only knew readings, so it could not repeat an answer Groundwork had just spoken.
- **V4 finished**: AI off, a spoken question about a figure says where it is and opens the page, as approved; it had
  stopped at a "Show me" button the person could not press by voice. Nothing to answer it: "Sorry, I didn't get that. You
  could say ...", not "Ask is AI help, and AI is off."
- **Replies**: Rob's "Sure, opening the Budget for you" is the first; pages opened in the next five minutes are "OK, here's
  the Ledger", "Here's the Calendar". Nothing about this is kept.
- **Two wrong answers found and fixed**: "show me how to split a transaction" searched the Ledger for "how to split a", and
  "why is my net worth down" opened the page instead of being a question.

With AI on, everything here that is a command acts the same; spending questions go to the assistant, as before (s286 N3).

**Rob's to rule** (built as recommended):

| # | Question | As built |
|---|---|---|
| N-a | Saying a figure with AI off | **RULED 2026-11-05 (Rob: "Yes, keep it").** Yes, only when asked, from the record's lines, by code. The old note read "the assistant never states a figure"; this is not the assistant, and the lines are on screen under it. |
| N-b | Which store total | **Kept as built 2026-11-05, read from the same answer.** A store's charges, all time unless a month or year is said; refunds are not netted. |
| N-c | The shorter replies | **Kept as built: V24 ACCEPTED 2026-11-05 (Rob: "accept and push").** On; one line to turn off. |

**Not the exit criterion**: the phrases are one author's idea of how people talk, and the audio check is synthetic voices.
Real people will say things no list has. s286.

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

**Built so far (2026-10-31/11-01, branch `voice-116`):** stage 1 (e673b42, s274), stage 2 (3d3062d, s280), stage 3 (s277).
**V3's cost, as measured:** while it waits for its name nothing is recognised until someone speaks; each thing said in
the room - for Groundwork or not - costs one recognition, 1.0 to 1.3 seconds on up to 4 processor threads (V8's
timings). A quiet room costs nothing; a television in the room costs a recognition per sentence. It stops when the
window is left, and is off unless chosen.
| 4 | V9 voices, V10 microphone, V12 voice first | none |
| 5 | V11 Spanish | measured size and accuracy, then Rob |
| 6 | V13 spoken figures in, V14 dictation, V15 what's coming up, V16 say a name right, V17 step by step | none beyond section 4 |
| 7 | V18 Mac and Linux | built from pywebview's hooks; proven only on the hardware |

Each stage: a smoke section, the gate, and a run on the Windows laptop with a real microphone.
