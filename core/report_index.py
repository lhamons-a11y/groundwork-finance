"""Item 115 stages 4 and 6 (gw 2.0/ASK_FOR_A_REPORT.md P3-P9; Rob 2026-10-31, C1-C11; 2026-11-01 "lets complete the
rest of the stages"): a request for a report, in the person's own words, read into sections.

    read(reader, text, terms=None, helper=None) -> {outcome, sections, style, said, question, choices, found, step, ...}

The index reads first, with no model (P3, P6 step 1): requests to act, the style, words that are not subjects, the
period (core/periods.py, P5), the record's own names (P4), then shape, subject and template terms. Phi is asked only
where the index cannot decide, and only to choose from a closed list under a grammar (P7, P8):
    H-a  two meanings   "payments" with nothing beside it: one of the readings, or can't tell
    H-b  unknown words  "the dog": one of the record's categories or payees, or none
    H-c  except/versus  a side of "except" or "versus" the index cannot name: one of the record's names, or none
Measured 2026-11-01 (section 14): phi never said "can't tell" where it was right for H-a and H-b, so those two only
advise - their pick is offered first, marked likely, and the person chooses. H-c builds on its pick and says it.
Every answer is checked against the record by code (grammar first, check second). Phi never reads a date, never
builds a section and never writes a figure (H22). With AI off, a doubt is a question with buttons (P12).

outcome: build | build_and_say | clarify | does_not_know | refuse_act | refuse | none
step:    1 the index built it; 2 it asked, or a helper chose between candidates; 3 nothing found (P6)
"""
import re

from core import agent_hands as ah
from core import periods
from core import report_sections as rs

