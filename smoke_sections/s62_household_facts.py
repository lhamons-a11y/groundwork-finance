"""Household facts on 1.x: one canonical value each, with append-only history (ONBOARDING_REVISIT.md, item 30).

1.x asks only the facts it has readers for (O9): home_state (the Budget page's EIA benchmarks), pay_frequency (the
cash-flow and payday views) and surplus_goal (the onboarding summary). The same model, write path and invariant as
2.0 (s139 there). Rob, 2026-10-02: the latest history row is authoritative; set_household_fact() appends the history
row and updates the current value together; a withdrawal is a row with no value, and the fact is then unanswered.
"""
import json


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    from sqlalchemy import text, inspect
    import migrate
    from core import household
    from core.database import engine, AppSetting, HouseholdFact

    def data_of(resp):
        body = resp.get_json() or {}
        return body.get('data') if 'data' in body else body

    def rows(s, key):
        return s.query(HouseholdFact).filter_by(key=key).order_by(HouseholdFact.id).all()

    def clean(s):
        for k in household.FACTS:
            s.query(HouseholdFact).filter_by(key=k).delete()
            s.query(AppSetting).filter_by(key=k).delete()
        s.commit()

    cols = {col['name'] for col in inspect(engine).get_columns('household_facts')}
    check("s62 the household_facts table exists, and it is the household's: no user or person column",
          {'key', 'value', 'answered_at', 'source'} <= cols and not any('user' in x or 'person' in x for x in cols))
    check('s62 1.x has only the facts it has readers for (O9): no home, heating or vehicle facts',
          set(household.FACTS) == {'home_state', 'pay_frequency', 'surplus_goal'})

    with ctx.dbs() as s:
        clean(s)
        wrote = household.set_household_fact(s, 'pay_frequency', 'weekly', 'onboarding')
        s.commit()
        r = rows(s, 'pay_frequency')
        check('s62 one call writes the history row and the current value together',
              wrote and len(r) == 1 and r[0].value == 'weekly' and r[0].source == 'onboarding'
              and r[0].answered_at is not None and household.current(s, 'pay_frequency') == 'weekly')
        check('s62 the same answer again records nothing (nothing changed)',
              household.set_household_fact(s, 'pay_frequency', 'weekly', 'settings') is False and len(rows(s, 'pay_frequency')) == 1)
        household.set_household_fact(s, 'pay_frequency', 'monthly', 'settings')
        household.set_household_fact(s, 'pay_frequency', None, 'inline_prompt')
        s.commit()
        r = rows(s, 'pay_frequency')
        check('s62 a change is a NEW row, and a withdrawal is a row with no value - the history keeps every answer',
              [x.value for x in r] == ['weekly', 'monthly', None] and [x.source for x in r] == ['onboarding', 'settings', 'inline_prompt'])
        check('s62 after a withdrawal the fact is unanswered: no current value',
              household.current(s, 'pay_frequency') is None and s.query(AppSetting).filter_by(key='pay_frequency').first() is None)
        household.set_household_fact(s, 'surplus_goal', 'unsure', 'onboarding')
        s.commit()
        check('s62 an explicit "not sure" is an answer, never collapsed into unanswered',
              household.current(s, 'surplus_goal') == 'unsure' and household.current(s, 'home_state') is None)
        refused = []
        for args in (('heating_fuel', 'propane', 'settings'), ('pay_frequency', 'hourly', 'settings'),
                     ('home_state', 'XX', 'settings'), ('pay_frequency', 'weekly', 'a_guess')):
            try:
                household.set_household_fact(s, *args)
            except household.FactError:
                refused.append(args)
        s.rollback()
        check('s62 an unknown fact (a 2.0 one included), answer or source is refused, and nothing is written',
              len(refused) == 4 and household.current(s, 'pay_frequency') is None and len(rows(s, 'pay_frequency')) == 3)

    r = c.patch('/api/settings', headers=HJ, data=json.dumps({'home_state': 'OH', 'savings_pct': '7'}))
    with ctx.dbs() as s:
        hist = rows(s, 'home_state')
        check('s62 PATCH /api/settings sends a household fact through the one write path (source "settings")',
              r.status_code == 200 and len(hist) == 1 and hist[0].value == 'OH' and hist[0].source == 'settings')
    r = c.patch('/api/settings', headers=HJ, data=json.dumps({'home_state': 'ZZ', 'savings_pct': '9'}))
    with ctx.dbs() as s:
        sp = s.query(AppSetting).filter_by(key='savings_pct').first()
        check('s62 an unknown answer through Settings is refused, and nothing else in that request is saved',
              r.status_code == 400 and household.current(s, 'home_state') == 'OH' and sp is not None and sp.value == '7')
    r = c.patch('/api/settings', headers=HJ, data=json.dumps({'home_state': ''}))
    with ctx.dbs() as s:
        check('s62 an empty state from Settings withdraws it: unanswered, with the history kept',
              r.status_code == 200 and household.current(s, 'home_state') is None
              and [x.value for x in rows(s, 'home_state')] == ['OH', None])
    r = c.post('/api/settings/household', headers=HJ, data=json.dumps({'key': 'pay_frequency', 'value': 'biweekly',
                                                                       'source': 'onboarding'}))
    check('s62 POST /api/settings/household sets a fact from onboarding, with its source',
          r.status_code == 200 and data_of(r).get('value') == 'biweekly' and data_of(r).get('changed') is True)
    check("s62 the page cannot claim a carried-over answer (that source is the migration's alone)",
          c.post('/api/settings/household', headers=HJ, data=json.dumps(
              {'key': 'pay_frequency', 'value': 'weekly', 'source': 'carried_over'})).status_code == 400)
    d = data_of(c.get('/api/settings/household?history=1', headers=H))
    check('s62 GET /api/settings/household: each fact with its question, its answers, its value and its history',
          d['pay_frequency']['value'] == 'biweekly' and [x['value'] for x in d['home_state']['history']] == ['OH', None]
          and 'heating_fuel' not in d)

    with ctx.dbs() as s:
        check("s62 INVARIANT: every fact's current value equals its latest history row", household.inconsistencies(s) == [])
        s.query(AppSetting).filter_by(key='surplus_goal').delete()
        s.add(AppSetting(key='surplus_goal', value='invest'))       # a write that bypassed the one path
        s.flush()
        caught_bypass = any(k == 'surplus_goal' for k, *_ in household.inconsistencies(s))
        s.rollback()
        last = household.latest(s, 'pay_frequency')
        last.value = 'monthly'                                       # history edited behind the current value
        s.flush()
        caught_edit = any(k == 'pay_frequency' for k, *_ in household.inconsistencies(s))
        s.rollback()
        check('s62 mutation caught: a current value written around the one path', caught_bypass)
        check('s62 mutation caught: a history row edited so it no longer matches the current value', caught_edit)

    with ctx.dbs() as s:
        clean(s)
        s.add(AppSetting(key='surplus_goal', value='savings'))      # answered before history existed
        s.commit()
        n = household.carry_over(s)
        s.commit()
        r = rows(s, 'surplus_goal')
        check('s62 an answer given before history existed is carried over once, with no invented date',
              n == 1 and len(r) == 1 and r[0].source == 'carried_over' and r[0].answered_at is None
              and household.carry_over(s) == 0 and household.inconsistencies(s) == [])

    with engine.begin() as conn:
        conn.execute(text('DROP TABLE IF EXISTS household_facts'))
        conn.execute(text("UPDATE app_settings SET value = '20260927-lts-cloud-ai-removed' WHERE key = 'schema_version'"))
        conn.execute(text("INSERT INTO app_settings (key, value) VALUES ('home_state', 'AZ')"))
    migrate.run_migration_if_needed()
    with ctx.dbs() as s:
        ver = s.query(AppSetting).filter_by(key='schema_version').first().value
        r = rows(s, 'home_state')
        check('s62 a database at the previous SCHEMA_VERSION gains household_facts on start, and its existing answers '
              'are carried over (a new table: s51 cannot see a forgotten bump, so this proves it)',
              ver == migrate.SCHEMA_VERSION and len(r) == 1 and r[0].value == 'AZ' and r[0].source == 'carried_over'
              and household.inconsistencies(s) == [])
        clean(s)
