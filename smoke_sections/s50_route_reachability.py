"""Every registered route answers, and none of them needs the internet to do it.

The suite tests routes it knows about. That is a list someone maintained, and
it had drifted: of 134 registered rules, 58 were touched by no check at all -
mostly the 1.x surface (accounts, investments, backup, import), which is the
part most likely to be broken by a refactor aimed at something else and least
likely to be noticed, because nothing here exercises it.

This is the cheap half of that gap, and it is worth having on its own terms. It
does not assert what a route MEANS - that is the job of the checks written per
feature. It asserts the route exists, imports, runs, and returns something that
is not a 500. That catches the whole class of failure where a helper is renamed,
a module is dropped from a spec, or an import moves, and the only symptom is one
page of the app going blank for a user.

Outbound network is blocked while it runs, for two reasons. A route with no
timeout would otherwise hang the suite on a machine with a slow DNS server. And
Groundwork is local-first: every read route is supposed to degrade to something
useful when the machine is offline, and until now nothing checked that. All 77
of them do.

The mutating surface is swept on a different contract, below: not "does it
work" - that would mean creating and destroying real rows - but "does it refuse
what it cannot use". A field left out of a request must come back as a 400 and
not a 500. Four routes failed that the first time it ran.

Sweeping it blindly would be a test that does damage to prove it can, so the
routes that act on an empty body because they require nothing are excluded by
name and by verb, each with the reason it is there.
"""
import re
import socket


class _Blocked(Exception):
    """Raised in place of any outbound connection attempt during the sweep."""


def _blocked_connect(*_args, **_kwargs):
    raise _Blocked('outbound network is blocked during the route sweep')


