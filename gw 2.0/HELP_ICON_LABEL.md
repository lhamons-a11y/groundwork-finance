# Item 36 — A help icon printed as raw template text

Opened 2026-10-03 (Rob: *"open the raw ${helpIcon(...)} text"*). No code. This pass asks for rulings; it authorises
nothing.

## 1. What happens today (measured 2026-10-03, both lines)

- **On the Net Worth page,** under *Update balances*, the 401(k) field's label reads *"401(K) / 403(B) ($)
  ${HELPICON('RETIREMENT_ACCOUNT')}"*. It was seen during item 35's browser check.
- **The cause.** `static/index.html` holds `${helpIcon('retirement_account')}` inside a plain `<label>`. Static HTML is
  never run as a JavaScript template, so the expression is printed as text (upper-cased by the label style).
  - `lts/1.x`: line 1933. master: line 1945.
  - It is in the first commit (`161f30e`, 2026-07-24), so 1.0 and 1.1 shipped with it.
- **The intended icon exists.** `helpIcon(topic)` in `app.js` returns
  `<span class="help-icon" onclick="showHelp('retirement_account',this)" title="What is this?">i</span>`, and
  `HELP_TOPICS.retirement_account` is defined. The icon was meant to open that explanation, and never has.
- **It is the only one.** A scan of `index.html` outside `<script>` blocks finds no other `${`, on either line.
- **Nothing in the gate looks for this.**

## 2. Points for ruling

**H1. Write the icon as the markup `helpIcon` would produce.** Put the `<span class="help-icon" …>i</span>` itself in the
label, so the 401(k) field gets the help icon and explanation it was written to have. The label text is unchanged.

*Recommended.* (The alternative, deleting the expression, would remove an explanation that already exists.)

**H2. A guard, so it cannot come back.** A gate check fails if `static/index.html` contains `${` outside a `<script>`
block. That is the only place such text can be printed raw.

*Recommended.*

**H3. Both lines, `lts/1.x` first.** It is a visible defect in shipped 1.x. Build on `lts/1.x`, merge to master, with a
gate on each.

*Recommended.*

## 3. Cases (for the build, if ruled)

| # | Case | Expected |
|---|---|---|
| Hi1 | The Net Worth page, 401(k) field | The label reads *401(k) / 403(b) ($)* followed by the ⓘ icon; no raw text |
| Hi2 | Click the icon | The retirement-account explanation opens (`HELP_TOPICS.retirement_account`) |
| Hi3 | The guard | It finds no `${` outside scripts. Adding one back makes the check fail. |
| Hi4 | Both lines | Hi1–Hi3 on `lts/1.x` and master |

## 4. Status

OPENED 2026-10-03. Ruling sought on H1–H3. No build authorised.
