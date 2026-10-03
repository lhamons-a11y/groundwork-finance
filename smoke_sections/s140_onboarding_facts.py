"""The onboarding revisit, steps 4-8 (ONBOARDING_REVISIT.md, item 30; Rob 2026-10-02).

O7 is a hard acceptance criterion: "every onboarding question must have at least one documented consumer, and every
consumer must identify which answer supplies its value". So the matrix is checked both ways, here, against the code:

    question (a data-gw-fact field, or a Settings field)  ->  a fact in core/household.py FACTS
    FACTS[key]['consumers'] (file, name)                  ->  that code exists AND reads that fact

and it is proved able to fail. The rest: the intent question is gone (O2); unanswered pay frequency is not "monthly"
(O6); item 26 follows what the household said (step 7); the words say why or what was assumed.
"""
import ast
import json
import re
import shutil
import subprocess


def run(ctx):
    check, BASE, c, H, HJ = ctx.check, ctx.BASE, ctx.c, ctx.H, ctx.HJ
    import server
    from core import household
    from core.database import AppSetting, HouseholdFact

    html = ctx.html_src
    app = ctx.app_src
    hh_js = BASE.joinpath('static/js/teaching/household.js').read_text(encoding='utf-8')
    server_src = ctx.server_src
    stree = ast.parse(server_src)

    # ── O7: the matrix, both ways ─────────────────────────────────────────────
    def asked_keys(html_text, js_text):
        keys = set(re.findall(r'data-gw-fact="([a-z_]+)"', html_text))
        q_block = js_text[js_text.index('var Q = {'):js_text.index('var FUEL')]
        keys |= set(re.findall(r'^\s{4}([a-z_]+): \{ asks:', q_block, re.M))
        if 'id="settingsHomeState"' in html_text:
            keys.add('home_state')
        if 'id="settingsPayFrequency"' in html_text:
            keys.add('pay_frequency')
        if "key: 'surplus_goal'" in app:
            keys.add('surplus_goal')
        return keys

    def code_of(path, name):
        text = BASE.joinpath(path).read_text(encoding='utf-8')
        if path.endswith('.py'):
            for n in ast.walk(ast.parse(text)):
                if isinstance(n, ast.FunctionDef) and n.name == name:
                    return ast.get_source_segment(text, n)
            return None
        if '.' in name:                                    # an expression consumer: the whole file reads it
            return text if name in text else None
        m = re.search(r'function ' + re.escape(name) + r'\s*\(', text)
        if not m:
            return None
        return text[m.start():m.start() + 4000]

    def matrix(facts, asked):
        problems = []
        for key in asked:
            if key not in facts:
                problems.append(f'a question asks {key!r}, which is not a household fact')
        for key, f in facts.items():
            if key not in asked:
                problems.append(f'{key} is a fact nothing asks')
            if not f['consumers']:
                problems.append(f'{key} has no consumer')
            for path, name, _what in f['consumers']:
                code = code_of(path, name)
                if code is None:
                    problems.append(f'{key}: consumer {path}:{name} does not exist')
                elif key not in code and not (name.startswith('S.') and key == 'pay_frequency' and 'pay_frequency' in code):
                    problems.append(f'{key}: consumer {path}:{name} does not read it')
        return problems

    asked = asked_keys(html, hh_js)
    problems = matrix(household.FACTS, asked)
    check('s140 O7 the matrix holds both ways: every question sets a fact, every fact is asked, and every consumer '
          'exists and reads its fact', not problems)
    for p in problems[:8]:
        print(f'        {p}')
    print('        matrix: ' + '; '.join(f"{k} -> " + ', '.join(n for _p, n, _w in f['consumers'])
                                         for k, f in household.FACTS.items()))
    fake = dict(household.FACTS, roof_type={'asks': 'x', 'values': ('flat',), 'lines': '2.0',
                                            'consumers': [('server.py', 'roof_engine', 'nothing')]})
    check('s140 O7 mutation caught: a fact whose consumer does not exist', bool(matrix(fake, asked | {'roof_type'})))
    check('s140 O7 mutation caught: a question that sets no fact',
          bool(matrix(household.FACTS, asked | {'favourite_colour'})))
    unread = dict(household.FACTS, vehicle_fuel=dict(household.FACTS['vehicle_fuel'],
                                                     consumers=[('server.py', 'gas_estimate', 'wrong reader')]))
    check('s140 O7 mutation caught: a consumer that does not read the fact it claims', bool(matrix(unread, asked)))

    # ── O2: the intent question is gone ──────────────────────────────────────
    check('s140 O2 "What brought you here today?" is gone: no screen, no handler, nothing stored',
          'obStepIntent' not in html and 'What brought you here' not in html
          and 'onboarding_intent' not in app and 'obSetIntent' not in app and '_OB_INTENT_COPY' not in app)
    check('s140 O2 after the AI choice onboarding goes straight to how to start',
          re.search(r"function _obFinishCapabilityStep\(\) \{\s*g\('obStepAICapability'\)\?\.classList\.add\('hidden'\);"
                    r"\s*g\('obStep0'\)\?\.classList\.remove\('hidden'\);", app) is not None)

    # ── O1 / O6: the order, skipping, unanswered ─────────────────────────────
    check('s140 O1 the home screen sits between income and the bills',
          html.index('id="obStep1"') < html.index('id="obStepHome"') < html.index('id="obStep2"')
          and '_obShowHome();' in app and "if (step === 2) {" in app)
    check('s140 O6 every onboarding fact can be skipped: each select starts with "Skip for now" (blank)',
          all(re.search(r'data-gw-fact="' + k + r'"[^>]*>\s*<option value="">Skip for now</option>', html)
              for k in re.findall(r'data-gw-fact="([a-z_]+)"', html))
          and "'<option value=\"\">Skip for now</option>'" in hh_js)
    check('s140 O6 a skipped field sends nothing (and nothing is assumed in its place)',
          "if (!f.value && !(key in _obAnswers)) continue;" in app)
    check("s140 O6 an unanswered pay frequency is unanswered, not 'monthly'",
          "payFrequency || 'monthly'" not in app and "pay_frequency    || 'monthly'" not in app
          and "payFrequency:   'monthly'" not in app)
    check('s140 O5 onboarding answers go through the one write path, with source onboarding',
          "API.post('/api/settings/household', { key, value: f.value || null, source: 'onboarding' })" in app
          and "{ key: 'surplus_goal', value: goal, source: 'onboarding' }" in app
          and 'surplus_goal: goal })' not in app)

    # ── O3: the priority's reader, no verdict ────────────────────────────────
    fn = app[app.index('function _obPriorityLine()'):app.index('// O7: each answer next to')]
    check("s140 O3 the summary states the user's own priority and its arithmetic from what they entered",
          'You said ${said} comes first.' in fn and 'From what you entered' in fn and "goal === 'unsure'" in fn)
    from_teaching = re.compile(r'on track|keep going|great job|you should|we recommend', re.I)
    check('s140 O3 no verdict: the priority line carries no judgement or advice wording, and no date',
          not from_teaching.search(fn) and 'debt-free by' not in fn)

    # ── O4: labels change; the ledger's category names do not ────────────────
    check('s140 O4 the bills screen says home heating fuel and vehicle fuel, not "Gas" twice',
          'Home heating fuel ($/month)' in html and 'Vehicle fuel (gasoline or diesel) ($/month)' in html
          and '<label>Gas ($/month)</label>' not in html and '<label>Gas / Fuel ($/month)</label>' not in html)
    check('s140 O4 the categories keep their names: Gas / Fuel for vehicles, Gas for natural gas (and unanswered)',
          "_obExp('obExpFuel',      'Gas / Fuel'," in app and "return { cat: 'Gas', name: 'Home heating fuel' };" in app)
    check('s140 O4 propane and heating oil get their own categories, so they never feed the natural gas estimate',
          "if (f === 'propane') return { cat: 'Propane'" in hh_js and "if (f === 'heating_oil') return { cat: 'Heating Oil'" in hh_js)
    check('s140 O9 the 2.0 questions live in the teaching layer; app.js names none of them',
          not re.search(r'heating_fuel|vehicle_fuel|housing_status|electricity_included|heating_payment', app))

    # ── Step 7: item 26 follows what the household said ──────────────────────
    def say(**facts):
        with ctx.dbs() as s:
            for k in household.FACTS:
                s.query(HouseholdFact).filter_by(key=k).delete()
                s.query(AppSetting).filter_by(key=k).delete()
            for k, v in facts.items():
                household.set_household_fact(s, k, v, 'settings')
            s.commit()
            return {kind: server.utility_applies(s, kind) for kind in ('gas', 'electric', 'gasoline')}

    a = say(heating_fuel='propane', home_state='OH')
    # Propane was "not priced yet" until item 34 F2-F4 (2026-10-03); it has its own estimate now, from deliveries.
    check('s140 step 7 propane: no natural gas estimate, and it points to propane\'s own estimate',
          a['gas']['applies'] is False and 'propane' in a['gas']['why'] and 'own estimate' in a['gas']['why'])
    a = say(housing_status='rent', electricity_included='yes', heating_fuel='included')
    check('s140 step 7 rent includes electricity and heat: neither estimate applies, each says why',
          not a['electric']['applies'] and 'includes electricity' in a['electric']['why']
          and not a['gas']['applies'] and 'includes heat' in a['gas']['why'])
    a = say(heating_fuel='natural_gas', heating_payment='even_monthly')
    check('s140 step 7 an even-monthly heating bill: no fit, because the payments do not follow the weather',
          not a['gas']['applies'] and 'do not follow' in a['gas']['why'])
    a = say(vehicle_fuel='electric')
    b = say(vehicle_fuel='diesel')
    n = say(vehicle_fuel='none')
    # Diesel was "not priced yet" until item 34 F1 (2026-10-03); it is priced now, from EIA's weekly diesel series.
    check('s140 step 7 vehicle: electric and no vehicle settle the vehicle-fuel estimate, saying why; diesel is priced',
          not a['gasoline']['applies'] and 'electric' in a['gasoline']['why']
          and b['gasoline']['applies'] and 'vehicle_fuel' not in b['gasoline'].get('ask', [])
          and not n['gasoline']['applies'] and 'no vehicle fuel' in n['gasoline']['why'])
    a = say()
    check('s140 step 7 nothing answered: the estimates run from the record, SAY what they read the bills as, and ask',
          a['gas']['applies'] and 'natural gas' in (a['gas'].get('assumes') or '')
          and 'heating_fuel' in a['gas']['ask'] and 'home_state' in a['gas']['ask']
          and a['gasoline']['applies'] and 'regular gasoline' in (a['gasoline'].get('assumes') or '')
          and 'vehicle_fuel' in a['gasoline']['ask'])
    a = say(heating_fuel='natural_gas', heating_payment='by_bill', home_state='OH', vehicle_fuel='gasoline')
    check('s140 step 7 everything answered: the estimates apply and ask nothing more',
          a['gas']['applies'] and a['gas']['ask'] == [] and not a['gas'].get('assumes')
          and a['gasoline']['applies'] and a['gasoline']['ask'] == [])

    say(heating_fuel='propane')
    real_steo = server._steo
    calls = []
    server._steo = lambda *x, **k: calls.append(x) or {}
    try:
        d = (c.get('/api/budget/utility-estimate/gas', headers=H).get_json() or {}).get('data') or {}
    finally:
        server._steo = real_steo
    check('s140 step 7 the route: a settled estimate answers with the reason, and fetches nothing from EIA',
          d.get('not_applicable') and d.get('estimate') is None and not calls)
    say()

    node = shutil.which('node')
    check('s140 node is available to run the words (skip the next if not)', bool(node))
    if node:
        path = str(BASE.joinpath('static/js/teaching/utilitytext.js')).replace('\\', '/')
        prog = f"""
const U = require({json.dumps(path)});
const F = {{money: n => '$' + Number(n).toFixed(2), month: m => m, date: s => s}};
const out = {{
  na: U.gas({{not_applicable: 'You told us propane heats your home.'}}, F),
  as: U.gas({{region: {{state: 'OH', national: false}}, estimate: null, needs: 'more bills', bills: 1,
             assumes: 'Reading the bills in your Gas category as natural gas.'}}, F),
}};
console.log(JSON.stringify(out));
"""
        r = subprocess.run([node, '-e', prog], capture_output=True, text=True, encoding='utf-8', timeout=30)
        try:
            o = json.loads(r.stdout.strip().splitlines()[-1])
        except Exception:                              # noqa: BLE001 - reported below
            o = {}
            print('        node:', r.stderr[:300])
        check('s140 the words: a settled estimate shows only the reason, and the report gets no statement',
              o.get('na', {}).get('lines') == ['You told us propane heats your home.'] and o['na']['statement'] is None)
        check('s140 the words: an assumption is said on the card, never silent',
              'Reading the bills in your Gas category as natural gas.' in (o.get('as', {}).get('lines') or []))

    # ── O8: Settings and inline ──────────────────────────────────────────────
    show = app[app.index('function _showOnboarding() {'):app.index('function _showOnboarding() {') + 400]
    check('s140 O8 a known answer opens prefilled: onboarding starts from the facts as they stand, so the summary '
          'never calls an answered fact "not answered" (found in the browser, 2026-10-02)',
          '_obPrefillFacts();' in show and "await API.get('/api/settings/household')" in app
          and '_obAnswers[f.dataset.gwFact] = v;' in app)
    check('s140 O8 Settings has a "Your home" card setting the same facts (source settings)',
          "card.id = 'gwYourHome'" in hh_js and "_set(f.dataset.gwFact, f.value, 'settings')" in hh_js)
    check('s140 O8 the utility cards ask a missing fact inline (source inline_prompt) and redraw once answered',
          "_set(f.dataset.gwFact, f.value, 'inline_prompt')" in hh_js
          and 'H.mod.ask(host, d.ask, {}, function () { _budgetCard(); });' in
          BASE.joinpath('static/js/teaching/utility.js').read_text(encoding='utf-8'))
