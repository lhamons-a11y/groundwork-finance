"""The request-host guard: a DNS-rebinding page is refused, and Groundwork's own requests are not.

`gw 2.0/BANK_BROWSER.md` F12, ruled 2026-09-23 to land before the bank window. `/` writes the session token into
index.html for anyone who asks, and the token check alone never asked who was asking: a page whose hostname was
made to resolve to 127.0.0.1 is same-origin with this server, reads the token, and has every /api/* route. The
Host header gives it away - the browser always sends the page's own hostname.

Two halves, and both are the evidence. Refusing a hostile Host proves nothing on its own if the app's own window,
the Downloads watcher and the startup health check are refused with it, so every case below is one of the pair:

    refused   a rebinding Host on /, on /api/*, on the token-exempt /api/health; a foreign or null Origin on
              /api/*; a loopback name on a port this request did not arrive on - and no token in any refusal
    admitted  127.0.0.1 and localhost on the arriving port, with no Origin or a matching one, on / and /api/*;
              the watcher's exact request (launch._queue_import_file: POST, urllib, no Origin); the bare
              `localhost` Flask's test client sends

Then the guard is broken three ways, and each break must fail at least one case:

    the Host check removed        only the Origin test left
    the Origin check removed      only the Host test left
    the allowed host widened      a third name admitted beside the two loopback names

Measured on the real stack when it was built (not re-run here - it needs a window): WebView2 sent
`Host: 127.0.0.1:8765` on all 33 requests of a cold boot, the one Origin it sent matched, none was refused.
"""


def _cases(c, H, server):
    def req(path, host, port, origin=None, token=True, method='get', **kw):
        headers = dict(H) if token else {}
        headers['Host'] = host
        if origin is not None:
            headers['Origin'] = origin
        r = getattr(c, method)(path, headers=headers, environ_overrides={'SERVER_PORT': port}, **kw)
        return r.status_code, (b'GW_SESSION_TOKEN' in r.data or server._GW_TOKEN.encode() in r.data)

    refused = {
        'a rebinding Host on / is refused, no token in the body':
            req('/', 'evil.example:8765', '8765', token=False) == (403, False),
        'a rebinding Host on /api/* is refused, even carrying the token':
            req('/api/settings/bootstrap', 'evil.example:8765', '8765')[0] == 403,
        'a rebinding Host on the token-exempt /api/health is refused':
            req('/api/health', 'evil.example:8765', '8765', token=False)[0] == 403,
        'a foreign Origin on /api/* is refused':
            req('/api/settings/bootstrap', '127.0.0.1:8765', '8765', origin='http://evil.example:8765')[0] == 403,
        'another local port as Origin on /api/* is refused':
            req('/api/settings/bootstrap', '127.0.0.1:8765', '8765', origin='http://localhost:3000')[0] == 403,
        'a null Origin on /api/* is refused':
            req('/api/settings/bootstrap', '127.0.0.1:8765', '8765', origin='null')[0] == 403,
        'a loopback name on a port the request did not arrive on is refused':
            req('/', '127.0.0.1:9999', '8765', token=False)[0] == 403,
    }
    admitted = {
        '127.0.0.1 on its own port gets / with the token':
            req('/', '127.0.0.1:8765', '8765', token=False) == (200, True),
        'localhost on its own port gets / with the token':
            req('/', 'localhost:8765', '8765', token=False) == (200, True),
        '127.0.0.1 /api/* with no Origin is admitted':
            req('/api/settings/bootstrap', '127.0.0.1:8765', '8765')[0] == 200,
        '127.0.0.1 /api/* with its own Origin is admitted (the WebView POST shape)':
            req('/api/settings/bootstrap', '127.0.0.1:8765', '8765', origin='http://127.0.0.1:8765')[0] == 200,
        'localhost /api/* with its own Origin is admitted':
            req('/api/settings/bootstrap', 'localhost:8765', '8765', origin='http://localhost:8765')[0] == 200,
        "dev_server.py's port is admitted on its own terms":
            req('/api/settings/bootstrap', '127.0.0.1:8766', '8766', origin='http://127.0.0.1:8766')[0] == 200,
        '_wait_for_flask\'s /api/health is admitted':
            req('/api/health', '127.0.0.1:8765', '8765', token=False)[0] == 200,
        "the watcher's request (POST, urllib, no Origin) is admitted":
            req('/api/auto-import/queue', '127.0.0.1:8765', '8765', method='post',
                json={'filename': 's125.csv', 'content': 'Date,Description,Amount\n', 'path': ''},
                ) [0] == 200,
        "the test client's bare localhost is admitted":
            c.get('/api/settings/bootstrap', headers=H).status_code == 200,
    }
    # the watcher case queued an item; drain it so no later section sees it
    c.get('/api/auto-import/pending', headers=H)
    return refused, admitted


def _mutations(server):
    real_refusal, real_names = server._request_host_refusal, server._LOCAL_HOSTNAMES

    def no_host_check(environ, path):
        env = dict(environ, HTTP_HOST=f"127.0.0.1:{environ.get('SERVER_PORT', '')}")
        return real_refusal(env, path)

    def no_origin_check(environ, path):
        env = {k: v for k, v in environ.items() if k != 'HTTP_ORIGIN'}
        return real_refusal(env, path)

    def set_refusal(fn):
        server._request_host_refusal = fn

    def set_names(names):
        server._LOCAL_HOSTNAMES = names

    def restore():
        server._request_host_refusal = real_refusal
        server._LOCAL_HOSTNAMES = real_names

    return [
        ('the Host check removed',     lambda: set_refusal(no_host_check)),
        ('the Origin check removed',   lambda: set_refusal(no_origin_check)),
        ('the allowed host widened',   lambda: set_names(real_names + ('evil.example',))),
    ], restore


def run(ctx):
    check, c, H = ctx.check, ctx.c, ctx.H
    import server

    src = ctx.server_src
    i_host, i_token = src.find('def _check_request_host'), src.find('def _check_session_token')
    check('s125 the host guard is registered before the token check (it must cover / and /api/health, which the token check exempts)',
          0 < i_host < i_token)
    check('s125 the allowed names are exactly the two loopback names',
          server._LOCAL_HOSTNAMES == ('127.0.0.1', 'localhost'))

    refused, admitted = _cases(c, H, server)
    for name, ok in refused.items():
        check(f's125 refused: {name}', ok)
    for name, ok in admitted.items():
        check(f's125 admitted: {name}', ok)
    baseline = all(refused.values()) and all(admitted.values())

    mutations, restore = _mutations(server)
    for label, apply in mutations:
        try:
            apply()
            r, a = _cases(c, H, server)
            caught = not (all(r.values()) and all(a.values()))
        finally:
            restore()
        check(f's125 mutation caught: {label}', baseline and caught)

    r, a = _cases(c, H, server)
    check('s125 the guard is left as found (baseline re-established after the mutations)',
          all(r.values()) and all(a.values()) and server._request_host_refusal.__module__ == 'server')
