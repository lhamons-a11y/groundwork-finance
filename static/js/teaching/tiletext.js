/*
 * The summary tiles' words, with no page in them (gw 2.0/SUMMARY_TILES_STANDARD.md, item 27, ruled
 * 2026-09-30: all six points).
 *
 * Teaching layer: absent from an LTS bundle by path. Pure, so the gate runs it in Node (s132).
 *
 * The standard is Needs attention's: a fact from the record with its source, completeness first, the
 * question taught - never a verdict, never advice. Every sentence here is the arithmetic the tile
 * already did, said as arithmetic.
 */
(function (root) {
  'use strict';

  // Words a tile may never say (St10). The lexicon test reads this list and the page's rendered text.
  var BANNED = ['on track', 'watch it', 'over budget', 'under budget', 'keep going', 'stay sharp', 'tip:',
                'lender-ready', 'behind schedule', 'ahead of schedule', 'needs attention.', 'unbreakable',
                'getting close', 'no emergency buffer'];

  function _names(list) {
    if (list.length <= 1) return list[0] || '';
    return list.slice(0, -1).join(', ') + ' and ' + list[list.length - 1];
  }

  /* T1 + T2: This month. `behind` lists the imported accounts with nothing imported since the month began
   * (the server's measured list). With any, no pace is stated - only the gap. */
  function month(o, f) {
    if (o.behind && o.behind.length) {
      return {
        head: o.monthName + ' so far',
        body: 'Nothing imported since ' + o.monthName + ' began for ' + _names(o.behind.map(function (b) {
          return b.account + ' (last import ' + f.date(b.last_import) + ')';
        })) + ', so this month\'s spending isn\'t known yet.'
      };
    }
    if (!(o.budget > 0)) {
      return { head: o.monthName + ' so far',
               body: 'Spent ' + f.money(o.spent) + ' in ' + o.daysGone + ' of ' + o.daysInMonth + ' days. There is no budgeted'
                     + ' income yet to compare it with.' };
    }
    var projected = o.daysGone > 0 ? (o.spent / o.daysGone) * o.daysInMonth : 0;
    return {
      head: o.monthName + ' so far',
      body: 'Spent ' + f.money(o.spent) + ' in ' + o.daysGone + ' of ' + o.daysInMonth + ' days. At that rate - a straight'
            + ' line, not a forecast - the month ends near ' + f.money(projected) + ' against ' + f.money(o.budget) + ' budgeted.'
    };
  }

  /* T4: the ratio, and the question it answers. */
  function dti(pct) {
    if (pct === null || pct === undefined || isNaN(pct)) return '';
    return 'Debt payments are ' + Math.round(pct) + '% of income - the debt-to-income ratio lenders look at, where 36%'
           + ' is a common cut-off.';
  }

  /* T5: two dates, not a schedule verdict. `mv` is app.js _gwDateMovement(): the payoff date the first recorded
   * balances pointed to, and the one today's point to. */
  function plan(mv, f) {
    if (!mv || !mv.computable || !mv.dateThen || !mv.dateNow) return '';
    if (Math.abs(mv.monthsDelta || 0) < 1) {
      return 'Your first recorded balances and today\'s both point to debt-free around ' + f.monthYear(mv.dateNow) + '.';
    }
    return 'Your first recorded balances pointed to debt-free around ' + f.monthYear(mv.dateThen) + '; today\'s point to '
           + f.monthYear(mv.dateNow) + '.';
  }

  /* T3: the greeting carries one upcoming fact from the record - the first Needs attention item - or nothing. */
  function greetingFact(item, f) {
    if (!item) return '';
    if (item.kind === 'payment_due') {
      return item.title + ': ' + (item.amount ? f.money(item.amount) + ' ' : '') + 'due ' + f.date(item.due)
             + ', not yet recorded as paid.';
    }
    if (item.kind === 'import_stale') return item.title + ' was last imported ' + item.days + ' days ago.';
    if (item.kind === 'blocked_conclusion') return item.title + ' can\'t be assessed yet: ' + item.missing.join('; ') + '.';
    return '';
  }

  /* Item 29 (INVESTMENTS_TILE.md): the Investments tile, from what is on record. Every figure names what it
   * leaves out - a holding with no price, shares with no purchase price - rather than counting it as zero. */
  function _cls(c) { return String(c).replace(/_/g, ' '); }
  function investments(d, f) {
    if (!d || !d.present) return null;
    var lines = [];
    if (d.prices_from) {
      var when = d.prices_from === d.prices_to ? 'as of ' + f.date(d.prices_from)
               : 'from ' + f.date(d.prices_from) + ' to ' + f.date(d.prices_to);
      lines.push('Value: ' + f.money(d.value) + ', at prices ' + when + '.'
                 + (d.manual_prices.length ? ' Hand-entered price: ' + _names(d.manual_prices) + '.' : ''));
    }
    if (d.unrealized) {
      var g = d.unrealized.gain;
      lines.push('Unrealized ' + (g < 0 ? 'loss' : 'gain') + ': ' + f.money(Math.abs(g))
                 + (d.unrealized.pct !== null ? ' (' + Math.abs(d.unrealized.pct).toFixed(1) + '%)' : '')
                 + ' on holdings with a recorded purchase price.');
    }
    if (d.unpriced.length) {
      lines.push('Not included: ' + _names(d.unpriced.map(function (u) { return u.ticker; })) + ' - no price on record.');
    }
    d.no_basis.forEach(function (n) {
      lines.push('Gain not stated for ' + n.shares + ' ' + n.ticker + ' shares: no purchase price recorded.');
    });
    var r = d.realized_this_year;
    if (r && r.lots > 0) {
      var parts = [];
      if (r.short) parts.push('short-term ' + f.money(r.short));
      if (r.long) parts.push('long-term ' + f.money(r.long));
      lines.push('Realized in ' + d.year + ': ' + f.money(r.total) + (parts.length ? ' (' + parts.join(', ') + ')' : '')
                 + (r.unstated ? '; ' + r.unstated + ' sale' + (r.unstated === 1 ? '' : 's') + ' with no gain recorded' : '') + '.');
    }
    if (d.allocation && d.allocation.length) {
      var un = d.allocation_unclassified || [];
      lines.push('Against your target: ' + d.allocation.map(function (a) {
        return _cls(a.asset_class) + ' ' + a.actual_pct + '% (target ' + a.target_pct + '%)';
      }).join('; ') + (un.length ? '; not yet assigned a class: ' + un.map(function (u) {
        return u.ticker + ' ' + u.pct + '%';
      }).join(', ') : '') + '.');
    }
    d.balance_only.forEach(function (b) {
      lines.push('Also on record: ' + b.account + ', ' + f.money(b.balance) + ' balance - holdings not recorded, so not in the figures above.');
    });
    return { lines: lines,
             source: 'From your investment lots, closed sales and the prices on record; prices are not refreshed here.' };
  }

  /* Item 28's first catalogue entry: net worth over time, from the user's own snapshots. */
  function netWorth(d, f) {
    if (!d) return null;
    if (!d.backed) return { lines: [d.needs], source: 'From your net worth snapshots.' };
    var pts = d.points, first = pts[0], last = pts[pts.length - 1];
    var change = last.net_worth - first.net_worth;
    return {
      lines: ['Net worth: ' + f.money(last.net_worth) + ' on ' + f.date(last.date) + '.',
              'First saved: ' + f.money(first.net_worth) + ' on ' + f.date(first.date) + ' - a change of '
              + (change < 0 ? '-' : '+') + f.money(Math.abs(change)) + ' across ' + pts.length + ' snapshots.'],
      source: 'From your net worth snapshots, as you saved them; Groundwork does not fill the gaps between them.'
    };
  }

  function banned(text) {
    var t = String(text || '').toLowerCase();
    return BANNED.filter(function (w) { return t.indexOf(w) >= 0; });
  }

  var api = { BANNED: BANNED, month: month, dti: dti, plan: plan, greetingFact: greetingFact, investments: investments,
              netWorth: netWorth, banned: banned };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root && root.GWTeaching) root.GWTeaching.register('tiletext', api);
})(typeof window !== 'undefined' ? window : null);
