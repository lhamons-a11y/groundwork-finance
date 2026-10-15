"""HSA and FSA balances (gw 2.0/HSA_FSA.md, item 86 = item 45 H5; F1-F7 ruled 2026-10-14).

Money only: a balance, the year's contributions against the IRS limit, and an FSA's deadline. No person, medication,
diagnosis or insurance plan year (H5's boundary). Every figure carries its working; every term the person did not
enter stays unknown and is said to be unknown - nothing here fills one in. No advice and no judgement (F7): the
sentences state what the record and the entered terms show, and never say what to do with the money.
"""
from datetime import date

TYPES = ('hsa', 'fsa')
FSA_WARN_DAYS = 60             # F5, ruled 2026-10-14: Needs attention from 60 days before the deadline

# F3: the IRS figures, each with the release it came from. A year not here is said to be missing, never borrowed.
LIMITS = {
    2025: {'hsa': {'self': 4300.0, 'family': 8550.0, 'catch_up': 1000.0, 'source': 'IRS Rev. Proc. 2024-25'},
           'fsa': {'limit': 3300.0, 'carryover_max': 660.0, 'source': 'IRS Rev. Proc. 2024-40'}},
    2026: {'hsa': {'self': 4400.0, 'family': 8750.0, 'catch_up': 1000.0, 'source': 'IRS Rev. Proc. 2025-19'},
           'fsa': {'limit': 3400.0, 'carryover_max': 680.0, 'source': 'IRS Rev. Proc. 2025-32'}},
}

# F4: a deposit is a contribution unless it is the account's own earnings, which the limit does not count.
_EARNINGS = ('interest', 'dividend', 'earnings', 'capital gain')

_TERM_FIELDS = ('coverage', 'catch_up', 'year_end', 'rule', 'grace_until', 'carryover_max', 'claims_by', 'election',
                'typed_contributions', 'typed_balance', 'typed_balance_on')
_CHOICES = {'coverage': ('self', 'family', ''), 'catch_up': ('yes', 'no', ''), 'rule': ('grace', 'carryover', 'none', '')}
_DATES = ('year_end', 'grace_until', 'claims_by', 'typed_balance_on')
_AMOUNTS = ('carryover_max', 'election', 'typed_contributions', 'typed_balance')


def money(x):
    return '${:,.2f}'.format(x)


def day(iso):
    d = date.fromisoformat(iso)
    return d.strftime('%b ') + str(d.day) + d.strftime(', %Y')


# ── The terms (F2): one row per change, the newest per plan year is current ─────────────────────────────────────

def clean_terms(body):
    """(terms dict, problem) from a request body. A blank is unknown; a wrong value is refused, never guessed."""
    out = {}
    for k in _TERM_FIELDS:
        v = body.get(k)
        if k in _CHOICES:
            v = str(v or '').strip().lower()
            if v not in _CHOICES[k]:
                return None, f'{k} must be one of {", ".join(c for c in _CHOICES[k] if c)} or blank'
        elif k in _DATES:
            v = str(v or '').strip() or None
            if v:
                try:
                    date.fromisoformat(v)
                except ValueError:
                    return None, f'{k} must be a date (YYYY-MM-DD) or blank'
        else:
            if v in (None, ''):
                v = None
            else:
                try:
                    v = round(float(v), 2)
                except (TypeError, ValueError):
                    return None, f'{k} must be an amount or blank'
                if v < 0:
                    return None, f'{k} must be zero or more'
        out[k] = v
    if out['typed_balance'] is not None and not out['typed_balance_on']:
        out['typed_balance_on'] = date.today().isoformat()
    return out, None


def save_terms(session, account, plan_year, body):
    from core.database import HealthAccountTerms
    terms, problem = clean_terms(body)
    if problem:
        return None, problem
    row = HealthAccountTerms(account_id=account.id, plan_year=int(plan_year), **terms)
    session.add(row)
    session.flush()
    return row, None


def _rows(session, account_id):
    from core.database import HealthAccountTerms
    return session.query(HealthAccountTerms).filter_by(account_id=account_id) \
        .order_by(HealthAccountTerms.id).all()


def current_by_year(session, account_id):
    """{plan_year: newest row}. Older rows are history."""
    out = {}
    for r in _rows(session, account_id):
        out[r.plan_year] = r
    return out


def history(session, account_id):
    return [dict({k: getattr(r, k) for k in _TERM_FIELDS}, id=r.id, plan_year=r.plan_year,
                 saved=r.created_at.isoformat(timespec='seconds') if r.created_at else None)
            for r in reversed(_rows(session, account_id))]


def _as_dict(r):
    return {k: (getattr(r, k) if r is not None else None) for k in _TERM_FIELDS}


# ── The balance (F1) ────────────────────────────────────────────────────────────────────────────────────────────

