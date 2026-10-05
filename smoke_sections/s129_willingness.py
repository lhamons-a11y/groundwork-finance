"""The Willingness Layer, first build: the record's readings, the user's word, the solution engine reading both.

`gw 2.0/WILLINGNESS_LAYER.md`, ruled 2026-09-27 (all eight). Cases Wl1-Wl13 of s4 where this build reaches them:

    observed    E.2's readings are citations: a cut that held (flexible), a cut later restored (sacred) - and,
                since item 39, nothing read from a cut the user never made; E.2a - a cut beside an income move is not
                classified, and income not on record is unknown, never level (absence is not zero)
    declared    the user's word beats every reading, a release is a new row, nothing is ever rewritten; a
                statement must answer a claim or a proposal that names the category (F.3)
    consumed    a protected category is never a lever; flexible candidates are offered first (E.3 rule 2);
                the generic lever names a category only when it is flexible, saying by record or by word;
                the necessity floor holds whatever is declared
    boundary    the gatherer reads the record and the declarations, and never usage - no session event, no
                page visit, no shown or dismissed suggestion (W6, pinned structurally, with mutations)
    words       no line sets a statement against behaviour as a failing (F.4)
    home        the empty state offers no controls; app.js and index.html know nothing of any of it
    upgrade     a database stored at the previous SCHEMA_VERSION gains the declarations table on start
"""
import ast
import json
import re
from datetime import date, datetime, timedelta

_RUN = [0]
_FORBIDDEN_EVENTS = ('session_start', 'session_end', 'budget_reviewed', 'proactive_shown',
                     'proactive_dismissed', 'engagement')


