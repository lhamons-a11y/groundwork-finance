"""Item 102 (gw 2.0/ASK_ASSISTANT.md; Rob 2026-10-19: "the ask how to is not useful at all ... It needs a overhaul or
removed. Lets try real assistant and if the user selects no AI it goes away", and "Also in that item add update help
file").

    A1 the Ask box is AI help: shown only while AI is on and able to run (ai-feature); the ? guide is always there
    A2 the assistant answers in its own words from the closest guide entries and nothing else, naming the one it used
    A3 an answer that names no entry, refuses, or carries a number not in its entry is not shown: the closest guide
       answers are, in the guide's own words
    A4 a "why does this figure..." question still goes to Groundwork's fixed checks (item 72 C2)
    A5 the help is current: the guide covers today's pages (Health, bills, collections, the Budget tabs, Before You
       Buy's flow, the new-vendor question, deleting a transaction), and so does the website's knowledge base
"""
import json
import re


def run(ctx):
    check, app, html = ctx.check, ctx.app_src, ctx.html_src
    ask = app[app.index('async function askGroundwork(question) {'):app.index('\nfunction _askWhyChoicesHTML() {')]
    check('s246 A1 the Ask box is AI help, shown only with AI on and able to run, named for what it does (Rob 2026-10-20: '
          '"lets change the phrase ask how to ... to something else since the text window can do more")',
          'id="gwAskBox" class="ai-feature"' in html and 'placeholder="Ask or tell Groundwork…"' in html and "document.querySelectorAll('.ai-feature')" in app
          and 'if (!aiEnabled()) {' in ask)
    sysmsg = app[app.index('const ASK_SYSTEM = '):app.index('const ASK_GUIDE_SIZE')]
    check('s246 A2 the model is told to answer only from the numbered guide entries, name the one it used, and say when none fits',
          'using ONLY the numbered guide entries' in sysmsg and 'Do not give financial advice' in sysmsg
          and 'End with the number of the entry' in sysmsg and 'NOT IN GUIDE' in sysmsg
          and 'helpRank(q).filter(x => x.score > 0).slice(0, ASK_GUIDE_SIZE)' in ask)
    check('s246 A3 no entry named, a refusal, or a number not in the entry: the closest guide answers are shown instead',
          "if (used && answer && _askNumbersOk(checked, used)) {" in ask and "The guide doesn't answer that exactly" in ask
          and 'function _askNumbersOk(' in app and "skipGate: true, surface: 'ask_howto'" in ask
          and "Written by the AI on this computer, only from Groundwork's guide." in ask
          and 'From the guide: ${esc(used.q)}' in ask)
    check('s246 A4 a "why" question still goes to the fixed checks, which the AI only names',
          ask.index("_helpWords(q).some(w => HELP_WHY_WORDS.has(w))") < ask.index('callAI(')
          and "the answer comes from your records, not from the AI" in ask)

    s = app.index('const HELP_FAQ = [')
    block = app[s:app.index('\n];\n', s) + 4]
    guide = [json.loads(l.strip().rstrip(',')) for l in block.split('\n') if l.strip().startswith('{')]
    qs = {g['q']: g for g in guide if 'q' in g}
    need = ('Where are my medical bills, health plan and reserve?', 'How do I add a medical bill?',
            'A medical bill went to collections. How do I track it?', 'Where is the Calendar?',
            'Why does the Ledger ask about a new vendor?', 'How do I delete a transaction?')
    check('s246 A5 the guide covers what changed: Health, bills, collections, the Calendar, the new-vendor question, deleting',
          all(q in qs for q in need) and 'Gifts tab on the Budget page' in qs['How does Gift Budget work?']['a']
          and 'What are you thinking of buying?' in qs['How does the Before You Buy tool work?']['a']
          and 'Ask box at the top is AI help' in qs['How do I turn the AI features on or off?']['a']
          and 'legal advice' in qs['A medical bill went to collections. How do I track it?']['a'])
    site = (ctx.BASE / 'Website' / 'website.py').read_text(encoding='utf-8')
    kb = site.split("@app.route('/knowledge-base')", 1)[1].split('@app.route', 1)[0]
    check('s246 A5 the website\'s knowledge base matches: Health, the Budget tabs, the new Before You Buy, Ask',
          '<div class="kb-article" id="health">' in kb and '<a href="#health">Health</a>' in kb
          and '<strong>Calendar</strong>' in kb and 'What are you thinking of buying?' in kb
          and '<strong>Ask or tell Groundwork…</strong>' in kb and 'Gifts</strong> tab on the Budget page' in kb)

    # "view X" means the page, now (Rob 2026-10-19); a question is answered - run in Node when it is available
    import shutil, subprocess, tempfile, os
    nav = app[app.index('const ASK_PLACES = ['):app.index('function askGo(')]
    check('s246 A6 "view", "see", "show me", "open", "go to", "take me to" a page or tab goes straight there; "show me how" is a question',
          'if (askIntent(q, p, head)) return;' in ask and 'picture' not in nav
          and ask.index('askIntent(q, p, head)') < ask.index('callAI(') and 'show me how to... is a question' in nav.replace('"', '')
          or ("show me how to..." in nav and 'askGo(place)' in ask))
    node = shutil.which('node')
    if node:
        js = nav + "\nconst cases = " + json.dumps([
            ['view the calendar', 'budget'], ['show me collections', 'health'], ['open settings', 'settings'],
            ['take me to my budget', 'budget'], ['go to debt payoff', 'debt'], ['show me how to import transactions', None],
            ['how do I view my calendar', None], ['view my medical bills', 'health'], ['can you show me my investments', 'investments'],
            ['open the month tracker', 'debt'], ['view my backups', 'settings'], ['see my budget', 'budget'],
            ['see collections', 'health'], ['see how to add a bill', None]]) + \
            ";\nconsole.log(JSON.stringify(cases.map(([q, v]) => { const p = askPlace(q); return [q, p ? p.view : null, v]; })));"
        d = tempfile.mkdtemp(prefix='s246_')
        f = os.path.join(d, 'nav.js')
        open(f, 'w', encoding='utf-8').write(js)
        out = json.loads(subprocess.run([node, f], capture_output=True, text=True, timeout=30).stdout or '[]')
        wrong = [q for q, got, want in out if got != want]
        check(f's246 A6 the phrases land where they mean, and questions are not navigated ({wrong})', out and not wrong)

    # Rob 2026-10-19: "get my accounts, fetch my accounts, download my accounts all should start the get my accounts"
    fetch = app[app.index('const ASK_FETCH = '):app.index('function askPlace(')]
    rx = re.search(r"const ASK_FETCH = /(.+)/i;", fetch).group(1).replace('\\\\', '\\')
    pyrx = re.compile(rx.replace('(?!', '(?!'), re.I)
    yes = ['get my accounts', 'fetch my accounts', 'download my accounts', 'please get all my accounts', 'refresh my bank accounts']
    no = ['how do I get my accounts from my bank', 'where are my accounts settings', 'get my accounts page']
    check('s246 A7 "get / fetch / download my accounts" presses Get my accounts; a question about it is answered',
          all(pyrx.search(q) for q in yes) and not any(pyrx.search(q) for q in no)
          and "if (btn && btn.style.display !== 'none') { startFetchAll(); return true; }" in fetch
          and "showView('automation');" in fetch)

    # Rob 2026-10-19: "add those four and anything else that you can think of" - what people actually type
    layer = app[app.index('const _ASK_SHORT = '):app.index('async function askGroundwork(question) {')]
    check('s246 A8 shorthand and lead-ins are tidied first ("acct", "txn", "cc"; "I need to", "can you", "please")',
          "acct: 'account'" in layer and "txn: 'transaction'" in layer and "cc: 'credit card'" in layer
          and 'i need to' in layer and 'can you' in layer)
    do = layer[layer.index('const ASK_DO = ['):layer.index('const ASK_RECORD = [')]
    check('s246 A8 commands open exactly what their own buttons open - import, add a transaction, back up, add a bill, '
          'add a card, report a problem, the AI switch (never flipped), the monthly report - and save nothing',
          all(f in do for f in ('showImportModal', 'openAddModal', 'openBackupModal', 'Bring in a bill', 'addCard()',
                                'openFeedbackModal', "_askReveal('settingsAiToggle')", "_rcOpenReport('monthly')"))
          and "Groundwork doesn't change it for you" in do and 'API.' not in do and 'toggleAI' not in do)
    rec = layer[layer.index('const ASK_RECORD = ['):layer.index('function _askSpend(')]
    check('s246 A8 a question about your own figures opens where Groundwork works them out - the assistant states no figure',
          all(w in rec for w in ('owe', 'debt.?free', 'net worth', '(?:budget|track)', '(?:due|coming)', 'hsa', 'income', 'balance'))
          and '${' not in rec and 'fmt(' not in rec and 'money(' not in rec and 'never as a guess' in layer)
    check('s246 A8 "how much did I spend on X": the category report set to X, or the Ledger searched for it; '
          '"find X" and "X transactions" search the Ledger',
          "sel.value = spend.cat; _rcUpdateCategoryDeepDive();" in layer and 'askLedgerSearch(spend.term)' in layer
          and 'askLedgerSearch(term)' in layer and "\"my transactions\" is the Ledger" in layer)
    check('s246 A8 a greeting, "help", "what\'s new" and "undo" get their own reply; undo is never done for you',
          "You're welcome." in layer and 'The whole guide' in layer and 'groundworkfinance.app/changelog' in layer
          and 'Groundwork never undoes anything by itself' in layer)
    check('s246 A8 just a page\'s name opens it', "const named = ASK_PLACES.find(pl => pl.names.includes(bare));" in layer)
