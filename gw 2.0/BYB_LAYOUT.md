# Item 99 — Before You Buy, one flow instead of five tools

Opened 2026-10-19 (Rob: *"the layout needs improvement, its all over the place ... I like the tools you added but I
feel that it all should flow better together it just seemed crammed and post purchase wizard just doesn't make any
logic"*). **No code.** Measured on master `3f5b467` in the browser, empty and with a test purchase.

## 1. What the page is today, top to bottom

1. **A title**, then **a blue note that repeats the title** ("Before You Buy - Thinking about a purchase?...").
2. **Trials and return windows**: paste a receipt or confirmation; its dates go on the dashboard.
3. **The full cost, and financing**: a car / phone / yearly-charge calculator (five boxes), then, in the same card,
   "paste a financing offer".
4. **From your records** (when there are any): purchases that *already happened* without coming through here,
   "shown as if you had asked first" - I meant to / I'll cancel it / Dismiss.
5. **The decisions list** (Committed / Tracking / Walked away), or, when empty, *"Nothing evaluated yet"* with the
   page's main button, **Evaluate a purchase →**, at the very bottom.
6. That button opens **a four-step pop-up wizard**: what and how much → adjust the whole budget → comparison →
   Commit / Track / Walk away → "Decision saved". A tracked item later asks "Decide on X: bought / walked away, what
   it actually cost".

## 2. Why it feels crammed and illogical

- **F1. The main thing is last.** The page's purpose, "should I buy this?", is a button under two side tools.
- **F2. Before and after are mixed.** Return windows, "from your records" and "did you buy it?" are all *after* the
  purchase, on a page named *before*. That is the "post-purchase" part that doesn't make sense here.
- **F3. The same question is asked in three places.** The wizard, the full-cost calculator and the financing reader
  each take a price on their own and give separate answers that never meet. A car's insurance and fuel (full cost)
  never reach the wizard's budget; a financing offer's real payment never becomes the wizard's monthly figure.
- **F4. A pop-up for the core decision.** The answer lives in a modal you must step through; the page behind it
  shows nothing of what you decided.
- **F5. Step 2 asks too much.** "Adjust your budget to make room" puts every budget line in front of you before you
  have seen the answer. Most people want the answer first, then "make room" only if it doesn't fit.
- **F6. Repeated words.** The title, the blue note and the empty card say the same thing three times.

## 3. Proposal, for ruling (L1-L7)

**L1. One question at the top, on the page (no pop-up).** "What are you thinking of buying?" - a name, a price, and
how you'd pay: *all at once*, *monthly*, or *over time (financed)*. A car, a phone plan and a yearly charge are kinds
you can pick, which reveal their few extra boxes (insurance, miles, registration...).

**L2. The answer appears right under it, in one card, as you type.** Three lines, from the one engine as today:
what's left each month (now → with it), the debt-free date (now → with it), and any goal it moves. Below, *"what
it's made of"*: the monthly cost with each part and its source (today's full-cost calculator, folded in).

**L3. Financing becomes part of the question, not a separate tool.** Choosing *over time* offers "paste the offer";
the rate, term, payment and any deferred-interest catch are read into the same answer (every figure still must be in
the offer).

**L4. "Make room" only when it's needed.** If it doesn't fit, a button *Make room in my budget* opens today's
sandbox and *Make It Work* cuts, inline. If it fits, nothing to adjust.

**L5. Three plain choices at the end of the answer:** *Buy it* (adds it to your budget, as Commit does now), *Wait
and watch* (Track), *Not buying* (Walk away). The page then shows it in **Your decisions**, below.

**L6. Everything after the purchase moves to one "After you buy" tab** on the same page (the Budget page's tab
pattern, item 79 U1): **Return windows and trials** (the receipt reader), **Purchases you didn't ask about**
(today's "from your records"), and **Did you buy it?** (tracked items waiting for an answer). The first tab, *Before
you buy*, holds only L1-L5 and Your decisions. The tab shows a count when something waits.

**L7. One sentence of explanation, once.** The blue note goes; the title's subtitle carries the purpose. The empty
state is the question itself (L1), not a card pointing to a button.

## 4. What does not change

The figures and their sources: the one payoff engine, the full-cost parts, the financing reader's rule that every
figure must be in the offer, the receipt reader, the records offers and their answers, and what Commit / Track /
Walk away save. This is layout and flow; s192, s199, s200, s201 and the BYB checks keep holding the numbers, and
each moved piece gets a check that it is where L1-L7 put it.

## 5. Status

Opened 2026-10-19, no code. For Rob's ruling on L1-L7.
