"""Item 115 P5 (Rob 2026-10-31, ruled C1-C11): dates are read by code, never by the model. One reader for every
surface that turns a person's words into a period - the assistant's repairs (item 114) and Ask for a report's index.

read_period(text, today) -> {'start': date, 'end': date, 'months': ['YYYY-MM', ...], 'said': 'the words read',
                              'window': True when it runs date to date, 'note': what was left out and why} or None

A month not yet reached this year means last year's ("in December", asked in October, is last December). A range
whose end is before its start runs across the new year ("November to February"). An end in the future is cut to today.

Calendar months or date to date (Rob 2026-10-31: it "depends on whether the user is measuring full calendar months or
a rolling 30-day/date-to-date window, and whether the current month is complete"):
    "the last six months"              the six most recent complete calendar months. This month counts once it is
                                       complete - on its last day; before that it is left out, and the note says so.
    "the last six months to date",     date to date: the same day six months back, to today
    "the last 30 days", "past 2 weeks" date to date, ending today
    "June 15 to September 15", "since June 15"   date to date, the days named
"""
import re
from calendar import monthrange
from datetime import date

_MONTHS = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october',
           'november', 'december']
_MON = r'(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|' \
       r'oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?'
_YR = r'(?:,?\s+(20\d\d))?'
_NUMS = {'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
         'eleven': 11, 'twelve': 12}

_RANGE = re.compile(r'\b(?:from\s+|between\s+)?' + _MON + _YR + r'\s*(?:-|–|to|through|thru|until|till|and)\s*'
                    + _MON + _YR + r'\b', re.I)
_SINCE = re.compile(r'\bsince\s+' + _MON + _YR + r'\b', re.I)
_ONE = re.compile(r'\b(?:in|for|during|of)?\s*' + _MON + _YR + r'\b', re.I)
_QUARTER = re.compile(r'\b(?:q([1-4])|(first|second|third|fourth)\s+quarter)(?:\s+(?:of\s+)?(20\d\d))?\b', re.I)
_LAST_N = re.compile(r'\b(?:the\s+)?(?:last|past)\s+(\d{1,2}|two|three|four|five|six|seven|eight|nine|ten|eleven|'
                     r'twelve)\s+months?\b', re.I)
_ORD = r'(\d{1,2})(?:st|nd|rd|th)?'
_DAY_RANGE = re.compile(r'\b(?:from\s+|between\s+)?' + _MON + r'\s+' + _ORD + _YR + r'\s*(?:-|–|to|through|thru|until|till|and)\s*'
                        + _MON + r'\s+' + _ORD + _YR + r'\b', re.I)
_DAY_SINCE = re.compile(r'\bsince\s+' + _MON + r'\s+' + _ORD + _YR + r'\b', re.I)
_LAST_DAYS = re.compile(r'\b(?:the\s+)?(?:last|past)\s+(\d{1,3}|two|three|four|five|six|seven|eight|nine|ten|eleven|'
                        r'twelve)\s+(days?|weeks?)\b', re.I)
_TO_DATE = re.compile(r'\s*(?:to\s+date|up\s+to\s+today|through\s+today|until\s+today|to\s+today|rolling)\b', re.I)
_YEAR = re.compile(r'\b(?:in|for|during)?\s*(20\d\d)\b')
_WORDS = [
    (re.compile(r'\bthis\s+month\b|\bso\s+far\s+this\s+month\b|\bmonth\s+to\s+date\b', re.I), 'this_month'),
    (re.compile(r'\blast\s+month\b|\bprevious\s+month\b', re.I), 'last_month'),
    (re.compile(r'\bthis\s+year\b|\byear\s+to\s+date\b|\bso\s+far\s+this\s+year\b|\bytd\b', re.I), 'this_year'),
    (re.compile(r'\blast\s+year\b|\bprevious\s+year\b', re.I), 'last_year'),
]
# "May" is also a word ("may we", "you may"): read as a month only beside a period word or a year
_MAY_WORD = re.compile(r'\bmay\b(?!\s+(?:20\d\d|to|through|thru|until|till|and|-|–))', re.I)


def _month_no(word):
    w = word.lower().rstrip('.')
    return next(i for i, m in enumerate(_MONTHS, 1) if m.startswith(w[:3]))


def _key(y, m):
    return f'{y:04d}-{m:02d}'


def _last_day(y, m):
    return date(y, m, monthrange(y, m)[1])


def _year_for(m, year, today):
    """The year a month without one means: this year's, or last year's when it has not come yet."""
    if year:
        return int(year)
    return today.year if m <= today.month else today.year - 1


