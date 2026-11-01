"""V8 (item 116, VOICE_ASSISTANT.md): voice measured like a product - the first cut.

    python scripts/voice_measure.py [--quick]

Real commands, said by several voices (Kokoro's American and British voices, and the computer's own voices on Windows),
clean and with noise at about 15 dB, are recognised by Groundwork's own whisper.cpp - with the household's words in the
hint (V1) and without - and routed by the Ask bar's own code from app.js, run in Node. It counts the commands that did
what was meant, and times Groundwork's first spoken reply. Prints a table; nothing is kept but the printout.

Synthetic voices are the first cut, not the verdict: the exit criterion (section 3, V8) needs real people on real
microphones. The household is the sample household (core/sample_household.py), in a temporary data folder.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')

# (what is said, what it must do) - "place:<label>", "do:<toast>", "ledger:<term>", "coming", "barge:<word>"
COMMANDS = [
    ('Groundwork, open my budget', 'place:the Budget'),
    ('Open the budget', 'place:the Budget'),
    ('Show me my Kroger transactions', 'ledger:kroger'),
    ('Show me my Lantern Cafe transactions', 'ledger:lantern cafe'),
    ('Show me Corner Market purchases', 'ledger:corner market'),
    ('Show me my transactions at Valley Foods', 'ledger:valley foods'),
    ("Let's build a report", 'do:Opened the report builder'),
    ('I want to see my debts', 'place:Debt Payoff'),
    ('Take me to net worth', 'place:Net Worth'),
    ('Open the calendar', 'place:the Calendar'),
    ("What's coming up this week?", 'coming'),
    ("What's due this month?", 'coming'),
    ('Import a statement', 'do:Opened Import'),
    ('Add a transaction', 'do:Opened Add transaction'),
    ('Back up my data', 'do:Opened Backup'),
    ('Open settings', 'place:Settings'),
    ('Show me my investments', 'place:Investments'),
    ('Go to the trip planner', 'place:the Trip Planner'),
    ('Open my medical bills', 'place:Medical bills'),
    ('Open the ledger', 'place:the Ledger'),
    ('Groundwork, I want my budget', 'place:the Budget'),
    ('Open the dashboard', 'place:the Dashboard'),
    ('View the trophy room', 'place:the Trophy Room'),
    ('Open gifts', 'place:Gifts'),
    ('Open before you buy', 'place:Before You Buy'),
    ('Stop', 'barge:stop'),
    ('Next', 'barge:next'),
    ('Repeat', 'barge:repeat'),
    ('Slower', 'barge:slower'),
    ("That's enough", 'barge:stop'),
]
KOKORO_VOICES = ['af_heart', 'am_michael', 'bf_emma', 'bm_george']
WINDOWS_VOICES = ['Microsoft David Desktop', 'Microsoft Zira Desktop']


def _wav16(samples, rate):
    """float samples at any rate -> 16 kHz mono 16-bit WAV bytes, as the page sends them"""
    import numpy as np
    a = np.asarray(samples, dtype=np.float32)
    n = int(len(a) * 16000 / rate)
    a = np.interp(np.linspace(0, len(a) - 1, n), np.arange(len(a)), a).astype(np.float32)
    pad = np.zeros(4000, dtype=np.float32)
    a = np.concatenate([pad, a, pad])
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        w.writeframes((np.clip(a, -1, 1) * 32767).astype('<i2').tobytes())
    return buf.getvalue()


def _noisy(samples, snr_db=15, seed=1):
    import numpy as np
    a = np.asarray(samples, dtype=np.float32)
    p = float(np.mean(a ** 2)) or 1e-6
    rng = np.random.default_rng(seed)
    return a + rng.normal(0, (p / 10 ** (snr_db / 10)) ** 0.5, len(a)).astype(np.float32)


def _kokoro_clips(voices, phrases):
    from core import speak
    k = speak._load()
    out = {}
    for v in voices:
        for text, _ in phrases:
            a, rate = k.create(text, voice=v, lang='en-gb' if v.startswith('b') else 'en-us')
            out[(v, text)] = (a, rate)
    return out


def _windows_clips(voices, phrases, d):
    if sys.platform != 'win32':
        return {}
    import numpy as np
    lines = ['Add-Type -AssemblyName System.Speech', '$s = New-Object System.Speech.Synthesis.SpeechSynthesizer']
    names = {}
    for vi, v in enumerate(voices):
        lines.append(f"$s.SelectVoice('{v}')")
        for pi, (text, _) in enumerate(phrases):
            f = os.path.join(d, f'w{vi}_{pi}.wav')
            names[(v, text)] = f
            lines.append(f"$s.SetOutputToWaveFile('{f}'); $s.Speak('{text.replace(chr(39), chr(39) * 2)}')")
    lines.append('$s.Dispose()')
    ps = os.path.join(d, 'say.ps1')
    open(ps, 'w', encoding='utf-8').write('\n'.join(lines))
    subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ps], capture_output=True, timeout=600)
    out = {}
    for key, f in names.items():
        if os.path.exists(f):
            with wave.open(f) as w:
                out[key] = (np.frombuffer(w.readframes(w.getnframes()), dtype='<i2').astype(np.float32) / 32768,
                            w.getframerate())
    return out


def _route_all(heard):
    """The Ask bar's own code, from app.js, decides what each heard phrase does."""
    app = (ROOT / 'static' / 'js' / 'app.js').read_text(encoding='utf-8')
    acc = (ROOT / 'static' / 'js' / 'teaching' / 'access.js').read_text(encoding='utf-8')
    js = (app[app.index('const _ASK_SHORT = '):app.index('function _askSay(')]
          + app[app.index('const ASK_PLACES = ['):app.index('function askGo(')]
          + app[app.index('const ASK_DO = ['):app.index('// Questions about the person')]
          + app[app.index('function _askShowTxns(n) {'):app.index('// Rob 2026-10-31: with Groundwork')]
          + app[app.index('const ASK_COMING = '):app.index('async function askComingUp(')]
          + acc[acc.index('  var BARGE = {'):acc.index('  function _hear(c, data) {')].replace('  var ', 'var ')
          + "function _norm(t) { return String(t).toLowerCase().replace(/[^a-z0-9\\u0027 ]+/g, ' ').replace(/\\s+/g, ' ').trim(); }\n"
          + 'const heard = ' + json.dumps(heard) + ';\n' + r"""
console.log(JSON.stringify(heard.map(h => {
  const b = BARGE[_norm(h).replace(/^(?:groundwork|ok|okay|hey|please)\s+/, '').replace(/\s+please$/, '')];
  const n = _askNorm(h);
  if (ASK_COMING.test(n)) return ['coming', b ? 'barge:' + b : null];
  const d = ASK_DO.find(x => x.re.test(n));
  if (d) return ['do:' + d.said, b ? 'barge:' + b : null];
  const s = _askShowTxns(n);
  if (s) return ['ledger:' + s, b ? 'barge:' + b : null];
  const bare = n.replace(/^(?:my|the|our|all)\s+/, '');
  const p = askPlace(n) || ASK_PLACES.find(pl => pl.names.includes(bare));
  return [p ? 'place:' + p.label : null, b ? 'barge:' + b : null];
})));
""")
    d = tempfile.mkdtemp(prefix='gw_route_')
    f = os.path.join(d, 'route.js')
    open(f, 'w', encoding='utf-8').write(js)
    return json.loads(subprocess.run([shutil.which('node'), f], capture_output=True, text=True, encoding='utf-8',
                                     timeout=60).stdout)


