# Item 77 — Text you can read: contrast everywhere

Opened 2026-10-11. Rob, on the AI analysis card: *"we need better contrasting on the bottom its very hard to read
against that green."* That one card was fixed (a `--note` colour, #475569, about 7:1; commit 19954b8). Then: *"open
an item to fix the contrast everywhere."*

**Points K1–K8 for ruling. No code yet.**

## 1. What is true today (measured 2026-10-11, master)

Contrast of each text colour on each background colour, by the WCAG formula. The standard for normal-size text is
**4.5:1**; text at least 18.7px bold or 24px needs **3:1**.

| text \ background | paper (white) | mist | mist-2 | pine-bg (green) | ember-bg (red) | gold-bg (yellow) | sky-bg (blue) | steel |
|---|---|---|---|---|---|---|---|---|
| ink | 18.9 | 18.1 | 17.1 | 18.1 | 17.3 | 18.3 | 17.4 | 15.4 |
| ink-2 | 15.4 | 14.7 | 14.0 | 14.7 | 14.1 | 14.9 | 14.2 | 12.5 |
| slate | **4.76** | **4.55** | 4.31 | **4.55** | 4.35 | **4.59** | 4.37 | 3.86 |
| slate-2 | 2.56 | 2.45 | 2.32 | 2.45 | 2.34 | 2.47 | 2.36 | 2.08 |
| pine (green) | 3.30 | 3.15 | 2.98 | 3.15 | 3.01 | 3.18 | 3.03 | 2.67 |
| ember (red) | **4.83** | **4.62** | 4.37 | **4.61** | 4.41 | **4.66** | 4.44 | 3.92 |
| gold | 3.19 | 3.04 | 2.88 | 3.04 | 2.91 | 3.07 | 2.93 | 2.58 |
| sky (blue) | **5.17** | **4.94** | **4.68** | **4.94** | **4.72** | **4.98** | **4.75** | 4.19 |

Bold cells pass 4.5:1. What that means:

- **`--slate-2` fails on every background (2.1–2.6:1).** It is the text colour in about **455** places: notes, sources,
  dates, "what this shows", small print. This is the main problem, and what Rob saw.
- **`--pine` and `--gold` fail as text on every background (2.6–3.3:1).** They are used for text in about **170** and
  **36** places: green amounts, "✓" lines, warning text. They pass 3:1 only for large text, and not on steel.
- **`--slate` and `--ember` are borderline.** They pass on white and the light tints, and fail on mist-2, the red and
  blue tints and steel. Used about **635** and **103** times.
- **`--ink`, `--ink-2` and `--sky` pass** everywhere except `--sky` on steel.
- About **21** places hard-code `#92400e` (the amber warning text), and **10** hard-code `#94a3b8` (the same value as
  `--slate-2`), outside the tokens.
- **There is no dark theme today**, so only these light backgrounds matter.
- **Nothing checks contrast.** A new colour, or a new background, can fail without anyone knowing.

## 2. Points for ruling

**K1. The standard.**
- WCAG 2.1 AA: **4.5:1** for normal text and **3:1** for large text (at least 18.7px bold or 24px).
- 3:1 for the parts of a control that show it can be used: borders of inputs and buttons, focus rings, icons that are
  the only label.
- Decorative lines, dividers and disabled controls are exempt.

*Recommended.*

**K2. Fix the tokens, not 1,400 places one by one.** Change each failing token's value so it passes on every background it's
used on. One edit then fixes every use, and the look stays recognisably Groundwork.
- `--slate-2` (#94a3b8) → about **#5b6576**: at least 4.77:1 on all eight backgrounds.
- `--slate` (#64748b) → about **#526073**: at least 5.19:1 on all eight.
- `--pine` as text: a deeper green, about **#166534**: at least 5.78:1 on all eight. The bright green stays for
  fills, bars and borders.
- `--gold` as text: an amber, about **#854d0e**: at least 5.56:1 on all eight. The bright gold stays for fills and
  borders.
- `--ember` as text: about **#b91c1c**: at least 5.25:1 on all eight.

Every value above was computed against all eight backgrounds, not chosen by eye. Each is shown to Rob before and
after on real pages.

*Recommended.*

**K3. Separate text colours from fill colours where one token does both.** `--pine`, `--gold`, `--sky` and `--ember`
colour both text and bars, dots and borders. A deeper text shade beside the bright fill keeps charts and badges as
they are while making the words readable. Add `--pine-text`, `--gold-text` and `--ember-text`, used wherever the
colour is on words.

*Recommended.*

**K4. Bring hard-coded colours into the tokens.** The 21 `#92400e` and 10 `#94a3b8` literals, and any other
hard-coded text colour, become tokens, so K2's fix reaches them.

*Recommended.*

**K5. Steel and the darkest tints.** Light grey text never sits on `--steel`. Where it does today (tags, chips,
disabled-looking rows), the text moves to `--ink-2`, or the background to a lighter one.

*Recommended.*

**K6. A test that keeps it fixed.**
- A smoke section computes every text token against every background token it may sit on, and fails below K1's
  threshold.
- A static scan fails on any new hard-coded text colour outside the tokens.

The check is on the colour pairs the app defines, not on every element, so it is quick and always runs.

*Recommended.*

**K7. Seen on real pages before it's accepted.** The dashboard, Budget, Ledger, Before You Buy, Debt, the Ask and
Why? panels and the AI analysis card, each shown before and after on a copy of Rob's data, with screenshots. Any
place a colour change hurts meaning (a red that no longer reads as a warning) is fixed before acceptance.

*Recommended.*

**K8. Order, master only.**
1. K6's test, written first so it shows today's failures.
2. K2 and K3, the tokens.
3. K4 and K5.
4. K7's look.

One build, one gate. Today's `--note` (#475569) folds into the new `--slate`.

*Recommended.*

## 3. Not decided here

- **A dark theme.** Not proposed. If it comes, it gets its own pass with K6's test extended to its backgrounds.
- **Larger default text size.** Most small print is 11–12px. Contrast is the fix asked for; size is a separate
  question.