def _span(sy, sm, ey, em, today, said):
    start, end = date(sy, sm, 1), _last_day(ey, em)
    if start > today:
        return None
    end = min(end, today)
    months, y, m = [], sy, sm
    while (y, m) <= (end.year, end.month):
        months.append(_key(y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return {'start': start, 'end': end, 'months': months, 'said': said.strip()}


def _window(start, end, today, said):
    """Date to date: the days named, the months they touch."""
    if start > today or end < start:
        return None
    p = _span(start.year, start.month, end.year, end.month, today, said)
    p.update({'start': start, 'end': min(end, today), 'window': True})
    return p


def _months_back(d, n):
    y, m = d.year, d.month - n
    while m < 1:
        y, m = y - 1, m + 12
    return date(y, m, min(d.day, monthrange(y, m)[1]))


def _day(mon, day, year, today):
    m = _month_no(mon)
    try:
        return date(_year_for(m, year, today), m, int(day))
    except ValueError:
        return None


def _is_may_word(text, mt):
    return mt.group(1).lower().startswith('may') and not mt.group(2) and _MAY_WORD.match(text, mt.start(1)) \
        and not re.search(r'\b(in|for|during|since|of)\s+$', text[:mt.start(1)], re.I)


def read_period(text, today):
    """The period the words name, or None when they name none."""
    t = text or ''
    m = _DAY_RANGE.search(t)
    if m:
        a, b = _day(m.group(1), m.group(2), m.group(3), today), _day(m.group(4), m.group(5), m.group(6), today)
        if a and b and b < a and not m.group(3):
            a = a.replace(year=a.year - 1)
        return _window(a, b, today, m.group(0)) if a and b else None
    m = _DAY_SINCE.search(t)
    if m:
        a = _day(m.group(1), m.group(2), m.group(3), today)
        return _window(a, today, today, m.group(0)) if a else None
    m = _LAST_DAYS.search(t)
    if m:
        n = int(m.group(1)) if m.group(1).isdigit() else _NUMS[m.group(1).lower()]
        days = n * (7 if m.group(2).lower().startswith('week') else 1)
        return _window(date.fromordinal(today.toordinal() - days + 1), today, today, m.group(0)) if n >= 1 else None
    m = _RANGE.search(t)
    if m:
        sm, em = _month_no(m.group(1)), _month_no(m.group(3))
        ey = _year_for(em, m.group(4), today)
        sy = int(m.group(2)) if m.group(2) else (ey if sm <= em else ey - 1)
        if not m.group(4) and m.group(2):
            ey = sy if em >= sm else sy + 1
        return _span(sy, sm, ey, em, today, m.group(0))
    m = _SINCE.search(t)
    if m:
        sm = _month_no(m.group(1))
        sy = _year_for(sm, m.group(2), today)
        return _span(sy, sm, today.year, today.month, today, m.group(0))
    m = _QUARTER.search(t)
    if m:
        q = int(m.group(1)) if m.group(1) else ['first', 'second', 'third', 'fourth'].index(m.group(2).lower()) + 1
        y = int(m.group(3)) if m.group(3) else (today.year if (q - 1) * 3 + 1 <= today.month else today.year - 1)
        return _span(y, (q - 1) * 3 + 1, y, q * 3, today, m.group(0))
    m = _LAST_N.search(t)
    if m:
        n = int(m.group(1)) if m.group(1).isdigit() else _NUMS[m.group(1).lower()]
        if n < 1:
            return None
        to_date = _TO_DATE.match(t, m.end())
        if to_date:                                  # date to date: the same day n months back, to today
            return _window(date.fromordinal(_months_back(today, n).toordinal() + 1), today, today,
                           m.group(0) + to_date.group(0))
        done = today == _last_day(today.year, today.month)     # this month is complete on its last day
        end = today if done else _months_back(today.replace(day=1), 1)
        start = _months_back(end.replace(day=1), n - 1)
        p = _span(start.year, start.month, end.year, end.month, today, m.group(0))
        if not done:
            p['note'] = f"{today.strftime('%B %Y')} is left out: it is not over yet."
        return p
    for rx, word in _WORDS:
        m = rx.search(t)
        if m:
            if word == 'this_month':
                return _span(today.year, today.month, today.year, today.month, today, m.group(0))
            if word == 'last_month':
                y, mo = (today.year, today.month - 1) if today.month > 1 else (today.year - 1, 12)
                return _span(y, mo, y, mo, today, m.group(0))
            if word == 'this_year':
                return _span(today.year, 1, today.year, today.month, today, m.group(0))
            return _span(today.year - 1, 1, today.year - 1, 12, today, m.group(0))
    for m in _ONE.finditer(t):
        if _is_may_word(t, m):
            continue
        mo = _month_no(m.group(1))
        y = _year_for(mo, m.group(2), today)
        return _span(y, mo, y, mo, today, m.group(0))
    m = _YEAR.search(t)
    if m:
        y = int(m.group(1))
        return _span(y, 1, y, 12, today, m.group(0))
    return None


def one_month(text, today):
    """'YYYY-MM' when the words name exactly one month, else None."""
    p = read_period(text, today)
    return p['months'][0] if p and len(p['months']) == 1 else None
