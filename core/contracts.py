"""
Groundwork - budget lines set by a contract (gw 2.0/INCOME_CHANGE_SCENARIOS.md section 4.7, item 71 amendment D11)
==================================================================================================================
A loan, lease, debt or insurance payment can't be cut by half in a budget - no one can pay half a lease. These lines
are never offered as cuts.

  - 'contract'  the line's name or category says so (loan, lease, debt, mortgage, insurance, financing), it shares a
                name with one of the person's debt accounts, or the person said so.
  - 'ask'       the name is a lender, insurer or loan servicer but nothing confirms a contract (e.g. "GEICO" with no
                category). Left alone until the person answers once (AP4); never guessed either way.
  - None        an ordinary spending line.
"""
import re

CONTRACT_WORDS = re.compile(r'\b(debt|loans?|lease|leasing|mortgage|insurance|premium|financ\w*|car payment|'
                            r'auto payment|student loans?)\b', re.I)
KNOWN_PAYEES = ('geico', 'state farm', 'progressive', 'allstate', 'liberty mutual', 'nationwide', 'farmers insurance',
                'usaa', 'travelers', 'ford motor', 'ford credit', 'stellantis', 'chrysler capital', 'toyota financial',
                'honda financial', 'gm financial', 'ally auto', 'santander', 'capital one auto', 'dept of education',
                'department of education', 'nelnet', 'mohela', 'navient', 'aidvantage', 'great lakes', 'sallie mae',
                'onemain', 'one main', 'rocket mortgage', 'mr. cooper', 'lendingclub', 'sofi')


def _norm(s):
    return re.sub(r'[^a-z0-9 ]', ' ', str(s or '').lower()).split()


def classify(lines, debt_names=(), answers=None):
    """{line_id: {'kind': 'contract'|'ask', 'why': str}} for every line that is or may be set by a contract.
    `answers`: {line_id: 'yes'|'no'} - the person's own word, which decides."""
    answers = answers or {}
    debts = [' '.join(_norm(n)) for n in debt_names if len(' '.join(_norm(n))) >= 4]
    out = {}
    for ln in lines:
        lid = ln['id']
        said = answers.get(lid)
        if said == 'yes':
            out[lid] = {'kind': 'contract', 'why': 'you said it is set by a contract'}
            continue
        if said == 'no':
            continue
        text = f"{ln.get('name') or ''} {ln.get('category') or ''}"
        if CONTRACT_WORDS.search(text):
            out[lid] = {'kind': 'contract', 'why': 'its name or category is a loan, lease, debt or insurance payment'}
            continue
        name = ' '.join(_norm(ln.get('name')))
        match = next((d for d in debts if name and d in name), None)     # the line names the whole account
        if match:
            out[lid] = {'kind': 'contract', 'why': 'it shares a name with one of your debt accounts'}
            continue
        if any(p in name for p in KNOWN_PAYEES):
            out[lid] = {'kind': 'ask', 'why': 'its name is a lender, insurer or loan servicer'}
    return out
