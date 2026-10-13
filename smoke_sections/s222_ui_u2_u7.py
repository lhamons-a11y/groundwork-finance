"""Item 79 U2-U7 (gw 2.0/UI_AUDIT.md; Rob 2026-10-13: "I agree with the UI proposals u2-u8"). Only where things sit
changes: every figure keeps its working and its source, and nothing is removed.

    U2  each debt is one line that opens on a tap; a debt just added opens; paid in full at the end, under Paid off (n)
    U3  the Calendar's next four weeks open; the rest folded by month into one line each
    U4  the AI gate's statistics are one line in Settings, the table on a tap
    U5  Needs attention: stale imports are one row; conclusions blocked by the one Verify step are one row
    U6  one rule for a recurring charge, shared by the Budget card and the Calendar
    U7  one heading style for every card
"""
from datetime import date, timedelta


def run(ctx):
    check = ctx.check
    app, html = ctx.app_src, ctx.html_src
    dash = (ctx.BASE / 'static/js/teaching/dashboard.js').read_text(encoding='utf-8')

    row = app.split('function _debtCardRowHTML(c, opts={}) {')[1]
    lst = app.split('function _renderCardList() {')[1].split('\n}\n')[0]
    check('s222 U2 each debt starts as its one-line summary (with APR and minimum), opens on a tap, opens when just added; paid off at the end',
          'let _openCards = new Set();' in app and 'if (!_openCards.has(c.id)) {' in row and '_collapsedCards' not in app
          and '% APR' in row.split('// ── Expanded')[0] and ' min' in row.split('// ── Expanded')[0]
          and 'if (!_dbId) _openCards.add(id);' in app
          and 'Paid off (${paid.length})' in lst and lst.index('owed.map') < lst.index('paid.map'))

    cal = app.split('async function renderCalendar() {')[1].split('\n}\n')[0]
    check('s222 U3 the Calendar: four weeks open, week by week; the rest folded by month into one line with its count and total',
          'fourWeeks.setDate(fourWeeks.getDate() + 28)' in cal and '<details class="card mb-4">' in cal
          and "gp.rows.length} date" in cal and "'Rest of '" in cal)

    check('s222 U4 the AI gate statistics are one line under AI features, the table one tap away',
          '<details class="card mb-4"' in html and 'id="gateHealthSummary"' in html and 'id="gateHealthPanel"' in html
          and 'held back before you saw' in app)

    grp = dash.split('function _groupedHTML(items) {')[1].split('\n  }\n')[0]
    check('s222 U5 Needs attention groups what repeats - stale imports, and conclusions answered by the one Verify step - and keeps each item and its Dismiss',
          "accounts</strong> haven\\'t been imported" in grp and 'Which ones' in grp and 'One step answers all of them' in grp
          and 'data-gw-dismiss="' in grp and "_groupedHTML(items)" in dash and 'data-gw-dismiss-all' in dash)

    from core import upcoming
    from core.database import Category, Transaction, db_session
    today = date.today()
    with db_session() as s:
        debt = s.query(Category).filter_by(name='Debt').first()
        if not debt:
            debt = Category(name='Debt'); s.add(debt); s.flush()
        for k in range(1, 5):
            d = today - timedelta(days=30 * k)
            s.add(Transaction(date=d, amount=19.99, type='debit', merchant='S222 STREAMER', description='S222 STREAMER'))
            s.add(Transaction(date=d, amount=150.00, type='debit', merchant='S222 LOAN', description='S222 LOAN', category_id=debt.id))
        s.commit()
        try:
            names = {r['merchant'] for r in upcoming.recurring_charges(s, today, include_budgeted=True)}
            cal_titles = {e['title'] for e in upcoming.entries(s, today, today + timedelta(days=60)) if e['kind'] == 'charge'}
        finally:
            s.query(Transaction).filter(Transaction.merchant.in_(['S222 STREAMER', 'S222 LOAN'])).delete(synchronize_session=False)
            s.commit()
    card = app.split('async function renderSubscriptionAudit() {')[1].split('\n}\n')[0]
    check('s222 U6 one rule for a recurring charge: the Budget card and the Calendar read the same function; a debt payment is not a recurring charge (its due day is on the calendar already)',
          'S222 STREAMER' in names and 'S222 LOAN' not in names and 'S222 STREAMER' in cal_titles
          and "API.get('/api/calendar/recurring')" in card and 'subscriptionCandidates' not in card
          and "showView('calendar')" in card)

    check('s222 U7 one heading style: the cards that had their own now use the card label',
          '<div class="card-label" style="margin:0">Positions</div>' in html
          and 'class="card-label" style="margin-bottom:6px" id="debtHeroEyebrow"' in html
          and '<div class="card-label nw-label"' in html and '<div class="card-label" style="margin-bottom:6px">Your money story so far</div>' in app)
