/*
 * Utility bill estimates: the words, with no page in them (gw 2.0/UTILITY_ESTIMATES.md, item 26, ruled 2026-10-01).
 *
 * Teaching layer: absent from an LTS bundle by path. Pure, so the gate runs it in Node.
 *
 * Every figure here comes from the server's estimate (core/utility_estimate.py): EIA's outlook and the user's own
 * bills. A forecast is always EIA's, never Groundwork's (U4). A change is split into price and usage against the
 * same month last year, so a price rise is never read as using more (U6). And while budget totals still use the
 * saved amount (Rob, 2026-10-01: totals in a follow-up pass), nothing here says the budget "includes" the estimate -
 * only that the estimate does.
 */
(function (root) {
  'use strict';

  function _signed(n, f) { return (n < 0 ? '-' : '+') + f.money(Math.abs(n)); }

  function gas(d, f) {
    if (!d) return null;
    var lines = [];
    var reg = d.region || {};
    lines.push(reg.national
      ? 'Using U.S. averages; set your home state in Settings for your region\'s prices and weather.'
      : 'Using EIA\'s outlook for ' + reg.division_name + ' (your home state, ' + reg.state + ').');
    if (!d.estimate) return { lines: lines.concat([d.needs]), statement: null };
    var e = d.estimate, c = d.choice || {}, fc = d.forecast || {};
    var bill = 'Next month\'s gas bill (for ' + f.month(e.month) + '\'s gas)';
    if (e.method === 'fit') {
      lines.push(bill + ' is estimated at about ' + f.money(e.amount) + ': about ' + e.usage_mcf.toFixed(1)
        + ' MCF at EIA\'s forecast ' + f.money(e.price) + '/MCF, plus about ' + f.money(e.fixed) + ' a month fixed.');
      lines.push('Your own bills follow the weather closely enough to predict them: on months held out, within about '
        + f.money(c.fit_error) + ' on average.');
    } else if (e.method === 'baseline') {
      lines.push(bill + ' is estimated at about ' + f.money(e.amount) + ': ' + f.month(e.from_month) + '\'s bill of '
        + f.money(e.from_amount) + ', at EIA\'s forecast ' + f.money(e.price) + '/MCF instead of ' + f.money(e.from_price) + '.');
      var why = {
        not_enough_bills: 'There are not yet enough bills for a weather fit (' + (c.bills || 0) + ' so far; about 8 are needed, across heating and non-heating months).',
        fit_did_not_beat_baseline: 'A weather fit did not predict your past bills better than this simpler figure, so the simpler one is used.',
        fit_no_better_than_average: 'A weather fit did not predict your past bills meaningfully better than their average, so it is not used.',
        no_heating_slope: 'Your bills do not rise with the cold the way a heating bill does, so a weather fit is not used.',
        no_fit: 'A weather fit could not be made from your bills, so the simpler figure is used.',
        no_baseline_to_test: 'There is nothing yet to test a weather fit against, so the simpler figure is used.'
      }[c.reason];
      if (why) lines.push(why);
    } else {
      lines.push(bill + ' cannot be estimated yet: it needs ' + e.needs + '.');
    }
    var sp = d.split;
    if (sp) {
      lines.push(sp.assumes_same_usage
        ? 'Against ' + f.month(sp.vs_month) + ' (' + f.money(sp.last_year_bill) + '): ' + _signed(sp.price, f)
          + ', all from price - this figure assumes the same usage as last year.'
        : 'Against ' + f.month(sp.vs_month) + ' (' + f.money(sp.last_year_bill) + '): ' + _signed(sp.price, f)
          + ' from price and ' + _signed(sp.usage, f) + ' from usage.');
    }
    var statement = null;
    if (fc.price !== null && fc.price !== undefined && fc.prev_price !== null && fc.prev_price !== undefined
        && Math.abs(fc.price - fc.prev_price) >= 0.01) {
      statement = 'EIA forecasts residential natural gas in ' + (reg.national ? 'the U.S.' : reg.division_name) + ' at '
        + f.money(fc.price) + '/MCF for ' + f.month(fc.month) + ', ' + (fc.price > fc.prev_price ? 'up' : 'down') + ' from '
        + f.money(fc.prev_price) + ' in ' + f.month(fc.prev_month) + '; the gas estimate on your Budget page uses that forecast.';
      lines.push(statement);
    }
    if (d.saved_amount !== null && d.saved_amount !== undefined) {
      lines.push('Your saved Gas budget of ' + f.money(d.saved_amount) + ' still sets the budget totals; this estimate is shown beside it.');
    }
    return { lines: lines, statement: statement,
             source: 'From the U.S. Energy Information Administration\'s Short-Term Energy Outlook and your own gas bills.' };
  }

  // Electricity (U8's second slice): the same shape as gas, in kWh and cents per kWh - the units on the bill.
  function electric(d, f) {
    if (!d) return null;
    var lines = [];
    var reg = d.region || {};
    lines.push(reg.national
      ? 'Using U.S. averages; set your home state in Settings for your region\'s prices and weather.'
      : 'Using EIA\'s outlook for ' + reg.division_name + ' (your home state, ' + reg.state + ').');
    if (!d.estimate) return { lines: lines.concat([d.needs]), statement: null };
    var e = d.estimate, c = d.choice || {}, fc = d.forecast || {};
    var cents = function (p) { return (p * 100).toFixed(2) + '\u00a2/kWh'; };
    var bill = 'Next month\'s electric bill (for ' + f.month(e.month) + '\'s power)';
    if (e.method === 'fit') {
      var t = e.terms || [];
      var with_ = t.length === 2 ? 'heating and cooling both' : t[0] === 'cdd' ? 'cooling (your bills don\'t rise with the cold)'
        : 'heating (your bills don\'t rise with the heat)';
      lines.push(e.usage_identified
        ? bill + ' is estimated at about ' + f.money(e.amount) + ': about ' + Math.round(e.usage_kwh)
          + ' kWh at EIA\'s forecast ' + cents(e.price) + ', plus about ' + f.money(e.fixed) + ' a month fixed.'
        : bill + ' is estimated at about ' + f.money(e.amount) + ', at EIA\'s forecast ' + cents(e.price)
          + '. Your bills don\'t yet separate how much power you use from the fixed charge, so no kWh figure is given.');
      lines.push('Your own bills follow the weather - ' + with_ + ' - closely enough to predict them: on months held out, within about '
        + f.money(c.fit_error) + ' on average.');
    } else if (e.method === 'baseline') {
      lines.push(bill + ' is estimated at about ' + f.money(e.amount) + ': ' + f.month(e.from_month) + '\'s bill of '
        + f.money(e.from_amount) + ', at EIA\'s forecast ' + cents(e.price) + ' instead of ' + cents(e.from_price) + '.');
      var why = {
        not_enough_bills: 'There are not yet enough bills for a weather fit (' + (c.bills || 0) + ' so far; about 8 are needed, across a summer and a winter).',
        fit_did_not_beat_baseline: 'A weather fit did not predict your past bills better than this simpler figure, so the simpler one is used.',
        fit_no_better_than_average: 'A weather fit did not predict your past bills meaningfully better than their average, so it is not used.',
        no_weather_slope: 'Your bills do not rise with either the heat or the cold, so a weather fit is not used.',
        no_baseline_to_test: 'There is nothing yet to test a weather fit against, so the simpler figure is used.'
      }[c.reason];
      if (why) lines.push(why);
    } else {
      lines.push(bill + ' cannot be estimated yet: it needs ' + e.needs + '.');
    }
    var sp = d.split;
    if (sp) {
      lines.push(sp.unsplit
        ? 'Against ' + f.month(sp.vs_month) + ' (' + f.money(sp.last_year_bill) + '): ' + _signed(sp.change, f)
          + ' in all; your bills can\'t yet tell how much of that is price and how much is usage.'
        : sp.assumes_same_usage
        ? 'Against ' + f.month(sp.vs_month) + ' (' + f.money(sp.last_year_bill) + '): ' + _signed(sp.price, f)
          + ', all from price - this figure assumes the same usage as last year.'
        : 'Against ' + f.month(sp.vs_month) + ' (' + f.money(sp.last_year_bill) + '): ' + _signed(sp.price, f)
          + ' from price and ' + _signed(sp.usage, f) + ' from usage.');
    }
    var statement = null;
    if (fc.price !== null && fc.price !== undefined && fc.prev_price !== null && fc.prev_price !== undefined
        && Math.abs(fc.price - fc.prev_price) >= 0.01) {
      statement = 'EIA forecasts residential electricity in ' + (reg.national ? 'the U.S.' : reg.division_name) + ' at '
        + fc.price.toFixed(2) + '\u00a2/kWh for ' + f.month(fc.month) + ', ' + (fc.price > fc.prev_price ? 'up' : 'down') + ' from '
        + fc.prev_price.toFixed(2) + '\u00a2 in ' + f.month(fc.prev_month) + '; the electricity estimate on your Budget page uses that forecast.';
      lines.push(statement);
    }
    if (d.saved_amount !== null && d.saved_amount !== undefined) {
      lines.push('Your saved Electric budget of ' + f.money(d.saved_amount) + ' still sets the budget totals; this estimate is shown beside it.');
    }
    return { lines: lines, statement: statement,
             source: 'From the U.S. Energy Information Administration\'s Short-Term Energy Outlook and your own electric bills.' };
  }

  // Gasoline (U2): gallons from the user's own fill-ups, at EIA's weekly price for their area. Facts only: the
  // weekly price is what EIA published, not a forecast.
  function gasoline(d, f) {
    if (!d) return null;
    var lines = [];
    // Item 34 F1: diesel is priced the same way, from EIA's weekly diesel series; the words name the fuel priced.
    var diesel = d.fuel === 'diesel';
    var fw = diesel ? 'diesel' : 'regular-gasoline', kw = diesel ? 'diesel' : 'gasoline';
    var reg = d.region || {}, area = d.area || {};
    var where = area.kind === 'state' ? 'your state' : area.kind === 'padd' ? area.label : 'the U.S.';
    lines.push(reg.national
      ? 'Using U.S. average prices; set your home state in Settings for your region\'s prices.'
      : 'Using EIA\'s weekly ' + fw + ' price for ' + where + (area.kind === 'padd'
          ? ' (EIA publishes no weekly series for ' + reg.state + ').' : ' (' + reg.state + ').'));
    var e = d.estimate || {};
    if (e.method !== 'gallons') {
      return { lines: lines.concat(['A ' + kw + ' estimate needs ' + (e.needs || d.needs) + '.']), statement: null,
               source: 'From the U.S. Energy Information Administration\'s weekly retail prices and your own fill-ups.' };
    }
    lines.push('Your fill-ups come to about ' + e.gallons.toFixed(1) + ' gallons in a typical month (the middle of your last '
      + e.months_used.length + ' months with fill-ups, at each week\'s average price - what you paid at the pump isn\'t in your record).');
    lines.push('At EIA\'s latest weekly price, ' + f.money(e.price) + '/gal (week of ' + f.date(e.week) + '), that is about '
      + f.money(e.amount) + ' a month.');
    var statement = null;
    if (e.year_ago) {
      lines.push('The same gallons a year earlier, at ' + f.money(e.year_ago.price) + '/gal, came to about ' + f.money(e.year_ago.amount)
        + ': ' + (e.year_ago.price_part >= 0 ? '+' : '-') + f.money(Math.abs(e.year_ago.price_part)) + ', all from price.');
      statement = 'EIA\'s latest weekly ' + fw + ' price for ' + where + ' is ' + f.money(e.price) + '/gal (week of '
        + f.date(e.week) + '), ' + (e.price >= e.year_ago.price ? 'up' : 'down') + ' from ' + f.money(e.year_ago.price)
        + ' a year earlier; the ' + kw + ' estimate on your Budget page uses it.';
    }
    if (d.saved_amount !== null && d.saved_amount !== undefined) {
      lines.push('Your saved Gas / Fuel budget of ' + f.money(d.saved_amount) + ' still sets the budget totals; this estimate is shown beside it.');
    }
    return { lines: lines, statement: statement,
             source: 'From the U.S. Energy Information Administration\'s weekly retail prices and your own fill-ups.' };
  }

  // Propane and heating oil (item 34 F2-F4, FUEL_PRICING.md): gallons from the user's own deliveries at EIA's weekly
  // RESIDENTIAL price, and a weather fit only where it passed the F2 guard. EIA collects these prices October to March;
  // out of season the latest is last season's, said as last season's - never this month's, never a zero (F3).
  function delivered(d, f) {
    if (!d) return null;
    var lines = [];
    var oil = d.fuel === 'heating_oil';
    var w = oil ? 'heating oil' : 'propane', cat = oil ? 'Heating Oil' : 'Propane';
    var reg = d.region || {}, area = d.area || {};
    var where = area.kind === 'state' ? 'your state' : area.kind === 'padd' ? area.label : 'the U.S.';
    var src = 'From the U.S. Energy Information Administration\'s weekly residential ' + w + ' prices and heating degree days, '
      + 'and your own deliveries.';
    lines.push(reg.national
      ? 'Using U.S. average prices; set your home state in Settings for your region\'s prices and weather.'
      : 'Using EIA\'s weekly residential ' + w + ' price for ' + where + (area.kind === 'state' ? ' (' + reg.state + ')'
          : ' (EIA publishes no residential ' + w + ' series for ' + reg.state + ')') + ' and its degree days for '
          + reg.division_name + '.');
    var e = d.estimate;
    if (!e) return { lines: lines.concat([d.needs]), statement: null, source: src };
    var c = d.choice || {};
    var lp = e.last_price;
    var pct = function (x) { return Math.round(x * 100) + '%'; };
    var week = function (iso) { return f.date(iso) + ', ' + String(iso).slice(0, 4); };
    if (c.method === 'weather') {
      lines.push('Your deliveries follow the weather: from ' + c.n + ' priced deliveries, about ' + c.base.toFixed(2)
        + ' gallons a day all year plus ' + c.k.toFixed(3) + ' per heating degree day. On deliveries held out, within about '
        + pct(c.held_out_error) + ' (one steady daily rate: ' + pct(c.average_error) + '); the weather is about '
        + pct(c.weather_share) + ' of a year\'s use.');
    } else {
      var why = {
        too_few: 'A delivery can be turned into gallons only when EIA published a residential price that week (October to March). '
          + (c.n || 0) + ' of your deliveries can be compared so far; 3 are needed.',
        no_fit: 'Your priced deliveries all fell in similar weather, so a weather fit cannot be made from them.',
        no_heating_slope: 'Your deliveries do not rise with the cold, so there is not enough evidence to estimate them as heating.',
        no_better_than_average: 'Your deliveries do not follow the weather more closely than one steady daily rate does'
          + (c.held_out_error !== undefined ? ' (held out: ' + pct(c.held_out_error) + ' against ' + pct(c.average_error) + ')' : '')
          + ', so there is not enough evidence to estimate them.',
        weather_share_too_small: 'The weather explains only about ' + pct(c.weather_share || 0) + ' of a year\'s use in your deliveries '
          + '- too little to estimate them as heating (30% is needed).',
        no_degree_days: 'EIA\'s degree days for your region are not complete for the past year, so the deliveries cannot be compared.'
      }[c.reason];
      lines.push(why || ('A ' + w + ' estimate needs ' + (d.needs || 'more deliveries') + '.'));
    }
    if (d.unpriced) {
      lines.push(d.unpriced + (d.unpriced === 1 ? ' delivery' : ' deliveries') + ' had no EIA residential price within two weeks (EIA prices mostly October to March), '
        + 'so ' + (d.unpriced === 1 ? 'it is' : 'they are') + ' not turned into gallons.');
    }
    var statement = null;
    if (e.method === 'weather') {
      lines.push('For ' + f.month(e.month) + ': about ' + e.gallons.toFixed(1) + ' gallons (EIA\'s outlook: ' + Math.round(e.hdd)
        + ' heating degree days) at EIA\'s latest residential price, ' + f.money(e.price) + '/gal (week of ' + week(e.week)
        + '), is about ' + f.money(e.amount) + '.');
      lines.push('This assumes each delivery refilled what was used since the one before; a fixed-amount or partial fill breaks that.');
      statement = 'EIA\'s latest weekly residential ' + w + ' price for ' + where + ' is ' + f.money(e.price) + '/gal (week of '
        + week(e.week) + '); the ' + w + ' estimate on your Budget page uses it.';
    } else if (lp && !e.current) {
      lines.push(lp.season === 'last'
        ? 'EIA publishes residential ' + w + ' prices weekly October to March. Its latest, ' + f.money(lp.price) + '/gal for the week of '
          + week(lp.week) + ', is last season\'s price, so there is no estimate for this month until this season\'s first price.'
        : 'EIA\'s latest residential ' + w + ' price, ' + f.money(lp.price) + '/gal for the week of ' + week(lp.week)
          + ', is more than two weeks old, so there is no estimate for this month until a current one.');
    }
    if (d.saved_amount !== null && d.saved_amount !== undefined) {
      lines.push('Your saved ' + cat + ' budget of ' + f.money(d.saved_amount) + ' still sets the budget totals; this estimate is shown beside it.');
    }
    return { lines: lines, statement: statement, source: src };
  }

  // What the household told Groundwork can settle an estimate before any figure (ONBOARDING_REVISIT.md): then the
  // card says why, and the report has no statement. An estimate read from the record while a fact is unanswered
  // says what it assumed, never silently.
  function _withFacts(fn) {
    return function (d, f) {
      if (d && d.not_applicable) return { lines: [d.not_applicable], statement: null, source: '' };
      var t = fn(d, f);
      if (t && d && d.assumes) t.lines = t.lines.concat([d.assumes]);
      if (t) _totals(t, d, f);
      return t;
    };
  }

  // BUDGET_MONTH_AMOUNT.md M4-M6: what this month's budget really uses, from the server's own figure for this request
  // (d.budget_uses). The report may say the budget includes the estimate only when it does (M6) - proven, not hoped.
  function _totals(t, d, f) {
    var u = d.budget_uses || {};
    var i = -1;
    t.lines.forEach(function (l, k) { if (l.indexOf('still sets the budget totals') >= 0) i = k; });
    if (i >= 0) {
      var saved = t.lines[i].replace(/ still sets the budget totals; this estimate is shown beside it\.$/, '');
      t.lines[i] = (d.optin && u.in_totals)
        ? (u.month_for
            ? "This month's budget uses the estimate for the bill paid this month (for " + f.month(u.month_for) + "'s use), "
              + f.money(u.month_amount) + ', in place of ' + saved.replace(/^Your/, 'your') + '.'
            : "This month's budget uses this estimate, " + f.money(u.month_amount) + ', in place of ' + saved.replace(/^Your/, 'your') + '.')
        : (d.optin && u.why)
          ? "You follow this estimate, but this month's budget uses " + saved.replace(/^Your/, 'your') + ': ' + u.why + '.'
          : saved + ' sets the budget totals. Follow this estimate to use it for this month instead.';
    }
    if (t.statement && d.optin && u.in_totals) {
      // "...; the gas estimate on your Budget page uses that forecast." becomes the proven "includes" (M6).
      var k = t.statement.lastIndexOf('; the ');
      if (k >= 0 && t.statement.indexOf(' estimate on your Budget page ', k) > k) {
        t.statement = t.statement.slice(0, k) + "; this month's budget includes the estimate built on it.";
      }
    }
  }

  var api = { gas: _withFacts(gas), electric: _withFacts(electric), gasoline: _withFacts(gasoline),
              propane: _withFacts(delivered), heating_oil: _withFacts(delivered) };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root && root.GWTeaching) root.GWTeaching.register('utilitytext', api);
})(typeof window !== 'undefined' ? window : null);