# ── the built-in vocabulary (C4: changed only by Rob's ruling) ──────────────────────────────────────────────────────
STYLE_TERMS = [
    (r'\b(as|in) (a )?(table|tables|grid)\b|\btable form\b|\bjust the (numbers|figures)\b|\bspreadsheet\b', 'text_grid'),
    (r'\bcharts? first\b|\bquick look\b|\bat a glance\b|\bjust the (charts|graphs)\b', 'charts_first'),
    (r'\bwith (charts|graphs)\b|\bas (a )?(chart|graph)s?\b|\b(chart|graph) it\b', 'text_charts'),
    (r'\bread (it|this|that)?\s*(to me|out|aloud)\b|\bout loud\b|\baloud\b|\bjust (the )?(text|words)\b|\bno charts\b',
     'text_only'),
    (r'\bfor printing\b|\bto print\b|\bprintable\b|\bprint (it|this|that|out)\b|\b(as a |in )?pdf\b', 'print'),
    (r'\bcompact\b|\bshort version\b|\bsummary cards?\b|\bon my phone\b|\bone card\b', 'compact'),
]
SHAPE_TERMS = [   # P3, in the order they are tried; a later shape never overrides an earlier one
    (6, r'\bwhat if\b|\bif (we|i) (paid|pay|put|added|threw)\b|\bwhat would happen\b'),
    (5, r'\bcompared? (to|with)\b|\bversus\b|\bvs\.?\b|\bthan (last|in|the)\b|\bagainst last\b'),
    (1, r'\b(each|every|per|by|a) month\b|\bmonthly\b|\bmonth by month\b|\bmonth to month\b'),
    (2, r'\btrend\w*\b|\bover time\b|\bgo(ing|ne)? (up|down)\b|\bchanged?\b|\bhistory\b'),
    (4, r'\bhow much do (we|i) owe\b|\bwhere (do|does) (we|i|it) stand\b|\bright now\b|\bsnapshot\b|\btoday\b'),
    (3, r'\blist\b|\btransactions?\b|\bcharges\b|\bitemi[sz]e\b|\bwhere\b.*\b(going|go|went|coming from|comes from)\b|'
        r'\bwhich\b|\btop \d*\s*\w*|\branked\b|\bbiggest\b|\blargest\b|\bpaychecks\b|\bputting on\b'),
]
SUBJECT_TERMS = [   # P3: subject words; names from the record come first (P4)
    (10, r'\broom in (the|my|our) budget\b|\bheadroom\b|\bwhere (could|can|should) (i|we) (cut|find)\b|\bfind \$|'
         r'\bfree up\b|\bcut back\b'),
    (3, r'\bpayees?\b|\bmerchants?\b|\bwhere (we|i) shop\b'),
    (9, r'\bbills?\b.*\b(due|coming|upcoming|next)\b|\bupcoming bills?\b|\bwhat\'?s due\b|\bwhat is due\b|\bdue (soon|next)\b'),
    (8, r'\brecurring\b|\bsubscriptions?\b|\bprice (went up|increase|increases|changes?|steps?)\b|\bwhat recurs\b|'
        r'\brepeating charges\b'),
    (7, r'\bnet worth\b|\bbalances\b|\bhow much (do )?(we|i) have\b|\bin the bank\b|\bset aside\b'),
    (6, r'\bowe\b|\bowed\b|\bdebt balances?\b|\bdebt[- ]free\b|\bpay ?off date\b|\bwhat (is|\'s) left on\b'),
    (5, r'\bdebt payments?\b|\bloan payments?\b|\bcard payments?\b|\bpaid (toward|towards|down|into|off)\b|'
        r'\bpaying (toward|towards|down|off|into)\b|\bthrowing at\b|\bput(ting)? (toward|towards)\b|\bcar note\b|'
        r'\bpaid (on|to) (the |my |our )?(debts?|loans?|cards?)\b'),
    (4, r'\bbr(ing|ought) in\b|\bpay ?checks?\b|\bincome\b|\bearn(ed|ings)?\b|\bsalary\b|\bwages\b|\bcame in\b|'
        r'\bcoming in\b|\bhow much (did |do )?(we|i) (make|made)\b'),
    (1, r'\bspen[dt]\w*\b|\bcost\w*\b|\bdropp\w*\b|\bmoney (is )?go(ing)?\b|\bputting on\b|\bcharges?\b|\bbought\b|'
        r'\bpurchases?\b|\bexpenses?\b|\btransactions?\b|\bbudget\b'),
]
TEMPLATE_TERMS = [   # P3: a request that names a report needs only its settings
    (r'\b(spending|expense)s? (breakdown|report|summary)\b|\bbreakdown of (my |our )?spending\b',
     [('3.1', {}), ('1.1', {})]),
    (r'\bdebt report\b|\bdebt progress\b|\bhow is the debt going\b|\bdebts?\b.*\b(paid down|paid off|progress)\b',
     'debt_progress'),
    (r'\bdebt payoff (report|analysis|plan)\b', 'debt_payoff'),
    (r'\bcash ?flow\b|\bsavings rate\b', 'income_savings'),
    (r'\bmonthly (review|summary|report)\b', 'monthly'),
    (r'\byear[- ]end\b|\bfor (my |our |the )?(taxes|accountant)\b', 'year_end'),
    (r'\bnet worth (timeline|report)\b', 'net_worth'),
    (r'\bannual (summary|report)\b|\byear in review\b', 'annual'),
    (r'\b(how|what)\b.*\b(my|our|the) budget\b.*\blook\w*\b|\b(over|under|on) budget\b|\bbudget (check|report)\b',
     [('4.1', {})]),
]
# P6 step 2: a word with more than one meaning and nothing beside it to decide. Each reading is sections.
TWO_MEANINGS = [
    ('payments', r'\bpayments?\b', 'Which payments do you mean?',
     [('Debt payments', [('1.5', {})]), ('Bills that recur', [('3.8', {})]), ('Everything spent', [('3.1', {})])]),
    ('paying out', r'\bpaying out\b|\bgoing out\b', 'Which do you mean by paying out?',
     [('Everything spent', [('1.1', {})]), ('Debt payments', [('1.5', {})]), ('What recurs', [('4.8', {})])]),
]
# Things the record holds no subject for - said plainly, with what Groundwork can show instead (G3, R18)
NOT_SUBJECTS = [
    (r'\btransfers?\b', 'Transfers between your own accounts are left out of spending on purpose, so there is no '
                        'report of them. Groundwork can show what was spent, or each account\'s balance.',
     [('Everything spent', [('3.1', {})]), ('Each account', [('3.7', {})])]),
    (r'\b(comes?|taken|came) out of (my|our|the) (pay ?)?checks?\b|\bbefore i (ever )?see it\b|\bwithh[oe]ld\w*\b|'
     r'\bdeductions?\b|\bpay ?stubs?\b|\btaxes taken\b',
     'The record holds what reached your accounts, not your pay stub, so Groundwork cannot show what was taken out '
     'before pay landed. It can show what came in.', [('What came in', [('3.4', {})])]),
]
VAGUE_ASK = r'\blately\b|\brecently\b|\bthese days\b|\bof late\b|\bthe past while\b|\ba while\b'
NOT_A_PERIOD = r'\bbetween paydays\b|\bpayday to payday\b|\beach pay period\b|\bbetween paychecks\b'
PERIOD_CHOICES = [('Last month', 'last month'), ('The last three months', 'the last three months'),
                  ('This year', 'this year'), ('Everything in the record', '')]
_ACT = re.compile(r'\b(e-?mail|send|share|upload|fax|forward|text me|schedule|remind me|automatically|on its own|'
                  r'every (mon|tues|wednes|thurs|fri|satur|sun)day|(mon|tues|wednes|thurs|fri|satur|sun)days)\b', re.I)
