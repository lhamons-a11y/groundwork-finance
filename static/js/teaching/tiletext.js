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
    // Once-a-month bills (rent, loan payments) are counted once, not stretched across the month at the daily rate.
    var bills = o.bills > 0 ? Math.min(o.bills, o.spent) : 0;
    var projected = o.daysGone > 0 ? bills + ((o.spent - bills) / o.daysGone) * o.daysInMonth : 0;
    var rate = bills > 0
      ? ', ' + f.money(bills) + ' of it once-a-month bills. Counting those once and the rest at that rate'
      : '. At that rate';
    return {
      head: o.monthName + ' so far',
      body: 'Spent ' + f.money(o.spent) + ' in ' + o.daysGone + ' of ' + o.daysInMonth + ' days' + rate + ' - a straight'
            + ' line, not a forecast - the month ends near ' + f.money(projected) + ' against ' + f.money(o.budget)
            + ' of budgeted income.'
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

  /* Item 28's remaining entries. Each says what the record holds and what it doesn't - never a verdict. */
  function _gate(d, title) {
    if (!d) return null;
    if (!d.backed) return { lines: [d.needs], source: '' };
    return false;
  }

  function funds(d, f) {
    var g = _gate(d); if (g !== false) return g;
    var lines = (d.funds || []).map(function (x) {
      var p = x.pace || {};
      if (p.funded) return x.name + ': funded.';
      if (!p.finish_months) return x.name + ': ' + f.money(p.remaining) + ' still to go; nothing going in and nothing planned, so no finish date.';
      var how = p.pace_source === 'observed' ? 'put in' : 'planned';
      var brk = p.since_break ? (p.insufficient_since_break
        ? ' (what goes in changed in ' + f.month(p.since_break.month) + '; too few months since to set a pace, so this is the plan\'s)'
        : ' (counting only since ' + f.month(p.since_break.month) + ', when what goes in changed)') : '';
      return x.name + ': ' + f.money(p.remaining) + ' still to go; at the ' + f.money(p.pace_monthly) + '/mo ' + how
        + ' it finishes in ' + p.finish_months + ' month' + (p.finish_months === 1 ? '' : 's')
        + (p.deadline_months !== null && p.deadline_months !== undefined ? ', with ' + p.deadline_months + ' months to its deadline' : '')
        + brk + '.';
    });
    return { lines: lines, source: 'From your savings funds and what has gone into them; the same pace the Budget page shows.' };
  }

  function recurring(d, f) {
    var g = _gate(d); if (g !== false) return g;
    var items = d.items || [];
    var total = items.reduce(function (s, i) { return s + (i.monthly || 0); }, 0);
    var lines = [items.length + ' recurring charge' + (items.length === 1 ? '' : 's') + ', about ' + f.money(total) + ' a month together:'];
    items.slice(0, 6).forEach(function (i) {
      lines.push(i.name + ': ' + f.money(i.monthly) + '/mo' + (i.category ? ' (' + i.category + ')' : ''));
    });
    return { lines: lines, source: 'From charges that repeat for at least three months in your ledger, at what each costs per month.' };
  }

  function category(d, f) {
    var g = _gate(d); if (g !== false) return g;
    var seen = d.months.filter(function (m) { return m.amount !== null && m.amount !== undefined; });
    var avg = seen.length ? seen.reduce(function (s, m) { return s + m.amount; }, 0) / seen.length : 0;
    return {
      lines: [d.category + ', by month: ' + d.months.map(function (m) {
                return f.month(m.month) + ' ' + (m.amount === null || m.amount === undefined ? 'none recorded' : f.money(m.amount));
              }).join('; ') + '.',
              'Average over the ' + seen.length + ' months it appears: ' + f.money(avg) + '.'],
      source: 'From your ledger, months that are complete; a month without ' + d.category + ' says so rather than counting it as zero.'
    };
  }

  function energy(d, f) {
    var g = _gate(d); if (g !== false) return g;
    var p = d.prices || {};
    var lines = [];
    if (p.elec) lines.push('Electricity (' + p.elec.area + '): ' + p.elec.price + '\u00a2/kWh' + (p.elec.period ? ', ' + p.elec.period : '') + '.');
    if (p.ng) lines.push('Natural gas (' + p.ng.area + '): ' + f.money(p.ng.price) + '/MCF' + (p.ng.period ? ', ' + p.ng.period : '') + '.');
    else lines.push('Natural gas: no EIA price on record yet.');
    if (p.gasoline) lines.push('Gasoline (U.S. average): ' + f.money(p.gasoline.price) + '/gal' + (p.gasoline.period ? ', week of ' + p.gasoline.period : '') + '.');
    return { lines: lines, source: 'From the U.S. Energy Information Administration, as last fetched; not refreshed here.' };
  }

  function picture(d, f) {
    var g = _gate(d); if (g !== false) return g;
    var read = { flexible: 'reads as flexible, from your record', sacred: 'reads as something you keep, from your record' };
    var lines = (d.claims || []).slice(0, 4).map(function (c) {
      if (c.reason === 'break') return c.category + ': set aside after its spending changed level.';
      if (c.reason === 'probation') return c.category + ': moved beside your income, so not classified.';
      return c.category + ': ' + (read[c.stance] || c.stance) + '.';
    });
    (d.said || []).slice(0, 4).forEach(function (s) {
      lines.push('You marked ' + s.category + ' ' + (s.stance === 'protect' ? 'protected' : 'flexible') + ' on ' + f.date(s.said_at) + '.');
    });
    return { lines: lines, source: 'From the working picture: what your record shows, and what you have told Groundwork.' };
  }

  function banned(text) {
    var t = String(text || '').toLowerCase();
    return BANNED.filter(function (w) { return t.indexOf(w) >= 0; });
  }

  var api = { BANNED: BANNED, month: month, dti: dti, plan: plan, greetingFact: greetingFact, investments: investments,
              netWorth: netWorth, funds: funds, recurring: recurring, category: category, energy: energy,
              picture: picture, banned: banned };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root && root.GWTeaching) root.GWTeaching.register('tiletext', api);
})(typeof window !== 'undefined' ? window : null);
