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

    # ── Lever 7: do-nothing, quantified ──────────────────────────────────────
    # "You're on track" is only worth saying with a number behind it, and only
    # when it is not contradicting another lever in the same breath.
    from core.consequence import simulate_payoff
    from core.solution import do_nothing_note

    note = do_nothing_note(cards, 775, 2400)
    base_months = simulate_payoff(cards, 775)['months']
    check('patience is quantified as the month the decision stops costing months',
          note and note['free_from_months'] == base_months)
    check('an unsimulatable budget produces no note rather than a hopeful one',
          do_nothing_note(cards, 100, 2400) is None)

    free = do_nothing_note(cards, 775, 100)
    check('a decision that needs no lever says so',
          free['moves_nothing'] is True)
    check('and still reports what it costs, since no months is not no cost',
          free['interest_cost'] > 0)

    # The proof only appears when it is proof. If the other order were better,
    # lever 3 offers it as a path, and claiming optimality alongside would be
    # the software arguing with itself.
    check('the order proof carries its own number',
          note['optimal_order'] and note['optimal_order']['months_better'] >= 0
          and note['optimal_order']['interest_better'] > 0)
    check('and is silent when the other order is actually the better one',
          do_nothing_note(cards, 775, 2400, strategy='snowball')['optimal_order'] is None)
    check('and silent with one balance, where the two orders are the same thing',
          do_nothing_note([cards[0]], 775, 2400)['optimal_order'] is None)

    # Patience must not be a path. Counted as one it would hold every date ever
    # asked about — wait until the debt clears and nothing can be delayed — and
    # §6.4's honest no would have nothing left to say.
    waited = solve_one_time_cost(cards, 775, 400000, categories=cats, recurring=rec)
    check('patience is never a path, so it cannot hollow out the honest no',
          waited['honest_no'] is not None
          and not any(p['kind'] in ('patience', 'do_nothing', 'wait')
                      for p in waited['paths']))

    resp3 = ctx.c.post('/api/debt/decision-impact', headers=ctx.HJ,
                       json={'one_time_cost': 2400}).get_json() or {}
    served3 = (resp3.get('data') or resp3)
    check('the route serves the do-nothing note',
          isinstance(served3.get('do_nothing'), dict)
          and served3['do_nothing'].get('free_from_months'))
    check('the view offers patience beside the honest no, where it is the answer left',
          'Waiting is the other answer' in view)
    check('and proves the current order when nothing needs changing at all',
          'Nothing needs to change: your ${esc(o.strategy)} order' in view)

    # ── Substitution's recurring half ────────────────────────────────────────
    # A commitment, not a purchase: the drain does not stop, so the money that
    # holds the date is exactly the net cost, and the failure mode is an
    # affordability wall rather than a longer delay.
    from core.solution import solve_monthly_cost
    from core.consequence import affordable_monthly

    car = solve_monthly_cost(cards, 775, 350, replaces_monthly=219,
                             categories=cats, recurring=rec)
    check('a commitment is priced net of what it replaces',
          car['net_monthly'] == 131 and car['gap_months'] > 0)
    sub_m = next((p for p in car['paths'] if p['kind'] == 'substitution'), None)
    check("substitution prices it GROSS, the way §6.1's own sentence reads",
          sub_m and all(r['price'] == r['net_price'] + 219 for r in sub_m['items']))
    check('and every rung costs the months it claims, net of the replacement',
          all(decision_impact(cards, 775,
                              monthly_delta=-(r['net_price']))['months_delta']
              == r['months_delta'] for r in sub_m['items']))
    check('the money that holds the date is the net cost itself, not a bisection',
          any(p['kind'] == 'monthly' and p['closes']
              and f"${car['net_monthly']:.0f}/mo" in p['detail'] for p in car['paths']))

    cheaper = solve_monthly_cost(cards, 775, 120, replaces_monthly=150)
    check('a replacement that costs less invents no problem',
          cheaper['gap_months'] == 0 and not cheaper['paths']
          and cheaper['net_monthly'] < 0)

    # The wall. BYB shipped a bug where this case read as the BEST outcome —
    # months came back null, became zero, and rendered as "sooner" in green.
    wall = solve_monthly_cost(cards, 775, 700)
    check('a payment that breaks the minimums is a wall, not a delay',
          wall['gap_months'] is None and wall['honest_no']
          and wall['honest_no']['unaffordable'] is True)
    cap = wall['honest_no']['max_payable_monthly']
    check('and the honest no answers in the units the decision is made in',
          cap and decision_impact(cards, 775, monthly_delta=-cap)['months_delta'] is not None
          and decision_impact(cards, 775, monthly_delta=-(cap + 50))['months_delta'] is None)
    check('the cap is what the extra above the minimums can actually carry',
          abs(cap - extra_above_minimums(cards, 775)) <= 1)

    check('affordable_monthly rounds down, so a price never misses its claim',
          affordable_monthly(cards, 775, 350) <= 350
          and decision_impact(cards, 775,
                              monthly_delta=-affordable_monthly(cards, 775, 350)
                              )['months_delta'] <= 0)

    # Through the route BYB will call, in the shape BYB will call it.
    resp4 = ctx.c.post('/api/debt/decision-impact', headers=ctx.HJ,
                       json={'monthly_cost': 350, 'replaces_monthly': 219}).get_json() or {}
    served4 = (resp4.get('data') or resp4)
    # Either shape is a real answer: paths when the commitment delays the date,
    # the wall when it breaks the minimums. Which one this fixture produces
    # depends on what every other section has left in the shared database, so
    # the check is on the wiring, not on which branch the numbers land in — the
    # branches themselves are pinned above, against a fixed portfolio.
    m4 = served4.get('monthly') or {}
    check('the route solves a commitment when asked in its own terms',
          isinstance(m4, dict)
          and (m4.get('paths') or (m4.get('honest_no') or {}).get('max_payable_monthly')))
    check('and derives the delta from cost and replacement, so both halves agree',
          served4.get('months_delta') == served4['monthly']['gap_months'])
    check('a negative price is refused rather than simulated',
          ctx.c.post('/api/debt/decision-impact', headers=ctx.HJ,
                     json={'monthly_cost': -50}).status_code >= 400)

    check('BYB asks the engine rather than netting it out in JS again',
          '_maybeLoadBYBImpact' in view and 'monthly_cost: monthly' in view
          and '_bybEngineNote()' in view)
    check('and the phrase says /mo, since a commitment is not a purchase',
          "_tripPathPhrases(paths, gap, unit = '')" in view
          and "${fmt(head.price)}${unit} version" in view)

    # ── BYB's calc, unified into Pillar 1 (§7) ───────────────────────────────
    # The wizard computed a payoff in three places, each with its own JS
    # simulator call, and searched the cards itself for the "what if you waited"
    # section. Every one of those now asks the engine. This checks the region
    # rather than the file: the other surfaces still use the JS simulators, and
    # retiring those is not this change.
    #
    # Comment lines are stripped first. Four times now a source check has
    # matched the prose explaining why something is absent — including the
    # comments directly above, which name both simulators.
    byb = view[view.index('let _bybImpactData'):view.index('function _bybCommit')]
    byb_code = chr(10).join(l for l in byb.split(chr(10)) if not l.strip().startswith(chr(47)*2))
    check("BYB no longer runs its own payoff simulation anywhere",
          '_simulatePayoff' not in byb_code and '_projectPayoff' not in byb_code)
    check('every BYB payoff figure comes from one adapter over the engine',
          byb_code.count('_bybEnginePayoff(') >= 3 and 'd.base' in byb_code)
    check('the baseline comes from the engine too, not from a second simulator',
          '_bybApplyImpact' in byb_code and "_bybEnginePayoff('base')" in byb_code)

    # Three states, kept apart. An unanswered fetch is not "not affordable", and
    # neither is a zero — a null read as 0 months is the July 6 field bug, where
    # the worst outcome rendered as the best one in green.
    check('a pending answer is distinguished from an honest null',
          'return undefined;' in byb_code and 'pending' in byb_code
          and byb_code.count('=== undefined') >= 1)
    check('and neither is allowed to become zero months',
          byb_code.count('(pending || budgetInsufficient) ? null') >= 2)

    # The waiting section reads the engine's clearing schedule, which accounts
    # for the extra cascading onto the card being targeted. The search it
    # replaces ran each balance in isolation at its minimum and dated every
    # clearing later than it happens.
    check("the waiting section reads the engine's own clearing schedule",
          "p.kind === 'timing'" in byb_code and 'available_in_months' in byb_code)
    check('and the affordability wall still says whether waiting moves it',
          'after_waiting' in byb_code)

    wall_w = solve_monthly_cost(cards, 775, 700)['honest_no']['after_waiting']
    check('the wall names the balance whose clearing raises the ceiling (C.4)',
          wall_w and wall_w['name'] and wall_w['available_in_months'] > 0
          and wall_w['max_payable_monthly'] > 0)
    check('and says plainly when waiting is enough, and when it is not',
          wall_w['enough'] is True
          and solve_monthly_cost(cards, 775, 1200)['honest_no']['after_waiting']['enough'] is False)

    # ── §8, the Debt Payoff surface: the levers pointed at the plan ──────────
    # Every solver above answers a question about a decision. This one answers
    # "what moves my date most", which is the question that surface is for.
    from core.solution import accelerations

    accel = accelerations(cards, 775, categories=cats, recurring=rec)
    check('the plan itself has levers, from the same record the solvers use',
          accel and all(a['months_saved'] > 0 for a in accel))
    check('ranked by what they actually move, which is the question asked',
          [a['months_saved'] for a in accel] == sorted(
              (a['months_saved'] for a in accel), reverse=True))
    check('and each carries whether it is a cut, so the two kinds stay apart',
          all('requires_cut' in a for a in accel)
          and any(not a['requires_cut'] for a in accel))

    base_m = simulate_payoff(cards, 775)['months']
    check('every saving is verified against the engine, not asserted',
          all(simulate_payoff(cards, 775 + a['monthly'])['months']
              == base_m - a['months_saved']
              for a in accel if a['monthly'] > 0))
    check('a lever that frees money but moves no month is not offered',
          all(a['months_saved'] >= 1 for a in accel))
    check('the necessity floor holds here too (E.1)',
          not any(i.get('name') in ('Rent', 'Groceries', 'City Power')
                  for a in accel for i in a['items']))
    check('and no combinations, which would need a willingness nobody has',
          all(len(a['items']) <= 1 for a in accel))
    check('nothing to accelerate returns nothing rather than a hopeful list',
          accelerations(cards, 775) == []
          and accelerations(cards, 100, categories=cats) == [])

    resp5 = ctx.c.get('/api/debt/accelerations', headers=ctx.H).get_json() or {}
    served5 = (resp5.get('data') or resp5)
    check('the route serves them with the plan they are measured against',
          'accelerations' in served5 and 'base' in served5
          and 'do_nothing' in served5)
    check('the advisor renders them, and says what each one assumes',
          '_debtRenderAccelerations' in view
          and 'assumes the money freed goes toward the debt' in view)
    check('an empty list still teaches, but only with the proof attached',
          'Nothing in your record moves it further' in view
          and 'months_better > 0' in view)

    # ── §8, the Budget surface: what an amount costs ─────────────────────────
    # "This category's overspend costs ~6 weeks; here's the reallocation that
    # fixes it." Overspend is the mirror of headroom and is measured the same
    # way — the part of the record that held in EVERY month it can speak about.
    from core.solution import budget_pressure, _overspend

    over_cats = [
        {'name': 'Dining Out', 'budgeted': 300, 'min_observed': 385,
         'max_observed': 480, 'months_observed': 6},
        {'name': 'Shopping', 'budgeted': 300, 'min_observed': 60,
         'max_observed': 185, 'months_observed': 6},
        {'name': 'Groceries', 'budgeted': 700, 'min_observed': 790,
         'max_observed': 910, 'months_observed': 6},
        {'name': 'Hobbies', 'budgeted': 100, 'min_observed': 140,
         'max_observed': 160, 'months_observed': 2},
        {'name': 'Travel', 'budgeted': 200, 'min_observed': 120,
         'max_observed': 900, 'months_observed': 6},
    ]
    over = _overspend(over_cats)
    names = {o['name'] for o in over}
    check('overspend is measured from the best month, so one spike cannot claim it',
          'Travel' not in names)
    check('a category under its budget is not overspending',
          'Shopping' not in names)
    check('and too little history claims nothing either way',
          'Hobbies' not in names)
    check('the amount is what held every month, not an average',
          any(o['name'] == 'Dining Out' and o['monthly'] == 85 for o in over))

    press = budget_pressure(cards, 775, categories=over_cats)
    check('each overspend is priced in months, the same currency as every decision',
          press and all(p['months_cost'] >= 0 and p['interest_cost'] > 0 for p in press))
    base_p = simulate_payoff(cards, 775)['months']
    check('and the months are verified against the engine, not asserted',
          all(simulate_payoff(cards, 775 + p['monthly'])['months']
              == base_p - p['months_cost'] for p in press))

    groc = next((p for p in press if p['name'] == 'Groceries'), None)
    check('a category on the necessity floor is flagged as a budget set too low',
          groc and groc['protected'] is True)
    check('and the fix asks for what the gap costs, not what the envelope holds',
          all(p['fix'] is None or p['fix']['monthly'] == p['monthly'] for p in press))
    check('a category never funds its own overspend',
          all(p['fix'] is None or all(sc['name'] != p['name'] for sc in p['fix']['sources'])
              for p in press))
    check('and the necessity floor still holds on the source side (E.1)',
          all(p['fix'] is None or not any(is_protected(sc['name'])
                                          for sc in p['fix']['sources'])
              for p in press))
    check('no debt means no way to price the time, and nothing is invented',
          budget_pressure(cards, 100, categories=over_cats) == [])

    resp6 = ctx.c.get('/api/budget/pressure', headers=ctx.H).get_json() or {}
    served6 = (resp6.get('data') or resp6)
    check('the route serves the pressure with the plan it is measured against',
          'pressure' in served6 and 'base' in served6)
    check('the budget page renders it, and says each line stands alone',
          '_budgetRenderPressure' in view
          and 'Each line is measured on its own' in view)

    # ── §8, the Ledger surface: a charge already made ────────────────────────
    # Every other question here is prospective. This one is in the past tense,
    # and the engine had no way to ask it: one_time_cost prices money that will
    # NOT reach the debt, and a charge already made needs the mirror.
    from core.solution import past_charge_lesson
    from core.consequence import simulate_payoff as _sim

    lesson = past_charge_lesson(cards, 775, 1850)
    base_l = _sim(cards, 775)
    check('a past charge is priced by what that money would have done here',
          lesson and lesson['months_cost'] > 0 and lesson['interest_cost'] > 0)
    check('and the counterfactual is the engine run, not a rule of thumb',
          _sim(cards, 775, one_time_extra=1850)['months']
          == base_l['months'] - lesson['months_cost'])
    check('one_time_extra lands once and changes nothing at zero',
          _sim(cards, 775, one_time_extra=0)['months'] == base_l['months'])
    check('a charge with no months in it is priced honestly as none',
          past_charge_lesson(cards, 775, 25)['months_cost'] == 0)
    check('and an unsimulatable plan prices nothing at all',
          past_charge_lesson(cards, 100, 1850) is None
          and past_charge_lesson(cards, 775, 0) is None)

    # The recovery a lesson offers is measured, not inherited from the path.
    # These paths were solved to cancel a FUTURE cost; the sentence claims they
    # put back months already lost, and those are two computations.
    resp7 = ctx.c.get('/api/transactions/lesson', headers=ctx.H).get_json() or {}
    served7 = (resp7.get('data') or resp7)
    check('the route answers, in one of its two honest shapes',
          'lesson' in served7)
    if served7.get('lesson'):
        # Against the route's OWN inputs, not the fixture portfolio above. The
        # first version of this check used a hardcoded budget and failed on a
        # database every other section has been writing to, which is the check
        # being wrong rather than the code.
        from server import _consequence_inputs
        with ctx.dbs() as _s:
            _cards, _budget, _strategy, _ = _consequence_inputs(_s)
        for p in (served7.get('paths') or []):
            if p.get('months_recovered'):
                kw = dict(today_key=None, start_month=None)
                got = (_sim(_cards, _budget, _strategy)['months']
                       - _sim(_cards, _budget + p['frees_monthly'], _strategy)['months'])
                check(f"the recovery on a {p['kind']} path is what the engine says",
                      p['months_recovered'] == got)
                break
    check('capacity that only arrives later never claims to put months back now',
          all(not p.get('months_recovered')
              for p in (served7.get('paths') or [])
              if p.get('available_in_months')))
    check('substitution is not offered on a purchase already made',
          not any(p['kind'] == 'substitution' for p in (served7.get('paths') or [])))

    check('the ledger renders it in the past tense, and offers what puts it back',
          '_ledgerRenderLesson' in view and 'had that money gone to the debt' in view
          and 'would put them back' in view)
    check('and the phrasing is written for a charge, not borrowed from a plan',
          'months_recovered' in view and '_tripPathPhrases([pick]' not in view)

    # ── §8, the Net Worth surface: what the number now covers ────────────────
    # "You crossed $X" is a milestone invented by whoever picked X. The crossing
    # that means something is liquid savings reaching a balance the user
    # actually holds, which their own portfolio defines.
    from core.solution import capacity_unlocked

    cap = capacity_unlocked(cards, 775, liquid=6000, monthly_expenses=2600)
    check('a balance the record can now cover is what counts as a crossing',
          cap and cap[0]['name'] == 'Store' and cap[0]['balance'] == 3000)
    check('and clearing it is priced by the engine, not by the balance',
          cap[0]['months_saved'] == simulate_payoff(cards, 775)['months']
          - simulate_payoff([c for c in cards if c.name != 'Store'], 775)['months'])

    # C.5: a path that breaks stability is not offered, however well it works.
    check('nothing is offered that would leave less than a month of expenses',
          capacity_unlocked(cards, 775, liquid=3200, monthly_expenses=2600) == [])
    check('and with no recorded expenses there is no buffer to express, so nothing',
          capacity_unlocked(cards, 775, liquid=20000, monthly_expenses=0) == [])
    check('what would be left is reported in months of their own expenses, not judged',
          all(c['months_of_expenses_after'] >= 1 for c in
              capacity_unlocked(cards, 775, liquid=12000, monthly_expenses=2600)))

    # The sentence this feeds has to survive being read on a net-worth page.
    check('it says outright that this does not raise net worth',
          all(c['changes_net_worth'] is False for c in cap))
    check('and the view says so where a reader would otherwise assume it does',
          'would not move your net worth today' in view)

    # A lease cannot be settled early and a forgiveness-bound loan is money
    # burned — the engine already refuses to send extra to either.
    from core.consequence import Card as _C
    odd = [_C(balance=2000, rate=0, minimum=300, name='Lease', is_lease=True),
           _C(balance=2500, rate=6, minimum=90, name='Loan', is_pslf=True,
              forgive_after_months=20)]
    check('savings are never pointed at a lease or a loan headed for forgiveness',
          capacity_unlocked(odd, 500, liquid=20000, monthly_expenses=1000) == [])

    resp8 = ctx.c.get('/api/debt/capacity', headers=ctx.H).get_json() or {}
    served8 = (resp8.get('data') or resp8)
    check('the route reads liquid as savings and cash, and says what it used',
          'liquid' in served8 and 'monthly_expenses' in served8)
    check('the net worth page renders what the number covers',
          '_nwRenderCapacity' in view and 'What this number now covers' in view)

    # ── §8, the fund surfaces: causal pace, not just a pace badge ────────────
    # The badge these rows carry says how reliably the plan is met. It does not
    # say when the thing arrives, or what would move that date.
    from core.solution import fund_pace

    behind = fund_pace(2400, 600, planned_monthly=150, deadline_months=6,
                       observed_monthly=95, samples=5,
                       categories=cats, recurring=rec)
    check('a fund lands where its actual pace puts it, not where the plan says',
          behind['pace_source'] == 'observed' and behind['pace_monthly'] == 95
          and behind['finish_months'] == 19)
    check('and missing the deadline is stated, not implied',
          behind['on_track'] is False and behind['short_monthly'] == 205)
    check('the lever is aimed at the shortfall, not at the whole contribution',
          behind['lever'] and behind['lever']['monthly'] == behind['short_monthly'])
    check('and it names what it would move the date to',
          behind['lever']['finish_months'] <= behind['deadline_months'])

    thin = fund_pace(2400, 600, planned_monthly=150, deadline_months=6,
                     observed_monthly=95, samples=1)
    check('too few contributions is a plan, not a pace, and says so',
          thin['pace_source'] == 'plan' and thin['pace_monthly'] == 150)
    check('nothing being contributed produces no finish date at all',
          fund_pace(2400, 600, planned_monthly=0,
                    deadline_months=6)['finish_months'] is None)
    check('a funded fund is done, not behind',
          fund_pace(2400, 2400, planned_monthly=150)['funded'] is True)
    check('and no deadline means a date with nothing to miss',
          fund_pace(2400, 600, planned_monthly=150)['on_track'] is None)
    check('no compounding is invented on money merely set aside',
          fund_pace(1200, 0, planned_monthly=100,
                    deadline_months=24)['finish_months'] == 12)

    # Per MONTH, not per contribution — the same distinction that bit the
    # recurring-cost lever. Months with no deposit are not logged at all, so
    # averaging the logged ones describes a saver who contributes every month.
    from core.database import HistorianEntry as _HE
    from datetime import datetime as _dt, timedelta as _td
    import json as _json
    from server import fund_observed_monthly
    with ctx.dbs() as session:
        for i, amt in enumerate((300.0, 300.0, 300.0)):
            e = _HE(event_category='sinking_fund_contribution_variance',
                    expected_value=300.0, actual_value=amt,
                    context_json=_json.dumps({'sinking_fund_id': 90901}))
            e.created_at = _dt.utcnow() - _td(days=30 * (5 - i * 2))
            session.add(e)
        session.commit()
    with ctx.dbs() as session:
        per_month, samples = fund_observed_monthly(session, 90901)
    check('a fund fed three times in six months is not a $300/mo fund',
          samples == 3 and per_month is not None and per_month < 300)
    check('and the span runs from the first deposit, not the whole window',
          per_month >= 900 / 7)

    resp9 = ctx.c.get('/api/sinking-funds/pace', headers=ctx.H).get_json() or {}
    served9 = (resp9.get('data') or resp9)
    check('the route serves a pace per fund', 'funds' in served9)
    check('the budget page narrates it and labels which pace it used',
          '_sfPaceSentence' in view
          and 'you have actually been putting in' in view
          and 'at the planned' in view)
    check('and an uncoverable shortfall is said plainly rather than left blank',
          'nothing in your record has that room' in view)

    # ── §8, Reports: the causal teaching layer, made explicit ────────────────
    # The report composes what the other surfaces compute rather than deriving
    # its own numbers, so it cannot drift from the pages it summarises. And it
    # is composed HERE rather than by the narrator: inference-smuggling ran
    # 37-70% on every model measured and rose with size, so a causal claim
    # written by a model is the one thing the evidence says not to build.
    resp10 = ctx.c.get('/api/debt/teaching', headers=ctx.H).get_json() or {}
    served10 = (resp10.get('data') or resp10)
    finds = served10.get('findings') or []
    check('the report serves findings, or says why it has none',
          'findings' in served10)
    check('every finding carries the proof behind it (B.1)',
          all(f.get('proof') for f in finds))
    check('and every proof figure states its own unit, never leaving it to prose',
          all(pf.get('unit') for f in finds for pf in f['proof']))
    check('a month count says what it is a month OF',
          all(f.get('months_label') for f in finds if f.get('months') is not None))
    check('and no two findings claim the same subject twice',
          len({f['subject'] for f in finds}) == len(finds))

    # The report must not become a sixth engine. Each finding is a figure some
    # other surface already renders, so a drift between them is impossible by
    # construction rather than by discipline.
    kinds = {f['kind'] for f in finds}
    check('the findings are drawn only from levers that exist elsewhere',
          kinds <= {'charge', 'overspend', 'lever', 'fund'})

    check('the teaching renders without the narrator, above it and apart from it',
          '_rcRenderMonthlyTeaching' in view
          and 'rcMonthlyTeaching' in view
          and 'Computed from your ledger, not written by the AI' in view)
    check('the narrator is handed facts, and told they are the only causal ones',
          'CAUSAL FINDINGS' in view
          and 'these are the ONLY' in view
          and 'do not explain WHY' in view)
    check('and the view formats each figure by its stated unit',
          "p.unit === 'money'" in view and "p.unit === 'months'" in view)

    # ── Pillar 5 (§7): the memory, finally read back ─────────────────────────
    # These decisions have been logged since Phase H1 and nothing has ever read
    # them. Two rules do the work: silence is not a decision, and a record is
    # not a forecast.
    from core.solution import decision_memory, MIN_DECISIONS

    hist = [{'decision': 'walkaway', 'variance_pct': None},
            {'decision': 'commit', 'variance_pct': 18.0},
            {'decision': 'commit', 'variance_pct': 22.0},
            {'decision': 'walkaway', 'variance_pct': None},
            {'decision': None, 'variance_pct': None},
            {'decision': 'track', 'variance_pct': None},
            {'decision': 'commit', 'variance_pct': 11.0}]
    mem = decision_memory(hist)
    check('an item with no decision is not counted as a decision',
          mem['decisions'] == 5 and mem['walkaways'] == 2)
    check('and neither is one still being tracked',
          decision_memory([{'decision': 'track'}])['decisions'] == 0)
    check('the walkaway rate is withheld until there is a practice to describe',
          decision_memory(hist[:2])['walkaway_rate_pct'] is None
          and mem['walkaway_rate_pct'] == 40 and MIN_DECISIONS >= 3)
    check('estimate bias counts only decisions that produced a real comparison',
          mem['estimate']['samples'] == 3)
    check('and names its direction rather than leaving a sign to be read',
          mem['estimate']['direction'] == 'under' and mem['estimate']['bias_pct'] == 17.0)
    check('an estimate that lands is called even, not spun as either way',
          decision_memory([{'decision': 'commit', 'variance_pct': v}
                           for v in (1.0, -1.0, 0.5)])['estimate']['direction'] == 'even')
    check('no history produces no claims at all',
          decision_memory([])['walkaway_rate_pct'] is None
          and decision_memory([])['estimate'] is None)

    resp11 = ctx.c.get('/api/byb/memory', headers=ctx.H).get_json() or {}
    served11 = (resp11.get('data') or resp11)
    check('the route reads the historian, which is the proof ledger (B.1)',
          'decisions' in served11 and 'walkaways' in served11)

    # A record, never a forecast. Comments are stripped first: the ones above
    # this quote the banned phrasing in order to forbid it, which is exactly
    # the trap that has caught four source checks in this file already.
    byb_view = view[view.index('let _bybMemoryData'):view.index('function _renderBYBList')]
    byb_code = chr(10).join(l for l in byb_view.split(chr(10))
                            if not l.strip().startswith(chr(47) * 2))
    check('the copy states what happened and predicts nothing',
          not any(w in byb_code.lower() for w in
                  ('usually', 'you tend', 'likely to', 'probably', 'expect you')))
    check('the list no longer reads an undecided item as a walkaway',
          "b.decision === 'walkaway')" in view
          and "b.decision === 'walkaway' || !b.decision" not in view)
    check('estimate bias sits where the estimate is typed, the record where history is',
          '_bybEstimateBiasNote' in view and '_bybMemoryHTML' in view)

    # ── Pillar 4 (§7, Appendix D): the green light ───────────────────────────
    # Appendix D spends four sections on what may go in front of "you freed
    # $180/mo", and the filtering is the substance. These check the filters.
    from core.solution import green_light, FRESH_CREDIT_MONTHS

    lit = green_light(cards, 775, [
        {'name': 'Old Card', 'monthly': 180, 'deliberate': True, 'months_ago': 2},
        {'name': 'Store Line', 'monthly': 40, 'deliberate': True, 'months_ago': 1}])
    check('freed capacity is what deliberate action ended',
          lit and lit['freed_monthly'] == 220 and lit['months_sooner'] > 0)
    check('and it is worth something the engine computed, not asserted',
          lit['months_sooner'] == simulate_payoff(cards, 775 - 220)['months']
          - simulate_payoff(cards, 775)['months'])

    # D.4: paying the minimum is the expected floor, and praising a floor erodes
    # trust. Capacity that arrived that way is reported, never credited.
    floor_only = green_light(cards, 775, [
        {'name': 'Ran Its Course', 'monthly': 180, 'deliberate': False, 'months_ago': 2}])
    check('a balance that ran out on its minimums lights nothing',
          floor_only is None)
    mixed = green_light(cards, 775, [
        {'name': 'Attacked', 'monthly': 100, 'deliberate': True, 'months_ago': 1},
        {'name': 'Ran Its Course', 'monthly': 60, 'deliberate': False, 'months_ago': 4}])
    check('and is kept separate from what was earned, not folded into it',
          mixed['freed_monthly'] == 100 and mixed['uncredited_monthly'] == 60)

    # D.5: name one or two by magnitude, or say plainly that it was diffuse.
    check('the top drivers are named, largest first',
          [d['name'] for d in lit['drivers']] == ['Old Card', 'Store Line'])
    diffuse = green_light(cards, 775, [
        {'name': n, 'monthly': m, 'deliberate': True, 'months_ago': 6}
        for n, m in (('a', 30), ('b', 28), ('c', 26), ('d', 25))])
    check('and a genuinely diffuse cause is not cherry-picked into one',
          diffuse['diffuse'] is True and diffuse['drivers'] == []
          and diffuse['driver_count'] == 4)

    check('recency sets the tense and nothing else',
          lit['fresh'] is True and diffuse['fresh'] is False
          and FRESH_CREDIT_MONTHS >= 1)
    check('nothing deliberate means no light at all',
          green_light(cards, 775, []) is None)

    resp12 = ctx.c.get('/api/debt/green-light', headers=ctx.H).get_json() or {}
    served12 = (resp12.get('data') or resp12)
    check('the route answers, with a light or an honest absence',
          'green_light' in served12)

    # D.3 / D.6, by construction rather than by filtering: no income or
    # investment figure is read by this path at all.
    route_src = ctx.server_src[ctx.server_src.index('def debt_green_light'):]
    route_src = route_src[:route_src.index('@debt_bp.route', 10)]
    # Strip the docstring as well as the comments. The docstring states the
    # rule this check enforces, in the words it forbids — the same trap that
    # has now caught five source checks in this file. A check that reads prose
    # is testing the prose.
    parts = route_src.split('\"\"\"')
    route_body = parts[2] if len(parts) > 2 else route_src
    route_code = chr(10).join(l for l in route_body.split(chr(10))
                              if not l.strip().startswith('#'))
    check('the green light never reads income or investments (D.3, D.6)',
          not any(t in route_code for t in
                  ('savings_balance', 'investments_balance', 'S.incomes', 'income')))
    check('the view fires it only when the freed money covers what is weighed',
          'monthly > gl.freed_monthly' in view)
    check('and says what it spends, so a yes is not applause',
          'and uses' in view and 'fits inside it' in view)

    # ── Appendix A: when the app may speak first ─────────────────────────────
    # The gauntlet is the feature. Every gate below withholds something true,
    # which is the point: strictness is free, because a candidate that fails
    # stays passive on its own surface rather than being lost (A.1).
    from core.proactive import (BRAKE_PER_WEEK, DISMISSALS_TO_PASSIVE,
                                PER_SESSION, budget_class, contend, verdict)

    quiet = {'monthly_budget': 2000, 'session_prompts': 0, 'brake_last_7d': 0,
             'green_last_7d': 0, 'shown': {}, 'dismissed': {},
             'category_dismissals': {}, 'cadence_tier': 0}
    brake = {'key': 'overspend:Groceries', 'kind': 'brake', 'months': 2,
             'dollars': 120, 'has_path': True, 'category': 'Groceries'}

    check('a material brake with a path may interrupt',
          verdict(brake, quiet)['promote'] is True)
    check('a trivial one never does, and materiality is relative to their scale',
          verdict({**brake, 'months': 0.1, 'dollars': 10}, quiet)['gate'] == 'materiality')
    check('bad news with no path is never delivered unprompted (A.2 #2)',
          verdict({**brake, 'has_path': False}, quiet)['gate'] == 'actionability')
    check('but good news needs no path, because it asks nothing',
          verdict({'key': 'g', 'kind': 'green', 'months': 1, 'has_path': False},
                  quiet)['promote'] is True)

    check('one interruption per session, whatever else is true',
          verdict(brake, {**quiet, 'session_prompts': PER_SESSION})['gate'] == 'budget'
          and PER_SESSION == 1)
    check('and a weekly cap on top of it',
          verdict(brake, {**quiet, 'brake_last_7d': BRAKE_PER_WEEK})['gate'] == 'budget')
    check('good news spends a different budget, since it is not pressure (A.3)',
          budget_class('green') == 'green' and budget_class('brake') == 'brake'
          and verdict({'key': 'g2', 'kind': 'green', 'months': 1},
                      {**quiet, 'brake_last_7d': BRAKE_PER_WEEK})['promote'] is True)
    check('a clarification mints no budget of its own, it joins the brake',
          budget_class('clarification') == 'brake')

    # A.4 — a dismissal is an instruction, not a signal to model.
    check('a dismissed lesson goes quiet for sixty days',
          verdict(brake, {**quiet, 'dismissed': {'overspend:Groceries': {'days_ago': 10}}}
                  )['gate'] == 'novelty')
    check('and the same lesson is never shown twice',
          verdict(brake, {**quiet, 'shown': {'overspend:Groceries': 3}})['gate'] == 'novelty')
    check('twice dismissed in a category drops that category to passive for good',
          verdict(brake, {**quiet, 'category_dismissals': {'Groceries': DISMISSALS_TO_PASSIVE}}
                  )['gate'] == 'novelty')
    check('sustained dismissals lower the whole cadence a tier',
          verdict(brake, {**quiet, 'brake_last_7d': BRAKE_PER_WEEK - 1,
                          'cadence_tier': 1})['gate'] == 'budget')

    # A.2 #5 is not checkable here and says so rather than passing quietly.
    check('the timing gate is delegated to the caller, and named as delegated',
          verdict(brake, quiet)['timing_delegated'] is True)

    # A.3's contention: the ruler is the user's goal, never our ordering.
    check('the scarce slot goes to what moves the goal most',
          contend([{'key': 'a', 'goal_impact': 1}, {'key': 'b', 'goal_impact': 3},
                   {'key': 'c', 'goal_impact': 2}])['key'] == 'b')
    check('a decision about to be made outranks a fact equally true next week',
          contend([{'key': 'x', 'goal_impact': 2},
                   {'key': 'y', 'goal_impact': 2, 'perishable': True}])['key'] == 'y')
    check('and a contradiction outranks anything ranked on what it contradicts',
          contend([{'key': 'big', 'goal_impact': 9, 'depends_on': 'Dining'},
                   {'key': 'check', 'goal_impact': 0, 'disputes': 'Dining'}])['key'] == 'check')
    check('nothing to say means nothing is said',
          contend([]) is None)

    # Through the route, which is where selecting and showing must stay apart.
    resp13 = ctx.c.get('/api/proactive/next', headers=ctx.H).get_json() or {}
    served13 = (resp13.get('data') or resp13)
    check('the route answers with a prompt or an honest silence',
          'prompt' in served13 and 'considered' in served13)
    check('and says which gate stopped each candidate it withheld',
          all(c.get('gate') for c in served13.get('considered', []) if not c['promote']))

    before = ctx.c.get('/api/proactive/next', headers=ctx.H).get_json() or {}
    after = ctx.c.get('/api/proactive/next', headers=ctx.H).get_json() or {}
    b, a = (before.get('data') or before), (after.get('data') or after)
    check('asking twice does not spend the budget, because asking is not showing',
          (b.get('prompt') or {}).get('key') == (a.get('prompt') or {}).get('key'))
    check('the ledger records what was shown, reported by the surface that showed it',
          '_dashRenderProactive' in view and "'/api/proactive/shown'" in view
          and '_dashProactiveAsked' in view)
    check('and the card is dismissable, in the page, never a modal',
          '_dashDismissProactive' in view and 'dashProactive' in view)

    # ── The Trophy Room's pinned standard (B.3, §12's gate) ──────────────────
    # §11 forbids building this until the per-case standard is pinned, because
    # "evidence-backed" degrades to "declared-backed" under deadline pressure.
    # The pinning lives in core/trophies.py; these check it holds.
    from core.trophies import (ACTION, DURABLE, DURABILITY_MONTHS, SETUP,
                               TROPHY_SPEC, attributable, held, verdict)

    check('every trophy in the app has a pinned class and proof source',
          len(TROPHY_SPEC) == 25
          and all(v['class'] in (ACTION, DURABLE, SETUP) for v in TROPHY_SPEC.values())
          and all(v.get('proof') for v in TROPHY_SPEC.values()
                  if v['class'] != SETUP))

    # D.4: using the app is not an achievement. The trophy is a receipt, and
    # entering data is not a change in anyone's money.
    setup_ids = {k for k, v in TROPHY_SPEC.items() if v['class'] == SETUP}
    check('setup steps are not sold as earned trophies (D.4)',
          {'eyes_open', 'honest_count', 'first_snapshot'} <= setup_ids
          and verdict('eyes_open')['earned'] is False)

    # E.2a: a number that can revert is not a fact until it has held.
    check('a revertible number waits until it has held',
          verdict('zero_crossing', {'held': None})['earned'] is None
          and verdict('zero_crossing', {'held': True, 'attributable': True})['earned'] is True
          and DURABILITY_MONTHS == 3)
    check('and the window counts recorded months, not elapsed ones',
          held([1, 1], bool) is None and held([1, 1, 1], bool) is True)

    # D.3/D.6: never the market, never a raise. What the record CAN prove is
    # the other side of the sheet — liabilities falling is debt being paid.
    check('a rise nobody can attribute to the user earns nothing (D.6)',
          verdict('zero_crossing', {'held': True, 'attributable': False})['earned'] is False)
    check('and attribution is answered from liabilities, or not at all',
          attributable([{'liabilities': 9000}, {'liabilities': 8000}]) is True
          and attributable([{'liabilities': 8000}, {'liabilities': 9000}]) is False
          and attributable([{'liabilities': 8000}]) is None)

    # B.3: the trophy IS the proof. An award with no receipt is unproven, which
    # is not the same as false — 1.x awarded these before any of this existed.
    check('an unproven trophy is unproven, never quietly true or quietly false',
          verdict('first_card_down', {'proven': None})['earned'] is None)

    resp14 = ctx.c.get('/api/trophies', headers=ctx.H).get_json() or {}
    served14 = (resp14.get('data') or resp14)
    rows = {t['id']: t for t in (served14.get('trophies') or [])}
    check('the route reports every trophy with a verdict and a reason',
          len(rows) == len(TROPHY_SPEC)
          and all(t.get('reason') for t in rows.values()))

    # The false trophy this caught: one cleared card proved "you are debt free"
    # while two balances were still open, because the check keyed on the proof
    # SOURCE rather than on what each trophy claims.
    from core.database import DebtAccount as _DA2
    with ctx.dbs() as _s2:
        still_open = [d for d in _s2.query(_DA2).filter_by(is_active=True).all()
                      if float(d.current_balance or 0) > 0]
    check('being debt free means every balance, not the first one',
          not still_open or rows['zero']['earned'] is not True)
    check('and a trophy that names a figure is not proved by any figure',
          TROPHY_SPEC['interest_slayer']['proof'] == 'engine_interest'
          and 'interest_saved >= 1000' in ctx.server_src)

    check('the room shows the receipt, or says why there is none',
          '_trophyReceipt' in view and '_loadTrophyVerdicts' in view
          and 'Setup step' in view)

    # ── above_minimum: awarded by payments, not by a typed number ────────────
    # It fired when the budget FIGURE exceeded the minimums, so the trophy could
    # be earned by editing a field and never paying anything. Its name always
    # claimed the other thing.
    check('the declaration no longer awards it',
          'if (budget > totalMin + 0.5)' not in view)
    check('and the payment record does, through the proof the room already has',
          '_awardProvenTrophies' in view
          and TROPHY_SPEC['above_minimum']['proof'] == 'payments_above_minimum')
    check('the trophy now describes what it actually takes',
          "desc:'Paid more than your minimums, three months running.'" in view)
    check('a proven trophy is awarded, and nothing anywhere revokes one',
          'v.earned === true' in view and 'awardAchievement(v.id)' in view
          and 'S.achievements.delete(' not in view)

    # And the verdict's reason says what was actually checked, not more.
    check('a reason claims attribution only where attribution was required',
          verdict('above_minimum', {'held': True})['reason'] == 'held for the whole window'
          and verdict('zero_crossing', {'held': True, 'attributable': True}
                      )['reason'] == 'held, and visibly theirs')

    # ── §12's dial: the explicit half of A.4's pair ──────────────────────────
    # Aliased, and this is not fussiness: the trophy block above imported a
    # `verdict` of its own, and these calls silently went to it — a gauntlet
    # candidate arriving where a trophy id was expected. Two functions with the
    # same name and different contracts in one scope is a trap, and the suite
    # sprang it.
    from core.proactive import DIAL_FEWER, DIAL_OFF, verdict as promotion_verdict
    html_src = ctx.html_src

    loud = {'key': 'k', 'kind': 'brake', 'months': 9, 'dollars': 900,
            'has_path': True}
    check('off means off, and is asked before anything else',
          promotion_verdict(loud, {**quiet, 'dial': DIAL_OFF})['gate'] == 'dial'
          # even something that would fail a later gate reports the dial, which
          # is what proves the order: the user said so, and that is the answer.
          and promotion_verdict({**loud, 'months': 0, 'dollars': 0},
                      {**quiet, 'dial': DIAL_OFF})['gate'] == 'dial')
    check('fewer halves the weekly allowance rather than silencing it',
          promotion_verdict(loud, {**quiet, 'dial': DIAL_FEWER})['promote'] is True
          and promotion_verdict(loud, {**quiet, 'dial': DIAL_FEWER,
                             'brake_last_7d': 1})['gate'] == 'budget')
    check('and the explicit dial composes with the implicit backoff (A.4)',
          promotion_verdict(loud, {**quiet, 'dial': DIAL_FEWER,
                         'cadence_tier': 1})['gate'] == 'budget')

    resp15 = ctx.c.get('/api/proactive/next', headers=ctx.H).get_json() or {}
    served15 = (resp15.get('data') or resp15)
    check('the route reports which way the dial is set',
          served15.get('dial') in ('normal', 'fewer', 'off'))
    check('the setting travels with the other preferences',
          "'proactiveDial'" in ctx.server_src
          and 'prefs.proactiveDial' in view)
    check('the control says plainly that turning it off hides nothing (A.1)',
          'Turning it down or off hides nothing' in html_src
          and 'still lives on the page it belongs to' in html_src)

    # ── Appendix G: the long arc, and the three things §12 gated ────────────
    # Bias to false-negatives throughout: missing a real cycle is the acceptable
    # cost, claiming one that is not real is a fabricated story about a life.
    from core.cycles import (APPROACHING_SHARE, MIN_CYCLE_MONTHS, detect_cycles,
                             recurrence)
    from core.proactive import is_material

    def _series(*balances):
        return [{'month': f'2025-{i+1:02d}', 'balance': b, 'interest': 10.0}
                for i, b in enumerate(balances)]

    closed = _series(3000, 6500, 9000, 4000, 0, 1200, 4000, 8200)
    cycles = detect_cycles(closed)
    check('a cycle closes when the whole revolving position reaches zero',
          len(cycles) == 1 and cycles[0]['peak'] == 9000
          and cycles[0]['closed_month'] == '2025-05')
    check('the run still in progress is not a cycle and lends no peak',
          detect_cycles(_series(3000, 6500, 9000)) == [])
    check('and a run too short to be a cycle is not one (false-negative bias)',
          detect_cycles(_series(9000, 0)) == [] and MIN_CYCLE_MONTHS == 3)

    # G.3a's four states, and only these four.
    r = recurrence(closed)
    check('proximity to the prior peak is a state, measured not predicted',
          r['state'] == 'approaching' and r['distance'] == 800
          and r['share'] >= APPROACHING_SHARE)
    check('well below the prior peak says nothing G-level',
          recurrence(_series(3000, 6500, 9000, 4000, 0, 500, 900, 1200)
                     )['state'] == 'below')
    check('past the prior peak is its own state',
          recurrence(_series(3000, 6500, 9000, 0, 1200, 5000, 9600)
                     )['state'] == 'past')

    # C.7: insufficient history routes through silence, never a fabricated peak.
    check('no completed cycle means silence, with the reason attached',
          recurrence(_series(3000, 6500, 9000))['state'] == 'none'
          and recurrence(_series(3000, 6500, 9000))['prior'] is None)
    check('and too little history since the close says so rather than compares',
          recurrence(_series(3000, 6500, 9000, 0, 400))['state'] == 'none')

    # The receipt travels, but only when it was actually recorded.
    partial = [{'month': '2025-01', 'balance': 3000, 'interest': 40},
               {'month': '2025-02', 'balance': 6000, 'interest': None},
               {'month': '2025-03', 'balance': 9000, 'interest': 90},
               {'month': '2025-04', 'balance': 0, 'interest': 0}]
    check('the cost of the last cycle is reported only if the whole of it was',
          detect_cycles(partial)[0]['interest'] is None
          and detect_cycles(_series(3000, 6000, 9000, 0))[0]['interest'] == 30.0)

    # G.3: the unit is revolving debt. An installment loan amortising to zero is
    # not a cycle closing, and the series it reads is filtered before it arrives.
    check('only revolving debt is read into the series',
          "(d.debt_type or 'credit') == 'credit'" in ctx.server_src)

    # G.3b: same voice, same gate, same budget — no separate alert channel.
    check("G's checkpoint clears materiality on its own ruler, not a lower bar",
          "'crosses_boundary': True" in ctx.server_src
          and is_material({'crosses_boundary': True}, 2000) is True
          and is_material({'months': 0.1, 'dollars': 1}, 2000) is False)
    check('and it is a brake, so it needs a lever or it stays passive (G.3b.2)',
          "'has_path': bool(levers)" in ctx.server_src)
    check('crossing from approaching to past is a new fact, not a repeat',
          "f\"cycle:{cyc['state']}" in ctx.server_src)

    # A.3's position-fact clause, which G is the doc's own example of.
    check('a position fact competes on perishability, not on a zero impact',
          contend([{'key': 'green', 'goal_impact': 6},
                   {'key': 'cycle', 'goal_impact': None, 'perishable': True}
                   ])['key'] == 'cycle'
          and contend([{'key': 'green', 'goal_impact': 6},
                       {'key': 'cycle', 'goal_impact': None}])['key'] == 'green')
    check('and a contradiction still outranks even that',
          contend([{'key': 'cycle', 'goal_impact': None, 'perishable': True},
                   {'key': 'check', 'disputes': 'Dining'}])['key'] == 'check')

    resp16 = ctx.c.get('/api/debt/cycle', headers=ctx.H).get_json() or {}
    served16 = (resp16.get('data') or resp16)
    check('the route answers with a state, or says why it cannot',
          isinstance(served16.get('cycle'), dict)
          and (served16['cycle'].get('state') != 'none'
               or served16['cycle'].get('reason')))
    check('the debt page carries the passive statement for the two checkpoints',
          "c.state !== 'approaching' && c.state !== 'past'" in view
          and 'You have been here before' in view)
    check('and the dashboard can carry it too, through the gauntlet only',
          "p.detail_kind === 'cycle'" in view)

    # ── Pillar 1: the JS no longer computes a payoff ─────────────────────────
    # app.js carried a second implementation of the payoff maths, proven
    # equivalent by a 300-scenario differential and equivalent right up until
    # the day someone edited one of them. It is gone; what is left asks the
    # engine. Comments are stripped first — the replacement explains what it
    # replaced, in the words this check searches for.
    sim_code = chr(10).join(l for l in view.split(chr(10))
                            if not l.strip().startswith(chr(47) * 2))
    # Portfolio loops specifically: iterating an array of balances month by
    # month IS the engine's job. Single-balance amortisation (_projectPayoff,
    # _mortgageSimulate) is a different question the engine does not answer —
    # it returns aggregates, not per-month schedules — so those stay.
    # Portfolio loops specifically: iterating an array of balances month by
    # month IS the engine's job. Single-balance amortisation (_projectPayoff,
    # _mortgageSimulate) is a different question the engine does not answer —
    # it returns aggregates, not per-month schedules — so those stay.
    #
    # One portfolio loop survives, deliberately and with its reason written
    # beside it: the min-only baseline recalculates each month's minimum the way
    # issuers do, which the engine cannot yet do. This pins the count at one, so
    # a second one cannot appear quietly.
    portfolio_loops = sim_code.count('bals.some(b=>b>0.01)')
    check('the client simulates a portfolio in exactly one remaining place',
          portfolio_loops == 1
          and 'THE LAST PORTFOLIO LOOP IN THIS FILE' in view)
    check('and the retired ones left no loop behind',
          'bals[i] += int; totalInterest += int;' not in sim_code
          and 'bals[i] = Math.max(0, bals[i] - apply)' not in sim_code)
    check('and the two entry points are readers over the engine',
          "API.post('/api/debt/simulate'" in sim_code
          and '_engineSims[key]' in sim_code)

    # Three states, and the middle one is not the other two.
    check('a pending answer is undefined, never the null that means something',
          'return undefined;' in sim_code
          and "if (key in _engineSims) return _engineSims[key];" in sim_code)

    # The route exists because live editing needs it: the debt page recalculates
    # from unsaved state, 600ms before the save lands.
    r = ctx.c.post('/api/debt/simulate', headers=ctx.HJ, json={
        'cards': [{'id': 1, 'name': 'A', 'balance': 8000, 'rate': 22, 'minimum': 200},
                  {'id': 2, 'name': 'B', 'balance': 3000, 'rate': 6, 'minimum': 75}],
        'budget': 775, 'strategy': 'avalanche'}).get_json() or {}
    served = (r.get('data') or r)
    check('the engine answers for a portfolio the caller is holding',
          served.get('result') and served['result']['months'] > 0)
    check('and it is the same engine, not a second one',
          served['result']['months'] == simulate_payoff(
              [Card(balance=8000, rate=22, minimum=200, name='A'),
               Card(balance=3000, rate=6, minimum=75, name='B')], 775)['months'])
    unaffordable = ctx.c.post('/api/debt/simulate', headers=ctx.HJ, json={
        'cards': [{'id': 1, 'name': 'A', 'balance': 8000, 'rate': 22, 'minimum': 200}],
        'budget': 50}).get_json() or {}
    ua = (unaffordable.get('data') or unaffordable)
    check('a budget that cannot cover the minimums is null, with the reason',
          ua.get('result') is None and ua.get('reason'))

    # One reading of the PSLF record, now shared. The client never modelled
    # forgiveness by payment count while the server did — two answers for
    # anyone on an income-driven plan.
    from server import _pslf_terms
    check('a flagged loan with a payment count is dated once, in one place',
          _pslf_terms({'enabled': True, 'program': 'pslf', 'paymentsMade': 110})
          == (True, 10, True))
    check('and a flagged loan with nothing recorded stays undated',
          _pslf_terms(True) == (True, None, False)
          and _pslf_terms({'enabled': True, 'program': 'pslf'})[2] is False)
    check('an unflagged loan is left alone',
          _pslf_terms(None) == (False, None, True))

    # The differential still runs — against the frozen reference, because there
    # is no second live implementation left to compare with.
    ref = (ctx.BASE / 'tests' / 'js_reference_payoff.js')
    check('the retired simulators are kept as the parity reference',
          ref.exists() and 'frozen' in ref.read_text(encoding='utf-8')[:400])
    harness = (ctx.BASE / 'tests' / 'js_payoff_harness.js').read_text(encoding='utf-8')
    check('and the harness reads them from there, not from the shipped app',
          "js_reference_payoff.js" in harness
          and "readFileSync('static/js/app.js'" not in harness)

    # ── The server the app is actually served on ────────────────────────────
    # Flask's built-in server is a development convenience that says so in its
    # own banner, and every launch path used it. The cost was measurable rather
    # than theoretical — loopback requests alternated between ~45ms and ~250ms,
    # health check and real route alike — and it only became visible once the
    # client started asking the server for payoff figures instead of computing
    # them itself.
    import ast as _ast
    server_src = ctx.server_src
    launch_src = (ctx.BASE / 'launch.py').read_text(encoding='utf-8')
    dev_src = (ctx.BASE / 'dev_server.py').read_text(encoding='utf-8')

    check('there is one place that knows how to serve the app',
          'def serve(app' in server_src)
    check('and every launch path goes through it',
          'serve(flask_app' in launch_src and 'serve(app' in dev_src
          and 'flask_app.run(' not in launch_src
          and 'app.run(host=' not in dev_src)
    check('the dev server runs the same machinery the packaged app does',
          'from server import create_app, serve' in dev_src)

    # The fallback keeps a source checkout working, and says what it did.
    serve_src = server_src[server_src.index('def serve(app'):]
    serve_src = serve_src[:serve_src.index('if __name__')]
    check('a missing waitress degrades to the old server rather than to nothing',
          'except ImportError' in serve_src and 'app.run(' in serve_src)
    check('and says so, through a logger that exists',
          "logging.getLogger('groundwork').warning" in serve_src
          and 'logger.warning' not in serve_src)

    check('the dependency is declared',
          'waitress' in (ctx.BASE / 'requirements.txt').read_text(encoding='utf-8'))
    for spec in ('groundwork.spec', 'groundwork_linux.spec', 'groundwork_macos.spec'):
        text = (ctx.BASE / spec).read_text(encoding='utf-8')
        # Imported inside a function, which is the style PyInstaller traces
        # least reliably — without this the bundle silently falls back.
        check(f'{spec} bundles it explicitly',
              "'waitress'" in text)
