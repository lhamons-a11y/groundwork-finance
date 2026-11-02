"""Groundwork's own voice, made on this computer (Rob 2026-10-31: "lets add a human sounding voice to groundwork").

Read aloud used the voices installed on the computer - on Windows, David, Zira and Mark - because the human-sounding
"Natural" voices are online and voice never leaves the computer (PANEL_REVIEW.md, 2026-10-24). This is the same rule
kept another way: Kokoro (82M, Apache-2.0), run here through onnxruntime, in the voice Rob chose from six samples
(af_heart). The page posts Groundwork's own words to this server on 127.0.0.1 and gets the sound back; nothing is
kept. This module imports nothing that can reach a network, and s273 holds it to that.

Figures are said the way a person says them (Rob: "instead of saying dollar it should say 100. dollars"): spoken()
turns "$87.62" into "87 dollars and 62 cents" before the voice sees it - the engine on its own read a dollar sign
first, and "APR" as a word.

Without kokoro-onnx or the model files, the voice is unavailable and says why; read aloud falls back to the
computer's own voices, as before.
"""
import io
import logging
import os
import re
import threading
import wave
from pathlib import Path

MODEL_FILE = 'kokoro-v1.0.int8.onnx'
VOICES_FILE = 'voices-v1.0.bin'
# The exact files listened to and measured on 2026-10-31 (scripts/fetch_kokoro_model.py checks them before packaging)
MODEL_SHA256 = '6e742170d309016e5891a994e1ce1559c702a2ccd0075e67ef7157974f6406cb'
VOICES_SHA256 = 'bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d'
VOICE = 'af_heart'                       # Rob 2026-10-31: "the first voice that appears to be modern and really good"
# V9 (item 116): the voices a person may choose, all in the shipped voices file - the default first. key -> (name, accent)
VOICES = {'af_heart': ('Heart', 'American'), 'af_bella': ('Bella', 'American'), 'af_sarah': ('Sarah', 'American'),
          'am_michael': ('Michael', 'American'), 'am_adam': ('Adam', 'American'), 'bf_emma': ('Emma', 'British'),
          'bm_george': ('George', 'British')}
SPEEDS = {'slower': 0.85, 'normal': 1.0, 'faster': 1.2}
MAX_CHARS = 600                          # the page sends a sentence or two at a time; a whole page is refused, not cut

_lock = threading.Lock()
_kokoro = None
# phonemizer notes a mismatch in its own word count on some lines; it changes nothing said, and names no words
logging.getLogger('phonemizer').setLevel(logging.ERROR)


class SpeakError(Exception):
    pass


# ── Words the voice says wrong, said right for everyone ──────────────────────────────────────────────────────────────
# Rob 2026-11-01: "it does miscreance copy .. it should sound like "cop-pee"". The phonemes were already kˈɑːpi; the
# voice still blurred it. Spelled his way it gets a clear "cop" and a stressed "pee" (kˈɑːppˈiː). A person's own
# names (V16) are applied first, so they can still change any of these.
# Rob 2026-11-01: "it pronounce meijer and major ... it shoud pronouce that word as My-Your". The voice's dictionary gives
# Meijer exactly major's sounds (mˈeɪdʒɚ). "Myer" is mˈaɪɚ - MY-er, stressed on "my", as the store is said; spelled
# "My-Your" it came out maɪjʊɹ, "my-yoor", with no stress.
SAID_RIGHT = {'copy': 'cop-pee', 'copies': 'cop-pees', 'copied': 'cop-peed', 'copying': 'cop-peeing',
              'meijer': 'Myer'}

# Rob 2026-11-01: the United States' supermarket chains (core/data/grocery_chains.json, from Wikipedia's list; built by
# scripts/build_grocery_chains.py). The ones the voice says wrong carry a respelling ("say"), each checked on the voice's
# own phonemes - Fred Meyer was "Fred MAY-er", IGA "igga", Lidl "LID-ul", Gelson's a soft g.
_CHAINS_SAY = None


