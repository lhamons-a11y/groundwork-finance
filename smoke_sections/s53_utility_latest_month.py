"""UTILITY_ESTIMATES.md U0 (item 26, ruled 2026-10-01): the latest PUBLISHED EIA month, for every state.

EIA's newest row for a state can exist with no value yet. Ohio's June 2026 residential natural gas did, so the
price fell to the hard-coded estimate and the Budget page showed no EIA line. Now:

    latest published   the last six rows are asked for, and the newest one with a value is used, with its own period
    every state        nothing here is Ohio's: the same rule for any state code
    unpublished state  no row with a value and no cache: the U.S. figure, labelled 'U.S.', naming the state asked for
    estimate           with neither state nor national data, the labelled estimate, as before (never 'live')

No network: EIA's responses are stood in for, in the shapes the API returns.
"""
import json


class _Resp:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode('utf-8')

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def run(ctx):
    check = ctx.check
    import utility_price as up

    asked = []

    def fake_urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, 'full_url') else str(req)
        asked.append(url)
        if 'duoarea' in url:
            area = url.split('facets[duoarea][]=')[1].split('&')[0]
            rows = {
                'SOH': [{'period': '2026-06', 'value': None, 'area-name': 'OHIO'},
                        {'period': '2026-05', 'value': '19.91', 'area-name': 'OHIO'}],
                'SAZ': [{'period': '2026-06', 'value': '21.40', 'area-name': 'ARIZONA'}],
                'SHI': [{'period': '2026-06', 'value': None, 'area-name': 'HAWAII'},
                        {'period': '2026-05', 'value': '', 'area-name': 'HAWAII'}],
                'NUS': [{'period': '2026-06', 'value': '24.09', 'area-name': 'U.S.'}],
            }.get(area, [])
            return _Resp({'response': {'data': rows}})
        state = url.split('facets[stateid][]=')[1].split('&')[0]
        rows = {'OH': [{'period': '2026-07', 'price': '19.45', 'stateDescription': 'Ohio'}],
                'US': [{'period': '2026-07', 'price': '17.62', 'stateDescription': 'U.S. Total'}]}.get(state, [])
        return _Resp({'response': {'data': rows}})

    store = {}
    real = (up.urllib.request.urlopen, up._read_cache, up._write_cache)
    try:
        up.urllib.request.urlopen = fake_urlopen
        up._read_cache = lambda key: store.get(key)
        up._write_cache = lambda key, price, period, area_name: store.__setitem__(
            key, {'price': price, 'period': period, 'area_name': area_name, 'fetched_at': '2099-01-01T00:00:00'})

        oh = up.get_natural_gas_price('k', 'OH')
        check('s53 U0 Ohio: the newest month with a value is used (May), not the empty June row',
              oh['live'] and oh['price'] == 19.91 and oh['period'] == '2026-05' and 'national_fallback' not in oh)
        check('s53 U0 the API is asked for the last six months, not one',
              all('length=6' in u for u in asked))
        az = up.get_natural_gas_price('k', 'AZ')
        check('s53 U0 every state: Arizona\'s own latest month', az['price'] == 21.40 and az['period'] == '2026-06')
        hi = up.get_natural_gas_price('k', 'HI')
        check('s53 U0 a state with nothing published: the U.S. figure, labelled U.S., naming the state asked for',
              hi['live'] and hi['price'] == 24.09 and hi['area_name'] == 'U.S.' and hi.get('national_fallback') == 'SHI')
        el = up.get_electricity_price('k', 'OH')
        check('s53 U0 electricity follows the same rule (Ohio\'s own latest month)', el['price'] == 19.45 and el['period'] == '2026-07')
        wy = up.get_electricity_price('k', 'WY')
        check('s53 U0 electricity for an unpublished state: the U.S. figure, labelled',
              wy['price'] == 17.62 and wy['area_name'] == 'U.S.' and wy.get('national_fallback') == 'WY')
        none = up.get_natural_gas_price('k', '')
        check('s53 no state set: the national series directly, with no fallback flag', none['price'] == 24.09 and 'national_fallback' not in none)

        up.urllib.request.urlopen = lambda req, timeout=None: (_ for _ in ()).throw(OSError('offline'))
        store.clear()
        off = up.get_natural_gas_price('k', 'OH')
        check('s53 offline with nothing cached: the labelled estimate, never "live"', off['source'] == 'estimate' and off['live'] is False)
    finally:
        up.urllib.request.urlopen, up._read_cache, up._write_cache = real
    # Every state: no string the module computes with is a particular state's code (docstring examples aside).
    import ast
    import re
    tree = ast.parse(ctx.BASE.joinpath('utility_price.py').read_text(encoding='utf-8'))
    docs = {id(n.body[0].value) for n in ast.walk(tree)
            if isinstance(n, (ast.Module, ast.FunctionDef)) and n.body and isinstance(n.body[0], ast.Expr)
            and isinstance(n.body[0].value, ast.Constant)}
    codes = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)
             and id(n) not in docs and re.fullmatch(r'S?[A-Z]{2}', n.value) and n.value not in ('US', 'NUS')]
    check('s53 nothing the price module computes with names one state', codes == [])
