"""Item 57 stage 2: "show me once" (gw 2.0/BANK_AGENT.md A5; Rob 2026-10-09: "BUILD 57").

    A1  the plain viewer (bank_window.py) is unchanged - s126 still holds it; the agent's page actions live in
        bank_agent_window.py, in the same kind of separate process, importing nothing of Groundwork's
    A5  recorded: the clicked control's name and role, and a choice from a list; NEVER a typed value, page content,
        balances or account numbers (four or more digits masked); a sign-in is recorded as "sign in", no values;
        the steps come back in words and are saved per account only on the user's yes, re-checked when saved
"""
import json
import re


def run(ctx):
    check, c, H, HJ, BASE = ctx.check, ctx.c, ctx.H, ctx.HJ, ctx.BASE
    import bank_agent_window as baw
    from core.database import Account, AppSetting, db_session

    src = (BASE / 'bank_agent_window.py').read_text(encoding='utf-8')
    body = src.split('"""', 2)[2]
    check('s173 A1 the agent\'s window imports nothing of Groundwork\'s - no server, core, database or network library',
          not re.search(r'^\s*(from|import)\s+(server|core|sqlite3|sqlalchemy|requests|urllib\.request|http\.client|socket)\b', body, re.M)
          and '/api/' not in body.split('# ── Groundwork\'s side')[0])
    check('s173 A1 the plain viewer still sets no js_api and runs no page script (s126 holds the rest)',
          'js_api' not in (BASE / 'bank_window.py').read_text(encoding='utf-8').split('"""', 2)[2]
          and 'evaluate_js' not in (BASE / 'bank_window.py').read_text(encoding='utf-8').split('"""', 2)[2])
    full = baw.RECORD_SCRIPT
    # The recording bar only DRAWS on the page (its own shadow root); the recorder is checked without it
    script = full[:full.index('  function gwBar(')] + full[full.index('  window.__gwBar = gwBar;'):]
    check('s173 A5 the page script never reads a typed value - no .value, no password, text or date box read',
          '.value' not in script and "getAttribute('value')" in script and 'type === \'submit\'' in script
          and 'innerHTML' not in script
          # the page's text is read only inside checkPage(), as a yes/no test for a code-check page; it never leaves
          and script.count('document.body.innerText') == 1
          and all(script.index('function checkPage()') < m.start() < script.index('function signInForm(')
                  for m in re.finditer(r'document\.body', script)))
    check('s173 A5 it acts on real clicks and choices only (isTrusted)', script.count('e.isTrusted') == 2)

    # the cleaner: what leaves the page
    cases = [
        ({'k': 'click', 'role': 'a', 'text': 'Download transactions'}, {'k': 'click', 'role': 'a', 'text': 'Download transactions'}),
        ({'k': 'click', 'role': 'a', 'text': 'Checking ...4321 balance $1,250.00'}, {'k': 'click', 'role': 'a', 'text': 'Checking ...•••• balance ••••'}),
        # Rob's first real run: a link named with two balances - both masked, and run together into one mark
        ({'k': 'click', 'text': 'STANDARD CHECKING ******1234 - 20 $2,608.57 $2,396.32'}, {'k': 'click', 'text': 'STANDARD CHECKING ******•••• - 20 ••••'}),
        ({'k': 'choose', 'field': 'Range', 'option': 'Last 30 days'}, {'k': 'choose', 'field': 'Range', 'option': 'Last 30 days'}),
        ({'k': 'choose', 'option': 'Trust Device', 'opt': True}, {'k': 'choose', 'option': 'Trust Device', 'opt': True}),
        ({'k': 'choose', 'option': 'Trust Device', 'opt': 'yes'}, {'k': 'choose', 'option': 'Trust Device'}),
        ({'k': 'sign_in_user', 'opt': False}, {'k': 'sign_in_user'}),
        ({'k': 'choose', 'field': 'Date range', 'option': 'Last 30 days'}, {'k': 'choose', 'field': 'Date range', 'option': 'Last 30 days'}),
        ({'k': 'sign_in'}, {'k': 'sign_in'}),
        ({'k': 'type', 'field': 'Password', 'value': 'hunter2'}, None),
        ({'k': 'click', 'text': 'Go', 'value': 'secret'}, {'k': 'click', 'text': 'Go'}),
        ({'k': 'click', 'text': ''}, None),
    ]
    got = [baw.clean_step(a) for a, _ in cases]
    check('s173 A5 only the named fields and kinds leave the page; a typed value is dropped; amounts, balances and account numbers are masked; a small number like "30 days" stays',
          got == [b for _, b in cases])
    check('s173 A5 Groundwork checks each line again: an extra field or an unknown kind is refused',
          baw.parse_step_line('step {"k":"click","text":"Go","value":"x"}') is None
          and baw.parse_step_line('step {"k":"type","text":"x"}') is None
          and baw.parse_step_line('step {"k":"click","text":"Go"}') == {'k': 'click', 'text': 'Go'}
          and baw.parse_step_line('fare 12.00') is None)
    check('s173 A5 the steps read as words',
          [baw.step_words(s) for s in ({'k': 'sign_in'}, {'k': 'click', 'text': 'Accounts'}, {'k': 'choose', 'field': 'Format', 'option': 'CSV'})]
          == ['Sign in (Groundwork fills your saved login)', 'Click “Accounts”', 'Choose “CSV” in “Format”'])

    made = []
    try:
        with db_session() as s:
            a = Account(name='s173 Checking', type='checking', is_active=True, portal_url='https://bank.example.com')
            b = Account(name='s173 No Link', type='checking', is_active=True)
            s.add_all([a, b]); s.commit()
            made += [a.id, b.id]
            ka, kb = f'account:{a.id}', f'account:{b.id}'
        r = c.post('/api/settings/bank-agent/record', headers=HJ, data=json.dumps({'key': kb}))
        check('s173 A5 an account with no bank link cannot be recorded', r.status_code == 400)
        baw.begin_for_test(ka)
        baw.collect(ka, ['ready\n', 'step {"k":"sign_in"}\n', 'step {"k":"click","role":"a","text":"Accounts"}\n',
                         'step {"k":"click","text":"Go","value":"x"}\n', 'nonsense\n',
                         'step {"k":"choose","field":"Range","option":"Last 30 days"}\n', 'step {"k":"click","role":"button","text":"Download"}\n'])
        live = c.get(f'/api/settings/bank-agent/record?key={ka}', headers=H).get_json()['data']
        check('s173 A5 the steps arrive as the user works, in words; a line with a typed value is refused',
              live['words'] == ['Sign in (Groundwork fills your saved login)', 'Click “Accounts”',
                                'Choose “Last 30 days” in “Range”', 'Click “Download”'])
        fin = c.post('/api/settings/bank-agent/record/finish', headers=HJ, data=json.dumps({'key': ka})).get_json()['data']
        with db_session() as s:
            saved_before = s.query(AppSetting).filter_by(key=f'bank_recipe:{ka}').first()
        check('s173 A5 finishing hands back the steps and saves nothing on its own', len(fin['steps']) == 4 and saved_before is None)
        tampered = fin['steps'] + [{'k': 'click', 'text': 'Pay 4111111111111111', 'value': 'x'}]
        sv = c.post('/api/settings/bank-agent/recipe', headers=HJ, data=json.dumps({'key': ka, 'steps': tampered})).get_json()['data']
        got = c.get(f'/api/settings/bank-agent/recipe?key={ka}', headers=H).get_json()['data']
        check('s173 A5 on the user\'s yes the steps are saved for that account - cleaned again (no value, digits masked)',
              got['steps'] == sv['steps'] and len(got['steps']) == 5 and got['steps'][-1] == {'k': 'click', 'text': 'Pay ••••'}
              and 'value' not in json.dumps(got['steps']))
        c.post('/api/settings/bank-agent/recipe/delete', headers=HJ, data=json.dumps({'key': ka}))
        check('s173 A5 the saved steps can be deleted', c.get(f'/api/settings/bank-agent/recipe?key={ka}', headers=H).get_json()['data']['steps'] == [])
    finally:
        with db_session() as s:
            s.query(AppSetting).filter(AppSetting.key.like('bank_recipe:%')).filter(AppSetting.key.in_([f'bank_recipe:account:{i}' for i in made])).delete(synchronize_session=False)
            s.query(Account).filter(Account.id.in_(made)).delete(synchronize_session=False)
            s.commit()
    launch = (BASE / 'launch.py').read_text(encoding='utf-8')
    check('s173 A1 the agent\'s process is dispatched before anything else starts, like the viewer\'s',
          launch.index("'--bank-agent' in sys.argv") < launch.index('logging.basicConfig(')
          and launch.index("'--bank-window' in sys.argv") < launch.index("'--bank-agent' in sys.argv"))
    script2 = baw.RECORD_SCRIPT
    check('s173 A5 a sign-in is recorded on any submit of a sign-in form - Enter included, not just a click (Rob\'s first real run)',
          "document.addEventListener('submit'" in script2 and 'signInForm(e.target)' in script2
          and 'if (signInForm(el.closest' in script2)
    check('s173 A5 steps taken on a code-check page are marked optional ("only if your bank asks")',
          script2.count('opt: checkPage()') == 5 and script2.count('pop: inPopup(el)') == 3
          and baw.step_words({'k': 'choose', 'option': 'Trust Device', 'opt': True}) == 'Choose \u201cTrust Device\u201d (only if your bank asks)')
    rs = baw.RECORD_SCRIPT
    check('s173 A5 the recording window shows that it is recording, with a live count, and says it never notes what you type (Rob: "so the user knows when to start")',
          'Recording for Groundwork' in rs and 'never what you type' in rs and 'step(s) noted' not in rs and "noted + ' step'" in rs
          and "pointer-events:none" in rs and 'attachShadow' in rs)
    check('s173 A5 the bar is visual only: it takes no clicks and is never recorded (it lives in a shadow root the recorder never sees)',
          rs.count('function note(') == 1 and rs.count('window.pywebview.api.step(') == 1)

    check('s173 A5 while recording the bar shows a blinking red dot (Rob: "a blinking red button instead of white"), steady for reduced motion',
          '#e5322d' in rs and '@keyframes gwrec' in rs and 'prefers-reduced-motion' in rs and "'rec');" in rs
          and "tone === 'rec' ? 'inline-block' : 'none'" in baw.DO_SCRIPT)
    # Rob: "the steps are not getting deleted when you record over them"
    ka2 = 'account:999173'
    baw.begin_for_test(ka2)
    baw.collect(ka2, ['step {"k":"click","text":"Old step"}\n'])
    class _Gone:
        def poll(self): return None
        def terminate(self): self.stopped = True
        def kill(self): self.stopped = True
        def wait(self, timeout=None): return 0
    with baw._lock:
        baw._recordings[ka2]['proc'] = _Gone()
    import bank_window as _bw
    real_status = _bw._read_status
    import subprocess as _sp
    class _P:
        def __init__(self, *a, **k):
            import io
            self.stdin, self.stdout = io.StringIO(), io.StringIO('')
        def poll(self): return None
        def terminate(self): pass
        def kill(self): pass
        def wait(self, timeout=None): return 0
    orig = _sp.Popen
    _sp.Popen, _bw._read_status = _P, (lambda proc, w: _bw.STATUS_READY)
    try:
        res = baw.start_recording(ka2, 'https://bank.example.com/')
    finally:
        _sp.Popen, _bw._read_status = orig, real_status
    check('s173 A5 recording again starts over: the old window is closed and its steps are gone',
          res == 'opened' and baw.steps(ka2) == [])
    baw.finish_recording(ka2)
    check('s173 A5 the bar\'s step count is kept per recording, and saving says it replaces the steps saved before',
          "'__gwNoted:' + (window.__gwRecId" in baw.RECORD_SCRIPT and 'Saving them replaces any steps saved before' in ctx.app_src)
    # Amendment A13 (Rob, 2026-10-10: "build A13"): the bank's pop-ups
    pop = baw.clean_step({'k': 'click', 'role': 'button', 'text': 'Close', 'opt': False, 'pop': True})
    check('s173 A13.1 a step inside the bank\'s pop-up is saved as "only if your bank shows it"',
          pop == {'k': 'click', 'role': 'button', 'text': 'Close', 'opt': True, 'pop': True}
          and baw.step_words(pop) == 'Click \u201cClose\u201d (only if your bank shows it)'
          and baw.parse_step_line('step {"k":"click","text":"Close","pop":true}') == {'k': 'click', 'text': 'Close', 'opt': True, 'pop': True}
          and 'function inPopup(el)' in baw.RECORD_SCRIPT and "[aria-modal=true]" in baw.RECORD_SCRIPT)
    check('s173 A13.2 a click that agrees to something is never saved as a step',
          all(baw.clean_step({'k': 'click', 'text': t}) is None for t in ('Accept', 'I agree', 'Agree', 'I Accept the terms', 'Accept and continue'))
          and baw.clean_step({'k': 'click', 'text': 'Accepted payments'}) is not None
          and baw.clean_step({'k': 'click', 'text': 'Continue'}) is not None)
    check('s173 A13.3 a choice that changes a setting at the bank ("don\'t show this again") is never saved',
          all(baw.clean_step({'k': 'choose', 'option': o, 'pop': True}) is None
              for o in ("Don't show this message again", 'Do not show again', 'Remember my choice', 'Don\u2019t ask me again'))
          and baw.clean_step({'k': 'choose', 'field': 'Range', 'option': 'Last 30 days'}) is not None)
    with db_session() as s:
        a = Account(name='s173 Pop', type='checking', is_active=True, portal_url='https://bank.example.com')
        s.add(a); s.commit(); kp = f'account:{a.id}'
    try:
        sv = c.post('/api/settings/bank-agent/recipe', headers=HJ, data=json.dumps({'key': kp, 'steps': [
            {'k': 'click', 'text': 'Close', 'pop': True}, {'k': 'choose', 'option': "Don't show this message again", 'pop': True},
            {'k': 'click', 'text': 'I agree'}, {'k': 'click', 'text': 'Download'}]})).get_json()['data']
        check('s173 A13 Groundwork cleans the steps again when saving: the pop-up step kept as optional, the agreement and the setting dropped',
              sv['steps'] == [{'k': 'click', 'text': 'Close', 'opt': True, 'pop': True}, {'k': 'click', 'text': 'Download'}])
    finally:
        with db_session() as s:
            s.query(AppSetting).filter(AppSetting.key == f'bank_recipe:{kp}').delete(synchronize_session=False)
            s.query(Account).filter(Account.id == a.id).delete(synchronize_session=False)
            s.commit()

