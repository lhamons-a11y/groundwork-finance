"""The United States' supermarket chains (Rob 2026-11-01: "here is a website to grab all of the major national Grocery
Stores that is in the United States" - all three uses chosen: say them right, hear them right, know they are grocery
stores). The list is core/data/grocery_chains.json, built by scripts/build_grocery_chains.py from Wikipedia.

    G1  the list ships with the app and names its source and revision; Groundwork never fetches it; the wholesalers,
        the defunct chains and the parent companies are not stores on a receipt
    G2  said right: the chains the voice says wrong are respelled - Fred Meyer is not "Fred MAY-er", IGA not "igga" -
        on a bank line too ("GELSON'S #12"); the person's own way still wins
    G3  heard right: a chain whisper writes as it sounds is the chain (the page reads the list from this computer)
    G4  known as grocery: a bank line naming a supermarket is Groceries, right after the Groceries rule, on the server
        and on the page alike - never a generic name ("LUCKY DRAGON", "123 MARKET STREET"), never a mixed store
        (Walmart, Target, Costco keep their own rules), never before a precise rule (Meijer Express is fuel)
"""
import json
import os
import shutil
import subprocess
import tempfile

LINES = {
    'FOOD LION #1234': 'Groceries', 'CUB FOODS 55': 'Groceries', 'HARPS FOOD STORE #12': 'Groceries',
    'CHIEF SUPERMARKET 2 MILLBROOK OH': 'Groceries', 'STOP & SHOP 0412': 'Groceries', 'WOODMANS MARKETS': 'Groceries',
    'WEGMANS #44': 'Groceries', 'HEINENS 12': 'Groceries', 'GIANT EAGLE 0042': 'Groceries', 'FOOD 4 LESS #77': 'Groceries',
    'SUPERMERCADO EL RANCHO': 'Groceries',
    'LUCKY DRAGON RESTAURANT': 'Restaurants', '123 MARKET STREET CAFE': 'Restaurants', 'JOES DINER': 'Restaurants',
    'EVERGREEN LANDSCAPING': 'Other', 'TOPS NAIL SALON': 'Haircut / Salon', 'MEIJER EXPRESS 22': 'Gasoline / Diesel',
    'WALGREENS 99': 'Prescriptions', 'TARGET 1234': 'Shopping',
}


