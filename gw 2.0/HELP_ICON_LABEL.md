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

## 4. Ruling (Rob, 2026-10-04)

*"I accept all three recommendations."*

- **H1:** the label carries the icon as the markup `helpIcon` produces, opening `HELP_TOPICS.retirement_account`.
- **H2:** a gate check fails on any `${` in `static/index.html` outside a `<script>` block.
- **H3:** both lines, `lts/1.x` first, then merged to master, with a gate on each.

## 5. Status

OPENED 2026-10-03. RULED 2026-10-04. AUTHORISED 2026-10-04 (Rob: *"I do authorize item 38 build"* — read as item 36,
the only build then awaiting authorisation; there is no item 38). BUILT on both lines. Awaiting acceptance.

## 6. Built (2026-10-04): `lts/1.x` `bfaa8fa` (gate 974 / 0), then master (gate 2372 / 0)

- **H1.** The label now reads `401(k) / 403(b) ($) <span class="help-icon" onclick="showHelp('retirement_account',this)"
  title="What is this?">i</span>`, exactly what `helpIcon('retirement_account')` returns.
  - **In the browser (1.x):** the label shows the ⓘ icon, and clicking it opens *"401(k) / 403(b) retirement accounts —
    Employer-sponsored retirement accounts with pre-tax contributions …"*.
- **H2.** s147 fails the gate on any `${` in `static/index.html` outside a `<script>` block.
  - It finds none now.
  - Run against the file as it was, it reports line 1933.
  - It also proves the check can fail: a template put back is caught, and one inside a script is not.
- **H3.** Built on 1.x first, then merged to master. Each line passed its gate.
