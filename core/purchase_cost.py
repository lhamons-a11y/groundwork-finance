"""
Groundwork - the full cost of a purchase, and a financing offer read (gw 2.0/BYB_AGENT.md, item 73 stage 3: Y3 + Y4)
===================================================================================================================
Y3: the monthly cost built from what Groundwork knows, each part with its source - the person's own figure, their
    confirmed bill reading, or a published price. A part with no source is left out and named, never guessed
    (the item 59 rule).
Y4: a pasted financing offer read for its APR, term, payment, price, fees and any deferred-interest terms - every
    figure must be in the text - and laid beside paying cash and the person's own debt. Facts side by side; the
    choice is the person's (teach the question). Arithmetic only; no model.
"""
import math
import re

from pdf_statement import _financial_numbers, _number_candidates


def _num(v):
    try:
        f = float(v)
        return f if f >= 0 else None
    except (TypeError, ValueError):
        return None


def full_cost(kind, inputs, insurance=None, gas=None):
    """`kind` 'car' | 'phone' | 'annual'. `inputs` the person's own figures. `insurance` {name, amount, date} from a
    confirmed bill reading, or None. `gas` {price, period, live} - used only when live (published, not a guess)."""
    i = inputs or {}
    parts, left_out = [], []

    def add(label, monthly, source, kind_):
        parts.append({'label': label, 'monthly': round(monthly, 2), 'source': source, 'kind': kind_})

    if kind == 'car':
        pay = _num(i.get('payment'))
        if pay:
            add('Payment', pay, 'you entered', 'user_supplied')
        else:
            left_out.append('Payment - enter the monthly payment')
        ins = _num(i.get('insurance'))
        if ins:
            add('Insurance', ins, 'you entered', 'user_supplied')
        elif insurance and insurance.get('amount'):
            add('Insurance', float(insurance['amount']), f"your {insurance['name']} bill reading of {insurance['date']}"
                f" (today's policy; a new car can change it)", 'observed')
        else:
            left_out.append('Insurance - enter the quote, or read your insurance bill in Assistant > Bills')
        miles, mpg = _num(i.get('miles_per_month')), _num(i.get('mpg'))
        if miles and mpg and gas and gas.get('live') and gas.get('price'):
            add('Fuel', miles / mpg * float(gas['price']),
                f"{miles:,.0f} miles a month at {mpg:g} mpg (you entered), gas ${float(gas['price']):.2f} a gallon "
                f"(EIA national average, {gas.get('period') or 'latest'})", 'published')
        elif miles and mpg:
            left_out.append('Fuel - no published gas price is available right now')
        else:
            left_out.append('Fuel - enter miles a month and the car\'s mpg')
        reg = _num(i.get('registration_yearly'))
        if reg:
            add('Registration', reg / 12, f'${reg:,.2f} a year (you entered)', 'user_supplied')
        else:
            left_out.append('Registration - enter the yearly fee')
        left_out.append('Repairs and maintenance - Groundwork has no source for these')
    elif kind == 'phone':
        dev = _num(i.get('device_payment'))
        if dev:
            add('Device payment', dev, 'you entered', 'user_supplied')
        else:
            left_out.append('Device payment - enter it')
        try:
            plan = float(i.get('plan_change'))
            add('Plan change', plan, 'you entered (the difference from your current plan)', 'user_supplied')
        except (TypeError, ValueError):
            left_out.append('Plan change - enter the difference from your current plan')
    elif kind == 'annual':
        yearly = _num(i.get('yearly'))
        if yearly:
            add('Yearly charge', yearly / 12, f'${yearly:,.2f} a year (you entered), shown a month at a time', 'user_supplied')
        else:
            left_out.append('Yearly charge - enter it')
    else:
        return None
    total = round(sum(p['monthly'] for p in parts), 2)
    return {'kind': kind, 'parts': parts, 'monthly': total, 'yearly': round(total * 12, 2), 'left_out': left_out}


# ── Y4: a financing offer ─────────────────────────────────────────────────────
_APR = re.compile(r'(\d{1,2}(?:\.\d{1,3})?)\s*%\s*(?:apr|annual percentage rate)|(?:apr|annual percentage rate)\s*(?:of|is|:)?\s*(\d{1,2}(?:\.\d{1,3})?)\s*%', re.I)
_TERM = re.compile(r'(\d{1,3})\s*(?:equal\s+)?(?:monthly\s+payments|months?\b|mos?\.?\b)', re.I)
_PAYMENT = re.compile(r'(?:monthly payment(?: of)?|payments? of)\s*\$\s?(\d[\d,]*(?:\.\d{2})?)|\$\s?(\d[\d,]*(?:\.\d{2})?)\s*(?:/\s*mo\b|/\s*month|per month|a month)', re.I)
_PRICE = re.compile(r'(?:amount financed|purchase price|cash price|total price|price)\s*:?\s*\$\s?(\d[\d,]*(?:\.\d{2})?)', re.I)
_FEE = re.compile(r'(?:origination|processing|documentation|doc|account|activation)?\s*fee\s*(?:of)?\s*:?\s*\$\s?(\d[\d,]*(?:\.\d{2})?)', re.I)
_DEFERRED = re.compile(r'deferred interest|interest (?:will be|is) (?:charged|assessed)[^.]{0,80}(?:from|since) the (?:purchase|original|transaction) date|'
                       r'if (?:the )?(?:promotional |promo )?(?:purchase )?balance is not paid in full', re.I)
