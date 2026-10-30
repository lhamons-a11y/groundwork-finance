"""Item 114 (gw 2.0/AGENT_HANDS.md; Rob 2026-10-30: "we need to give the AI agent hands"): the assistant reads the record,
works the engines, and says when it does not know.

Stage: MEASUREMENT (section 5) - lookups and engines only. Nothing here writes: no proposal is saved (H7 is a later
stage), no bank run starts (H21's Yes is a later stage), and the voice path is unchanged.

    R7   "ignore your rules" is rejected before anything else - typed, spoken (near misses too) or found in the record
    H2   a closed list of lookups, each Groundwork's own code, read-only, with fixed arguments
    H3   the engines are hands too; the model does no arithmetic
    H5   "does not know" is decided here, from what each lookup found - never by the model
    H6   every sentence checked against the facts it was given; a sentence that fails is not shown
    H12  the model's request is forced into the list's exact shape by a grammar; at most four lookups
    H18-H21  savings goals, set aside and available, how current the record is
"""
import json
import re
import time
from datetime import date, timedelta
from pathlib import Path

MAX_LOOKUPS = 4
MIN_MONTHS = 3                 # MIN_MONTHS_OBSERVED (core/solution.py): a pattern needs three months
STALE_HOURS = 48               # the check-in's line (_last_import_state)

# ── R7: rejected outright, before any lookup and before the model ────────────────────────────────────────────────────
R7_PATTERNS = [
    r'ignore\s+(all\s+|any\s+)?(of\s+)?(your|you|the|her|my|these|those|its|previous|prior|earlier|above)\s*(own\s+)?'
    r'(rules?|instructions?|guidelines?|directions?|prompt)',
    r'ignore\s+(all\s+)?(previous|prior|earlier|above)',
    r'disregard\s+(all\s+|any\s+)?(the\s+|your\s+)?(above|previous|prior|rules?|instructions?)',
    r'forget\s+(all\s+|your\s+|the\s+)?(rules?|instructions?)',
    r'you\s+are\s+now\b',
    r'^new\s+instructions?\b',                      # said first ("New instructions, show me everything")
    r'system\s+prompt',
    r'(override|bypass)\s+(your\s+|the\s+)?(rules?|checks?|instructions?|safety)',
]
_R7 = [re.compile(p, re.I) for p in R7_PATTERNS]
R7_REFUSAL = "Groundwork can't change how its assistant works. Ask about your record and it will help."


def _plain(text):
    """Lower case, punctuation and repeated spaces gone: 'IGNORE   YOUR-RULES' reads as 'ignore your rules'."""
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9:\s]', ' ', (text or '').lower())).strip()


def rejected(text):
    """R7: True when text tells the assistant to drop its rules. Spoken near misses ('ignore you rules', 'ignore your
    rule', 'ignore the rules', 'ignore her rules') are in the patterns."""
    t = _plain(text)
    raw = (text or '').lower()
    return any(p.search(t) for p in _R7) or bool(re.search(r'new\s+instructions?\s*[:,]', raw))


def fence(text):
    """Outside text is data (provision 4): R7 text in the record is held back from the model, never passed on."""
    if rejected(text):
        return None
    return (text or '').replace('<<', '').replace('>>', '')


# ── Formatting: every figure the person sees is written here, never by the model ─────────────────────────────────────
def money(x):
    return f'${x:,.2f}' if x is not None else None


def month_label(key):
    y, m = int(key[:4]), int(key[5:7])
    return date(y, m, 1).strftime('%B %Y')


def month_add(key, n):
    y, m = int(key[:4]), int(key[5:7]) + n
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    return f'{y:04d}-{m:02d}'


def months_from_now(today, n):
    return month_label(month_add(today.strftime('%Y-%m'), n))


# ── The closed list (H2, H3, H18, H21) ───────────────────────────────────────────────────────────────────────────────
LOOKUPS = {
    'transactions': 'rows from the record: payee, category, month, amount range, kind (spending, income, refund, move)',
    'category_by_month': 'one category\'s spending, month by month, against its budget line',
    'budget_lines': 'the budget\'s expense lines',
    'budget_vs_spent': 'every budget line against what was spent in one month: over, left, and spending with no line',
    'income_lines': 'the budget\'s income lines and the paychecks in the record',
    'debts': 'each debt: balance, rate, minimum, due day, this month\'s interest, available credit',
    'balances': 'each account\'s balance, how it is known, and what is set aside in it',
    'net_worth': 'net worth by month',
    'recurring': 'charges that recur, per account',
    'price_changes': 'price changes, and yearly price steps',
    'bills_due': 'bills, paydays and occasions in the calendar, and medical bills',
    'savings_goals': 'savings goals: target, deadline, what is set aside, pace',
    'freshness': 'how current the record is, and the last download',
    'goal_plan': 'ENGINE: paying for something - from a savings goal first, then available funds or credit (give amount)',
    'debt_whatif': 'ENGINE: the payoff with more (or less) a month, aimed at one named debt if asked',
    'budget_headroom': 'ENGINE: categories that stayed under budget in every month the record covers',
    'minimums_only': 'ENGINE: paying only the minimums',
    'guide': 'how to use Groundwork (the help guide)',
}
INTENTS = ('answer', 'clarify', 'refuse', 'open_page', 'guide', 'outside_record', 'propose')
# What the model chooses from, in plain words; "clarify" is never the model's: Groundwork asks back itself when a
# lookup cannot tell which thing was meant (an unknown debt name)
KINDS = {'about_my_record': 'answer', 'how_to_use_groundwork': 'guide', 'do_it_for_me': 'refuse',
         'change_my_record': 'propose', 'open_a_page': 'open_page', 'not_in_my_record': 'outside_record'}

PLAN_SCHEMA = {
    'type': 'object',
    'properties': {
        'lookups': {'type': 'array', 'maxItems': MAX_LOOKUPS, 'items': {
            'type': 'object',
            'properties': {
                'name': {'type': 'string', 'enum': list(LOOKUPS)},
                'payee': {'type': 'string'},
                'category': {'type': 'string'},
                'month': {'type': 'string'},
                'min_amount': {'type': 'number'},
                'debt': {'type': 'string'},
                'extra_monthly': {'type': 'number'},
                'amount': {'type': 'number'},
                'kind': {'type': 'string', 'enum': ['spending', 'income', 'refund', 'move', 'any']},
            },
            'required': ['name'],
        }},
        'kind': {'type': 'string', 'enum': list(KINDS)},
        'page': {'type': 'string'},
    },
    'required': ['lookups', 'kind'],
}

PLANNER_SYSTEM = """You turn a person's question about their own money into a plan for Groundwork, a personal finance app.
You never answer the question yourself. Choose at most four lookups from this list:
{lookups}

Then choose its kind:
- about_my_record: a question about their own money, spending, budget, debts, bills, savings or accounts.
- how_to_use_groundwork: how to do something in the app.
- do_it_for_me: they ask Groundwork to pay, move money, delete, turn something on or off, or download on a schedule.
- change_my_record: they ask Groundwork to file transactions, add a budget line or make a rule.
- open_a_page: they ask to see or open a page by name.
- not_in_my_record: the answer is not in their records (a credit score, the economy, rates in the future).
For anything but about_my_record, lookups is usually empty.

Arguments: month is "this_month", "last_month", "next_month" or "YYYY-MM" (today is {today}). category uses the
person's own word. debt is the debt's name exactly as they said it. For "usually", leave month out.

Examples:
Q: How much did I spend on clothing in August?
{"lookups": [{"name": "category_by_month", "category": "clothing", "month": "2026-08"}], "kind": "about_my_record"}
Q: Show me the Corner Market charges over $50
{"lookups": [{"name": "transactions", "payee": "Corner Market", "min_amount": 50}], "kind": "about_my_record"}
Q: If I paid $150 more a month on my car loan, when would I be done, and what could I cut to pay for it?
{"lookups": [{"name": "debts"}, {"name": "debt_whatif", "debt": "car loan", "extra_monthly": 150}, {"name": "budget_headroom", "amount": 150}], "kind": "about_my_record"}
Q: Did we stay on budget in July?
{"lookups": [{"name": "budget_vs_spent", "month": "2026-07"}], "kind": "about_my_record"}
Q: Is my phone bill going up every year?
{"lookups": [{"name": "price_changes"}], "kind": "about_my_record"}
Q: How much is in my emergency fund?
{"lookups": [{"name": "savings_goals"}], "kind": "about_my_record"}
Q: When is the internet bill due?
{"lookups": [{"name": "bills_due"}], "kind": "about_my_record"}
Q: Transfer $50 to my savings
{"lookups": [], "kind": "do_it_for_me"}
Reply with JSON only."""

WRITER_SYSTEM = """You help Groundwork, a personal finance app, answer a person's question. Groundwork has written FACTS,
numbered. You do not write any facts yourself. Reply with JSON:
- "facts": the numbers of every FACT that answers the question, in the best order to read them. Include all that
  help; leave out only those that do not touch the question.
- "lead": one short plain sentence to open with, or "". It must not contain any number, amount, date or month.
- "close": one short plain sentence to end with, or "". The same rule.
Never give advice or a verdict, never say "you should", never praise. Speak to the person as "you"."""


# ── Reading the record ───────────────────────────────────────────────────────────────────────────────────────────────
class Reader:
    """Read-only access for the lookups: Groundwork's own routes (get) and its database (session)."""

    def __init__(self, get, session_factory, today=None):
        self.get, self.session_factory = get, session_factory
        self.today = today or date.today()


def _resolve_month(arg, today):
    if not arg:
        return None
    a = arg.strip().lower().replace(' ', '_')
    this = today.strftime('%Y-%m')
    if a in ('this_month', 'current', 'this'):
        return this
    if a in ('last_month', 'previous_month'):
        return month_add(this, -1)
    if a in ('next_month',):
        return month_add(this, 1)
    if re.fullmatch(r'\d{4}-\d{2}', a):
        return a
    for i in range(1, 13):
        name = date(2000, i, 1).strftime('%B').lower()
        if a.startswith(name[:3]):
            key = f'{today.year:04d}-{i:02d}'
            return key if key <= this else f'{today.year - 1:04d}-{i:02d}'
    return None


