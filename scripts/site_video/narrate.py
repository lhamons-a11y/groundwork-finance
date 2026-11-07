"""Speak each narration line in Groundwork's own voice (Kokoro, af_heart) and write one WAV per line.

    python scripts/site_video/narrate.py <script.json> <out_dir>

The script is the video's scene list ({"scenes": [{"say": "..."}, ...]}). Each line becomes <out_dir>/line_NN.wav and
<out_dir>/narration.json records every line's length in seconds, so the composer can time scenes and captions to it.
"""
import json
import sys
import wave
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(BASE), str(BASE / 'core')]

from core import speak  # noqa: E402


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
        wav = speak.speak(text)
        path = out / f'line_{i:02d}.wav'
        path.write_bytes(wav)
        with wave.open(str(path)) as w:
            lengths.append(round(w.getnframes() / w.getframerate(), 3))
        print(f'{i:02d} {lengths[-1]:5.2f}s  {text[:70]}')
    (out / 'narration.json').write_text(json.dumps({'lengths': lengths}, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
