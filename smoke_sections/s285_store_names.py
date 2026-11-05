"""The other major United States stores and everyday payees, for the voice to hear (item 116 V23; Rob 2026-11-04: "grab
all of the Department stores, pharmacies, all major shopping stores in the United States with phonetic spelling to train
Whisper"). The list is core/data/us_stores.json. whisper is not retrained by a list: a store's spelling in its prompt
nudges it, and what it writes instead is corrected afterwards (_askSoundsLike).

    N1  every row has a name and a phonetic spelling; the kinds asked for are there; a form heard for one store is not
        another store's own name
    N2  the page reads names, kinds and heard forms from this computer - no phonetic, no parent companies
    N3  a store written as it sounds is the store, the person's own first: "coals" is their KOHLS #12, and their own
        "Coal Creek Grill" before that; one sound can be two stores, and the one in the record wins
    N4  everyday words are taken for no store (the null model: the matcher now has far more names to hit)
    N5  hearing only: no row here decides a category, on the server or the page
"""
import json
import os
import shutil
import subprocess
import tempfile

# Not store names, and said to Groundwork or likely to come back from whisper (V22's measured set, and more). A word is
# wrong only if it comes back as something else: "best" finding nothing as "best" is what it did before.
EVERYDAY = '''dinner lunch breakfast milk bread eggs rent mortgage budget ledger debt debts dashboard settings report reports
groceries restaurants food gas gasoline fuel coffee water electric electricity insurance interest savings checking
transfer deposit payment payments income paycheck salary bills bill taxes tax fees fee shopping clothes clothing shoes
pets pet medicine doctor dentist school tuition phone internet cable movie movies travel hotel flight flights car auto
truck tires repair haircut gift gifts church charity donation vacation holiday christmas birthday wedding kids children
family friends house home yard garden tools furniture books toys games music subscription subscriptions today yesterday
tomorrow month monthly weekly year last next this that please thanks okay stop repeat slower faster again everything
nothing something money cash card credit visa balance total spending'''.split()


def _rows(groups):
    return [(g, *r) for g, rs in groups.items() for r in rs]


