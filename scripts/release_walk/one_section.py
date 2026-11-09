"""Run one smoke section on a throwaway database: python one_section.py s294_release_walk

The context matches smoke_test.py's (check, BASE, TMP, c, H, HJ, dbs, and the three sources), so a section behaves
here as it does in the gate - quicker, for one section while working on it. The gate is still the verdict.
"""
import importlib.util
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

TMP = tempfile.mkdtemp(prefix='gw_one_')
os.environ['GROUNDWORK_DATA_DIR'] = TMP
BASE = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(BASE), str(BASE / 'core')]
os.chdir(BASE)
import server  # noqa: E402
from core.database import db_session  # noqa: E402

app = server.create_app()
c = app.test_client()
H = {'X-GW-Token': server._GW_TOKEN}
HJ = {**H, 'Content-Type': 'application/json'}
results = []


def check(name, ok):
    results.append((bool(ok), name))
    print(('PASS ' if ok else 'FAIL ') + name)


ctx = SimpleNamespace(check=check, BASE=BASE, TMP=Path(TMP), c=c, H=H, HJ=HJ, dbs=db_session,
                      app_src=(BASE / 'static/js/app.js').read_text(encoding='utf-8'),
                      html_src=(BASE / 'static/index.html').read_text(encoding='utf-8'),
                      server_src=(BASE / 'server.py').read_text(encoding='utf-8'))
spec = importlib.util.spec_from_file_location('sec', BASE / 'smoke_sections' / (sys.argv[1] + '.py'))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
mod.run(ctx)
print(f"{sum(ok for ok, _ in results)} passed, {sum(not ok for ok, _ in results)} failed")
