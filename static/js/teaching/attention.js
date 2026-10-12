/*
 * Needs attention: the rules, with no page in them (DASHBOARD_SUMMARY_ATTENTION.md,
 * ruled 2026-09-27, authorised 2026-09-30).
 *
 * Teaching layer: absent from an LTS bundle by path. Pure functions, so the
 * gate can run them in Node (s131) exactly as the page does.
 *
 * Rob's rule, exactly: usage never creates, ranks, or implies an attention
 * item; an attention item requires evidence about the user's finances. So
 * every item here is a dated fact from the record, with its source and a way
 * to resolve it, and there are exactly three kinds (ruling 4). A new kind is a
 * ruled addition, never something code invents - build() refuses any other.
 */
(function (root) {
  'use strict';

  var KINDS = ['payment_due', 'import_stale', 'blocked_conclusion', 'date_ends'];   // date_ends: item 73 Y2, ruled 2026-10-10
  var DUE_WITHIN_DAYS = 7;                                  // ruling 4

  function _iso(d) {
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
  }

  // The next due date on or after today, for a day-of-month (clamped to short months).
  function _nextDue(day, today) {
    function at(y, m) {
      var last = new Date(y, m + 1, 0).getDate();
      return new Date(y, m, Math.min(day, last));
    }
    var t = new Date(today.getFullYear(), today.getMonth(), today.getDate());
    var d = at(t.getFullYear(), t.getMonth());
    if (d < t) d = at(t.getFullYear(), t.getMonth() + 1);
    return d;
  }

  /* Kind 1: a payment due within seven days and not yet paid.
   * `cards` [{id, name, dueDay, minimum}] - the debt record; `isPaid(card, 'YYYY-MM')` - the record's own
   * paid-this-month test (app.js _debtPaidThisMonth). A card with no due day has no date to be due on. */
  function paymentsDue(cards, today, isPaid) {
    var t = new Date(today.getFullYear(), today.getMonth(), today.getDate());
    var out = [];
    (cards || []).forEach(function (c) {
      var day = parseInt(c.dueDay, 10);
      if (!day) return;
      var due = _nextDue(day, t);
      var days = Math.round((due - t) / 86400000);
      if (days < 0 || days > DUE_WITHIN_DAYS) return;
      var month = _iso(due).slice(0, 7);
      if (isPaid(c, month)) return;
      var amount = parseFloat(c.minimum) || 0;
      out.push({ kind: 'payment_due', subject: String(c.id), title: c.name, amount: amount,
                 due: _iso(due), days: days, fact: _iso(due) + '|' + amount.toFixed(2) });
    });
    return out;
  }

  /* Kind 2: an account not imported for three weeks - the server's measured list (stale_imports). */
  function importsStale(stale) {
    return (stale || []).map(function (s) {
      return { kind: 'import_stale', subject: String(s.account_id), title: s.account,
               last_import: s.last_import, days: s.days, fact: s.last_import };
    });
  }

  /* Kind 3: a conclusion blocked by missing data - app.js _computeClaimConfidence's own 'insufficient'
   * claims. Completeness first: with no transactions at all there is no record to be incomplete, and the
   * dashboard's empty state speaks instead. */
  function blockedConclusions(conf, hasRecord) {
    if (!hasRecord || !conf || !conf.claims) return [];
    return Object.keys(conf.claims).map(function (k) { return conf.claims[k]; })
      .filter(function (c) { return c && c.status === 'insufficient'; })
      .map(function (c) {
        // What is missing, named: the checks that failed, each with the record's own words.
        var missing = (c.checks || []).filter(function (k) { return k.state === 'fail'; })
          .map(function (k) { return k.label + ': ' + k.detail; });
        return { kind: 'blocked_conclusion', subject: String(c.claim || c.label), title: c.label,
                 missing: missing, fact: missing.join('; ') };
      });
  }

  /* Kind 4 (item 73 Y2): a trial's end, a return or a cancel-by date the person kept from a receipt, from seven
   * days before. `rows` [{id, merchant, kind, date, price_after, every, done}] - the person's own kept dates. */
  function datesEnding(rows, today) {
    var t = new Date(today.getFullYear(), today.getMonth(), today.getDate());
    var out = [];
    (rows || []).forEach(function (r) {
      if (r.done || !r.date) return;
      var p = String(r.date).split('-').map(Number);
      var d = new Date(p[0], p[1] - 1, p[2]);
      var days = Math.round((d - t) / 86400000);
      if (days < 0 || days > DUE_WITHIN_DAYS) return;
      out.push({ kind: 'date_ends', subject: String(r.id), title: r.merchant, what: r.kind, due: r.date, days: days,
                 price_after: r.price_after, every: r.every, rowId: r.id, fact: r.kind + '|' + r.date });
    });
    return out;
  }

  function fingerprint(item) {
    return item.kind + '|' + item.subject + '|' + item.fact;
  }

  /* The list: the three kinds, less what the user dismissed while its fact stood. Ordered by kind and
   * then by the fact's own urgency (days to due; days since import) - never by anything the user did. */
  function build(parts, dismissed) {
    var gone = {};
    (dismissed || []).forEach(function (f) { gone[f] = true; });
    var items = [].concat(parts.payments || [], parts.imports || [], parts.blocked || [], parts.dates || []);
    items.forEach(function (i) {
      if (KINDS.indexOf(i.kind) < 0) throw new Error('attention: "' + i.kind + '" is not a ruled kind');
    });
    return items.filter(function (i) { return !gone[fingerprint(i)]; }).sort(function (a, b) {
      var k = KINDS.indexOf(a.kind) - KINDS.indexOf(b.kind);
      if (k) return k;
      if (a.kind === 'payment_due' || a.kind === 'date_ends') return a.days - b.days;
      if (a.kind === 'import_stale') return b.days - a.days;
      return 0;
    });
  }

  var api = { KINDS: KINDS, DUE_WITHIN_DAYS: DUE_WITHIN_DAYS, paymentsDue: paymentsDue, datesEnding: datesEnding,
              importsStale: importsStale, blockedConclusions: blockedConclusions,
              fingerprint: fingerprint, build: build };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root && root.GWTeaching) root.GWTeaching.register('attention', api);
})(typeof window !== 'undefined' ? window : null);