def run(ctx):
    check, c, H = ctx.check, ctx.c, ctx.H
    from core import grocery_chains
    import bank_importer as bi

    # ── N1 ───────────────────────────────────────────────────────────────────────────────────────────────────────────
    groups = grocery_chains.load_stores()
    rows = _rows(groups)
    names = {grocery_chains.norm(r[1]) for r in rows}
    wanted = {'department': "Kohl's", 'pharmacy': 'Walgreens', 'discount': 'T.J. Maxx', 'warehouse': 'Costco',
              'home_improvement': "Lowe's", 'gas_convenience': 'Sheetz', 'clothing': 'Uniqlo', 'fast_food': 'Chick-fil-A'}
    check(f"s285 N1 every row has a name and a phonetic spelling, and the kinds asked for are there ({len(rows)} rows, "
          f"{len(groups)} groups)",
          len(rows) > 500 and all(r[1].strip() and r[2].strip() for r in rows) and len(names) == len(rows)
          and all(n in [r[0] for r in groups[g]] for g, n in wanted.items()))
    clash = sorted({h for r in rows for h in r[3] if grocery_chains.norm(h) in names - {grocery_chains.norm(r[1])}})
    check(f"s285 N1 a form heard for one store is not another store's own name{' - ' + str(clash) if clash else ''}",
          not clash)

    # ── N2 ───────────────────────────────────────────────────────────────────────────────────────────────────────────
    r = c.get('/api/voice/chains', headers=H).get_json()['data']
    served = {x['name']: x for x in r['chains']}
    check(f"s285 N2 the page reads names, kinds and heard forms - no phonetic, no parent companies ({len(served)} served)",
          "coals" in served["Kohl's"]['heard'] and served["Kohl's"]['kind'] == 'department'
          and served['Walmart']['kind'] == 'mixed' and served['Walmart'].get('heard')
          and served['Kroger']['kind'] == 'grocery' and served['Kroger'].get('heard')
          and 'Ahold Delhaize' not in served
          and all(set(x) <= {'name', 'kind', 'generic', 'heard'} for x in served.values()))

    node = shutil.which('node')
    if not node:
        check('s285 node is available for the page test', False)
        return
    app = ctx.app_src if '_askSoundsLike' in ctx.app_src else (ctx.BASE / 'static' / 'js' / 'app.js').read_text(encoding='utf-8')

    def fn(name):
        i = app.index('function ' + name + '(')
        return app[i:app.index('\n}\n', i) + 3]
    js = ('globalThis.window = globalThis;\nvar S = {transactions: []};\nwindow._gwChains = ' + json.dumps(r['chains'])
          + ';\n' + fn('_askSoundsLike') + fn('_gwChainNorm') + fn('_gwGroceryChain') + r"""
const like = (t, ...own) => { S.transactions = own.map(m => ({merchant: m})); return _askSoundsLike(t); };
const out = {
  theirs: like('coals', 'KOHLS #12'), none: like('coals'), own_first: like('coals', 'Coal Creek Grill', 'KOHLS #12'),
  wall: like('wall greens', 'WALGREENS 99'), sefora: like('sefora'), major: like('major', 'Meijer'),
  kwik: like('quick trip', 'KWIK TRIP 112'), quik: like('quick trip', 'QUIKTRIP 7'), wegmen: like("wegmen's"),
  groc: ['KOHLS #12', 'SHELL OIL 123', 'CVS 8', 'SHEETZ 44', 'FOOD LION 1'].map(_gwGroceryChain),
};
S.transactions = [];
out.everyday = Object.fromEntries(""" + json.dumps(EVERYDAY) + r""".map(w => [w, _askSoundsLike(w)]).filter(([w, v]) => v && v !== w));
console.log(JSON.stringify(out));
""")
    f = os.path.join(tempfile.mkdtemp(prefix='s285_'), 'page.js')
    open(f, 'w', encoding='utf-8').write(js)
    p = subprocess.run([node, f], capture_output=True, text=True, encoding='utf-8', timeout=60)
    try:
        o = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        check('s285 the page test ran: ' + (p.stdout + p.stderr)[-400:], False)
        return

    # ── N3 ───────────────────────────────────────────────────────────────────────────────────────────────────────────
    check(f"s285 N3 a store written as it sounds is the store, the person's own first ({o})",
          o['theirs'] == 'kohls' and o['none'] == "kohl's" and o['own_first'] == 'coal'
          and o['wall'] == 'walgreens' and o['sefora'] == 'sephora' and o['major'] == 'meijer'
          and o['wegmen'] == 'wegmans')
    check(f"s285 N3 one sound, two stores: the one in the record wins (kwik {o['kwik']}, quik {o['quik']})",
          o['kwik'] == 'kwik trip' and o['quik'].startswith('quiktrip'))

    # ── N4 ───────────────────────────────────────────────────────────────────────────────────────────────────────────
    check(f"s285 N4 of {len(EVERYDAY)} everyday words, none is taken for a store ({o['everyday']})", not o['everyday'])

    # ── N5 ───────────────────────────────────────────────────────────────────────────────────────────────────────────
    lines = {'KOHLS #12': 'Clothing', 'SHELL OIL 123': 'Gasoline / Diesel', 'CVS 8': 'Prescriptions', 'TARGET 1': 'Shopping'}
    server = {k: bi.auto_category(k) for k in lines}
    check(f"s285 N5 hearing only: no new store is a grocery chain, on the server or the page ({server}, {o['groc']})",
          server == lines and not any(grocery_chains.grocery_chain(x) for x in ('KOHLS #12', 'SHELL OIL 123', 'CVS 8', 'SHEETZ 44'))
          and o['groc'] == [None, None, None, None, 'Food Lion'])
