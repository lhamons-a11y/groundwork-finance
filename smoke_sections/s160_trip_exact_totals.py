"""A fare or hotel total the user chose or typed is used to the cent (gw 2.0/TRIP_EXACT_TOTALS.md, item 48; Rob
2026-10-08: "it should grab the exact total since a good chance the user ordered it").

    E1  the flight total and the hotel quote total go into the trip budget exactly, not rounded to dollars
    E2  the planner's own estimates are still rounded (they were never exact)
"""
import json
import re
import shutil
import subprocess


def run(ctx):
    check, app = ctx.check, ctx.app_src
    check('s160 E1 the flight total and the hotel quote total are kept to the cent',
          'transportCost = tripExactTotal(_tripQuoteData.flightTotal);' in app
          and 'hotelCost = tripExactTotal(_tripQuoteData.hotelTotal);' in app
          and 'Math.round(_tripQuoteData.flightTotal)' not in app and 'Math.round(_tripQuoteData.hotelTotal)' not in app)
    check('s160 E2 the planner\'s own estimates are still rounded (fuel, a per-night guess)',
          'transportCost  = Math.round(gallons * gasRate);' in app and 'hotelCost = Math.round(hotelPerNight * nights);' in app)
    node = shutil.which('node')
    check('s160 node is available (skip the rest if not)', bool(node))
    if not node:
        return
    m = re.search(r'\nfunction tripExactTotal\(.*?\n\}\n', app, re.S)
    src = m.group(0) if m else ''
    p = subprocess.run([node, '-e', src + 'console.log(JSON.stringify([612.48, 690, 1234.567, "301.1"].map(tripExactTotal)))'],
                       capture_output=True, text=True, encoding='utf-8', timeout=60)
    out = json.loads(p.stdout.strip() or 'null')
    check('s160 E1 an exact total stays exact ($612.48 is $612.48, not $612)', out == [612.48, 690, 1234.57, 301.1])
