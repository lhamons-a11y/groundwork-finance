"""Item 79 U1 (gw 2.0/UI_AUDIT.md; Rob 2026-10-12: "I accept u1"): the Budget page in three tabs.

    Your budget (opens first) / Possible futures / Bills and charges - every card kept, only where it sits changes
    a link to a card inside a tab opens that tab first (the guide's "Open it for me", the what-if shortcuts)
    something waiting on the person is a plain count on its tab
"""
import re


def run(ctx):
    check = ctx.check
    html, app = ctx.html_src, ctx.app_src
    view = html.split('<div id="view-budget" class="view">')[1].split('<!-- end budPanel-bills -->')[0]
    panel = lambda pid: view.split(f'<div id="budPanel-{pid}"')[1].split('<div id="budPanel-')[0]
    plan, fut, bills = panel('plan'), panel('futures'), panel('bills')
    check('s219 U1 three tabs, the budget first and shown; the other two hidden until chosen',
          view.index('id="budTab-plan"') < view.index('id="budTab-futures"') < view.index('id="budTab-bills"')
          and 'aria-selected="true" aria-controls="budPanel-plan"' in view
          and 'id="budPanel-futures" role="tabpanel" aria-labelledby="budTab-futures" style="display:none"' in view
          and 'id="budPanel-bills" role="tabpanel" aria-labelledby="budTab-bills" style="display:none"' in view)
    check('s219 U1 every card kept, each in its tab: the plan, the futures, the bills and charges',
          all(f'id="{i}"' in plan for i in ('budgetIncomeChange', 'budgetTripsMonth', 'budgetContent'))
          and 'id="budgetFutures"' in fut
          and all(f'id="{i}"' in bills for i in ('budgetBillsCard', 'budgetPriceChanges', 'subscriptionAuditCard', 'sinkingFundsCard')))
    # inside the view: the tab bar and the three panels, the last closed just before the end-of-panel comment
    check("s219 U1 the page's markup still closes every box it opens",
          len(re.findall(r'<div\b', view)) == view.count('</div>'))
    help_fn = app.split('function helpOpen(open) {')[1].split('\n}\n')[0]
    check('s219 U1 a link to a card opens its tab first: the guide, and the what-if shortcuts',
          '_budReveal(open.el && g(open.el));' in help_fn and help_fn.index('_budReveal(') < help_fn.index('scrollIntoView')
          and "_budShowTab('futures');" in app.split('function openWhatIf(preset) {')[1].split('\n}\n')[0]
          and "el.closest('[id^=\"budPanel-\"]')" in app)
    pc = app.split('async function renderPriceChanges() {')[1].split('\n}\n')[0]
    check('s219 U1 a price change waiting for a tap is a plain count on Bills and charges - no badge, no motion',
          "_budTabCount('bills', _priceChanges.filter(c => c.line && !c.line_matches).length, 'price');" in pc
          and "b.textContent = n ? `${base} (${n})` : base;" in app)
