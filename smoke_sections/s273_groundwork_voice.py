"""Groundwork's own voice (core/speak.py; Rob 2026-10-31: "lets add a human sounding voice to groundwork").

    V1  said on this computer: the module imports nothing that can reach a network, and the page asks this server only
    V2  figures said the way a person says them - "instead of saying dollar it should say 100. dollars", and "instead
        of saying apr it should say interest rate of"; a card's last four one digit at a time
    V3  the voice Rob chose (af_heart), from the measured files; read aloud asks Groundwork's voice first and falls
        back to the computer's own voices; the first sentence goes alone so it starts soon
    V4  loaded while read aloud or voice commands want it, let go when neither does
    V5  every build carries it: the specs, the installers, requirements.txt, the fetch script, the notices
Listened to 2026-10-31 (six voices, Rob chose the first); round-tripped through whisper base.en, every figure heard right.
"""
import ast
import json
import os
import shutil
import subprocess
import tempfile


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    from core import speak
    src = (ctx.BASE / 'core' / 'speak.py').read_text(encoding='utf-8')
    mods = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            mods |= {a.name.split('.')[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module.split('.')[0])
    net = mods & {'socket', 'http', 'urllib', 'requests', 'ssl', 'ftplib', 'smtplib', 'websocket', 'websockets',
                  'httpx', 'aiohttp'}
    check(f's273 V1 the voice imports nothing that can reach a network ({sorted(mods)})', not net)

    cases = [
        ('Debt payments: $450 a month.', 'Debt payments: 450 dollars a month.'),
        ('June 2026, $1,199.00.', 'June 2026, 1199 dollars.'),
        ('$612.38. That', '612 dollars and 38 cents. That'),
        ('$87.62 under', '87 dollars and 62 cents under'),
        ('$1 and $1.01 and $0.50', '1 dollar and 1 dollar and 1 cent and 50 cents'),
        ('Refund -$12.05', 'Refund minus 12 dollars and 5 cents'),
        ('$450/mo', '450 dollars a month'),
        ('Your Visa ends 4417.', 'Your Visa ends 4 4 1 7.'),
        ('Card •••• 4417, x9921', 'Card ending 4 4 1 7, ending 9 9 2 1'),
        ('Fax 1234', 'Fax 1234'),
        ('APR 24.99%.', 'interest rate of 24.99 percent.'),
        ('at an APR of 19.5%', 'at an interest rate of 19.5 percent'),
        ('Change the APR here.', 'Change the interest rate here.'),
        ('HSA vs FSA', 'H S A versus F S A'),
        ('Due 2026-11-03', 'Due November 3, 2026'),
        ('1,234,567 lines', '1234567 lines'),
    ]
    wrong = [(a, speak.spoken(a)) for a, want in cases if speak.spoken(a) != want]
    check(f's273 V2 figures are said the way a person says them: "100 dollars", "interest rate of" ({wrong})', not wrong)

    import spec_engine
    check('s273 V3 the voice Rob chose, from the files listened to and measured (pinned, and the build checks them)',
          speak.VOICE == 'af_heart' and spec_engine.SPEAK_FILES == {speak.MODEL_FILE: speak.MODEL_SHA256,
                                                                    speak.VOICES_FILE: speak.VOICES_SHA256})

    st = c.get('/api/voice', headers=H).get_json()['data']
    empty = c.post('/api/voice/speak', headers=HJ, data=json.dumps({'text': '  '}))
    long = c.post('/api/voice/speak', headers=HJ, data=json.dumps({'text': 'word ' * 200}))
    if st['speak']['available']:
        r = c.post('/api/voice/speak', headers=HJ, data=json.dumps({'text': 'Debt payments: $450 a month.'}))
        check('s273 V3 this server says Groundwork\'s words aloud as a WAV, and keeps nothing; nothing to say, or a whole '
              'page at once, is refused', r.status_code == 200 and r.data[:4] == b'RIFF' and r.mimetype == 'audio/wav'
              and r.headers.get('Cache-Control') == 'no-store' and empty.status_code == 400 and long.status_code == 400)
    else:
        r = c.post('/api/voice/speak', headers=HJ, data=json.dumps({'text': 'Debt payments: $450 a month.'}))
        check(f"s273 V3 without the voice files the server says why, and the page reads with the computer's voice "
              f"({st['speak']['reason']})", r.status_code == 503 and st['speak']['reason'])

    calls = []
    real = speak.preload, speak.release
    speak.preload, speak.release = (lambda: calls.append('load')), (lambda: calls.append('let go'))
    try:
        for body in ({'read_aloud': 'key'}, {'read_aloud': 'off'}, {'voice_commands': 'on'}, {'voice_commands': 'off'}):
            c.patch('/api/settings', headers=HJ, data=json.dumps(body))
    finally:
        speak.preload, speak.release = real
    check(f's273 V4 the voice is loaded while read aloud or voice commands want it, and let go when neither does ({calls})',
          calls == ['load', 'let go', 'load', 'let go'])

    acc = (ctx.BASE / 'static' / 'js' / 'teaching' / 'access.js').read_text(encoding='utf-8')
    say = acc[acc.index('  function say(words, then) {'):acc.index('function _clean(')]
    check("s273 V1/V3 read aloud asks this computer's Groundwork server for the voice, and falls back to the computer's "
          "own voices; it doesn't listen while either is speaking",
          "_gwFetch('/api/voice/speak'" in acc and 'own.available !== false ? _sayOwn(words, then) : _saySystem(words, then)' in say
          and 'function _speaking() { return own.playing ||' in acc and 'new window.Audio(url)' in acc)

    node = shutil.which('node')
    if node:
        fn = acc[acc.index('  function _chunks(words) {'):acc.index('  async function _made(text) {')]
        text = ('Your Visa ends 4417, at an APR of 24.99%. Paying $300 instead of the $95 minimum saves $2,140 in '
                'interest. June 2026, $1,199.00. Groundwork adds up every payment you have made toward this card since you '
                'started tracking it. It compares that with what you owed on the first statement. The difference is what '
                'went to interest and fees. Would you like this explained further?')
        f = os.path.join(tempfile.mkdtemp(prefix='s273_'), 'chunks.js')
        open(f, 'w', encoding='utf-8').write(fn + '\nconsole.log(JSON.stringify(_chunks(' + json.dumps(text) + ')));')
        parts = json.loads(subprocess.run([node, f], capture_output=True, text=True, encoding='utf-8', timeout=30).stdout or '[]')
        grows = all(len(b) <= max(120, 2 * len(a)) for a, b in zip(parts, parts[1:]))
        check(f's273 V3 the first sentence goes alone, each piece at most twice the last, no figure split, nothing lost '
              f'({[len(p) for p in parts]})',
              parts and parts[0] == 'Your Visa ends 4417, at an APR of 24.99%.' and grows
              and ' '.join(parts) == text and any('$1,199.00.' in p for p in parts))

    specs = {n: (ctx.BASE / n).read_text(encoding='utf-8') for n in ('groundwork.spec', 'groundwork_macos.spec',
                                                                    'groundwork_linux.spec')}
    isss = [(ctx.BASE / n).read_text(encoding='utf-8') for n in ('groundwork.iss', 'groundwork_offline.iss', 'groundwork_store.iss')]
    check('s273 V5 every build carries the voice: three specs, three installers, requirements, the fetch script, the notices',
          all('spec_engine.speak_parts()' in s and "'core.speak'" in s for s in specs.values())
          and all('spec_engine.speak_model_data()' in specs[n] for n in ('groundwork_macos.spec', 'groundwork_linux.spec'))
          and all('vendor\\kokoro\\kokoro-v1.0.int8.onnx' in s and 'vendor\\kokoro\\voices-v1.0.bin' in s for s in isss)
          and 'kokoro-onnx==' in (ctx.BASE / 'requirements.txt').read_text(encoding='utf-8')
          and (ctx.BASE / 'scripts' / 'fetch_kokoro_model.py').is_file()
          and 'Kokoro-82M' in (ctx.BASE / 'THIRD_PARTY_NOTICES.md').read_text(encoding='utf-8'))