def _chains_say():
    global _CHAINS_SAY
    if _CHAINS_SAY is None:
        try:
            import json
            d = json.loads((Path(__file__).parent / 'data' / 'grocery_chains.json').read_text(encoding='utf-8'))
            pairs = [(c['name'], c['say']) for c in d.get('chains', []) if c.get('say')]
        except Exception:
            pairs = []
        # a bank line says "GELSON'S #12", not "Gelson's Markets": the store's own words alone, when the respelling
        # leaves the generic tail as it was
        tail = re.compile(r'\s+(?:Markets?|Supermarkets?|Foods?|Food Center|Plaza|Gourmet|Supermarket and Cafe)$')
        for n, how in list(pairs):
            m, h = tail.search(n), tail.search(how)
            if m and h and m.group(0) == h.group(0) and len(n[:m.start()]) >= 4:
                pairs.append((n[:m.start()], how[:h.start()]))
        _CHAINS_SAY = [(re.compile(r'(?<![\w-])' + re.escape(n) + r'(?![\w-])', re.I), how)
                       for n, how in sorted(pairs, key=lambda p: -len(p[0]))]
    return _CHAINS_SAY

# ── Figures, said the way a person says them ─────────────────────────────────────────────────────────────────────────
_ABBREV = {'APY': 'A P Y', 'HSA': 'H S A', 'FSA': 'F S A', 'EOB': 'E O B', 'IRA': 'I R A',
           'CD': 'C D', 'ATM': 'A T M', 'PDF': 'P D F', 'CSV': 'C S V', 'YTD': 'year to date', 'vs': 'versus',
           'vs.': 'versus', 'approx.': 'about', 'mo': 'month', 'yr': 'year'}
_MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
           'November', 'December']
# A sentence's own full stop may follow the figure ("$1,199.00."); a further digit may not
_MONEY = re.compile(r'(?P<neg>[-−]\s?)?\$\s?(?P<d>\d{1,3}(?:,\d{3})+|\d+)(?:\.(?P<c>\d{1,2}))?(?!\d)(?!\.\d)')


def _money(m):
    dollars = int(m.group('d').replace(',', ''))
    cents = int((m.group('c') or '0').ljust(2, '0'))
    parts = []
    if dollars or not cents:
        parts.append(f'{dollars} dollar' + ('' if dollars == 1 else 's'))
    if cents:
        parts.append(f'{cents} cent' + ('' if cents == 1 else 's'))
    return ('minus ' if m.group('neg') else '') + ' and '.join(parts)


def _iso_date(m):
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return f'{_MONTHS[mo - 1]} {d}, {y}' if 1 <= mo <= 12 and 1 <= d <= 31 else m.group(0)


def spoken(text, names=None):
    """Groundwork's words, as they are to be said: money as "N dollars and N cents", a card's last four one digit at a
    time, a percent as "percent", an abbreviation letter by letter, a date in words. Nothing is added or left out.
    `names`: V16 (item 116) - the person's own "say Meijer like my-er", {name: how}, applied first, whole words."""
    t = str(text or '')
    for name, how in sorted((names or {}).items(), key=lambda kv: -len(kv[0])):
        if name and how and len(name) <= 60 and len(how) <= 60:
            t = re.sub(r'(?<!\w)' + re.escape(name) + r'(?!\w)', how, t, flags=re.I)
    for word, how in SAID_RIGHT.items():                  # after the person's own, so theirs win
        t = re.sub(r'(?<![\w-])' + word + r'(?![\w-])', how, t, flags=re.I)
    for name_re, how in _chains_say():                    # the supermarket chains it says wrong, after theirs too
        t = name_re.sub(how, t)
    t = t.replace('→', ' to ').replace('–', ' to ').replace('—', ', ').replace('&', ' and ')
    t = re.sub(r'\b(\d{4})-(\d{2})-(\d{2})\b', _iso_date, t)
    t = re.sub(r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b',
               lambda m: _iso_date(re.match(r'(\d+)-(\d+)-(\d+)', f'{m.group(3)}-{m.group(1)}-{m.group(2)}')), t)
    # A card's last four, one digit at a time: "ends 4417", "ending in 4417", "•••• 4417", "x4417"
    t = re.sub(r'(\b(?:ends|ending)(?: in)?\s+|(?<![A-Za-z])[•*xX]{1,4}\s?)(\d{4})\b',
               lambda m: (m.group(1) if m.group(1).startswith('end') else 'ending ') + ' '.join(m.group(2)), t)
    t = _MONEY.sub(_money, t)
    # Rob 2026-10-31: "instead of saying apr it should say interest rate of" - "APR 24.99%" is "interest rate of 24.99
    # percent", "an APR of" is "an interest rate of", and APR alone is "interest rate"
    t = re.sub(r'\bAPR\b\s*:?\s*(?=\d)', 'interest rate of ', t)
    t = re.sub(r'\bAPR\b', 'interest rate', t)
    t = re.sub(r'(\d+(?:\.\d+)?)\s?%', r'\1 percent', t)
    t = re.sub(r'/(mo|month)\b', ' a month', t)
    t = re.sub(r'/(yr|year)\b', ' a year', t)
    t = re.sub(r'(?<=\d),(?=\d{3}\b)', '', t)                  # "4,796" said as one number, not "4, 796"
    t = re.sub(r"(?<![\w'])(APY|HSA|FSA|EOB|IRA|CD|ATM|PDF|CSV|YTD|vs\.?|approx\.)(?![\w'])",
               lambda m: _ABBREV[m.group(1)], t)
    return re.sub(r'\s+', ' ', t).strip()


