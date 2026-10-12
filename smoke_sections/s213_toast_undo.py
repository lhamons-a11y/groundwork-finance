"""Undo on toasts keeps its function (found 2026-10-12 on master, fixed on both lines; Rob: "push the undo fix to master
and 1.x").

showToast copied the Undo function into the button as text, so it lost every variable it closed over. The Ledger's
delete Undo looked up `id`, which inside an inline handler is the button's own empty id - so Undo did nothing and the
transaction was deleted five seconds later. Run here in Node, with the page stubbed: the Undo a toast was given is the
Undo that runs, with its variables.
"""
import json
import re
import shutil
import subprocess


def run(ctx):
    check = ctx.check
    app = ctx.app_src
    toast = re.search(r'^function showToast\(.*?^\}', app, re.M | re.S)
    runner = re.search(r'^var _toastUndo = .*?^function _runToastUndo\(k, btn\) \{.*?^\}', app, re.M | re.S)
    check('s213 showToast never copies the Undo function into the button as text',
          toast is not None and runner is not None and 'toString()' not in toast.group(0))
    node = shutil.which('node')
    if toast and runner and node:
        prog = (
            "const made = []; const g = () => ({ appendChild: el => made.push(el) });\n"
            "const document = { createElement: () => ({ style: {}, remove() {} }) };\n"
            "const setTimeout = () => 0;\n"
            + runner.group(0) + '\n' + toast.group(0) + '\n'
            + "let got = null;\n"
            "(function () { const id = 4242; showToast('Transaction deleted', '', 'info', () => { got = id; }); })();\n"
            "const k = +made[0].innerHTML.match(/_runToastUndo\\((\\d+), this\\)/)[1];\n"
            "_runToastUndo(k, null); const again = got; got = null; _runToastUndo(k, null);\n"
            "console.log(JSON.stringify([again, got]));\n")
        r = subprocess.run([node, '-e', prog], capture_output=True, text=True, encoding='utf-8', timeout=30)
        out = json.loads(r.stdout.strip() or 'null') if r.returncode == 0 else r.stderr[-200:]
        check(f's213 the Undo a toast was given runs with its own variables (the deleted row\'s id), once ({out})',
              out == [4242, None])