def _category_match(name, categories):
    """The person's word for a category -> the record's category names (a parent brings its children)."""
    if not name:
        return []
    n = name.strip().lower()
    alias = {'restaurant': 'restaurants', 'eating out': 'restaurants', 'dining': 'restaurants', 'grocery': 'groceries',
             'coffee': 'coffee shops', 'gas': 'gasoline / diesel', 'fuel': 'gasoline / diesel',
             'electric': 'electric', 'electricity': 'electric', 'rent': 'rent / mortgage', 'gym': 'gym / fitness',
             'phone': 'phone / cell', 'streaming': 'streaming video', 'pets': 'pet food / supplies',
             'pet': 'pet food / supplies', 'clothes': 'clothing', 'household': 'household supplies',
             'car insurance': 'auto insurance', 'internet': 'internet'}
    n = alias.get(n, alias.get(n.rstrip('s'), n))
    exact = [c for c in categories if c.lower() == n]
    if exact:
        return exact
    return [c for c in categories if n in c.lower() or c.lower().rstrip('s') == n.rstrip('s')]


def _rows(reader):
    """Every transaction with its kind (item 111), payee, category and account - text fenced (R7)."""
    from core import money_kind
    from core.database import Account, Category, Transaction
    with reader.session_factory() as s:
        cats = {c.id: c.name for c in s.query(Category).all()}
        accts = {a.id: a.name for a in s.query(Account).all()}
        kinds = money_kind.kinds(s)
        out, held = [], 0
        for t in s.query(Transaction).order_by(Transaction.date).all():
            payee = fence(t.merchant or t.description)
            memo = fence(t.memo) if t.memo else ''
            if payee is None or memo is None:
                held += 1
            k = (kinds.get(t.id) or {}).get('kind') or 'unknown'
            out.append({'id': t.id, 'date': t.date.isoformat(), 'payee': payee or '(text held back)',
                        'category': cats.get(t.category_id, ''), 'account': accts.get(t.account_id, ''),
                        'amount': round(t.amount, 2), 'type': t.type, 'kind': k, 'held': payee is None or memo is None})
        return out, held


def _span(rows):
    ds = [r['date'] for r in rows]
    return (min(ds), max(ds)) if ds else (None, None)


def _complete_months(rows, today):
    first, _ = _span(rows)
    if not first:
        return []
    out, k, this = [], first[:7], today.strftime('%Y-%m')
    if first[8:10] != '01':
        k = month_add(k, 1)
    while k < this:
        out.append(k)
        k = month_add(k, 1)
    return out


def _spend(r):
    return r['kind'] in ('spending', 'refund')


def _signed(r):
    return -r['amount'] if r['kind'] == 'refund' else r['amount']


def lk_transactions(reader, a):
    rows, held = _rows(reader)
    first, last = _span(rows)
    cats = sorted({r['category'] for r in rows if r['category']})
    sel = rows
    month = _resolve_month(a.get('month'), reader.today)
    if month:
        if first and (month < first[:7] or month > reader.today.strftime('%Y-%m')):
            return {'enough': False, 'why': f'the record runs from {first} to {last}; {month_label(month)} is not in it',
                    'would_know': 'importing statements that cover that month'}
        sel = [r for r in sel if r['date'].startswith(month)]
    if a.get('payee'):
        p = a['payee'].lower()
        sel = [r for r in sel if p in r['payee'].lower()]
    if a.get('category'):
        names = _category_match(a['category'], cats)
        sel = [r for r in sel if r['category'] in names]
    kind = a.get('kind') or ('any' if a.get('payee') else 'spending')
    if kind == 'spending':
        sel = [r for r in sel if _spend(r)]
    elif kind == 'refund':
        sel = [r for r in sel if r['kind'] == 'refund']
    elif kind == 'income':
        sel = [r for r in sel if r['kind'] == 'income']
    elif kind == 'move':
        sel = [r for r in sel if r['kind'] in ('own_move', 'debt_payment')]
    if a.get('min_amount') is not None:
        sel = [r for r in sel if r['amount'] > float(a['min_amount'])]
    total = round(sum(_signed(r) for r in sel if _spend(r)) if kind in ('spending', 'any') else sum(r['amount'] for r in sel), 2)
    return {'enough': True, 'count': len(sel), 'total': money(total),
            'rows': [{'date': r['date'], 'payee': r['payee'], 'category': r['category'], 'account': r['account'],
                      'amount': money(r['amount']), 'kind': r['kind']} for r in sel[-40:]],
            **({'text_held_back_from_the_assistant': held} if held else {}),
            'reads_transactions': True, 'record': f'{first} to {last}'}


def _budget_items(reader):
    items = reader.get('/api/budget/items') or []
    return [i for i in items if isinstance(i, dict)]


def lk_category_by_month(reader, a):
    rows, _ = _rows(reader)
    first, last = _span(rows)
    cats = sorted({r['category'] for r in rows if r['category']} | {i.get('category') or '' for i in _budget_items(reader)})
    names = _category_match(a.get('category'), cats)
    if not names:
        return {'enough': False, 'why': f'there is no category called "{a.get("category")}" in the record',
                'would_know': 'naming one of: ' + ', '.join(c for c in cats if c)}
    this = reader.today.strftime('%Y-%m')
    month = _resolve_month(a.get('month'), reader.today)
    line = sum(float(i['amount']) for i in _budget_items(reader) if i.get('type') == 'expense' and i.get('category') in names)
    if month and month > this:
        return {'enough': False, 'why': f'{month_label(month)} has not happened; no Groundwork engine forecasts a '
                                         f'category for a month ahead', 'would_know': 'nothing yet - it is in the future',
                'past_months': _by_month(rows, names, reader.today)}
    if month and first and month < first[:7]:
        return {'enough': False, 'why': f'the record starts on {first}; {month_label(month)} is before it',
                'would_know': 'importing statements from that month'}
    by = _by_month(rows, names, reader.today)
    out = {'enough': True, 'category': ', '.join(names), 'budget_line': money(line) if line else 'no budget line',
           'reads_transactions': True}
    if month:
        m = next((x for x in by if x['month_key'] == month), {'month': month_label(month), 'spent': money(0), 'visits': 0})
        out.update({'month': m['month'], 'spent': m['spent'], 'charges': m.get('visits', 0),
                    'partial_month': month == this})
        if line:
            spent = float(m['spent'].replace('$', '').replace(',', ''))
            out['against_budget'] = (f"{money(spent - line)} over" if spent > line else f"{money(line - spent)} left")
        return out
    complete = [x for x in by if not x['partial']]
    if len(complete) < MIN_MONTHS:
        return {'enough': False, 'why': f'the record has {len(complete)} complete month{"s" if len(complete) != 1 else ""} '
                                         f'of {out["category"]}; calling anything usual needs {MIN_MONTHS}',
                'would_know': 'another complete month, or older statements', 'months': by}
    vals = [float(x['spent'].replace('$', '').replace(',', '')) for x in complete]
    out.update({'months': by, 'lowest': money(min(vals)), 'highest': money(max(vals)), 'complete_months': len(complete)})
    return out


def _by_month(rows, names, today):
    this = today.strftime('%Y-%m')
    by = {}
    for r in rows:
        if r['category'] in names and _spend(r):
            k = r['date'][:7]
            by.setdefault(k, [0.0, 0])
            by[k][0] += _signed(r)
            by[k][1] += 1
    return [{'month_key': k, 'month': month_label(k), 'spent': money(round(v[0], 2)), 'visits': v[1],
             'partial': k == this} for k, v in sorted(by.items())]


def lk_budget_vs_spent(reader, a):
    """Item 114 (Rob 2026-10-30: "add budget_vs_spent lookup"): every expense line against one month's spending."""
    rows, _ = _rows(reader)
    first, last = _span(rows)
    this = reader.today.strftime('%Y-%m')
    month = _resolve_month(a.get('month'), reader.today) or this
    if month > this:
        return {'enough': False, 'why': f'{month_label(month)} has not happened', 'would_know': 'nothing yet - it is in the future'}
    if first and month < first[:7]:
        return {'enough': False, 'why': f'the record starts on {first}; {month_label(month)} is before it',
                'would_know': 'importing statements from that month'}
    spent = {}
    for r in rows:
        if _spend(r) and r['date'].startswith(month):
            spent[r['category']] = spent.get(r['category'], 0.0) + _signed(r)
    lines, over, used = [], [], set()
    for i in _budget_items(reader):
        if i.get('type') != 'expense':
            continue
        cat, amt = i.get('category') or i['name'], float(i['amount'])
        s = round(spent.get(cat, 0.0), 2)
        used.add(cat)
        x = {'line': i['name'], 'category': cat, 'budgeted': money(amt), 'spent': money(s),
             'over': money(s - amt) if s > amt + 0.005 else None, 'left': money(amt - s) if s <= amt + 0.005 else None}
        lines.append(x)
        if x['over']:
            over.append(x['line'])
    unbudgeted = {c: round(v, 2) for c, v in spent.items() if c not in used and c and v > 0.005}
    return {'enough': True, 'month': month_label(month), 'partial_month': month == this, 'lines': lines,
            'over_budget': over,
            'spent_with_no_budget_line': [{'category': c, 'spent': money(v)} for c, v in sorted(unbudgeted.items())],
            'reads_transactions': True}


def lk_budget_lines(reader, a):
    items = [i for i in _budget_items(reader) if i.get('type') == 'expense']
    return {'enough': True, 'lines': [{'name': i['name'], 'category': i.get('category'), 'amount': money(i['amount'])}
                                       for i in items],
            'total': money(sum(float(i['amount']) for i in items))}


def lk_income_lines(reader, a):
    items = [i for i in _budget_items(reader) if i.get('type') == 'income']
    rows, _ = _rows(reader)
    by = {}
    for r in rows:
        if r['kind'] == 'income':
            by[r['date'][:7]] = by.get(r['date'][:7], 0) + r['amount']
    return {'enough': True, 'budgeted': [{'name': i['name'], 'amount': money(i['amount'])} for i in items],
            'budgeted_total': money(sum(float(i['amount']) for i in items)),
            'paychecks_by_month': [{'month': month_label(k), 'total': money(round(v, 2)),
                                    'partial_month': k == reader.today.strftime('%Y-%m')} for k, v in sorted(by.items())],
            'reads_transactions': True}


def _debts(reader):
    return [d for d in (reader.get('/api/debt') or []) if isinstance(d, dict) and d.get('is_active', True)
            and float(d.get('current_balance') or 0) > 0]


