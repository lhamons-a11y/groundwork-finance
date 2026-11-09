"""The 2.0 release walk (2026-11-08): what walking every first-launch path and every page found, each fixed and held.

    W1  no saved debt plan means the minimums everywhere (panel I-01): the Debt page AND the payoff engine behind
        Before You Buy, trips and the assistant; a saved plan is used as saved, $0 included - never the 1500 default
    W2  Before You Buy says where a monthly cost is paid from: the debt plan, or what's left each month, or neither.
        "unable to cover your minimum payments" only when what's left goes below zero
    W3  first launch: the import window names the first account when there are none; the snapshot follows the import
        (decided after the rows are loaded); the income step starts from the income the snapshot just reported; the
        plan screen never calls skipped debts "debt-free"; the snapshot's confidence follows categorization
    W4  restore from a backup file sends the session token (it was refused as "Unauthorized" and read as protected)
    W5  the "What if you paid extra?" slider keeps the amount chosen when the engine's answer re-renders the page
    W6  a dev server's vault entries are its own (GROUNDWORK_VAULT_SERVICE), never the installed app's
    W7  saving Settings with the debt budget empty does not save a $0 plan
    W8  the Net Worth page fills its brokerage field with brokerage only: it held the combined total (brokerage + 401k
        + IRA), so each visit added the retirement balances again and saved it (the math audit; present since 1.0)
    W10 records upgraded from 1.x are asked once to check the brokerage figure W8 inflated (Rob 2026-11-08: "Yes put
        the note in"): only with a 401(k) or IRA and a brokerage figure, until the person says they have checked it
    W9  a falling minimum is a credit card's: a loan's payment is never held to the card formula ("↓ min $171.27" on
        a $389 car loan), and a statement minimum below Groundwork's estimate is saved, not refused
"""
import os
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]


