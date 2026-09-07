# Before, alongside or after the last debt balance — the payoff half

**The question, scoped before anything is touched**

> Status: **OPEN. Rob's.** This document does not answer it. Written 2026-09-07 at Rob's
> request, to establish *what the three words mean in the actual consequence model, and what
> existing behaviour each choice would invalidate* — because recording a rule while leaving an
> implementation underneath that still embodies the old model is exactly what happened to
> `core/reserve.py` a day earlier.
>
> **Open Question 6 has two halves and they are separate decisions.** The data half is frozen:
> *a reserve is an allocation of an existing financial state, recorded alongside the applicable
> balance; it does not modify the historical account balance and is not itself a transaction.*
> That half changed no engine code. **This is the other half**, and it is the one design §1.4
> flagged as landing in `core/consequence.py` and affecting every user.
>
> Reproducible: `tests/payoff_option_measurement.py`.

---

## 1. Where the decision actually lands

`simulate_payoff`'s monthly loop, in one shape:

```text
extra = budget − minimums
   ├── one_time_cost draws first        money that never reaches the debt
   └── the remainder goes to `order`    avalanche by rate, or snowball by balance
```

**A reserve contribution is structurally identical to `one_time_cost`**: money drawn from
`extra` that never reaches principal. The only difference is that it recurs until the target is
met. So all three words are answers to a single mechanical question — **does the reserve draw
from `extra`, and when?**

| | means, in the loop |
|---|---|
| **before** | the reserve takes the whole of `extra` until the target is met; principal resumes after |
| **alongside** | `extra` is split between reserve and principal every month |
| **after** | the reserve is funded from capacity that exists once the balances are gone — **not a change to this loop at all** |

The codebase already half-anticipates this. `extra_above_minimums`'s docstring names this pool
as *"the money that actually reduces principal … so it is also the pool a save-first plan saves
out of."* Saving out of this pool is a shape the engine has already had to describe.

## 2. What each would invalidate — measured, not argued

Against the recorded `green_light` contract (55 user-like states, the baseline that exists
precisely to answer this class of question) and the solution engine, on 2026-09-07:

| Option | Recorded states that change | One-time-cost gap | Honest paths offered |
|---|---|---|---|
| **after** | **0 of 55** (0%) | 4 months | 3 |
| **alongside** | 15 of 55 (27%) | 7 months | 4 |
| **before** | 23 of 55 (42%) | 9 months | **1** |

*(Same portfolio throughout: two cards, $775 budget, a $2,400 one-time cost, a $6,000 target.)*

**The last column is the one to look at.** Under *before*, the solution engine goes from three
honest paths to one. §6.4's honest-no would fire far more often — not because the engine got
more careful, but because there is much less left to offer. A reserve that consumes the whole
lever pool removes most of what Pillar 3 exists to say.

## 3. The constraint that outranks the measurements

**The payoff math exists twice.** `core/consequence.py` and `_simulatePayoffStrategy` in
`static/js/app.js:12517`. `tests/test_consequence_parity.py` holds them to agreement *to the
month* against the live JS extracted at runtime — 32 checks, passing today.

So *before* and *alongside* are not engine changes. They are **product changes to a shipped LTS
line, landing in two implementations**, and the parity harness will refuse either one until
both move together. `after` touches neither.

## 4. The asymmetry, stated carefully

Only *after* is free. **That is not an argument for it.** A free option that gives the wrong
advice is still the wrong advice, and §1.4's whole point is that *optimal payoff and
never-needing-the-card are not the same objective* — the engine models only the first, which
is precisely why the cheap option is cheap. What the measurement changes is that the price of
the other two is now a number instead of an intuition.

## 5. What the measurement does not settle

Three things it cannot, and they are the actual decision:

- **Whether a household with an empty reserve and one card left is better served by clearing
  the card or filling the reserve.** That is a judgement about *risk* — a $1,400 emergency-room
  bill landing on a cleared card and undoing a year — and the engine measures months, not
  exposure. No amount of contract-state counting speaks to it.
