"""Item 99 (BYB_LAYOUT.md; Rob 2026-10-19: "I will let you work magic on item 99", "Feel free to use animations also"):
Before You Buy as one flow instead of five tools. The figures and their sources are unchanged (s192, s197, s200 and
the payoff engine keep holding them); these checks hold where each piece now sits.

    L1  the question is on the page (no pop-up), first on the page
    L2  the answer shows as you type; the full cost is folded into the question, its figure usable with one tap
    L3  a financing offer is part of the question, its payment usable with one tap (only a payment read from it)
    L4  "make room" only when wanted: deciding goes straight from the question, on the real budget, built quietly
    L5  Buy it / Wait and watch / Not buying
    L6  after the purchase on its own tab: did you buy it, return windows, purchases you didn't ask about - with a count
    L7  one sentence of explanation; no first-visit note, no card pointing at a button
    and the motion respects a reduced-motion setting
"""
import re


def run(ctx):
    check, app, html = ctx.check, ctx.app_src, ctx.html_src
    view = html[html.index('<div id="view-byb" class="view">'):html.index('<div id="view-investments" class="view">')]
    check('s242 L1 the question is on the page, first, and the pop-up is gone',
          'id="bybOverlay"' not in html and 'What are you thinking of buying?' in view
          and view.index('id="bybAsk"') < view.index('id="bybContent"') and 'id="bybStep1"' in view)
    check('s242 L6 two tabs: thinking of buying, and after you buy (with what waits there counted)',
          'id="bybTab-before"' in view and 'id="bybTab-after"' in view and 'id="bybAfterCount"' in view
          and view.index('id="bybPanel-after"') < view.index('id="bybFollowUps"') < view.index('id="bybReceipts"')
          < view.index('id="bybFromRecord"'))
    check('s242 L2/L3 the full cost and the financing offer live inside the question, folded away until asked',
          'id="bybHelpCost"' in view and 'id="bybHelpOffer"' in view
          and view.index('id="bybHelpCost"') < view.index('id="bybStep2"') and 'id="bybCost"' in view and 'id="bybOffer"' in view)
    use = app[app.index('function bybUseFigure('):app.index('async function bybReadOffer(')]
    check('s242 L2/L3 a worked-out cost or an offer\'s payment becomes the monthly figure with one tap, and the answer follows',
          '_bybLiveUpdate()' in use and "g('bybMonthlyAmount')" in use
          and 'bybUseFigure(${Number(d.monthly)}' in app and 'o.payment != null && o.payment > 0' in app)
    step = app[app.index('function _bybGoStep('):app.index('// ── Type / subtype selectors')]
    check('s242 L4 deciding goes straight from the question, on the real budget built quietly (a sandbox\'s edits are kept)',
          "_bybGoStep(3)" in view and "if (n === 3 && _byb.sandboxKey !== key) { _bybBuildSandbox();" in step
          and "Doesn't fit? Make room in my budget" in view)
    check('s242 L5 the three choices say what they do',
          "Buy it — add it to my budget" in view and "Wait and watch — nothing changes yet" in view and ">Not buying it<" in view
          and "'commit'" in view and "'track'" in view and "'walkaway'" in view)
    follow = app[app.index('function _renderBYBFollowUps('):app.index('function _renderBYBFollowUps(') + 1400]
    check('s242 L6 what you chose to wait on is asked on the After tab, "Did you buy it?"',
          'Did you buy it?' in follow and '_bybResolveTracked(' in follow and "_bybAfterCount('tracked'" in follow
          and "_bybAfterCount('receipts'" in app and "_bybAfterCount('offers'" in app)
    lst = app[app.index('function _renderBYBList('):app.index('function _renderBYBFollowUps(')]
    check('s242 L7 one sentence of explanation: no first-visit note on the page, no card pointing at a button, no verdict',
          'id="fvb-byb"' not in view and 'Nothing evaluated yet' not in lst and 'openBYBWizard()' not in lst
          and 'Good call' not in app)
    css = html[html.index('@keyframes bybIn'):html.index('@keyframes bybIn') + 1400]
    check('s242 motion: steps and tabs ease in, a pulled-in figure pulses once - and none of it with reduced motion',
          '@media (prefers-reduced-motion:reduce)' in css and '.byb-in' in css and '.byb-pulse' in css
          and '_bybAnimate(el)' in step)
