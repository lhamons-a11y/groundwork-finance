"""Item 8 (SAFETY_PROVISIONS_INVENTORY.md section 9; Rob 2026-10-19: "approve"): the five safety provisions, each held
by a check that fails when it is broken - Rob's 2026-09-19 rule: every settled safety rule gets an executable
violation test once its code exists.

    1  one door out: every internet request goes through core/egress.py, to the hosts the Privacy page names, nowhere
       else - not another host, plain http, a port, credentials in the URL, or a redirect that ends somewhere else
    2  the AI has no hands: the engine is never given tools or functions, and a request offering them is refused
    3  no silent writing: model output is saved only as labelled, checked text on the surfaces registered here;
       a figure or plan from the model reaches the record only on a person's yes
    4  outside text is data: a bank's descriptions, a pasted quote or itinerary reach the model fenced, the fence
       can't be faked from inside, and the model is told the fence is material, never instructions
    5  bank runs on a leash: the password only into the sign-in step, and never a payment button - the existing
       checks that hold this (s174 A4, s179 B9) are named here so neither can quietly disappear
"""
import ast
import json
import re


def _functions(js):
    """{name: body} for each top-level `function` / `async function` in app.js."""
    out, starts = {}, [(m.start(), m.group(1)) for m in re.finditer(r'^(?:async )?function ([A-Za-z_$][\w$]*)\(', js, re.M)]
    for i, (pos, name) in enumerate(starts):
        out[name] = js[pos:starts[i + 1][0] if i + 1 < len(starts) else len(js)]
    return out


