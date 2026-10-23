"""The top bar (Rob 2026-10-22): the date, the Ask bar, Explain and ? - nothing else.

    Reports is in the menu, Report a problem in the ? help, Backup in Settings
    the Ask bar is a white pill that springs open when clicked (Dynamic Island), and closes again
    the date beside it stays the date while the Ask bar is open - no clock appears (Rob: "remove the clock")
"""


def run(ctx):
    check, html, app = ctx.check, ctx.html_src, ctx.app_src
    bar = html.split('<div class="topbar-right">')[1].split('\n    </div>\n')[0]
    check('s253 the top bar keeps the date, the Ask bar, Explain and ? - Report, Reports and Backup are gone from it',
          'id="topbarDate"' in bar and 'id="gwAskBox"' in bar and 'explainPage()' in bar and 'showHelpOverlay()' in bar
          and 'openFeedbackModal()' not in bar and "showView('reports')" not in bar and 'openBackupModal()' not in bar)
    check('s253 each is still one step away: Reports in the menu, Report a problem in the ? help, Backup in Settings',
          "showView('reports')" in html.split('class="sidebar-nav"')[1]
          and 'openFeedbackModal()' in app.split('function _renderHelpFaq(filter) {')[1].split('\n}\n')[0]
          and 'openBackupModal();' in app)
    check('s253 the Ask bar is a white pill that springs open on a click and closes on leaving, motion off when asked',
          '#gwAskBox{' in html and 'border-radius:999px' in html and '#gwAskBox:focus{width:460px' in html
          and 'cubic-bezier(.34,1.56,.64,1)' in html and '#gwAskBox{transition:none}' in html)
    check('s253 the date stays the date while the Ask bar is open: no clock, nothing on focus or leaving (Rob: "remove the clock")',
          '_topbarClock' not in app and '_topbarClock' not in html and 'gw-clock' not in html and 'gw-clock' not in app
          and "setText('topbarDate', new Date().toLocaleDateString('en-US',{weekday:'short',month:'short',day:'numeric',year:'numeric'}));" in app)
