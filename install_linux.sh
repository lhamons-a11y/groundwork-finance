#!/bin/bash
# ============================================================
#  Groundwork - Linux Install Script
#  Run after extracting the Linux download. Installs to /opt/groundwork (replacing any earlier version there) and
#  creates a desktop shortcut. Your records stay in ~/.local/share/Groundwork.
# ============================================================

set -e

INSTALL_DIR="/opt/groundwork"
APP_NAME="Groundwork"

echo ""
echo " Installing Groundwork..."
echo ""

# Check for root/sudo for /opt install
if [ "$EUID" -ne 0 ]; then
    echo " This script installs to /opt/groundwork and needs sudo."
    exec sudo "$0" "$@"
fi

# Install system dependencies
echo " [1/3] Installing system dependencies..."
if command -v apt-get &>/dev/null; then
    apt-get install -y python3-gi gir1.2-webkit2-4.0 gir1.2-webkit2-4.1 2>/dev/null || \
    apt-get install -y python3-gi gir1.2-webkit2-4.0 2>/dev/null || true
elif command -v dnf &>/dev/null; then
    dnf install -y python3-gobject webkit2gtk4.1 2>/dev/null || true
elif command -v pacman &>/dev/null; then
    pacman -S --needed python-gobject webkit2gtk 2>/dev/null || true
fi
echo "       Done."

# Copy app to /opt, replacing any earlier version (Rob 2026-10-31: "the files should overwrite the previous"). Only
# the program folder is replaced: your records live in ~/.local/share/Groundwork, which this script never touches.
echo " [2/3] Installing to ${INSTALL_DIR}..."
if [ -d "$INSTALL_DIR" ]; then
    pkill -f "$INSTALL_DIR/Groundwork" 2>/dev/null || true      # an open Groundwork is closed first
    echo "       Replacing the earlier version in ${INSTALL_DIR} (your records are not touched)."
    rm -rf "${INSTALL_DIR:?}"
fi
mkdir -p "$INSTALL_DIR"
cp -r ./* "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/Groundwork"
echo "       Done."

# Create desktop entry
echo " [3/3] Creating desktop shortcut..."
cat > /usr/share/applications/groundwork.desktop << DESKTOP
[Desktop Entry]
Name=Groundwork
GenericName=Personal Finance
Comment=Personal finance for people who weren't taught.
Exec=${INSTALL_DIR}/Groundwork
Icon=${INSTALL_DIR}/groundwork.png
Type=Application
Categories=Finance;Office;
Terminal=false
StartupNotify=true
DESKTOP

# Make it launchable from terminal too
ln -sf "$INSTALL_DIR/Groundwork" /usr/local/bin/groundwork 2>/dev/null || true

echo "       Done."
echo ""
echo " ============================================================"
echo "  Groundwork installed successfully!"
echo "  Launch from your Applications menu or run: groundwork"
echo " ============================================================"
echo ""
