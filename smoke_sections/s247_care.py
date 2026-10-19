"""Item 104 (gw 2.0/CARE.md; Rob 2026-10-19: "a calming voice that tells them it will be ok and that finances are only
temporary but fixable and let them know their are crisis help lines out there and link them to it. We should do
extensive research on this and make sure to add that").

    K1 words of self-harm or despair bring the support message - fixed words, never the AI's - before anything else
       the Ask box does, and in the guide's search too (where it lives with AI off)
    K2 stress, worry or anger about money brings the calmer message: it will be okay, money trouble is temporary and
       fixable, free money help (NFCC, 211), and 988 if it is ever more than money
    K3 everyday money questions bring neither ("kill the subscription", "give up coffee", "hurt my credit score")
    K4 the lines are as each service publishes them, each one a tap away; 911 for danger right now; "a program, not a
       person"; nothing typed is saved, logged, or sent to the AI
    K5 only web links and tel:/sms: with digits leave Groundwork
"""
import re


def _rx(app, name):
    block = app[app.index(f'const {name} = new RegExp(['):]
    block = block[:block.index("].join('|'), 'i');")]
    return re.compile('|'.join(re.findall(r'String\.raw`([^`]*)`', block)), re.I)


def _level(danger, strain, text):
    t = text.lower().replace('’', "'")
    for a, b in ((r'\bcant\b', "can't"), (r'\bwasnt\b', "wasn't"), (r'\bwerent\b', "weren't"), (r'\bim\b', "i'm")):
        t = re.sub(a, b, t)
    t = re.sub(r'\s+', ' ', t)
    return 'danger' if danger.search(t) else 'strain' if strain.search(t) else None


DANGER = ['i want to kill myself', 'thinking about suicide', 'i just want to end it all', 'i want to die',
          "i don't want to be alive anymore", 'my family would be better off without me', "i can't go on like this",
          'my wife gets the life insurance if i die', 'nothing left to live for', 'i wish i wasnt alive',
          'i am worth more dead', 'i keep hurting myself', 'no reason to live', 'kms', 'I’m going to end my life',
          'im ready to die over this debt', 'i want to hurt someone']
STRAIN = ["i'm so stressed about money", 'i feel hopeless', 'drowning in debt', 'i cant do this anymore',
          'this debt is killing me', 'i am so angry at my bank', 'i give up', 'i want to give up on everything', "i'm overwhelmed", 'i hate my life',
          'having a panic attack over bills', 'depressed about my credit card', "there's no way out"]
NEITHER = ['how do I kill a subscription', 'what should I give up to save more', 'i want to give up coffee', 'will this hurt my credit score',
           'how do I end a budget month', 'how do I cut my spending', 'what happens to my debt when I die',
           'show me my life insurance', 'how do I import transactions', 'what is the snowball method',
           'how do I pay off my card faster', 'deadline for taxes', 'how do i add a medical bill', 'view my budget']


def run(ctx):
    check, app = ctx.check, ctx.app_src
    danger, strain = _rx(app, 'CARE_DANGER'), _rx(app, 'CARE_STRAIN')
    miss = [q for q in DANGER if _level(danger, strain, q) != 'danger']
    check(f's247 K1 words of self-harm or despair bring the support message ({miss})', not miss)
    miss = [q for q in STRAIN if _level(danger, strain, q) != 'strain']
    check(f's247 K2 stress, worry or anger about money brings the calmer message ({miss})', not miss)
    wrong = [q for q in NEITHER if _level(danger, strain, q)]
    check(f's247 K3 everyday money questions bring neither ({wrong})', not wrong)

    ask = app[app.index('async function askGroundwork(question) {'):app.index('\nfunction _askWhyChoicesHTML() {')]
    first = ask.index('if (careAsk(q, p, head)) return;')
    check('s247 K1 it is checked first in the Ask box - before commands, the guide, the AI, or the unanswered list',
          first < ask.index('askIntent(q, p, head)') < ask.index('callAI(') and first < ask.index('/api/help/unanswered'))
    faq = app[app.index('function _renderHelpFaq(filter) {'):app.index('function closeHelpOverlay()')]
    check("s247 K1 the guide's search shows it too, before any entry (the guide is there with AI off)",
          'const care = careLevel(f);' in faq and faq.index('careHTML(care)') < faq.index('for (const item of HELP_FAQ)'))

    care = app[app.index('const CARE_DANGER = '):app.index('async function askGroundwork(question) {')]
    check('s247 K2 the calm words: it will be okay, money trouble is temporary and can be fixed, not alone',
          care.count('It will be okay.') == 2 and care.count('Money trouble is temporary, and it can be fixed') == 2
          and "You're not alone in this." in care and "You don't have to carry this alone." in care
          and 'You matter more than any bill.' in care
          and "There's no rush. Whenever you feel up to it" in care and 'plan my debts' not in care)
    check('s247 K4 the lines as their services publish them (checked 2026-10-19)',
          all(x in care for x in ("'tel:988'", "'sms:988'", 'https://988lifeline.org/chat/', 'Text HOME to 741741',
                                  'Dial 988 then press 1, or text 838255', '1-866-488-7386', 'text START to 678-678',
                                  'https://findahelpline.com/', '1-800-388-2227', 'Call or text 211',
                                  'https://988lifeline.org/deaf-hard-of-hearing-hearing-loss/', 'https://988lifeline.org/es/inicio/')))
    check('s247 K4 911 for danger right now; Groundwork says it is a program, and that nothing was kept',
          'If you or someone else is in danger right now, call 911.' in care
          and 'Groundwork is a program, not a person' in care and 'Nothing you typed here was saved or sent anywhere.' in care)
    check('s247 K4 nothing is saved, logged or sent: no API call, no AI, no storage; the typed words are not shown back',
          'API.' not in care and 'callAI' not in care and 'localStorage' not in care and 'fetch(' not in care
          and "box.value = ''" in care and "head.replace(/You asked: [^<]*/, '')" in care)
    check('s247 K4 the guide has an entry anyone can find: who to talk to when money worries feel like too much',
          'Money worries feel like too much. Who can I talk to?' in app)
    launch = (ctx.BASE / 'launch.py').read_text(encoding='utf-8')
    check('s247 K5 only web links and tel:/sms: with digits open outside Groundwork',
          r"re.fullmatch(r'(?:tel|sms):\d{3,11}', url)" in launch
          and r"/^(?:https:\/\/[\w.-]+\/[\w./-]*|tel:\d{3,11}|sms:\d{3,11})$/.test(url)" in care)
