"""
Groundwork - Ask why, stage 1 (gw 2.0/ASK_WHY.md, item 72, C1-C10 as revised in section 5)
========================================================================================
Fixed checks on the person's own record, and fixes they preview, approve and can undo. No model: every word here is
written by the engine, from the rows (C2 stage 1, A10).

  - C3  each check reports what the ledger shows, never a cause. Each says what it can establish, what it can't,
        its period, and what missing data does to it. When nothing explains a figure, it says so.
  - C4  a fix is an exact list. preview() shows each row, its current and proposed category, the total, the asked
        figure before and after, and the totals it feeds; apply() refuses a stale preview, confirms the write and
        records it in the Historian; undo() reverts only the rows still as the fix left them.
  - Bank text (descriptions, merchants) is data: it is shown, never followed (C10).

Not here: changed (not stopped) pay - the rule for that is item 71's amendment D3-D6, unruled.
"""
import hashlib
import json
import re
import statistics
from collections import defaultdict
from datetime import date, datetime, timedelta

PERIOD_MONTHS = 12
STALE_DAYS = 45
SWITCH_MIN = 2            # rows on each side of a category switch
WRONG_KIND_MIN = 3        # deposits in an expense-type category before it is shown
REGULAR = ((6, 8, 7), (13, 15, 14), (27, 33, 30))      # weekly, every two weeks, monthly: (low, high, nominal)

CHECKS = {
    'inputs_income': {
        'title': 'What went into your monthly income',
        'establishes': 'Which deposits were counted as income each month, and which deposits were not.',
        'cannot': 'Whether a deposit that was not counted is income - only you know that.'},
    'payer_switch': {
        'title': 'One payer, filed under two categories',
        'establishes': 'That the same payer\'s deposits (or charges) were filed under one category up to a date and '
                       'under another after it.',
        'cannot': 'Which category is the one you meant.'},
    'wrong_kind': {
        'title': 'Deposits in a spending category, or charges in an income category',
        'establishes': 'That a category of one kind holds money moving the other way.',
        'cannot': 'Whether that is how you meant to file it. Refunds are deposits in spending categories on purpose; '
                  'a category is shown only when most of its money is deposits.'},
    'stopped': {
        'title': 'A regular deposit that has not come in',
        'establishes': 'That a payer who paid on a regular schedule has nothing on record since a date.',
        'cannot': 'Whether it stopped, or arrived and is not on record yet. A missing deposit is never counted as zero.'},
    'duplicates': {
        'title': 'The same transaction on record twice',
        'establishes': 'Two or more rows with the same account, date, amount, direction and description.',
        'cannot': 'Whether it was imported twice or really happened twice - so these stay suspected until you say.'},
    'own_transfers': {
        'title': 'Money between your own accounts counted as income',
        'establishes': 'A deposit counted as income with the same amount leaving another of your accounts within two '
                       'days.',
        'cannot': 'Whether the two are the same money - a matching amount can be chance.'},
    'empty_months': {
        'title': 'Months with no records',
        'establishes': 'Accounts with no rows in a month between their first and last rows, and accounts whose records '
                       'stop well before today.',
        'cannot': 'What happened in those months. A total over them is missing data, not zero.'},
}

FIGURES = {
    'income_month': {'label': 'Your monthly income',
                     'checks': ['inputs_income', 'payer_switch', 'wrong_kind', 'stopped', 'own_transfers', 'empty_months']},
    'records': {'label': 'Your records',
                'checks': ['payer_switch', 'wrong_kind', 'stopped', 'duplicates', 'own_transfers', 'empty_months']},
}


# ── the record ────────────────────────────────────────────────────────────────
def _month(d):
    return f'{d.year}-{d.month:02d}'


def _period(today):
    start = today.replace(day=1)
    for _ in range(PERIOD_MONTHS):
        start = (start - timedelta(days=1)).replace(day=1)
    return start, today.replace(day=1)          # [start, month_start): complete months only


