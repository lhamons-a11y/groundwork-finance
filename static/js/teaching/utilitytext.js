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

  var api = { gas: gas };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root && root.GWTeaching) root.GWTeaching.register('utilitytext', api);
})(typeof window !== 'undefined' ? window : null);
