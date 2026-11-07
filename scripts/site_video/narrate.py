"""Speak each narration line in Groundwork's own voice (Kokoro, af_heart) and write one WAV per line.

    python scripts/site_video/narrate.py <script.json> <out_dir>

The script is the video's scene list ({"scenes": [{"say": "..."}, ...]}). Each line becomes <out_dir>/line_NN.wav and
<out_dir>/narration.json records every line's length in seconds, so the composer can time scenes and captions to it.
"""
import json
import re
import sys
import wave
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(BASE), str(BASE / 'core')]

from core import speak  # noqa: E402

# How a version is said aloud (Rob 2026-11-07: "two point Oh", not "two point zero"). Only the spoken words change;
# the captions keep "2.0".
SAY_AS = [(re.compile(r'\b(\d+)\.0\b'), lambda m: f'{m.group(1)} point oh'),
          # Letters said as letters (Rob 2026-11-07: "H S A, not hsaa", then "H S eh"). In a sentence the voice reads a
          # lone "A" as the word "a" (ɐ) and "ay" as "eye" (aɪ); "eh" it reads as the letter (eɪ).
          (re.compile(r'\b(HSA|FSA|IRS|PDF)s?\b'), lambda m: ' '.join({'A': 'eh'}.get(c, c) for c in m.group(1)))]


def for_speech(text):
    for pattern, said in SAY_AS:
        text = pattern.sub(said, text)
    return text


def main(script_path, out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    scenes = json.loads(Path(script_path).read_text(encoding='utf-8'))['scenes']
    lengths = []
    for i, scene in enumerate(scenes):
        text = scene.get('say', '').strip()
        if not text:
            lengths.append(0.0)
            continue
        wav = speak.speak(for_speech(text))
        path = out / f'line_{i:02d}.wav'
        path.write_bytes(wav)
        with wave.open(str(path)) as w:
            lengths.append(round(w.getnframes() / w.getframerate(), 3))
        print(f'{i:02d} {lengths[-1]:5.2f}s  {text[:70]}')
    (out / 'narration.json').write_text(json.dumps({'lengths': lengths}, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
