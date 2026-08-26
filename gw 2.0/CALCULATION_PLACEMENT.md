# Calculation Placement — where the money math lives

**A design note for the 1.x → 2.0 transition**

> Status: **Decided, with named open questions.** Written 2026-08-26 against the real 1.1
> codebase, after a session that fixed four calculation bugs in one afternoon.
> Companion to `GW_2.0_TEACHING_PLATFORM_BLUEPRINT.md` — this note constrains where that
> document's consequence engine can live.

---

## The question

Should Groundwork's calculations move into a calculation engine, or stay built into the code
as they are today — knowing the software is expected to expand into a teaching platform and,
eventually, an assistant?

## The decision

**No general calculation engine. Yes to migrating claim-backing derivations to Python,
incrementally, as each is next touched.**

Two rules do the work:

1. **Name the concept.** Duplication is not the disease; anonymity is. A calculation with a
   name and a stated contract can be reused; one without a name gets retyped and drifts.
2. **Split by claim, not by math.** If a number is used to tell the user something is true,
   it belongs where it can be tested and logged. If it only draws a screen, leave it alone.

---

## Why not an engine — the argument that nearly went the other way

The obvious reading of the August 2026 bugs is "the math is scattered, centralize it." That
reading is wrong, and checking it is what changed the conclusion.

Transfer-inflated spending had to be fixed in four places (`generateReport`,
`updateReportPreview`, `_rcMonthlyGenerate`, `_rcUpdateAnnualSummary`). Searching for the same
defect server-side turns up raw `sum(... if t.type == 'credit')` at `server.py:875` and
`server.py:973` — no transfer filter.

**Those are correct.** They compute `total_credits` / `total_debits` for account balance
reconciliation, where a transfer genuinely *is* money moving in or out of that account.

So there is no single "spent." There are several correct calculations that share a name:

| Context | Does a transfer count? | Why |
|---|---|---|
| Account balance | **Yes** | The money really did leave the account |
| Budget comparison | **No** | `income` comes from the budget profile; nothing offsets an inflated `spent` |
| Annual savings rate | **No**, both sides | Transfers largely cancel in the total but inflate the denominator |

A canonical `spent()` applied uniformly would have broken balance math in order to fix budget
math — converting two right answers and one wrong answer into one right answer and two wrong
ones. **An engine that flattens this distinction manufactures bugs at the sites that were
already correct.**

What actually fixed the four-place bug was naming the predicate — `_isSpend`, `_isEarn`, and
27 call sites agreeing on it, each carrying a comment explaining what it excludes and why.
The naming *was* the architecture. No framework was required, and one would not have helped.

---

## The real structural problem: the language boundary

The problem is not engine-vs-inline. It is that the most consequential arithmetic lives where
it cannot be tested.

| Measure | Value |
|---|---|
| `static/js/app.js` | **26,264 lines** — dashboard, reports, claim confidence, priority |
| Sites filtering transactions in the client | **75** |
| `server.py` | 6,949 lines, **39** reader functions (a de-facto engine already) |
| Smoke checks asserting on `app.js` **source text** | **43** |

That last row is the tell. Because the suite cannot execute client math, it greps for strings —
`'gift_advisor'`, `_bybResolveTracked` — and calls that coverage. All four bugs fixed on
2026-08-26 lived in code the suite "covered" this way, and every one of them survived a green
run. The streak that was structurally always `0` (`S.sbState` has no write path anywhere in the
app) sat there through every deploy the gate ever approved.

A test that asserts a function *name* appears in a file cannot notice that the function returns
a constant.

---

## Why 2.0 forces the move anyway

Three things, none of them cleanliness:

1. **The blueprint already specifies it.** "Consequence engine — one deterministic core,"
   unifying the math that exists separately in BYB, the trip planner, and debt projection.
2. **A second consumer is coming.** The assistant needs the same numbers, and neither the
   teaching layer nor the assistant can call into `app.js`.
3. **The receipts principle demands one code path.** From the claim-confidence fix:
   *"A gate that measures something the arithmetic doesn't see is not a gate."* The income gate
   had been recognising a paycheck by its description while the cash-flow engine skipped it for
   its category — so a month of payroll filed under "Transfer" read as both present and absent
   at once. Proof-not-persuasion holds only when the claim and the number come from the same
   place. That is an argument for consolidating **gate + derivation**, not for a general engine.

One objection that does *not* apply: latency. `server.py` runs on localhost inside the desktop
app. Moving a derivation across the wire costs a function call, not a network round trip.

---

## The rule

**Split by whether the calculation produces a claim.**

| Move to Python | Leave in JS |
|---|---|
| Anything used to assert something is true | Rendering math — formatting, chart layout, per-row display |
| Streak, claim confidence, current priority, what-changed, cash-flow verdicts | Anything consumed by exactly one screen and never quoted |
| Anything the historian should log | Anything whose wrongness is visible at a glance |
| Anything the assistant will need | |

**Migration candidates, in rough order** — each moves when it is next touched anyway, never as
a big-bang rewrite:

1. `_streakFromData` — a server sibling already exists (`get_engagement_streak`); the client
   copy is the duplication that today's fix should retire.
2. `_computeClaimConfidence` — the gate; highest value, because it is what licenses every
   other claim.
3. `_computeCurrentPriority` — already encodes the completeness floor; belongs next to the
   historian that can log why it fired.
4. `_computeWhatChanged` — stamps rows "Confirmed," the highest claim tier.
5. Report aggregates — lowest value, move last or never.

---

## Explicitly not doing

- **No engine abstraction or framework.** Named functions with explicit contracts, not a
  registry, a rule DSL, or a pipeline.
- **No shared `spent()`** spanning balance and budget contexts. See the table above.
- **No big-bang migration.** Anything moved without a reason to touch it is speculative work.
- **No moving rendering math.** It is fine where it is and always was.

## The stopping rule

If a calculation is used by exactly one screen and never appears in a claim, inline is correct
and moving it is waste. If it ever backs a statement to the user, it belongs where it can be
tested and where the historian can log it.

---

## Open

- **The offline snapshot path.** `buildSnapshot` / `_restoreFromSnapshot` let the client run
  without a live server. Moving a derivation server-side raises the question of what those
  screens show when it is unreachable. **A client mirror is the wrong answer** — a second
  implementation of the same concept is precisely the duplication that caused the four-place
  transfer bug. The likely answer is to degrade to showing nothing, consistent with the
  no-fabrication rule, but which derivations need that treatment is unresolved.
- **Where the consequence engine lives relative to `historian/`.** The historian protocol
  (branch `historian-a7a`) is domain-agnostic and currently unwired. Whether the consequence
  engine sits above it, beside it, or is the thing that finally wires it is undecided.
- **How to test derivations during the move.** Once a calculation is in Python, `smoke_test.py`
  can exercise behavior instead of grepping source. The 43 existing source-text checks should
  be retired as their subjects move — but retiring them early would remove the only signal
  those surfaces have.

---

## Provenance

Written after the 2026-08-26 session, which fixed: a streak that was structurally always zero,
transfer inflation across four report surfaces, an income gate that tested existence rather
than coverage, and a cash-flow priority that read blank months as a shortfall. All four shared
one root cause — a missing record treated as a measured zero — and none was catchable by the
suite as it stands. The conclusions above are drawn from those four, not from general
architecture principle.
