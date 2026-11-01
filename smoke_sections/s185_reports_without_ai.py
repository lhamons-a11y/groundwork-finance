"""Item 64: reports that stand on their own without AI; AI adds the teaching (gw 2.0/REPORTS_WITHOUT_AI.md N1-N7,
RULED 2026-10-10 - Rob: "I accept item 62 and 64", then "build all items that have been ruled on").

    N1/N5  every report shows its summary - each computed figure as a plain line - with AI on or off; with AI off
           that is the report beneath its charts, never an "unavailable" panel
    N2     the AI-off words are facts: no verdict, no advice (the monthly "solid / tight month" and "trim" are gone)
    N3     with AI on, the same summary, and the written part teaches rather than retells
    N4     Settings says plainly that turning AI off loses no figures; a slow answer is named, never acted on
    N6     a verdict word put back in the AI-off words fails here
"""
import json
import os
import re
import shutil
import subprocess
import tempfile

VERDICT = r'\b(solid|tight|great|good|bad|healthy|unhealthy|worth reviewing|trim|should|must|need to|saves? money|top debt priority|get you back)\b'


def run(ctx):
    check, BASE = ctx.check, ctx.BASE
    app = ctx.app_src

    an = app.split('async function _rcAnalyzeWithAI(')[1].split('\n}')[0]
    check('s185 N1 the summary is drawn before AI is even asked - so with AI off the report still has it',
          an.index('_rcRenderSummary(reportId, dataLines, target);') < an.index('if (!aiEnabled()) return;'))
    fb = app.split('function _rcRenderAIFallback(')[1].split('\n}')[0]
    check('s185 N1 no "unavailable" panel over raw data: a written part that did not come says so in one quiet line',
          'Written analysis unavailable' not in app and '_rcRenderSummary(reportId, dataLines, target);' in fb
          and 'the figures above are complete' in fb)
    check('s185 N3 the written part is told the person already sees the figures, and to teach rather than list them',
          'do not list them again. Teach instead' in app)
    check('s185 N4 Settings says turning AI off loses no figures; a slow answer is named with a link, never switched off for the person',
          'With AI off, every report still shows its full summary' in ctx.html_src and 'globalThis._gwAiSlowSecs' in app
          and 'Every report works fully without it' in app and 'toggleAI(' not in app.split('function _rcRenderSummary(')[1].split('\n}')[0])

    fn = app.split('function _rcMonthlyFallbackText(')[1].split('\n}')[0]
    summ = re.search(r'\nfunction _rcSummaryLines\(.*?\n\}\n', app, re.S)
    node = shutil.which('node')
    out = {}
    if node:
        js = ('const fmt = n => "$" + Number(n).toFixed(2); const esc = s => String(s); const escJs = esc;\n'
              'function _rcMonthlyFallbackText(' + fn + '\n}\n' + (summ.group(0) if summ else '') +
              'console.log(JSON.stringify({kept: _rcMonthlyFallbackText("September", 3412.18, 4280, 867.82, "Housing: $1,500.00, Dining: $412.00"),'
              ' over: _rcMonthlyFallbackText("August", 4500, 4280, -220, "Housing: $1,500.00"),'
              ' empty: _rcMonthlyFallbackText("July", 0, 4280, 4280, ""),'
              ' lines: _rcSummaryLines(["Income: $4,280.00", "Spent: $3,412.18 (budget $3,600.00)", "", "A line with no label"])}));')
        fd, path = tempfile.mkstemp(suffix='.js')
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(js)
        try:
            p = subprocess.run([node, path], capture_output=True, text=True, encoding='utf-8', timeout=60)
            out = json.loads(p.stdout.strip() or '{}')
        except Exception:                      # noqa: BLE001
            out = {}
        finally:
            os.remove(path)
    words = ' '.join(out.get(k, '') for k in ('kept', 'over', 'empty'))
    check('s185 N2 the AI-off monthly words, run in Node, are facts: kept or over, by how much, where it went',
          'In September you kept $867.82 of $4280.00 income' in out.get('kept', '')
          and '$220.00 more than the $4280.00 income' in out.get('over', '') and 'no transactions on record' in out.get('empty', ''))
    check(f's185 N2 no verdict or advice words in them (found: {re.findall(VERDICT, words, re.I)})', bool(words) and not re.search(VERDICT, words, re.I))
    check('s185 N6 mutation caught: "a solid month" put back would fail the check above', bool(re.search(VERDICT, 'September was a solid month', re.I)))
    check('s185 N1 the summary lays each figure out as a label and its value; an empty line is dropped',
          out.get('lines') == [{'label': 'Income', 'value': '$4,280.00'}, {'label': 'Spent', 'value': '$3,412.18 (budget $3,600.00)'},
                               {'label': '', 'value': 'A line with no label'}])
