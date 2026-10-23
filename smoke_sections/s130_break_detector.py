"""The break-detector, Appendix F.8 only (`gw 2.0/BREAK_DETECTOR.md`, ruled and authorised 2026-09-28).

    shape       a sustained level shift of >= 2 recorded months, material against the series' own spread; one
                odd month is a wobble; a gap is never a zero and never makes a break
    null model  the thresholds hold on every gate: false breaks <= 5% on trend-free series at every noise
                level, known shifts found at the floors in core.breaks.DETECTION_FLOOR - or the detector does
                not ship (a loosened threshold is shown to fail it)
    boundary    a break scopes evidence: a reading resting on months before it is set aside, keeping what it
                read as its receipt (nothing is erased), and returns only on post-break evidence; a cut that
                explains its own category's drop is not a break for that category
    reach       a category break reaches its category; an income break, or categories moving together over a
                quarter of spending, reaches every reading
    immune      what the user said is never touched by a break
    fund pace   post-break months only, and too few of them says so - never the old average
    words       the fact of the shift, never a cause, a duration or advice
    scope       no storage, no schema, no debt-cycle wiring (G named, not connected)
"""
import ast
import json
import re
from datetime import datetime, timedelta

_RUN = [0]
_MONTHS = [f'2025-{m:02d}' for m in range(10, 13)] + [f'2026-{m:02d}' for m in range(1, 9)]   # 11 complete months


def _series(values):
    return list(zip(_MONTHS[:len(values)], values))


def _detector_cases():
    from core.breaks import detect_break
    out = {}
    flat = [300, 310, 295, 305, 300, 290, 315, 300, 305, 298, 302]
    out['Bd1 a flat series has no break'] = detect_break(_series(flat)) is None
    spike = flat[:9] + [640, 300]
    out['Bd2 one odd month is a wobble, never a break'] = detect_break(_series(spike)) is None
    b = detect_break(_series(flat[:8] + [520, 515, 530]))
    out['Bd3 a sustained shift is a break: its month, direction and levels'] = (
        b is not None and b['month'] == _MONTHS[8] and b['direction'] == 'up'
        and 295 <= b['before'] <= 305 and b['after'] == 520 and b['months_after'] == _MONTHS[8:11])
    b = detect_break(_series(flat[:9] + [520, 300]))
    out['a shift that returns is not a new level'] = b is None
    gapped = [(m, v) for (m, v) in _series(flat) if m not in ('2026-06', '2026-07')]
    out['Bd4 missing months are gaps: they neither create nor confirm a break'] = detect_break(gapped) is None
    b = detect_break(_series(flat[:9] + [150, 140]))
    out['two recorded months at a new level are enough - the ruled minimum'] = (
        b is not None and b['direction'] == 'down' and b['month'] == _MONTHS[9])
    out['too little history before a run: no yardstick, no break'] = detect_break(_series([300, 300, 520, 530])) is None
    return out