def run(ctx):
    check, app = ctx.check, ctx.app_src
    import server
    from core.database import AppSetting, DebtAccount, db_session

    byb_js = (BASE / 'static' / 'js' / 'teaching' / 'byb.js').read_text(encoding='utf-8')

    # ── W1: the engine's budget with and without a saved plan ─────────────────────────────────────────────────────
    with db_session() as s:
        others = [d.id for d in s.query(DebtAccount).filter_by(is_active=True).all()]
        s.query(DebtAccount).filter(DebtAccount.id.in_(others)).update({'is_active': False}, synchronize_session=False)
        row = s.query(AppSetting).filter_by(key='monthly_budget').first()
        saved_before = row.value if row else None
        if row:
            s.delete(row)
        a = DebtAccount(name='S294 Card', current_balance=3200.0, begin_balance=3200.0, interest_rate=22.9,
                        minimum_payment=95.0, is_active=True)
        b = DebtAccount(name='S294 Loan', current_balance=8000.0, begin_balance=9000.0, interest_rate=6.0,
                        minimum_payment=210.0, is_active=True)
        s.add_all([a, b])
        s.commit()
        made = [a.id, b.id]

    def set_mb(v):
        with db_session() as s:
            r = s.query(AppSetting).filter_by(key='monthly_budget').first()
            if v is None:
                if r:
                    s.delete(r)
            elif r:
                r.value = str(v)
            else:
                s.add(AppSetting(key='monthly_budget', value=str(v)))
            s.commit()

    def engine_budget():
        with db_session() as s:
            return server._consequence_inputs(s)[1]

    try:
        none_saved = engine_budget()
        set_mb(600)
        saved = engine_budget()
        set_mb(0)
        zero = engine_budget()
        check(f"s294 W1 the payoff engine's budget: the minimums with no saved plan, the plan as saved, $0 kept as $0 - "
              f"never 1500 ({none_saved}, {saved}, {zero})",
              abs(none_saved - 305.0) < 0.01 and abs(saved - 600.0) < 0.01 and zero == 0.0)
        check("s294 W1 the bootstrap's debt budget is the saved figure or 0, never the 1500 default, and the page "
              "fills its field only from a saved plan",
              "'monthlyBudget':  _float_or(settings.get('monthly_budget'), 0.0)" in ctx.server_src
              and server._float_or('', 0.0) == 0.0 and server._float_or('0', 9.0) == 0.0 and server._float_or('x', 1.0) == 1.0
              and "const mb = S.monthlyBudgetSaved ? (parseFloat(prefs.monthlyBudget) || 0) : '';" in app
              and 'if (!S.monthlyBudgetSaved) return _debtMonthPlan().minimums;' in app
              and 'prefs.monthlyBudget || 1500' not in app)
    finally:
        with db_session() as s:
            s.query(DebtAccount).filter(DebtAccount.id.in_(made)).delete(synchronize_session=False)
            s.query(DebtAccount).filter(DebtAccount.id.in_(others)).update({'is_active': True}, synchronize_session=False)
            s.commit()
        set_mb(saved_before)

    # ── W2: Before You Buy names where the money comes from ───────────────────────────────────────────────────────
    check("s294 W2 Before You Buy: three cases - the plan carries it, only what's left does, or neither - and the "
          "minimums warning only when what's left is below zero",
          "function _bybFunding(whatsLeft, payoff)" in app
          and "return whatsLeft >= 0 ? 'left' : 'short';" in app
          and "funding === 'short' ? `<div style=\"color:var(--ember-text);font-weight:500\">This payment would leave you short every month" in app
          and 'This payment would leave you unable to cover your current minimum debt payments' not in app
          and "funding === 'left' ? 'Not in your debt plan'" in app)
    check("s294 W2 the what's-left alternative is offered for a small cost the plan carries as for a large one it "
          "can't, so a bigger purchase never reads better than a smaller one",
          "(funding === 'left' || (funding === 'plan' && !_byb.origInsufficient && moDiff > 0)) ? _bybFromLeftHTML(" in app)
    check("s294 W2 the engine note says the wall is the plan's when what's left covers the cost",
          "if (funding === 'left') {" in byb_js and '_bybFunding(c.whatsLeft' in byb_js)

    # ── W3: first launch ───────────────────────────────────────────────────────────────────────────────────────────
    check("s294 W3 the import window names the first account when there are none (the welcome's fastest start was a "
          "dead end), and Settings no longer promises accounts are made automatically",
          'async function importCreateFirstAccount()' in app and 'id="importFirstAccount"' in ctx.html_src
          and 'accounts are created automatically the first time' not in app)
    check("s294 W3 the welcome's next step after an import is decided once its rows are loaded, so the snapshot shows",
          'closeImportModal({ deferOnboarding: true });' in app
          and app.index('closeImportModal({ deferOnboarding: true });') < app.index('_obAfterImport();                          // the welcome')
          and app.index('const refreshed = await _refreshTransactionsFromServer();') < app.index('_obAfterImport();                          // the welcome'))
    check("s294 W3 the income step starts from the income the snapshot reported, and never replaces a typed figure",
          '_obPrefillIncomeFromImport();' in app and "if (!box || box.value) return;" in app)
    check("s294 W3 the plan screen says only what the record holds: no debts entered is not debt-free",
          "'No debts entered yet." in app and "const entered = (S.debtCards || []).some(c => !c.paidInFull);" in app)
    check("s294 W3 the snapshot's confidence follows categorization, the dashboard's own gate",
          "if (debits.length && catRate < 60)" in app and "monthsSpan >= 3 && catRate >= 90" in app)

    # ── W4 - W7 ────────────────────────────────────────────────────────────────────────────────────────────────────
    check("s294 W4 restore from a backup file sends the session token; only a locked backup asks for its password",
          "fetch('/api/backup/restore-upload', { method:'POST', body: formData, headers: _GW_AUTH_HEADER() })" in app
          and "r.status === 403 && res.error !== 'Unauthorized'" in app)
    adv = app[app.index('function loadDebtAdvisor('):app.index('// Strategy comparison')]
    check("s294 W5 the what-if slider keeps the extra chosen when the advisor re-renders",
          'slider.value = 0' not in adv and 'slider.value = _debtWhatIfExtra;' in adv and 'runWhatIf(_debtWhatIfExtra);' in adv)
    env = dict(os.environ, GROUNDWORK_VAULT_SERVICE='Groundwork dev')
    out = subprocess.run([sys.executable, '-c', 'import bank_agent_window as b; from core import bank_vault as v; '
                          'print(b.VAULT_SERVICE, "|", v.SERVICE)'], cwd=str(BASE), env=env, capture_output=True, text=True)
    from core import bank_vault
    dev_src = (BASE / 'dev_server.py').read_text(encoding='utf-8')
    check(f"s294 W6 a dev server's vault entries are its own: both modules read GROUNDWORK_VAULT_SERVICE, the dev "
          f"server sets it, and unset it is 'Groundwork' ({out.stdout.strip()})",
          out.stdout.strip() == 'Groundwork dev | Groundwork dev'
          and (os.environ.get('GROUNDWORK_VAULT_SERVICE') or bank_vault.SERVICE == 'Groundwork')
          and "os.environ.setdefault('GROUNDWORK_VAULT_SERVICE', 'Groundwork dev')" in dev_src)
    rnw = app[app.index('function renderNetWorth('):app.index('function renderNetWorth(') + 1200]
    check("s294 W8 Net Worth's brokerage field gets brokerage only, never the combined total it is saved as",
          "g('nwInvestments').value  = nw.investments||''" not in rnw
          and "Math.max(0, (nw.investments||0) - (nw.retirement401k||0) - (nw.retirementIRA||0))" in rnw
          and 'const totalInvestments = investments + totalRetirement;' in app
          and 'investments: totalInvestments' in app)
    decay = app[app.index('function _budgetMinDecay('):app.index('function _budgetMinDecay(') + 900]
    save_bloom = app[app.index('function _budgetSaveDebtBloom('):app.index('function _budgetSaveDebtBloom(') + 6000]
    snap = app[app.index('async function _budgetSaveDebtSnapshot('):app.index('async function _budgetSaveDebtSnapshot(') + 900]
    freed = app.split('function _freedMinimums() {')[1].split('\n}\n')[0]
    check("s294 W9 a loan is never held to the card minimum formula: no falling-minimum badge, history keeps its "
          "payment, freed minimums read its payment, the report shows no card estimate beside it",
          "if ((card.debtType || 'credit') !== 'credit') return null;" in decay
          and "(card.debtType || 'credit') === 'credit' ? _calcMinPayment(bal, apr) : pmt;" in snap
          and "parseFloat(earliest.payment)" in freed
          and app.count("(card.debtType || 'credit') === 'credit' && bal > 0 && apr > 0 ? _calcMinPayment(bal, apr)") >= 2)
    check("s294 W9 a statement minimum below Groundwork's estimate is saved with a note, never refused",
          "Payment cannot be below the calculated minimum." not in app
          and "showToast(`Saved ${fmt(pmt)} as the minimum`" in save_bloom
          and "return;\n  }\n\n  // Local state" not in save_bloom)
    note = app[app.index('async function _nwCheckNote('):app.index('async function _nwCheckNoteDone(')]
    bm = ctx.server_src[ctx.server_src.index('def _backup_before_migration('):ctx.server_src.index('def _backup_after_migration(')]
    check("s294 W10 an upgrade from 1.x leaves a note to check the brokerage figure; the page shows it only with a "
          "401(k) or IRA and a brokerage figure, until 'I've checked it'; a 2.0 database never gets it",
          "if stored and stored[:8] < '20261018':" in bm and "'nw_check_note'" in bm and "'checked': False" in bm
          and "!_nwCheck || _nwCheck.checked || !(retirement > 0) || !(brokerage > 0)" in note
          and "I've checked it" in note and 'checked: true' in app
          and '_nwCheckNote().catch(' in app and 'id="nwCheckNote"' in ctx.html_src)
    check("s294 W7 saving Settings with the debt budget empty does not save a $0 plan",
          "if (budgetRaw !== '') { patch.monthly_budget = String(budget); S.monthlyBudgetSaved = true; }" in app
          and 'monthly_budget:  String(budget),' not in app)
