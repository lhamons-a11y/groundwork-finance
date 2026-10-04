"""No template text in static HTML (gw 2.0/HELP_ICON_LABEL.md, item 36; Rob 2026-10-04: "I accept all three
recommendations" / authorised).

static/index.html is never run as a JavaScript template, so a `${...}` written in it is printed to the user as text -
the Net Worth 401(k) label showed "${helpIcon('retirement_account')}" from the first commit until this pass.
    H1  the label carries the icon as the markup helpIcon() produces, opening its explanation
    H2  any `${` in index.html outside a <script> block fails the gate
"""
import re


def raw_templates(html):
    """Positions of `${` in the HTML outside <script> blocks - the only place it can be printed raw."""
    body = re.sub(r'<script\b.*?</script>', lambda m: ' ' * len(m.group(0)), html, flags=re.S | re.I)
    return [m.start() for m in re.finditer(r'\$\{', body)]


def run(ctx):
    check, html, app = ctx.check, ctx.html_src, ctx.app_src
    found = raw_templates(html)
    check('s147 H2 static/index.html has no ${ outside a <script> block (it would be printed as text)',
          found == [] or print('        at', [html.count('\n', 0, i) + 1 for i in found]))
    check('s147 H2 the guard catches one put back (the check can fail)',
          raw_templates(html.replace('</body>', "<label>X ${helpIcon('x')}</label></body>", 1)) != []
          and raw_templates("<script>const a = `${b}`;</script>") == [])
    label = re.search(r'<label>401\(k\) / 403\(b\) \(\$\)(.*?)</label>', html)
    check('s147 H1 the 401(k) label carries the help icon itself, opening the retirement-account explanation',
          bool(label) and "class=\"help-icon\" onclick=\"showHelp('retirement_account',this)\"" in label.group(1)
          and '${' not in label.group(1))
    m = re.search(r'function helpIcon\(topic\) \{\s*return `(.*?)`;', app, re.S)
    check('s147 H1 it is exactly what helpIcon() would produce, and the topic it opens exists',
          bool(m) and label and m.group(1).replace('${topic}', 'retirement_account') == label.group(1).strip()
          and re.search(r'\n\s*retirement_account: \{', app) is not None)
