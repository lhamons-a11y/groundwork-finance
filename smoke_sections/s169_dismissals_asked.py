"""A dismissal is said, and a category is silenced only when the user says so (gw 2.0/USAGE_SIGNALS.md, item 39 point 2;
Rob 2026-10-09: "approve U1–U4 as recommended").

    U1  a dismissal answers that insight for 60 days, and the card says so
    U2  (b) from the second dismissal in a category the card ASKS; a yes is the user's setting, listed with Undo; a no is
        not asked again; nothing is silenced on its own
    U3  dismissals never change the pace - the dial is the control
    U4  a category the old rule silenced (two dismissals, no answer) is no longer silenced
The tests are U6's list.
"""
import json
import re
import shutil
import subprocess


def _fn(src, name):
    m = re.search(r'\n  function ' + name + r'\(.*?\n  \}\n', src, re.S) or re.search(r'\n(?:async )?function ' + name + r'\(.*?\n\}\n', src, re.S)
    return m.group(0) if m else ''


def run(ctx):
    check, c, H, HJ, BASE, app = ctx.check, ctx.c, ctx.H, ctx.HJ, ctx.BASE, ctx.app_src
    from core.database import HistorianEntry, AppSetting, db_session
    from core.proactive import verdict, BRAKE_PER_WEEK
    from server import _proactive_state

    CAT, CAT2 = 's169 Dining', 's169 Hobbies'
    src = (BASE / 'core/proactive.py').read_text(encoding='utf-8')
    check('s169 U2/U3 the old rules are gone from the gate: no "passive for good", no backoff tier',
          'DISMISSALS_TO_PASSIVE' not in src and 'cadence_tier' not in src)

    def cand(cat):
        return {'key': 's169 probe ' + cat, 'kind': 'brake', 'months': 9, 'dollars': 900, 'has_path': True, 'category': cat}

    def state():
        with db_session() as s:
            st = _proactive_state(s)
        return {**st, 'session_prompts': 0, 'brake_last_7d': 0, 'shown': {}, 'monthly_budget': 2000}

    try:
        r1 = c.post('/api/proactive/dismiss', headers=HJ, data=json.dumps({'key': 's169 a', 'category': CAT})).get_json()['data']
        check('s169 U1 a dismissal is logged and says its 60 days; one dismissal asks nothing',
              r1['cooldown_days'] == 60 and r1['ask_silence'] is None)
        r2 = c.post('/api/proactive/dismiss', headers=HJ, data=json.dumps({'key': 's169 b', 'category': CAT})).get_json()['data']
        st = state()
        check('s169 U2 the second dismissal in a category ASKS - and nothing is silenced on its own',
              r2['ask_silence'] == CAT and CAT not in st['silenced_categories'] and st['category_dismissals'].get(CAT) == 2)
        check('s169 U4 a category with two dismissals and no answer still comes up (the old rule silenced it for good)',
              verdict(cand(CAT), st)['promote'] is True)
        check('s169 U3 dismissals never change the pace: no backoff in the state, and the weekly allowance is the dial\'s',
              'cadence_tier' not in st
              and verdict(cand(CAT), {**st, 'brake_last_7d': BRAKE_PER_WEEK - 1})['promote'] is True)

        y = c.post('/api/proactive/silence', headers=HJ, data=json.dumps({'category': CAT, 'silence': True})).get_json()['data']
        listed = c.get('/api/proactive/silenced', headers=H).get_json()['data']['silenced']
        check('s169 U2 a yes is the user\'s setting: listed, and the category is quiet',
              CAT in y['silenced'] and CAT in listed and verdict(cand(CAT), state())['gate'] == 'silenced')
        r3 = c.post('/api/proactive/dismiss', headers=HJ, data=json.dumps({'key': 's169 c', 'category': CAT})).get_json()['data']
        check('s169 U2 a silenced category is not asked about again', r3['ask_silence'] is None)
        u = c.post('/api/proactive/unsilence', headers=HJ, data=json.dumps({'category': CAT})).get_json()['data']
        check('s169 U2 Undo: the category can come up on its own again',
              CAT not in u['silenced'] and verdict(cand(CAT), state())['promote'] is True)

        for k in ('s169 d', 's169 e'):
            last = c.post('/api/proactive/dismiss', headers=HJ, data=json.dumps({'key': k, 'category': CAT2})).get_json()['data']
        c.post('/api/proactive/silence', headers=HJ, data=json.dumps({'category': CAT2, 'silence': False}))
        again = c.post('/api/proactive/dismiss', headers=HJ, data=json.dumps({'key': 's169 f', 'category': CAT2})).get_json()['data']
        check('s169 U2 a No changes nothing and is not asked again',
              last['ask_silence'] == CAT2 and again['ask_silence'] is None and CAT2 not in state()['silenced_categories']
              and verdict(cand(CAT2), state())['promote'] is True)
        with db_session() as s:
            evs = [e.event_category for e in s.query(HistorianEntry).all() if 's169' in (e.context_json or '')]
        check('s169 U2 each answer is the user\'s own, recorded: silenced, undone, declined',
              {'proactive_category_silenced', 'proactive_category_unsilenced', 'proactive_silence_declined'} <= set(evs))
    finally:
        with db_session() as s:
            for e in s.query(HistorianEntry).all():
                if 's169' in (e.context_json or ''):
                    s.delete(e)
            row = s.query(AppSetting).filter_by(key='proactive_silenced').first()
            if row:
                row.value = json.dumps([x for x in json.loads(row.value or '[]') if 's169' not in x])
            s.commit()

    node = shutil.which('node')
    pj = (BASE / 'static/js/teaching/proactive.js').read_text(encoding='utf-8')
    if node:
        js = ('const esc = s => String(s);\n' + _fn(pj, 'dismissedHtml') + _fn(pj, 'silencedHtml')
              + "console.log(JSON.stringify([dismissedHtml({cooldown_days: 60, ask_silence: null}),"
              + " dismissedHtml({cooldown_days: 60, ask_silence: 'Dining'}), silencedHtml(['Dining']), silencedHtml([])]));")
        p = subprocess.run([node, '-e', js], capture_output=True, text=True, encoding='utf-8', timeout=60)
        out = json.loads(p.stdout.strip() or '["","","",""]') if p.returncode == 0 else ['', '', '', '']
        check('s169 U1 the card says it: "Dismissed. Groundwork won\'t bring this up again for 60 days."',
              "Dismissed. Groundwork won't bring this up again for 60 days." in out[0] and 'Stop bringing up' not in out[0])
        check('s169 U2 the card asks, once the category has two dismissals, with Yes and No',
              'Stop bringing up Dining on its own? Insights about it stay on their pages.' in out[1]
              and 'data-gw-silence="yes"' in out[1] and 'data-gw-silence="no"' in out[1])
        check('s169 U2 Settings lists a silenced category with Undo, and lists nothing when there is none',
              'Dining' in out[2] and 'Undo' in out[2] and out[3] == '')
    check('s169 U2 the Settings list sits under the dial, drawn by the teaching layer (app.js calls no proactive route)',
          'id="proactiveSilenced"' in ctx.html_src and "getElementById('proactiveSilenced')" in pj
          and '/api/proactive/silenced' not in app)
