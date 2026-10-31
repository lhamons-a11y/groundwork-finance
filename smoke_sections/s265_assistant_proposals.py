"""Item 114 stage 2, H7 (gw 2.0/AGENT_HANDS.md; Rob 2026-10-30: "yes" to stage 2): the assistant proposes a change to
the record; only the person's Yes makes it, and Undo puts it back.

    H7   a card states exactly what would change; Yes applies it by the card's one-time ticket; Undo puts it back
    H7   checked against the record: a category must exist (nothing is created); an amount must be one the person said
    H8   moving money, deleting or a setting is refused, never proposed
    P3   provision 3 as amended: no writing without the person's Yes - the assistant's module writes only a name the
         person confirmed (R17); every change goes through /proposal/yes
"""
import json
import time


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    from core import engine
    from core.database import db_session, Transaction, Category, BudgetItem

    def fake(system, user, schema, max_tokens=300):
        return {'ok': True, 'text': json.dumps({'facts': [], 'lead': '', 'close': ''} if 'facts' in (schema.get('properties') or {})
                                               else {'lookups': [], 'kind': 'about_my_record'})}

    def data(r):
        d = r.get_json(silent=True) or {}
        return d.get('data', d)

    def ask(q):
        r = c.post('/api/assistant/ask', headers=HJ, data=json.dumps({'question': q}))
        job = data(r)['job']
        for _ in range(300):
            d = data(c.get(f'/api/assistant/job/{job}', headers=H))
            if d['done']:
                return d['result']
            time.sleep(0.02)

    # A payee of our own, filed under one category, to move to another
    with db_session() as s:
        a = s.query(Category).filter(Category.name == 'Groceries').first()
        b = s.query(Category).filter(Category.name == 'Restaurants').first()
        ga, gb = (a.id if a else None), (b.id if b else None)
    acct = data(c.post('/api/accounts', headers=HJ, data=json.dumps({'name': 's265 Checking', 'type': 'checking'})))['id']
    for i, d in enumerate(('2026-08-04', '2026-09-04', '2026-10-04')):
        c.post('/api/transactions', headers=HJ, data=json.dumps({'date': d, 'description': 'S265 SNACKBAR', 'merchant': 's265 Snackbar',
                                                                 'amount': 12.5 + i, 'type': 'debit', 'category': 'Groceries',
                                                                 'source': 'csv', 'account_id': acct}))

    real = engine.complete_json
    engine.complete_json = fake
    c.patch('/api/settings', headers=HJ, data=json.dumps({'ai_enabled': 'true'}))
    try:
        r = ask('File the s265 Snackbar charges under Restaurants')
        pr = r.get('proposal') or {}
        with db_session() as s:
            still = [t.category_id for t in s.query(Transaction).filter(Transaction.merchant == 's265 Snackbar').all()]
        check('s265 H7 a change is proposed - stated exactly, nothing changed until Yes',
              r['outcome'] == 'propose' and pr.get('ticket') and 'File 3 transactions from s265 Snackbar under Restaurants?' in pr['sentences']
              and still == [ga, ga, ga])
        forged = c.post('/api/assistant/proposal/yes', headers=HJ, data=json.dumps({'ticket': 'not-a-ticket'}))
        y = c.post('/api/assistant/proposal/yes', headers=HJ, data=json.dumps({'ticket': pr['ticket']}))
        again = c.post('/api/assistant/proposal/yes', headers=HJ, data=json.dumps({'ticket': pr['ticket']}))
        with db_session() as s:
            moved = [t.category_id for t in s.query(Transaction).filter(Transaction.merchant == 's265 Snackbar').all()]
        check('s265 H7 only a ticket a card holds applies a change, once', forged.status_code == 404 and y.status_code == 200
              and again.status_code == 404 and moved == [gb, gb, gb])
        u = c.post('/api/assistant/proposal/undo', headers=HJ, data=json.dumps({'undo': data(y)['undo']}))
        with db_session() as s:
            back = [t.category_id for t in s.query(Transaction).filter(Transaction.merchant == 's265 Snackbar').all()]
        check('s265 H7 Undo puts back exactly what the Yes changed', u.status_code == 200 and back == [ga, ga, ga])

        # a budget line: the amount must be one the person said; the line's change and its Undo
        with db_session() as s:
            line = s.query(BudgetItem).filter(BudgetItem.category == 'Restaurants', BudgetItem.is_active.is_(True)).first()
            before = line.amount if line else None
        if line is not None:
            r = ask('Change the Restaurants budget to $351')
            y = c.post('/api/assistant/proposal/yes', headers=HJ, data=json.dumps({'ticket': r['proposal']['ticket']}))
            with db_session() as s:
                mid = s.get(BudgetItem, line.id).amount
            c.post('/api/assistant/proposal/undo', headers=HJ, data=json.dumps({'undo': data(y)['undo']}))
            with db_session() as s:
                after = s.get(BudgetItem, line.id).amount
            check('s265 H7 a budget line changed to the amount the person said, and put back on Undo',
                  r['proposal']['sentences'][0].endswith('to $351.00 a month?') and mid == 351 and after == before)

        n_cats = None
        with db_session() as s:
            n_cats = s.query(Category).count()
        r = ask('File the s265 Snackbar charges under Moon Rocks')
        with db_session() as s:
            n_after = s.query(Category).count()
        check('s265 H7 a category that is not there is said, never created', not r.get('proposal')
              and 'no category called "Moon Rocks"' in r['shown'][0] and n_after == n_cats)

        for q in ('Move $200 from savings to the Visa', 'Delete the s265 Snackbar transactions', 'Turn off the AI'):
            r = ask(q)
            check(f's265 H8 "{q}" is refused, never proposed', r['outcome'] == 'refuse' and not r.get('proposal'))
    finally:
        engine.complete_json = real
        c.patch('/api/settings', headers=HJ, data=json.dumps({'ai_enabled': 'false'}))
        with db_session() as s:
            s.query(Transaction).filter(Transaction.merchant == 's265 Snackbar').delete()
            s.commit()

    # Provision 3, as amended: the assistant's module writes only a name the person confirmed; changes go through Yes
    import ast
    src = (ctx.BASE / 'core' / 'agent_hands.py').read_text(encoding='utf-8')
    writers = sorted({n.name for n in ast.walk(ast.parse(src)) if isinstance(n, ast.FunctionDef)
                      and any(isinstance(x, ast.Attribute) and x.attr in ('commit', 'add', 'delete', 'flush', 'merge')
                              and isinstance(x.value, ast.Name) and x.value.id in ('s', 'session', 'db')   # a database session
                              for x in ast.walk(n))})
    check(f's265 P3 the assistant\'s module writes only a confirmed name ({writers})', writers == ['confirm_name'])
    srv = ctx.server_src
    check('s265 P3 every change the assistant can make is applied only in /proposal/yes, by ticket',
          srv.count('= _assistant_apply(session') == 1 and "pr = _ASSIST_PROPOSALS.pop(tk, None)" in srv
          and srv.split('= _assistant_apply(session', 1)[0].rsplit('\ndef ', 1)[1].startswith('assistant_proposal_yes('))