_PROMO = re.compile(r'(?:no interest|0\s*%\s*(?:apr|interest)?|special financing|promotional (?:period|financing))[^.]{0,40}?(\d{1,2})\s*months?|'
                    r'(\d{1,2})\s*months?\s*(?:no interest|special financing|promotional|interest[- ]free|at 0\s*%)', re.I)


def read_offer(text):
    """-> {'apr', 'term_months', 'payment', 'price', 'fees', 'deferred', 'deferred_phrase', 'promo_months',
    'warnings'}. A figure the text doesn't contain is left out and said."""
    t = text or ''
    nums = _financial_numbers(t)
    out, warnings = {}, []

    def take(field, value, pct=False):
        if value is None:
            return
        v = float(str(value).replace(',', ''))
        cands = _number_candidates(v)
        if cands & nums or (pct and (str(value) in nums or f'{v:g}' in nums)):
            out[field] = round(v, 3 if pct else 2)
        else:
            warnings.append(f'{field.replace("_", " ")} ({value}) is not in the text as a figure - left out')
    m = _APR.search(t)
    take('apr', m and (m.group(1) or m.group(2)), pct=True)
    m = _TERM.search(t)
    if m:
        out['term_months'] = int(m.group(1))
    m = _PAYMENT.search(t)
    take('payment', m and (m.group(1) or m.group(2)))
    m = _PRICE.search(t)
    take('price', m and m.group(1))
    fees = [float(f.replace(',', '')) for f in _FEE.findall(t)]
    if fees:
        out['fees'] = round(sum(fees), 2)
    d = _DEFERRED.search(t)
    out['deferred'] = bool(d)
    if d:
        s = max(0, t.rfind('.', 0, d.start()) + 1)
        e = t.find('.', d.end())
        out['deferred_phrase'] = t[s:(e + 1 if e != -1 else len(t))].strip()[:300]
    m = _PROMO.search(t)
    if m:
        out['promo_months'] = int(m.group(1) or m.group(2))
    out['warnings'] = warnings
    return out


def _amortized_payment(principal, apr, months):
    r = apr / 100 / 12
    if r <= 0:
        return principal / months
    return principal * r / (1 - (1 + r) ** -months)


def compare(offer, debts):
    """Y4: paying cash, the offer, and the person's own debt, side by side - each figure with how it was found.
    `debts` [{name, balance, rate}] - the person's active debts with a balance."""
    price, apr, n = offer.get('price'), offer.get('apr'), offer.get('term_months')
    pay, fees = offer.get('payment'), offer.get('fees') or 0
    rows = []
    if price:
        rows.append({'label': 'Pay cash', 'total': round(price, 2), 'how': 'the price in the offer'})
    financed = None
    if pay and n:
        financed = round(pay * n + fees, 2)
        rows.append({'label': 'Finance it', 'total': financed,
                     'how': f'${pay:,.2f} x {n} payments' + (f' + ${fees:,.2f} in fees' if fees else '') + ' (from the offer)'})
    elif price and offer.get('promo_months'):
        # a no-interest promotion: paid off in time it costs the price; the APR only applies if it isn't (below)
        pm = offer['promo_months']
        financed = round(price + fees, 2)
        rows.append({'label': f'Finance it, paid off within {pm} months', 'total': financed,
                     'how': f'no interest on ${price:,.2f} if all of it is paid within {pm} months (about '
                            f'${price / pm:,.2f} a month)' + (f', + ${fees:,.2f} in fees' if fees else '') + ' - from the offer'})
    elif price and apr is not None and n:
        p = _amortized_payment(price, apr, n)
        financed = round(p * n + fees, 2)
        rows.append({'label': 'Finance it', 'total': financed,
                     'how': f'${price:,.2f} at {apr:g}% APR over {n} months = about ${p:,.2f} a month (worked out by Groundwork)'
                            + (f' + ${fees:,.2f} in fees' if fees else '')})
    extra = round(financed - price, 2) if (financed is not None and price) else None
    deferred = None
    if offer.get('deferred') and offer.get('promo_months') and price and apr:
        back = price * apr / 100 * offer['promo_months'] / 12
        deferred = {'months': offer['promo_months'], 'apr': apr, 'cost': round(back, 2),
                    'how': f'if the balance isn\'t paid off in {offer["promo_months"]} months, interest at {apr:g}% is charged '
                           f'back to the purchase date - about ${back:,.2f} on ${price:,.2f} (simple interest, worked out by '
                           f'Groundwork; the offer\'s own terms decide the exact figure)'}
    own = sorted((d for d in debts if (d.get('rate') or 0) > 0 and (d.get('balance') or 0) > 0), key=lambda d: -d['rate'])
    debt_line = None
    if own:
        top = own[0]
        debt_line = {'name': top['name'], 'rate': top['rate'], 'balance': round(top['balance'], 2),
                     'offer_apr': apr, 'year_interest_on_cash': round(min(price or 0, top['balance']) * top['rate'] / 100, 2) if price else None}
    return {'rows': rows, 'extra': extra, 'deferred': deferred, 'own_debt': debt_line}
