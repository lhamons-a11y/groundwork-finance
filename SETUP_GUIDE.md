# Getting Started with Groundwork
### A personal finance app that actually tells you the truth

---

## Before you begin

You'll need a Windows computer. You don't need to install Python or any other software first — the installer handles everything.

**We suggest a computer whose operating system still gets security updates** (Windows 11 today). Groundwork holds your financial data, and an up-to-date system is the first thing protecting it. Groundwork still installs and runs on Windows 10, which no longer receives security updates; on an older computer that stays offline, that's perfectly fine.

---

## Step 1 — Download the installer

Go to the Groundwork releases page and download **GroundworkSetup.exe**.

> **GitHub link:** https://github.com/your-github-username/groundwork/releases

Click the file named `GroundworkSetup.exe` under the latest release. Your browser will download it to your Downloads folder.

---

## Step 2 — Install Groundwork

### Windows

Find `GroundworkSetup.exe` in your Downloads folder and double-click it.

**You may see a blue warning screen from Windows** that says "Windows protected your PC." This appears because the app is new and hasn't been downloaded by millions of people yet — not because it's dangerous. Here's what to do:

1. Click **More info**
2. Click **Run anyway**

The installer will open. Follow the steps — it takes about 30 seconds.

---

### macOS

Double-click `Groundwork-1.0.0.0.dmg` to open it. Drag the Groundwork icon into your Applications folder.

**You may see a warning:** "Groundwork cannot be opened because Apple cannot check it for malicious software." This appears because the app is not signed with an Apple Developer certificate. Here's what to do:

1. Right-click (or Control-click) on the Groundwork app in Applications
2. Click **Open**
3. Click **Open** again in the dialog that appears

You only need to do this once. After that, Groundwork opens normally.

---

### Linux

**Option A — AppImage (easiest):** No installation required. The AppImage runs on any modern Linux distribution.

```bash
chmod +x Groundwork-1.0.0.0.AppImage
./Groundwork-1.0.0.0.AppImage
```

**Option B — Manual install:**
```bash
tar -xzf groundwork-1.0.0.0-linux.tar.gz
cd Groundwork
sudo ./install_linux.sh
```

This installs Groundwork to `/opt/groundwork` and adds it to your Applications menu.

**Linux prerequisite:** Groundwork requires WebKit2GTK for its window. If the app doesn't open, run:
```bash
# Ubuntu / Debian
sudo apt install python3-gi gir1.2-webkit2-4.0

# Fedora
sudo dnf install python3-gobject webkit2gtk4.1

# Arch Linux
sudo pacman -S python-gobject webkit2gtk
```

---

## Step 3 — First launch

When Groundwork opens for the first time, you'll see a short setup screen with five questions:

1. **What's your monthly income?** — Your take-home pay after taxes
2. **What are your monthly expenses?** — Rent, groceries, utilities, etc.
3. **Do you have any debts?** — Credit cards, car loans, student loans
4. **What are your savings goals?** — Optional, you can skip this
5. **Your numbers** — The app shows you your financial picture

After that, you're on the main dashboard. Your debt-free date is on the screen. That number is real. It will change as you use the app.

---

## Step 4 — Import your bank transactions (optional but recommended)

The app works without importing — you can enter transactions manually. But importing gives it the full picture.

**To import from your bank:**
1. Log into your bank's website
2. Find the option to export or download your transactions (usually under Statements or Account History)
3. Download as CSV or OFX format
4. In Groundwork, go to **Settings → Import** and upload the file

The app will recognize your bank automatically and categorize your transactions. The first time you import, it will ask you to match any categories it doesn't recognize to your budget categories — this takes about a minute and it remembers your choices forever.

---

## Step 5 — Auto-import from Downloads (the easy way)

Once you have the app set up, there's an even easier way to import:

1. Download a bank statement to your Downloads folder as you normally would
2. Groundwork detects it automatically
3. A notification appears: "Harbor CSV detected — ready to import?"
4. Click Import

That's it. The file finds the app.

> **Note:** This feature requires one extra step. Open a Command Prompt and type:
> ```
> pip install watchdog
> ```
> Press Enter and wait about 30 seconds. Then restart Groundwork.
>
> If you're not sure how to open a Command Prompt, search "Command Prompt" in the Windows start menu.

---

## Step 6 — AI features (optional)

Groundwork includes an AI monthly report that writes a plain-English summary of your finances — not just numbers, but what they mean. It runs **only on your own computer**, using a free local model through [Ollama](https://ollama.com). There is no cloud AI, no account and no API key.

**The AI features are optional.** Everything else in the app works without them.

**To enable AI features:** in Groundwork, go to **Settings → AI features** and follow **Set up Local AI**. Groundwork installs Ollama and a small language model (a few GB of disk space).

If your computer doesn't have enough free memory to run a local model well, AI features stay off, and everything else works exactly the same. Reading PDF statements also needs the local model; without it, import your bank's CSV or QFX download instead.

---

## Your data

Everything Groundwork stores lives on your computer. Your financial data is never sent to any server, never sold, never used for advertising. The AI features run on your computer too, so they never send your data anywhere.

Your database is stored at:
```
C:\Users\[your name]\AppData\Local\Groundwork\groundwork.db
```

To back up your data: go to **Settings → Data & Backup → Create backup now**.

---

## Something went wrong?

**The app won't open:** Try downloading and installing the Microsoft WebView2 runtime from https://developer.microsoft.com/microsoft-edge/webview2/

**The window is blank:** Same fix — WebView2 runtime.

**Import isn't working:** Make sure you're downloading CSV or OFX format from your bank, not PDF.

**The AI report isn't working:** Open **Settings → AI features** and click **Test connection**. If the local model isn't reachable, follow **Set up Local AI**, or check that Ollama is running.

---

## A note on why this exists

Groundwork is free because it was built for the person who can't afford $99/year for a budgeting app. Financial software has always been built for people who already understand money. This one was built for people who weren't taught.

It will tell you the truth about your finances. It won't make you feel stupid for not already knowing. It will show you your debt-free date, which is probably sooner than you think.

Good luck.

---

*Groundwork v1.0.0.0 · Free and open source · No ads, no subscriptions, no cloud*
