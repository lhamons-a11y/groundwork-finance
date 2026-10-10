"""Item 23's remaining slices (gw 2.0/WILLINGNESS_LAYER.md, ruled 2026-09-27; Rob 2026-10-10: "finish building
the entire thing").

    W-D  the contradiction-check (E.2b): a statement against the user's own LATER budget edits, read as E.2 reads
         them; asked ("which do you mean?"), never applied; answering again is a newer statement; in the A.2
         gauntlet as a clarification from the brake budget, disputing its category
    W-E  strategy inference (F.6b): trim or reallocation after a short month, attributed only when it predicts
         held-out short months better than chance; doing nothing is not an event; the null model holds (W4:
         trend-free histories almost never labelled); E.3 rule 4 only; the user can set it aside
"""
import json
import random


def run(ctx):
    check, c, H, HJ, BASE = ctx.check, ctx.c, ctx.H, ctx.HJ, ctx.BASE
    from core import willingness as w
    from core import proactive, solution

    # ── W-D ──
    income = {m: 5000.0 for m in ('2026-02', '2026-03', '2026-04', '2026-05', '2026-06', '2026-07')}
    months = {'2026-02', '2026-03', '2026-04', '2026-05', '2026-06', '2026-07'}
    spend = {('Dining', m): 180.0 for m in months}
    said = {'id': 1, 'category': 'Dining', 'stance': 'protect', 'answer_kind': 'claim', 'answer_text': '', 'said_at': '2026-03-03T10:00:00'}
    cut = {'id': 11, 'date': '2026-04-02', 'category': 'Dining', 'old': 300.0, 'new': 200.0}
    found = w.contradictions([said], [cut], spend, months, income)
    check('s181 W-D "protect" against a cut made since, that held: asked, with the statement and the edit side by side',
          len(found) == 1 and found[0]['category'] == 'Dining' and found[0]['declaration'] == said
          and found[0]['reading']['reason'] == 'cut_held' and found[0]['dollars'] == 100.0)
    check('s181 W-D the statement itself is untouched - your word stands until you change it',
          w.current_declarations([said])['dining']['stance'] == 'protect'
          and w.effective([], [said])['dining']['stance'] == 'protected')
    before = dict(cut, id=10, date='2026-02-10')
    check('s181 W-D only edits made after the statement count against it (what came before is what it answered)',
          w.contradictions([said], [before], spend, months, income) == [])
    again = dict(said, id=2, said_at='2026-07-15T09:00:00')
    check('s181 W-D answering again is a newer statement, and the earlier edits no longer count against it',
          w.contradictions([said, again], [cut], spend, months, income) == [])
    flex = dict(said, stance='flexible')
    restore = {'id': 12, 'date': '2026-05-20', 'category': 'Dining', 'old': 200.0, 'new': 300.0}
    found = w.contradictions([flex], [cut, restore], spend, months, income)
    check('s181 W-D "flexible" against a cut made since and then put back: asked too',
          len(found) == 1 and found[0]['reading']['reason'] == 'restored')
    check('s181 W-D a statement the record agrees with raises nothing',
          w.contradictions([flex], [cut], spend, months, income) == [])
    cand = {'key': 'contradiction:dining:1:11', 'kind': 'clarification', 'category': 'Dining', 'dollars': 100.0,
            'has_path': True, 'disputes': 'Dining'}
    v = proactive.verdict(cand, {'monthly_budget': 1000})
    check('s181 W-D in the gauntlet: a clarification spends from the brake budget and must still be material',
          proactive.budget_class('clarification') == 'brake' and v['budget'] == 'brake' and v['promote'] is True
          and proactive.verdict(dict(cand, dollars=20.0), {'monthly_budget': 4000})['gate'] == 'materiality')
    srv = (BASE / 'server.py').read_text(encoding='utf-8')
    block = srv.split("for cx in willingness_state(session)['contradictions']:")[1][:900] if "for cx in willingness_state(session)['contradictions']:" in srv else ''
    check('s181 W-D the proactive candidate disputes its category, so it fires before anything ranked on it',
          "'kind': 'clarification'" in block and "'disputes': cx['category']" in block and "'has_path': True" in block)
    pj = (BASE / 'static/js/teaching/proactive.js').read_text(encoding='utf-8')
    wj = (BASE / 'static/js/teaching/willingness.js').read_text(encoding='utf-8')
    check('s181 W-D it asks which you mean - never why you did not',
          'Which do you mean?' in pj and 'Which do you mean?' in wj and 'nothing has been changed' in wj
          and not any(x in (pj + wj).lower() for x in ("why didn't you", 'why did you', 'you failed', 'you broke')))

    # ── W-E ──
    debits = {f'2025-{m:02d}': 6000.0 for m in range(1, 13)}
    inc = {f'2025-{m:02d}': 5000.0 for m in range(1, 12)}       # December's income not on record
    ed = [{'id': 1, 'date': '2025-02-05', 'category': 'Dining', 'old': 300, 'new': 250},
          {'id': 2, 'date': '2025-03-05', 'category': 'Dining', 'old': 250, 'new': 200},
          {'id': 3, 'date': '2025-03-06', 'category': 'Fun', 'old': 50, 'new': 100},
          {'id': 4, 'date': '2025-04-05', 'category': 'Fun', 'old': 100, 'new': 120}]
    ev = w.shortfall_responses(ed, inc, debits)
    check('s181 W-E a short month answered by a cut is trimming; a cut beside a raise is reallocation; a raise alone or nothing is not an event; a month with no income on record is not short',
          [(e['month'], e['lever']) for e in ev] == [('2025-01', 'trim'), ('2025-02', 'reallocation')])
    trims = [{'month': f'x{i}', 'lever': 'trim'} for i in range(10)]
    st = w.strategy(trims)
    check('s181 W-E a label is earned by prediction: fit on the first half, right on the held-out half, unlikely by chance',
          st['label'] == 'trim' and st['fit'] == 5 and st['test'] == 5 and st['hits'] == 5 and st['p'] < 0.05)
    check('s181 W-E fewer than ten answered short months: unclassified, said as too few',
          w.strategy(trims[:9])['label'] == 'unclassified' and w.strategy(trims[:9])['reason'] == 'too_few')
    alt = [{'month': f'x{i}', 'lever': ('trim' if i % 2 else 'reallocation')} for i in range(12)]
    check('s181 W-E a history that does not predict itself stays unclassified',
          w.strategy(alt)['label'] == 'unclassified')
    rnd = random.Random(23)
    labelled = sum(1 for _ in range(1000)
                   if w.strategy([{'month': str(i), 'lever': rnd.choice(w.STRATEGY_LEVERS)} for i in range(rnd.randint(10, 24))])['label'] != 'unclassified')
    check(f's181 W-E null model (W4): 1,000 trend-free histories, {labelled / 10:.1f}% labelled - nearly all unclassified, as F.6b requires',
          labelled / 1000 <= 0.05)
    habit = sum(1 for _ in range(500)
                if w.strategy([{'month': str(i), 'lever': ('trim' if rnd.random() < 0.9 else 'reallocation')} for i in range(20)])['label'] == 'trim')
    check(f's181 W-E and it still sees a real habit: 90% trimming over 20 short months, {habit / 5:.0f}% labelled', habit / 500 >= 0.6)

    def path(kind, cut):
        return {'kind': kind, 'requires_cut': cut, 'reversible': True, 'closes': True, 'available_in_months': None, 'cost_months': None}
    ps = [path('reallocation', True), path('trim', True), path('timing', False)]
    check('s181 W-E rule 4: with no label the order is exactly E.3\'s; with "trim" earned, trimming comes first among the cuts - and waiting still ranks first',
          solution._rank_key_for(None) is solution._rank_key
          and [p['kind'] for p in sorted(ps, key=solution._rank_key_for('trim'))] == ['timing', 'trim', 'reallocation']
          and [p['kind'] for p in sorted(ps, key=solution._rank_key_for('reallocation'))] == ['timing', 'reallocation', 'trim'])
    check('s181 W-E the solvers take the label from the server only - never from usage',
          srv.count('demonstrated=_demonstrated_lever(session)') == 3
          and "return st['label'] if st['label'] != 'unclassified' and not st.get('set_aside') else None" in srv)

    s = c.get('/api/willingness', headers=H).get_json()['data']
    check('s181 the working picture carries the questions and the strategy reading',
          'contradictions' in s and 'strategy' in s and s['strategy']['label'] in ('unclassified', 'trim', 'reallocation'))
    a = c.post('/api/willingness/strategy', headers=HJ, data=json.dumps({'use': False})).get_json()['data']
    b = c.post('/api/willingness/strategy', headers=HJ, data=json.dumps({'use': True})).get_json()['data']
    bad = c.post('/api/willingness/strategy', headers=HJ, data=json.dumps({'use': 'no'}))
    check('s181 W-E the label can be set aside and used again - the user\'s word, kept with when; the label is never stored',
          a['strategy']['set_aside'] and a['strategy']['set_aside'].get('said') and b['strategy']['set_aside'] is None
          and bad.status_code == 400)
    check('s181 W-E unclassified is said plainly as the usual answer, and an earned label shows its test',
          'That is the usual answer.' in wj and 'it was right' in wj and 'That is not how I work - set it aside' in wj)
