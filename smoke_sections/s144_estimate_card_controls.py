"""The estimate cards' controls (Rob 2026-10-03): "we are not giving the user full control. we should also offer do
not follow and hide the card" - and hiding "doesn't assume the user is not wanting to track it but maybe due to season
they don't see a need to view it".

    choice   follow / do not follow, each an explicit answer; never chosen is None - not read as "do not follow",
             though until they choose the saved amount sets the totals
    hidden   a VIEW choice only: the card keeps its follow choice and lag; a followed, hidden estimate still sets this
             month's budget, and the hidden line on the Budget page says so, with Show to bring it back
    route    each field changes only when sent; the saved amount is never touched, nothing is logged
"""
import json
import shutil
import subprocess


def run(ctx):
    check, c, HJ = ctx.check, ctx.c, ctx.HJ
    import server
    from core import household
    from core.database import AppSetting, BudgetItem, HistorianEntry, HouseholdFact

    def post(**body):
        return c.post('/api/budget/utility-estimate/optin', headers=HJ, data=json.dumps({'kind': 'propane', **body}))

    def prefs():
        with ctx.dbs() as s:
            return (server._dashboard_json(s, 'utility_estimates', {}) or {}).get('propane') or {}

    def card():
        return (c.get('/api/budget/utility-estimate/propane', headers=HJ).get_json() or {}).get('data') or {}

    real = server.delivered_estimate
    with ctx.dbs() as s:
        for k in household.FACTS:
            s.query(HouseholdFact).filter_by(key=k).delete()
            s.query(AppSetting).filter_by(key=k).delete()
        p = server._dashboard_json(s, 'utility_estimates', {}) or {}
        p.pop('propane', None)
        server._dashboard_store(s, 'utility_estimates', p)
        item = BudgetItem(name='S144 Propane', category='Propane', amount=150.0, type='expense', is_active=True)
        s.add(item)
        s.commit()
        item_id = item.id
        amounts = sorted((b.id, b.amount) for b in s.query(BudgetItem).all())
        logged = s.query(HistorianEntry).count()
    try:
        server.delivered_estimate = lambda session, fuel, fetch=True, today=None: {
            'kind': fuel, 'fuel': fuel, 'lag': 0, 'optin': False, 'bills': 4, 'saved_amount': 150.0, 'region': {},
            'area': {}, 'choice': {'method': 'weather'}, 'estimate': {'method': 'weather', 'amount': 123.45, 'current': True}}
        d0 = card()
        check('s144 never chosen: no choice is assumed (None, not "do not follow") and the card is shown',
              d0.get('follow') is None and d0.get('hidden') is False)
        with ctx.dbs() as s:
            m0 = server.budget_month_amounts(s)[item_id]
        check('s144 never chosen: the saved amount sets the totals until they choose', m0['month_source'] == 'saved'
              and m0['month_amount'] == 150.0)

        r1 = post(choice='follow', lag=0)
        with ctx.dbs() as s:
            m1 = server.budget_month_amounts(s)[item_id]
        check('s144 follow: chosen, and this month\'s row uses the estimate',
              r1.status_code == 200 and prefs().get('choice') == 'follow' and prefs().get('on') is True
              and m1['month_source'] == 'estimate' and m1['month_amount'] == 123.45)

        r2 = post(hidden=True)
        d2 = card()
        with ctx.dbs() as s:
            m2 = server.budget_month_amounts(s)[item_id]
        check('s144 hide: a view choice only - the follow choice and lag are kept, and the budget still uses the estimate',
              r2.status_code == 200 and prefs() == {'on': True, 'lag': 0, 'choice': 'follow', 'hidden': True}
              and d2.get('hidden') is True and d2.get('follow') == 'follow' and d2.get('choice') == {'method': 'weather'} and m2['month_source'] == 'estimate'
              and d2.get('budget_uses', {}).get('in_totals') is True)

        post(choice='not_follow')
        d3 = card()
        with ctx.dbs() as s:
            m3 = server.budget_month_amounts(s)[item_id]
        check('s144 do not follow: an explicit answer, the saved amount sets the totals, and the card stays hidden',
              prefs().get('choice') == 'not_follow' and prefs().get('on') is False and prefs().get('hidden') is True
              and d3.get('follow') == 'not_follow' and m3['month_source'] == 'saved')

        post(hidden=False)
        check('s144 show: the card comes back with its choice unchanged',
              prefs().get('hidden') is False and prefs().get('choice') == 'not_follow' and card().get('hidden') is False)
        post(on=True)
        check('s144 an earlier page\'s on: true is the same choice as follow (and on: false as do not follow)',
              prefs().get('choice') == 'follow' and (post(on=False) and prefs().get('choice') == 'not_follow'))
        bad = [post(choice='maybe').status_code, post(hidden='yes').status_code, post(lag=5).status_code,
               post(lag=True).status_code]
        check('s144 a choice, hidden or lag outside its values is refused', bad == [400, 400, 400, 400])
        with ctx.dbs() as s:
            household.set_household_fact(s, 'heating_fuel', 'natural_gas', 'settings')
            s.commit()
        post(hidden=True)
        na = card()
        check('s144 a card the household\'s answer settled can be hidden too', na.get('not_applicable') and na.get('hidden') is True)
        # Rob 2026-10-03: a household that moves must be able to change the decision its new situation made stale.
        post(hidden=False, choice='follow')
        st = card()
        with ctx.dbs() as s:
            ms = server.budget_month_amounts(s)[item_id]
        check('s144 moved (natural gas now heats the home): the estimate no longer applies, the old follow is still '
              'reported as theirs - not changed for them - and the saved amount sets the budget',
              st.get('not_applicable') and st.get('follow') == 'follow' and ms['month_source'] == 'saved'
              and prefs().get('choice') == 'follow')
        post(choice='not_follow')
        with ctx.dbs() as s:
            mu = server.budget_month_amounts(s)[item_id]
        check('s144 ...and they can stop following it from that card: no longer followed, and the row note goes',
              card().get('follow') == 'not_follow' and mu['kind'] is None and mu['month_why'] is None)
        with ctx.dbs() as s:
            check('s144 none of it touches a saved amount or logs anything',
                  sorted((b.id, b.amount) for b in s.query(BudgetItem).all()) == amounts
                  and s.query(HistorianEntry).count() == logged)
    finally:
        server.delivered_estimate = real
        with ctx.dbs() as s:
            for k in household.FACTS:
                s.query(HouseholdFact).filter_by(key=k).delete()
                s.query(AppSetting).filter_by(key=k).delete()
            p = server._dashboard_json(s, 'utility_estimates', {}) or {}
            p.pop('propane', None)
            server._dashboard_store(s, 'utility_estimates', p)
            s.query(BudgetItem).filter_by(id=item_id).delete()
            s.commit()

    ut = ctx.BASE.joinpath('static/js/teaching/utility.js').read_text(encoding='utf-8')
    check('s144 the card offers Follow this estimate, Do not follow, and Hide this card - and no lone checkbox',
          "radio('follow', 'Follow this estimate') + radio('not_follow', 'Do not follow')" in ut
          and 'Hide this card' in ut and 'type="checkbox" data-gw-util-optin' not in ut)
    check('s144 a hidden card is listed on the Budget page with Show, and a followed one says what the budget uses',
          "host.id = 'gwHiddenEstimates'" in ut and 'data-gw-util-show' in ut
          and "followed; this month\\u2019s budget uses it" in ut and "followed; this month\\u2019s budget uses your saved amount" in ut)
    check('s144 the page sends only the field changed (hiding never resends the choice)',
          "patch.choice = dr.follow" in ut and "_save(kind, { hidden: t.hasAttribute('data-gw-util-hide') })" in ut)
    # Rob 2026-10-03: "we do need to add a submit button ... That would be the user decision to hit the submit button."
    change = ut[ut.index("document.addEventListener('change'"):ut.index("document.addEventListener('click'")]
    check('s144 picking a choice or a billing month saves nothing: only Submit sends it',
          '_save(' not in change and 'API.post' not in change and 'data-gw-util-submit' in ut
          and "class=\"btn btn-primary btn-sm\" data-gw-util-submit" in ut)
    check('s144 Submit starts disabled, is enabled only when the draft differs from what is saved, and the card says a '
          'choice is waiting', 'data-gw-util-submit data-kind="\' + k.kind + \'" disabled>Submit' in ut
          and 'btn.disabled = !changed' in ut and 'press Submit to keep this choice' in ut)
    na_js = ut[ut.index('    if (d.not_applicable) {'):ut.index('    var card = g(k.id);')]
    check('s144 a ruled-out estimate still followed from before shows the choice and Submit, and says so',
          "var stale = d.follow === 'follow';" in na_js and 'You still follow this estimate from before.' in na_js
          and "radio('not_follow', 'Do not follow')" in na_js and 'data-gw-util-submit' in na_js
          and 'Saved: you no longer follow this estimate.' in na_js)
    check('s144 hiding stays immediate - no Submit needed to hide or show a card',
          "// hiding is a view choice: immediate" in ut)

    node = shutil.which('node')
    check('s144 node is available to run the words (skip the next if not)', bool(node))
    if not node:
        return
    path = str(ctx.BASE.joinpath('static/js/teaching/utilitytext.js')).replace('\\', '/')
    base = {'fuel': 'propane', 'region': {'state': 'OH', 'national': False, 'division_name': 'the East North Central'},
            'area': {'kind': 'state'}, 'saved_amount': 150, 'optin': False, 'budget_uses': {'in_totals': False},
            'choice': {'method': 'none', 'reason': 'too_few', 'n': 1},
            'estimate': {'method': 'none', 'reason': 'too_few', 'current': True}}
    prog = f"""
const U = require({json.dumps(path)});
const F = {{money: n => '$' + Number(n).toFixed(2), month: m => m, date: s => s}};
const b = {json.dumps(base)};
console.log(JSON.stringify({{none: U.propane(b, F).lines, no: U.propane(Object.assign({{}}, b, {{follow: 'not_follow'}}), F).lines}}));
"""
    rr = subprocess.run([node, '-e', prog], capture_output=True, text=True, encoding='utf-8', timeout=30)
    try:
        o = json.loads(rr.stdout.strip().splitlines()[-1])
    except Exception:                                   # noqa: BLE001 - reported below
        o = {}
        print('        node:', rr.stderr[:300])
    check('s144 never chosen: the card says the saved amount sets the totals, and how to follow',
          any('Your saved Propane budget of $150.00 sets the budget totals. Follow this estimate' in l for l in o.get('none', [])))
    check('s144 do not follow: the card says it was their choice, and what sets the totals',
          any(l == 'You chose not to follow this estimate: your saved Propane budget of $150.00 sets the budget totals.'
              for l in o.get('no', [])))