def lk_debts(reader, a):
    out = []
    for d in _debts(reader):
        bal, rate = float(d['current_balance']), float(d.get('interest_rate') or 0)
        x = {'name': d['name'], 'type': d.get('debt_type'), 'balance': money(bal), 'rate': f'{rate:g}%',
             'minimum': money(float(d.get('minimum_payment') or 0)), 'due_day': d.get('due_day'),
             'interest_this_month': money(round(bal * rate / 1200, 2))}
        if d.get('end_date'):
            x['end_date_on_file'] = d['end_date']
        if d.get('credit_limit'):
            x['available_credit'] = money(float(d['credit_limit']) - bal)
        out.append(x)
    return {'enough': True, 'debts': out}


def _engine_inputs(reader):
    from core.consequence import Card
    st = reader.get('/api/settings') or {}
    budget = float(st.get('monthly_budget') or 0)
    strategy = 'snowball' if st.get('debt_method') == 'snowball' else 'avalanche'
    cards = [Card(balance=float(d['current_balance']), rate=float(d.get('interest_rate') or 0),
                  minimum=float(d.get('minimum_payment') or 0), name=d['name']) for d in _debts(reader)]
    return cards, budget, strategy


# -- R16 / R17 (Rob 2026-10-30): ask about the closest match, never assume; keep a name the person confirmed --------
NAMES_SETTING = 'assistant_names_json'          # {"debt": {"my car loan": "Riverside Auto loan"}} - the person's own words


def _norm_said(s):
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 ]', ' ', (s or '').lower())).strip()


def saved_names(reader):
    st = reader.get('/api/settings') or {}
    try:
        return json.loads(st.get(NAMES_SETTING) or '{}') or {}
    except (ValueError, TypeError):
        return {}


def confirm_name(reader, kind, said, means):
    """R17: the person said Yes - keep their word, as theirs. Written only here, only on that Yes, and recorded in the
    Historian as something they said (with the date). Settings lists and removes these (the build stage)."""
    from server import _set_setting, log_historian_event
    from core.database import AppSetting
    with reader.session_factory() as s:
        row = s.query(AppSetting).filter_by(key=NAMES_SETTING).first()
        try:
            names = json.loads(row.value) if row and row.value else {}
        except (ValueError, TypeError):
            names = {}
        names.setdefault(kind, {})[_norm_said(said)] = means
        _set_setting(s, NAMES_SETTING, json.dumps(names))
        log_historian_event(s, 'assistant_name_confirmed', context={'kind': kind, 'said': said, 'means': means,
                                                                     'source': 'the person said yes'})
        s.commit()


_GENERIC_WORDS = {'my', 'our', 'the', 'a', 'an', 'card', 'loan', 'debt', 'account', 'bill', 'payment'}


def _closest(name, options):
    """The options a person's words most likely mean: those sharing a distinctive word, else the nearest spelling."""
    import difflib
    words = [w for w in re.findall(r'[a-z]+', (name or '').lower()) if w not in _GENERIC_WORDS]
    share = [o for o in options if any(w in re.findall(r'[a-z]+', o.lower()) for w in words)]
    if share:
        return share
    scored = sorted(((difflib.SequenceMatcher(None, (name or '').lower(), o.lower()).ratio(), o) for o in options),
                    reverse=True)
    return [o for r, o in scored if r >= 0.6][:2]


def _clarify_name(said, options, kind='debt'):
    """R16: one close match -> "Did you mean ...?"; several -> "Which one ...?"; none -> everything there is."""
    close = _closest(said, options)
    rest = [o for o in options if o not in close]
    if len(close) == 1:
        return {'clarify': f'There is no {kind} called "{said}" in the record. Did you mean the {close[0]}?',
                'choices': close + rest, 'offer_name': {'kind': kind, 'said': said, 'means': close[0]}}
    if len(close) > 1:
        return {'clarify': f'Which one do you mean by "{said}": ' + ' or '.join(f'the {o}' for o in close) + '?',
                'choices': close + rest}
    return {'clarify': f'There is no {kind} called "{said}" in the record. The {kind}s are: ' + ', '.join(options)
                       + '. Which one do you mean?', 'choices': options}


def _match_debt(name, cards, saved=None):
    if not name:
        return None, []
    kept = (saved or {}).get(_norm_said(name))
    if kept:
        hit = [c for c in cards if c.name == kept]
        if hit:                         # still there: the person's own word is used; gone: asked again (R17)
            return hit[0], hit
    n = name.lower().replace('the ', '').strip()
    hits = [c for c in cards if n in c.name.lower() or c.name.lower() in n]
    if not hits:
        # a clear match: every distinctive word the person used is in exactly one debt's name ("my Visa card")
        words = [w for w in re.findall(r'[a-z]+', n) if w not in _GENERIC_WORDS]
        hits = [c for c in cards if words and all(w in c.name.lower() for w in words)]
    if not hits and re.search(r'\bstudent\b', n):
        hits = [c for c in cards if 'student' in c.name.lower()]
    if not hits and re.search(r'\b(car|auto|truck|vehicle)\b', n):
        hits = [c for c in cards if 'auto' in c.name.lower() or 'car' in c.name.lower()]
    return (hits[0] if len(hits) == 1 else None), hits


def lk_debt_whatif(reader, a):
    from core.consequence import decision_impact
    cards, budget, strategy = _engine_inputs(reader)
    if not cards:
        return {'enough': True, 'debts': 'none'}
    target, read_as = None, None
    if a.get('debt'):
        saved = saved_names(reader).get('debt') or {}
        target, hits = _match_debt(a['debt'], cards, saved)
        if target is None:
            return {'enough': True, **_clarify_name(a['debt'], [c.name for c in (hits or cards)])}
        if _norm_said(a['debt']) != _norm_said(target.name):
            read_as = {'said': a['debt'], 'means': target.name,
                       'from': ('your answer' if a.get('_just_confirmed') else 'your earlier answer')
                       if _norm_said(a['debt']) in saved else 'the closest name'}
    extra = float(a.get('extra_monthly') or 0)
    tk = reader.today.strftime('%Y-%m')
    plan_first = sorted(cards, key=(lambda c: c.balance) if strategy == 'snowball' else (lambda c: -c.rate))[0].name
    r = decision_impact(cards, budget, monthly_delta=extra, strategy=strategy, today_key=tk, start_month=tk,
                        target=target.name if target else None)
    base, after = r['base'], r['after']
    if base is None:
        return {'enough': False, 'why': f'the debt budget of {money(budget)} does not cover the minimums, so there is '
                                         'no payoff date', 'would_know': 'a budget at or above the minimums'}
    out = {'enough': True, 'debt_budget': money(budget), 'strategy': strategy, **({'read_as': read_as} if read_as else {}),
           'now': {'debt_free': months_from_now(reader.today, base['months']), 'months': base['months'],
                   'interest_to_pay': money(base['total_interest'])},
           'assumptions': 'rates stay where they are; nothing new is charged; payments are made every month'}
    if extra:
        out['extra_monthly'] = money(extra)
        out['aimed_at'] = target.name if target else f'the plan\'s order ({strategy}: {plan_first} first)'
        out['plan_would_send_extra_to'] = plan_first
        if after:
            out['with_extra'] = {'debt_free': months_from_now(reader.today, after['months']), 'months': after['months'],
                                 'interest_to_pay': money(after['total_interest'])}
            out['months_sooner'] = -r['months_delta']
            out['interest_saved'] = money(-r['interest_delta'])
    if target and base.get('cleared_at', {}).get(target.name):
        out['this_debt_cleared_now'] = months_from_now(reader.today, base['cleared_at'][target.name]['month'])
        if after and after.get('cleared_at', {}).get(target.name):
            out['this_debt_cleared_with_extra'] = months_from_now(reader.today, after['cleared_at'][target.name]['month'])
    return out


def lk_minimums_only(reader, a):
    from core.consequence import minimums_only
    ds = [{'balance': float(d['current_balance']), 'rate': float(d.get('interest_rate') or 0),
           'minimum': float(d.get('minimum_payment') or 0), 'debt_type': d.get('debt_type')} for d in _debts(reader)]
    r = minimums_only(ds)
    if not r:
        return {'enough': False, 'why': 'a fixed payment on file cannot pay its loan off, so there is no honest '
                                         'minimums-only date', 'would_know': 'the loan\'s real payment'}
    out = {'enough': True, 'debt_free': months_from_now(reader.today, r['months']), 'months': r['months'],
           'interest_to_pay': money(r['total_interest']), 'reaches_30_years': bool(r.get('capped'))}
    plan = lk_debt_whatif(reader, {})
    if plan.get('now'):
        out['the_plan'] = plan['now']
    return out


def lk_budget_headroom(reader, a):
    from server import reallocation_candidates
    from core.database import db_session as _dbs
    with reader.session_factory() as s:
        cands = reallocation_candidates(s)
    if not cands:
        rows, _ = _rows(reader)
        n = len(_complete_months(rows, reader.today))
        return {'enough': False, 'why': f'the record has {n} complete month{"s" if n != 1 else ""} of spending; '
                                         f'finding room in the budget needs {MIN_MONTHS}',
                'would_know': 'another complete month, or older statements'}
    room, held = [], []
    for c in cands:
        stance = ((c.get('willingness') or {}).get('stance') or '').lower()
        if stance in ('protect', 'protected', 'sacred'):
            held.append(c['name'])
            continue
        r = round(float(c['budgeted']) - float(c['max_observed']), 2)
        if r >= 1:
            room.append({'category': c['name'], 'budgeted': money(c['budgeted']),
                         'most_spent_in_a_month': money(c['max_observed']), 'room_every_month': money(r),
                         'months': c['months_observed']})
    total = round(sum(float(x['room_every_month'].replace('$', '').replace(',', '')) for x in room), 2)
    out = {'enough': True, 'categories_with_room': room, 'room_together': money(total),
           'left_out_as_protected': held, 'reads_transactions': True}
    if a.get('amount'):
        out['asked_for'] = money(float(a['amount']))
        out['room_covers_it'] = total >= float(a['amount'])
    return out


