"""Item 78 (gw 2.0/WORKING_PICTURE_TABS.md T1-T6, RULED 2026-10-11 by agreement; Rob: "build 78").

    T1  four tabs: Needs you, What your record shows, What you've said, Research and rhythm
    T2  opens on Needs you when anything waits there
    T3  a plain count on Needs you - no badge, no motion
    T4  how Groundwork concludes is one line that opens in place
    T5  the open tab is kept for the session only - never stored, never read as a signal; switching fetches nothing
    T6  every section keeps its text and controls in its tab; the empty state is unchanged
"""
import re


def run(ctx):
    check = ctx.check
    js = (ctx.BASE / 'static/js/teaching/willingness.js').read_text(encoding='utf-8')
    body = js.split('// Item 78 (WORKING_PICTURE_TABS.md')[1].split('\n  }\n')[0]

    check('T1 four tabs, in order, as a keyboard-reachable tab bar',
          all(x in body for x in ("['needs', 'Needs you'", "['record', 'What your record shows']", "['said', 'What you\\'ve said']",
                                  "['research', 'Research and rhythm']"))
          and 'role="tablist"' in body and 'role="tab"' in body and 'role="tabpanel"' in body and 'aria-selected' in body)
    check('T2 a question is never buried: the page opens on Needs you whenever anything waits there',
          "_tab = needs.length ? 'needs' : 'record'" in body and "(_tab === 'needs' && !needs.length)" in body)
    check('T3 the count is a plain number - no badge colour, no animation',
          "(needs.length ? ' (' + needs.length + ')' : '')" in body
          and not re.search(r'animation|@keyframes|pulse|var\(--ember\)|badge', body))
    check('T4 how Groundwork concludes is one line that opens in place, not a card on every visit',
          'How Groundwork reaches these conclusions' in body and '<details' in body
          and "out + '<div class=\"card mt-5\">' + how" not in js)
    handler = js.split("ev.target.closest('[data-gw-wtab]')")[1].split('\n  });')[0]
    check('T5 the open tab is held in memory for the session only: nothing stored, nothing fetched or counted on a switch',
          not re.search(r'localStorage|sessionStorage|API\.(get|post)|_gwFetch|fetch\(', handler)
          and not re.search(r'localStorage|sessionStorage', js) and 'var _tab = null;' in js)
    sections = {
        'needs': ('A question about what you said', 'needs.push(strat)', 'needs.push(inc)'),
        'record': ('What your record shows</div>', '_claimControls(r)'),
        'said': ('What you have told Groundwork', '_statementControls(d)', 'Everything you have said, in order'),
        'research': ('id="evidenceWillingness"',),
    }
    missing = [s for k, v in sections.items() for s in v if s not in body]
    check(f'T6 every section keeps its text and controls, each in its tab ({missing or "all present"})',
          not missing and "panel('needs', needs.join" in body and "panel('record', record" in body
          and "panel('said', saidHtml" in body and "panel('research'," in body)
    check('T6 the empty state is unchanged and the evidence still renders when it shows',
          'Groundwork has not drawn any conclusions about you yet.' in js
          and "html + '<div id=\"evidenceWillingness\"" in js and "renderEvidence('willingness', g('evidenceWillingness'))" in js)
