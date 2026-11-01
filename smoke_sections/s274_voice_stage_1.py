"""Item 116 stage 1 (gw 2.0/VOICE_ASSISTANT.md; Rob 2026-10-31: "this should be a serious feature", approved):

    V1   the person's own words in the recogniser - payees, accounts, people, budget lines, categories; health left out
    V2   interrupt it: while Groundwork speaks, "stop", "next", "repeat" are heard; anything else is let go (s266 runs it)
    V4   every answer to a spoken question said aloud; follow-ups ("what about Walmart?", "and last month?")
    V7   "what can I say?" said short; a sound when listening starts and stops; "One moment."; a tour, once
    V8   voice measured like a product: scripts/voice_measure.py, and a quick cut of it here when the models are present
    V15  "what's coming up this week?" - the Calendar's own dates, said with how sure each one is
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    import server
    from core import voice
    from core.database import db_session, Account, Category, Transaction
    from datetime import date

    with db_session() as s:
        acct = Account(name='Ally Savings', type='savings')
        hsa = Account(name='Health Savings', type='hsa')
        groc = s.query(Category).filter(Category.name == 'Groceries').first() or Category(name='Groceries')
        med = s.query(Category).filter(Category.name == 'Medical').first() or Category(name='Medical')
        s.add_all([acct, hsa, groc, med]); s.flush()
        for i in range(3):
            s.add(Transaction(date=date(2026, 10, 1 + i), description='MEIJER #12', merchant='Meijer', amount=40,
                              account_id=acct.id, category_id=groc.id))
        s.add(Transaction(date=date(2026, 10, 5), description='DR PATEL', merchant='Dr Patel Clinic', amount=90,
                          account_id=acct.id, category_id=med.id))
        s.add(Transaction(date=date(2026, 10, 6), description='CVS', merchant='Walgreens Pharmacy', amount=12,
                          account_id=hsa.id, category_id=groc.id))
        s.commit()
        words = server._voice_words(s)
    check(f"s274 V1 the person's own words for the recogniser - payees first, accounts, categories - and no health "
          f"name, nor anything in an HSA ({words[:6]})",
          'Meijer' in words and 'Ally Savings' in words and 'Groceries' in words
          and 'Dr Patel Clinic' not in words and 'Walgreens Pharmacy' not in words and 'Health Savings' not in words)
    hint = voice.hint_for(words)
    check('s274 V1 the hint is Groundwork\'s words, then the person\'s, and stays inside what whisper reads as a prompt',
          hint.startswith(voice.HINT) and 'Your words: ' in hint and 'Meijer' in hint and len(hint) <= voice.HINT_CHARS + 1
          and voice.hint_for([]) == voice.HINT and len(voice.hint_for(['x' * 30] * 100)) <= voice.HINT_CHARS + 1)

    class _Seg:
        text = 'show me my meijer transactions'

    class _Fake:
        def transcribe(self, samples, **params):
            self.params = params
            return [_Seg()]
    import io, wave
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(b'\x10\x00' * 16000)
    fake, real = _Fake(), (voice.status, voice._model, voice.preload)
    voice.status, voice._model, voice.preload = (lambda: {'available': True, 'reason': ''}), fake, (lambda: None)
    c.patch('/api/settings', headers=HJ, data=json.dumps({'voice_commands': 'on'}))
    try:
        r = c.post('/api/voice/transcribe', headers={**H, 'Content-Type': 'audio/wav'}, data=buf.getvalue())
        full_prompt = (getattr(fake, 'params', {}) or {}).get('initial_prompt') or ''
        c.post('/api/voice/transcribe?short=1', headers={**H, 'Content-Type': 'audio/wav'}, data=buf.getvalue())
        short_prompt = (getattr(fake, 'params', {}) or {}).get('initial_prompt') or ''
    finally:
        voice.status, voice._model, voice.preload = real
        c.patch('/api/settings', headers=HJ, data=json.dumps({'voice_commands': 'off'}))
    check('s274 V1 each clip is recognised with the household\'s own words as whisper\'s prompt',
          r.status_code == 200 and 'Meijer' in full_prompt)
    acc0 = (ctx.BASE / 'static' / 'js' / 'teaching' / 'access.js').read_text(encoding='utf-8')
    check('s274 V2 a clip heard over Groundwork\'s voice is recognised against the short words only (measured: 82/84 '
          'against 76/84 with the full hint)', short_prompt == voice.SHORT_HINT
          and "'/api/voice/transcribe' + (over ? '?short=1' : '')" in acc0)

    app = ctx.app_src if 'function _askFollow(' in ctx.app_src else (ctx.BASE / 'static/js/app.js').read_text(encoding='utf-8')
    acc = (ctx.BASE / 'static' / 'js' / 'teaching' / 'access.js').read_text(encoding='utf-8')
    ask = app[app.index('async function askGroundwork('):app.index('async function _askGroundwork(')]
    check('s274 V4/V7 a spoken question gets its answer said aloud, whatever answered it, and "One moment." when it takes '
          'more than a moment; typed, nothing is read',
          "if (spoken && window._gwVoiceAsked) { window._gwVoiceAsked = false; _askSpeakPanel(); }" in ask
          and "window.GWVoice.say('One moment.')" in ask and 'const spoken = !!window._gwVoiceAsked;' in ask)
    check('s274 V7 "what can I say?" is answered short and aloud; the tour is given once; a sound marks the microphone '
          'on and off; the button names what to try',
          "_askSaid('You can say: open my budget." in app and "if (prefs.voice_tour === 'done') return;" in acc
          and "_save('voice_tour', 'done')" in acc and '_chime(true);' in acc and '_chime(false);' in acc
          and 'Try "open my budget"' in acc)

    node = shutil.which('node')
    if node:
        js = (app[app.index('const _ASK_SHORT = '):app.index('function _askSay(')]
              + app[app.index('const ASK_PLACES = ['):app.index('function askGo(')]
              + app[app.index('let _askLast = null;'):app.index('async function askComingUp(')]
              + acc[acc.index('  var BARGE = {'):acc.index('  function _hear(c, data) {')].replace('  var ', 'var ')
              + "function _norm(t) { return String(t).toLowerCase().replace(/[^a-z0-9\\u0027 ]+/g, ' ').replace(/\\s+/g, ' ').trim(); }\n"
              + r"""