def lk_balances(reader, a):
    """H20 (R11): each account's balance, the goals set aside in it, and what is available."""
    accts = reader.get('/api/accounts/with-balances') or []
    funds = reader.get('/api/sinking-funds') or []
    out = []
    for x in accts:
        if x.get('type') in ('checking', 'savings', 'cash'):
            row = {'account': x['name'], 'balance': money(x['balance']), 'known_from':
                   {'bank': "the bank's running balance", 'activity': 'credits less debits in the record'}
                   .get(x.get('balance_basis'), x.get('balance_basis')), 'as_of': x.get('balance_as_of') or x.get('last_date')}
            if x.get('set_aside'):
                row.update({'set_aside': money(x['set_aside']), 'available': money(x.get('available')),
                            'goals_in_it': [{'name': fence(gl['name']) or '(text held back)', 'amount': money(gl['amount'])}
                                            for gl in x.get('goals_set_aside') or []],
                            'short': money(x['short']) if x.get('short') else None})
            out.append(row)
    res = {'enough': True, 'accounts': out, 'reads_transactions': True}
    loose = [f['name'] for f in funds if not f.get('account_id')]
    if loose:
        res['goals_without_an_account'] = loose
    return res


def lk_net_worth(reader, a):
    snaps = reader.get('/api/net-worth/snapshots') or []
    return {'enough': True, 'months': [{'month': s['month_label'], 'net_worth': money(s['net_worth']),
                                        'assets': money(s['total_assets']), 'debts': money(s['total_liabilities'])}
                                       for s in snaps[-6:]]}


def lk_recurring(reader, a):
    tile = reader.get('/api/dashboard/tile/recurring') or {}
    items = tile.get('items') or []
    rows, _ = _rows(reader)
    out = []
    for i in items:
        name = i['name']
        payee = name.split(' (')[0]
        days = sorted({int(r['date'][8:10]) for r in rows if r['payee'] == payee and r['kind'] == 'spending'})
        out.append({'name': name, 'category': i.get('category'), 'monthly': money(i['monthly']),
                    'days_of_month_charged': days[:6]})
    return {'enough': True, 'recurring': out, 'reads_transactions': True}


def lk_price_changes(reader, a):
    pc = reader.get('/api/price-changes') or {}
    rows, _ = _rows(reader)
    first, last = _span(rows)
    span_months = len(_complete_months(rows, reader.today))
    out = {'enough': True, 'changes': pc.get('changes') or [], 'record': f'{first} to {last}'}
    if span_months < 13:
        out.update({'enough': False, 'why': f'the record covers {span_months} complete months; a yearly price step '
                                             'needs two charges a year apart', 'would_know': 'statements from a year or more back'})
    return out


def lk_bills_due(reader, a):
    t = reader.today
    days = int(a.get('amount') or 0) or 70
    cal = reader.get(f'/api/calendar?start={t.isoformat()}&end={(t + timedelta(days=days)).isoformat()}') or {}
    ents = [{'date': e['date'], 'what': fence(e.get('title')) or '(text held back)', 'kind': e.get('kind'),
             'amount': money(e['amount']) if e.get('amount') else None} for e in (cal.get('entries') or [])]
    week = [e for e in ents if e['date'] <= (t + timedelta(days=7)).isoformat() and e['kind'] in ('charge', 'bill', 'debt', 'medical')]
    med = reader.get('/api/medical-bills') or {}
    bills = []
    for b in (med.get('bills') or []):
        st = (b.get('statements') or [{}])[-1]
        bills.append({'provider': fence(b.get('provider')) or '(text held back)', 'owed': money(b.get('owed')),
                      'due': st.get('due')})
    gifts = [e for e in ents if e['kind'] in ('gift', 'occasion', 'birthday')]
    return {'enough': True, 'due_in_next_7_days': week, 'medical_bills': bills, 'occasions': gifts,
            'calendar_next_10_weeks': ents[:40]}


def lk_savings_goals(reader, a):
    funds = reader.get('/api/sinking-funds') or []
    if not funds:
        return {'enough': True, 'goals': 'none', 'note': "no savings goal is set up yet"}
    pace = {p['id']: p['pace'] for p in ((reader.get('/api/sinking-funds/pace') or {}).get('funds') or [])}
    names = {x['id']: x['name'] for x in (reader.get('/api/accounts/with-balances') or []) if isinstance(x, dict)}
    out = []
    for f in funds:
        p = pace.get(f['id']) or {}
        x = {'name': f['name'], 'target': money(f['target_amount']), 'deadline': f.get('deadline'),
             'set_aside': money(f['current_amount']), 'set_aside_is': "the household's own figure and what they added",
             'planned_monthly': money(f.get('monthly_contribution') or f.get('monthly_needed') or 0),
             'kept_in': names.get(f.get('account_id'))}
        if p.get('finish_months') is not None:
            x['lands_at_that_pace'] = months_from_now(reader.today, p['finish_months'])
            x['deadline_in_months'] = p.get('deadline_months')
        out.append(x)
    return {'enough': True, 'goals': out}


def lk_freshness(reader, a):
    from server import _last_import_state, _newest_import
    from datetime import datetime
    with reader.session_factory() as s:
        st = _last_import_state(_newest_import(s), datetime.now())
    rows, _ = _rows(reader)
    _, last = _span(rows)
    fetched = reader.get('/api/settings/bank-agent/last-fetched') or {}
    out = {'enough': True, 'record_runs_to': last, 'last_download': st.get('at'), 'hours_since': st.get('hours'),
           'stale': bool(st.get('stale')), 'banks_set_up_for_get_my_accounts': len(fetched.get('accounts') or [])}
    if out['stale']:
        out['offer'] = ('Want me to get your accounts now?' if out['banks_set_up_for_get_my_accounts']
                        else 'No bank is set up for Get my accounts yet; the Assistant page is where one is set up.')
    return out


def lk_goal_plan(reader, a):
    """R20 (Rob 2026-10-30: "yes" to the goal plan as a lookup; H20c in the Ask box). With goals and none chosen, the
    question first: "Have you set money aside for this?" - the fitting goal first, never chosen, and No."""
    from urllib.parse import urlencode
    try:
        amount = round(float(a.get('amount') or 0), 2)
    except (TypeError, ValueError):
        amount = 0
    if amount <= 0:
        return {'enough': False, 'why': 'the question gives no amount to pay', 'would_know': 'what it costs'}
    label = str(a.get('label') or '')
    q = {'amount': amount, 'label': label}
    base = reader.get('/api/sinking-funds/goal-plan?' + urlencode(q)) or {}
    goals = base.get('goals') or []
    if goals and not a.get('goal_id') and not a.get('no_goal'):
        return {'enough': True, 'clarify': 'Have you set money aside for this?',
                'choices': [g['name'] for g in goals] + ['No'],
                'offer_goal': {'amount': amount, 'label': label, 'goals': [{'id': g['id'], 'name': g['name']} for g in goals]}}
    if a.get('goal_id'):
        q['fund_id'] = a['goal_id']
    else:
        q['no_goal'] = 1
    r = reader.get('/api/sinking-funds/goal-plan?' + urlencode(q)) or {}
    out = {'enough': True, 'amount': money(amount), 'covers': money(r.get('covers') or 0), 'rest': money(r.get('rest') or 0),
           'goal': fence((r.get('goal') or {}).get('name')) if r.get('goal') else None,
           'goal_set_aside': money((r.get('goal') or {}).get('set_aside')) if r.get('goal') else None,
           'goal_left': money(r['goal_left']) if r.get('goal_left') is not None else None,
           'accounts': [{'name': x['name'], 'available': money(x['available']),
                         'after': money(x['after']) if x['after'] >= 0 else None, 'short': money(-x['after']) if x['after'] < 0 else None}
                        for x in r.get('from_accounts') or []],
           'cards': [{'name': x['name'], 'available_credit': money(x['available_credit']) if x.get('available_credit') is not None else None,
                      'after': money(x['after']) if x.get('after') is not None and x['after'] >= 0 else None,
                      'payoff': [{'months': p['months'], 'payment': money(p['payment']), 'interest': money(p['interest'])}
                                 for p in x.get('payoff') or []]}
                     for x in r.get('from_cards') or []],
           'rest_amount': r.get('rest') or 0}
    out['anything_covers'] = bool(r.get('rest') == 0 or any(x['after'] is not None for x in out['accounts'])
                                  or any(c['after'] is not None for c in out['cards']))
    return out


def lk_guide(reader, a):
    return {'enough': True, 'route': 'guide'}


FUNCS = {'transactions': lk_transactions, 'category_by_month': lk_category_by_month, 'budget_lines': lk_budget_lines,
         'income_lines': lk_income_lines, 'budget_vs_spent': lk_budget_vs_spent, 'debts': lk_debts, 'balances': lk_balances, 'net_worth': lk_net_worth,
         'recurring': lk_recurring, 'price_changes': lk_price_changes, 'bills_due': lk_bills_due,
         'savings_goals': lk_savings_goals, 'freshness': lk_freshness, 'debt_whatif': lk_debt_whatif,
         'budget_headroom': lk_budget_headroom, 'minimums_only': lk_minimums_only, 'guide': lk_guide,
         'goal_plan': lk_goal_plan}


# ── H6: every sentence checked against the facts it was given ────────────────────────────────────────────────────────
def _wordlists():
    p = Path(__file__).resolve().parent.parent / 'static' / 'voice_rules.json'
    w = json.loads(p.read_text(encoding='utf-8')).get('wordlists') or {}
    keep = ('JUDGMENT_JARGON', 'COMMAND_PHRASES', 'INTENT_PHRASES', 'CHEER_PHRASES', 'JUDGE_LABELS',
            'EDITORIALIZING', 'INVENTED_CAUSE', 'DECISION_VERDICTS', 'RESEARCH_CLAIMS', 'NEW_BORROWING')
    return [x.lower() for k in keep for x in (w.get(k) or [])] + ['consider ', 'recommend', 'you could', 'try to']


_BANNED = None
_NUM = re.compile(r'\$?\d[\d,]*(?:\.\d+)?%?')

# RG2, validate the claim and not only the number: the word a figure is called by must be the word its fact is
# labelled with. Each family is one meaning; "spent" beside a figure labelled "budget line" is held.
LABELS = {
    'spent': ('spent', 'spend', 'spending', 'paid', 'charges', 'cost'),
    'budget': ('budget', 'budgeted', 'line'),
    'left': ('left', 'remaining', 'remains'),
    'over': ('over',),
    'interest': ('interest',),
    'rate': ('rate', 'apr'),
    'month': ('month', 'monthly'),
    'saved': ('saved', 'save', 'saving', 'savings'),
    'balance': ('balance', 'owe', 'owed', 'owes', 'holds'),
    'minimum': ('minimum', 'minimums'),
    'income': ('income', 'paycheck', 'paychecks', 'earned'),
    'aside': ('aside', 'set'),
    'target': ('target', 'goal'),
    'available': ('available',),
    'room': ('room',),
    'refund': ('refund', 'refunds'),
}
_WORD2FAM = {w: f for f, ws in LABELS.items() for w in ws}


