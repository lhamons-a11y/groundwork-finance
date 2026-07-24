# Installing Groundwork

## Windows

1. Install Python 3.11 or 3.12 from [python.org](https://www.python.org/downloads/)
   - During install: check **"Add Python to PATH"**
2. Open Command Prompt and run:
   ```
   pip install -r requirements.txt
   python launch.py
   ```

---

## macOS

### First-time setup

1. Install Python 3.11 or 3.12 from [python.org](https://www.python.org/downloads/)
2. Open Terminal and run:
   ```
   pip3 install -r requirements.txt
   python3 launch.py
   ```

### Gatekeeper warning (macOS security)

The first time you open Groundwork, macOS may show:
> *"Groundwork cannot be opened because the developer cannot be verified."*

This happens because Groundwork is not yet signed with an Apple Developer certificate.
**Your data is safe** — this is a standard macOS warning for any unsigned app.

**To open it anyway:**
1. In Finder, locate the Groundwork folder
2. Right-click `launch.py` → **Open With → Python Launcher**
3. Click **Open** in the dialog that appears
4. You only need to do this once — macOS remembers your choice

Or run from Terminal (Terminal is always allowed):
```
python3 /path/to/groundwork/launch.py
```

---

## Linux

### Install system dependencies first

**Ubuntu 22.04 / Debian 11:**
```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-webkit2-4.0 python3-tk python3-pip
```

**Ubuntu 23.04+ / Debian 12+:**
```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-webkit2-4.1 python3-tk python3-pip
```

**Fedora:**
```bash
sudo dnf install python3-gobject webkit2gtk4.0 python3-tkinter python3-pip
```

**Arch Linux:**
```bash
sudo pacman -S python-gobject webkit2gtk python-tk python-pip
```

### Then install Python packages and run:
```bash
pip3 install -r requirements.txt
python3 launch.py
```

### If you see "No module named 'gi'" or WebKit errors:
The system WebKit library is missing. Run the apt/dnf/pacman command above for your distro and try again.

### Wayland note
Groundwork runs under XWayland automatically on Wayland desktops (GNOME, KDE Plasma).
If the window appears blurry, set:
```bash
export GDK_BACKEND=x11
python3 launch.py
```

---

## Where your data is stored

| Platform | Location |
|----------|----------|
| Windows  | `%LOCALAPPDATA%\Groundwork\groundwork.db` |
| macOS    | `~/Library/Application Support/Groundwork/groundwork.db` |
| Linux    | `~/.local/share/Groundwork/groundwork.db` |

Backups are stored in the same folder under `backups/`.