ACT_SAID = ("Groundwork never sends anything off this computer, and it never runs on its own. Here is the report: "
            "⎙ Print it or save it as a PDF to send it yourself, or Save… it and it runs again whenever you open it, "
            "with the period moved on.")
_EXCEPT = re.compile(r'\s*,?\s*\b(except( for)?|but not|other than|excluding|leaving out|not counting|without)\b\s*', re.I)
_VERSUS = re.compile(r'\s*,?\s*\b(versus|vs\.?|compared (to|with)|against)(?![a-z])\s*', re.I)
NO_PERIOD = {'2.6', '5.6', '3.6', '4.6', '6.6', '3.7', '4.7', '3.8', '4.8', '3.9', '4.9', '4.10', '6.10', '2.8'}
_WEAK = {'the', 'my', 'our', 'a', 'an', 'and', 'of', 'to', 'at', 'on', 'in', 'for', 'from', 'me', 'i', 'we', 'show',
         'what', 'how', 'much', 'many', 'is', 'are', 'was', 'were', 'been', 'have', 'has', 'had', 'did', 'do', 'does',
         'can', 'you', 'give', 'see', 'want', 'all', 'some', 'that', 'this', 'those', 'these', 'it', 'its', 'be', 'by',
         'with', 'about', 'report', 'month', 'months', 'year', 'last', 'each', 'every', 'per', 'so', 'far', 'store',
         'shop', 'place', 'stuff', 'things', 'money', 'spend', 'spent', 'spending', 'paid', 'pay', 'paying', 'payment',
         'payments', 'card', 'loan', 'account', 'debt', 'bill', 'bills', 'food', 'supplies', 'shops', 'care', 'fees',
         'other', 'total', 'totals', 'like', 'please', 'just', 'get', 'much', 'more', 'less', 'than', 'am', 'out',
         'up', 'down', 'over', 'into', 'there', 'their', 'they', 'where', 'which', 'when', 'who', 'why', 'let',
         'lets', 'looking', 'look', 'doing', 'going', 'been', 'lately', 'recently', 'today', 'now', 'something',
         'anything', 'everything', 'useful', 'interesting', 'good', 'nice', 'thing', 'need', 'know', 'tell', 'us',
         'whats', 'much', 'went', 'go', 'new', 'old'}
_FIRST_WORD_COMMON = {'corner', 'fresh', 'happy', 'golden', 'metro', 'pine', 'valley', 'luna', 'northside'}


def _rx(p):
    return re.compile(p, re.I)


_STYLE = [(_rx(p), k) for p, k in STYLE_TERMS]
_SHAPES = [(n, _rx(p)) for n, p in SHAPE_TERMS]
_SUBJECTS = [(n, _rx(p)) for n, p in SUBJECT_TERMS]
_TEMPLATES = [(_rx(p), t) for p, t in TEMPLATE_TERMS]


def _words(s):
    return re.findall(r"[a-z0-9]+", (s or '').lower())


def _has(text, phrase):
    return bool(re.search(r'(?<![a-z0-9])' + re.escape(phrase.lower()) + r'(?![a-z0-9])', text.lower()))


def _norm(s):
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 ]', ' ', (s or '').lower())).strip()


# ── the record's own names (P4) ─────────────────────────────────────────────────────────────────────────────────────
def record_names(reader):
    rows, _ = ah._rows(reader)
    cards, _, _ = ah._engine_inputs(reader)
    return {'payees': sorted({r['payee'] for r in rows if r['payee'] and rs._is_spend(r)}),
            'categories': sorted({r['category'] for r in rows if r['category'] and rs._is_spend(r)}),   # money_kind's
            'accounts': sorted({r['account'] for r in rows if r['account']}),
            'debts': [c.name for c in cards]}


def _named(text, names, kind):
    """The names of one kind the words mean: the whole name; every distinctive word of it; or a word only it has."""
    t = text.lower()
    whole = [n for n in names if _has(t, n)]
    if whole:
        return sorted(whole, key=len, reverse=True)[:1] if len(whole) > 1 and any(
            _has(a, b) for a in whole for b in whole if a != b) else whole
    tw = set(_words(t))
    dist = {n: [w for w in _words(n) if w not in ah._GENERIC_WORDS and w not in _WEAK and len(w) >= 3] for n in names}
    every = [n for n, ws in dist.items() if ws and len(ws) >= 2 and all(w in tw for w in ws)]
    if every:
        return every
    if kind == 'payees':        # brand-like first words: "Corner" is Corner Market, "QuickFuel" is QuickFuel
        hits = [n for n, ws in dist.items() if ws and ws[0] in tw and len(ws[0]) >= 4
                and sum(1 for o in dist.values() if ws[0] in o) == 1 and ws[0] not in _FIRST_WORD_COMMON]
        return hits
    hits = [n for n, ws in dist.items() if any(w in tw and sum(1 for o in dist.values() if w in o) == 1 for w in ws)]
    return hits