def _willingness_cases():
    from core.willingness import observed_readings, breaks, effective
    out = {}
    months = set(_MONTHS)
    income = {m: 4000.0 for m in _MONTHS}
    income['2025-09'] = 4000.0
    debits = {m: 2000.0 for m in _MONTHS}

    # A category with a sacred 'restored' reading early on (a cut the user set back), then a level shift late.
    # (Item 39 removed the "kept through tight months" reading these cases used to rest on.)
    kept = [{'id': 11, 'date': '2025-10-05', 'category': 'Hobbies', 'old': 80.0, 'new': 50.0},
            {'id': 12, 'date': '2025-11-05', 'category': 'Hobbies', 'old': 50.0, 'new': 80.0},
            {'id': 13, 'date': '2025-10-05', 'category': 'Dining', 'old': 350.0, 'new': 250.0},
            {'id': 14, 'date': '2025-11-05', 'category': 'Dining', 'old': 250.0, 'new': 350.0}]
    hob = {('Hobbies', m): v for m, v in zip(_MONTHS, [60, 62, 58, 61, 60, 59, 63, 60, 140, 150, 145])}
    din = {('Dining', m): 300.0 for m in _MONTHS}
    spend = {**hob, **din}
    r = {x['category']: x for x in observed_readings(['Hobbies', 'Dining'], kept, spend, months, income, debits)}
    h = r['Hobbies']
    out['Bd5 a local break sets its category\'s reading aside, the break and the old reading as receipt'] = (
        h['stance'] == 'unclassified' and h['reason'] == 'break' and h['receipt']['break']['month'] == '2026-06'
        and h['receipt']['break']['scope'] == 'category' and h['receipt']['set_aside']['reason'] == 'restored')
    out['nothing is erased: the set-aside reading keeps the edits it read'] = (
        h['receipt']['set_aside']['receipt']['cut']['id'] == 11 and h['receipt']['set_aside']['receipt']['restore']['id'] == 12)
    out['Bd5 a local break reaches no other category'] = r['Dining']['reason'] == 'restored'

    # The user's own cut explains the drop that follows it: no boundary for that category.
    cut = {'id': 1, 'date': '2026-02-05', 'category': 'Dining', 'old': 450.0, 'new': 300.0}
    din2 = {('Dining', m): v for m, v in zip(_MONTHS, [430, 425, 440, 435, 290, 280, 295, 285, 290, 288, 292])}
    found = breaks(['Dining'], [cut], din2, months, income, debits)
    rr = observed_readings(['Dining'], [cut], din2, months, income, debits)[0]
    out['a cut that explains its own category\'s drop is not a break - the cut that held still reads'] = (
        'dining' not in found['local'] and rr['reason'] == 'cut_held')
    late = dict(cut, date='2026-03-02')     # spending fell in February; the budget caught up in March
    out['a cut recorded the month after the drop still explains it (spend first, budget after)'] = (
        'dining' not in breaks(['Dining'], [late], din2, months, income, debits)['local'])
    early = dict(cut, date='2025-11-20')    # an edit months before is no explanation
    out['an edit months away from the drop explains nothing'] = (
        'dining' in breaks(['Dining'], [early], din2, months, income, debits)['local'])
    found = breaks(['Dining'], [], din2, months, income, debits)
    out['the same drop with no edit behind it is a break'] = found['local'].get('dining', {}).get('month') == '2026-02'

    # Income breaks: broad, reaching every reading with pre-break evidence.
    inc2 = dict(income, **{'2026-07': 2600.0, '2026-08': 2500.0})
    r = {x['category']: x for x in observed_readings(['Hobbies', 'Dining'], kept, {**din, **{('Hobbies', m): 60.0 for m in _MONTHS}},
                                                     months, inc2, debits)}
    out['Bd6 an income break reaches every reading resting on earlier months'] = (
        all(x['reason'] == 'break' and x['receipt']['break']['scope'] == 'income' for x in r.values()))

    # Categories moving together over a quarter of spending: broad.
    tog = {('Rent2', m): 900.0 for m in _MONTHS}
    tog.update({('A', m): v for m, v in zip(_MONTHS, [400] * 8 + [700, 710, 705])})
    tog.update({('B', m): v for m, v in zip(_MONTHS, [300] * 8 + [520, 510, 515])})
    found = breaks(['A', 'B', 'Rent2'], [], tog, months, income, {m: 2000.0 for m in _MONTHS})
    out['Bd6 categories changing level together over a quarter of spending: one broad break'] = (
        found['broad'] is not None and found['broad']['scope'] == 'together'
        and found['broad']['categories'] == ['A', 'B'] and found['broad']['month'] == '2026-06')
    small = {('A', m): v for m, v in zip(_MONTHS, [40] * 8 + [70, 71, 70])}
    small.update({('B', m): v for m, v in zip(_MONTHS, [30] * 8 + [52, 51, 52])})
    found = breaks(['A', 'B'], [], small, months, income, {m: 2000.0 for m in _MONTHS})
    out['two small envelopes moving together stay local (under a quarter of spending)'] = (
        found['broad'] is None and set(found['local']) == {'a', 'b'})

    # Recovery by proof only: a cut after the break that holds three months reads again, on post-break months.
    hob3 = {('Hobbies', m): v for m, v in zip(_MONTHS, [60, 62, 58, 61, 150, 145, 150, 120, 118, 119, 117])}
    cut2 = {'id': 2, 'date': '2026-04-10', 'category': 'Hobbies', 'old': 160.0, 'new': 125.0}
    rr = observed_readings(['Hobbies'], [cut2], hob3, months, income, debits)[0]
    out['Bd7 a reading returns on post-break evidence alone, citing only months since the break'] = (
        rr['reason'] == 'cut_held' and rr.get('boundary', {}).get('month') == '2026-02'
        and all(m >= '2026-02' for m in rr['receipt']['months']))

    # Declarations are immune.
    decl = [{'id': 1, 'category': 'Hobbies', 'stance': 'protect', 'said_at': '2025-10-01T00:00:00', 'answer_kind': 'claim'}]
    eff = effective(observed_readings(['Hobbies'], kept, spend, months, income, debits), decl)
    out['Bd8 what the user said stands through a break, untouched'] = (
        eff['hobbies']['stance'] == 'protected' and eff['hobbies']['source'] == 'declared'
        and eff['hobbies']['declaration'] == decl[0])

    # A break with nothing concluded before it adds nothing to the picture.
    plain = {('Quiet', m): v for m, v in zip(_MONTHS, [60] * 8 + [140, 150, 145])}
    rq = observed_readings(['Quiet'], [], plain, months, income, debits)[0]
    out['Bd13 a break with no reading to set aside makes no claim (the empty state stays empty)'] = (
        rq['reason'] == 'no_evidence' and rq['stance'] == 'unclassified')
    return out


