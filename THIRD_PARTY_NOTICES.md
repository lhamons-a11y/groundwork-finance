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

## Groundwork's voice

Read aloud is said on this computer (core/speak.py); nothing it reads is sent anywhere.

| Component | License | Project |
|---|---|---|
| Kokoro-82M (the bundled voice model, int8, and its voices) | Apache-2.0 | https://huggingface.co/hexgrad/Kokoro-82M |
| kokoro-onnx 0.6.1 | MIT | https://github.com/thewh1teagle/kokoro-onnx |
| The names of United States supermarket chains (core/data/grocery_chains.json), from Wikipedia's "List of supermarket chains in the United States", revision 1375454291 (2026-09-17), by its contributors; names only, with Groundwork's own kinds and respellings | CC BY-SA 4.0, https://creativecommons.org/licenses/by-sa/4.0/ | https://en.wikipedia.org/wiki/List_of_supermarket_chains_in_the_United_States |
| WeSpeaker ResNet34-LM trained on VoxCeleb (the bundled voiceprint model for "Only voices it knows"), by the WeNet community, used unchanged | CC BY 4.0, https://creativecommons.org/licenses/by/4.0/ | https://huggingface.co/Wespeaker/wespeaker-voxceleb-resnet34-LM |
| ONNX Runtime | MIT | https://onnxruntime.ai |
| phonemizer | GPL-3.0-or-later | https://github.com/bootphon/phonemizer |
| eSpeak NG (through espeakng-loader) | GPL-3.0-or-later | https://github.com/espeak-ng/espeak-ng |

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
| Valhalla, through pyvalhalla (and the libraries its package bundles in pyvalhalla.libs, each under its own licence) | MIT | https://github.com/valhalla/valhalla |
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

The app bundles Inter, DM Mono and Playfair Display (Latin and Latin Extended) in `static/fonts/`, each under the
SIL Open Font License 1.1, with its license text beside it (`OFL-inter.txt`, `OFL-dmmono.txt`,
`OFL-playfairdisplay.txt`). The website (not the app) loads Inter, DM Mono and Fraunces from Google Fonts.

## Map data

Place lookups and the optional road map use data from **OpenStreetMap**, made available under the Open Database License (ODbL): https://www.openstreetmap.org/copyright. The road map is a database derived from it and is shared under the same licence, with the method that made it, at https://groundworkfinance.app/static/download/road-map/README.txt.