def _engine_cases():
    from core.willingness import observed_readings, current_declarations, effective, annotate, claim_for
    from core.solution import _headroom, _trims, solve_one_time_cost
    out = {}
    months = ['2026-03', '2026-04', '2026-05', '2026-06', '2026-07', '2026-08']
    flat = {m: 4000.0 for m in ['2026-02'] + months}
    cut = {'id': 1, 'date': '2026-03-10', 'category': 'Dining', 'old': 450.0, 'new': 350.0}

    def read(cat, edits, spend, income=flat, debits=None):
        r = observed_readings([cat], edits, spend, set(months), income, debits or {m: 1000.0 for m in months})
        return r[0] if r else None

    held = {('Dining', m): 300.0 for m in months[1:]}
    r = read('Dining', [cut], held)
    out['Wl2 a cut that held three months is flexible, citing the edit and the months'] = (
        r['stance'] == 'flexible' and r['reason'] == 'cut_held' and r['receipt']['cut'] == cut
        and r['receipt']['months'] == months[1:] and r['receipt']['worst'] == 300.0)

    restore = {'id': 2, 'date': '2026-05-02', 'category': 'Dining', 'old': 350.0, 'new': 450.0}
    r = read('Dining', [cut, restore], held)
    out['Wl3 a cut later restored is sacred, citing both edits'] = (
        r['stance'] == 'sacred' and r['reason'] == 'restored' and r['receipt']['restore'] == restore)

    moved = dict(flat, **{'2026-03': 4800.0})
    r = read('Dining', [cut], held, income=moved)
    out['Wl4 a cut beside an income move is not classified; the move is shown as a fact'] = (
        r['stance'] == 'unclassified' and r['reason'] == 'probation'
        and r['receipt']['income'] == {'from_month': '2026-02', 'from': 4000.0, 'month': '2026-03', 'to': 4800.0})
    # The month before the cut is not on record: income there is unknown, not level.
    r = read('Dining', [cut], held, income={m: 4000.0 for m in months})
    out['E.2a income not on record around the cut is unknown, not level - unclassified'] = (
        r['stance'] == 'unclassified' and r['reason'] == 'income_unrecorded')
    r = read('Dining', [dict(cut, date='2026-06-10')], held)
    out['a cut with fewer than three months after it concludes nothing yet'] = (
        r['stance'] == 'unclassified' and r['reason'] == 'too_soon' and r['receipt']['months_seen'] == 2)
    over = {**held, ('Dining', '2026-05'): 420.0}
    r = read('Dining', [cut], over)
    out['a cut that did not hold is not classified either way - an answer, not a verdict'] = (
        r['stance'] == 'unclassified' and r['reason'] == 'did_not_hold')

    # Item 39 (Rob 2026-10-05): an envelope kept, not cut, through months when spending passed income is no
    # longer read as sacred - that concluded from what the user did not do.
    tight = {m: (5000.0 if m in ('2026-04', '2026-06') else 1000.0) for m in months}
    r = read('Hobbies', [], {('Hobbies', '2026-04'): 60.0, ('Hobbies', '2026-06'): 55.0}, debits=tight)
    out['item 39 an envelope kept through tight months concludes nothing - no reading from a cut never made'] = (
        r['stance'] == 'unclassified' and r['reason'] == 'no_evidence' and r['receipt'] is None)
    import core.willingness as _w
    out['item 39 the reading is gone from the engine and the page, not just unreached'] = (
        not hasattr(_w, 'tight_months') and not hasattr(_w, 'MIN_TIGHT_MONTHS')
        and "'held'" not in __import__('pathlib').Path(__file__).resolve().parents[1].joinpath(
            'static/js/teaching/willingness.js').read_text(encoding='utf-8'))
    out['a necessity-floor category gets no reading at all (E.1 already governs it)'] = (
        observed_readings(['Groceries', 'Rent'], [], {}, set(months), flat, {}) == [])
    r = read('Hobbies', [], {})
    out['Wl1 no edits and no tight months: unclassified, no receipt'] = (
        r['stance'] == 'unclassified' and r['reason'] == 'no_evidence' and r['receipt'] is None)

    d1 = {'id': 1, 'category': 'Dining', 'stance': 'protect', 'said_at': '2026-04-01T10:00:00', 'answer_kind': 'claim'}
    d2 = {'id': 2, 'category': 'dining', 'stance': 'release', 'said_at': '2026-05-01T10:00:00', 'answer_kind': 'claim'}
    d3 = {'id': 3, 'category': 'Dining', 'stance': 'flexible', 'said_at': '2026-06-01T10:00:00', 'answer_kind': 'claim'}
    out['the latest statement stands; a release removes it; a changed mind is the newer row'] = (
        current_declarations([d1]) == {'dining': d1} and current_declarations([d1, d2]) == {}
        and current_declarations([d1, d2, d3]) == {'dining': d3})
    readings = [read('Dining', [cut], held)]
    eff = effective(readings, [d1])
    out['Wl5 the declared word beats the reading, and the reading stays attached'] = (
        eff['dining']['stance'] == 'protected' and eff['dining']['source'] == 'declared'
        and eff['dining']['reading']['stance'] == 'flexible')
    out['a claim exists to answer only where something was concluded or said'] = (
        claim_for('Dining', readings, []) is not None and claim_for('Hobbies', readings, []) is None
        and claim_for('Hobbies', [], [dict(d1, category='Hobbies')]) is not None)

    cats = [{'name': 'Dining', 'budgeted': 400, 'max_observed': 250, 'months_observed': 6},
            {'name': 'Shopping', 'budgeted': 500, 'max_observed': 200, 'months_observed': 6},
            {'name': 'Hobbies', 'budgeted': 200, 'max_observed': 100, 'months_observed': 6}]
    eff = {'dining': {'stance': 'flexible', 'source': 'observed', 'reading': {'reason': 'cut_held'}},
           'shopping': {'stance': 'protected', 'source': 'declared', 'declaration': d1},
           'hobbies': {'stance': 'sacred', 'source': 'observed', 'reading': {'reason': 'restored'}}}
    ann = annotate(cats, eff)
    room = _headroom(ann)
    out['Wl5 a protected category is never a lever'] = [c['name'] for c in room] == ['Dining', 'Hobbies']
    out['E.3 rule 2: a smaller flexible candidate is offered before a larger kept one'] = (
        room[0]['name'] == 'Dining' and room[0]['monthly'] < 200 and room[1]['monthly'] == 100
        and room[0]['willingness']['stance'] == 'flexible')
    out['with no willingness, candidates keep the old order (size only)'] = (
        [c['name'] for c in _headroom(cats)] == ['Shopping', 'Dining', 'Hobbies'])
    trims = _trims(annotate([{'name': 'Netflix', 'monthly': 20, 'category': 'Shopping'},
                             {'name': 'Gym', 'monthly': 40, 'category': 'Hobbies'}], eff, field='category'))
    out['a recurring item in a protected category is not a trim candidate'] = [t['name'] for t in trims] == ['Gym']
    floor = annotate([{'name': 'Groceries', 'budgeted': 900, 'max_observed': 500, 'months_observed': 6}],
                     {'groceries': {'stance': 'flexible', 'source': 'declared', 'declaration': d3}})
    out['Wl10 the necessity floor holds even against a flexible statement'] = _headroom(floor) == []

    from core.consequence import Card
    cards = [Card(balance=8000, rate=22, minimum=200, name='Visa')]
    try:
        plain = solve_one_time_cost(cards, 775, 2400)
        named = solve_one_time_cost(cards, 775, 2400, categories=ann)
        m_plain = next((p for p in plain['paths'] if p['kind'] == 'monthly'), None)
        m_named = next((p for p in named['paths'] if p['kind'] == 'monthly'), None)
        out['Wl7 the generic lever names a category only when flexible, saying how'] = (
            m_plain is not None and m_named is not None and m_plain['items'] == []
            and 'your record shows Dining has moved before' in m_named['detail']
            and 'Hobbies' not in m_named['detail'] and 'Shopping' not in m_named['detail'])
    except Exception as e:
        out[f'Wl7 the generic lever names a category only when flexible ({e!r})'] = False
    return out


