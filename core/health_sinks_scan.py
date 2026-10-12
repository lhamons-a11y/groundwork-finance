"""P9's scanner (HEALTH_PRIVACY_H6.md): every place the app's Python writes, sends, logs or hands data out, by file,
function and kind. The gate compares what it finds with core/health_boundary.HEALTH_SINKS, so a new sink cannot slip
past the enforcement point unregistered, and a registered one that is gone is noticed too."""
import ast
from pathlib import Path

APP_FILES = ('server.py', 'launch.py', 'migrate.py', 'bank_window.py', 'bank_agent_window.py', 'flights_window.py',
             'hotels_window.py', 'bank_importer.py', 'price_engine.py', 'gas_price.py', 'utility_price.py',
             'trip_distance.py', 'recycle_bin.py', 'pdf_statement.py')
LOG_ATTRS = {'debug', 'info', 'warning', 'error', 'exception', 'critical'}
NET_NAMES = {'urlopen', 'create_window'}
NET_ATTRS = {('requests', 'get'), ('requests', 'post'), ('webview', 'create_window'), ('http.client', 'HTTPSConnection')}


def _kind(call):
    f = call.func
    name = f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else ''
    base = f.value.id if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) else ''
    if name == 'print':
        return 'log'
    if isinstance(f, ast.Attribute) and name in LOG_ATTRS and base in ('logging', 'logger', 'log', '_log', 'LOG') or \
            (isinstance(f, ast.Attribute) and name in LOG_ATTRS and isinstance(f.value, ast.Call)
             and getattr(f.value.func, 'attr', '') == 'getLogger'):
        return 'log'
    if name in ('write_text', 'write_bytes', 'copy', 'copy2', 'copyfile', 'backup') or \
            (name == 'open' and any(isinstance(a, ast.Constant) and isinstance(a.value, str) and a.value[:1] in 'wa'
                                    for a in call.args[1:2])):
        return 'file'
    if name in ('send_file', 'send_from_directory'):
        return 'download'
    if name in NET_NAMES or (base, name) in NET_ATTRS:
        return 'network'
    if name == '_ai_log_write':
        return 'ai_log'
    return None


def scan(base):
    """{(file, function, kind)}; logs are recorded per file ('*'), as the registry keeps them."""
    base = Path(base)
    files = [base / f for f in APP_FILES if (base / f).exists()] + sorted((base / 'core').glob('*.py'))
    found = set()
    for p in files:
        rel = p.relative_to(base).as_posix()
        if rel in ('core/health_boundary.py', 'core/health_sinks_scan.py'):
            continue
        tree = ast.parse(p.read_text(encoding='utf-8'))
        stack = []

        def visit(node):
            pushed = isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            if pushed:
                stack.append(node.name)
            if isinstance(node, ast.Call):
                k = _kind(node)
                if k:
                    found.add((rel, '*' if k == 'log' else (stack[0] if stack else '<module>'), k))
            for ch in ast.iter_child_nodes(node):
                visit(ch)
            if pushed:
                stack.pop()
        visit(tree)
    return found
