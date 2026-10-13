"""
Groundwork - a plan's budget edits, and its Undo (gw 2.0/PLAN_EDITS.md, item 80, E1-E6)
=======================================================================================
"Make this my budget" (item 71) and its Undo write one budget_adjusted entry per line. They carry
`source` ('income_change_apply' / 'income_change_undo') and `plan_at` (the apply's time) in their context (E1),
so the Willingness Layer can tell them from the person's own edits:

  - E2  a line the plan cut and its Undo restored contributes nothing - both entries are left out. Undo means
        "not that", not "I keep this".
  - E3  a line the plan cut and nobody restored is read like the person's own edit (they chose the plan).
        A line the person edited after the plan, which the Undo therefore left alone (I6), stays theirs.
  - E4  entries written before E1 carry no source. `unmarked_pairs` finds them by their shape: three or more lines
        written in the same second (a plan's tap), then a later group restoring exactly those lines to exactly
        their old amounts (its Undo). `mark` adds the marker; nothing is deleted - the history stays as it happened.
"""
import json
from collections import OrderedDict

SOURCES = ('income_change_apply', 'income_change_undo')
MIN_LINES = 3          # a hand edit is one line; a plan's tap writes several in the same second


def plan_context(item, source, plan_at):
    return {'budget_item_id': item.id, 'name': item.name, 'item_type': item.type, 'source': source,
            'plan_at': plan_at}


def leave_out(entries):
    """E2: the ids of entries the Willingness Layer must not read - an undone plan's cuts and the Undo's restores.
    `entries` [(id, context dict)] in order."""
    undone = set()
    for _id, c in entries:
        if c.get('source') == 'income_change_undo':
            undone.add((c.get('plan_at'), c.get('budget_item_id')))
    out = set()
    for _id, c in entries:
        if c.get('source') in SOURCES and (c.get('plan_at'), c.get('budget_item_id')) in undone:
            out.add(_id)
    return out


def unmarked_pairs(rows):
    """E4: [(id, created_at, context dict, expected, actual)] of budget_adjusted entries with no source, in order ->
    [{'apply_at', 'undo_at', 'apply_ids', 'undo_ids', 'lines': [{'id', 'name', 'old', 'new'}]}]."""
    groups = OrderedDict()
    for r in rows:
        _id, at, c, old, new = r
        if c.get('source') or at is None or old is None or new is None:
            continue
        groups.setdefault(at.strftime('%Y-%m-%d %H:%M:%S'), []).append(r)
    stamps = [k for k, v in groups.items() if len(v) >= MIN_LINES]
    pairs, used = [], set()
    for i, a in enumerate(stamps):
        if a in used:
            continue
        cut = {g[2].get('budget_item_id'): g for g in groups[a]}
        for b in stamps[i + 1:]:
            if b in used:
                continue
            back = {g[2].get('budget_item_id'): g for g in groups[b]}
            # the Undo restores exactly the lines the plan cut, each from its new amount back to its old one
            mirrored = [k for k, g in back.items() if k in cut
                        and abs(g[3] - cut[k][4]) < 0.005 and abs(g[4] - cut[k][3]) < 0.005]
            if mirrored and len(mirrored) == len(back):
                pairs.append({'apply_at': a, 'undo_at': b,
                              'apply_ids': [cut[k][0] for k in mirrored], 'undo_ids': [back[k][0] for k in mirrored],
                              'lines': [{'id': k, 'name': cut[k][2].get('name') or '', 'old': cut[k][3], 'new': cut[k][4]}
                                        for k in mirrored]})
                used.update((a, b))
                break
    return pairs


def mark(session, pair):
    """E4: add the plan's marker to exactly the matched entries. Returns how many were marked."""
    from core.database import HistorianEntry
    n = 0
    for ids, source in ((pair['apply_ids'], 'income_change_apply'), (pair['undo_ids'], 'income_change_undo')):
        for e in session.query(HistorianEntry).filter(HistorianEntry.id.in_(ids)).all():
            c = json.loads(e.context_json or '{}')
            if c.get('source'):
                continue
            c.update(source=source, plan_at=pair['apply_at'], marked_later=True)
            e.context_json = json.dumps(c)
            n += 1
    return n