def _route_cases(c, HJ, dbs):
    from core.database import BudgetItem, Category, Transaction, HistorianEntry, WillingnessDeclaration
    import server
    _RUN[0] += 1
    n = _RUN[0]
    out = {}
    cat_a, cat_b = f'S129 Takeout {n}', f'S129 Quiet {n}'
    today = date.today()
    first = today.replace(day=1)
    back = [(first - timedelta(days=31 * k)).replace(day=12) for k in (1, 2, 3, 4)]
    with dbs() as s:
        ca = Category(name=cat_a, type='expense')
        s.add(ca)
        s.add(Category(name=cat_b, type='expense'))
        s.flush()
        item = BudgetItem(name=cat_a, category=cat_a, amount=400.0, type='expense', is_active=True)
        s.add(item)
        s.add(BudgetItem(name=cat_b, category=cat_b, amount=90.0, type='expense', is_active=True))
        for d in back[:3]:
            s.add(Transaction(date=d, description=f'S129 {n}', amount=120.0, type='debit', category_id=ca.id))
        s.commit()
        item_id = item.id

    r = c.patch(f'/api/budget/items/{item_id}', headers=HJ, data=json.dumps({'amount': 300.0}))
    with dbs() as s:
        e = s.query(HistorianEntry).filter_by(event_category='budget_adjusted').order_by(HistorianEntry.id.desc()).first()
        e.created_at = datetime.combine(back[3], datetime.min.time())
        s.commit()
        inputs = server._willingness_inputs(s)
    mine = [x for x in inputs['edits'] if x['category'] == cat_a]
    out['the gatherer reads the user\'s budget edit, by the item\'s category, old -> new'] = (
        r.status_code == 200 and len(mine) == 1 and mine[0]['old'] == 400.0 and mine[0]['new'] == 300.0)
    out['the gatherer reads spending by category over complete months only'] = (
        all((cat_a, d.strftime('%Y-%m')) in inputs['spend'] for d in back[:3])
        and not any(k[1] == today.strftime('%Y-%m') for k in inputs['spend']))

    def rows():
        with dbs() as s:
            return s.query(WillingnessDeclaration).count()

    def names(ss):
        return {x['name'] for x in server.reallocation_candidates(ss)}

    with dbs() as s:
        was_candidate = cat_a in names(s)

    base = rows()
    r = c.post('/api/willingness/declarations', headers=HJ,
               data=json.dumps({'category': cat_b, 'stance': 'protect', 'answer': {'kind': 'claim', 'text': 'x'}}))
    out['F.3 nothing to dispute: a statement about an unclaimed category is refused'] = (
        r.status_code == 409 and rows() == base)
    r = c.post('/api/willingness/declarations', headers=HJ,
               data=json.dumps({'category': cat_a, 'stance': 'protect',
                                'answer': {'kind': 'proposal', 'text': 'shifting $80/mo from somewhere else'}}))
    out['a proposal answered must name the category'] = r.status_code == 400 and rows() == base
    r = c.post('/api/willingness/declarations', headers=HJ,
               data=json.dumps({'category': cat_a, 'stance': 'release',
                                'answer': {'kind': 'claim', 'text': 'x'}}))
    out['there is nothing to release before anything was said'] = r.status_code == 409 and rows() == base
    r = c.post('/api/willingness/declarations', headers=HJ,
               data=json.dumps({'category': cat_a, 'stance': 'protect',
                                'answer': {'kind': 'proposal', 'text': f'shifting $80/mo from {cat_a}'}}))
    body = (r.get_json() or {}).get('data') or {}
    now = [d for d in body.get('current', []) if d['category'] == cat_a]
    out['in context: "never X" answering a path is stored with what it answered'] = (
        r.status_code == 200 and rows() == base + 1 and len(now) == 1 and now[0]['stance'] == 'protect'
        and now[0]['answer_kind'] == 'proposal' and cat_a in now[0]['answer_text'])
    with dbs() as s:
        protected_out = cat_a not in names(s)
    out['Wl5 end to end: the protected category leaves the solution engine\'s candidates'] = (
        was_candidate and protected_out)

    r = c.post('/api/willingness/declarations', headers=HJ,
               data=json.dumps({'category': cat_a, 'stance': 'flexible',
                                'answer': {'kind': 'claim', 'text': 'You marked it protected'}}))
    with dbs() as s:
        cand = [x for x in server.reallocation_candidates(s) if x['name'] == cat_a]
    out['a changed mind is a new row, and the candidate returns carrying the user\'s word'] = (
        r.status_code == 200 and rows() == base + 2 and len(cand) == 1
        and cand[0].get('willingness') == {'stance': 'flexible', 'source': 'declared'})
    r = c.post('/api/willingness/declarations', headers=HJ,
               data=json.dumps({'category': cat_a, 'stance': 'release', 'answer': {'kind': 'claim', 'text': 'x'}}))
    hist = [d for d in ((r.get_json() or {}).get('data') or {}).get('declarations', []) if d['category'] == cat_a]
    out['a release is a row too - the whole history stays readable, oldest first'] = (
        r.status_code == 200 and rows() == base + 3 and [d['stance'] for d in hist] == ['protect', 'flexible', 'release'])
    r = c.get('/api/willingness', headers=HJ)
    d = (r.get_json() or {}).get('data') or {}
    out['the picture carries readings, the history and the current word - and no derived state to store'] = (
        r.status_code == 200 and set(d) == {'readings', 'declarations', 'current'}
        and not any(x['category'] == cat_a for x in d['current']))
    rules = [(str(rule), rule.methods) for rule in c.application.url_map.iter_rules() if '/api/willingness' in str(rule)]
    out['append-only by construction: no route can edit or delete a statement'] = (
        rules and all(not ({'PUT', 'PATCH', 'DELETE'} & set(m)) for _, m in rules))
    return out


