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
