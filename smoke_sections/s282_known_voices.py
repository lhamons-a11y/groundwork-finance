"""Item 116 V19: only voices it knows (VOICE_ASSISTANT.md 4c; Rob 2026-11-01: "lets have it recognize your voice.. Since
we are dealing with people finance and health information").

    K1  the voiceprint engine imports nothing that can reach a network; its features are Kaldi's 80-band log mel
        filterbank, with the silence trimmed; the model file is the one measured, and is packaged only when it is
    K2  enrolling: five readings make one voiceprint, kept in the record; too few, or one that does not sound like the
        others (another voice, the television), is refused and nothing is kept
    K3  the voiceprint never goes to the page: /api/settings leaves it out, PATCH cannot write it, /api/voice shows names
        and dates only
    K4  with it on, a voice it knows is recognised; any other is let go before whisper runs - except "stop" while
        Groundwork reads, which anyone may say
    K5  forgetting the last voice turns it off; it cannot be turned on with no voice to know
    K6  Test my microphone says whose voice it heard, with the score and the bar it had to clear
"""
import ast
import base64
import io
import json
import wave


def _wav(value, seconds=2.0):
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        w.writeframes(int(value).to_bytes(2, 'little', signed=True) * int(seconds * 16000))
    return buf.getvalue()


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    import numpy as np
    import server
    from core import voice, voiceprint

    # ── K1 ──────────────────────────────────────────────────────────────────────────────────────────────────────────
    src = (ctx.BASE / 'core' / 'voiceprint.py').read_text(encoding='utf-8')
    mods = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            mods |= {a.name.split('.')[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module.split('.')[0])
    check(f"s282 K1 the voiceprint engine imports nothing that can reach a network ({sorted(mods)})",
          not mods & {'socket', 'http', 'urllib', 'requests', 'ssl', 'websocket', 'httpx', 'aiohttp'})
    t = np.arange(16000) / 16000.0
    tone = (0.3 * np.sin(2 * np.pi * 1000 * t)).astype(np.float32)
    fb = voiceprint.fbank(tone)
    mel = lambda f: 1127.0 * np.log(1.0 + f / 700.0)
    want = int(round((mel(1000) - mel(20)) / ((mel(8000) - mel(20)) / 81))) - 1
    check(f"s282 K1 Kaldi's filterbank: 25 ms frames every 10 ms, 80 bands, a 1 kHz tone in the band for 1 kHz "
          f"({fb.shape}, peak band {int(fb.mean(axis=0).argmax())}, expected {want})",
          fb.shape == (98, 80) and abs(int(fb.mean(axis=0).argmax()) - want) <= 1)
    paused = np.concatenate([tone, np.zeros(32000, dtype=np.float32)])
    check(f"s282 K1 the pause that ends a clip is trimmed before its voiceprint ({voiceprint.voiced_seconds(paused):.2f} s "
          f"voiced of 3 s)", 0.9 <= voiceprint.voiced_seconds(paused) <= 1.05)
    import spec_engine
    pinned = spec_engine.VOICEPRINT_SHA256 == voiceprint.MODEL_SHA256 and spec_engine.VOICEPRINT_FILE == voiceprint.MODEL_FILE
    iss = all('vendor\\voiceprint\\voxceleb_resnet34_LM.onnx' in (ctx.BASE / n).read_text(encoding='utf-8')
              for n in ('groundwork.iss', 'groundwork_offline.iss', 'groundwork_store.iss'))
    specs = all('spec_engine.voiceprint_model_data()' in (ctx.BASE / n).read_text(encoding='utf-8')
                for n in ('groundwork_macos.spec', 'groundwork_linux.spec'))
    notice = 'CC BY 4.0' in (ctx.BASE / 'THIRD_PARTY_NOTICES.md').read_text(encoding='utf-8')
    check(f"s282 K1 the measured model is pinned, installed by every installer, and credited (CC BY 4.0) "
          f"({pinned}, {iss}, {specs}, {notice})", pinned and iss and specs and notice)
    if voiceprint.status()['available']:
        p = voiceprint.embed(np.random.default_rng(1).normal(0, 0.1, 32000).astype(np.float32))
        check('s282 K1 the installed model makes a 256-number voiceprint of unit length',
              p is not None and p.shape == (256,) and abs(float(np.linalg.norm(p)) - 1) < 1e-4)

    # ── A stand-in voice model: a clip's loudness says whose voice it is ─────────────────────────────────────────────
    rng = np.random.default_rng(7)
    unit = lambda v: (v / np.linalg.norm(v)).astype(np.float32)
    ROB, TV = unit(rng.normal(size=256)), unit(rng.normal(size=256))
    ROB_AGAIN = unit(ROB + 0.3 * unit(rng.normal(size=256)))
    who_by_level = {1000: ROB, 1100: ROB_AGAIN, 3000: TV}
    seen = []

    def fake_embed(samples, session=None):
        seen.append(1)
        lvl = int(round(float(np.abs(samples).mean()) * 32768 / 100) * 100)
        return who_by_level.get(lvl)

    class _Seg:
        def __init__(self, t):
            self.text = t

    class _Whisper:
        said, calls = 'open my budget', 0

        def transcribe(self, samples, **params):
            _Whisper.calls += 1
            return [_Seg(_Whisper.said)]

    acc_src = (ctx.BASE / 'static' / 'js' / 'teaching' / 'access.js').read_text(encoding='utf-8')
    real = (voiceprint.embed, voiceprint.voiced_seconds, voiceprint.status, voice.status, voice._model, voice.preload)
    voiceprint.embed, voiceprint.voiced_seconds = fake_embed, (lambda s: 3.0)
    voiceprint.status = lambda: {'available': True, 'reason': ''}
    voice.status, voice._model, voice.preload = (lambda: {'available': True, 'reason': ''}), _Whisper(), (lambda: None)
    WAV = {'Content-Type': 'audio/wav'}
    c.patch('/api/settings', headers=HJ, data=json.dumps({'voice_commands': 'on'}))
    try:
        # K5 first: nothing to know, so it cannot be turned on
        c.patch('/api/settings', headers=HJ, data=json.dumps({'voice_only_known': 'on'}))
        off_first = c.get('/api/voice/voices', headers=H).get_json()['data']['on'] is False

        # K2: enrolling
        b64 = lambda v: base64.b64encode(_wav(v, 4.0)).decode()
        _Whisper.said = ' '.join(voiceprint.SENTENCES)
        mixed = c.post('/api/voice/voices', headers=HJ, data=json.dumps({'name': 'Rob', 'clips': [b64(1000)] * 4 + [b64(3000)]}))
        none_kept = c.get('/api/voice/voices', headers=H).get_json()['data']['voices'] == []
        _Whisper.said = 'and in other news tonight the weather turns cold'          # the television, not the sentences
        tv_room = c.post('/api/voice/voices', headers=HJ, data=json.dumps({'name': 'Rob', 'clips': [b64(1000)] * 5}))
        _Whisper.said = ' '.join(voiceprint.SENTENCES)                           # each sentence, read
        good = c.post('/api/voice/voices', headers=HJ, data=json.dumps({'name': 'Rob', 'clips': [b64(1000)] * 3 + [b64(1100)] * 2}))
        _Whisper.said = 'open my budget'
        view = good.get_json()['data']
        check(f"s282 K2 five readings make one voiceprint, and 'Only voices it knows' turns on "
              f"({good.status_code}, {[v['name'] for v in view['voices']]}, {view['on']})",
              good.status_code == 200 and [v['name'] for v in view['voices']] == ['Rob'] and view['on'] is True)
        check(f"s282 K2 a reading in another voice - the television - is refused, and nothing is kept "
              f"({mixed.status_code}: {(mixed.get_json() or {}).get('error')})",
              mixed.status_code == 400 and 'did not sound like the others' in (mixed.get_json() or {}).get('error', '')
              and none_kept)

        check(f"s282 K2 readings that do not say their sentences - the television talking - are refused "
              f"({tv_room.status_code}: {(tv_room.get_json() or {}).get('error')})",
              tv_room.status_code == 400 and 'did not sound like they were read' in (tv_room.get_json() or {}).get('error', ''))
        check('s282 K2 the page listens to the room first and will not enrol over sound that comes and goes like speech, '
              'and drops a reading that never paused', 'if (await _roomTalking(stream))' in acc_src
              and 'clips.push(b ? _b64(b) : null)' in acc_src and 'Date.now() - t0 <= ENROL_MAX_MS' in acc_src)

        # K3: the voiceprint never reaches the page
        sets = c.get('/api/settings', headers=H).get_json()['data']
        from core.database import AppSetting, db_session
        with db_session() as s:
            kept = json.loads(s.query(AppSetting).filter_by(key='voiceprints').first().value)
        c.patch('/api/settings', headers=HJ, data=json.dumps({'voiceprints': '[]'}))
        after_patch = c.get('/api/voice/voices', headers=H).get_json()['data']['voices']
        status = c.get('/api/voice', headers=H).get_json()['data']['known']
        check(f"s282 K3 the voiceprint is kept in the record but never sent to the page; PATCH cannot write it "
              f"({'voiceprints' in sets}, {len(after_patch)}, {sorted(status['voices'][0])})",
              'voiceprints' not in sets and len(kept) == 1 and kept[0]['print'] and len(after_patch) == 1
              and sorted(status['voices'][0]) == ['enrolled_at', 'id', 'name'])

        # K4: a known voice is heard; another is let go before whisper runs
        calls = _Whisper.calls
        mine = c.post('/api/voice/transcribe', headers={**H, **WAV}, data=_wav(1100)).get_json()['data']
        mine_calls = _Whisper.calls - calls
        calls = _Whisper.calls
        tv = c.post('/api/voice/transcribe', headers={**H, **WAV}, data=_wav(3000)).get_json()['data']
        tv_calls = _Whisper.calls - calls
        check(f"s282 K4 a voice it knows is recognised; the television is let go before whisper runs ({mine}, {tv}, "
              f"whisper ran {mine_calls} and {tv_calls})",
              mine == {'text': 'open my budget', 'voice': 'Rob'} and tv == {'text': '', 'voice': None}
              and mine_calls == 1 and tv_calls == 0)
        _Whisper.said = 'Stop.'
        stop = c.post('/api/voice/transcribe?short=1', headers={**H, **WAV}, data=_wav(3000)).get_json()['data']
        _Whisper.said = 'Next.'
        nxt = c.post('/api/voice/transcribe?short=1', headers={**H, **WAV}, data=_wav(3000)).get_json()['data']
        silent = c.post('/api/voice/transcribe', headers={**H, **WAV}, data=_wav(0)).get_json()['data']
        check(f"s282 K4 while Groundwork reads anyone may say 'stop' - and nothing else; a clip it cannot score is no one "
              f"it knows ({stop}, {nxt}, {silent})",
              stop.get('text') == 'Stop.' and nxt == {'text': '', 'voice': None} and silent == {'text': '', 'voice': None})
        _Whisper.said = 'open my budget'
        c.patch('/api/settings', headers=HJ, data=json.dumps({'voice_only_known': 'off'}))
        anyone = c.post('/api/voice/transcribe', headers={**H, **WAV}, data=_wav(3000)).get_json()['data']
        c.patch('/api/settings', headers=HJ, data=json.dumps({'voice_only_known': 'on'}))
        check(f"s282 K4 turned off, any voice is heard again ({anyone})", anyone == {'text': 'open my budget'})

        # K6: Test my microphone
        ck_mine = c.post('/api/voice/voices/check', headers={**H, **WAV}, data=_wav(1100)).get_json()['data']
        ck_tv = c.post('/api/voice/voices/check', headers={**H, **WAV}, data=_wav(3000)).get_json()['data']
        check(f"s282 K6 Test my microphone says whose voice, with its score and the bar ({ck_mine}, {ck_tv})",
              ck_mine['voice'] == 'Rob' and ck_mine['score'] >= voiceprint.THRESHOLD == ck_mine['threshold']
              and ck_tv['voice'] is None and ck_tv['score'] < voiceprint.THRESHOLD)

        # K5: forgetting the last voice turns it off
        vid = c.get('/api/voice/voices', headers=H).get_json()['data']['voices'][0]['id']
        gone = c.delete('/api/voice/voices/' + vid, headers=H).get_json()['data']
        back = c.post('/api/voice/transcribe', headers={**H, **WAV}, data=_wav(3000)).get_json()['data']
        check(f"s282 K5 forgetting the last voice deletes its voiceprint and turns it off; it could not be turned on with "
              f"no voice ({off_first}, {gone['voices']}, {gone['on']}, {back})",
              off_first and gone['voices'] == [] and gone['on'] is False and back == {'text': 'open my budget'})
    finally:
        (voiceprint.embed, voiceprint.voiced_seconds, voiceprint.status, voice.status, voice._model, voice.preload) = real
        c.patch('/api/settings', headers=HJ, data=json.dumps({'voice_commands': 'off', 'voice_only_known': 'off'}))

    acc = (ctx.BASE / 'static' / 'js' / 'teaching' / 'access.js').read_text(encoding='utf-8')
    check("s282 K2/K6 Settings teaches it a voice, forgets one, and Test my microphone asks whose voice it heard",
          "API.post('/api/voice/voices', { name: name, clips: clips })" in acc and "data-gw-unvoice" in acc
          and "'/api/voice/voices/check'" in acc and 'not a lock' in acc)
