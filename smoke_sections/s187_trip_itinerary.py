"""Item 60: bring in a whole itinerary and see the trip's budget (gw 2.0/TRIP_ITINERARY_IMPORT.md I1-I7, RULED
2026-10-09; built on "build all items that have been ruled on").

    I1  pasted text, a PDF or a saved email (.eml), read on this computer; nothing fetched
    I2  broken into parts - flight, lodging, car, activity, transfer, insurance, fees - with dates and paid / due
    I3  every figure must be in the document; Groundwork's sum beside the document's total, both shown when they differ
    I4  nothing is used or saved until the person ticks the parts and says yes
    I5  Expedia, Booking.com, an airline receipt and a hotel folio are read without the model (AI off works)
    I6  the file is not kept; confirmation numbers never reach the model, and only a flight's travels with its part
"""
import io
import json
import os
import re
import shutil
import subprocess
import tempfile


def run(ctx):
    check, c, H, HJ = ctx.check, ctx.c, ctx.H, ctx.HJ
    app = ctx.app_src
    from tests import itineraries as S
    from core import itinerary as it
    from core.database import AppSetting, TripBooking, DATA_DIR, db_session

    def counts():
        with db_session() as s:
            return s.query(AppSetting).count(), s.query(TripBooking).count(), sorted(os.listdir(DATA_DIR))
    before = counts()

    def read(text):
        r = c.post('/api/trip/itinerary/read', headers=HJ, data=json.dumps({'text': text}))
        return r.status_code, (r.get_json() or {}).get('data') or {}

    # ── I5 / I2 / I3: the known formats ──
    code, ex = read(S.EXPEDIA)
    got = [(p['kind'], p['vendor'], p['amount'], p['status']) for p in ex.get('parts', [])]
    check(f's187 I5/I2 an Expedia itinerary breaks into its five parts, without a model ({got})',
          code == 200 and ex['needs_model'] is False and ex['format'] == 'expedia' and got == [
              ('flight', 'United', 722.0, 'paid'), ('lodging', 'The Curtis Denver', 561.15, 'paid'),
              ('car', 'Hertz, Denver Intl Airport', 179.7, 'due_later'), ('insurance', 'Trip protection plan', 64.0, 'paid'),
              ('fees', 'Expedia booking fee', 15.0, 'paid')])
    fl = ex['parts'][0] if ex.get('parts') else {}
    check('s187 I2 each part keeps its dates and its figures as printed; a part with several lines is summed by Groundwork and says so',
          fl.get('start') == '2026-11-12' and fl.get('end') == '2026-11-15' and fl.get('basis') == 'sum'
          and [l['amount'] for l in fl.get('lines', [])] == [312.4, 312.4, 97.2]
          and ex['parts'][2]['start'] == '2026-11-12' and ex['parts'][2]['end'] == '2026-11-15')
    check('s187 I3 the parts\' sum is shown beside the document\'s own total (they agree here)',
          ex.get('sum') == 1541.85 and ex.get('printed_total') == 1541.85 and ex.get('agree') is True and ex.get('warnings') == [])
    _, bk = read(S.BOOKING_COM)
    _, al = read(S.AIRLINE)
    _, ho = read(S.HOTEL_CHAIN)
    check('s187 I5 Booking.com, an airline receipt and a hotel folio each read without a model, with dates and how they are paid',
          bk.get('format') == 'booking_com' and [(p['kind'], p['amount'], p['status'], p['start'], p['end']) for p in bk['parts']]
          == [('lodging', 455.82, 'due_later', '2027-03-05', '2027-03-08')]
          and al.get('format') == 'airline' and [(p['kind'], p['vendor'], p['amount'], p['status']) for p in al['parts']]
          == [('flight', 'Delta', 459.37, 'paid')]
          and ho.get('format') == 'hotel_chain' and [(p['kind'], p['amount'], p['status']) for p in ho['parts']]
          == [('lodging', 414.75, 'due_later')] and ho.get('printed_total') == 414.75)

    # ── I6: confirmation numbers ──
    blob = json.dumps(ex)
    check('s187 I6 confirmation numbers are taken out; only the flight\'s travels, with its part, for a booking',
          '72041188305512' not in blob and '88231945' not in blob and blob.count('KX7Q2M') == 1
          and fl.get('confirmation') == 'KX7Q2M' and al['parts'][0].get('confirmation') == 'GH4T9Z'
          and all('confirmation' not in p for p in ex['parts'][1:]))
    code, un = read(S.UNKNOWN)
    check('s187 I2/I6 a sender Groundwork has no reader for goes to the model - with its reference number already removed',
          code == 200 and un.get('needs_model') is True and un.get('parts') == [] and 'TOUR-5521' not in un.get('text', '')
          and 'TOUR-5521' not in un.get('model_text', '') and '$180.00' in un.get('model_text', ''))

    # ── I1: files ──
    eml = ('From: Booking.com <noreply@booking.com>\r\nSubject: Your booking\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n'
           + S.BOOKING_COM.replace('\n', '\r\n')).encode()
    r = c.post('/api/trip/itinerary/read', headers=H, data={'file': (io.BytesIO(eml), 'confirmation.eml')},
               content_type='multipart/form-data')
    e = (r.get_json() or {}).get('data') or {}
    import pdf_statement
    seen, real = [], pdf_statement.extract_text
    pdf_statement.extract_text = lambda b: (seen.append(b), S.AIRLINE)[1]
    try:
        rp = c.post('/api/trip/itinerary/read', headers=H, data={'file': (io.BytesIO(b'%PDF-1.4 stand-in'), 'receipt.pdf')},
                    content_type='multipart/form-data')
    finally:
        pdf_statement.extract_text = real
    p = (rp.get_json() or {}).get('data') or {}
    re_ = c.post('/api/trip/itinerary/read', headers=H, data={'file': (io.BytesIO(b''), 'x.pdf')}, content_type='multipart/form-data')
    check('s187 I1 a saved email and a PDF are read on this computer (the PDF by the statement reader); an empty file says so',
          r.status_code == 200 and e.get('format') == 'booking_com' and e['parts'][0]['amount'] == 455.82
          and rp.status_code == 200 and seen == [b'%PDF-1.4 stand-in'] and p.get('format') == 'airline'
          and re_.status_code == 400 and 'empty' in (re_.get_json() or {}).get('error', ''))

    # ── I3: the model's transcription, checked ──
    raw = {'sender': 'Sunny Isles Tours', 'components': [
        {'kind': 'activity', 'vendor': 'Snorkel trip', 'start': '2027-06-03', 'price': 180.0, 'status': 'paid'},
        {'kind': 'activity', 'vendor': 'Sunset cruise', 'start': '2027-06-04', 'price': 95.0, 'status': 'due_later'},
        {'kind': 'activity', 'vendor': 'Parasailing', 'price': 140.0},
        {'kind': 'spaceflight', 'vendor': 'Moon', 'price': 95.0}], 'printed_total': 275.0}
    ck = c.post('/api/trip/itinerary/check', headers=HJ, data=json.dumps({'text': un['text'], 'raw': raw})).get_json()['data']
    para = next((p for p in ck['parts'] if p['vendor'] == 'Parasailing'), {})
    check('s187 I3 a figure the model planted that the document does not contain is dropped and said; an unknown kind is left out',
          [p['amount'] for p in ck['parts']] == [180.0, 95.0, None] and para.get('lines') == []
          and any('Parasailing' in w and '140.00' in w and 'not in the document' in w for w in ck['warnings'])
          and any('spaceflight' in w for w in ck['warnings']) and ck['source'] == 'model' and ck['agree'] is True)
    raw2 = {'components': [raw['components'][0]], 'printed_total': 275.0}
    d2 = c.post('/api/trip/itinerary/check', headers=HJ, data=json.dumps({'text': un['text'], 'raw': raw2})).get_json()['data']
    check('s187 I3 when the parts and the document\'s total differ, both are shown - never reconciled',
          d2['sum'] == 180.0 and d2['printed_total'] == 275.0 and d2['agree'] is False)
    raw3 = {'components': [{'kind': 'activity', 'vendor': 'Snorkel trip', 'price': 180.0}], 'printed_total': 9999.0}
    d3 = c.post('/api/trip/itinerary/check', headers=HJ, data=json.dumps({'text': un['text'], 'raw': raw3})).get_json()['data']
    bad = c.post('/api/trip/itinerary/check', headers=HJ, data=json.dumps({'text': un['text'], 'raw': 'Here is the JSON you asked for'}))
    check('s187 I3 a printed total the document lacks is dropped too; an answer that is not the asked shape is refused whole',
          d3['printed_total'] is None and d3['agree'] is None and bad.status_code == 400)

    # ── I4 / I6: nothing written, nothing kept ──
    check('s187 I4/I6 reading and checking wrote nothing - no setting, no booking, no file kept', counts() == before)
    rd = app.split('async function _readTripItinerary(')[1].split('\n}')[0]
    ap = app.split('async function _applyTripItinerary(')[1].split('\n}')[0]
    check('s187 I4 the parts are used only from the "Use the ticked parts" button; a booking only for a ticked paid flight',
          app.count('onclick="_applyTripItinerary()"') == 1 and '/api/trip/budget' not in rd and '/api/trip/budget' not in ap
          and "g(`itinBook${p.id}`)?.checked" in ap and "if (!g(`itinUse${p.id}`)?.checked) continue;" in ap)
    check('s187 I5 with AI off the known formats still read: AI is asked about only when the server says a model is needed',
          rd.index('if (res.needs_model)') < rd.index('aiEnabled()') and 'callAI(' not in rd)
    srv = ctx.server_src.split("def trip_itinerary_read(")[1].split('\n@')[0]
    check('s187 I6 the read route never logs the document', 'text' not in ''.join(re.findall(r'logging\.[^\n]*', srv)))

    # ── the budget: each line says it came from the itinerary ──
    up = app.split('function tripUpdateBudget(')[1].split('\nfunction ')[0]
    check('s187 I4 the used parts become the trip\'s lines, each sourced "from your <sender> itinerary"; car, transfers, insurance and fees are their own line',
          'transportNote = `${fmt(transportCost)} total (from ${itin.label})`' in up and 'hotelSource = `from ${itin.label}`' in up
          and 'activitiesSource = `from ${itin.label}`' in up and '+ activitiesCost + otherCost' in up
          and "line('🧾 Other', d.other, d.otherSource, 'trip.other')" in app)   # item 103: the line carries its figure key
    node = shutil.which('node')
    out = {}
    if node:
        fn = lambda name: re.search(r'\nfunction ' + name + r'\(.*?\n\}\n', app, re.S).group(0)
        js = ('function tripExactTotal(x) { return Math.round(Number(x) * 100) / 100; }\n' + fn('_itinLabel') + fn('_tripItineraryTotals') +
              'let _tripItinerary = {sender: "Expedia", parts: [{kind:"flight",amount:722},{kind:"lodging",amount:561.15},'
              '{kind:"car",amount:179.7},{kind:"insurance",amount:64},{kind:"fees",amount:15}]};\n'
              'const a = _tripItineraryTotals(); _tripItinerary = {sender: "your", parts: [{kind:"activity",amount:180}]};\n'
              'console.log(JSON.stringify({a, b: _tripItineraryTotals()}));')
        fd, path = tempfile.mkstemp(suffix='.js')
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(js)
        try:
            out = json.loads(subprocess.run([node, path], capture_output=True, text=True, encoding='utf-8', timeout=60).stdout or '{}')
        except Exception:                      # noqa: BLE001
            out = {}
        finally:
            os.remove(path)
    check(f's187 I4 the parts, run in Node, land on their lines ({out})',
          out.get('a') == {'label': 'your Expedia itinerary', 'flight': 722, 'lodging': 561.15, 'activity': None, 'other': 258.7,
                           'otherWhat': 'car, insurance, fees'}
          and out.get('b', {}).get('label') == 'your itinerary' and out['b'].get('activity') == 180)