def main():
    quick = '--quick' in sys.argv
    data = tempfile.mkdtemp(prefix='gw_measure_')
    os.environ['GROUNDWORK_DATA_DIR'] = data
    import logging; logging.disable(logging.WARNING)
    from server import create_app, _voice_words, _GW_TOKEN
    from core import voice, speak
    from core.database import db_session
    app = create_app()
    from core import sample_household as sh
    sh.build(app.test_client(), {'X-GW-Token': _GW_TOKEN})
    with db_session() as s:
        words = _voice_words(s)
    phrases = COMMANDS[:8] if quick else COMMANDS
    clips = {}
    clips.update(_kokoro_clips(KOKORO_VOICES[:1] if quick else KOKORO_VOICES, phrases))
    if not quick:
        clips.update(_windows_clips(WINDOWS_VOICES, phrases, tempfile.mkdtemp(prefix='gw_say_')))
    runs = []                                       # (voice, condition, hint, phrase, want, heard, seconds)
    for (v, text), (a, rate) in clips.items():
        want = dict(phrases)[text]
        for cond in (['clean'] if quick else ['clean', 'noise 15 dB']):
            wav = _wav16(a if cond == 'clean' else _noisy(a), rate)
            for hint in (['own words'] if quick else ['own words', 'fixed hint']):
                t = time.perf_counter()
                heard = voice.transcribe(wav, words=words if hint == 'own words' else None)
                runs.append((v, cond, hint, text, want, heard, time.perf_counter() - t))
    routed = _route_all([r[5] for r in runs])
    rows = {}
    misses = []
    for r, (got, barge) in zip(runs, routed):
        ok = (barge == r[4]) if r[4].startswith('barge:') else (got == r[4])
        key = (r[0], r[1], r[2])
        n, k, secs = rows.get(key, (0, 0, 0.0))
        rows[key] = (n + 1, k + ok, secs + r[6])
        if not ok:
            misses.append((r[0], r[1], r[2], r[3], r[5], got or barge))
    print('| voice | condition | hint | did what was meant | recognise (s, mean) |')
    print('|---|---|---|---|---|')
    tot_n = tot_k = 0
    for (v, cond, hint), (n, k, secs) in sorted(rows.items()):
        tot_n += n; tot_k += k
        print(f'| {v} | {cond} | {hint} | {k}/{n} ({100 * k / n:.0f}%) | {secs / n:.2f} |')
    print(f'\nall: {tot_k}/{tot_n} ({100 * tot_k / tot_n:.0f}%)')
    for hint in ('own words', 'fixed hint'):
        sel = [(n, k) for (v, c, h), (n, k, s) in rows.items() if h == hint]
        if sel:
            print(f'{hint}: {sum(k for n, k in sel)}/{sum(n for n, k in sel)}')
    speak._load()
    firsts = []
    for line in ('Sure, opening the Budget for you.', 'OK, showing your Kroger transactions in the Ledger.'):
        t = time.perf_counter(); speak.speak(line); firsts.append(time.perf_counter() - t)
    print(f'first spoken reply made in: {", ".join(f"{x:.2f} s" for x in firsts)}')
    print('\nmisses:')
    for m in misses:
        print('  ', m)


if __name__ == '__main__':
    main()