def _stem(a, b):
    return a == b or (len(a) >= 4 and len(b) >= 4 and (a.startswith(b) or b.startswith(a))) or \
        (len(a) >= 5 and len(b) >= 5 and a[:5] == b[:5])


def _categories(text, cats):
    """Categories the words mean - item 114's word list first ("eating out", "gas"), then the record's own names."""
    t = text.lower()
    phrases = {'grocery store': 'groceries', 'supermarket': 'groceries', 'gas station': 'gasoline / diesel',
               'take out': 'restaurants', 'takeout': 'restaurants', 'eat out': 'restaurants', 'dinner out': 'restaurants',
               'cell phone': 'phone / cell', 'power bill': 'electric', 'auto insurance': 'auto insurance'}
    for p, means in phrases.items():
        if _has(t, p):
            got = ah._category_match(means, cats)
            if got:
                return got
    for alias in ('eating out', 'car insurance', 'restaurant', 'dining', 'grocery', 'coffee', 'gas', 'fuel',
                  'electricity', 'electric', 'rent', 'gym', 'phone', 'pets', 'pet', 'clothes', 'internet'):
        if _has(t, alias):
            got = ah._category_match(alias, cats)
            if got:
                return got
    tw = [w for w in _words(t) if w not in _WEAK]
    hits = []
    for c in cats:
        cw = [w for w in _words(c) if w not in _WEAK and w not in ('and',)]
        if cw and any(_stem(a, b) for a in tw for b in cw):
            hits.append(c)
    return hits


_CAR = re.compile(r'\b(car|cars|vehicle|truck|auto)\b(?!\s+(note|loan|payments?|insurance|repairs?|finance))', re.I)
_LOANISH = re.compile(r'\b(car|auto|truck|vehicle)\s+(note|loan|payments?|finance)\b|\bpaid (on|toward|towards|off)\b|'
                      r'\bpaying (on|toward|towards|off|down)\b|\bthrowing at\b', re.I)


def _debts(text, debts):
    t = text.lower()
    got = _named(t, debts, 'debts')
    if not got and re.search(r'\b(car|auto|truck|vehicle)\s+(note|loan|payments?|finance)\b', t):
        got = [d for d in debts if re.search(r'\b(auto|car)\b', d.lower())]
    if not got and re.search(r'\bstudent\b', t):
        got = [d for d in debts if 'student' in d.lower()]
    return got


def _accounts(text, accounts):
    """An account only after "on", "in", "from", "with" or "using" - "savings rate" is not the savings account."""
    hits = []
    for a in accounts:
        for w in [a.lower()] + [w for w in _words(a) if w not in ah._GENERIC_WORDS and len(w) >= 4
                                and sum(1 for o in accounts if w in _words(o)) == 1]:
            if re.search(r'\b(on|in|from|with|using|to)\s+(the\s+|my\s+|our\s+)?' + re.escape(w) + r'\b', text, re.I):
                hits.append(a)
                break
    return hits


def _person_terms(text, terms):
    """C4: words a person accepted through H-d, kept on their computer. {said: {'kind', 'means'}}"""
    out = {}
    for said, v in (terms or {}).items():
        if isinstance(v, dict) and v.get('kind') in ('category', 'payee') and said and _has(text, said):
            out.setdefault(v['kind'], []).append(v['means'])
    return out


# ── reading ─────────────────────────────────────────────────────────────────────────────────────────────────────────
def _first(rxs, text):
    for n, rx in rxs:
        if rx.search(text):
            return n
    return None


def _template(t):
    for rx, tid in _TEMPLATES:
        if rx.search(t):
            if isinstance(tid, list):
                return None, [{'id': i, 'settings': dict(s)} for i, s in tid]
            tpl = next(x for x in rs.TEMPLATES if x['id'] == tid)
            return tpl['name'], [{'id': i, 'settings': dict(s)} for i, s in tpl['sections']]
    return None, None


def _with_period(sections, said):
    for s in sections:
        if said and s['id'] not in NO_PERIOD and not s['settings'].get('period'):
            s['settings']['period'] = said
    return sections


def _section(shape, subj, settings=None):
    return {'id': f'{shape}.{subj}', 'settings': dict(settings or {})}


