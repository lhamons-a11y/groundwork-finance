"""The macOS / Linux builds fetch the model in halves (Rob 2026-10-08: "lets build the linux installers and macos
installers"). The model is 2.03 GiB, over GitHub's 2 GiB limit for one release file, so the release
model-phi3.5-mini-q4 holds MODEL_FILE.part1 and .part2; fetch_model.py joins them in order and then applies the same
mandatory fingerprint check (item 33 Q5).

    P1  halves join in number order into the whole file, and are removed
    P2  an incomplete run of halves (a gap, a missing first half) is refused, never joined
    P3  no halves: nothing happens (a release holding the whole file still works)
    P4  the download asks for the halves too, and the fingerprint check still follows the join
    P5  the Linux build pins pygobject below 3.51, which still builds on Ubuntu 22.04
    P6  the macOS build compiles the pinned engine from source, CPU only, before the other packages (every published
        macOS arm64 wheel is corrupt), and checks the engine and model are inside the app (Rob 2026-10-08, option (a))
"""
import importlib
import re
import sys
import tempfile
from pathlib import Path


def run(ctx):
    check, BASE = ctx.check, ctx.BASE
    sys.path.insert(0, str(BASE))
    fm = importlib.import_module('fetch_model')

    d = Path(tempfile.mkdtemp(prefix='s157_'))
    name = 'model.gguf'
    data = bytes(range(256)) * 64
    (d / f'{name}.part2').write_bytes(data[9000:])
    (d / f'{name}.part1').write_bytes(data[:9000])
    n = fm.join_parts(d, name)
    check('s157 P1 the halves join in number order into the whole file, and the halves are removed',
          n == 2 and (d / name).read_bytes() == data and sorted(p.name for p in d.iterdir()) == [name])

    for case, files in (('a gap', ('part1', 'part3')), ('no first half', ('part2',))):
        g = Path(tempfile.mkdtemp(prefix='s157_'))
        for f in files:
            (g / f'{name}.{f}').write_bytes(b'x')
        try:
            fm.join_parts(g, name)
            refused = False
        except ValueError:
            refused = True
        check(f's157 P2 an incomplete run of halves is refused ({case}), and nothing is joined',
              refused and not (g / name).exists())

    check('s157 P3 with no halves nothing happens', fm.join_parts(Path(tempfile.mkdtemp(prefix='s157_')), name) == 0)

    src = (BASE / 'fetch_model.py').read_text(encoding='utf-8')
    main = src.split('def main():', 1)[1]
    check('s157 P4 the download asks for the halves as well as the whole file',
          "'--pattern', f'{MODEL_FILE}*'" in main)
    check('s157 P4 the fingerprint check comes after the join, unchanged',
          main.index('join_parts(out, MODEL_FILE)') < main.index('got = sha256(dest)') < main.index('if got != MODEL_SHA256'))
    wf = (BASE / '.github/workflows/linux-build.yml').read_text(encoding='utf-8')
    check('s157 P5 the Linux build pins pygobject below 3.51 (3.51+ needs GLib 2.80, which Ubuntu 22.04 lacks)',
          '"pygobject<3.51"' in wf and 'ubuntu-22.04' in wf and re.search(r'pip install [^\n]*\bpygobject\b(?!<)', wf) is None)

    mac = (BASE / '.github/workflows/macos-build.yml').read_text(encoding='utf-8')
    src_at = mac.find('pip install --no-binary llama-cpp-python')
    check('s157 P6 the macOS build compiles the pinned engine (0.3.35) from source, CPU only, before the other packages',
          src_at > 0 and '"llama-cpp-python==0.3.35"' in mac and 'CMAKE_ARGS: -DGGML_METAL=OFF' in mac
          and src_at < mac.find('pip install -r requirements.txt'))
    check('s157 P6 the macOS build checks the engine is 0.3.35 and that it and the model are inside the app',
          "llama_cpp.__version__ != '0.3.35'" in mac and "find dist/Groundwork.app -name 'libllama*'" in mac
          and "find dist/Groundwork.app -name 'phi3.5-mini-instruct-q4.gguf'" in mac)