def _function_src(src, name):
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(src, node)
    return ''


def _boundary(server_src, wmod_src):
    """W6: the gatherer's event reads are exactly budget_adjusted; the engine touches no storage at all."""
    gather = _function_src(server_src, '_willingness_inputs') + _function_src(server_src, 'willingness_state')
    events = set(re.findall(r"event_category\s*==\s*'([^']+)'", gather))
    touches = [f for f in _FORBIDDEN_EVENTS if f in gather or f in wmod_src]
    tree = ast.parse(wmod_src)
    imports = {(n.module or '') for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | \
              {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    return {
        'gather': bool(gather),
        'events': events == {'budget_adjusted'},
        'no usage': not touches,
        'no storage': not any(i.startswith(('core.database', 'sqlalchemy', 'server')) for i in imports),
    }


def run(ctx):
    check, c, HJ, dbs = ctx.check, ctx.c, ctx.HJ, ctx.dbs
    import migrate
    from core.database import engine
    from sqlalchemy import text

    for name, ok in _engine_cases().items():
        check(f's129 {name}', ok)
    for name, ok in _route_cases(c, HJ, dbs).items():
        check(f's129 {name}', ok)

    wmod = ctx.BASE.joinpath('core/willingness.py').read_text(encoding='utf-8')
    b = _boundary(ctx.server_src, wmod)
    check('s129 W6 the gatherer exists and reads exactly one event kind: the user\'s own budget edit', b['gather'] and b['events'])
    check('s129 W6 no usage is read anywhere on the layer\'s path - no session, page visit, shown or dismissed suggestion',
          b['no usage'])
    check('s129 W6 the engine has no storage access at all - derived readings cannot be persisted from it', b['no storage'])
    # Mutations: each way the boundary could be crossed must be caught.
    gather = _function_src(ctx.server_src, '_willingness_inputs')
    for label, mutated in (
            ('a dismissal read as willingness',
             gather.replace("HistorianEntry.event_category == 'budget_adjusted'",
                            "HistorianEntry.event_category.in_(('budget_adjusted', 'proactive_dismissed'))")),
            ('a page visit counted', gather + "\n    _ = HistorianEntry.event_category == 'budget_reviewed'\n"),
            ('a second event kind', gather.replace("== 'budget_adjusted'", "== 'budget_variance_observed'"))):
        m = _boundary(ctx.server_src.replace(gather, mutated), wmod)
        check(f's129 mutation caught: {label}', mutated != gather and not (m['events'] and m['no usage']))
    m = _boundary(ctx.server_src, wmod + '\nfrom core.database import db_session\n')
    check('s129 mutation caught: the engine given database access', not m['no storage'])

    js = ctx.BASE.joinpath('static/js/teaching/willingness.js').read_text(encoding='utf-8')
    paths = ctx.BASE.joinpath('static/js/teaching/paths.js').read_text(encoding='utf-8')
    # What the user reads: the page's text without its comments, and the route's refusals.
    shown = re.sub(r'/\*.*?\*/', '', js, flags=re.S)
    shown = '\n'.join(line.split(' // ')[0] for line in shown.splitlines() if not line.strip().startswith('//'))
    words = shown + '\n'.join(re.findall(r"err\('([^']*)'", _function_src(ctx.server_src, 'willingness_declare')))
    stick = [p for p in (r'you said you', r'\bbut you\b', r'\bfail', r'should have', r'promis', r'supposed to',
                         r'you didn.t', r'you did not') if re.search(p, words, re.I)]
    probe = words + "\n'You said you would cut Dining, but you did not.'"
    check('s129 mutation caught: a scolding line added to what the user reads',
          any(re.search(p, probe, re.I) for p in (r'you said you', r'\bbut you\b')))
    check('s129 F.4 no line sets the user\'s word against their behaviour as a failing', not stick)
    if stick:
        print(f'        found: {stick}')
    empty = js.split('if (!claims.length && !answered.length && !history.length) {', 1)[-1].split('var out = head;', 1)[0]
    check('s129 Wl1 the empty state offers no controls - nothing to dispute, nothing to set (F.3)',
          'return head' in empty and '_control(' not in empty and 'data-gw-declare' not in empty)
    check('s129 the empty state says it never learns from pages opened or suggestions dismissed',
          'never learns from which' in js and 'pages you open or which suggestions you dismiss' in js)
    check('s129 in context: a path naming a category can be answered where it stands ("never X")',
          '_answerable(items.map(i => i.name), said)' in paths and 'window._gwDeclareInline' in paths)
    check('s129 Wl13 app.js and index.html know nothing of the layer (the seam holds)',
          not re.search(r'willingness|view-picture|_gwDeclare|Working picture', ctx.app_src, re.I)
          and 'view-picture' not in ctx.BASE.joinpath('static/index.html').read_text(encoding='utf-8'))

    # Wl12: the upgrade. A database stored at the previous version gains the table on start - s51's
    # fingerprint cannot see a model-only table, so this is what proves the bump does its job.
    with engine.begin() as conn:
        conn.execute(text('DROP TABLE IF EXISTS willingness_declarations'))
        conn.execute(text("UPDATE app_settings SET value = '20260927-cloud-ai-removed' WHERE key = 'schema_version'"))
        gone = not conn.execute(text("SELECT name FROM sqlite_master WHERE name='willingness_declarations'")).fetchone()
    migrate.run_migration_if_needed()
    with engine.connect() as conn:
        back = bool(conn.execute(text("SELECT name FROM sqlite_master WHERE name='willingness_declarations'")).fetchone())
        ver = conn.execute(text("SELECT value FROM app_settings WHERE key='schema_version'")).scalar()
    check('s129 Wl12 a database at the previous SCHEMA_VERSION gains willingness_declarations on start',
          gone and back and ver == migrate.SCHEMA_VERSION)
    check('s129 the bump is recorded: SCHEMA_VERSION moved past the cloud-removal version',
          migrate.SCHEMA_VERSION != '20260927-cloud-ai-removed')
