"""The onboarding revisit on 1.x (ONBOARDING_REVISIT.md, item 30, step 9; s140 is 2.0's).

O7, a hard acceptance criterion, both ways: every question 1.x asks sets a fact in core/household.py FACTS, and every
fact's consumers exist and read it - proved able to fail. 1.x asks only the facts it has readers for (O9).
"""
import ast
import re


def run(ctx):
    check, BASE = ctx.check, ctx.BASE
    from core import household
    html, app = ctx.html_src, ctx.app_src

    def asked_keys():
        keys = set(re.findall(r'data-gw-fact="([a-z_]+)"', html))
        if 'id="settingsHomeState"' in html:
            keys.add('home_state')
        if 'id="settingsPayFrequency"' in html:
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
        if '.' in name:
            return text if name in text else None
        m = re.search(r'function ' + re.escape(name) + r'\s*\(', text)
        return text[m.start():m.start() + 4000] if m else None

    def matrix(facts, asked):
        problems = []
        for key in asked:
            if key not in facts:
                problems.append(f'a question asks {key!r}, which is not a household fact')
        for key, f in facts.items():
            if key not in asked:
                problems.append(f'{key} is a fact nothing asks')
            for path, name, _what in f['consumers']:
                code = code_of(path, name)
                if code is None:
                    problems.append(f'{key}: consumer {path}:{name} does not exist')
                elif key not in code and not (name.startswith('S.') and 'pay_frequency' in code):
                    problems.append(f'{key}: consumer {path}:{name} does not read it')
        return problems

    asked = asked_keys()
    problems = matrix(household.FACTS, asked)
    check('s63 O7 the matrix holds both ways on 1.x: every question sets a fact, every fact is asked, and every '
          'consumer exists and reads its fact', not problems)
    for p in problems[:8]:
        print(f'        {p}')
    check('s63 O7 mutation caught: a fact whose consumer does not exist (a 2.0 fact on 1.x)',
          bool(matrix(dict(household.FACTS, heating_fuel={'asks': 'x', 'values': ('propane',), 'lines': '2.0',
                                                         'consumers': [('server.py', 'utility_applies', 'x')]}),
                      asked | {'heating_fuel'})))
    check('s63 O7 mutation caught: a question that sets no fact', bool(matrix(household.FACTS, asked | {'favourite_colour'})))

    check('s63 O2 "What brought you here today?" is gone: no screen, no handler, nothing stored',
          'obStepIntent' not in html and 'What brought you here' not in html
          and 'onboarding_intent' not in app and 'obSetIntent' not in app)
    check('s63 O1 the home screen (the state) sits between income and the bills',
          html.index('id="obStep1"') < html.index('id="obStepHome"') < html.index('id="obStep2"'))
    check('s63 O6 every onboarding fact can be skipped, and a skipped one sends nothing',
          all(re.search(r'data-gw-fact="' + k + r'"[^>]*>\s*<option value="">Skip for now</option>', html)
              for k in re.findall(r'data-gw-fact="([a-z_]+)"', html))
          and "if (!f.value && !(key in _obAnswers)) continue;" in app)
    check("s63 O6 an unanswered pay frequency is unanswered, not 'monthly'",
          "payFrequency || 'monthly'" not in app and "pay_frequency    || 'monthly'" not in app)
    check('s63 O5 onboarding answers go through the one write path, with source onboarding',
          "API.post('/api/settings/household', { key, value: f.value || null, source: 'onboarding' })" in app
          and 'surplus_goal: goal })' not in app)
    fn = app[app.index('function _obPriorityLine()'):app.index('// O7: each answer next to')]
    check("s63 O3 the summary states the user's own priority and its arithmetic, with no verdict and no date",
          'You said ${said} comes first.' in fn and 'From what you entered' in fn
          and not re.search(r'on track|keep going|great job|you should|we recommend', fn, re.I) and 'debt-free by' not in fn)
    check('s63 O4 the bills say home heating fuel and vehicle fuel; the categories keep their names (Gas, Gas / Fuel)',
          'Home heating fuel ($/month)' in html and 'Vehicle fuel (gasoline or diesel) ($/month)' in html
          and "_obExp('obExpFuel',      'Gas / Fuel'," in app and "return { cat: 'Gas', name: 'Home heating fuel' };" in app)
    check('s63 O9 1.x asks no home, heating or vehicle fact (their readers are 2.0\'s)',
          not re.search(r'heating_fuel|vehicle_fuel|housing_status|electricity_included|heating_payment', app + html))
    show = app[app.index('function _showOnboarding() {'):app.index('function _showOnboarding() {') + 400]
    check('s63 O8 a known answer opens prefilled, so the summary never calls an answered fact "not answered"',
          '_obPrefillFacts();' in show and '_obAnswers[f.dataset.gwFact] = v;' in app)
