/*
 * Household facts on the 2.0 surfaces (gw 2.0/ONBOARDING_REVISIT.md, item 30).
 *
 * Teaching layer: absent from an LTS bundle by path. 1.x asks only the facts it has readers for (the state and the
 * pay frequency, in app.js); the questions here have readers only in 2.0 (item 26), so they are asked only here (O9).
 *
 * Rob, 2026-10-02: "Onboarding is a data-collection mechanism, not a conversation script. Every question must
 * create or update a canonical fact that the product actually uses." So:
 *   - onboarding, Settings' "Your home" card and the inline prompts set the SAME facts, through one route
 *     (POST /api/settings/household -> core.household.set_household_fact), each with its source
 *   - every field can be skipped; a skipped fact stays unanswered - nothing is assumed in its place
 *   - a known answer is never asked again inline; an unknown one is asked where it is needed, and the prompt goes
 *     once it is answered (O8)
 *   - the bills screen is labelled from the answers; the ledger's category names do not change (O4)
 */
(function () {
  'use strict';

  // The answers, in words. Keys and values are core/household.py FACTS (the server refuses anything else).
  var Q = {
    housing_status: { asks: 'Do you own or rent your home?',
                      words: { own: 'Own', rent: 'Rent', other: 'Something else' } },
    electricity_included: { asks: 'Does your rent include electricity?', onlyIf: { housing_status: ['rent'] },
                            words: { yes: 'Yes', no: 'No', not_sure: 'Not sure' } },
    heating_fuel: { asks: 'What heats your home?',
                    words: { natural_gas: 'Natural gas', propane: 'Propane', electric: 'Electricity',
                             heating_oil: 'Heating oil', wood_pellets: 'Wood or pellets', included: 'Heat is included in my rent',
                             other: 'Something else', not_sure: 'Not sure' } },
    heating_payment: { asks: 'How do you pay for your heating fuel?', onlyIf: { heating_fuel: ['natural_gas', 'propane', 'heating_oil'] },
                       words: { by_bill: 'A bill (or delivery) for what I use', even_monthly: 'The same amount every month (a budget plan)',
                                prepaid: 'A prepaid contract', not_sure: 'Not sure' } },
    vehicle_fuel: { asks: 'What type of fuel does your vehicle use?',
                    words: { gasoline: 'Gasoline', diesel: 'Diesel', electric: 'Electric (charged)', other: 'Something else',
                             none: 'No vehicle / no fuel expense' } },
    // Item 56 (MUNICIPAL_UTILITIES.md, U2): a SET of answers - the services one city/village/town bill covers
    municipal_covers: { asks: 'What does your municipal utility bill cover?', multi: true,
                        words: { water: 'Water', sewer: 'Sewer', trash: 'Trash', electricity: 'Electricity',
                                 natural_gas: 'Natural gas', none: "I don't get a municipal utility bill" } }
  };
  // Item 56 U3: where each service is filed when the city doesn't cover it
  var SERVICE_LEAF = { water: 'Water / Sewer', sewer: 'Water / Sewer', trash: 'Trash', electricity: 'Electric',
                       natural_gas: 'Natural Gas' };   // item 84: was 'Gas'
  var FUEL = { natural_gas: 'natural gas', propane: 'propane', heating_oil: 'heating oil', wood_pellets: 'wood or pellets',
               other: 'other fuel' };

  // The state is asked in Settings' Budget card on both lines; inline it uses app.js's own list (US_STATES).
  function _stateQ() {
    var words = {};
    (typeof US_STATES !== 'undefined' ? US_STATES : []).forEach(function (st) { words[st[0]] = st[1]; });
    return { asks: 'Which state is your home in?', words: words };
  }

  // Item 56 U2: a multi-answer fact is a checklist; its value is the sorted, comma-joined set (the server's form)
  function _checklist(key, value, source) {
    var q = Q[key], have = (value || '').split(',');
    return '<div class="field" data-gw-q="' + key + '"><label>' + esc(q.asks) + '</label>'
      + '<div data-gw-fact="' + key + '" data-gw-multi="1" data-gw-source="' + source + '">'
      + Object.keys(q.words).map(function (v) {
          return '<label style="display:inline-block;margin:2px 12px 2px 0;font-size:var(--fs-sm)"><input type="checkbox" value="' + v + '"'
            + (have.indexOf(v) >= 0 ? ' checked' : '') + '> ' + esc(q.words[v]) + '</label>';
        }).join('')
      + '</div>' + (source === 'settings' ? '<div data-gw-municipal-services>' + _municipalServices(value) + '</div>' : '')
      + '</div>';
  }

  // The checklist's value: "none" alone, or the checked services sorted; '' when nothing is checked (withdrawn).
  function _multiValue(box, changed) {
    var boxes = [].slice.call(box.querySelectorAll('input[type=checkbox]'));
    if (changed && changed.value === 'none' && changed.checked) boxes.forEach(function (b) { if (b !== changed) b.checked = false; });
    else if (changed && changed.checked) boxes.forEach(function (b) { if (b.value === 'none') b.checked = false; });
    return boxes.filter(function (b) { return b.checked; }).map(function (b) { return b.value; }).sort().join(',');
  }

  // Item 56 U3: each service - on the municipal bill, or its own company and the category it is filed under. Nothing
  // is concluded from a bill that isn't there (absence is not zero): a service not on the city bill is a question.
  function _municipalServices(value) {
    if (!value || value === 'none') return '';
    var on = value.split(','), w = Q.municipal_covers.words;
    var lines = ['water', 'sewer', 'trash', 'electricity', 'natural_gas'].map(function (s) {
      return on.indexOf(s) >= 0
        ? esc(w[s]) + ': on your municipal utility bill (filed under Municipal Utilities).'
        : esc(w[s]) + ': not on your municipal bill. If you pay for it, its own company\'s charge is filed under ' + esc(SERVICE_LEAF[s]) + '.';
    });
    return '<div style="font-size:var(--fs-xs);color:var(--slate-2);line-height:1.7;margin-top:4px">' + lines.join('<br>') + '</div>';
  }

  function _select(key, value, source) {
    if (Q[key] && Q[key].multi) return _checklist(key, value, source);
    var q = key === 'home_state' ? _stateQ() : Q[key];
    return '<div class="field" data-gw-q="' + key + '"><label>' + esc(q.asks) + '</label>'
      + '<select class="field-input" data-gw-fact="' + key + '" data-gw-source="' + source + '">'
      + '<option value="">Skip for now</option>'
      + Object.keys(q.words).map(function (v) {
          return '<option value="' + v + '"' + (value === v ? ' selected' : '') + '>' + esc(q.words[v]) + '</option>';
        }).join('')
      + '</select></div>';
  }

  // A question shows only when its answer can matter: electricity-in-rent only for renters, how heating is paid only
  // for a fuel that is billed or delivered. The "heat included" answer is offered only to renters.
  function _applyConditions(root) {
    var vals = {};
    root.querySelectorAll('[data-gw-fact]').forEach(function (f) { vals[f.dataset.gwFact] = f.value; });
    Object.keys(Q).forEach(function (key) {
      var cond = Q[key].onlyIf, box = root.querySelector('[data-gw-q="' + key + '"]');
      if (!box || !cond) return;
      var show = Object.keys(cond).every(function (k) { return cond[k].indexOf(vals[k]) >= 0; });
      box.classList.toggle('hidden', !show);
    });
    var inc = root.querySelector('[data-gw-fact="heating_fuel"] option[value="included"]');
    if (inc) inc.hidden = vals.housing_status !== 'rent';
  }

  // ── Onboarding: the 2.0 questions on the home screen ──────────────────────────────────────────────────────
  function _onboarding() {
    var more = document.getElementById('obHomeMore');
    if (!more || more.dataset.gwFilled) return;
    more.dataset.gwFilled = '1';
    more.innerHTML = ['housing_status', 'electricity_included', 'heating_fuel', 'heating_payment', 'vehicle_fuel']
      .map(function (k) { return _select(k, '', 'onboarding'); }).join('');
    more.addEventListener('change', function () { _applyConditions(more); });
    _applyConditions(more);
  }

  // Consumers of housing_status and heating_fuel (core/household.py FACTS): the bills screen's words. Only labels
  // change; the heating bill is filed by fuel so propane and oil never feed the natural gas estimate.
  function _housingLabel(a) {
    return a.housing_status === 'own' ? 'Mortgage ($/month)'
         : a.housing_status === 'rent' ? 'Rent ($/month)' : 'Mortgage or rent ($/month)';
  }
  function _heatingLabel(a) {
    var f = a.heating_fuel;
    if (f === 'electric' || f === 'included') return null;      // in the electric bill, or in the rent: no line
    return FUEL[f] ? 'Home heating fuel: ' + FUEL[f] + ' ($/month)' : 'Home heating fuel ($/month)';
  }
  function _labelBills() {
    var a = (typeof _obAnswers !== 'undefined' && _obAnswers) || {};   // app.js's walk-through answers (shared global scope)
    setText('obExpHousingLabel', _housingLabel(a));
    var heat = _heatingLabel(a), gas = document.getElementById('obExpGasField');
    if (gas) gas.classList.toggle('hidden', heat === null);
    if (heat) setText('obExpGasLabel', heat);
    var el = document.getElementById('obExpElectricField');
    if (el) el.classList.toggle('hidden', a.housing_status === 'rent' && a.electricity_included === 'yes');
    var fuel = document.getElementById('obExpFuelField');
    if (fuel) fuel.classList.toggle('hidden', a.vehicle_fuel === 'electric' || a.vehicle_fuel === 'none');
  }

  var prepOriginal = window._obPrepareExpensesStep;
  if (typeof prepOriginal === 'function') {
    window._obPrepareExpensesStep = function () {
      var out = prepOriginal.apply(this, arguments);
      try { _labelBills(); } catch (e) { /* never break onboarding */ }
      return out;
    };
  }
  var catOriginal = window._obHeatingCategory;
  window._obHeatingCategory = function (a) {
    var f = (a || {}).heating_fuel;
    if (f === 'propane') return { cat: 'Propane', name: 'Propane' };
    if (f === 'heating_oil') return { cat: 'Heating Oil', name: 'Heating oil' };
    if (f === 'wood_pellets' || f === 'other') return { cat: 'Home Heating', name: 'Home heating' };
    if (f === 'natural_gas') return { cat: 'Natural Gas', name: 'Natural gas' };
    return catOriginal ? catOriginal(a) : { cat: 'Natural Gas', name: 'Home heating fuel' };
  };

  // O7: what each 2.0 answer turned on, in the summary - every line true of what item 26 now does.
  ['housing_status', 'electricity_included', 'heating_fuel', 'heating_payment', 'vehicle_fuel'].forEach(function (k) {
    _OB_FACT_LABELS[k] = { housing_status: 'whether you own or rent', electricity_included: 'whether rent includes electricity',
                           heating_fuel: 'what heats your home', heating_payment: 'how you pay for heating fuel',
                           vehicle_fuel: 'your vehicle fuel' }[k];
  });
  var effectOriginal = window._obFactEffect;
  window._obFactEffect = function (key, v) {
    var fuel = FUEL[v] || v;
    switch (key) {
      case 'housing_status': return v === 'other' ? '' : 'Your bills list ' + (v === 'own' ? 'a mortgage' : 'rent') + '.';
      case 'electricity_included': return v === 'yes' ? 'Your rent includes electricity, so there is no electricity estimate.' : '';
      case 'heating_fuel':
        if (v === 'natural_gas') return 'Natural gas heats your home: your Budget page can estimate the gas bill.';
        if (v === 'electric') return 'Electric heat: heating is part of your electricity bill.';
        if (v === 'included') return 'Your rent includes heat, so there is no heating estimate.';
        if (v === 'not_sure') return 'Heating fuel not sure: no natural gas estimate until you know.';
        if (v === 'propane' || v === 'heating_oil') return fuel.charAt(0).toUpperCase() + fuel.slice(1) + ' heats your home: your '
          + 'Budget page can estimate it from your deliveries, at EIA\'s weekly residential price (published October to March).';
        return 'Your heating line is ' + fuel + '. Groundwork does not price ' + fuel + ' yet, so there is no estimate for it.';
      case 'heating_payment':
        return (v === 'even_monthly' || v === 'prepaid')
          ? 'A ' + (v === 'prepaid' ? 'prepaid' : 'same-every-month') + ' heating bill does not follow the weather, so the estimate does not try to fit it.' : '';
      case 'vehicle_fuel':
        if (v === 'gasoline') return 'Gasoline: your Budget page can estimate fuel from your fill-ups.';
        if (v === 'diesel') return 'Diesel: your Budget page can estimate fuel from your fill-ups, at EIA\'s weekly diesel price.';
        if (v === 'electric') return 'An electric vehicle: no gasoline estimate.';
        if (v === 'none') return 'No vehicle fuel: no fuel line in your bills.';
        return '';
      default: return effectOriginal ? effectOriginal(key, v) : '';
    }
  };

  // ── Settings: "Your home" (O8) - the same facts, source 'settings' ────────────────────────────────────────
  function _settingsCard(facts) {
    var anchor = document.getElementById('settingsHomeState');
    var after = anchor && anchor.closest('.card');
    if (!after) return;
    var card = document.getElementById('gwYourHome');
    if (!card) {
      card = document.createElement('div');
      card.className = 'card';
      card.id = 'gwYourHome';
      after.parentNode.insertBefore(card, after.nextSibling);
      card.addEventListener('change', function (ev) {
        var f = ev.target.closest('[data-gw-fact]');
        if (!f) return;
        _applyConditions(card);
        if (f.dataset.gwMulti) {                    // item 56: the checklist's whole set is the answer
          var v = _multiValue(f, ev.target);
          var sv = card.querySelector('[data-gw-municipal-services]');
          if (sv) sv.innerHTML = _municipalServices(v);
          _set(f.dataset.gwFact, v, 'settings');
          return;
        }
        _set(f.dataset.gwFact, f.value, 'settings');
      });
    }
    card.innerHTML = '<div class="card-label">Your home</div>'
      + '<div style="font-size:var(--fs-sm);color:var(--slate-2);margin-bottom:12px">What these answers turn on is the estimates on your Budget page. Choose "Skip for now" to withdraw an answer: nothing is assumed in its place.</div>'
      + Object.keys(Q).map(function (k) { return _select(k, (facts[k] || {}).value || '', 'settings'); }).join('');
    _applyConditions(card);
  }

  function _set(key, value, source) {
    return API.post('/api/settings/household', { key: key, value: value || null, source: source })
      .catch(_gwErr('household._set'));
  }

  function _loadFacts() {
    return API.get('/api/settings/household').then(function (r) { return (r && (r.data || r)) || {}; });
  }

  var settingsOriginal = window.renderSettings;
  if (typeof settingsOriginal === 'function') {
    window.renderSettings = function () {
      var out = settingsOriginal.apply(this, arguments);
      _loadFacts().then(_settingsCard).catch(_gwErr('household.settings'));
      return out;
    };
  }

  // ── Inline: ask a missing fact where it is needed (O8), source 'inline_prompt' ─────────────────────────────
  // ask(host, keys, facts, done): one select per key that is still unanswered; the prompt is gone once answered.
  function ask(host, keys, facts, done) {
    var open = keys.filter(function (k) { return (Q[k] || k === 'home_state') && !((facts[k] || {}).value); });
    if (!open.length) { host.innerHTML = ''; return; }
    host.innerHTML = '<div style="font-size:var(--fs-sm);color:var(--slate);margin-top:8px" data-gw-inline>'
      + open.map(function (k) { return _select(k, '', 'inline_prompt'); }).join('') + '</div>';
    host.onchange = function (ev) {
      var f = ev.target.closest('[data-gw-fact]');
      if (!f) return;
      if (f.dataset.gwMulti) {                      // item 56: a checklist is sent with its own Save, not per tick
        _multiValue(f, ev.target);
        return;
      }
      if (!f.value) return;
      _set(f.dataset.gwFact, f.value, 'inline_prompt').then(function () { if (done) done(); });
    };
    [].slice.call(host.querySelectorAll('[data-gw-multi]')).forEach(function (f) {
      var b = document.createElement('button');
      b.type = 'button'; b.className = 'btn btn-secondary btn-sm'; b.textContent = 'Save';
      b.onclick = function () {
        var v = _multiValue(f);
        if (v) _set(f.dataset.gwFact, v, 'inline_prompt').then(function () { if (done) done(); });
      };
      f.appendChild(b);
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', _onboarding);
  else _onboarding();

  GWTeaching.register('household', { ask: ask, load: _loadFacts, questions: Q, municipalServices: _municipalServices,
                                      housingLabel: _housingLabel, heatingLabel: _heatingLabel });
})();