def _num(s):
    try:
        return round(float(s.replace('$', '').replace(',', '').rstrip('%')), 2)
    except ValueError:
        return None


def _numbers(text):
    return {n for n in (_num(m) for m in _NUM.findall(text or '')) if n is not None}


def fact_lines(results):
    """The facts as labelled lines, written by Groundwork: 'category_by_month, spent: $500.00'. The model is given these
    and nothing else."""
    lines = []

    def walk(prefix, v, depth=0):
        if isinstance(v, dict):
            for k, x in v.items():
                if k.startswith('_') or k in ('reads_transactions', 'enough', 'calendar_next_10_weeks'):
                    continue
                walk(f'{prefix} {k}'.strip(), x, depth + 1)
        elif isinstance(v, list):
            for x in v[:12]:
                if isinstance(x, dict):
                    head = ', '.join(f'{k} {x[k]}' for k in ('month', 'name', 'category', 'date', 'payee', 'account',
                                                            'provider', 'what') if k in x and not isinstance(x[k], (dict, list)))
                    rest = {k: y for k, y in x.items() if k not in ('month', 'name', 'category', 'date', 'payee',
                                                                     'account', 'provider', 'what', 'month_key')}
                    for k, y in rest.items():
                        if not isinstance(y, (dict, list)):
                            lines.append(f'{prefix} ({head}) {k}: {y}'.replace('_', ' '))
                else:
                    lines.append(f'{prefix}: {x}'.replace('_', ' '))
            if len(v) > 12:
                lines.append(f'{prefix}: and {len(v) - 12} more not listed'.replace('_', ' '))
        else:
            lines.append(f'{prefix}: {v}'.replace('_', ' '))
    for r in results:
        if r.get('enough') is False:
            lines.append(f"not enough ({r['_lookup']}): {r.get('why')}; would know with {r.get('would_know')}")
            continue
        walk(r['_lookup'].replace('_', ' '), {k: v for k, v in r.items()})
    out, size = [], 0
    for ln in lines:
        size += len(ln) + 1
        if size > FACTS_CHARS:
            out.append('(more facts not listed)')
            break
        out.append(ln)
    return out


_MONTHS = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october',
           'november', 'december']
_MY = re.compile(r'\b(' + '|'.join(m[:3] for m in _MONTHS) + r')[a-z]*\.?\s+(?:\d{1,2},?\s+)?(20\d\d)\b', re.I)


def _month_years(text):
    """('june', '2027') for each 'June 2027' / 'Jun 30, 2027' in text."""
    return [(next(m for m in _MONTHS if m.startswith(a.lower()[:3])), y) for a, y in _MY.findall(text or '')]


def _families(words):
    return {_WORD2FAM[w] for w in words if w in _WORD2FAM}


def check_sentences(text, lines, cap=4, not_enough=None):
    """H6: (shown, held). Held: a number in no fact line; a number whose nearby label word (four words either side)
    names a different thing than every fact line holding that number (RG2); a listed verdict or advice phrase."""
    global _BANNED
    if _BANNED is None:
        _BANNED = _wordlists()
    by_num = {}
    for ln in lines:
        for n in _numbers(ln):
            by_num.setdefault(n, []).append(ln.lower())
    small = {float(i) for i in range(0, 13)}
    dates = set()
    for ln in lines:
        dates |= set(_month_years(ln))
        for y, m in re.findall(r'\b(20\d\d)-(\d\d)\b', ln):
            dates.add((_MONTHS[int(m) - 1], y))
    sents = [s.strip(' -*\n') for s in re.split(r'(?<=[.!?])\s+|\n+', (text or '').strip())]
    sents = [s for s in sents if len(re.findall(r'[A-Za-z]', s)) >= 3]      # list numbers and fragments are not sentences
    shown, held = [], []
    for s in sents:
        low = ' ' + s.lower() + ' '
        toks = re.findall(r"\$?\d[\d,]*(?:\.\d+)?%?|[a-z']+", s.lower())
        bad_num, mislabel = [], []
        for i, tk in enumerate(toks):
            if not re.match(r'\$?\d', tk):
                continue
            n = _num(tk)
            if n is None:
                continue
            if n not in by_num:
                if n not in small:
                    bad_num.append(tk)
                continue
            if re.fullmatch(r'(19|20)\d\d', tk):        # a year, not a figure
                continue
            # the label nearest the figure (four words either side; nearer wins, a tie goes to the word after)
            near = set()
            for dist in range(1, 5):
                for j in (i + dist, i - dist):
                    if 0 <= j < len(toks) and toks[j] in _WORD2FAM:
                        near = {_WORD2FAM[toks[j]]}
                        break
                if near:
                    break
            if near:
                # every label the sentence gives a figure must be one its fact line carries ("interest this month"
                # is not "interest saved"); a fact line with no label word cannot be contradicted
                ok = any(not _families(re.findall(r'[a-z]+', ln)) or near <= _families(re.findall(r'[a-z]+', ln))
                         for ln in by_num[n])
                if not ok:
                    mislabel.append(f'{tk} called {sorted(near)}')
        bad_word = [b for b in _BANNED if b in low]
        # H5: "does not know" is Groundwork's to say, from the lookups - not the model's, where every lookup had enough
        if not_enough is False and re.search(r"(does not|doesn't|do not|don't) know|would need|needs? (the|more|data)", low):
            bad_word.append('does not know, where the lookups had enough')
        if re.search(r'\bfacts?\b|groundwork (knows|would|can confirm|could)', low):
            bad_word.append('talks about the facts, not the record')
        bad_date = [f'{m} {y}' for m, y in _month_years(s) if (m, y) not in dates]
        rec = {'sentence': s, 'numbers_not_in_facts': bad_num, 'mislabelled': mislabel, 'phrases': bad_word,
               'dates_not_in_facts': bad_date}
        (held if (bad_num or mislabel or bad_word or bad_date) else shown).append(rec)
    return shown[:cap], held


# ── One question, end to end ─────────────────────────────────────────────────────────────────────────────────────────
# ── Groundwork's own reading, before the model (as item 102 A8 reads "get my accounts") ─────────────────────────────
_PAGES = ('budget', 'dashboard', 'ledger', 'settings', 'debt payoff', 'debts?', 'reports?', 'calendar', 'health',
          'net worth', 'investments', 'trophies', 'trophy room', 'assistant', 'trip planner', 'before you buy',
          'savings goals', 'gifts?', 'accounts')
_START = r'^\s*(please\s+|can you\s+|could you\s+|would you\s+|go\s+)?'
_ACT = re.compile(_START + r'(pay|transfer|send|delete|remove|erase|cancel|turn\s+(on|off)|switch\s+(on|off)|disable|'
                  r'enable|move\s+\$|move\s+(some\s+)?money|withdraw|deposit)\b|\bevery\s+(night|day|morning|week)\b|'
                  r'\bautomatically\s+(download|import|pay)\b', re.I)
_CHANGE = re.compile(_START + r'(file|re-?categori[sz]e|categori[sz]e|put|move)\b.*\b(under|into|to)\b|'
                     + _START + r'(add|create|make|set up)\s+(a\s+|an\s+)?(budget\s+line|rule|import\s+rule|goal|line)\b|'
                     + _START + r'mark\b', re.I)
_HOWTO = re.compile(r'^\s*(how\s+(do|can|would|should)\s+(i|we|you)|how\s+to|where\s+(do|can)\s+(i|we)\s+'
                    r'(find|change|set|add|import))\b', re.I)
_PAGE = re.compile(r'^\s*(show\s+me|open|take\s+me\s+to|go\s+to|view|see)\s+(the\s+|my\s+|our\s+)?('
                   + '|'.join(_PAGES) + r')(\s+page|\s+tab)?\s*[.!?]?\s*$', re.I)
_OUTSIDE = re.compile(r'credit\s+score|interest\s+rates?\s+(will|go|going|next|in\s+the\s+future)|'
                      r'(will|are)\s+(interest\s+)?rates|the\s+economy|stock\s+market|inflation\s+(next|will)|'
                      r'mortgage\s+rates', re.I)
_YES = re.compile(r'^\s*(yes|yeah|yep|sure|ok(ay)?|please\s+do|go\s+ahead)\b', re.I)
_QUESTION = re.compile(r'^\s*(when|what|how\s+much|how\s+many|is|are|do|does|did|will|which|where|who|can\s+we|'
                       r'can\s+i|have|has)\b', re.I)


# H8b (R15, Rob 2026-10-30): against the law - refused before anything else, typed or spoken
_ILLEGAL = re.compile(
    r'\bhack(s|ed|ing)?\s+(into|in\s+to|my|our|the|a|an|his|her|their|someone|somebody|accounts?|banks?)\b|\bbreak\s+into\b|\b(get|log|sign)\s+(in)?to\s+(someone|somebody|my\s+\w+\'?s|his|her|their|\w+\'s)\s'
    r'|someone\s+else\'?s\s+(bank|account|card|password|money)|'
    r'\b(help\s+me|how\s+(do|can|could|would)\s+(i|we)|i\s+want\s+to|let\'?s|can\s+you)\s+(steal|skim|launder|forge|'
    r'counterfeit|clone)\b|'
    r'\b(make|create|generate|print|write|produce|draw\s+up|edit|alter|change)\s+(me\s+)?(a\s+|an\s+|some\s+)?(fake|forged|false|phony|'
    r'fraudulent)\b|\bfake\s+(pay\s*stubs?|paystubs?|statements?|receipts?|checks?|cheques?|invoices?|w-?2s?|1099s?|'
    r'documents?|ids?|bank\s+statements?)\b|'
    r'\bmoney\s+launder|\blaunder(ing)?\s+(money|cash)|\btax\s+evasion|\bevade\s+(the\s+)?(irs|taxes?)|'
    r'\bhide\s+(my\s+|our\s+)?(income|money|cash|earnings)\s+from\s+(the\s+)?(irs|tax|taxes|government)|'
    r'\b(not|never|without)\s+report(ing)?\s+(my\s+|our\s+|the\s+)?(income|cash|tips|earnings)\s+to\s+(the\s+)?irs|'
    r'\bchange\s+(my|the|our)\s+(bank\s+)?balance\b|\b(chargeback|refund)\s+(scam|fraud)|\bidentity\s+theft\b|'
    r'\bcommit\s+fraud|\bdefraud\b|\bphish', re.I)
