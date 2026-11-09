"""Group a crawl's problems by what went wrong: python triage.py <crawl.json> [...]"""
import json
import re
import sys
from collections import defaultdict

groups = defaultdict(list)
totals = []
for path in sys.argv[1:]:
    for v in json.load(open(path, encoding='utf-8')):
        if v.get('missing'):
            groups[('page missing', v['view'])].append(path)
            continue
        totals.append((path.split('\\')[-2] if '\\' in path else path, v['view'], v.get('clicks'), v.get('problems'), v.get('seconds')))
        for r in v.get('log', []):
            if r.get('ok'):
                continue
            where = f"{v['view']}: [{r.get('text', '')[:40]}]"
            for e in r.get('errors', []) or []:
                groups[('exception', re.sub(r'\d+', 'N', (e or '').split('\n')[0])[:160])].append(where)
            for e in r.get('rejections', []) or []:
                groups[('unhandled rejection', re.sub(r'\d+', 'N', e.split('\n')[0])[:160])].append(where)
            for e in r.get('console', []) or []:
                groups[('console error', re.sub(r'\d+', 'N', e)[:160])].append(where)
            for h in r.get('http', []) or []:
                body = re.sub(r'\d+', 'N', h.get('body', ''))[:120]
                groups[(f"HTTP {h['s']}", f"{h['m']} {re.sub(r'/[0-9]+', '/N', h['p'].split('?')[0])} {body}")].append(where)
            if r.get('clickErr'):
                groups[('click failed', r['clickErr'][:160])].append(where)
            if r.get('evalErr'):
                groups[('page stopped answering', r['evalErr'][:160])].append(where)
            if r.get('err'):
                groups[('crawler', r['err'][:160])].append(where)

print('run / page / controls / with problems / seconds')
for t in totals:
    print('  ', *t)
print()
for (kind, what), where in sorted(groups.items(), key=lambda x: (x[0][0], -len(x[1]))):
    uniq = sorted(set(where))
    print(f'[{kind}] x{len(where)}  {what}')
    for w in uniq[:6]:
        print('      ', w)
    if len(uniq) > 6:
        print(f'       ... and {len(uniq) - 6} more')
