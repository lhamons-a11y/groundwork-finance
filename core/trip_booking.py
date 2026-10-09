"""
"I booked it" - a booking recorded once, matched to its real charge with the user's yes (gw 2.0/TRIP_BOOKED.md, item 50;
Rob 2026-10-08: "approve B1-B8 as recommended").

A booking is a planned record (B2). It never enters spending, a budget total or a card balance. The money is counted
once, when the real charge arrives by import and the user says yes to the match (B3). This module only proposes:

    a charge is a candidate when it is on the card or account the booking says it was paid with, within $1.00 of the
    booked amount, dated within 7 days of the booking, from a merchant or description that names the airline, and is
    not already matched to another booking.

A refund on a cancelled booking (B6) is matched the same way, as money coming back. Nothing here links anything; the
route does that only when the user says yes. Nothing here learns anything about the person (B5).
"""
import re
from datetime import date, timedelta

AMOUNT_TOLERANCE = 1.00
DAYS_TOLERANCE = 7


def names_airline(text, airline):
    """True when every word of the airline's name appears as a whole word in the merchant or description
    ("DELTA AIR 0062345" names "Delta"; "DELTAPLEX" does not)."""
    words = re.findall(r'[a-z0-9]+', (airline or '').lower())
    have = set(re.findall(r'[a-z0-9]+', (text or '').lower()))
    return bool(words) and all(w in have for w in words)


def is_candidate(booking, amount, when, text, already_matched=False):
    """The B3 rule for one charge (or, for a refund, one credit)."""
    if already_matched or amount is None or when is None:
        return False
    if abs(float(amount) - float(booking['amount'])) > AMOUNT_TOLERANCE + 1e-9:
        return False
    if abs((when - booking['booked_on']).days) > DAYS_TOLERANCE:
        return False
    return names_airline(text, booking['airline'])


def candidates(booking, rows, matched_ids=()):
    """The rows - each {id, amount, date, text} - that match the booking, nearest amount first."""
    taken = set(matched_ids)
    out = [r for r in rows if is_candidate(booking, r['amount'], r['date'], r['text'], r['id'] in taken)]
    return sorted(out, key=lambda r: (abs(float(r['amount']) - float(booking['amount'])), abs((r['date'] - booking['booked_on']).days)))


def window(booked_on):
    return booked_on - timedelta(days=DAYS_TOLERANCE), booked_on + timedelta(days=DAYS_TOLERANCE)


def trip_cost(booking):
    """B7: what the trip's flight line shows for a booking - the charged amount once matched, else the booked one -
    with the label that says which, and both when they differ."""
    if booking is None:
        return None
    if booking.get('status') == 'charged' and booking.get('charged_amount') is not None:
        charged, booked = float(booking['charged_amount']), float(booking['amount'])
        return {'amount': charged, 'label': 'charged',
                'differs': abs(charged - booked) >= 0.005, 'booked': booked}
    if booking.get('status') in ('cancelled', 'refunded'):
        return None
    return {'amount': float(booking['amount']), 'label': 'booked', 'differs': False, 'booked': float(booking['amount'])}