def run(ctx):
    check, c, H = ctx.check, ctx.c, ctx.H
    from core import grocery_chains, speak
    import bank_importer as bi

    # ── G1 ───────────────────────────────────────────────────────────────────────────────────────────────────────────
    d = json.loads((ctx.BASE / 'core' / 'data' / 'grocery_chains.json').read_text(encoding='utf-8'))
    names = {x['name']: x for x in d['chains']}
    kinds = {k: sum(1 for x in d['chains'] if x['kind'] == k) for k in ('grocery', 'mixed', 'company')}
    check(f"s284 G1 the list ships with its source and revision ({len(names)} chains, {kinds}, revision {d.get('revision')})",
          d['source'].startswith('https://en.wikipedia.org/wiki/List_of_supermarket_chains') and d.get('revision')
          and kinds['grocery'] > 300 and names['Meijer']['kind'] == 'grocery' and names['Walmart']['kind'] == 'mixed'
          and names['Ahold Delhaize']['kind'] == 'company' and 'C&S Wholesale Grocers' not in names and 'SuperValu' not in names
          and not any(n in names for n in ('Nevada', 'Korean-American', 'Illinois', 'Seattle, Washington')))
    src = (ctx.BASE / 'core' / 'grocery_chains.py').read_text(encoding='utf-8')
    check('s284 G1 Groundwork never fetches the list: the module reads only the shipped file',
          'urllib' not in src and 'requests' not in src and 'http' not in src.split('"""', 2)[2])

    # ── G2 ───────────────────────────────────────────────────────────────────────────────────────────────────────────
    said = {t: speak.spoken(t) for t in ('OK, showing your Fred Meyer transactions.', 'Your Lidl and IGA spending',
                                          "GELSON'S #12", 'Stater Bros. receipt', 'Uwajimaya')}
    check(f"s284 G2 the chains the voice says wrong are respelled, on a bank line too ({said})",
          said == {'OK, showing your Fred Meyer transactions.': 'OK, showing your Fred Myer transactions.',
                   'Your Lidl and IGA spending': 'Your Leedle and I G A spending', "GELSON'S #12": "Ghelson's #12",
                   'Stater Bros. receipt': 'Stater Brothers receipt', 'Uwajimaya': 'Oo-wah-jee-mah-yah'}
          and speak.spoken('Lidl', names={'Lidl': 'lid-dull'}) == 'lid-dull')
    check('s284 G2 each respelling names a chain on the list', sum(1 for x in d['chains'] if x.get('say')) >= 40)

    # ── G3 ───────────────────────────────────────────────────────────────────────────────────────────────────────────
    r = c.get('/api/voice/chains', headers=H).get_json()['data']
    served = {x['name']: x for x in r['chains']}
    check(f"s284 G3 the page reads the chains from this computer - names and kinds, no parent companies "
          f"({len(served)} served)",
          'Wegmans' in served and 'Ahold Delhaize' not in served and served['Giant'].get('generic') is True
          and set(next(iter(served.values()))) <= {'name', 'kind', 'generic'})

    # ── G4 ───────────────────────────────────────────────────────────────────────────────────────────────────────────
    server = {line: bi.auto_category(line) for line in LINES}
    wrong = {k: (v, LINES[k]) for k, v in server.items() if v != LINES[k]}
    check(f"s284 G4 a bank line naming a supermarket is Groceries; a generic name, a mixed store and a precise rule are "
          f"not moved ({len(LINES)} lines){' - wrong: ' + json.dumps(wrong) if wrong else ''}", not wrong)
    check('s284 G4 a chain is found by its own name only, the line tidied the same way',
          grocery_chains.grocery_chain('STOP & SHOP 0412') == 'Stop & Shop'
          and grocery_chains.grocery_chain('LUCKY DRAGON RESTAURANT') is None
          and grocery_chains.norm("HARPS FOOD STORES") == grocery_chains.norm('Harps Food Store'))

    node = shutil.which('node')
    if not node:
        check('s284 node is available for the page test', False)
        return
    app = ctx.app_src if '_gwGroceryChain' in ctx.app_src else (ctx.BASE / 'static' / 'js' / 'app.js').read_text(encoding='utf-8')

    def fn(name):
        i = app.index('function ' + name + '(')
        return app[i:app.index('\n}\n', i) + 3]
    js = ('globalThis.window = globalThis;\nwindow._gwChains = ' + json.dumps(r['chains']) + ';\n'
          + fn('_gwChainNorm') + fn('_gwGroceryChain') + fn('clientAutoCategory')
          + 'console.log(JSON.stringify(Object.fromEntries(' + json.dumps(list(LINES)) + '.map(d => [d, clientAutoCategory(d)]))));\n'
          + 'window._gwChains = null;\nconsole.log(JSON.stringify(clientAutoCategory("FOOD LION #1234")));\n')
    f = os.path.join(tempfile.mkdtemp(prefix='s284_'), 'page.js')
    open(f, 'w', encoding='utf-8').write(js)
    p = subprocess.run([node, f], capture_output=True, text=True, encoding='utf-8', timeout=60)
    try:
        out = p.stdout.strip().splitlines()
        page, before = json.loads(out[0]), json.loads(out[1])
    except Exception:
        page, before = {'error': (p.stdout + p.stderr)[-400:]}, None
    diff = {k: (page.get(k), server[k]) for k in LINES if page.get(k) != server[k]}
    check(f"s284 G4 the page files every line as the server does{' - differs: ' + json.dumps(diff) if diff else ''}",
          not diff)
    check(f"s284 G4 before the list has loaded, the page's other rules decide, as before ({before})",
          before == 'Restaurants')
    check("s284 G4 the page asks the list right after its Groceries rule, and loads it at start",
          "  if (typeof _gwGroceryChain === 'function' && _gwGroceryChain(d)) return 'Groceries';" in fn('clientAutoCategory') and '_gwLoadChains();' in fn('bootFromDB'))
