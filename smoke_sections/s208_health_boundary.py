"""Item 45 stage 1, the health privacy enforcement point (gw 2.0/HEALTH_PRIVACY_H6.md P1-P9; Rob 2026-10-12: "I approve
P1 - P9"). H6 is complete only when these pass (HEALTH_REVIEW.md section 7):

    P1  one classifier, from the one protected list, and one scrubber
    P2  logs: every record scrubbed on every handler; no log call formats a merchant or description
    P3  exports leave health spending out unless ticked, and say how many
    P4  a backup says it holds everything, health included
    P5  the model's context is scrubbed      P6  the AI log is scrubbed again - the named regression case
    P7  no outbound request is built from a transaction or a health record
    P8  the Historian's context carries no health text
    P9  every sink in the code is registered, and every registered sink exists
    and the derived-disclosure case: a pharmacy charge that names no person reaches no sink
"""
import ast
import io
import json
import logging
import os
import tempfile
from datetime import date
from pathlib import Path

MERCHANT = 'S208 CORNER PHARMACY #771'


def run(ctx):
    check, c, H, HJ, BASE = ctx.check, ctx.c, ctx.H, ctx.HJ, ctx.BASE
    from core import health_boundary as hb
    from core.health_sinks_scan import scan
    from core.database import AiLog, AppSetting, Category, HistorianEntry, Transaction, db_session
    import server

    # P1: the classifier is the protected list's health block, in whole words
    check('s208 P1 one classifier from the one protected list: care is health, the look-alikes are not',
          all(hb.is_health_category(n) for n in ('Pharmacy', 'Doctor / Co-pays', 'Health', 'Prescriptions', 'Mental Health', 'Dental'))
          and not any(hb.is_health_category(n) for n in ('Water', 'Groceries', 'Gas', 'Health Club', 'Rent', 'Hospitality'))
          and hb.HEALTH_TERMS[0] == 'health care' and 'pharmacy' in hb.HEALTH_TERMS and 'rent' not in hb.HEALTH_TERMS)

    with db_session() as s:
        pharm = s.query(Category).filter_by(name='Pharmacy').first()
        if not pharm:
            pharm = Category(name='Pharmacy', type='expense'); s.add(pharm); s.flush()
        kid = Category(name='s208 Rx refills', type='expense', parent_id=pharm.id)
        shop = Category(name='s208 Hardware', type='expense')
        s.add_all([kid, shop]); s.flush()
        t1 = Transaction(date=date.today(), amount=42.10, type='debit', category_id=pharm.id, merchant=MERCHANT, description=MERCHANT)
        t2 = Transaction(date=date.today(), amount=19.99, type='debit', category_id=shop.id, merchant='S208 BOLT BARN', description='S208 BOLT BARN')
        s.add_all([t1, t2]); s.commit()
        ids = hb.health_category_ids(s)
        n = hb.refresh(s)
        kid_id, pharm_id = kid.id, pharm.id
    check('s208 P1 a health category\'s child is health too', pharm_id in ids and kid_id in ids)
    clean = hb.scrub(f'paid {MERCHANT.lower()} and S208 BOLT BARN')
    check(f's208 P1 the scrubber takes out the pharmacy and leaves the hardware store ({clean!r})',
          n >= 1 and MERCHANT.lower() not in clean.lower() and '[health: Pharmacy]' in clean and 'S208 BOLT BARN' in clean)

    # P2: logs
    buf = io.StringIO()
    h = logging.StreamHandler(buf)
    root = logging.getLogger()
    root.addHandler(h)
    try:
        hb.install_log_filter()
        logging.getLogger('groundwork').warning('import failed on %s', MERCHANT)
    finally:
        root.removeHandler(h)
    check(f"s208 P2 a log line naming the pharmacy is scrubbed on its way out ({buf.getvalue().strip()!r})",
          MERCHANT not in buf.getvalue() and '[health: Pharmacy]' in buf.getvalue())
    offenders = []
    from core.health_sinks_scan import APP_FILES
    files = [BASE / f for f in APP_FILES if (BASE / f).exists()] + sorted((BASE / 'core').glob('*.py'))
    for p in files:
        for node in ast.walk(ast.parse(p.read_text(encoding='utf-8'))):
            if isinstance(node, ast.Call) and getattr(node.func, 'attr', '') in ('debug', 'info', 'warning', 'error', 'exception') \
                    and any(isinstance(a, ast.Attribute) and a.attr in ('merchant', 'description') for arg in node.args for a in ast.walk(arg)):
                offenders.append(f'{p.name}:{node.lineno}')
    check(f's208 P2 no log call formats a transaction\'s merchant or description ({offenders})', not offenders)

    # P3: exports
    out_dir = Path(tempfile.mkdtemp(prefix='gw_s208_'))
    with db_session() as s:
        s.query(AppSetting).filter_by(key='export_dir').delete()
        s.add(AppSetting(key='export_dir', value=str(out_dir))); s.commit()
    def export(body):    # read at once: two exports in the same second share a file name
        r = c.post('/api/settings/export-to-file', headers=HJ, data=json.dumps(body)).get_json()['data']
        return r, Path(r['path']).read_text(encoding='utf-8')
    r1, j1 = export({'format': 'json'})
    r2, c2 = export({'format': 'csv'})
    r3, j3 = export({'format': 'json', 'include_health': True})
    check(f"s208 P3 an export leaves health spending out unless ticked, and says how many ({r1.get('health_left_out')})",
          MERCHANT not in j1 and MERCHANT not in c2 and r1['health_left_out'] >= 1 and 'left out' in j1 and 'left out' in c2
          and 'S208 BOLT BARN' in j1 and MERCHANT in j3 and r3['health_left_out'] == 0)
    with db_session() as s:
        s.query(AppSetting).filter_by(key='export_dir').delete(); s.commit()

    # P4: backups
    b = c.post('/api/backup/create', headers=HJ, data='{}').get_json()['data']
    check('s208 P4 a backup copies everything and says so, on the page and in its answer',
          b.get('statement') == server.BACKUP_STATEMENT and 'health' in server.BACKUP_STATEMENT
          and server.BACKUP_STATEMENT in ctx.html_src)

    # P5: the model's context
    body = server._health_scrub_prompt({'system': f'Spending: {MERCHANT} $42.10; Pharmacy $42.10',
                                        'messages': [{'role': 'user', 'content': f'what was {MERCHANT}?'}]})
    check('s208 P5 the model is given the category and the amount, never the pharmacy\'s name',
          MERCHANT not in json.dumps(body) and 'Pharmacy $42.10' in body['system']
          and 'body = _health_scrub_prompt(request.json or {})' in ctx.server_src)

    # P6: the AI log - the named regression case
    with db_session() as s:
        s.query(AppSetting).filter_by(key='ai_log_keep').delete(); s.commit()
    lid = server._ai_log_write({'surface': 's208', 'system': f'about {MERCHANT}',
                                'messages': [{'role': 'user', 'content': MERCHANT}]}, f'You paid {MERCHANT}.')
    with db_session() as s:
        row = s.get(AiLog, lid) if lid else None
        stored = (row.system + row.messages + row.response) if row else ''
    check('s208 P6 the AI log stores no pharmacy name, whoever wrote to it (item 62\'s log, the named regression case)',
          lid is not None and MERCHANT not in stored and '[health: Pharmacy]' in stored)
    vm = c.post('/api/ai/voice-miss', headers=HJ, data=json.dumps({'surface': 's208', 'text': f'You paid {MERCHANT}.'}))
    from core.database import DATA_DIR
    vlog = (Path(DATA_DIR) / 'voice_miss_log.jsonl')
    check('s208 P5 the voice-check miss log keeps no pharmacy name either',
          vm.status_code == 200 and vlog.exists() and MERCHANT not in vlog.read_text(encoding='utf-8'))

    # P7: outbound requests are built from no transaction or health record
    leaks = []
    for f in sorted({f for (f, fn, kind) in hb.HEALTH_SINKS if kind == 'network'}):
        text = (BASE / f).read_text(encoding='utf-8')
        tree = ast.parse(text)
        parents = {}
        for node in ast.walk(tree):
            for ch in ast.iter_child_nodes(node):
                parents[ch] = node
        from core.health_sinks_scan import _kind
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _kind(node) == 'network':
                fn = parents.get(node)
                while fn is not None and not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    fn = parents.get(fn)
                src = ast.get_source_segment(text, fn) if fn is not None else ''
                if any(w in (src or '') for w in ('Transaction', 'Healthcare', 'HealthPlan', 'PersonAssignment', '.merchant')):
                    leaks.append(f'{f}:{fn.name}')
    check(f's208 P7 no outbound request is built from a transaction or a health record ({leaks})', not leaks)

    # P8: the Historian
    with db_session() as s:
        e = server.log_historian_event(s, 's208_probe', context={'merchant': MERCHANT, 'category_id': pharm_id})
        s.commit()
        ctxj = s.get(HistorianEntry, e.id).context_json
    check('s208 P8 the Historian keeps the category and drops the pharmacy\'s name',
          MERCHANT not in ctxj and str(pharm_id) in ctxj)

    # P9: the registry matches the code, both ways
    found, reg = scan(BASE), set(hb.HEALTH_SINKS)
    check(f's208 P9 every sink in the code is registered with its enforcement, and every registered one exists '
          f'(new {sorted(found - reg)[:3]}, gone {sorted(reg - found)[:3]})', found == reg and len(found) >= 40)
    tmp = Path(tempfile.mkdtemp(prefix='gw_s208_scan_'))
    (tmp / 'core').mkdir()
    (tmp / 'server.py').write_text('import requests\ndef leak(t):\n    requests.post("https://x.example", json=t)\n', encoding='utf-8')
    check('s208 P9 the scanner sees a new outbound path, so an unregistered one fails the gate',
          ('server.py', 'leak', 'network') in scan(tmp))

    with db_session() as s:
        s.query(Transaction).filter(Transaction.merchant.in_([MERCHANT, 'S208 BOLT BARN'])).delete(synchronize_session=False)
        s.query(HistorianEntry).filter_by(event_category='s208_probe').delete()
        s.commit()
