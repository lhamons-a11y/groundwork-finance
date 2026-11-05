"""
Groundwork — Trip Distance Engine
===================================
Real driving-distance estimate for trip fuel-cost math, replacing the
hardcoded 400-miles-each-way placeholder (Phase 5E).

Geocodes origin/destination via OpenStreetMap's Nominatim (free, keyless —
no account to create, no key to manage), then computes great-circle
distance and applies a fixed road-distance correction factor. This is an
ESTIMATE for a fuel-cost budget, not turn-by-turn routing.

Nominatim usage policy (operations.osmfoundation.org/policies/nominatim):
  - max 1 request/second
  - must identify the application via User-Agent
  - no bulk/heavy geocoding — cache results
This module caches every successful geocode by normalized place name (an
AppSetting row per place, never expires — city coordinates don't change),
so a repeat trip to the same city never hits Nominatim again. Only the
place names typed into the trip form are sent — no other trip or
financial data.

Design matches price_engine.py / gas_price.py: stdlib urllib only, a
failure never raises into the caller, honest fallback when a place name
can't be resolved.
"""
import json
import logging
import math
import urllib.request
import urllib.parse

from core.database import db_session, AppSetting

logger = logging.getLogger('groundwork.trip_distance')

REQUEST_TIMEOUT = 6
USER_AGENT = 'Groundwork-PersonalFinance/1.0 (local desktop app; trip fuel estimate; +https://groundworkfinance.app)'
NOMINATIM_URL = 'https://nominatim.openstreetmap.org/search?q={q}&format=json&limit=1'

# Real road distance runs longer than great-circle ("as the crow flies")
# distance — this factor approximates typical U.S. highway travel. It's a
# blunt correction, not routing; good enough for a fuel-cost estimate, not
# for navigation.
ROAD_DISTANCE_FACTOR = 1.25

FALLBACK_ONEWAY_MILES = 400   # matches the pre-Phase-5E hardcoded placeholder

CACHE_PREFIX = 'geocode_'   # AppSetting key: geocode_<normalized place> -> JSON {lat, lon}


def _cache_key(place: str) -> str:
    return CACHE_PREFIX + place.strip().lower()


def _geocode(place: str):
    """{lat, lon} for a place name, or None if it can't be resolved. Checks
    the cache first (a hit never touches the network); never raises."""
    if not place or not place.strip():
        return None
    key = _cache_key(place)
    try:
        with db_session() as session:
            row = session.query(AppSetting).filter_by(key=key).first()
            if row:
                return json.loads(row.value)
    except Exception:
        pass

    try:
        url = NOMINATIM_URL.format(q=urllib.parse.quote(place.strip()))
        from core import egress                    # item 8: the one door out
        results = egress.get_json(url, headers={'User-Agent': USER_AGENT}, timeout=REQUEST_TIMEOUT)
        if not results:
            return None
        coords = {'lat': float(results[0]['lat']), 'lon': float(results[0]['lon'])}
    except Exception as e:
        logger.info('trip_distance: geocode failed for %r: %s', place, e)
        return None

    try:
        with db_session() as session:
            session.add(AppSetting(key=key, value=json.dumps(coords)))
            session.commit()
    except Exception as e:
        logger.warning('trip_distance: geocode cache write failed: %s', e)

    return coords


def _haversine_miles(lat1, lon1, lat2, lon2) -> float:
    r = 3958.8  # Earth's radius in miles
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def get_route_points(origin: str, destination: str) -> dict:
    """The two ends of the drive, for the printed itinerary's map, with the same one-way estimate the trip budget uses.
    Uses the same cache and the same place names as get_drive_distance, so a trip already priced sends nothing new."""
    o = _geocode(origin)
    d = _geocode(destination)
    if not o or not d:
        return {'found': False, 'miles': None, 'origin': None, 'destination': None}
    great_circle = _haversine_miles(o['lat'], o['lon'], d['lat'], d['lon'])
    return {'found': True, 'miles': round(great_circle * ROAD_DISTANCE_FACTOR), 'origin': o, 'destination': d,
            'road_factor': ROAD_DISTANCE_FACTOR}


def get_drive_distance(origin: str, destination: str) -> dict:
    """
    One-way estimated driving distance in miles. Returns
    {miles, live, source}:
      live=True  — both places geocoded successfully; miles is a real
                   (great-circle x road-factor) estimate
      live=False — one or both places couldn't be resolved (empty, typo,
                   Nominatim unreachable); miles is the honest
                   FALLBACK_ONEWAY_MILES placeholder
    """
    o = _geocode(origin)
    d = _geocode(destination)
    if not o or not d:
        return {'miles': FALLBACK_ONEWAY_MILES, 'live': False, 'source': 'estimate'}

    great_circle = _haversine_miles(o['lat'], o['lon'], d['lat'], d['lon'])
    miles = round(great_circle * ROAD_DISTANCE_FACTOR)
    return {'miles': miles, 'live': True, 'source': 'OpenStreetMap (estimated road distance)'}
