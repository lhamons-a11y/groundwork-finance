"""Item 100 (gw 2.0/HEALTH_PAGE.md; Rob 2026-10-19: "open it, make it and I'll approve it") - the Health page - and the
Calendar as a Budget tab (Rob 2026-10-19: "lets also move Calendar as a tab to budget").

    HP1 its own page, in the sidebar under Track where the Calendar was
    HP2 four tabs, bills first
    HP3 four facts across the top, each from existing working, "—" and a plain line when the record hasn't it
    HP4 people, the plan, the reserve and the bills move from Settings, which points to the page; HSA / FSA summarised
    HP5 spending as recorded: by month, by person as said ("Not said" otherwise), the year so far; the records
    HP6 never a lever: no budget, no "over", nothing about spending less on care
    HP7 the sidebar entry can be turned off; the visibility notice stays with the people
    and the Calendar: a fourth Budget tab, every "open the Calendar" lands there
"""
import json
import re
from datetime import date, timedelta


def run(ctx):
    check, c, H, HJ, html, app = ctx.check, ctx.c, ctx.H, ctx.HJ, ctx.html_src, ctx.app_src
    from core import health_page
    from core.database import Account, CareFor, Category, Person, Transaction, db_session

    view = html[html.index('<div id="view-health" class="view">'):html.index('<!-- DEBT -->')]
    track = html[html.index('<div class="nav-section-label">Track</div>'):html.index('<div class="nav-section-label">Decide</div>')]
    check('s244 HP1 Health is in the sidebar under Track, where the Calendar was; the Calendar is not',
          'data-view="health"' in track and 'data-view="calendar"' not in html and "health: 'Health'" in app)
    check('s244 HP2 four tabs, bills first',
          view.index('id="hlTab-bills"') < view.index('id="hlTab-plan"') < view.index('id="hlTab-spending"')
          < view.index('id="hlTab-people"') and 'aria-selected="true" aria-controls="hlPanel-bills"' in view)
    check('s244 HP4 the bills, the plan, the reserve and the people live on the page; Settings points to it',
          all(f'id="{i}"' in view for i in ('medicalBillsCard', 'healthPlanCard', 'healthReserveCard', 'healthPeopleCard',
                                             'healthHsaFsa', 'healthSpending', 'healthFacts'))
          and 'id="healthPlanCard"' not in app and 'id="medicalBillsCard"' not in app
          and "showView('health');return false" in app.split('function _drawAccountManager()')[1][:2500])
    facts = app[app.index('async function _healthFacts('):app.index('function _renderHealthHsaFsa(')]
    check('s244 HP3 four facts from existing working, each saying plainly when the record hasn\'t it',
          all(t in facts for t in ("'Owed on bills'", "'Plan year'", "'Reserve'", "'HSA and FSA'", 'No plan entered',
                                   'No target set', 'No HSA or FSA account', "No bill you said is yours")))

    # HP5, on the server, with a health category, a person and a payment said to be theirs
    with db_session() as s:
        cat = Category(name='S244 Doctor', type='expense'); s.add(cat)
        acct = Account(name='S244 Checking', type='checking', is_active=True); s.add(acct)
        from core import people
        per, _problem = people.add(s, 'S244 Sam'); s.commit()       # a person the proper way (and never deleted, N1)
        t1 = Transaction(account_id=acct.id, category_id=cat.id, date=date.today().replace(day=1), description='S244 CLINIC',
                         amount=80.0, type='debit')
        t2 = Transaction(account_id=acct.id, category_id=cat.id, date=date.today().replace(day=1), description='S244 CLINIC 2',
                         amount=20.0, type='debit')
        s.add_all([t1, t2]); s.commit()
        s.add(CareFor(transaction_id=t1.id, person_id=per.id, mode='initial')); s.commit()
        ids = (cat.id, acct.id, per.id, t1.id, t2.id)
    try:
        from core import health_boundary
        health_cat = health_boundary.is_health_category('S244 Doctor')
        d = c.get('/api/accounts/health-summary', headers=H).get_json()['data']
        who = {r['who']: r['amount'] for r in d['by_person']}
        check('s244 HP5 spending as recorded: by month (twelve complete and this one), by person as said, "Not said" otherwise',
              health_cat and (who.get('S244 Sam') == 80.0 and who.get('Not said', 0) >= 20.0
                                    and len(d['months']) in (12, 13) and d['months'][-1]['so_far']
                                    and d['year_line'].startswith(f'{date.today().year} so far:')))
    finally:
        with db_session() as s:
            s.query(CareFor).filter(CareFor.transaction_id.in_(ids[3:])).delete(synchronize_session=False)
            s.query(Transaction).filter(Transaction.id.in_(ids[3:])).delete(synchronize_session=False)
            pp = s.get(Person, ids[2])
            if pp is not None:
                pp.active = False                                   # people are made inactive, never deleted (item 92 N1)
            s.query(Account).filter(Account.id == ids[1]).delete(synchronize_session=False)
            s.query(Category).filter(Category.id == ids[0]).delete(synchronize_session=False)
            s.commit()
    spend = app[app.index('async function _renderHealthSpending('):app.index('// HP7: the page in the sidebar')]
    src = (ctx.BASE / 'core' / 'health_page.py').read_text(encoding='utf-8')
    check('s244 HP5 the records open from here: the visit report and the year in review',
          "_rcOpenReport('visit_report')" in spend and "_rcOpenReport('year_end')" in spend)
    check('s244 HP6 never a lever: no budget, no "over", nothing about spending less on care - and the page says so',
          not re.search(r'\bover budget\b|\bcut\b|\breduce\b|\bspend less\b|\btoo much\b|\bbudgeted\b', spend + src + view, re.I)
          and 'never suggests spending less on care' in src and 'never judged' in view
          and 'health_rows(session)' in src and not re.search(r'logging\.|callAI|urlopen|egress', src))
    check('s244 HP7 the sidebar entry can be turned off (the page and its data stay)',
          'id="setShowHealth"' in app and "show_health_nav: on ? 'true' : 'false'" in app
          and "nav.style.display = _healthNavShown ? '' : 'none'" in app and '_applyHealthNav();' in app)

    # the Calendar, a Budget tab
    bud = html[html.index('<div id="view-budget" class="view">'):html.index('<!-- end budPanel-bills -->') + 900]
    sv = app[app.index('function showView(name) {'):app.index('function showView(name) {') + 900]
    check('s244 the Calendar is the fourth Budget tab, with its content; the old page is gone',
          bud.index('id="budTab-bills"') < bud.index('id="budTab-calendar"')
          and 'id="budPanel-calendar"' in bud and 'id="calendarContent"' in bud and 'id="view-calendar"' not in html
          and "['plan', 'futures', 'bills', 'calendar']" in app and "if (id === 'calendar') { try { renderCalendar();" in app)
    check('s244 every "open the Calendar" lands on the Budget page\'s Calendar tab',
          "if (name === 'calendar') {\n    showView('budget');\n    setTimeout(() => _budShowTab('calendar'), 50);" in sv)
