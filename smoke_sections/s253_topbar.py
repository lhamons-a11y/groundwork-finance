"""The top bar (Rob 2026-10-22): the date, the Ask bar, Explain and ? - nothing else.

    Reports is in the menu, Report a problem in the ? help, Backup in Settings
    the Ask bar is a white pill that springs open when clicked (Dynamic Island), and closes again
    while it is open, the date beside it is the time above the date, as Windows shows its clock
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
          and 'cubic-bezier(.34,1.56,.64,1)' in html and '#gwAskBox{transition:none}' in html
          and 'onfocus="_topbarClock(true)" onblur="_topbarClock(false)"' in bar)
    tick = app.split('function _topbarClockTick() {')[1].split('\n}\n')[0]
    check('s253 while the Ask bar is open, the time sits above the date (10:57am over 10/22/2026); closed, the date',
          "classList.add('gw-clock')" in tick and '<b>${time}</b><span>${day}</span>' in tick
          and "weekday: 'short'" in tick and 'setInterval(_topbarClockTick, 10000);' in app)