def _default_shape(subj, t, period):
    one = period and len(period['months']) == 1
    if subj == 1:      # "the budget" alone is the budget against spending; "spending" is the categories ranked
        return 4 if re.search(r'\bbudget\b', t, re.I) and not re.search(r'\bspen[dt]|\bcost|\bcharges?\b', t, re.I) else 3
    if subj == 2:
        return 3 if one else 1
    if subj == 3:
        return 1
    if subj == 4:
        return 3 if one or re.search(r'\bpay ?checks?\b|\bwhere\b|\bcoming from\b|\bsources?\b', t, re.I) else 1
    if subj == 5:
        return 1
    if subj == 6:
        return 4
    if subj == 7:
        return 1 if re.search(r'\bnet worth\b', t, re.I) else 4
    if subj == 8:
        return 3
    if subj == 9:
        return 3
    return 6 if re.search(r'\$\s?\d', t) else 4


def _choice(label, sections, period):
    return {'label': label, 'sections': _with_period([{'id': i, 'settings': dict(s)} for i, s in sections], period)}


def _shape_question(subj, period_said, settings):
    su = rs.SUBJECTS[subj - 1]['name']
    ok = rs.PAIRS[subj]
    return {'question': f'{su} as: ' + ' · '.join(rs.SHAPES[s - 1]['name'].lower() for s in ok) + '?',
            'choices': [{'label': rs.SHAPES[s - 1]['name'],
                         'sections': _with_period([_section(s, subj, settings)], period_said)} for s in ok]}


def _subject_question(shape, period_said):
    subs = [n for n, shapes in rs.PAIRS.items() if shape in shapes and n not in (2, )]
    return {'question': f"{rs.SHAPES[shape - 1]['name']} of what?",
            'choices': [{'label': rs.SUBJECTS[n - 1]['name'],
                         'sections': _with_period([_section(shape, n)], period_said)} for n in subs]}


def _templates_offer():
    return [{'label': t['name'], 'sections': [{'id': i, 'settings': dict(s)} for i, s in t['sections']]}
            for t in rs.TEMPLATES]


def _side(t, names, terms, prefer_debt=False):
    """The names one stretch of words means, each kind on its own."""
    mine = _person_terms(t, terms)
    payees = mine.get('payee') or _named(t, names['payees'], 'payees')
    debts = _debts(t, names['debts'])
    accounts = _accounts(t, names['accounts'])
    cats = mine.get('category') or ([] if payees else _categories(t, names['categories']))
    if debts and accounts and set(debts) & set(accounts):
        if prefer_debt or _LOANISH.search(t) or re.search(r'\bpa(id|ying|y)\b', t, re.I):
            accounts = [a for a in accounts if a not in debts]
        else:
            debts = [d for d in debts if d not in accounts]
    return {'payees': payees, 'debts': debts, 'accounts': accounts, 'categories': cats}


