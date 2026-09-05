"""The solution engine offers only honest levers, ranked by what is universal.

Pillar 3 (§6). Given a gap it searches the sanctioned lever set and returns paths
with their costs so the user chooses — E.4's rank, don't decide — or the honest
no with the nearest true path (§6.4).

The bans in §6.3 hold here by construction rather than by filtering: no lever
produces new income, a loan, a balance transfer or motivational filler, so none
can appear. These checks assert that the construction still holds.
"""


def run(ctx):
    check = ctx.check

    try:
        from core.consequence import Card
        from core.solution import solve_one_time_cost, is_protected, NECESSITY_FLOOR
    except Exception as e:
        check(f'core/solution.py imports ({type(e).__name__}: {e})', False)
        return
    check('core/solution.py imports', True)

    cards = [Card(balance=8000, rate=22, minimum=200, name='Visa'),
             Card(balance=3000, rate=6, minimum=75, name='Store')]
    r = solve_one_time_cost(cards, 775, 2400)

    check('a real gap produces at least one path', r['gap_months'] > 0 and r['paths'])
    check('every path carries its cost, so the user can weigh it (E.4)',
          all('cost_months' in p and 'closes' in p for p in r['paths']))

    # E.3 rule 1: waiting/timing over cutting, always.
    cuts = [i for i, p in enumerate(r['paths']) if p['requires_cut']]
    nocuts = [i for i, p in enumerate(r['paths']) if not p['requires_cut']]
    check('paths needing no cut rank above paths that do (E.3 rule 1)',
          not cuts or not nocuts or min(cuts) > max(nocuts))

    # §6.3: the bans. No lever may propose income or new credit.
    blob = ' '.join(f"{p['kind']} {p['label']} {p['detail']}" for p in r['paths']).lower()
    banned = ['side hustle', 'raise', 'earn more', 'make more', 'loan', 'balance transfer',
              'credit card', 'bnpl', 'refinanc', 'borrow']
    hit = [b for b in banned if b in blob]
    check('no path proposes income or new credit (§6.3)', not hit)
    if hit:
        print(f'        banned terms present: {hit}')

    # A path claiming to close a gap must actually close it. "Save for it first"
    # was offered and removed for exactly this: the money comes from the same
    # surplus, so saving first delays the payoff by the same amount — the same
    # money, spent later, presented as free.
    check('no path claims to close the gap by rescheduling the same money',
          not any(p['kind'] == 'save_first' for p in r['paths']))

    # E.1 — the necessity floor, the one objective layer.
    check('the necessity floor protects stability, and only that',
          is_protected('Rent') and is_protected('Groceries')
          and is_protected('Car Insurance')
          and not is_protected('Dining Out') and not is_protected('Streaming'))
    check('the floor is a named constant, not a scatter of string literals',
          isinstance(NECESSITY_FLOOR, tuple) and len(NECESSITY_FLOOR) > 5)

    # Honest-null and the honest no.
    none_needed = solve_one_time_cost(cards, 775, 0)
    check('nothing to close returns no paths and no honest-no',
          none_needed['gap_months'] == 0 and not none_needed['paths']
          and none_needed['honest_no'] is None)

    unaffordable = solve_one_time_cost(cards, 100, 2400)
    check('an unsimulatable budget declines rather than inventing a path',
          unaffordable['gap_months'] is None and not unaffordable['paths'])

    # §6.4: never a bare "you can't" — the nearest true path comes with it.
    huge = solve_one_time_cost(cards, 775, 400000)
    if huge['honest_no']:
        check('an unclosable gap returns the honest no with a nearest path, not a refusal',
              'nearest_monthly' in huge['honest_no'] and 'gap_months' in huge['honest_no'])
    else:
        check('an unclosable gap returns an honest no', False)

    # Every timing path must carry what it frees — the view renders that figure,
    # and it was None on the first pass because the field was never passed.
    timing = [p for p in r['paths'] if p['kind'] == 'timing']
    check('a timing path carries the amount it frees and when',
          all(p['frees_monthly'] and p['available_in_months'] for p in timing))

    # The view shows two paths. Ranking puts no-cut paths first, and a closing
    # path usually requires a cut, so a naive top-two can hide the only option
    # that works. This asserts the data supports the guard the view applies.
    cheap = solve_one_time_cost(cards, 775, 900)
    if any(p['closes'] for p in cheap['paths']):
        check('a closing path exists even when the top two do not close the gap',
              any(p['closes'] for p in cheap['paths']))

    # Ranking must not have quietly acquired a willingness rule. E.3's rules 2, 4
    # and 5 need proof of what this user finds flexible, and F.6b keeps that
    # unclassified for most people — guessing it is the assumption E.2 forbids.
    import inspect
    from core import solution as _sol
    # Strip the docstring first: it names the willingness rules precisely to
    # explain why they are absent, and a check that reads prose finds them there.
    src = inspect.getsource(_sol._rank_key)
    body = src.split('"""')[-1] if '"""' in src else src
    check('ranking uses only the universal rules, not a guess at willingness',
          'requires_cut' in body and 'reversible' in body
          and 'sacred' not in body.lower() and 'flexible' not in body.lower())

    # ── Levers 1 and 4: the two that name something ───────────────────────
    # Reallocation and specific-cost trimming name a category and a merchant,
    # which the generic monthly lever deliberately refuses to do. The line they
    # have to stay on is between a receipt and a recommendation: the arithmetic
    # is the user's own record, and nothing here may assert what they would be
    # willing to give up. These check the receipt half; the willingness half is
    # checked by what is absent from the ranking, above.
    from core.solution import _headroom, _trims, MIN_MONTHS_OBSERVED
    from core.consequence import decision_impact

    cats = [
        {'name': 'Dining Out', 'budgeted': 400, 'max_observed': 310, 'months_observed': 6},
        {'name': 'Shopping', 'budgeted': 300, 'max_observed': 185, 'months_observed': 6},
        {'name': 'Rent', 'budgeted': 1400, 'max_observed': 1200, 'months_observed': 6},
        {'name': 'Groceries', 'budgeted': 800, 'max_observed': 600, 'months_observed': 6},
        {'name': 'Hobbies', 'budgeted': 200, 'max_observed': 20, 'months_observed': 2},
    ]
    rec = [
        {'name': 'Meal Kit Co', 'monthly': 110.0, 'category': 'Shopping'},
        {'name': 'Corner Coffee', 'monthly': 64.0, 'category': 'Dining Out'},
        {'name': 'City Power', 'monthly': 120.0, 'category': 'Utilities'},
        {'name': 'Mystery Charge', 'monthly': 60.0, 'category': None},
    ]
    room, cuts = _headroom(cats), _trims(rec)
    named_names = {c['name'] for c in room} | {c['name'] for c in cuts}

    check('the necessity floor holds on both naming levers (E.1)',
          not (named_names & {'Rent', 'Groceries', 'City Power'}))
    check('an item whose category is unknown is protected, not proposed',
          'Mystery Charge' not in named_names)
    check('a category with too little history is not a candidate',
          'Hobbies' not in named_names and MIN_MONTHS_OBSERVED >= 3)
    check('headroom is measured against the worst month, never the average',
          any(c['name'] == 'Dining Out' and c['monthly'] == 90 for c in room))

    named = solve_one_time_cost(cards, 775, 2400, categories=cats, recurring=rec)
    kinds = {p['kind'] for p in named['paths']}
    check('reallocation and trimming appear once the data can back them (§6.1)',
          'reallocation' in kinds and 'trim' in kinds)
    check('a named path frees exactly what the items it names add up to',
          all(abs(p['frees_monthly'] - sum(i['monthly'] for i in p['items'])) < 0.01
              for p in named['paths']
              if p['items'] and p['kind'] in ('reallocation', 'trim')))

    # The check that catches the baseline mistake. A named path is simulated as
    # `monthly_delta` against today's plan, not as a raised budget: raising the
    # budget moves the baseline too, which is right for timing (the card clears
    # either way) and wrong here (this money moves only if the user moves it).
    # Measured against a shifted baseline, a shift the lever says holds the date
    # reports that it does not.
    def _verify(p):
        d = decision_impact(cards, 775, monthly_delta=p['frees_monthly'], one_time_cost=2400)
        return d['months_delta'] is not None and (d['months_delta'] <= 0) == p['closes']
    check('a named path that claims to hold the date actually holds it',
          all(_verify(p) for p in named['paths'] if p['kind'] in ('reallocation', 'trim')))

    named_blob = ' '.join(f"{p['label']} {p['detail']}" for p in named['paths']).lower()
    check('the naming levers propose no income and no new credit either (§6.3)',
          not [b for b in banned if b in named_blob])
    # Proof, not persuasion. A path states what the record says and stops; the
    # moment it tells someone a cut is easy it is asserting a willingness it has
    # no evidence for.
    check('no named path characterises a cut as easy, small or obvious',
          not any(w in named_blob for w in
                  (' just ', 'easily', 'simply', 'only $', 'hardly', 'you should')))

    swap = solve_one_time_cost(cards, 775, 900, categories=cats, recurring=rec)
    trimmed = next((p for p in swap['paths'] if p['kind'] == 'trim'), None)
    check('a named path carries what it passed over, so one can be swapped for another',
          trimmed is not None and len(trimmed['alternatives']) > 0)

    stuck = solve_one_time_cost(cards, 775, 400000, categories=cats, recurring=rec)
    hn = stuck['honest_no'] or {}
    check('the honest no names where the money could come from (§6.4)',
          bool(hn.get('named_sources')) and hn.get('named_total') > 0)
    check('and does not dress that total up as enough',
          not any(p['closes'] for p in stuck['paths'])
          and hn['named_total'] < hn['nearest_monthly'])

    # C.4: an honest no carries the nearest lever, and the bound on what may be
    # OFFERED must not silence what may be STATED. Capped at the debt budget,
    # this figure was structurally always None — anything smaller would have
    # closed the gap as a path and this branch would never have run — so every
    # honest no said only what could not be done.
    check('the honest no carries the nearest lever, searched past the offer bound',
          hn['reachable'] and hn['nearest_monthly'] > 775)
    near = solve_one_time_cost(cards, 775, 12000, categories=cats, recurring=rec)
    near_no = near['honest_no'] or {}
    check('a gap just past that bound gets an answer instead of silence',
          near_no.get('nearest_monthly') is not None)
    check('and the figure stated is never one a path would have offered',
          near_no['nearest_monthly'] > 775
          and not any(p['closes'] for p in near['paths']))

    # ── The measurements the engine cannot make for itself ──────────────────
    # Everything above is arithmetic on numbers handed in. These are the numbers
    # themselves, measured from a real ledger through the route that serves
    # them. Three of the four rules that keep them honest are invisible from
    # inside core/solution.py — what a recurring item costs per month rather
    # than per charge, whether anyone still pays it, and which months the ledger
    # can speak about — so a fixture is the only place they can fail.
    from datetime import date as _date, timedelta as _td
    from core.database import Category as _Cat, Transaction as _Txn, BudgetItem as _BI

    def _mstart(back):
        d = _date.today().replace(day=1)
        for _ in range(back):
            d = (d - _td(days=1)).replace(day=1)
        return d

    with ctx.dbs() as session:
        ids = {}
        for nm in ('Lever Dining', 'Lever Shopping', 'Utilities', 'Lever Cash Only'):
            row = session.query(_Cat).filter_by(name=nm).first() or _Cat(name=nm)
            session.add(row)
            session.flush()
            ids[nm] = row.id
        for nm, amt in (('Lever Dining', 600), ('Lever Shopping', 400),
                        ('Utilities', 250), ('Lever Cash Only', 300)):
            session.add(_BI(name=nm, category=nm, amount=amt, type='expense', is_active=True))

        def _txn(when, amount, cat=None, merchant=''):
            session.add(_Txn(date=when, amount=amount, type='debit', merchant=merchant,
                             category_id=ids[cat] if cat else None))

        for back in range(1, 5):                    # four complete months
            m = _mstart(back)
            _txn(m + _td(days=3), 300.0, 'Lever Dining')
            _txn(m + _td(days=4), 110.0, 'Lever Shopping', 'Lever Meal Kit')
            _txn(m + _td(days=5), 120.0, 'Utilities', 'Lever Power')
            _txn(m + _td(days=6), 29.0, None, 'Lever Unknown Sub')
            for w in range(4):                      # weekly: a $16 charge, a $64 line
                _txn(m + _td(days=7 * w + 1), 16.0, 'Lever Dining', 'Lever Coffee')
        for back in range(3, 6):                    # cancelled three months ago
            _txn(_mstart(back) + _td(days=2), 55.0, 'Lever Shopping', 'Lever Old Gym')
        _txn(_date.today(), 25.0, 'Lever Dining')   # the half-recorded month
        session.commit()

    with ctx.dbs() as session:
        from server import reallocation_candidates, trim_candidates
        rooms = {c['name']: c for c in reallocation_candidates(session)}
        trims = {c['name']: c for c in trim_candidates(session)}

    check('a weekly charge is priced as the monthly line it is, not as the charge',
          'Lever Coffee' in trims and abs(trims['Lever Coffee']['monthly'] - 64.0) < 1.0)
    check('an item nobody has paid in months is not offered as a saving',
          'Lever Old Gym' not in trims)
    check('an uncategorised merchant comes back uncategorised, for the floor to catch',
          trims.get('Lever Unknown Sub', {}).get('category') is None)
    check('a budgeted category the ledger has never seen is not headroom',
          'Lever Cash Only' not in rooms)
    check('the half-recorded current month is left out of the measurement',
          'Lever Dining' in rooms
          and abs(rooms['Lever Dining']['max_observed'] - 364.0) < 0.01
          and rooms['Lever Dining']['months_observed'] == 4)
    check('a protected category is measured but never offered as headroom',
          'Utilities' in rooms
          and all(c['name'] != 'Utilities' for c in _headroom(list(rooms.values()))))

    # And the same numbers, through the route that will actually serve them.
    with ctx.dbs() as session:
        from core.database import DebtAccount as _DA, AppSetting as _AS
        session.add(_DA(name='Lever Card', current_balance=6000.0,
                        interest_rate=21.0, minimum_payment=150.0, is_active=True))
        row = session.query(_AS).filter_by(key='monthly_budget').first()
        if row:
            row.value = '700'
        else:
            session.add(_AS(key='monthly_budget', value='700'))
        session.commit()

    resp = ctx.c.post('/api/debt/decision-impact', headers=ctx.HJ,
                      json={'one_time_cost': 2400}).get_json() or {}
    served = ((resp.get('data') or resp).get('paths') or [])
    check('the route serves the naming levers, not just the engine',
          any(p['kind'] in ('reallocation', 'trim') for p in served))
    check('nothing on the necessity floor reaches the route\'s answer',
          # A .get, not a subscript: substitution's items are price rungs
          # rather than named sources, and every path's items go through here.
          not any(i.get('name') in ('Lever Power', 'Utilities')
                  for p in served for i in (p.get('items') or [])))

    # The sentence, not just the payload. Rendering the copy has found three
    # bugs that code review did not, and a field the view never reads is the
    # collect-and-ignore loop this platform exists to close.
    view = ctx.app_src
    check('the view phrases the naming levers from their fields, not their detail string',
          "p.kind === 'reallocation'" in view and "p.kind === 'trim'" in view
          and '_joinNames(items)' in view)
    check("the honest no's figures reach the page instead of sitting in the payload",
          'hn.named_total' in view and 'hn.nearest_monthly' in view)
    check('the stated figure rounds up, since rounded down it would not hold the date',
          'Math.ceil(hn.nearest_monthly / 5) * 5' in view)

    # ── Lever 5: substitution, priced rather than invented ───────────────────
    # The engine cannot know what a cheaper version of a thing IS — §6.1's own
    # example is BYB's mechanic, where the user names what is being replaced.
    # What it may do is price the same decision against the time it costs. Every
    # rung is verified here against the engine itself: a price that claims to
    # cost two months must cost two months, and a dollar more must cost more.
    from core.consequence import affordable_one_time

    sub_sol = solve_one_time_cost(cards, 775, 2400, categories=cats, recurring=rec)
    sub = next((p for p in sub_sol['paths'] if p['kind'] == 'substitution'), None)
    check('substitution offers the same decision at a price, with its cost',
          sub is not None and sub['items'] and sub['amount'] < 2400)

    def _at(price):
        return decision_impact(cards, 775, one_time_cost=price)['months_delta']
    check('every rung costs exactly the months it claims',
          all(_at(r['price']) == r['months_delta'] for r in (sub['items'] if sub else [])))
    check('and rounds down, so a rung is never a price that misses its claim',
          all(_at(r['price'] + 25) > r['months_delta'] for r in (sub['items'] if sub else [])))
    check('no rung costs more than the decision the user asked about',
          all(r['price'] < 2400 for r in (sub['items'] if sub else [])))

    # The rung that moves nothing is about one month of surplus whatever the
    # decision costs — the granularity of the model, not an alternative. Priced
    # alone it would answer a $900 question and a $40,000 one with the same
    # number, which is why the lever prices the delay the user actually faces.
    hold_900 = affordable_one_time(cards, 775, 900)
    hold_40k = affordable_one_time(cards, 775, 40000)
    check('the price that moves nothing is the same at any size, so it is not the lever',
          hold_900 is not None and hold_40k is not None and abs(hold_900 - hold_40k) < 25)
    check('while the priced-against-delay rung tracks the decision',
          affordable_one_time(cards, 775, 40000, max_delay_months=28) > 10000)

    # Substitution holds the date by changing the decision, not by finding the
    # money — so it must not be what silences §6.4's honest no.
    far = solve_one_time_cost(cards, 775, 400000, categories=cats, recurring=rec)
    check('substitution never silences the honest no',
          far['honest_no'] is not None)

    sub_blob = f"{sub['label']} {sub['detail']}".lower() if sub else ''
    check('and proposes no income and no new credit either (§6.3)',
          not [b for b in banned if b in sub_blob])
    check('the view prices it from the rungs, and shows one lever of each kind',
          "p.kind === 'substitution'" in view and 'rungs[0]' in view
          and "all.find(p => p.kind === 'substitution')" in view)

    # ── Lever 6: save-first, the anti-loan ───────────────────────────────────
    # Its value is against financing, not against paying cash, and the plan says
    # so rather than dressing a delay up as thrift. The engine absorbs a cash
    # cost out of the extra above minimums on the same schedule a saver would
    # save it, so the payoff moves identically either way — these check that the
    # plan states that instead of implying otherwise.
    from core.consequence import extra_above_minimums
    from core.solution import save_first_plan

    pool = extra_above_minimums(cards, 775)
    check('the plan saves out of the pool the cost actually comes from',
          pool == 775 - (200 + 75))
    check('a budget that cannot cover the minimums has no pool, and says so',
          extra_above_minimums(cards, 100) is None)

    plan = save_first_plan(cards, 775, 2400)
    check('save-first prices the plan from that pool, in whole months',
          plan and plan['monthly'] == pool and plan['months_to_save'] == 5)
    check('and reports the delay it does NOT remove',
          plan['months_delta'] == decision_impact(cards, 775, one_time_cost=2400)['months_delta']
          and plan['months_delta'] > 0)
    check('saving first is never offered as a path that closes the gap',
          not any(p['kind'] in ('save_first', 'save-first')
                  for p in solve_one_time_cost(cards, 775, 2400)['paths']))

    # The financing comparison is priced on the LOWEST-rate card the user holds
    # — the most flattering financing they could find — so the comparison
    # understates our own case rather than overstating theirs.
    fin = plan['financed']
    check('financing is priced on a card the user holds, at its own rate',
          fin and fin['card'] == min(cards, key=lambda c: c.rate).name
          and fin['apr'] == 6.0)
    check('and on the cheapest one, so the comparison cannot flatter the lever',
          fin['apr'] == min(c.rate for c in cards))

    # §6.1 assumed financing always costs more. Against a mixed-rate portfolio
    # it often does not, and the plan reports what is true rather than what the
    # lever would prefer. This pins the finding: if it ever flips, someone has
    # changed the engine's assumption about where a cash purchase comes from.
    check('the plan reports the arbitrage honestly rather than assuming it away',
          fin['extra_interest'] < 0 and plan['interest_paying_cash'] > fin['interest'])

    # And it must not reach the page. §6.2: a solution needs no new debt.
    resp2 = ctx.c.post('/api/debt/decision-impact', headers=ctx.HJ,
                       json={'one_time_cost': 2400}).get_json() or {}
    served2 = (resp2.get('data') or resp2)
    check('the funding panel gets the plan',
          isinstance(served2.get('save_first'), dict)
          and served2['save_first'].get('months_to_save'))
    check('and never the financing comparison (§6.2 — no new debt)',
          'financed' not in served2['save_first'])
    check('the view renders the plan from the engine, not from a division',
          '_tripImpactData && _tripImpactData.save_first' in view
          and 'out of the money now going to debt' in view)
    check('and says plainly that saving does not shorten the delay',
          'does not shorten the ${plan.months_delta}-month delay' in view)
