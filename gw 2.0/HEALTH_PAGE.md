# Item 100 — A Health page

Opened 2026-10-19 (Rob: *"should medical have a page so users can see their medical expenses and track it? Kinda like
the debt payoff page?"*, then *"open it, make it and I'll approve it"*). Built the same day, for Rob's approval.

## Why

Health in Groundwork is built (item 45 H7 stages 1-6, items 86-94) but scattered: people, the plan, the reserve and
the medical bills sit at the bottom of Settings → Accounts; the HSA and FSA in their account rows; the visit report
and the year in review in Reports; deductible progress only inside the plan card. Debt Payoff works because one goal
has one page.

## The points (HP1-HP8)

**HP1. Its own page.** *Health* in the sidebar under Track, after Calendar.

**HP2. Four tabs, bills first** (the Budget page's pattern): *Bills* (what you owe, each bill's working, the dates),
*Plan and reserve* (the plan year, the reserve, HSA and FSA), *Spending* (by month and by person, and the records),
*People* (whom care was for).

**HP3. Four facts across the top**, each from working that already exists: owed on bills now (bills you said are yours),
the plan's deductible as your insurer shows it, the reserve covered of its target, and HSA and FSA balances. A fact the
record doesn't have says so ("no plan entered"); none is guessed.

**HP4. The cards move, nothing is rebuilt.** People, the health plan, the reserve and the medical bills move from
Settings → Accounts to the page, with the same working and the same buttons. Settings keeps a line pointing to the page.
The HSA and FSA panels stay in their account rows (their terms live there); the page shows each one's sentence and
balance, with a link to manage it.

**HP5. Spending, as recorded.** Health money out by month (the last twelve complete months and this month so far) and
by person (as the household said, payment by payment; "not said" otherwise), and the year so far. The same test of
"health" as everywhere (`health_boundary.health_rows`: the category, or an HSA / FSA account). The records: the visit
report and the year in review, opened from here.

**HP6. Never a lever (item 89 C1).** Tracking only: no budget to beat, no "over", no trophies, nothing about spending
less on care. Bills, deadlines and the reserve have progress; care doesn't.

**HP7. Privacy.** The page says, where people are listed, that anyone who opens Groundwork on this computer can see it.
*Show Health in the sidebar* can be turned off in Settings (the page and its data stay; turning it back on brings it
back). Nothing new leaves the computer, reaches the model or the AI log, or enters an export without the health tick.

**HP8. Motion as Before You Buy's (item 99):** a tab eases in; nothing moves under reduced motion.

## Status

Opened and built 2026-10-19 (s244). For Rob's approval.