_NOISE = re.compile(r'\b(deposit|withdrawal|check card tran|ach|pos|debit|credit|purchase|type|payroll|co|entry class '
                    r'code|ppd|trace number|card|date)\b|#?\d[\d/:-]*|[^a-z ]', re.I)


def payer_key(t):
    """Who the money came from or went to: the canonical merchant when the import set one, else the description with
    bank boilerplate and numbers taken out."""
    name = (t.merchant or '').strip() or _NOISE.sub(' ', t.description or '')
    return re.sub(r'\s+', ' ', name).strip().lower()[:60]


def _load(session, today):
    from core.database import Account, Category, Transaction
    from core.income_def import income_category_ids
    _INCOME_IDS.clear()
    _INCOME_IDS.update(income_category_ids(session))
    cats = {c.id: c for c in session.query(Category).all()}
    accts = {a.id: a for a in session.query(Account).all()}
    since = _period(today)[0] - timedelta(days=62)        # a little before the period, for schedules and switches
    rows = session.query(Transaction).filter(Transaction.date >= since).order_by(Transaction.date, Transaction.id).all()
    return cats, accts, rows


def _cat_name(cats, cid):
    c = cats.get(cid)
    return c.name if c else '(no category)'


_INCOME_IDS = set()


def _is_income_cat(cats, cid):
    """Item 71 amendment D1 (core/income_def.py): the one definition the income figure uses."""
    return cid in _INCOME_IDS


def _row(t, cats, accts):
    return {'id': t.id, 'date': t.date.isoformat(), 'amount': round(float(t.amount or 0), 2), 'type': t.type,
            'description': (t.description or '')[:140], 'merchant': t.merchant or '',
            'category': _cat_name(cats, t.category_id), 'category_id': t.category_id,
            'account': (accts.get(t.account_id).name if accts.get(t.account_id) else '')}


def _finding(check, text, rows=(), fixes=(), extra=None):
    out = {'check': check, 'title': CHECKS[check]['title'], 'text': text, 'rows': list(rows), 'fixes': list(fixes),
           'establishes': CHECKS[check]['establishes'], 'cannot': CHECKS[check]['cannot']}
    if extra:
        out.update(extra)
    return out


# ── the checks ────────────────────────────────────────────────────────────────
def check_inputs_income(session, today, data):
    cats, accts, rows = data
    start, end = _period(today)
    counted, left = defaultdict(float), defaultdict(lambda: defaultdict(float))
    transfer = {cid for cid, c in cats.items() if (c.name or '').lower() == 'transfer'}
    for t in rows:
        if t.type != 'credit' or not (start <= t.date < end):
            continue
        m = _month(t.date)
        if _is_income_cat(cats, t.category_id):
            counted[m] += t.amount or 0
        elif t.category_id not in transfer:
            left[m][_cat_name(cats, t.category_id)] += t.amount or 0
    months = []
    for i in range(PERIOD_MONTHS):
        d = end
        for _ in range(i + 1):
            d = (d - timedelta(days=1)).replace(day=1)
        months.append(_month(d))
    months.sort()
    table = [{'month': m, 'counted': round(counted.get(m, 0), 2),
              'left_out': {k: round(v, 2) for k, v in sorted(left.get(m, {}).items())}} for m in months]
    big = sorted({k for r in table for k, v in r['left_out'].items() if v >= 500})
    text = (f'Your monthly income counts deposits in income categories (Income, the categories under it, and any '
            f'named for your budget\'s income lines), in complete months ({months[0]} to {months[-1]}); the month in '
            f'progress is left out. Transfers are left out.')
    if big:
        text += ' Deposits filed under ' + ', '.join(f'"{b}"' for b in big) + ' are not counted.'
    return [_finding('inputs_income', text, extra={'table': table, 'period': [months[0], months[-1]]})]


