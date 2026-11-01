#!/bin/bash
# Groundwork — build the Mac app, every step in one place (Mac check 2026-10-31, issues 5 and 14).
#
#   ./build_macos.sh                 build dist/Groundwork.app, signed ad hoc (runs on this Mac only)
#   GW_SIGN_IDENTITY="Developer ID Application: …" ./build_macos.sh
#                                    sign with that certificate and the hardened runtime
#   GW_NOTARY_PROFILE=groundwork …   also notarize and staple (xcrun notarytool store-credentials made the profile)
#
# The models: GW_MODEL_PATH / GW_WHISPER_PATH when set, else vendor/ (spec_engine.py), else the copies inside an
# installed /Applications/Groundwork.app - the same pinned files, checked by spec_engine against their SHA-256.
set -euo pipefail
cd "$(dirname "$0")"

PY="${GW_PYTHON:-$HOME/gw-engine-venv/bin/python}"
APP=dist/Groundwork.app
INSTALLED=/Applications/Groundwork.app/Contents/Resources/models

"$PY" -c 'import PyInstaller' 2>/dev/null || "$PY" -m pip install --quiet pyinstaller
"$PY" -c 'import certifi' 2>/dev/null || "$PY" -m pip install --quiet certifi

if [ -z "${GW_MODEL_PATH:-}" ] && [ ! -d vendor/phi3.5_model ] && [ -f "$INSTALLED/phi3.5-mini-instruct-q4.gguf" ]; then
    export GW_MODEL_PATH="$INSTALLED/phi3.5-mini-instruct-q4.gguf"
fi
if [ -z "${GW_WHISPER_PATH:-}" ] && [ ! -d vendor/whisper ] && [ -f "$INSTALLED/ggml-base.en.bin" ]; then
    export GW_WHISPER_PATH="$INSTALLED/ggml-base.en.bin"
fi

# The icon: committed as assets/groundwork.icns; remade from the PNG only when it is missing.
if [ ! -f assets/groundwork.icns ]; then
    "$PY" build_icns.py && iconutil -c icns groundwork.iconset -o assets/groundwork.icns
    rm -rf groundwork.iconset
fi

"$PY" -m PyInstaller groundwork_macos.spec --clean --noconfirm

# Finder metadata and resource forks make codesign refuse the bundle, and when this folder is under iCloud's file
# syncing (Documents is), it puts Finder info back on the bundle's folders as fast as xattr -cr takes it off. So the
# bundle is signed in a copy outside it, made without any extended attributes, and brought back signed.
STAGE=$(mktemp -d /tmp/gw-sign.XXXXXX)
ditto --norsrc --noextattr --noacl "$APP" "$STAGE/Groundwork.app"
xattr -cr "$STAGE/Groundwork.app"
if [ -n "${GW_SIGN_IDENTITY:-}" ]; then
    codesign --force --deep --timestamp --options runtime \
             --entitlements entitlements_macos.plist -s "$GW_SIGN_IDENTITY" "$STAGE/Groundwork.app"
else
    echo "build_macos.sh: no GW_SIGN_IDENTITY - signing ad hoc. This build runs on this Mac only, and macOS asks"
    echo "                again for its permissions (Downloads, microphone) after every rebuild."
    codesign --force --deep -s - "$STAGE/Groundwork.app"
fi
codesign --verify --deep --strict "$STAGE/Groundwork.app"
rm -rf "$APP"
ditto "$STAGE/Groundwork.app" "$APP"
rm -rf "$STAGE"
codesign --verify --deep "$APP"

if [ -n "${GW_SIGN_IDENTITY:-}" ] && [ -n "${GW_NOTARY_PROFILE:-}" ]; then
    zip=dist/Groundwork-notarize.zip
    ditto -c -k --keepParent "$APP" "$zip"
    xcrun notarytool submit "$zip" --keychain-profile "$GW_NOTARY_PROFILE" --wait
    xcrun stapler staple "$APP"
    rm -f "$zip"
    spctl --assess --type execute -v "$APP"
fi

echo "build_macos.sh: built $APP ($(/usr/libexec/PlistBuddy -c 'Print :CFBundleVersion' "$APP/Contents/Info.plist"))"
