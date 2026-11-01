"""Voice commands, recognised on this computer (gw 2.0/PANEL_REVIEW.md, item 113; Rob 2026-10-24).

Rob: "Sending the data to someone though is kinda of a deal breaker for me." So the page records a short clip only while
the person holds push-to-talk, posts it to this server on 127.0.0.1, and whisper.cpp (the base.en model, through
pywhispercpp) turns it into words here. Nothing is kept: the clip and the words live for the one request. This module
imports nothing that can reach a network, and s262 holds it to that.

One engine, off by default (the voice_commands setting). Without pywhispercpp or the model file, voice is unavailable
and says why; the rest of Groundwork is untouched.
"""
import io
import logging
import os
import threading
import wave
from pathlib import Path

MODEL_FILE = 'ggml-base.en.bin'
# The exact file measured on 2026-10-24 (scripts/fetch_whisper_model.py checks it before it is packaged).
MODEL_SHA256 = 'a03779c86df3323075f5e796cb2ce5029f00ec8869eee3fdfb897afe36c6d002'

# Groundwork's own words, so a short command lands on them rather than on a sound-alike ("dead" for "debt").
HINT = ('Groundwork budget words: debt, debts, debt payoff, budget, ledger, dashboard, settings, groceries, '
        'restaurants, Kroger, interest, snowball, explain further, read this, read the page, repeat, slower, faster, '
        'go back, next.')

RATE = 16000            # whisper.cpp reads 16 kHz mono
MAX_SECONDS = 15        # push-to-talk is for a short command; a longer clip is refused, not trimmed
MAX_BYTES = 44 + RATE * 2 * MAX_SECONDS

_lock = threading.Lock()
_model = None
# The library notes each clip it hears in Groundwork's log; only its warnings are let through, so no trace of a clip is kept
logging.getLogger('pywhispercpp').setLevel(logging.WARNING)


class VoiceError(Exception):
    pass


def model_path():
    """GW_WHISPER_PATH (tests, dev), else the install's models folder, the same places the AI model is looked for."""
    env = os.environ.get('GW_WHISPER_PATH')
    if env:
        return Path(env)
    from core.engine import _base_dirs
    for base in _base_dirs():
        p = base / 'models' / MODEL_FILE
        if p.exists():
            return p
    for base in _base_dirs():      # a source checkout: staged by scripts/fetch_whisper_model.py
        p = base / 'vendor' / 'whisper' / MODEL_FILE
        if p.exists():
            return p
    return _base_dirs()[0] / 'models' / MODEL_FILE


def status():
    """{'available': bool, 'reason': str} - checked without loading the model."""
    try:
        import pywhispercpp  # noqa: F401
    except Exception:
        return {'available': False, 'reason': 'This copy of Groundwork was built without the voice engine.'}
    if not model_path().exists():
        return {'available': False, 'reason': 'The voice model file is not installed with this copy of Groundwork.'}
    return {'available': True, 'reason': ''}


def _load():
    global _model
    if _model is None:
        from pywhispercpp.model import Model
        _model = Model(str(model_path()), print_progress=False, print_realtime=False, initial_prompt=HINT,
                       language='en', single_segment=True, no_context=True,
                       n_threads=max(1, min(4, (os.cpu_count() or 2) - 1)))
    return _model


def preload():
    """Voice switched on: the model is loaded in the background, so the first command isn't kept waiting."""
    if _model is not None or not status()['available']:
        return

    def _go():
        try:
            with _lock:
                _load()
        except Exception:
            logging.getLogger(__name__).warning('voice: the model could not be loaded', exc_info=True)
    threading.Thread(target=_go, name='voice-preload', daemon=True).start()


def release():
    """Voice switched off: the model is let go."""
    global _model
    with _lock:
        _model = None


def read_wav(data):
    """A 16 kHz mono 16-bit WAV clip as float samples in -1..1. Anything else is refused."""
    if not data or len(data) > MAX_BYTES:
        raise VoiceError('The clip is empty or longer than %d seconds.' % MAX_SECONDS)
    try:
        with wave.open(io.BytesIO(data), 'rb') as w:
            if w.getnchannels() != 1 or w.getsampwidth() != 2 or w.getframerate() != RATE:
                raise VoiceError('The clip is not 16 kHz mono.')
            frames = w.readframes(w.getnframes())
    except (wave.Error, EOFError) as e:
        raise VoiceError('The clip could not be read.') from e
    import numpy as np
    return np.frombuffer(frames, dtype='<i2').astype(np.float32) / 32768.0


HINT_CHARS = 800        # whisper reads at most half its 448-token context as a prompt; this stays well inside it


def hint_for(words=None):
    """V1 (item 116, VOICE_ASSISTANT.md): Groundwork's words, then the person's own - their payees, accounts, people,
    budget lines and categories - so "Meijer" or "Ally" is heard as itself and not as a sound-alike. Nothing is kept."""
    hint = HINT
    for w in words or []:
        more = (' Your words: ' if hint == HINT else ', ') + w
        if len(hint) + len(more) > HINT_CHARS:
            break
        hint += more
    return hint if hint == HINT else hint + '.'


# V2 (item 116): a clip heard while Groundwork speaks can only be one of a few short words, so whisper is told only those
# (measured 2026-10-31: with the full hint, a British voice's "Stop" came back "Stomp!" and "Slower" as "Slow earn")
SHORT_HINT = 'Stop. Next. Repeat. Slower. Faster. Stop it. That is enough. Say that again. Slow down. Speed up.'


def transcribe(data, model=None, words=None, short=False):
    """The words in a clip, recognised here. `model` is for tests; otherwise the base.en model is loaded once.
    `words`: the person's own names for the hint (hint_for); the hint is set on every clip, so none carries over.
    `short`: heard while Groundwork spoke - the hint is the short words only (SHORT_HINT)."""
    samples = read_wav(data)
    if len(samples) < RATE // 4:
        return ''
    with _lock:
        m = model or _load()
        prompt = SHORT_HINT if short else hint_for(words)
        segments = m.transcribe(samples, initial_prompt=prompt) if model is None else m.transcribe(samples)
    text = ' '.join((getattr(s, 'text', s) or '').strip() for s in segments).strip()
    # whisper marks silence and noise in brackets ("[BLANK_AUDIO]", "(wind)"); those are not words
    if text.startswith(('[', '(')) and text.endswith((']', ')')):
        return ''
    return text