def check_payer_switch(session, today, data):
    cats, accts, rows = data
    by = defaultdict(list)
    for t in rows:
        if t.category_id:
            by[(payer_key(t), t.type)].append(t)
    out = []
    for (key, kind), ts in by.items():
        if not key or len(ts) < 2 * SWITCH_MIN:
            continue
        for k in range(SWITCH_MIN, len(ts) - SWITCH_MIN + 1):
            a, b = {t.category_id for t in ts[:k]}, {t.category_id for t in ts[k:]}
            if len(a) == 1 and len(b) == 1 and a != b:
                old, new = next(iter(a)), next(iter(b))
                before, after = ts[:k], ts[k:]
                who = after[0].merchant or key
                noun = 'deposits' if kind == 'credit' else 'charges'
                text = (f'{len(before)} {noun} from {who} were filed under "{_cat_name(cats, old)}" up to '
                        f'{before[-1].date.isoformat()}. The {len(after)} since {after[0].date.isoformat()} are filed '
                        f'under "{_cat_name(cats, new)}" (${sum(t.amount or 0 for t in after):,.2f}).')
                fixes = [_recat_fix(f'Move the {len(after)} since {after[0].date.isoformat()} to "{_cat_name(cats, old)}"',
                                    [t.id for t in after], old, who, kind),
                         _recat_fix(f'Move the {len(before)} before to "{_cat_name(cats, new)}"',
                                    [t.id for t in before], new, None, kind)]
                out.append(_finding('payer_switch', text, [_row(t, cats, accts) for t in after], fixes,
                                    {'payer': who, 'direction': kind}))
                break
    return out


def check_wrong_kind(session, today, data):
    cats, accts, rows = data
    by = defaultdict(lambda: {'credit': [], 'debit': []})
    for t in rows:
        if t.category_id in cats and t.type in ('credit', 'debit'):
            by[t.category_id][t.type].append(t)
    income_cats = [c for c in cats.values() if (c.type or '') == 'income']
    out = []
    # D2: a category named for a budget income line already counts as income (core/income_def.py), so the check no
    # longer offers to retype it - nothing in the figures would change (Rob 2026-10-11: "make check my records skip
    # it"). The retype_category fix itself stays, for a caller that asks for it.
    for cid, d in by.items():
        c = cats[cid]
        cr, db = d['credit'], d['debit']
        crs, dbs = sum(t.amount or 0 for t in cr), sum(t.amount or 0 for t in db)
        if (c.type or 'expense') == 'expense' and (c.name or '').lower() != 'transfer' \
                and cid not in _INCOME_IDS and len(cr) >= WRONG_KIND_MIN and crs > dbs:
            text = (f'"{c.name}" is a spending category, and it holds {len(cr)} deposits (${crs:,.2f})'
                    + (f' and {len(db)} charges (${dbs:,.2f})' if db else '') + '.')
            fixes = [_recat_fix(f'Move the {len(cr)} deposits to "{ic.name}"', [t.id for t in cr], ic.id, None, 'credit')
                     for ic in income_cats if ic.parent_id is None][:1]
            if db:
                fixes.append(_recat_fix(f'Move the {len(db)} charges to a category you pick', [t.id for t in db], None,
                                        None, 'debit'))
            out.append(_finding('wrong_kind', text, [_row(t, cats, accts) for t in cr + db], fixes, {'category': c.name}))
        elif cid in _INCOME_IDS and db:
            text = f'"{c.name}" is an income category, and it holds {len(db)} charges (${dbs:,.2f}).'
            out.append(_finding('wrong_kind', text, [_row(t, cats, accts) for t in db],
                                [_recat_fix(f'Move the {len(db)} charges to a category you pick', [t.id for t in db],
                                            None, None, 'debit')], {'category': c.name}))
    return out


def _schedule(dates):
    if len(dates) < 4:
        return None
    gaps = [(b - a).days for a, b in zip(dates, dates[1:])]
    g = statistics.median(gaps)
    for lo, hi, nominal in REGULAR:
        if lo <= g <= hi and sum(lo <= x <= hi for x in gaps) >= 0.75 * len(gaps):
            return nominal
    return None


