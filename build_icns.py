"""
Generate a macOS .iconset from the source PNG, for the GitHub Actions
macOS build workflow (.github/workflows/macos-build.yml) to feed into
iconutil. Source PNG is 256x256; sizes above that are upscaled with
Pillow's LANCZOS resampling.

Not run locally — sips was tried first and repeatedly produced files
iconutil rejected ("Failed to generate ICNS"), including exact-size,
non-upscaled 256x256 files, with a suspicious "Output file suffix should
be jpg" warning on every sips call for a PNG input. Pillow doesn't have
that issue.
"""
from pathlib import Path
from PIL import Image

SRC = Path('assets/groundwork_256.png')
OUT_DIR = Path('groundwork.iconset')

SIZES = {
    'icon_16x16.png': 16, 'icon_16x16@2x.png': 32,
    'icon_32x32.png': 32, 'icon_32x32@2x.png': 64,
    'icon_128x128.png': 128, 'icon_128x128@2x.png': 256,
    'icon_256x256.png': 256, 'icon_256x256@2x.png': 512,
    'icon_512x512.png': 512, 'icon_512x512@2x.png': 1024,
}


def main():
    OUT_DIR.mkdir(exist_ok=True)
    src = Image.open(SRC).convert('RGBA')
    for name, size in SIZES.items():
        src.resize((size, size), Image.LANCZOS).save(OUT_DIR / name)
    print(f'Wrote {len(SIZES)} icon sizes to {OUT_DIR}/')


if __name__ == '__main__':
    main()