def balance(session, account, txns, anchor_fn):
    """The newer of the bank's own reported balance (from an imported statement) and a balance the person typed.
    Neither: unknown. Never the sum of imported activity, which is right only for a full history."""
    anchor, _ok = anchor_fn(txns)
    bank = (round(anchor.running_balance, 2), anchor.date.isoformat()) if anchor is not None and anchor.date else None
    typed = None
    for r in reversed(_rows(session, account.id)):
        if r.typed_balance is not None:
            typed = (r.typed_balance, r.typed_balance_on or (r.created_at.date().isoformat() if r.created_at else None))
            break
    if bank and (not typed or not typed[1] or bank[1] >= typed[1]):
        return {'amount': bank[0], 'as_of': bank[1], 'basis': 'bank',
                'working': f'{money(bank[0])}, the balance on the statement you imported, as of {day(bank[1])}.'}
    if typed:
        when = f' on {day(typed[1])}' if typed[1] else ''
        return {'amount': typed[0], 'as_of': typed[1], 'basis': 'typed',
                'working': f'{money(typed[0])}, the balance you typed{when}.'}
    return {'amount': None, 'as_of': None, 'basis': 'unknown',
            'working': 'No balance yet: type one in, or import a statement that shows the balance.'}


# ── HSA: contributions against the limit (F3, F4, F5) ───────────────────────────────────────────────────────────

def _is_earnings(t):
    text = f'{t.description or ""} {t.merchant or ""} {t.memo or ""}'.lower()
    return any(w in text for w in _EARNINGS)


def contributions(txns, year, today, typed=None):
    """F4: deposits this year from the account's own rows, its earnings left out. Absence is not zero: with no rows
    the total is unknown, and every month so far with nothing imported is named. A typed total wins, labelled."""
    if typed is not None:
        return {'total': typed, 'basis': 'typed', 'missing_months': [], 'complete': True,
                'working': f'{money(typed)}, the total you typed for {year}.'}
    rows = [t for t in txns if t.date and t.date.year == year]
    last_month = 12 if year < today.year else today.month
    seen = {t.date.month for t in rows}
    missing = [date(year, m, 1).strftime('%B') for m in range(1, last_month + 1) if m not in seen]
    if not rows:
        return {'total': None, 'basis': 'unknown', 'missing_months': missing, 'complete': False,
                'working': f'No rows imported into this account for {year}, so its contributions aren\'t known.'
                           ' Import its statements, or type the year\'s total.'}
    deposits = [t for t in rows if t.type == 'credit' and not _is_earnings(t)]
    left_out = [t for t in rows if t.type == 'credit' and _is_earnings(t)]
    total = round(sum(float(t.amount or 0) for t in deposits), 2)
    w = f'{money(total)} from {len(deposits)} deposit{"s" if len(deposits) != 1 else ""} into this account in {year}'
    if left_out:
        w += f'; {len(left_out)} interest or earnings row{"s" if len(left_out) != 1 else ""} left out (they don\'t count toward the limit)'
    w += '.'
    if missing:
        w += ' Nothing imported for ' + ', '.join(missing) + ', so this total may be incomplete.'
    return {'total': total, 'basis': 'record', 'missing_months': missing, 'complete': not missing, 'working': w}


def hsa_limit(year, terms):
    """F3: the limit for the coverage the person entered, with its source; unknown when coverage is unknown or the
    year is not in the table. The 55+ catch-up only on a yes. Assumes a full year of eligible coverage, and says so."""
    fig = LIMITS.get(year, {}).get('hsa')
    if not fig:
        return {'amount': None, 'working': f'The IRS limit for {year} isn\'t in Groundwork\'s table yet.'}
    cov = (terms or {}).get('coverage') or ''
    if not cov:
        return {'amount': None, 'working': 'The limit can\'t be checked until you enter self-only or family coverage.'}
    amt = fig[cov]
    w = f'{money(amt)} for {"self-only" if cov == "self" else "family"} coverage in {year} ({fig["source"]})'
    cu = (terms or {}).get('catch_up') or ''
    if cu == 'yes':
        amt += fig['catch_up']
        w += f', plus the {money(fig["catch_up"])} catch-up at 55 or older'
    elif cu == '':
        w += '; the 55-or-older catch-up isn\'t counted because it hasn\'t been answered'
    w += '. It assumes a full year of eligible coverage; part-year rules aren\'t worked out here.'
    return {'amount': round(amt, 2), 'working': w, 'source': fig['source']}


def hsa_state(session, account, txns, anchor_fn, today=None):
    today = today or date.today()
    year = today.year
    cur = current_by_year(session, account.id).get(year)
    terms = _as_dict(cur)
    bal = balance(session, account, txns, anchor_fn)
    con = contributions(txns, year, today, terms.get('typed_contributions'))
    lim = hsa_limit(year, terms)
    warning, sentence = None, None
    if con['total'] is not None and lim['amount'] is not None:
        over = round(con['total'] - lim['amount'], 2)
        if over > 0:
            warning = 'over_limit'
            sentence = (f'Contributions on record for {year} are {money(con["total"])}, {money(over)} more than the '
                        f'{money(lim["amount"])} limit for the coverage you entered.')
        else:
            sentence = (f'Contributions on record for {year}: {money(con["total"])} of the {money(lim["amount"])} limit'
                        + ('.' if con['complete'] else ', with months missing from the record.'))
    elif con['total'] is not None:
        sentence = f'Contributions on record for {year}: {money(con["total"])}.'
    return {'account_id': account.id, 'name': account.name, 'kind': 'hsa', 'year': year, 'terms': terms,
            'balance': bal, 'contributions': con, 'limit': lim, 'warning': warning, 'sentence': sentence}


