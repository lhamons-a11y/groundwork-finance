// Fills in the parts of the sample household the walkthroughs show that the sample leaves empty: a health plan with
// the insurer's figures, a reserve aimed at the out-of-pocket maximum, and two people. Throwaway dev database only.
export async function seedHealth(page) {
  return page.eval(`(async () => {
    const H = {'Content-Type': 'application/json', 'X-GW-Token': window.GW_SESSION_TOKEN || ''};
    const call = (m, u, b) => fetch(u, {method: m, headers: H, body: b ? JSON.stringify(b) : undefined}).then(r => r.json());
    const out = {};
    const plans = await call('GET', '/api/accounts/health-plans');
    if (!JSON.stringify(plans).includes('Lakeshore')) {
      const p = await call('POST', '/api/accounts/health-plans', {name: 'Lakeshore PPO', effective_from: '2026-01-01',
        effective_to: '2026-12-31', deductible: 1500, oop_max: 4000, tier: 'family'});
      out.plan = p;
      const id = (p.data && (p.data.plan_id || p.data.id)) || (JSON.stringify(p).match(/"plan_id":(\\d+)/) || [])[1]
        || (await call('GET', '/api/accounts/health-plans')).data?.current?.plan_id;
      out.reading = await call('POST', '/api/accounts/health-plans/' + (id || 1) + '/readings',
        {deductible_met: 900, oop_met: 1240, as_of: '2026-11-01'});
    }
    const accts = (await call('GET', '/api/accounts')).data || [];
    const savings = (Array.isArray(accts) ? accts : accts.accounts || []).find(a => /sav/i.test(a.type + ' ' + a.name));
    out.target = await call('POST', '/api/accounts/health-reserve/target', {basis: 'oop_max'});
    if (savings) out.reserved = await call('POST', '/api/accounts/health-reserve/reserved',
      {amount: 1800, account_id: savings.id, reason: 'health reserve'});
    for (const name of ['Dana', 'Sam']) out['person_' + name] = await call('POST', '/api/accounts/people', {name});
    return JSON.stringify(out).slice(0, 1500);
  })()`);
}
