# Item 39 — Where Groundwork reads the person from how they use it

Opened 2026-10-05. Rob asked: *"have we feature creep the willingness layer? and are we breaking guardrails?"* The
review (2026-10-05, master `a83ed1d`) found the Willingness Layer within its ruling and its read boundary intact. It
found three places close to the line. Rob: *"Yes open the small pass covering 2-3 .. also remove rule on the dead
label"*, then *"Point 1 can go"*.

The rules in play:
- **No silent learning** (2026-08-17): an observation not surfaced to the person may not become persistent memory. No
  engagement signals, no learned ranking, no inference from silence.
- **The Willingness Layer's ruling 6** (2026-09-27): it never reads usage, dismissals included. *"A dismissal says 'I
  dismissed this', not 'I am unwilling to do this'."*
- **The dashboard rule** (2026-09-27): usage never creates, ranks or implies anything.

## 1. Ruled and built in this pass

**Point 1 — the "kept through tight months" reading is removed** (Rob: *"Point 1 can go"*).
- **What it was.** `core/willingness.py` read an envelope as *sacred, until shown otherwise* when it was kept, not
  cut, through two months in which spending passed income.
- **Why it goes.** It was the one reading that concluded from what the user did *not* do, the nearest thing in the
  layer to inference from silence.
- **What remains.** The two readings that rest on something the user *did* to the budget: a cut that held
  (flexible), and a cut later restored (sacred).
- **The change:**
  - `tight_months`, `MIN_TIGHT_MONTHS` and the `held` branch are removed. An envelope never cut reads *no_evidence*.
  - The page's wording for it (`static/js/teaching/willingness.js`) is removed.
- **What it does to existing data.** Readings are recalculated on every read and never stored, so no saved data
  changes. A statement a user made in answer to such a reading stays theirs (W-B is sovereign and append-only).
- **Tests:**
  - s129 now proves an envelope kept through tight months concludes nothing, and that the reading is gone from the
    engine and the page.
  - s130's break-detector cases used a *held* reading as their concluded reading. They now use a *restored* one,
    with the same assertions.
- **This amends blueprint Appendix E.2**, which listed *"held through tight months"* as a reading. The amendment is
  Rob's ruling of 2026-10-05.

**Point 3 — the dead "engaged / occasional / passive" label is removed** (Rob: *"remove rule on the dead label"*).
- **What it was.** `app.js` `_calcBehavioralProfile` labelled the user from how many transactions they had in three
  months.
- **What read it.** Nothing. It reached no prompt and no screen. It is removed with its comment, and s150 keeps it out.
- **Lines.** Under item 32's L1 this is not a 1.x fix, so it is removed on master only. 1.x keeps the unused value.

## 2. Point 2 — dismissing a proactive insight (measured 2026-10-05; for ruling)

**What a dismissal does today.** The dashboard's proactive card has a dismiss button (`static/js/teaching/proactive.js`).
Pressing it removes the card and posts `/api/proactive/dismiss`, which logs `proactive_dismissed` with the insight's
key and category. `core/proactive.py` then applies three effects:

| # | Effect | How long | Seen by the user? |
|---|---|---|---|
| a | **That insight** is not shown again | 60 days | No. The card just disappears. |
| b | **Its whole category** is never promoted again once two of its insights have been dismissed (*"drops it to passive for good"*). Insights stay on their own pages. | **Permanent** | **No.** Nothing says it happened, nothing lists silenced categories, and nothing undoes it. |
| c | **The cadence drops a tier** when the number of dismissals in seven days reaches the weekly brake allowance (2) | While it holds | No. The Settings dial still shows its own setting's note. |

- The code calls (c) *"implicit learning"* and *"the only sanctioned use of engagement data"*. It describes (b) as
  *"an instruction, not a signal to be modelled"*.
- **On both lines:** `core/proactive.py` is on `lts/1.x` and master. It was built 2026-09-05, after the no-silent-learning
  rule.
- **The explicit control already exists:** Settings' dial (*normal / fewer / off*), with its own notes.

**Measured against the rules:**
- **(a)** answers the thing dismissed, so it is an instruction about that insight. It is just not said.
- **(b)** turns two clicks into a permanent conclusion about a whole category, never shown to the person: an
  unsurfaced observation that persists. That is what the no-silent-learning rule forbids.
- **(c)** learns a pace from behaviour when the user has a dial for it. It is temporary, but unsurfaced.

**Points for ruling:**

