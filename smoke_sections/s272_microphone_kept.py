"""Rob 2026-10-31: "when Groundwork ask the operating system to use the microphone and the user selects yes that answer
should be recorded and kept. The red light and the timing will keep the microphone from always listening."

    M1  the yes is recorded once the microphone has actually opened, with its date; a second yes keeps the first date
    M2  the window answers a microphone request from that record - only the microphone, only Groundwork's own page;
        with nothing on record the window asks its own question, as before (a no is not kept)
    M3  Settings shows when it was allowed, and "Ask me next time" forgets it
Measured on Windows 2026-10-31 in a real WebView2 window: with the yes on record the microphone opened with no question;
with none, the window asked.
"""
import json


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    first = c.get('/api/voice/microphone', headers=H).get_json()['data']
    a = c.post('/api/voice/microphone', headers=HJ, data=json.dumps({})).get_json()['data']
    from core.database import db_session
    import server
    with db_session() as s:                            # an earlier yes on record: a later one does not move it
        server._set_setting(s, server.MICROPHONE_SETTING, '2026-01-02T03:04:05')
        s.commit()
    b = c.post('/api/voice/microphone', headers=HJ, data=json.dumps({})).get_json()['data']
    check('s272 M1 nothing on record at first; the yes is recorded with its date; a second yes keeps the first date',
          first['allowed_at'] is None and a['allowed_at'] and b['allowed_at'] == '2026-01-02T03:04:05'
          and server.microphone_allowed() == '2026-01-02T03:04:05')

    import launch
    page = launch.MAIN_PAGE
    cases = [
        (launch.microphone_answer(True, page, '2026-01-02T03:04:05'), True),
        (launch.microphone_answer(True, page + 'index.html', '2026-01-02T03:04:05'), True),
        (launch.microphone_answer(True, page, None), False),                       # nothing on record: the window asks
        (launch.microphone_answer(False, page, '2026-01-02T03:04:05'), False),     # the camera, location...: asked
        (launch.microphone_answer(True, 'https://www.yourbank.com/', '2026-01-02T03:04:05'), False),
        (launch.microphone_answer(True, 'http://127.0.0.1:8765.evil.example/', '2026-01-02T03:04:05'), False),
        (launch.microphone_answer(True, 'http://localhost:8765/', '2026-01-02T03:04:05'), False),
    ]
    check(f's272 M2 the window answers only the microphone, only for Groundwork\'s page, only with a yes on record '
          f'({[i for i, (got, want) in enumerate(cases) if got != want]})', all(got == want for got, want in cases))
    src = (ctx.BASE / 'launch.py').read_text(encoding='utf-8')
    main = src[src.index('def main():'):]
    check('s272 M2 the main window is hooked before it starts; the hook allows only from the record',
          main.index('_keep_microphone_answer(window)') < main.index('webview.start(')
          and 'args.State = CoreWebView2PermissionState.Allow' in src
          and 'microphone_answer(args.PermissionKind == CoreWebView2PermissionKind.Microphone, args.Uri,' in src
          and 'CoreWebView2PermissionState.Deny' not in src)

    acc = (ctx.BASE / 'static' / 'js' / 'teaching' / 'access.js').read_text(encoding='utf-8')
    mic_on = acc[acc.index('async function micOn()'):acc.index('c.ctx = new window.AudioContext();')]
    check('s272 M1 the page records the yes only after the microphone opened',
          mic_on.index("API.post('/api/voice/microphone'") > mic_on.index('getUserMedia(')
          and mic_on.index("API.post('/api/voice/microphone'") > mic_on.index('return;\n'))
    check('s272 M3 Settings says when the microphone was allowed, and "Ask me next time" forgets it',
          'You allowed the microphone on ' in acc and "API.delete('/api/voice/microphone')" in acc)
    gone = c.delete('/api/voice/microphone', headers=H).get_json()['data']
    check('s272 M3 forgotten: nothing on record, so the window asks again',
          gone['allowed_at'] is None and server.microphone_allowed() is None)
