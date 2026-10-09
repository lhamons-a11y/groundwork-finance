"""Room to finish: each AI surface's length cap (gw 2.0/NARRATION_CAPS.md, item 12 step 2; Rob 2026-10-09: K1-K8
"as written").

    K1  caps sized from what finished answers used          K2  each prompt names its length in words
    K3  an answer cut at its cap keeps its finished, checked sentences, marked "Shortened at the length limit."
        (fewer than two: reworded as before); a streamed one keeps what was shown
    K4  the trip classifier works ten transactions a call    K5  the unreachable old monthly report is gone
    K6  every gated AI call declares its cap
"""
import json
import re
import shutil
import subprocess


def _calls(app):
    """Every callAI({...}) call's argument text."""
    out, i = [], 0
    while True:
        i = app.find('callAI({', i)
        if i < 0:
            return out
        j, depth = i + len('callAI('), 0
        for k in range(j, len(app)):
            ch = app[k]
            depth += ch == '{'
            depth -= ch == '}'
            if depth == 0:
                out.append(app[j:k + 1])
                break
        i = j


def run(ctx):
    check, app = ctx.check, ctx.app_src

    calls = _calls(app)
    gated = [c for c in calls if 'skipGate: true' not in c]
    undeclared = [c[:80] for c in gated if 'max_tokens' not in c]
    check(f's171 K6 every gated AI call declares its cap ({len(gated)} gated calls)', gated and undeclared == [])

    def cap_of(marker):
        c = next((c for c in calls if marker in c), '')
        m = re.search(r'max_tokens:\s*(\d+)', c)
        return int(m.group(1)) if m else None
    caps = {'monthly report': cap_of("surface: 'monthly_report_v2'"), 'report narratives': cap_of('surface: reportId,'),
            'follow-up': cap_of('_followup`'), 'Sunday check-in': cap_of("surface: 'sunday_checkin'"),
            'projection': cap_of("surface:'projection'")}
    check(f's171 K1 the caps are the ruled ones {caps}',
          caps == {'monthly report': 1000, 'report narratives': 700, 'follow-up': 400, 'Sunday check-in': 200, 'projection': 280})
    check('s171 K2 each prompt names its length in words',
          'Two sentences, about 40 words. Conversational' in app and "Two sentences, about 40 words. Exact numbers" in app
          and 'about 200 words in all' in app and '1-2 short paragraphs, about 100 words' in app
          and 'Write 3-4 paragraphs, about 300 words' in app)

    check('s171 K4 the trip classifier asks ten transactions a call, capped at 600, and says what it could not read',
          'for (let i = 0; i < txns.length; i += 10)' in app and 'max_tokens: 600' in app
          and "couldn't be read by the model" in app and 'Math.min(4000' not in app)
    check('s171 K5 the old monthly report is gone, and its buttons open the live report',
          'async function generateReport' not in app and "surface: 'monthly_report'," not in app
          and 'onclick="generateReport()"' not in app and 'onclick="generateReport()"' not in ctx.html_src)

    node = shutil.which('node')
    check('s171 node is available', bool(node))
    if not node:
        return
    a = app.index('let _GW_VOICE = null;')
    b = app.index('// ─── Phase 8C')
    harness = r'''
let REPLY = null, STREAM = [];
const API = { _n: 0, post: async (url, body) => { if (url === '/api/ai/chat') { API._n++; return { data: REPLY(API._n) }; } return {}; }, get: async () => ({}) };
const _gwErr = () => () => {};
const _GW_AUTH_HEADER = () => ({});
const esc = s => String(s);
globalThis.fetch = async (url) => {
  if (url === 'voice_rules.json') return new Response('', { status: 404 });
  const enc = new TextEncoder();
  const body = new ReadableStream({ start(c) { for (const e of STREAM) c.enqueue(enc.encode('data: ' + JSON.stringify(e) + '\n\n')); c.close(); } });
  return new Response(body, { headers: { 'content-type': 'text/event-stream' } });
};
''' + app[a:b] + r'''
const FIND = 'Income: $4,280.00. Spent: $3,100.00. Surplus: $1,180.00.';
const ask = (extra) => callAI({ surface: 's171', findings_kinds: ['income', 'total'], max_tokens: 50,
  messages: [{ role: 'user', content: FIND }], ...extra });
const cut = (t) => ({ content: [{ type: 'text', text: t }], stop_reason: 'max_tokens', provider: 'local' });
(async () => {
  const out = {};
  REPLY = () => cut('Income was $4,280.00 this month. Spending was $3,100.00. The surplus was $1,180.00 and it');
  API._n = 0; out.kept = await ask({}); out.kept.calls = API._n;
  REPLY = (n) => n === 1 ? cut('Income was $4,280.00 this month. Spending was') : { content: [{ type: 'text', text: 'Income was $4,280.00.' }], stop_reason: 'end_turn' };
  API._n = 0; out.short = await ask({}); out.short.calls = API._n;
  STREAM = [{ t: 'Income was $4,280.00 this month. ' }, { t: 'Spending was $3,100.00. ' }, { t: 'The surplus' }, { done: true, stop_reason: 'max_tokens' }];
  const shown = [], resets = [];
  out.stream = await ask({ onSentence: s => shown.push(s), onReset: w => resets.push(w) });
  out.stream.shown = shown; out.stream.resets = resets;
  console.log(JSON.stringify(out));
})();
'''
    p = subprocess.run([node, '-e', harness], capture_output=True, text=True, encoding='utf-8', timeout=120)
    try:
        out = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:                                          # noqa: BLE001
        out = {}
        print('        node said:', (p.stderr or p.stdout)[-600:])
    k, s, st = out.get('kept', {}), out.get('short', {}), out.get('stream', {})
    check('s171 K3 an answer cut at its cap keeps its finished sentences, drops the unfinished one, and says so - no rewrite',
          k.get('ok') and k.get('shortened') and k.get('calls') == 1
          and k.get('text') == 'Income was $4,280.00 this month. Spending was $3,100.00.\n\nShortened at the length limit.')
    check('s171 K3 fewer than two finished sentences: reworded as before (R10 still refuses the cut answer)',
          s.get('ok') and not s.get('shortened') and s.get('calls') == 2 and s.get('text') == 'Income was $4,280.00.')
    check('s171 K3 a streamed answer cut at its cap keeps what was shown - nothing the person read is withdrawn',
          st.get('ok') and st.get('shortened') and st.get('resets') == []
          and st.get('shown') == ['Income was $4,280.00 this month.', 'Spending was $3,100.00.', 'Shortened at the length limit.'])