def read(reader, text, terms=None, helper=None):
    """A request -> what Groundwork will build, or the one question it asks first. No figure is written here."""
    raw = (text or '').strip()[:300]
    out = {'outcome': 'none', 'sections': [], 'style': None, 'said': [], 'step': 1, 'found': {}, 'helpers': []}
    if not raw:
        out['said'] = ['Say what you would like to see.']
        return out
    if ah.rejected(raw):
        out.update(outcome='refuse', said=[ah.R7_REFUSAL])
        return out
    if ah.read_request(raw) == 'refuse' and not _ACT.search(raw):
        out.update(outcome='refuse', said=["Groundwork never moves money or changes your accounts. It can show you "
                                           "a report of them."])
        return out
    today = reader.today
    act = bool(_ACT.search(raw))
    t = raw
    for rx, key in _STYLE:
        m = rx.search(t)
        if m:
            out['style'] = key
            out['found']['style'] = m.group(0)
            t = (t[:m.start()] + ' ' + t[m.end():]).strip()
            break
    if act:
        out['said'].append(ACT_SAID)

    for rx, said, offer in [(_rx(p), s, o) for p, s, o in NOT_SUBJECTS]:
        if rx.search(t):
            out.update(outcome='does_not_know', step=2, question=said,
                       choices=[_choice(lbl, secs, None) for lbl, secs in offer])
            out['said'].append(said)
            out['found']['not_a_subject'] = rx.search(t).group(0)
            return out

    names = record_names(reader)
    ex_m = _EXCEPT.search(t)
    main, except_t = (t[:ex_m.start()], t[ex_m.end():]) if ex_m else (t, '')
    period = periods.read_period(main, today) or periods.read_period(t, today)
    psaid = re.sub(r'^(in|for|during|of|over)\s+', '', period['said'].strip(), flags=re.I) if period else None
    if psaid:
        out['found']['period'] = psaid
    ask_period = bool(re.search(VAGUE_ASK, t, re.I)) and not period
    if re.search(NOT_A_PERIOD, t, re.I) and not period:
        w = re.search(NOT_A_PERIOD, t, re.I).group(0)
        out['said'].append(f'"{w[0].upper() + w[1:]}" is not a period Groundwork can read yet, so this is over the '
                           'whole record. Choose a period below to narrow it.')

    def finish(sections, step=1):
        sections = _with_period(sections, psaid)
        if ask_period:
            out.update(outcome='clarify', step=2, question='Over what period?',
                       choices=[{'label': lbl, 'sections': _with_period(
                           [{'id': s['id'], 'settings': dict(s['settings'])} for s in sections], said)}
                                for lbl, said in PERIOD_CHOICES])
            return out
        out['sections'] = sections
        out['step'] = max(out['step'], step)
        out['outcome'] = 'refuse_act' if act else ('build_and_say' if [s for s in out['said'] if s != ACT_SAID]
                                                    else 'build')
        return out

    tname, tsecs = _template(main)
    if tsecs:
        out['found']['template'] = tname or ' + '.join(s['id'] for s in tsecs)
        return finish(tsecs)

    # versus: two names, two subjects or two periods (H-c by code; phi only for a side it cannot name)
    vs = _VERSUS.search(main)
    if vs:
        left, right = main[:vs.start()], main[vs.end():]
        got = _versus(left, right, names, terms, today, helper, out)
        if got is not None:
            return finish(got, out['step'])

    side = _side(main, names, terms)
    out['found'].update({k: v for k, v in side.items() if v})
    if not side['payees']:          # P4: a name the record does not have is dropped, and said
        m = re.search(r"\bat\s+((?:[A-Z][\w&'-]*\s?)+)", main)
        if m and not _categories(m.group(1), names['categories']):
            out['said'].append(f'There is no payee called "{m.group(1).strip()}" in the record, so this shows all '
                               'spending.')
    exclude = _side(except_t, names, terms) if except_t else None
    if except_t:
        out['found']['except'] = except_t.strip()

    for kind in ('payees', 'debts', 'categories'):          # P4 / item 114 Q17: two close matches - ask, never pick
        if len(side[kind]) > 1 and not (kind == 'debts' and len(side[kind]) == 2 and _VERSUS.search(main)):
            word = {'payees': 'payee', 'debts': 'debt', 'categories': 'category'}[kind]
            out.update(outcome='clarify', step=2, question=f'Which {word} do you mean?',
                       choices=[_choice(n, [_named_section(kind, n, main, psaid)], psaid) for n in side[kind]])
            return out

    shape = _first(_SHAPES, main)
    subj = _first(_SUBJECTS, main)
    settings = {}
    if side['payees']:
        subj, settings = 3, {'payee': side['payees'][0]}
    elif side['debts'] and (subj in (None, 1, 5, 6) or _LOANISH.search(main)):
        if subj == 6:
            out['said'].append(f'Debt balances are shown for every debt; {side["debts"][0]} is among them.')
        else:
            subj, settings = 5, {'debt': side['debts'][0]}
    elif side['categories']:
        subj, settings = 2, {'category': side['categories'][0]}
    if side['accounts'] and (subj in (None, 1, 2, 3, 4)):
        settings['account'] = side['accounts'][0]
        subj = subj or 1

    # two meanings, with nothing beside them to decide (H-a)
    if subj in (None, 1) and not settings:
        car = _CAR.search(main)
        if car:
            cands = ([(d, [('1.5', {'debt': d})]) for d in names['debts'] if re.search(r'\b(auto|car)\b', d.lower())]
                     + [(c, [('1.2', {'category': c})]) for c in names['categories']
                        if re.search(r'\b(auto|car|gasoline)\b', c.lower())])
            if len(cands) > 1:
                return _two_meanings(out, 'car', raw, f'What about the {car.group(1).lower()} do you mean?',
                                     cands, psaid, helper, finish)
            if len(cands) == 1:
                settings = cands[0][1][0][1]
                subj = 5 if 'debt' in settings else 2
        for key, rxp, question, readings in TWO_MEANINGS:
            if subj is None or key == 'paying out':
                if re.search(rxp, main, re.I) and not settings:
                    return _two_meanings(out, key, raw, question, readings, psaid, helper, finish, shape)

    if except_t and exclude is not None:
        gone = exclude['payees'] or exclude['categories']
        if not gone and helper is not None:
            gone = _helper_name(helper, out, 'H-c', except_t, names)
        if gone and subj == 3 and settings.get('payee') and gone[0] != settings['payee']:
            out['said'].append(f"{gone[0]} is a different payee from {settings['payee']}, so nothing is taken out.")
        elif gone and (subj in (1, 2) or subj is None):
            settings['exclude'] = gone[:1]
        elif not gone:
            out['said'].append(f'"{except_t.strip()}" is not a payee or category in the record, so nothing is left out.')

    if subj in (None, 1) and not settings and not out['said']:
        unread = unknown_words(main, names, terms)
        if unread:
            out['found']['unread'] = unread
            # H-b advises only (measured 2026-11-01: it named a category where "none" was right); the person picks
            likely = _helper_name(helper, out, 'H-b', main, {'categories': names['categories'],
                                                             'payees': names['payees']}) if helper is not None else []
            cands = list(dict.fromkeys(likely + names['categories']))[:30]     # every category with spending
            choices = [_choice(c, [_named_section('payees' if c in names['payees'] else 'categories', c, main, psaid)],
                               psaid) for c in cands]
            if likely:
                choices[0]['likely'] = True
            out.update(outcome='clarify', step=2, question=f'Groundwork doesn\'t know "{unread}". Which is it?',
                       choices=choices + [_choice('All spending', [(f'{shape}.1' if shape in rs.PAIRS[1] else '3.1', {})],
                                                  psaid)])
            return out
    if subj is None and shape is None:
        out.update(outcome='none', step=3, question='Groundwork could not tell what to show. Start from one of these, '
                                                    'or build it section by section below.', choices=_templates_offer())
        return out
    if subj is None:
        out.update(outcome='clarify', step=2, **_subject_question(shape, psaid))
        return out
    if shape is None:
        shape = _default_shape(subj, main, period)
    if shape == 5 and subj in (1, 2, 3, 4, 5):
        pb = _second_period(main, period, today)
        if pb:
            settings['period_b'] = pb
    if shape not in rs.PAIRS[subj]:
        q =_shape_question(subj, psaid, settings)
        out.update(outcome='clarify', step=2, **q)
        return out
    if subj == 10 and shape == 6:
        m = re.search(r'\$\s?([\d,]+(?:\.\d+)?)', main)
        if m:
            settings['amount'] = float(m.group(1).replace(',', ''))
    if subj == 6 and shape == 6:
        m = re.search(r'\$\s?([\d,]+(?:\.\d+)?)', main)
        settings['amount'] = float(m.group(1).replace(',', '')) if m else 100
    return finish([_section(shape, subj, settings)], out['step'])


