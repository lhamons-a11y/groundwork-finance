"""Household facts: one canonical value each, with append-only history (ONBOARDING_REVISIT.md, item 30, steps 1-3).

Rob, 2026-10-02: the latest history row is authoritative; set_household_fact() appends the history row and updates
the current value together; current_value == latest_history_value for every fact with history; a withdrawal is a
row with no value, and the fact is then unanswered - never "unknown propane".

    the table      household_facts, the household's (no user column); a new table, so the bump is proved here
    the write      one path: history + current together; same answer records nothing; withdrawal is a row
    the states     an answer, an explicit none ('none', 'not_sure'), unanswered - never collapsed
    the routes     PATCH /api/settings and POST /api/settings/household both go through the one path
    the invariant  checked across everything above, and proved able to fail (mutations)
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

    cols = {col['name'] for col in inspect(engine).get_columns('household_facts')}
    check('s139 the household_facts table exists, and it is the household\'s: no user or person column',
          {'key', 'value', 'answered_at', 'source'} <= cols and not any('user' in x or 'person' in x for x in cols))

    with ctx.dbs() as s:
        for k in household.FACTS:                    # start clean for the facts this section uses
            s.query(HouseholdFact).filter_by(key=k).delete()
            s.query(AppSetting).filter_by(key=k).delete()
        s.commit()

        wrote = household.set_household_fact(s, 'heating_fuel', 'propane', 'onboarding')
        s.commit()
        r = rows(s, 'heating_fuel')
        check('s139 one call writes the history row and the current value together',
              wrote and len(r) == 1 and r[0].value == 'propane' and r[0].source == 'onboarding'
              and r[0].answered_at is not None and household.current(s, 'heating_fuel') == 'propane')
        check('s139 the same answer again records nothing (nothing changed)',
              household.set_household_fact(s, 'heating_fuel', 'propane', 'settings') is False
              and len(rows(s, 'heating_fuel')) == 1)
        household.set_household_fact(s, 'heating_fuel', 'natural_gas', 'settings')
        household.set_household_fact(s, 'heating_fuel', None, 'inline_prompt')
        s.commit()
        r = rows(s, 'heating_fuel')
        check('s139 a change is a NEW row, and a withdrawal is a row with no value - the history keeps every answer',
              [x.value for x in r] == ['propane', 'natural_gas', None]
              and [x.source for x in r] == ['onboarding', 'settings', 'inline_prompt'])
        check('s139 after a withdrawal the fact is unanswered: no current value, not an "unknown propane"',
              household.current(s, 'heating_fuel') is None
              and s.query(AppSetting).filter_by(key='heating_fuel').first() is None)
        check('s139 withdrawing what is already unanswered records nothing',
              household.set_household_fact(s, 'heating_fuel', '', 'settings') is False and len(rows(s, 'heating_fuel')) == 3)

        household.set_household_fact(s, 'vehicle_fuel', 'none', 'onboarding')
        household.set_household_fact(s, 'electricity_included', 'not_sure', 'onboarding')
        s.commit()
        check('s139 an explicit "no vehicle" and "not sure" are answers, never collapsed into unanswered',
              household.current(s, 'vehicle_fuel') == 'none' and household.current(s, 'electricity_included') == 'not_sure'
              and household.current(s, 'housing_status') is None)

        refused = []
        for args in (('no_such_fact', 'x', 'settings'), ('heating_fuel', 'coal', 'settings'),
                     ('home_state', 'XX', 'settings'), ('heating_fuel', 'propane', 'a_guess')):
            try:
                household.set_household_fact(s, *args)
            except household.FactError:
                refused.append(args)
        s.rollback()
        check('s139 an unknown fact, answer or source is refused, and nothing is written',
              len(refused) == 4 and household.current(s, 'heating_fuel') is None and len(rows(s, 'heating_fuel')) == 3)

    # ── Through the routes the page uses ─────────────────────────────────────
    r = c.patch('/api/settings', headers=HJ, data=json.dumps({'home_state': 'OH', 'savings_pct': '7'}))
    with ctx.dbs() as s:
        hist = rows(s, 'home_state')
        check('s139 PATCH /api/settings sends a household fact through the one write path (source "settings")',
              r.status_code == 200 and len(hist) == 1 and hist[0].value == 'OH' and hist[0].source == 'settings')
    r = c.patch('/api/settings', headers=HJ, data=json.dumps({'home_state': 'ZZ', 'savings_pct': '9'}))
    with ctx.dbs() as s:
        sp = s.query(AppSetting).filter_by(key='savings_pct').first()
        check('s139 an unknown answer through Settings is refused, and nothing else in that request is saved',
              r.status_code == 400 and household.current(s, 'home_state') == 'OH' and sp is not None and sp.value == '7')
    r = c.patch('/api/settings', headers=HJ, data=json.dumps({'home_state': ''}))
    with ctx.dbs() as s:
        check('s139 an empty state from Settings withdraws it: unanswered, with the history kept',
              r.status_code == 200 and household.current(s, 'home_state') is None
              and [x.value for x in rows(s, 'home_state')] == ['OH', None])

    r = c.post('/api/settings/household', headers=HJ, data=json.dumps({'key': 'housing_status', 'value': 'rent',
                                                                       'source': 'inline_prompt'}))
    check('s139 POST /api/settings/household sets a fact from a page, with its source',
          r.status_code == 200 and data_of(r).get('value') == 'rent' and data_of(r).get('changed') is True)
    check('s139 the page cannot claim a carried-over answer (that source is the migration\'s alone)',
          c.post('/api/settings/household', headers=HJ, data=json.dumps(
              {'key': 'housing_status', 'value': 'own', 'source': 'carried_over'})).status_code == 400)
    d = data_of(c.get('/api/settings/household?history=1', headers=H))
    check('s139 GET /api/settings/household: each fact with its question, its answers, its value and its history',
          d['housing_status']['value'] == 'rent' and 'rent' in d['housing_status']['values']
          and d['home_state']['value'] is None and [x['value'] for x in d['home_state']['history']] == ['OH', None]
          and d['heating_fuel']['asks'] == 'What heats your home?')

    # ── The invariant, and that it can fail ──────────────────────────────────
    with ctx.dbs() as s:
        check('s139 INVARIANT: every fact\'s current value equals its latest history row', household.inconsistencies(s) == [])
        s.add(AppSetting(key='pay_frequency', value='weekly'))     # a write that bypassed the one path
        s.flush()
        caught_bypass = ('pay_frequency', 'weekly', 'no history') in household.inconsistencies(s)
        s.rollback()
        last = household.latest(s, 'housing_status')
        last.value = 'own'                                          # history edited behind the current value
        s.flush()
        caught_edit = any(k == 'housing_status' for k, *_ in household.inconsistencies(s))
        s.rollback()
        check('s139 mutation caught: a current value written around the one path', caught_bypass)
        check('s139 mutation caught: a history row edited so it no longer matches the current value', caught_edit)

    # ── Carry-over and the upgrade (a new table: s51 cannot see a forgotten bump, so this proves it) ──
    with ctx.dbs() as s:
        s.add(AppSetting(key='surplus_goal', value='savings'))     # answered before history existed
        s.commit()
        n = household.carry_over(s)
        s.commit()
        r = rows(s, 'surplus_goal')
        check('s139 an answer given before history existed is carried over once, with no invented date',
              n == 1 and len(r) == 1 and r[0].source == 'carried_over' and r[0].answered_at is None
              and household.carry_over(s) == 0 and household.inconsistencies(s) == [])

    with engine.begin() as conn:
        conn.execute(text('DROP TABLE IF EXISTS household_facts'))
        conn.execute(text("UPDATE app_settings SET value = '20260928-willingness-declarations' WHERE key = 'schema_version'"))
        conn.execute(text("INSERT INTO app_settings (key, value) VALUES ('home_state', 'AZ')"))
    migrate.run_migration_if_needed()
    with ctx.dbs() as s:
        ver = s.query(AppSetting).filter_by(key='schema_version').first().value
        r = rows(s, 'home_state')
        check('s139 a database at the previous SCHEMA_VERSION gains household_facts on start, and its existing '
              'answers are carried over',
              ver == migrate.SCHEMA_VERSION and len(r) == 1 and r[0].value == 'AZ' and r[0].source == 'carried_over'
              and household.inconsistencies(s) == [])
        for k in household.FACTS:                                   # leave nothing behind for later sections
            s.query(HouseholdFact).filter_by(key=k).delete()
            s.query(AppSetting).filter_by(key=k).delete()
        s.commit()
    check('s139 every fact names at least one consumer (the full matrix test is step 8)',
          all(f['consumers'] for f in household.FACTS.values()))
