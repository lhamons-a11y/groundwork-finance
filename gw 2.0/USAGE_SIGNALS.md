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

## 3. Status

OPENED 2026-10-05. Points 1 and 3 ruled and built on master (gate below). U1–U6 for point 2 sought. Their build is
not authorised.
