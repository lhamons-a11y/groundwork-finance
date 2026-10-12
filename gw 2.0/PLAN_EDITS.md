# Item 80 — A plan's Undo is not 33 decisions

Opened 2026-10-11. Found while building item 78: the working picture's *What your record shows* lists about 33
readings like *"ATM: you lowered its budget from $90.48 to $45.24 on Oct 10, 2026, then set it back to $90.48 on Oct
10, 2026. Groundwork reads it as something you keep."* Rob: *"yes open it as an item."*

**E1–E6 RULED 2026-10-11 as recommended (Rob: "approve E1–E6 as recommended"). No code yet:** the build needs its own go-ahead.

## 1. What is true today (measured 2026-10-11)

- **Two kinds of budget edits are written the same way.** The budget page's own edit route (`update_budget_item`)
  writes a `budget_adjusted` Historian entry when the person changes an amount. Item 71's *Make this my budget*
  (`income_change_apply`) and its *Undo* (`income_change_undo`) write one `budget_adjusted` entry per line, with the
  **same context**: nothing marks them as a plan or its Undo. These are the only code that writes budget edits.
- **The Willingness Layer reads every `budget_adjusted` entry as the person's own edit** (`_willingness_inputs`).
  Its rule (`core/willingness.py _reading`, ruled in item 23): a cut later restored means *sacred, restored* -
  "something you keep".
- **On Rob's data:**
  - *Make this my budget* was tapped on the false income card at 22:02:30 UTC on 2026-10-10, writing 33 cuts;
  - *Undo* was tapped at 23:19:03 UTC, writing 33 restores (66 entries in all);
  - the Layer now reads each of the 33 lines as kept on purpose.

  The readings are false, and they could steer later plans: a "sacred" line is the last place the budget-follows
  option looks.

## 2. Points for ruling

**E1. Mark a plan's edits.** *Make this my budget* and its *Undo* record which plan they belong to, in the entry's
context (`source: income_change_apply / income_change_undo`, with the plan's time). The page's own edit route stays
unmarked: those are the person's edits. *Recommended.*

**E2. An undone plan cancels out.** A plan that was undone contributes nothing to the Willingness Layer: neither its
cuts nor its restores are readings. Undoing a plan means *"not that"*, not *"I keep all 33 lines"*. *Recommended.*

**E3. A plan that is kept is the person's own choice.** They tapped *Make this my budget* on a plan they saw line by
line, so its cuts are read like any edit of theirs, under the existing rules. A cut is *flexible* only once it has
held for three months, and is read as *sacred* if they later restore it themselves.

*Recommended.* The alternative, never reading a plan's cuts, would ignore a choice the person made.

**E4. Repair what is already stored, shown first.**
- The 66 entries are identified by matching `income_change_applied` and the Undo: the same lines, the same old and
  new amounts, at the two times.
- They are **marked**, not deleted. The history stays as it happened (AP10); only how the Layer reads it changes.
- Rob sees the list before anything is changed.

*Recommended.*

**E5. Any later plan follows the same rule.** Future features that change budget amounts on the person's tap (item
73's purchases, a future goal plan) mark their edits the same way, and an Undo cancels its apply. *Recommended.*

**E6. Tests.**
- An applied-then-undone plan produces no readings.
- A kept plan's cut is read like a hand edit, *flexible* after three months.
- A hand edit is still read as before.
- The repair marks exactly the matched entries and nothing else.
- A plan undone after the person edited one line leaves that line's edit as theirs.

*Recommended.*