def _fund_cases(dbs):
    from core.solution import fund_pace
    from core.database import SinkingFund
    import server
    out = {}
    brk = {'month': '2026-07', 'direction': 'down', 'before': 200.0, 'after': 60.0}
    p = fund_pace(3000, 500, 200, deadline_months=20, observed_monthly=60.0, samples=2, since_break=brk)
    out['Bd12 too few months since a break: the plan\'s date, flagged - never the old average'] = (
        p['pace_source'] == 'plan' and p['insufficient_since_break'] is True and p['pace_monthly'] == 200.0
        and p['since_break']['month'] == '2026-07')
    p = fund_pace(3000, 500, 200, deadline_months=20, observed_monthly=60.0, samples=3, since_break=brk)
    out['enough months since a break: the pace is the post-break one'] = (
        p['pace_source'] == 'observed' and p['pace_monthly'] == 60.0 and p['insufficient_since_break'] is False)
    p = fund_pace(3000, 500, 200, deadline_months=20, observed_monthly=150.0, samples=6)
    out['no break: fund pace exactly as before'] = (
        p['pace_source'] == 'observed' and p['since_break'] is None and p['insufficient_since_break'] is False)

    # End to end: seven months of $200, then two of $60, in the Historian.
    _RUN[0] += 1
    now = datetime.now()
    first_of = datetime(now.year, now.month, 1)

    def month_back(k):
        y, m = first_of.year, first_of.month - k
        while m <= 0:
            y, m = y - 1, m + 12
        return datetime(y, m, 10)

    with dbs() as s:
        f = SinkingFund(name=f'S130 Fund {_RUN[0]}', target_amount=5000, current_amount=1000, monthly_contribution=200)
        s.add(f)
        s.flush()
        for k in range(9, 0, -1):
            e = server.log_historian_event(s, 'sinking_fund_contribution_variance', expected_value=200.0,
                                           actual_value=(200.0 if k > 2 else 60.0),
                                           context={'sinking_fund_id': f.id})
            e.created_at = month_back(k)
        s.commit()
        fid = f.id
    with dbs() as s:
        b = server.fund_contribution_break(s, fid)
        whole, n_all = server.fund_observed_monthly(s, fid)
        since, n_since = server.fund_observed_monthly(s, fid, since=b['month'] if b else None)
    out['Bd12 the contributions\' break is found from the Historian, at the first $60 month'] = (
        b is not None and b['direction'] == 'down' and b['month'] == month_back(2).strftime('%Y-%m'))
    out['Bd12 the pace since the break counts only post-break months and contributions'] = (
        n_all == 9 and n_since == 2 and since is not None and since < whole)
    return out


