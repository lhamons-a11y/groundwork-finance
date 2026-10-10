"""Sample itineraries for item 60 (s187). Representative layouts written for the tests - not real confirmations;
the format readers still need one real document of each sender before they are trusted (TRIP_ITINERARY_IMPORT.md)."""

EXPEDIA = """Expedia
Your trip to Denver is booked!
Expedia itinerary number: 72041188305512

Flight: Columbus (CMH) to Denver (DEN)
United Airlines
Airline confirmation: KX7Q2M
Departure: Thu, Nov 12, 2026 8:05am
Return: Sun, Nov 15, 2026 5:40pm

Hotel: The Curtis Denver
Hotel confirmation #: 88231945
Check-in: Thu, Nov 12, 2026
Check-out: Sun, Nov 15, 2026

Car rental: Hertz, Denver Intl Airport
Pick-up: Nov 12, 2026
Drop-off: Nov 15, 2026

Price summary
Flight
Traveler 1: Adult $312.40
Traveler 2: Adult $312.40
Taxes & fees $97.20
Hotel
3 nights $489.00
Taxes and fees $72.15
Car rental
3 days $141.00
Taxes & fees $38.70
Due at pick-up
Travel protection
Trip protection plan $64.00
Expedia booking fee $15.00
Total $1,541.85
Amount paid $1,362.15
"""

BOOKING_COM = """Booking.com
Your booking is confirmed - Hotel Alder, New Orleans
Booking number: 4021775390
PIN code: 7731
Check-in: Friday, March 5, 2027 (from 3:00 PM)
Check-out: Monday, March 8, 2027 (until 11:00 AM)

Price
3 nights US$426
City tax US$29.82
Total price US$455.82
You'll pay when you stay
"""

AIRLINE = """Delta Air Lines - eTicket Receipt
Confirmation number: GH4T9Z
Flight DL 1123 Detroit (DTW) to Orlando (MCO)
Departure: Feb 14, 2027
Return: Feb 21, 2027

Fare details
Base fare $398.00
Taxes, fees and charges $61.37
Total $459.37
Paid with Visa ending 4421
"""

HOTEL_CHAIN = """Hilton Garden Inn Nashville Downtown
Reservation confirmation: 3318044721
Arrival: April 9, 2027
Departure date: April 11, 2027

Summary of charges
Room rate 2 nights $358.00
Taxes $56.75
Total for stay $414.75
Payable at the hotel
"""

# A tour operator Groundwork has no reader for: goes to the model.
UNKNOWN = """Sunny Isles Tours - Your Itinerary
Reference: TOUR-5521
Snorkel trip, June 3, 2027: $180.00 (paid)
Sunset cruise, June 4, 2027: $95.00, due on the day
Total: $275.00
"""