def _named_section(kind, name, t, psaid):
    if kind == 'payees':
        return ('1.3', {'payee': name})
    if kind == 'debts':
        return ('1.5', {'debt': name})
    shape = _first(_SHAPES, t) or 1
    return (f'{shape if shape in rs.PAIRS[2] else 1}.2', {'category': name})


def _second_period(t, period, today):
    """'this month compared to last month': the period after the comparison word is the second (P5, by code)."""
    m = re.search(r'\b(compared? (to|with)|versus|vs\.?|than|against)\b(.*)$', t, re.I)
    if not m:
        return None
    p = periods.read_period(m.group(3), today)
    return p['said'] if p and (not period or p['said'] != period['said']) else None


def _versus(left, right, names, terms, today, helper, out):
    """R22 / R23: two debts, two subjects or two periods, each its own section - never a difference written."""
    pl, pr = periods.read_period(left, today), periods.read_period(right, today)
    a, b = _side(left, names, terms, True), _side(right, names, terms, True)
    sa, sb = _first(_SUBJECTS, left), _first(_SUBJECTS, right)
    if pl and pr and pl['said'] != pr['said'] and not (b['payees'] or b['debts'] or b['categories']):
        subj = 2 if a['categories'] else (3 if a['payees'] else (sa or 1))
        st = {'period': pl['said'], 'period_b': pr['said']}
        if a['categories']:
            st['category'] = a['categories'][0]
        if a['payees']:
            st['payee'] = a['payees'][0]
        if 5 not in rs.PAIRS[subj]:
            return None
        out['found']['versus'] = 'two periods'
        return [_section(5, subj, st)]
    for kind, sid, key in (('debts', '1.5', 'debt'), ('payees', '1.3', 'payee'), ('categories', '1.2', 'category')):
        if a[kind] and not b[kind] and helper is not None and not any(b.values()):
            got = _helper_name(helper, out, 'H-c', right, {**{k: [] for k in names}, kind: names[kind]})
            if got:
                b[kind] = got
        if a[kind] and b[kind] and a[kind][0] != b[kind][0]:
            out['found']['versus'] = [a[kind][0], b[kind][0]]
            return [{'id': sid, 'settings': {key: a[kind][0]}}, {'id': sid, 'settings': {key: b[kind][0]}}]
    if sa and sb and sa != sb and not any(a.values()) and not any(b.values()):
        shape = _first(_SHAPES, left + ' ' + right)
        shape = shape if shape in (1, 2) else 1
        if shape in rs.PAIRS[sa] and shape in rs.PAIRS[sb]:
            out['found']['versus'] = [rs.SUBJECTS[sa - 1]['name'], rs.SUBJECTS[sb - 1]['name']]
            return [_section(shape, sa), _section(shape, sb)]
    return None


