/*
 * Groundwork 2.0 — teaching layer entry point.
 *
 * THE SEAM
 * --------
 * Everything the 2.0 teaching platform adds to the front end lives under this
 * directory. Nothing here ships in a GW LTS build: groundwork*.spec strips
 * static/js/teaching/ when GW_PRODUCT=lts, and server.py emits no loader tag
 * for a file that is not there. So the boundary is a path, not a runtime flag,
 * and an LTS build does not merely disable the teaching layer - it does not
 * contain it.
 *
 * THE ONE RULE THAT KEEPS THAT TRUE
 * ---------------------------------
 * The dependency runs one way. Teaching code may read app.js's globals and the
 * DOM it renders. app.js may never reference anything in here - no import, no
 * `if (window.GWTeaching)`, no teaching-shaped branch. The moment app.js knows
 * this directory exists, the LTS build carries a dead branch for a feature it
 * cannot run, on the machines with the least room to spare, and the seam is
 * back to being a runtime flag wearing a directory as a costume.
 *
 * smoke_test.py enforces that rule by grepping app.js. It is a real check, not
 * a comment.
 *
 * This file is the seam itself, not the teaching layer. The modules beside it
 * are the teaching layer (corrected 2026-09-27 - this note said "none of the
 * blueprint's mechanisms are built" when it was written, 2026-09-02, and was
 * true then). Built since: the Solution Engine and honest-no (core/solution.py,
 * paths.js), green-light, the proactive threshold, the Trophy Room's proof
 * standard, §8's teaching on eleven surfaces, and (2026-09-28) the Willingness
 * Layer's observed and declared channels with its home, the working picture
 * (willingness.js), and the break-detector (core/breaks.py, shown there and in
 * funds.js). Still not built: the Willingness Layer's inferred channel. The
 * blueprint's Status section
 * keeps the current list: gw 2.0/GW_2.0_TEACHING_PLATFORM_BLUEPRINT.md.
 */
(function () {
  'use strict';

  var GWTeaching = {
    /* Set from server.py's loader tag so the build stamp is visible here too. */
    version: null,

    /* Modules register themselves; the entry point never imports them by name,
     * so adding one is adding a file, not editing this one. */
    _modules: [],

    register: function (name, mod) {
      if (!name || typeof name !== 'string') {
        throw new Error('GWTeaching.register: a module needs a name');
      }
      if (this._modules.some(function (m) { return m.name === name; })) {
        throw new Error('GWTeaching.register: duplicate module "' + name + '"');
      }
      this._modules.push({ name: name, mod: mod });
      return mod;
    },

    modules: function () {
      return this._modules.map(function (m) { return m.name; });
    },

    /* Present only in a teaching build, by construction: in an LTS build this
     * file is absent, so window.GWTeaching is undefined. Anything that needs to
     * know should ask that question, and only from inside this directory. */
    isPresent: function () { return true; }
  };

  var tag = document.currentScript;
  if (tag && tag.src) {
    var m = tag.src.match(/[?&]v=([^&]+)/);
    if (m) { GWTeaching.version = decodeURIComponent(m[1]); }
  }

  window.GWTeaching = GWTeaching;
})();