# ── FSA: the deadline and what is at risk (F2, F5) ──────────────────────────────────────────────────────────────

def _deadline(terms):
    """(last day to spend, problem). Unknown when the year end or the rule is not entered."""
    if not terms.get('year_end'):
        return None, 'year_end'
    rule = terms.get('rule') or ''
    if rule == 'grace':
        return (terms['grace_until'], None) if terms.get('grace_until') else (None, 'grace_until')
    if rule in ('carryover', 'none'):
        return terms['year_end'], None
    return None, 'rule'


def _pick_plan(rows, today):
    """The plan year still running (its deadline today or later, the soonest), else the latest one entered."""
    running = []
    for r in rows.values():
        dl, _ = _deadline(_as_dict(r))
        end = dl or r.year_end
        if end and end >= today.isoformat():
            running.append((end, r))
    if running:
        return sorted(running, key=lambda x: x[0])[0][1]
    return rows[max(rows)] if rows else None


def fsa_state(session, account, txns, anchor_fn, today=None):
    today = today or date.today()
    cur = _pick_plan(current_by_year(session, account.id), today)
    terms = _as_dict(cur)
    bal = balance(session, account, txns, anchor_fn)
    out = {'account_id': account.id, 'name': account.name, 'kind': 'fsa', 'year': cur.plan_year if cur else None,
           'terms': terms, 'balance': bal, 'deadline': None, 'days': None, 'at_risk': None, 'warning': None,
           'attention': False}
    fig = LIMITS.get(cur.plan_year if cur else today.year, {}).get('fsa')
    out['limit'] = ({'amount': fig['limit'], 'working': f'{money(fig["limit"])} a year for a health FSA ({fig["source"]}); '
                     f'the IRS carryover most is {money(fig["carryover_max"])}, and your plan may allow less or none.'}
                    if fig else {'amount': None, 'working': 'The IRS figures for this plan year aren\'t in Groundwork\'s table yet.'})
    dl, missing = _deadline(terms)
    claims = f' Claims must be submitted by {day(terms["claims_by"])}.' if terms.get('claims_by') else ''
    if bal['amount'] is None:
        out['sentence'] = 'Groundwork can\'t tell whether any FSA money is at risk: there is no balance yet.'
        return out
    if dl is None or (terms.get('rule') == 'carryover' and terms.get('carryover_max') is None):
        out['sentence'] = (f'{money(bal["amount"])} is in your FSA. Groundwork can\'t tell whether any of this is at risk: '
                           'the plan\'s deadline and carryover rule haven\'t been entered.')
        return out
    rule = terms['rule']
    if rule == 'carryover':
        carry = min(bal['amount'], terms['carryover_max'])
        at_risk = round(max(0.0, bal['amount'] - terms['carryover_max']), 2)
        s = (f'{money(bal["amount"])} is in your FSA. Under the terms you entered, up to {money(terms["carryover_max"])} '
             f'carries over and the rest, {money(at_risk)}, is lost after {day(dl)}.')
        if at_risk == 0:
            s = (f'{money(bal["amount"])} is in your FSA. Under the terms you entered, up to '
                 f'{money(terms["carryover_max"])} carries over, so all of it ({money(carry)}) carries past {day(dl)}.')
    elif rule == 'grace':
        at_risk = bal['amount']
        s = (f'{money(bal["amount"])} is in your FSA. Under the terms you entered, the plan year ends {day(terms["year_end"])}'
             f' and the grace period runs to {day(dl)}; what is left after that is lost.')
    else:
        at_risk = bal['amount']
        s = (f'{money(bal["amount"])} is in your FSA. Under the terms you entered, nothing carries over: what is left '
             f'after {day(dl)} is lost.')
    days = (date.fromisoformat(dl) - today).days
    out.update(deadline=dl, days=days, at_risk=at_risk, sentence=s + claims)
    if at_risk > 0 and days >= 0:
        out['warning'] = 'at_risk'
        out['attention'] = days <= FSA_WARN_DAYS
    return out


def states(session, anchor_fn, today=None):
    """Every active HSA and FSA account, with its working."""
    from core.database import Account, Transaction
    out = []
    for a in session.query(Account).filter(Account.type.in_(TYPES), Account.is_active.is_(True)) \
            .order_by(Account.sort_order, Account.name).all():
        txns = session.query(Transaction).filter_by(account_id=a.id).all()
        out.append((hsa_state if a.type == 'hsa' else fsa_state)(session, a, txns, anchor_fn, today))
    return out


def attention(rows):
    """F5: an FSA with money at risk within 60 days, as the facts the dashboard shows."""
    return [{'account_id': r['account_id'], 'account': r['name'], 'deadline': r['deadline'], 'days': r['days'],
             'at_risk': r['at_risk'], 'sentence': r['sentence']}
            for r in rows if r['kind'] == 'fsa' and r.get('attention')]