def check_stopped(session, today, data):
    cats, accts, rows = data
    last_row = defaultdict(lambda: date.min)
    for t in rows:
        last_row[t.account_id] = max(last_row[t.account_id], t.date)
    by = defaultdict(list)
    for t in rows:
        if t.type == 'credit':
            by[(payer_key(t), t.account_id)].append(t)
    out = []
    for (key, acct), ts in by.items():
        every = _schedule(sorted({t.date for t in ts}))
        if not every:
            continue
        last = ts[-1].date
        due = last + timedelta(days=every)
        grace = 3 if every < 20 else 5
        if today <= due + timedelta(days=grace):
            continue
        who = ts[-1].merchant or key
        records_end = last_row[acct]
        acct_name = accts.get(acct).name if accts.get(acct) else 'its account'
        if records_end <= due + timedelta(days=grace):
            text = (f'{who} paid about every {every} days; the last deposit on record is {last.isoformat()}. '
                    f'{acct_name}\'s records end on {records_end.isoformat()}, so the next one may simply not be on '
                    f'record yet.')
        else:
            text = (f'{who} paid about every {every} days; the last deposit on record is {last.isoformat()}, and '
                    f'{acct_name} has records through {records_end.isoformat()}. Nothing from {who} is on record since. '
                    f'Is it filed somewhere else, or did it stop?')
        out.append(_finding('stopped', text, [_row(t, cats, accts) for t in ts[-3:]], [],
                            {'payer': who, 'every_days': every, 'records_end': records_end.isoformat()}))
    return out


def check_duplicates(session, today, data):
    cats, accts, rows = data
    by = defaultdict(list)
    for t in rows:
        by[(t.account_id, t.date, round(t.amount or 0, 2), t.type, (t.description or '').strip().lower())].append(t)
    out = []
    for k, ts in by.items():
        if len(ts) > 1:
            text = (f'{len(ts)} rows on {k[1].isoformat()} for ${k[2]:,.2f} with the same description, in the same '
                    f'account. Suspected, not confirmed: two identical real charges look exactly like this.')
            out.append(_finding('duplicates', text, [_row(t, cats, accts) for t in ts], [], {'suspected': True}))
    return out


def check_own_transfers(session, today, data):
    cats, accts, rows = data
    debits = [t for t in rows if t.type == 'debit']
    out = []
    for t in rows:
        if t.type != 'credit' or not _is_income_cat(cats, t.category_id):
            continue
        match = [d for d in debits if d.account_id != t.account_id and abs((d.date - t.date).days) <= 2
                 and abs((d.amount or 0) - (t.amount or 0)) < 0.005 and d.account_id in accts]
        if match:
            transfer = next((c for c in cats.values() if (c.name or '').lower() == 'transfer'), None)
            text = (f'A ${t.amount:,.2f} deposit on {t.date.isoformat()} is counted as income, and the same amount left '
                    f'{accts[match[0].account_id].name} on {match[0].date.isoformat()}.')
            fixes = [_recat_fix('Move the deposit to "Transfer"', [t.id], transfer.id, None, 'credit')] if transfer else []
            out.append(_finding('own_transfers', text, [_row(x, cats, accts) for x in [t] + match[:1]], fixes))
    return out


def check_empty_months(session, today, data):
    cats, accts, rows = data
    start, end = _period(today)
    months = defaultdict(set)
    last = {}
    for t in rows:
        months[t.account_id].add(_month(t.date))
        last[t.account_id] = max(last.get(t.account_id, t.date), t.date)
    out = []
    for aid, ms in months.items():
        a = accts.get(aid)
        if not a or not a.is_active:
            continue
        span = sorted(m for m in ms if _month(start) <= m < _month(end))
        if len(span) >= 3:
            y, mo = int(span[0][:4]), int(span[0][5:])
            gaps = []
            while f'{y}-{mo:02d}' < span[-1]:
                if f'{y}-{mo:02d}' not in ms:
                    gaps.append(f'{y}-{mo:02d}')
                y, mo = (y + 1, 1) if mo == 12 else (y, mo + 1)
            if gaps:
                out.append(_finding('empty_months', f'{a.name} has no records in {", ".join(gaps)}, between months that '
                                    f'do. A total over those months is missing data, not zero.', extra={'account': a.name,
                                                                                                        'months': gaps}))
        if (today - last[aid]).days > STALE_DAYS:
            out.append(_finding('empty_months', f'{a.name}\'s records end on {last[aid].isoformat()}. Anything after that '
                                f'is not on record.', extra={'account': a.name, 'records_end': last[aid].isoformat()}))
    return out