def run(ctx):
    check, c, H = ctx.check, ctx.c, ctx.H
    from server import create_app as _create_app, db_session as _dbsession

    app = _create_app()
    urls = set()
    for rule in app.url_map.iter_rules():
        if 'GET' not in (rule.methods or ()):
            continue
        raw = str(rule.rule)
        # The static catch-all serves files, not JSON, and has its own checks.
        if raw.startswith('/static') or '<path:' in raw:
            continue
        url = re.sub(r'<int:[^>]+>', '1', raw)
        url = re.sub(r'<[^>]+>', 'x', url)
        urls.add(url)
    urls = sorted(urls)

    # If this ever sweeps nothing it must fail loudly rather than pass by
    # vacuum - a sweep of an empty list is a green check that tested the
    # for-loop. The number only goes up; it is 77 as written.
    check('the route sweep found the app\'s GET surface to sweep',
          len(urls) >= 70)

    _real_connect = socket.socket.connect
    _real_create = socket.create_connection
    broken = []
    try:
        socket.socket.connect = _blocked_connect
        socket.create_connection = _blocked_connect
        for url in urls:
            try:
                resp = c.get(url, headers=H)
                if resp.status_code >= 500:
                    broken.append((url, str(resp.status_code),
                                   resp.get_data(as_text=True)[:120]))
            except Exception as exc:                      # noqa: BLE001
                broken.append((url, 'RAISED', repr(exc)[:120]))
    finally:
        socket.socket.connect = _real_connect
        socket.create_connection = _real_create

    check(f'all {len(urls)} GET routes answer without a 500, with the network '
          f'unavailable', not broken)
    for url, status, detail in broken[:12]:
        print(f'        {url}  ->  {status}  {detail}')

    # ── The mutating surface ────────────────────────────────────────────────
    # The sweep above asks GET routes to answer. Asking a POST route to do its
    # job means creating and destroying real rows, so the contract here is the
    # other one every one of them owes: a request missing what it needs must be
    # REFUSED, not crashed on. body['name'] on a body without a name is a
    # KeyError, and a KeyError reaches the caller as a 500 - the app reporting
    # that it broke when what happened is that a field was left out.
    #
    # Four routes failed this when it was first run: POST /api/budget/items,
    # /api/budget/plan, /api/byb and /api/debt. /api/budget/plan was the one
    # worth the trouble - it retires the active plan BEFORE building the new
    # one, so the failure landed after the retirement, and the only reason it
    # never cost anyone their plan is that the session closes without
    # committing on the way out.
    #
    # Path parameters are filled with an id nothing owns, so a destructive verb
    # sweeps its lookup path and finds nothing there: 404, not 500, and no row
    # is harmed to prove it.
    MISSING_ID = 987654321

    # Routes that ACT on an empty body, because they require nothing. They are
    # excluded per verb rather than per path - DELETE /api/transactions empties
    # the table, while POST /api/transactions on the same path is a create that
    # validates like any other and is swept. Each line is a reason, not a
    # convenience: the ones that reach the network or the filesystem cannot be
    # made safe by a temp database.
    ACTS_ON_EMPTY = {
        ('POST', '/api/ai/install-ollama'),       # downloads and runs an installer
        ('POST', '/api/ai/pull-model'),           # downloads a model
        ('POST', '/api/investments/prices/refresh'),   # reaches the network
        ('POST', '/api/backup'),                  # writes a backup
        ('POST', '/api/backup/create'),           # writes a backup
        ('POST', '/api/backup/restore'),          # overwrites the database
        ('POST', '/api/backup/restore-upload'),   # overwrites the database
        ('POST', '/api/backup/location'),         # moves where backups live
        ('POST', '/api/settings/export-to-file'), # writes a file outside the DB
        ('POST', '/api/save'),                    # saves the settings blob
        ('POST', '/api/net-worth/snapshot'),      # a snapshot needs no fields
        ('POST', '/api/import/commit'),           # commits whatever it is given
        ('POST', '/api/categories/reclassify-income'),  # rewrites rows in bulk
        ('POST', '/api/categories/smart-backfill'),     # rewrites rows in bulk
        ('POST', '/api/sinking-funds/auto-credit'),     # moves money in bulk
        ('DELETE', '/api/transactions'),          # empties the table
    }

    refused, crashed = [], []
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: str(r.rule)):
        raw = str(rule.rule)
        if raw.startswith('/static') or '<path:' in raw:
            continue
        for verb in sorted((rule.methods or set()) - {'GET', 'HEAD', 'OPTIONS'}):
            if (verb, raw) in ACTS_ON_EMPTY:
                continue
            url = re.sub(r'<int:[^>]+>', str(MISSING_ID), raw)
            url = re.sub(r'<[^>]+>', 'nonexistent', url)
            try:
                resp = c.open(url, method=verb, headers=ctx.HJ, json={})
                refused.append((verb, url))
                if resp.status_code >= 500:
                    crashed.append((verb, url, str(resp.status_code)))
            except Exception as exc:                  # noqa: BLE001
                crashed.append((verb, url, repr(exc)[:100]))

    check('the mutating surface is swept too, not just the readable one',
          len(refused) >= 60)
    check(f'all {len(refused)} mutating routes refuse an empty body rather than '
          f'crashing on it', not crashed)
    for verb, url, detail in crashed[:12]:
        print(f'        {verb} {url}  ->  {detail}')

    # The other half of a refusal check, for the two routes that have no other.
    # A guard that rejects everything also passes "it refuses an empty body",
    # and POST /api/debt and POST /api/budget/plan are created nowhere else in
    # this suite - the fixtures build debts straight in the database - so
    # without this, the validation added to them is proven in one direction
    # only. Both rows are removed afterwards: creating a plan retires whatever
    # plan was already active, and that is not something to leave behind.
    from core.database import BudgetPlan as _Plan, DebtAccount as _Debt
    _mk_debt = c.post('/api/debt', headers=ctx.HJ, json={
        'name': 'Route Sweep Card', 'current_balance': 1200,
        'interest_rate': 19.99, 'minimum_payment': 45})
    check('and a create that carries what it needs is still accepted (debt)',
          _mk_debt.status_code in (200, 201))

    _mk_plan = c.post('/api/budget/plan', headers=ctx.HJ, json={
        'goal_amount': 4200, 'goal_months': 14, 'start_month': '2026-09'})
    check('and the same for the plan route, whose guard runs before it retires '
          'the old one', _mk_plan.status_code in (200, 201))
    with _dbsession() as _s:
        _made = _s.query(_Plan).filter_by(goal_amount=4200.0).first()
        _plan_ok = _made is not None and _made.is_active
        for _row in _s.query(_Debt).filter_by(name='Route Sweep Card').all():
            _s.delete(_row)
        if _made is not None:
            _s.delete(_made)
        _s.commit()
    check('the plan it created is the active one, read back from the database',
          _plan_ok)

    # And the specific one that cost an account. An import carrying no records
    # used to fall through to account resolution, find no name, and create one
    # called "Imported" - so a failed import left a stray empty account behind
    # with nothing in it to say where it came from.
    from core.database import Account as _Account
    with _dbsession() as _s:
        _before = _s.query(_Account).count()
    _empty = c.post('/api/import/commit', headers=ctx.HJ, json={'records': []})
    with _dbsession() as _s:
        _after = _s.query(_Account).count()
    check('an import with no records creates nothing, least of all an account',
          _empty.status_code == 400 and _after == _before)

    # The other direction: a route nobody calls. Four of these are real - they
    # predate the 2.0 work and are pinned rather than deleted, because deleting
    # a route is a product decision and this is a test file. The pin is the
    # point: removing one from the app is a passing change, adding a new
    # unreachable route is a failing one.
    UNCALLED = {
        '/api/auto-import/delete-file',
        '/api/budget/variance',
        '/api/debug/bootstrap',      # deliberate: a debug handle, not a feature
        '/api/import/quicken',
    }
    from pathlib import Path as _Path
    callers = ''
    for rel in ('static/js/app.js', 'static/index.html', 'launch.py'):
        callers += (ctx.BASE / rel).read_text(encoding='utf-8')
    for mod in sorted((ctx.BASE / 'static' / 'js' / 'teaching').glob('*.js')):
        callers += mod.read_text(encoding='utf-8')

    unreferenced = set()
    for rule in app.url_map.iter_rules():
        raw = str(rule.rule)
        if raw.startswith('/static') or '<path:' in raw:
            continue
        stem = re.sub(r'<[^>]+>.*$', '', raw).rstrip('/')
        if stem and stem not in callers:
            unreferenced.add(stem)
    check('no route is unreachable from the client or the launcher, beyond the '
          'pinned four', unreferenced == UNCALLED)
    if unreferenced != UNCALLED:
        for r in sorted(unreferenced - UNCALLED):
            print(f'        NEW unreachable route: {r}')
        for r in sorted(UNCALLED - unreferenced):
            print(f'        now reachable (shrink the pin): {r}')
