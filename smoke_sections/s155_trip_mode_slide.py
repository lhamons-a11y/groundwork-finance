"""Drive / Fly cards slide (Rob 2026-10-08: "When I select the fly button the drive card should slide up and be hidden.
vice vera when i select drive. That will give the user more screen space.").

    M1  choosing Fly hides the drive card and shows the fly card, and the reverse; the hidden one ends display:none
    M2  the change slides (a height animation) when motion is allowed, and switches at once when reduced motion is
        asked for or the browser cannot animate
    M3  a second click mid-slide does not leave a card half-open or wrongly hidden
    R1  Round trip is a plain checkbox on the Google Flights row (Rob 2026-10-08, from his screenshot)
    R2  a round trip with no return date says so, instead of quietly searching one way
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
const els = { tripDriveDetails: el(''), tripFlyDetails: el('none'), tripModeDrive: el(''), tripModeFly: el('') };
const g = id => els[id];
let reduce = false;
const window = { matchMedia: () => ({ matches: reduce }) };
let _tripMode = 'drive'; const tripUpdateBudget = () => {}; const _tripCarryCities = () => {};
eval(process.argv[1]);
const D = els.tripDriveDetails, F = els.tripFlyDetails, out = {};
setTripMode('fly');
out.flyAnims = [D.anims.length, F.anims.length, D.anims[0] && D.anims[0].frames[1].height, F.anims[0] && F.anims[0].frames[0].height];
out.midway = [D.style.display, F.style.display];
D.anims[0].onfinish();
out.done = [D.style.display, F.style.display];
F.anims[0].onfinish && F.anims[0].onfinish();
setTripMode('drive');
const hideFly = F.anims[F.anims.length - 1];
setTripMode('fly');                                  // a second click before the slide ends
out.reclick = [hideFly.cancelled, F.style.display];
reduce = true; setTripMode('drive');
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
    src = _fn(app, '_slideTripPanel') + _fn(app, 'setTripMode')
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