**U1–U4 RULED 2026-10-09 (Rob: "approve U1–U4 as recommended")**: U1 said, U2 (b) asked, U3 the backoff goes, U4 old silenced categories are no longer silenced. U5 (lines) and U6 (tests) were not in the ruling and stay open by name. **BUILT 2026-10-09 (Rob: "build item 39")**, master only (the 1.x rule's default; U5 itself is still unruled): `core/proactive.py` gates a category only on the user's `proactive_silenced` setting and has no backoff; `/api/proactive/dismiss` returns the 60 days and, from the second dismissal in a category, the question; `/silence`, `/silenced`, `/unsilence`; the card's words and the Settings list with Undo in `teaching/proactive.js`; `s169` holds U6's list; `s45`'s A.4 checks now hold the ruled behaviour. Awaiting acceptance.

- **U1. The insight's own cooldown stays, and is said.** At the moment of dismissing, the card is replaced by
  *"Dismissed. Groundwork won't bring this up again for 60 days."*

  *Recommended.*
- **U2. A category is silenced only when the user says so.** Three options:
  - (a) Removed: a dismissal applies to that insight alone.
  - (b) **Asked:** after a second dismissal in a category, the card asks once: *"Stop bringing up <category> on its
    own? Insights about it stay on their pages."* A yes is stored as the user's own setting, listed in Settings
    with *Undo*. A no, or no answer, changes nothing. Nothing is inferred.
  - (c) Kept as it works now, but shown in Settings and undoable.

  *Recommended: (b).* It turns an inference into a statement, the same move the Willingness Layer makes. (c) still
  concludes first and tells afterwards.
- **U3. The cadence backoff goes.** The dial is the control. A user who wants fewer insights says so with it, and the
  backoff's reading of *"the same request made two ways"* is an inference.

  *Recommended.* (Keeping it, but surfaced, is the alternative.)
- **U4. What happens to categories already silenced.** Existing `proactive_dismissed` rows stay as recorded (nothing
  rewritten). Under U2 (b), a category silenced by the old rule is no longer silenced, because no one said so. Its
  next insight can appear and, if dismissed twice, asks.

  *Recommended.*
- **U5. Lines.** Not a data-loss, wrong-saved-figure or security fix, so master only under item 32's L1 (L2b). 1.x
  keeps today's behaviour.

  *Recommended.*
- **U6. Tests:**
  - a dismissal logs and says its 60 days;
  - two dismissals ask and never silence on their own;
  - a yes is listed and undoable;
  - no cadence change follows dismissals;
  - the old rule's silenced category is no longer silenced.

  *Recommended.*

## 2a. The rule's edges

Rob asked: *"What are your feelings on the no silent learning rule? Are we narrowing the scope too much?"* The review
found the rule right and not too narrow, read as *surface it*, not *never infer*. It also found three ways it can be
over-read:
- **It can be read as forbidding a conclusion that is shown, with its receipt, and disputable.** The tight-months
  reading met the rule. It was removed for weak evidence, which is a different reason.
- **It can be read as forbidding protective bookkeeping,** such as caps and cooldowns.
- **It can be read as forbidding the user's own settings.**

The cost of the rule is that Groundwork asks rather than guesses. The answer to that cost is to ask rarely, at the
moment the evidence appears (U2 (b)), not to loosen the rule.

Rob, 2026-10-05: *"Groundwork should be transparent and let the user know everything it is doing. That builds trust
with the user also it makes the software be 100% accurate. If the formulas are correct and the numbers are correct the
math is correct and math doesn't have an opinion it's just a fact."*

**U7. The rule's edges, written down so later passes neither widen nor narrow it by accident.**

- **Conclusions about the person** (willingness, strategy, any label of who they are or how they behave):
  - always shown to them, with the evidence they rest on, and disputable;
  - **never drawn from usage** (pages opened, clicks, dismissals, time in the app);
  - an inference must earn its place by test before it exists (W-E's null model).
- **Protective bookkeeping** (frequency caps, cooldowns, limits that keep Groundwork from nagging):
  - allowed, and may count what was shown or dismissed;
  - it draws no conclusion about the person;
  - **it is stated whenever it changes what the user sees** (U1).
- **The user's own settings and conveniences** (a dial, a hidden card, a collapsed panel, the last tab): allowed. They
  are the user's choice, kept as such.
- **Transparency is the default:**
  - Groundwork tells the user what it is doing, what it has concluded and why, and what it chose not to show.
  - Nothing that affects what they see happens without a sentence that says so.
- **A figure is a fact only when its inputs are.**
  - A figure computed from the user's record by a correct formula is stated as a fact.
  - Anything resting on an assumption is stated **as an assumption, with the assumption named**. For example: a
    return rate, an EIA forecast, a typical month.
  - It is never shown as a fact. This extends the report rule (2026-09-27), that a statement must be proven in the
    same run or it is blocked.

*Recommended.* It is a statement of the rule, not a build. It applies to every pass that follows, and BUILD_QUEUE's
header carries a one-line pointer to it.

**U7 RULED (Rob, 2026-10-05: *"I accept it"*).** With it, Rob: *"I really feel we are close to building this as a full
feature financial application and we have an obligation to make sure the software shows the user why the answer is
what it is and how the answer came about."*

So every figure and conclusion Groundwork shows carries, where the user can reach it:
- **why** it is what it is;
- **how** it came about: the inputs from their record, the formula, and any assumption, named as one.

A pass that adds a figure says how it meets this. A figure that cannot show its working is not shown. This is the
same standard as the report rule (proven in the same run, or blocked), applied to every screen.

**U7, where the working lives (Rob, 2026-10-05).** *"We can show our formulas in the help menu and items that won't
change in the help menu. What we show the user is what transactions they made and those numbers. If a user manually
entered the wrong number they should see that values in the report. Like how a bank sends monthly draft reports. That
shows the transactions. We don't need to show everything in the ui but the report will be valued."*

| Where | What it carries |
|---|---|
| **The screens** | The figures, and the user's own transactions and numbers behind them. Not every formula. |
| **The help menu** | The formulas, and the fixed inputs that do not change (constants, published rates, rules), each named. |
| **The monthly report** | The statement, like a bank's monthly statement: every transaction and every entry the user made, **as entered**, including a number they typed wrong, so they can see it and fix it. |

- The report never corrects, smooths or hides a user's entry. The value shown is the value recorded, with its source:
  imported or entered by hand.
- So *"why and how"* is always reachable: the figure on screen, its formula in help, and its transactions in the
  report.
- This explains the volume concern raised in review (transparency becoming overload): the working is one step away,
  not on every screen.

## 3. Status

OPENED 2026-10-05. U7 refined 2026-10-05 (where the working lives: screens / help / report). Points 1 and 3 ruled and built on master: `f300d85`, master gate 2396 / 0 (s129 45/45, s130 35/35, s150 2/2). U7 RULED 2026-10-05. U1–U6 for point 2
sought, and not assumed. Their build is not authorised.