# ── The engine ───────────────────────────────────────────────────────────────────────────────────────────────────────
def _model_dir():
    """GW_KOKORO_DIR (tests, dev), else the install's models folder, else a source checkout's vendor/kokoro/."""
    env = os.environ.get('GW_KOKORO_DIR')
    if env:
        return Path(env)
    from core.engine import _base_dirs
    for base in _base_dirs():
        if (base / 'models' / MODEL_FILE).exists():
            return base / 'models'
    for base in _base_dirs():
        if (base / 'vendor' / 'kokoro' / MODEL_FILE).exists():
            return base / 'vendor' / 'kokoro'
    return _base_dirs()[0] / 'models'


def status():
    """{'available': bool, 'reason': str} - checked without loading the model."""
    try:
        import kokoro_onnx  # noqa: F401
    except Exception:
        return {'available': False, 'reason': "This copy of Groundwork was built without its own voice."}
    d = _model_dir()
    if not (d / MODEL_FILE).exists() or not (d / VOICES_FILE).exists():
        return {'available': False, 'reason': "Groundwork's voice files are not installed with this copy."}
    return {'available': True, 'reason': ''}


def is_loaded():
    return _kokoro is not None


def _roomy():
    """True on a computer with 12 GB or more, where the voice keeps its faster memory pool."""
    try:
        import psutil
        return psutil.virtual_memory().total >= 12 * 2**30
    except Exception:
        return False


def _load():
    global _kokoro
    if _kokoro is None:
        import onnxruntime as rt
        from kokoro_onnx import Kokoro
        d = _model_dir()
        opts = rt.SessionOptions()
        # The AI model has the processor too: the voice keeps to a few threads, and a stretch of speech is fast enough
        opts.intra_op_num_threads = max(1, min(4, (os.cpu_count() or 2) - 1))
        opts.inter_op_num_threads = 1
        # ONNX Runtime's memory pool, measured 2026-10-31: on, +505 MB and 3 sentences in 8 s; off, +130 MB and 13.6 s -
        # still faster than it is said. Below 12 GB (the 8 GB floor, with the AI model's 2.9 GB) the 375 MB matters more.
        opts.enable_cpu_mem_arena = _roomy()
        session = rt.InferenceSession(str(d / MODEL_FILE), sess_options=opts, providers=['CPUExecutionProvider'])
        _kokoro = Kokoro.from_session(session, str(d / VOICES_FILE))
    return _kokoro


def preload():
    """Read aloud or voice commands switched on: the voice is loaded in the background, ready for the first words."""
    if _kokoro is not None or not status()['available']:
        return

    def _go():
        try:
            with _lock:
                _load()
        except Exception:
            logging.getLogger(__name__).warning('speak: the voice could not be loaded', exc_info=True)
    threading.Thread(target=_go, name='speak-preload', daemon=True).start()


def release():
    """Read aloud and voice commands both off: the voice is let go."""
    global _kokoro
    with _lock:
        _kokoro = None


def speak(text, speed='normal', engine=None, voice=None, names=None):
    """The words as a 16-bit mono WAV. `engine` is for tests; otherwise the voice is loaded once. `voice`: one of VOICES
    (V9), else the default."""
    words = spoken(text, names)
    if not words:
        raise SpeakError('There is nothing to say.')
    if len(words) > MAX_CHARS:
        raise SpeakError('That is more than the voice says at once.')
    v = voice if voice in VOICES else VOICE
    import numpy as np
    with _lock:
        k = engine or _load()
        audio, rate = k.create(words, voice=v, speed=SPEEDS.get(speed, 1.0),
                               lang='en-gb' if VOICES[v][1] == 'British' else 'en-us')
    pcm = (np.clip(np.asarray(audio, dtype=np.float32), -1, 1) * 32767).astype('<i2')
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(int(rate))
        w.writeframes(pcm.tobytes())
    return buf.getvalue()
