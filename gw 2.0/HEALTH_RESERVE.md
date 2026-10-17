# Item 88 — The health reserve (item 45 H7 stage 3)

**OPENED 2026-10-16 (Rob: "Continue"; the next stage in H7's ruled order). RULED 2026-10-16 (Rob: "I approve", on R1-R9 as
recommended); build not yet authorised.**

## Summary

The health reserve is money set aside in an account you already have, so that a bad medical year doesn't put a
credit card back to work. Its natural size comes from your own plan: the out-of-pocket maximum is the most a covered
year can cost, and item 87 now holds that figure. The record layer exists. `core/reserve.py` and two tables keep a
target and an allocation, and the allocation is a *level* of a balance (Rob's frozen rule of 2026-09-07), not money
moving. Nothing calls them yet.

One question has been open since September, design Q9. Should freed money fill the reserve before the last debt is
paid, alongside it, or after? Whichever is chosen changes the payoff plan, so it touches every user. The
recommendation here (R1) is that **Groundwork doesn't choose**. You pick, Groundwork shows what each choice does in
your own numbers (the debt-free date, the interest, the date the reserve is full), and nothing changes for anyone
until they pick. That follows your rulings of 2026-10-14: the user decides, no one-size rules, no judgement. It works
with AI off and is master only.

## 1. What is there today (measured on master `54e5062`)

- **`core/reserve.py`**, specified by `tests/test_reserve_fixture.py` and checked by s90:
  - a target with a basis (`oop_max`, `custom` or `historical`), superseded and never overwritten, the OOP figure
    resolved on read and never copied;
  - an allocation as a level with history;
  - no contribute or withdraw by design.

  It keeps its state in memory, with tables `reserve_targets` and `reserve_allocations` already in the schema.
  Nothing calls it.
- **`core/consequence.py`** `simulate_payoff` already takes an `extra_schedule` (item 61's trips), a per-month
  change to the money going to debt. That is all "alongside" or "before" needs, so the engine needs no new idea.
- **`core/solution.py`** keeps a one-month floor of your own recorded expenses before it will suggest paying debt
  from savings (C.5). This item doesn't change that floor.
- **Item 87** holds the plan's out-of-pocket maximum. **Item 86** holds the HSA balance.

## 2. Points for ruling

**R1. You choose when the reserve fills; Groundwork shows each choice and picks none.** Three options:
- *after* the last debt, which is how the engine works today;
- *before* it: freed money goes to the reserve until it's full, then to debt;
- *alongside* it: an amount you set each month goes to the reserve, the rest to debt.

Each option shows, from your own record:
- the debt-free date;
- the total interest;
- the date the reserve would be full.

Groundwork shows no "best", "recommended" or "smart" label. Until you choose, the payoff plan is exactly as it is
today, for every user. Choosing writes your choice down with its date, and you can change it any time.
*Recommended.*

**R2. The target is the plan's out-of-pocket maximum, or your own figure, never an invented one.**
- With a current plan from item 87, the target is that plan's maximum, read from the plan and never copied (so a
  corrected maximum moves the target).
- Without one, you can type a figure, labelled as yours.
- Without either, there is no target, and the card says so.
- Groundwork never suggests "three to six months of expenses".
- `reserve.py`'s `historical` basis (past health spending) is left out of this stage. Past spending isn't a promise
  about next year.

*Recommended.*

**R3. The reserve is a level of a balance in an account you name, never a movement.** You pick the account (a
savings account, say) and say how much of its balance is the reserve. The account's balance never changes. The card
shows *reserved* and *available = balance − reserved*, worked out as you look and stored nowhere. Saying $700 after
$500 means $700, not $1,200. If the account's balance falls below the reserved level, the card says so as a fact,
and never quietly lowers the reserve. *Recommended.*

**R4. An HSA balance counts toward the reserve, shown on its own line.** HSA money is for qualified care, so it
covers part of the target. The card shows *"HSA $1,240 + reserved in Savings $800 = $1,775 of $8,000"*. It never
moves or locks the HSA. FSA money is left out, because it can expire. *Recommended*; the other choice is to keep
them separate.

**R5. How "before" and "alongside" reach the engine.** Through the existing `extra_schedule`. For the months until
the reserve is full, the money to debt drops by the reserve amount, and after that it returns. "Before" uses all the
freed money above the minimums; "alongside" uses your amount. Minimum payments are never touched, so no card is ever
paid late because of the reserve. The months to full are worked out from what is reserved today. *Recommended.*

**R6. Using the reserve is your act.** When a health bill is paid from it, you lower the reserved level, or
Groundwork offers to when it sees a health payment from that account, only on your yes. Nothing lowers it on its
own. *Recommended.*

**R7. Privacy.** A reserve is money: an amount in an account, like a savings goal. It names no person, medication or
diagnosis, so it stays ordinary money under H6. The word "health" in its name is the only health signal, and it says
nothing about anyone's condition. *Recommended.*

**R8. Where it shows.** The reserve's state (target, HSA, reserved, available) goes on the Health plan card from
item 87. The R1 choice, with its three sets of dates, goes on the Debt Payoff page, because that is the plan it
changes. *Recommended.*

**R9. Words.** The card explains what the reserve is for in one plain line: *"Money set aside so a medical bill can
be paid without a card."* It never says how much anyone should have. *Recommended.*

## 3. Left out of this stage, on purpose

- **The reserve for things other than health** (car, home): it would use the same machinery, but it's its own item.
- **The `historical` target basis:** see R2.
- **A Needs attention item when the reserve is low:** none, unless you want one.
- **The visit report and year in review (stage 4), named people (5), the bill that lands (6) and collections (7).**
- **The 1.x line:** master only.

## 4. How it would be built and proven, once authorised

1. A storage layer keeping `reserve.py`'s rules over its two tables. If an account column is needed, that means a
   `SCHEMA_VERSION` bump and pin.
2. `core/health_reserve.py`: the target from item 87, the HSA line from item 86, available worked out on read, and
   the R1 comparison through `simulate_payoff` with an `extra_schedule`.
3. The card lines, and the Debt Payoff choice.

A new smoke section would check:
- with no choice made, every user's payoff plan is identical to today's (a regression pin on the engine output);
- the three options' dates come from the same engine;
- minimums are never reduced;
- a corrected out-of-pocket maximum moves the target;
- $500 then $700 is $700;
- a balance below the reserved level is named;
- no "best", "recommended" or "should" wording appears.

## Closing

The before / alongside / after question is the kind of choice you said yesterday belongs to the user. R1 builds it
that way: three sets of dates from the user's own numbers, and Groundwork's own payoff plan unchanged until they
choose. The rest connects pieces already built, ruled and tested.
