"""What has been earned, and the proof that it was — the Trophy Room's standard.

B.3: "the trophy *is* the proof." §12 gated this until the per-case standard was
pinned, because building first and pinning after is how "evidence-backed"
quietly degrades to "declared-backed" (§11, the D.4 failure). This module is
that pinning, in code rather than in a comment, so the rule and the thing it
governs cannot drift apart.

Three classes, decided per trophy against D.4 (credit deliberate action above
the baseline), D.3/D.6 (never the market, never a raise) and E.2a (a shift is
not a fact until it has held):

**ACTION** — instantly provable, and cannot later become untrue. A card hitting
zero is the blueprint's own example: it happened, it is in the ledger, and no
subsequent month can un-happen it. These fire on the triggering action.

**DURABLE** — the underlying number can revert, or its cause may not be the
user's. Net worth crossing zero, a DTI threshold, a $500 buffer: each can be
undone next month, and each can be reached without the user doing anything —
a market gain or a raise. So they fire only after the condition has held across
`DURABILITY_MONTHS` recorded observations AND the change is attributable.

**SETUP** — not trophies. Entering income, adding five categories, running a
calculation, adding a holding: real things a person did, and none of them a
change in their money. D.4's reasoning about praising a floor applies directly
— the trophy is meant to be a receipt, and there is no financial change here to
receipt. They remain in the app as setup progress, which is a different object
and is not sold as an achievement.

**On attribution.** D.6 forbids crediting a paper gain, and the honest problem
is that snapshots record assets and liabilities, not what moved inside assets.
So the app cannot prove a net-worth rise was not the market — but it CAN prove
the part that is the user's: liabilities falling is debt being paid, which is
action. A durable net-worth trophy therefore requires liabilities to have
fallen across the window. If assets did all the work, the number is reported
wherever numbers are reported and no trophy is claimed for it.
"""

# The same floor every other reader in this codebase uses for "a record rather
# than an anecdote" — three recorded observations. E.2a asks for the pattern to
# hold long enough to satisfy the normal threshold; this is that threshold,
# borrowed rather than invented so the app has one answer to "how long is long
# enough" instead of five.
DURABILITY_MONTHS = 3

ACTION = 'action'
DURABLE = 'durable'
SETUP = 'setup'

# The pinned table. Every id here exists in ACHIEVEMENTS in app.js; the classes
# and proofs are what §12 gated.
TROPHY_SPEC = {
    # ── Fires on the action ──────────────────────────────────────────────────
    'first_card_down': {'class': ACTION, 'proof': 'debt_cleared'},
    'zero':            {'class': ACTION, 'proof': 'debt_cleared'},
    'chipping_away':   {'class': ACTION, 'proof': 'balance_history'},
    'halfway':         {'class': ACTION, 'proof': 'balance_history'},
    'interest_slayer': {'class': ACTION, 'proof': 'engine_interest'},
    'first_green':     {'class': ACTION, 'proof': 'closed_month'},
    'back_to_back':    {'class': ACTION, 'proof': 'closed_month'},
    'unbreakable':     {'class': ACTION, 'proof': 'closed_month'},
    'bounce_back':     {'class': ACTION, 'proof': 'closed_month'},
    'overachiever':    {'class': ACTION, 'proof': 'closed_month'},
    'goal_reached':    {'class': ACTION, 'proof': 'closed_month'},

    # `above_minimum` fires today on SETTING a payment above the minimums, which
    # is a declaration and not an action — the money has not moved. It is
    # classed here on what would make it a receipt: payments actually landing
    # above the minimums, which needs the payment record rather than the
    # setting. Left DURABLE deliberately: one payment above the floor is a
    # moment, and the trophy names a habit.
    'above_minimum':   {'class': DURABLE, 'proof': 'payments_above_minimum',
                        'attribution': False},

    # ── Fires only once it has held, and only if it was theirs ───────────────
    'safety_net':      {'class': DURABLE, 'proof': 'buffer_held', 'attribution': False},
    'moving_needle':   {'class': DURABLE, 'proof': 'net_worth_series', 'attribution': True},
    'zero_crossing':   {'class': DURABLE, 'proof': 'net_worth_series', 'attribution': True},
    'dti_threshold':   {'class': DURABLE, 'proof': 'dti_series', 'attribution': True},
    'goal_on_track':   {'class': DURABLE, 'proof': 'pace_series', 'attribution': False},
    'groundwork_laid': {'class': DURABLE, 'proof': 'composite', 'attribution': True},

    # ── Setup, not trophies ──────────────────────────────────────────────────
    'eyes_open':       {'class': SETUP, 'proof': None},
    'honest_count':    {'class': SETUP, 'proof': None},
    'full_picture':    {'class': SETUP, 'proof': None},
    'real_cost':       {'class': SETUP, 'proof': None},
    'net_worth_known': {'class': SETUP, 'proof': None},
    'first_snapshot':  {'class': SETUP, 'proof': None},
    'first_position':  {'class': SETUP, 'proof': None},
}