ILLEGAL_REFUSAL = ("Groundwork won't help with that. It can't reach into a bank or change what a bank holds, and it doesn't "
                   "help with anything against the law.")


def illegal(text):
    """H8b: True when text asks for something against the law (R15)."""
    return bool(_ILLEGAL.search(text or ''))


def read_request(question, context=None):
    """The kind of request, read by Groundwork's own code before the model, or None (the model plans it). A command to
    act must lead the sentence, so "what if we only paid the minimums" stays a question."""
    q = question.strip()
    if context and _YES.match(q) and context.get('offer'):
        return 'propose'
    if _ACT.search(q) and not _QUESTION.match(q):
        return 'refuse'
    if _CHANGE.search(q) and not _QUESTION.match(q):
        return 'propose'
    if _HOWTO.match(q):
        return 'guide'
    if _PAGE.match(q):
        return 'open_page'
    if _OUTSIDE.search(q):
        return 'outside_record'
    return None


def plan(model_call, question, today, context=None, force_record=False):
    """The model's request, forced into PLAN_SCHEMA by a grammar (H12). context: the last question and its plan (H13)."""
    lk = '\n'.join(f'- {k}: {v}' for k, v in LOOKUPS.items())
    sysmsg = PLANNER_SYSTEM.replace('{lookups}', lk).replace('{today}', today.isoformat())
    user = question if not context else (f'Earlier question: {context["question"]}\nEarlier plan: '
                                         f'{json.dumps(context.get("plan"))}\nFollow-up: {question}')
    schema = PLAN_SCHEMA
    if force_record:            # a question is answered from the record: the plan may only be about_my_record
        schema = json.loads(json.dumps(PLAN_SCHEMA))
        schema['properties']['kind']['enum'] = ['about_my_record']
        user += '\n(This is a question about their own record: choose the lookups that answer it.)'
    raw = model_call(sysmsg, user, schema)
    p = json.loads(raw)
    p['intent'] = KINDS.get(p.get('kind'), 'answer')
    p['lookups'] = [x for x in (p.get('lookups') or []) if x.get('name') in FUNCS][:MAX_LOOKUPS]
    return p


_ROOM_WORDS = re.compile(r'where in (my|our) budget|where could|what could (i|we) cut|find (the )?(money|room)|'
                         r'make (that|it) happen|pay for (it|that)|free up|in (my|our) budget could', re.I)
_AMOUNT = re.compile(r'\$\s?([\d,]+(?:\.\d+)?)')


_GENERIC_DEBT = {'debt', 'debts', 'loan', 'loans', 'card', 'cards', 'credit', 'the', 'my', 'our', 'here', 'name', 'named', 'any'}


def repair(question, p, reader):
    """Groundwork's own completion of the model's plan, each step recorded in p['repaired'] (measured apart from the
    model's raw choices): an obvious missing lookup is added, a category given as a payee is read as the category."""
    rep_ = []
    lk = p['lookups']
    names = {x['name'] for x in lk}
    if p.get('intent') != 'answer':
        if lk:
            rep_.append('lookups dropped: not a question about the record')
        p['lookups'], p['repaired'] = [], rep_
        return p
    rows, _ = _rows(reader)
    payees = {r['payee'].lower() for r in rows}
    cats = sorted({r['category'] for r in rows if r['category']})
    for x in lk:
        if x['name'] == 'transactions' and x.get('payee') and not any(x['payee'].lower() in y for y in payees):
            m = _category_match(x['payee'], cats) or next(
                (_category_match(w, cats) for w in re.findall(r'[a-z]+', x['payee'].lower()) if _category_match(w, cats)), [])
            if m:
                x.pop('payee')
                x['category'] = m[0]
                rep_.append(f'"{x["category"]}" read as a category, not a payee')
    given = next((x.get('category') for x in lk if x.get('category')), None)
    for x in lk:
        if x['name'] in ('category_by_month', 'budget_lines') and not x.get('category') and given:
            x['category'] = given
            rep_.append(f'{x["name"]}: category "{given}" from the same plan')
    mon = next((x.get('month') for x in lk if x['name'] == 'category_by_month' and x.get('month')), None)
    for x in lk:
        if x['name'] == 'transactions' and mon and not x.get('month') and not x.get('payee'):
            x['month'] = mon
            rep_.append(f'transactions: month {mon} from the same plan')
    if 'budget_lines' in names and given and 'category_by_month' not in names:
        bl = next(x for x in lk if x['name'] == 'budget_lines')
        lk.append({'name': 'category_by_month', 'category': given, 'month': bl.get('month') or 'this_month'})
        rep_.append('category_by_month added: a budget line is read against what was spent')
    if 'debt_whatif' in names and 'debts' not in names:
        lk.insert(0, {'name': 'debts'})
        rep_.append('debts added beside the what-if')
    if _ROOM_WORDS.search(question) and 'budget_headroom' not in names:
        amt = next((x.get('extra_monthly') for x in lk if x.get('extra_monthly')), None)
        if amt is None:
            m = _AMOUNT.search(question)
            amt = float(m.group(1).replace(',', '')) if m else None
        lk.append({'name': 'budget_headroom', **({'amount': amt} if amt else {})})
        rep_.append('budget_headroom added: the question asks where in the budget')
    ql = question.lower()
    for x in lk:            # a debt name the person did not say, and no debt has, is not theirs ("named_debt_here")
        own = [w for w in re.findall(r'[a-z]{3,}', x['debt'].lower()) if w not in _GENERIC_DEBT] if x.get('debt') else []
        if x.get('debt') and (not own or not all(w in ql for w in own)):
            rep_.append(f'debt "{x.pop("debt")}" dropped: not in the question')
    if re.search(r'\bavailable\b|how much (money )?(do|have) (we|i) (have|got)|in (my|our) (checking|savings)', ql) \
            and not any(x['name'] == 'balances' for x in lk):
        lk.insert(0, {'name': 'balances'})
        rep_.append('balances added: the question asks what is available, or what an account holds')
    if re.search(r'\b(afford|pay for|buy|cover)\b', ql) and _AMOUNT.search(question) \
            and not any(x['name'] in ('goal_plan', 'debt_whatif') for x in lk):
        lk = [x for x in lk if x['name'] not in ('budget_lines', 'net_worth', 'category_by_month')]
        lk.insert(0, {'name': 'goal_plan', 'amount': float(_AMOUNT.search(question).group(1).replace(',', '')),
                      'label': question})
        rep_.append('goal_plan added: the question asks about paying for something with an amount')
    for x in lk:
        if x['name'] == 'goal_plan' and not x.get('label'):
            x['label'] = question
    if 'minimum' not in ql and any(x['name'] == 'minimums_only' for x in lk):
        lk = [x for x in lk if x['name'] != 'minimums_only']
        rep_.append('minimums_only dropped: the question does not ask about minimums')
    seen, dedup = set(), []
    for x in lk:
        key = json.dumps(x, sort_keys=True)
        if x['name'] == 'debt_whatif' and not x.get('debt') and not x.get('extra_monthly'):
            key = 'debt_whatif-plain'
        if key not in seen:
            seen.add(key)
            dedup.append(x)
    if len(dedup) < len(lk):
        rep_.append('a repeated lookup dropped')
    lk = dedup
    if 'debt_whatif' in {x['name'] for x in lk}:
        for x in lk:
            if x['name'] == 'debt_whatif' and not x.get('debt'):
                m = re.search(r'\bon (?:the |my |our )?([A-Za-z][\w ]{2,30}?)(?: make| would|\?|,|$)', question)
                if m:
                    x['debt'] = m.group(1).strip()
                    rep_.append(f'debt "{x["debt"]}" taken from the question')
    p['lookups'], p['repaired'] = lk[:MAX_LOOKUPS], rep_
    return p


# H17 (Rob 2026-10-30): the working indicator names the step that is actually running, in plain words
STEP_WORDS = {
    'transactions': 'Looking at your transactions', 'category_by_month': 'Adding up a category, month by month',
    'budget_lines': 'Reading your budget', 'budget_vs_spent': 'Checking your budget against what you spent',
    'income_lines': 'Reading your income', 'debts': 'Looking at your debts', 'balances': 'Reading your account balances',
    'net_worth': 'Reading your net worth', 'recurring': 'Finding charges that repeat', 'price_changes': 'Looking for price changes',
    'bills_due': 'Reading your calendar and bills', 'savings_goals': 'Reading your savings goals', 'goal_plan': 'Working out how it could be paid for',
    'freshness': 'Checking how current your record is', 'debt_whatif': 'Working out the payoff',
    'budget_headroom': 'Finding room in your budget', 'minimums_only': 'Working out minimums only', 'guide': 'Opening the guide',
}


def run_lookups(reader, p, progress=None):
    results = []
    for x in p['lookups']:
        args = {k: v for k, v in x.items() if k != 'name'}
        if progress:
            progress(STEP_WORDS.get(x['name'], 'Reading your record'))
        t0 = time.time()
        try:
            r = FUNCS[x['name']](reader, args)
        except Exception as e:                        # a lookup that fails says so; it is never guessed around
            r = {'enough': False, 'why': f'the lookup failed ({type(e).__name__}: {e})', 'would_know': 'a fix'}
        r['_lookup'] = x['name']
        r['_ms'] = round((time.time() - t0) * 1000)
        results.append(r)
    return results


def decide(p, results):
    """The outcome, decided in code from the plan and what the lookups found (H5) - never by the model."""
    intent = p.get('intent')
    if intent != 'answer':
        return intent
    if any(r.get('clarify') for r in results):
        return 'clarify'
    if not results:
        return 'outside_record'
    if any(r.get('route') == 'guide' for r in results):
        return 'guide'
    if any(r.get('enough') is False for r in results):
        return 'does_not_know'
    return 'answer'


FACTS_CHARS = 3600             # N_CTX is 2048 tokens: the facts, the rules and the answer have to fit together


def _trim(v, n=12):
    if isinstance(v, list):
        return [_trim(x, n) for x in v[:n]] + ([f'... and {len(v) - n} more'] if len(v) > n else [])
    if isinstance(v, dict):
        return {k: _trim(x, n) for k, x in v.items()}
    return v


