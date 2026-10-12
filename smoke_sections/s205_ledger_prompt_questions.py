"""The Ledger's after-a-category-change prompt: its two questions are answered on their own (Rob 2026-10-11: "if I
have two questions that is being asked of me in ledger when I answer 1 question both questions go away ... They should
be treated as individual. I believe this is a UI bug.").

The prompt asks "always categorize this merchant this way?" and "this looks like a monthly bill - add it to recurring?".
Every button used to remove the whole prompt. Now each answer closes only its own question, the prompt goes when both
are answered, and the auto-close restarts after an answer. "Never ask for this merchant" still closes both - it is
about the merchant, not one question.
"""
import re


def run(ctx):
    check = ctx.check
    app = ctx.app_src
    show = app.split('function _showRecurringPrompt(')[1].split('\nasync function _acceptRecurringRule(')[0]
    check('each question sits in its own section of the prompt', 'id="rrpRule"' in show and 'id="rrpBill"' in show)
    whole = re.findall(r"onclick=\"document\.getElementById\('recurringRulePrompt'\)\?\.remove\(\)\"", show)
    check(f'no "No thanks" removes the whole prompt any more ({len(whole)} found)', not whole
          and show.count("onclick=\"_rrpClose('rule')\"") == 1 and show.count("onclick=\"_rrpClose('bill')\"") == 1)
    acc = app.split('async function _acceptRecurringRule(')[1].split('\n}')[0]
    bill = app.split('async function _promptAcceptBill(')[1].split('\n}')[0]
    check('accepting one question closes only that question', "_rrpClose('rule')" in acc and "_rrpClose('bill')" in bill
          and "getElementById('recurringRulePrompt')?.remove()" not in acc + bill)
    close = app.split('function _rrpClose(')[1].split('\n}')[0]
    check('the prompt goes only when both questions are answered, and the auto-close restarts after an answer',
          "if (!document.getElementById('rrpRule') && !document.getElementById('rrpBill')) { el.remove(); return; }" in close
          and '_rrpTimer(el);' in close and 'clearTimeout(el._rrpT);' in app)
    sup = app.split('function _suppressRecurringRule(')[1].split('\n}')[0]
    check('"Never ask for this merchant" still closes the whole prompt - it is about the merchant',
          "getElementById('recurringRulePrompt')?.remove()" in sup)