const did = [];
globalThis.askGo = pl => did.push('place:' + pl.label);
globalThis.askLedgerSearch = t => did.push('ledger:' + t);
globalThis.showView = () => {}; globalThis.ledgerMonthStep = d => did.push('month:' + d); globalThis._askSaid = () => {};
const follow = q => { did.length = 0; return [_askFollow(_askNorm(q)), did.slice()]; };
const out = {};
out.none = follow('what about walmart');
_askLast = { kind: 'ledger', term: 'kroger' };
out.walmart = follow('what about Walmart?');
out.month = follow('and last month?');
out.page = follow('what about my debts');
out.question = follow('what is my balance');
const coming = ['what\x27s coming up this week', 'what is coming up', 'whats due this month', 'what bills are due this week',
                'what\x27s coming up next month', 'what is coming up for me', 'what\x27s do this month'].map(q => [q, ASK_COMING.test(_askNorm(q))]);
out.coming = coming; out.notComing = ['what is my net worth', 'how much do i owe'].map(q => ASK_COMING.test(_askNorm(q)));
out.barge = ['Stop.', 'Groundwork, stop', "That's enough.", 'Okay, next please', 'Repeat', 'What is my balance?']
  .map(h => BARGE[_norm(h).replace(/^(?:groundwork|ok|okay|hey|please)\s+/, '').replace(/\s+please$/, '')] || null);
console.log(JSON.stringify(out));
""")
        f = os.path.join(tempfile.mkdtemp(prefix='s274_'), 'follow.js')
        open(f, 'w', encoding='utf-8').write(js)
        o = json.loads(subprocess.run([node, f], capture_output=True, text=True, encoding='utf-8', timeout=30).stdout or '{}')
        check(f"s274 V4 follow-ups carry the last subject: \"what about Walmart?\" searches Walmart, \"and last month?\" "
              f"steps the Ledger back, a page name opens it; with nothing before, or a question, nothing is assumed ({o})",
              o.get('none') == [False, []] and o.get('walmart') == [True, ['ledger:walmart']]
              and o.get('month') == [True, ['month:1']] and o.get('page') == [True, ['place:Debt Payoff']]
              and o.get('question') == [False, []])
        check(f"s274 V15 \"what's coming up\" this week or this month is heard as that, and other questions are not "
              f"({o.get('coming')}, {o.get('notComing')})",
              o.get('coming') and all(x[1] for x in o['coming']) and o.get('notComing') == [False, False])
        check(f"s274 V2 over Groundwork's voice, only the short words count ({o.get('barge')})",
              o.get('barge') == ['stop', 'stop', 'stop', 'next', 'repeat', None])

    script = ctx.BASE / 'scripts' / 'voice_measure.py'
    check('s274 V8 the measured set is in the repository: real commands, several voices, clean and with noise, with '
          'and without the person\'s words, routed by the Ask bar\'s own code', script.is_file()
          and 'KOKORO_VOICES' in script.read_text(encoding='utf-8') and '_route_all' in script.read_text(encoding='utf-8'))
    from core import speak
    if voice.status()['available'] and speak.status()['available'] and node and os.environ.get('GW_SKIP_VOICE_MEASURE') != '1':
        r = subprocess.run([sys.executable, str(script), '--quick'], capture_output=True, text=True, encoding='utf-8',
                           timeout=900, cwd=str(ctx.BASE))
        line = next((ln for ln in r.stdout.splitlines() if ln.startswith('all: ')), '')
        got = line.split()[1] if line else '0/1'
        k, n = (int(x) for x in got.split('/'))
        check(f's274 V8 the quick cut: commands said by Groundwork\'s voice, recognised and routed here, do what was '
              f'meant ({line or r.stderr[-300:]})', n >= 8 and k >= n - 1)
