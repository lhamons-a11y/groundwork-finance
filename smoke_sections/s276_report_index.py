"""Item 115 stages 4-7 (gw 2.0/ASK_FOR_A_REPORT.md P3-P9, section 14; Rob 2026-11-01 "lets complete the rest of the
stages"): a request for a report in the person's own words.

    P3-P6  the index reads Rob's 25 and the 25 held out with no model: right sections, a doubt asks, nothing wrong built
    P5     every period read by core/periods.py; style terms read ("as a table", "for printing", "out loud")
    P6.4   a request the index could not build alone is kept on this computer, with what the person picked; cleared
    P7/P8  the helpers choose only from a list, under a grammar; an answer off the list is refused
           measured: H-a and H-b only advise (their pick first, the person chooses); H-c builds and says it
    P9/C4  H-d suggests; a word is kept only on the person's Yes, and only as a name the record has
"""
import json
from datetime import date, timedelta
from pathlib import Path

SAMPLE = {'payees': ['Bayside Grill', 'BrightCell Wireless', 'ClearWave Internet', 'Corner Market', 'Fresh Farm Market',
                     'GiftNook', 'Golden Wok', 'Happy Paws Pet Supply', 'Ironworks Gym', 'Lakeside Property Management',
                     'Lantern Cafe', 'Luna Taqueria', 'Metro Power & Light', 'Northside Urgent Care', 'ParcelMart',
                     'Pine Street Pizza', 'QuickFuel', 'SafeHarbor Auto Insurance', 'StreamBox', 'Threadline',
                     'TuneFlow', 'Valley Foods'],
          'categories': ['Auto Insurance', 'Clothing', 'Coffee Shops', 'Doctor / Co-pays', 'Electric', 'Gasoline / Diesel',
                         'Gifts', 'Groceries', 'Gym / Fitness', 'Household Supplies', 'Internet', 'Pet Food / Supplies',
                         'Phone / Cell', 'Rent / Mortgage', 'Restaurants', 'Streaming Music', 'Streaming Video'],
          'accounts': ['Cashback Visa', 'Everyday Checking', 'High-Yield Savings'],
          'debts': ['Cashback Visa', 'Riverside Auto loan', 'Student loan']}


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    import importlib.util
    from core import engine, report_index as ri
    root = Path(__file__).resolve().parent.parent
    spec = importlib.util.spec_from_file_location('rr_measure', root / 'scripts' / 'report_requests_measure.py')
    measure = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(measure)

    today = date(2026, 10, 31)          # the day Rob's 25 were written against
    reader = type('R', (), {'today': today})()
    real_names, calls = ri.record_names, []
    real_pick, real_json = engine.pick_label, engine.complete_json
    ri.record_names = lambda r: {k: list(v) for k, v in SAMPLE.items()}
    engine.pick_label = lambda *a, **k: calls.append(1)
    engine.complete_json = lambda *a, **k: calls.append(1) or {'ok': False}
    try:
        sets = {}
        for name, f in (('rob', 'report_requests.json'), ('held_out', 'report_requests_heldout.json')):
            got = []
            for q in json.loads((root / 'tests' / f).read_text())['requests']:
                r = ri.read(reader, q['ask'])
                got.append((q, r, measure.score(r, q['expect'], today)))
            sets[name] = got
        rob, held = sets['rob'], sets['held_out']
        check("s276 P3-P6 the index alone reads Rob's 25: every outcome and section right, no model call",
              all(s['outcome_ok'] and s['sections_ok'] for _, _, s in rob) and not calls)
        check('s276 P3-P6 the 25 held out (written before they were run): every one right',
              all(s['outcome_ok'] and s['sections_ok'] for _, _, s in held))
        check('s276 section 6 no wrong section built by the index alone - a doubt asks',
              not any(s['wrong_section_built'] for _, _, s in rob + held))
        check('s276 P15 style terms read: as a table, out loud, for printing, compact',
              [r['style'] for q, r, _ in held if q['id'] in ('H11', 'H12', 'H13', 'H14')]
              == ['text_grid', 'text_only', 'print', 'compact'])
        r24 = next(r for q, r, _ in rob if q['id'] == 'R24')
        check('s276 P6 a request to act is never done: it says so and builds what it can show',
              r24['outcome'] == 'refuse_act' and r24['sections'] and 'never sends anything' in r24['said'][0])
        r12 = next(r for q, r, _ in rob if q['id'] == 'R12')
        check('s276 G4 "lately" asks the period, and each answer is the same sections with a period Groundwork reads',
              r12['outcome'] == 'clarify' and r12['question'] == 'Over what period?'
              and r12['choices'][0]['sections'][0]['settings'] == {'account': 'Cashback Visa', 'period': 'last month'})
        dog = ri.read(reader, 'What did the dog cost us this year?')
        check('s276 a word nothing read is asked about, never dropped into all spending in silence',
              dog['outcome'] == 'clarify' and 'dog' in dog['question'] and not dog['sections']
              and dog['choices'][-1]['label'] == 'All spending')

        # the helpers, with a stand-in for phi: what it answers is checked by code
        def says(answer):
            return lambda system, question, labels: answer if answer in labels else None
        a = ri.read(reader, 'Show me my payments from last month.', helper=says('Bills that recur'))
        check('s276 H-a advises only: its reading is offered first, marked likely, and the person chooses',
              a['outcome'] == 'clarify' and a['choices'][0]['label'] == 'Bills that recur' and a['choices'][0].get('likely')
              and not a['sections'])
        b = ri.read(reader, 'What did the dog cost us this year?', helper=says('Pet Food / Supplies'))
        check('s276 H-b advises only: the category it names is first, the person chooses',
              b['outcome'] == 'clarify' and b['choices'][0]['label'] == 'Pet Food / Supplies' and b['choices'][0].get('likely'))
        off = ri.read(reader, 'What did the dog cost us this year?', helper=says('Pet Food / Supplies; DROP TABLE'))
        check('s276 P8 an answer that is not on the list is refused, never salvaged',
              off['outcome'] == 'clarify' and not any(ch.get('likely') for ch in off['choices']))
        cc = ri.read(reader, 'Spending last month except the stuff for the dog', helper=says('Pet Food / Supplies'))
        check('s276 H-c builds on its pick and says it; the name is the record\'s',
              cc['outcome'] == 'build_and_say' and cc['sections'][0]['settings'].get('exclude') == ['Pet Food / Supplies']
              and any('Pet Food / Supplies' in x for x in cc['said']))
        none = ri.read(reader, 'Spending last month except the unicorn rides', helper=says(ri.CANT_TELL))
        check('s276 H-c "can\'t tell" leaves nothing out, and says so',
              none['outcome'] == 'build_and_say' and 'exclude' not in none['sections'][0]['settings']
              and any('nothing is left out' in x for x in none['said']))
        check('s276 P8 the grammar allows only the labels, quotes in a name escaped',
              engine.label_grammar(['Groceries', 'Ava "the niece"']) == 'root ::= "Groceries" | "Ava \\"the niece\\""')
        sug = ri.suggest_terms(reader, [{'said': 'What did the dog cost us this year?', 'picked': 'Pet Food / Supplies'},
                                        {'said': "How much did the kids' piano lessons cost?", 'picked': 'All spending'}],
                               says('Pet Food / Supplies'))
        check('s276 H-d suggests a word for a name of the record; not for words the person said name nothing',
              sug == [{'said': 'dog', 'kind': 'category', 'means': 'Pet Food / Supplies'}])
        mine = ri.read(reader, 'What did the dog cost us this year?', terms={'dog': {'kind': 'category', 'means': 'Pet Food / Supplies'}})
        check('s276 C4 a word the person accepted is read as theirs, with no model call',
              mine['outcome'] == 'build' and mine['sections'][0]['settings'].get('category') == 'Pet Food / Supplies')
    finally:
        ri.record_names, engine.pick_label, engine.complete_json = real_names, real_pick, real_json

    # the routes: AI off here, so no helper; a miss kept on this computer with what was picked, cleared on the word
    c.post('/api/reports/builder/misses/clear', headers=HJ)
    r = c.post('/api/reports/builder/ask', headers=HJ, data=json.dumps({'text': 'Show me my payments from last month.'}))
    d = r.get_json()['data']
    c.post('/api/reports/builder/ask/picked', headers=HJ, data=json.dumps({'miss': d.get('miss'), 'picked': 'Debt payments'}))
    m = c.get('/api/reports/builder/misses', headers=H).get_json()['data']['misses']
    check('s276 P6.4 a request it had to ask about is kept here, with what the person picked',
          r.status_code == 200 and d['outcome'] == 'clarify' and m and m[-1]['said'] == 'Show me my payments from last month.'
          and m[-1]['picked'] == 'Debt payments')
    built = c.post('/api/reports/builder/ask', headers=HJ, data=json.dumps({'text': 'Debt payments each month this year'})).get_json()['data']
    m2 = c.get('/api/reports/builder/misses', headers=H).get_json()['data']['misses']
    check('s276 P6.4 a request the index built alone is not kept', built['outcome'] == 'build' and 'miss' not in built
          and len(m2) == len(m))
    c.post('/api/reports/builder/misses/clear', headers=HJ)
    check('s276 the person clears the list', c.get('/api/reports/builder/misses', headers=H).get_json()['data']['misses'] == [])
    s = c.post('/api/reports/builder/terms/suggest', headers=HJ)
    bad = c.post('/api/reports/builder/terms', headers=HJ, data=json.dumps({'said': 'dog', 'kind': 'category', 'means': 'Narnia'}))
    check('s276 P9 suggestions are AI help (refused with AI off); a word for a name the record lacks is not kept',
          s.status_code == 409 and bad.status_code == 400)

    js = ctx.app_src
    check('s276 Build a report has the Ask box, the question buttons, "likely", the kept list and Yes / No for a word',
          '_rbAskBox()' in js and "'/api/reports/builder/ask'" in js and '(likely)' in js
          and "'/api/reports/builder/misses/clear'" in js and '_rbTermYes' in js and '_rbTermNo' in js)