def run(ctx):
    check = ctx.check
    import core.breaks as cb

    r = cb.null_model()
    fp = r['false']
    check('s130 null model: false breaks on trend-free series stay <= 5% at every noise level '
          + ' '.join(f'cv{k:.2f}={v:.3f}' for k, v in fp.items()),
          all(v <= cb.MAX_FALSE_BREAK_RATE for v in fp.values()))
    check('s130 null model: known shifts are found at the committed floors '
          + ' '.join(f'cv{k[0]:.2f}x{k[1]}={v:.2f}' for k, v in r['found'].items()),
          all(r['found'][k] >= floor for k, floor in cb.DETECTION_FLOOR.items()))
    # The gate is what keeps the rule "if no threshold separates them, it does not ship" true.
    saved = (cb.Z_MIN, cb.EACH_MULTIPLE, cb.MIN_RELATIVE)
    try:
        cb.Z_MIN, cb.EACH_MULTIPLE, cb.MIN_RELATIVE = 1.5, 0.5, 0.05
        loose = cb.null_model(trials=600, shifted=100)
        check('s130 mutation caught: a loosened threshold fails the null model (the detector would not ship)',
              any(v > cb.MAX_FALSE_BREAK_RATE for v in loose['false'].values()))
    finally:
        cb.Z_MIN, cb.EACH_MULTIPLE, cb.MIN_RELATIVE = saved
    saved = cb.MIN_AFTER
    try:
        cb.MIN_AFTER = 1
        from core.breaks import detect_break
        flat = [300, 310, 295, 305, 300, 290, 315, 300, 305, 298, 640]
        check('s130 mutation caught: a one-month run would make a wobble a break', detect_break(_series(flat)) is not None)
    finally:
        cb.MIN_AFTER = saved

    for name, ok in _detector_cases().items():
        check(f's130 {name}', ok)
    for name, ok in _willingness_cases().items():
        check(f's130 {name}', ok)
    for name, ok in _fund_cases(ctx.dbs).items():
        check(f's130 {name}', ok)

    # Scope: no storage, no schema, no debt-cycle wiring.
    src = ctx.BASE.joinpath('core/breaks.py').read_text(encoding='utf-8')
    wsrc = ctx.BASE.joinpath('core/willingness.py').read_text(encoding='utf-8')
    imports = set()
    for s in (src, wsrc):
        for n in ast.walk(ast.parse(s)):
            if isinstance(n, ast.ImportFrom):
                imports.add(n.module or '')
            elif isinstance(n, ast.Import):
                imports.update(a.name for a in n.names)
    check('s130 B8 the detector touches no storage and reads no usage (imports: random, statistics, the engines only)',
          not any(i.startswith(('core.database', 'sqlalchemy', 'server')) for i in imports)
          and not re.search(r'session_start|budget_reviewed|proactive_(shown|dismissed)|engagement', src + wsrc))
    check('s130 B9 the debt cycle is named, not wired: nothing on this path imports core.cycles',
          'core.cycles' not in imports)
    import migrate
    # Was pinned to the Willingness Layer's SCHEMA_VERSION, which proved "no schema change" only until the next
    # legitimate bump (the household facts, 2026-10-02). What B8 means is that the detector owns no schema.
    _db_src = ctx.BASE.joinpath('core/database.py').read_text(encoding='utf-8')
    _mig_src = ctx.BASE.joinpath('migrate.py').read_text(encoding='utf-8')
    check('s130 B8 no schema of its own: no break table, and nothing of the detector in the migration',
          not re.search(r"__tablename__ = '[a-z_]*break", _db_src) and not re.search(r'\bbreaks?\b|detect_break', _mig_src)
          and bool(migrate.SCHEMA_VERSION))

    # Words: the fact of the shift, never a cause, a duration or advice (ruling 7).
    js = ctx.BASE.joinpath('static/js/teaching/willingness.js').read_text(encoding='utf-8')
    fjs = ctx.BASE.joinpath('static/js/teaching/funds.js').read_text(encoding='utf-8')
    text = js.split('function _breakText(r) {', 1)[1].split('\n  }\n', 1)[0] \
        + fjs.split('const brk = p.since_break;', 1)[1].split('const lands', 1)[0]
    story = r'\bbecause\b|\bdue to\b|for now|temporar|\bwill\b|\btrend|probably|likely|\bseems?\b|\bshould\b|\btry\b|consider'
    found = re.findall(story, text, re.I)
    check('s130 B7 the break is stated as a fact: no cause, no duration, no advice', not found)
    if found:
        print(f'        found: {found}')
    check('s130 mutation caught: a cause added to the break text',
          bool(re.search(story, text + " 'because your hours were cut'", re.I)))
    check('s130 B7 the break is shown in the working picture only - no dashboard, no unprompted voice',
          not re.search(r"since_break|receipt\.break|reason === 'break'|/api/willingness",
                        ctx.BASE.joinpath('static/js/teaching/proactive.js').read_text(encoding='utf-8'))
          and not re.search(r'core\.breaks|detect_break', ctx.app_src))
