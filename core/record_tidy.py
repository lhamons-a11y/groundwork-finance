"""Item 83 (gw 2.0/RECORD_TIDY.md, ruled 2026-10-13): the agent keeps the record tidy - it proposes, the person decides.

Arithmetic over what it is handed - no database, nothing stored. The server gathers the record and shows each
proposal first; only the person's tap changes anything, and every change has Undo (no silent writing, AP10).

  T1  empty categories: no transactions, no budget line, no import rule, no subcategory in use - offered to hide
      (hiding, never deleting: it leaves every picker and comes back with one tap)
  T2  near-twins: an empty, non-built-in category whose name is another's in a different form (Restaurant /
      Restaurants, Fastfood / Fast Food / Takeout, Charity / Charitable Donations) is offered to merge into the one used
  T3  a merchant filed under two or more categories is asked about, never merged: one store sells different things,
      and a store card's payment is a transfer beside its purchases
  T4  an imported category name is matched to the person's own: exactly, then as a near-twin (a Quicken
      "Parent:Child" name is tried child first, then parent); what matches nothing is kept to ask about
"""
import re

NEVER_HIDE = {'other', 'transfer', 'income', 'uncategorized'}
# Names that look like one but are two on purpose. Gas is the natural-gas utility and Gas / Fuel is fill-ups:
# item 52 (CATEGORY_LABELS.md) separated them because fuel was counted as a gas bill. Found measuring item 83 on Rob's
# data, where the alternatives rule offered Gas -> Gas / Fuel.
NOT_TWINS = {frozenset(('gas', 'gasfuel'))}


def norm(name):
    """Letters and digits only, lower case: 'Fast Food / Takeout' -> 'fastfoodtakeout'."""
    return re.sub(r'[^a-z0-9]', '', (name or '').lower())


def _stem(s):
    if s.endswith('ies') and len(s) > 4:
        return s[:-3] + 'y'                                   # Hobbies -> hobby
    return s[:-1] if s.endswith('s') and len(s) > 3 else s


def _words(name):
    return frozenset(_stem(w) for w in re.findall(r'[a-z0-9]+', (name or '').lower()) if w not in ('and', 'the', 'of'))


def twin(a, b):
    """True when two category names are one name in different forms."""
    x, y = norm(a), norm(b)
    if not x or not y or x == y:
        return bool(x) and x == y
    if frozenset((x, y)) in NOT_TWINS:
        return False
    wa, wb = _words(a), _words(b)
    if len(wa) >= 2 and wa == wb:                             # Insurance:Auto / Auto Insurance
        return True
    if _stem(x) == _stem(y):                                  # Restaurant / Restaurants
        return True
    # one name is one of the other's alternatives: Fastfood / "Fast Food / Takeout", Interest / "Interest / Fees".
    # Measured on Rob's 103 categories 2026-10-13: a starts-with or shared-prefix rule paired Streaming Music with
    # Streaming Video, Health Insurance with Healthcare, Personal with Personal Care - so alternatives only.
    alts = lambda n: [_stem(norm(p)) for p in re.split(r'[/&]', n or '') if norm(p)]
    return (len(alts(b)) > 1 and _stem(x) in alts(b)) or (len(alts(a)) > 1 and _stem(y) in alts(a))


def near_twin(name, names):
    """The person's own category an imported name means, or None: exact (any case), then the same letters, then a
    twin. A Quicken 'Parent:Child' name tries the child, then the parent. Never a guess between two candidates."""
    own = list(names)
    parts = [p.strip() for p in re.split(r'[:>]', name or '') if p.strip()]
    for cand in ([name, parts[-1], parts[0]] if len(parts) > 1 else parts):
        exact = [n for n in own if n.lower() == cand.lower()]
        if exact:
            return exact[0]
        same = [n for n in own if norm(n) == norm(cand)]
        if same:
            return same[0]
        tw = [n for n in own if twin(cand, n)]
        if len(tw) == 1:
            return tw[0]
    return None


def hideable(cats, used, budgeted, ruled):
    """T1. `cats` [{id, name, parent_id, is_system, is_enabled, type}]; `used` {id: transaction count};
    `budgeted` / `ruled` lower-case names a budget line or an import rule uses."""
    kids = {}
    for c in cats:
        if c.get('parent_id'):
            kids.setdefault(c['parent_id'], []).append(c)
    out = []
    for c in cats:
        low = (c['name'] or '').strip().lower()
        if (c.get('is_enabled') is False or used.get(c['id'], 0) or low in budgeted or low in ruled
                or low in NEVER_HIDE or (c.get('type') or 'expense') not in ('expense',)
                or any(used.get(k['id'], 0) or k['name'].lower() in budgeted for k in kids.get(c['id'], []))):
            continue
        out.append({'id': c['id'], 'name': c['name']})
    return sorted(out, key=lambda c: c['name'].lower())


def twins(cats, used, budget_lines):
    """T2. Each empty, non-built-in category with a used twin: [{source, target, line}], where `line` is the source's
    budget line {id, name, amount} when it has one (added into the target's line, as Rob ruled 2026-10-13)."""
    by_line = {}
    for b in budget_lines:
        by_line.setdefault((b.get('category') or '').strip().lower(), []).append(b)
    out = []
    for c in cats:
        if c.get('is_system') or used.get(c['id'], 0):
            continue
        cand = [d for d in cats if d['id'] != c['id'] and used.get(d['id'], 0) and twin(c['name'], d['name'])]
        if len(cand) != 1:
            continue                                          # none, or two to choose between: not ours to pick
        lines = by_line.get(c['name'].strip().lower(), [])
        if len(lines) > 1:
            continue
        d = cand[0]
        out.append({'source': {'id': c['id'], 'name': c['name']}, 'target': {'id': d['id'], 'name': d['name'],
                    'transactions': used[d['id']]},
                    'line': ({'id': lines[0]['id'], 'name': lines[0]['name'], 'amount': lines[0]['amount']} if lines else None),
                    'target_line': next(({'id': b['id'], 'name': b['name'], 'amount': b['amount']}
                                         for b in by_line.get(d['name'].strip().lower(), [])), None)})
    return sorted(out, key=lambda t: t['source']['name'].lower())


def splits(rows, min_each=1):
    """T3. `rows` [(merchant, category, amount, date)] debits: [{merchant, categories: [{name, count, total, last}],
    transfer}] for every merchant filed under two or more categories, the most transactions first."""
    by = {}
    for m, cat, amt, d in rows:
        if not m or not cat:
            continue
        e = by.setdefault(m, {}).setdefault(cat, {'name': cat, 'count': 0, 'total': 0.0, 'last': None})
        e['count'] += 1
        e['total'] = round(e['total'] + abs(float(amt or 0)), 2)
        e['last'] = max(e['last'] or d, d)
    out = []
    for m, cats in by.items():
        cs = [c for c in cats.values() if c['count'] >= min_each]
        if len(cs) < 2:
            continue
        cs.sort(key=lambda c: -c['count'])
        out.append({'merchant': m, 'categories': cs, 'transfer': any(c['name'].lower() == 'transfer' for c in cs),
                    'count': sum(c['count'] for c in cs)})
    return sorted(out, key=lambda s: -s['count'])
