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

GET only. The POST surface takes side effects by definition - creating backups,
pulling models, writing rows - and sweeping it blindly would be a test that
does damage to prove it can.
"""
import re
import socket


class _Blocked(Exception):
    """Raised in place of any outbound connection attempt during the sweep."""


def _blocked_connect(*_args, **_kwargs):
    raise _Blocked('outbound network is blocked during the route sweep')


def run(ctx):
    check, c, H = ctx.check, ctx.c, ctx.H
    from server import create_app as _create_app

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
