"""Item 83 (gw 2.0/RECORD_TIDY.md; Rob 2026-10-13: "Yes i agree and accept item 83"): the agent keeps the record tidy.

    T1  empty categories offered to hide - hidden, never deleted; back on a tap, and offered back if used again
    T2  an empty, non-built-in twin offered to merge into the one used; a budget line it held is added into the
        target's line, so the total never changes
    T3  a merchant in several categories is asked about, never merged; an answer can move them and add an import rule
    T4  an imported name matched exactly, then as a near-twin (Quicken Parent:Child both ways), else kept to ask
    every tap has Undo; nothing runs on its own
"""
import json
from datetime import date


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    from core import record_tidy as rt
    from core.database import AppSetting, BudgetItem, Category, Transaction, db_session

    check('s223 twins: the same name in another form, and never two different things that share a word',
          rt.twin('Restaurant', 'Restaurants') and rt.twin('Hobby', 'Hobbies') and rt.twin('Fastfood', 'Fast Food / Takeout')
          and rt.twin('Interest', 'Interest / Fees') and rt.twin('Insurance:Auto', 'Auto Insurance')
          and not rt.twin('Streaming Music', 'Streaming Video') and not rt.twin('Health Insurance', 'Healthcare')
          and not rt.twin('Personal', 'Personal Care') and not rt.twin('Gas', 'Gas / Fuel') and not rt.twin('Home', 'Home Improvement'))
    own = ['Restaurants', 'Gas / Fuel', 'Auto Insurance', 'Groceries']
    check('s223 T4 an imported Quicken name finds the person\'s own: whole, child, then parent; nothing when it means none',
          rt.near_twin('Dining:Restaurant', own) == 'Restaurants' and rt.near_twin('Insurance:Auto', own) == 'Auto Insurance'
          and rt.near_twin('Auto:Fuel', own) == 'Gas / Fuel' and rt.near_twin('Groceries', own) == 'Groceries'
          and rt.near_twin('Auto:Service', own) is None)

    data = lambda r: (r.get_json() or {}).get('data') or {}
    post = lambda p, b: c.post(p, headers=HJ, data=json.dumps(b))
    with db_session() as s:
        for k in ('tidy_answers_json', 'tidy_last', 'import_unmatched_json', 'category_aliases_json'):
            s.query(AppSetting).filter_by(key=k).delete()
        used = Category(name='S223 Snacks'); twin_src = Category(name='S223 Snack')
        empty = Category(name='S223 Never Used'); a = Category(name='S223 Hardware'); b = Category(name='S223 Garden')
        s.add_all([used, twin_src, empty, a, b]); s.flush()
        ids = {x.name: x.id for x in (used, twin_src, empty, a, b)}
        for k in range(3):
            s.add(Transaction(date=date(2026, 3, 1 + k), amount=5, type='debit', merchant='S223 SNACKBAR', description='x', category_id=used.id))
        for cid in (a.id, a.id, b.id):
            s.add(Transaction(date=date(2026, 4, 2), amount=20, type='debit', merchant='S223 HOME STORE', description='y', category_id=cid))
        main = BudgetItem(name='S223 Snacks', category='S223 Snacks', amount=100.0, type='expense', is_active=True)
        small = BudgetItem(name='S223 Snack', category='S223 Snack', amount=7.0, type='expense', is_active=True)
        s.add_all([main, small]); s.commit()
        main_id = main.id
    try:
        st = data(c.get('/api/tidy', headers=H))
        tw = next((t for t in st['twins'] if t['source']['name'] == 'S223 Snack'), None)
        check(f"s223 T1/T2 proposed, shown first: the empty one to hide, the twin with its budget line added into the main line ({tw and tw['target_line']})",
              any(h['name'] == 'S223 Never Used' for h in st['hide']) and tw and tw['target']['name'] == 'S223 Snacks'
              and tw['line']['amount'] == 7.0 and tw['target_line']['amount'] == 100.0
              and not any(h['name'] in ('S223 Snacks', 'S223 Snack') for h in st['hide']))
        with db_session() as s:
            total0 = round(sum(x.amount or 0 for x in s.query(BudgetItem).filter_by(is_active=True, type='expense').all()), 2)
        m = post('/api/tidy/twin', {'source_id': ids['S223 Snack'], 'answer': 'yes'})
        with db_session() as s:
            gone = s.get(Category, ids['S223 Snack']) is None
            total1 = round(sum(x.amount or 0 for x in s.query(BudgetItem).filter_by(is_active=True, type='expense').all()), 2)
            main_amt = s.get(BudgetItem, main_id).amount
        u = post('/api/tidy/undo', {})
        with db_session() as s:
            back = s.query(Category).filter_by(name='S223 Snack').first() is not None
            line_back = s.query(BudgetItem).filter_by(name='S223 Snack').first()
            main_back = s.get(BudgetItem, main_id).amount
        check(f's223 T2 the merge keeps the total budget the same ({total0} -> {total1}), and Undo brings the category and its line back',
              m.status_code == 200 and gone and main_amt == 107.0 and total1 == total0 and u.status_code == 200
              and back and line_back and line_back.amount == 7.0 and main_back == 100.0)

        h = post('/api/tidy/hide', {'ids': [ids['S223 Never Used'], ids['S223 Snacks']]})
        with db_session() as s:
            hidden = s.get(Category, ids['S223 Never Used']).is_enabled
            kept = s.get(Category, ids['S223 Snacks']).is_enabled
        post('/api/tidy/undo', {})
        with db_session() as s:
            shown = s.get(Category, ids['S223 Never Used']).is_enabled
        check('s223 T1 hiding takes only what is still empty (re-checked on the server), never deletes, and Undo shows it again',
              h.status_code == 200 and hidden is False and kept is not False and shown is True)

        sp = next((x for x in data(c.get('/api/tidy', headers=H))['splits'] if x['merchant'] == 'S223 HOME STORE'), None)
        mv = post('/api/tidy/split', {'merchant': 'S223 HOME STORE', 'answer': 'move', 'category': 'S223 Hardware'})
        bad = post('/api/tidy/split', {'merchant': 'S223 HOME STORE', 'answer': 'move', 'category': 'Groceries'})
        with db_session() as s:
            now = {t.category_id for t in s.query(Transaction).filter_by(merchant='S223 HOME STORE').all()}
            rules = json.loads(s.query(AppSetting).filter_by(key='import_rules_json').first().value)
        post('/api/tidy/undo', {})
        with db_session() as s:
            after = sorted(t.category_id for t in s.query(Transaction).filter_by(merchant='S223 HOME STORE').all())
            rules2 = json.loads(s.query(AppSetting).filter_by(key='import_rules_json').first().value)
        check('s223 T3 a split merchant is asked; "all in one" moves them and adds an import rule, only to a category it is already in; Undo puts both back',
              sp and len(sp['categories']) == 2 and mv.status_code == 200 and now == {ids['S223 Hardware']}
              and any(r.get('value') == 'S223 HOME STORE' and r.get('category') == 'S223 Hardware' for r in rules)
              and bad.status_code == 404 and after == sorted([ids['S223 Hardware'], ids['S223 Hardware'], ids['S223 Garden']])
              and not any(r.get('value') == 'S223 HOME STORE' for r in rules2))
        keep = post('/api/tidy/split', {'merchant': 'S223 HOME STORE', 'answer': 'keep'})
        again = [x for x in data(c.get('/api/tidy', headers=H))['splits'] if x['merchant'] == 'S223 HOME STORE']
        check('s223 T3 "keep as they are" is kept, and the merchant is not asked about again', keep.status_code == 200 and not again)

        imp = c.post('/api/import/commit', headers=HJ, data=json.dumps({'account_name': 'S223 Import', 'source': 'qif', 'records': [
            {'date': '2026-05-01', 'amount': 12.5, 'description': 'S223 DINER', 'type': 'debit', 'category': 'Dining:S223 Snack'},
            {'date': '2026-05-02', 'amount': 40.0, 'description': 'S223 MECHANIC', 'type': 'debit', 'category': 'Auto:S223 Service Odd'}]}))
        with db_session() as s:
            diner = s.query(Transaction).filter_by(description='S223 DINER').first()
            mech = s.query(Transaction).filter_by(description='S223 MECHANIC').first()
            other = s.query(Category).filter(Category.name.ilike('other')).first()
            snack_id = s.query(Category).filter_by(name='S223 Snack').first().id
        un = data(c.get('/api/tidy', headers=H))['unmatched']
        mine = next((x for x in un if x['name'] == 'Auto:S223 Service Odd'), None)
        ans = post('/api/tidy/unmatched', {'name': 'Auto:S223 Service Odd', 'answer': 'move', 'category': 'S223 Garden'})
        with db_session() as s:
            mech2 = s.get(Transaction, mech.id).category_id
            alias = json.loads(s.query(AppSetting).filter_by(key='category_aliases_json').first().value)
        check(f's223 T4 an import matches a Quicken name to the person\'s own; one that matches nothing lands in Other and is kept to ask; the answer moves it and is remembered ({imp.status_code})',
              imp.status_code in (200, 201) and diner.category_id == snack_id and other and mech.category_id == other.id
              and mine and mech.id in mine['ids'] and ans.status_code == 200 and mech2 == ids['S223 Garden']
              and alias.get('auto:s223 service odd') == 'S223 Garden')

        app = ctx.app_src
        page = app.split('async function renderRecordTidy() {')[1].split('\n}\n')[0]
        check('s223 the card sits on Settings, Categories: each proposal shown first, a choice for each, Undo, nothing automatic',
              'id="recordTidy"' in ctx.html_src and "if (tab === 'categories') renderRecordTidy();" in app
              and 'Nothing changes until you choose' in page and 'Undo the last change' in page
              and "They're different" in page and 'Keep as they are' in page and 'Leave in Other' in page
              and '_offerRecordTidy();    // item 83 T5' in app and 'callAI' not in page)
    finally:
        with db_session() as s:
            s.query(Transaction).filter(Transaction.merchant.in_(['S223 SNACKBAR', 'S223 HOME STORE'])).delete(synchronize_session=False)
            s.query(Transaction).filter(Transaction.description.in_(['S223 DINER', 'S223 MECHANIC'])).delete(synchronize_session=False)
            s.query(BudgetItem).filter(BudgetItem.name.like('S223%')).delete(synchronize_session=False)
            s.query(Category).filter(Category.name.like('S223%')).delete(synchronize_session=False)
            for k in ('tidy_answers_json', 'tidy_last', 'import_unmatched_json', 'category_aliases_json'):
                s.query(AppSetting).filter_by(key=k).delete()
            rules = s.query(AppSetting).filter_by(key='import_rules_json').first()
            if rules and rules.value:
                rules.value = json.dumps([r for r in json.loads(rules.value) if not str(r.get('value', '')).startswith('S223')])
            s.commit()