RUN = {'inputs_income': check_inputs_income, 'payer_switch': check_payer_switch, 'wrong_kind': check_wrong_kind,
       'stopped': check_stopped, 'duplicates': check_duplicates, 'own_transfers': check_own_transfers,
       'empty_months': check_empty_months}


def investigate(session, figure, today=None):
    """Every check that applies to the figure, run on the record. `explained` is False when no check found
    anything beyond the figure's own working - and the answer says so (C3)."""
    if figure not in FIGURES:
        return None
    today = today or date.today()
    data = _load(session, today)
    results = []
    for c in FIGURES[figure]['checks']:
        results += RUN[c](session, today, data)
    if figure == 'income_month':
        # the income figure is made of deposits: charges, and accounts that never take a deposit, are not part of it
        cats, accts, rows = data
        paid_into = {accts[t.account_id].name for t in rows if t.type == 'credit' and t.account_id in accts
                     and _is_income_cat(cats, t.category_id)}
        paid_into |= {x['account'] for r in results if r['check'] in ('payer_switch', 'wrong_kind') for x in r['rows']
                      if x['type'] == 'credit'}
        results = [r for r in results if r.get('direction') != 'debit'
                   and not (r['check'] == 'wrong_kind' and not any(x['type'] == 'credit' for x in r['rows']))
                   and not (r['check'] == 'empty_months' and r.get('account') not in paid_into)]
    found = [r for r in results if r['check'] != 'inputs_income']
    return {'figure': figure, 'label': FIGURES[figure]['label'], 'results': results, 'explained': bool(found),
            'none_text': None if found else 'None of the checks explains this figure. What went into it is shown above; '
                                            'nothing else on record stands out.'}


def run_one(session, check, today=None):
    """Stage 3: a single check, as the person's question asked for it - with its finding, or the plain line that it
    found nothing."""
    if check not in RUN:
        return None
    today = today or date.today()
    results = RUN[check](session, today, _load(session, today))
    return {'figure': None, 'check': check, 'label': CHECKS[check]['title'], 'results': results,
            'explained': bool(results),
            'none_text': None if results else f'{CHECKS[check]["title"]}: nothing on record matches. ' + CHECKS[check]['cannot']}


# ── C4: fixes ─────────────────────────────────────────────────────────────────
def _recat_fix(label, ids, to_category_id, rule_payer, direction):
    return {'kind': 'recategorize', 'label': label, 'ids': list(ids), 'to_category_id': to_category_id,
            'rule_payer': rule_payer, 'direction': direction}


def fingerprint(rows):
    s = json.dumps(sorted((t.id, t.category_id, round(t.amount or 0, 2), t.date.isoformat(), t.type) for t in rows))
    return hashlib.sha256(s.encode()).hexdigest()[:24]


def _income_by_month(rows, cats, override=None):
    """The income figure's own rule, month by month, with `override` {id: category_id} applied."""
    override = override or {}
    out = defaultdict(float)
    for t in rows:
        cid = override.get(t.id, t.category_id)
        if t.type == 'credit' and _is_income_cat(cats, cid):
            out[_month(t.date)] += t.amount or 0
    return out


def matching_rules(rules, payer, direction):
    """The saved import rules that would file this payer's rows (first match wins, as in the import screen)."""
    p = (payer or '').lower()
    return [r for r in rules if (not r.get('direction') or r.get('direction') == direction)
            and ((r.get('type') == 'contains' and str(r.get('value', '')).lower() in p)
                 or (r.get('type') == 'startsWith' and p.startswith(str(r.get('value', '')).lower())))]


