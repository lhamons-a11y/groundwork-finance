# Item 38 — The paid-off marker writes a $0 net worth into history

Opened 2026-10-04 (Rob: *"Let's address the paid off snapshot bug"*). No code. This pass asks for rulings; it
authorises nothing. Found in item 35 (`INVESTMENT_VALUATION.md` §6, *seen and not fixed*).

## 1. What happens today (measured 2026-10-04, both lines, temp DB)

When the user marks a debt paid in full, `setCardPaidInFull` (`static/js/app.js`) does two things:
- calls `autoSnapshotNetWorthIfDue()`, which posts this month's real totals, `force: false`;
- then, *without waiting for it*, posts a "chart marker":
  `POST /api/net-worth/snapshot {force: false, note: "Paid off: <card>"}`, with **no assets and no liabilities**.

`create_snapshot` reads a missing figure as `0`.

| # | Measured | Result, identical on `lts/1.x` and master |
|---|---|---|
| 1 | The marker is the month's first snapshot | A snapshot of **$0 assets, $0 liabilities, $0 net worth**, noted *"Paid off: Visa"*. It also logs a `net_worth_milestone_variance` event with **actual $0**: persisted evidence that milestone confidence later reads. |
| 2 | The real snapshot arrives after it | Refused (*"Snapshot already exists"*). The month stays **$0**, and nothing on screen says so. |
| 3 | The month already has its snapshot (the usual case) | The marker is a no-op, so *"Paid off"* is never recorded. The marker almost never marks. |
| 4 | Both sent at once, as the page sends them (20 trials, two threads) | **20 of 20 wrote two rows for the same month**, one of them $0. The route checks and inserts without a lock, and `snapshot_date` has no uniqueness. |

**Downstream:**
- **The Net Worth chart** draws every row, so a payoff month shows a drop to $0, the opposite of what happened.
- **`_updateNWDelta`** compares the last two rows, so it can report the whole net worth as lost.
- **`list_snapshots`** limits by row count, so a duplicate takes the place of a real month.
- **`get_net_worth_milestone_confidence`** counts the $0 variance as a real result.

**What can be found afterwards:**
- A marker snapshot is identifiable: assets = liabilities = 0, and on master (since item 35 stored notes) the note
  *"Paid off: …"*. On 1.x before `55310dd` the note was dropped, so only the all-zero figures remain.
- Its milestone event is not identifiable for certain. The event has no month and no snapshot link, only
  `actual_value = 0`, which a real $0 net worth could also produce.

This has been in the code since the first commit (`161f30e`), so 1.0 and 1.1 users can have such rows.

## 2. Points for ruling

**P1. A payoff is a note on the month's snapshot, never a snapshot of its own.**
- The second POST is removed. `setCardPaidInFull` awaits the one auto snapshot and passes the payoff as its note.
- When the month already has its snapshot, the server appends the note to it and leaves its figures alone (a note is
  not a re-take).

*Recommended.*

**P2. A snapshot without figures is refused.**
- `create_snapshot` requires `assets` and `liabilities` as numbers. A missing one is a 400, never a 0.
- This is "absence is not zero" on the one route that writes net worth history.

*Recommended.*

**P3. One snapshot per month, enforced on the server.**
- The check and the insert happen under one lock, so two requests cannot both create the month.
- (a) A process lock in `create_snapshot`. The app is one process; no schema change.
- (b) A unique index on `snapshot_date`. That needs a SCHEMA_VERSION bump and the s51 pin, and it cannot be added while
  duplicate rows exist (P4 first).

*Recommended: (a).* It closes the race now without a migration. (b) can follow once P4's reading is settled, if Rob
wants the database itself to hold the rule.

**P4. Rows already written are never rewritten or deleted. They are read for what they are.**
- A snapshot with assets = 0 and liabilities = 0 that sits beside a real snapshot for the same month is a marker
  record, not a net worth. Readers (the chart, the delta, `list_snapshots`) skip it in favour of the real one.
- An all-zero snapshot alone in its month is kept and shown, labelled: *"recorded without figures — not a net worth."*
  The chart draws no point for it, and the delta never compares against it.
- Nothing is deleted. The rows stay as they were written.

*Recommended.* (Deleting would remove a record. Rewriting would invent figures nobody entered.)

**P5. Milestone confidence leaves out what cannot be evidence.**
- From now on, no variance is logged for a snapshot without figures (P2 makes that impossible).
- Past `net_worth_milestone_variance` events with `actual_value = 0`, logged at the moment a $0 snapshot was created,
  cannot be told for certain from a real $0.
- (a) Leave them, and say on the milestone that its confidence may include a payoff-day $0.
- (b) Leave out any $0 actual whose day also has an all-zero snapshot.
- (c) Leave them as they are, unsaid.

*Recommended: (b).* It is the only evidence-based link (same day, same all-zero figure). It is stated where it applies.
(c) is the silent version this project rules out.

**P6. Lines.** This is a correctness fix to shared code, with persisted damage on shipped 1.x. Build `lts/1.x` first,
then merge to master, with a gate on each.

*Recommended.*

## 3. Cases (for the build, if ruled)

| # | Case | Expected |
|---|---|---|
| Ps1 | Mark a card paid off, no snapshot yet this month | One snapshot, with the real totals and the note *"Paid off: Visa"* |
| Ps2 | Mark a card paid off, the month already taken | Figures unchanged; *"Paid off: Visa"* appended to its note |
| Ps3 | `POST /snapshot` without assets or liabilities | 400; nothing written; no milestone event |
| Ps4 | Two creates at once, 20 trials | Always one row for the month |
| Ps5 | An existing all-zero row beside a real one for the same month | The chart, delta and list use the real one; nothing deleted |
| Ps6 | An existing all-zero row alone in its month | Shown, labelled *"recorded without figures — not a net worth"*; no chart point; no delta against it |
| Ps7 | Milestone confidence with a $0 variance logged the same day as an all-zero snapshot | Left out, and the milestone says so |
| Ps8 | Both lines | Ps1–Ps7 on `lts/1.x` and master |

## 4. Ruling (Rob, 2026-10-04)

*"I agree with you. I accept your recommendations."*

- **P1:** the payoff is a note on the month's snapshot. The second POST is removed. On a month already taken, the note
  is appended and the figures are left alone.
- **P2:** a snapshot without `assets` and `liabilities` as numbers is refused (400).
- **P3 (a):** a process lock around the check-and-insert. No schema change.
- **P4:** existing rows are never deleted or rewritten.
  - An all-zero row beside a real one for the same month is skipped by the readers.
  - One alone in its month is shown labelled *"recorded without figures — not a net worth"*, with no chart point and
    no delta against it.
- **P5 (b):** a $0 `net_worth_milestone_variance` logged the same day as an all-zero snapshot is left out of
  confidence, and the milestone says so.
- **P6:** both lines, `lts/1.x` first, with a gate on each.

## 5. Status

OPENED and RULED 2026-10-04. No build authorised (a ruling is not an authorisation).
