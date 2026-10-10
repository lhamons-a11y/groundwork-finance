"""Item 58: the evidence library - what research says, offered where it applies (gw 2.0/EVIDENCE_LIBRARY.md E1-E10,
RULED 2026-10-09; built on "build all items that have been ruled on").

    E1  every entry has its finding, limits, source, strength, facts, surfaces and offer
    E2  an entry is chosen from the person's goals and debts only - never from how the app is used (ruling 6)
    E3  shown as written, with its limits and source; no model, so AI off changes nothing
    E4  the voice check's R11 blocks a research claim that cites no accepted entry (both gate copies)
    E5  the offer is a question; the answer is the person's, kept append-only
    E6  only entries Rob has accepted are offered; drafts never show
    E8  the person's own rhythm is shown to them and read by nothing else
    E9  the goal card, the debt plan and the working picture carry it
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timedelta


def run(ctx):
    check, c, H, HJ, BASE = ctx.check, ctx.c, ctx.H, ctx.HJ, ctx.BASE
    app, html = ctx.app_src, ctx.html_src
    from core import evidence as ev
    from core.database import AppSetting, DebtAccount, SinkingFund, db_session

    lib = ev.library()
    bad = {e.get('id'): ev.problems(e) for e in lib['entries'] if ev.problems(e)}
    check(f's188 E1 every entry has all its fields, a full source and a question for its offer ({bad})',
          len(lib['entries']) >= 9 and not bad and len({e['id'] for e in lib['entries']}) == len(lib['entries']))
    rules = json.loads((BASE / 'static' / 'voice_rules.json').read_text(encoding='utf-8'))['wordlists']
    banned = [w for k, ws in rules.items() if k != 'RESEARCH_CLAIMS' for w in ws]
    hits = {e['id']: [w for w in banned if w in ' ' + ' '.join((e['finding'], e['limits'], e['offer'])).lower() + ' ']
            for e in lib['entries']}
    hits = {k: v for k, v in hits.items() if v}
    check(f's188 E10 no entry\'s words carry a verdict, command or judgement the voice rules block ({hits})', not hits)
    check('s188 E6 nothing is offered until Rob accepts it: every shipped entry is a draft, with what it was checked against',
          ev.accepted_ids() == [] and all(e['status'] == 'draft' and e.get('checked_against') for e in lib['entries']))

    # ── E2 / E6: selection, against a library with one accepted entry ──
    accepted = dict(lib['entries'][0], status='accepted', accepted_on='2026-10-10')
    debt_one = dict(lib['entries'][5], id='t_debt', status='accepted', accepted_on='2026-10-10')
    fd, path = tempfile.mkstemp(suffix='.json')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        json.dump({'version': 't', 'entries': [accepted, debt_one, lib['entries'][1]]}, f)
    real = ev.LIBRARY
    ev.LIBRARY = type(real)(path)
    try:
        with db_session() as s:
            s.query(SinkingFund).update({'is_active': False}); s.commit()
            for d in s.query(DebtAccount).all():
                d.is_active = False
            s.commit()
        none = c.get('/api/evidence?surface=goal', headers=H).get_json()['data']['entries']
        with db_session() as s:
            s.add(SinkingFund(name='s188 trip', target_amount=900, current_amount=100, is_active=True))
            s.add(DebtAccount(name='s188 card', current_balance=500, is_active=True))
            s.commit()
        goal = c.get('/api/evidence?surface=goal', headers=H).get_json()['data']['entries']
        debt1 = c.get('/api/evidence?surface=debt_plan', headers=H).get_json()['data']['entries']
        with db_session() as s:
            s.add(DebtAccount(name='s188 loan', current_balance=800, is_active=True, debt_type='loan')); s.commit()
        debt2 = c.get('/api/evidence?surface=debt_plan', headers=H).get_json()['data']['entries']
        ids = c.get('/api/evidence/ids', headers=H).get_json()['data']['ids']
        check('s188 E2/E6 an accepted entry appears only once its facts hold (a goal; two debts); a draft never does',
              none == [] and [e['id'] for e in goal] == [accepted['id']] and debt1 == [] and [e['id'] for e in debt2] == ['t_debt']
              and ids == sorted([accepted['id'], 't_debt']))

        # E5: the answer
        r1 = c.post('/api/evidence/answer', headers=HJ, data=json.dumps({'id': accepted['id'], 'answer': 'yes'}))
        r2 = c.post('/api/evidence/answer', headers=HJ, data=json.dumps({'id': accepted['id'], 'answer': 'no'}))
        r3 = c.post('/api/evidence/answer', headers=HJ, data=json.dumps({'id': lib['entries'][1]['id'], 'answer': 'yes'}))
        r4 = c.post('/api/evidence/answer', headers=HJ, data=json.dumps({'id': accepted['id'], 'answer': 'maybe'}))
        shown = c.get('/api/evidence?surface=goal', headers=H).get_json()['data']['entries'][0]
        check('s188 E5 an answer is the person\'s statement: kept in order, the latest shown, a draft or other answer refused',
              r1.status_code == r2.status_code == 200 and [a['answer'] for a in r2.get_json()['data']['answers']] == ['yes', 'no']
              and r3.status_code == 404 and r4.status_code == 400 and shown['answer']['answer'] == 'no')
    finally:
        ev.LIBRARY = real
        os.remove(path)
        with db_session() as s:
            s.query(SinkingFund).filter(SinkingFund.name.like('s188%')).delete(synchronize_session=False)
            s.query(DebtAccount).filter(DebtAccount.name.like('s188%')).delete(synchronize_session=False)
            s.query(AppSetting).filter_by(key='evidence_answers').delete()
            s.commit()

    # ── E2 / ruling 6: usage is never read ──
    evsrc = (BASE / 'core' / 'evidence.py').read_text(encoding='utf-8')
    reads_usage = lambda src: bool(re.search(r"app_opens|usage|AiLog|last_seen|page_view", src))
    srv = ctx.server_src
    holders = sorted(set(re.findall(r'\ndef (\w+)\([^)]*\):(?:(?!\ndef ).)*?app_opens', srv, re.S)))
    core_hits = [p.name for p in (BASE / 'core').glob('*.py') if 'app_opens' in p.read_text(encoding='utf-8')]
    check(f"s188 E2/E8 selection reads no usage; only usage_open and usage_rhythm touch the opens ({holders}, {core_hits})",
          not reads_usage(evsrc) and holders == ['usage_open', 'usage_rhythm'] and core_hits == []
          and "'app_opens'" not in app and "'app_opens'" not in ''.join(p.read_text(encoding='utf-8') for p in (BASE / 'static' / 'js' / 'teaching').glob('*.js')))
    check('s188 E2 mutation caught: selection that reads the opens would fail the check above',
          reads_usage(evsrc + "\n_setting_json(session, 'app_opens')"))

    # ── E8: the rhythm ──
    with db_session() as s:
        s.query(AppSetting).filter_by(key='app_opens').delete(); s.commit()
    c.post('/api/usage/open', headers=HJ, data='{}')
    one = c.get('/api/usage/rhythm', headers=H).get_json()['data']
    now = datetime.now()
    sun = now - timedelta(days=(now.weekday() + 1) % 7 or 7)
    opens = [(sun - timedelta(days=7 * k)).replace(hour=19, minute=30).isoformat(timespec='seconds') for k in range(4)]
    opens += [(now - timedelta(days=1)).replace(hour=9).isoformat(timespec='seconds'), (now - timedelta(days=90)).isoformat(timespec='seconds')]
    with db_session() as s:
        s.query(AppSetting).filter_by(key='app_opens').first().value = json.dumps(sorted(opens)); s.commit()
    many = c.get('/api/usage/rhythm', headers=H).get_json()['data']
    with db_session() as s:
        s.query(AppSetting).filter_by(key='app_opens').delete(); s.commit()
    check(f's188 E8 opens are counted for the last 30 days, and "mostly" named only when one time clearly leads ({one}, {many})',
          one == {'opens_30d': 1, 'mostly': None} and many == {'opens_30d': 5, 'mostly': 'Sunday evenings'})
    check('s188 E8 the line is the fact and says nothing reads it',
          'You opened Groundwork ' in app and 'Nothing in Groundwork reads it or draws anything from it.' in app
          and "API.post('/api/usage/open', {})" in app)

    # ── E3 / A10 / E9 ──
    rend = app.split('async function renderEvidence(')[1].split('\n}')[0] + app.split('function _evidenceHTML(')[1].split('\n}')[0]
    check('s188 E3/A10 an entry shows as written, with its limits and source, and no model is involved',
          'callAI(' not in rend and 'aiEnabled' not in rend and 'esc(e.finding)' in rend and 'esc(e.limits)' in rend
          and "What it doesn't show:" in rend and 'esc(s.journal' in rend)
    wl = (BASE / 'static' / 'js' / 'teaching' / 'willingness.js').read_text(encoding='utf-8')
    check('s188 E9 the goal card, the debt plan and the working picture carry the library',
          'id="evidenceGoal" data-evidence-surface="goal"' in html and 'id="evidenceDebt" data-evidence-surface="debt_plan"' in html
          and "renderEvidence('goal', g('evidenceGoal'))" in app and "renderEvidence('debt_plan', g('evidenceDebt'))" in app
          and "renderEvidence('willingness', g('evidenceWillingness'))" in wl)

    # ── E4: R11 in the shipped gate, run in Node, and in the Python harness ──
    node = shutil.which('node')
    out = {}
    if node:
        def fn(name):
            i = app.find(f'function {name}(')
            return app[i:app.find('\n}', i) + 2]
        i = app.find('const _VOICE_RULES_FALLBACK = {')
        js = ('const _VOICE_RULES = null;\n' + app[i:app.find('\n};', i) + 3] + '\n'
              + 'const _FIN_NUM_RE = ' + re.search(r'const _FIN_NUM_RE = (.+);', app).group(1) + ';\n'
              + fn('_financialNumbers') + '\n' + fn('_voiceGateCheck') + '\n'
              + 'let _EVIDENCE_IDS = new Set(["harkin2016_monitoring"]);\n'
              + 'const r = t => (_voiceGateCheck(t, null).results.R11_research_claims_sourced || {}).ok;\n'
              + 'console.log(JSON.stringify({bare: r("Studies show that people who budget save more."),'
              + ' most: r("Most people check less often when markets fall."),'
              + ' cited: r("Research on goals found that checking progress helped [ev:harkin2016_monitoring]."),'
              + ' unknown: r("Research found this [ev:made_up_2020]."),'
              + ' plain: r("Income was $4,280.00 this month."),'
              + ' other: r("A study found it [ev:harkin2016_monitoring]. Experts agree.")}));')
        fd, p = tempfile.mkstemp(suffix='.js')
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(js)
        try:
            out = json.loads(subprocess.run([node, p], capture_output=True, text=True, encoding='utf-8', timeout=60).stdout or '{}')
        except Exception:                      # noqa: BLE001
            out = {}
        finally:
            os.remove(p)
    check(f's188 E4 R11, run in Node: an unsourced claim fails, a claim citing an accepted id passes, a made-up id fails, '
          f'and each sentence needs its own ({out})',
          out == {'bare': False, 'most': False, 'cited': True, 'unknown': False, 'plain': True, 'other': False})
    import voice_discipline_test as vdt
    real_ids = vdt._accepted_evidence_ids
    try:
        a = vdt.check('Studies show that people who budget save more.')['R11_research_claims_sourced'][0]
        vdt._accepted_evidence_ids = lambda: {'harkin2016_monitoring'}
        b = vdt.check('Research on goals found that checking progress helped [ev:harkin2016_monitoring].')['R11_research_claims_sourced'][0]
    finally:
        vdt._accepted_evidence_ids = real_ids
    check('s188 E4 the Python harness holds the same R11', a is False and b is True)
    check('s188 E4 the gate fails closed: with no accepted ids loaded, every research claim fails',
          'catch (e) { _EVIDENCE_IDS = new Set(); }' in app and "(typeof _EVIDENCE_IDS !== 'undefined' && _EVIDENCE_IDS) || new Set()" in app)
