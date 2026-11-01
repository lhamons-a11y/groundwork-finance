"""Item 116 stage 4 (gw 2.0/VOICE_ASSISTANT.md, approved 2026-10-31):

    V9   a choice of Groundwork's voices - seven, all in the shipped voices file, heard before chosen; anything else is
         the default (Heart, Rob's choice)
    V10  which microphone, falling back to the computer's default when it is gone; "Test my microphone" says what it heard
    V12  voice first: each page, message and answer said aloud; off by default, and the Settings text says to leave it
         off with a screen reader (PANEL_REVIEW.md P6b: nothing said twice)
"""
import json
import os
import shutil
import subprocess
import tempfile


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    from core import speak
    import numpy as np
    voices_file = ctx.BASE / 'vendor' / 'kokoro' / speak.VOICES_FILE
    if voices_file.is_file():
        shipped = set(np.load(str(voices_file)).files)
        check(f's278 V9 every voice offered is in the shipped voices file ({sorted(set(speak.VOICES) - shipped)})',
              set(speak.VOICES) <= shipped)
    check('s278 V9 seven voices, Rob\'s first and the default; British voices say English the British way',
          list(speak.VOICES)[0] == speak.VOICE == 'af_heart' and len(speak.VOICES) == 7)

    used = []

    class _Fake:
        def create(self, words, voice, speed, lang):
            used.append((voice, lang))
            return np.zeros(2400, dtype=np.float32), 24000
    real_load, real_status = speak._load, speak.status
    speak._load, speak.status = (lambda: _Fake()), (lambda: {'available': True, 'reason': ''})
    try:
        for body in ({'text': 'Hello.'}, {'text': 'Hello.', 'voice': 'bm_george'}, {'text': 'Hello.', 'voice': 'xx_any'}):
            c.post('/api/voice/speak', headers=HJ, data=json.dumps(body))
        c.patch('/api/settings', headers=HJ, data=json.dumps({'speak_voice': 'af_bella'}))
        c.post('/api/voice/speak', headers=HJ, data=json.dumps({'text': 'Hello.'}))
        c.patch('/api/settings', headers=HJ, data=json.dumps({'speak_voice': 'not_a_voice'}))
        c.post('/api/voice/speak', headers=HJ, data=json.dumps({'text': 'Hello.'}))
        st = c.get('/api/voice', headers=H).get_json()['data']['speak']
    finally:
        speak._load, speak.status = real_load, real_status
        c.patch('/api/settings', headers=HJ, data=json.dumps({'speak_voice': ''}))
    check(f"s278 V9 the voice named for \"Hear it\", else the one chosen in Settings, else the default - never one not "
          f"offered ({used})",
          used == [('af_heart', 'en-us'), ('bm_george', 'en-gb'), ('af_heart', 'en-us'), ('af_bella', 'en-us'),
                   ('af_heart', 'en-us')]
          and [v['key'] for v in st['voices']] == list(speak.VOICES) and st['default'] == 'af_heart')

    acc = (ctx.BASE / 'static' / 'js' / 'teaching' / 'access.js').read_text(encoding='utf-8')
    check('s278 V9/V10/V12 Settings offers the voice with "Hear it", the microphone with a test, and voice first - off '
          'by default, with the screen-reader warning',
          'id="gwVoicePick"' in acc and 'id="gwVoiceHear"' in acc and 'id="gwMicPick"' in acc and 'id="gwMicTest"' in acc
          and "voice_first: 'off' }" in acc and 'If you use a screen reader, leave this off' in acc)
    node = shutil.which('node')
    if not node:
        return
    fn = acc[acc.index('  async function _openMic() {'):acc.index('  // V10: "Test my microphone"')]
    js = r"""
const calls = []; let refuse = null;
Object.defineProperty(globalThis, 'navigator', { configurable: true, value: { mediaDevices: { getUserMedia: async (c) => {
  calls.push(c.audio.deviceId ? c.audio.deviceId.exact : 'default');
  if (refuse && c.audio.deviceId) { const e = new Error('gone'); e.name = refuse; throw e; } return 'stream'; } } } });   // Node has its own
const prefs = { mic_device: '' };
""" + fn + r"""
(async () => {
  const out = {};
  await _openMic(); out.none = calls.splice(0);
  prefs.mic_device = 'usb-mic'; await _openMic(); out.chosen = calls.splice(0);
  refuse = 'OverconstrainedError'; await _openMic(); out.gone = calls.splice(0);
  refuse = 'NotAllowedError'; try { await _openMic(); out.denied = 'opened'; } catch (e) { out.denied = e.name; }
  console.log(JSON.stringify(out));
})();
"""
    f = os.path.join(tempfile.mkdtemp(prefix='s278_'), 'mic.js')
    open(f, 'w', encoding='utf-8').write(js)
    o = json.loads(subprocess.run([node, f], capture_output=True, text=True, encoding='utf-8', timeout=30).stdout or '{}')
    check(f"s278 V10 the chosen microphone is used; when it is gone, the computer's default; a refusal is not "
          f"overridden ({o})",
          o.get('none') == ['default'] and o.get('chosen') == ['usb-mic'] and o.get('gone') == ['usb-mic', 'default']
          and o.get('denied') == 'NotAllowedError')