def facts_of(results):
    """What the model is given: each lookup's findings, long lists cut to their first 12 (and said so)."""
    out = [_trim({k: v for k, v in r.items() if not k.startswith('_') and k not in ('reads_transactions',
                                                                                    'calendar_next_10_weeks')})
           for r in results]
    s = json.dumps(out)
    n = 12
    while len(s) > FACTS_CHARS and n > 3:
        n -= 3
        out = [_trim(x, n) for x in out]
        s = json.dumps(out)
    return out


# ── H22 (Rob 2026-10-30): Groundwork writes every sentence with a figure, in fixed wording; the model chooses ─────────
def _day(iso):
    try:
        d = date.fromisoformat(str(iso)[:10])
        return f'{d:%B} {d.day}, {d.year}'
    except (ValueError, TypeError):
        return str(iso)


def _plural(n, word):
    return f'{n} {word}' + ('' if n == 1 else 's')


def render(r, today):
    """One lookup's findings as Groundwork's own sentences. Every figure here came from the record or an engine."""
    k = r.get('_lookup')
    if r.get('enough') is False:
        s = [f"Groundwork doesn't know yet: {r.get('why')}."]
        if r.get('would_know'):
            s.append(f"It would know with {r['would_know']}.")
        if r.get('past_months'):
            s.append('What the record does show, month by month (past months, not a forecast): '
                     + '; '.join(f"{m['month']} {m['spent']}" for m in r['past_months'] if not m.get('partial')) + '.')
        if r.get('months'):
            s.append('What the record holds: ' + '; '.join(f"{m['month']} {m['spent']}" + (' so far' if m.get('partial') else '')
                                                          for m in r['months']) + '.')
        return s
    if r.get('clarify') or r.get('route'):
        return []
    s = []
    if k == 'transactions':
        s.append(f"Groundwork found {_plural(r['count'], 'transaction')}" + (f", {r['total']} in all." if r['count'] else '.'))
        if r.get('rows'):
            s.append('They are: ' + '; '.join(f"{_day(x['date'])}, {x['payee']}, {x['amount']}"
                                              + (' (a refund)' if x['kind'] == 'refund' else '') for x in r['rows']) + '.')
        if r.get('text_held_back_from_the_assistant'):
            s.append(f"Text on {_plural(r['text_held_back_from_the_assistant'], 'transaction')} was held back from the "
                     'assistant: it reads as instructions, so it was not passed on. The transactions themselves are unchanged.')
    elif k == 'category_by_month':
        if r.get('month'):
            s.append(f"You spent {r['spent']} on {r['category']} in {r['month']}" + (' so far' if r.get('partial_month') else '')
                     + f", over {_plural(r.get('charges', 0), 'charge')}.")
            if r.get('budget_line') and r['budget_line'] != 'no budget line':
                s.append(f"The {r['category']} budget line is {r['budget_line']} a month.")
                if r.get('against_budget'):
                    s.append(f"Against that line: {r['against_budget']}.")
            else:
                s.append(f"{r['category']} has no budget line.")
        else:
            s.append(f"{r['category']}, month by month: " + '; '.join(
                f"{m['month']} {m['spent']}" + (' so far' if m.get('partial') else '') for m in r.get('months', [])) + '.')
            s.append(f"Over {_plural(r['complete_months'], 'complete month')}, the lowest was {r['lowest']} and the "
                     f"highest {r['highest']}.")
            if r.get('budget_line') and r['budget_line'] != 'no budget line':
                s.append(f"The {r['category']} budget line is {r['budget_line']} a month.")
    elif k == 'budget_vs_spent':
        when = r['month'] + (' so far' if r.get('partial_month') else '')
        s.append(f"Your budget against what you spent in {when}:")
        for x in r['lines']:
            s.append(f"{x['line']}: {x['spent']} spent of {x['budgeted']}"
                     + (f", {x['over']} over." if x.get('over') else f", {x['left']} left."))
        s.append(('Over budget in ' + when + ': ' + ', '.join(r['over_budget']) + '.') if r['over_budget']
                 else f"No line is over budget in {when}.")
        if r.get('spent_with_no_budget_line'):
            s.append('Spending with no budget line: ' + '; '.join(f"{x['category']} {x['spent']}"
                                                                   for x in r['spent_with_no_budget_line']) + '.')
    elif k == 'budget_lines':
        s.append('Your budget lines: ' + '; '.join(f"{x['name']} {x['amount']}" for x in r['lines']) + '.')
        s.append(f"Together they come to {r['total']} a month.")
    elif k == 'income_lines':
        s.append('Budgeted income: ' + '; '.join(f"{x['name']} {x['amount']}" for x in r['budgeted'])
                 + f", {r['budgeted_total']} a month in all.")
        if r.get('paychecks_by_month'):
            s.append('Paychecks in the record: ' + '; '.join(
                f"{x['month']} {x['total']}" + (' so far' if x.get('partial_month') else '') for x in r['paychecks_by_month']) + '.')
    elif k == 'debts':
        for d in r['debts']:
            line = (f"{d['name']}: {d['balance']} at {d['rate']}, minimum {d['minimum']}"
                    + (f", due on the {d['due_day']}{_th(d['due_day'])}" if d.get('due_day') else '')
                    + f"; at that rate this month's interest is {d['interest_this_month']}.")
            if d.get('end_date_on_file'):
                line += f" The end date on file is {_day(d['end_date_on_file'])}."
            if d.get('available_credit'):
                line += f" Available credit: {d['available_credit']}."
            s.append(line)
    elif k == 'debt_whatif':
        if r.get('debts') == 'none':
            return ['There are no debts in the record.']
        if r.get('read_as'):
            ra = r['read_as']
            s.append(f"Reading \"{ra['said']}\" as the {ra['means']}"
                     + ({'your earlier answer': ', as you said before.', 'your answer': ', as you said.'}.get(ra['from'], '.')))
        n = r['now']
        s.append(f"At your {r['debt_budget']} a month debt budget ({r['strategy']}), you are debt-free in "
                 f"{n['debt_free']}, {_plural(n['months'], 'month')} from now, with {n['interest_to_pay']} in interest still to pay.")
        if r.get('extra_monthly') and r.get('with_extra'):
            w = r['with_extra']
            s.append(f"With {r['extra_monthly']} more a month, aimed at {r['aimed_at']}, you are debt-free in "
                     f"{w['debt_free']}: {_plural(r['months_sooner'], 'month')} sooner, with {w['interest_to_pay']} in "
                     f"interest - {r['interest_saved']} less.")
            if r.get('plan_would_send_extra_to') and r.get('aimed_at') != r['plan_would_send_extra_to']:
                s.append(f"Your plan's own order would send extra money to {r['plan_would_send_extra_to']} first.")
            elif r.get('plan_would_send_extra_to'):
                s.append(f"That is where your plan's own order sends extra money first.")
        if r.get('this_debt_cleared_now'):
            s.append(f"{r['aimed_at'] if r.get('extra_monthly') else 'That debt'} is paid off in {r['this_debt_cleared_now']}"
                     + (f" now, and in {r['this_debt_cleared_with_extra']} with the extra." if r.get('this_debt_cleared_with_extra') else '.'))
        s.append(f"This assumes {r['assumptions']}.")
    elif k == 'minimums_only':
        s.append(f"Paying only the minimums, you are debt-free in {r['debt_free']}, {_plural(r['months'], 'month')} from now, "
                 f"with {r['interest_to_pay']} in interest." + (' That reaches the 30-year limit with a balance left.'
                                                                if r.get('reaches_30_years') else ''))
        if r.get('the_plan'):
            s.append(f"Your plan, for comparison: debt-free in {r['the_plan']['debt_free']}, with "
                     f"{r['the_plan']['interest_to_pay']} in interest.")
    elif k == 'budget_headroom':
        for c in r['categories_with_room']:
            s.append(f"{c['category']}: budgeted {c['budgeted']}; the most spent in any of the last "
                     f"{_plural(c['months'], 'month')} was {c['most_spent_in_a_month']}, so {c['room_every_month']} of room every month.")
        s.append(f"Together that is {r['room_together']} a month of room"
                 + (f", which {'covers' if r.get('room_covers_it') else 'does not cover'} the {r['asked_for']}."
                    if r.get('asked_for') else '.'))
        if r.get('left_out_as_protected'):
            s.append('Left out, because you said to protect them: ' + ', '.join(r['left_out_as_protected']) + '.')
        s.append('The current month is not counted: it is only part of a month.')
    elif k == 'balances':
        for a in r['accounts']:
            s.append(f"{a['account']}: {a['balance']}, from {a['known_from']}" + (f", as of {_day(a['as_of'])}." if a.get('as_of') else '.'))
            if a.get('set_aside'):
                s.append(f"In {a['account']}, {a['set_aside']} is set aside ("
                         + ', '.join(f"{g['name']} {g['amount']}" for g in a['goals_in_it']) + f"), so {a['available']} is available.")
                if a.get('short'):
                    s.append(f"That is {a['short']} more set aside than {a['account']} holds.")
        if r.get('goals_without_an_account'):
            s.append("These goals don't name the account their money is kept in yet, so they aren't counted in any "
                     'account: ' + ', '.join(r['goals_without_an_account']) + '.')
    elif k == 'net_worth':
        s.append('Net worth by month: ' + '; '.join(f"{m['month']} {m['net_worth']}" for m in r['months']) + '.')
    elif k == 'recurring':
        for x in r['recurring']:
            s.append(f"{x['name']} ({x['category']}): {x['monthly']} a month"
                     + (f", charged on day {', '.join(map(str, x['days_of_month_charged']))} of the month."
                        if x.get('days_of_month_charged') else '.'))
    elif k == 'price_changes':
        s.append('Price changes the record shows: ' + ('; '.join(json.dumps(c) for c in r['changes']) if r['changes'] else 'none') + '.')
    elif k == 'bills_due':
        week = r.get('due_in_next_7_days') or []
        s.append('Due in the next seven days: ' + ('; '.join(f"{_day(e['date'])}, {e['what']}" + (f" {e['amount']}" if e.get('amount') else '')
                                                          for e in week) if week else 'nothing in the calendar') + '.')
        for b in r.get('medical_bills') or []:
            s.append(f"{b['provider']}: {b['owed']} owed" + (f", due {_day(b['due'])}." if b.get('due') else '.'))
        for o in r.get('occasions') or []:
            s.append(f"{o['what']}: {_day(o['date'])}.")
    elif k == 'savings_goals':
        if r.get('goals') == 'none':
            return ["You don't have a savings goal set up yet."]
        for g in r['goals']:
            line = (f"{g['name']}: {g['set_aside']} set aside, toward {g['target']}"
                    + (f" by {_day(g['deadline'])}" if g.get('deadline') else '') + f"; planned {g['planned_monthly']} a month.")
            if g.get('lands_at_that_pace'):
                line += f" At the pace of what has been put in, it is reached in {g['lands_at_that_pace']}."
            s.append(line)
        s.append('The amounts set aside are your own figures and what you added.')
        for g in r['goals']:
            s.append(f"{g['name']} is kept in {g['kept_in']}." if g.get('kept_in')
                     else f"{g['name']} doesn't name the account its money is kept in yet.")
    elif k == 'goal_plan':
        if r.get('goal') and r.get('rest_amount') == 0:
            s.append(f"{r['goal']} has {r['goal_set_aside']} set aside; this is {r['amount']}, so {r['goal_left']} stays in {r['goal']}.")
        else:
            s.append(f"{r['goal']} covers {r['covers']}. The other {r['rest']} would come from:" if r.get('goal')
                     else f"With nothing set aside for it, the whole {r['amount']} would come from:")
            for x in r['accounts']:
                s.append(f"{x['name']}: {x['available']} available, " + (f"{x['after']} left after." if x['after'] else f"{x['short']} short."))
            for c in r['cards']:
                line = (f"{c['name']}: its limit isn't entered" if not c['available_credit']
                        else f"{c['name']}: {c['available_credit']} of available credit" + (f", {c['after']} left after" if c['after'] else ', not enough'))
                if c['payoff']:
                    line += '; on it, it is new debt: ' + ' or '.join(f"{p['months']} months at {p['payment']} a month ({p['interest']} interest)" for p in c['payoff'])
                s.append(line + '.')
            if not r.get('anything_covers'):
                s.append(f"None of these covers the {r['rest']}.")
        if not r.get('goal'):
            s.append('Money set aside in your goals is not counted here.')
        s.append('Nothing moves; a goal is reduced only when the purchase happens.')
    elif k == 'freshness':
        s.append(f"Your record runs to {_day(r['record_runs_to'])}" + (
            f"; the last download was {r['hours_since']:.0f} hours ago." if r.get('hours_since') is not None else '.'))
        if r.get('offer'):
            s.append(r['offer'])
    return s


