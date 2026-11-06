"""An activity total is not a balance (independent engineering review, 2026-11-05).

Three months imported into a checking account nets $1,500 while the bank holds $2,300. The server already labelled that
figure 'activity'; the page added it into net worth anyway, saved it as if it had been typed, and a failed account read
as a real $0.00. Now:

    B1   the server: a balance is the bank's or activity, an unreadable account has no balance, a failed read is a failure
    B2   Net Worth counts only known balances, and names the accounts it left out
    B3   a figure saved before the source was kept is shown as unconfirmed until the person answers
    B4   the source survives a reload: a typed figure stays typed; a figure from the accounts follows them
    B5   the Accounts page shows activity as activity, says when a balance is from, and shows an unreadable account as one

The page's helpers are run for real, under node, extracted from app.js.
"""
import json
import subprocess


def _extract(src, name):
    s = src.index('function ' + name + '(')
    i = src.index('{', s)
    d = 0
    for p in range(i, len(src)):
        if src[p] == '{':
            d += 1
        elif src[p] == '}':
            d -= 1
            if d == 0:
                return src[s:p + 1]
    raise ValueError('unbalanced ' + name)


HARNESS = """
global.esc = s => String(s);
global.fmt = n => '$' + Number(n).toFixed(2);
global.fmtDate = s => s;
global.ACCOUNT_TYPES = { checking: 'Checking', savings: 'Savings' };
global.g = () => null;
const bank = { id: 1, name: 'Bank Checking', type: 'checking', balance: 2300, balance_basis: 'bank', balance_as_of: '2026-10-30', transaction_count: 9 };
const odd = { id: 2, name: 'Odd Savings', type: 'savings', balance: 100, balance_basis: 'bank_unordered', balance_as_of: '2026-10-29', transaction_count: 3 };
const act = { id: 3, name: 'Partial Checking', type: 'checking', balance: 1500, balance_basis: 'activity', activity_net: 1500, balance_as_of: null, transaction_count: 40 };
const bad = { id: 4, name: 'Broken Savings', type: 'savings', balance: null, balance_basis: 'error', error: 'x', transaction_count: null };
const out = {};
const state = (accounts, netWorth) => { global.S = { accounts, netWorth, accountsLoaded: true, hsaFsa: [] }; };

state([bank, odd, act, bad], {});
const l = _nwLinkedCash();
out.linked = { total: l.total, known: l.known.map(a => a.id), unknown: l.unknown.map(a => a.id) };
out.gapMixed = _nwSavingsGapNote();

state([act], { savings: 1500 });
out.legacyWithAccounts = _nwSavingsSource();
out.gapLegacy = _nwSavingsGapNote();
state([], { savings: 1500 });
out.legacyNoAccounts = _nwSavingsSource();
state([act], { savings: 0 });
out.emptyWithAccounts = _nwSavingsSource();
state([act], { savings: 1500, savingsSource: 'typed' });
out.typed = _nwSavingsSource();
out.gapTyped = _nwSavingsGapNote();

state([act], { savings: 1500 });
_nwSavingsTyped({ value: '2300' });
out.afterTyping = S.netWorth.savingsSource;
_nwSavingsTyped({ value: '  ' });
out.afterClearing = S.netWorth.savingsSource;

state([bank, act, bad], {});
out.rowBank = _accountRowHTML(bank);
out.rowActivity = _accountRowHTML(act);
out.rowBad = _accountRowHTML(bad);
out.asideUnknown = _setAsideLine({ ...act, set_aside: 300, goals_set_aside: [{ name: 'Trip', amount: 300 }], available: 1200 });
console.log(JSON.stringify(out));
"""


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    import server

    def data(r):
        d = r.get_json(silent=True) or {}
        return d.get('data', d)

    def row(aid):
        return next(x for x in data(c.get('/api/accounts/with-balances', headers=H)) if x['id'] == aid)

    def txn(aid, day, amount, kind, running=None):
        body = {'account_id': aid, 'date': day, 'description': 's290 row', 'merchant': 's290 row', 'amount': amount,
                'type': kind, 'category': 'Transfer', 'source': 'manual'}
        c.post('/api/transactions', headers=HJ, data=json.dumps(body))

    # B1: the server
    aid = data(c.post('/api/accounts', headers=HJ, data=json.dumps({'name': 's290 Partial', 'type': 'checking'})))['id']
    txn(aid, '2026-09-01', 6000, 'credit')
    txn(aid, '2026-09-02', 4500, 'debit')
    r = row(aid)
    check(f"s290 B1 three months imported, no bank balance: basis activity, the net kept as activity ({r.get('balance_basis')}, {r.get('activity_net')})",
          r['balance_basis'] == 'activity' and r['activity_net'] == 1500 and r['balance_as_of'] is None)

    done = data(c.post(f'/api/accounts/{aid}/recalculate-balances', headers=HJ,
                       data=json.dumps({'anchor_balance': 2300, 'anchor_date': '2026-10-01', 'direction': 'backward'})))
    r = row(aid)
    check(f"s290 B1 the person enters the balance: it is known, dated, and the activity is unchanged ({r.get('balance')}, {r.get('balance_basis')})",
          done.get('current_balance') == 2300 and 'fmt(result.current_balance)' in ctx.app_src
          and r['balance'] == 2300 and r['balance_basis'] == 'bank'
          and r['balance_as_of'] == '2026-09-02' and r['activity_net'] == 1500)

    real = server._resolve_bank_anchor

    def broken(_txns):
        raise ValueError('s290 unreadable')
    server._resolve_bank_anchor = broken
    try:
        r = row(aid)
    finally:
        server._resolve_bank_anchor = real
    check(f"s290 B1 an account that cannot be read has no balance and no count, not $0 and 0 ({r.get('balance')}, {r.get('transaction_count')})",
          r['balance'] is None and r['transaction_count'] is None and r['balance_basis'] == 'error' and r['type'] == 'checking'
          and r['error'] and r['available'] is None)

    real_session = server.db_session

    def no_session():
        raise RuntimeError('s290 no database')
    server.db_session = no_session
    try:
        failed = c.get('/api/accounts/with-balances', headers=H)
    finally:
        server.db_session = real_session
    check(f'a failed read of the accounts is a failure, not an empty list (s290 B1, {failed.status_code})',
          failed.status_code == 500 and failed.get_json().get('ok') is False)

    # B4: the source round-trips through the database and the load the page boots from
    before = data(c.get('/api/settings/bootstrap', headers=H))['netWorth']
    c.patch('/api/settings', headers=HJ, data=json.dumps({'savings_balance': '2300', 'savings_balance_source': 'typed'}))
    after = data(c.get('/api/settings/bootstrap', headers=H))['netWorth']
    check(f"s290 B4 the savings source comes back on load ({before.get('savingsSource')!r} then {after.get('savingsSource')!r})",
          after['savingsSource'] == 'typed' and after['savings'] == 2300)
    c.patch('/api/settings', headers=HJ, data=json.dumps({'savings_balance': '0', 'savings_balance_source': ''}))

    # The assistant is told what the figure is
    from core import agent_hands as ah
    said = ah.lk_balances(ah.Reader(lambda path: [{'name': 'A', 'type': 'checking', 'balance': 1500.0, 'balance_basis': 'activity'},
                                                  {'name': 'B', 'type': 'savings', 'balance': None, 'balance_basis': 'error'}]
                                    if 'with-balances' in path else [], None), {})['accounts']
    check(f"s290 the assistant hears an activity total as unconfirmed and an unreadable account as unreadable ({said})",
          'not a confirmed balance' in said[0]['known_from'] and said[1]['balance'] is None and 'could not be read' in said[1]['known_from'])

    no_read = ah.lk_balances(ah.Reader(lambda path: {'ok': False, 'error': 'x'}, None), {})
    check('s290 the assistant is told a failed read failed, not that there are no accounts', no_read.get('enough') is False)

    # B2, B3, B5: the page's own code, under node
    js = ctx.app_src
    names = ('_acctBalanceKnown', '_nwCashAccounts', '_nwLinkedCash', '_nwSavingsSource', '_nwSavingsTyped', '_nwSavingsGapNote',
             '_accountBasisLine', '_setAsideLine', '_accountRowHTML')
    script = '\n'.join(_extract(js, n) for n in names) + '\nconst _portalButtonsHTML = () => "", _hsaFsaPanelHTML = () => "";\n' + HARNESS
    try:
        proc = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=60)
        res = json.loads(proc.stdout.strip() or '{}')
    except Exception as e:                      # noqa: BLE001
        res, proc = {}, None
        print(f'        node harness failed: {e}')
    if not res and proc is not None:
        print(f'        node harness: {proc.stderr[:500]}')

    linked = res.get('linked') or {}
    check(f'B2 net worth counts bank balances only: activity and an unreadable account are left out (s290, {linked})',
          linked.get('total') == 2400 and linked.get('known') == [1, 2] and linked.get('unknown') == [3, 4])
    check('s290 B2 what is left out is named, beside the headline and in the snapshot note',
          'leaves out Partial Checking, Broken Savings' in (res.get('gapMixed') or '')
          and '_nwSavingsGapNote()].filter(Boolean)' in js and 'const nwSavingsGap = _nwSavingsGapNote();' in js)
    check('s290 B3 a figure saved before the source was kept, with accounts on record, is unconfirmed; the note says so',
          res.get('legacyWithAccounts') == 'unconfirmed' and 'not confirmed' in (res.get('gapLegacy') or ''))
    check('s290 B3 with no accounts it cannot have been filled in, so it stands; with nothing saved the accounts are used',
          res.get('legacyNoAccounts') == 'typed' and res.get('emptyWithAccounts') == 'accounts')
    check('s290 B3 a typed figure is not questioned, typing confirms, and clearing the field goes back to the accounts',
          res.get('typed') == 'typed' and res.get('gapTyped') == '' and res.get('afterTyping') == 'typed'
          and res.get('afterClearing') == 'accounts')
    check('s290 B3 an unconfirmed figure earns no achievement, and the person is asked',
          "savings >= 500 && savingsSource !== 'unconfirmed'" in js and "_nwSetSavingsSource('typed')" in js
          and "linked.known.length\n          ? `<button class=\"btn btn-ghost btn-sm\" onclick=\"_nwSetSavingsSource('accounts')\"" in js
          and 'id="nwSavingsNote"' in ctx.html_src
          and '_nwSavingsTyped(this); updateNetWorth()' in ctx.html_src)
    bank, act, bad = res.get('rowBank') or '', res.get('rowActivity') or '', res.get('rowBad') or ''
    check('s290 B5 a bank balance: the figure and its date',
          '$2300.00' in bank and 'As of 2026-10-30' in bank)
    check('s290 B5 activity: not shown as the balance; the net named as activity, with a way to enter the balance',
          'balance not confirmed' in act and 'Imported activity nets $1500.00' in act and '_accountEnterBalance(3)' in act)
    check('s290 B5 an unreadable account says so, with no $0.00 and no "null txns"',
          'could not be read' in bad and '$0.00' not in bad and 'null' not in bad)
    check('s290 B5 with no confirmed balance, what is available is not claimed',
          'needs a confirmed balance' in (res.get('asideUnknown') or '') and '1200' not in (res.get('asideUnknown') or ''))

    c.delete(f'/api/accounts/{aid}', headers=H)
