# Item 102 — Ask, as a real assistant

**RULED 2026-10-19 by Rob:** *"the ask how to is not useful at all. Rather its using Ai or not. It needs a overhaul or
removed. Lets try real assistant and if the user selects no AI it goes away."* And: *"Also in that item add update help
file."* This supersedes item 72's C1 (no model for how-to answers) and the AI-off audit's F6 for the Ask box.

## What it does (A1-A5)

**A1. AI help, or nothing.** The Ask box shows only while AI is on and able to run. With AI off it is gone; the ? button's
guide - the same answers - is always there, and the record checks stay one tap away ("Check my records").

**A2. Answers in its own words, from the guide only.** The few guide entries closest to the question (keywords, with
other ways of saying the same thing) go to the local model with the question. It answers in two to four sentences, using
only those entries, naming the one it used; or says the guide doesn't cover it. The answer shows which guide entry it
came from (with that entry's own words a tap away) and "Open it for me" where the entry has one.

**A3. Checked before it is shown.** An answer that names no entry, refuses, or carries a number not in its entry is not
shown; the closest guide answers are, in the guide's own words, with "Browse the whole guide". The question goes to the
person's own unanswered list, as before.

**A4. "Why" questions** (a figure looks off) still go to Groundwork's fixed checks; the AI only names one (item 72 C2).

**A5. The help is current.** The guide covers what changed on 2026-10-19 - the Health page, medical bills,
collections, the Calendar and Gifts as Budget tabs, Before You Buy's new flow, the new-vendor question - and deleting a
transaction, which the first real-model test showed was missing. The website's knowledge base matches (a Health article,
the Budget tabs, the new Before You Buy, Ask). "Open it for me" opens the right tab on the Health page too.

**A6. "View" means the page** (Rob 2026-10-19: *"when someone say's view they ... want the page now what the page does.
when someone ask a direct question the help guide should know they are asking a direct question"*). "View the calendar",
"see my budget" (Rob: "lets make see as the another word for view"), "show me collections", "open settings", "take me to my budget", "go to the month tracker" open that page and tab
straight away, with no answer to read - about thirty pages and tabs, by their names and everyday words for them. A
direct question ("how do I...", "where is...", "show me how to...") is a question, and is answered (A2). Checked in the
browser on 14 phrases: every page phrase landed on its page and tab, and the two questions were left to be answered.

## Measured

On Rob's M2 with the shipped model (Phi-3.5, on Metal), real questions in loose wording ("how do i put my bank stuff
in", "where did the calendar go", "my hospital bill went to a collection agency", "can i get rid of a transaction",
"how do i add my doctor bill"): each answered from the right entry, citing it, in 1.4-4.0 s; "what is the meaning of
life" was declined. The model sometimes appends "NOT IN GUIDE" after a cited answer; that tail is dropped, a bare refusal
is not. In the browser (the model stood in): the answer and its source, "Open it for me" to Health → Bills with the
card outlined, an invented figure caught and replaced by the closest guide answers, and the AI-off path.

## Status

Ruled and built 2026-10-19 (s246; s193, s198, s217 and s240 updated to the ruling).