def _retype_preview(session, fix):
    """D2: a category's kind and parent, changed. Rows keep their category; what they count toward follows it."""
    from core.database import Category, Transaction
    c = session.get(Category, fix.get('category_id') or 0)
    parent = session.get(Category, fix.get('to_parent_id') or 0)
    if not c or not parent or fix.get('to_type') != 'income':
        return None
    rows = session.query(Transaction).filter_by(category_id=c.id).order_by(Transaction.date).all()
    state = json.dumps([c.id, c.type, c.parent_id, len(rows)])
    return {'label': f'Make "{c.name}" an income category under "{parent.name}"', 'retype': True,
            'category': {'id': c.id, 'name': c.name, 'type': c.type or 'expense', 'parent': c.parent_id},
            'to': {'type': 'income', 'parent': parent.name},
            'count': len(rows), 'deposits': sum(1 for t in rows if t.type == 'credit'),
            'charges': sum(1 for t in rows if t.type == 'debit'),
            'total': round(sum(t.amount or 0 for t in rows if t.type == 'credit'), 2), 'rows': [],
            'figure': [], 'feeds': ['Every place that sorts categories by kind (the category list, the budget, reports)'],
            'others_may_change': 'Its rows keep their category; only the category\'s kind and place change.',
            'rule': None, 'fingerprint': hashlib.sha256(state.encode()).hexdigest()[:24], 'fix': fix}


def preview(session, fix, rules):
    """Everything the person sees before saying yes. None when the fix is malformed."""
    from core.database import Category, Transaction
    if isinstance(fix, dict) and fix.get('kind') == 'retype_category':
        return _retype_preview(session, fix)
    if not isinstance(fix, dict) or fix.get('kind') != 'recategorize':
        return None
    ids = [int(i) for i in (fix.get('ids') or []) if str(i).isdigit()][:500]
    to = session.get(Category, fix.get('to_category_id') or 0)
    rows = session.query(Transaction).filter(Transaction.id.in_(ids)).order_by(Transaction.date).all() if ids else []
    if not rows or not to or len(rows) != len(set(ids)):
        return None
    cats = {c.id: c for c in session.query(Category).all()}
    accts = {}
    today = date.today()
    all_rows = session.query(Transaction).filter(Transaction.date >= min(t.date for t in rows).replace(day=1)).all()
    before = _income_by_month(all_rows, cats)
    after = _income_by_month(all_rows, cats, {t.id: to.id for t in rows})
    months = sorted({_month(t.date) for t in rows})
    payer = fix.get('rule_payer')
    direction = fix.get('direction') if fix.get('direction') in ('credit', 'debit') else None
    rule = None
    if payer and direction:
        now = matching_rules(rules, payer, direction)
        rule = {'value': payer.lower(), 'type': 'contains', 'direction': direction, 'category': to.name,
                'replaces_for_this_direction': now[0] if now else None,
                'note': ('Only for ' + ('deposits' if direction == 'credit' else 'charges') + ' - '
                         + ('charges' if direction == 'credit' else 'deposits') + ' from the same payer keep their rule.')}
    return {
        'label': fix.get('label') or '', 'to': {'id': to.id, 'name': to.name},
        'rows': [{**_row(t, cats, accts), 'proposed': to.name} for t in rows],
        'total': round(sum(t.amount or 0 for t in rows), 2), 'count': len(rows),
        'figure': [{'month': m, 'before': round(before.get(m, 0), 2), 'after': round(after.get(m, 0), 2)} for m in months],
        'feeds': ['Your monthly income (the income card on the Budget page)', 'The income-change scenarios',
                  'The Willingness readings that compare spending with income'],
        'others_may_change': 'Other figures that use these categories may change too.',
        'rule': rule, 'fingerprint': fingerprint(rows), 'fix': {**fix, 'ids': [t.id for t in rows]}}


