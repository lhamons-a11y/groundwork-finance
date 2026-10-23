"""Item 108 (gw 2.0/RECURRING_PER_ACCOUNT.md; Rob 2026-10-22: "R1-R10 as recommended, build it"): a recurring charge
is one payee from one account.

    R1  every recurring reading groups a payee's charges by account, not across all the person's accounts
    R3  where a payee recurs from more than one account, each is its own line, named with its account; from one
        account, the payee's name alone, as before
    R4  (a) a card switch is one charge that moved: one account's charges stop and another's start within about a
        month, at amounts within 5% - read as one charge, on the account it is on now, with its history
    R5  (a) the payee stays the identity: budget lines and every answer the person gave are matched by payee, so each
        reading keeps `payee` and adds `label` and `account` for what is shown

Pure: no database, no words beyond the label.
"""
from statistics import median

SWITCH_DAYS = 31          # R4: the new account starts within about a month of the old one's last charge
SAME = 0.05               # R4: at amounts within 5% (the house "same subscription" rule)


def _median_amount(rows):
    return median(abs(float(r[1] or 0)) for r in rows) if rows else 0.0


def _chains(by_account):
    """R4: {account_id: [(date, amount, *extra)]} -> [(account_id now, rows)] with switches joined."""
    parts = sorted(((acct, sorted(rows, key=lambda r: r[0])) for acct, rows in by_account.items()),
                   key=lambda p: (p[1][0][0], str(p[0])))
    chains = []                                       # [account now, rows, last date, median amount]
    for acct, rows in parts:
        first, last, amt = rows[0][0], rows[-1][0], _median_amount(rows)
        joined = None
        for ch in chains:
            if ch[0] == acct or abs((first - ch[2]).days) > SWITCH_DAYS or not last > ch[2]:
                continue
            if ch[3] <= 0 or abs(amt - ch[3]) > ch[3] * SAME:
                continue
            joined = ch
            break
        if joined:
            joined[0], joined[2] = acct, last
            joined[1] = sorted(joined[1] + rows, key=lambda r: r[0])
        else:
            chains.append([acct, rows, last, amt])
    return [(ch[0], ch[1]) for ch in chains]


def groups(rows, names=None):
    """`rows` [(payee, account_id, date, amount, *extra)] -> [{payee, account_id, account, label, rows}], where each
    group's rows are [(date, amount, *extra)] in date order. `names` {account_id: name}."""
    names = names or {}
    by = {}
    for r in rows:
        payee, acct, d = r[0], r[1], r[2]
        if payee and d:
            by.setdefault(payee, {}).setdefault(acct, []).append(tuple(r[2:]))
    out = []
    for payee, accts in by.items():
        chains = _chains(accts)
        many = len(chains) > 1
        for acct, rs in chains:
            name = names.get(acct) or ''
            out.append({'payee': payee, 'account_id': acct, 'account': name,
                        'label': f'{payee} ({name})' if many and name else payee, 'rows': rs})
    return out