def held(observations, predicate, months=DURABILITY_MONTHS):
    """Whether a condition held across the last `months` recorded observations.

    Recorded, not elapsed: a user who opened the app twice in a year has two
    observations, and three months of silence is not three months of evidence.
    Fewer observations than the window is not a failure and not a pass — it is
    `None`, which the caller renders as "not yet provable" rather than as "not
    earned".
    """
    series = list(observations or [])
    if len(series) < months:
        return None
    return all(bool(predicate(o)) for o in series[-months:])


def attributable(snapshots):
    """Whether the user's own action is visibly part of a net-worth improvement.

    D.6: a paper gain is not an achievement and a raise is not a virtue. What
    the record can prove is the other side of the sheet — liabilities falling is
    debt being paid, and debt is not paid by the market. So this asks only that
    question, and answers None when there is not enough history to ask it.

    It does not claim the market contributed nothing. It claims the user did.
    """
    series = [s for s in (snapshots or []) if s.get('liabilities') is not None]
    if len(series) < 2:
        return None
    return float(series[-1]['liabilities']) < float(series[0]['liabilities'])


def verdict(trophy_id, evidence=None):
    """Whether a trophy may be shown as earned, and under which rule.

    Returns {'class', 'earned', 'rule', 'reason'}. `earned` is None wherever the
    record cannot answer — a trophy awarded in 1.x before any of this existed is
    not retroactively false, it is simply unproven, and B.3's whole claim is
    that a trophy is its proof. Showing one with no receipt would be the
    declared-backed failure this module exists to prevent.
    """
    spec = TROPHY_SPEC.get(trophy_id)
    if not spec:
        return {'class': None, 'earned': None, 'rule': None,
                'reason': 'not in the pinned table'}

    ev = evidence or {}
    if spec['class'] == SETUP:
        return {'class': SETUP, 'earned': False, 'rule': 'setup',
                'reason': 'setup progress, not an earned trophy (D.4)'}

    if spec['class'] == ACTION:
        proven = ev.get('proven')
        return {'class': ACTION, 'earned': proven, 'rule': 'action',
                'reason': ('proved by the ledger' if proven
                           else 'no receipt recorded for it' if proven is None
                           else 'the ledger does not show it')}

    # DURABLE
    persisted = ev.get('held')
    if persisted is None:
        return {'class': DURABLE, 'earned': None, 'rule': 'durable',
                'reason': f'needs {DURABILITY_MONTHS} recorded months to prove it held'}
    if not persisted:
        return {'class': DURABLE, 'earned': False, 'rule': 'durable',
                'reason': 'it did not hold'}
    if spec.get('attribution'):
        credit = ev.get('attributable')
        if credit is None:
            return {'class': DURABLE, 'earned': None, 'rule': 'durable',
                    'reason': 'not enough history to tell whose change it was'}
        if not credit:
            return {'class': DURABLE, 'earned': False, 'rule': 'durable',
                    'reason': "the improvement is not visibly the user's (D.6)"}
    # The reason says what was actually checked. Only trophies that require
    # attribution had it checked, and claiming otherwise would be a small lie
    # in the field whose entire job is to explain a verdict.
    return {'class': DURABLE, 'earned': True, 'rule': 'durable',
            'reason': ('held, and visibly theirs' if spec.get('attribution')
                       else 'held for the whole window')}