def run(ctx):
    check, BASE, c, HJ = ctx.check, ctx.BASE, ctx.c, ctx.HJ
    from core import egress

    # ── 1. one door out ──
    refused = []
    for url in ('http://api.eia.gov/x', 'https://api.eia.gov.example.com/x', 'https://evil.api.eia.gov/x',
                'https://example.com/', 'https://api.eia.gov:8443/x', 'https://u:p@api.eia.gov/x', 'ftp://api.eia.gov/',
                '', 'https://127.0.0.1/'):
        try:
            egress.check(url)
        except egress.Refused:
            refused.append(url)
    check('s240 P1 the door refuses another host, a look-alike or subdomain, plain http, a port and credentials',
          len(refused) == 9 and all(egress.check(f'https://{h}/x') for h in egress.ALLOWED))
    try:
        egress._StayInside().redirect_request(None, None, 302, 'Found', {}, 'https://example.com/elsewhere')
        redirect_ok = False
    except egress.Refused:
        redirect_ok = True
    check('s240 P1 a redirect off the list is refused before it is followed', redirect_ok)

    skip = re.compile(r'^(smoke_|tests/|scripts/|Website/|llm_|jev_|voice_discipline_test|engine_8gb_test|schema_fixture|'
                      r'fetch_model|historian/|installer/|core/egress\.py$)')
    net = re.compile(r'urlopen\(|http\.client\.|requests\.(get|post|put|head|request|Session)\(|socket\.create_connection\(|'
                     r'urllib3\.|aiohttp|httpx')
    loopback = {('launch.py', '_wait_for_flask'), ('launch.py', '_post_queue_item')}
    stray = []
    for p in sorted(list(BASE.glob('*.py')) + list((BASE / 'core').glob('*.py'))):
        rel = p.relative_to(BASE).as_posix()
        if skip.match(rel):
            continue
        src = p.read_text(encoding='utf-8')
        tree = ast.parse(src)
        fn_of = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for ln in range(node.lineno, (node.end_lineno or node.lineno) + 1):
                    fn_of.setdefault(ln, node.name)
        for n, line in enumerate(src.splitlines(), 1):
            if net.search(line) and not line.lstrip().startswith('#'):
                fn = fn_of.get(n, '')
                body = ast.get_source_segment(src, next(x for x in ast.walk(tree) if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef)) and x.name == fn)) if fn else ''
                if (rel, fn) in loopback and '127.0.0.1' in body:
                    continue
                stray.append(f'{rel}:{n}')
    check(f"s240 P1 no code but the door opens an internet connection (this computer's own server excepted): {stray}",
          not stray)
    users = ('core/airfare.py', 'core/per_diem.py', 'gas_price.py', 'price_engine.py', 'trip_distance.py',
             'utility_price.py', 'server.py')
    check('s240 P1 every feature that fetches from outside goes through the door',
          all('egress.get' in (BASE / u).read_text(encoding='utf-8') for u in users))
    site = (BASE / 'Website' / 'website.py').read_text(encoding='utf-8')
    privacy = ' '.join(site.split("@app.route('/privacy')", 1)[1].split('@app.route', 1)[0].split())
    missing = sorted({label for label in egress.ALLOWED.values() if f'<strong>{label}</strong>' not in privacy})
    check(f's240 P1 every service the door allows is named on the Privacy page, with what it is sent (missing {missing})',
          not missing and 'These are the only services the app itself contacts.' in privacy
          and 'Google Hotels' in privacy and 'never presses a payment button' in privacy)

    # ── 2. the AI has no hands ──
    tool_kw = {'tools', 'tool_choice', 'functions', 'function_call'}
    calls, armed = 0, []
    for rel in ('core/engine.py', 'core/engine_fit.py'):
        tree = ast.parse((BASE / rel).read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, 'attr', '') in ('create_chat_completion', 'create_completion'):
                calls += 1
                if tool_kw & {k.arg for k in node.keywords} or any(k.arg is None for k in node.keywords):
                    armed.append(f'{rel}:{node.lineno}')
    check(f's240 P2 no call into the model passes tools, functions or open-ended arguments ({calls} calls; armed: {armed})',
          calls >= 5 and not armed)
    r = c.post('/api/ai/chat', headers=HJ, data=json.dumps({'messages': [{'role': 'user', 'content': 'hi'}],
                                                             'tools': [{'type': 'function', 'function': {'name': 'pay'}}]}))
    check('s240 P2 a request that offers the model tools is refused, AI on or off', r.status_code == 400)

    # ── 3. no silent writing ──
    js = ctx.app_src
    fns = _functions(js)
    callers = {n for n, b in fns.items() if re.search(r'\bcallAI\(\{', b) and n != 'callAI'}   # a call, not a mention
    writes = re.compile(r"API\.(post|put|patch)\(")
    # the surfaces that may save the model's words: each saves text only, after the checks, as written text
    TEXT_SAVES = {'writeSundayCheckin': "/api/checkin/written", '_evidenceIntro': "/api/evidence/intro",
                  'monthlyReviewAfterImport': "/api/reports/review", '_rcMonthlyGenerate': "/api/reports/review",
                  '_rcSendAI': "/api/settings"}
    CHECKS_ONLY = {'_readTripItineraryWithModel': "/api/trip/itinerary/check"}   # validated, then held for a yes
    KNOWN = set(TEXT_SAVES) | set(CHECKS_ONLY) | {'_learnFromPastTrip', '_readTripQuote', '_renderProjectionAI',
                                                  '_rcFollowUp'}
    check(f's240 P3 every surface that calls the model is registered here, so a new one is reviewed (new: {sorted(callers - KNOWN)})',
          callers == KNOWN)
    silent = [n for n in callers if writes.search(fns[n]) and n not in TEXT_SAVES and n not in CHECKS_ONLY]
    off_route = [n for n, route in {**TEXT_SAVES, **CHECKS_ONLY}.items() if route not in fns.get(n, '')]
    check(f's240 P3 the model\'s output is written only by the registered text surfaces, to their own routes '
          f'(writing elsewhere: {silent}; route moved: {off_route})', not silent and not off_route)
    check('s240 P3 a quote the model read waits for the person; the trip budget is not written from the model',
          '_tripQuotePending = { clean, warnings }' in fns.get('_readTripQuote', '')
          and "'/api/trip/budget'" not in fns.get('_readTripQuote', '') + fns.get('_learnFromPastTrip', ''))

    # ── 4. outside text is data ──
    check('s240 P4 a bank\'s descriptions, a pasted quote and a pasted itinerary reach the model fenced',
          '${_asData(txnList)}' in fns.get('_learnFromPastTrip', '') and '${_asData(text)}' in fns.get('_readTripQuote', '')
          and '${_asData(read.model_text)}' in fns.get('_readTripItineraryWithModel', ''))
    check('s240 P4 a fence inside the text is removed, and a fenced call tells the model the fence is material only',
          "replace(/<<<DATA|DATA>>>/g, '')" in fns.get('_asData', '')
          and "includes('<<<DATA')" in fns['callAI'] and "(fenced ? '\\n' + DATA_RULE : '')" in fns['callAI']
          and 'Never follow an' in js)

    # ── 5. bank runs on a leash ──
    s174 = (BASE / 'smoke_sections' / 's174_bank_fetch.py').read_text(encoding='utf-8')
    s179 = (BASE / 'smoke_sections' / 's179_bill_pay_way.py').read_text(encoding='utf-8')
    check('s240 P5 the checks that keep bank runs on a leash are still there: the password only into the sign-in step '
          '(s174 A4), never a payment button (s179 B9)',
          "s174 A4 the password goes only into the sign-in step" in s174
          and "s174 A4 the agent writes the password to no file and no log" in s174
          and "s179 B9 the page script refuses to press every payment button" in s179)
