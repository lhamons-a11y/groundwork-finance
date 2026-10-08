"""Drive / Fly cards slide (Rob 2026-10-08: "When I select the fly button the drive card should slide up and be hidden.
vice vera when i select drive. That will give the user more screen space.").

    M1  choosing Fly hides the drive card and shows the fly card, and the reverse; the hidden one ends display:none
    M2  the change slides (a height animation) when motion is allowed, and switches at once when reduced motion is
        asked for or the browser cannot animate
    M3  a second click mid-slide does not leave a card half-open or wrongly hidden
    R1  Round trip is a plain checkbox on the Google Flights row (Rob 2026-10-08, from his screenshot)
    R2  a round trip with no return date says so, instead of quietly searching one way
    T1  Fly also slides away the top card's Destination and Home city, which repeat Flying to / Flying from (Rob
        2026-10-08: "Top card should also hide when fly is clicked. It does confuse a user (me)"); Drive brings them back
    T2  back to Drive, a city chosen only in the Fly section fills an empty Destination / Home city
    T3  while flying, the trip's destination is the Flying to city
"""
import json
import re
import shutil
import subprocess


def _fn(app, name):
    m = re.search(r'\nfunction ' + name + r'\(.*?\n\}\n', app, re.S)
    return m.group(0) if m else ''


RUNNER = r'''
function el(display) {
  const e = { style: { display }, scrollHeight: 300, offsetHeight: 300, classList: { toggle() {} }, anims: [] };
  e.animate = (frames, opts) => {
    const a = { frames, opts, cancelled: false, onfinish: null, cancel() { this.cancelled = true; } };
    e.anims.push(a); return a;
  };
  return e;
}
const els = { tripDriveDetails: el(''), tripFlyDetails: el('none'), tripModeDrive: el(''), tripModeFly: el(''),
              tripDestField: el(''), tripOriginField: el(''), tripFromCity: el(''), tripToCity: el(''),
              tripOrigin: el(''), tripDestination: el('') };
const g = id => els[id];
let reduce = false;
const window = { matchMedia: () => ({ matches: reduce }) };
let _tripMode = 'drive'; const tripUpdateBudget = () => {}; const _tripCarryCities = () => {};
eval(process.argv[1]);
const D = els.tripDriveDetails, F = els.tripFlyDetails, out = {};
setTripMode('fly');
out.topHid = [els.tripDestField.anims.length, els.tripOriginField.anims.length];
out.flyAnims = [D.anims.length, F.anims.length, D.anims[0] && D.anims[0].frames[1].height, F.anims[0] && F.anims[0].frames[0].height];
out.midway = [D.style.display, F.style.display];
D.anims[0].onfinish();
out.done = [D.style.display, F.style.display];
F.anims[0].onfinish && F.anims[0].onfinish();
setTripMode('drive');
const hideFly = F.anims[F.anims.length - 1];
setTripMode('fly');                                  // a second click before the slide ends
out.reclick = [hideFly.cancelled, F.style.display];
reduce = true;
els.tripToCity.value = 'Las Vegas, NV'; els.tripFromCity.value = 'New York City, NY (Metropolitan Area)';
els.tripDestination.value = ''; els.tripOrigin.value = 'Columbus, OH';
setTripMode('drive');
out.carriedBack = [els.tripDestination.value, els.tripOrigin.value];
out.topBack = [els.tripDestField.style.display, els.tripOriginField.style.display];
out.reduced = [D.style.display, F.style.display, F.anims.length, D.anims.length];
console.log(JSON.stringify(out));
'''


def run(ctx):
    check, app, html = ctx.check, ctx.app_src, ctx.html_src
    # Rob 2026-10-08 (screenshot): Round trip sits on the Google Flights row, as a plain checkbox, not a field.
    row = html[html.find('onclick="openFlightSearch()"'):html.find('id="tripFlightFare"')]
    check('s155 R1 Round trip is on the Google Flights row, once, as a plain checkbox',
          'id="tripRoundTrip" checked' in row and html.count('id="tripRoundTrip"') == 1
          and 'style="width:auto;margin:0">Round trip' in row)
    check('s155 R2 a round trip with no return date says so instead of searching one way',
          'Round trip is ticked: enter your return date above, or untick Round trip to search one way.' in app)
    check('s155 M1 setTripMode slides the two cards, one each way',
          "_slideTripPanel(driveDet, mode === 'drive');" in app and "_slideTripPanel(flyDet,   mode === 'fly');" in app)
    node = shutil.which('node')
    check('s155 node is available to run the slide (skip the rest if not)', bool(node))
    if not node:
        return
    src = _fn(app, '_slideTripPanel') + _fn(app, '_tripCarryBack') + _fn(app, 'setTripMode')
    p = subprocess.run([node, '-e', RUNNER, src], capture_output=True, text=True, encoding='utf-8', timeout=60)
    try:
        out = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        print('        node stderr:', p.stderr[-800:])
        out = {}
    check('s155 M2 Fly slides the drive card closed (to 0px) and the fly card open (from 0px)',
          out.get('flyAnims') == [1, 1, '0px', '0px'])
    check('s155 M1 the drive card stays on screen while it slides, then is hidden; the fly card is shown',
          out.get('midway') == ['', ''] and out.get('done') == ['none', ''])
    check('s155 M3 a second click mid-slide cancels the slide and leaves the card open',
          out.get('reclick') == [True, ''])
    check('s155 M2 with reduced motion the cards switch at once, with no animation',
          (out.get('reduced') or [None])[:2] == ['', 'none'] and out['reduced'][2] == 2)
    check("s155 T1 Fly slides the top card's Destination and Home city away; Drive brings them back",
          out.get('topHid') == [1, 1] and out.get('topBack') == ['', ''])
    check('s155 T2 back to Drive, a Fly-only city fills an empty Destination; a Home city already typed is kept',
          out.get('carriedBack') == ['Las Vegas, NV', 'Columbus, OH'])
    html = ctx.html_src
    check('s155 T1 the two top boxes carry the ids the slide uses',
          'id="tripDestField"' in html and 'id="tripOriginField"' in html)
    check('s155 T3 while flying, the trip budget\'s destination is the Flying to city',
          "const dest      = (_tripMode === 'fly' && g('tripToCity')?.value?.trim()) || g('tripDestination')?.value?.trim();" in app)