def _th(n):
    try:
        n = int(n)
    except (TypeError, ValueError):
        return ''
    return 'th' if 11 <= n % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')


_WE = ["let's", 'let us', 'we ', "we'll", 'together we']    # the voice rules' WE_PHRASES, held on the model's own words
_DATEISH = re.compile(r'\d|\$|\b(' + '|'.join(m for m in _MONTHS) + r')\b', re.I)


def check_words(s, not_enough):
    """H22 + H6 on the model's own words: no figure, amount, date or month (H22), no verdict or advice, no "does not
    know" where the lookups had enough (H5), no talk about the facts."""
    global _BANNED
    if _BANNED is None:
        _BANNED = _wordlists()
    if not s or not s.strip():
        return None
    low = ' ' + s.lower() + ' '
    why = []
    if _DATEISH.search(s):
        why.append('carries a figure, date or month (H22)')
    why += [b for b in _BANNED + _WE if b in low]
    if not not_enough and re.search(r"(does not|doesn't|do not|don't) know|would need", low):
        why.append('does not know, where the lookups had enough')
    if re.search(r'\bfacts?\b|groundwork (knows|would|can confirm|could)', low):
        why.append('talks about the facts')
    if re.search(r"\b(does not|doesn't|do not|don't|cannot|can't|is not|isn't)\s+(specify|show|include|say|provide|list|mention|cover)", low):
        why.append('says the record lacks something - that is Groundwork\'s to say (H5)')
    return why


def write(model_call, question, sentences, not_enough):
    """H22: the model chooses which of Groundwork's sentences answer the question (by number), and may add a lead-in
    and a close with no figures in them. No limit on how many sentences are shown (R13)."""
    ids = [str(i + 1) for i in range(len(sentences))]
    schema = {'type': 'object', 'properties': {
        'facts': {'type': 'array', 'items': {'type': 'string', 'enum': ids}},
        'lead': {'type': 'string'}, 'close': {'type': 'string'}},
        'required': ['facts', 'lead', 'close']}
    user = 'QUESTION: ' + question + '\n\nFACTS:\n' + '\n'.join(f'{i + 1}. {x}' for i, x in enumerate(sentences))
    raw = json.loads(model_call(WRITER_SYSTEM, user, schema))
    chosen = []
    for x in raw.get('facts') or []:
        i = int(x) - 1
        if 0 <= i < len(sentences) and i not in chosen:
            chosen.append(i)
    if not chosen:
        chosen = list(range(len(sentences)))
    held = {}
    words = {}
    for part in ('lead', 'close'):
        txt = (raw.get(part) or '').strip()
        w = check_words(txt, not_enough)
        if w:
            held[part] = {'sentence': txt, 'why': w}
        elif w is not None:
            words[part] = txt
    shown = ([words['lead']] if 'lead' in words else []) + [sentences[i] for i in chosen] + \
            ([words['close']] if 'close' in words else [])
    return shown, {'raw': raw, 'chosen': [i + 1 for i in chosen], 'held': held}


def answer(reader, model_call, model_call_text, question, context=None, progress=None):
    """R7 first, then the plan, the lookups, the outcome, the words and the check. Returns everything measured.
    `progress(step)` hears each step as it starts (H17)."""
    progress = progress or (lambda step: None)
    out = {'question': question, 'timings': {}}
    just_confirmed = False
    t0 = time.time()
    if illegal(question):
        out.update({'outcome': 'refuse', 'r15': True, 'shown': [ILLEGAL_REFUSAL], 'lookups': []})
        out['timings']['total'] = round(time.time() - t0, 2)
        return out
    if rejected(question):
        out.update({'outcome': 'refuse', 'r7': True, 'shown': [R7_REFUSAL], 'lookups': []})
        out['timings']['total'] = round(time.time() - t0, 2)
        return out
    if context and context.get('offer_goal'):
        og, said = context['offer_goal'], question.strip().lower()
        pick = next((x for x in og['goals'] if x['name'].lower() in said or said in x['name'].lower()), None)
        no = re.match(r'^(no|nope|nothing|none)\b', said)
        if pick or no:
            p = {'intent': 'answer', 'read_by': 'groundwork',
                 'lookups': [{'name': 'goal_plan', 'amount': og['amount'], 'label': og['label'],
                              **({'goal_id': pick['id']} if pick else {'no_goal': True})}]}
            out['plan'] = p
            out['raw_plan'] = p
            results = run_lookups(reader, p, progress)
            out['lookups'] = [r['_lookup'] for r in results]
            out['results'] = results
            out['outcome'] = decide(p, results)
            out['shown'] = [x for r in results for x in render(r, reader.today)]
            out['timings']['total'] = round(time.time() - t0, 2)
            return out
    if context and context.get('offer_name') and _YES.match(question.strip()):
        on = context['offer_name']
        confirm_name(reader, on['kind'], on['said'], on['means'])          # R17: on the person's Yes, kept as theirs
        out['confirmed_name'] = on
        question = context['question']
        context = None
        just_confirmed = True
    kind = read_request(question, context)
    if kind:
        p = {'intent': kind, 'lookups': [], 'read_by': 'groundwork'}
    else:
        progress('Reading your question')
        p = plan(model_call, question, reader.today, context)
        # a question is answered from the record: the model may not turn it into a refusal, a change, a page or "outside"
        # - Groundwork's own reading (read_request) already decided those
        if p.get('intent') in ('open_page', 'outside_record', 'guide', 'refuse', 'propose') and _QUESTION.match(question):
            out['first_plan'] = json.loads(json.dumps(p))
            p = plan(model_call, question, reader.today, context, force_record=True)
    out['timings']['plan'] = round(time.time() - t0, 2)
    out['raw_plan'] = json.loads(json.dumps(p))
    p = repair(question, p, reader)
    out['plan'] = p
    if just_confirmed:
        for x in p['lookups']:
            if x.get('debt'):
                x['_just_confirmed'] = True
    results = run_lookups(reader, p, progress)
    out['timings']['lookups'] = round(time.time() - t0 - out['timings']['plan'], 2)
    out['lookups'] = [r['_lookup'] for r in results]
    out['results'] = results
    out['outcome'] = decide(p, results)
    shown = []
    if out['outcome'] == 'clarify':
        c = next((r for r in results if r.get('clarify')), {})
        shown = [c.get('clarify', 'Which one do you mean?')]
        if c.get('offer_name'):
            out['offer_name'] = c['offer_name']
        if c.get('offer_goal'):
            out['offer_goal'] = c['offer_goal']
    elif out['outcome'] == 'refuse':
        shown = ['Groundwork never does that for you. It is yours to do, in the app or at your bank.']
    elif out['outcome'] == 'propose' and context and context.get('offer'):
        shown = [context['offer'] if 'No bank' in context['offer'] else
                 'Groundwork would press Get my accounts now (not in this measurement: nothing is pressed).']
    elif out['outcome'] == 'propose':
        shown = ['Groundwork cannot make changes from here yet; it opens the place where you can.']
    elif out['outcome'] in ('open_page', 'guide'):
        shown = [f'(opens {p.get("page") or "the page"})' if out['outcome'] == 'open_page' else '(the guide answers)']
    elif out['outcome'] == 'outside_record':
        shown = ["Your record can't answer that, and Groundwork doesn't look outside it."]
    else:
        t1 = time.time()
        progress('Checking the answer')
        sentences = [x for r in results for x in render(r, reader.today)]
        out['facts'] = sentences
        if sentences:
            shown, w = write(model_call, question, sentences, any(r.get('enough') is False for r in results))
            out['written'] = w['raw']
            out['chosen'] = w['chosen']
            out['held'] = [{'sentence': v['sentence'], 'why': v['why']} for v in w['held'].values()]
        out['timings']['write'] = round(time.time() - t1, 2)
    # H21: an answer that read transactions says how current they are - always shown, Groundwork's own words
    if any(r.get('reads_transactions') for r in results) and out['outcome'] in ('answer', 'does_not_know') \
            and not any(r.get('_lookup') == 'freshness' for r in results):
        try:
            shown += render({**lk_freshness(reader, {}), '_lookup': 'freshness'}, reader.today)
        except Exception:
            pass
    out['shown'] = shown
    out['timings']['total'] = round(time.time() - t0, 2)
    return out
