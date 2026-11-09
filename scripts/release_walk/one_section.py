"""Run one smoke section on a throwaway database: python one_section.py s294_release_walk"""
import importlib.util
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

os.environ['GROUNDWORK_DATA_DIR'] = tempfile.mkdtemp(prefix='gw_one_')
BASE = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(BASE), str(BASE / 'core')]
os.chdir(BASE)
import server  # noqa: E402

app = server.create_app()
c = app.test_client()
H = {'X-GW-Token': server._GW_TOKEN, 'Content-Type': 'application/json'}
results = []


def check(name, ok):
    results.append((bool(ok), name))
    print(('PASS ' if ok else 'FAIL ') + name)


ctx = SimpleNamespace(check=check, c=c, H=H, BASE=BASE,
                      app_src=(BASE / 'static/js/app.js').read_text(encoding='utf-8'),
                      html_src=(BASE / 'static/index.html').read_text(encoding='utf-8'),
                      server_src=(BASE / 'server.py').read_text(encoding='utf-8'))
spec = importlib.util.spec_from_file_location('sec', BASE / 'smoke_sections' / (sys.argv[1] + '.py'))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
mod.run(ctx)
print(f"{sum(ok for ok, _ in results)} passed, {sum(not ok for ok, _ in results)} failed")