- **`alongside` needs a split ratio, and there is no uninvented one.** This is the "three to six
  months of expenses" problem returning: §1.4 rejected an invented number for the *target* and
  would have to accept one for the *rate*. Unless the ratio derives from something real, it is
  the same defect in a new place.
- **Whether this belongs in the engine at all**, rather than in the solution engine as a
  **lever the user chooses** — which would make it a path among paths, ranked and costed like
  every other, instead of a global change to how every user's payoff is computed.

That third one is worth weighing before the first two, because it changes what the question is.

## 6. If it is ever *before* or *alongside* — the audit list

Named now, so the frozen-rule failure is not repeated in the other direction. Each of these
currently embodies "every spare dollar goes to principal":

- `core/consequence.py`'s allocation loop, and `_simulatePayoffStrategy` in `app.js`, together
- `tests/test_consequence_parity.py` — 32 checks, both implementations
- `tests/green_light_contract.json` — re-recording requires a `CONTRACT_VERSION` bump and a
  written reason, which is the mechanism working as intended rather than an obstacle
- `core/solution.py`'s levers, which price against `extra_above_minimums`
- `extra_above_minimums`'s own docstring, which describes the pool

## 7. The requirement this produces

The decision is not finished when the position is chosen. Stated in the form it has to be
carried out (Rob, 2026-09-07):

> **The reserve/payoff treatment must be resolved relative to the final debt balance before
> `core/consequence.py` is modified. Once the position is chosen, audit the existing
> consequence calculations against that rule and identify every calculation whose ordering or
> baseline changes.**

The deliverable is not *we decided what the system means*. It is *the system now actually means
that* — which is the lesson `core/reserve.py` supplied a day earlier, where the correct rule sat
above an implementation that still embodied the old model.

### The audit, prepared in advance

`tests/payoff_option_measurement.py` performs it. Run it once a position is chosen and the list
of calculations to re-examine is its output rather than a fresh reading of the engine. Measured
2026-09-07, against a representative portfolio:

| Position | Engine-consuming calculations that change |
|---|---|
| **after** | **0 of 15** |
| **alongside** | 12 of 15 |
| **before** | 12 of 15 |

```text
consequence.simulate_payoff · decision_impact · affordable_one_time
              · affordable_monthly · offsetting_monthly_delta
solution.solve_one_time_cost · save_first_plan · do_nothing_note
              · solve_monthly_cost · accelerations · past_charge_lesson · green_light
```

**Two caveats, so 12 of 15 is not read as authoritative.** `extra_above_minimums` shows as
unchanged only because the perturbation models the draw *inside* `simulate_payoff`; a real
implementation redefines the pool itself, so it moves too — and being the pool definition, it
moves **first**. And `budget_pressure` and `capacity_unlocked` are unchanged *for this
portfolio*, which is not the same as unable to change; both consume the engine.

**Deliberately absent from the inventory**, because none of them reaches the engine and so none
can move: `_prepare`, `_month_key`, `is_protected`, `_headroom`, `_trims`, `_overspend`,
`fund_pace`, `decision_memory`. The absence is part of the inventory rather than an omission
from it.

**Outside this process entirely**, and changed by any position but *after*:
`_simulatePayoffStrategy` in `static/js/app.js`, `tests/test_consequence_parity.py`, and
`tests/green_light_contract.json` — the last re-recorded under a version bump and a written
reason, which is that mechanism working rather than an obstacle.

## 8. Not decided here

Deliberately. The measurements above are inputs to the decision, and a document that slid from
*here is what each costs* to *therefore choose this* would be making a risk judgement that is
not its to make — and dressing it as arithmetic, which is worse.

**And the lever option is a fourth position, not a reframing to admire.** If the reserve is a
path the user chooses in the solution engine rather than a global property of payoff, the
audit above returns nothing: the default computation does not move, so parity holds and the
LTS blast radius disappears. That is a claim this instrument can check the moment the position
is taken seriously, and it should be checked rather than reasoned about.
