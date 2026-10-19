# Third-party software in Groundwork

Groundwork is licensed under the GNU General Public License, version 3 (see `LICENSE`). It is built on, and its
installers bundle, the open-source software below. Each keeps its own license. The full license texts ship inside
the installed app, with each package's metadata (the `*.dist-info/` folders); the links below are the projects'
own pages.

Versions are the ones current builds use; `requirements.txt` and the build workflows pin what matters.

## The AI engine and model

| Component | License | Project |
|---|---|---|
| llama-cpp-python 0.3.35 (with llama.cpp and ggml) | MIT | https://github.com/abetlen/llama-cpp-python |
| Phi-3.5-mini-instruct (the bundled model, Q4_0) | MIT | https://huggingface.co/microsoft/Phi-3.5-mini-instruct |
| NumPy (bundles OpenBLAS, and on some platforms the GCC runtime libraries under the GCC Runtime Library Exception) | BSD-3-Clause and others; see its LICENSE.txt | https://numpy.org |

## The app

| Component | License | Project |
|---|---|---|
| Python | PSF License | https://www.python.org |
| Flask, Werkzeug, Jinja2, MarkupSafe, click, itsdangerous | BSD-3-Clause | https://palletsprojects.com |
| blinker | MIT | https://github.com/pallets-eco/blinker |
| flask-cors | MIT | https://github.com/corydolphin/flask-cors |
| waitress | ZPL 2.1 | https://github.com/Pylons/waitress |
| SQLAlchemy | MIT | https://www.sqlalchemy.org |
| pywebview (and proxy_tools, bottle) | BSD-3-Clause (MIT) | https://pywebview.flowrl.com |
| requests, urllib3, idna, charset-normalizer | Apache-2.0, MIT, BSD-3-Clause, MIT | https://requests.readthedocs.io |
| certifi | MPL-2.0 | https://github.com/certifi/python-certifi |
| pdfplumber, pdfminer.six | MIT | https://github.com/jsvine/pdfplumber |
| pypdfium2 (and PDFium) | Apache-2.0 / BSD-3-Clause | https://github.com/pypdfium2-team/pypdfium2 |
| Pillow | MIT-CMU | https://python-pillow.org |
| psutil | BSD-3-Clause | https://github.com/giampaolo/psutil |
| keyring, jaraco.*, more-itertools | MIT | https://github.com/jaraco/keyring |
| cryptography, cffi, pycparser | Apache-2.0 or BSD-3-Clause; MIT-0; BSD-3-Clause | https://cryptography.io |
| typing_extensions | PSF-2.0 | https://github.com/python/typing_extensions |
| diskcache | Apache-2.0 | https://github.com/grantjenks/python-diskcache |

## Per platform

| Platform | Component | License |
|---|---|---|
| macOS | PyObjC (core and the Cocoa, Quartz, Security, WebKit, UniformTypeIdentifiers frameworks) | MIT |
| Windows | pythonnet, clr_loader (pywebview's WebView2 support) | MIT |
| Linux | PyGObject | LGPL-2.1-or-later |

## Building

| Component | License | Note |
|---|---|---|
| PyInstaller | GPL-2.0 with a bootloader exception | The exception lets apps it builds use any license. |

## Fonts

The app and the website use Inter, DM Mono, Playfair Display and Fraunces, all under the SIL Open Font License 1.1.