# ── phi's helpers (P7, P8): one closed question each, with "can't tell"; code checks every answer ─────────────────────
CANT_TELL = "can't tell"
HELPER_SYSTEM = ("You help Groundwork, a personal finance app, understand a request for a report. Answer with exactly "
                 "one of the choices given. If the request does not make the answer clear, answer \"can't tell\". "
                 "Never guess.")


def _ask(helper, out, name, question, labels):
    """One helper call: the answer, checked against the choices, or None for can't tell / not ready."""
    got = helper(HELPER_SYSTEM, question, list(labels) + [CANT_TELL])
    out['helpers'].append({'helper': name, 'answer': got})
    return got if got in labels else None


def _two_meanings(out, key, raw, question, readings, psaid, helper, finish, shape=None):
    choices = []
    for label, secs in readings:
        cs = [(i, dict(s)) for i, s in secs]
        if shape in (1, 2):
            cs = [(f'{shape}.{i.split(".")[1]}' if shape in rs.PAIRS[int(i.split('.')[1])] else i, s) for i, s in cs]
        choices.append(_choice(label, cs, psaid))
    out['found']['two_meanings'] = key
    if helper is not None:          # H-a advises only: its pick is offered first, and the person still chooses
        q = f'Request: "{raw}"\nWhat does "{key}" mean in this request?'
        pick = _ask(helper, out, 'H-a', q, [c['label'] for c in choices])
        if pick:
            got = next(c for c in choices if c['label'] == pick)
            choices = [got] + [c for c in choices if c is not got]
            got['likely'] = True
    out.update(outcome='clarify', step=2, question=question, choices=choices)
    return out


def _content(t):
    t = re.sub(periods._RANGE.pattern, ' ', t, flags=re.I)
    return ' '.join(w for w in _words(t) if w not in _WEAK and not re.fullmatch(r'\d+', w))


def _helper_name(helper, out, name, words, names):
    """H-b / H-c: which of the record's names the words mean, or none."""
    w = _content(words)
    if not w:
        return []
    opts = (names.get('categories') or []) + (names.get('payees') or []) + (names.get('debts') or [])
    opts = list(dict.fromkeys(opts))[:40]
    if not opts:
        return []
    q = f'Words: "{w}"\nWhich one of these names do these words mean?'
    pick = _ask(helper, out, name, q, opts)
    if pick and name == 'H-c':          # H-c builds on its pick, and says it (measured: 4 / 4); H-a and H-b only advise
        out['said'].append(f'Read "{w}" as {pick}.')
    return [pick] if pick else []



# ── H-d (P9): words from the miss log, suggested - nothing enters the index until the person says Yes ──────────────
_VOCAB = [rx for _, rx in _SHAPES] + [rx for _, rx in _SUBJECTS] + [rx for rx, _ in _STYLE] + [rx for rx, _ in _TEMPLATES]


def unknown_words(text, names, terms=None):
    """The words of a request nothing read: no vocabulary term, no period, no name of the record, no accepted term.
    Two or three words at most - a longer stretch is not one word for one thing."""
    t = text or ''
    for rx in _VOCAB + [_rx(VAGUE_ASK), _rx(NOT_A_PERIOD), _ACT, _CAR] + [_rx(p) for _, p, _, _ in TWO_MEANINGS]:
        t = rx.sub(' ', t)
    t = re.sub(periods._RANGE.pattern, ' ', t, flags=re.I)
    known = {w for kind in names.values() for n in kind for w in _words(n)}
    known |= {w for said in (terms or {}) for w in _words(said)}
    left = [w for w in _words(t) if w not in _WEAK and w not in known and not w.isdigit() and len(w) >= 3
            and not periods.read_period(w, __import__('datetime').date.today())]
    return ' '.join(left) if 1 <= len(left) <= 3 else None


def suggest_terms(reader, misses, helper, terms=None):
    """For each miss with words the index did not know, phi picks one of the record's categories or payees, or none.
    Code checks the name is the record's and the words are not already a term. -> [{said, kind, means}]"""
    names = record_names(reader)
    opts = list(dict.fromkeys(names['categories'] + names['payees']))[:40]
    seen, out = set(terms or {}), []
    for m in misses[-20:]:
        said = unknown_words(m.get('said') or '', names, terms)
        if not said or said in seen:
            continue
        if m.get('picked') and m['picked'] not in opts:     # they answered "All spending": the words name nothing
            continue
        seen.add(said)
        q = f'A person asked for a report: "{m.get("said")}"'
        if m.get('picked'):
            q += f'\nWhen asked, they chose: {m["picked"]}'
        q += f'\nWhich one of these names do the words "{said}" mean?'
        pick = helper(HELPER_SYSTEM, q, opts + [CANT_TELL])
        if pick in opts:
            out.append({'said': said, 'kind': 'payee' if pick in names['payees'] else 'category', 'means': pick})
        if len(out) >= 8:
            break
    return out