def apply(session, fix, fp, rules, use_rule=False):
    """-> ('applied', result) | ('stale', fresh_preview) | ('invalid', None). Commits nothing on any failure."""
    from core.database import HistorianEntry, Transaction
    p = preview(session, fix, rules)
    if not p:
        return 'invalid', None
    if p['fingerprint'] != fp:
        return 'stale', p
    if p.get('retype'):
        from core.database import Category
        c = session.get(Category, p['category']['id'])
        before = {'type': c.type, 'parent_id': c.parent_id}
        c.type, c.parent_id = 'income', fix['to_parent_id']
        session.flush()
        got = session.query(Category.type, Category.parent_id).filter(Category.id == c.id).one()
        if tuple(got) != ('income', fix['to_parent_id']):
            session.rollback()
            return 'failed', None
        entry = HistorianEntry(event_category='record_fix', context_json=json.dumps({
            'label': p['label'], 'to': 'income category', 'changes': [], 'total': p['total'],
            'retype': {'category_id': c.id, 'before': before, 'after': {'type': 'income', 'parent_id': fix['to_parent_id']}},
            'rule_added': None}))
        session.add(entry)
        session.flush()
        return 'applied', {'historian_id': entry.id, 'changed': 1, 'rules': rules, 'rule_added': None}
    rows = session.query(Transaction).filter(Transaction.id.in_(p['fix']['ids'])).all()
    changes = [{'id': t.id, 'from': t.category_id, 'to': p['to']['id']} for t in rows]
    for t in rows:
        t.category_id = p['to']['id']
    new_rules, added = rules, None
    if use_rule and p['rule']:
        added = {'id': int(datetime.now().timestamp() * 1000), 'type': 'contains', 'value': p['rule']['value'],
                 'category': p['rule']['category'], 'direction': p['rule']['direction']}
        new_rules = [added] + list(rules)          # first match wins: the narrower rule goes first
    session.flush()
    # read back what the database holds - columns, not the session's own copies of the rows
    got = dict(session.query(Transaction.id, Transaction.category_id)
               .filter(Transaction.id.in_([c['id'] for c in changes])).all())
    if any(got.get(c['id']) != c['to'] for c in changes):
        session.rollback()
        return 'failed', None
    entry = HistorianEntry(event_category='record_fix', context_json=json.dumps({
        'label': p['label'], 'to': p['to']['name'], 'changes': changes, 'total': p['total'], 'rule_added': added}))
    session.add(entry)
    session.flush()
    return 'applied', {'historian_id': entry.id, 'changed': len(changes), 'rules': new_rules, 'rule_added': added}


def undo(session, historian_id, rules):
    """Revert a fix: only rows still as the fix left them; rows edited since are listed and left (C4)."""
    from core.database import HistorianEntry, Transaction
    e = session.get(HistorianEntry, historian_id)
    if not e or e.event_category != 'record_fix':
        return None
    ctx = json.loads(e.context_json or '{}')
    if ctx.get('undone'):
        return {'already': True}
    reverted, kept = [], []
    rt = ctx.get('retype')
    if rt:
        from core.database import Category
        c = session.get(Category, rt['category_id'])
        if c and c.type == rt['after']['type'] and c.parent_id == rt['after']['parent_id']:
            c.type, c.parent_id = rt['before']['type'], rt['before']['parent_id']
            reverted.append(c.id)
        elif c:
            kept.append(c.id)
    by_id = {t.id: t for t in session.query(Transaction).filter(Transaction.id.in_([c['id'] for c in ctx['changes']]))}
    for c in ctx['changes']:
        t = by_id.get(c['id'])
        if t and t.category_id == c['to']:
            t.category_id = c['from']
            reverted.append(c['id'])
        else:
            kept.append(c['id'])
    added = ctx.get('rule_added')
    new_rules = [r for r in rules if not (added and r.get('id') == added.get('id') and r == added)]
    ctx['undone'] = datetime.now().isoformat(timespec='seconds')
    e.context_json = json.dumps(ctx)
    session.add(HistorianEntry(event_category='record_fix_undone', context_json=json.dumps(
        {'fix': historian_id, 'reverted': reverted, 'left_as_edited': kept, 'rule_removed': bool(added) and new_rules != rules})))
    session.flush()
    return {'reverted': reverted, 'left_as_edited': kept, 'rules': new_rules}
