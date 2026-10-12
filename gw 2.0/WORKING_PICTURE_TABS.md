# Item 78 — The working picture, in tabs

Opened 2026-10-11. Rob: *"working picture is looking a little too busy. Should we tab the sections out to keep the
pages cleaner?"* On the tabs proposed: *"I agree with those tabs."*

**T1–T6 RULED 2026-10-11 by agreement (Rob: "I agree with those tabs"). BUILT 2026-10-11 (Rob: "build 78"), awaiting acceptance; §3.**

## 1. What is true today (2026-10-11, master a2c89f3)

The working picture (Coach → Working picture, `static/js/teaching/willingness.js`) stacks up to nine sections on one
page:

1. a question about something the person said (contradictions);
2. the strategy after a short month;
3. income (item 71);
4. what the record shows, with Dispute and Protect;
5. what the person has told Groundwork;
6. everything they have said, in order (folded);
7. how Groundwork concludes;
8. their rhythm (item 58 E8);
9. the evidence-library findings.

## 2. The points (as agreed)

**T1. Four tabs:**
- **Needs you:** anything asking for the person's answer, meaning the contradiction questions, the strategy question
  and income;
- **What your record shows:** the readings, with their evidence and controls;
- **What you've said:** the current statements, plus the full history;
- **Research and rhythm:** the evidence-library findings and the rhythm.

**T2. A question is never buried.** The page opens on *Needs you* when anything is waiting there, and otherwise on
*What your record shows*.

**T3. A plain count.** *Needs you (2)* is a plain number: no red badge, no pulse, no motion (TM6). With nothing
waiting, it shows no count.

**T4. "How Groundwork concludes" becomes one line** at the top, opening the explanation in place, instead of a card
on every visit.

**T5. Same tabs as the Assistant page.** The same keyboard-reachable tab bar (`role="tablist"`) and smooth panel
change as item 69's amendment. The chosen tab is remembered for the session only, never as a usage signal (AP3).

**T6. Nothing is lost.** Every control and every piece of text stays; only its place changes. The empty state stays as
it is. s129's checks keep passing, and a test proves each section still renders in its tab.


## 3. Built (2026-10-11)

- `_pictureHTML` now draws a tab bar and four panels in place of the stack. Each panel holds exactly the cards it
  stacked before, with their text and controls unchanged.
- **Needs you** holds the contradiction questions, the strategy card and the income card, with a plain count when
  any are there.
- The page opens on *Needs you* if anything waits there; otherwise on *What your record shows*.
- The chosen tab lives in memory for the session. Switching fetches, stores and counts nothing.
- *How Groundwork reaches these conclusions* is one line that opens in place.
- The empty state is unchanged. The evidence and rhythm render inside *Research and rhythm*, or below the empty state
  as before.
- s129's empty-state check now ends where the tabs begin.
- **Tests:** s202 checks T1–T6.
- **Seen in the page** on a copy of Rob's data, with no page errors:
  - nothing was waiting, so it opened on *What your record shows*;
  - switching to *Research and rhythm* showed only that panel, with the rhythm line.
- **Found while looking (not changed here):** *What your record shows* lists about 33 readings of the form "you
  lowered its budget … then set it back … Groundwork reads it as something you keep". They all come from one tap of
  *Make this my budget* on the false income card (2026-10-10) and its Undo the same day. An Undo is not 33
  decisions. This needs its own ruling (the Willingness Layer's edit history).
